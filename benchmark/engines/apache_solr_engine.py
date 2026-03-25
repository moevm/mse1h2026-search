from __future__ import annotations

import copy
import sys
from pathlib import Path

from core.engine_base import BaseSearchEngine
from core.types import SearchResult


class ApacheSolrEngine(BaseSearchEngine):
    def __init__(self, config):
        super().__init__(config)

        # Import local Solr config.
        root = Path(__file__).resolve().parents[1]  # benchmark/
        solr_dir = root / "apache_solr"
        sys.path.insert(0, str(solr_dir))
        try:
            import config as solr_config  # type: ignore
        finally:
            sys.path.pop(0)

        self._solr_config = solr_config

        import pysolr  # local dependency from apache_solr/requirements.txt

        self._solr = pysolr.Solr(solr_config.SOLR_URL)
        # Base query params; runner will override rows.
        self._base_params = copy.deepcopy(solr_config.SEARCH_PARAMS)

    def healthcheck(self) -> None:
        # A lightweight ping: request core metadata.
        # If Solr is down/unindexed, this will fail.
        self._solr.ping()

    def index(self, dump_or_db_path: str | None = None) -> None:
        command = self.config.index_command
        if not command:
            return
        import subprocess

        subprocess.run(command, shell=True, check=True)

    def search(self, query: str, k: int) -> list[SearchResult]:
        params = dict(self._base_params)
        params["rows"] = k
        results = self._solr.search(query, **params)

        ranked: list[SearchResult] = []
        for doc in results:
            doc_id = doc.get("id") if hasattr(doc, "get") else getattr(doc, "id", None)
            ranked.append(SearchResult(id=doc_id, url=None, raw=dict(doc)))
        return ranked

