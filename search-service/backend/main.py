import asyncio
import logging
from contextlib import asynccontextmanager, suppress

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI

from config import get_settings
from indexer.meili_indexer import MeiliIndexer
from routers import indexer, search
from services.indexing_service import run_sync_task
from services.providers.meilisearch_provider import apply_index_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_settings = get_settings()
scheduler = AsyncIOScheduler()


async def _indexing_loop(indexer: MeiliIndexer) -> None:
    try:
        if await asyncio.to_thread(indexer.is_empty):
            logger.info("Index is empty, running full sync...")
            await asyncio.to_thread(indexer.full_sync)
        else:
            logger.info("Index already has documents, skipping full sync.")

        while True:
            await asyncio.sleep(3600)
            await asyncio.to_thread(indexer.incremental_sync)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Indexing loop crashed:")


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(
        run_sync_task,
        CronTrigger.from_crontab("0 3 * * *"),
        id="daily_cms_sync",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Task scheduler started.")

    task = None
    if _settings.SEARCH_PROVIDER == "meilisearch":
        logger.info("Applying Meilisearch index settings...")
        await asyncio.to_thread(
            apply_index_settings,
            _settings.MEILI_URL,
            _settings.MEILI_API_KEY,
            _settings.MEILI_INDEX,
        )
        logger.info("Meilisearch index settings applied.")

        indexer_instance = MeiliIndexer(_settings)
        task = asyncio.create_task(_indexing_loop(indexer_instance))

    yield

    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    scheduler.shutdown()


app = FastAPI(
    title="ETU Search Service",
    description="Prototype of search service for ETU",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(search.router)
app.include_router(indexer.router)


@app.get("/api/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


def main():
    uvicorn.run("main:app", host=_settings.HOST, port=_settings.PORT)


if __name__ == "__main__":
    main()
