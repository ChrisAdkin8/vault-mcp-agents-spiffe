# Development Guide

This document covers setting up a development environment, project conventions, and how to extend the codebase.

## Prerequisites

- **Python 3.11 – 3.13** (3.14 is not supported due to LangChain/Pydantic runtime type evaluation changes)
- **Docker** (for local Vault)
- **Terraform >= 1.5** (for GCP secrets engine provisioning)
- **gcloud CLI** (authenticated with `gcloud auth application-default login`)

## Setting up the development environment

### 1. Clone and install

```bash
git clone <repo-url>
cd vault-mcp-agents

# Create virtual environment (use 3.13 if 3.14 is your default)
python3.13 -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

### 2. Start Vault (local development)

```bash
# Start Vault OSS in dev mode
docker compose -f docker-compose.dev.yaml up -d

export VAULT_ADDR=http://127.0.0.1:8200
export VAULT_TOKEN=dev-root-token

# Configure users, policies, and auth methods
bash scripts/setup_vault.sh
```

### 3. Configure GCP (if testing with real GCP resources)

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars — set gcp_project_id
terraform init && terraform apply
cd ..
```

Update `config/settings.yaml` with your GCP project ID.

### 4. Set LLM API key

```bash
export ANTHROPIC_API_KEY=sk-ant-...
# or
export OPENAI_API_KEY=sk-...
```

### 5. Run the application

```bash
vault-mcp-agents
# or with debug logging
python -m vault_mcp_agents.main --verbose
```

### 6. Run tests

```bash
pytest -v
```

## Project conventions

### Code style

- **Formatter/linter:** [Ruff](https://docs.astral.sh/ruff/) (configured in `pyproject.toml`)
- **Type checking:** [mypy](https://mypy-lang.org/) with `strict = true`
- **Line length:** 100 characters
- **Target Python:** 3.11

```bash
# Run linter
ruff check src/ tests/

# Run type checker
mypy src/
```

### Ruff rules enabled

From `pyproject.toml`:

| Rule set | Description |
|----------|-------------|
| `E` | pycodestyle errors |
| `F` | pyflakes |
| `I` | isort (import sorting) |
| `N` | pep8-naming |
| `W` | pycodestyle warnings |
| `UP` | pyupgrade (modern Python) |
| `B` | flake8-bugbear |
| `SIM` | flake8-simplify |

### Module docstrings

Every module begins with a docstring explaining the **pattern** it implements. This convention helps both humans and AI coding assistants understand the design intent:

```python
"""Human authentication against HashiCorp Vault.

Pattern: Vault as Identity Broker
----------------------------------
Vault is the single source of truth for both *who the human is* and *what
secrets they may access*.
"""
```

### Immutable dataclasses

All security-critical data structures use `frozen=True` dataclasses. This prevents accidental mutation after creation:

```python
@dataclasses.dataclass(frozen=True)
class Session:
    human_id: str
    human_role: str
    vault_token: str
    ...
```

### Async conventions

- MCP servers, agent construction, and GCP clients are all async.
- Tests use `pytest-asyncio` with `asyncio_mode = "auto"`.
- The CLI uses `asyncio.run()` as the top-level async entry point.

## How to extend the project

### Adding a new MCP tool

1. **Add the handler** to the relevant server class (`data_server.py` or `compute_server.py`):

```python
async def _my_new_tool(
    self,
    args: dict[str, Any],
    gcp_token: Callable[[], GCPAccessToken],
) -> list[TextContent]:
    token = gcp_token()
    # ... implement tool logic ...
    return [TextContent(type="text", text=json.dumps({"result": "ok"}))]
```

2. **Register it** in `_register_all_tools()`:

```python
self._register_tool(
    name="my_new_tool",
    description="Description for the LLM.",
    input_schema={
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "..."},
        },
        "required": ["param1"],
    },
    handler=self._my_new_tool,
)
```

3. **Add to policy** in `policies/capabilities.yaml`:

```yaml
roles:
  operator:
    agents:
      data_agent:
        allowed_tools:
          - "my_new_tool"   # Add here
          - "list_buckets"
          # ...
```

4. **Write a test** — the policy engine tests will catch missing entries:

```bash
pytest tests/test_policy_engine.py -v
```

### Adding a new role

1. **Create a Vault policy** (e.g. `auditor-policy`) in `scripts/setup_vault.sh`:

```bash
vault policy write auditor-policy - <<EOF
path "gcp/impersonated-account/data-agent-gcp/token" {
  capabilities = ["read"]
}
EOF
```

2. **Add the role mapping** in `vault_authenticator.py`:

```python
_POLICY_TO_ROLE: list[tuple[str, str]] = [
    ("operator-policy", "operator"),
    ("analyst-policy", "analyst"),
    ("auditor-policy", "auditor"),    # New role
    ("viewer-policy", "viewer"),
]
```

3. **Add the role block** in `policies/capabilities.yaml`:

```yaml
roles:
  auditor:
    vault_policy: "auditor-policy"
    agents:
      data_agent:
        allowed_tools:
          - "list_buckets"
          - "read_object"
        max_gcp_token_ttl: "5m"
```

4. **Create a test user** in `scripts/setup_vault.sh`:

```bash
vault write auth/userpass/users/dave password="dave-pass" policies="auditor-policy"
```

### Adding a new agent

1. **Create an MCP server** class in `src/vault_mcp_agents/mcp/`:

```python
class NetworkMCPServer(BaseMCPServer):
    def __init__(self) -> None:
        super().__init__("network-server")
        self._register_all_tools()

    def _register_all_tools(self) -> None:
        self._register_tool(...)
```

2. **Add agent config** in `config/settings.yaml`:

```yaml
agents:
  network_agent:
    description: "Handles network operations"
    mcp_server: "network_server"
    vault_role: "network-agent-role"
    gcp_impersonated_account: "network-agent-gcp"

mcp_servers:
  network_server:
    transport: "stdio"
    command: "python"
    args: ["-m", "vault_mcp_agents.mcp.network_server"]
    url: "http://network-mcp-server:8003/mcp"
```

3. **Add to capabilities.yaml** with per-role tool lists.

4. **Add to the CLI** in `prompt/cli.py`:

```python
AGENT_CHOICES = {
    "1": "data_agent",
    "2": "compute_agent",
    "3": "network_agent",
}
```

### Switching LLM providers

Change the `llm` section in `config/settings.yaml`:

```yaml
llm:
  provider: "openai"           # Switch from anthropic to openai
  model: "gpt-4o"
  temperature: 0.0
```

Set the corresponding API key:

```bash
export OPENAI_API_KEY=sk-...
```

No code changes are required.

### Switching authentication methods

Change `vault.auth_method` in `settings.yaml` to `ldap` or `oidc`. The `VaultAuthenticator._login()` method delegates to the corresponding `hvac` auth backend.

For OIDC, additional Vault configuration is required — see the [Vault OIDC documentation](https://developer.hashicorp.com/vault/docs/auth/jwt/oidc-providers).

## Local development with Docker Compose

The `docker-compose.dev.yaml` file provides Vault OSS for local development:

```bash
# Start Vault only (MCP servers run as local subprocesses)
docker compose -f docker-compose.dev.yaml up -d

# Configure Vault
export VAULT_ADDR=http://127.0.0.1:8200
export VAULT_TOKEN=dev-root-token
bash scripts/setup_vault.sh
```

To test with the full containerised stack (Vault Enterprise + MCP servers + agent CLI):

```bash
# Create environment file
cp docker/.env.example docker/.env
# Edit docker/.env — add VAULT_LICENSE and ANTHROPIC_API_KEY

# Start everything
docker compose --env-file docker/.env up -d --build
```

## Dependency management

Dependencies are declared in `pyproject.toml`:

| Section | Purpose |
|---------|---------|
| `dependencies` | Runtime dependencies |
| `project.optional-dependencies.dev` | Development dependencies (pytest, ruff, mypy, httpx) |

To update dependencies:

```bash
pip install -e ".[dev]"
```

## Key design decisions

| Decision | Rationale |
|----------|-----------|
| Frozen dataclasses for identity | Prevents accidental mutation of security-critical state |
| YAML policy file (not database) | Version-controllable, auditable, testable without Vault |
| Environment variable for stdio identity | Simplest side-channel for subprocess communication |
| Thin MCP → LangChain adapter | Keeps access control in the MCP server, not the adapter |
| Factory pattern for agent construction | Encapsulates 5-step construction sequence away from CLI |
| Audit token hashing | Enables correlation without logging sensitive tokens |
| Dual transport support | Stdio for development speed, HTTP for container deployment |
