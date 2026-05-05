from abc import ABC, abstractmethod

from models.schemas import SearchResponse


class BaseSearchProvider(ABC):
    @abstractmethod
    async def search(
        self,
        query: str,
        page: int = 1,
        page_size: int = 10,
        lang: list[str] | None = None,
        sort_by: str = "relevance",
        date_filter: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> SearchResponse:
        pass

    @abstractmethod
    async def suggest(self, query: str) -> list[str]:
        pass
