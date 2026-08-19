"""
Cypher/Bolt driver — used for CognoDB Cloud and Neo4j AuraDB Free.
"""

import time
from neo4j import GraphDatabase
from src.drivers.base import GraphDriver


class CypherDriver(GraphDriver):

    def __init__(self, uri: str, user: str, password: str, platform_label: str):
        self.uri = uri
        self.user = user
        self.password = password
        self.platform_label = platform_label
        self.driver = None

    def connect(self):
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        self.driver.verify_connectivity()

    def close(self):
        if self.driver:
            self.driver.close()

    def clear_database(self):
        with self.driver.session() as session:
            while True:
                result = session.run(
                    "MATCH (n) WITH n LIMIT 5000 DETACH DELETE n RETURN count(n) AS deleted"
                )
                deleted = result.single()["deleted"]
                if deleted == 0:
                    break

    def load_nodes(self, nodes: list[dict], batch_size: int) -> float:
        start = time.perf_counter()
        with self.driver.session() as session:
            for i in range(0, len(nodes), batch_size):
                batch = nodes[i:i + batch_size]
                session.run(
                    """
                    UNWIND $batch AS row
                    CREATE (a:Author {id: row.id, bucket: row.bucket})
                    """,
                    batch=batch,
                )
        return time.perf_counter() - start

    def load_edges(self, edges: list[dict], batch_size: int) -> float:
        start = time.perf_counter()
        with self.driver.session() as session:
            for i in range(0, len(edges), batch_size):
                batch = edges[i:i + batch_size]
                session.run(
                    """
                    UNWIND $batch AS row
                    MATCH (a:Author {id: row.source})
                    MATCH (b:Author {id: row.target})
                    CREATE (a)-[:COLLABORATES]->(b)
                    """,
                    batch=batch,
                )
        return time.perf_counter() - start

    def create_primary_index(self) -> float:
        start = time.perf_counter()
        with self.driver.session() as session:
            session.run("CREATE INDEX author_id_index IF NOT EXISTS FOR (a:Author) ON (a.id)")
            session.run("CALL db.awaitIndexes(300)")
        return time.perf_counter() - start

    def create_secondary_index(self) -> float:
        start = time.perf_counter()
        with self.driver.session() as session:
            session.run("CREATE INDEX author_bucket_index IF NOT EXISTS FOR (a:Author) ON (a.bucket)")
            session.run("CALL db.awaitIndexes(300)")
        return time.perf_counter() - start

    def run_read_query(self, cypher: str, aql: str, params: dict) -> list:
        with self.driver.session() as session:
            result = session.run(cypher, **params)
            return [record.data() for record in result]

    def get_footprint(self) -> dict:
        try:
            with self.driver.session() as session:
                result = session.run("CALL apoc.monitor.store()")
                record = result.single()
                if record:
                    return dict(record.data())
        except Exception as e:
            pass
        return {"note": "not observable — store-size procedure not available on this instance"}
