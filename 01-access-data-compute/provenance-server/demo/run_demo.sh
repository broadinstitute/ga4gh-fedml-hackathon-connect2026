#!/usr/bin/env bash
# run_demo.sh — End-to-end demo of the GA4GH Provenance Server federation
#
# Prerequisites:
#   - Docker and docker-compose installed
#   - curl and python3 available on PATH
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

NODE_A="http://localhost:8001"
NODE_B="http://localhost:8002"
WORKFLOW_GATK="trs://dockstore.org/workflow/github.com/broadinstitute/gatk-workflows/broad-prod-wgs-germline-snps-indels"

echo "=== GA4GH Provenance Server Demo ==="
echo ""

# ------------------------------------------------------------------
# 1. Start the two nodes
# ------------------------------------------------------------------
echo ">>> Starting nodes with docker-compose ..."
docker compose up --build --detach

# Wait for both nodes to be ready
echo ">>> Waiting for nodes to be ready ..."
for port in 8001 8002; do
  for _ in $(seq 1 20); do
    if curl -sf "http://localhost:${port}/provenance/info" > /dev/null 2>&1; then
      echo "    Node on port ${port} is up."
      break
    fi
    sleep 2
  done
done

# ------------------------------------------------------------------
# 2. Seed demo data
# ------------------------------------------------------------------
echo ""
echo ">>> Seeding demo data ..."
python3 seed_data.py

# ------------------------------------------------------------------
# 3. Local query on Node A
# ------------------------------------------------------------------
echo ""
echo ">>> Querying Node A for GATK records ..."
curl -s -X POST "${NODE_A}/provenance/query" \
  -H "Content-Type: application/json" \
  -d "{\"workflow_id\": \"${WORKFLOW_GATK}\"}" | python3 -m json.tool

# ------------------------------------------------------------------
# 4. Federated query through Node A (reaches Node B too)
# ------------------------------------------------------------------
echo ""
echo ">>> Federated query (Node A fans out to Node B) ..."
curl -s -X POST "${NODE_A}/federated/query" \
  -H "Content-Type: application/json" \
  -d "{\"workflow_id\": \"${WORKFLOW_GATK}\"}" | python3 -m json.tool

# ------------------------------------------------------------------
# 5. Export as RO-Crate
# ------------------------------------------------------------------
echo ""
echo ">>> Exporting GATK provenance from Node A as RO-Crate zip ..."
curl -s -X POST "${NODE_A}/provenance/query/export" \
  -H "Content-Type: application/json" \
  -d "{\"workflow_id\": \"${WORKFLOW_GATK}\"}" \
  -o /tmp/provenance-crate.zip
echo "    Saved to /tmp/provenance-crate.zip"
unzip -l /tmp/provenance-crate.zip

# ------------------------------------------------------------------
# 6. Cleanup
# ------------------------------------------------------------------
echo ""
echo ">>> Demo complete. Nodes are still running."
echo "    Node A docs: ${NODE_A}/docs"
echo "    Node B docs: ${NODE_B}/docs"
echo ""
echo "    To stop: docker compose down"
