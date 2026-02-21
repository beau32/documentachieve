# AWS S3 Iceberg Tables for Document Metadata

This document explains how to use AWS S3-based Iceberg tables for storing document metadata instead of SQLite or MySQL.

## What is Iceberg?

Apache Iceberg is an open table format that provides:
- **ACID Transactions**: Ensures data consistency
- **Schema Evolution**: Modify schemas without rewriting data
- **Time Travel**: Query data at any point in time
- **Partitioning**: Efficient data organization and pruning
- **Hidden Partitioning**: Partition columns are maintained automatically
- **Cost-effective**: Works directly with S3 for scalable metadata storage

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Document Archive Application                        │
├─────────────────────────────────────────────────────┤
│  Metadata Storage Options:                           │
│  ├─ SQLite (default, single-machine)                │
│  ├─ MySQL (relational, multi-machine)               │
│  └─ Iceberg on S3 (ACID, scalable, time-travel)    │
└─────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
    document_archive.db          S3 Iceberg Warehouse
                                        │
                                        ├─ Apache Iceberg REST Catalog
                                        ├─ Parquet Files
                                        └─ Metadata Files
```

## Setup

### 1. Install Dependencies

```bash
pip install pyiceberg[s3] pyarrow nessie-client
```

### 2. Set Up Iceberg Catalog

You need a REST Catalog to manage Iceberg tables. Options:

#### Option A: Using Nessie (Recommended)

Deploy Nessie as a Docker container:

```bash
docker run -d \
  -p 19120:19120 \
  ghcr.io/projectnessie/nessie:latest
```

#### Option B: Using Polaris

Use Polaris for a managed Iceberg catalog (enterprise option).

#### Option C: Using AWS Glue

AWS Glue can serve as an Iceberg catalog (simpler for AWS-only deployments).

### 3. Configure Application

Update `config.yaml`:

```yaml
database:
  url: "iceberg"

iceberg:
  catalog_uri: "http://localhost:8181"  # Nessie/Polaris endpoint
  s3_endpoint: "https://s3.us-east-1.amazonaws.com"
  warehouse_path: "s3://document-archive-iceberg-warehouse"
```

Or set environment variables:

```bash
export DATABASE_URL=iceberg
export ICEBERG_CATALOG_URI=http://localhost:8181
export ICEBERG_S3_ENDPOINT=https://s3.us-east-1.amazonaws.com
export ICEBERG_WAREHOUSE_PATH=s3://document-archive-iceberg-warehouse
```

### 4. Create S3 Bucket for Warehouse

```bash
aws s3 mb s3://document-archive-iceberg-warehouse --region us-east-1

# Enable versioning for audit trail
aws s3api put-bucket-versioning \
  --bucket document-archive-iceberg-warehouse \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket document-archive-iceberg-warehouse \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

### 5. Initialize Iceberg Table

```bash
python -c "from app.iceberg_database import get_iceberg_db; get_iceberg_db()"
```

This creates the `document_metadata` table partitioned by `created_at`.

## Docker Compose Setup

Complete Docker Compose setup with Nessie and your app:

```yaml
version: '3.8'

services:
  # Nessie Iceberg Catalog
  nessie:
    image: ghcr.io/projectnessie/nessie:latest
    ports:
      - "19120:19120"
    environment:
      NESSIE_CATALOG_DEFAULT_WAREHOUSE: s3://document-archive-iceberg-warehouse
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
      AWS_DEFAULT_REGION: us-east-1

  # LocalStack for local S3 testing (optional)
  localstack:
    image: localstack/localstack:latest
    ports:
      - "4566:4566"
    environment:
      SERVICES: s3
      AWS_ACCESS_KEY_ID: test
      AWS_SECRET_ACCESS_KEY: test
    volumes:
      - "${TMPDIR}localstack:/tmp/localstack"

  # Document Archive Application
  app:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - nessie
    environment:
      DATABASE_URL: iceberg
      ICEBERG_CATALOG_URI: http://nessie:19120
      ICEBERG_S3_ENDPOINT: http://localstack:4566
      ICEBERG_WAREHOUSE_PATH: s3://document-archive-iceberg-warehouse
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
      AWS_REGION: us-east-1
```

## Usage Examples

### Querying Metadata

```python
from app.iceberg_database import get_iceberg_db

db = get_iceberg_db()

# Get all documents
all_docs = db.list_metadata()

# Filter by storage tier
archive_docs = db.list_metadata(storage_tier="archive")

# Time range query
docs = db.list_metadata(
    start_date=1707000000,  # Unix timestamp
    end_date=1708000000
)

# Get statistics
stats = db.get_statistics()
print(f"Total documents: {stats['total_documents']}")
print(f"Total size: {stats['total_size_bytes']} bytes")
```

### Time Travel

Query data as it existed at a specific point in time:

```python
# Get document metadata from 1 hour ago
past_metadata = db.get_time_travel_snapshot(
    document_id="abc123",
    timestamp=int((datetime.now() - timedelta(hours=1)).timestamp() * 1000)
)
```

### Updating Metadata

```python
# Update restore status
db.update_metadata("abc123", {
    "restore_status": "restored",
    "restore_expiry": int((datetime.now() + timedelta(days=7)).timestamp() * 1000)
})
```

## Performance Characteristics

| Operation | SQLite | MySQL | Iceberg |
|-----------|--------|-------|---------|
| Insert | Fast (local) | Medium | Medium (S3) |
| Query (small) | Very Fast | Fast | Fast |
| Query (large/analytical) | Slow | Medium | Fast |
| Time Travel | Not supported | Not supported | Supported |
| Schema Evolution | Limited | Limited | Full support |
| Scalability | Single machine | Multi-machine | Unlimited (S3) |
| Cost | Low | Medium | Very Low (S3 storage) |

## Deployment on AWS

### Using AWS Glue Catalog

```yaml
iceberg:
  catalog_uri: "glue"  # Use AWS Glue as catalog
  warehouse_path: "s3://document-archive-iceberg-warehouse"
```

IAM permissions required:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::document-archive-iceberg-warehouse",
        "arn:aws:s3:::document-archive-iceberg-warehouse/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "glue:GetDatabase",
        "glue:GetTable",
        "glue:GetTables",
        "glue:CreateTable",
        "glue:UpdateTable",
        "glue:DeleteTable"
      ],
      "Resource": "*"
    }
  ]
}
```

## Migration from SQLite/MySQL to Iceberg

```bash
# Export from SQLite/MySQL
python scripts/export_metadata.py --from sqlite --to iceberg

# Verify
python -c "
from app.iceberg_database import get_iceberg_db
db = get_iceberg_db()
stats = db.get_statistics()
print(f'Migrated {stats[\"total_documents\"]} documents')
"
```

## Monitoring

### Check Iceberg Table Metadata

```bash
# Using Nessie CLI
nessie --uri http://localhost:19120 show-content

# Using Python
from pyiceberg.catalog import load_catalog

catalog = load_catalog("nessie")
table = catalog.load_table("document_archive.document_metadata")
print(f"Snapshots: {len(table.snapshots())}")
print(f"Latest snapshot ID: {table.current_snapshot().snapshot_id}")
```

### Query Statistics

```python
db = get_iceberg_db()
stats = db.get_statistics()

print(f"Documents by provider: {stats['by_provider']}")
print(f"Documents by tier: {stats['by_tier']}")
print(f"Documents by restore status: {stats['by_restore_status']}")
```

## Troubleshooting

### Connection Issues

```bash
# Test Nessie connectivity
curl http://localhost:19120/v1/health

# Test S3 access
aws s3 ls s3://document-archive-iceberg-warehouse/
```

### Performance Tuning

1. **Partition pruning**: Queries are automatically pruned by date
2. **Manifest caching**: Enable manifest cache in Iceberg config
3. **Parallel scans**: Leverage S3's parallel reads for large queries

### Costs

- S3 storage: ~$0.023/GB/month
- S3 requests: ~$0.0004/1000 PUT, ~$0.0002/1000 GET
- Data transfer: Varies by region

For typical usage (10GB metadata): ~$0.50/month

## Comparison with Alternatives

| Feature | Iceberg | Delta Lake | Apache Hudi |
|---------|---------|-----------|-----------|
| ACID Transactions | ✓ | ✓ | ✓ |
| Time Travel | ✓ | ✓ | Limited |
| Schema Evolution | ✓ | ✓ | Limited |
| S3 Native | ✓ | ✓ | Requires HBase |
| Community | Apache | Databricks | Apache |
| Maturity | Mature | Mature | Growing |

## References

- [Apache Iceberg Documentation](https://iceberg.apache.org/)
- [Nessie Documentation](https://projectnessie.org/)
- [PyIceberg Documentation](https://py.iceberg.apache.org/)
