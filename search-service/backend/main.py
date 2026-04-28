import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import get_settings
from routers import search, indexer
from services.indexing_service import run_sync_task

logging.basicConfig(level=logging.INFO)

_settings = get_settings()

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):

    scheduler.add_job(
        run_sync_task,
        CronTrigger.from_crontab("0 3 * * *"),
        id="daily_cms_sync",
        replace_existing=True
    )
    scheduler.start()
    logging.info("Планировщик задач запущен.")

    yield

    scheduler.shutdown()

app = FastAPI(
    title="ETU Search Service",
    description="Prototype of search service for ETU",
    version="0.1.0",
    lifespan=lifespan
)

app.include_router(search.router)
app.include_router(indexer.router)


@app.get("/api/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


def main():
    uvicorn.run(
        "main:app", host=_settings.HOST, port=_settings.PORT
    )


if __name__ == "__main__":
    main()