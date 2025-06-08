from typing import List, Optional
from sqlmodel import Session, select
from models.item import Item, ItemCreate
from sqlalchemy.orm import selectinload


def get_all_items(session: Session) -> List[Item]:
    """
    Получает список всех товаров.
    """
    try:
        statement = select(Item).options(selectinload(Item.interactions))
        return session.exec(statement).all()
    except Exception as e:
        raise


def get_item_by_id(item_id: int, session: Session) -> Optional[Item]:
    """
    Получает товар по ID.
    """
    try:
        statement = select(Item).where(Item.id == item_id).options(selectinload(Item.interactions))
        return session.exec(statement).first()
    except Exception as e:
        raise


def create_item(item: ItemCreate, session: Session) -> Item:
    """
    Создаёт новый товар.
    """
    db_item = Item.model_validate(item)
    try:
        session.add(db_item)
        session.commit()
        session.refresh(db_item)
        return db_item
    except Exception as e:
        session.rollback()
        raise


def delete_item(item_id: int, session: Session) -> bool:
    """
    Удаляет товар по ID.
    """
    try:
        item = get_item_by_id(item_id, session)
        if item:
            session.delete(item)
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        raise
