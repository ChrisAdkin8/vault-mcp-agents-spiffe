variable "gcp_project_id" {
  description = "GCP project ID where the Vault service account will be created."
  type        = string
}

variable "gcp_region" {
  description = "Default GCP region for resources."
  type        = string
  default     = "us-central1"
}

variable "vault_address" {
  description = "Vault server address."
  type        = string
  default     = "http://127.0.0.1:8200"
}

variable "vault_token" {
  description = "Vault token for provider authentication (root token for dev)."
  type        = string
  sensitive   = true
  default     = "dev-root-token"
}

variable "vault_gcp_secrets_mount" {
  description = "Mount path for the Vault GCP secrets engine."
  type        = string
  default     = "gcp"
}

variable "vault_service_account_id" {
  description = "ID (not email) for the GCP service account created for Vault."
  type        = string
  default     = "vault-gcp-secrets"
}
