import json
import sys
from dataclasses import dataclass, field

import typesense
from tqdm import tqdm

from config import (
    METRICS_K_VALUES,
    SEARCH_PARAMS,
    TYPESENSE_COLLECTION,
    TYPESENSE_CONFIG,
)
from lemmatizer import lemmatize_query


@dataclass
class QueryResult:
    query: str
    query_lemm: str
    expected_id: int
    expected_url: str
    found_ids: list[int]
    hit_at_k: dict[int, bool] = field(default_factory=dict)
    rr: float = 0.0
    no_result: bool = False


def compute_rr(found_ids: list[int], expected_id: int) -> float:
    for pos, did in enumerate(found_ids, 1):
        if did == expected_id:
            return 1.0 / pos
    return 0.0


def search(client: typesense.Client, query: str, top_k: int) -> tuple[list[int], str]:
    lemm = lemmatize_query(query)
    params = {**SEARCH_PARAMS, "q": lemm, "per_page": top_k}
    try:
        result = client.collections[TYPESENSE_COLLECTION].documents.search(params)
        ids = [int(h["document"]["id"]) for h in result.get("hits", [])]
        return ids, lemm
    except Exception:
        return [], lemm


def evaluate_items(
    client: typesense.Client,
    items: list[dict],
    top_k: int,
) -> list[QueryResult]:
    results = []
    for item in tqdm(items, desc="Оценка", unit="doc"):
        expected_id = item["id"]
        expected_url = item.get("url", "")
        for query_text in item.get("requests", []):
            found, query_lemm = search(client, query_text, top_k)
            no_result = len(found) == 0
            rr = compute_rr(found, expected_id)

            qr = QueryResult(
                query=query_text,
                query_lemm=query_lemm,
                expected_id=expected_id,
                expected_url=expected_url,
                found_ids=found,
                no_result=no_result,
                rr=rr,
            )
            for k in METRICS_K_VALUES:
                if k <= top_k:
                    qr.hit_at_k[k] = expected_id in found[:k]

            results.append(qr)
    return results


def aggregate(results: list[QueryResult]) -> dict:
    n = len(results)
    if n == 0:
        return {}

    m = {"total_queries": n}
    for k in METRICS_K_VALUES:
        m[f"hit_at_{k}"] = round(sum(r.hit_at_k.get(k, False) for r in results) / n, 4)
    m["mrr"] = round(sum(r.rr for r in results) / n, 4)
    m["no_result_rate"] = round(sum(1 for r in results if r.no_result) / n, 4)
    return m


def print_metrics(overall: dict) -> None:
    ks = METRICS_K_VALUES
    k_s = "  ".join(f"Hit@{k}" for k in ks)
    print("\n" + "=" * 50)
    print("ИТОГОВЫЕ МЕТРИКИ")
    print("=" * 50)
    hits = "  ".join(f"{overall.get(f'hit_at_{k}', 0):>6.1%}" for k in ks)
    print(f"  {k_s}   MRR")
    print(f"  {hits}   {overall.get('mrr', 0):.4f}")
    print(
        f"  Запросов: {overall.get('total_queries', 0)}  |  Без результатов: {overall.get('no_result_rate', 0):.1%}"
    )
    print("=" * 50)


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            data = json.load(f)
    elif not sys.stdin.isatty():
        data = json.load(sys.stdin)
    else:
        print("Использование: python evaluate_search.py queries.json")
        return

    top_k = max(METRICS_K_VALUES)
    items = data.get("items", []) if isinstance(data, dict) else data

    client = typesense.Client(TYPESENSE_CONFIG)
    try:
        client.collections[TYPESENSE_COLLECTION].retrieve()
    except typesense.exceptions.ObjectNotFound:
        print("Коллекция не найдена. Сначала запустите setup_typesense.py")
        sys.exit(1)

    all_results = evaluate_items(client, items, top_k)
    overall = aggregate(all_results)
    print_metrics(overall)


if __name__ == "__main__":
    main()
