# Terraform — GCP + Vault Configuration

This Terraform configuration creates GCP service accounts for Vault and its agents, and configures the Vault GCP secrets engine with two impersonated accounts that issue 5-minute OAuth2 tokens. No service-account key file is written to disk — the key material flows directly from GCP into Vault via Terraform state.

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

| Resource | Purpose |
|---|---|
| GCP service account (`vault-gcp-secrets@<project>.iam`) | Identity Vault uses to impersonate agent service accounts |
| GCP service account (`data-agent-gcp@<project>.iam`) | Agent identity with `roles/storage.admin` + `roles/bigquery.admin` |
| GCP service account (`compute-agent-gcp@<project>.iam`) | Agent identity with `roles/compute.admin` |
| IAM binding: `serviceAccountTokenCreator` | Allows Vault's SA to generate OAuth2 tokens for agent SAs |
| Vault GCP secrets backend (`gcp/`) | Enables and configures the secrets engine |
| Vault impersonated account `data-agent-gcp` | 5-minute OAuth2 tokens for data agent operations |
| Vault impersonated account `compute-agent-gcp` | 5-minute OAuth2 tokens for compute agent operations |

## Important notes

- **IAM propagation delay:** After `terraform apply`, wait 1–2 minutes before requesting GCP tokens through Vault. GCP IAM bindings can take up to 60 seconds to propagate.
- **State contains secrets:** `terraform.tfstate` holds the GCP service account key. For production, use a [remote backend](https://developer.hashicorp.com/terraform/language/settings/backends/configuration) with encryption (e.g., GCS with CMEK).
- **Teardown:** `terraform destroy` deletes the GCP service account and invalidates any active Vault leases.

## Variables

| Variable | Default | Description |
|---|---|---|
| `gcp_project_id` | *(required)* | GCP project ID |
| `gcp_region` | `us-central1` | Default GCP region |
| `vault_address` | `http://127.0.0.1:8200` | Vault server address |
| `vault_token` | `dev-root-token` | Vault token (sensitive) |
| `vault_gcp_secrets_mount` | `gcp` | Vault GCP secrets mount path |
| `vault_service_account_id` | `vault-gcp-secrets` | GCP service account ID |
