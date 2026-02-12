#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Vault Enterprise SPIFFE Configuration
# ---------------------------------------------------------------------------
# This script enables and configures the SPIFFE auth method in Vault
# Enterprise.  It is designed to run AFTER setup_vault.sh (which handles
# userpass, policies, and test users).
#
# Prerequisites:
#   - Vault Enterprise 1.21+ running with a valid license
#   - VAULT_ADDR and VAULT_TOKEN exported
#   - The setup_vault.sh script has already been run
# ---------------------------------------------------------------------------

set -euo pipefail

echo "=== Vault Enterprise: SPIFFE Auth Configuration ==="

# ---------- Enable SPIFFE auth method ----------
echo "Enabling SPIFFE auth method..."
vault auth enable -path=spiffe spiffe 2>/dev/null || echo "  (already enabled)"

# ---------- Configure trust domain ----------
echo "Configuring SPIFFE trust domain..."
vault write auth/spiffe/config \
    trust_domain="vault-mcp-demo"

# ---------- Create roles for agent workloads ----------
# Each role maps a SPIFFE ID to a set of Vault policies.
# The token_ttl here is the Vault token TTL, not the GCP token TTL.

echo "Creating SPIFFE role: data-agent..."
vault write auth/spiffe/roles/data-agent \
    spiffe_id_allowed="spiffe://vault-mcp-demo/agent/data_agent" \
    token_policies="operator-policy" \
    token_ttl="1h" \
    token_max_ttl="4h"

echo "Creating SPIFFE role: compute-agent..."
vault write auth/spiffe/roles/compute-agent \
    spiffe_id_allowed="spiffe://vault-mcp-demo/agent/compute_agent" \
    token_policies="operator-policy" \
    token_ttl="1h" \
    token_max_ttl="4h"

echo ""
echo "=== SPIFFE auth configuration complete ==="
echo ""
echo "Trust domain:  vault-mcp-demo"
echo "Roles:"
echo "  data-agent     → spiffe://vault-mcp-demo/agent/data_agent"
echo "  compute-agent  → spiffe://vault-mcp-demo/agent/compute_agent"
echo ""
echo "Workloads can now authenticate using their X.509 SVIDs."
