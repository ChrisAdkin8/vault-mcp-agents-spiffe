"""Tests for SPIFFE workload authentication."""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

import pytest

from vault_mcp_agents.auth.spiffe_authenticator import (
    SpiffeAuthenticationError,
    SpiffeAuthenticator,
)
from vault_mcp_agents.auth.workload_session import WorkloadSession


# ---------------------------------------------------------------------------
# WorkloadSession tests
# ---------------------------------------------------------------------------


class TestWorkloadSession:
    def test_not_expired_when_fresh(self):
        ws = WorkloadSession(
            spiffe_id="spiffe://vault-mcp-demo/agent/data_agent",
            vault_token="s.test",
            token_policies=frozenset(["operator-policy"]),
            created_at=datetime.datetime.now(datetime.UTC),
            ttl_seconds=3600,
        )
        assert not ws.is_expired

    def test_expired_when_ttl_exceeded(self):
        ws = WorkloadSession(
            spiffe_id="spiffe://vault-mcp-demo/agent/data_agent",
            vault_token="s.test",
            token_policies=frozenset(["operator-policy"]),
            created_at=datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=2),
            ttl_seconds=60,
        )
        assert ws.is_expired

    def test_immutable(self):
        ws = WorkloadSession(
            spiffe_id="spiffe://vault-mcp-demo/agent/data_agent",
            vault_token="s.test",
            token_policies=frozenset(["operator-policy"]),
            created_at=datetime.datetime.now(datetime.UTC),
            ttl_seconds=3600,
        )
        with pytest.raises(AttributeError):
            ws.spiffe_id = "modified"  # type: ignore[misc]

    def test_str_contains_spiffe_id(self):
        ws = WorkloadSession(
            spiffe_id="spiffe://vault-mcp-demo/agent/data_agent",
            vault_token="s.test",
            token_policies=frozenset(["operator-policy"]),
            created_at=datetime.datetime.now(datetime.UTC),
            ttl_seconds=3600,
        )
        assert "data_agent" in str(ws)


# ---------------------------------------------------------------------------
# SpiffeAuthenticator tests
# ---------------------------------------------------------------------------


class TestSpiffeAuthenticator:
    def test_authenticate_workload_success(self):
        auth = SpiffeAuthenticator(
            vault_addr="http://vault:8200",
            trust_domain="vault-mcp-demo",
        )

        mock_svid = MagicMock()
        mock_svid.spiffe_id = "spiffe://vault-mcp-demo/agent/data_agent"
        mock_svid.cert_chain_pem = b"FAKE-CERT"
        mock_svid.private_key_pem = b"FAKE-KEY"

        mock_workload_client_cls = MagicMock()
        mock_workload_client_cls.return_value.fetch_x509_svid.return_value = mock_svid

        mock_spiffe_module = MagicMock()
        mock_spiffe_module.WorkloadApiClient = mock_workload_client_cls

        mock_hvac = MagicMock()
        mock_hvac.auth.cert.login.return_value = {
            "auth": {
                "client_token": "s.spiffe-token",
                "policies": ["default", "operator-policy"],
                "lease_duration": 3600,
            }
        }

        with (
            patch.dict("sys.modules", {"spiffe": mock_spiffe_module}),
            patch("vault_mcp_agents.auth.spiffe_authenticator.hvac.Client", return_value=mock_hvac),
            patch.dict("os.environ", {"SPIFFE_ENDPOINT_SOCKET": "unix:///tmp/test.sock"}),
        ):
            session = auth.authenticate_workload()

        assert isinstance(session, WorkloadSession)
        assert session.spiffe_id == "spiffe://vault-mcp-demo/agent/data_agent"
        assert session.vault_token == "s.spiffe-token"
        assert "operator-policy" in session.token_policies

    def test_authenticate_workload_no_svid_raises(self):
        auth = SpiffeAuthenticator(
            vault_addr="http://vault:8200",
            trust_domain="vault-mcp-demo",
        )

        mock_workload_client_cls = MagicMock()
        mock_workload_client_cls.return_value.fetch_x509_svid.side_effect = RuntimeError("No SVID available")

        mock_spiffe_module = MagicMock()
        mock_spiffe_module.WorkloadApiClient = mock_workload_client_cls

        with (
            patch.dict("sys.modules", {"spiffe": mock_spiffe_module}),
            patch.dict("os.environ", {"SPIFFE_ENDPOINT_SOCKET": "unix:///tmp/test.sock"}),
        ):
            with pytest.raises(SpiffeAuthenticationError, match="Failed to fetch"):
                auth.authenticate_workload()

    def test_authenticate_workload_vault_rejects(self):
        auth = SpiffeAuthenticator(
            vault_addr="http://vault:8200",
            trust_domain="vault-mcp-demo",
        )

        mock_svid = MagicMock()
        mock_svid.spiffe_id = "spiffe://vault-mcp-demo/agent/data_agent"
        mock_svid.cert_chain_pem = b"FAKE-CERT"
        mock_svid.private_key_pem = b"FAKE-KEY"

        mock_workload_client_cls = MagicMock()
        mock_workload_client_cls.return_value.fetch_x509_svid.return_value = mock_svid

        mock_spiffe_module = MagicMock()
        mock_spiffe_module.WorkloadApiClient = mock_workload_client_cls

        import hvac.exceptions

        mock_hvac = MagicMock()
        mock_hvac.auth.cert.login.side_effect = hvac.exceptions.VaultError("Forbidden")

        with (
            patch.dict("sys.modules", {"spiffe": mock_spiffe_module}),
            patch("vault_mcp_agents.auth.spiffe_authenticator.hvac.Client", return_value=mock_hvac),
            patch.dict("os.environ", {"SPIFFE_ENDPOINT_SOCKET": "unix:///tmp/test.sock"}),
        ):
            with pytest.raises(SpiffeAuthenticationError, match="Vault SPIFFE authentication failed"):
                auth.authenticate_workload()

    def test_spiffe_import_error_raises(self):
        """If py-spiffe is not installed, a clear error is raised."""
        auth = SpiffeAuthenticator(
            vault_addr="http://vault:8200",
            trust_domain="vault-mcp-demo",
        )

        with patch.dict("sys.modules", {"spiffe": None}):
            with pytest.raises(SpiffeAuthenticationError, match="py-spiffe library is required"):
                auth.authenticate_workload()

    def test_is_enabled_checks_env_var(self):
        auth = SpiffeAuthenticator(
            vault_addr="http://vault:8200",
            trust_domain="vault-mcp-demo",
        )

        with patch.dict("os.environ", {}, clear=True):
            assert not auth.is_enabled()

        with patch.dict("os.environ", {"SPIFFE_ENDPOINT_SOCKET": "unix:///tmp/test.sock"}):
            assert auth.is_enabled()
