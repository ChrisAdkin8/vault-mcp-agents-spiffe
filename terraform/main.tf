# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

provider "vault" {
  address = var.vault_address
  token   = var.vault_token
}

provider "local" {
  # Used to write AppRole credentials to a shared volume
  # so that Vault Agent can read them at startup.
}
