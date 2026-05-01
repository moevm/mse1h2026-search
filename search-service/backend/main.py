import asyncio
import logging
from contextlib import asynccontextmanager, suppress

import uvicorn
from fastapi import FastAPI

from config import get_settings
from indexer.meili_indexer import MeiliIndexer
from routers import search
from services.providers.meilisearch_provider import apply_index_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_settings = get_settings()


async def _indexing_loop(indexer) -> None:
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

        indexer = MeiliIndexer(_settings)
        task = asyncio.create_task(_indexing_loop(indexer))

    yield

    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title="ETU Search Service",
    description="Prototype of search service for ETU",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(search.router)


@app.get("/api/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


def main():
    uvicorn.run("main:app", host=_settings.HOST, port=_settings.PORT)


if __name__ == "__main__":
    main()
