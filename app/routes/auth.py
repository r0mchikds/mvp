from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from auth.hash_password import HashPassword
from auth.jwt_handler import create_access_token
from auth.authenticate import  authenticate
from database.database import get_session
from services.crud import user as UsersService
from database.config import get_settings
from typing import Dict


# Получаем настройки приложения
settings = get_settings()
# Создаем экземпляр роутера
auth_route = APIRouter()
# Создаем экземпляр для хеширования паролей
hash_password = HashPassword()

@auth_route.post("/token")
async def login_for_access_token(
    response: Response,
    form_data: OAuth2PasswordRequestForm=Depends(),
    session=Depends(get_session)
) -> Dict[str, str]:
    """
    Создает access token для аутентифицированного пользователя.

    Args:
        response (Response): Объект HTTP-ответа для установки cookie
        form_data (OAuth2PasswordRequestForm): Данные формы с email и паролем
        session (Session): Сессия базы данных

    Returns:
        Dict[str, str]: Словарь с токеном и типом токена

    Raises:
        HTTPException: 404 если пользователь не найден
        HTTPException: 401 если неверные учетные данные
    """    
    # Проверяем существование пользователя по email
    user_exist = UsersService.get_user_by_email(form_data.username, session)
    if user_exist is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not exist"
        )
    
    # Проверяем правильность пароля
    if hash_password.verify_hash(form_data.password, user_exist.password):
        # Создаем JWT токен
        access_token = create_access_token(user_exist.email)
        # Устанавливаем токен в cookie
        response.set_cookie(
            key=settings.COOKIE_NAME, 
            value=f"Bearer {access_token}", 
            httponly=True
        )
        
        # Возвращаем токен в ответе
        return {settings.COOKIE_NAME: access_token, "token_type": "bearer"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid details passed."
    )

@auth_route.get("/logout")
async def logout(response: Response) -> Dict[str, str]:
    """
    Удаляет куку с access token (logout).
    """
    response.delete_cookie(settings.COOKIE_NAME)
    return {"message": "Successfully logged out"}
