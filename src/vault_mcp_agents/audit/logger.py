"""Structured audit logger for security-relevant events.

Every audit event is emitted as a single-line JSON object containing a fixed
set of fields.  The Vault token is **never** included — only a truncated hash
is logged for cross-event correlation.
"""

from __future__ import annotations

import hashlib
import logging
import sys
from enum import Enum
from typing import Any

from vault_mcp_agents.audit.formatter import JSONFormatter


class AuditEvent(str, Enum):
    """Audit event types."""

    TOOL_ACCESS_ALLOWED = "TOOL_ACCESS_ALLOWED"
    TOOL_ACCESS_DENIED = "TOOL_ACCESS_DENIED"
    CREDENTIAL_REQUESTED = "CREDENTIAL_REQUESTED"
    CREDENTIAL_ISSUED = "CREDENTIAL_ISSUED"
    CREDENTIAL_EXPIRED = "CREDENTIAL_EXPIRED"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    SESSION_CREATED = "SESSION_CREATED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    SPIFFE_AUTH_SUCCESS = "SPIFFE_AUTH_SUCCESS"
    SPIFFE_AUTH_FAILURE = "SPIFFE_AUTH_FAILURE"


def _token_hash(vault_token: str) -> str:
    """Return a short SHA-256 prefix suitable for log correlation.

    This is intentionally one-way and truncated so the token cannot be
    recovered from the audit log.
    """
    return hashlib.sha256(vault_token.encode()).hexdigest()[:12]


class AuditLogger:
    """Structured JSON audit logger.

    Usage::

        audit = AuditLogger()
        audit.log_tool_access(identity, "list_buckets", allowed=True)
    """

    _LOGGER_NAME = "vault_mcp_agents.audit"

    def __init__(
        self,
        *,
        log_file: str | None = None,
        log_to_stdout: bool = True,
    ) -> None:
        self._logger = logging.getLogger(self._LOGGER_NAME)
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False

        # Avoid adding duplicate handlers on repeated instantiation.
        if not self._logger.handlers:
            formatter = JSONFormatter()
            if log_to_stdout:
                sh = logging.StreamHandler(sys.stdout)
                sh.setFormatter(formatter)
                self._logger.addHandler(sh)
            if log_file:
                fh = logging.FileHandler(log_file)
                fh.setFormatter(formatter)
                self._logger.addHandler(fh)

    # -- public API ----------------------------------------------------------

    def log_event(self, event_type: AuditEvent, /, **fields: Any) -> None:
        """Emit a structured audit event."""
        record = self._logger.makeRecord(
            name=self._LOGGER_NAME,
            level=logging.INFO,
            fn="",
            lno=0,
            msg="",
            args=(),
            exc_info=None,
        )
        record.audit_data = {"event_type": event_type.value, **fields}  # type: ignore[attr-defined]
        self._logger.handle(record)

    def log_tool_access(
        self,
        *,
        agent_id: str,
        human_id: str,
        human_role: str,
        tool_name: str,
        allowed: bool,
        spiffe_id: str | None = None,
        vault_token: str | None = None,
    ) -> None:
        event = AuditEvent.TOOL_ACCESS_ALLOWED if allowed else AuditEvent.TOOL_ACCESS_DENIED
        self.log_event(
            event,
            agent_id=agent_id,
            human_id=human_id,
            human_role=human_role,
            tool_name=tool_name,
            outcome="allowed" if allowed else "denied",
            spiffe_id=spiffe_id,
            session_id=_token_hash(vault_token) if vault_token else None,
        )

    def log_credential_event(
        self,
        *,
        event_type: AuditEvent,
        agent_id: str,
        human_id: str,
        human_role: str,
        detail: str = "",
        spiffe_id: str | None = None,
        vault_token: str | None = None,
    ) -> None:
        self.log_event(
            event_type,
            agent_id=agent_id,
            human_id=human_id,
            human_role=human_role,
            detail=detail,
            spiffe_id=spiffe_id,
            session_id=_token_hash(vault_token) if vault_token else None,
        )

    def log_session_event(
        self,
        *,
        event_type: AuditEvent,
        human_id: str,
        human_role: str,
        vault_token: str | None = None,
        detail: str = "",
    ) -> None:
        self.log_event(
            event_type,
            human_id=human_id,
            human_role=human_role,
            detail=detail,
            session_id=_token_hash(vault_token) if vault_token else None,
        )

    def log_policy_violation(
        self,
        *,
        human_role: str,
        agent_id: str,
        detail: str,
    ) -> None:
        self.log_event(
            AuditEvent.POLICY_VIOLATION,
            human_role=human_role,
            agent_id=agent_id,
            detail=detail,
            outcome="denied",
        )
