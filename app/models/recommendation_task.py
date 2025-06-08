from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from models.user import User


class TaskStatus(str, Enum):
    NEW = "new"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class RecommendationTaskBase(SQLModel):
    status: TaskStatus = Field(default=TaskStatus.NEW)
    result: Optional[str] = Field(default=None, description="Сырые рекомендации или путь к результату")
    top_n: Optional[int] = Field(default=10, description="Количество запрашиваемых рекомендаций")
    query: Optional[str] = Field(default=None, description="Поисковый запрос (если задача от поиска)")

class RecommendationTask(RecommendationTaskBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional["User"] = Relationship(back_populates="recommendation_tasks")

    def to_queue_message(self) -> dict:
        return {
            "task_id": self.id,
            "user_id": self.user_id,
            "top_n": self.top_n,
            "query": self.query
        }


class RecommendationTaskCreate(RecommendationTaskBase):
    user_id: int
    top_n: Optional[int] = 10

class RecommendationTaskRead(SQLModel):
    id: int
    user_id: int
    top_n: int
    status: TaskStatus
    result: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
