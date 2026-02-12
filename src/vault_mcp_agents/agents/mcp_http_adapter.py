"""Adapter that bridges MCP HTTP client sessions into LangChain tools.

This is the HTTP/Streamable HTTP counterpart of ``mcp_langchain_adapter.py``
which uses the stdio transport.  The identity context is delivered via the
``X-Identity-Context`` HTTP header instead of an environment variable.
"""

from __future__ import annotations

import contextlib
import json
import logging
from typing import Any

from langchain_core.tools import StructuredTool
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from vault_mcp_agents.agents.mcp_langchain_adapter import _json_schema_to_pydantic
from vault_mcp_agents.mcp.http_identity_middleware import encode_identity_header
from vault_mcp_agents.mcp.identity_context import IdentityContext

logger = logging.getLogger(__name__)


async def create_mcp_http_langchain_tools(
    server_url: str,
    identity_context: IdentityContext,
) -> tuple[list[StructuredTool], contextlib.AsyncExitStack]:
    """Connect to an MCP server over Streamable HTTP and return LangChain tools.

    Args:
        server_url: Full URL to the MCP endpoint (e.g. ``http://data-mcp-server:8001/mcp``).
        identity_context: Composite identity passed via ``X-Identity-Context`` header.

    Returns:
        A tuple of (tools, exit_stack) — the caller must keep exit_stack alive
        and call ``await exit_stack.aclose()`` when done.
    """
    headers = {
        "X-Identity-Context": encode_identity_header(identity_context),
    }

    exit_stack = contextlib.AsyncExitStack()
    try:
        read_stream, write_stream, _ = await exit_stack.enter_async_context(
            streamablehttp_client(url=server_url, headers=headers)
        )
        session = await exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await session.initialize()
    except BaseException:
        await exit_stack.aclose()
        raise

    mcp_tools = await session.list_tools()
    langchain_tools: list[StructuredTool] = []

    for tool in mcp_tools.tools:
        tool_name = tool.name

        async def _call_mcp(
            _session: ClientSession = session,
            _name: str = tool_name,
            **kwargs: Any,
        ) -> str:
            result = await _session.call_tool(_name, arguments=kwargs)
            parts = []
            for content in result.content:
                if hasattr(content, "text"):
                    parts.append(content.text)
            return "\n".join(parts) if parts else json.dumps({"status": "ok"})

        schema = getattr(tool, "inputSchema", None) or {}
        args_model = (
            _json_schema_to_pydantic(tool.name, schema)
            if schema.get("properties")
            else None
        )

        lc_tool = StructuredTool.from_function(
            coroutine=_call_mcp,
            name=tool.name,
            description=tool.description or "",
            args_schema=args_model,
        )
        langchain_tools.append(lc_tool)

    logger.info(
        "Created %d LangChain tools from MCP HTTP server (%s): %s",
        len(langchain_tools),
        server_url,
        [t.name for t in langchain_tools],
    )

    return langchain_tools, exit_stack
