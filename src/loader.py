"""
Loader orchestrator — runs the full timed data-loading pipeline against
one platform (or all platforms, via --all).
"""

import argparse
import csv
import json
import time
from pathlib import Path

from src.config import PLATFORMS
from src.driver_factory import get_driver

REPO_ROOT = Path(__file__).resolve().parent.parent
NODES_CSV = REPO_ROOT / "data" / "nodes.csv"
EDGES_CSV = REPO_ROOT / "data" / "edges.csv"
RESULTS_DIR = REPO_ROOT / "results"

BATCH_SIZE = 1000


def load_csv_data():
    with open(NODES_CSV) as f:
        reader = csv.DictReader(f)
        nodes = [{"id": int(row["id"]), "bucket": int(row["bucket"])} for row in reader]

    with open(EDGES_CSV) as f:
        reader = csv.DictReader(f)
        edges = [{"source": int(row["source"]), "target": int(row["target"])} for row in reader]

    return nodes, edges


def run_load_for_platform(platform_key: str, nodes: list, edges: list) -> dict:
    spec = PLATFORMS[platform_key]
    print(f"\n{'='*60}")
    print(f"Loading into: {spec.display_name}")
    print(f"{'='*60}")

    driver = get_driver(platform_key)

    print("Clearing database for a clean baseline...")
    driver.clear_database()

    print(f"Loading {len(nodes):,} nodes (batch size {BATCH_SIZE})...")
    node_load_seconds = driver.load_nodes(nodes, BATCH_SIZE)
    print(f"  -> {node_load_seconds:.2f}s ({len(nodes)/node_load_seconds:.1f} nodes/sec)")

    print("Creating primary index on 'id' (required before edge loading)...")
    primary_index_seconds = driver.create_primary_index()
    print(f"  -> {primary_index_seconds:.2f}s")

    print(f"Loading {len(edges):,} edges (batch size {BATCH_SIZE})...")
    edge_load_seconds = driver.load_edges(edges, BATCH_SIZE)
    print(f"  -> {edge_load_seconds:.2f}s ({len(edges)/edge_load_seconds:.1f} relationships/sec)")

    print("Creating secondary index on 'bucket' (used by lookup workload)...")
    secondary_index_seconds = driver.create_secondary_index()
    print(f"  -> {secondary_index_seconds:.2f}s")

    print("Capturing footprint (where observable)...")
    footprint = driver.get_footprint()
    print(f"  -> {footprint}")

    driver.close()

    total_wall_clock_seconds = node_load_seconds + primary_index_seconds + edge_load_seconds

    result = {
        "platform": platform_key,
        "platform_display_name": spec.display_name,
        "node_count": len(nodes),
        "relationship_count": len(edges),
        "batch_size": BATCH_SIZE,
        "node_load_seconds": round(node_load_seconds, 3),
        "nodes_per_second": round(len(nodes) / node_load_seconds, 1),
        "primary_index_seconds": round(primary_index_seconds, 3),
        "edge_load_seconds": round(edge_load_seconds, 3),
        "relationships_per_second": round(len(edges) / edge_load_seconds, 1),
        "secondary_index_seconds": round(secondary_index_seconds, 3),
        "total_wall_clock_load_seconds": round(total_wall_clock_seconds, 3),
        "footprint": footprint,
    }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", type=str, help="Single platform key to load")
    parser.add_argument("--all", action="store_true", help="Load all platforms in sequence")
    args = parser.parse_args()

    if not args.platform and not args.all:
        parser.error("Specify --platform <key> or --all")

    RESULTS_DIR.mkdir(exist_ok=True)

    print("Loading dataset CSVs into memory...")
    nodes, edges = load_csv_data()
    print(f"  {len(nodes):,} nodes, {len(edges):,} edges ready to load.")

    platform_keys = list(PLATFORMS.keys()) if args.all else [args.platform]

    all_results = {}
    for key in platform_keys:
        result = run_load_for_platform(key, nodes, edges)
        all_results[key] = result

        out_path = RESULTS_DIR / f"load_{key}.json"
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nResults written to {out_path}")

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for key, r in all_results.items():
        print(
            f"{r['platform_display_name']:45s} | "
            f"{r['nodes_per_second']:>10.1f} nodes/sec | "
            f"{r['relationships_per_second']:>10.1f} rels/sec | "
            f"{r['total_wall_clock_load_seconds']:>8.2f}s total"
        )


if __name__ == "__main__":
    main()
