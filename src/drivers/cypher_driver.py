"""
Cypher/Bolt driver — used for CognoDB Cloud and Neo4j AuraDB Free.
"""

import time
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from src.drivers.base import GraphDriver


def _run_with_retry(session, query, params, max_retries=5):
    """
    Same resilience pattern as ArangoDriver's _insert_with_retry, applied
    here for methodology consistency: if one platform gets crash protection
    against transient connection issues under a capped-CPU instance, every
    platform should, so a transient failure doesn't unfairly penalize one
    platform with a hard crash while another survives it gracefully.
    """
    retries = 0
    last_exception = None
    for attempt in range(max_retries):
        try:
            session.run(query, **params)
            return retries
        except (ServiceUnavailable, SessionExpired, ConnectionError) as e:
            last_exception = e
            retries += 1
            time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(
        f"Query failed after {max_retries} retries. Last error: {last_exception}"
    )


class CypherDriver(GraphDriver):

    def __init__(self, uri: str, user: str, password: str, platform_label: str):
        self.uri = uri
        self.user = user
        self.password = password
        self.platform_label = platform_label
        self.driver = None
        self.last_node_load_retries = 0
        self.last_edge_load_retries = 0

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
        total_retries = 0
        with self.driver.session() as session:
            for i in range(0, len(nodes), batch_size):
                batch = nodes[i:i + batch_size]
                total_retries += _run_with_retry(
                    session,
                    """
                    UNWIND $batch AS row
                    CREATE (a:Author {id: row.id, bucket: row.bucket})
                    """,
                    {"batch": batch},
                )
        elapsed = time.perf_counter() - start
        self.last_node_load_retries = total_retries
        if total_retries > 0:
            print(f"  [{self.platform_label}] node load required {total_retries} batch retries")
        return elapsed

    def load_edges(self, edges: list[dict], batch_size: int) -> float:
        start = time.perf_counter()
        total_retries = 0
        with self.driver.session() as session:
            for i in range(0, len(edges), batch_size):
                batch = edges[i:i + batch_size]
                total_retries += _run_with_retry(
                    session,
                    """
                    UNWIND $batch AS row
                    MATCH (a:Author {id: row.source})
                    MATCH (b:Author {id: row.target})
                    CREATE (a)-[:COLLABORATES]->(b)
                    """,
                    {"batch": batch},
                )
        elapsed = time.perf_counter() - start
        self.last_edge_load_retries = total_retries
        if total_retries > 0:
            print(f"  [{self.platform_label}] edge load required {total_retries} batch retries")
        return elapsed

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
