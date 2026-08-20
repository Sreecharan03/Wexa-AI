#!/bin/bash
set -e
echo "Configuring FalkorDB persistence..."
docker exec bench-falkordb redis-cli CONFIG SET appendonly yes
docker exec bench-falkordb redis-cli CONFIG SET save "60 1"
echo "Verifying config took effect:"
docker exec bench-falkordb redis-cli CONFIG GET appendonly
docker exec bench-falkordb redis-cli CONFIG GET save
echo "Forcing an immediate save:"
docker exec bench-falkordb redis-cli BGSAVE
sleep 1
echo "Data directory now:"
docker exec bench-falkordb ls -la /var/lib/falkordb/data
