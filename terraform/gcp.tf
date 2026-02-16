# ---------------------------------------------------------------------------
# GCP Service Account for Vault
# ---------------------------------------------------------------------------

resource "google_service_account" "vault" {
  account_id   = var.vault_service_account_id
  display_name = "Vault GCP Secrets Engine"
  description  = "Service account used by Vault to manage GCP rolesets and issue short-lived credentials."
  project      = var.gcp_project_id
}

# ---------------------------------------------------------------------------
# IAM roles for Vault's service account
#   - serviceAccountAdmin: Vault creates/deletes SA for each roleset
#   - serviceAccountKeyAdmin: Vault creates/rotates SA keys for rolesets
#   - serviceAccountTokenCreator: Vault generates OAuth2 access tokens
#   - projectIamAdmin: Vault binds IAM roles to roleset service accounts
# ---------------------------------------------------------------------------

resource "google_project_iam_member" "vault_sa_admin" {
  project = var.gcp_project_id
  role    = "roles/iam.serviceAccountAdmin"
  member  = "serviceAccount:${google_service_account.vault.email}"
}

resource "google_project_iam_member" "vault_sa_key_admin" {
  project = var.gcp_project_id
  role    = "roles/iam.serviceAccountKeyAdmin"
  member  = "serviceAccount:${google_service_account.vault.email}"
}

resource "google_project_iam_member" "vault_sa_token_creator" {
  project = var.gcp_project_id
  role    = "roles/iam.serviceAccountTokenCreator"
  member  = "serviceAccount:${google_service_account.vault.email}"
}

resource "google_project_iam_member" "vault_project_iam_admin" {
  project = var.gcp_project_id
  role    = "roles/resourcemanager.projectIamAdmin"
  member  = "serviceAccount:${google_service_account.vault.email}"
}

# ---------------------------------------------------------------------------
# Service account key (used to configure Vault GCP backend)
#   The key material lives only in Terraform state — no file on disk.
# ---------------------------------------------------------------------------

resource "google_service_account_key" "vault" {
  service_account_id = google_service_account.vault.name
}

# ---------------------------------------------------------------------------
# GCP Service Accounts for agents
#   Impersonated accounts require pre-existing service accounts (unlike
#   rolesets which auto-create them).
# ---------------------------------------------------------------------------

resource "google_service_account" "data_agent" {
  account_id   = "data-agent-gcp"
  display_name = "Data Agent (Vault-managed)"
  description  = "Service account impersonated by Vault for data agent operations."
  project      = var.gcp_project_id
}

resource "google_service_account" "compute_agent" {
  account_id   = "compute-agent-gcp"
  display_name = "Compute Agent (Vault-managed)"
  description  = "Service account impersonated by Vault for compute agent operations."
  project      = var.gcp_project_id
}

# ---------------------------------------------------------------------------
# IAM roles on agent service accounts
# ---------------------------------------------------------------------------

resource "google_project_iam_member" "data_agent_storage" {
  project = var.gcp_project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.data_agent.email}"
}

resource "google_project_iam_member" "data_agent_bigquery" {
  project = var.gcp_project_id
  role    = "roles/bigquery.admin"
  member  = "serviceAccount:${google_service_account.data_agent.email}"
}

resource "google_project_iam_member" "compute_agent_compute" {
  project = var.gcp_project_id
  role    = "roles/compute.admin"
  member  = "serviceAccount:${google_service_account.compute_agent.email}"
}

# ---------------------------------------------------------------------------
# Allow Vault's SA to impersonate agent SAs (generate tokens on their behalf)
# ---------------------------------------------------------------------------

resource "google_service_account_iam_member" "vault_impersonate_data" {
  service_account_id = google_service_account.data_agent.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${google_service_account.vault.email}"
}

resource "google_service_account_iam_member" "vault_impersonate_compute" {
  service_account_id = google_service_account.compute_agent.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${google_service_account.vault.email}"
}
