# Audit Logging

This guide documents the structured audit logging system used to track security-relevant events across the application.

## Overview

Every security-relevant action — tool access decisions, credential lifecycle events, policy violations, session management, and SPIFFE authentication — is recorded as a structured JSON event. These events form a tamper-evident audit trail suitable for compliance, incident investigation, and real-time monitoring.

## Design principles

1. **Vault tokens are never logged.** Only a 12-character SHA-256 prefix (the `session_id` field) is recorded for cross-event correlation.
2. **Single-line JSON.** Each event is a self-contained JSON object on one line, suitable for ingestion by log aggregation systems (ELK, Splunk, CloudWatch, Datadog).
3. **Fixed schema.** Every event contains `timestamp`, `level`, `logger`, and `event_type`. Additional fields vary by event type.
4. **No buffering.** Events are emitted synchronously via Python's `logging` module.

## Event types

| Event Type | Description | When it fires |
|-----------|-------------|---------------|
| `TOOL_ACCESS_ALLOWED` | An MCP tool invocation was permitted | `BaseMCPServer._get_handler()` allows the tool |
| `TOOL_ACCESS_DENIED` | An MCP tool invocation was rejected | `BaseMCPServer._get_handler()` rejects the tool |
| `CREDENTIAL_REQUESTED` | A GCP credential was requested from Vault | `BaseMCPServer._get_gcp_token()` initiates a Vault call |
| `CREDENTIAL_ISSUED` | A GCP credential was successfully issued | Vault returns a valid OAuth2 token |
| `CREDENTIAL_EXPIRED` | A cached GCP credential has expired | Token TTL exceeded on next access attempt |
| `POLICY_VIOLATION` | A policy lookup failed (unknown role/agent) | `PolicyEngine.resolve()` rejects the combination |
| `SESSION_CREATED` | A human successfully authenticated | `VaultAuthenticator.authenticate()` succeeds |
| `SESSION_EXPIRED` | A session's Vault token has expired | Checked in the conversation loop |
| `SPIFFE_AUTH_SUCCESS` | A workload authenticated via SPIFFE | `SpiffeAuthenticator.authenticate_workload()` succeeds |
| `SPIFFE_AUTH_FAILURE` | A SPIFFE authentication attempt failed | SVID retrieval or Vault auth fails |

## Event format

Every audit event is a JSON object with these common fields:

```json
{
  "timestamp": "2025-01-15T14:30:00.123456Z",
  "level": "INFO",
  "logger": "vault_mcp_agents.audit",
  "event_type": "TOOL_ACCESS_ALLOWED"
}
```

### Tool access events

```json
{
  "timestamp": "2025-01-15T14:30:00.123456Z",
  "level": "INFO",
  "logger": "vault_mcp_agents.audit",
  "event_type": "TOOL_ACCESS_ALLOWED",
  "agent_id": "data_agent",
  "human_id": "alice",
  "human_role": "operator",
  "tool_name": "list_buckets",
  "outcome": "allowed",
  "session_id": "a1b2c3d4e5f6"
}
```

For denied access, `event_type` is `TOOL_ACCESS_DENIED` and `outcome` is `"denied"`.

### Credential events

```json
{
  "timestamp": "2025-01-15T14:30:01.456789Z",
  "level": "INFO",
  "logger": "vault_mcp_agents.audit",
  "event_type": "CREDENTIAL_ISSUED",
  "agent_id": "data_agent",
  "human_id": "alice",
  "human_role": "operator",
  "detail": "effective_ttl=300s",
  "session_id": "a1b2c3d4e5f6"
}
```

### Session events

```json
{
  "timestamp": "2025-01-15T14:29:59.000000Z",
  "level": "INFO",
  "logger": "vault_mcp_agents.audit",
  "event_type": "SESSION_CREATED",
  "human_id": "alice",
  "human_role": "operator",
  "detail": "ttl=3600s, policies=['operator-policy', 'default']",
  "session_id": "a1b2c3d4e5f6"
}
```

### Policy violation events

```json
{
  "timestamp": "2025-01-15T14:30:00.000000Z",
  "level": "INFO",
  "logger": "vault_mcp_agents.audit",
  "event_type": "POLICY_VIOLATION",
  "human_role": "viewer",
  "agent_id": "data_agent",
  "detail": "Role 'viewer' has no policy for agent 'data_agent'",
  "outcome": "denied"
}
```

### SPIFFE authentication events

```json
{
  "timestamp": "2025-01-15T14:30:00.000000Z",
  "level": "INFO",
  "logger": "vault_mcp_agents.audit",
  "event_type": "SPIFFE_AUTH_SUCCESS",
  "spiffe_id": "spiffe://vault-mcp-demo/agent/data_agent",
  "detail": "policies=['operator-policy'], ttl=3600s"
}
```

## Token hashing

The `session_id` field in audit events is a **one-way, truncated hash** of the Vault token:

```python
session_id = hashlib.sha256(vault_token.encode()).hexdigest()[:12]
```

This provides:
- **Correlation** — events from the same session share the same `session_id`.
- **Security** — the full token cannot be recovered from the hash.
- **Uniqueness** — 12 hex characters (48 bits) provide sufficient collision resistance for log correlation.

## Configuration

In `config/settings.yaml`:

```yaml
audit:
  enabled: true
  log_file: ""          # Set a path to write audit events to a file
  log_to_stdout: true   # Emit audit events to stdout
```

| Option | Description |
|--------|-------------|
| `log_file` | Path to a JSON lines file. If empty, file logging is disabled. |
| `log_to_stdout` | Emit audit events to stdout alongside regular application logs. |

Both options can be enabled simultaneously for dual output.

## Integration points

The `AuditLogger` is instantiated in these components:

| Component | Events logged |
|-----------|---------------|
| `VaultAuthenticator` | `SESSION_CREATED` |
| `SpiffeAuthenticator` | `SPIFFE_AUTH_SUCCESS`, `SPIFFE_AUTH_FAILURE` |
| `PolicyEngine` | `POLICY_VIOLATION` |
| `BaseMCPServer` | `TOOL_ACCESS_ALLOWED`, `TOOL_ACCESS_DENIED`, `CREDENTIAL_REQUESTED`, `CREDENTIAL_ISSUED`, `CREDENTIAL_EXPIRED` |

## Querying audit logs

Since events are single-line JSON, standard tools work well:

```bash
# Find all denied tool access events
grep '"TOOL_ACCESS_DENIED"' audit.log | jq .

# Find all events for a specific user
grep '"alice"' audit.log | jq .

# Find all credential events in the last hour
grep '"CREDENTIAL_' audit.log | jq 'select(.timestamp > "2025-01-15T13:30:00")'

# Count events by type
cat audit.log | jq -r '.event_type' | sort | uniq -c | sort -rn
```

## Key files

| File | Purpose |
|------|---------|
| `src/vault_mcp_agents/audit/logger.py` | `AuditLogger` class and `AuditEvent` enum |
| `src/vault_mcp_agents/audit/formatter.py` | `JSONFormatter` for single-line JSON output |
