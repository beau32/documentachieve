# Cloud Document Archive

A multi-cloud document archiving service supporting AWS S3, Azure Blob Storage, and Google Cloud Storage. Archive documents with metadata and tags, retrieve them by unique identifiers, and generate analytics reports.

## Features

- **Archive**: Upload documents in base64 format with custom tags and metadata
- **Retrieve**: Download documents using unique hashed identifiers  
- **Vector Search**: Semantic search to find similar documents using AI embeddings
- **PII Detection & Anonymization**: Detect and redact personally identifiable information for compliance
- **Report**: Generate metrics and analytics for archived documents
- **Multi-Cloud**: Support for AWS S3, Azure Blob Storage, and GCP Storage
- **Deep Archive**: Move documents to cost-effective cold storage (AWS Glacier, Azure Archive, GCP Archive)
- **Restore**: Initiate and track restoration of documents from deep archive
- **Kafka Events**: Publish events for archive, delete, and restore operations
- **Docker**: Pre-configured Docker and Docker Compose setup with Kafka integration
- **YAML Configuration**: Support for declarative configuration via YAML files

## Installation

### Option 1: Local Installation

1. Clone the repository:
```bash
cd clouddocumentachieve
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
.\venv\Scripts\activate  # On Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Option 2: Docker Installation

See [Running with Docker](#running-with-docker) section below for container-based setup.
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your cloud provider credentials
```

## Configuration

Set the `STORAGE_PROVIDER` environment variable to select your cloud provider:
- `aws_s3` - Amazon S3
- `azure_blob` - Azure Blob Storage
- `gcp_storage` - Google Cloud Storage

### AWS S3 Configuration
```env
STORAGE_PROVIDER=aws_s3
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
AWS_S3_BUCKET=your-bucket-name
```

### Azure Blob Storage Configuration
```env
STORAGE_PROVIDER=azure_blob
AZURE_CONNECTION_STRING=your-connection-string
AZURE_CONTAINER_NAME=your-container-name
```

### GCP Storage Configuration
```env
STORAGE_PROVIDER=gcp_storage
GCP_PROJECT_ID=your-project-id
GCP_CREDENTIALS_PATH=/path/to/credentials.json
GCP_BUCKET_NAME=your-bucket-name
```

### Kafka Configuration (Optional)
```env
KAFKA_ENABLED=true
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_RESTORE_READY=document-restore-ready
KAFKA_TOPIC_ARCHIVED=document-archived
```

### Lifecycle/Automatic Archival Configuration
```env
LIFECYCLE_ENABLED=true
LIFECYCLE_ARCHIVE_AFTER_DAYS=90        # Move to archive after 90 days
LIFECYCLE_DEEP_ARCHIVE_AFTER_DAYS=365  # Move to deep archive after 1 year
LIFECYCLE_CHECK_INTERVAL_HOURS=24      # Check every 24 hours
```

### YAML Configuration (Optional)

Alternatively, use a `config.yaml` file for cleaner, hierarchical configuration:

1. Copy the example:
```bash
cp config.yaml.example config.yaml
```

2. Edit `config.yaml` with your settings:
```yaml
app:
  name: Cloud Document Archive
  debug: false

storage:
  provider: aws_s3
  aws:
    access_key_id: "your-key"
    secret_access_key: "your-secret"
    region: us-east-1
    bucket: document-archive
    glacier:
      restore_days: 7
      restore_tier: Standard

kafka:
  enabled: true
  bootstrap_servers: localhost:9092

lifecycle:
  enabled: true
  archive_after_days: 90
  deep_archive_after_days: 365
```

3. Load the YAML configuration:
```bash
export CONFIG_YAML_PATH=config.yaml
uvicorn app.main:app --reload
```

**Note:** Environment variables take precedence over YAML values.

## Running the Application

Start the server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Running with Docker

### Prerequisites
- Docker and Docker Compose installed

### Quick Start
Start all services (API, Kafka, Zookeeper) with Docker Compose:

```bash
docker-compose up -d
```

This will:
- Start Zookeeper for Kafka
- Start Kafka message broker (port 9092)
- Start the FastAPI application (port 8000)
- Enable Kafka event publishing
- Enable automatic lifecycle archival

View logs:
```bash
docker-compose logs -f api
docker-compose logs -f kafka
```

Stop all services:
```bash
docker-compose down
```

### Building Docker Image Manually
Build the Docker image:
```bash
docker build -t clouddocumentarchive:latest .
```

Run the container:
```bash
docker run -p 8000:8000 \
  -e STORAGE_PROVIDER=aws_s3 \
  -e AWS_ACCESS_KEY_ID=your-key \
  -e AWS_SECRET_ACCESS_KEY=your-secret \
  -e AWS_S3_BUCKET=your-bucket \
  clouddocumentarchive:latest
```

### Configuration for Docker
Set environment variables in `docker-compose.yml` or pass them to `docker run`:
- `STORAGE_PROVIDER`: aws_s3, azure_blob, or gcp_storage
- `AWS_*`: AWS S3 credentials and configuration
- `AZURE_*`: Azure Blob Storage credentials
- `GCP_*`: GCP Storage credentials
- `KAFKA_ENABLED`: true to enable Kafka event publishing
- `LIFECYCLE_ENABLED`: true to enable automatic archival

## Testing with Postman

A complete Postman collection is included for testing all API endpoints.

### Import the Collection
1. Download or clone the repository
2. In Postman, click **Import**
3. Select `Cloud_Document_Archive.postman_collection.json`
4. Click **Import**

### Configuration
Update the Postman variables:
- `base_url`: Change to your API endpoint (default: http://localhost:8000)
- `document_id`: Will be populated after archiving a document

For detailed instructions, see [POSTMAN.md](./POSTMAN.md)

### Quick Test Workflow
1. **Archive Document** → Copy the `document_id` from response
2. **Retrieve Document** → Paste the document_id
3. **Move to Deep Archive** → Use the document_id
4. **Check Status** → Verify archive status

## Vector Search & Embeddings

The application supports semantic search using vector embeddings to find similar documents based on content relevance rather than exact text matching.

### How It Works

1. **Embedding Generation**: When a document is archived, its filename, tags, and metadata are combined and converted to a dense vector representation using the `all-MiniLM-L6-v2` sentence transformer model.

2. **Semantic Indexing**: Embeddings are stored in the database alongside document metadata, enabling fast similarity search.

3. **Query Processing**: Search queries are converted to embeddings using the same model, ensuring comparable vector space.

4. **Similarity Matching**: Cosine similarity is calculated between query and document embeddings, ranking results by relevance.

5. **Filtering**: Results are filtered by configurable similarity threshold and limited to top-k matches.

### Use Cases

- **Document Discovery**: Find related reports, articles, or documents without exact keywords
- **Content-Based Retrieval**: Locate documents by meaning rather than specific terms
- **Duplicate Detection**: Identify similar or duplicate documents in the archive
- **Cross-Language Search**: With multilingual models, search across documents in different languages

### Configuration

The embedding model can be customized (default: `all-MiniLM-L6-v2`):

```python
# Lightweight & fast (recommended for CPU)
all-MiniLM-L6-v2   # 22M parameters, fastest
all-MiniLM-L12-v2  # 33M parameters, good balance

# More accurate (requires GPU for optimal performance)
all-mpnet-base-v2  # 109M parameters, most accurate
```

### Performance Notes

- First query may take longer (model load time ~2-3 seconds)
- Subsequent queries are fast (typically <500ms for 1000 documents)
- Small model recommended for CPU-only environments
- Larger model beneficial for high accuracy requirements

## Document Anonymization & PII Detection

The application includes built-in PII (Personally Identifiable Information) detection and anonymization capabilities to help comply with data privacy regulations like GDPR and CCPA.

### Supported PII Types

The system can detect and anonymize the following types of PII:

- **Email Addresses**: `email@example.com`
- **Phone Numbers**: `(555) 123-4567`, `+1-555-123-4567`
- **Social Security Numbers**: `123-45-6789`
- **Credit Card Numbers**: `4532-1234-5678-9101`
- **IP Addresses**: `192.168.1.1`, `2001:0db8:85a3::8a2e:0370:7334`
- **Names**: Capitalized name patterns (heuristic-based)
- **Addresses**: Street, city, state patterns
- **Dates of Birth**: Various date formats
- **Organizations**: Company and institution names

### How PII Detection Works

1. **Pattern Matching**: Regular expressions detect well-formed patterns (emails, phones, SSNs, etc.)
2. **Heuristic Analysis**: Machine learning-friendly patterns detect names and complex entities
3. **Confidence Scoring**: Each detected PII includes a confidence score (0-1)
4. **Position Tracking**: Exact location of PII in document is preserved

### Anonymization Modes

**Redact Mode (Default)**
Replaces detected PII with placeholder text:
```
Original: "Contact John Smith at john@example.com or 555-123-4567"
Redacted: "Contact [NAME] at [EMAIL] or [PHONE]"
```

**Remove Mode**
Completely removes detected PII from document:
```
Original: "Contact John Smith at john@example.com or 555-123-4567"
Removed:  "Contact at"
```

### Use Cases

- **Compliance**: Prepare documents for sharing while protecting personal data
- **Data Sharing**: Safely share documents with third parties
- **Research**: Anonymize sensitive documents for research purposes
- **Privacy**: Remove personal information before archiving
- **GDPR/CCPA**: Meet regulatory requirements for data minimization

### Performance Notes

- PII detection: Varies by document size (~100ms for typical documents)
- Pattern matching is performed in-memory for speed
- Optional: Save anonymized version as new archived document
- Detailed audit trail of all anonymization operations

## API Endpoints

### Health Check
**GET** `/health`

Get comprehensive health status and key application statistics.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-17T21:19:16.141",
  "application": "Cloud Document Archive",
  "version": "1.0.0",
  "configuration": {
    "storage_provider": "aws_s3",
    "kafka_enabled": true,
    "lifecycle_enabled": true,
    "database_type": "sqlite"
  },
  "statistics": {
    "total_documents": 42,
    "total_size_mb": 156.82,
    "documents_24h": 5,
    "storage_tier_distribution": {
      "standard": 35,
      "archive": 5,
      "deep_archive": 2
    },
    "restore_status_distribution": {
      "not_archived": 35,
      "archived": 5,
      "restored": 2
    },
    "content_types_distribution": {
      "application/pdf": 30,
      "image/png": 10,
      "text/plain": 2
    },
    "avg_document_size_kb": 3745.33
  },
  "uptime_info": "Monitor with your infrastructure tools"
}
```

### Root Endpoint
**GET** `/`

Get basic application info.

**Response:**
```json
{
  "status": "healthy",
  "application": "Cloud Document Archive",
  "version": "1.0.0",
  "storage_provider": "aws_s3"
}
```

### Archive Document
**POST** `/api/v1/archive`

Archive a document with metadata and tags.

**Request Body:**
```json
{
  "document_base64": "SGVsbG8gV29ybGQh",
  "filename": "report.pdf",
  "content_type": "application/pdf",
  "tags": {
    "department": "finance",
    "year": "2026"
  },
  "metadata": {
    "author": "John Doe",
    "version": "1.0"
  }
}
```

**Response:**
```json
{
  "success": true,
  "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
  "message": "Document archived successfully",
  "storage_provider": "aws_s3",
  "archived_at": "2026-02-17T10:30:00"
}
```

### Retrieve Document
**POST** `/api/v1/retrieve` or **GET** `/api/v1/retrieve/{document_id}`

Retrieve a document by its unique identifier.

**Request Body (POST):**
```json
{
  "document_id": "a1b2c3d4e5f6abcd1234567890abcdef"
}
```

**Response:**
```json
{
  "success": true,
  "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
  "document_base64": "SGVsbG8gV29ybGQh",
  "filename": "report.pdf",
  "content_type": "application/pdf",
  "tags": {"department": "finance"},
  "metadata": {"author": "John Doe"},
  "archived_at": "2026-02-17T10:30:00",
  "retrieved_at": "2026-02-17T11:00:00"
}
```

### Delete Document
**DELETE** `/api/v1/archive/{document_id}`

Permanently delete a document from cloud storage and database. Publishes a Kafka event when deleted.

**Response:**
```json
{
  "success": true,
  "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
  "message": "Document deleted successfully",
  "deleted_at": "2026-02-17T12:00:00"
}
```

### Generate Report
**POST** `/api/v1/report`

Generate metrics report for a time period.

**Request Body:**
```json
{
  "start_date": "2026-01-01T00:00:00",
  "end_date": "2026-02-17T23:59:59",
  "group_by": "department"
}
```

**Response:**
```json
{
  "success": true,
  "start_date": "2026-01-01T00:00:00",
  "end_date": "2026-02-17T23:59:59",
  "metrics": {
    "total_documents": 150,
    "total_size_bytes": 52428800,
    "total_size_mb": 50.0,
    "documents_by_content_type": {
      "application/pdf": 100,
      "image/png": 50
    },
    "documents_by_tag": {
      "department": {"finance": 80, "hr": 70}
    },
    "storage_provider": "aws_s3"
  },
  "daily_uploads": [
    {"date": "2026-02-16", "count": 25, "size_bytes": 5242880}
  ],
  "top_tags": [
    {"tag_key": "department", "tag_value": "finance", "count": 80}
  ]
}
```

### Vector Semantic Search
**POST** `/api/v1/search`

Perform semantic search to find documents similar to a query using vector embeddings and cosine similarity.

**Request Body:**
```json
{
  "query": "quarterly financial report",
  "top_k": 5,
  "min_similarity": 0.5
}
```

**Response:**
```json
{
  "success": true,
  "query": "quarterly financial report",
  "results": [
    {
      "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
      "filename": "q4_2025_report.pdf",
      "content_type": "application/pdf",
      "similarity_score": 0.95,
      "tags": {"department": "finance"},
      "created_at": "2026-02-17T10:30:00",
      "storage_tier": "standard"
    },
    {
      "document_id": "b2c3d4e5f6abcd1234567890abcdef01",
      "filename": "financial_summary.pdf",
      "content_type": "application/pdf",
      "similarity_score": 0.87,
      "tags": {"department": "finance"},
      "created_at": "2026-02-10T14:22:00",
      "storage_tier": "standard"
    }
  ],
  "total_results": 2,
  "search_time_ms": 234.56
}
```

**Parameters:**
- `query`: Search query text (required)
- `top_k`: Number of top results to return (1-100, default: 10)
- `min_similarity`: Minimum similarity score threshold (0-1, default: 0.0)

**How It Works:**
1. Query text is converted to a vector embedding using sentence-transformers
2. Embeddings are compared with all archived documents using cosine similarity
3. Results are ranked by similarity score (highest first)
4. Only results meeting the min_similarity threshold are returned
5. Results are limited to top_k matches

### Move to Deep Archive
**POST** `/api/v1/deep-archive`

Move a document to deep archive storage (AWS Glacier, Azure Archive, GCP Archive).

**Request Body:**
```json
{
  "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
  "storage_tier": "deep_archive"
}
```

**Storage Tiers:**
- `standard` - Regular storage (S3 Standard, Azure Hot, GCP Standard)
- `infrequent` - Infrequent access (S3 IA, Azure Cool, GCP Nearline)
- `archive` - Archive tier (S3 Glacier IR, Azure Cold, GCP Coldline)
- `deep_archive` - Deep archive (S3 Glacier Deep Archive, Azure Archive, GCP Archive)

**Response:**
```json
{
  "success": true,
  "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
  "message": "Document moved to deep_archive successfully",
  "previous_tier": "standard",
  "new_tier": "deep_archive",
  "archived_at": "2026-02-17T10:30:00"
}
```

### Restore from Deep Archive
**POST** `/api/v1/restore`

Initiate restore of a document from deep archive. Required for AWS Glacier and Azure Archive before retrieval.

**Request Body:**
```json
{
  "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
  "restore_days": 7,
  "restore_tier": "Standard"
}
```

**Restore Tiers (AWS Glacier):**
- `Expedited` - 1-5 minutes (higher cost)
- `Standard` - 3-5 hours
- `Bulk` - 5-12 hours (lowest cost)

**Response:**
```json
{
  "success": true,
  "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
  "message": "Restore initiated successfully with Standard tier",
  "restore_status": "in_progress",
  "estimated_completion": "3-5 hours",
  "restore_expiry": null
}
```

### Get Archive Status
**GET** `/api/v1/archive-status/{document_id}`

Check the current archive/restore status of a document.

**Response:**
```json
{
  "success": true,
  "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
  "storage_tier": "deep_archive",
  "restore_status": "restored",
  "restore_expiry": "2026-02-24T10:30:00",
  "is_retrievable": true,
  "message": "Document is restored and available"
}
```

**Restore Statuses:**
- `not_archived` - Document is in standard storage
- `archived` - Document is in archive, not being restored
- `in_progress` - Restore is in progress
- `restored` - Document is temporarily restored and accessible

### Retrieve from Glacier
**POST** `/api/v1/glacier/retrieve`

Retrieve a document from Glacier storage. If the document is archived, initiates a restore operation. Publishes Kafka events when restore completes.

**Request:**
```json
{
  "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
  "restore_tier": "standard",
  "restore_days": 7
}
```

**Response (Restore Initiated):**
```json
{
  "success": true,
  "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
  "storage_tier": "deep_archive",
  "restore_status": "in_progress",
  "message": "Restore initiated. A Kafka event will be published when ready.",
  "estimated_completion": "2026-02-21T16:30:00"
}
```

**Response (Already Available):**
```json
{
  "success": true,
  "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
  "storage_tier": "standard",
  "restore_status": "not_archived",
  "message": "Document is available for immediate retrieval",
  "content_base64": "SGVsbG8gV29ybGQh..."
}
```

**Restore Tiers:**
- `expedited` - 1-5 minutes (higher cost)
- `standard` - 3-5 hours (default)
- `bulk` - 5-12 hours (lowest cost)

### Run Lifecycle Archival
**POST** `/api/v1/lifecycle/archive`

Manually trigger lifecycle archival to move old documents to Glacier based on age.

**Request:**
```json
{
  "dry_run": false
}
```

**Response:**
```json
{
  "success": true,
  "documents_processed": 5,
  "documents_archived": 3,
  "documents_failed": 0,
  "details": [
    {
      "document_id": "abc123...",
      "previous_tier": "standard",
      "new_tier": "deep_archive",
      "status": "success"
    }
  ],
  "message": "Lifecycle archival completed"
}
```

### Check Restore Status
**POST** `/api/v1/lifecycle/check-restores`

Check all pending restores and publish Kafka events for any that have completed.

**Response:**
```json
{
  "success": true,
  "documents_checked": 2,
  "documents_ready": 1,
  "kafka_events_published": 1,
  "message": "Restore status check completed"
}
```

### List Eligible Documents
**GET** `/api/v1/lifecycle/eligible`

List documents eligible for lifecycle archival based on configured age thresholds.

**Response:**
```json
{
  "success": true,
  "eligible_for_archive": [
    {
      "document_id": "abc123...",
      "filename": "old_document.pdf",
      "created_at": "2025-01-01T00:00:00",
      "age_days": 45,
      "current_tier": "standard",
      "target_tier": "deep_archive"
    }
  ],
  "total_count": 1,
  "archive_threshold_days": 30,
  "deep_archive_threshold_days": 90
}
```

## Kafka Events

When documents are archived, deleted, moved to Glacier, or restored, events are published to Kafka:

**Event Types:**
- `document.archived` - Document uploaded and stored
- `document.deleted` - Document permanently deleted
- `document.moved_to_glacier` - Document moved to Glacier storage
- `document.restore_initiated` - Restore request started
- `document.restore_ready` - Document restored and available
- `document.restore_expired` - Temporary restore has expired

**Example Event Payload:**
```json
{
  "event_type": "document.restore_ready",
  "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
  "filename": "document.pdf",
  "storage_tier": "deep_archive",
  "restore_status": "restored",
  "restore_expiry": "2026-02-28T16:30:00",
  "timestamp": "2026-02-21T16:30:00"
}
```

## Project Structure

```
clouddocumentachieve/
├── app/
│   ├── __init__.py
│   ├── config.py            # Configuration management
│   ├── database.py          # Database models and session
│   ├── kafka_producer.py    # Kafka event publishing
│   ├── lifecycle_service.py # Automatic Glacier archival
│   ├── main.py              # FastAPI application
│   ├── models.py            # Pydantic request/response models
│   ├── routes.py            # API route definitions
│   ├── services.py          # Business logic
│   └── storage/
│       ├── __init__.py
│       ├── base.py          # Abstract storage provider
│       ├── aws_s3.py        # AWS S3 implementation
│       ├── azure_blob.py    # Azure Blob implementation
│       ├── gcp_storage.py   # GCP Storage implementation
│       └── factory.py       # Storage provider factory
├── .env.example             # Environment template
├── requirements.txt         # Python dependencies
└── README.md
```

## License

MIT License
