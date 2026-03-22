import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from routers import search

_settings = get_settings()

app = FastAPI(
    title="ETU Search Service",
    description="Prototype of search service for ETU",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(search.router)


@app.get("/api/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


def main():
    uvicorn.run(
        "main:app", host=_settings.HOST, port=_settings.PORT, reload=_settings.RELOAD
    )


if __name__ == "__main__":
    main()
