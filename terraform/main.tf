# ---------------------------------------------------------------------------
# Provider — GCP only
#
# Vault configuration is now handled by scripts/vault_init.sh (run
# automatically by the vault-init container in docker-compose.yaml).
# ---------------------------------------------------------------------------

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}
