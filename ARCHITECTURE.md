# Architecture

This document describes the design patterns and security model used in this project. It is intended to be read by both humans and AI coding assistants working on the codebase.

## Design patterns

### 1. Composite Identity Pattern

**Problem:** An MCP server needs to decide which tools to expose. Neither the agent identity alone nor the human identity alone is sufficient — an analyst using the data agent should see different tools than an operator using the same agent.

**Solution:** Every access-control decision is based on a tuple of `(agent_id, human_role)`. This tuple is materialised as an `IdentityContext` object that travels from the agent factory through to the MCP server process.

**Where it lives:** `src/vault_mcp_agents/mcp/identity_context.py`

```
┌──────────────┐   ┌─────────────┐
│ agent_id     │ + │ human_role  │  ──▶  IdentityContext  ──▶  tool filter
│ "data_agent" │   │ "analyst"   │
└──────────────┘   └─────────────┘
```

### 2. Vault as Identity Broker

**Problem:** The system needs to authenticate humans, identify agents, and issue GCP credentials. Using three separate systems creates a large trust surface.

**Solution:** Vault is the single authority for all three concerns:

| Concern | Vault mechanism |
|---|---|
| Human authentication | `userpass` / `ldap` / `oidc` auth methods |
| Agent identity | `approle` auth method (one role per agent) |
| GCP credentials | GCP secrets engine → short-lived OAuth2 access tokens |

The human's Vault token is passed to the MCP server (inside `IdentityContext`) so that the server requests GCP tokens *as the human's session*. Vault policies on the human's token control which GCP impersonated accounts they can access.

**Where it lives:** `src/vault_mcp_agents/auth/vault_authenticator.py`, `src/vault_mcp_agents/vault/gcp_credentials.py`

### 3. Policy-Gated Capability Filtering

**Problem:** Vault policies control access to *Vault paths* (e.g. `gcp/impersonated-account/*/token`), but we also need fine-grained control over *which MCP tools* a given identity can invoke. These are different layers.

**Solution:** A YAML policy file (`policies/capabilities.yaml`) defines the mapping from `(human_role, agent_id)` to a set of allowed tool names and a maximum GCP token TTL.

```yaml
roles:
  analyst:
    agents:
      data_agent:
        allowed_tools: [list_buckets, read_object, query_bigquery]
        max_gcp_token_ttl: "5m"
```

The `PolicyEngine` loads this file and resolves it at agent-construction time. The resolved set of allowed tools is baked into the `IdentityContext` and enforced by the MCP server's `BaseMCPServer._get_visible_tools()`.

**Defence in depth:** Even if the policy file were bypassed, Vault policies on the human's token independently restrict which GCP impersonated accounts they can access. The two layers are complementary.

**Where it lives:** `policies/capabilities.yaml`, `src/vault_mcp_agents/policy/engine.py`, `src/vault_mcp_agents/mcp/base_server.py`

### 4. Session Context Propagation

**Problem:** After authentication, the human's identity, role, and Vault token must be available to every downstream component (agent factory, MCP server, GCP credential broker) without global state.

**Solution:** An immutable `Session` dataclass is created at login and explicitly passed as a parameter through the call chain. No module reads identity from global state or environment variables (except the MCP server, which receives it via `MCP_IDENTITY_CONTEXT` because it runs as a subprocess).

**Where it lives:** `src/vault_mcp_agents/auth/session.py`

### 5. Adapter Pattern (MCP → LangChain)

**Problem:** LangChain agents consume `BaseTool` instances. MCP servers expose tools via the MCP protocol. These are different type systems.

**Solution:** `mcp_langchain_adapter.py` connects to the MCP server as a client, lists its tools, and wraps each one as a `StructuredTool` that delegates `invoke()` to `ClientSession.call_tool()`.

The adapter is intentionally thin — it does no access control, caching, or transformation. All intelligence is in the MCP server and the LangChain agent.

**Where it lives:** `src/vault_mcp_agents/agents/mcp_langchain_adapter.py`

### 6. Factory Pattern

**Problem:** Constructing a usable agent requires five ordered steps: resolve policy → build identity context → start MCP server → adapt tools → create LangChain agent. This logic should not leak into the CLI.

**Solution:** `factory.py` exposes a single `build_agent(agent_id, session, policy_engine)` async function. The CLI calls it and gets back an `AgentExecutor` ready for conversation.

**Where it lives:** `src/vault_mcp_agents/agents/factory.py`

### 7. Structured Audit Logging

**Problem:** Security-relevant events (tool access decisions, credential issuance, policy violations) must be captured for compliance and incident investigation, but sensitive data (Vault tokens) must never appear in logs.

**Solution:** An `AuditLogger` emits single-line JSON events for every security-relevant action. Vault tokens are never logged directly — only a 12-character SHA-256 prefix is recorded for cross-event correlation.

**Event types:** `TOOL_ACCESS_ALLOWED`, `TOOL_ACCESS_DENIED`, `CREDENTIAL_REQUESTED`, `CREDENTIAL_ISSUED`, `CREDENTIAL_EXPIRED`, `POLICY_VIOLATION`, `SESSION_CREATED`, `SESSION_EXPIRED`, `SPIFFE_AUTH_SUCCESS`, `SPIFFE_AUTH_FAILURE`.

**Where it lives:** `src/vault_mcp_agents/audit/logger.py`, `src/vault_mcp_agents/audit/formatter.py`. See [Audit Logging Guide](docs/AUDIT_LOGGING.md).

### 8. SPIFFE Workload Identity

**Problem:** In containerised deployments, MCP servers need to authenticate to Vault without static secrets baked into the container image.

**Solution:** Each container receives an X.509 SVID from a SPIRE agent, presents it to Vault Enterprise's SPIFFE auth method, and receives a short-lived Vault token. The SPIFFE ID is mapped to an agent ID via the `spiffe_identity_map` in `capabilities.yaml`.

**Where it lives:** `src/vault_mcp_agents/auth/spiffe_authenticator.py`, `src/vault_mcp_agents/auth/workload_session.py`. See [SPIFFE Guide](docs/SPIFFE_GUIDE.md).

### 9. Dual Transport (Stdio + HTTP)

**Problem:** Local development benefits from simple subprocess-based stdio transport, but containerised deployment requires network-based communication.

**Solution:** Both transports are fully supported. The `transport` field in `settings.yaml` selects the mode. Identity delivery adapts automatically — environment variable for stdio, `X-Identity-Context` HTTP header for HTTP.

**Where it lives:** `src/vault_mcp_agents/mcp/http_transport.py`, `src/vault_mcp_agents/mcp/http_identity_middleware.py`, `src/vault_mcp_agents/agents/mcp_http_adapter.py`. See [HTTP Transport Guide](docs/HTTP_TRANSPORT.md).

## Security model

### Trust boundaries

```
┌──────────────────────────────────────────────────┐
│                  User's machine                  │
│                                                  │
│  ┌────────┐    ┌────────────┐    ┌─────────────┐ │
│  │  CLI   │───▶│ Agent proc │───▶│ MCP server  │ │
│  │(human) │    │(LangChain) │    │ (subprocess)│ │
│  └────────┘    └────────────┘    └──────┬──────┘ │
│                                         │        │
└─────────────────────────────────────────┼────────┘
                                          │
                          ┌───────────────▼──────────────┐
                          │        Vault (network)       │
                          │  - authenticates human       │
                          │  - issues GCP tokens         │
                          │  - enforces path policies    │
                          └───────────────┬──────────────┘
                                          │
                          ┌───────────────▼──────────────┐
                          │        GCP APIs (network)    │
                          └──────────────────────────────┘
```

### What each layer enforces

| Layer | What it checks |
|---|---|
| **Vault auth** | Human is who they claim to be; token gets correct policies |
| **Vault GCP secrets** | Human's token policies allow access to the requested GCP impersonated account |
| **Policy engine** | The `(human_role, agent_id)` pair allows the requested MCP tool name |
| **MCP server** | Tool registry only contains tools the identity context permits |
| **GCP IAM** | The Vault-issued service account / token has the necessary GCP IAM roles |

### Credential lifecycle

1. Human authenticates → receives a Vault token (TTL from Vault config).
2. Agent factory resolves policy → `max_gcp_token_ttl` (`"5m"` for all roles).
3. MCP server tool handler calls `_get_gcp_token()` → Vault issues an OAuth2 token with TTL = min(policy TTL, backend max lease TTL, session remaining TTL).
4. GCP API call uses the short-lived token.
5. Token expires (after at most 5 minutes); next call gets a fresh one.

No credential is stored on disk. No credential outlives the session.

### Why 5 minutes?

The GCP secrets backend enforces a hard ceiling of 300 seconds (`max_lease_ttl_seconds = 300`), and every role in the application policy requests at most `"5m"`. This dual-layer enforcement ensures that even if one layer is misconfigured, the other still caps credential lifetime. A 5-minute window limits the blast radius of a compromised token: an attacker who intercepts a GCP OAuth2 token has at most 5 minutes before it becomes worthless.

## Data flow for a single user request

```
User types: "List all GCS buckets"
      │
      ▼
CLI sends to AgentExecutor.ainvoke({"input": "List all GCS buckets"})
      │
      ▼
LangChain agent decides to call tool "list_buckets"
      │
      ▼
StructuredTool.invoke() → MCP ClientSession.call_tool("list_buckets", {})
      │
      ▼
MCP server receives call_tool
  ├── checks tool name is in identity_context.allowed_tools
  ├── calls _get_gcp_token() → Vault GCP secrets engine → OAuth2 token
  ├── uses token to call GCS list_buckets API
  └── returns JSON result as TextContent
      │
      ▼
LangChain agent formats result into natural language
      │
      ▼
CLI displays response
```

## Extension points

| To add... | Modify... |
|---|---|
| A new MCP tool | Server class `_register_all_tools()` + `capabilities.yaml` |
| A new human role | `vault_authenticator._POLICY_TO_ROLE` + `capabilities.yaml` + Vault policy |
| A new agent | `config/settings.yaml` agents block + new MCP server module + `capabilities.yaml` |
| A new auth method | `VaultAuthenticator._login()` + `settings.yaml` |
| HTTP transport | Already implemented — switch `transport` in `settings.yaml` between `stdio` and `http`. See [HTTP Transport Guide](docs/HTTP_TRANSPORT.md) |

## Infrastructure provisioning

The GCP secrets engine configuration is managed by Terraform (`terraform/`). This replaces
manual `vault write` commands with a declarative, version-controlled approach.

| Resource | Terraform resource type | Purpose |
|---|---|---|
| GCP service account (Vault) | `google_service_account` | Identity Vault uses to impersonate agent service accounts |
| Agent service accounts | `google_service_account` | Per-agent identities (`data-agent-gcp`, `compute-agent-gcp`) with their own IAM roles |
| SA IAM bindings | `google_project_iam_member` | Grants admin, key-admin, token-creator, and project IAM admin roles |
| SA key | `google_service_account_key` | Key material passed to Vault (lives in TF state only) |
| Vault GCP backend | `vault_gcp_secret_backend` | Enables and configures the GCP secrets mount |
| Vault GCP impersonated accounts | `vault_gcp_secret_impersonated_account` | Defines `data-agent-gcp` and `compute-agent-gcp` with 5-minute token TTL |

The Vault-internal resources (userpass auth, policies, test users) remain in `scripts/setup_vault.sh`
because they are simple, idempotent shell commands that do not benefit from Terraform's state management.

**Security note:** Terraform state contains the GCP service account key. For production, use a
[remote backend](https://developer.hashicorp.com/terraform/language/settings/backends/configuration)
with encryption (e.g., GCS backend with CMEK).
