# Docker Compose Guide

This guide explains how to run the full containerised stack: Vault Enterprise, MCP servers, and the agent CLI.

## Prerequisites

- Docker and Docker Compose v2+
- A **Vault Enterprise license key** (required for the SPIFFE auth method)
- An LLM API key (Anthropic or OpenAI)

### Obtaining a Vault Enterprise license

A Vault Enterprise license is required because this stack uses the SPIFFE auth method, which is an Enterprise-only feature. Options:

1. **HashiCorp Vault Enterprise trial** — request at [hashicorp.com/products/vault/trial](https://www.hashicorp.com/products/vault/trial)
2. **HCP Vault** — managed Vault with Enterprise features included
3. **Existing license** — if your organisation has a Vault Enterprise license

The license key is a long string that starts with a product identifier. It is passed to the Vault container via the `VAULT_LICENSE` environment variable.

## Quick start

### 1. Create the environment file

```bash
cp docker/.env.example docker/.env
```

Edit `docker/.env` and fill in:

```
VAULT_LICENSE=<your-vault-enterprise-license-key>
ANTHROPIC_API_KEY=sk-ant-...
```

### 2. Start the stack

```bash
docker compose --env-file docker/.env up -d --build
```

This starts five services:

| Service | Description | Port |
|---------|-------------|------|
| `vault` | Vault Enterprise 1.21 in dev mode | 8200 |
| `vault-init` | One-shot: configures Vault (users, policies, SPIFFE), then exits | — |
| `data-mcp-server` | Data MCP server (GCS + BigQuery tools) | 8001 |
| `compute-mcp-server` | Compute MCP server (GCE tools) | 8002 |
| `agent-cli` | Interactive LangChain agent CLI | — |

### 3. Wait for services to be healthy

```bash
docker compose --env-file docker/.env ps
```

All services should show `healthy` (except `vault-init`, which exits after completion, and `agent-cli`, which waits for input).

### 4. Run the agent

```bash
docker compose --env-file docker/.env exec agent-cli vault-mcp-agents
```

You will be prompted to log in with one of the test users (alice/bob/carol), select an agent, and interact with it.

### 5. Tear down

```bash
docker compose --env-file docker/.env down
```

Add `-v` to also remove the Vault data volume:

```bash
docker compose --env-file docker/.env down -v
```

## Service architecture

```
                         ┌──────────────┐
                         │   vault      │
                         │  :8200       │
                         │  (Enterprise)│
                         └──────┬───────┘
                                │
                    ┌───────────┼───────────┐
                    │           │           │
            ┌───────▼──────┐   │   ┌───────▼──────┐
            │ data-mcp-    │   │   │ compute-mcp- │
            │ server :8001 │   │   │ server :8002 │
            └───────▲──────┘   │   └───────▲──────┘
                    │          │           │
                    └──────────┤───────────┘
                               │
                        ┌──────▼──────┐
                        │  agent-cli  │
                        │  (tty)      │
                        └─────────────┘

              All services on: mcp-net (bridge)
```

### Startup order

1. `vault` starts and becomes healthy (health check: `vault status`)
2. `vault-init` runs `setup_vault.sh` + `setup_vault_enterprise.sh`, then exits
3. `data-mcp-server` and `compute-mcp-server` start (wait for `vault-init` to complete)
4. `agent-cli` starts (waits for both MCP servers to be healthy)

## Environment variables

### Required (in `docker/.env`)

| Variable | Description |
|----------|-------------|
| `VAULT_LICENSE` | Vault Enterprise license key |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude models |

### Optional (in `docker/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key (alternative to Anthropic) | — |

### Set internally by Docker Compose

These are set in the `docker-compose.yaml` and should not normally be overridden:

| Variable | Service | Value |
|----------|---------|-------|
| `VAULT_DEV_ROOT_TOKEN_ID` | vault | `dev-root-token` |
| `MCP_TRANSPORT` | MCP servers | `http` |
| `MCP_PORT` | data-mcp-server | `8001` |
| `MCP_PORT` | compute-mcp-server | `8002` |
| `MCP_HOST` | MCP servers | `0.0.0.0` |
| `VAULT_ADDR` | all (except vault) | `http://vault:8200` |

## Dockerfiles

### `docker/mcp-server.Dockerfile`

Multi-stage build for MCP servers:

- **Stage 1** (`builder`): Installs Python dependencies into a virtual environment
- **Stage 2** (`runtime`): Copies the venv and application code, installs `curl` for health checks
- **Build arg** `MCP_SERVER_MODULE`: The Python module to run (e.g. `vault_mcp_agents.mcp.data_server`)

Both `data-mcp-server` and `compute-mcp-server` use the same Dockerfile with different build arguments.

### `docker/agent.Dockerfile`

Multi-stage build for the agent CLI:

- Same structure as the MCP server Dockerfile
- Entry point is `vault-mcp-agents` (the console script)
- Runs with `stdin_open: true` and `tty: true` for interactive use

## Local development (Vault OSS)

For local development without Vault Enterprise:

```bash
docker compose -f docker-compose.dev.yaml up -d
```

This starts only Vault (OSS, not Enterprise) on port 8200. MCP servers run locally as stdio subprocesses — no containers needed. This preserves the original development workflow.

To switch back to the full enterprise stack:

```bash
docker compose -f docker-compose.dev.yaml down
docker compose --env-file docker/.env up -d --build
```

## Viewing logs

```bash
# All services
docker compose --env-file docker/.env logs -f

# Specific service
docker compose --env-file docker/.env logs -f data-mcp-server

# Vault init output (useful for debugging configuration)
docker compose --env-file docker/.env logs vault-init
```

## Health checks

Each service exposes a health check:

| Service | Health check | Interval |
|---------|-------------|----------|
| `vault` | `vault status` | 5s |
| `data-mcp-server` | `curl -f http://localhost:8001/health` | 10s |
| `compute-mcp-server` | `curl -f http://localhost:8002/health` | 10s |

You can also check health endpoints directly:

```bash
curl http://localhost:8200/v1/sys/health    # Vault
curl http://localhost:8001/health            # Data MCP server
curl http://localhost:8002/health            # Compute MCP server
```

## Running integration tests

The integration test suite runs against the Docker Compose stack:

```bash
# Start the stack
docker compose --env-file docker/.env up -d --build

# Run integration tests (from host, with venv activated)
source .venv/bin/activate
python -m pytest tests/integration/ -v --run-integration

# Or use the convenience script
./scripts/run_integration_tests.sh
```

See the main [README.md](../README.md) for more details on running tests.

## Troubleshooting

### Vault fails to start

**Symptom:** `vault` container exits immediately or fails health check.

**Common causes:**
- Missing or invalid `VAULT_LICENSE` in `docker/.env`
- Port 8200 already in use

**Fix:**
```bash
# Check Vault logs
docker compose --env-file docker/.env logs vault

# Verify license is set
grep VAULT_LICENSE docker/.env
```

### MCP servers fail health check

**Symptom:** `data-mcp-server` or `compute-mcp-server` stuck in "starting" state.

**Common causes:**
- `vault-init` failed (Vault configuration incomplete)
- Build errors in the Dockerfile

**Fix:**
```bash
# Check vault-init completed successfully
docker compose --env-file docker/.env logs vault-init

# Check MCP server logs
docker compose --env-file docker/.env logs data-mcp-server
```

### Agent CLI cannot connect to MCP servers

**Symptom:** Agent commands fail with connection errors.

**Common causes:**
- MCP servers not healthy yet
- Network misconfiguration

**Fix:**
```bash
# Verify all services are healthy
docker compose --env-file docker/.env ps

# Test connectivity from agent container
docker compose --env-file docker/.env exec agent-cli curl http://data-mcp-server:8001/health
```

### Rebuilding after code changes

```bash
docker compose --env-file docker/.env up -d --build
```

The `--build` flag forces a rebuild of the Docker images with your latest code changes.
