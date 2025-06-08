from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlmodel import Session

from models.recommendation_task import (
    RecommendationTask,
    RecommendationTaskCreate,
    RecommendationTaskRead,
    TaskStatus,
)
from services.crud.recommendation_task import RecommendationTaskService
from services.rm.rm import rabbit_client
from services.logging.logging import get_logger
from database.database import get_session
from auth.authenticate import authenticate

recs_route = APIRouter()
logger = get_logger(__name__)

def get_task_service(session: Session = Depends(get_session)) -> RecommendationTaskService:
    return RecommendationTaskService(session)


@recs_route.post("/", response_model=RecommendationTaskRead, status_code=status.HTTP_201_CREATED)
def create_recommendation_task(
    task_data: RecommendationTaskCreate,
    task_service: RecommendationTaskService = Depends(get_task_service),
    user_email: str = Depends(authenticate)
):
    """
    Создание задачи на рекомендации и отправка в очередь RabbitMQ.
    """
    created_task = None
    try:
        # Создаём задачу в БД
        created_task = task_service.create(task_data)
        logger.info(f"RecommendationTask created: id={created_task.id}, user_id={created_task.user_id}, query={created_task.query}")

        # Отправляем в очередь
        rabbit_client.send_task(created_task)
        task_service.set_status(created_task.id, TaskStatus.QUEUED)

        return created_task

    except Exception as e:
        logger.error(f"Error sending recommendation task: {str(e)}")
        if created_task:
            task_service.set_status(created_task.id, TaskStatus.FAILED)
        raise HTTPException(status_code=500, detail="Failed to send recommendation task")


@recs_route.get("/", response_model=List[RecommendationTaskRead])
def get_all_tasks(
    task_service: RecommendationTaskService = Depends(get_task_service),
    user_email: str = Depends(authenticate)
):
    """
    Получение всех задач на рекомендации.
    """
    return task_service.get_all()


@recs_route.get("/{task_id}", response_model=RecommendationTaskRead)
def get_task_by_id(
    task_id: int,
    task_service: RecommendationTaskService = Depends(get_task_service),
    user_email: str = Depends(authenticate)
):
    """
    Получение статуса и результата задачи по ID.
    """
    task = task_service.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@recs_route.post("/send_task_result")
def receive_ml_result(
    task_id: int,
    result: str,
    task_service: RecommendationTaskService = Depends(get_task_service)
):
    """
    Получение результата предсказания от ML-воркера.
    Сохраняем результат в БД.
    """
    try:
        task = task_service.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        task_service.set_result(task_id, result)

        logger.info(f"ML result saved: task_id={task_id}, result={result}")
        return {"status": "ok", "task_id": task_id}
    except Exception as e:
        logger.error(f"Failed to save ML result: {e}")
        raise HTTPException(status_code=500, detail="Failed to save ML result")
