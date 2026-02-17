# ---------------------------------------------------------------------------
# GCP outputs
# ---------------------------------------------------------------------------

output "vault_service_account_email" {
  description = "Email of the GCP service account created for Vault."
  value       = google_service_account.vault.email
}

output "data_agent_service_account_email" {
  description = "Email of the data agent GCP service account."
  value       = google_service_account.data_agent.email
}

output "compute_agent_service_account_email" {
  description = "Email of the compute agent GCP service account."
  value       = google_service_account.compute_agent.email
}

output "vault_sa_key_base64" {
  description = "Base64-encoded GCP SA key for Vault. Decode and save to a file for use with docker-compose."
  value       = google_service_account_key.vault.private_key
  sensitive   = true
}
