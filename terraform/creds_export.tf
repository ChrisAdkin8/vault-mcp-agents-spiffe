# ---------------------------------------------------------------------------
# Export AppRole credentials to shared volume
#
# Terraform writes the role_id and secret_id to /creds/ so that
# the Vault Agent sidecar can read them at startup and authenticate
# via AppRole without any manual intervention.
# ---------------------------------------------------------------------------

resource "local_file" "role_id" {
  content  = vault_approle_auth_backend_role.mcp_docker_role.role_id
  filename = "/creds/role_id"
}

resource "local_file" "secret_id" {
  content  = vault_approle_auth_backend_role_secret_id.id.secret_id
  filename = "/creds/secret_id"
}
