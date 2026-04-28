import logging

from config import get_settings
from indexer.cms_sync import CMSExtractor

logger = logging.getLogger(__name__)

def run_sync_task():
    logger.info("Запуск процесса переиндексации...")
    settings = get_settings()
    try:
        extractor = CMSExtractor(settings=settings)
        data = extractor.extract_data()

        logger.info(f"Переиндексация успешно завершена. Обработано записей: {len(data)}")

    except Exception as e:
        logger.error(f"Ошибка во время переиндексации: {e}")