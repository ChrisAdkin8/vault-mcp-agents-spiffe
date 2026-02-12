"""Adapter that bridges MCP client sessions into LangChain tools.

Pattern: Adapter / Bridge
---------------------------
LangChain agents consume ``BaseTool`` instances.  MCP servers expose tools via
the MCP protocol.  This module bridges the two:

  1. Connects to an MCP server subprocess using ``mcp.ClientSession``.
  2. Lists the tools the server exposes (already filtered by identity).
  3. Wraps each MCP tool as a LangChain ``StructuredTool``.

The adapter is intentionally thin — it does not add behaviour, only
translates types.  All access control has already happened on the MCP server
side.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import subprocess
import sys
from typing import Any, Optional

from langchain_core.tools import StructuredTool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel, Field, create_model

from vault_mcp_agents.mcp.identity_context import IdentityContext

logger = logging.getLogger(__name__)

_JSON_TYPE_MAP: dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _json_schema_to_pydantic(tool_name: str, schema: dict[str, Any]) -> type[BaseModel]:
    """Convert a JSON Schema *object* definition to a Pydantic model class.

    This lets LangChain advertise the correct parameter names, types and
    descriptions to the LLM, and validate inputs before calling the MCP tool.
    """
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    fields: dict[str, Any] = {}
    for prop_name, prop_schema in properties.items():
        py_type = _JSON_TYPE_MAP.get(prop_schema.get("type", "string"), str)
        description = prop_schema.get("description", "")
        default = prop_schema.get("default")

        if prop_name in required:
            fields[prop_name] = (py_type, Field(description=description))
        elif default is not None:
            fields[prop_name] = (py_type, Field(default=default, description=description))
        else:
            fields[prop_name] = (Optional[py_type], Field(default=None, description=description))

    class_name = "".join(part.capitalize() for part in tool_name.split("_")) + "Input"
    return create_model(class_name, **fields)


async def create_mcp_langchain_tools(
    server_command: str,
    server_args: list[str],
    identity_context: IdentityContext,
    vault_addr: str = "http://127.0.0.1:8200",
    gcp_mount: str = "gcp",
) -> tuple[list[StructuredTool], contextlib.AsyncExitStack]:
    """Start an MCP server subprocess and return LangChain tools wrapping its capabilities.

    Returns:
        A tuple of (tools, exit_stack) where exit_stack must be kept alive for
        the duration of the agent's execution. Call ``await exit_stack.aclose()``
        to shut down the MCP server cleanly.
    """
    env = {
        **os.environ,
        "MCP_IDENTITY_CONTEXT": identity_context.to_json(),
        "VAULT_ADDR": vault_addr,
        "VAULT_GCP_MOUNT": gcp_mount,
    }

    server_params = StdioServerParameters(
        command=server_command,
        args=server_args,
        env=env,
    )

    # Use AsyncExitStack to properly manage the async context managers.
    # Manually calling __aenter__/__aexit__ on stdio_client breaks anyio's
    # cancel-scope tracking because the enter and exit happen in different
    # task contexts.
    exit_stack = contextlib.AsyncExitStack()
    try:
        read_stream, write_stream = await exit_stack.enter_async_context(
            stdio_client(server_params)
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
        # Capture tool name in closure.
        tool_name = tool.name

        async def _call_mcp(
            _session: ClientSession = session,
            _name: str = tool_name,
            **kwargs: Any,
        ) -> str:
            result = await _session.call_tool(_name, arguments=kwargs)
            # Flatten TextContent list to a single string.
            parts = []
            for content in result.content:
                if hasattr(content, "text"):
                    parts.append(content.text)
            return "\n".join(parts) if parts else json.dumps({"status": "ok"})

        # Build a Pydantic model from the MCP tool's JSON Schema so that
        # LangChain advertises the correct parameters to the LLM.
        schema = getattr(tool, "inputSchema", None) or {}
        args_model = _json_schema_to_pydantic(tool.name, schema) if schema.get("properties") else None

        lc_tool = StructuredTool.from_function(
            coroutine=_call_mcp,
            name=tool.name,
            description=tool.description or "",
            args_schema=args_model,
        )
        langchain_tools.append(lc_tool)

    logger.info(
        "Created %d LangChain tools from MCP server (%s %s): %s",
        len(langchain_tools),
        server_command,
        " ".join(server_args),
        [t.name for t in langchain_tools],
    )

    return langchain_tools, exit_stack
