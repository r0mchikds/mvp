import torch
import torch.nn as nn
import torch.nn.functional as F
from rmq.rmqconf import RabbitMQConfig
import pika
import time
import requests
import logging
import json
import numpy as np
from sqlmodel import Session, select
from models.item import Item
from models.interaction import Interaction
from models.user import User
from models.recommendation_task import RecommendationTask
from services.crud import user as UserService
from database.database import get_database_engine
import socket


logger = logging.getLogger(__name__)
hostname = socket.gethostname()

logging.basicConfig(
    level=logging.INFO,
    format=f'%(asctime)s - {hostname} - %(name)s - %(levelname)s - %(message)s'
)

logging.getLogger('pika').setLevel(logging.INFO)

class CLIPCosineModel(nn.Module):
    def __init__(self, init_scale=2.0):
        super().__init__()
        self.scale = nn.Parameter(torch.tensor(init_scale))

    def forward(self, user_vec, item_vec):
        user_norm = F.normalize(user_vec, p=2, dim=1)
        item_norm = F.normalize(item_vec, p=2, dim=1)
        cosine = (user_norm * item_norm).sum(dim=1, keepdim=True)
        return torch.sigmoid(self.scale * cosine)

# Определяем основной класс для обработки ML задач
class MLWorker:
    MAX_RETRIES = 3
    RETRY_DELAY = 0.5
    RESULT_ENDPOINT = 'http://app:8080/api/recommendation/send_task_result'

    def __init__(self, config: RabbitMQConfig):
        self.config = config
        self.connection = None
        self.channel = None
        self.retry_count = 0

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = CLIPCosineModel()
        self.model.load_state_dict(torch.load("ml_models/clip_cosine_best_model.pth", map_location=self.device))
        self.model.to(self.device)
        self.model.eval()

    def connect(self) -> None:
        while True:
            try:
                connection_params = self.config.get_connection_params()
                self.connection = pika.BlockingConnection(connection_params)
                self.channel = self.connection.channel()
                self.channel.queue_declare(queue=self.config.queue_name)
                logger.info("Successfully connected to RabbitMQ")
                break
            except Exception as e:
                logger.error(f"Failed to connect to RabbitMQ: {e}")
                time.sleep(self.RETRY_DELAY)

    def cleanup(self):
        try:
            if self.channel:
                self.channel.close()
            if self.connection:
                self.connection.close()
            logger.info("Соединения успешно закрыты")
        except Exception as e:
            logger.error(f"Ошибка при закрытии соединений: {e}")

    def send_result(self, task_id: str, result: str) -> bool:
        try:
            response = requests.post(
                self.RESULT_ENDPOINT,
                params={'task_id': task_id, 'result': result}
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to send result: {e}")
            return False

    def process_message(self, ch, method, properties, body):
        try:
            logger.info(f"Processing message: {body}")
            data = json.loads(body.decode("utf-8"))

            user_id = data.get("user_id")
            
            # Получаем top_n от клиента (может быть до 50), но ограничим в зависимости от задачи
            requested_top_n = int(data.get("top_n", 10))
            top_n = min(requested_top_n, 50) if data.get("query") else 10

            task_id = data.get("task_id")
            filter_item_ids = data.get("item_ids")
            query_text = data.get("query")

            query = select(Item).where(Item.embedding != None)

            # Если есть query (поисковый запрос) — фильтруем по title/description
            if query_text:
                logger.info(f"Поисковый запрос от пользователя: {query_text}")
                query = query.where(
                    (Item.title.ilike(f"%{query_text}%")) |
                    (Item.description.ilike(f"%{query_text}%"))
                )
            
            # Если заданы item_ids напрямую (например, через старый механизм) — фильтруем по ним
            elif filter_item_ids:
                logger.info(f"Фильтрация item_ids: {filter_item_ids[:10]}... (всего {len(filter_item_ids)})")
                query = query.where(Item.id.in_(filter_item_ids))

            if user_id is None or task_id is None:
                raise ValueError("Missing user_id or task_id")

            engine = get_database_engine()
            with Session(engine) as session:
                users = session.exec(select(User)).all()
                for u in users:
                    logger.info("User in DB: id=%s, email=%s, created_at=%s", u.id, u.email, u.created_at)

                logger.info(f"Запрашиваем user_id={user_id} из базы...")
                user = UserService.get_user_by_id(user_id, session)

                if not user:
                    logger.error(f"Пользователь с id={user_id} не найден в базе")
                    raise ValueError("User not found")
                
                logger.info(f"Пользователь найден: {user.email} (id={user.id})")
                
                if not user.embedding:
                    logger.warning(f"Embedding у пользователя id={user.id} отсутствует")

                    base_query = select(Item).where(Item.embedding != None)

                    if query_text:
                        logger.info(f"[Fallback+Query] Фильтруем по запросу: {query_text}")
                        base_query = base_query.where(
                            (Item.title.ilike(f"%{query_text}%")) |
                            (Item.description.ilike(f"%{query_text}%"))
                        )
                    
                    items = session.exec(base_query.order_by(Item.popularity_score.desc())).all()
                    top_items = [item.id for item in items[:top_n]]

                    logger.info(f"[Fallback] Top popular items for user {user.id}: {top_items}")
                    result = json.dumps(top_items)

                    if self.send_result(task_id, result):
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                        logger.info("Task completed successfully (fallback)")
                    else:
                        raise Exception("Failed to send fallback result")
                    return
                
                user_emb = json.loads(user.embedding)
                logger.info(f"Размерность user embedding: {len(user_emb)}")
                
                items = session.exec(query).all()

                user_tensor = torch.tensor(user_emb, dtype=torch.float32).unsqueeze(0).to(self.device)

                scored = []
                for item in items:
                    item_emb = json.loads(item.embedding)
                    item_tensor = torch.tensor(item_emb, dtype=torch.float32).unsqueeze(0).to(self.device)
                    with torch.no_grad():
                        score = self.model(user_tensor, item_tensor).item()
                    scored.append((item.id, score))

            scored.sort(key=lambda x: x[1], reverse=True)
            top_items = [item_id for item_id, _ in scored[:top_n]]

            logger.info(f"Top items for user {user_id}: {top_items}")
            result = json.dumps(top_items)

            if self.send_result(task_id, result):
                ch.basic_ack(delivery_tag=method.delivery_tag)
                logger.info("Task completed successfully")
            else:
                raise Exception("Failed to send result")

        except Exception as e:
            logger.error(f"Error processing task: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def start_consuming(self) -> None:
        try:
            self.channel.basic_consume(
                queue=self.config.queue_name,
                on_message_callback=self.process_message,
                auto_ack=False
            )
            logger.info('Started consuming messages. Press Ctrl+C to exit.')
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.cleanup()
