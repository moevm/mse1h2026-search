from __future__ import annotations

import sys
from pathlib import Path

from core.engine_base import BaseSearchEngine
from core.types import SearchResult


class ManticoreEngine(BaseSearchEngine):
    def __init__(self, config):
        super().__init__(config)

        # Import local Manticore scripts (they use relative "config"/"queries" imports).
        root = Path(__file__).resolve().parents[1]  # benchmark/
        scripts_dir = root / "manticore" / "scripts"
        sys.path.insert(0, str(scripts_dir))
        try:
            # Both solr and manticore have their own local `config.py`.
            # `import config` would otherwise resolve to the first one cached in sys.modules.
            sys.modules.pop("config", None)
            import search_client  # type: ignore
        finally:
            # Keep modules in sys.modules, but avoid polluting sys.path for other adapters.
            sys.path.pop(0)

        self._search_client = search_client

    def healthcheck(self) -> None:
        if not self._search_client.check_connection():
            raise RuntimeError("Manticore is not reachable")

    def index(self, dump_or_db_path: str | None = None) -> None:
        # Optional: users can provide index_command in engines config.
        command = self.config.index_command
        if not command:
            return
        import subprocess

        subprocess.run(command, shell=True, check=True)

    def search(self, query: str, k: int) -> list[SearchResult]:
        ids = self._search_client.search(query, k)
        return [SearchResult(id=doc_id, url=None, raw={}) for doc_id in ids]
