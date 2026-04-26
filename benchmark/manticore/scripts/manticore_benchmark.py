import json
import time
import os
import sys
from dataclasses import dataclass, field

from tqdm import tqdm

from config import METRICS_K_VALUES, PATHS, logger, BAD_RESULTS_METRIC_K
from search_client import search, check_connection


@dataclass
class QueryResult:
    query:        str
    expected_id:  int
    expected_url: str
    found_ids:    list[int]
    latency_ms:   float = 0.0
    hit_at_k:     dict[int, bool] = field(default_factory=dict)
    rr:           float = 0.0
    no_result:    bool = False


def compute_rr(found_ids: list[int], expected_id: int) -> float:
    """Вычисляет Reciprocal Rank (RR) для одного запроса"""
    for pos, did in enumerate(found_ids, 1):
        if did == expected_id:
            return 1.0 / pos
    return 0.0


def evaluate_items(items: list[dict], top_k: int) -> list[QueryResult]:
    """Прогоняет все запросы из JSON через поисковик и собирает статистику"""
    results = []
    for item in tqdm(items, desc="Оценка Manticore", unit="док."):
        expected_id = int(item["id"])
        expected_url = item.get("url", "")

        for query_text in item.get("requests", []):
            start_time = time.perf_counter()
            found_ids = search(query_text, top_k)
            latency = (time.perf_counter() - start_time) * 1000
            no_result = len(found_ids) == 0
            rr = compute_rr(found_ids, expected_id)

            qr = QueryResult(
                query=query_text,
                expected_id=expected_id,
                expected_url=expected_url,
                found_ids=found_ids,
                latency_ms=latency,
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
    m["avg_latency"] = round(sum(r.latency_ms for r in results) / n, 2)
    return m


def save_no_result_log(results: list[QueryResult], filepath: str = PATHS['no_results_log']) -> bool:
    """Сохраняет запросы без результатов в отдельный лог-файл"""
    no_results = [r for r in results if r.no_result]
    if not no_results:
        return False

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"Запросы без результатов ({len(no_results)}):\n")
        f.write("=" * 60 + "\n")
        for r in no_results:
            f.write(f"Запрос: {r.query}\n")
            f.write(f"Ожидаемый URL: {r.expected_url}\n")
            f.write("-" * 60 + "\n")
    return True


def save_bad_results_log(results: list[QueryResult], filepath: str = PATHS['bad_results_log']) -> bool:
    """Сохраняет запросы, которые не попали в целевой Топ-K (BAD_RESULTS_METRIC_K)"""
    k_threshold = BAD_RESULTS_METRIC_K
    max_k = max(METRICS_K_VALUES)

    bad_results = []
    for r in results:
        if r.no_result:
            continue
        pos = int(1 / r.rr) if r.rr > 0 else float('inf')
        if pos > k_threshold:
            bad_results.append((r, pos))

    if not bad_results:
        return False

    bad_results.sort(key=lambda x: x[1], reverse=True)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(
            f"Запросы, не попавшие в Топ-{k_threshold} ({len(bad_results)}):\n")
        f.write("=" * 60 + "\n")
        for r, pos in bad_results:
            f.write(f"Запрос: {r.query}\n")
            f.write(f"Ожидаемый URL: {r.expected_url}\n")
            if pos == float('inf'):
                f.write(f"Результат: Не найдено в Топ-{max_k}\n")
            else:
                f.write(
                    f"Результат: Найдено на позиции {pos} (ожидалось в Топ-{k_threshold})\n")
            f.write("-" * 60 + "\n")
    return True


def print_metrics(overall: dict) -> None:
    ks = METRICS_K_VALUES
    k_s = "  ".join(f"Hit@{k}" for k in ks)
    hits = "  ".join(f"{overall.get(f'hit_at_{k}', 0):>6.1%}" for k in ks)
    output = (
        f"\n{'=' * 50}\nИТОГОВЫЕ МЕТРИКИ: MANTICORE SEARCH\n{'=' * 50}\n"
        f"  {k_s}   MRR\n  {hits}   {overall.get('mrr', 0):.4f}\n"
        f"  Запросов: {overall.get('total_queries', 0)}  |  "
        f"Без результатов: {overall.get('no_result_rate', 0):.1%}\n{'=' * 50}"
        f"\nСр. время 1 запроса{overall.get('avg_latency', 0):>7} ms\n"
    )
    print(output)


def load_items() -> list[dict]:
    """Загружает датасет из файла или стандартного ввода"""
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            data = json.load(f)
    elif not sys.stdin.isatty():
        data = json.load(sys.stdin)
    else:
        default_path = PATHS['dataset']
        logger.info(
            f"Путь к файлу не передан, используем по умолчанию: {default_path}")
        try:
            with open(default_path, encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            logger.error(
                f"Файл {default_path} не найден. Проверьте настройки или передайте путь аргументом.")
            sys.exit(1)

    return data.get("items", []) if isinstance(data, dict) else data


def save_logs(results: list[QueryResult]) -> None:
    """Отвечает за создание директорий и запись всех логов бенчмарка"""
    for path_key in ['no_results_log', 'bad_results_log']:
        log_dir = os.path.dirname(PATHS[path_key])
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

    if save_no_result_log(results):
        logger.info(
            f"Лог пустых запросов сохранен в: {PATHS['no_results_log']}")

    if save_bad_results_log(results):
        logger.info(
            f"Лог запросов с плохой позицией сохранен в: {PATHS['bad_results_log']}")


def main():
    items = load_items()
    top_k = max(METRICS_K_VALUES)

    if not check_connection():
        logger.error(
            "Manticore Search недоступен. Убедитесь, что контейнеры запущены (docker-compose up -d).")
        sys.exit(1)

    all_results = evaluate_items(items, top_k)
    overall = aggregate(all_results)

    save_logs(all_results)
    print_metrics(overall)


if __name__ == "__main__":
    main()
