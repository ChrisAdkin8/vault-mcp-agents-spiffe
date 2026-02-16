# Terraform — GCP + Vault Configuration

This Terraform configuration creates GCP service accounts for Vault and its agents, configures the Vault GCP secrets engine with two impersonated accounts that issue 5-minute OAuth2 tokens, provisions a PKI engine for SPIFFE X.509 SVIDs, and sets up AppRole and Kubernetes auth backends. No service-account key file is written to disk — the key material flows directly from GCP into Vault via Terraform state.

## File layout

| File | Purpose |
|---|---|
| `main.tf` | Provider configuration (Google + Vault + Local) |
| `gcp.tf` | All GCP resources: service accounts (Vault + agents), IAM bindings, SA keys, impersonation grants |
| `vault_gcp_secrets.tf` | Vault GCP secrets engine and impersonated accounts with 5-minute token TTL |
| `vault_pki.tf` | PKI engine for SPIFFE SVIDs: root CA, issuing URLs, SPIFFE-compliant certificate role |
| `vault_auth.tf` | Vault policy, AppRole auth (Docker Compose), Kubernetes auth (K8s migration) |
| `creds_export.tf` | Writes AppRole `role_id` and `secret_id` to `/creds/` for the Vault Agent sidecar |
| `variables.tf` | Input variables (project ID, region, Vault address, etc.) |
| `outputs.tf` | GCP outputs: SA email, GCP secrets mount path |
| `versions.tf` | Provider version constraints (Google, Vault, Local) |

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.5
- `gcloud` CLI installed and authenticated:
  ```bash
  gcloud auth application-default login
  ```
- Your GCP user account needs the following IAM roles on the target project:
  - `roles/iam.serviceAccountAdmin` (create service accounts)
  - `roles/iam.serviceAccountKeyAdmin` (create SA keys)
  - `roles/resourcemanager.projectIamAdmin` (grant IAM bindings)
- Vault dev server running (`docker compose up -d` from the project root)
- `scripts/setup_vault.sh` already executed (creates userpass auth, policies, test users)

## Quick start

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars — set gcp_project_id to your GCP project
terraform init
terraform plan
terraform apply
```

## What this creates

### GCP resources (`gcp.tf`)

| Resource | Purpose |
|---|---|
| GCP service account (`vault-gcp-secrets@<project>.iam`) | Identity Vault uses to impersonate agent service accounts |
| GCP service account (`data-agent-gcp@<project>.iam`) | Agent identity with `roles/storage.admin` + `roles/bigquery.admin` |
| GCP service account (`compute-agent-gcp@<project>.iam`) | Agent identity with `roles/compute.admin` |
| IAM bindings on Vault SA | `serviceAccountAdmin`, `serviceAccountKeyAdmin`, `serviceAccountTokenCreator`, `projectIamAdmin` |
| IAM binding: `serviceAccountTokenCreator` on agent SAs | Allows Vault's SA to generate OAuth2 tokens for agent SAs |

### Vault GCP secrets (`vault_gcp_secrets.tf`)

| Resource | Purpose |
|---|---|
| Vault GCP secrets backend (`gcp/`) | Enables and configures the secrets engine |
| Vault impersonated account `data-agent-gcp` | 5-minute OAuth2 tokens for data agent operations |
| Vault impersonated account `compute-agent-gcp` | 5-minute OAuth2 tokens for compute agent operations |

### Vault PKI (`vault_pki.tf`)

| Resource | Purpose |
|---|---|
| PKI secrets engine (`pki/`) | Mount for issuing SPIFFE X.509 SVIDs |
| Internal root CA (`MCP Root CA`) | 10-year self-signed root certificate |
| PKI role `mcp-server` | SPIFFE-compliant role allowing `spiffe://my-trust-domain/ns/*/sa/*` URI SANs |

### Vault auth and policy (`vault_auth.tf`)

| Resource | Purpose |
|---|---|
| `mcp-policy` | Vault policy granting `pki/issue/mcp-server` access |
| AppRole auth backend + `mcp-role` | Docker Compose workload authentication for Vault Agent |
| Kubernetes auth backend + `mcp-server` role | Pre-configured for Kubernetes migration (see below) |

### Credential export (`creds_export.tf`)

| Resource | Purpose |
|---|---|
| `/creds/role_id` | AppRole role ID written to shared Docker volume |
| `/creds/secret_id` | AppRole secret ID written to shared Docker volume |

These files are consumed by the Vault Agent sidecar at startup. The agent reads them, authenticates to Vault via AppRole, and uses the resulting token to render X.509 SVIDs from the PKI engine.

## Kubernetes auth backend

The Kubernetes auth backend and `mcp-server` role are pre-configured for the migration from Docker Compose to Kubernetes. The Docker Compose stack uses AppRole auth (credentials written to a shared volume by Terraform), but the same Vault PKI role and policy work with both auth methods.

When deploying to Kubernetes:
- Pods authenticate using their service account token instead of AppRole credentials
- The Vault Agent Injector admission controller replaces the manual `vault-agent` sidecar — it injects the same agent automatically based on pod annotations
- The `mcp-server` K8s role is bound to service account `mcp-sa` in the `default` namespace (update these for your cluster)
- No changes to the PKI configuration, policy, or MCP server code are needed

This pre-configuration means the Terraform state is ready for Kubernetes from day one — only the auth method changes, not the certificate infrastructure.

## Important notes

- **IAM propagation delay:** After `terraform apply`, wait 1–2 minutes before requesting GCP tokens through Vault. GCP IAM bindings can take up to 60 seconds to propagate.
- **State contains secrets:** `terraform.tfstate` holds the GCP service account key and AppRole secret ID. For production, use a [remote backend](https://developer.hashicorp.com/terraform/language/settings/backends/configuration) with encryption (e.g., GCS with CMEK).
- **Teardown:** `terraform destroy` deletes the GCP service account, Vault mounts, and invalidates any active Vault leases.

## Variables

| Variable | Default | Description |
|---|---|---|
| `gcp_project_id` | *(required)* | GCP project ID |
| `gcp_region` | `us-central1` | Default GCP region |
| `vault_address` | `http://127.0.0.1:8200` | Vault server address |
| `vault_token` | `dev-root-token` | Vault token (sensitive) |
| `vault_gcp_secrets_mount` | `gcp` | Vault GCP secrets mount path |
| `vault_service_account_id` | `vault-gcp-secrets` | GCP service account ID |
