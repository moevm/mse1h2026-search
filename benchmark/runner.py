from __future__ import annotations

import argparse
import importlib
import json
import time
from pathlib import Path

from core.dataset_loader import load_dataset
from core.metrics import aggregate_metrics
from core.normalization import to_doc_key
from core.types import EngineConfig


DEFAULT_KS = [1, 3, 5, 10]


def load_engine_configs(path: str) -> list[EngineConfig]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Engine config not found: {path}")

    if file_path.suffix in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Install pyyaml to use YAML config files") from exc
        with file_path.open("r", encoding="utf-8") as fp:
            payload = yaml.safe_load(fp) or {}
    else:
        with file_path.open("r", encoding="utf-8") as fp:
            payload = json.load(fp)

    raw_engines = payload.get("engines", [])
    configs: list[EngineConfig] = []
    for item in raw_engines:
        configs.append(
            EngineConfig(
                name=item["name"],
                kind=item["kind"],
                enabled=item.get("enabled", True),
                timeout_seconds=float(item.get("timeout_seconds", 5.0)),
                retries=int(item.get("retries", 1)),
                index_command=item.get("index_command"),
                params=item.get("params", {}),
            )
        )
    return configs


def make_engine(config: EngineConfig):
    module_name = f"engines.{config.kind}_engine"
    class_name = (
        "".join(part.capitalize() for part in config.kind.split("_")) + "Engine"
    )
    module = importlib.import_module(module_name)
    engine_cls = getattr(module, class_name)
    return engine_cls(config)


def evaluate_engine(engine, queries, ks: list[int]):
    ranked_per_query: list[list[str]] = []
    expected_per_query: list[set[str]] = []

    for query_item in queries:
        ranked_results = []
        last_error = None
        for attempt in range(max(1, engine.config.retries)):
            try:
                ranked_results = engine.search(query_item.query, max(ks))
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                if attempt + 1 < max(1, engine.config.retries):
                    time.sleep(0.2)
        if last_error is not None:
            raise last_error

        ranked_doc_keys = [
            to_doc_key(result.id, result.url) for result in ranked_results
        ]
        ranked_doc_keys = [x for x in ranked_doc_keys if x]

        ranked_per_query.append(ranked_doc_keys)
        expected_per_query.append(query_item.relevant_doc_keys)

    return aggregate_metrics(
        engine_name=engine.config.name,
        ks=ks,
        ranked_per_query=ranked_per_query,
        expected_per_query=expected_per_query,
    )


def print_metrics_wide(results, ks: list[int], title: str) -> None:
    by_k = {row.k: row for row in results}
    ordered = [by_k[k] for k in ks if k in by_k]
    if not ordered:
        return
    r0 = ordered[0]
    w = 8
    sep = "\t"

    def fmt_float4(getter) -> str:
        return sep.join(f"{getter(by_k[k]):{w}.4f}" for k in ks)

    def fmt_int4(getter) -> str:
        return sep.join(f"{getter(by_k[k]):{w}d}" for k in ks)

    k_header = sep.join(f"{k:>{w}}" for k in ks)

    print(f"\n## {title}")
    print(
        f"{'engine':<22}{sep}{'n_queries':>{w}}{sep}{'mrr':>{w}}{sep}"
        f"{'hitrate @k':<35}{sep}{'duplicate @k':<35}{sep}{'novelty @k':<35}{sep}{'underfilled @k':<35}"
    )
    print(
        f"{'':22}{sep}{'':>{w}}{sep}{'':>{w}}{sep}"
        f"{k_header}{sep}{k_header}{sep}{k_header}{sep}{k_header}"
    )
    print(
        f"{r0.engine:<22}{sep}{r0.evaluated_queries:>{w}d}{sep}{r0.mrr:>{w}.4f}{sep}"
        f"{fmt_float4(lambda r: r.hitrate)}{sep}"
        f"{fmt_float4(lambda r: r.duplicate_rate)}{sep}"
        f"{fmt_float4(lambda r: r.novelty)}{sep}"
        f"{fmt_int4(lambda r: r.short_topk_responses)}"
    )


def rows_to_k_arrays(rows, ks: list[int]) -> dict[str, object]:
    by_k = {row.k: row for row in rows}
    ordered = [by_k[k] for k in ks if k in by_k]
    return {
        "hitrate": [row.hitrate for row in ordered],
        "mrr": ordered[0].mrr if ordered else 0.0,
        "duplicate_rate": [row.duplicate_rate for row in ordered],
        "novelty": [row.novelty for row in ordered],
        "evaluated_queries": ordered[0].evaluated_queries if ordered else 0,
        "underfilled_topk": [row.short_topk_responses for row in ordered],
    }


def discover_datasets(data_dir: str) -> dict[str, dict[str, str]]:
    root = Path(data_dir)
    if not root.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    by_lang: dict[str, dict[str, str]] = {}
    for path in sorted(root.glob("*/*/*.json")):
        # expected shape: <data_dir>/<type>/<lang>/<file>.json
        if len(path.parts) < 3:
            continue
        request_type = path.parts[-3]
        lang = path.parts[-2]
        by_lang.setdefault(lang, {})[request_type] = str(path)
    return by_lang


def merge_query_sets(grouped_queries: list) -> list:
    merged: dict[str, set[str]] = {}
    for query_items in grouped_queries:
        for item in query_items:
            merged.setdefault(item.query, set()).update(item.relevant_doc_keys)
    from core.types import QueryItem

    return [
        QueryItem(query=query, relevant_doc_keys=doc_keys)
        for query, doc_keys in merged.items()
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Search engines benchmark runner")
    parser.add_argument("data_dir", help="Path to benchmark data directory")
    parser.add_argument(
        "--engines-config",
        default="benchmark/config/engines.example.yaml",
        help="Path to engines YAML/JSON config",
    )
    parser.add_argument(
        "--ks",
        default="1,3,5,10",
        help="Comma-separated k values (default: 1,3,5,10)",
    )
    parser.add_argument(
        "--report-json",
        default=None,
        help="Optional path to save aggregated report as JSON",
    )
    args = parser.parse_args()

    ks = [int(x) for x in args.ks.split(",") if x.strip()]
    if not ks:
        ks = DEFAULT_KS

    datasets = discover_datasets(args.data_dir)
    configs = load_engine_configs(args.engines_config)
    full_report: dict[str, object] = {"engines": {}}

    for config in configs:
        if not config.enabled:
            continue
        engine = make_engine(config)
        engine.healthcheck()
        engine.index(args.data_dir)

        per_lang_report: dict[str, object] = {}
        all_lang_queries = []

        for lang, datasets_by_type in sorted(datasets.items()):
            per_type_metrics: dict[str, object] = {}
            lang_queries_by_type = []

            for request_type, dataset_path in sorted(datasets_by_type.items()):
                queries = load_dataset(dataset_path)
                lang_queries_by_type.append(queries)
                metrics_rows = evaluate_engine(engine, queries, ks)
                per_type_metrics[request_type] = rows_to_k_arrays(metrics_rows, ks)
                print_metrics_wide(
                    metrics_rows, ks, f"{config.name} | {lang} | {request_type}"
                )

            lang_merged_queries = merge_query_sets(lang_queries_by_type)
            all_lang_queries.append(lang_merged_queries)
            lang_avg_rows = evaluate_engine(engine, lang_merged_queries, ks)
            per_lang_report[lang] = {
                "by_type": per_type_metrics,
                "language_average": rows_to_k_arrays(lang_avg_rows, ks),
            }
            print_metrics_wide(
                lang_avg_rows, ks, f"{config.name} | {lang} | language_average"
            )

        global_queries = merge_query_sets(all_lang_queries)
        global_avg_rows = evaluate_engine(engine, global_queries, ks)
        print_metrics_wide(global_avg_rows, ks, f"{config.name} | global_average")

        full_report["engines"][config.name] = {
            "by_language": per_lang_report,
            "global_average": rows_to_k_arrays(global_avg_rows, ks),
        }

    if args.report_json:
        path = Path(args.report_json)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fp:
            json.dump(full_report, fp, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
