📝 I wrote up the full story of what broke — [read it on dev.to](https://dev.to/sree_charan/i-gave-five-graph-databases-256mb-of-ram-each-heres-what-broke-1jde)

# CognoDB vs. the World: A Graph Database Benchmark

This is a benchmark comparing [CognoDB Cloud](https://console.cognodb.com) against four other graph databases — Neo4j AuraDB Free, FalkorDB, and ArangoDB, all under matched resource limits, on the same dataset, with the same queries. It was built for a take-home assignment, but I tried to build it like something I'd actually trust if I found it on GitHub while evaluating databases for a real project.

Short version of the results: nobody "wins." CognoDB is fast and consistent for everything except one query type where it falls apart for reasons I don't fully understand. FalkorDB is stupidly fast because it's in-memory and running on localhost. AuraDB pays a steep, very consistent tax for being a managed cloud service. ArangoDB is solid but its graph traversal engine gets unpredictable at depth 3. Read on for the actual numbers and a pretty long list of things that broke along the way.

## TL;DR results

| | CognoDB | AuraDB Free | FalkorDB | ArangoDB |
|---|---|---|---|---|
| 1-hop lookup (p50) | 14.7ms | 220ms | 0.75ms | 2.0ms |
| 3-hop traversal (p50) | 374ms | 1118ms | 19ms | 380ms |
| 3-hop traversal (p95) | 3443ms | 3590ms | 69ms | **8933ms** |
| Mixed workload throughput | 419 ops/sec | 38 ops/sec | 2253 ops/sec | 852 ops/sec |
| Deployment | managed cloud | managed cloud | self-hosted (Docker) | self-hosted (Docker) |

Full tables with p50/p95/mean/min/max for every metric are in [`results/RESULTS_TABLES.md`](results/RESULTS_TABLES.md), auto-generated from the raw JSON so nothing here is hand-typed or could have drifted from what was actually measured.

## Reproducing this

```bash
git clone https://github.com/Sreecharan03/Wexa-AI.git
cd Wexa-AI/wexa-benchmark
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your own CognoDB + AuraDB credentials
docker compose up -d
bash scripts/configure_falkordb_persistence.sh   # see caveats — this is not optional
python -m src.dataset
python -m src.loader --all
python -m src.workload_runner --all
python -m src.mixed_workload_runner --all
python -m src.aggregate_results
```

You'll need free accounts for CognoDB Cloud and Neo4j AuraDB — both are genuinely free, no card required. FalkorDB and ArangoDB run locally via the included `docker-compose.yml`, capped to match CognoDB's free-tier specs (0.5 vCPU / 256MB RAM).

## The dataset

[SNAP's `ca-AstroPh`](https://snap.stanford.edu/data/ca-AstroPh.html) — a collaboration network of arXiv Astro Physics papers. **18,772 nodes, 198,050 edges**, both numbers measured directly off the downloaded file at prep time, not copied from SNAP's own documentation page. That distinction actually mattered: SNAP's file stores each collaboration as two directed entries (A→B and B→A), so the raw file has 396,160 rows. I deduplicated those down to true unique undirected edges. If I hadn't caught this, every platform would've been loading double the real edge count, and 396,160 relationships sits uncomfortably close to AuraDB Free's hard 400k cap — close enough that a small quirk in how Aura counts internally could've caused a load failure on exactly one platform, which would've been a fairness problem, not just an inconvenience.

Every node also carries a synthetic `bucket` property (`id % 100`). This isn't part of the original dataset — I added it because the assignment asks for two genuinely different lookup metrics ("point lookup" and "indexed/filtered lookup"), and the raw data only has one property (`id`). Without `bucket`, both queries would've been identical, which felt like padding a metrics table rather than actually testing anything.

## Why these four platforms

CognoDB was mandatory. For the other four, I originally picked Memgraph, FalkorDB, and ArangoDB — self-hostable via Docker, plus AuraDB Free as the one genuinely comparable managed-cloud alternative.

Memgraph didn't make it. It segfaulted on startup, reproducibly, across two versions (2.20.1 and 2.18.1), with zero resource limits applied, unconfined seccomp, forced `runc` runtime, and confirmed AVX2 support on the host CPU — six separate variables ruled out one at a time before I gave up and moved on. Whatever's wrong is specific to this host environment at a level below anything I could fix from inside a container. I've got the full debugging trail if anyone's curious, but the short version is: sometimes a database just won't run on your machine and the honest move is to say so and swap it, not force it. CognoDB + AuraDB + FalkorDB + ArangoDB still meets the assignment's "at least four" minimum — this isn't a shortfall, it's landing exactly on the required count.

FalkorDB Cloud and ArangoDB Oasis both turned out to have worse free tiers than expected once I actually checked — FalkorDB Cloud caps out at 100MB RAM (smaller than CognoDB's 256MB, which would've been its own fairness violation), and ArangoDB Oasis dropped its permanent free tier sometime before I started this and now only offers a 14-day trial. Self-hosting both via Docker, capped to match CognoDB's specs exactly, was the more honest way to keep the comparison fair — the assignment explicitly allows this.

## Resource parity

Every platform runs at 0.5 vCPU / 256MB RAM, matching CognoDB's advertised free-tier spec. For CognoDB and AuraDB that's the vendor's actual number; for FalkorDB and ArangoDB it's enforced via `docker-compose.yml`'s `cpus`/`mem_limit`. Disk isn't hard-capped for the self-hosted pair — Docker doesn't cleanly enforce per-container disk quotas without a dedicated loop-mounted filesystem, and I'd rather say that plainly than pretend it's capped when it isn't.

AuraDB Free doesn't publish a disk figure at all — it caps by node/relationship count instead (200k nodes / 400k relationships). The dataset was sized to sit comfortably under that.

## Architecture

```
src/
  config.py              platform registry — specs, connection info, notes
  dataset.py             downloads + dedupes the SNAP data, writes clean CSVs
  queries.py             every benchmark query, once, in Cypher AND AQL
  harness.py             warmup/timing/percentile math
  drivers/
    base.py               abstract interface every driver implements
    cypher_driver.py       CognoDB + AuraDB (genuinely shared code, both Bolt/Cypher)
    falkordb_driver.py     FalkorDB (Cypher over Redis protocol)
    arangodb_driver.py     ArangoDB (AQL, document API)
  driver_factory.py       platform key -> connected driver
  loader.py                runs the timed data load
  workload_runner.py       runs traversal/lookup/aggregation queries
  mixed_workload_runner.py concurrent read/write test
  aggregate_results.py     builds RESULTS_TABLES.md from the raw JSON
```

The thing I actually care about here, more than any individual number, is `queries.py`. Every query — 1-hop, 2-hop, 3-hop, both lookups, both aggregations — is defined exactly once, with a Cypher version and an AQL version sitting next to each other. Every driver pulls from this same file. There's no path where CognoDB's "1-hop traversal" could quietly become a slightly different query than FalkorDB's without someone noticing, because there's only one place that query text lives. That's the whole ballgame for the "same logical queries everywhere" requirement — not a promise in a README, but something structurally impossible to violate by accident.

## What went wrong (the honest section)

I'm putting this front and center rather than burying it, because I think a benchmark that pretends everything went smoothly is less trustworthy than one that shows its work.

**Memgraph — dropped entirely.** Covered above. Reproducible SIGSEGV, root cause not identified, moved on after exhausting the reasonable debugging avenues.

**ArangoDB dropped connections under sustained load, twice.** During bulk loading, `insert_many` calls started failing with `ConnectionAbortedError` partway through the edge load — not from memory pressure (confirmed via `docker stats`, usage stayed under 60% of the cap) but seemingly from the 0.5 vCPU cap causing request timeouts during back-to-back HTTP calls. Fixed with retry-with-backoff logic, which now lives in the driver and gets reported honestly in the results (`node_load_retries` / `edge_load_retries` fields) rather than silently absorbed.

**CognoDB doesn't implement `db.awaitIndexes`.** That's a Neo4j-specific procedure, not core Cypher, and CognoDB threw a straight syntax error on it. Switched to polling `SHOW INDEXES` instead — except CognoDB's version of that command doesn't return a `state` column at all (Neo4j's does, for tracking POPULATING/ONLINE/FAILED). That's actually informative: it suggests CognoDB might build indexes synchronously rather than asynchronously, though I want to be careful — that's an inference from the missing column, not something I directly confirmed. Ended up with a driver that tries the Neo4j-style approach first and falls back to a simpler existence check, logging which strategy actually worked so the difference is visible in the run output rather than hidden.

**ArangoDB's 3-hop AQL traversal is dramatically, unpredictably slow.** The anonymous graph traversal syntax (`FOR v IN 3..3 ANY 'authors/X' collaborates`) took anywhere from a few hundred milliseconds to nearly 20 seconds for a single query, and the p95/p50 ratio for this one query is over 23x — nothing else in the whole dataset comes close to that kind of spread. One of these slow queries directly preceded a container restart mid-benchmark, which then cascaded into every subsequent query failing with connection-refused errors, because — and this was a real gap in the code, not a platform issue — the read path had zero retry protection while the write path already did. Fixed by adding the same retry/reconnect logic to reads that writes already had, symmetrically across all three Cypher-family drivers plus ArangoDB.

**FalkorDB lost all its data on a Studio restart**, despite a correctly-configured bind mount. Turned out to be two separate, compounding bugs: the bind mount was pointed at `/data`, but FalkorDB's actual working directory is `/var/lib/falkordb/data` — wrong path entirely. And separately, passing `--save`/`--appendonly` as a `command:` override in `docker-compose.yml` silently didn't work — `docker inspect` showed the override correctly set, but `redis-cli CONFIG GET` showed the defaults were still active, meaning this image's entrypoint doesn't forward CLI args to the underlying `redis-server` process the way you'd expect. Fixed with the correct mount path plus a small script (`scripts/configure_falkordb_persistence.sh`) that sets persistence via `CONFIG SET` after the container starts, since that's the one thing that actually took effect. This has to be re-run every time the container starts fresh — noted in the reproduction steps above, and yes, I only found this because I lost real data and had to redo a load.

**A Neo4j-specific Cypher extension broke FalkorDB.** The bonus aggregation query originally used `COUNT { (a)-[:COLLABORATES]-() }`, Neo4j 5.x's count-subquery syntax. FalkorDB's openCypher implementation doesn't have it. Rewrote it as `OPTIONAL MATCH` + `count()`, which is core Cypher and works identically everywhere — a good reminder that "Cypher-compatible" doesn't mean every Cypher dialect extension travels with it.

None of these were hidden or patched over quietly — they're all in the git history with commit messages that explain what broke and why, if you want the blow-by-blow.

## Results

Full tables: [`results/RESULTS_TABLES.md`](results/RESULTS_TABLES.md). Everything below is pulled straight from there.

<!-- PASTE FULL RESULTS_TABLES.md CONTENT HERE -->

## Analysis

**AuraDB has a strange, dead-flat floor around 219-225ms on literally every query type**, including `point_lookup` — the simplest possible query, one node by exact id. Even that never drops below ~219ms. That's not query execution cost; a query that trivial should be sub-millisecond on any reasonably-indexed database. It's almost certainly a fixed per-request overhead in AuraDB's free-tier connection routing or auth handshake, paid on every single call regardless of what's being asked. If that's right, it means AuraDB Free's real bottleneck for latency-sensitive workloads isn't its query engine at all — it's the network path in front of it.

**CognoDB is the fastest platform on nearly everything, except one query where it's the slowest by a wide margin.** `aggregation_degree_distribution` — the full-graph degree-bucketing query — takes CognoDB 4051ms at p50, compared to FalkorDB's 1393ms and ArangoDB's 503ms. Every other query on CognoDB is competitive with or faster than the self-hosted platforms. I don't have a confirmed explanation for this — my best guess is something about how CognoDB's query planner handles the `WITH ... CASE ... WITH ... RETURN` chain in this specific query differently than simpler `MATCH` patterns, but that's speculation, not something I verified. Flagging it honestly rather than guessing at a tidy explanation.

**ArangoDB's 3-hop traversal has the widest p50-to-p95 spread of anything in this benchmark** — 380ms to 8933ms, over 23x. Combined with the connection-drop incident during the workload run, this points at something structurally unstable about ArangoDB's anonymous graph traversal (`FOR v IN n..n ANY ...`) under sustained load at this resource tier, rather than a database that's simply "slow but consistent." A named graph object (rather than the anonymous edge-collection traversal used here) might behave differently — that's a real avenue for follow-up I didn't have time to test.

**The mixed workload numbers are the starkest illustration of managed-cloud cost**: FalkorDB sustained 2253 ops/sec, AuraDB sustained 38. That's a 60x gap, and it's not really about database engine quality — FalkorDB is on localhost with zero network hops, AuraDB is a real round trip to managed infrastructure every single time. It's the clearest number in this whole dataset for the tradeoff between "fully managed, zero ops burden" and "raw throughput," and probably the single most useful chart for anyone actually deciding between these options.

## What I'd add with more time

Everything below is explicitly optional per the assignment's own "beyond minimum" criteria, not something skipped from the required scope:

- **Concurrency sweep** (1/10/40 clients) — only ran a single fixed level of 10. Would show whether the throughput gaps above widen or narrow under heavier concurrent load.
- **Charts** — the tables are complete but a few bar charts (especially for that mixed-workload gap) would communicate faster than a table.
- **Cold vs. warm separation** — every number here is post-warmup; cold-start latency wasn't captured separately.
- **Investigating the CognoDB aggregation anomaly and ArangoDB's traversal instability** properly, rather than flagging them as open questions.
