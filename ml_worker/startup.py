import os
import gdown
import logging


# Настройка логирования как в main.py
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Получаем file_id из переменной окружения
file_id = os.getenv("MODEL_FILE_ID")
if not file_id:
    raise ValueError("MODEL_FILE_ID не задан в .env файле")

# Путь до модели
model_path = "ml_models/contrastive_rating_best.pth"
gdrive_url = f"https://drive.google.com/uc?id={file_id}"

# Создание директории при необходимости
os.makedirs("ml_models", exist_ok=True)

# Скачивание, если файл отсутствует
if not os.path.exists(model_path):
    logger.info(f"[startup] Модель {model_path} не найдена. Скачиваем с Google Drive...")
    try:
        gdown.download(gdrive_url, model_path, quiet=False)
        logger.info(f"[startup] Модель {model_path} успешно скачана.")
    except Exception as e:
        logger.error(f"[startup] Ошибка при скачивании модели: {str(e)}")
else:
    logger.info(f"[startup] Модель {model_path} уже существует. Пропускаем загрузку.")
