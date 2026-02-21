# Local Storage Configuration Guide

Run Document Archive locally using filesystem directories instead of cloud providers. Perfect for development, testing, and learning.

## 🚀 Quick Start

### 1. Create config.yaml

```bash
cp config.yaml.example config.yaml
```

### 2. Set storage provider to local

```yaml
app:
  name: Cloud Document Archive
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

### 3. Run the application

```bash
python -m app.main
```

### 4. Start archiving documents

```bash
curl -X POST http://localhost:8000/archive \
  -H "Content-Type: application/json" \
  -d '{
    "document_base64": "SGVsbG8gV29ybGQh",
    "filename": "hello.txt",
    "content_type": "text/plain",
    "tags": {"department": "finance"},
    "metadata": {"version": "1.0"}
  }'
```

## 📁 Directory Structure

After running the application, you'll see:

```
documentarchieve/
├── documents/                          # Standard tier (0-30 days)
│   └── 2026/02/19/*.meta.json         # Auto-organized by date
│
├── documents_archive/                  # Archive tier (90-365 days)
│   └── 2026/02/19/*.meta.json         # Each tier separate
│
├── documents_deep_archive/             # Deep archive (365+ days)
│   └── 2026/02/19/*.meta.json         # Simulates Glacier
│
├── iceberg_warehouse/ (optional)       # Iceberg metadata
│   └── document_archive/
│       └── document_metadata/
│           ├── metadata/
│           └── data/metadata.jsonl
│
└── document_archive.db                 # SQLite metadata database
```

## 🔄 Storage Tiers (Simulated)

### Standard Tier (Cold start)
- Location: `./documents/`
- Life cycle: 0-30 days
- Retrieval: Immediate (< 1ms)
- Represented by: Regular files

### Archive Tier
- Location: `./documents_archive/`
- Lifecycle: 30-365 days
- Retrieval: Simulated via `/restore` endpoint
- Represented by: Copied to standard on restore

### Deep Archive Tier
- Location: `./documents_deep_archive/`
- Lifecycle: 365+ days
- Retrieval: Simulated via `/restore` endpoint with longer expiry
- Represented by: Stored in separate deep archive folder

## ⚙️ Configuration Options

```yaml
storage:
  local:
    # Path for documents in standard tier
    storage_path: ./documents
    
    # Path for documents in archive tier
    archive_path: ./documents_archive
    
    # Path for documents in deep archive tier
    deep_archive_path: ./documents_deep_archive
```

Or use environment variables:

```bash
export LOCAL_STORAGE_PATH=/var/lib/documents
export LOCAL_ARCHIVE_PATH=/var/lib/documents_archive
export LOCAL_DEEP_ARCHIVE_PATH=/var/lib/documents_deep_archive
```

## 📊 Metadata Storage

### Option 1: SQLite (Default)
```yaml
database:
  url: sqlite:///./document_archive.db
```

Metadata stored in local SQLite database:
- ✓ Simple, no setup
- ✓ Good for development
- ✓ Indexing and queries work well

### Option 2: Local Iceberg (Development)
```yaml
database:
  url: "iceberg"

iceberg:
  catalog_uri: "http://localhost:8181"  # Local Nessie or REST catalog
  warehouse_path: ./iceberg_local       # Local Iceberg warehouse
```

Files stored as JSONL:
- ✓ Time travel queries possible
- ✓ No external service needed
- ✓ Schema evolution

## 🔍 Understanding File Organization

Documents are organized automatically by date:

```
documents/
2026/
  02/
    19/
      a1b2c3d4e5f6abcd1234567890abcdef       # Document ID as filename
      a1b2c3d4e5f6abcd1234567890abcdef.meta.json
      a2c3d4e5f6g7hij8klmnopqrstu
      a2c3d4e5f6g7hij8klmnopqrstu.meta.json
```

Each document has:
1. **Document file**: Binary content (PDF, Word, Image, etc.)
2. **Metadata file**: `.meta.json` with:
   - Original filename
   - Content type
   - File size
   - Tags and custom metadata
   - Upload timestamp
   - Content hash (SHA256)
   - Storage tier

## 📝 Metadata File Example

```json
{
  "document_id": "a1b2c3d4e5f6abc...",
  "filename": "report.pdf",
  "content_type": "application/pdf",
  "size_bytes": 2048576,
  "tags": {
    "department": "finance",
    "year": "2026",
    "category": "quarterly"
  },
  "metadata": {
    "author": "John Doe",
    "version": "1.0"
  },
  "uploaded_at": "2026-02-19T10:30:00.123456",
  "storage_tier": "standard",
  "content_hash": "sha256:abcd1234..."
}
```

## 🎯 Use Cases

### Development
```yaml
storage:
  provider: local
  local:
    storage_path: ./documents
    archive_path: ./documents_archive
    deep_archive_path: ./documents_deep_archive

database:
  url: sqlite:///./document_archive.db
```

### Testing
```yaml
storage:
  provider: local
  local:
    storage_path: /tmp/test_documents
    archive_path: /tmp/test_archive
    deep_archive_path: /tmp/test_deep_archive

database:
  url: sqlite:///./test_archive.db
```

### Demo with Iceberg
```yaml
storage:
  provider: local
  local:
    storage_path: ./demo_documents
    archive_path: ./demo_archive
    deep_archive_path: ./demo_deep_archive

database:
  url: "iceberg"

iceberg:
  warehouse_path: ./demo_warehouse
```

## 📊 API Examples

### Upload Document
```bash
curl -X POST http://localhost:8000/archive \
  -H "Content-Type: application/json" \
  -d '{
    "document_base64": "SGVsbG8gV29ybGQh",
    "filename": "hello.txt",
    "content_type": "text/plain",
    "tags": {"type": "demo"},
    "metadata": {"app": "test"}
  }'
```

Response:
```json
{
  "success": true,
  "document_id": "abc123def456",
  "message": "Document archived successfully",
  "storage_provider": "local",
  "archived_at": "2026-02-19T10:30:00"
}
```

### Retrieve Document
```bash
curl -X POST http://localhost:8000/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "abc123def456"
  }'
```

### Archive to Cold Storage (Move to archive_path)
```bash
# Check current tier
curl http://localhost:8000/document/abc123def456/info

# Archive to cold tier (simulate 90+ days)
curl -X POST http://localhost:8000/document/abc123def456/archive \
  -H "Content-Type: application/json" \
  -d '{"target_tier": "archive"}'
```

### Restore from Archive
```bash
curl -X POST http://localhost:8000/document/abc123def456/restore \
  -H "Content-Type: application/json" \
  -d '{"restore_days": 7}'
```

## 🔄 Simulate Lifecycle

Local storage allows you to manually simulate the archival lifecycle:

```bash
# Day 1: Document uploaded (standard tier)
# Location: documents/2026/02/19/doc_id

# Day 31: Move to archive (simulate 30+ days)
curl -X POST http://localhost:8000/lifecycle/now \
  -H "Content-Type: application/json" \
  -d '{"target_tier": "archive"}'
# Location: documents_archive/2026/02/19/doc_id

# Day 91: Move to deep archive (simulate 90+ days)
curl -X POST http://localhost:8000/lifecycle/now \
  -H "Content-Type: application/json" \
  -d '{"target_tier": "deep_archive"}'
# Location: documents_deep_archive/2026/02/19/doc_id

# Restore: Copy back to standard (expiry in 7 days)
curl -X POST http://localhost:8000/document/doc_id/restore \
  -H "Content-Type: application/json" \
  -d '{"restore_days": 7}'
# Location: documents/2026/02/19/restored_doc_id
```

## 📈 Monitoring Local Storage

### Check Disk Usage
```bash
# Standard tier size
du -sh documents/

# Archive tier size
du -sh documents_archive/

# Deep archive tier size
du -sh documents_deep_archive/

# Total
du -sh documents* | tail -1
```

### Count Documents by Tier
```bash
# Standard
find documents -type f ! -name "*.meta.json" | wc -l

# Archive
find documents_archive -type f ! -name "*.meta.json" | wc -l

# Deep Archive
find documents_deep_archive -type f ! -name "*.meta.json" | wc -l
```

### List Recent Documents
```bash
# Most recent documents added (standard tier)
ls -lt documents/$(date +%Y/%m/%d)/ | head -10

# All archived documents
find documents_archive -name "*.meta.json" -type f
```

## 🧹 Cleanup

### Clear All Local Data
```bash
# Remove all documents and metadata
rm -rf documents documents_archive documents_deep_archive iceberg_warehouse

# Remove database
rm document_archive.db

# Recreate empty directories (app will create them)
mkdir -p documents documents_archive documents_deep_archive iceberg_warehouse
```

### Archive Old Documents
```bash
# Find and remove documents older than 1 year
find documents_deep_archive -type f ! -name "*.meta.json" -mtime +365 -delete
```

## ⚡ Performance

Local storage performance characteristics:

| Operation | Time | Notes |
|-----------|------|-------|
| Upload 10MB | ~1ms | SATA SSD, network not involved |
| Download 10MB | ~1ms | SATA SSD |
| Archive (move) | ~1ms | Same filesystem |
| Restore | ~30ms | Copy to standard tier |
| List 1000 docs | ~50ms | Filesystem scan |
| Query metadata | <1ms | SQLite index |

## 🔐 Security Notes

For production-like testing:

```bash
# Use disk encryption
sudo disk-utility encryptStorageDevice documents

# Set restrictive permissions
chmod 700 documents documents_archive documents_deep_archive

# Chown to specific user
sudo chown app:app documents*

# Only app user can access
chmod 700 iceberg_warehouse document_archive.db
```

## 📚 Related Documentation

- [config.yaml.example](config.yaml.example) - Configuration examples
- [ICEBERG_SETUP.md](ICEBERG_SETUP.md) - Iceberg metadata storage
- [app/storage/local.py](app/storage/local.py) - Local storage implementation
- [app/local_iceberg_database.py](app/local_iceberg_database.py) - Local Iceberg DB

## 🆘 Troubleshooting

### Files not found after upload
- Check `storage_path` configuration is correct
- Verify directory exists: `ls -la documents/`
- Check file permissions: `ls -la documents/2026/02/19/`

### Metadata missing
- Check `.meta.json` files exist alongside documents
- View metadata: `cat documents/2026/02/19/*.meta.json`

### Disk full
- Check total size: `du -sh documents*`
- Move old deep archive to backup: `mv documents_deep_archive /backup/`

### Permission denied
- Check user permissions: `ls -la documents/`
- Change owner: `sudo chown $USER documents*`

## 💡 Tips

1. **Use for learning**: Perfect way to understand the archive lifecycle
2. **Integration tests**: Run full tests without cloud credentials
3. **Demo mode**: Show clients how archival works
4. **Development**: Fast iteration without API calls or costs
5. **Backup current state**: `tar -czf backup-$(date +%s).tar.gz documents* iceberg_warehouse`

---

**All document files are stored locally. No cloud providers needed!** 🎉
