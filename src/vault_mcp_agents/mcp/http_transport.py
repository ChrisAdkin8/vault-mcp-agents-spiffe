"""HTTP transport for MCP servers using Streamable HTTP.

This module creates a Starlette/ASGI application that serves an MCP server
over the Streamable HTTP transport (MCP spec 2025-06-18).  It is the
network-based counterpart to the stdio transport used in local development.

Usage::

    from vault_mcp_agents.mcp.data_server import DataMCPServer

    server = DataMCPServer()
    app = create_http_app(server)
    # Run with: uvicorn ... --host 0.0.0.0 --port 8001
"""

from __future__ import annotations

import logging
import os
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from mcp.server.streamable_http import StreamableHTTPServerTransport

from vault_mcp_agents.mcp.base_server import BaseMCPServer
from vault_mcp_agents.mcp.http_identity_middleware import IdentityContextMiddleware

logger = logging.getLogger(__name__)


async def _health(request: Request) -> JSONResponse:
    """Unauthenticated health check endpoint."""
    return JSONResponse({"status": "ok"})


def create_http_app(server: BaseMCPServer) -> Starlette:
    """Create a Starlette ASGI app serving *server* over Streamable HTTP.

    The app exposes:

    - ``/health``  — unauthenticated health probe.
    - ``/mcp``     — MCP Streamable HTTP endpoint (POST + GET).

    All requests except ``/health`` must include the ``X-Identity-Context``
    header (base64-encoded JSON ``IdentityContext``).
    """
    server.setup_handlers()

    transport = StreamableHTTPServerTransport(
        mcp_session_id=None,  # Stateless mode
    )

    async def handle_mcp(request: Request) -> Any:
        """Route MCP requests through the Streamable HTTP transport."""
        return await transport.handle_request(request.scope, request.receive, request._send)

    async def on_startup() -> None:
        logger.info("Starting MCP HTTP server")
        await transport.connect(server._server)

    routes = [
        Route("/health", endpoint=_health, methods=["GET"]),
        Mount("/mcp", app=transport.handle_request),
    ]

    app = Starlette(
        routes=routes,
        on_startup=[on_startup],
    )
    app.add_middleware(IdentityContextMiddleware)

    return app


def run_http_server(server: BaseMCPServer) -> None:
    """Create the HTTP app and run it with uvicorn.

    Reads ``MCP_HOST`` (default ``0.0.0.0``) and ``MCP_PORT`` (default ``8000``)
    from environment variables.
    """
    import uvicorn

    app = create_http_app(server)
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8000"))
    logger.info("MCP HTTP server listening on %s:%d", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")
