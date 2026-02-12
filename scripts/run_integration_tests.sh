#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Run integration tests against the Docker Compose stack.
#
# Usage:
#   ./scripts/run_integration_tests.sh
#
# Prerequisites:
#   - Docker and Docker Compose installed
#   - docker/.env file with VAULT_LICENSE set
# ---------------------------------------------------------------------------

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"

echo "=== Starting Docker Compose stack ==="
docker compose --env-file docker/.env up -d --build

echo "=== Waiting for services to be healthy ==="
for service in vault data-mcp-server compute-mcp-server; do
    echo "  Waiting for $service..."
    timeout 120 bash -c "
        until docker compose ps $service | grep -q healthy; do
            sleep 2
        done
    " || { echo "FAILED: $service did not become healthy"; docker compose logs $service; exit 1; }
    echo "  $service is healthy."
done

echo ""
echo "=== Running integration tests ==="
python -m pytest tests/integration/ -v --run-integration
TEST_EXIT=$?

echo ""
echo "=== Tearing down Docker Compose stack ==="
docker compose --env-file docker/.env down

exit $TEST_EXIT
