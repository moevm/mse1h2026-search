from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class QueryItem:
    query: str
    relevant_doc_keys: set[str]


@dataclass(slots=True)
class SearchResult:
    id: Any = None
    url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EngineConfig:
    name: str
    kind: str
    enabled: bool = True
    timeout_seconds: float = 5.0
    retries: int = 1
    index_command: str | None = None
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BenchmarkResult:
    engine: str
    k: int
    hitrate: float
    mrr: float
    duplicate_rate: float
    novelty: float
    evaluated_queries: int
    short_topk_responses: int
