# Multi-stage build for the agent CLI container.

FROM python:3.13-slim AS builder

WORKDIR /app
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir .

FROM python:3.13-slim AS runtime

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY config/ config/
COPY policies/ policies/

ENV VAULT_ADDR=http://vault:8200
ENV PYTHONUNBUFFERED=1

CMD ["vault-mcp-agents"]
