import json
import sys

import typesense

from config import (
    METRICS_K_VALUES,
    SEARCH_PARAMS,
    TYPESENSE_COLLECTION,
    TYPESENSE_CONFIG,
)

from evaluate_search import aggregate, evaluate_items


def main():
    files = ["ru.json", "en.json", "de.json"]

    # Генерируем значения alpha от 0.0 до 1.0 с шагом 0.05
    alphas = [round(i * 0.05, 2) for i in range(21)]
    top_k = max(METRICS_K_VALUES)

    client = typesense.Client(TYPESENSE_CONFIG)

    try:
        client.collections[TYPESENSE_COLLECTION].retrieve()
    except typesense.exceptions.ObjectNotFound:
        print("Коллекция не найдена. Проверьте Typesense.")
        sys.exit(1)

    # Словарь для хранения всех результатов
    all_experiments = {}

    for file_name in files:
        print(f"\n{'=' * 60}")
        print(f"НАЧАЛО РАБОТЫ С ФАЙЛОМ: {file_name}")
        print(f"{'=' * 60}")

        try:
            with open(file_name, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"Файл {file_name} не найден. Пропускаем.")
            continue

        items = data.get("items", []) if isinstance(data, dict) else data
        file_results = []

        for alpha in alphas:
            print(f"\n--- Тестируем {file_name} с alpha = {alpha:.2f} ---")

            SEARCH_PARAMS["vector_query"] = f"embedding:([], alpha: {alpha:.2f})"

            results = evaluate_items(client, items, top_k)
            metrics = aggregate(results)

            file_results.append({"alpha": alpha, "metrics": metrics})

        all_experiments[file_name] = file_results

    # Вывод таблиц
    print("\n\n" + "#" * 60)
    print("ИТОГОВЫЕ РЕЗУЛЬТАТЫ ПО ВСЕМ ЯЗЫКАМ")
    print("#" * 60)

    for file_name, results in all_experiments.items():
        print(f"\n=== Результаты для {file_name} ===")

        header = f"| {'Alpha':<5} |"
        for k in METRICS_K_VALUES:
            header += f" {'Hit@' + str(k):<8} |"
        header += f" {'MRR':<6} | {'No Result':<9} |"

        sep = "-" * len(header)
        print(sep)
        print(header)
        print(sep)

        best_alpha = None
        best_mrr = -1.0

        for res in results:
            alpha = res["alpha"]
            m = res["metrics"]
            mrr = m.get("mrr", 0)

            if mrr > best_mrr:
                best_mrr = mrr
                best_alpha = alpha

            row = f"| {alpha:<5.2f} |"
            for k in METRICS_K_VALUES:
                hit_val = f"{m.get(f'hit_at_{k}', 0) * 100:.1f}%"
                row += f" {hit_val:<8} |"

            mrr_val = f"{mrr:.4f}"
            no_res_val = f"{m.get('no_result_rate', 0) * 100:.1f}%"

            row += f" {mrr_val:<6} | {no_res_val:<9} |"
            print(row)

        print(sep)
        print(
            f"ЛУЧШЕЕ ЗНАЧЕНИЕ ДЛЯ {file_name}: Alpha = {best_alpha:.2f} (MRR = {best_mrr:.4f})\n"
        )


if __name__ == "__main__":
    main()
