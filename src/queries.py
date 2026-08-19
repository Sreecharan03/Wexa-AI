"""
Single source of truth for every benchmark query, translated per platform's
query dialect (Cypher for CognoDB/AuraDB/FalkorDB, AQL for ArangoDB).
"""

QUERIES = {

    "traversal_1hop": {
        "description": "1-hop traversal from a random start node",
        "cypher": """
            MATCH (a:Author {id: $start_id})-[:COLLABORATES]-(b:Author)
            RETURN DISTINCT b.id AS neighbor_id
        """,
        "aql": """
            FOR v IN 1..1 ANY CONCAT('authors/', @start_id) collaborates
                RETURN DISTINCT v._key
        """,
        "params": ["start_id"],
    },

    "traversal_2hop": {
        "description": "2-hop traversal from a random start node",
        "cypher": """
            MATCH (a:Author {id: $start_id})-[:COLLABORATES]-()-[:COLLABORATES]-(b:Author)
            WHERE b.id <> $start_id
            RETURN DISTINCT b.id AS neighbor_id
        """,
        "aql": """
            FOR v IN 2..2 ANY CONCAT('authors/', @start_id) collaborates
                FILTER v._key != TO_STRING(@start_id)
                RETURN DISTINCT v._key
        """,
        "params": ["start_id"],
    },

    "traversal_3hop": {
        "description": "3-hop traversal from a random start node",
        "cypher": """
            MATCH (a:Author {id: $start_id})-[:COLLABORATES]-()-[:COLLABORATES]-()-[:COLLABORATES]-(b:Author)
            WHERE b.id <> $start_id
            RETURN DISTINCT b.id AS neighbor_id
        """,
        "aql": """
            FOR v IN 3..3 ANY CONCAT('authors/', @start_id) collaborates
                FILTER v._key != TO_STRING(@start_id)
                RETURN DISTINCT v._key
        """,
        "params": ["start_id"],
    },

    "point_lookup": {
        "description": "Fetch a single node by its primary id (exact match)",
        "cypher": """
            MATCH (a:Author {id: $lookup_id})
            RETURN a.id AS id, a.bucket AS bucket
        """,
        "aql": """
            RETURN DOCUMENT(CONCAT('authors/', @lookup_id))
        """,
        "params": ["lookup_id"],
    },

    "indexed_filtered_lookup": {
        "description": (
            "Fetch all nodes matching a secondary indexed property (bucket). "
            "Distinct from point_lookup: this is a range/filter scan on a "
            "secondary index, not an exact-match on the primary key."
        ),
        "cypher": """
            MATCH (a:Author {bucket: $bucket_value})
            RETURN a.id AS id
        """,
        "aql": """
            FOR a IN authors
                FILTER a.bucket == @bucket_value
                RETURN a.id
        """,
        "params": ["bucket_value"],
    },

    "aggregation_relationship_count": {
        "description": (
            "Count all relationships of type COLLABORATES — aggregation "
            "scanning over the relationship type, per assignment section 5.2"
        ),
        "cypher": """
            MATCH ()-[r:COLLABORATES]->()
            RETURN count(r) AS total_relationships
        """,
        "aql": """
            RETURN LENGTH(collaborates)
        """,
        "params": [],
    },

    "aggregation_degree_distribution": {
        "description": (
            "Group-by aggregation: bucket nodes into degree ranges "
            "(low/medium/high) and count nodes per bucket."
        ),
        "cypher": """
            MATCH (a:Author)
            WITH a, COUNT { (a)-[:COLLABORATES]-() } AS degree
            WITH CASE
                WHEN degree < 5 THEN 'low'
                WHEN degree < 20 THEN 'medium'
                ELSE 'high'
            END AS degree_bucket
            RETURN degree_bucket, count(*) AS node_count
        """,
        "aql": """
            FOR a IN authors
                LET degree = LENGTH(FOR v IN 1..1 ANY a collaborates RETURN 1)
                COLLECT degree_bucket = (
                    degree < 5 ? 'low' :
                    degree < 20 ? 'medium' : 'high'
                ) WITH COUNT INTO node_count
                RETURN { degree_bucket, node_count }
        """,
        "params": [],
    },
}


if __name__ == "__main__":
    for name, q in QUERIES.items():
        assert "cypher" in q and "aql" in q, f"{name} is missing a dialect!"
        print(f"{name:35s} | params: {q['params']}")
    print(f"\n{len(QUERIES)} queries defined, all with both Cypher and AQL versions.")
