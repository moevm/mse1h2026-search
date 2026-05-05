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

def run_full_sync_task() -> bool:
    if not _sync_lock.acquire(blocking=False):
        logger.warning("Синхронизация уже выполняется, пропускаем запуск.")
        return False
    try:
        logger.info("Запуск ПОЛНОЙ переиндексации...")
        indexer = _get_indexer()
        if indexer:
            indexer.full_sync()
            logger.info("Полная переиндексация успешно завершена.")
        else:
            logger.warning("Провайдер не поддерживает переиндексацию.")
    except Exception as e:
        logger.error("Ошибка во время полной переиндексации: %s", e)
    finally:
        _sync_lock.release()
    return True

def run_incremental_sync_task() -> bool:
    if not _sync_lock.acquire(blocking=False):
        logger.warning("Синхронизация уже выполняется, пропускаем запуск.")
        return False
    try:
        logger.info("Запуск ЧАСТИЧНОЙ переиндексации...")
        indexer = _get_indexer()
        if indexer:
            indexer.incremental_sync()
            logger.info("Частичная переиндексация успешно завершена.")
    except Exception as e:
        logger.error("Ошибка во время частичной переиндексации: %s", e)
    finally:
        _sync_lock.release()
    return True