"""Tests for IdentityContext serialisation round-trip."""

from __future__ import annotations

from vault_mcp_agents.mcp.identity_context import IdentityContext


class TestIdentityContext:
    def test_round_trip_json(self) -> None:
        original = IdentityContext(
            agent_id="data_agent",
            human_id="alice",
            human_role="operator",
            vault_token="s.test-token",
            allowed_tools=frozenset(["list_buckets", "read_object"]),
            gcp_impersonated_account="data-agent-gcp",
            max_gcp_token_ttl="1h",
            gcp_project="my-gcp-project",
            session_created_at="2025-01-01T00:00:00+00:00",
            session_ttl_seconds=3600,
        )
        raw = original.to_json()
        restored = IdentityContext.from_json(raw)

        assert restored.agent_id == original.agent_id
        assert restored.human_id == original.human_id
        assert restored.human_role == original.human_role
        assert restored.vault_token == original.vault_token
        assert restored.allowed_tools == original.allowed_tools
        assert restored.gcp_impersonated_account == original.gcp_impersonated_account
        assert restored.max_gcp_token_ttl == original.max_gcp_token_ttl
        assert restored.gcp_project == original.gcp_project
        assert restored.session_created_at == original.session_created_at
        assert restored.session_ttl_seconds == original.session_ttl_seconds

    def test_round_trip_with_spiffe_id(self) -> None:
        original = IdentityContext(
            agent_id="data_agent",
            human_id="alice",
            human_role="operator",
            vault_token="s.test-token",
            allowed_tools=frozenset(["list_buckets"]),
            gcp_impersonated_account="data-agent-gcp",
            max_gcp_token_ttl="5m",
            gcp_project="test-project",
            session_created_at="2025-01-01T00:00:00+00:00",
            session_ttl_seconds=3600,
            spiffe_id="spiffe://vault-mcp-demo/agent/data_agent",
        )
        restored = IdentityContext.from_json(original.to_json())
        assert restored.spiffe_id == "spiffe://vault-mcp-demo/agent/data_agent"

    def test_round_trip_without_spiffe_id(self) -> None:
        original = IdentityContext(
            agent_id="data_agent",
            human_id="alice",
            human_role="operator",
            vault_token="s.test-token",
            allowed_tools=frozenset(["list_buckets"]),
            gcp_impersonated_account="data-agent-gcp",
            max_gcp_token_ttl="5m",
            gcp_project="test-project",
            session_created_at="2025-01-01T00:00:00+00:00",
            session_ttl_seconds=3600,
        )
        restored = IdentityContext.from_json(original.to_json())
        assert restored.spiffe_id is None

    def test_spiffe_id_omitted_from_json_when_none(self) -> None:
        import json

        ctx = IdentityContext(
            agent_id="x", human_id="y", human_role="z", vault_token="t",
            allowed_tools=frozenset(), gcp_impersonated_account="r",
            max_gcp_token_ttl="5m", gcp_project="p",
            session_created_at="2025-01-01T00:00:00+00:00",
            session_ttl_seconds=3600,
        )
        data = json.loads(ctx.to_json())
        assert "spiffe_id" not in data

    def test_allowed_tools_sorted_in_json(self) -> None:
        ctx = IdentityContext(
            agent_id="x",
            human_id="y",
            human_role="z",
            vault_token="t",
            allowed_tools=frozenset(["z_tool", "a_tool", "m_tool"]),
            gcp_impersonated_account="r",
            max_gcp_token_ttl="1h",
            gcp_project="test-project",
            session_created_at="2025-01-01T00:00:00+00:00",
            session_ttl_seconds=3600,
        )
        import json

        data = json.loads(ctx.to_json())
        assert data["allowed_tools"] == ["a_tool", "m_tool", "z_tool"]
