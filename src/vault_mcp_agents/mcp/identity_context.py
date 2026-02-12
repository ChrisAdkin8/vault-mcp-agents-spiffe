"""Identity context passed from agents to MCP servers.

Pattern: Composite Identity
----------------------------
An MCP server needs to know *two* things to decide what tools to expose:

  1. Which agent is calling (agent identity).
  2. Which human authorised the call (human identity / role).

These are bundled into an ``IdentityContext`` that is serialised as JSON and
passed to the MCP server process via an environment variable
(``MCP_IDENTITY_CONTEXT``).  The server deserialises it at startup and uses it
to filter its tool registry.

Why an environment variable?
The MCP stdio transport starts the server as a subprocess.  Environment
variables are the simplest side-channel that doesn't require protocol
extensions.  For HTTP/SSE transports, this would instead be a header or
query parameter.
"""

from __future__ import annotations

import dataclasses
import json


@dataclasses.dataclass(frozen=True)
class IdentityContext:
    """Identity context that travels from the agent to the MCP server.

    Attributes:
        agent_id:        Which agent is making the request.
        human_id:        The authenticated human's username / entity ID.
        human_role:      Application role resolved from Vault policies.
        vault_token:     The session's Vault token (so the MCP server can
                         fetch GCP credentials on behalf of the human).
        allowed_tools:   The set of tool names this identity pair may use.
        gcp_impersonated_account: Vault GCP impersonated account the server should use.
        max_gcp_token_ttl: Maximum TTL for GCP tokens.
        gcp_project:     GCP project ID for API calls.
        session_created_at: ISO-8601 UTC timestamp of the original Vault session.
        session_ttl_seconds: TTL (in seconds) of the original Vault session.
    """

    agent_id: str
    human_id: str
    human_role: str
    vault_token: str
    allowed_tools: frozenset[str]
    gcp_impersonated_account: str
    max_gcp_token_ttl: str
    gcp_project: str
    session_created_at: str
    session_ttl_seconds: int
    spiffe_id: str | None = None

    def to_json(self) -> str:
        payload: dict[str, object] = {
            "agent_id": self.agent_id,
            "human_id": self.human_id,
            "human_role": self.human_role,
            "vault_token": self.vault_token,
            "allowed_tools": sorted(self.allowed_tools),
            "gcp_impersonated_account": self.gcp_impersonated_account,
            "max_gcp_token_ttl": self.max_gcp_token_ttl,
            "gcp_project": self.gcp_project,
            "session_created_at": self.session_created_at,
            "session_ttl_seconds": self.session_ttl_seconds,
        }
        if self.spiffe_id is not None:
            payload["spiffe_id"] = self.spiffe_id
        return json.dumps(payload)

    @classmethod
    def from_json(cls, raw: str) -> IdentityContext:
        data = json.loads(raw)
        return cls(
            agent_id=data["agent_id"],
            human_id=data["human_id"],
            human_role=data["human_role"],
            vault_token=data["vault_token"],
            allowed_tools=frozenset(data["allowed_tools"]),
            gcp_impersonated_account=data["gcp_impersonated_account"],
            max_gcp_token_ttl=data["max_gcp_token_ttl"],
            gcp_project=data["gcp_project"],
            session_created_at=data["session_created_at"],
            session_ttl_seconds=data["session_ttl_seconds"],
            spiffe_id=data.get("spiffe_id"),
        )
