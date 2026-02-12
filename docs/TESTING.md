# Testing Guide

This document explains the test suite structure, how to run tests, and how to add new tests.

## Test categories

Tests are organised into three tiers based on their infrastructure requirements:

| Tier | Directory | Infrastructure required | Run command |
|------|-----------|----------------------|-------------|
| **Unit tests** | `tests/test_*.py` | None | `pytest -v` |
| **HTTP transport tests** | `tests/test_http_*.py` | None | `pytest tests/test_http_transport.py -v` |
| **Integration tests** | `tests/integration/` | Docker Compose stack (Vault + MCP servers) | `pytest tests/integration/ -v --run-integration` |

## Running tests

### All unit tests (no infrastructure)

```bash
source .venv/bin/activate
pytest -v
```

Integration tests are deselected by default (marked with `@pytest.mark.integration`).

### Specific test file

```bash
pytest tests/test_policy_engine.py -v
```

### Specific test class or method

```bash
pytest tests/test_policy_engine.py::TestPolicyResolution -v
pytest tests/test_policy_engine.py::TestPolicyResolution::test_operator_data_agent_gets_full_data_tools -v
```

### 5-minute TTL verification only

```bash
pytest tests/test_policy_engine.py -v -k "five_minute"
```

### Integration tests (requires Docker stack)

```bash
# Start the full Docker Compose stack first
docker compose --env-file docker/.env up -d --build

# Run integration tests
pytest tests/integration/ -v --run-integration

# Or use the convenience script
./scripts/run_integration_tests.sh
```

## Shared fixtures

Fixtures are defined in `tests/conftest.py` and automatically available to all tests.

### `policy_engine`

Returns a `PolicyEngine` loaded from the real `policies/capabilities.yaml` file.

```python
def test_example(policy_engine: PolicyEngine) -> None:
    policy = policy_engine.resolve("operator", "data_agent")
    assert "list_buckets" in policy.allowed_tools
```

### `operator_session`, `analyst_session`, `viewer_session`

Pre-built `Session` objects for each role with fake Vault tokens:

| Fixture | `human_id` | `human_role` | `ttl_seconds` |
|---------|-----------|-------------|---------------|
| `operator_session` | `alice` | `operator` | 3600 |
| `analyst_session` | `bob` | `analyst` | 1800 |
| `viewer_session` | `carol` | `viewer` | 900 |

```python
def test_example(operator_session: Session) -> None:
    assert operator_session.human_role == "operator"
    assert not operator_session.is_expired
```

## Unit test descriptions

### `test_policy_engine.py`

Tests the core access-control logic without any infrastructure.

| Test class | What it verifies |
|-----------|-----------------|
| `TestPolicyResolution` | Correct tool sets for each (role, agent) pair; unknown role/agent errors; 5-minute TTL for all roles |
| `TestSpiffeResolution` | SPIFFE ID → agent ID mapping; unknown SPIFFE ID errors |
| `TestPolicyReload` | Policy file reload; `list_roles()` returns all defined roles |

### `test_session.py`

Tests the immutable `Session` dataclass.

| What it verifies |
|-----------------|
| `is_expired` property returns `False` for fresh sessions |
| `is_expired` returns `True` for sessions past their TTL |
| Session is frozen (cannot mutate fields) |

### `test_identity_context.py`

Tests JSON serialisation round-trips for `IdentityContext`.

| What it verifies |
|-----------------|
| `to_json()` produces valid JSON |
| `from_json()` round-trips correctly |
| `allowed_tools` is sorted in JSON output |
| Optional `spiffe_id` field is handled correctly |

### `test_capability_filter.py`

End-to-end filtering: constructs an `IdentityContext` from policy resolution and verifies that only the allowed tools pass through.

### `test_gcp_credential_ttl.py`

Verifies the 5-minute TTL enforcement logic:

| What it verifies |
|-----------------|
| Policy engine resolves `"5m"` for all roles |
| `_parse_ttl_to_seconds()` correctly parses `"5m"` → 300 |
| Effective TTL is `min(vault_ttl, policy_max)` |

### `test_audit_logger.py`

Tests the `AuditLogger` and `JSONFormatter`:

| What it verifies |
|-----------------|
| Tool access events contain correct fields |
| Token hashing produces the expected 12-character prefix |
| Denied and allowed events use correct event types |
| Credential and session events are formatted correctly |

### `test_http_transport.py`

Tests the Starlette HTTP server without running a real MCP server:

| What it verifies |
|-----------------|
| `/health` endpoint returns `{"status": "ok"}` without auth |
| Requests without `X-Identity-Context` header return 401 |
| Malformed identity headers return 401 |

### `test_spiffe_authenticator.py`

Tests `SpiffeAuthenticator` with mocked SVID retrieval and Vault auth:

| What it verifies |
|-----------------|
| Successful SVID fetch and Vault login produce a `WorkloadSession` |
| Missing `py-spiffe` library raises a descriptive error |
| Vault authentication failure propagates correctly |

### `test_mcp_http_adapter.py`

Tests the HTTP client adapter with mocked HTTP connections:

| What it verifies |
|-----------------|
| `X-Identity-Context` header is correctly encoded |
| MCP tools are wrapped as LangChain `StructuredTool` objects |

## Integration test descriptions

### `tests/integration/test_credential_flow_e2e.py`

Full end-to-end: authenticate as a human, resolve policy, obtain a GCP token via Vault, and verify the token works against GCP APIs.

### `tests/integration/test_http_mcp_e2e.py`

Connect to MCP servers running in Docker over HTTP, list tools, and invoke a tool.

### `tests/integration/test_spiffe_auth_e2e.py`

Authenticate a workload container via SPIFFE/SPIRE and verify the resulting Vault token has the expected policies.

## pytest configuration

From `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = [
    "integration: requires Docker Compose stack (deselected by default)",
]
```

- `asyncio_mode = "auto"` — async test functions are automatically detected and run with `pytest-asyncio`.
- The `integration` marker allows selective execution of integration tests.

## Adding a new test

1. Create a test file in `tests/` (unit) or `tests/integration/` (integration).
2. Use the shared fixtures from `conftest.py` for sessions and policy engine.
3. For integration tests, add the `@pytest.mark.integration` decorator.
4. Run `pytest tests/your_test_file.py -v` to verify.

### Example unit test

```python
"""Tests for a new feature."""

from vault_mcp_agents.policy.engine import PolicyEngine


def test_new_feature(policy_engine: PolicyEngine) -> None:
    policy = policy_engine.resolve("operator", "data_agent")
    assert "list_buckets" in policy.allowed_tools
```

### Example integration test

```python
"""Integration test requiring Docker stack."""

import pytest

@pytest.mark.integration
async def test_end_to_end_flow() -> None:
    # This test requires the Docker Compose stack to be running
    ...
```
