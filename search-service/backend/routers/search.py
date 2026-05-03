from fastapi import APIRouter, Depends, HTTPException, Query

from models.schemas import SearchResponse, SuggestResponse
from services.exceptions import InvalidParameterError
from services.providers.base import BaseSearchProvider
from services.search_service import get_provider

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    lang: list[str] | None = Query(None, description="Language filter"),
    sort_by: str = Query(
        "relevance", pattern="^(relevance|date)$", description="Sort criteria"
    ),
    date_filter: str | None = Query(
        None, pattern="^(month|year|3years)$", description="Date period filter"
    ),
    from_date: str | None = Query(None, description="Start date (DD-MM-YYYY)"),
    to_date: str | None = Query(None, description="End date (DD-MM-YYYY)"),
    provider: BaseSearchProvider = Depends(get_provider),
) -> SearchResponse:
    try:
        response = await provider.search(
            query=q,
            page=page,
            page_size=page_size,
            lang=lang,
            sort_by=sort_by,
            date_filter=date_filter,
            from_date=from_date,
            to_date=to_date,
        )
    except InvalidParameterError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return response


@router.get("/suggest", response_model=SuggestResponse)
async def suggest(
    q: str = Query(..., description="Suggest query"),
    provider: BaseSearchProvider = Depends(get_provider),
) -> SuggestResponse:
    suggestions = await provider.suggest(query=q)
    return SuggestResponse(suggestions=suggestions)
