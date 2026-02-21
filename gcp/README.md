# GCP Configuration for Document Archive

Google Cloud Platform storage provisioning for document archiving with Cloud Storage and optional Iceberg support.

## Files

- **gcs_bucket.tf** - Terraform template for GCP infrastructure
  - GCS bucket with lifecycle policies
  - Automatic storage class transitions (Standard → Nearline → Coldline → Archive)
  - KMS encryption at rest
  - Service Account with minimal IAM permissions
  - Optional Iceberg warehouse bucket
  - Versioning and object retention

## Quick Start

```bash
# Set up Terraform
cd gcp
terraform init

# Plan deployment
terraform plan \
  -var="project_id=my-project" \
  -var="environment=dev" \
  -var="region=us-central1" \
  -var="create_iceberg_warehouse=true"

# Apply
terraform apply \
  -var="project_id=my-project" \
  -var="environment=dev" \
  -var="region=us-central1" \
  -var="create_iceberg_warehouse=true"

# Get outputs
terraform output
```

## Configuration

Update `config.yaml`:

```yaml
storage:
  provider: gcp_storage
  gcp:
    project_id: my-project
    credentials_path: /path/to/service-account-key.json
    bucket_name: document-archive-my-project
```

Or use Application Default Credentials:

```bash
gcloud auth application-default login
```

```yaml
storage:
  provider: gcp_storage
  gcp:
    project_id: my-project
    bucket_name: document-archive-my-project
```

## Architecture

```
GCS Bucket (Multi-region: STANDARD)
├── Standard (0-30 days, ~$0.020/GB)
├── Nearline (30-90 days, ~$0.010/GB)
├── Coldline (90-365 days, ~$0.004/GB)
└── Archive (365+ days, ~$0.0012/GB)

KMS Encryption
└── Customer-managed encryption keys

Service Account
└── Minimal IAM permissions (Object Admin only)

Iceberg Warehouse (optional)
└── Separate bucket with aggressive lifecycle
```

## Storage Classes

| Class | Latency | Cost/GB/Month | Min Storage | Use Case |
|-------|---------|---|---|---|
| STANDARD | Immediate | $0.020 | None | Recent docs, frequent access |
| NEARLINE | Seconds | $0.010 | 30 days | Medium-term, occasional access |
| COLDLINE | 2-4 hours | $0.004 | 90 days | Long-term, rare access |
| ARCHIVE | 12 hours | $0.0012 | 365 days | Compliance, archival |

## Lifecycle Policies

```
Day 0 ──→ Standard
  ↓ (30 days)
Day 30 ──→ Nearline
  ↓ (90 days total)
Day 90 ──→ Coldline
  ↓ (365 days total)
Day 365 ──→ Archive
  ↓ (retention policy)
Deleted/Retained
```

Savings: 94% for documents aged 365+ days

## Security Features

- **Encryption at Rest**: Customer-managed KMS keys
- **Versioning**: Full version history with retention
- **Least Privilege**: Service account with minimal permissions
- **Uniform Access**: Bucket-level uniform access control
- **Audit Logging**: GCS lifecycle and access logs

## Cost Analysis

### Monthly costs for 1TB metadata:

| Scenario | Cost/Month | Notes |
|----------|-----------|-------|
| All Standard | $20 | Worst case: no aging |
| Optimized mix | $2-5 | With lifecycle transitions |
| Archive only | $1.20 | After 365 days |
| **Savings** | **94%** | Using full lifecycle |

## References

- [GCS Documentation](https://cloud.google.com/storage/docs)
- [Storage Classes](https://cloud.google.com/storage/docs/storage-classes)
- [Lifecycle Policies](https://cloud.google.com/storage/docs/lifecycle)
- [Terraform GCP Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [KMS Documentation](https://cloud.google.com/kms/docs)
