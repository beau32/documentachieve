# Postman Collection Guide

## Overview

This directory contains a Postman collection for the Cloud Document Archive API. The collection includes all available endpoints with example requests and responses.

**File:** `Cloud_Document_Archive.postman_collection.json`

## Importing the Collection

### Method 1: Postman UI
1. Open Postman
2. Click **Import** (top left)
3. Select **File**
4. Choose `Cloud_Document_Archive.postman_collection.json`
5. Click **Import**

### Method 2: Direct Import
1. Open Postman
2. Use this link in your browser: `postman://app/import/by-link?url=<path-to-file>`

## Collection Structure

The collection is organized into 5 main folders:

### 1. Health & Status
- **Root Health Check** - GET / - Basic application health
- **Health Check** - GET /health - Detailed stats and status

### 2. Document Archive
- **Archive Document** - POST /api/v1/archive - Upload and archive a document
- **Retrieve Document (POST)** - POST /api/v1/retrieve - Retrieve by ID (POST)
- **Retrieve Document (GET)** - GET /api/v1/retrieve/{id} - Retrieve by ID (GET)
- **Delete Document** - DELETE /api/v1/archive/{id} - Permanently delete

### 3. Deep Archive & Restoration
- **Move to Deep Archive** - POST /api/v1/deep-archive - Archive to Glacier/Azure Archive
- **Restore from Deep Archive** - POST /api/v1/restore - Restore from deep archive
- **Get Archive Status** - GET /api/v1/archive-status/{id} - Check status
- **Retrieve from Glacier** - POST /api/v1/glacier/retrieve - Retrieve with auto-restore
- **Retrieve from Glacier (GET)** - GET /api/v1/glacier/retrieve/{id} - GET variant

### 4. Reports & Analytics
- **Generate Report** - POST /api/v1/report - Generate metrics for time period

### 5. Search & Discovery
- **Vector Semantic Search** - POST /api/v1/search - Find similar documents by semantic meaning

### 6. Privacy & Compliance
- **Detect PII** - POST /api/v1/detect-pii - Scan for personally identifiable information
- **Anonymize Document** - POST /api/v1/anonymize - Redact or remove PII from document

### 7. Lifecycle Management
- **Run Lifecycle Archival** - POST /api/v1/lifecycle/archive - Trigger archival
- **Check Restore Status** - POST /api/v1/lifecycle/check-restores - Check restores
- **List Eligible Documents** - GET /api/v1/lifecycle/eligible - List archival candidates

## Variables

The collection uses Postman variables for easy configuration:

| Variable | Default | Description |
|----------|---------|-------------|
| `base_url` | http://localhost:8000 | API base URL |
| `document_id` | a1b2c3d4e5f6abcd... | Sample document ID for testing |

### Updating Variables

1. Click **Variables** (at collection level)
2. Edit `base_url` to your API endpoint
3. Update `document_id` after archiving a document

Or use environment variables in Postman for different environments (dev, staging, prod).

## Workflow Example

### 1. Archive a Document
```json
POST /api/v1/archive
{
  "document_base64": "SGVsbG8gV29ybGQh",
  "filename": "report.pdf",
  "tags": {"department": "finance"}
}
```
**Response:** Copy the `document_id` for further operations

### 2. Retrieve the Document
```json
GET /api/v1/retrieve/{document_id}
```
Returns the base64 encoded document

### 3. Move to Deep Archive
```json
POST /api/v1/deep-archive
{
  "document_id": "{document_id}",
  "storage_tier": "deep_archive"
}
```

### 4. Restore from Archive
```json
POST /api/v1/restore
{
  "document_id": "{document_id}",
  "restore_days": 7,
  "restore_tier": "Standard"
}
```

### 5. Check Status
```json
GET /api/v1/archive-status/{document_id}
```

## Base64 Encoding

For testing, use base64 encoded content. Examples:

- **"Hello World"** → `SGVsbG8gV29ybGQh`
- **"Test Document"** → `VGVzdCBEb2N1bWVudA==`

Use online tools or command line:
```bash
echo "Hello World" | base64
```

## Response Examples

### Archive Success
```json
{
  "success": true,
  "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
  "message": "Document archived successfully",
  "storage_provider": "aws_s3",
  "archived_at": "2026-02-17T10:30:00"
}
```

### Health Check
```json
{
  "status": "healthy",
  "storage_provider": "aws_s3",
  "kafka_enabled": true,
  "lifecycle_enabled": true
}
```

## Environment Setup

### For AWS S3
Set environment variables:
```bash
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_S3_BUCKET=your-bucket
```

### For Azure Blob
```bash
export AZURE_CONNECTION_STRING=your-connection-string
export AZURE_CONTAINER_NAME=your-container
```

### For GCP Storage
```bash
export GCP_PROJECT_ID=your-project
export GCP_CREDENTIALS_PATH=/path/to/credentials.json
export GCP_BUCKET_NAME=your-bucket
```

## Vector Search Guide

### Basic Usage
```json
{
  "query": "quarterly report",
  "top_k": 10,
  "min_similarity": 0.5
}
```

### Search Tips
- **Query Tips**: Use natural language, similar to how you'd describe the document
- **Broader Searches**: Lower `min_similarity` (0.3-0.5) for broader results
- **Strict Searches**: Higher `min_similarity` (0.7-0.9) for very relevant results
- **Result Limit**: Increase `top_k` for more results (up to 100 max)

### Example Searches
- "financial statement" → Finds financial reports, balance sheets, budgets
- "employee handbook" → Finds HR documents, policies, guidelines
- "project proposal" → Finds project plans, RFPs, business proposals
- "meeting notes" → Finds meeting minutes, action items, summaries

## PII Detection & Anonymization Guide

### Basic PII Detection
Scan a document for any PII without specifying types:
```json
{
  "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
  "pii_types": null
}
```

### Detect Specific PII Types
Scan only for certain PII types:
```json
{
  "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
  "pii_types": ["email", "phone", "ssn", "credit_card"]
}
```

### Anonymize with Redaction (Default)
Replace PII with placeholders:
```json
{
  "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
  "mask_mode": "redact",
  "save_anonymized_version": true
}
```

Result: `"Contact John Smith at john@example.com"` → `"Contact [NAME] at [EMAIL]"`

### Anonymize with Removal
Completely remove detected PII:
```json
{
  "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
  "mask_mode": "remove",
  "save_anonymized_version": true
}
```

Result: `"Contact John Smith at john@example.com"` → `"Contact at"`

### Supported PII Types
- `email` - Email addresses
- `phone` - Phone numbers (various formats)
- `ssn` - Social Security Numbers
- `credit_card` - Credit card numbers
- `ip_address` - IP addresses (v4 and v6)
- `name` - Person names
- `address` - Physical addresses
- `date_of_birth` - Dates of birth
- `person` - Person entities
- `organization` - Organization/company names

### Use Cases
- **GDPR Compliance**: Prepare documents for sharing while protecting personal data
- **Data Sharing**: Safely share documents with third parties
- **Research**: Anonymize sensitive data for research purposes
- **Privacy**: Remove personal info before long-term archival
- **Audit Trail**: Track all anonymization operations for compliance

### Workflow Example

**Step 1: Detect PII**
```json
POST /api/v1/detect-pii
{
  "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
  "pii_types": null
}
```
Response shows detected PIIs and confidence scores.

**Step 2: Review Detection**
Look at the `pii_found` flag and `pii_summary` to see what was detected.

**Step 3: Anonymize Document**
```json
POST /api/v1/anonymize
{
  "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
  "mask_mode": "redact",
  "save_anonymized_version": true
}
```
Response includes preview of anonymized content and new document_id if saved.

**Step 4: Use Anonymized Version**
New document ID can be used like any other archived document for retrieval, archival, etc.

## Tips & Tricks

### 1. Save Document ID for Later
After archiving, save the `document_id` to a variable:
- In response, right-click on `document_id` value
- Select **Set as variable** → **document_id**

### 2. Use Pre-request Scripts
Add logic to auto-generate test data:
```javascript
pm.variables.set("timestamp", new Date().toISOString());
```

### 3. Test Workflows
Create a collection run to test multiple endpoints in sequence:
1. Archive doc
2. Retrieve doc
3. Move to archive
4. Check status

### 4. Copy as cURL
Right-click any request → **Copy as cURL** for command-line testing

### 5. Monitor Performance
Use Postman's built-in timeline to see request/response times

## Troubleshooting

### 401 Unauthorized
- Check API is running on correct port
- Verify base_url variable

### 404 Not Found
- Verify document_id exists
- Check API endpoint path spelling

### 400 Bad Request
- Verify request body JSON is valid
- Ensure base64 encoding is correct

## Additional Resources

- [API Documentation](../README.md)
- [FastAPI Swagger UI](http://localhost:8000/docs)
- [Postman Documentation](https://learning.postman.com/)
