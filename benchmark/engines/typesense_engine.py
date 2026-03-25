from __future__ import annotations

import subprocess
import time

from core.engine_base import BaseSearchEngine
from core.types import SearchResult

try:
    import typesense
except ImportError:  # pragma: no cover
    typesense = None


class TypesenseEngine(BaseSearchEngine):
    def __init__(self, config):
        super().__init__(config)
        if typesense is None:
            raise RuntimeError("typesense package is not installed")

        nodes = self.config.params.get(
            "nodes",
            [{"host": "localhost", "port": "8108", "protocol": "http"}],
        )
        api_key = self.config.params.get("api_key", "xyz")
        timeout = int(self.config.timeout_seconds)
        self.client = typesense.Client(
            {
                "nodes": nodes,
                "api_key": api_key,
                "connection_timeout_seconds": timeout,
            }
        )
        self.collection_name = self.config.params.get("collection_name", "site_content")
        self.query_by = self.config.params.get(
            "query_by", "pagetitle,longtitle,description,introtext,content"
        )
        self.extra_search_params = self.config.params.get("search_params", {})

    def healthcheck(self) -> None:
        self.client.collections[self.collection_name].retrieve()

    def index(self, dump_or_db_path: str | None = None) -> None:
        command = self.config.index_command
        if not command:
            return
        subprocess.run(command, shell=True, check=True)
        wait_seconds = float(self.config.params.get("post_index_wait_seconds", 0))
        if wait_seconds > 0:
            time.sleep(wait_seconds)

    def search(self, query: str, k: int) -> list[SearchResult]:
        params = {
            "q": query,
            "query_by": self.query_by,
            "per_page": k,
            **self.extra_search_params,
        }
        response = self.client.collections[self.collection_name].documents.search(params)
        hits = response.get("hits", [])
        results: list[SearchResult] = []
        for hit in hits:
            doc = hit.get("document", {})
            results.append(SearchResult(id=doc.get("id"), url=doc.get("url"), raw=doc))
        return results
