from __future__ import annotations

from abc import ABC, abstractmethod

from core.types import EngineConfig, SearchResult


class BaseSearchEngine(ABC):
    def __init__(self, config: EngineConfig) -> None:
        self.config = config

    @abstractmethod
    def healthcheck(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def index(self, dump_or_db_path: str | None = None) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(self, query: str, k: int) -> list[SearchResult]:
        raise NotImplementedError
