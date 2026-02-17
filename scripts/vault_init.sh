#!/bin/sh
# ---------------------------------------------------------------------------
# Comprehensive Vault initialisation for the vault-mcp-agents project.
#
# This script configures a dev-mode Vault instance with everything needed
# for the Docker Compose stack:
#   1. PKI secrets engine (SPIFFE SVIDs)
#   2. Vault policy for certificate issuance
#   3. AppRole auth backend + credential export
#   4. GCP secrets engine with 5-minute impersonated accounts (conditional)
#   5. Userpass auth + test users with role-scoped policies
#
# Prerequisites (provided by docker-compose environment):
#   - VAULT_ADDR and VAULT_TOKEN set
#   - /creds/ volume mounted (for AppRole credential export)
#   - /gcp/sa-key.json mounted (optional, for GCP secrets engine)
#   - DATA_AGENT_SA_EMAIL and COMPUTE_AGENT_SA_EMAIL set (if using GCP)
#
# Usage (run automatically by docker-compose vault-init service):
#   sh /scripts/vault_init.sh
# ---------------------------------------------------------------------------
set -eu

echo "==> Waiting for Vault to be ready at ${VAULT_ADDR}..."
until vault status >/dev/null 2>&1; do
  sleep 1
done
echo "==> Vault is ready."

# ===== 1. PKI Secrets Engine (SPIFFE SVIDs) ================================

echo "--- Enabling PKI secrets engine"
vault secrets enable \
    -path=pki \
    -default-lease-ttl=3600s \
    -max-lease-ttl=315360000s \
    pki 2>/dev/null || echo "    (already enabled)"

echo "--- Generating internal root CA"
vault write -field=certificate pki/root/generate/internal \
    common_name="MCP Root CA" \
    ttl=87600h \
    key_type=rsa \
    key_bits=4096 \
    exclude_cn_from_sans=true > /dev/null 2>&1 || echo "    (root CA may already exist)"

echo "--- Configuring PKI issuing and CRL URLs"
vault write pki/config/urls \
    issuing_certificates="http://vault:8200/v1/pki/ca" \
    crl_distribution_points="http://vault:8200/v1/pki/crl"

echo "--- Creating mcp-server PKI role (SPIFFE-compliant)"
vault write pki/roles/mcp-server \
    ttl=3600 \
    max_ttl=86400 \
    allow_ip_sans=true \
    key_type=rsa \
    key_bits=2048 \
    allowed_domains="mcp-server,localhost,svc.cluster.local" \
    allow_subdomains=true \
    allowed_uri_sans="spiffe://my-trust-domain/ns/*/sa/*" \
    enforce_hostnames=false \
    allow_any_name=false

# ===== 2. Vault Policy =====================================================

echo "--- Writing mcp-policy"
vault policy write mcp-policy - <<'EOF'
# Allow requesting X.509 certificates from the PKI engine
path "pki/issue/mcp-server" {
  capabilities = ["create", "update"]
}
EOF

# ===== 3. AppRole Auth Backend ==============================================

echo "--- Enabling AppRole auth"
vault auth enable approle 2>/dev/null || echo "    (already enabled)"

echo "--- Creating mcp-role"
vault write auth/approle/role/mcp-role \
    token_policies="mcp-policy"

echo "--- Exporting AppRole credentials to /creds/"
ROLE_ID=$(vault read -field=role_id auth/approle/role/mcp-role/role-id)
SECRET_ID=$(vault write -field=secret_id -f auth/approle/role/mcp-role/secret-id)

printf '%s' "$ROLE_ID"  > /creds/role_id
printf '%s' "$SECRET_ID" > /creds/secret_id

echo "    role_id written to /creds/role_id"
echo "    secret_id written to /creds/secret_id"

# ===== 4. GCP Secrets Engine (conditional) ==================================

GCP_SA_KEY_FILE="${GCP_SA_KEY_FILE:-/gcp/sa-key.json}"

if [ -s "$GCP_SA_KEY_FILE" ]; then
    echo "--- Enabling GCP secrets engine"
    vault secrets enable \
        -path=gcp \
        -default-lease-ttl=300s \
        -max-lease-ttl=300s \
        gcp 2>/dev/null || echo "    (already enabled)"

    echo "--- Configuring GCP secrets engine with SA credentials"
    vault write gcp/config \
        credentials=@"${GCP_SA_KEY_FILE}" \
        ttl=300 \
        max_ttl=300

    echo "--- Creating data-agent-gcp impersonated account (5-min TTL)"
    vault write gcp/impersonated-account/data-agent-gcp \
        service_account_email="${DATA_AGENT_SA_EMAIL}" \
        token_scopes="https://www.googleapis.com/auth/cloud-platform" \
        ttl="300"

    echo "--- Creating compute-agent-gcp impersonated account (5-min TTL)"
    vault write gcp/impersonated-account/compute-agent-gcp \
        service_account_email="${COMPUTE_AGENT_SA_EMAIL}" \
        token_scopes="https://www.googleapis.com/auth/compute" \
        ttl="300"

    echo "    GCP secrets engine configured with 5-minute token TTL"
else
    echo "--- Skipping GCP secrets engine (no SA key file at ${GCP_SA_KEY_FILE})"
    echo "    To enable, set GCP_SA_KEY_FILE in docker/.env"
fi

# ===== 5. Userpass Auth + Test Users ========================================

echo "--- Enabling userpass auth method"
vault auth enable userpass 2>/dev/null || echo "    (already enabled)"

echo "--- Writing operator policy"
vault policy write operator-policy - <<'EOF'
# Operator: full access to both GCP impersonated accounts.
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

echo "--- Creating test users"
vault write auth/userpass/users/alice password="alice-pass" policies="operator-policy"
vault write auth/userpass/users/bob   password="bob-pass"   policies="analyst-policy"
vault write auth/userpass/users/carol password="carol-pass"  policies="viewer-policy"

# ===== Done =================================================================

echo ""
echo "==> Vault initialisation complete."
echo "    PKI engine:    pki/ (root CA + mcp-server role)"
echo "    AppRole auth:  auth/approle/role/mcp-role"
echo "    Credentials:   /creds/role_id, /creds/secret_id"
if [ -s "$GCP_SA_KEY_FILE" ]; then
echo "    GCP engine:    gcp/ (data-agent-gcp, compute-agent-gcp — 5-min TTL)"
fi
echo "    Userpass auth: alice (operator), bob (analyst), carol (viewer)"
