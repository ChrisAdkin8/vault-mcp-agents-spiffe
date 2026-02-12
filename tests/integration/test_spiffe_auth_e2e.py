"""End-to-end tests for SPIFFE authentication.

These tests verify that Vault Enterprise's SPIFFE auth method is configured
and that workloads can authenticate using their SVIDs.
"""

from __future__ import annotations

import httpx
import pytest


pytestmark = pytest.mark.integration


class TestSpiffeAuthSetup:
    def test_spiffe_auth_method_enabled(self, vault_addr: str):
        """Verify the SPIFFE auth method is mounted in Vault."""
        resp = httpx.get(
            f"{vault_addr}/v1/sys/auth",
            headers={"X-Vault-Token": "dev-root-token"},
        )
        assert resp.status_code == 200
        auth_methods = resp.json().get("data", resp.json())
        assert "spiffe/" in auth_methods, f"SPIFFE not in auth methods: {list(auth_methods.keys())}"

    def test_spiffe_trust_domain_configured(self, vault_addr: str):
        """Verify the trust domain is set."""
        resp = httpx.get(
            f"{vault_addr}/v1/auth/spiffe/config",
            headers={"X-Vault-Token": "dev-root-token"},
        )
        assert resp.status_code == 200
        data = resp.json().get("data", {})
        assert data.get("trust_domain") == "vault-mcp-demo"

    def test_data_agent_role_exists(self, vault_addr: str):
        """Verify the data-agent SPIFFE role is configured."""
        resp = httpx.get(
            f"{vault_addr}/v1/auth/spiffe/roles/data-agent",
            headers={"X-Vault-Token": "dev-root-token"},
        )
        assert resp.status_code == 200

    def test_compute_agent_role_exists(self, vault_addr: str):
        """Verify the compute-agent SPIFFE role is configured."""
        resp = httpx.get(
            f"{vault_addr}/v1/auth/spiffe/roles/compute-agent",
            headers={"X-Vault-Token": "dev-root-token"},
        )
        assert resp.status_code == 200
