"""
Timing harness — runs a query N times against a connected driver, discards
a warmup period, and computes p50/p95 latency percentiles.
"""

import json
import random
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATS_PATH = REPO_ROOT / "data" / "dataset_stats.json"

with open(STATS_PATH) as f:
    _stats = json.load(f)

NODE_COUNT = _stats["node_count"]
BUCKET_RANGE = 100


def random_start_id():
    return random.randint(0, NODE_COUNT - 1)


def random_lookup_id():
    return random.randint(0, NODE_COUNT - 1)


def random_bucket():
    return random.randint(0, BUCKET_RANGE - 1)


PARAM_GENERATORS = {
    "traversal_1hop": lambda: {"start_id": random_start_id()},
    "traversal_2hop": lambda: {"start_id": random_start_id()},
    "traversal_3hop": lambda: {"start_id": random_start_id()},
    "point_lookup": lambda: {"lookup_id": random_lookup_id()},
    "indexed_filtered_lookup": lambda: {"bucket_value": random_bucket()},
    "aggregation_relationship_count": lambda: {},
    "aggregation_degree_distribution": lambda: {},
}


def compute_percentiles(latencies_ms: list) -> dict:
    if not latencies_ms:
        raise ValueError("Cannot compute percentiles on empty latency list")

    sorted_lat = sorted(latencies_ms)
    n = len(sorted_lat)

    def percentile(p):
        if n == 1:
            return sorted_lat[0]
        rank = (p / 100) * (n - 1)
        lower = int(rank)
        upper = min(lower + 1, n - 1)
        frac = rank - lower
        return sorted_lat[lower] + (sorted_lat[upper] - sorted_lat[lower]) * frac

    return {
        "p50_ms": round(percentile(50), 3),
        "p95_ms": round(percentile(95), 3),
        "min_ms": round(sorted_lat[0], 3),
        "max_ms": round(sorted_lat[-1], 3),
        "mean_ms": round(sum(sorted_lat) / n, 3),
        "n_samples": n,
    }


def run_workload(driver, query_name: str, cypher: str, aql: str,
                  iterations: int = 100, warmup: int = 10) -> dict:
    param_gen = PARAM_GENERATORS[query_name]
    latencies_ms = []
    errors = 0

    total_calls = warmup + iterations
    for i in range(total_calls):
        params = param_gen()
        start = time.perf_counter()
        try:
            driver.run_read_query(cypher, aql, params)
            elapsed_ms = (time.perf_counter() - start) * 1000
            if i >= warmup:
                latencies_ms.append(elapsed_ms)
        except Exception as e:
            errors += 1
            if i >= warmup:
                pass

    if not latencies_ms:
        return {
            "query": query_name,
            "error": f"All {total_calls} calls failed — no successful timed samples",
            "errors": errors,
        }

    result = compute_percentiles(latencies_ms)
    result["query"] = query_name
    result["warmup_calls"] = warmup
    result["timed_calls"] = iterations
    result["errors_during_timed_phase"] = errors
    return result


if __name__ == "__main__":
    test_latencies = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    result = compute_percentiles(test_latencies)
    print("Percentile sanity check (input: 10..100 step 10):")
    print(json.dumps(result, indent=2))
    assert result["p50_ms"] == 55.0, f"Expected p50=55.0, got {result['p50_ms']}"
    assert result["min_ms"] == 10.0
    assert result["max_ms"] == 100.0
    print("\nPercentile math verified correct.")

    print(f"\nDataset node count loaded: {NODE_COUNT}")
    print(f"Param generators defined for: {list(PARAM_GENERATORS.keys())}")
