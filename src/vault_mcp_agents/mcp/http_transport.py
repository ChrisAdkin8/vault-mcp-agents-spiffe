"""HTTP transport for MCP servers using Streamable HTTP.

This module creates a Starlette/ASGI application that serves an MCP server
over the Streamable HTTP transport (MCP spec 2025-06-18).  It is the
network-based counterpart to the stdio transport used in local development.

When X.509 SVIDs are available at ``/etc/mcp/certs/`` (rendered by Vault
Agent), the server enables mTLS — providing both transport encryption and
cryptographic workload identity via the SPIFFE URI SAN in the certificate.

Usage::

    from vault_mcp_agents.mcp.data_server import DataMCPServer

    server = DataMCPServer()
    app = create_http_app(server)
    # Run with: uvicorn ... --host 0.0.0.0 --port 8001
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from mcp.server.streamable_http import StreamableHTTPServerTransport

from vault_mcp_agents.mcp.base_server import BaseMCPServer
from vault_mcp_agents.mcp.http_identity_middleware import IdentityContextMiddleware

logger = logging.getLogger(__name__)

# Default certificate paths rendered by Vault Agent
CERT_DIR = Path("/etc/mcp/certs")
CERT_FILE = CERT_DIR / "server.crt"
KEY_FILE = CERT_DIR / "server.key"
CA_FILE = CERT_DIR / "ca.crt"


def _tls_available() -> bool:
    """Check whether Vault Agent has rendered SVID certificates."""
    return CERT_FILE.is_file() and KEY_FILE.is_file() and CA_FILE.is_file()


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

    When Vault Agent has rendered X.509 SVIDs to ``/etc/mcp/certs/``, the
    server starts with mTLS enabled (TLS + client certificate verification).
    Otherwise it falls back to plain HTTP for local development.
    """
    import ssl

    import uvicorn

    app = create_http_app(server)
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8000"))

    if _tls_available():
        logger.info(
            "SVID certificates found at %s — starting with mTLS enabled",
            CERT_DIR,
        )
        # Note: SPIFFE URI SAN validation (checking the peer certificate's
        # spiffe:// URI) is not possible at the uvicorn/ASGI layer — Python's
        # ssl module and uvicorn do not expose the peer certificate to
        # application code.  However, since the project runs its own Vault PKI
        # CA with a single role and a single allowed SPIFFE ID, any certificate
        # signed by this CA *is* the authorised MCP workload.
        # ssl.CERT_REQUIRED ensures only holders of a cert from this CA can
        # connect.  For production deployments requiring per-connection SPIFFE
        # ID extraction, use Envoy or Istio for mTLS termination.
        logger.info("MCP HTTPS server listening on %s:%d (mTLS)", host, port)
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            ssl_certfile=str(CERT_FILE),
            ssl_keyfile=str(KEY_FILE),
            ssl_ca_certs=str(CA_FILE),
            ssl_cert_reqs=ssl.CERT_REQUIRED,
            ssl_ciphers="ECDHE+AESGCM:ECDHE+CHACHA20",
        )
    else:
        logger.info(
            "No SVID certificates at %s — starting in plain HTTP mode",
            CERT_DIR,
        )
        logger.info("MCP HTTP server listening on %s:%d", host, port)
        uvicorn.run(app, host=host, port=port, log_level="info")
