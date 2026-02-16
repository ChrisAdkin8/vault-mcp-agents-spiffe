# ---------------------------------------------------------------------------
# Vault GCP secrets backend configuration
# ---------------------------------------------------------------------------

resource "vault_gcp_secret_backend" "gcp" {
  path                      = var.vault_gcp_secrets_mount
  credentials               = base64decode(google_service_account_key.vault.private_key)
  default_lease_ttl_seconds = 300
  max_lease_ttl_seconds     = 300
}

# ---------------------------------------------------------------------------
# Vault GCP Impersonated Accounts
#   These match the accounts referenced in config/settings.yaml:
#     data_agent    -> gcp_impersonated_account: "data-agent-gcp"
#     compute_agent -> gcp_impersonated_account: "compute-agent-gcp"
#
#   Unlike rolesets, impersonated accounts support a configurable token TTL
#   via GCP's generateAccessToken API lifetime field.  Setting ttl = "300"
#   produces genuine 5-minute OAuth2 tokens.
# ---------------------------------------------------------------------------

resource "vault_gcp_secret_impersonated_account" "data_agent" {
  backend               = vault_gcp_secret_backend.gcp.path
  impersonated_account  = "data-agent-gcp"
  service_account_email = google_service_account.data_agent.email
  token_scopes = [
    "https://www.googleapis.com/auth/cloud-platform",
  ]
  ttl = "300"

  depends_on = [
    google_service_account_iam_member.vault_impersonate_data,
  ]
}

resource "vault_gcp_secret_impersonated_account" "compute_agent" {
  backend               = vault_gcp_secret_backend.gcp.path
  impersonated_account  = "compute-agent-gcp"
  service_account_email = google_service_account.compute_agent.email
  token_scopes = [
    "https://www.googleapis.com/auth/compute",
  ]
  ttl = "300"

  depends_on = [
    google_service_account_iam_member.vault_impersonate_compute,
  ]
}
