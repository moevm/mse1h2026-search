from __future__ import annotations

import json
from pathlib import Path

from core.normalization import to_doc_key
from core.types import QueryItem


def load_dataset(dataset_path: str) -> list[QueryItem]:
    path = Path(dataset_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    with path.open("r", encoding="utf-8") as fp:
        payload = json.load(fp)

    items = payload.get("items", []) if isinstance(payload, dict) else payload
    grouped: dict[str, set[str]] = {}

    for item in items:
        doc_key = to_doc_key(item.get("id"), item.get("final_url") or item.get("url"))
        if not doc_key:
            continue
        for query in item.get("requests", []):
            q = str(query or "").strip()
            if not q:
                continue
            grouped.setdefault(q, set()).add(doc_key)

    return [QueryItem(query=q, relevant_doc_keys=keys) for q, keys in grouped.items()]
