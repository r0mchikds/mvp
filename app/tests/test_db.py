import pytest
from sqlmodel import Session
from models.user import User, UserCreate
from models.item import Item
from pydantic import ValidationError
from auth.hash_password import HashPassword


def test_create_user(session: Session):
    user = User(
        email="newuser@test.com",
        password=HashPassword().create_hash("1234test")
    )
    session.add(user)
    session.commit()

    fetched_user = session.get(User, user.id)
    assert fetched_user is not None
    assert fetched_user.email == "newuser@test.com"


def test_fail_create_user(session: Session):
    with pytest.raises(ValidationError):
        UserCreate(email="baduser@test.com", password="12")


def test_delete_user(session: Session):
    user = User(
        email="tobedeleted@test.com",
        password=HashPassword().create_hash("1234test")
    )
    session.add(user)
    session.commit()

    session.delete(user)
    session.commit()

    assert session.get(User, user.id) is None
