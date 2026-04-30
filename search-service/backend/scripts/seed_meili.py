import logging
import sys
from pathlib import Path

import meilisearch

from config import Settings
from indexer.cms_sync import CMSExtractor
from indexer.exceptions import DatabaseExtractionError

sys.path.insert(0, str(Path(__file__).parent.parent))


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings()
    client = meilisearch.Client(settings.MEILI_URL, settings.MEILI_API_KEY or None)
    index = client.index(settings.MEILI_INDEX)

    extractor = CMSExtractor(settings)
    try:
        rows = extractor.extract_data()
    except DatabaseExtractionError as e:
        logger.error("Extraction failed: %s", e)
        sys.exit(1)

    if not rows:
        logger.info("No documents to index.")
        return

    batch_size = 5000
    last_task = None
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        last_task = index.add_documents(batch, primary_key="id")
        logger.info(
            "Enqueued batch %d–%d (task %d).", i, i + len(batch), last_task.task_uid
        )

    if last_task:
        client.wait_for_task(last_task.task_uid, timeout_in_ms=120_000)

    logger.info("Done. Stats: %s", index.get_stats())


if __name__ == "__main__":
    main()
