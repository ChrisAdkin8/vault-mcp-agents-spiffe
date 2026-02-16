# ---------------------------------------------------------------------------
# Vault policy (shared by both AppRole and Kubernetes auth)
# ---------------------------------------------------------------------------

resource "vault_policy" "mcp_policy" {
  name = "mcp-policy"

  policy = <<EOT
# Allow requesting the cert
path "pki/issue/mcp-server" {
  capabilities = ["create", "update"]
}
EOT
}

# ---------------------------------------------------------------------------
# AppRole auth backend
# ---------------------------------------------------------------------------

resource "vault_auth_backend" "approle" {
  type = "approle"
}

resource "vault_approle_auth_backend_role" "mcp_docker_role" {
  backend        = vault_auth_backend.approle.path
  role_name      = "mcp-role"
  token_policies = [vault_policy.mcp_policy.name]
}

resource "vault_approle_auth_backend_role_secret_id" "id" {
  backend   = vault_auth_backend.approle.path
  role_name = vault_approle_auth_backend_role.mcp_docker_role.role_name
}

# ---------------------------------------------------------------------------
# Kubernetes auth backend
# ---------------------------------------------------------------------------

resource "vault_auth_backend" "kubernetes" {
  type = "kubernetes"
}

resource "vault_kubernetes_auth_backend_config" "k8s_config" {
  backend         = vault_auth_backend.kubernetes.path
  kubernetes_host = "https://kubernetes.default.svc:443"
  # In a real setup, you might fetch these from a data source or var
  # kubernetes_ca_cert = ...
  # token_reviewer_jwt = ...
}

resource "vault_kubernetes_auth_backend_role" "mcp_k8s_role" {
  backend                          = vault_auth_backend.kubernetes.path
  role_name                        = "mcp-server"
  bound_service_account_names      = ["mcp-sa"]
  bound_service_account_namespaces = ["default"]
  token_policies                   = [vault_policy.mcp_policy.name]
  token_ttl                        = 3600
}
