"""
Quick connectivity test for the self-hosted ArangoDB container.
"""

import os
from dotenv import load_dotenv
from arango import ArangoClient

load_dotenv()

uri = os.environ.get("ARANGO_URI", "http://localhost:8529")
user = os.environ.get("ARANGO_USER", "root")
password = os.environ["ARANGO_PASSWORD"]
db_name = os.environ.get("ARANGO_DB", "benchmark")

print(f"Connecting to ArangoDB at {uri} ...")

client = ArangoClient(hosts=uri)
sys_db = client.db("_system", username=user, password=password)

if not sys_db.has_database(db_name):
    print(f"Database '{db_name}' does not exist yet — creating it.")
    sys_db.create_database(db_name)
else:
    print(f"Database '{db_name}' already exists.")

bench_db = client.db(db_name, username=user, password=password)
cursor = bench_db.aql.execute("RETURN 1")
value = list(cursor)[0]

print("Connection OK:", value)
