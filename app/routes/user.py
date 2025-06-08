from fastapi import APIRouter, HTTPException, status, Depends
from database.database import get_session
from auth.hash_password import HashPassword
from models.user import UserCreate, UserRead
from services.crud import user as UserService
from typing import List, Dict
from services.logging.logging import get_logger


logger = get_logger(logger_name=__name__)
user_route = APIRouter()
hash_password = HashPassword()

@user_route.post(
    '/signup',
    response_model=Dict[str, str],
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация пользователя",
    description="Регистрация нового пользователя с помощью email и пароля")
async def signup(user: UserCreate, session=Depends(get_session)) -> Dict[str, str]:
    """
    Создание новой учетной записи пользователя.

    Аргументы:
        user: Данные для регистрации пользователя
        session: Сессия базы данных

    Возвращает:
        Dict: Сообщение об успешной регистрации

    Исключения:
        HTTPException: Если пользователь уже существует
    """

    try:
        user_exist = UserService.get_user_by_email(user.email, session)
        
        if user_exist:
            raise HTTPException( 
                status_code=status.HTTP_409_CONFLICT, 
                detail="User with email provided exists already.")
        
        user.password = hash_password.create_hash(user.password)
        UserService.create_user(user, session)
        return {"message": "User created successfully"}

    except HTTPException as http_exc:
        raise http_exc  # пробрасываем как есть

    except Exception as e:
        logger.error(f"Error during signup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user"
        )

@user_route.get(
    "/",
    response_model=List[UserRead],
    summary="Получение всех пользователей",
    description="Возвращает список всех зарегистрированных пользователей"
)
async def get_all_users(session=Depends(get_session)) -> List[UserRead]:
    """
    Получает список всех пользователей.
    """
    try:
        users = UserService.get_all_users(session)
        return users
    except Exception as e:
        logger.error(f"Get users error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve users"
        )

@user_route.get(
    "/by_email",
    response_model=UserRead,
    summary="Получение пользователя по email",
    description="Возвращает информацию о пользователе по email"
)
async def get_user_by_email(email: str, session=Depends(get_session)) -> UserRead:
    try:
        user = UserService.get_user_by_email(email, session)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except Exception as e:
        logger.error(f"Get user by email error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve user"
        )
