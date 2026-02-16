# Configuration Reference

This document provides a complete reference for all configuration files in the project.

## config/settings.yaml

The main configuration file controls Vault connectivity, agent definitions, MCP server transports, LLM provider selection, GCP project settings, SPIFFE identity, and audit logging.

### `vault` — Vault connection settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `address` | string | `http://127.0.0.1:8200` | Vault server URL. Use `https://` for production. |
| `namespace` | string | `""` | Vault Enterprise namespace. Leave empty for OSS. |
| `auth_method` | string | `userpass` | Human authentication method. Options: `userpass`, `ldap`, `oidc`. |
| `gcp_secrets_mount` | string | `gcp` | Mount path for the Vault GCP secrets engine. |
| `agent_approle_mount` | string | `approle` | Mount path for the Vault AppRole auth method. |

**Example:**

```yaml
vault:
  address: "http://127.0.0.1:8200"
  namespace: ""
  auth_method: "userpass"
  gcp_secrets_mount: "gcp"
  agent_approle_mount: "approle"
```

### `agents` — Agent definitions

Each agent maps to an MCP server target and a GCP impersonated account.

| Key | Type | Description |
|-----|------|-------------|
| `description` | string | Human-readable description of the agent's purpose. |
| `mcp_server` | string | Key in the `mcp_servers` section that this agent connects to. |
| `vault_role` | string | Vault AppRole role name for the agent. |
| `gcp_impersonated_account` | string | Name of the Vault GCP impersonated account to use for GCP token generation. |

**Example:**

```yaml
agents:
  data_agent:
    description: "Handles GCS and BigQuery operations"
    mcp_server: "data_server"
    vault_role: "data-agent-role"
    gcp_impersonated_account: "data-agent-gcp"

  compute_agent:
    description: "Handles GCE instance and infrastructure operations"
    mcp_server: "compute_server"
    vault_role: "compute-agent-role"
    gcp_impersonated_account: "compute-agent-gcp"
```

### `mcp_servers` — MCP server endpoints

Each MCP server supports two transports. The `transport` field selects which mode is active.

| Key | Type | Description |
|-----|------|-------------|
| `transport` | string | `"stdio"` for local development, `"http"` for containerised deployment. |
| `command` | string | Python interpreter to use (stdio mode only). |
| `args` | list | Arguments to pass to the command (stdio mode only). |
| `url` | string | Full URL to the MCP endpoint (HTTP mode only). |

**Example:**

```yaml
mcp_servers:
  data_server:
    transport: "stdio"
    command: "python"
    args: ["-m", "vault_mcp_agents.mcp.data_server"]
    url: "http://data-mcp-server:8001/mcp"

  compute_server:
    transport: "stdio"
    command: "python"
    args: ["-m", "vault_mcp_agents.mcp.compute_server"]
    url: "http://compute-mcp-server:8002/mcp"
```

### `llm` — LLM provider configuration

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `provider` | string | `anthropic` | LLM provider. Options: `anthropic`, `openai`. |
| `model` | string | `claude-sonnet-4-20250514` | Model identifier. |
| `temperature` | float | `0.0` | Sampling temperature (0.0 = deterministic). |
| `api_key` | string | *(none)* | API key. Prefer environment variables instead. |

The API key is resolved in this order:
1. `api_key` field in settings.yaml (not recommended for production)
2. `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` environment variable

**Example:**

```yaml
llm:
  provider: "anthropic"
  model: "claude-sonnet-4-20250514"
  temperature: 0.0
```

### `gcp` — GCP project defaults

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `project_id` | string | *(required)* | GCP project ID. Must match `terraform.tfvars`. |
| `region` | string | `us-central1` | Default GCP region. |

This is required because OAuth2 access tokens (unlike service account key files) do not carry project metadata. The project ID is passed through the `IdentityContext` to every GCS, BigQuery, and Compute client call.

**Example:**

```yaml
gcp:
  project_id: "my-gcp-project-123"
  region: "us-central1"
```

### `vault_agent` — Vault Agent sidecar (containerised deployment)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `cert_dir` | string | `/etc/mcp/certs` | Directory where Vault Agent writes X.509 SVIDs. |
| `trust_domain` | string | `my-trust-domain` | SPIFFE trust domain used in URI SANs. |

In containerised deployments, the Vault Agent sidecar authenticates via AppRole and renders X.509 SVIDs with SPIFFE URI SANs to the certificate directory. MCP servers detect these certificates and enable mTLS automatically.

In local development (stdio transport), no certificates are needed — workloads use the human's Vault token.

**Example:**

```yaml
vault_agent:
  cert_dir: "/etc/mcp/certs"
  trust_domain: "my-trust-domain"
```

### `audit` — Audit logging

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | `true` | Enable audit event emission. |
| `log_file` | string | `""` | Path to a file for JSON audit events. Empty = disabled. |
| `log_to_stdout` | bool | `true` | Emit audit events to stdout. |

**Example:**

```yaml
audit:
  enabled: true
  log_file: "audit.log"
  log_to_stdout: true
```

---

## policies/capabilities.yaml

The policy file defines access control rules mapping `(human_role, agent_id)` pairs to allowed MCP tools. It is loaded by the `PolicyEngine` at startup.

### Top-level fields

| Key | Type | Description |
|-----|------|-------------|
| `trust_domain` | string | SPIFFE trust domain name (used for SPIFFE ID mapping). |
| `spiffe_identity_map` | map | Maps SPIFFE IDs to agent IDs for policy resolution. |
| `roles` | map | Per-role access control definitions. |

### `spiffe_identity_map`

Maps SPIFFE URIs to the agent ID used for policy lookup. This allows `PolicyEngine.resolve_by_spiffe_id()` to resolve policies for workload-authenticated containers.

```yaml
spiffe_identity_map:
  "spiffe://vault-mcp-demo/agent/data_agent": "data_agent"
  "spiffe://vault-mcp-demo/agent/compute_agent": "compute_agent"
```

### `roles`

Each role contains:

| Key | Type | Description |
|-----|------|-------------|
| `vault_policy` | string | The Vault policy name that maps to this role. |
| `agents` | map | Per-agent tool allowlists and TTL. |

Each agent entry within a role:

| Key | Type | Description |
|-----|------|-------------|
| `allowed_tools` | list | MCP tool names this identity pair may invoke. |
| `max_gcp_token_ttl` | string | Maximum GCP token TTL (e.g. `"5m"`, `"1h"`, `"300"`). |

### Built-in roles

| Role | Vault Policy | Data Agent Tools | Compute Agent Tools |
|------|-------------|-----------------|-------------------|
| `operator` | `operator-policy` | All 7 tools (list, read, write, delete, query, list datasets, create dataset) | All 6 tools (list, get, start, stop, create, delete) |
| `analyst` | `analyst-policy` | 4 read-only tools (list, read, query, list datasets) | 2 read-only tools (list, get) |
| `viewer` | `viewer-policy` | 3 minimal tools (list, read, list datasets) | 1 tool (list) |

### TTL format

The `max_gcp_token_ttl` field accepts Vault-style duration strings:

| Format | Example | Seconds |
|--------|---------|---------|
| Minutes | `"5m"` | 300 |
| Hours | `"1h"` | 3600 |
| Seconds suffix | `"300s"` | 300 |
| Bare integer | `"300"` | 300 |

---

## Environment variables

These environment variables affect runtime behaviour:

| Variable | Used By | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Agent factory | Anthropic API key for Claude models. |
| `OPENAI_API_KEY` | Agent factory | OpenAI API key (alternative to Anthropic). |
| `VAULT_ADDR` | MCP servers | Vault server address (defaults to `http://127.0.0.1:8200`). |
| `VAULT_TOKEN` | Scripts only | Root token for Vault setup scripts. |
| `VAULT_GCP_MOUNT` | MCP servers | Vault GCP secrets engine mount path (defaults to `gcp`). |
| `MCP_IDENTITY_CONTEXT` | MCP servers (stdio) | JSON-serialised `IdentityContext` for stdio transport. |
| `MCP_TRANSPORT` | MCP servers | Transport mode: `http` or `stdio` (defaults to `stdio`). |
| `MCP_HOST` | MCP servers (HTTP) | Bind address for HTTP mode (defaults to `0.0.0.0`). |
| `MCP_PORT` | MCP servers (HTTP) | Port for HTTP mode (defaults to `8000`). |
| `VAULT_LICENSE` | Docker Compose | Vault Enterprise license key (containerised deployment). |
