# Docker Compose Guide

This guide explains how to run the full containerised stack: Vault, vault-init bootstrap, Vault Agent sidecar, MCP servers, and the agent CLI.

## Prerequisites

- Docker and Docker Compose v2+
- An LLM API key (Anthropic or OpenAI)

## Quick start

### 1. Create the environment file

```bash
cp docker/.env.example docker/.env
```

Edit `docker/.env` and fill in:

```
ANTHROPIC_API_KEY=sk-ant-...
```

### 2. (Optional) Configure GCP secrets engine

To enable Vault-brokered GCP credentials with 5-minute TTLs, first provision the GCP service accounts using Terraform (see [`terraform/README.md`](../terraform/README.md)), then add these to `docker/.env`:

```
GCP_SA_KEY_FILE=./path/to/sa-key.json
DATA_AGENT_SA_EMAIL=data-agent-gcp@YOUR_PROJECT.iam.gserviceaccount.com
COMPUTE_AGENT_SA_EMAIL=compute-agent-gcp@YOUR_PROJECT.iam.gserviceaccount.com
```

If these variables are not set, the stack starts without the GCP secrets engine — PKI, AppRole, and SPIFFE functionality still work.

### 3. Start the stack

```bash
docker compose --env-file docker/.env up -d --build
```

This starts six services:

| Service | Description | Port |
|---------|-------------|------|
| `vault` | Vault 1.21 (OSS) in dev mode | 8200 |
| `vault-init` | One-shot: configures Vault (PKI, AppRole, GCP secrets, policies, users), writes creds to shared volume, then exits | — |
| `vault-agent` | Sidecar: authenticates via AppRole, renders X.509 SVIDs to cert volume | — |
| `data-mcp-server` | Data MCP server (GCS + BigQuery tools) with mTLS | internal only |
| `compute-mcp-server` | Compute MCP server (GCE tools) with mTLS | internal only |
| `agent-cli` | Interactive LangChain agent CLI | — |

### 4. Wait for services to be healthy

```bash
docker compose --env-file docker/.env ps
```

All services should show `healthy` (except `vault-init` which exits after completion, `vault-agent` which runs continuously, and `agent-cli` which waits for input).

### 5. Verify SVIDs (optional)

```bash
# Check certificate files exist
docker exec data-mcp-server ls -l /etc/mcp/certs/

# Verify the SPIFFE URI SAN in the certificate
docker exec data-mcp-server openssl x509 \
    -in /etc/mcp/certs/server.crt -text -noout | grep "URI"
```

Expected: `URI:spiffe://my-trust-domain/ns/default/sa/mcp`

### 6. Run the agent

```bash
docker compose --env-file docker/.env exec agent-cli vault-mcp-agents
```

You will be prompted to log in with one of the test users (alice/bob/carol), select an agent, and interact with it.

### 7. Tear down

```bash
docker compose --env-file docker/.env down
```

Add `-v` to also remove all volumes (Vault data, credentials, certificates):

```bash
docker compose --env-file docker/.env down -v
```

## Service architecture

```
                         ┌──────────────┐
                         │   vault      │
                         │  :8200       │
                         │  (OSS)       │
                         └──────┬───────┘
                                │
               ┌────────────────┼────────────────┐
               │                │                │
       ┌───────▼──────┐ ┌──────▼───────┐ ┌──────▼──────┐
       │  vault-init  │ │ vault-agent  │ │  agent-cli  │
       │  (one-shot)  │ │ (sidecar)    │ │  (tty)      │
       └──────┬───────┘ └──────┬───────┘ └──────┬──────┘
              │                │                │
     writes role_id/    renders SVIDs    ┌──────┴──────┐
     secret_id to       to cert volume   │             │
     shared-creds vol   (certs-vol)      │             │
                               │         │             │
                    ┌──────────┤─────────┤             │
                    │          │         │             │
            ┌───────▼──────┐  │  ┌──────▼──────┐      │
            │ data-mcp-    │  │  │ compute-mcp-│      │
            │ server :8001 │  │  │ server :8002│      │
            │ (mTLS)       │  │  │ (mTLS)      │      │
            └──────────────┘  │  └─────────────┘      │
                              │                       │
            All services on: mcp-net (bridge)         │
            Vault Agent renders X.509 SVIDs           │
            MCP servers use SVIDs for mTLS            │
```

### Startup order

1. `vault` starts and becomes healthy (health check: `vault status`)
2. `vault-init` waits for Vault, runs vault CLI commands to configure PKI + AppRole + GCP secrets engine + policies + test users, writes AppRole credentials to `shared-creds` volume, then exits
3. `vault-agent` starts after `vault-init` exits successfully, reads AppRole credentials, authenticates, renders SVIDs to `certs-vol`
4. `data-mcp-server` and `compute-mcp-server` start after `vault-agent` (mount `certs-vol` for mTLS)
5. `agent-cli` starts after both MCP servers are healthy

## Volumes

| Volume | Purpose | Used by |
|--------|---------|---------|
| `vault-data` | Vault persistent data | `vault` |
| `shared-creds` | AppRole role_id and secret_id files | `vault-init` (write), `vault-agent` (read) |
| `certs-vol` | Rendered X.509 SVIDs (server.crt, server.key, ca.crt) | `vault-agent` (write), MCP servers + agent-cli (read) |

## Environment variables

### Required (in `docker/.env`)

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude models |

### Optional — GCP secrets engine (in `docker/.env`)

| Variable | Description |
|----------|-------------|
| `GCP_SA_KEY_FILE` | Path to the GCP service account key JSON file on the host. If not set, the GCP secrets engine is skipped. |
| `DATA_AGENT_SA_EMAIL` | Email of the pre-provisioned data agent GCP service account |
| `COMPUTE_AGENT_SA_EMAIL` | Email of the pre-provisioned compute agent GCP service account |

### Optional — other (in `docker/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key (alternative to Anthropic) | — |

### Set internally by Docker Compose

These are set in the `docker-compose.yaml` and should not normally be overridden:

| Variable | Service | Value |
|----------|---------|-------|
| `VAULT_DEV_ROOT_TOKEN_ID` | vault | `dev-root-token` |
| `VAULT_ADDR` / `VAULT_TOKEN` | vault-init | `http://vault:8200` / `dev-root-token` |
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

## Migration path to Kubernetes

The Docker Compose stack is designed as a stepping stone toward Kubernetes deployment. The sidecar pattern used here maps directly to the Vault Agent Injector in Kubernetes:

| Docker Compose (this stack) | Kubernetes equivalent |
|-------------------------------|----------------------|
| `vault-init` writes AppRole creds to `shared-creds` volume | Vault Agent Injector admission controller injects credentials automatically |
| `vault-agent` service in `docker-compose.yaml` | `vault.hashicorp.com/agent-inject: "true"` pod annotation triggers automatic sidecar injection |
| `certs-vol` shared volume | Injected shared volume managed by the sidecar |
| `depends_on` for startup ordering | Kubernetes init containers and readiness probes |
| AppRole auth | Kubernetes auth (pod service account token) |

The MCP servers are agnostic to how certificates arrive at `/etc/mcp/certs/`. Whether a manually configured Vault Agent or a Kubernetes-injected sidecar renders the SVIDs, the application code is identical.

To migrate:

1. Deploy the [Vault Agent Injector](https://developer.hashicorp.com/vault/docs/platform/k8s/injector) into the cluster
2. Annotate MCP server pod specs with Vault Agent injection annotations
3. Switch from AppRole auth to Kubernetes auth
4. The same PKI role, policy, and certificate paths work unchanged

## Local development (stdio transport)

For local development without the full containerised stack:

```bash
docker compose -f docker-compose.dev.yaml up -d
```

This starts only Vault on port 8200. MCP servers run locally as stdio subprocesses — no containers needed. This preserves the original development workflow.

To switch back to the full stack:

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

# Vault Agent output (useful for debugging certificate rendering)
docker compose --env-file docker/.env logs vault-agent
```

## Health checks

Each service exposes a health check:

| Service | Health check | Interval |
|---------|-------------|----------|
| `vault` | `vault status` | 5s |
| `data-mcp-server` | `curl --cacert/--cert/--key ... https://localhost:8001/health` (mTLS) | 10s |
| `compute-mcp-server` | `curl --cacert/--cert/--key ... https://localhost:8002/health` (mTLS) | 10s |

You can check the Vault health endpoint directly from the host:

```bash
curl http://localhost:8200/v1/sys/health    # Vault
```

MCP server health endpoints are internal to the Docker network and require mTLS certificates. To check from within a container:

```bash
docker compose --env-file docker/.env exec data-mcp-server \
    curl --cacert /etc/mcp/certs/ca.crt --cert /etc/mcp/certs/server.crt \
         --key /etc/mcp/certs/server.key -f https://localhost:8001/health
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
- Port 8200 already in use

**Fix:**
```bash
# Check Vault logs
docker compose --env-file docker/.env logs vault
```

### vault-init fails

**Symptom:** `vault-init` exits with a non-zero code and downstream services do not start.

**Common causes:**
- Vault not healthy yet (should be handled by `depends_on`)
- Invalid GCP SA key file path or format
- Missing `DATA_AGENT_SA_EMAIL` / `COMPUTE_AGENT_SA_EMAIL` when `GCP_SA_KEY_FILE` is set

**Fix:**
```bash
docker compose --env-file docker/.env logs vault-init

# If state is stale, clear volumes and restart
docker compose --env-file docker/.env down -v
docker compose --env-file docker/.env up -d --build
```

### Vault Agent not rendering certificates

**Symptom:** `/etc/mcp/certs/` is empty in MCP server containers.

**Common causes:**
- vault-init did not write AppRole credentials
- AppRole policy misconfigured

**Fix:**
```bash
docker compose --env-file docker/.env logs vault-agent
docker compose --env-file docker/.env logs vault-init
```

### MCP servers fail health check

**Symptom:** `data-mcp-server` or `compute-mcp-server` stuck in "starting" state.

**Common causes:**
- Vault Agent hasn't rendered certificates yet
- Build errors in the Dockerfile

**Fix:**
```bash
docker compose --env-file docker/.env logs data-mcp-server
docker compose --env-file docker/.env logs vault-agent
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
