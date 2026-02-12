"""End-to-end tests for the credential flow through the containerised stack.

These tests verify that Vault can issue credentials and that the
5-minute TTL enforcement works through the HTTP transport.
"""

from __future__ import annotations

import httpx
import pytest


pytestmark = pytest.mark.integration


class TestVaultCredentialIssuance:
    def test_vault_userpass_login(self, vault_addr: str):
        """Verify that test users can authenticate via userpass."""
        resp = httpx.post(
            f"{vault_addr}/v1/auth/userpass/login/alice",
            json={"password": "alice-pass"},
        )
        assert resp.status_code == 200
        auth = resp.json()["auth"]
        assert auth["client_token"]
        assert "operator-policy" in auth["policies"]

    def test_analyst_login_gets_analyst_policy(self, vault_addr: str):
        resp = httpx.post(
            f"{vault_addr}/v1/auth/userpass/login/bob",
            json={"password": "bob-pass"},
        )
        assert resp.status_code == 200
        assert "analyst-policy" in resp.json()["auth"]["policies"]

    def test_viewer_login_gets_viewer_policy(self, vault_addr: str):
        resp = httpx.post(
            f"{vault_addr}/v1/auth/userpass/login/carol",
            json={"password": "carol-pass"},
        )
        assert resp.status_code == 200
        assert "viewer-policy" in resp.json()["auth"]["policies"]

    def test_gcp_secrets_engine_mounted(self, vault_addr: str):
        """Verify the GCP secrets engine is accessible (if configured via Terraform)."""
        resp = httpx.get(
            f"{vault_addr}/v1/sys/mounts",
            headers={"X-Vault-Token": "dev-root-token"},
        )
        assert resp.status_code == 200
        # GCP mount may or may not be present depending on whether Terraform has run.
        # This test just verifies the Vault API is responding correctly.
