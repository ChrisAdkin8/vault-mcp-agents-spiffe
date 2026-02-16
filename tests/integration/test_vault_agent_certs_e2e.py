"""End-to-end tests for Vault Agent SVID certificate provisioning.

These tests verify that Vault Agent has rendered X.509 SVIDs with
SPIFFE URI SANs to the shared certificate volume, and that the PKI
infrastructure is correctly configured in Vault.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import httpx
import pytest


pytestmark = pytest.mark.integration

CERT_DIR = Path("/etc/mcp/certs")


class TestVaultAgentCerts:
    def test_cert_files_exist(self):
        """Verify that Vault Agent has rendered all three certificate files."""
        assert (CERT_DIR / "server.crt").is_file(), "server.crt not found"
        assert (CERT_DIR / "server.key").is_file(), "server.key not found"
        assert (CERT_DIR / "ca.crt").is_file(), "ca.crt not found"

    def test_certificate_has_spiffe_uri_san(self):
        """Verify the rendered certificate contains the expected SPIFFE URI SAN."""
        result = subprocess.run(
            ["openssl", "x509", "-in", str(CERT_DIR / "server.crt"), "-text", "-noout"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "spiffe://my-trust-domain/ns/default/sa/mcp" in result.stdout, (
            f"SPIFFE URI SAN not found in certificate:\n{result.stdout}"
        )

    def test_certificate_common_name(self):
        """Verify the certificate CN is 'mcp-server'."""
        result = subprocess.run(
            ["openssl", "x509", "-in", str(CERT_DIR / "server.crt"), "-subject", "-noout"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "mcp-server" in result.stdout

    def test_ca_certificate_is_valid(self):
        """Verify the CA certificate is parseable and is a CA cert."""
        result = subprocess.run(
            ["openssl", "x509", "-in", str(CERT_DIR / "ca.crt"), "-text", "-noout"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "CA:TRUE" in result.stdout or "MCP Root CA" in result.stdout

    def test_server_cert_verifies_against_ca(self):
        """Verify the server certificate was issued by the CA."""
        result = subprocess.run(
            [
                "openssl", "verify",
                "-CAfile", str(CERT_DIR / "ca.crt"),
                str(CERT_DIR / "server.crt"),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Certificate verification failed: {result.stderr}"


class TestVaultPKISetup:
    def test_pki_mount_exists(self, vault_addr: str):
        """Verify the PKI secrets engine is mounted in Vault."""
        resp = httpx.get(
            f"{vault_addr}/v1/sys/mounts",
            headers={"X-Vault-Token": "dev-root-token"},
        )
        assert resp.status_code == 200
        mounts = resp.json().get("data", resp.json())
        assert "pki/" in mounts, f"PKI mount not found: {list(mounts.keys())}"

    def test_approle_auth_enabled(self, vault_addr: str):
        """Verify AppRole auth backend is enabled."""
        resp = httpx.get(
            f"{vault_addr}/v1/sys/auth",
            headers={"X-Vault-Token": "dev-root-token"},
        )
        assert resp.status_code == 200
        auth_methods = resp.json().get("data", resp.json())
        assert "approle/" in auth_methods, f"AppRole not in auth methods: {list(auth_methods.keys())}"

    def test_mcp_role_exists(self, vault_addr: str):
        """Verify the mcp-role AppRole role is configured."""
        resp = httpx.get(
            f"{vault_addr}/v1/auth/approle/role/mcp-role",
            headers={"X-Vault-Token": "dev-root-token"},
        )
        assert resp.status_code == 200

    def test_pki_role_exists(self, vault_addr: str):
        """Verify the mcp-server PKI role is configured."""
        resp = httpx.get(
            f"{vault_addr}/v1/pki/roles/mcp-server",
            headers={"X-Vault-Token": "dev-root-token"},
        )
        assert resp.status_code == 200
