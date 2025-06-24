import os
from sqlmodel import SQLModel, Session, select
from models import user, item
from models.user import User
from models.item import Item
from auth.hash_password import HashPassword
from database.database import get_database_engine
import csv
import ast
import json
import pathlib
import logging # log


BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
ITEMS_CSV_PATH = BASE_DIR / "data" / "amazon_items_projected.csv"

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO)

def init_db(drop_all: bool = False) -> None:
    """
    Инициализация схемы базы данных.
    
    Аргументы:
        drop_all: Если True, удаляет все таблицы перед созданием
    
    Исключения:
        Exception: Любые исключения, связанные с базой данных
    """
    try:
        engine = get_database_engine()
        logger.info("Создание engine: %s", engine.url)
        if drop_all:
            # Удаление всех таблиц, если указано
            SQLModel.metadata.drop_all(engine)
        
        logger.info("Создание таблиц...")
        # Создание всех таблиц
        SQLModel.metadata.create_all(engine)
        logger.info("Таблицы в БД после create_all: %s", list(SQLModel.metadata.tables.keys()))
        logger.info("Таблицы созданы")

        # Создание начальных данных
        with Session(engine) as session:
            logger.info("Проверка пользователей в БД...")
             # Создание тестовых пользователей
            if session.exec(select(User)).first() is None:
                hash_password = HashPassword()

                user1 = User(
                    email="user1@example.com",
                    password=hash_password.create_hash("123user")
                )
                user2 = User(
                    email="user2@example.com",
                    password=hash_password.create_hash("123other")
                )
                session.add_all([user1, user2])
                session.commit()
                logger.info("Добавлены тестовые пользователи")

                users = session.exec(select(User)).all()
                for u in users:
                    logger.info("User in DB: id=%s, email=%s, created_at=%s", u.id, u.email, u.created_at)

            logger.info("Проверка товаров в БД...")
            # Загрузка товаров из CSV
            if session.exec(select(Item)).first() is None:
                logger.info("Начинаем загрузку CSV: %s", ITEMS_CSV_PATH)
                if not os.path.exists(ITEMS_CSV_PATH):
                    raise FileNotFoundError(f"Файл с товарами не найден: {ITEMS_CSV_PATH}")

                with open(ITEMS_CSV_PATH, encoding="utf-8") as f:
                    reader = csv.DictReader(f)

                    batch = []
                    batch_size = 5000
                    total_loaded = 0

                    for idx, row in enumerate(reader):
                        try:
                            embedding = ast.literal_eval(row["embedding"])
                            embedding = json.dumps(embedding) if isinstance(embedding, list) else None
                        except Exception:
                            embedding = None

                        try:
                            embedding_proj = ast.literal_eval(row["embedding_proj"])
                            embedding_proj = json.dumps(embedding_proj) if isinstance(embedding_proj, list) else None
                        except Exception:
                            embedding_proj = None

                        item = Item(
                            title=row["title"],
                            description=row.get("description"),
                            image_url=row.get("image_url"),
                            embedding=embedding,
                            embedding_proj=embedding_proj,
                            popularity_score=int(row.get("popularity_score", 0))
                        )

                        batch.append(item)

                        if len(batch) >= batch_size:
                            session.add_all(batch)
                            session.commit()
                            total_loaded += len(batch)
                            logger.info(f"Загружено товаров: {total_loaded}")
                            batch.clear()
                        
                    # Commit оставшихся айтемов
                    if batch:
                        session.add_all(batch)
                        session.commit()
                        total_loaded += len(batch)
                        logger.info(f"Загружено товаров (финальный батч): {total_loaded}")

                items_in_db = session.exec(select(Item).limit(3)).all()
                for it in items_in_db:
                    logger.info("Item in DB: id=%s, title=%s, popularity_score=%s", it.id, it.title, it.popularity_score)
                
                 # Проверка эмбеддинга
                sample_item = session.exec(select(Item).where(Item.embedding.is_not(None))).first()
                if sample_item:
                    logger.info("Sample item id=%s, title=%s", sample_item.id, sample_item.title)
                    logger.info("Raw embedding (truncated): %s...", sample_item.embedding[:100])

                    try:
                        embedding_list = json.loads(sample_item.embedding)
                        logger.info("Parsed embedding length: %d, type of first element: %s", 
                                    len(embedding_list), type(embedding_list[0]) if embedding_list else "empty")
                    except Exception as e:
                        logger.error("Ошибка при десериализации embedding: %s", e)

    except Exception as e:
        raise RuntimeError(f"Ошибка инициализации базы данных: {e}")
