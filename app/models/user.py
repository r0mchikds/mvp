from sqlmodel import SQLModel, Field, Relationship
from pydantic import EmailStr
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
import json
from sqlalchemy import Column, Text


if TYPE_CHECKING:
    from models.interaction import Interaction
    from models.recommendation_task import RecommendationTask


class UserBase(SQLModel):
    email: EmailStr = Field(
        ...,
        unique=True,
        index=True,
        description="Электронная почта пользователя"
    )
    password: str = Field(
        ..., 
        min_length=4,
        description="Хешированный пароль"
    )


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # эмбеддинг храним как JSON или text; зависит от БД — можно оптимизировать позже
    embedding: Optional[str] = Field(default=None, sa_column=Column(Text), description="Вектор предпочтений пользователя")

    # связи (заполним позже)
    interactions: List["Interaction"] = Relationship(back_populates="user")

    recommendation_tasks: List["RecommendationTask"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    
    def __str__(self):
        return f"User(id={self.id}, email={self.email})"


class UserCreate(UserBase):
    pass


class UserRead(SQLModel):
    id: int
    email: str
    created_at: datetime

    class Config:
        from_attributes = True
