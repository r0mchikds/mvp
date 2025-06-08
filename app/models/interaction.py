from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING


if TYPE_CHECKING:
    from models.user import User
    from models.item import Item

class InteractionBase(SQLModel):
    """
    Общие поля для лайков (user_id и item_id).
    """
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    item_id: int = Field(foreign_key="item.id", primary_key=True)

class Interaction(InteractionBase, table=True):
    """
    Таблица взаимодействий пользователя с товаром (лайк/дизлайк).
    """
    liked: bool = Field(default=True, description="Является ли это лайком")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    user: Optional["User"] = Relationship(back_populates="interactions")
    item: Optional["Item"] = Relationship(back_populates="interactions")

class InteractionCreate(InteractionBase):
    """
    Схема для создания лайка.
    """
    pass
