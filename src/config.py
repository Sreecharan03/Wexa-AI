"""
Central platform registry for the benchmark suite.

Every loader, workload runner, and report generator imports PLATFORMS from
here rather than hardcoding connection details or specs — this is what
guarantees "same resources, same setup, documented" across the whole suite
instead of each script silently drifting from the others.

Final lineup (4 platforms, meets the assignment's "at least four" minimum):
  - CognoDB Cloud   (managed, required by the assignment)
  - Neo4j AuraDB Free (managed)
  - FalkorDB        (self-hosted, Docker, capped to match CognoDB's free tier)
  - ArangoDB CE      (self-hosted, Docker, capped to match CognoDB's free tier)

Memgraph was evaluated and dropped — see README's Methodology & Caveats
section for the full reproducible-crash writeup.
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class PlatformSpec:
    key: str                    # short id used in results filenames, e.g. "cognodb"
    display_name: str           # human-readable name for README tables
    query_language: str         # "cypher" or "aql"
    deployment: str             # "managed-cloud" or "self-hosted-docker"
    advertised_vcpu: str        # as documented by the vendor / as set in docker-compose
    advertised_ram: str
    advertised_disk: str
    indexed_properties: list    # properties we create indexes on, for the lookup workload
    notes: str = ""             # anything relevant to fairness/caveats for this platform


PLATFORMS = {

    "cognodb": PlatformSpec(
        key="cognodb",
        display_name="CognoDB Cloud",
        query_language="cypher",
        deployment="managed-cloud",
        advertised_vcpu="0.5 (burstable)",
        advertised_ram="256 MB",
        advertised_disk="1 GB",
        indexed_properties=["id", "bucket"],
        notes="Free tier (c0 instance). Bolt+s protocol, Neo4j driver compatible.",
    ),

    "aura": PlatformSpec(
        key="aura",
        display_name="Neo4j AuraDB Free",
        query_language="cypher",
        deployment="managed-cloud",
        advertised_vcpu="not published (shared/burstable)",
        advertised_ram="~250 MB (vendor-stated ceiling)",
        advertised_disk="hard-capped at 200k nodes / 400k relationships (not a GB figure)",
        indexed_properties=["id", "bucket"],
        notes=(
            "AuraDB Free enforces a node/relationship count cap rather than a disk size. "
            "Dataset was sized to fit under this cap (see README dataset section). "
            "Auth gotcha: the connection username is the instance ID itself (e.g. "
            "'6faa993d'), NOT the literal string 'neo4j' as older Neo4j community "
            "threads and some docs suggest — confirmed via the console's own "
            "copy-paste connection snippet, not general documentation."
        ),
    ),

    "falkordb": PlatformSpec(
        key="falkordb",
        display_name="FalkorDB (self-hosted)",
        query_language="cypher",
        deployment="self-hosted-docker",
        advertised_vcpu="0.5 (docker --cpus cap)",
        advertised_ram="256 MB (docker --memory cap)",
        advertised_disk="not hard-capped (Docker limitation, stated as caveat)",
        indexed_properties=["id", "bucket"],
        notes=(
            "FalkorDB Cloud's actual free tier is only 100MB RAM (smaller than CognoDB's "
            "256MB) — self-hosting via Docker and capping to 256MB was used instead to "
            "keep resource parity honest, per the assignment's explicit allowance for "
            "capped self-hosted deployments."
        ),
    ),

    "arangodb": PlatformSpec(
        key="arangodb",
        display_name="ArangoDB Community Edition (self-hosted)",
        query_language="aql",
        deployment="self-hosted-docker",
        advertised_vcpu="0.5 (docker --cpus cap)",
        advertised_ram="256 MB (docker --memory cap)",
        advertised_disk="not hard-capped (Docker limitation, stated as caveat)",
        indexed_properties=["id", "bucket"],
        notes=(
            "ArangoDB Oasis dropped its permanent free tier (now 14-day trial only), "
            "which would risk expiring mid-benchmark. Self-hosted Community Edition via "
            "Docker used instead, capped identically to FalkorDB."
        ),
    ),
}


def get_connection_info(platform_key: str) -> dict:
    """
    Returns the env-var-sourced connection details for a given platform.
    Never hardcode secrets here — everything comes from .env (gitignored).
    """
    if platform_key == "cognodb":
        return {
            "uri": os.environ["COGNODB_URI"],
            "user": os.environ["COGNODB_USER"],
            "password": os.environ["COGNODB_PASSWORD"],
        }
    elif platform_key == "aura":
        return {
            "uri": os.environ["AURA_URI"],
            "user": os.environ["AURA_USER"],
            "password": os.environ["AURA_PASSWORD"],
        }
    elif platform_key == "falkordb":
        return {
            "host": os.environ.get("FALKORDB_HOST", "localhost"),
            "port": int(os.environ.get("FALKORDB_PORT", 6380)),
        }
    elif platform_key == "arangodb":
        return {
            "uri": os.environ.get("ARANGO_URI", "http://localhost:8529"),
            "user": os.environ.get("ARANGO_USER", "root"),
            "password": os.environ["ARANGO_PASSWORD"],
            "db_name": os.environ.get("ARANGO_DB", "benchmark"),
        }
    else:
        raise ValueError(f"Unknown platform key: {platform_key}")


if __name__ == "__main__":
    # Quick sanity check — run this file directly to confirm registry loads correctly
    for key, spec in PLATFORMS.items():
        print(f"{spec.display_name:45s} | {spec.query_language:6s} | {spec.deployment}")
