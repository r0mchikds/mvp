from fastapi import APIRouter, Depends, HTTPException, Request
from auth.authenticate import authenticate
from typing import Dict


home_route = APIRouter()

@home_route.get("/private")
async def private_route(request: Request, user: str = Depends(authenticate)):
    """
    Приватный API эндпоинт, доступный только авторизованным пользователям.

    Args:
        request (Request): Запрос
        user (str): Email пользователя, извлечённый из токена

    Returns:
        dict: Информация о пользователе
    """
    return {"user": user}

@home_route.get(
    "/health",
    response_model=Dict[str, str],
    summary="Проверка работоспособности",
    description="Возвращает статус работоспособности сервиса"
)
async def health_check() -> Dict[str, str]:
    """
    Эндпоинт проверки работоспособности сервиса.
    """
    try:
        return {"status": "healthy"}
    except Exception as e:
        raise HTTPException(
            status_code=503, 
            detail="Service unavailable"
        )
