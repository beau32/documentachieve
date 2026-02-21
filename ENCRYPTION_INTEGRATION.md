# Encryption Integration Guide

This guide explains how to integrate the encryption system with the existing Cloud Document Archive components (storage providers, database, and API routes).

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│         API Routes (routes.py)                      │
│  POST /api/v1/archive                              │
│  POST /api/v1/retrieve                             │
└─────────────────────────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────┐
│      Document Archive Service (services.py)         │
│  - archive_document()                               │
│  - retrieve_document()                              │
└─────────────────────────────────────────────────────┘
                        │
          ┌─────────────┼─────────────┐
          ↓             ↓             ↓
    ┌──────────┐  ┌──────────┐  ┌──────────────┐
    │ Storage  │  │ Database │  │ Encryption   │
    │ Factory  │  │ Metadata │  │ Service (NEW)│
    └──────────┘  └──────────┘  └──────────────┘
         │             │             │
         ↓             ↓             ↓
    ┌──────────┐  ┌──────────┐
    │  Cloud   │  │  SQLite  │
    │ Providers│  │/Database │
    └──────────┘  └──────────┘
```

## Integration Points

### 1. Storage Providers Integration

Update storage providers to support encryption:

```python
# In app/storage/aws_s3.py (and other providers)

from app.encryption_service import get_encryption_service
import base64

class S3StorageProvider(BaseStorageProvider):
    async def upload(self, document_id, data, filename, content_type, tags, metadata):
        # Check if encryption is needed
        should_encrypt = metadata.get("encrypt", False)
        
        encryption_service = get_encryption_service()
        
        if should_encrypt and encryption_service.config.enabled:
            # Encrypt document
            encrypted, iv_or_key, tag = encryption_service.encrypt_data(
                data,
                associated_data=document_id.encode()
            )
            
            # Store encrypted data
            data_to_upload = encrypted
            
            # Store encryption metadata for retrieval
            metadata["_encrypted"] = True
            metadata["_encryption_iv_key"] = base64.b64encode(iv_or_key).decode()
            metadata["_encryption_tag"] = base64.b64encode(tag).decode()
        else:
            data_to_upload = data
        
        # Upload to cloud storage
        # ... existing upload logic ...
        
        return StorageResult(...)
    
    async def download(self, storage_path):
        # Download data
        # ... existing download logic ...
        
        result = RetrieveResult(...)
        
        # Check if data is encrypted
        if result.metadata.get("_encrypted"):
            encryption_service = get_encryption_service()
            
            if encryption_service.config.enabled and encryption_service.config.private_key:
                # Decrypt data
                iv_or_key = base64.b64decode(result.metadata["_encryption_iv_key"])
                tag = base64.b64decode(result.metadata["_encryption_tag"])
                
                result.data = encryption_service.decrypt_data(
                    result.data,
                    iv_or_key,
                    tag,
                    associated_data=storage_path.encode()
                )
        
        return result
```

### 2. Database Integration

The database model already has encryption fields. Update the services to use them:

```python
# In app/services.py - DocumentArchiveService

async def archive_document(self, request):
    # ... existing code ...
    
    # Check if encryption is requested
    should_encrypt = request.metadata.get("encrypt", False)
    
    encryption_service = get_encryption_service()
    
    # Create database record
    db_record = DocumentMetadata(
        document_id=document_id,
        filename=request.filename,
        # ... other fields ...
        is_encrypted="true" if should_encrypt else "false",
        encryption_algorithm=encryption_service.config.algorithm if should_encrypt else None,
    )
    
    # If encryption is enabled, encrypt metadata
    if should_encrypt and encryption_service.config.enabled:
        if request.metadata:
            metadata_json = json.dumps(request.metadata).encode()
            encrypted, key, tag = encryption_service.encrypt_data(
                metadata_json,
                associated_data=document_id.encode()
            )
            
            db_record.metadata_encrypted = "true"
            db_record.metadata_json = base64.b64encode(encrypted).decode()
            db_record.encryption_iv_or_key = base64.b64encode(key).decode()
            db_record.encryption_tag = base64.b64encode(tag).decode()
        else:
            db_record.metadata_json = None
    else:
        db_record.metadata_json = json.dumps(request.metadata) if request.metadata else None
    
    self.db.add(db_record)
    self.db.commit()
    
    return ArchiveResponse(...)
```

### 3. API Route Integration

Update routes to accept and return encryption information:

```python
# In app/routes.py

@router.post("/archive", response_model=ArchiveResponse)
async def archive_document(request: ArchiveRequest, db: Session = Depends(get_db)):
    service = DocumentArchiveService(db)
    
    # The encryption flag can be in metadata
    response = await service.archive_document(request)
    
    # Check database for encryption status
    if response.success:
        db_record = db.query(DocumentMetadata).filter_by(
            document_id=response.document_id
        ).first()
        
        if db_record and db_record.is_encrypted == "true":
            response.is_encrypted = True
            response.encryption_algorithm = db_record.encryption_algorithm
    
    return response
```

## Data Flow with Encryption

### Upload (Encryption) Flow:

```
1. Client sends: ArchiveRequest
   └─ document_base64 (base64 encoded file)
   └─ metadata: {encrypt: true}

2. API Route
   └─ Calls DocumentArchiveService.archive_document()

3. Document Archive Service
   ├─ Checks if encryption requested
   ├─ Gets EncryptionService
   ├─ Calls storage provider for document

4. Storage Provider
   ├─ Encrypts document (if requested)
   │  ├─ Generates AES key
   │  ├─ Encrypts with AES-256-GCM
   │  └─ Encrypts AES key with RSA
   ├─ Stores encrypted document in cloud storage
   └─ Returns metadata with encryption info

5. Document Archive Service
   ├─ Stores document metadata in database
   ├─ Encrypts database metadata (tags, etc.)
   ├─ Stores encryption IV/key and tag
   └─ Returns ArchiveResponse with is_encrypted=true

6. Client receives: ArchiveResponse
   └─ Document stored encrypted in cloud
   └─ Metadata encrypted in database
```

### Download (Decryption) Flow:

```
1. Client sends: RetrieveRequest
   └─ document_id

2. API Route
   └─ Calls DocumentArchiveService.retrieve_document()

3. Document Archive Service
   ├─ Queries database for document metadata
   ├─ Gets encryption metadata from database
   ├─ Calls storage provider for document

4. Storage Provider
   ├─ Downloads from cloud storage
   ├─ Checks if encrypted
   ├─ If encrypted:
   │  ├─ Decrypts AES key with RSA private key
   │  ├─ Decrypts document with AES-256-GCM
   │  └─ Verifies AEAD tag
   └─ Returns decrypted data

5. Document Archive Service
   ├─ Decrypts database metadata if needed
   ├─ Reconstructs document object
   └─ Returns RetrieveResponse with decrypted data

6. Client receives: RetrieveResponse
   └─ Document data (decrypted)
   └─ Metadata (decrypted)
```

## Step-by-Step Integration

### Phase 1: Core Encryption (Done ✓)
- [x] Create `encryption_service.py`
- [x] Update `config.py` with encryption settings
- [x] Update `database.py` with encryption fields
- [x] Update `requirements.txt` with cryptography

### Phase 2: Storage Provider Integration (TODO)
1. Update `app/storage/base.py`:
   - Add encryption support to abstract methods
   - Document encryption parameter

2. Update each storage provider:
   - `app/storage/local.py`
   - `app/storage/aws_s3.py`
   - `app/storage/azure_blob.py`
   - `app/storage/gcp_storage.py`

### Phase 3: Service Integration (TODO)
1. Update `app/services.py`:
   - Modify `archive_document()` to handle encryption
   - Modify `retrieve_document()` to handle decryption
   - Add encryption metadata tracking

2. Update `app/models.py`:
   - Add `is_encrypted` field to response models
   - Add `encryption_algorithm` to response models

### Phase 4: API Integration (TODO)
1. Update `app/routes.py`:
   - Add encryption info to responses
   - Document encryption parameters
   - Add encryption status to API docs

2. Update API examples/documentation

## Configuration Checklist

Before integrating encryption with existing code:

- [ ] Private key file exists and is readable by application
- [ ] Certificate file exists and is accessible
- [ ] File permissions: private_key (600), certificate (644)
- [ ] cryptography library installed (>= 41.0.0)
- [ ] config.yaml or environment variables set correctly
- [ ] Storage provider can handle encrypted data (size increases by ~10-15%)
- [ ] Database has encryption fields (migration may be needed)

## Testing the Integration

### Unit Tests

```python
from app.encryption_service import EncryptionConfig, EncryptionService
from app.database import DocumentMetadata

def test_encryption_decrypt_cycle():
    # Setup
    config = EncryptionConfig(enabled=True, ...)
    service = EncryptionService(config)
    
    # Test
    original = b"test data"
    encrypted, key, tag = service.encrypt_data(original)
    decrypted = service.decrypt_data(encrypted, key, tag)
    
    assert decrypted == original
```

### Integration Tests

```python
async def test_archive_with_encryption():
    # Create request with encryption
    request = ArchiveRequest(
        document_base64=base64.b64encode(b"test").decode(),
        filename="test.pdf",
        metadata={"encrypt": "true"}
    )
    
    # Archive
    service = DocumentArchiveService(db)
    response = await service.archive_document(request)
    
    # Verify encryption
    assert response.success is True
    db_record = db.query(DocumentMetadata).filter_by(
        document_id=response.document_id
    ).first()
    assert db_record.is_encrypted == "true"
```

## Performance Considerations

- **Encryption overhead**: 10-15% CPU increase
- **Data size increase**: ~50-60 bytes per document (key + IV + tag)
- **Recommended caching**: Cache decrypted data for 5-15 minutes
- **Key access**: Use HSM for production for better performance

## Migration Path

For existing systems without encryption:

1. **Enable encryption for new documents**: No backward compatibility issues
2. **Re-encrypt existing documents** (optional):
   - Background job to re-encrypt old documents
   - Keep unencrypted versions temporarily
   - Mark as encrypted after re-encryption succeeds
3. **Monitor performance**: Track encryption/decryption times

## Next Steps

1. Review and implement Phase 2 (Storage Provider Integration)
2. Implement Phase 3 (Service Integration)
3. Implement Phase 4 (API Integration)
4. Add comprehensive tests
5. Update API documentation
6. Deploy with monitoring

For detailed information, see [ENCRYPTION.md](ENCRYPTION.md)
