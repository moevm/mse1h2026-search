import logging
import threading

from config import get_settings
from indexer.meili_indexer import MeiliIndexer

logger = logging.getLogger(__name__)

_indexer: MeiliIndexer | None = None
_sync_lock = threading.Lock()

def _get_indexer() -> MeiliIndexer | None:
    global _indexer
    settings = get_settings()
    if settings.SEARCH_PROVIDER != "meilisearch":
        return None
    if _indexer is None:
        _indexer = MeiliIndexer(settings)
    return _indexer

def run_full_sync_task() -> None:
    if _sync_lock.locked():
        logger.warning("Синхронизация уже выполняется, пропускаем запуск.")
        return
    with _sync_lock:
        logger.info("Запуск ПОЛНОЙ переиндексации...")
        try:
            indexer = _get_indexer()
            if indexer:
                indexer.full_sync()
                logger.info("Полная переиндексация успешно завершена.")
            else:
                logger.warning("Провайдер не поддерживает переиндексацию.")
        except Exception as e:
            logger.error("Ошибка во время полной переиндексации: %s", e)

def run_incremental_sync_task() -> None:
    if _sync_lock.locked():
        logger.warning("Синхронизация уже выполняется, пропускаем запуск.")
        return
    with _sync_lock:
        logger.info("Запуск ЧАСТИЧНОЙ переиндексации...")
        try:
            indexer = _get_indexer()
            if indexer:
                indexer.incremental_sync()
                logger.info("Частичная переиндексация успешно завершена.")
        except Exception as e:
            logger.error("Ошибка во время частичной переиндексации: %s", e)