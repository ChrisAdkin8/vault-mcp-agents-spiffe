# Multi-stage build for MCP servers (data_server / compute_server).
# Build with:
#   docker build -f docker/mcp-server.Dockerfile \
#     --build-arg MCP_SERVER_MODULE=vault_mcp_agents.mcp.data_server .

FROM python:3.13-slim AS builder

WORKDIR /app
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir .

FROM python:3.13-slim AS runtime

# Install curl for health checks.
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY config/ config/
COPY policies/ policies/

ARG MCP_SERVER_MODULE=vault_mcp_agents.mcp.data_server
ENV MCP_SERVER_MODULE=${MCP_SERVER_MODULE}
ENV MCP_TRANSPORT=http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000
ENV PYTHONUNBUFFERED=1

EXPOSE ${MCP_PORT}

HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
    CMD curl -f http://localhost:${MCP_PORT}/health || exit 1

CMD python -m ${MCP_SERVER_MODULE}
