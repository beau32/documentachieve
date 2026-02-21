#!/usr/bin/env bash
# Quick start guide for AWS S3 Iceberg tables

set -e

echo "=== Document Archive with Iceberg Quick Start ==="
echo ""

# 1. Update dependencies
echo "1. Installing dependencies..."
pip install -q pyiceberg[s3] pyarrow nessie-client
echo "✓ Dependencies installed"
echo ""

# 2. Start Nessie catalog locally
echo "2. Starting Nessie catalog..."
docker-compose -f docker-compose.iceberg.yml up -d nessie
echo "✓ Nessie started at http://localhost:19120"
sleep 5

# Wait for Nessie to be ready
echo "   Waiting for Nessie to be ready..."
for i in {1..30}; do
  if curl -s http://localhost:19120/v1/health > /dev/null 2>&1; then
    echo "✓ Nessie is ready"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "✗ Nessie failed to start"
    exit 1
  fi
  sleep 1
done
echo ""

# 3. Create S3 bucket
echo "3. Creating S3 buckets..."

# For AWS
if command -v aws &> /dev/null; then
  ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "123456789")
  WAREHOUSE_BUCKET="document-archive-iceberg-warehouse-${ACCOUNT_ID}"
  
  # Check if bucket exists
  if ! aws s3 ls "s3://${WAREHOUSE_BUCKET}" 2>/dev/null; then
    echo "   Creating bucket: ${WAREHOUSE_BUCKET}"
    aws s3 mb "s3://${WAREHOUSE_BUCKET}" --region us-east-1
    echo "✓ S3 bucket created"
  else
    echo "✓ S3 bucket already exists"
  fi
else
  echo "⚠ AWS CLI not installed, skipping S3 bucket creation"
  echo "  Manually create: s3://document-archive-iceberg-warehouse"
fi
echo ""

# 4. Create config.yaml
echo "4. Creating config.yaml for Iceberg..."
cat > config.yaml << 'EOF'
app:
  name: Cloud Document Archive
  debug: true

storage:
  provider: aws_s3
  aws:
    access_key_id: ""
    secret_access_key: ""
    region: us-east-1
    bucket: document-archive
    glacier:
      restore_days: 7
      restore_tier: Standard

database:
  url: "iceberg"

iceberg:
  catalog_uri: "http://localhost:19120"
  s3_endpoint: "https://s3.us-east-1.amazonaws.com"
  warehouse_path: "s3://document-archive-iceberg-warehouse"

kafka:
  enabled: false
  bootstrap_servers: localhost:9092

lifecycle:
  enabled: false
  archive_after_days: 90
  deep_archive_after_days: 365
  check_interval_hours: 24
EOF
echo "✓ config.yaml created"
echo ""

# 5. Initialize Iceberg table
echo "5. Initializing Iceberg table..."
python3 << 'PYTHON'
from app.iceberg_database import get_iceberg_db
try:
    db = get_iceberg_db()
    print("✓ Iceberg table initialized successfully")
except Exception as e:
    print(f"✗ Failed to initialize Iceberg table: {e}")
    exit(1)
PYTHON
echo ""

# 6. Test connection
echo "6. Testing Iceberg connection..."
python3 << 'PYTHON'
from app.iceberg_database import get_iceberg_db
try:
    db = get_iceberg_db()
    stats = db.get_statistics()
    print(f"✓ Connected to Iceberg catalog")
    print(f"  Total documents: {stats['total_documents']}")
except Exception as e:
    print(f"✗ Failed: {e}")
    exit(1)
PYTHON
echo ""

# 7. Next steps
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo ""
echo "1. Start the application:"
echo "   python -m app.main"
echo ""
echo "2. Access the API:"
echo "   curl http://localhost:8000/docs"
echo ""
echo "3. Query Iceberg table:"
echo "   python << 'PYTHON'"
echo "   from app.iceberg_database import get_iceberg_db"
echo "   db = get_iceberg_db()"
echo "   stats = db.get_statistics()"
echo "   print(f'Documents: {stats[\"total_documents\"]}')"
echo "   PYTHON"
echo ""
echo "4. View Nessie catalog:"
echo "   Open http://localhost:19120"
echo ""
echo "5. Stop services:"
echo "   docker-compose -f docker-compose.iceberg.yml down"
echo ""
