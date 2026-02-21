# Encryption Configuration Guide

## Overview

The Cloud Document Archive supports certificate-based encryption for securing both document files and their database catalog entries. This guide explains how to configure and use encryption.

## Features

- **Hybrid RSA+AES Encryption**: Uses RSA for key management and AES-256-GCM for symmetric encryption
- **X.509 Certificate Support**: Works with standard X.509 certificates in PEM format
- **Database Integration**: Encrypts sensitive metadata in the database
- **Transparent Operation**: Encryption/decryption handled automatically by the application
- **Algorithm Flexibility**: Support for both RSA and AES-256-GCM algorithms

## Supported Algorithms

### RSA (Recommended for Production)

**How it works:**
1. The application generates a random AES-256 key
2. The AES key is encrypted using the RSA public key
3. The document is encrypted using the AES key with GCM mode
4. Only the holder of the private key can decrypt the AES key, and thus access the document

**Advantages:**
- Public key can be distributed safely
- Only the private key needs to be kept secure
- Industry standard for certificate-based encryption
- Suitable for distributed systems

**Key sizes supported:**
- 2048-bit (minimum)
- 4096-bit (recommended)
- 8192-bit (maximum security)

### AES-256-GCM (Symmetric Encryption)

**How it works:**
1. Uses a shared symmetric key for encryption and decryption
2. Provides authenticated encryption with associated data (AEAD)
3. Key size: 256 bits

**Advantages:**
- Faster performance than RSA
- Simpler key management for single-node setups
- Good for small-scale deployments

**Disadvantages:**
- Same key needed for encryption and decryption
- Not suitable for distributed systems without secure key sharing

## Getting Started

### Step 1: Generate RSA Keys and Certificate

For development/testing, use the built-in key generation:

```python
from app.encryption_service import generate_test_keys

cert_path, key_path = generate_test_keys(output_dir="./certs")
print(f"Certificate: {cert_path}")
print(f"Private Key: {key_path}")
```

For production, generate proper certificates using OpenSSL:

```bash
# Generate a 4096-bit RSA private key
openssl genrsa -out private_key.pem 4096

# Generate a self-signed certificate (valid for 365 days)
openssl req -new -x509 -key private_key.pem -out certificate.pem -days 365 \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Or, with a certificate signing request (CSR)
openssl req -new -key private_key.pem -out certificate.csr \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
# Then get it signed by your CA
openssl x509 -req -days 365 -in certificate.csr -signkey private_key.pem -out certificate.pem
```

For production with encrypted private key:

```bash
# Generate encrypted private key (you'll be prompted for a password)
openssl genrsa -des3 -out private_key.pem 4096

# Generate certificate from encrypted key
openssl req -new -x509 -key private_key.pem -out certificate.pem -days 365
```

### Step 2: Store Keys Securely

**Important Security Practices:**

1. **Private Key**:
   ```bash
   # Restrict access to private key
   chmod 600 private_key.pem
   chown <app-user>:<app-group> private_key.pem
   ```

2. **Certificate**:
   ```bash
   # Certificate can be public
   chmod 644 certificate.pem
   ```

3. **Key Storage Options**:
   - **Local Storage**: Store in a secure directory with restricted permissions
   - **Kubernetes Secrets**: Mount keys as secrets in Kubernetes
   - **Cloud Key Management** (recommended for production):
     - AWS Secrets Manager or KMS
     - Azure Key Vault
     - Google Cloud Key Management Service

### Step 3: Configure Encryption in config.yaml

Basic configuration:

```yaml
encryption:
  enabled: true
  algorithm: RSA
  certificate_path: ./certs/certificate.pem
  private_key_path: ./certs/private_key.pem
```

With password-protected private key:

```yaml
encryption:
  enabled: true
  algorithm: RSA
  certificate_path: ./certs/certificate.pem
  private_key_path: ./certs/private_key.pem
  key_password: "your-secure-password-here"
```

Alternatively, use environment variables:

```bash
export ENCRYPTION_ENABLED=true
export ENCRYPTION_ALGORITHM=RSA
export ENCRYPTION_CERTIFICATE_PATH=/app/certs/certificate.pem
export ENCRYPTION_PRIVATE_KEY_PATH=/app/certs/private_key.pem
```

### Step 4: Enable Encryption in Document Upload

Update your document archive request:

```python
import requests
import base64

# Read the document
with open("document.pdf", "rb") as f:
    document_base64 = base64.b64encode(f.read()).decode()

# Archive with encryption
response = requests.post(
    "http://localhost:8000/api/v1/archive",
    json={
        "document_base64": document_base64,
        "filename": "document.pdf",
        "content_type": "application/pdf",
        "tags": {
            "department": "finance",
            "confidential": "yes"
        },
        "metadata": {
            "author": "John Doe",
            "encrypt": "true"  # Flag to encrypt
        }
    }
)
```

Or using the API endpoint with encryption parameter:

```json
POST /api/v1/archive
{
  "document_base64": "...",
  "filename": "document.pdf",
  "content_type": "application/pdf",
  "metadata": {
    "encrypt": "true"
  }
}
```

## API Response for Encrypted Documents

When a document is encrypted, the response includes encryption information:

```json
{
  "success": true,
  "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
  "message": "Document archived successfully (encrypted)",
  "storage_provider": "aws_s3",
  "archived_at": "2026-02-21T10:30:00",
  "is_encrypted": true,
  "encryption_algorithm": "RSA"
}
```

## Retrieving Encrypted Documents

The application automatically handles decryption when retrieving documents:

```python
response = requests.post(
    "http://localhost:8000/api/v1/retrieve",
    json={
        "document_id": "a1b2c3d4e5f6abcd1234567890abcdef"
    }
)

# If encrypted, the application automatically decrypts it
document_data = base64.b64decode(response.json()["document_base64"])
```

## Database Encryption

Documents and sensitive metadata are encrypted in the database when encryption is enabled:

### Fields Encrypted:
- `metadata_json`: Document metadata (author, tags, etc.)
- `embedding_text`: Text used for semantic search embedding
- `tags_json`: Document tags (sensitive classification)

### Fields NOT Encrypted (for indexing/searching):
- `document_id`: Needed for lookups
- `filename`: Used for retrieval
- `storage_path`: Needed to locate document in storage
- `created_at`, `updated_at`: Timestamps for lifecycle management

### Encryption Metadata:
- `is_encrypted`: Whether the document is encrypted
- `encryption_algorithm`: Algorithm used (RSA, AES-256-GCM)
- `encryption_iv_or_key`: Initialization Vector or encrypted AES key
- `encryption_tag`: Authentication tag for verification

## Security Best Practices

### Key Management

1. **Separate Public and Private Keys**:
   - Distribute only the public certificate
   - Keep private key on secure, restricted servers
   - Never commit private keys to version control

2. **Key Rotation**:
   - Routinely rotate encryption keys
   - Implement a key versioning system
   - Document key rotation procedures

3. **Access Control**:
   ```bash
   # Restrict private key access
   chmod 600 private_key.pem
   
   # Only app user can read
   chown app:app private_key.pem
   ```

4. **Hardware Security Module (HSM)**:
   - For high-security requirements
   - Store private keys in HSM
   - Use PKCS#11 or similar interface

### Database Security

1. **Backup Encryption**:
   - Backup database regularly
   - Encrypt backups separately
   - Test backup restoration

2. **Access Controls**:
   - Limit database access to application only
   - Use database-level encryption (TDE)
   - Enable audit logging

3. **Compliance**:
   - Meet regulatory requirements (HIPAA, GDPR, PCI-DSS)
   - Document encryption procedures
   - Implement access logging

## Troubleshooting

### Certificate Not Found

**Error**: `FileNotFoundError: Certificate file not found`

**Solution:**
1. Verify file path exists
2. Check file permissions
3. Use absolute paths in configuration

### Private Key Password Incorrect

**Error**: `ValueError: Bad decrypt. Incorrect password?`

**Solution:**
1. Verify password is correct
2. Ensure password matches key encryption
3. Try without password if not encrypted

### Decryption Failed

**Error**: `InvalidTag: Decryption failed - invalid authentication tag`

**Solution:**
1. Ensure correct private key is being used
2. Verify the document wasn't corrupted during storage
3. Check that encryption algorithm matches what was used for encryption

### Performance Issues

If encryption is slowing down the application:

1. **Use Async Operations**: Ensure async/await is used
2. **Reduce Key Size**: Use 2048-bit keys instead of 4096-bit
3. **Cache Decrypted Data**: Implement caching for frequently accessed documents
4. **Hardware Acceleration**: Use TPM or HSM for cryptographic operations

## Testing Encryption

### Unit Tests

```python
from app.encryption_service import EncryptionConfig, EncryptionService

# Test encryption/decryption
config = EncryptionConfig(
    enabled=True,
    certificate_path="./certs/certificate.pem",
    private_key_path="./certs/private_key.pem",
    algorithm="RSA"
)

service = EncryptionService(config)

# Test data
original_data = b"Sensitive document content"
associated_data = b"document_id_12345"

# Encrypt
encrypted, key, tag = service.encrypt_data(original_data, associated_data)

# Decrypt
decrypted = service.decrypt_data(encrypted, key, tag, associated_data)

assert decrypted == original_data
print("✓ Encryption/Decryption successful!")
```

### Integration Tests

Test the full archive and retrieve flow with encryption:

```python
import requests
import base64
import json

# 1. Archive a document with encryption
doc_content = b"Test document with confidential information"
response = requests.post(
    "http://localhost:8000/api/v1/archive",
    json={
        "document_base64": base64.b64encode(doc_content).decode(),
        "filename": "confidential.pdf",
        "content_type": "application/pdf",
        "metadata": {"encrypt": "true"}
    }
)

assert response.status_code == 200
result = response.json()
doc_id = result["document_id"]
assert result.get("is_encrypted") is True

# 2. Retrieve the document
response = requests.post(
    "http://localhost:8000/api/v1/retrieve",
    json={"document_id": doc_id}
)

assert response.status_code == 200
retrieved = response.json()
retrieved_content = base64.b64decode(retrieved["document_base64"])

# 3. Verify content is intact
assert retrieved_content == doc_content
print("✓ Full encryption/decryption pipeline working!")
```

## Migration Guide: Enabling Encryption on Existing System

If you have existing unencrypted documents and want to start using encryption:

### Option 1: Enable for New Documents (Recommended)

1. Enable encryption in configuration
2. New documents are automatically encrypted
3. Old documents remain unencrypted but readable
4. Re-encrypt later using migration script

### Option 2: Encrypt All Documents at Once

```python
# Script to re-encrypt all existing documents
from app.database import SessionLocal, DocumentMetadata
from app.services import DocumentArchiveService
from app.storage.factory import get_storage_provider

db = SessionLocal()
service = DocumentArchiveService(db)
storage = get_storage_provider()

# Get all unencrypted documents
unencrypted = db.query(DocumentMetadata).filter(
    DocumentMetadata.is_encrypted == "false"
).all()

for doc_meta in unencrypted:
    try:
        # Download original
        result = await storage.download(doc_meta.storage_path)
        
        if result.success:
            # Re-upload with encryption
            encrypted_result = await storage.upload(
                document_id=doc_meta.document_id,
                data=result.data,
                filename=doc_meta.filename,
                content_type=doc_meta.content_type,
                tags=doc_meta.tags,
                metadata=doc_meta.meta
            )
            
            # Update metadata
            doc_meta.is_encrypted = "true"
            db.commit()
            print(f"✓ Encrypted {doc_meta.filename}")
    except Exception as e:
        print(f"✗ Failed to encrypt {doc_meta.filename}: {e}")
```

## Compliance and Regulatory Notes

- **HIPAA**: Encryption meets HIPAA requirements for protected health information (PHI)
- **GDPR**: Supports GDPR's right to erasure with encrypted data deletion
- **PCI-DSS**: AES-256 encryption meets PCI-DSS requirements for payment card data
- **SOC 2**: Encryption supports SOC 2 Type II compliance

## Additional Resources

- [NIST Cryptographic Standards](https://csrc.nist.gov/)
- [OWASP Cryptographic Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
- [Python cryptography library](https://cryptography.io/)
- [X.509 Certificate Standard](https://en.wikipedia.org/wiki/X.509)
