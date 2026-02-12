"""ASGI middleware that extracts identity context from HTTP headers.

For the HTTP/Streamable HTTP transport, the composite identity is delivered
via an ``X-Identity-Context`` header containing a base64-encoded JSON payload
(the same ``IdentityContext`` that is passed via environment variable in the
stdio transport).
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from vault_mcp_agents.audit.logger import AuditLogger
from vault_mcp_agents.mcp.identity_context import IdentityContext

logger = logging.getLogger(__name__)

IDENTITY_HEADER = "X-Identity-Context"


class IdentityContextMiddleware(BaseHTTPMiddleware):
    """Extract and validate identity context from every inbound request.

    The identity is attached to ``request.state.identity_context`` so that
    downstream handlers can access it.  If the header is missing or malformed
    the request is rejected with a 401 response.
    """

    def __init__(self, app: Any, *, audit: AuditLogger | None = None) -> None:
        super().__init__(app)
        self._audit = audit or AuditLogger(log_to_stdout=True)

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        # Health endpoint is always unauthenticated.
        if request.url.path == "/health":
            return await call_next(request)

        raw_header = request.headers.get(IDENTITY_HEADER)
        if not raw_header:
            logger.warning("Missing %s header from %s", IDENTITY_HEADER, request.client)
            return JSONResponse(
                status_code=401,
                content={"error": f"Missing {IDENTITY_HEADER} header"},
            )

        try:
            decoded = base64.b64decode(raw_header).decode("utf-8")
            identity = IdentityContext.from_json(decoded)
        except (json.JSONDecodeError, KeyError, ValueError, Exception) as exc:
            logger.warning("Malformed %s header: %s", IDENTITY_HEADER, exc)
            return JSONResponse(
                status_code=401,
                content={"error": f"Malformed {IDENTITY_HEADER} header"},
            )

        request.state.identity_context = identity
        return await call_next(request)


def encode_identity_header(identity: IdentityContext) -> str:
    """Encode an ``IdentityContext`` as a base64 string for the HTTP header."""
    return base64.b64encode(identity.to_json().encode("utf-8")).decode("ascii")
