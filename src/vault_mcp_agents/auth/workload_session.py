"""Workload session produced by SPIFFE authentication against Vault Enterprise.

This is the agent-side counterpart of the human ``Session``.  Where a
``Session`` proves a human authenticated via userpass/LDAP/OIDC, a
``WorkloadSession`` proves an agent container authenticated via its X.509
SVID through Vault's SPIFFE auth method.
"""

from __future__ import annotations

import dataclasses
import datetime


@dataclasses.dataclass(frozen=True)
class WorkloadSession:
    """Immutable session obtained when a workload authenticates via SPIFFE.

    Attributes:
        spiffe_id:      The workload's SPIFFE ID (e.g. ``spiffe://vault-mcp-demo/agent/data_agent``).
        vault_token:    Vault client token issued by the SPIFFE auth method.
        token_policies: Vault policies attached to the token.
        created_at:     UTC timestamp of authentication.
        ttl_seconds:    Token TTL at issuance.
    """

    spiffe_id: str
    vault_token: str
    token_policies: frozenset[str]
    created_at: datetime.datetime
    ttl_seconds: int

    @property
    def is_expired(self) -> bool:
        elapsed = (datetime.datetime.now(datetime.UTC) - self.created_at).total_seconds()
        return elapsed >= self.ttl_seconds

    def __str__(self) -> str:
        return (
            f"WorkloadSession(spiffe={self.spiffe_id}, "
            f"expired={self.is_expired})"
        )
