# API Reference

Module-level reference for all public classes and functions in the `vault_mcp_agents` package.

## Package structure

```
vault_mcp_agents/
├── main.py               # CLI entry point
├── auth/                  # Authentication layer
│   ├── vault_authenticator.py
│   ├── session.py
│   ├── spiffe_authenticator.py
│   └── workload_session.py
├── vault/                 # Vault credential brokering
│   └── gcp_credentials.py
├── policy/                # Access control
│   └── engine.py
├── mcp/                   # MCP server infrastructure
│   ├── identity_context.py
│   ├── base_server.py
│   ├── data_server.py
│   ├── compute_server.py
│   ├── http_transport.py
│   └── http_identity_middleware.py
├── agents/                # Agent construction
│   ├── factory.py
│   ├── mcp_langchain_adapter.py
│   └── mcp_http_adapter.py
├── audit/                 # Audit logging
│   ├── logger.py
│   └── formatter.py
└── prompt/                # CLI interface
    └── cli.py
```

---

## `vault_mcp_agents.auth.session`

### `Session`

Immutable snapshot of an authenticated human interaction. Created at login and threaded through every downstream component.

```python
@dataclasses.dataclass(frozen=True)
class Session:
    human_id: str                       # Username from Vault auth response
    human_role: str                     # Application role (operator/analyst/viewer)
    vault_token: str                    # Short-lived Vault client token
    token_policies: frozenset[str]      # Vault policy names on the token
    created_at: datetime.datetime       # UTC timestamp of session creation
    ttl_seconds: int                    # Vault token TTL at creation time
    spiffe_id: str | None = None        # Optional SPIFFE ID
```

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `is_expired` | `bool` | `True` if elapsed time since `created_at` exceeds `ttl_seconds` |

---

## `vault_mcp_agents.auth.workload_session`

### `WorkloadSession`

Immutable session for workloads authenticated via SPIFFE.

```python
@dataclasses.dataclass(frozen=True)
class WorkloadSession:
    spiffe_id: str                      # e.g. spiffe://vault-mcp-demo/agent/data_agent
    vault_token: str                    # Vault token from SPIFFE auth
    token_policies: frozenset[str]      # Vault policies
    created_at: datetime.datetime       # UTC timestamp
    ttl_seconds: int                    # Token TTL
```

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `is_expired` | `bool` | `True` if token has expired |

---

## `vault_mcp_agents.auth.vault_authenticator`

### `VaultAuthenticator`

Authenticates a human user via Vault and produces a `Session`.

```python
class VaultAuthenticator:
    def __init__(self, vault_addr: str, auth_method: str = "userpass") -> None: ...
    def authenticate(self, username: str, password: str) -> Session: ...
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `vault_addr` | `str` | Vault server URL |
| `auth_method` | `str` | Auth method: `"userpass"` or `"ldap"` |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `authenticate(username, password)` | `Session` | Authenticate and return an immutable session. Raises `VaultAuthenticationError` on failure. |

### `VaultAuthenticationError`

Raised when Vault authentication or token lookup fails.

### Role resolution

Vault policies are mapped to application roles via `_POLICY_TO_ROLE`. The first matching policy wins (most-privileged first):

| Vault Policy | Application Role |
|-------------|-----------------|
| `operator-policy` | `operator` |
| `analyst-policy` | `analyst` |
| `viewer-policy` | `viewer` |

---

## `vault_mcp_agents.auth.spiffe_authenticator`

### `SpiffeAuthenticator`

Authenticates a workload using its SPIFFE SVID against Vault Enterprise.

```python
class SpiffeAuthenticator:
    def __init__(
        self,
        vault_addr: str,
        trust_domain: str,
        spiffe_auth_mount: str = "spiffe",
    ) -> None: ...

    def authenticate_workload(self) -> WorkloadSession: ...
    def is_enabled(self) -> bool: ...
```

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `authenticate_workload()` | `WorkloadSession` | Fetch SVID from SPIRE agent, authenticate to Vault. Raises `SpiffeAuthenticationError`. |
| `is_enabled()` | `bool` | `True` if `SPIFFE_ENDPOINT_SOCKET` environment variable is set. |

### `SpiffeAuthenticationError`

Raised when SVID retrieval or Vault SPIFFE auth fails.

---

## `vault_mcp_agents.vault.gcp_credentials`

### `GCPCredentialBroker`

Fetches short-lived GCP tokens from Vault's GCP secrets engine.

```python
class GCPCredentialBroker:
    def __init__(self, vault_addr: str, gcp_mount: str = "gcp") -> None: ...

    def get_access_token(
        self,
        session: Session,
        impersonated_account: str,
        requested_ttl: str = "5m",
    ) -> GCPAccessToken: ...
```

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `get_access_token(session, impersonated_account, requested_ttl)` | `GCPAccessToken` | Request a GCP OAuth2 token. Raises `GCPCredentialError`. |

### `GCPAccessToken`

```python
@dataclasses.dataclass(frozen=True)
class GCPAccessToken:
    token: str                      # OAuth2 access token
    ttl_seconds: int                # Token TTL reported by Vault
    impersonated_account: str       # Vault impersonated account name
```

### `GCPCredentialError`

Raised when Vault cannot issue a GCP credential (session expired, Vault error, etc.).

---

## `vault_mcp_agents.policy.engine`

### `PolicyEngine`

Loads `capabilities.yaml` and resolves tool permissions for identity pairs.

```python
class PolicyEngine:
    def __init__(self, policy_path: str | pathlib.Path | None = None) -> None: ...

    def resolve(self, human_role: str, agent_id: str) -> ResolvedPolicy: ...
    def resolve_by_spiffe_id(self, human_role: str, spiffe_id: str) -> ResolvedPolicy: ...
    def list_roles(self) -> list[str]: ...
    def reload(self) -> None: ...
```

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `resolve(human_role, agent_id)` | `ResolvedPolicy` | Resolve allowed tools for the identity pair. Raises `PolicyError`. |
| `resolve_by_spiffe_id(human_role, spiffe_id)` | `ResolvedPolicy` | Resolve via SPIFFE ID → agent ID mapping. Raises `PolicyError`. |
| `list_roles()` | `list[str]` | All role names defined in the policy file. |
| `reload()` | `None` | Re-read the policy file from disk. |

### `ResolvedPolicy`

```python
@dataclasses.dataclass(frozen=True)
class ResolvedPolicy:
    role: str                           # Human role name
    agent_id: str                       # Agent identifier
    allowed_tools: frozenset[str]       # Permitted MCP tool names
    max_gcp_token_ttl: str              # e.g. "5m"
```

### `PolicyError`

Raised when the policy file is malformed or lookup fails.

---

## `vault_mcp_agents.mcp.identity_context`

### `IdentityContext`

Composite identity passed from agents to MCP servers. Serialised as JSON for transport.

```python
@dataclasses.dataclass(frozen=True)
class IdentityContext:
    agent_id: str
    human_id: str
    human_role: str
    vault_token: str
    allowed_tools: frozenset[str]
    gcp_impersonated_account: str
    max_gcp_token_ttl: str
    gcp_project: str
    session_created_at: str             # ISO-8601 UTC timestamp
    session_ttl_seconds: int
    spiffe_id: str | None = None
```

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `to_json()` | `str` | Serialise to JSON (with sorted `allowed_tools`). |
| `from_json(raw)` | `IdentityContext` | Deserialise from JSON string. |

---

## `vault_mcp_agents.mcp.base_server`

### `BaseMCPServer`

Base class for identity-aware MCP servers. Subclasses register tools; the base class handles filtering, GCP credentials, and audit.

```python
class BaseMCPServer:
    def __init__(self, server_name: str) -> None: ...
```

**Protected methods (for subclasses):**

| Method | Description |
|--------|-------------|
| `_register_tool(name, description, input_schema, handler)` | Register a tool in the full registry. |
| `_get_visible_tools()` | Return only tools permitted by the identity context. |
| `_get_handler(tool_name)` | Check permissions, log audit event, return handler. Raises `PermissionError` if denied. |
| `_get_gcp_token()` | Obtain a cached or fresh GCP token via Vault. Raises `GCPCredentialError` on expiry. |

**Public methods:**

| Method | Description |
|--------|-------------|
| `setup_handlers()` | Wire up MCP `list_tools` and `call_tool` protocol handlers. |
| `run()` | Start the MCP server on stdio (async). |
| `run_http()` | Start the MCP server on Streamable HTTP transport. |
| `transport_mode` | Property returning `"stdio"` or `"http"`. |

### `_parse_ttl_to_seconds(ttl_str)`

Module-level function that parses Vault-style duration strings:

| Input | Output |
|-------|--------|
| `"5m"` | `300` |
| `"1h"` | `3600` |
| `"300s"` | `300` |
| `"300"` | `300` |

---

## `vault_mcp_agents.mcp.data_server`

### `DataMCPServer(BaseMCPServer)`

MCP server exposing GCS and BigQuery tools.

**Registered tools:**

| Tool | Description | Required args |
|------|-------------|--------------|
| `list_buckets` | List GCS buckets | *(optional: prefix)* |
| `read_object` | Read a GCS object | `bucket`, `object_path` |
| `write_object` | Write content to GCS | `bucket`, `object_path`, `content` |
| `delete_object` | Delete a GCS object | `bucket`, `object_path` |
| `query_bigquery` | Execute BigQuery SQL | `sql` *(optional: max_rows)* |
| `list_datasets` | List BigQuery datasets | *(optional: prefix)* |
| `create_dataset` | Create a BigQuery dataset | `dataset_id` *(optional: location)* |

---

## `vault_mcp_agents.mcp.compute_server`

### `ComputeMCPServer(BaseMCPServer)`

MCP server exposing GCE Compute Engine tools.

**Registered tools:**

| Tool | Description | Required args |
|------|-------------|--------------|
| `list_instances` | List GCE instances | `project`, `zone` |
| `get_instance` | Get instance details | `project`, `zone`, `instance_name` |
| `start_instance` | Start a stopped instance | `project`, `zone`, `instance_name` |
| `stop_instance` | Stop a running instance | `project`, `zone`, `instance_name` |
| `create_instance` | Create a new instance | `project`, `zone`, `instance_name` *(optional: machine_type, source_image)* |
| `delete_instance` | Delete an instance | `project`, `zone`, `instance_name` |

---

## `vault_mcp_agents.mcp.http_transport`

### `create_http_app(server)`

Creates a Starlette ASGI app serving an MCP server over Streamable HTTP.

```python
def create_http_app(server: BaseMCPServer) -> Starlette: ...
```

**Endpoints:**

| Endpoint | Method | Auth required | Description |
|----------|--------|---------------|-------------|
| `/health` | GET | No | Health check probe |
| `/mcp` | POST, GET | Yes | MCP JSON-RPC endpoint |

### `run_http_server(server)`

Creates the app and runs it with Uvicorn. Reads `MCP_HOST` and `MCP_PORT` from environment.

```python
def run_http_server(server: BaseMCPServer) -> None: ...
```

---

## `vault_mcp_agents.mcp.http_identity_middleware`

### `IdentityContextMiddleware(BaseHTTPMiddleware)`

Starlette middleware that extracts identity from the `X-Identity-Context` HTTP header.

- Skips the `/health` endpoint (no auth required).
- Returns `401 Unauthorized` if the header is missing or malformed.
- Attaches the parsed `IdentityContext` to `request.state.identity_context`.

### `encode_identity_header(identity)`

Encodes an `IdentityContext` as a base64 string for the HTTP header.

```python
def encode_identity_header(identity: IdentityContext) -> str: ...
```

---

## `vault_mcp_agents.agents.factory`

### `build_agent(agent_id, session, policy_engine)`

Constructs a LangChain agent wired to an identity-gated MCP server.

```python
async def build_agent(
    agent_id: str,
    session: Session,
    policy_engine: PolicyEngine,
) -> tuple[AgentExecutor, Any]: ...
```

**Steps:**
1. Load `config/settings.yaml`.
2. Resolve policy for `(human_role, agent_id)`.
3. Build the LLM (Anthropic or OpenAI).
4. Construct `IdentityContext`.
5. Start MCP server (stdio subprocess or HTTP connection).
6. Adapt MCP tools to LangChain `StructuredTool` objects.
7. Create `AgentExecutor` with a tool-calling agent.

**Returns:** `(AgentExecutor, cleanup_handles)` — the caller must `await cleanup.aclose()` when done.

---

## `vault_mcp_agents.agents.mcp_langchain_adapter`

### `create_mcp_langchain_tools(server_command, server_args, identity_context, vault_addr, gcp_mount)`

Starts an MCP server as a subprocess (stdio) and wraps its tools as LangChain `StructuredTool` objects.

```python
async def create_mcp_langchain_tools(
    server_command: str,
    server_args: list[str],
    identity_context: IdentityContext,
    vault_addr: str = "http://127.0.0.1:8200",
    gcp_mount: str = "gcp",
) -> tuple[list[StructuredTool], contextlib.AsyncExitStack]: ...
```

**Returns:** `(tools, exit_stack)` — `exit_stack` must be kept alive for the duration of agent execution.

---

## `vault_mcp_agents.agents.mcp_http_adapter`

### `create_mcp_http_langchain_tools(server_url, identity_context)`

Connects to an MCP server over Streamable HTTP and wraps its tools as LangChain `StructuredTool` objects.

```python
async def create_mcp_http_langchain_tools(
    server_url: str,
    identity_context: IdentityContext,
) -> tuple[list[StructuredTool], contextlib.AsyncExitStack]: ...
```

Identity is delivered via the `X-Identity-Context` HTTP header (base64-encoded JSON).

**Returns:** `(tools, exit_stack)` — `exit_stack` must be kept alive for the duration of agent execution.

---

## `vault_mcp_agents.audit.logger`

### `AuditEvent`

Enum of audit event types:

```python
class AuditEvent(str, Enum):
    TOOL_ACCESS_ALLOWED = "TOOL_ACCESS_ALLOWED"
    TOOL_ACCESS_DENIED = "TOOL_ACCESS_DENIED"
    CREDENTIAL_REQUESTED = "CREDENTIAL_REQUESTED"
    CREDENTIAL_ISSUED = "CREDENTIAL_ISSUED"
    CREDENTIAL_EXPIRED = "CREDENTIAL_EXPIRED"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    SESSION_CREATED = "SESSION_CREATED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    SPIFFE_AUTH_SUCCESS = "SPIFFE_AUTH_SUCCESS"
    SPIFFE_AUTH_FAILURE = "SPIFFE_AUTH_FAILURE"
```

### `AuditLogger`

Structured JSON audit logger.

```python
class AuditLogger:
    def __init__(self, *, log_file: str | None = None, log_to_stdout: bool = True) -> None: ...

    def log_event(self, event_type: AuditEvent, /, **fields: Any) -> None: ...
    def log_tool_access(self, *, agent_id, human_id, human_role, tool_name, allowed, spiffe_id=None, vault_token=None) -> None: ...
    def log_credential_event(self, *, event_type, agent_id, human_id, human_role, detail="", spiffe_id=None, vault_token=None) -> None: ...
    def log_session_event(self, *, event_type, human_id, human_role, vault_token=None, detail="") -> None: ...
    def log_policy_violation(self, *, human_role, agent_id, detail) -> None: ...
```

---

## `vault_mcp_agents.audit.formatter`

### `JSONFormatter(logging.Formatter)`

Formats log records as single-line JSON objects. Handles `frozenset`, `set`, and `datetime` serialisation.

---

## `vault_mcp_agents.prompt.cli`

### `run_cli(vault_addr, auth_method, policy_path=None)`

Main entry point for the interactive CLI. Orchestrates: login → agent selection → conversation loop.

```python
def run_cli(vault_addr: str, auth_method: str, policy_path: str | None = None) -> None: ...
```

---

## `vault_mcp_agents.main`

### `main()`

CLI entry point. Parses command-line arguments and delegates to `run_cli()`.

```
usage: vault-mcp-agents [--config PATH] [--policies PATH] [--verbose]

Options:
  --config PATH     Path to settings.yaml (default: config/settings.yaml)
  --policies PATH   Path to capabilities.yaml (default: policies/capabilities.yaml)
  --verbose, -v     Enable debug logging
```
