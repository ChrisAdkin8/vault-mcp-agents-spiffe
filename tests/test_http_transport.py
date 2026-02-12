"""Tests for the HTTP/Streamable HTTP MCP transport layer."""

from __future__ import annotations

import base64
import json
import logging
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from vault_mcp_agents.mcp.http_identity_middleware import (
    IDENTITY_HEADER,
    encode_identity_header,
)
from vault_mcp_agents.mcp.identity_context import IdentityContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_identity(**overrides) -> IdentityContext:
    defaults = dict(
        agent_id="data_agent",
        human_id="alice",
        human_role="operator",
        vault_token="s.test-token",
        allowed_tools=frozenset(["list_buckets", "read_object"]),
        gcp_impersonated_account="data-agent-gcp",
        max_gcp_token_ttl="5m",
        gcp_project="test-project",
        session_created_at="2025-01-01T00:00:00+00:00",
        session_ttl_seconds=3600,
    )
    defaults.update(overrides)
    return IdentityContext(**defaults)


def _make_test_app():
    """Build a minimal Starlette app with the identity middleware and health route."""
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    from vault_mcp_agents.mcp.http_identity_middleware import IdentityContextMiddleware

    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    async def protected(request: Request) -> JSONResponse:
        identity = request.state.identity_context
        return JSONResponse({
            "agent_id": identity.agent_id,
            "human_id": identity.human_id,
        })

    app = Starlette(routes=[
        Route("/health", endpoint=health, methods=["GET"]),
        Route("/protected", endpoint=protected, methods=["GET"]),
    ])
    app.add_middleware(IdentityContextMiddleware)
    return app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        app = _make_test_app()
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_health_requires_no_identity(self):
        """Health endpoint should NOT require the identity header."""
        app = _make_test_app()
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200


class TestIdentityMiddleware:
    def test_missing_identity_returns_401(self):
        app = _make_test_app()
        client = TestClient(app)
        resp = client.get("/protected")
        assert resp.status_code == 401
        assert "Missing" in resp.json()["error"]

    def test_malformed_base64_returns_401(self):
        app = _make_test_app()
        client = TestClient(app)
        resp = client.get("/protected", headers={IDENTITY_HEADER: "not-valid-base64!!!"})
        assert resp.status_code == 401
        assert "Malformed" in resp.json()["error"]

    def test_malformed_json_returns_401(self):
        app = _make_test_app()
        client = TestClient(app)
        encoded = base64.b64encode(b"not json").decode()
        resp = client.get("/protected", headers={IDENTITY_HEADER: encoded})
        assert resp.status_code == 401

    def test_valid_identity_is_parsed(self):
        identity = _make_identity()
        app = _make_test_app()
        client = TestClient(app)
        resp = client.get("/protected", headers={
            IDENTITY_HEADER: encode_identity_header(identity),
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == "data_agent"
        assert data["human_id"] == "alice"


class TestIdentityEncoding:
    def test_encode_decode_round_trip(self):
        identity = _make_identity()
        encoded = encode_identity_header(identity)
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        restored = IdentityContext.from_json(decoded_json)
        assert restored.agent_id == identity.agent_id
        assert restored.human_id == identity.human_id
        assert restored.allowed_tools == identity.allowed_tools

    def test_encoded_value_is_base64(self):
        identity = _make_identity()
        encoded = encode_identity_header(identity)
        # Should be valid base64 — no exception.
        decoded = base64.b64decode(encoded)
        assert len(decoded) > 0
