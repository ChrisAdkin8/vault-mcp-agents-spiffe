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

# Template to render the SVID (certificate)
template {
  destination = "/etc/mcp/certs/server.crt"
  contents    = <<EOH
{{- with secret "pki/issue/mcp-server" "common_name=mcp-server" "uri_sans=spiffe://my-trust-domain/ns/default/sa/mcp" -}}
{{ .Data.certificate }}
{{- end }}
EOH
}

# Template to render the private key
template {
  destination = "/etc/mcp/certs/server.key"
  contents    = <<EOH
{{- with secret "pki/issue/mcp-server" "common_name=mcp-server" "uri_sans=spiffe://my-trust-domain/ns/default/sa/mcp" -}}
{{ .Data.private_key }}
{{- end }}
EOH
}

# Template to render the CA chain
template {
  destination = "/etc/mcp/certs/ca.crt"
  contents    = <<EOH
{{- with secret "pki/issue/mcp-server" "common_name=mcp-server" "uri_sans=spiffe://my-trust-domain/ns/default/sa/mcp" -}}
{{ .Data.issuing_ca }}
{{- end }}
EOH
}
