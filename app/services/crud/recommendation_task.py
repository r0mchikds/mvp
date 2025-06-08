from datetime import datetime
from typing import List, Optional
from sqlmodel import Session, select

from models.recommendation_task import (
    RecommendationTask,
    RecommendationTaskCreate,
    TaskStatus,
)

class RecommendationTaskService:
    def __init__(self, session: Session):
        self.session = session

    def create(self, task_create: RecommendationTaskCreate) -> RecommendationTask:
        """Создаёт новую задачу на рекомендации"""
        task = RecommendationTask(
            user_id=task_create.user_id,
            top_n=task_create.top_n or 10,
            query=task_create.query,
            status=TaskStatus.NEW
        )
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return task

    def get(self, task_id: int) -> Optional[RecommendationTask]:
        """Получает задачу по ID"""
        return self.session.get(RecommendationTask, task_id)

    def get_all(self, skip: int = 0, limit: int = 100) -> List[RecommendationTask]:
        """Получает все задачи"""
        statement = select(RecommendationTask).offset(skip).limit(limit)
        return self.session.exec(statement).all()

    def set_status(self, task_id: int, status: TaskStatus) -> Optional[RecommendationTask]:
        """Обновляет статус задачи"""
        task = self.get(task_id)
        if not task:
            return None
        task.status = status
        task.updated_at = datetime.utcnow()
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return task

    def set_result(self, task_id: int, result: str) -> Optional[RecommendationTask]:
        """Устанавливает результат задачи"""
        task = self.get(task_id)
        if not task:
            return None
        task.result = result
        task.status = TaskStatus.COMPLETED
        task.updated_at = datetime.utcnow()
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return task

    def delete(self, task_id: int) -> bool:
        """Удаляет задачу"""
        task = self.get(task_id)
        if not task:
            return False
        self.session.delete(task)
        self.session.commit()
        return True
