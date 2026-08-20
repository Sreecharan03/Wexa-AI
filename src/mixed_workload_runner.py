"""
Mixed read/write workload runner.
"""

import argparse
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from src.config import PLATFORMS
from src.driver_factory import get_driver
from src.queries import QUERIES
from src.harness import NODE_COUNT

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "results"
STATS_PATH = REPO_ROOT / "data" / "dataset_stats.json"

DEFAULT_DURATION_SECONDS = 15
DEFAULT_CONCURRENCY = 10
DEFAULT_READ_RATIO = 0.8


def _client_worker(worker_id: int, platform_key: str, deadline: float, read_ratio: float) -> dict:
    driver = get_driver(platform_key)
    point_lookup = QUERIES["point_lookup"]

    reads_ok = 0
    reads_failed = 0
    writes_ok = 0
    writes_failed = 0
    local_write_counter = 0

    while time.perf_counter() < deadline:
        if random.random() < read_ratio:
            try:
                driver.run_read_query(
                    point_lookup["cypher"],
                    point_lookup["aql"],
                    {"lookup_id": random.randint(0, NODE_COUNT - 1)},
                )
                reads_ok += 1
            except Exception:
                reads_failed += 1
        else:
            try:
                scratch_id = worker_id * 10_000_000 + local_write_counter
                driver.write_scratch_node(scratch_id)
                local_write_counter += 1
                writes_ok += 1
            except Exception:
                writes_failed += 1

    driver.close()
    return {
        "worker_id": worker_id,
        "reads_ok": reads_ok,
        "reads_failed": reads_failed,
        "writes_ok": writes_ok,
        "writes_failed": writes_failed,
    }


def run_mixed_workload(platform_key: str, duration: int, concurrency: int, read_ratio: float) -> dict:
    spec = PLATFORMS[platform_key]
    print(f"\n{'='*60}")
    print(f"Mixed workload: {spec.display_name}")
    print(f"  {concurrency} concurrent clients | {duration}s duration | "
          f"{read_ratio*100:.0f}% reads / {(1-read_ratio)*100:.0f}% writes")
    print(f"{'='*60}")

    setup_driver = get_driver(platform_key)
    setup_driver.cleanup_scratch()
    setup_driver.close()

    actual_start = time.perf_counter()
    deadline = actual_start + duration

    worker_results = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(_client_worker, i, platform_key, deadline, read_ratio)
            for i in range(concurrency)
        ]
        for future in as_completed(futures):
            worker_results.append(future.result())

    actual_elapsed = time.perf_counter() - actual_start

    total_reads_ok = sum(w["reads_ok"] for w in worker_results)
    total_reads_failed = sum(w["reads_failed"] for w in worker_results)
    total_writes_ok = sum(w["writes_ok"] for w in worker_results)
    total_writes_failed = sum(w["writes_failed"] for w in worker_results)
    total_ops = total_reads_ok + total_writes_ok

    print(f"  Reads:  {total_reads_ok} ok, {total_reads_failed} failed")
    print(f"  Writes: {total_writes_ok} ok, {total_writes_failed} failed")
    print(f"  Throughput: {total_ops / actual_elapsed:.1f} ops/sec over {actual_elapsed:.2f}s")

    print("  Cleaning up scratch data...")
    cleanup_driver = get_driver(platform_key)
    cleanup_driver.cleanup_scratch()

    with open(STATS_PATH) as f:
        expected = json.load(f)

    integrity_check = {"verified": False, "note": "verification query not implemented for this check"}
    try:
        node_result = cleanup_driver.run_read_query(
            "MATCH (a:Author) RETURN count(a) AS c",
            "RETURN LENGTH(authors)",
            {},
        )
        edge_result = cleanup_driver.run_read_query(
            "MATCH ()-[r:COLLABORATES]->() RETURN count(r) AS c",
            "RETURN LENGTH(collaborates)",
            {},
        )
        def extract_scalar(row):
            if isinstance(row, dict):
                return list(row.values())[0]
            return row

        actual_nodes = extract_scalar(node_result[0]) if node_result else None
        actual_edges = extract_scalar(edge_result[0]) if edge_result else None
        integrity_check = {
            "verified": True,
            "expected_nodes": expected["node_count"],
            "actual_nodes": actual_nodes,
            "expected_edges": expected["relationship_count"],
            "actual_edges": actual_edges,
            "dataset_intact": (actual_nodes == expected["node_count"] and actual_edges == expected["relationship_count"]),
        }
        print(f"  Integrity check: dataset_intact={integrity_check['dataset_intact']}")
    except Exception as e:
        integrity_check = {"verified": False, "error": str(e)}
        print(f"  Integrity check FAILED to run: {e}")

    cleanup_driver.close()

    return {
        "platform": platform_key,
        "platform_display_name": spec.display_name,
        "concurrency": concurrency,
        "requested_duration_seconds": duration,
        "actual_duration_seconds": round(actual_elapsed, 3),
        "read_ratio": read_ratio,
        "reads_ok": total_reads_ok,
        "reads_failed": total_reads_failed,
        "writes_ok": total_writes_ok,
        "writes_failed": total_writes_failed,
        "total_successful_ops": total_ops,
        "ops_per_second": round(total_ops / actual_elapsed, 2),
        "reads_per_second": round(total_reads_ok / actual_elapsed, 2),
        "writes_per_second": round(total_writes_ok / actual_elapsed, 2),
        "post_run_integrity_check": integrity_check,
        "per_worker_breakdown": worker_results,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", type=str, help="Single platform key to test")
    parser.add_argument("--all", action="store_true", help="Test all platforms in sequence")
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION_SECONDS)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--read-ratio", type=float, default=DEFAULT_READ_RATIO)
    args = parser.parse_args()

    if not args.platform and not args.all:
        parser.error("Specify --platform <key> or --all")

    RESULTS_DIR.mkdir(exist_ok=True)
    platform_keys = list(PLATFORMS.keys()) if args.all else [args.platform]

    for key in platform_keys:
        result = run_mixed_workload(key, args.duration, args.concurrency, args.read_ratio)
        out_path = RESULTS_DIR / f"mixed_workload_{key}.json"
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"  Results written to {out_path}")


if __name__ == "__main__":
    main()
