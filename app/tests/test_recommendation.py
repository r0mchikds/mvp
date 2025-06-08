import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from sqlmodel import Session, select
from models.recommendation_task import RecommendationTask, TaskStatus
from models.user import User


@pytest.fixture
def test_user(session: Session) -> User:
    return session.exec(select(User).where(User.email == "user@test.com")).first()


def test_create_recommendation_task(client: TestClient, test_user: User, session: Session):
    task_payload = {
        "user_id": test_user.id,
        "top_n": 5,
    }

    # Мокаем отправку задачи в очередь
    with patch("services.rm.rm.rabbit_client.send_task") as mock_send_task:
        mock_send_task.return_value = None

        response = client.post("/api/recommendation/", json=task_payload)
        assert response.status_code == 201
        task_data = response.json()

        assert task_data["user_id"] == test_user.id
        assert task_data["status"] == "queued"
        assert task_data["top_n"] == 5

        task_id = task_data["id"]
        db_task = session.get(RecommendationTask, task_id)
        assert db_task.status == TaskStatus.QUEUED


def test_receive_ml_result(client: TestClient, test_user: User, session: Session):
    # Создаем задание
    task = RecommendationTask(user_id=test_user.id, top_n=5, status=TaskStatus.QUEUED)
    session.add(task)
    session.commit()
    session.refresh(task)

    # Отправляем результат от ML-воркера
    payload = {"task_id": task.id, "result": "[1, 2, 3, 4, 5]"}
    response = client.post(f"/api/recommendation/send_task_result", params=payload)

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    updated_task = session.get(RecommendationTask, task.id)
    assert updated_task.status == TaskStatus.COMPLETED
    assert updated_task.result == "[1, 2, 3, 4, 5]"
