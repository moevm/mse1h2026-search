import asyncio
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from click_log_db import ClickLogRepository, is_allowed_redirect_target
from config import Settings, get_settings

router = APIRouter(prefix="/api", tags=["click"])


def get_click_repository(
    settings: Settings = Depends(get_settings),
) -> ClickLogRepository:
    return ClickLogRepository(settings)


@router.get("/click")
async def click_redirect(
    target: str = Query(..., description="Original target URL"),
    query: str = Query(..., description="Search query text"),
    position: int = Query(..., ge=1, description="Position in result list"),
    repo: ClickLogRepository = Depends(get_click_repository),
) -> RedirectResponse:
    if not is_allowed_redirect_target(target):
        raise HTTPException(status_code=400, detail="Invalid redirect target URL")

    await asyncio.to_thread(repo.save_click, query, position, target)
    return RedirectResponse(url=target, status_code=307)


def wrap_results_with_click_links(request: Request, query: str, results: list) -> list:
    wrapped_results = []
    click_path = str(request.app.url_path_for("click_redirect"))
    for index, result in enumerate(results, start=1):
        params = urlencode(
            {
                "target": str(result.url),
                "query": query,
                "position": index,
            }
        )
        wrapped_url = f"{click_path}?{params}"
        wrapped_results.append(result.model_copy(update={"url": wrapped_url}))
    return wrapped_results
