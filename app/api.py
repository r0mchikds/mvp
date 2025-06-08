from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.home import home_route
from routes.user import user_route
from routes.auth import auth_route
from routes.recommendation import recs_route
from routes.search import search_route
from routes.interaction import interaction_route

from database.initdb import init_db
from database.config import get_settings
from services.logging.logging import get_logger
import uvicorn

from sqlmodel import Session, select
from models.user import User
from models.item import Item
from database.database import get_database_engine
import subprocess


logger = get_logger(logger_name=__name__)
settings = get_settings()
subprocess.run(["python", "startup.py"], check=True)

def create_application() -> FastAPI:
    """
    Создание и конфигурация FastAPI приложения.
    
    Возвращает:
        FastAPI: Настроенный экземпляр приложения
    """
    
    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.API_VERSION,
        docs_url="/api/docs",
        redoc_url="/api/redoc"
    )
    
   # Настройка CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Регистрация маршрутов
    app.include_router(home_route, tags=['Home'])
    app.include_router(auth_route, prefix='/auth', tags=['Auth'])
    app.include_router(user_route, prefix='/api/users', tags=['Users'])
    app.include_router(recs_route, prefix="/api/recommendation", tags=["Recommendation"])
    app.include_router(search_route, prefix="/api/search", tags=["Search"])
    app.include_router(interaction_route, prefix="/api/interaction", tags=["Interaction"])

    return app

app = create_application()

@app.on_event("startup") 
def on_startup():
    try:
        logger.info("Инициализация базы данных...")
        init_db(drop_all=True)
        logger.info("Запуск приложения успешно завершен")

        # 💡 Проверка наличия данных сразу после запуска
        engine = get_database_engine()
        with Session(engine) as session:
            users = session.exec(select(User)).all()
            for u in users:
                logger.info("POST-startup user: id=%s, email=%s", u.id, u.email)

            items = session.exec(select(Item).limit(5)).all()
            for it in items:
                logger.info("POST-startup item: id=%s, title=%s", it.id, it.title)


    except Exception as e:
        logger.error(f"Ошибка при запуске: {str(e)}")
        raise
    
@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при завершении работы приложения."""
    logger.info("Завершение работы приложения...")

if __name__ == '__main__':
    uvicorn.run(
        'api:app',
        host='0.0.0.0',
        port=8080,
        reload=True,
        log_level="info"
    )
