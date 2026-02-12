"""Integration-style tests verifying the end-to-end capability filtering logic.

These tests do NOT require a running Vault or GCP — they exercise the policy
engine combined with identity context construction, which is the core access
control mechanism.
"""

from __future__ import annotations

from vault_mcp_agents.auth.session import Session
from vault_mcp_agents.mcp.identity_context import IdentityContext
from vault_mcp_agents.policy.engine import PolicyEngine


def _build_identity(session: Session, agent_id: str, policy_engine: PolicyEngine) -> IdentityContext:
    """Replicate the identity context construction from the agent factory."""
    policy = policy_engine.resolve(session.human_role, agent_id)
    return IdentityContext(
        agent_id=agent_id,
        human_id=session.human_id,
        human_role=session.human_role,
        vault_token=session.vault_token,
        allowed_tools=policy.allowed_tools,
        gcp_impersonated_account=f"{agent_id}-gcp",
        max_gcp_token_ttl=policy.max_gcp_token_ttl,
        gcp_project="test-project",
        session_created_at=session.created_at.isoformat(),
        session_ttl_seconds=session.ttl_seconds,
    )


class TestCapabilityFilter:
    """Verify that the same human gets different tools depending on the agent."""

    def test_analyst_gets_different_tools_per_agent(
        self, analyst_session: Session, policy_engine: PolicyEngine
    ) -> None:
        data_ctx = _build_identity(analyst_session, "data_agent", policy_engine)
        compute_ctx = _build_identity(analyst_session, "compute_agent", policy_engine)

        # Data agent: read-only data tools.
        assert "query_bigquery" in data_ctx.allowed_tools
        assert "list_datasets" in data_ctx.allowed_tools
        assert "write_object" not in data_ctx.allowed_tools

        # Compute agent: read-only compute tools.
        assert "list_instances" in compute_ctx.allowed_tools
        assert "get_instance" in compute_ctx.allowed_tools
        assert "create_instance" not in compute_ctx.allowed_tools

    def test_operator_vs_viewer_on_same_agent(
        self,
        operator_session: Session,
        viewer_session: Session,
        policy_engine: PolicyEngine,
    ) -> None:
        op_ctx = _build_identity(operator_session, "compute_agent", policy_engine)
        vw_ctx = _build_identity(viewer_session, "compute_agent", policy_engine)

        # Operator can do everything.
        assert "create_instance" in op_ctx.allowed_tools
        assert "delete_instance" in op_ctx.allowed_tools

        # Viewer can only list.
        assert "create_instance" not in vw_ctx.allowed_tools
        assert vw_ctx.allowed_tools == frozenset(["list_instances"])

    def test_identity_context_carries_vault_token(
        self, operator_session: Session, policy_engine: PolicyEngine
    ) -> None:
        ctx = _build_identity(operator_session, "data_agent", policy_engine)
        assert ctx.vault_token == operator_session.vault_token
