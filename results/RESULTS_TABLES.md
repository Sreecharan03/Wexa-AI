# Results Tables (auto-generated from results/*.json — do not hand-edit)

## Platform Specifications

| Platform | Deployment | Query Language | vCPU | RAM | Disk |
|---|---|---|---|---|---|
| CognoDB Cloud | managed-cloud | cypher | 0.5 (burstable) | 256 MB | 1 GB |
| Neo4j AuraDB Free | managed-cloud | cypher | not published (shared/burstable) | ~250 MB (vendor-stated ceiling) | hard-capped at 200k nodes / 400k relationships (not a GB figure) |
| FalkorDB (self-hosted) | self-hosted-docker | cypher | 0.5 (docker --cpus cap) | 256 MB (docker --memory cap) | not hard-capped (Docker limitation, stated as caveat) |
| ArangoDB Community Edition (self-hosted) | self-hosted-docker | aql | 0.5 (docker --cpus cap) | 256 MB (docker --memory cap) | not hard-capped (Docker limitation, stated as caveat) |

## Platform Notes & Fairness Deviations

**CognoDB Cloud**: Free tier (c0 instance). Bolt+s protocol, Neo4j driver compatible.

**Neo4j AuraDB Free**: AuraDB Free enforces a node/relationship count cap rather than a disk size. Dataset was sized to fit under this cap (see README dataset section). Auth gotcha: the connection username is the instance ID itself (e.g. '6faa993d'), NOT the literal string 'neo4j' as older Neo4j community threads and some docs suggest — confirmed via the console's own copy-paste connection snippet, not general documentation.

**FalkorDB (self-hosted)**: FalkorDB Cloud's actual free tier is only 100MB RAM (smaller than CognoDB's 256MB) — self-hosting via Docker and capping to 256MB was used instead to keep resource parity honest, per the assignment's explicit allowance for capped self-hosted deployments.

**ArangoDB Community Edition (self-hosted)**: ArangoDB Oasis dropped its permanent free tier (now 14-day trial only), which would risk expiring mid-benchmark. Self-hosted Community Edition via Docker used instead, capped identically to FalkorDB.


## Data Loading

| Platform | Nodes/sec | Rel/sec | Primary Index (s) | Secondary Index (s) | Total Load Time (s) | Node Retries | Edge Retries |
|---|---|---|---|---|---|---|---|
| CognoDB Cloud | 26,901.7 | 21,704.0 | 0.057 | 0.056 | 9.88 | 0 | 0 |
| Neo4j AuraDB Free | 3,169.9 | 2,802.3 | 0.468 | 0.463 | 77.06 | 0 | 0 |
| FalkorDB (self-hosted) | 45,613.0 | 5,004.2 | 0.003 | 0.004 | 39.99 | 0 | 0 |
| ArangoDB Community Edition (self-hosted) | 14,990.3 | 16,906.7 | 0.000 | 0.002 | 12.97 | 0 | 3 |

## Footprint

| Platform | Footprint |
|---|---|
| CognoDB Cloud | note: not observable — store-size procedure not available on this instance |
| Neo4j AuraDB Free | note: not observable — store-size procedure not available on this instance |
| FalkorDB (self-hosted) | redis_used_memory_bytes: 24216904 |
| ArangoDB Community Edition (self-hosted) | authors_collection_bytes: 1248223, collaborates_collection_bytes: 17714642 |

## Traversal Latency

**1-Hop Traversal**

| Platform | p50 (ms) | p95 (ms) | Mean (ms) | Min (ms) | Max (ms) | Errors |
|---|---|---|---|---|---|---|
| CognoDB Cloud | 14.68 | 18.43 | 15.29 | 13.76 | 27.90 | 0 |
| Neo4j AuraDB Free | 220.32 | 225.13 | 234.25 | 219.34 | 1334.74 | 0 |
| FalkorDB (self-hosted) | 0.75 | 1.25 | 0.92 | 0.58 | 13.46 | 0 |
| ArangoDB Community Edition (self-hosted) | 2.04 | 4.06 | 2.29 | 1.35 | 8.25 | 0 |

**2-Hop Traversal**

| Platform | p50 (ms) | p95 (ms) | Mean (ms) | Min (ms) | Max (ms) | Errors |
|---|---|---|---|---|---|---|
| CognoDB Cloud | 19.93 | 134.59 | 38.23 | 13.75 | 189.14 | 0 |
| Neo4j AuraDB Free | 228.32 | 556.62 | 298.38 | 219.50 | 1439.71 | 0 |
| FalkorDB (self-hosted) | 1.60 | 13.35 | 3.37 | 0.69 | 30.97 | 0 |
| ArangoDB Community Edition (self-hosted) | 9.49 | 183.40 | 39.67 | 1.55 | 309.28 | 0 |

**3-Hop Traversal**

| Platform | p50 (ms) | p95 (ms) | Mean (ms) | Min (ms) | Max (ms) | Errors |
|---|---|---|---|---|---|---|
| CognoDB Cloud | 373.88 | 3442.52 | 808.02 | 13.99 | 7676.30 | 0 |
| Neo4j AuraDB Free | 1118.14 | 3590.11 | 1375.73 | 219.40 | 4090.56 | 0 |
| FalkorDB (self-hosted) | 19.28 | 68.88 | 25.56 | 0.99 | 94.10 | 0 |
| ArangoDB Community Edition (self-hosted) | 379.85 | 8933.29 | 2158.97 | 2.23 | 19925.71 | 0 |

## Lookup Latency

**Point Lookup (exact id match)**

| Platform | p50 (ms) | p95 (ms) | Mean (ms) | Min (ms) | Max (ms) | Errors |
|---|---|---|---|---|---|---|
| CognoDB Cloud | 14.26 | 14.69 | 14.34 | 13.79 | 16.12 | 0 |
| Neo4j AuraDB Free | 219.94 | 223.33 | 242.59 | 219.51 | 1355.61 | 0 |
| FalkorDB (self-hosted) | 0.50 | 0.62 | 0.51 | 0.41 | 0.72 | 0 |
| ArangoDB Community Edition (self-hosted) | 1.19 | 1.77 | 1.30 | 0.99 | 3.01 | 0 |

**Indexed Filtered Lookup (bucket)**

| Platform | p50 (ms) | p95 (ms) | Mean (ms) | Min (ms) | Max (ms) | Errors |
|---|---|---|---|---|---|---|
| CognoDB Cloud | 20.27 | 23.34 | 20.46 | 18.32 | 24.77 | 0 |
| Neo4j AuraDB Free | 225.27 | 229.68 | 248.17 | 224.06 | 1336.85 | 0 |
| FalkorDB (self-hosted) | 1.55 | 2.49 | 1.64 | 1.28 | 3.50 | 0 |
| ArangoDB Community Edition (self-hosted) | 2.15 | 3.92 | 2.38 | 1.69 | 7.04 | 0 |

## Aggregation Latency

**Relationship Count**

| Platform | p50 (ms) | p95 (ms) | Mean (ms) | Min (ms) | Max (ms) | Errors |
|---|---|---|---|---|---|---|
| CognoDB Cloud | 14.21 | 15.38 | 14.34 | 13.78 | 16.99 | 0 |
| Neo4j AuraDB Free | 219.83 | 222.44 | 242.42 | 219.28 | 1340.12 | 0 |
| FalkorDB (self-hosted) | 0.57 | 0.76 | 0.60 | 0.43 | 2.70 | 0 |
| ArangoDB Community Edition (self-hosted) | 1.08 | 1.35 | 1.12 | 0.96 | 1.86 | 0 |

**Degree Distribution (bonus)**

| Platform | p50 (ms) | p95 (ms) | Mean (ms) | Min (ms) | Max (ms) | Errors |
|---|---|---|---|---|---|---|
| CognoDB Cloud | 4051.24 | 4301.87 | 4068.99 | 3841.74 | 4527.28 | 0 |
| Neo4j AuraDB Free | 264.88 | 294.19 | 301.04 | 260.79 | 1375.80 | 0 |
| FalkorDB (self-hosted) | 1393.55 | 1569.26 | 1393.30 | 1193.78 | 1609.42 | 0 |
| ArangoDB Community Edition (self-hosted) | 503.16 | 596.06 | 512.97 | 427.58 | 663.01 | 0 |

## Mixed Read/Write Workload

| Platform | Concurrency | Read/Write Mix | Ops/sec | Reads/sec | Writes/sec | Total Errors | Dataset Intact |
|---|---|---|---|---|---|---|---|
| CognoDB Cloud | 10 | 80/20 | 418.7 | 335.3 | 83.4 | 0 | True |
| Neo4j AuraDB Free | 10 | 80/20 | 37.9 | 30.2 | 7.7 | 0 | True |
| FalkorDB (self-hosted) | 10 | 80/20 | 2253.2 | 1806.0 | 447.2 | 0 | True |
| ArangoDB Community Edition (self-hosted) | 10 | 80/20 | 851.8 | 680.9 | 170.9 | 0 | True |
