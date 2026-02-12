"""Policy engine that resolves allowed MCP tools for a (role, agent) pair.

Pattern: Policy-Gated Capability Filtering
--------------------------------------------
A YAML policy file (``policies/capabilities.yaml``) is the single declarative
source for *what each identity combination can do*.  The file is loaded once
at startup and queried on every MCP tool-list request.

Why a separate policy file instead of Vault policies alone?
Vault policies control *Vault paths* (e.g. which GCP roleset a token can
read).  Application-level capabilities — "may this user call the
``delete_object`` MCP tool?" — are a layer above Vault.  Keeping them in a
dedicated file makes them auditable, version-controllable, and testable
without a running Vault instance.

The engine is intentionally stateless: it receives the role and agent ID and
returns a ``ResolvedPolicy``.  No mutation, no caching of decisions.
"""

from __future__ import annotations

import dataclasses
import logging
import pathlib
from typing import Any

import yaml

from vault_mcp_agents.audit.logger import AuditLogger

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class ResolvedPolicy:
    """The result of resolving a (human_role, agent_id) pair against the policy file.

    Attributes:
        role:             Human role name.
        agent_id:         Agent identifier.
        allowed_tools:    Frozenset of MCP tool names the combination may invoke.
        max_gcp_token_ttl: Maximum GCP token TTL string (e.g. ``"1h"``).
    """

    role: str
    agent_id: str
    allowed_tools: frozenset[str]
    max_gcp_token_ttl: str


class PolicyError(Exception):
    """Raised when the policy file is malformed or lookup fails."""


class PolicyEngine:
    """Loads ``capabilities.yaml`` and resolves tool permissions."""

    def __init__(self, policy_path: str | pathlib.Path | None = None) -> None:
        if policy_path is None:
            policy_path = pathlib.Path(__file__).resolve().parents[3] / "policies" / "capabilities.yaml"
        self._policy_path = pathlib.Path(policy_path)
        self._data: dict[str, Any] = self._load()
        self._audit = AuditLogger(log_to_stdout=True)

    def reload(self) -> None:
        """Re-read the policy file from disk."""
        self._data = self._load()

    def resolve(self, human_role: str, agent_id: str) -> ResolvedPolicy:
        """Return the resolved policy for *human_role* acting through *agent_id*.

        Raises ``PolicyError`` if the combination is not defined.
        """
        roles: dict[str, Any] = self._data.get("roles", {})
        role_block = roles.get(human_role)
        if role_block is None:
            self._audit.log_policy_violation(
                human_role=human_role,
                agent_id=agent_id,
                detail=f"Unknown role: {human_role}",
            )
            raise PolicyError(f"Unknown role: {human_role}")

        agents_block: dict[str, Any] = role_block.get("agents", {})
        agent_block = agents_block.get(agent_id)
        if agent_block is None:
            self._audit.log_policy_violation(
                human_role=human_role,
                agent_id=agent_id,
                detail=f"Role '{human_role}' has no policy for agent '{agent_id}'",
            )
            raise PolicyError(
                f"Role '{human_role}' has no policy for agent '{agent_id}'"
            )

        return ResolvedPolicy(
            role=human_role,
            agent_id=agent_id,
            allowed_tools=frozenset(agent_block.get("allowed_tools", [])),
            max_gcp_token_ttl=agent_block.get("max_gcp_token_ttl", "5m"),
        )

    def resolve_by_spiffe_id(self, human_role: str, spiffe_id: str) -> ResolvedPolicy:
        """Resolve policy using a SPIFFE ID instead of an agent_id.

        The SPIFFE ID is mapped to an agent_id via the ``spiffe_identity_map``
        section in the policy file, then delegated to :meth:`resolve`.

        Raises ``PolicyError`` if the SPIFFE ID is not mapped.
        """
        identity_map: dict[str, str] = self._data.get("spiffe_identity_map", {})
        agent_id = identity_map.get(spiffe_id)
        if agent_id is None:
            self._audit.log_policy_violation(
                human_role=human_role,
                agent_id=spiffe_id,
                detail=f"No agent mapping for SPIFFE ID: {spiffe_id}",
            )
            raise PolicyError(f"No agent mapping for SPIFFE ID: {spiffe_id}")
        return self.resolve(human_role=human_role, agent_id=agent_id)

    def list_roles(self) -> list[str]:
        """Return all role names defined in the policy file."""
        return list(self._data.get("roles", {}).keys())

    # -- private helpers -----------------------------------------------------

    def _load(self) -> dict[str, Any]:
        if not self._policy_path.exists():
            raise PolicyError(f"Policy file not found: {self._policy_path}")
        with open(self._policy_path) as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict) or "roles" not in data:
            raise PolicyError("Policy file must contain a top-level 'roles' key")
        return data
