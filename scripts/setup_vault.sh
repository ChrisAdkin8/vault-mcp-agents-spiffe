#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Configures a local Vault dev instance for the vault-mcp-agents project.
#
# Prerequisites:
#   - Vault CLI installed
#   - Vault dev server running (docker compose up -d)
#   - VAULT_ADDR and VAULT_TOKEN exported
#
# Usage:
#   export VAULT_ADDR=http://127.0.0.1:8200
#   export VAULT_TOKEN=dev-root-token
#   bash scripts/setup_vault.sh
# ---------------------------------------------------------------------------
set -euo pipefail

echo "==> Configuring Vault at ${VAULT_ADDR}"

# ---------- 1. Enable userpass auth for humans ----------
echo "--- Enabling userpass auth method"
vault auth enable userpass 2>/dev/null || echo "    (already enabled)"

# ---------- 2. Create policies ----------
echo "--- Writing operator policy"
vault policy write operator-policy - <<'EOF'
# Operator: full access to both GCP impersonated accounts.
# Impersonated account token path (used by hvac: generate_impersonated_account_oauth2_access_token)
path "gcp/impersonated-account/data-agent-gcp/token" {
  capabilities = ["read"]
}
path "gcp/impersonated-account/compute-agent-gcp/token" {
  capabilities = ["read"]
}
EOF

echo "--- Writing analyst policy"
vault policy write analyst-policy - <<'EOF'
# Analyst: read-only access to both GCP impersonated accounts.
path "gcp/impersonated-account/data-agent-gcp/token" {
  capabilities = ["read"]
}
path "gcp/impersonated-account/compute-agent-gcp/token" {
  capabilities = ["read"]
}
EOF

echo "--- Writing viewer policy"
vault policy write viewer-policy - <<'EOF'
# Viewer: minimal GCP access (data agent only).
path "gcp/impersonated-account/data-agent-gcp/token" {
  capabilities = ["read"]
}
EOF

# ---------- 3. Create test users ----------
echo "--- Creating test users"
vault write auth/userpass/users/alice password="alice-pass" policies="operator-policy"
vault write auth/userpass/users/bob   password="bob-pass"   policies="analyst-policy"
vault write auth/userpass/users/carol password="carol-pass"  policies="viewer-policy"

# ---------- 4. GCP secrets engine ----------
# The GCP secrets engine is provisioned by Terraform.
# See terraform/README.md for setup instructions.

echo ""
echo "==> Vault configured.  Test users:"
echo "    alice / alice-pass  (operator)"
echo "    bob   / bob-pass    (analyst)"
echo "    carol / carol-pass  (viewer)"
echo ""
echo "NOTE: Run 'cd terraform && terraform apply' to configure the GCP secrets engine."
echo "See terraform/README.md for details."