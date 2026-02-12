"""Tests for the MCP HTTP client adapter."""

from __future__ import annotations

import base64

from vault_mcp_agents.agents.mcp_langchain_adapter import _json_schema_to_pydantic
from vault_mcp_agents.mcp.http_identity_middleware import encode_identity_header
from vault_mcp_agents.mcp.identity_context import IdentityContext


def _make_identity(**overrides) -> IdentityContext:
    defaults = dict(
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
    defaults.update(overrides)
    return IdentityContext(**defaults)


class TestIdentityHeaderEncoding:
    def test_identity_context_encoded_as_base64_json(self):
        identity = _make_identity()
        header_value = encode_identity_header(identity)
        decoded = base64.b64decode(header_value).decode("utf-8")
        restored = IdentityContext.from_json(decoded)
        assert restored.agent_id == "data_agent"
        assert restored.human_id == "alice"

    def test_different_identities_produce_different_headers(self):
        id1 = _make_identity(human_id="alice")
        id2 = _make_identity(human_id="bob")
        assert encode_identity_header(id1) != encode_identity_header(id2)


class TestSharedSchemaConversion:
    """Verify that _json_schema_to_pydantic (reused by HTTP adapter) works correctly."""

    def test_converts_required_string_field(self):
        schema = {
            "type": "object",
            "properties": {"bucket": {"type": "string", "description": "Bucket name"}},
            "required": ["bucket"],
        }
        model = _json_schema_to_pydantic("list_buckets", schema)
        assert "bucket" in model.model_fields

    def test_converts_optional_field_with_default(self):
        schema = {
            "type": "object",
            "properties": {
                "max_rows": {"type": "integer", "description": "Max rows", "default": 100}
            },
        }
        model = _json_schema_to_pydantic("query", schema)
        assert model.model_fields["max_rows"].default == 100

    def test_empty_properties_produces_no_fields(self):
        schema = {"type": "object", "properties": {}}
        model = _json_schema_to_pydantic("empty_tool", schema)
        assert len(model.model_fields) == 0
