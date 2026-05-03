import logging
from config import get_settings
from indexer.meili_indexer import MeiliIndexer

logger = logging.getLogger(__name__)

def _get_active_indexer():
    settings = get_settings()
    if settings.SEARCH_PROVIDER == "meilisearch":
        return MeiliIndexer(settings)
    return None

def run_full_sync_task():
    logger.info("Запуск ПОЛНОЙ переиндексации...")
    try:
        indexer = _get_active_indexer()
        if indexer:
            indexer.full_sync()
            logger.info("Полная переиндексация успешно завершена.")
        else:
            logger.warning("Провайдер не поддерживает переиндексацию (возможно включен mock).")
    except Exception as e:
        logger.error(f"Ошибка во время полной переиндексации: {e}")

def run_incremental_sync_task():
    logger.info("Запуск ЧАСТИЧНОЙ переиндексации...")
    try:
        indexer = _get_active_indexer()
        if indexer:
            indexer.incremental_sync()
            logger.info("Частичная переиндексация успешно завершена.")
    except Exception as e:
        logger.error(f"Ошибка во время частичной переиндексации: {e}")