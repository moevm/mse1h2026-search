from __future__ import annotations

import math
from collections import defaultdict

from core.types import BenchmarkResult


def hitrate_at_k(expected: set[str], ranked: list[str], k: int) -> float:
    topk = ranked[:k]
    return 1.0 if any(doc in expected for doc in topk) else 0.0


def mrr_at_k(expected: set[str], ranked: list[str], k: int) -> float:
    for index, doc_key in enumerate(ranked[:k], start=1):
        if doc_key in expected:
            return 1.0 / index
    return 0.0


def duplicate_rate_at_k(ranked: list[str], k: int) -> float:
    if k <= 0:
        return 0.0
    # Wiki: (k - |U_{q,k}|) / k, but for underfilled results we use the
    # фактический размер top-k (то есть len(R_{q,k}) вместо запрошенного k).
    topk = [x for x in ranked[:k] if x]
    n = len(topk)
    if n == 0:
        return 0.0
    unique_count = len(set(topk))
    return (n - unique_count) / n


def novelty_at_k(ranked_per_query: list[list[str]], k: int) -> float:
    # Wiki:
    # Novelty@k = (1 / (|Q| * k * log|Q|)) * sum_q sum_{d in R_{q,k}} -log P_k(d)
    # where P_k(d) = count_k(d) / |Q| and count_k(d) is the number of queries
    # whose top-k contains d (unique per query).
    q_count = len(ranked_per_query)
    if q_count == 0 or k <= 0:
        return 0.0
    if q_count == 1:
        # log(|Q|)=0 => formula undefined; return a neutral value.
        return 0.0

    counts: dict[str, int] = defaultdict(int)
    for ranked in ranked_per_query:
        for doc in set([x for x in ranked[:k] if x]):
            counts[doc] += 1

    log_q = math.log(q_count)
    if log_q == 0.0:
        return 0.0

    numerator = 0.0
    term_count = 0  # how many documents actually participate in the sum over R_{q,k}
    for ranked in ranked_per_query:
        for doc in ranked[:k]:
            if not doc:
                continue
            p = counts[doc] / q_count
            # p>0 by construction because doc comes from some ranked[:k]
            numerator += -math.log(p)
            term_count += 1

    if term_count == 0:
        return 0.0
    return numerator / (term_count * log_q)


def aggregate_metrics(
    engine_name: str,
    ks: list[int],
    ranked_per_query: list[list[str]],
    expected_per_query: list[set[str]],
) -> list[BenchmarkResult]:
    total_queries = len(ranked_per_query)
    results: list[BenchmarkResult] = []
    mrr_total = 0.0

    for ranked, expected in zip(ranked_per_query, expected_per_query):
        mrr_total += mrr_at_k(expected, ranked, len(ranked))
    mrr_value = mrr_total / (total_queries or 1)

    for k in ks:
        hitrate_sum = 0.0
        duplicate_sum = 0.0
        short_topk = 0

        for ranked, expected in zip(ranked_per_query, expected_per_query):
            if len(ranked) < k:
                short_topk += 1
            hitrate_sum += hitrate_at_k(expected, ranked, k)
            duplicate_sum += duplicate_rate_at_k(ranked, k)

        divisor = total_queries or 1
        results.append(
            BenchmarkResult(
                engine=engine_name,
                k=k,
                hitrate=hitrate_sum / divisor,
                mrr=mrr_value,
                duplicate_rate=duplicate_sum / divisor,
                novelty=novelty_at_k(ranked_per_query, k),
                evaluated_queries=total_queries,
                short_topk_responses=short_topk,
            )
        )

    return results
