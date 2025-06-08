from typing import List, Optional
from sqlmodel import Session, select
from models.interaction import Interaction
from models.user import User
from models.item import Item


def create_interaction(user_id: int, item_id: int, session: Session) -> Interaction:
    """
    Создаёт новое взаимодействие (лайк) между пользователем и товаром.
    """
    interaction = Interaction(user_id=user_id, item_id=item_id)
    try:
        session.add(interaction)
        session.commit()
        session.refresh(interaction)
        return interaction
    except Exception as e:
        session.rollback()
        raise

def get_interaction(user_id: int, item_id: int, session: Session) -> Optional[Interaction]:
    """
    Проверяет, существует ли взаимодействие между пользователем и товаром.
    """
    try:
        statement = select(Interaction).where(
            (Interaction.user_id == user_id) & (Interaction.item_id == item_id)
        )
        return session.exec(statement).first()
    except Exception as e:
        raise

def delete_interaction(user_id: int, item_id: int, session: Session) -> bool:
    """
    Удаляет взаимодействие (отмена лайка) по user_id и item_id.
    """
    interaction = get_interaction(user_id, item_id, session)
    if interaction:
        try:
            session.delete(interaction)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise
    return False

def get_user_liked_items(user_id: int, session: Session) -> List[Item]:
    """
    Возвращает список товаров, которые пользователь лайкнул.
    """
    try:
        statement = select(Item).join(Interaction).where(Interaction.user_id == user_id)
        return session.exec(statement).all()
    except Exception as e:
        raise

def get_item_liked_by_users(item_id: int, session: Session) -> List[User]:
    """
    Возвращает список пользователей, лайкнувших данный товар.
    """
    try:
        statement = select(User).join(Interaction).where(Interaction.item_id == item_id)
        return session.exec(statement).all()
    except Exception as e:
        raise
