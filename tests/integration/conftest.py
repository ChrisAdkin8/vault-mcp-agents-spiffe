"""Fixtures for integration tests.

These tests require the Docker Compose stack to be running.
They are skipped by default unless ``--run-integration`` is passed to pytest.
"""

from __future__ import annotations

import os

import httpx
import pytest

from vault_mcp_agents.mcp.identity_context import IdentityContext
from vault_mcp_agents.mcp.http_identity_middleware import encode_identity_header


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests that require Docker Compose stack",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: requires Docker Compose stack")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-integration"):
        skip_integration = pytest.mark.skip(reason="Need --run-integration to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)


# ---------------------------------------------------------------------------
# Server URLs — configurable via env vars for CI flexibility.
# ---------------------------------------------------------------------------

DATA_SERVER_URL = os.environ.get("DATA_MCP_SERVER_URL", "http://localhost:8001")
COMPUTE_SERVER_URL = os.environ.get("COMPUTE_MCP_SERVER_URL", "http://localhost:8002")
VAULT_ADDR = os.environ.get("VAULT_ADDR", "http://localhost:8200")


@pytest.fixture
def data_server_url() -> str:
    return DATA_SERVER_URL


@pytest.fixture
def compute_server_url() -> str:
    return COMPUTE_SERVER_URL


@pytest.fixture
def vault_addr() -> str:
    return VAULT_ADDR


def _make_identity_context(
    agent_id: str = "data_agent",
    human_id: str = "alice",
    human_role: str = "operator",
) -> IdentityContext:
    return IdentityContext(
        agent_id=agent_id,
        human_id=human_id,
        human_role=human_role,
        vault_token="s.integration-test-token",
        allowed_tools=frozenset([
            "list_buckets", "read_object", "write_object", "delete_object",
            "query_bigquery", "list_datasets", "create_dataset",
            "list_instances", "get_instance", "start_instance",
            "stop_instance", "create_instance", "delete_instance",
        ]),
        gcp_impersonated_account=f"{agent_id.replace('_', '-')}-gcp",
        max_gcp_token_ttl="5m",
        gcp_project="test-project",
        session_created_at="2025-01-01T00:00:00+00:00",
        session_ttl_seconds=3600,
    )


@pytest.fixture
def operator_identity() -> IdentityContext:
    return _make_identity_context("data_agent", "alice", "operator")


@pytest.fixture
def viewer_identity() -> IdentityContext:
    return _make_identity_context(
        agent_id="data_agent",
        human_id="carol",
        human_role="viewer",
    )


@pytest.fixture
def identity_header(operator_identity: IdentityContext) -> dict[str, str]:
    return {"X-Identity-Context": encode_identity_header(operator_identity)}
