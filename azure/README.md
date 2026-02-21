# Azure Configuration for Document Archive

Azure storage provisioning for document archiving with Blob Storage and optional Iceberg support.

## Files

- **blob_storage.bicep** - Bicep template for Azure infrastructure
  - Azure Storage Account (GRS)
  - Blob Storage containers
  - Lifecycle management policies (Hot → Cool → Archive)
  - Managed Identity for app access
  - Optional Iceberg warehouse container
  - Access policies and versioning

## Quick Start

```bash
# Create resource group
az group create --name doc-archive-rg --location eastus

# Deploy Bicep template
az deployment group create \
  --resource-group doc-archive-rg \
  --template-file azure/blob_storage.bicep \
  --parameters \
    environment=dev \
    createIcebergWarehouse=true

# Get outputs
az deployment group show \
  --resource-group doc-archive-rg \
  --name blob_storage \
  --query properties.outputs
```

## Configuration

Update `config.yaml`:

```yaml
storage:
  provider: azure_blob
  azure:
    connection_string: "DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net"
    container_name: document-archive
```

Or use Managed Identity (recommended):

```yaml
storage:
  provider: azure_blob
  azure:
    storage_account: docarchive...
    container_name: document-archive
    use_managed_identity: true
```

## Architecture

```
Storage Account (GRS)
├── Hot tier (0-30 days)
├── Cool tier (30-365 days)
└── Archive tier (365+ days)

Iceberg Warehouse (optional)
└── Blob container with lifecycle management

Managed Identity
└── Secure app access without credentials
```

## Lifecycle Policies

- Day 0-30: Hot tier (~$0.0184/GB)
- Day 30-365: Cool tier (~$0.011/GB)
- Day 365+: Archive tier (~$0.0032/GB)

Savings: 82% for aged documents

## Tiers Comparison

| Tier | Access Latency | Cost/GB | Use Case |
|------|---|---|---|
| Hot | Immediate | $0.0184 | Recent docs |
| Cool | Minutes | $0.011 | 30+ days |
| Archive | Hours-15 min | $0.0032 | Long-term |

## References

- [Azure Blob Storage Docs](https://docs.microsoft.com/en-us/azure/storage/blobs/)
- [Lifecycle Management](https://docs.microsoft.com/en-us/azure/storage/blobs/storage-lifecycle-management-concepts)
- [Bicep Documentation](https://docs.microsoft.com/en-us/azure/azure-resource-manager/bicep/)
- [Managed Identity](https://docs.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/)
