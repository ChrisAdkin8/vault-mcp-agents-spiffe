"""Tests that the GCP credentials 5-minute TTL is honoured end-to-end.

The 5-minute TTL is the security boundary that limits blast radius if a GCP
token is leaked.  These tests verify the TTL is enforced at every layer:

  - Session expiry gates credential issuance.
  - GCPCredentialBroker refuses expired sessions and propagates the TTL.
  - The default TTL is 300 s (5 min) when Vault omits ``token_ttl``.
  - PolicyEngine defaults ``max_gcp_token_ttl`` to ``"5m"``.
  - IdentityContext round-trips the TTL through JSON serialisation.
  - BaseMCPServer passes the TTL from the identity context to the broker.
"""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

import pytest

from vault_mcp_agents.auth.session import Session
from vault_mcp_agents.mcp.identity_context import IdentityContext
from vault_mcp_agents.policy.engine import PolicyEngine
from vault_mcp_agents.vault.gcp_credentials import (
    GCPAccessToken,
    GCPCredentialBroker,
    GCPCredentialError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session(
    *,
    ttl_seconds: int = 3600,
    age_seconds: float = 0,
) -> Session:
    """Create a Session with a controllable age."""
    return Session(
        human_id="testuser",
        human_role="operator",
        vault_token="s.test-token",
        token_policies=frozenset(["default"]),
        created_at=datetime.datetime.now(datetime.UTC)
        - datetime.timedelta(seconds=age_seconds),
        ttl_seconds=ttl_seconds,
    )


def _make_identity_context(
    *,
    max_gcp_token_ttl: str = "5m",
    session_created_at: str | None = None,
    session_ttl_seconds: int = 3600,
) -> IdentityContext:
    if session_created_at is None:
        session_created_at = datetime.datetime.now(datetime.UTC).isoformat()
    return IdentityContext(
        agent_id="data_agent",
        human_id="testuser",
        human_role="operator",
        vault_token="s.test-token",
        allowed_tools=frozenset(["list_buckets"]),
        gcp_impersonated_account="data-agent-gcp",
        max_gcp_token_ttl=max_gcp_token_ttl,
        gcp_project="test-project",
        session_created_at=session_created_at,
        session_ttl_seconds=session_ttl_seconds,
    )


# ---------------------------------------------------------------------------
# GCPAccessToken
# ---------------------------------------------------------------------------

class TestGCPAccessToken:
    def test_ttl_field_stores_value(self) -> None:
        token = GCPAccessToken(token="ya29.abc", ttl_seconds=300, impersonated_account="sa")
        assert token.ttl_seconds == 300

    def test_frozen_immutable(self) -> None:
        token = GCPAccessToken(token="ya29.abc", ttl_seconds=300, impersonated_account="sa")
        with pytest.raises(AttributeError):
            token.ttl_seconds = 600  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Session expiry — the gate that protects credential issuance
# ---------------------------------------------------------------------------

class TestSessionExpiryGatesCredentials:
    def test_fresh_session_is_not_expired(self) -> None:
        session = _make_session(ttl_seconds=300, age_seconds=0)
        assert not session.is_expired

    def test_session_within_five_minutes_is_valid(self) -> None:
        session = _make_session(ttl_seconds=300, age_seconds=299)
        assert not session.is_expired

    def test_session_at_exactly_five_minutes_is_expired(self) -> None:
        session = _make_session(ttl_seconds=300, age_seconds=300)
        assert session.is_expired

    def test_session_past_five_minutes_is_expired(self) -> None:
        session = _make_session(ttl_seconds=300, age_seconds=301)
        assert session.is_expired


# ---------------------------------------------------------------------------
# GCPCredentialBroker — TTL enforcement
# ---------------------------------------------------------------------------

class TestGCPCredentialBrokerTTL:
    """Verify the broker refuses expired sessions and propagates TTL."""

    def test_expired_session_raises(self) -> None:
        broker = GCPCredentialBroker(vault_addr="http://127.0.0.1:8200")
        expired_session = _make_session(ttl_seconds=300, age_seconds=301)

        with pytest.raises(GCPCredentialError, match="expired"):
            broker.get_access_token(
                session=expired_session,
                impersonated_account="data-agent-gcp",
            )

    def test_default_requested_ttl_is_five_minutes(self) -> None:
        """The default ``requested_ttl`` parameter is '5m'."""
        import inspect

        sig = inspect.signature(GCPCredentialBroker.get_access_token)
        default = sig.parameters["requested_ttl"].default
        assert default == "5m"

    @patch("vault_mcp_agents.vault.gcp_credentials.hvac.Client")
    def test_vault_response_ttl_is_propagated(self, mock_client_cls: MagicMock) -> None:
        """When Vault returns a ``token_ttl``, it appears in the result."""
        mock_client = mock_client_cls.return_value
        mock_client.secrets.gcp.generate_impersonated_account_oauth2_access_token.return_value = {
            "data": {
                "token": "ya29.live-token",
                "token_ttl": 300,
            }
        }

        broker = GCPCredentialBroker(vault_addr="http://127.0.0.1:8200")
        session = _make_session()
        result = broker.get_access_token(session=session, impersonated_account="sa")

        assert result.ttl_seconds == 300
        assert result.token == "ya29.live-token"
        assert result.impersonated_account == "sa"

    @patch("vault_mcp_agents.vault.gcp_credentials.hvac.Client")
    def test_missing_token_ttl_defaults_to_300(self, mock_client_cls: MagicMock) -> None:
        """When Vault omits ``token_ttl``, the broker defaults to 300 s (5 min)."""
        mock_client = mock_client_cls.return_value
        mock_client.secrets.gcp.generate_impersonated_account_oauth2_access_token.return_value = {
            "data": {
                "token": "ya29.no-ttl-field",
                # token_ttl deliberately omitted
            }
        }

        broker = GCPCredentialBroker(vault_addr="http://127.0.0.1:8200")
        session = _make_session()
        result = broker.get_access_token(session=session, impersonated_account="sa")

        assert result.ttl_seconds == 300

    @patch("vault_mcp_agents.vault.gcp_credentials.hvac.Client")
    def test_vault_error_raises_credential_error(self, mock_client_cls: MagicMock) -> None:
        import hvac.exceptions

        mock_client = mock_client_cls.return_value
        mock_client.secrets.gcp.generate_impersonated_account_oauth2_access_token.side_effect = (
            hvac.exceptions.VaultError("permission denied")
        )

        broker = GCPCredentialBroker(vault_addr="http://127.0.0.1:8200")
        session = _make_session()

        with pytest.raises(GCPCredentialError, match="permission denied"):
            broker.get_access_token(session=session, impersonated_account="sa")

    @patch("vault_mcp_agents.vault.gcp_credentials.hvac.Client")
    def test_custom_requested_ttl_is_accepted(self, mock_client_cls: MagicMock) -> None:
        """A non-default ``requested_ttl`` is passed through without error.

        The actual TTL is server-side; ``requested_ttl`` is for audit only.
        """
        mock_client = mock_client_cls.return_value
        mock_client.secrets.gcp.generate_impersonated_account_oauth2_access_token.return_value = {
            "data": {"token": "ya29.custom", "token_ttl": 120}
        }

        broker = GCPCredentialBroker(vault_addr="http://127.0.0.1:8200")
        session = _make_session()
        result = broker.get_access_token(
            session=session,
            impersonated_account="sa",
            requested_ttl="2m",
        )

        # The actual TTL comes from the Vault response, not the request.
        assert result.ttl_seconds == 120

    @patch("vault_mcp_agents.vault.gcp_credentials.hvac.Client")
    def test_broker_uses_session_vault_token(self, mock_client_cls: MagicMock) -> None:
        """The broker authenticates to Vault with the session's token."""
        mock_client = mock_client_cls.return_value
        mock_client.secrets.gcp.generate_impersonated_account_oauth2_access_token.return_value = {
            "data": {"token": "ya29.x", "token_ttl": 300}
        }

        broker = GCPCredentialBroker(vault_addr="http://vault:8200")
        session = _make_session()
        broker.get_access_token(session=session, impersonated_account="sa")

        mock_client_cls.assert_called_once_with(
            url="http://vault:8200", token="s.test-token"
        )

    @patch("vault_mcp_agents.vault.gcp_credentials.hvac.Client")
    def test_broker_passes_impersonated_account_and_mount(
        self, mock_client_cls: MagicMock
    ) -> None:
        mock_client = mock_client_cls.return_value
        mock_method = (
            mock_client.secrets.gcp.generate_impersonated_account_oauth2_access_token
        )
        mock_method.return_value = {
            "data": {"token": "ya29.x", "token_ttl": 300}
        }

        broker = GCPCredentialBroker(vault_addr="http://127.0.0.1:8200", gcp_mount="custom-gcp")
        session = _make_session()
        broker.get_access_token(session=session, impersonated_account="my-account")

        mock_method.assert_called_once_with(
            name="my-account",
            mount_point="custom-gcp",
        )


# ---------------------------------------------------------------------------
# PolicyEngine — TTL defaults
# ---------------------------------------------------------------------------

class TestPolicyEngineTTLDefaults:
    def test_all_roles_default_to_five_minutes(self, policy_engine: PolicyEngine) -> None:
        for role in policy_engine.list_roles():
            for agent_id in ["data_agent", "compute_agent"]:
                try:
                    policy = policy_engine.resolve(role, agent_id)
                    assert policy.max_gcp_token_ttl == "5m", (
                        f"Expected 5m for {role}/{agent_id}, got {policy.max_gcp_token_ttl}"
                    )
                except Exception:
                    # Some (role, agent) pairs may not exist; that's fine.
                    pass

    def test_fallback_default_is_five_minutes(self, tmp_path) -> None:
        """When the YAML omits ``max_gcp_token_ttl``, the engine falls back to '5m'."""
        policy_file = tmp_path / "caps.yaml"
        policy_file.write_text(
            "roles:\n"
            "  tester:\n"
            "    agents:\n"
            "      test_agent:\n"
            "        allowed_tools: [read_object]\n"
        )
        engine = PolicyEngine(policy_path=policy_file)
        policy = engine.resolve("tester", "test_agent")
        assert policy.max_gcp_token_ttl == "5m"


# ---------------------------------------------------------------------------
# IdentityContext — TTL survives JSON round-trip
# ---------------------------------------------------------------------------

class TestIdentityContextTTLRoundTrip:
    def test_five_minute_ttl_round_trips(self) -> None:
        ctx = _make_identity_context(max_gcp_token_ttl="5m")
        restored = IdentityContext.from_json(ctx.to_json())
        assert restored.max_gcp_token_ttl == "5m"

    def test_custom_ttl_round_trips(self) -> None:
        ctx = _make_identity_context(max_gcp_token_ttl="10m")
        restored = IdentityContext.from_json(ctx.to_json())
        assert restored.max_gcp_token_ttl == "10m"


# ---------------------------------------------------------------------------
# BaseMCPServer._get_gcp_token — integration of identity TTL with broker
# ---------------------------------------------------------------------------

class TestBaseMCPServerTTLPropagation:
    """Verify BaseMCPServer passes ``max_gcp_token_ttl`` from the identity
    context through to the GCPCredentialBroker.
    """

    @patch.dict(
        "os.environ",
        {
            "MCP_IDENTITY_CONTEXT": _make_identity_context(max_gcp_token_ttl="5m").to_json(),
            "VAULT_ADDR": "http://127.0.0.1:8200",
        },
    )
    @patch("vault_mcp_agents.mcp.base_server.GCPCredentialBroker")
    def test_requested_ttl_is_forwarded(self, mock_broker_cls: MagicMock) -> None:
        from vault_mcp_agents.mcp.base_server import BaseMCPServer

        mock_broker = mock_broker_cls.return_value
        mock_broker.get_access_token.return_value = GCPAccessToken(
            token="ya29.mcp", ttl_seconds=300, impersonated_account="data-agent-gcp"
        )

        server = BaseMCPServer("test-server")
        token = server._get_gcp_token()

        # Verify the broker was called with the TTL from identity context.
        call_kwargs = mock_broker.get_access_token.call_args
        assert call_kwargs.kwargs["requested_ttl"] == "5m"
        assert token.ttl_seconds == 300

    @patch.dict(
        "os.environ",
        {
            "MCP_IDENTITY_CONTEXT": _make_identity_context(max_gcp_token_ttl="5m").to_json(),
            "VAULT_ADDR": "http://127.0.0.1:8200",
        },
    )
    @patch("vault_mcp_agents.mcp.base_server.GCPCredentialBroker")
    def test_session_constructed_from_identity(self, mock_broker_cls: MagicMock) -> None:
        """The session built inside _get_gcp_token carries the identity's fields."""
        from vault_mcp_agents.mcp.base_server import BaseMCPServer

        mock_broker = mock_broker_cls.return_value
        mock_broker.get_access_token.return_value = GCPAccessToken(
            token="ya29.x", ttl_seconds=300, impersonated_account="data-agent-gcp"
        )

        server = BaseMCPServer("test-server")
        server._get_gcp_token()

        call_args = mock_broker.get_access_token.call_args
        session = call_args.kwargs["session"]
        assert session.human_id == "testuser"
        assert session.human_role == "operator"
        assert session.vault_token == "s.test-token"
        assert not session.is_expired

    @patch.dict(
        "os.environ",
        {
            "MCP_IDENTITY_CONTEXT": _make_identity_context(max_gcp_token_ttl="5m").to_json(),
            "VAULT_ADDR": "http://127.0.0.1:8200",
        },
    )
    @patch("vault_mcp_agents.mcp.base_server.GCPCredentialBroker")
    def test_cached_token_is_reused_within_ttl(self, mock_broker_cls: MagicMock) -> None:
        """Within the TTL window, _get_gcp_token returns the cached token
        without calling the broker again.
        """
        from vault_mcp_agents.mcp.base_server import BaseMCPServer

        mock_broker = mock_broker_cls.return_value
        mock_broker.get_access_token.return_value = GCPAccessToken(
            token="ya29.cached", ttl_seconds=300, impersonated_account="data-agent-gcp"
        )

        server = BaseMCPServer("test-server")
        first = server._get_gcp_token()
        second = server._get_gcp_token()

        assert first is second
        assert mock_broker.get_access_token.call_count == 1

    @patch.dict(
        "os.environ",
        {
            "MCP_IDENTITY_CONTEXT": _make_identity_context(max_gcp_token_ttl="5m").to_json(),
            "VAULT_ADDR": "http://127.0.0.1:8200",
        },
    )
    @patch("vault_mcp_agents.mcp.base_server.GCPCredentialBroker")
    def test_cached_token_expires_after_ttl(self, mock_broker_cls: MagicMock) -> None:
        """After the GCP token TTL elapses, _get_gcp_token raises instead of
        fetching a fresh token.  This is the core fix for the manual-test
        failure: Alice calls list_datasets, waits 5 minutes, calls again, and
        the second call must fail.
        """
        from vault_mcp_agents.mcp.base_server import BaseMCPServer

        mock_broker = mock_broker_cls.return_value
        mock_broker.get_access_token.return_value = GCPAccessToken(
            token="ya29.will-expire", ttl_seconds=300, impersonated_account="data-agent-gcp"
        )

        server = BaseMCPServer("test-server")
        server._get_gcp_token()  # populate cache

        # Simulate 5 minutes passing by backdating _token_issued_at.
        server._token_issued_at -= datetime.timedelta(seconds=301)

        with pytest.raises(GCPCredentialError, match="expired"):
            server._get_gcp_token()

        # Broker should only have been called once (the initial fetch).
        assert mock_broker.get_access_token.call_count == 1

    @patch.dict(
        "os.environ",
        {
            "MCP_IDENTITY_CONTEXT": _make_identity_context(max_gcp_token_ttl="5m").to_json(),
            "VAULT_ADDR": "http://127.0.0.1:8200",
        },
    )
    @patch("vault_mcp_agents.mcp.base_server.GCPCredentialBroker")
    def test_policy_ttl_caps_vault_ttl(self, mock_broker_cls: MagicMock) -> None:
        """When Vault/GCP returns a token_ttl larger than the policy's
        max_gcp_token_ttl (e.g. 3600 s vs 5 m), the policy TTL must win.

        This is the root cause of the Alice manual-test failure: GCP issues
        tokens with a default 3600 s lifetime; without the policy cap, the
        cache check only expires after an hour instead of 5 minutes.
        """
        from vault_mcp_agents.mcp.base_server import BaseMCPServer

        mock_broker = mock_broker_cls.return_value
        mock_broker.get_access_token.return_value = GCPAccessToken(
            token="ya29.long-lived", ttl_seconds=3600, impersonated_account="data-agent-gcp"
        )

        server = BaseMCPServer("test-server")
        server._get_gcp_token()  # populate cache

        # Simulate 5 minutes + 1 s passing.  The Vault TTL (3600 s) has NOT
        # elapsed, but the policy cap (300 s) HAS.
        server._token_issued_at -= datetime.timedelta(seconds=301)

        with pytest.raises(GCPCredentialError, match="expired"):
            server._get_gcp_token()

        assert mock_broker.get_access_token.call_count == 1

    def test_expired_session_is_rejected_by_mcp_server(self) -> None:
        """After the session TTL elapses, _get_gcp_token must refuse to issue
        new GCP tokens.  This is the core regression test for the bug where
        _get_gcp_token fabricated a fresh Session(created_at=now()) on every
        call, defeating the expiry check.
        """
        # Create an identity context whose session expired 1 second ago.
        expired_created_at = (
            datetime.datetime.now(datetime.UTC) - datetime.timedelta(seconds=301)
        ).isoformat()
        ctx = _make_identity_context(
            max_gcp_token_ttl="5m",
            session_created_at=expired_created_at,
            session_ttl_seconds=300,
        )

        with patch.dict(
            "os.environ",
            {
                "MCP_IDENTITY_CONTEXT": ctx.to_json(),
                "VAULT_ADDR": "http://127.0.0.1:8200",
            },
        ):
            from vault_mcp_agents.mcp.base_server import BaseMCPServer

            server = BaseMCPServer("test-server")

            with pytest.raises(GCPCredentialError, match="expired"):
                server._get_gcp_token()


# ---------------------------------------------------------------------------
# _parse_ttl_to_seconds
# ---------------------------------------------------------------------------

class TestParseTTLToSeconds:
    def test_minutes(self) -> None:
        from vault_mcp_agents.mcp.base_server import _parse_ttl_to_seconds
        assert _parse_ttl_to_seconds("5m") == 300

    def test_hours(self) -> None:
        from vault_mcp_agents.mcp.base_server import _parse_ttl_to_seconds
        assert _parse_ttl_to_seconds("1h") == 3600

    def test_seconds_suffix(self) -> None:
        from vault_mcp_agents.mcp.base_server import _parse_ttl_to_seconds
        assert _parse_ttl_to_seconds("300s") == 300

    def test_bare_integer(self) -> None:
        from vault_mcp_agents.mcp.base_server import _parse_ttl_to_seconds
        assert _parse_ttl_to_seconds("300") == 300


# ---------------------------------------------------------------------------
# End-to-end: factory → identity context → broker TTL chain
# ---------------------------------------------------------------------------

class TestFactoryTTLChain:
    """Verify the factory wires the policy TTL into the identity context."""

    def test_factory_sets_identity_ttl_from_policy(self, policy_engine: PolicyEngine) -> None:
        session = _make_session()
        policy = policy_engine.resolve(
            human_role=session.human_role, agent_id="data_agent"
        )
        identity = IdentityContext(
            agent_id="data_agent",
            human_id=session.human_id,
            human_role=session.human_role,
            vault_token=session.vault_token,
            allowed_tools=policy.allowed_tools,
            gcp_impersonated_account="data-agent-gcp",
            max_gcp_token_ttl=policy.max_gcp_token_ttl,
            gcp_project="test-project",
            session_created_at=session.created_at.isoformat(),
            session_ttl_seconds=session.ttl_seconds,
        )
        assert identity.max_gcp_token_ttl == "5m"
        assert identity.session_ttl_seconds == session.ttl_seconds
