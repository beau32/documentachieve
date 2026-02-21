# Storage Providers Integration Guide

Complete guide to configuring and using different storage backends with Document Archive.

## 📊 Storage Providers Overview

| Provider | Use Case | Setup Time | Cost | Best For |
|----------|----------|-----------|------|----------|
| **Local** | Development, Testing, Learning | 2 min | Free | Getting started, unit tests |
| **AWS S3** | Production, High availability | 10 min + IAM | Variable | Large scale, enterprise |
| **Azure Blob** | Enterprise, Compliance | 10 min + RBAC | Variable | Microsoft shops, compliance |
| **GCP Cloud Storage** | Multi-cloud, Big Data | 10 min + IAM | Variable | Analytics, BigQuery |

## 🎯 Quick Start by Use Case

### Developer (No Cloud Account)
```yaml
storage:
  provider: local
database:
  url: sqlite:///./document_archive.db
```
→ See [LOCAL_STORAGE.md](LOCAL_STORAGE.md)

### Local Learning with Iceberg
```yaml
storage:
  provider: local
database:
  url: "iceberg"
iceberg:
  warehouse_path: ./iceberg_warehouse
```
→ See [ICEBERG_SETUP.md](ICEBERG_SETUP.md)

### Production on AWS
```yaml
storage:
  provider: aws_s3
  aws_s3:
    bucket: my-archive-bucket
    region: us-east-1
database:
  url: mysql://user:pass@host/db
```
→ See [aws/README.md](aws/README.md)

### Production on Azure
```yaml
storage:
  provider: azure_blob
  azure_blob:
    container: archive-container
database:
  url: mysql://user:pass@host/db
```
→ See [azure/README.md](azure/README.md)

### Production on GCP
```yaml
storage:
  provider: gcp_storage
  gcp_storage:
    bucket: my-archive-bucket
database:
  url: mysql://user:pass@host/db
```
→ See [gcp/README.md](gcp/README.md)

## 🔄 Storage Provider Architecture

All storage providers implement the same `BaseStorageProvider` interface:

```python
class BaseStorageProvider:
    def upload(self, file: BinaryIO, document_id: str, metadata: dict) -> None
    def download(self, document_id: str) -> BinaryIO
    def delete(self, document_id: str) -> None
    def archive_to_tier(self, document_id: str, target_tier: StorageTier) -> None
    def restore_from_archive(self, document_id: str, restore_days: int) -> str
    def get_object_metadata(self, document_id: str) -> dict
```

This ensures **drop-in replacement** - switch providers with just a config change.

## 🏗️ Storage Implementations

### 1. Local Storage (`LocalStorageProvider`)
**File**: [app/storage/local.py](app/storage/local.py)

```
documents/
├── 2026/02/19/
│   ├── doc_id
│   └── doc_id.meta.json
├── 2026/02/20/
│   └── ...
```

**Features**:
- Filesystem-based (no cloud deps)
- Three-tier simulation: standard/archive/deep_archive
- Date-based organization (YYYY/MM/DD)
- JSON metadata files
- SHA256 checksums
- Perfect for development

**Config**:
```yaml
storage:
  provider: local
  local:
    storage_path: ./documents
    archive_path: ./documents_archive
    deep_archive_path: ./documents_deep_archive
```

### 2. AWS S3 (`AwsS3StorageProvider`)
**File**: [app/storage/aws_s3.py](app/storage/aws_s3.py)

```
s3://my-bucket/
├── standard/2026/02/19/doc_id
├── archive/2026/02/19/doc_id
└── deep-archive/2026/02/19/doc_id
```

**Features**:
- S3 standard, intelligent-tiering, glacier
- Automatic lifecycle policies
- Versioning support
- High availability and durability
- CloudFront CDN integration

**Config**:
```yaml
storage:
  provider: aws_s3
  aws_s3:
    bucket: archive-bucket
    region: us-east-1
    enable_versioning: true
```

**Cloud Resources** (CloudFormation):
- S3 Bucket with versioning
- S3 Glacier Vault for deep archive
- IAM roles and policies
- SNS notifications

**Setup**:
```bash
cd aws/
aws cloudformation create-stack \
  --stack-name archive-stack \
  --template-body file://s3_bucket.yaml
```

→ See [aws/README.md](aws/README.md) for details

### 3. Azure Blob Storage (`AzureBlobStorageProvider`)
**File**: [app/storage/azure_blob.py](app/storage/azure_blob.py)

```
archive-container/
├── standard/2026/02/19/doc_id
├── archive/2026/02/19/doc_id
└── deep-archive/2026/02/19/doc_id
```

**Features**:
- Hot, cool, cold, and archive tiers
- Automatic lifecycle management
- Managed Identity support (no secrets in config)
- Encryption at rest
- Compliance certifications

**Config**:
```yaml
storage:
  provider: azure_blob
  azure_blob:
    account_name: archiveaccount
    container: documents
    use_managed_identity: true
```

**Cloud Resources** (Bicep):
- Storage Account
- Blob containers
- Managed Identity
- Lifecycle policies
- RBAC roles

**Setup**:
```bash
cd azure/
az deployment group create \
  --resource-group mygroup \
  --template-file blob_storage.bicep
```

→ See [azure/README.md](azure/README.md) for details

### 4. GCP Cloud Storage (`GcpStorageProvider`)
**File**: [app/storage/gcp_storage.py](app/storage/gcp_storage.py)

```
archive-bucket/
├── standard/2026/02/19/doc_id
├── archive/2026/02/19/doc_id
└── deep-archive/2026/02/19/doc_id
```

**Features**:
- Nearline, coldline, archive storage classes
- Customer-managed encryption keys (CMEK)
- BigQuery integration
- Dataflow pipeline support
- Multiregional replication

**Config**:
```yaml
storage:
  provider: gcp_storage
  gcp_storage:
    bucket: archive-bucket
    project_id: my-project
    use_service_account: true
```

**Cloud Resources** (Terraform):
- GCS Bucket
- Lifecycle rules
- Service Account
- KMS encryption
- IAM policies

**Setup**:
```bash
cd gcp/
terraform init
terraform apply
```

→ See [gcp/README.md](gcp/README.md) for details

## 🌐 Database Backends

### SQLite (Development)
```yaml
database:
  url: sqlite:///./document_archive.db
```
- Single file
- No setup
- Perfect for development
- Limited concurrency

### MySQL/MariaDB (Production)
```yaml
database:
  url: mysql+pymysql://user:pass@host:3306/db
```
- Highly available
- Replication support
- Advanced querying
- Production-ready

### PostgreSQL (Production)
```yaml
database:
  url: postgresql://user:pass@host:5432/db
```
- ACID compliant
- Advanced features
- JSON support
- Great for complex queries

### Local Iceberg (Development)
```yaml
database:
  url: "iceberg"
iceberg:
  warehouse_path: ./iceberg_warehouse
  enable_local_mode: true
```
- Time travel queries
- Schema evolution
- Metadata versioning
- Perfect for learning

### Remote Iceberg (Production)
```yaml
database:
  url: "iceberg"
iceberg:
  catalog_uri: https://nessie.mycompany.com
  warehouse_path: s3://archive-bucket/iceberg
```
- Nessie catalog integration
- S3 data plane
- Multi-table transactions
- Git-like versioning

## 🔗 Configuration Patterns

### Pattern 1: Simple Local Development
```yaml
app:
  debug: true
storage:
  provider: local
  local:
    storage_path: ./documents
    archive_path: ./documents_archive
    deep_archive_path: ./documents_deep_archive
database:
  url: sqlite:///./document_archive.db
```

### Pattern 2: Local with Iceberg
```yaml
storage:
  provider: local
  local:
    storage_path: ./documents
    archive_path: ./documents_archive
    deep_archive_path: ./documents_deep_archive
database:
  url: "iceberg"
iceberg:
  warehouse_path: ./iceberg_warehouse
  enable_local_mode: true
```

### Pattern 3: AWS Production with Iceberg
```yaml
storage:
  provider: aws_s3
  aws_s3:
    bucket: archive-prod
    region: us-east-1
database:
  url: "iceberg"
iceberg:
  catalog_uri: https://nessie.prod.mycompany.com
  warehouse_path: s3://archive-prod/iceberg
```

### Pattern 4: Azure Production with MySQL
```yaml
storage:
  provider: azure_blob
  azure_blob:
    account_name: archiveprod
    container: documents
    use_managed_identity: true
database:
  url: mysql+pymysql://user:pass@myserver.mysql.database.azure.com/archive
```

### Pattern 5: Multi-Cloud (Dynamic Selection)
```yaml
storage:
  provider: ${STORAGE_PROVIDER}  # Set via env var
  aws_s3:
    bucket: ${AWS_BUCKET}
  azure_blob:
    account_name: ${AZURE_ACCOUNT}
  gcp_storage:
    bucket: ${GCP_BUCKET}
database:
  url: ${DATABASE_URL}
```

## 🚀 Switching Between Providers

All providers are **drop-in replacements** due to interface standardization:

```bash
# Development with Local Storage
export STORAGE_PROVIDER=local
export LOCAL_STORAGE_PATH=./documents
python -m app.main

# Switch to AWS (no code change!)
export STORAGE_PROVIDER=aws_s3
export AWS_S3_BUCKET=my-bucket
export AWS_REGION=us-east-1
python -m app.main

# Switch to Azure (no code change!)
export STORAGE_PROVIDER=azure_blob
export AZURE_ACCOUNT_NAME=account
export AZURE_CONTAINER=container
python -m app.main
```

## 📊 Metadata Storage Comparison

| Feature | SQLite | MySQL | PostgreSQL | Iceberg Local | Iceberg Nessie |
|---------|--------|-------|-----------|---------------|----------------|
| Setup | 1 min | 30 min | 30 min | 5 min | 60 min |
| ACID | ✓ | ✓ | ✓ | ✓ | ✓ |
| Time Travel | ✗ | ✗ | ✗ | ✓ | ✓ |
| Schema Evolution | ✗ | Limited | ✓ | ✓ | ✓ |
| Concurrency | Limited | ✓ | ✓ | ✓ | ✓ |
| Production Ready | ✗ | ✓ | ✓ | ✗ | ✓ |

## 🔒 Security Considerations

### Local Storage (Development)
```yaml
storage:
  provider: local
  local:
    storage_path: ./documents  # Permissions: 700
```
- ✓ No network exposure
- ✗ Not persistent (docker containers)
- ✓ Easy to backup

### AWS (Production)
```yaml
storage:
  provider: aws_s3
  aws_s3:
    bucket: archive-prod
    kms_key_id: arn:aws:kms:...
```
- ✓ Encryption at rest (KMS)
- ✓ Encryption in transit (TLS)
- ✓ IAM role-based access
- ✓ Versioning + MFA delete

### Azure (Production)
```yaml
storage:
  provider: azure_blob
  azure_blob:
    use_managed_identity: true
    encryption: true
```
- ✓ Managed Identity (no secrets)
- ✓ Encryption at rest (SME)
- ✓ Private endpoints
- ✓ RBAC policies

### GCP (Production)
```yaml
storage:
  provider: gcp_storage
  gcp_storage:
    use_service_account: true
    cmek_key_name: projects/.../keys/...
```
- ✓ Service account authentication
- ✓ CMEK encryption
- ✓ Binary Authorization
- ✓ VPC Service Controls

## 📈 Performance Characteristics

### Upload Performance (1GB file)
| Provider | Time | Cost per GB |
|----------|------|------------|
| Local | 1 sec | Free |
| AWS S3 | 2-5 sec | $0.025 |
| Azure Blob | 2-5 sec | $0.018 |
| GCP GCS | 2-5 sec | $0.020 |

### Retrieval Performance (1GB file)
| Provider | Time | Cost per GB |
|----------|------|------------|
| Local | 1 sec | Free |
| AWS S3 Standard | 100ms | $0.09 |
| AWS Glacier | 1-12 hours | $0.004 |
| Azure Hot | 100ms | $0.018 |
| Azure Cold | 100ms | $0.01 |

## 🎓 Learning Path

1. **Start Local** (5 min)
   - Run [local-setup.sh](local-setup.sh) or [local-setup.bat](local-setup.bat)
   - See [LOCAL_STORAGE.md](LOCAL_STORAGE.md)

2. **Learn Iceberg** (30 min)
   - Add iceberg to local config
   - Study [ICEBERG_SETUP.md](ICEBERG_SETUP.md)
   - Run time travel queries

3. **Deploy to Cloud** (60 min)
   - Choose AWS, Azure, or GCP
   - Run provisioning script
   - Switch provider in config
   - Deploy → See [CLOUD_ORGANIZATION.md](CLOUD_ORGANIZATION.md)

4. **Production Setup** (2 hours)
   - Set up managed database
   - Configure monitoring and alerts
   - Implement backup strategy
   - Load test with production data

## 📚 Further Reading

- [LOCAL_STORAGE.md](LOCAL_STORAGE.md) - Filesystem-based development
- [ICEBERG_SETUP.md](ICEBERG_SETUP.md) - Iceberg metadata versioning
- [aws/README.md](aws/README.md) - AWS CloudFormation deployment
- [azure/README.md](azure/README.md) - Azure Bicep deployment
- [gcp/README.md](gcp/README.md) - GCP Terraform deployment
- [CLOUD_PROVIDERS.md](CLOUD_PROVIDERS.md) - Multi-cloud comparison
- [cloud-deploy.sh](cloud-deploy.sh) - Unified deployment

## 🆘 Troubleshooting

### Storage Provider Not Found
```
ERROR: Storage provider 'xyz' not registered
```
**Solution**: Check config provider name matches enum in [app/config.py](app/config.py)

### Connection Refused
```
ERROR: Cannot connect to storage backend
```
**Solution**: Verify credentials and network connectivity

### Out of Storage
- **Local**: Check disk space: `df -h documents*`
- **AWS**: Enable lifecycle policies to move old docs
- **Azure**: Enable cool/archive tiers

### Permission Denied
- **Local**: `chmod 755 documents*`
- **AWS**: Check IAM role has S3 permissions
- **Azure**: Check Managed Identity has RBAC role

---

**Questions?** See the provider-specific README files or check the configuration examples in [config.yaml.example](config.yaml.example).
