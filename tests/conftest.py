"""Shared fixtures for tests."""

from __future__ import annotations

import datetime
import pathlib

import pytest

from vault_mcp_agents.auth.session import Session
from vault_mcp_agents.policy.engine import PolicyEngine

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture
def policy_engine(tmp_path: pathlib.Path) -> PolicyEngine:
    """Return a PolicyEngine loaded from the real capabilities.yaml."""
    real_path = pathlib.Path(__file__).resolve().parents[1] / "policies" / "capabilities.yaml"
    return PolicyEngine(policy_path=real_path)


@pytest.fixture
def operator_session() -> Session:
    return Session(
        human_id="alice",
        human_role="operator",
        vault_token="s.fake-operator-token",
        token_policies=frozenset(["default", "operator-policy"]),
        created_at=datetime.datetime.now(datetime.UTC),
        ttl_seconds=3600,
    )


@pytest.fixture
def analyst_session() -> Session:
    return Session(
        human_id="bob",
        human_role="analyst",
        vault_token="s.fake-analyst-token",
        token_policies=frozenset(["default", "analyst-policy"]),
        created_at=datetime.datetime.now(datetime.UTC),
        ttl_seconds=1800,
    )


@pytest.fixture
def viewer_session() -> Session:
    return Session(
        human_id="carol",
        human_role="viewer",
        vault_token="s.fake-viewer-token",
        token_policies=frozenset(["default", "viewer-policy"]),
        created_at=datetime.datetime.now(datetime.UTC),
        ttl_seconds=900,
    )
