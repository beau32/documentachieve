# Quick Start: Configuring Encryption for Cloud Document Archive

This guide provides quick-start instructions for setting up encryption in the Cloud Document Archive.

## 5-Minute Setup

### 1. Generate Encryption Keys

```bash
# Generate self-signed certificate and private key
python generate_encryption_keys.py

# This creates:
# - ./certs/certificate.pem (public certificate)
# - ./certs/private_key.pem (private key - keep secure!)
```

### 2. Enable Encryption in Config

Create `config.yaml` with encryption enabled:

```yaml
encryption:
  enabled: true
  algorithm: RSA
  certificate_path: ./certs/certificate.pem
  private_key_path: ./certs/private_key.pem
```

Or set environment variables:

```bash
export ENCRYPTION_ENABLED=true
export ENCRYPTION_ALGORITHM=RSA
export ENCRYPTION_CERTIFICATE_PATH=./certs/certificate.pem
export ENCRYPTION_PRIVATE_KEY_PATH=./certs/private_key.pem
```

### 3. Restart Application

```bash
# Install dependencies
pip install -r requirements.txt

# Start the application
python -m uvicorn app.main:app --reload
```

### 4. Upload Documents with Encryption

```python
import requests
import base64

with open("document.pdf", "rb") as f:
    content = base64.b64encode(f.read()).decode()

response = requests.post(
    "http://localhost:8000/api/v1/archive",
    json={
        "document_base64": content,
        "filename": "document.pdf",
        "content_type": "application/pdf",
        "metadata": {"encrypt": "true"}
    }
)

print(response.json())
```

## Next Steps

For complete details, see [ENCRYPTION.md](ENCRYPTION.md)

### Key Topics to Review:

1. **Key Management**
   - How to generate production certificates
   - Where to store private keys
   - Key rotation strategies

2. **Security Best Practices**
   - Access control for private keys
   - Database encryption
   - Compliance requirements

3. **Troubleshooting**
   - Common errors and solutions
   - Performance tuning
   - Testing encryption

4. **Production Deployment**
   - Using certificates from trusted CAs
   - Kubernetes secrets integration
   - Cloud key management services

## Architecture

```
Document Upload
    ↓
[Optional Encryption]
    ↓
    ├─→ Cloud Storage (encrypted document)
    └─→ Database (encrypted metadata)
        ├─→ is_encrypted: true
        ├─→ encryption_algorithm: RSA
        ├─→ encryption_iv_or_key: [encrypted key]
        └─→ encryption_tag: [auth tag]
```

## Supported Algorithms

| Algorithm | Key Size | Best For |
|-----------|----------|----------|
| RSA | 2048-8192 bits | Production, distributed systems |
| AES-256-GCM | 256 bits | Development, single server |

## Key Features

✅ **Hybrid RSA+AES Encryption** - Secure key management  
✅ **Database Integration** - Metadata encryption  
✅ **X.509 Certificates** - Industry standard  
✅ **Transparent Operation** - Automatic encryption/decryption  
✅ **AEAD Authentication** - Integrity verification  

## Common Commands

Generate test keys:
```bash
python generate_encryption_keys.py --non-interactive
```

Generate production keys (4096-bit, encrypted):
```bash
python generate_encryption_keys.py --key-size 4096 --encrypt-key
```

Verify certificate and key:
```bash
python generate_encryption_keys.py --verify
```

## Troubleshooting

**Encryption not working?**
- Check file paths in config
- Verify key file permissions (private key: 600, certificate: 644)
- Ensure cryptography library is installed: `pip install cryptography`

**Performance issues?**
- Use 2048-bit keys instead of 4096
- Implement caching for frequently accessed documents
- Use HSM for cryptographic operations in production

## Support

For detailed documentation, see [ENCRYPTION.md](ENCRYPTION.md)

For issues, check:
1. Certificate paths are absolute or relative to app directory
2. Private key has restricted permissions (600)
3. cryptography library version >= 41.0.0
4. All required fields in config.yaml
