variable "gcp_project_id" {
  description = "GCP project ID where service accounts will be created."
  type        = string
}

variable "gcp_region" {
  description = "Default GCP region for resources."
  type        = string
  default     = "us-central1"
}

variable "vault_service_account_id" {
  description = "ID (not email) for the GCP service account created for Vault."
  type        = string
  default     = "vault-gcp-secrets"
}
