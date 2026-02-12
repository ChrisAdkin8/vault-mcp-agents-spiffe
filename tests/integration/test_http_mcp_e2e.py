"""End-to-end tests for HTTP MCP transport.

These tests verify that the MCP servers respond correctly over HTTP when
the Docker Compose stack is running.
"""

from __future__ import annotations

import httpx
import pytest

from vault_mcp_agents.mcp.http_identity_middleware import encode_identity_header
from vault_mcp_agents.mcp.identity_context import IdentityContext


pytestmark = pytest.mark.integration


class TestHealthChecks:
    def test_data_server_health(self, data_server_url: str):
        resp = httpx.get(f"{data_server_url}/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_compute_server_health(self, compute_server_url: str):
        resp = httpx.get(f"{compute_server_url}/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestIdentityEnforcement:
    def test_missing_identity_returns_401(self, data_server_url: str):
        resp = httpx.post(f"{data_server_url}/mcp")
        assert resp.status_code == 401

    def test_malformed_identity_returns_401(self, data_server_url: str):
        resp = httpx.post(
            f"{data_server_url}/mcp",
            headers={"X-Identity-Context": "not-valid"},
        )
        assert resp.status_code == 401


class TestMCPProtocol:
    def test_mcp_endpoint_accepts_post(
        self,
        data_server_url: str,
        identity_header: dict[str, str],
    ):
        """The MCP endpoint should accept POST requests with valid identity."""
        resp = httpx.post(
            f"{data_server_url}/mcp",
            headers={
                **identity_header,
                "Content-Type": "application/json",
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0.0"},
                },
            },
        )
        # Should get a valid JSON-RPC response (200) or protocol-level response.
        assert resp.status_code in (200, 202, 204)


class TestVaultConnectivity:
    def test_vault_is_reachable(self, vault_addr: str):
        resp = httpx.get(f"{vault_addr}/v1/sys/health")
        assert resp.status_code == 200
