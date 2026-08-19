"""
FalkorDB driver.
"""

import time
from falkordb import FalkorDB
from src.drivers.base import GraphDriver


class FalkorDriver(GraphDriver):

    def __init__(self, host: str, port: int, graph_name: str = "benchmark"):
        self.host = host
        self.port = port
        self.graph_name = graph_name
        self.db = None
        self.graph = None

    def connect(self):
        self.db = FalkorDB(host=self.host, port=self.port)
        self.graph = self.db.select_graph(self.graph_name)
        self.graph.query("RETURN 1")

    def close(self):
        pass

    def clear_database(self):
        try:
            self.graph.delete()
        except Exception:
            pass
        self.graph = self.db.select_graph(self.graph_name)

    def load_nodes(self, nodes: list[dict], batch_size: int) -> float:
        start = time.perf_counter()
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i + batch_size]
            self.graph.query(
                "UNWIND $batch AS row CREATE (a:Author {id: row.id, bucket: row.bucket})",
                {"batch": batch},
            )
        return time.perf_counter() - start

    def load_edges(self, edges: list[dict], batch_size: int) -> float:
        start = time.perf_counter()
        for i in range(0, len(edges), batch_size):
            batch = edges[i:i + batch_size]
            self.graph.query(
                """
                UNWIND $batch AS row
                MATCH (a:Author {id: row.source})
                MATCH (b:Author {id: row.target})
                CREATE (a)-[:COLLABORATES]->(b)
                """,
                {"batch": batch},
            )
        return time.perf_counter() - start

    def create_primary_index(self) -> float:
        start = time.perf_counter()
        self.graph.query("CREATE INDEX FOR (a:Author) ON (a.id)")
        return time.perf_counter() - start

    def create_secondary_index(self) -> float:
        start = time.perf_counter()
        self.graph.query("CREATE INDEX FOR (a:Author) ON (a.bucket)")
        return time.perf_counter() - start

    def run_read_query(self, cypher: str, aql: str, params: dict) -> list:
        result = self.graph.query(cypher, params)
        columns = result.header
        column_names = [col[1] for col in columns] if columns else []
        return [dict(zip(column_names, row)) for row in result.result_set]

    def get_footprint(self) -> dict:
        try:
            info = self.db.connection.info("memory")
            return {"redis_used_memory_bytes": info.get("used_memory")}
        except Exception:
            return {"note": "not observable — memory INFO command not available"}
