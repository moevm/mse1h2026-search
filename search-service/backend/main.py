import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI

from config import get_settings
from indexer.meili_indexer import MeiliIndexer
from routers import indexer, search
from services.indexing_service import run_full_sync_task, run_incremental_sync_task
from services.providers.meilisearch_provider import apply_index_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_settings = get_settings()
scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(
        run_incremental_sync_task,
        CronTrigger.from_crontab("0 * * * *"),
        id="hourly_incremental_sync",
        replace_existing=True,
    )

    scheduler.add_job(
        run_full_sync_task,
        CronTrigger.from_crontab("0 3 * * 0"),
        id="weekly_full_sync",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Task scheduler started.")

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
        if await asyncio.to_thread(indexer_instance.is_empty):
            logger.info("Index is empty, scheduling initial full sync...")
            scheduler.add_job(run_full_sync_task, id="initial_startup_sync")

    yield

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