from models.user import User, UserCreate
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from typing import List, Optional


def get_all_users(session: Session) -> List[User]:
    """
    Получает всех пользователей с их взаимодействиями.
    """
    try:
        statement = select(User).options(
            selectinload(User.interactions)
        )
        return session.exec(statement).all()
    except Exception as e:
        raise

def get_user_by_id(user_id: int, session: Session) -> Optional[User]:
    """
    Получает пользователя по ID.
    """
    try:
        statement = select(User).where(User.id == user_id).options(
            selectinload(User.interactions)
        )
        return session.exec(statement).first()
    except Exception as e:
        raise

def get_user_by_email(email: str, session: Session) -> Optional[User]:
    """
    Получает пользователя по email.
    """
    try:
        statement = select(User).where(User.email == email).options(
            selectinload(User.interactions)
        )
        return session.exec(statement).first()
    except Exception as e:
        raise

def create_user(user: UserCreate, session: Session) -> User:
    """
    Создаёт нового пользователя.
    """
    db_user = User.model_validate(user)  # Pydantic v2
    try:
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        return db_user
    except Exception as e:
        session.rollback()
        raise

def delete_user(user_id: int, session: Session) -> bool:
    """
    Удаляет пользователя по ID.
    """
    try:
        user = get_user_by_id(user_id, session)
        if user:
            session.delete(user)
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        raise
