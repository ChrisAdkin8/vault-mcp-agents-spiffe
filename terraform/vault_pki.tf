# ---------------------------------------------------------------------------
# PKI secrets engine for SPIFFE SVIDs
# ---------------------------------------------------------------------------

resource "vault_mount" "pki" {
  path        = "pki"
  type        = "pki"
  description = "PKI engine for MCP Server SVIDs"

  default_lease_ttl_seconds = 3600
  max_lease_ttl_seconds     = 87600 * 3600
}

# Root CA (internal)
resource "vault_pki_secret_backend_root_cert" "mcp_root" {
  backend              = vault_mount.pki.path
  type                 = "internal"
  common_name          = "MCP Root CA"
  ttl                  = "87600h"
  format               = "pem"
  private_key_format   = "der"
  key_type             = "rsa"
  key_bits             = 4096
  exclude_cn_from_sans = true
}

# Issuing / CRL URLs (required for certificate validation)
resource "vault_pki_secret_backend_config_urls" "config" {
  backend                 = vault_mount.pki.path
  issuing_certificates    = ["http://vault:8200/v1/pki/ca"]
  crl_distribution_points = ["http://vault:8200/v1/pki/crl"]
}

# SPIFFE-compliant PKI role
resource "vault_pki_secret_backend_role" "mcp_server" {
  backend          = vault_mount.pki.path
  name             = "mcp-server"
  ttl              = 3600
  max_ttl          = 86400
  allow_ip_sans    = true
  key_type         = "rsa"
  key_bits         = 2048
  allowed_domains  = ["mcp-server", "localhost", "svc.cluster.local"]
  allow_subdomains = true

  # SPIFFE URI SANs
  allowed_uri_sans = ["spiffe://my-trust-domain/ns/*/sa/*"]

  # CN enforcement disabled because SPIFFE relies on SANs
  enforce_hostnames = false
  allow_any_name    = false
}
