# CLAUDE.md

# Project
LangChain agents > MCP servers > Vault (5-min GCP creds, SPIFFE). Py3.11+, hatchling.

## Structure
- `src/vault_mcp_agents/`: App code (auth, vault, policy, mcp, agents)
- `config/`: `settings.yaml` (App), `agent.hcl` (Vault sidecar)
- `policies/capabilities.yaml`: Role/Tool/SPIFFE rules
- `scripts/`: `vault_init.sh` (Prod), `setup_vault.sh` (Dev)
- `terraform/`: GCP IAM only
- `docker-compose.yaml`: Full stack (Vault → MCP → Agent)

## Commands
```sh
# Setup
python3.13 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"

# Test & Lint
pytest                                          # Unit (-k five for TTL)
pytest tests/integration/ -v --run-integration  # Needs Docker
ruff check src/ tests/ && mypy src/

# Docker (Context: docker/.env)
export DC="docker compose --env-file docker/.env"
$DC up -d --build
$DC logs vault-init
$DC exec agent-cli vault-mcp-agents