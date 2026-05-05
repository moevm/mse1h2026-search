import logging
from datetime import datetime

import meilisearch
from meilisearch.errors import MeilisearchError

from config import Settings
from indexer.cms_sync import CMSExtractor
from indexer.exceptions import DatabaseExtractionError
from services.providers.meilisearch_provider import apply_index_settings

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
        self._url = settings.MEILI_URL
        self._api_key = settings.MEILI_API_KEY

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

    def rebuild_index(self) -> None:
        """Пересоздание индекса"""
        logger.info("Starting index rebuild...")
        try:
            rows = self._extractor.extract_data()
        except DatabaseExtractionError as e:
            logger.error("Rebuild failed during extraction: %s", e)
            return

        if not rows:
            logger.info("No documents to index during rebuild.")
            return

        temp_name = f"{self._index.uid}_temp"
        temp_index = self._client.index(temp_name)
        is_swap_pending = False

        try:
            logger.info("Applying settings to temporary index: %s", temp_name)
            apply_index_settings(self._url, self._api_key, temp_name)

            self._push(rows, target_index=temp_index)

            logger.info("Swapping indexes...")
            swap_task = self._client.swap_indexes([
                {"indexes": [self._index.uid, temp_name]}
            ])

            is_swap_pending = True
            self._client.wait_for_task(
                swap_task.task_uid, timeout_in_ms=14_400_000, interval_in_ms=1000)
            is_swap_pending = False

            logger.info(
                "Index rebuild complete: %d documents indexed.", len(rows))

        except Exception as e:
            logger.error("Failed during rebuild procedure: %s", e)
        finally:
            if not is_swap_pending:
                try:
                    temp_index.delete()
                    logger.info("Temporary index %s cleaned up.", temp_name)
                except MeilisearchError as e:
                    logger.warning(
                        "Failed to delete temp index %s: %s", temp_name, e)
            else:
                logger.warning(
                    "Swap task timed out or failed locally. Temp index %s left intact for Meilisearch to complete the swap in the background.", temp_name)

    def incremental_sync(self) -> None:
        logger.info("Starting incremental sync since ts=%d...", self._last_sync_ts)
        new_sync_ts = int(datetime.now().timestamp())
        try:
            rows = self._extractor.extract_since(self._last_sync_ts)
        except DatabaseExtractionError as e:
            logger.error("Incremental sync failed during extraction: %s", e)
            return

        if not rows:
            logger.info("No new or updated documents.")
            self._last_sync_ts = new_sync_ts
            return

        self._push(rows)
        self._last_sync_ts = new_sync_ts
        logger.info("Incremental sync complete: %d documents indexed.", len(rows))

    def _push(self, rows: list[dict], batch_size: int = 5000) -> None:
        last_task = None
        for i in range(0, len(rows), batch_size):
            batch = rows[i: i + batch_size]
            try:
                task = idx.add_documents(batch, primary_key="id")
                task_uids.append(task.task_uid)
                logger.info(
                    "Enqueued batch %d-%d (task %d).", i, i +
                    len(batch), task.task_uid
                )
            except MeilisearchError as e:
                logger.error("Failed to enqueue batch %d-%d: %s",
                             i, i + len(batch), e)
                raise

        if task_uids:
            logger.info(
                "Waiting for %d indexing tasks to complete...", len(task_uids))
            try:
                for uid in task_uids:
                    task_info = self._client.wait_for_task(
                        uid, timeout_in_ms=14_400_000, interval_in_ms=1000)

                    if task_info.status != "succeeded":
                        logger.error(
                            "Batch task %d failed inside Meilisearch. Status: %s",
                            uid, task_info.status
                        )
                        raise MeilisearchError(
                            f"Task {uid} failed with status: {task_info.status}"
                        )

                logger.info("All %d batches indexed successfully.",
                            len(task_uids))
                self._last_sync_ts = new_sync_ts

            except MeilisearchError as e:
                logger.error(
                    "Error or timeout waiting for indexing tasks: %s", e)
                raise
