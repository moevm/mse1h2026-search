from __future__ import annotations

import subprocess
import time

from core.engine_base import BaseSearchEngine
from core.types import SearchResult

try:
    import meilisearch
except ImportError:  # pragma: no cover
    meilisearch = None


class MeilisearchEngine(BaseSearchEngine):
    def __init__(self, config):
        super().__init__(config)
        if meilisearch is None:
            raise RuntimeError("meilisearch package is not installed")

        host = self.config.params.get("host", "http://localhost:7700")
        api_key = self.config.params.get("api_key")
        self.client = meilisearch.Client(host, api_key)
        self.index_name = self.config.params.get("index_name", "site_content")
        self.index_ref = self.client.index(self.index_name)

    def healthcheck(self) -> None:
        self.client.health()

    def index(self, dump_or_db_path: str | None = None) -> None:
        command = self.config.index_command
        if not command:
            return
        subprocess.run(command, shell=True, check=True)
        wait_seconds = float(self.config.params.get("post_index_wait_seconds", 0))
        if wait_seconds > 0:
            time.sleep(wait_seconds)

    def search(self, query: str, k: int) -> list[SearchResult]:
        response = self.index_ref.search(query, {"limit": k})
        hits = response.get("hits", [])
        results: list[SearchResult] = []
        for hit in hits:
            results.append(SearchResult(id=hit.get("id"), url=hit.get("url"), raw=hit))
        return results
