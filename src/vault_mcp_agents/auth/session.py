"""Session context that carries authenticated identity through the call chain.

Pattern: Session Context Propagation
-------------------------------------
A single ``Session`` object is created after the human authenticates via Vault
and is threaded through every downstream call — agent construction, MCP server
initialisation, and GCP credential requests.  This avoids scattering identity
state across disconnected modules and makes the security boundary explicit: if
a component does not receive a Session, it cannot act on behalf of a user.

The session is intentionally immutable after creation.  Credential refresh is
handled by obtaining a new session rather than mutating the existing one.
"""

from __future__ import annotations

import dataclasses
import datetime


@dataclasses.dataclass(frozen=True)
class Session:
    """Immutable snapshot of an authenticated interaction.

    Attributes:
        human_id:       Username or entity ID from Vault's auth response.
        human_role:     Role name resolved from the Vault token's policies
                        (maps to a key in ``policies/capabilities.yaml``).
        vault_token:    Short-lived Vault client token for this session.
        token_policies: Set of Vault policy names attached to the token.
        created_at:     UTC timestamp of session creation.
        ttl_seconds:    Remaining TTL of the Vault token at creation time.
    """

    human_id: str
    human_role: str
    vault_token: str
    token_policies: frozenset[str]
    created_at: datetime.datetime
    ttl_seconds: int
    spiffe_id: str | None = None

    @property
    def is_expired(self) -> bool:
        elapsed = (datetime.datetime.now(datetime.UTC) - self.created_at).total_seconds()
        return elapsed >= self.ttl_seconds

    def __str__(self) -> str:
        spiffe_part = f", spiffe={self.spiffe_id}" if self.spiffe_id else ""
        return f"Session(human={self.human_id}, role={self.human_role}{spiffe_part}, expired={self.is_expired})"
