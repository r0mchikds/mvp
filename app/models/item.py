from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import Column, Text


if TYPE_CHECKING:
    from models.interaction import Interaction


class ItemBase(SQLModel):
    title: str = Field(
        ..., 
        description="Название товара",
        sa_column=Column(Text)  # убираем ограничение 255 символов
    )
    description: Optional[str] = Field(
        default=None,
        description="Описание товара",
        sa_column=Column(Text)
    )
    image_url: Optional[str] = Field(
        default=None,
        description="Ссылка на изображение товара",
        sa_column=Column(Text)
    )

class Item(ItemBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # эмбеддинги для мультимодальной модели
    embedding: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Сырой CLIP-вектор товара (для user-вектора)"
    )
    
    embedding_proj: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Проецированный нормализованный эмбеддинг товара (для FAISS)"
    )

    # поле популярности (baseline рекомендаций)
    popularity_score: int = Field(default=0, description="Счёт популярности товара")

    # связи
    interactions: List["Interaction"] = Relationship(back_populates="item")

    def __str__(self):
        return f"Item(id={self.id}, title={self.title})"


class ItemCreate(ItemBase):
    pass


class ItemRead(SQLModel):
    id: int
    title: str
    description: Optional[str]
    image_url: Optional[str]
    created_at: datetime
    popularity_score: int

    class Config:
        from_attributes = True
