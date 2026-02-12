"""Tests for structured audit logging."""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path

import pytest

from vault_mcp_agents.audit.logger import AuditEvent, AuditLogger, _token_hash


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _capture_audit_line(audit: AuditLogger, callback) -> dict:
    """Call *callback* to emit one audit event and return the parsed JSON."""
    handler = audit._logger.handlers[0]
    # Temporarily redirect handler to a list
    records: list[str] = []
    original_emit = handler.emit

    def capture_emit(record):
        records.append(handler.format(record))

    handler.emit = capture_emit
    try:
        callback()
    finally:
        handler.emit = original_emit
    assert len(records) == 1, f"Expected 1 record, got {len(records)}"
    return json.loads(records[0])


@pytest.fixture(autouse=True)
def _clean_audit_logger():
    """Remove all handlers between tests to avoid cross-contamination."""
    yield
    audit_logger = logging.getLogger("vault_mcp_agents.audit")
    audit_logger.handlers.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestJSONFormat:
    def test_output_is_valid_json(self):
        audit = AuditLogger(log_to_stdout=True)
        line = _capture_audit_line(
            audit,
            lambda: audit.log_event(AuditEvent.SESSION_CREATED, human_id="alice"),
        )
        assert isinstance(line, dict)
        assert "timestamp" in line
        assert line["event_type"] == "SESSION_CREATED"

    def test_timestamp_is_iso8601(self):
        audit = AuditLogger(log_to_stdout=True)
        line = _capture_audit_line(
            audit,
            lambda: audit.log_event(AuditEvent.SESSION_CREATED, human_id="alice"),
        )
        assert line["timestamp"].endswith("Z")


class TestToolAccessEvents:
    def test_allowed_event_fields(self):
        audit = AuditLogger(log_to_stdout=True)
        line = _capture_audit_line(
            audit,
            lambda: audit.log_tool_access(
                agent_id="data_agent",
                human_id="alice",
                human_role="operator",
                tool_name="list_buckets",
                allowed=True,
                vault_token="s.secret-token",
            ),
        )
        assert line["event_type"] == "TOOL_ACCESS_ALLOWED"
        assert line["agent_id"] == "data_agent"
        assert line["human_id"] == "alice"
        assert line["human_role"] == "operator"
        assert line["tool_name"] == "list_buckets"
        assert line["outcome"] == "allowed"
        assert line["session_id"] is not None

    def test_denied_event_fields(self):
        audit = AuditLogger(log_to_stdout=True)
        line = _capture_audit_line(
            audit,
            lambda: audit.log_tool_access(
                agent_id="data_agent",
                human_id="carol",
                human_role="viewer",
                tool_name="delete_object",
                allowed=False,
                vault_token="s.viewer-token",
            ),
        )
        assert line["event_type"] == "TOOL_ACCESS_DENIED"
        assert line["outcome"] == "denied"


class TestCredentialEvents:
    def test_credential_issued_event(self):
        audit = AuditLogger(log_to_stdout=True)
        line = _capture_audit_line(
            audit,
            lambda: audit.log_credential_event(
                event_type=AuditEvent.CREDENTIAL_ISSUED,
                agent_id="data_agent",
                human_id="alice",
                human_role="operator",
                detail="effective_ttl=300s",
                vault_token="s.secret-token",
            ),
        )
        assert line["event_type"] == "CREDENTIAL_ISSUED"
        assert "300" in line["detail"]

    def test_credential_expired_event(self):
        audit = AuditLogger(log_to_stdout=True)
        line = _capture_audit_line(
            audit,
            lambda: audit.log_credential_event(
                event_type=AuditEvent.CREDENTIAL_EXPIRED,
                agent_id="data_agent",
                human_id="alice",
                human_role="operator",
                detail="elapsed=310s",
                vault_token="s.secret-token",
            ),
        )
        assert line["event_type"] == "CREDENTIAL_EXPIRED"


class TestSessionEvents:
    def test_session_created_event(self):
        audit = AuditLogger(log_to_stdout=True)
        line = _capture_audit_line(
            audit,
            lambda: audit.log_session_event(
                event_type=AuditEvent.SESSION_CREATED,
                human_id="bob",
                human_role="analyst",
                vault_token="s.analyst-token",
                detail="ttl=1800s",
            ),
        )
        assert line["event_type"] == "SESSION_CREATED"
        assert line["human_id"] == "bob"
        assert line["human_role"] == "analyst"


class TestPolicyViolation:
    def test_policy_violation_event(self):
        audit = AuditLogger(log_to_stdout=True)
        line = _capture_audit_line(
            audit,
            lambda: audit.log_policy_violation(
                human_role="unknown_role",
                agent_id="data_agent",
                detail="Unknown role: unknown_role",
            ),
        )
        assert line["event_type"] == "POLICY_VIOLATION"
        assert line["outcome"] == "denied"
        assert "unknown_role" in line["detail"]


class TestSensitiveFields:
    def test_vault_token_never_in_output(self):
        """The actual Vault token must never appear in audit logs."""
        secret_token = "s.very-secret-vault-token-12345"
        audit = AuditLogger(log_to_stdout=True)
        line_str = ""

        handler = audit._logger.handlers[0]
        records: list[str] = []
        original_emit = handler.emit

        def capture_emit(record):
            records.append(handler.format(record))

        handler.emit = capture_emit
        try:
            audit.log_tool_access(
                agent_id="data_agent",
                human_id="alice",
                human_role="operator",
                tool_name="list_buckets",
                allowed=True,
                vault_token=secret_token,
            )
        finally:
            handler.emit = original_emit

        line_str = records[0]
        assert secret_token not in line_str
        # But the hash should be present
        parsed = json.loads(line_str)
        assert parsed["session_id"] == _token_hash(secret_token)


class TestSpiffeIdNullable:
    def test_spiffe_id_is_nullable(self):
        audit = AuditLogger(log_to_stdout=True)
        line = _capture_audit_line(
            audit,
            lambda: audit.log_tool_access(
                agent_id="data_agent",
                human_id="alice",
                human_role="operator",
                tool_name="list_buckets",
                allowed=True,
                spiffe_id=None,
            ),
        )
        assert line["spiffe_id"] is None

    def test_spiffe_id_present_when_set(self):
        audit = AuditLogger(log_to_stdout=True)
        line = _capture_audit_line(
            audit,
            lambda: audit.log_tool_access(
                agent_id="data_agent",
                human_id="alice",
                human_role="operator",
                tool_name="list_buckets",
                allowed=True,
                spiffe_id="spiffe://vault-mcp-demo/agent/data_agent",
            ),
        )
        assert line["spiffe_id"] == "spiffe://vault-mcp-demo/agent/data_agent"


class TestFileOutput:
    def test_log_to_file(self):
        with tempfile.NamedTemporaryFile(mode="r", suffix=".log", delete=False) as f:
            log_path = f.name

        audit = AuditLogger(log_file=log_path, log_to_stdout=False)
        audit.log_event(AuditEvent.SESSION_CREATED, human_id="alice")

        content = Path(log_path).read_text().strip()
        parsed = json.loads(content)
        assert parsed["event_type"] == "SESSION_CREATED"
        assert parsed["human_id"] == "alice"

        Path(log_path).unlink(missing_ok=True)
