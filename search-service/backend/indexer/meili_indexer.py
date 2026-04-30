import logging
from datetime import datetime

import meilisearch
from meilisearch.errors import MeilisearchError

from config import Settings
from indexer.cms_sync import CMSExtractor
from indexer.exceptions import DatabaseExtractionError

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class MeiliIndexer:
    def __init__(self, settings: Settings) -> None:
        self._extractor = CMSExtractor(settings)
        self._client = meilisearch.Client(
            settings.MEILI_URL,
            settings.MEILI_API_KEY or None,
        )
        self._index = self._client.index(settings.MEILI_INDEX)
        self._last_sync_ts: int = 0

    def is_empty(self) -> bool:
        try:
            stats = self._index.get_stats()
            return stats.number_of_documents == 0
        except MeilisearchError:
            return True

    def full_sync(self) -> None:
        logger.info("Starting full sync from CMS...")
        try:
            rows = self._extractor.extract_data()
        except DatabaseExtractionError as e:
            logger.error("Full sync failed during extraction: %s", e)
            return

        if not rows:
            logger.info("No documents to index.")
            return

        self._push(rows)
        logger.info("Full sync complete: %d documents indexed.", len(rows))

    def incremental_sync(self) -> None:
        logger.info("Starting incremental sync since ts=%d...", self._last_sync_ts)
        try:
            rows = self._extractor.extract_since(self._last_sync_ts)
        except DatabaseExtractionError as e:
            logger.error("Incremental sync failed during extraction: %s", e)
            return

        if not rows:
            logger.info("No new or updated documents.")
            return

        self._push(rows)
        logger.info("Incremental sync complete: %d documents indexed.", len(rows))

    def _push(self, rows: list[dict], batch_size: int = 5000) -> None:
        self._last_sync_ts = int(datetime.now().timestamp())
        last_task = None
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            try:
                last_task = self._index.add_documents(batch, primary_key="id")
                logger.info("Enqueued batch %d-%d (task %d).", i, i + len(batch), last_task.task_uid)
            except MeilisearchError as e:
                logger.error("Failed to enqueue batch %d-%d: %s", i, i + len(batch), e)
                raise

        if last_task:
            logger.info("Waiting for indexing and embedding generation to complete (task %d)...", last_task.task_uid)
            try:
                task_info = self._client.wait_for_task(last_task.task_uid, timeout_in_ms=14_400_000)
                logger.info(
                    "All indexing and embeddings complete. Last task duration: %s, status: %s.",
                    task_info.duration,
                    task_info.status,
                )
            except MeilisearchError as e:
                logger.warning("Timeout waiting for last indexing task: %s", e)
