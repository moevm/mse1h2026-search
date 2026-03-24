import json
import os
import pysolr
from config import SOLR_URL, DATA_PATH, SEARCH_PARAMS

# Добавим Hit@3, так как он есть в твоем примере
K_VALUES = [1, 3, 5, 10]


def calculate_metrics(results):
    if not results:
        return None
    total = len(results)
    no_results = sum(1 for r in results if r["rank"] == 0)

    metrics = {
        "total": total,
        "no_results_rate": no_results / total,
        "mrr": sum((1 / r["rank"] if r["rank"] > 0 else 0) for r in results) / total
    }
    for k in K_VALUES:
        metrics[f"hit@{k}"] = sum(1 for r in results if 0 < r["rank"] <= k) / total
    return metrics


def print_markdown_table(title, rows):
    print(f"\n### {title}\n")
    header = "| " + " | ".join(rows[0].keys()) + " |"
    separator = "| " + " | ".join([":---:"] * len(rows[0])) + " |"
    print(header)
    print(separator)
    for row in rows:
        formatted_row = "| " + " | ".join([f"{v:.2%}" if isinstance(v, float) and "rate" in k or "hit" in k else (
            f"{v:.4f}" if isinstance(v, float) else str(v)) for k, v in row.items()]) + " |"
        print(formatted_row)


def run_evaluation():
    solr = pysolr.Solr(SOLR_URL)
    lang_stats = {}
    overall_results = []

    # Обход папок
    for root, _, files in os.walk(DATA_PATH):
        for file in files:
            if file.endswith(".json"):
                # Определяем язык по пути (например, ../data/information/ru -> ru)
                parts = root.replace("\\", "/").split("/")
                lang = parts[-1] if len(parts[-1]) == 2 else "unknown"

                if lang not in lang_stats:
                    lang_stats[lang] = []

                with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    items = data.get("items", [])
                    for item in items:
                        expected_id = str(item["id"])
                        for query in item.get("requests", []):
                            results = solr.search(query, **SEARCH_PARAMS)
                            found_ids = [str(d["id"]) for d in results]
                            rank = found_ids.index(expected_id) + 1 if expected_id in found_ids else 0

                            res_obj = {"rank": rank}
                            lang_stats[lang].append(res_obj)
                            overall_results.append(res_obj)

    # 1. Общая таблица (Метод поиска)
    overall_metrics = calculate_metrics(overall_results)
    if overall_metrics:
        method_row = {
            "Метод поиска": "Solr (eDisMax)",
            "Hit@1": overall_metrics["hit@1"],
            "Hit@3": overall_metrics["hit@3"],
            "Hit@5": overall_metrics["hit@5"],
            "Hit@10": overall_metrics["hit@10"],
            "MRR": overall_metrics["mrr"],
            "Запросов": overall_metrics["total"],
            "Без результатов": overall_metrics["no_results_rate"]
        }
        print_markdown_table("Результаты оценки", [method_row])

    # 2. Таблица по языкам
    lang_rows = []
    # Сортируем языки для красоты (ru, en, de...)
    for lang in sorted(lang_stats.keys()):
        m = calculate_metrics(lang_stats[lang])
        if m:
            lang_rows.append({
                "Язык": lang.upper(),
                "Hit@1": m["hit@1"],
                "Hit@3": m["hit@3"],
                "Hit@5": m["hit@5"],
                "Hit@10": m["hit@10"],
                "MRR": m["mrr"]
            })

    if lang_rows:
        print_markdown_table("Результаты оценки по языкам", lang_rows)


if __name__ == "__main__":
    run_evaluation()