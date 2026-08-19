"""
ArangoDB driver.
"""

import time
from arango import ArangoClient
from src.drivers.base import GraphDriver


class ArangoDriver(GraphDriver):

    def __init__(self, uri: str, user: str, password: str, db_name: str):
        self.uri = uri
        self.user = user
        self.password = password
        self.db_name = db_name
        self.client = None
        self.db = None

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
        for i in range(0, len(docs), batch_size):
            authors.insert_many(docs[i:i + batch_size])
        return time.perf_counter() - start

    def load_edges(self, edges: list[dict], batch_size: int) -> float:
        collab = self.db.collection("collaborates")
        docs = [
            {"_from": f"authors/{e['source']}", "_to": f"authors/{e['target']}"}
            for e in edges
        ]

        start = time.perf_counter()
        for i in range(0, len(docs), batch_size):
            collab.insert_many(docs[i:i + batch_size])
        return time.perf_counter() - start

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
                "authors_collection_bytes": authors_stats.get("figures", {}).get("documentsSize"),
                "collaborates_collection_bytes": collab_stats.get("figures", {}).get("documentsSize"),
            }
        except Exception:
            return {"note": "not observable — collection statistics not available"}
