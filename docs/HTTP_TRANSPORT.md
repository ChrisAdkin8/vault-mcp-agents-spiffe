# HTTP Transport Guide

This guide explains the Streamable HTTP transport for MCP servers, which enables containerised deployment and network-based communication between agents and MCP servers.

## Overview

MCP (Model Context Protocol) supports two transport mechanisms:

| Transport | Use case | Identity delivery |
|-----------|----------|-------------------|
| **stdio** | Local development — agent spawns MCP server as a subprocess | `MCP_IDENTITY_CONTEXT` environment variable |
| **Streamable HTTP** | Containerised deployment — MCP servers run as HTTP services | `X-Identity-Context` HTTP header (base64 JSON) |

Both transports are fully supported. The `transport` field in `config/settings.yaml` controls which mode is used.

## How it works

### Streamable HTTP transport

When `MCP_TRANSPORT=http` is set, each MCP server starts as an HTTP service using Starlette and Uvicorn:

```
┌─────────────┐     HTTP POST      ┌──────────────────────────┐
│  Agent      │ ──────────────────▶ │  MCP Server (HTTP)       │
│  (client)   │                     │  ┌────────────────────┐  │
│             │ ◀────────────────── │  │ Identity Middleware │  │
│             │     JSON-RPC        │  └────────┬───────────┘  │
└─────────────┘                     │           ▼              │
                                    │  ┌────────────────────┐  │
                                    │  │ MCP Server Logic   │  │
                                    │  └────────────────────┘  │
                                    └──────────────────────────┘
```

The server exposes two endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check (no auth required) |
| `/mcp` | POST | MCP JSON-RPC requests (identity header required) |

### Identity delivery via HTTP header

In HTTP mode, the composite identity (`IdentityContext`) is delivered via the `X-Identity-Context` HTTP header. The value is a base64-encoded JSON string:

```
X-Identity-Context: eyJhZ2VudF9pZCI6ImRhdGFfYWdlbnQiLCJodW1hbl9pZCI6...
```

The `IdentityContextMiddleware` (Starlette middleware) intercepts every request except `/health`:

1. Extracts the `X-Identity-Context` header
2. Base64-decodes and JSON-parses the value
3. Deserialises it into an `IdentityContext` object
4. Attaches it to the request state (`request.state.identity_context`)
5. Returns `401 Unauthorized` if the header is missing or malformed

### Encoding identity (client side)

The `encode_identity_header()` utility function creates the header value:

```python
from vault_mcp_agents.mcp.http_identity_middleware import encode_identity_header
from vault_mcp_agents.mcp.identity_context import IdentityContext

identity = IdentityContext(
    agent_id="data_agent",
    human_id="alice",
    human_role="operator",
    vault_token="s.xxxxx",
    allowed_tools=frozenset(["list_buckets", "read_object"]),
    gcp_impersonated_account="data-agent-gcp",
    max_gcp_token_ttl="5m",
    gcp_project="my-project",
    session_created_at="2025-01-01T00:00:00+00:00",
    session_ttl_seconds=3600,
)

header_value = encode_identity_header(identity)
# Use in HTTP requests:
headers = {"X-Identity-Context": header_value}
```

## Configuration

### settings.yaml

```yaml
mcp_servers:
  data_server:
    transport: "stdio"          # "stdio" for local dev, "http" for containers
    command: "python"           # used when transport: "stdio"
    args: ["-m", "vault_mcp_agents.mcp.data_server"]
    url: "http://data-mcp-server:8001/mcp"  # used when transport: "http"
```

### Environment variables (MCP server side)

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_TRANSPORT` | Transport mode: `http` or `stdio` | `stdio` |
| `MCP_HOST` | Bind address for HTTP mode | `0.0.0.0` |
| `MCP_PORT` | Port for HTTP mode | `8000` |

### Agent factory behaviour

The agent factory (`src/vault_mcp_agents/agents/factory.py`) reads the `transport` field from the MCP server config:

- `"stdio"` — spawns the MCP server as a subprocess, passes identity via environment variable
- `"http"` — connects to the MCP server's URL, passes identity via HTTP header

## Running HTTP mode locally

You can run MCP servers in HTTP mode without Docker for testing:

### Terminal 1 — Start the data MCP server

```bash
source .venv/bin/activate
MCP_TRANSPORT=http MCP_PORT=8001 python -m vault_mcp_agents.mcp.data_server
```

### Terminal 2 — Start the compute MCP server

```bash
source .venv/bin/activate
MCP_TRANSPORT=http MCP_PORT=8002 python -m vault_mcp_agents.mcp.compute_server
```

### Terminal 3 — Test the health endpoint

```bash
curl http://localhost:8001/health
# {"status": "ok"}
```

### Terminal 3 — Run the agent with HTTP transport

Edit `config/settings.yaml` to use HTTP transport:

```yaml
mcp_servers:
  data_server:
    transport: "http"
    url: "http://localhost:8001/mcp"
  compute_server:
    transport: "http"
    url: "http://localhost:8002/mcp"
```

Then run the agent:

```bash
vault-mcp-agents
```

## Switching between transports

To switch from HTTP back to stdio (local development):

```yaml
mcp_servers:
  data_server:
    transport: "stdio"
    command: "python"
    args: ["-m", "vault_mcp_agents.mcp.data_server"]
```

No code changes are required — just update `config/settings.yaml`.

## Security considerations

### Identity header trust

In HTTP mode, the MCP server trusts the `X-Identity-Context` header. This is safe within the Docker Compose network (bridge mode, no external access to MCP ports). In a production deployment:

- MCP server ports should **not** be exposed externally
- Use network policies to restrict which services can reach MCP servers
- Consider mTLS between the agent and MCP servers for additional assurance
- The SPIFFE workload identity layer provides an additional authentication mechanism

### Vault token in transit

The `X-Identity-Context` header contains the human's Vault token (needed for GCP credential issuance). Within a Docker bridge network this is acceptable. For production:

- Use TLS between all services
- Consider a token-exchange pattern where the human's Vault token is exchanged for a scoped service token

## Implementation details

### Key files

| File | Purpose |
|------|---------|
| `src/vault_mcp_agents/mcp/http_transport.py` | Creates the Starlette ASGI app with MCP mounted |
| `src/vault_mcp_agents/mcp/http_identity_middleware.py` | Starlette middleware for identity extraction |
| `src/vault_mcp_agents/agents/mcp_http_adapter.py` | HTTP client adapter for LangChain tools |
| `src/vault_mcp_agents/mcp/base_server.py` | `run_http()` method and `transport_mode` property |

### MCP SDK integration

The HTTP transport uses the MCP SDK's `StreamableHTTPServerTransport` on the server side and `streamablehttp_client()` on the client side. The protocol version is `2025-06-18`.
