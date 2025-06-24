import os
import gdown
from services.logging.logging import get_logger
from database.config import get_settings


settings = get_settings()
logger = get_logger(logger_name=__name__)
# Путь до файла
file_path = "data/amazon_items_projected.csv"
# Ссылка (ID) на Google Drive файл
file_id = settings.DATA_FILE_ID
# Полученная ссылка от gdown
gdrive_url = f"https://drive.google.com/uc?id={file_id}"

os.makedirs("data", exist_ok=True)

if not os.path.exists(file_path):
    logger.info(f"[startup] Файл {file_path} не найден. Скачиваем с Google Drive...")
    try:
        gdown.download(gdrive_url, file_path, quiet=False)
        logger.info(f"[startup] Файл {file_path} успешно скачан.")
    except Exception as e:
        logger.error(f"[startup] Ошибка при скачивании: {str(e)}")
else:
    logger.info(f"[startup] Файл {file_path} уже существует. Пропускаем загрузку.")
