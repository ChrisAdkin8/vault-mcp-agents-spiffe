output "vault_service_account_email" {
  description = "Email of the GCP service account created for Vault."
  value       = google_service_account.vault.email
}

output "gcp_secrets_mount_path" {
  description = "Vault mount path for the GCP secrets engine."
  value       = vault_gcp_secret_backend.gcp.path
}
