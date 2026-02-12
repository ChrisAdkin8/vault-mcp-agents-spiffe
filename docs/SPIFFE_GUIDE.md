# SPIFFE Workload Identity Guide

This guide explains how SPIFFE (Secure Production Identity Framework for Everyone) is used in this project to provide cryptographic workload identity for MCP server containers.

## What is SPIFFE?

SPIFFE is an open standard for securely identifying software systems in dynamic and heterogeneous environments. Instead of relying on network-level trust (IP addresses, firewall rules), SPIFFE gives each workload a cryptographic identity document called an **SVID** (SPIFFE Verifiable Identity Document).

Key concepts:

| Concept | Description |
|---------|-------------|
| **SPIFFE ID** | A URI that uniquely identifies a workload: `spiffe://trust-domain/path` |
| **SVID** | An X.509 certificate (or JWT) that proves a workload's SPIFFE ID |
| **Trust Domain** | A security boundary (like a Kerberos realm): `vault-mcp-demo` |
| **Workload API** | A local Unix socket that workloads use to fetch their SVIDs |

## Why SPIFFE in this project?

Without SPIFFE, an MCP server container has no way to prove its identity to Vault. It would need a static Vault token or AppRole credentials baked into the container image — exactly the kind of long-lived secret we are trying to avoid.

With SPIFFE:

1. Each MCP server container receives an X.509 SVID from the SPIRE agent
2. The container presents this SVID to Vault's SPIFFE auth method
3. Vault verifies the certificate chain and issues a short-lived Vault token
4. No static secrets exist in the container image or environment

This adds a **workload identity layer** to the existing defence-in-depth model:

```
┌─────────────────────────────────────────────────┐
│  Layer 1: Human Identity                        │
│  Vault userpass → Session (token + role)         │
├─────────────────────────────────────────────────┤
│  Layer 2: Workload Identity (SPIFFE)            │
│  X.509 SVID → WorkloadSession (Vault token)     │
├─────────────────────────────────────────────────┤
│  Layer 3: Application Policy                    │
│  capabilities.yaml → (role, agent) → tools      │
└─────────────────────────────────────────────────┘
```

## Trust domain configuration

This project uses the trust domain `vault-mcp-demo`. Each agent container has a SPIFFE ID within this domain:

| Container | SPIFFE ID |
|-----------|-----------|
| data-mcp-server | `spiffe://vault-mcp-demo/agent/data_agent` |
| compute-mcp-server | `spiffe://vault-mcp-demo/agent/compute_agent` |

These are mapped to agent IDs in `policies/capabilities.yaml`:

```yaml
trust_domain: "vault-mcp-demo"
spiffe_identity_map:
  "spiffe://vault-mcp-demo/agent/data_agent": "data_agent"
  "spiffe://vault-mcp-demo/agent/compute_agent": "compute_agent"
```

## Vault Enterprise SPIFFE auth method

### Prerequisites

- **Vault Enterprise 1.21+** with a valid license
- The SPIFFE auth method is an Enterprise-only feature

### How it works

Vault Enterprise's SPIFFE auth method accepts X.509 SVIDs for authentication. When a workload presents its SVID:

1. Vault verifies the certificate was issued by the trusted SPIRE CA
2. Vault extracts the SPIFFE ID from the certificate's SAN (Subject Alternative Name)
3. Vault matches the SPIFFE ID against configured roles
4. Vault issues a token with the policies defined for that role

### Roles configured by this project

The `scripts/setup_vault_enterprise.sh` script creates two roles:

```bash
# Data agent role
vault write auth/spiffe/roles/data-agent \
    spiffe_id_allowed="spiffe://vault-mcp-demo/agent/data_agent" \
    token_policies="operator-policy" \
    token_ttl="1h" \
    token_max_ttl="4h"

# Compute agent role
vault write auth/spiffe/roles/compute-agent \
    spiffe_id_allowed="spiffe://vault-mcp-demo/agent/compute_agent" \
    token_policies="operator-policy" \
    token_ttl="1h" \
    token_max_ttl="4h"
```

Each role:
- Allows a specific SPIFFE ID
- Grants the `operator-policy` (which allows access to the GCP secrets engine)
- Issues tokens with a 1-hour TTL (max 4 hours)

## SpiffeAuthenticator

The `SpiffeAuthenticator` class (`src/vault_mcp_agents/auth/spiffe_authenticator.py`) handles SVID retrieval and Vault authentication:

```python
from vault_mcp_agents.auth.spiffe_authenticator import SpiffeAuthenticator

auth = SpiffeAuthenticator(
    vault_addr="http://vault:8200",
    trust_domain="vault-mcp-demo",
    spiffe_auth_mount="spiffe",
)

# Fetches SVID from SPIRE agent, authenticates to Vault
session = auth.authenticate_workload()
print(session.spiffe_id)     # spiffe://vault-mcp-demo/agent/data_agent
print(session.vault_token)   # s.xxxxx (short-lived Vault token)
```

### How SVID retrieval works

The authenticator uses the `py-spiffe` library to communicate with the local SPIRE agent via the Workload API:

1. The SPIRE agent runs as a sidecar or DaemonSet
2. It exposes a Unix domain socket (default: `/run/spire/sockets/agent.sock`)
3. The `WorkloadApiClient` connects to this socket
4. The SPIRE agent attests the workload (verifies it should receive the SVID)
5. The workload receives its X.509 certificate and private key

### Configuration

In `config/settings.yaml`:

```yaml
spiffe:
  enabled: false         # Set to true in container deployments
  trust_domain: "vault-mcp-demo"
  auth_mount: "spiffe"
  workload_api_endpoint: "unix:///run/spire/sockets/agent.sock"
```

The `SPIFFE_ENDPOINT_SOCKET` environment variable can also be used to set the Workload API endpoint (this is the standard SPIFFE convention).

## Setting up SPIRE (production)

For a production deployment, you need a SPIRE server and agent:

### 1. Deploy SPIRE server

The SPIRE server manages the CA and issues SVIDs. In Kubernetes, deploy it as a StatefulSet. In Docker Compose, run it as a service with a persistent volume for the CA keys.

### 2. Deploy SPIRE agent

The SPIRE agent runs on each node and exposes the Workload API socket. Workloads connect to this socket to retrieve their SVIDs.

### 3. Register workload entries

Create SPIRE registration entries for each MCP server:

```bash
# Register data agent
spire-server entry create \
    -spiffeID spiffe://vault-mcp-demo/agent/data_agent \
    -parentID spiffe://vault-mcp-demo/node/docker-node \
    -selector docker:label:com.example.service:data-mcp-server

# Register compute agent
spire-server entry create \
    -spiffeID spiffe://vault-mcp-demo/agent/compute_agent \
    -parentID spiffe://vault-mcp-demo/node/docker-node \
    -selector docker:label:com.example.service:compute-mcp-server
```

### 4. Configure Vault trust

Upload the SPIRE server's CA certificate to Vault so it can verify SVIDs:

```bash
vault write auth/spiffe/config \
    trust_domain="vault-mcp-demo" \
    ca_cert=@/path/to/spire-ca.pem
```

## Troubleshooting

### "SPIFFE auth method not found"

The SPIFFE auth method is only available in Vault Enterprise 1.21+. Verify:

```bash
vault version  # Must show Enterprise
vault auth list  # Should include "spiffe/"
```

### "No SVID available"

The SPIRE agent is not running or the workload is not registered:

1. Check the SPIRE agent is running: `spire-agent healthcheck`
2. Check registration entries: `spire-server entry show`
3. Verify the socket path matches `SPIFFE_ENDPOINT_SOCKET`

### "Certificate verification failed"

The SPIRE CA certificate is not configured in Vault:

```bash
vault read auth/spiffe/config
# Verify ca_cert is set and matches the SPIRE server CA
```

### "Role not found for SPIFFE ID"

The SPIFFE ID in the SVID does not match any configured Vault role:

```bash
vault list auth/spiffe/roles
vault read auth/spiffe/roles/data-agent
# Verify spiffe_id_allowed matches the workload's SPIFFE ID exactly
```

### SPIFFE disabled in local development

SPIFFE is disabled by default (`spiffe.enabled: false` in settings.yaml). In local development with stdio transport, workloads authenticate using the human's Vault token passed through the `IdentityContext`. SPIFFE is only needed in containerised deployments where workloads need their own identity.
