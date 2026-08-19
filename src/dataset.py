"""
Downloads and prepares the ca-AstroPh dataset (SNAP arXiv Astro Physics
collaboration network) for the benchmark suite.
"""

import gzip
import json
import os
import urllib.request
from pathlib import Path

SNAP_URL = "https://snap.stanford.edu/data/ca-AstroPh.txt.gz"

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
DATA_DIR = REPO_ROOT / "data"

RAW_GZ_PATH = RAW_DIR / "ca-AstroPh.txt.gz"
NODES_CSV_PATH = DATA_DIR / "nodes.csv"
EDGES_CSV_PATH = DATA_DIR / "edges.csv"
STATS_JSON_PATH = DATA_DIR / "dataset_stats.json"


def download_raw_file():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if RAW_GZ_PATH.exists():
        print(f"Raw file already cached at {RAW_GZ_PATH}, skipping download.")
        return
    print(f"Downloading {SNAP_URL} ...")
    urllib.request.urlretrieve(SNAP_URL, RAW_GZ_PATH)
    print(f"Downloaded to {RAW_GZ_PATH} ({RAW_GZ_PATH.stat().st_size:,} bytes)")


def parse_edge_list():
    original_id_to_new_id = {}
    seen_pairs = set()
    edges = []
    raw_pair_count = 0
    self_loop_count = 0

    print("Parsing raw edge list...")
    with gzip.open(RAW_GZ_PATH, "rt") as f:
        for line in f:
            if line.startswith("#"):
                continue
            parts = line.strip().split()
            if len(parts) != 2:
                continue
            from_id, to_id = parts[0], parts[1]
            raw_pair_count += 1

            if from_id not in original_id_to_new_id:
                original_id_to_new_id[from_id] = len(original_id_to_new_id)
            if to_id not in original_id_to_new_id:
                original_id_to_new_id[to_id] = len(original_id_to_new_id)

            a = original_id_to_new_id[from_id]
            b = original_id_to_new_id[to_id]

            if a == b:
                self_loop_count += 1
                continue

            key = (a, b) if a < b else (b, a)
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            edges.append(key)

    print(f"Raw directed pairs: {raw_pair_count:,} | Self-loops dropped: {self_loop_count:,} | Unique undirected edges: {len(edges):,}")
    return original_id_to_new_id, edges, raw_pair_count, self_loop_count


def write_csvs(id_map: dict, edges: list):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Writing {NODES_CSV_PATH} ({len(id_map):,} nodes, with synthetic 'bucket' property)...")
    with open(NODES_CSV_PATH, "w") as f:
        f.write("id,bucket\n")
        for new_id in range(len(id_map)):
            f.write(f"{new_id},{new_id % 100}\n")

    print(f"Writing {EDGES_CSV_PATH} ({len(edges):,} edges)...")
    with open(EDGES_CSV_PATH, "w") as f:
        f.write("source,target\n")
        for source, target in edges:
            f.write(f"{source},{target}\n")


def write_stats(id_map: dict, edges: list, raw_pair_count: int, self_loop_count: int):
    stats = {
        "source": "SNAP ca-AstroPh (arXiv Astro Physics collaboration network)",
        "source_url": SNAP_URL,
        "node_count": len(id_map),
        "relationship_count": len(edges),
        "raw_directed_pair_count_before_dedup": raw_pair_count,
        "self_loops_dropped": self_loop_count,
        "directed_in_source_file": True,
        "treated_as": "undirected",
        "notes": (
            "Node/edge counts are measured directly from the downloaded file at "
            f"prep time, not copied from documentation. Raw file contains "
            f"{raw_pair_count:,} directed pairs (each real edge listed twice); "
            f"these were deduplicated to unique undirected edges via a canonical "
            f"(min_id, max_id) key, and {self_loop_count:,} self-loops were dropped. "
            "This keeps a comfortable safety margin under AuraDB Free's 400k "
            "relationship cap and avoids double-counting edges in ingest "
            "throughput / traversal fan-out metrics."
        ),
    }
    with open(STATS_JSON_PATH, "w") as f:
        json.dump(stats, f, indent=2)

    print("\n--- Dataset stats (measured, not assumed) ---")
    print(json.dumps(stats, indent=2))

    if stats["node_count"] > 200_000:
        print("\n⚠️  WARNING: node count exceeds AuraDB Free's 200k node cap!")
    if stats["relationship_count"] > 400_000:
        print("\n⚠️  WARNING: relationship count exceeds AuraDB Free's 400k relationship cap!")
    if not (100_000 <= stats["relationship_count"] <= 500_000):
        print("\n⚠️  WARNING: relationship count falls outside the assignment's suggested 100k-500k range!")


if __name__ == "__main__":
    download_raw_file()
    id_map, edges, raw_pair_count, self_loop_count = parse_edge_list()
    write_csvs(id_map, edges)
    write_stats(id_map, edges, raw_pair_count, self_loop_count)
    print("\nDataset preparation complete.")
