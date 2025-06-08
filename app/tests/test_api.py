import pytest
from fastapi.testclient import TestClient
from models.user import UserCreate
from sqlmodel import Session


def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_signup(client: TestClient):
    user_data = {
        "email": "signup_unique_user@test.com",
        "password": "1234test"
    }
    response = client.post("/api/users/signup", json=user_data)
    assert response.status_code == 201
    assert response.json() == {"message": "User created successfully"}


def test_duplicate_signup(client: TestClient):
    # Повторная регистрация того же пользователя
    user_data = {
        "email": "test_user@test.com",
        "password": "1234test"
    }
    response = client.post("/api/users/signup", json=user_data)
    assert response.status_code == 409
    assert response.json()["detail"] == "User with email provided exists already."


def test_login(client: TestClient):
    login_data = {
        "username": "test_user@test.com",
        "password": "1234test"
    }
    response = client.post("/auth/token", data=login_data)
    assert response.status_code == 200
    assert "RECS_API" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_get_all_users(client: TestClient):
    response = client.get("/api/users/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert any(user["email"] == "test_user@test.com" for user in response.json())


def test_get_user_by_email(client: TestClient):
    response = client.get("/api/users/by_email", params={"email": "test_user@test.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test_user@test.com"


def test_logout(client: TestClient):
    response = client.get("/auth/logout")
    assert response.status_code == 200
    assert response.json() == {"message": "Successfully logged out"}


def test_search_by_ids(client: TestClient, session: Session):
    # Добавим товар в базу, чтобы было что искать
    from models.item import Item
    item = Item(
        title="Test Product",
        description="Test description",
        image_url="http://example.com/image.jpg",
        popularity_score=10
    )
    session.add(item)
    session.commit()

    # Отправим ID товара для поиска
    response = client.post("/api/search/by_ids", json={"item_ids": [item.id]})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data[0]["title"] == "Test Product"
