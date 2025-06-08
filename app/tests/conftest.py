import pytest
from fastapi.testclient import TestClient
from api import app
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool
from database.database import get_session
from auth.authenticate import authenticate
from models.user import User
from auth.hash_password import HashPassword


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        hash_password = HashPassword()

        # Первый пользователь
        session.add(User(
            email="user@test.com",
            password=hash_password.create_hash("1234test")
        ))

        # Второй пользователь — используется в тестах login / get_user_by_email
        session.add(User(
            email="test_user@test.com",
            password=hash_password.create_hash("1234test")
        ))

        session.commit()
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """
    Фикстура клиента с подменой зависимостей.
    """
    # Подменяем get_session на тестовую сессию
    def get_session_override():
        return session

    # Подменяем authenticate на фиктивного пользователя
    def fake_authenticate():
        return "user@test.com"

    app.dependency_overrides[get_session] = get_session_override
    app.dependency_overrides[authenticate] = fake_authenticate

    client = TestClient(app)
    yield client

    app.dependency_overrides.clear()
