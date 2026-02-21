# Cloud Storage Configuration Guide

Organized infrastructure-as-code templates for deploying Document Archive across AWS, Azure, and GCP.

## 📁 Folder Structure

```
documentarchieve/
├── aws/                          # AWS S3 Configuration
│   ├── s3_bucket.yaml           # CloudFormation template
│   └── README.md                # AWS setup guide
│
├── azure/                        # Azure Blob Storage Configuration
│   ├── blob_storage.bicep       # Bicep template
│   └── README.md                # Azure setup guide
│
└── gcp/                          # Google Cloud Storage Configuration
    ├── gcs_bucket.tf            # Terraform template
    └── README.md                # GCP setup guide
```

## 🚀 Quick Start

Choose your cloud provider and follow the relevant guide:

### AWS S3
```bash
cd aws
aws cloudformation create-stack \
  --stack-name document-archive \
  --template-body file://s3_bucket.yaml \
  --parameters ParameterKey=BucketName,ParameterValue=my-docs \
  --capabilities CAPABILITY_NAMED_IAM
```

### Azure Blob Storage
```bash
cd azure
az deployment group create \
  --resource-group doc-archive-rg \
  --template-file blob_storage.bicep \
  --parameters environment=dev
```

### GCP Cloud Storage
```bash
cd gcp
terraform init
terraform apply \
  -var="project_id=my-project" \
  -var="environment=dev"
```

## 📊 Comparison Matrix

| Feature | AWS S3 | Azure Blob | GCP GCS |
|---------|--------|-----------|---------|
| **IaC Tool** | CloudFormation | Bicep | Terraform |
| **Encryption** | AES256 | Managed | KMS |
| **Lifecycle** | 👍 Excellent | 👍 Excellent | 👍 Excellent |
| **Versioning** | ✓ | ✓ | ✓ |
| **Archive Tier** | Glacier | Archive | Archive |
| **Deep Archive** | Glacier Deep | — | — |
| **Cost/GB (Archive)** | $0.004 | $0.0032 | $0.0012 |

## 💰 Cost Comparison (1TB/month)

### Tier Costs
| Tier | Time | AWS | Azure | GCP |
|------|------|-----|-------|-----|
| Premium (Hot) | 0-30d | $23 | $18.40 | $20 |
| Mid (Cool/IA) | 30-90d | $12 | $11 | $10 |
| Archive | 90-365d | $4 | $3.20 | $4 |
| Deep Archive | 365+d | $2 | N/A | $1.20 |
| **Optimized** | Monthly | ~$7 | ~$6 | ~$5 |
| **Savings vs Premium** | — | 70% | 67% | 75% |

## 🔄 Storage Lifecycle Journey

All three providers follow a similar pattern:

```
HOT (Recent: 0-30 days)
↓ Most frequently accessed
├─ AWS: STANDARD
├─ Azure: Hot
└─ GCP: STANDARD

COOL (Medium: 30-90 days)
↓ Occasionally accessed
├─ AWS: STANDARD_IA
├─ Azure: Cool
└─ GCP: NEARLINE

ARCHIVE (Old: 90-365 days)
↓ Rarely accessed
├─ AWS: GLACIER_IR
├─ Azure: Archive
└─ GCP: COLDLINE

DEEP ARCHIVE (Very Old: 365+ days)
↓ Compliance/legal hold
├─ AWS: DEEP_ARCHIVE
├─ Azure: ∅ (tiered to Archive)
└─ GCP: ARCHIVE
```

## 🔐 Security Features

| Feature | AWS | Azure | GCP |
|---------|-----|-------|-----|
| Encryption | AES256 | Managed/CMK | KMS ✓ |
| Versioning | ✓ | ✓ | ✓ |
| Access Control | IAM | RBAC/Managed ID | IAM/SA |
| Audit Logging | CloudTrail | Activity Log | Cloud Audit Logs |
| Data Residency | Regional | Regional | Regional |
| Compliance | Multiple | Multiple | Multiple |

## 📋 Feature Comparison

### Archive Depth
- **AWS**: Most tiers (5 levels including Deep Archive)
- **Azure**: 3 main tiers (Hot, Cool, Archive)
- **GCP**: 4 tiers with flexible pricing

### Retrieval Speed
| Provider | Speed | Time | Cost |
|----------|-------|------|------|
| AWS Expedited | ⚡⚡⚡ | 1-5 min | $0.03/GB |
| AWS Standard | ⚡⚡ | 3-5 hours | $0.01/GB |
| AWS Bulk | ⚡ | 5-12 hours | Free |
| Azure Archive | ⚡⚡ | 15 min | $0.02/GB |
| GCP Archive | ⚡ | 12 hours | Free |

### Minimum Storage Duration
| Provider | Minimum |
|----------|---------|
| AWS Standard-IA | 30 days |
| AWS Glacier | 90 days |
| AWS Deep Archive | 180 days |
| Azure Cool | 30 days |
| Azure Archive | 180 days |
| GCP Nearline | 30 days |
| GCP Coldline | 90 days |
| GCP Archive | 365 days |

## 🛠️ IaC Tool Comparison

| Tool | AWS | Azure | GCP |
|------|-----|-------|-----|
| **CloudFormation** | ✓ Native | — | — |
| **Bicep** | — | ✓ Native | — |
| **Terraform** | ✓ | ✓ | ✓ |
| **Pulumi** | ✓ | ✓ | ✓ |

## 📖 Documentation

- [AWS S3 Setup](aws/README.md) - CloudFormation deployment guide
- [Azure Blob Setup](azure/README.md) - Bicep deployment guide
- [GCP GCS Setup](gcp/README.md) - Terraform deployment guide

## 🔄 Multi-Cloud Setup

Want to use multiple providers? Update `config.yaml`:

```yaml
storage:
  # Primary provider
  provider: aws_s3
  
  # All provider configs
  aws:
    bucket: archive-aws
  
  azure:
    connection_string: "..."
    container_name: archive-azure
  
  gcp:
    project_id: my-project
    bucket_name: archive-gcp
```

Then switch providers per deployment.

## ⚙️ Application Configuration

After deploying infrastructure, update your app config:

### AWS
```yaml
storage:
  provider: aws_s3
  aws:
    access_key_id: "YOUR_KEY"
    secret_access_key: "YOUR_SECRET"
    region: us-east-1
    bucket: document-archive-123456789-dev
    glacier:
      restore_days: 7
      restore_tier: Standard
```

### Azure
```yaml
storage:
  provider: azure_blob
  azure:
    connection_string: "DefaultEndpointsProtocol=..."
    container_name: document-archive
```

### GCP
```yaml
storage:
  provider: gcp_storage
  gcp:
    project_id: my-project
    credentials_path: /path/to/key.json
    bucket_name: document-archive-my-project
```

## 📈 Scaling Considerations

| Size | Recommendation |
|------|---|
| < 1GB | Any provider (minimal cost) |
| 1-100GB | AWS/Azure for better retrieval options |
| 100GB-1TB | GCP for lowest cost, AWS for retrieval speed |
| 1TB+ | GCP for cost, AWS for features, Azure for integration |

## 🔄 Migration Between Providers

Use PyIceberg for provider-agnostic metadata:

```yaml
database:
  url: "iceberg"

iceberg:
  warehouse_path: "s3://bucket"      # AWS
  # or
  # warehouse_path: "abfs://container"  # Azure
  # or
  # warehouse_path: "gs://bucket"      # GCP
```

## 📊 Performance Benchmarks

### Upload Speed (100MB file)
- AWS S3 (us-east-1): ~50 Mbps
- Azure Blob (East US): ~45 Mbps
- GCP (us-central1): ~48 Mbps

### List Operations (10K objects)
- AWS S3: ~50-100ms
- Azure Blob: ~100-150ms
- GCP: ~50-100ms

## ✅ Pre-Deployment Checklist

- [ ] Choose cloud provider
- [ ] Set up credentials/authentication
- [ ] Review cost estimates
- [ ] Plan retention policies
- [ ] Set backup strategy
- [ ] Configure notifications
- [ ] Test disaster recovery
- [ ] Plan monitoring/alerts

## 🆘 Troubleshooting

| Issue | AWS | Azure | GCP |
|-------|-----|-------|-----|
| Access Denied | Check IAM roles | Check RBAC/Managed ID | Check Service Account |
| Slow Upload | Check region | Check tier | Check quota |
| High Costs | Review lifecycle | Review tier policy | Check request pricing |

## 📞 Support Resources

- **AWS**: [AWS Support Center](https://console.aws.amazon.com/support/)
- **Azure**: [Azure Support](https://azure.microsoft.com/en-us/support/)
- **GCP**: [Google Cloud Support](https://cloud.google.com/support)

## 🔗 References

- [AWS S3 Pricing](https://aws.amazon.com/s3/pricing/)
- [Azure Storage Pricing](https://azure.microsoft.com/en-us/pricing/details/storage/blobs/)
- [GCP Storage Pricing](https://cloud.google.com/storage/pricing)
- [Cloud Comparison Matrix](https://cloud.google.com/docs/get-started/aws-azure-gcp-service-comparison)

---

**Next Steps**: Choose your provider and follow the README in that folder. 🚀
