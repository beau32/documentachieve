"""
Example and test code for encryption functionality.

This module demonstrates how to use the encryption service and shows
examples of encrypting documents and metadata.

Usage:
    python examples_encryption.py
    python -m pytest examples_encryption.py -v
"""

import asyncio
import base64
from pathlib import Path
from app.encryption_service import (
    EncryptionConfig, 
    EncryptionService, 
    generate_test_keys
)


def example_1_generate_keys():
    """Example 1: Generate test keys."""
    print("\n" + "="*60)
    print("Example 1: Generate Test Keys")
    print("="*60)
    
    cert_path, key_path = generate_test_keys(output_dir="./test_certs")
    
    print(f"✓ Certificate created: {cert_path}")
    print(f"✓ Private key created: {key_path}")
    
    return cert_path, key_path


def example_2_create_encryption_service(cert_path: str, key_path: str):
    """Example 2: Create and initialize encryption service."""
    print("\n" + "="*60)
    print("Example 2: Create Encryption Service")
    print("="*60)
    
    # Create encryption config
    config = EncryptionConfig(
        enabled=True,
        certificate_path=cert_path,
        private_key_path=key_path,
        algorithm="RSA"
    )
    
    print(f"✓ Configuration created")
    print(f"  - Enabled: {config.enabled}")
    print(f"  - Algorithm: {config.algorithm}")
    print(f"  - Public key loaded: {config.public_key is not None}")
    print(f"  - Private key loaded: {config.private_key is not None}")
    
    # Create service
    service = EncryptionService(config)
    print(f"✓ Encryption service created")
    
    return service


def example_3_encrypt_decrypt(service: EncryptionService):
    """Example 3: Encrypt and decrypt data."""
    print("\n" + "="*60)
    print("Example 3: Encrypt and Decrypt Data")
    print("="*60)
    
    # Original data
    original_data = b"This is a confidential document content"
    associated_data = b"document_id_12345"
    
    print(f"Original data: {original_data.decode()}")
    print(f"Associated data (authenticated): {associated_data.decode()}")
    
    # Encrypt
    print("\nEncrypting...")
    encrypted, key_material, tag = service.encrypt_data(original_data, associated_data)
    
    print(f"✓ Encrypted successfully")
    print(f"  - Ciphertext size: {len(encrypted)} bytes")
    print(f"  - Key material size: {len(key_material)} bytes")
    print(f"  - Authentication tag: {tag.hex()[:32]}...")
    
    # Decrypt
    print("\nDecrypting...")
    decrypted = service.decrypt_data(encrypted, key_material, tag, associated_data)
    
    print(f"✓ Decrypted successfully")
    print(f"Decrypted data: {decrypted.decode()}")
    
    # Verify
    assert decrypted == original_data
    print(f"✓ Verification passed - data matches!")
    
    return encrypted, key_material, tag


def example_4_encrypt_file(service: EncryptionService):
    """Example 4: Encrypt file content."""
    print("\n" + "="*60)
    print("Example 4: Encrypt File Content")
    print("="*60)
    
    # Create sample file
    sample_file = Path("./sample_document.txt")
    sample_content = b"""
    CONFIDENTIAL DOCUMENT
    
    This is a sample document that contains sensitive information.
    It will be encrypted before being stored in the cloud.
    
    Document ID: DOC-2026-00123
    Author: John Doe
    Classification: Confidential
    """
    
    with open(sample_file, "wb") as f:
        f.write(sample_content)
    
    print(f"✓ Sample file created: {sample_file}")
    print(f"  File size: {len(sample_content)} bytes")
    
    # Read file
    with open(sample_file, "rb") as f:
        file_data = f.read()
    
    # Encrypt with file name as associated data
    print("\nEncrypting file...")
    encrypted, key_material, tag = service.encrypt_data(
        file_data,
        associated_data=str(sample_file).encode()
    )
    
    print(f"✓ File encrypted")
    print(f"  Original size: {len(file_data)} bytes")
    print(f"  Encrypted size: {len(encrypted)} bytes")
    
    # Save encrypted file
    encrypted_file = Path("./sample_document.enc")
    with open(encrypted_file, "wb") as f:
        f.write(encrypted)
    
    print(f"✓ Encrypted file saved: {encrypted_file}")
    
    # Decrypt
    print("\nDecrypting file...")
    decrypted = service.decrypt_data(
        encrypted,
        key_material,
        tag,
        associated_data=str(sample_file).encode()
    )
    
    # Verify
    assert decrypted == file_data
    print(f"✓ Decryption successful - file verified!")
    
    # Cleanup
    sample_file.unlink()
    encrypted_file.unlink()
    print(f"✓ Cleanup complete")


def example_5_encrypt_metadata():
    """Example 5: Encrypt document metadata."""
    print("\n" + "="*60)
    print("Example 5: Encrypt Document Metadata")
    print("="*60)
    
    import json
    from app.config import settings
    
    # Get encryption service (if enabled)
    if settings.encryption_enabled:
        from app.encryption_service import get_encryption_service
        service = get_encryption_service()
        
        # Sample metadata
        metadata = {
            "author": "Jane Smith",
            "department": "Finance",
            "classification": "Confidential",
            "tags": {
                "project": "Q1-2026-Budget",
                "sensitivity": "high"
            }
        }
        
        metadata_json = json.dumps(metadata).encode()
        document_id = b"doc_2026_001"
        
        print(f"Original metadata: {metadata}")
        
        # Encrypt metadata
        print("\nEncrypting metadata...")
        encrypted, key_material, tag = service.encrypt_data(
            metadata_json,
            associated_data=document_id
        )
        
        print(f"✓ Metadata encrypted")
        print(f"  Original size: {len(metadata_json)} bytes")
        print(f"  Encrypted size: {len(encrypted)} bytes")
        
        # Decrypt metadata
        print("\nDecrypting metadata...")
        decrypted = service.decrypt_data(
            encrypted,
            key_material,
            tag,
            associated_data=document_id
        )
        
        restored_metadata = json.loads(decrypted.decode())
        
        print(f"✓ Metadata decrypted")
        print(f"Restored metadata: {restored_metadata}")
        
        # Verify
        assert restored_metadata == metadata
        print(f"✓ Verification passed!")
    else:
        print("⚠ Encryption not enabled in settings")


def example_6_error_handling(service: EncryptionService):
    """Example 6: Error handling and validation."""
    print("\n" + "="*60)
    print("Example 6: Error Handling")
    print("="*60)
    
    # Test 1: Decrypt with wrong associated data
    print("\nTest 1: Decrypt with wrong associated data")
    
    data = b"Secret message"
    correct_assoc = b"correct_id"
    wrong_assoc = b"wrong_id"
    
    encrypted, key, tag = service.encrypt_data(data, correct_assoc)
    
    try:
        # Try to decrypt with wrong associated data
        decrypted = service.decrypt_data(encrypted, key, tag, wrong_assoc)
        print("✗ Should have failed with wrong associated data!")
    except Exception as e:
        print(f"✓ Correctly failed with wrong associated data")
        print(f"  Error: {type(e).__name__}")
    
    # Test 2: Decrypt with corrupted ciphertext
    print("\nTest 2: Decrypt with corrupted ciphertext")
    
    corrupted = bytes([encrypted[0] ^ 0xFF]) + encrypted[1:]
    
    try:
        decrypted = service.decrypt_data(corrupted, key, tag, correct_assoc)
        print("✗ Should have failed with corrupted data!")
    except Exception as e:
        print(f"✓ Correctly failed with corrupted data")
        print(f"  Error: {type(e).__name__}")
    
    # Test 3: Encrypt/decrypt with various data sizes
    print("\nTest 3: Various data sizes")
    
    for size in [1, 100, 1024, 1024*10]:
        test_data = b"x" * size
        encrypted, key, tag = service.encrypt_data(test_data)
        decrypted = service.decrypt_data(encrypted, key, tag)
        
        assert decrypted == test_data
        print(f"✓ {size:6d} bytes - OK")


def example_7_base64_encoding(service: EncryptionService):
    """Example 7: Base64 encoding for API serialization."""
    print("\n" + "="*60)
    print("Example 7: Base64 Encoding for Storage/API")
    print("="*60)
    
    # Original binary data
    original = b"Binary encrypted content"
    print(f"Original: {original}")
    
    # Encrypt
    encrypted, key_material, tag = service.encrypt_data(original)
    
    print(f"\nEncrypted (binary):")
    print(f"  Ciphertext size: {len(encrypted)} bytes")
    print(f"  Key material size: {len(key_material)} bytes")
    print(f"  Tag size: {len(tag)} bytes")
    
    # For database storage, convert to base64 or hex
    print(f"\nBase64 encoded (for storage/API):")
    encrypted_b64 = base64.b64encode(encrypted).decode("utf-8")
    key_b64 = base64.b64encode(key_material).decode("utf-8")
    tag_b64 = base64.b64encode(tag).decode("utf-8")
    
    print(f"  Ciphertext: {encrypted_b64[:50]}...")
    print(f"  Key material: {key_b64[:50]}...")
    print(f"  Tag: {tag_b64}")
    
    # Decrypt from base64
    print(f"\nDecrypting from base64...")
    encrypted_decoded = base64.b64decode(encrypted_b64)
    key_decoded = base64.b64decode(key_b64)
    tag_decoded = base64.b64decode(tag_b64)
    
    decrypted = service.decrypt_data(encrypted_decoded, key_decoded, tag_decoded)
    
    print(f"Decrypted: {decrypted}")
    assert decrypted == original
    print(f"✓ Base64 encoding/decoding verified!")


def example_8_database_storage(service: EncryptionService):
    """Example 8: Storing encrypted data in database."""
    print("\n" + "="*60)
    print("Example 8: Database Storage Pattern")
    print("="*60)
    
    import base64
    
    # Simulate database record creation
    document_id = "doc_12345"
    filename = "confidential.pdf"
    metadata = {"author": "John", "department": "Finance"}
    
    # Encrypt metadata
    import json
    metadata_bytes = json.dumps(metadata).encode()
    encrypted, key_material, tag = service.encrypt_data(
        metadata_bytes,
        associated_data=document_id.encode()
    )
    
    # Create database record (simulated)
    db_record = {
        "document_id": document_id,
        "filename": filename,
        "is_encrypted": "true",
        "encryption_algorithm": "RSA",
        "encryption_iv_or_key": base64.b64encode(key_material).decode(),
        "encryption_tag": base64.b64encode(tag).decode(),
        "metadata_encrypted": "true",
        "metadata_json": base64.b64encode(encrypted).decode(),
    }
    
    print("Database record structure:")
    for key, value in db_record.items():
        if isinstance(value, str) and len(value) > 50:
            print(f"  {key}: {value[:50]}...")
        else:
            print(f"  {key}: {value}")
    
    # Retrieve and decrypt from database
    print("\nRetrieving and decrypting...")
    encrypted_meta = base64.b64decode(db_record["metadata_json"])
    key_material_stored = base64.b64decode(db_record["encryption_iv_or_key"])
    tag_stored = base64.b64decode(db_record["encryption_tag"])
    
    decrypted_meta = service.decrypt_data(
        encrypted_meta,
        key_material_stored,
        tag_stored,
        associated_data=document_id.encode()
    )
    
    restored_metadata = json.loads(decrypted_meta.decode())
    
    print(f"✓ Decrypted metadata: {restored_metadata}")
    assert restored_metadata == metadata
    print(f"✓ Database storage pattern verified!")


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("Cloud Document Archive - Encryption Examples")
    print("="*60)
    
    try:
        # Generate keys
        cert_path, key_path = example_1_generate_keys()
        
        # Create service
        service = example_2_create_encryption_service(cert_path, key_path)
        
        # Basic encryption/decryption
        example_3_encrypt_decrypt(service)
        
        # File encryption
        example_4_encrypt_file(service)
        
        # Metadata encryption
        example_5_encrypt_metadata()
        
        # Error handling
        example_6_error_handling(service)
        
        # Base64 encoding
        example_7_base64_encoding(service)
        
        # Database storage
        example_8_database_storage(service)
        
        print("\n" + "="*60)
        print("✓ All examples completed successfully!")
        print("="*60 + "\n")
        
        return 0
    
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
