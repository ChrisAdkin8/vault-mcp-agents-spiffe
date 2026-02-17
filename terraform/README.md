# Terraform — GCP Resource Provisioning

This Terraform configuration creates the GCP service accounts and IAM bindings required by the Vault GCP secrets engine. It does **not** configure Vault itself — that is handled automatically by the `vault-init` container in `docker-compose.yaml` (see [`scripts/vault_init.sh`](../scripts/vault_init.sh)).

## File layout

| File | Purpose |
|---|---|
| `main.tf` | Provider configuration (Google) |
| `gcp.tf` | All GCP resources: service accounts (Vault + agents), IAM bindings, SA keys, impersonation grants |
| `variables.tf` | Input variables (project ID, region) |
| `outputs.tf` | GCP outputs: SA emails, SA key (base64) |
| `versions.tf` | Provider version constraints (Google) |

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

## Extracting the SA key for Docker Compose

After `terraform apply`, extract the service account key and save it to a file:

```bash
terraform output -raw vault_sa_key_base64 | base64 -d > sa-key.json
```

Then configure `docker/.env`:

```
GCP_SA_KEY_FILE=./sa-key.json
DATA_AGENT_SA_EMAIL=data-agent-gcp@YOUR_PROJECT.iam.gserviceaccount.com
COMPUTE_AGENT_SA_EMAIL=compute-agent-gcp@YOUR_PROJECT.iam.gserviceaccount.com
```

You can get the exact email addresses from Terraform outputs:

```bash
terraform output data_agent_service_account_email
terraform output compute_agent_service_account_email
```

The `vault-init` container in Docker Compose will use these to configure the Vault GCP secrets engine with 5-minute credential TTLs automatically.

## Important notes

- **IAM propagation delay:** After `terraform apply`, wait 1-2 minutes before requesting GCP tokens through Vault. GCP IAM bindings can take up to 60 seconds to propagate.
- **State contains secrets:** `terraform.tfstate` holds the GCP service account key. For production, use a [remote backend](https://developer.hashicorp.com/terraform/language/settings/backends/configuration) with encryption (e.g., GCS with CMEK).
- **Teardown:** `terraform destroy` deletes the GCP service accounts and invalidates any active credentials.

## Variables

| Variable | Default | Description |
|---|---|---|
| `gcp_project_id` | *(required)* | GCP project ID |
| `gcp_region` | `us-central1` | Default GCP region |
| `vault_service_account_id` | `vault-gcp-secrets` | GCP service account ID for Vault |

## Outputs

| Output | Description |
|---|---|
| `vault_service_account_email` | Email of Vault's GCP service account |
| `data_agent_service_account_email` | Email of the data agent GCP service account |
| `compute_agent_service_account_email` | Email of the compute agent GCP service account |
| `vault_sa_key_base64` | Base64-encoded SA key (sensitive) — decode and save to a file for Docker Compose |
