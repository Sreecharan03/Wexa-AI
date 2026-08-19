"""
ArangoDB driver.

Genuinely different from the other 3: ArangoDB is document+graph, not a
pure property-graph engine, and its bulk-insert API (collection.insert_many)
is a proper batch API rather than a "run this query N times" pattern like
the Cypher-based UNWIND approach.
"""

import time
from arango import ArangoClient
from arango.exceptions import ArangoServerError
from src.drivers.base import GraphDriver


def _insert_with_retry(collection, docs, max_retries=5):
    """
    ArangoDB under the 0.5 vCPU cap has been observed to intermittently
    drop HTTP connections during sustained back-to-back insert_many calls.
    This retry wrapper is a resilience measure to let the benchmark
    complete, NOT a silent cover-up: retry_count is tracked and returned
    to the caller so it appears in the final results as an honest caveat.
    """
    retries = 0
    last_exception = None
    for attempt in range(max_retries):
        try:
            collection.insert_many(docs)
            return retries
        except (ConnectionAbortedError, ConnectionError, ArangoServerError) as e:
            last_exception = e
            retries += 1
            time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(
        f"insert_many failed after {max_retries} retries. Last error: {last_exception}"
    )


class ArangoDriver(GraphDriver):

    def __init__(self, uri: str, user: str, password: str, db_name: str):
        self.uri = uri
        self.user = user
        self.password = password
        self.db_name = db_name
        self.client = None
        self.db = None
        self.last_node_load_retries = 0
        self.last_edge_load_retries = 0

    def connect(self):
        self.client = ArangoClient(hosts=self.uri)
        sys_db = self.client.db("_system", username=self.user, password=self.password)
        if not sys_db.has_database(self.db_name):
            sys_db.create_database(self.db_name)
        self.db = self.client.db(self.db_name, username=self.user, password=self.password)

        if not self.db.has_collection("authors"):
            self.db.create_collection("authors")
        if not self.db.has_collection("collaborates"):
            self.db.create_collection("collaborates", edge=True)

    def close(self):
        pass

    def clear_database(self):
        self.db.collection("authors").truncate()
        self.db.collection("collaborates").truncate()

    def load_nodes(self, nodes: list[dict], batch_size: int) -> float:
        authors = self.db.collection("authors")
        docs = [{"_key": str(n["id"]), "id": n["id"], "bucket": n["bucket"]} for n in nodes]

        start = time.perf_counter()
        total_retries = 0
        for i in range(0, len(docs), batch_size):
            total_retries += _insert_with_retry(authors, docs[i:i + batch_size])
        elapsed = time.perf_counter() - start
        self.last_node_load_retries = total_retries
        if total_retries > 0:
            print(f"  [ArangoDB] node load required {total_retries} batch retries")
        return elapsed

    def load_edges(self, edges: list[dict], batch_size: int) -> float:
        collab = self.db.collection("collaborates")
        docs = [
            {"_from": f"authors/{e['source']}", "_to": f"authors/{e['target']}"}
            for e in edges
        ]

        start = time.perf_counter()
        total_retries = 0
        for i in range(0, len(docs), batch_size):
            total_retries += _insert_with_retry(collab, docs[i:i + batch_size])
        elapsed = time.perf_counter() - start
        self.last_edge_load_retries = total_retries
        if total_retries > 0:
            print(f"  [ArangoDB] edge load required {total_retries} batch retries")
        return elapsed

    def create_primary_index(self) -> float:
        return 0.0

    def create_secondary_index(self) -> float:
        start = time.perf_counter()
        self.db.collection("authors").add_index({"type": "persistent", "fields": ["bucket"]})
        return time.perf_counter() - start

    def run_read_query(self, cypher: str, aql: str, params: dict) -> list:
        cursor = self.db.aql.execute(aql, bind_vars=params)
        return list(cursor)

    def get_footprint(self) -> dict:
        try:
            authors_stats = self.db.collection("authors").statistics()
            collab_stats = self.db.collection("collaborates").statistics()
            return {
                "authors_collection_bytes": authors_stats.get("documents_size"),
                "collaborates_collection_bytes": collab_stats.get("documents_size"),
            }
        except Exception:
            return {"note": "not observable — collection statistics not available"}
