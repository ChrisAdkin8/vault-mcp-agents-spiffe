"""Base class for identity-aware MCP servers.

Pattern: Policy-Gated Tool Registry
-------------------------------------
Each MCP server defines a *full* set of tools it is capable of exposing.
At startup the server reads the ``IdentityContext`` from the environment and
removes any tool whose name is not in the ``allowed_tools`` set.  This means:

  - The server process itself never has access to tools it shouldn't.
  - The filtering happens once, at startup, not on every call.
  - Adding a new tool is a two-step process: implement it in the server *and*
    add it to the relevant policies — defence in depth.

The base class also handles GCP credential retrieval so that concrete servers
only need to implement tool logic, not plumbing.
"""

from __future__ import annotations

import datetime
import logging
import os
from typing import Any

from mcp.server import Server
from mcp.types import Tool

from vault_mcp_agents.audit.logger import AuditEvent, AuditLogger
from vault_mcp_agents.mcp.identity_context import IdentityContext
from vault_mcp_agents.vault.gcp_credentials import (
    GCPAccessToken,
    GCPCredentialBroker,
    GCPCredentialError,
)

logger = logging.getLogger(__name__)


def _parse_ttl_to_seconds(ttl_str: str) -> int:
    """Parse a Vault-style duration string to seconds.

    Examples: ``"5m"`` → 300, ``"1h"`` → 3600, ``"300"`` → 300.
    """
    s = ttl_str.strip()
    if s.endswith("m"):
        return int(s[:-1]) * 60
    if s.endswith("h"):
        return int(s[:-1]) * 3600
    if s.endswith("s"):
        return int(s[:-1])
    return int(s)


class BaseMCPServer:
    """Scaffolding shared by all identity-aware MCP servers.

    Subclasses must:
      1. Call ``super().__init__(server_name)`` to set up the MCP ``Server``.
      2. Register tools via ``self._register_tool(name, description, schema, handler)``.
      3. Call ``self.run()`` to start the stdio event loop.

    The base class takes care of:
      - Parsing the ``IdentityContext`` from the environment.
      - Filtering the tool list to only what the identity context allows.
      - Providing ``self._get_gcp_token()`` for GCP-backed tool handlers.
    """

    def __init__(self, server_name: str) -> None:
        self._server = Server(server_name)
        self._identity = self._load_identity()
        self._vault_addr = os.environ.get("VAULT_ADDR", "http://127.0.0.1:8200")
        self._gcp_broker = GCPCredentialBroker(
            vault_addr=self._vault_addr,
            gcp_mount=os.environ.get("VAULT_GCP_MOUNT", "gcp"),
        )
        self._cached_gcp_token: GCPAccessToken | None = None
        self._token_issued_at: datetime.datetime | None = None
        self._audit = AuditLogger(log_to_stdout=True)

        # Full registry before filtering — populated by subclass __init__.
        self._all_tools: dict[str, Tool] = {}
        self._tool_handlers: dict[str, Any] = {}

        logger.info(
            "MCP server '%s' starting — agent=%s, human=%s (%s), allowed_tools=%s",
            server_name,
            self._identity.agent_id,
            self._identity.human_id,
            self._identity.human_role,
            sorted(self._identity.allowed_tools),
        )

    # -- tool registration (called by subclasses) ----------------------------

    def _register_tool(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        handler: Any,
    ) -> None:
        """Register a tool.  It will only be exposed if the identity context allows it."""
        self._all_tools[name] = Tool(
            name=name,
            description=description,
            inputSchema=input_schema,
        )
        self._tool_handlers[name] = handler

    def _get_visible_tools(self) -> list[Tool]:
        """Return only the tools the current identity context permits."""
        return [
            tool
            for name, tool in self._all_tools.items()
            if name in self._identity.allowed_tools
        ]

    def _get_handler(self, tool_name: str) -> Any:
        if tool_name not in self._identity.allowed_tools:
            self._audit.log_tool_access(
                agent_id=self._identity.agent_id,
                human_id=self._identity.human_id,
                human_role=self._identity.human_role,
                tool_name=tool_name,
                allowed=False,
                vault_token=self._identity.vault_token,
            )
            raise PermissionError(
                f"Tool '{tool_name}' is not permitted for "
                f"agent={self._identity.agent_id}, human={self._identity.human_id}"
            )
        self._audit.log_tool_access(
            agent_id=self._identity.agent_id,
            human_id=self._identity.human_id,
            human_role=self._identity.human_role,
            tool_name=tool_name,
            allowed=True,
            vault_token=self._identity.vault_token,
        )
        return self._tool_handlers[tool_name]

    # -- GCP credential helper -----------------------------------------------

    def _get_gcp_token(self) -> GCPAccessToken:
        """Obtain a short-lived GCP token via Vault using the session's identity.

        The token is cached after the first call.  Subsequent calls return the
        cached token until the *effective* TTL expires, at which point a
        ``GCPCredentialError`` is raised — the human must re-authenticate.

        The effective TTL is the lesser of the Vault-reported ``token_ttl`` and
        the policy's ``max_gcp_token_ttl``.  This ensures the 5-minute policy
        boundary is honoured even when the underlying GCP token has a longer
        lifetime (GCP defaults to 3600 s).
        """
        from vault_mcp_agents.auth.session import Session

        max_policy_ttl = _parse_ttl_to_seconds(self._identity.max_gcp_token_ttl)

        # If we already issued a token, enforce the effective TTL.
        if self._cached_gcp_token is not None:
            elapsed = (
                datetime.datetime.now(datetime.UTC) - self._token_issued_at
            ).total_seconds()
            effective_ttl = min(self._cached_gcp_token.ttl_seconds, max_policy_ttl)
            if elapsed >= effective_ttl:
                logger.info(
                    "GCP token expired: elapsed=%.0fs, effective_ttl=%ds "
                    "(vault_ttl=%ds, policy_max=%ds)",
                    elapsed,
                    effective_ttl,
                    self._cached_gcp_token.ttl_seconds,
                    max_policy_ttl,
                )
                self._audit.log_credential_event(
                    event_type=AuditEvent.CREDENTIAL_EXPIRED,
                    agent_id=self._identity.agent_id,
                    human_id=self._identity.human_id,
                    human_role=self._identity.human_role,
                    detail=f"elapsed={elapsed:.0f}s, effective_ttl={effective_ttl}s",
                    vault_token=self._identity.vault_token,
                )
                raise GCPCredentialError(
                    "GCP token has expired — re-authenticate"
                )
            return self._cached_gcp_token

        # Reconstruct the original Session from the identity context so the
        # credential broker can check session expiry accurately.
        session = Session(
            human_id=self._identity.human_id,
            human_role=self._identity.human_role,
            vault_token=self._identity.vault_token,
            token_policies=frozenset(),
            created_at=datetime.datetime.fromisoformat(self._identity.session_created_at),
            ttl_seconds=self._identity.session_ttl_seconds,
        )
        self._audit.log_credential_event(
            event_type=AuditEvent.CREDENTIAL_REQUESTED,
            agent_id=self._identity.agent_id,
            human_id=self._identity.human_id,
            human_role=self._identity.human_role,
            detail=f"impersonated_account={self._identity.gcp_impersonated_account}",
            vault_token=self._identity.vault_token,
        )
        token = self._gcp_broker.get_access_token(
            session=session,
            impersonated_account=self._identity.gcp_impersonated_account,
            requested_ttl=self._identity.max_gcp_token_ttl,
        )
        self._cached_gcp_token = token
        self._token_issued_at = datetime.datetime.now(datetime.UTC)

        effective_ttl = min(token.ttl_seconds, max_policy_ttl)
        logger.info(
            "Cached GCP token: vault_ttl=%ds, policy_max=%ds, effective_ttl=%ds",
            token.ttl_seconds,
            max_policy_ttl,
            effective_ttl,
        )
        self._audit.log_credential_event(
            event_type=AuditEvent.CREDENTIAL_ISSUED,
            agent_id=self._identity.agent_id,
            human_id=self._identity.human_id,
            human_role=self._identity.human_role,
            detail=f"effective_ttl={effective_ttl}s",
            vault_token=self._identity.vault_token,
        )
        return token

    # -- lifecycle ------------------------------------------------------------

    def setup_handlers(self) -> None:
        """Wire up MCP protocol handlers.  Call after all tools are registered."""
        server = self._server

        @server.list_tools()
        async def list_tools() -> list[Tool]:
            return self._get_visible_tools()

        @server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> Any:
            handler = self._get_handler(name)
            return await handler(arguments, gcp_token=self._get_gcp_token)

    @property
    def transport_mode(self) -> str:
        """Return the active transport mode (``"stdio"`` or ``"http"``)."""
        return os.environ.get("MCP_TRANSPORT", "stdio")

    async def run(self) -> None:
        """Start the MCP server on stdio."""
        from mcp.server.stdio import stdio_server

        self.setup_handlers()
        async with stdio_server() as (read_stream, write_stream):
            await self._server.run(
                read_stream,
                write_stream,
                self._server.create_initialization_options(),
            )

    def run_http(self) -> None:
        """Start the MCP server on Streamable HTTP transport."""
        from vault_mcp_agents.mcp.http_transport import run_http_server

        run_http_server(self)

    # -- private helpers ------------------------------------------------------

    @staticmethod
    def _load_identity() -> IdentityContext:
        raw = os.environ.get("MCP_IDENTITY_CONTEXT")
        if not raw:
            raise RuntimeError(
                "MCP_IDENTITY_CONTEXT environment variable is required but not set"
            )
        return IdentityContext.from_json(raw)
