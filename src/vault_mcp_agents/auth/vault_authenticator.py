"""Human authentication against HashiCorp Vault.

Pattern: Vault as Identity Broker
----------------------------------
Vault is the single source of truth for both *who the human is* and *what
secrets they may access*.  The human authenticates with Vault directly (via
userpass, LDAP, or OIDC) and receives a short-lived token.  That token's
attached policies are mapped to an application-level role (operator, analyst,
viewer) which is the key used by the policy engine.

Why Vault and not a standalone IdP?
Because we already need Vault for GCP credential brokering.  Using it for
human auth as well keeps the trust boundary in one place and lets us tie
GCP token TTL to the human's session TTL.
"""

from __future__ import annotations

import datetime
import logging
from typing import Any

import hvac

from vault_mcp_agents.audit.logger import AuditEvent, AuditLogger
from vault_mcp_agents.auth.session import Session

logger = logging.getLogger(__name__)

# Mapping from Vault policy names to application roles.  The first matching
# policy wins (order = most-privileged first).
_POLICY_TO_ROLE: list[tuple[str, str]] = [
    ("operator-policy", "operator"),
    ("analyst-policy", "analyst"),
    ("viewer-policy", "viewer"),
]


class VaultAuthenticationError(Exception):
    """Raised when Vault authentication or token lookup fails."""


class VaultAuthenticator:
    """Authenticates a human user via Vault and produces a ``Session``."""

    def __init__(self, vault_addr: str, auth_method: str = "userpass") -> None:
        self._vault_addr = vault_addr
        self._auth_method = auth_method
        self._client = hvac.Client(url=vault_addr, token="")
        self._audit = AuditLogger(log_to_stdout=True)

    def authenticate(self, username: str, password: str) -> Session:
        """Authenticate *username* and return an immutable ``Session``.

        Raises ``VaultAuthenticationError`` on failure.
        """
        try:
            auth_response = self._login(username, password)
        except hvac.exceptions.VaultError as exc:
            raise VaultAuthenticationError(f"Vault login failed: {exc}") from exc

        client_token: str = auth_response["auth"]["client_token"]
        policies: list[str] = auth_response["auth"]["policies"]
        ttl: int = auth_response["auth"]["lease_duration"]

        role = self._resolve_role(policies)
        logger.info("User %s authenticated — role=%s, policies=%s", username, role, policies)

        session = Session(
            human_id=username,
            human_role=role,
            vault_token=client_token,
            token_policies=frozenset(policies),
            created_at=datetime.datetime.now(datetime.UTC),
            ttl_seconds=ttl,
        )
        self._audit.log_session_event(
            event_type=AuditEvent.SESSION_CREATED,
            human_id=username,
            human_role=role,
            vault_token=client_token,
            detail=f"ttl={ttl}s, policies={policies}",
        )
        return session

    # -- private helpers -----------------------------------------------------

    def _login(self, username: str, password: str) -> dict[str, Any]:
        if self._auth_method == "userpass":
            return self._client.auth.userpass.login(username=username, password=password)
        if self._auth_method == "ldap":
            return self._client.auth.ldap.login(username=username, password=password)
        raise VaultAuthenticationError(f"Unsupported auth method: {self._auth_method}")

    @staticmethod
    def _resolve_role(policies: list[str]) -> str:
        for policy_name, role in _POLICY_TO_ROLE:
            if policy_name in policies:
                return role
        raise VaultAuthenticationError(
            f"No application role maps to Vault policies: {policies}"
        )
