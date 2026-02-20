# Security Model

This document describes the threat model, defence-in-depth layers, and security considerations for the project.

## OWASP Agentic AI threat mapping

This project mitigates three threats from the [OWASP Top 10 for Agentic Applications (2026)](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/):

| OWASP ID | Threat | Mitigation |
|----------|--------|------------|
| **ASI03** | Identity & Privilege Abuse | Vault brokers all credentials — human auth, agent identity, and GCP tokens are issued with a hard 5-minute TTL. No long-lived keys exist on disk. |
| **ASI02** | Tool Misuse & Exploitation | A YAML policy maps each `(human_role, agent_id)` pair to an explicit tool allowlist. The MCP server only exposes permitted tools. |
| **ASI10** | Rogue Agents | Short-lived credentials and per-agent tool scoping contain the blast radius. A compromised agent can only reach its allowed tools, and any stolen GCP token expires within minutes. |

## Trust boundaries

Local (stdio transport):

```
┌──────────────────────────────────────────────────┐
│                  User's machine                  │
│                                                  │
│  ┌────────┐    ┌────────────┐    ┌─────────────┐ │
│  │  CLI   │───>│ Agent proc │───>│ MCP server  │ │
│  │(human) │    │(LangChain) │    │ (subprocess) │ │
│  └────────┘    └────────────┘    └──────┬──────┘ │
│                                         │        │
└─────────────────────────────────────────┼────────┘
                                          │
                          ┌───────────────▼──────────────┐
                          │        Vault (network)       │
                          │  - authenticates human       │
                          │  - issues GCP tokens         │
                          │  - enforces path policies    │
                          └───────────────┬──────────────┘
                                          │
                          ┌───────────────▼──────────────┐
                          │        GCP APIs (network)    │
                          └──────────────────────────────┘
```

Containerised (HTTP + mTLS via Vault Agent):

```
┌──────────────────────────────────────────────────────────────┐
│                   Docker network (mcp-net)                    │
│                                                              │
│            ┌──────────────────────────────┐                  │
│            │       Vault Agent            │                  │
│            │   (AppRole → PKI → SVIDs)    │                  │
│            └──────┬───────────────┬───────┘                  │
│         certs-vol │               │ certs-vol                │
│                   ▼               ▼                          │
│  ┌────────┐ mTLS ┌──────────────┐ ┌──────────────┐          │
│  │agent-  │─────▶│ data-mcp-    │ │ compute-mcp- │          │
│  │cli     │─────▶│ server :8001 │ │ server :8002 │          │
│  └───┬────┘      └──────┬───────┘ └──────┬───────┘          │
│      │                  │                │                   │
└──────┼──────────────────┼────────────────┼───────────────────┘
       │                  │                │
       │     ┌────────────▼────────────────▼───────────────┐
       └────▶│      Vault (network)             │
             │  - authenticates human (userpass)            │
             │  - issues X.509 SVIDs via PKI               │
             │  - issues GCP tokens                         │
             │  - enforces path policies                    │
             └──────────────────────┬──────────────────────┘
                                    │
             ┌──────────────────────▼──────────────────────┐
             │           GCP APIs (network)                │
             └─────────────────────────────────────────────┘
```

In the containerised deployment, the trust boundary extends to the Docker bridge network. MCP servers run as separate containers communicating over mTLS, using X.509 SVIDs with SPIFFE URI SANs rendered by the Vault Agent sidecar — no static secrets exist in the container images.

## Defence-in-depth layers

Access to GCP resources is controlled by five independent layers. Each layer provides protection even if another is compromised:

| Layer | What it checks | Component |
|-------|---------------|-----------|
| **1. Vault authentication** | Human is who they claim to be; token gets correct policies | `VaultAuthenticator` |
| **2. Vault GCP secrets engine** | Human's token policies allow access to the requested GCP impersonated account | Vault server-side |
| **3. Application policy engine** | The `(human_role, agent_id)` pair allows the requested MCP tool name | `PolicyEngine` |
| **4. MCP server tool filtering** | Tool registry only contains tools the identity context permits | `BaseMCPServer._get_visible_tools()` |
| **5. GCP IAM** | The Vault-issued service account has the necessary GCP IAM roles | GCP server-side |

### Why five layers?

Any single layer can fail:

- Vault policies could be misconfigured → Layers 3 and 4 still block tool misuse.
- Policy YAML could be tampered with → Layers 1 and 2 still restrict which GCP accounts are accessible.
- An MCP tool could have a bug → Layer 5 (GCP IAM) limits what the leaked token can do.
- GCP IAM could be overly permissive → Layer 3 limits which tools can be called at all.

## Credential lifecycle

```
Human authenticates    Policy resolved     Tool invoked        Token expires
       │                    │                   │                   │
       ▼                    ▼                   ▼                   ▼
   ┌────────┐          ┌────────┐         ┌────────────┐     ┌──────────┐
   │ Vault  │─ token ─>│ Policy │─ ctx ──>│ MCP server │     │ GCP API  │
   │ auth   │  (1h)    │ engine │         │ calls Vault│────>│ rejects  │
   └────────┘          └────────┘         │ for GCP    │     │ stale    │
                                          │ token (5m) │     │ token    │
                                          └────────────┘     └──────────┘
```

1. Human authenticates → receives a Vault token (TTL from Vault config, typically 1 hour).
2. Agent factory resolves policy → `max_gcp_token_ttl` (`"5m"` for all roles).
3. MCP server tool handler calls `_get_gcp_token()` → Vault issues an OAuth2 token.
4. Token TTL = min(policy TTL, Vault impersonated account TTL, session remaining TTL).
5. GCP API call uses the short-lived token.
6. Token expires (after at most 5 minutes); next call requires a fresh token.

**No credential is stored on disk. No credential outlives the session.**

## 5-minute TTL enforcement

The 5-minute ceiling is enforced at two independent layers:

| Layer | Configuration | Enforcement point |
|-------|--------------|-------------------|
| **Vault GCP impersonated account** | `ttl = "300"` in `vault_init.sh` | Server-side — Vault passes this as the `lifetime` to GCP's `generateAccessToken` API |
| **Application policy** | `max_gcp_token_ttl: "5m"` in `capabilities.yaml` | Client-side — `BaseMCPServer._get_gcp_token()` computes `effective_ttl = min(vault_ttl, policy_max)` |

Even if one layer is misconfigured, the other still caps credential lifetime.

## Token handling

### Vault tokens

- Created at human login, stored only in the in-memory `Session` object.
- Passed to the MCP server via `IdentityContext` (environment variable for stdio, HTTP header for HTTP transport).
- Never logged directly — only a 12-character SHA-256 prefix is recorded in audit logs.
- Never written to disk.

### GCP OAuth2 tokens

- Obtained on-demand from Vault's GCP secrets engine.
- Cached in `BaseMCPServer._cached_gcp_token` for the effective TTL duration.
- Never stored on disk.
- After expiry, the server raises `GCPCredentialError` — the human must re-authenticate.

## Transport security

### Stdio transport (local development)

- Agent spawns MCP server as a subprocess on the same machine.
- Identity context is passed via the `MCP_IDENTITY_CONTEXT` environment variable.
- No network exposure — communication happens over stdin/stdout pipes.
- **Risk:** Environment variables are visible to processes with the same UID. Acceptable for local development.

### HTTP transport (containerised deployment)

- MCP servers run as HTTP services on a Docker bridge network.
- Identity context is passed via the `X-Identity-Context` HTTP header (base64-encoded JSON).
- The header contains the human's Vault token — necessary for GCP credential issuance.

**Security considerations for HTTP mode:**

| Concern | Mitigation |
|---------|------------|
| MCP ports exposed externally | MCP server ports are **not** exposed outside the Docker network (no `ports:` mapping in `docker-compose.yaml`) |
| Vault token in transit | mTLS encrypts all agent-to-MCP traffic; Vault tokens are never transmitted in plaintext |
| Header spoofing | mTLS with `ssl.CERT_REQUIRED` ensures only certificate holders can connect |
| Workload impersonation | Vault Agent renders X.509 SVIDs with SPIFFE URI SANs; clients must present a valid certificate signed by the project CA |

**mTLS enforcement details:**

The MCP servers start uvicorn with `ssl_cert_reqs=ssl.CERT_REQUIRED`, meaning every connecting client must present a certificate signed by the project's internal CA. Since the Vault PKI engine has a single role (`mcp-server`) with a single allowed SPIFFE ID (`spiffe://my-trust-domain/ns/default/sa/mcp`), any certificate from this CA is guaranteed to belong to an authorised workload.

**SPIFFE URI SAN validation limitation:** Uvicorn and Python's ASGI layer do not expose the peer certificate to application code, so per-connection SPIFFE ID extraction is not possible at this layer. The project-internal CA already constrains identity sufficiently for this deployment model. For production deployments requiring per-connection SPIFFE ID validation, use Envoy or Istio for mTLS termination with SPIFFE-aware SAN enforcement.

### Production recommendations

For production deployments beyond the proof-of-concept:

1. **mTLS is enforced** — Vault Agent renders X.509 SVIDs; MCP servers require client certificates (`CERT_REQUIRED`); clients present certificates via httpx.
2. **Use Envoy/Istio** for SPIFFE-aware mTLS termination with per-connection SPIFFE URI SAN validation.
3. **Use network policies** to restrict MCP server access to authorised agent containers only.
4. **Use a remote Terraform backend** with encryption for state files containing GCP service account keys (if using Terraform for GCP provisioning).
5. **Rotate Vault root token** — the dev-mode root token is for development only.
6. **Configure Vault audit logging** in addition to application-level audit logging.
7. **Rotate SVIDs** — configure Vault Agent template `max_stale` and PKI role TTLs for regular certificate rotation.

## Session expiry

The `Session.is_expired` property checks whether the elapsed time since session creation exceeds the token TTL:

```python
@property
def is_expired(self) -> bool:
    elapsed = (datetime.now(UTC) - self.created_at).total_seconds()
    return elapsed >= self.ttl_seconds
```

The conversation loop checks this before every agent invocation and terminates the session if expired.

## Policy violation handling

When the policy engine cannot resolve a `(role, agent_id)` pair:

1. A `POLICY_VIOLATION` audit event is logged.
2. A `PolicyError` exception is raised.
3. The agent is not constructed.

When an MCP tool call is attempted for a tool not in the identity context:

1. A `TOOL_ACCESS_DENIED` audit event is logged.
2. A `PermissionError` is raised.
3. The LLM receives the error and informs the user.

## Immutability guarantees

All security-critical data structures are frozen dataclasses:

| Class | Frozen | Purpose |
|-------|--------|---------|
| `Session` | Yes | Human authentication proof |
| `WorkloadSession` | Yes | Workload authentication proof |
| `IdentityContext` | Yes | Composite identity for MCP servers |
| `ResolvedPolicy` | Yes | Policy resolution result |
| `GCPAccessToken` | Yes | Short-lived GCP credential |

Frozen dataclasses prevent accidental mutation of security-critical state after creation.
