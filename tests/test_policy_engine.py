"""Tests for the policy engine — the core access-control logic."""

from __future__ import annotations

import pytest

from vault_mcp_agents.policy.engine import PolicyEngine, PolicyError


class TestPolicyResolution:
    """Verify that (role, agent_id) pairs resolve to the correct tool sets."""

    def test_operator_data_agent_gets_full_data_tools(self, policy_engine: PolicyEngine) -> None:
        policy = policy_engine.resolve("operator", "data_agent")
        assert "list_buckets" in policy.allowed_tools
        assert "write_object" in policy.allowed_tools
        assert "delete_object" in policy.allowed_tools
        assert "query_bigquery" in policy.allowed_tools
        assert "create_dataset" in policy.allowed_tools

    def test_analyst_data_agent_gets_read_only(self, policy_engine: PolicyEngine) -> None:
        policy = policy_engine.resolve("analyst", "data_agent")
        assert "list_buckets" in policy.allowed_tools
        assert "read_object" in policy.allowed_tools
        assert "query_bigquery" in policy.allowed_tools
        # Write/delete should be absent.
        assert "write_object" not in policy.allowed_tools
        assert "delete_object" not in policy.allowed_tools
        assert "create_dataset" not in policy.allowed_tools

    def test_viewer_compute_agent_can_only_list(self, policy_engine: PolicyEngine) -> None:
        policy = policy_engine.resolve("viewer", "compute_agent")
        assert policy.allowed_tools == frozenset(["list_instances"])

    def test_operator_compute_agent_gets_full_compute_tools(self, policy_engine: PolicyEngine) -> None:
        policy = policy_engine.resolve("operator", "compute_agent")
        assert "create_instance" in policy.allowed_tools
        assert "delete_instance" in policy.allowed_tools
        assert "start_instance" in policy.allowed_tools
        assert "stop_instance" in policy.allowed_tools

    def test_unknown_role_raises(self, policy_engine: PolicyEngine) -> None:
        with pytest.raises(PolicyError, match="Unknown role"):
            policy_engine.resolve("superadmin", "data_agent")

    def test_unknown_agent_raises(self, policy_engine: PolicyEngine) -> None:
        with pytest.raises(PolicyError, match="no policy for agent"):
            policy_engine.resolve("operator", "nonexistent_agent")

    def test_all_roles_get_five_minute_ttl(self, policy_engine: PolicyEngine) -> None:
        op = policy_engine.resolve("operator", "data_agent")
        an = policy_engine.resolve("analyst", "data_agent")
        vw = policy_engine.resolve("viewer", "data_agent")
        assert op.max_gcp_token_ttl == "5m"
        assert an.max_gcp_token_ttl == "5m"
        assert vw.max_gcp_token_ttl == "5m"


class TestSpiffeResolution:
    """Verify SPIFFE ID to agent_id mapping and policy resolution."""

    def test_resolve_by_spiffe_id_data_agent(self, policy_engine: PolicyEngine) -> None:
        policy = policy_engine.resolve_by_spiffe_id(
            "operator", "spiffe://vault-mcp-demo/agent/data_agent"
        )
        assert policy.agent_id == "data_agent"
        assert "list_buckets" in policy.allowed_tools

    def test_resolve_by_spiffe_id_compute_agent(self, policy_engine: PolicyEngine) -> None:
        policy = policy_engine.resolve_by_spiffe_id(
            "analyst", "spiffe://vault-mcp-demo/agent/compute_agent"
        )
        assert policy.agent_id == "compute_agent"
        assert "list_instances" in policy.allowed_tools

    def test_resolve_by_spiffe_id_unknown_raises(self, policy_engine: PolicyEngine) -> None:
        with pytest.raises(PolicyError, match="No agent mapping for SPIFFE ID"):
            policy_engine.resolve_by_spiffe_id(
                "operator", "spiffe://evil-domain/agent/rogue"
            )


class TestPolicyReload:
    def test_reload_does_not_raise(self, policy_engine: PolicyEngine) -> None:
        policy_engine.reload()

    def test_list_roles(self, policy_engine: PolicyEngine) -> None:
        roles = policy_engine.list_roles()
        assert set(roles) == {"operator", "analyst", "viewer"}
