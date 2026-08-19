"""
Quick connectivity test for the self-hosted FalkorDB container.

Run this standalone before wiring FalkorDB into config.py's driver layer —
isolates "can we even talk to it" from "does our abstraction layer work."
"""

import os
from dotenv import load_dotenv
from falkordb import FalkorDB

load_dotenv()

host = os.environ.get("FALKORDB_HOST", "localhost")
port = int(os.environ.get("FALKORDB_PORT", 6380))

print(f"Connecting to FalkorDB at {host}:{port} ...")

db = FalkorDB(host=host, port=port)

graph = db.select_graph("benchmark")

result = graph.query("RETURN 1 AS test")
value = result.result_set[0][0]

print("Connection OK:", value)
