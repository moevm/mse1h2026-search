#!/usr/bin/env python3
import json
import os
import sys
import argparse
from dataclasses import dataclass, field
from tqdm import tqdm
import meilisearch
from dotenv import load_dotenv

load_dotenv()

MEILI_URL = os.getenv('MEILI_URL', 'http://localhost:7700')
MEILI_MASTER_KEY = os.getenv('MEILI_MASTER_KEY', '')
DEFAULT_INDEX_NAME = 'site_content'

METRICS_K_VALUES = [1, 5, 10]
BAD_RESULTS_METRIC_K = 1
PATHS = {
    'no_results_log': 'logs/meilisearch_no_results.txt',
    'bad_results_log': 'logs/meilisearch_bad_results.txt'
}

LANG_TO_LOCALE = {
    'ru': 'rus',
    'en': 'eng',
    'de': 'deu',
    'sp': 'spa',
    'pt': 'por',
    'fr': 'fra',
    'vn': 'vie',
    'ar': 'ara',
    'cn': 'zho'
}

client = meilisearch.Client(MEILI_URL, MEILI_MASTER_KEY)
index = None

@dataclass
class QueryResult:
    query:        str
    expected_id:  int
    expected_url: str
    found_ids:    list[int]
    hit_at_k:     dict[int, bool] = field(default_factory=dict)
    rr:           float = 0.0
    no_result:    bool = False

def search_meili(query: str, limit: int, use_multi: bool = False, lang: str = None) -> list[int]:
    """Выполняет поиск в Meilisearch и возвращает список ID найденных документов"""
    try:
        if use_multi:
            indexes_res = client.get_indexes()
            if isinstance(indexes_res, list):
                all_uids = [idx.uid for idx in indexes_res]
            elif isinstance(indexes_res, dict) and 'results' in indexes_res:
                all_uids = [idx.uid for idx in indexes_res['results']]
            else:
                all_uids = [idx.uid for idx in indexes_res.results]
            
            target_uids = [uid for uid in all_uids if uid.startswith('site_') and uid != 'site_content']
            
            if not target_uids:
                return []
                
            queries = []
            for uid in target_uids:
                l_code = uid.replace('site_', '')
                locales = [LANG_TO_LOCALE.get(l_code)] if l_code in LANG_TO_LOCALE else None
                
                queries.append({
                    'indexUid': uid, 
                    'q': query,
                    'locales': locales
                })
                
            result = client.multi_search(queries, federation={'limit': limit})
            
            ids = []
            for hit in result.get('hits', []):
                try:
                    ids.append(int(hit['id']))
                except (ValueError, KeyError, TypeError):
                    continue
            return ids
        else:
            locales = [LANG_TO_LOCALE.get(lang)] if lang in LANG_TO_LOCALE else None
            results = index.search(query, {
                'limit': limit,
                'locales': locales
            })
            ids = []
            for hit in results.get('hits', []):
                try:
                    ids.append(int(hit['id']))
                except (ValueError, KeyError, TypeError):
                    continue
            return ids
    except Exception:
        return []

def compute_rr(found_ids: list[int], expected_id: int) -> float:
    """Вычисляет Reciprocal Rank (RR) для одного запроса"""
    for pos, did in enumerate(found_ids, 1):
        if did == expected_id:
            return 1.0 / pos
    return 0.0

def evaluate_items(items: list[dict], top_k: int, use_multi: bool = False, lang: str = None) -> list[QueryResult]:
    """Прогоняет все запросы через Meilisearch и собирает статистику"""
    results = []
    for item in tqdm(items, desc="Оценка Meilisearch", unit="док."):
        expected_id = int(item["id"])
        expected_url = item.get("url", "")

        for query_text in item.get("requests", []):
            found_ids = search_meili(query_text, top_k, use_multi, lang)
            no_result = len(found_ids) == 0
            rr = compute_rr(found_ids, expected_id)

            qr = QueryResult(
                query=query_text,
                expected_id=expected_id,
                expected_url=expected_url,
                found_ids=found_ids,
                no_result=no_result,
                rr=rr,
            )
            for k in METRICS_K_VALUES:
                if k <= top_k:
                    qr.hit_at_k[k] = expected_id in found_ids[:k]

            results.append(qr)
    return results

def aggregate(results: list[QueryResult]) -> dict:
    """Агрегирует результаты в итоговые метрики (Hit@K, MRR)"""
    n = len(results)
    if n == 0:
        return {}

    m = {"total_queries": n}
    for k in METRICS_K_VALUES:
        m[f"hit_at_{k}"] = round(
            sum(r.hit_at_k.get(k, False) for r in results) / n, 4
        )
    m["mrr"] = round(sum(r.rr for r in results) / n, 4)
    m["no_result_rate"] = round(sum(1 for r in results if r.no_result) / n, 4)
    return m

def save_logs(results: list[QueryResult]):
    """Сохраняет логи ошибок и плохих результатов"""
    for path in PATHS.values():
        os.makedirs(os.path.dirname(path), exist_ok=True)

    no_results = [r for r in results if r.no_result]
    with open(PATHS['no_results_log'], "w", encoding="utf-8") as f:
        f.write(f"Запросы без результатов Meilisearch ({len(no_results)}):\n")
        f.write("=" * 60 + "\n")
        for r in no_results:
            f.write(f"Запрос: {r.query}\nОжидаемый URL: {r.expected_url}\n" + "-"*60 + "\n")

    bad_results = []
    for r in results:
        if r.no_result: continue
        pos = int(1 / r.rr) if r.rr > 0 else float('inf')
        if pos > BAD_RESULTS_METRIC_K:
            bad_results.append((r, pos))
    
    bad_results.sort(key=lambda x: x[1], reverse=True)
    with open(PATHS['bad_results_log'], "w", encoding="utf-8") as f:
        f.write(f"Запросы с плохой позицией в Meilisearch ({len(bad_results)}):\n")
        f.write("=" * 60 + "\n")
        for r, pos in bad_results:
            f.write(f"Запрос: {r.query}\nОжидаемый URL: {r.expected_url}\n")
            f.write(f"Результат: Позиция {pos} (ожидался ТОП-{BAD_RESULTS_METRIC_K})\n" + "-"*60 + "\n")

def print_metrics(overall: dict, index_name: str):
    ks = METRICS_K_VALUES
    k_s = "  ".join(f"Hit@{k}" for k in ks)
    hits = "  ".join(f"{overall.get(f'hit_at_{k}', 0):>6.1%}" for k in ks)
    output = (
        f"\n{'=' * 50}\nИТОГОВЫЕ МЕТРИКИ: MEILISEARCH (Индекс: {index_name})\n{'=' * 50}\n"
        f"  {k_s}   MRR\n  {hits}   {overall.get('mrr', 0):.4f}\n"
        f"  Запросов: {overall.get('total_queries', 0)}  |  "
        f"Без результатов: {overall.get('no_result_rate', 0):.1%}\n{'=' * 50}"
    )
    print(output)

def main():
    parser = argparse.ArgumentParser(description='Meilisearch Benchmark')
    parser.add_argument('dataset', help='Путь к JSON файлу с датасетом')
    parser.add_argument('--lang', help='Язык для индекса (например, ru, en). Если не указан, используется site_content.')
    parser.add_argument('--multi', action='store_true', help='Использовать федеративный поиск по всем языковым индексам.')
    args = parser.parse_args()

    global index
    index_name = "multi-index (federated)" if args.multi else (f'site_{args.lang}' if args.lang else DEFAULT_INDEX_NAME)
    
    if not args.multi:
        index = client.index(index_name)

    print(f"Используется режим: {index_name}")

    if not os.path.exists(args.dataset):
        print(f"Файл не найден: {args.dataset}")
        sys.exit(1)

    with open(args.dataset, encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("items", []) if isinstance(data, dict) else data

    top_k = max(METRICS_K_VALUES)
    
    try:
        client.health()
    except Exception:
        print("Meilisearch недоступен. Проверьте MEILI_URL в .env")
        sys.exit(1)

    all_results = evaluate_items(items, top_k, use_multi=args.multi, lang=args.lang)
    overall = aggregate(all_results)
    
    save_logs(all_results)
    print_metrics(overall, index_name)

if __name__ == "__main__":
    main()
