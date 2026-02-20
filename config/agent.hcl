pid_file = "/var/run/vault-agent-pid"

vault {
  address = "http://vault:8200"
}

auto_auth {
  method "approle" {
    mount_path = "auth/approle"
    config = {
      role_id_file_path                   = "/vault/creds/role_id"
      secret_id_file_path                 = "/vault/creds/secret_id"
      remove_secret_id_file_after_reading = false
    }
  }

  sink "file" {
    config = {
      path = "/tmp/agent_token"
    }
  }
}

# Single template using pkiCert to issue ONE certificate and write all three
# files atomically.  This prevents the cert/key mismatch that occurs when
# three separate template blocks each call pki/issue independently (each call
# generates a different key pair).
template {
  destination = "/tmp/vault-agent-cert-render-status"
  contents    = <<EOH
{{ with pkiCert "pki/issue/mcp-server" "common_name=mcp-server" "uri_sans=spiffe://my-trust-domain/ns/default/sa/mcp" }}
{{ .Cert | writeToFile "/etc/mcp/certs/server.crt" "" "" "0644" }}
{{ .Key | writeToFile "/etc/mcp/certs/server.key" "" "" "0600" }}
{{ .CA | writeToFile "/etc/mcp/certs/ca.crt" "" "" "0644" }}
{{ .Cert }}
{{ end }}
EOH
}
