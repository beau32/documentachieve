"""Encryption service for securing document files and database entries."""

import logging
import os
from typing import Optional, Tuple
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

logger = logging.getLogger(__name__)


class EncryptionConfig:
    """Configuration for encryption settings."""
    
    def __init__(
        self,
        enabled: bool = False,
        certificate_path: Optional[str] = None,
        private_key_path: Optional[str] = None,
        key_password: Optional[str] = None,
        algorithm: str = "AES-256-GCM"
    ):
        """
        Initialize encryption configuration.
        
        Args:
            enabled: Whether encryption is enabled
            certificate_path: Path to public certificate (X.509)
            private_key_path: Path to private key
            key_password: Password for encrypted private key
            algorithm: Encryption algorithm (AES-256-GCM or RSA)
        """
        self.enabled = enabled
        self.certificate_path = certificate_path
        self.private_key_path = private_key_path
        self.key_password = key_password
        self.algorithm = algorithm
        self._public_key = None
        self._private_key = None
        
        if self.enabled:
            self._load_keys()
    
    def _load_keys(self):
        """Load public and private keys from certificate and key files."""
        if self.certificate_path and os.path.exists(self.certificate_path):
            try:
                with open(self.certificate_path, "rb") as f:
                    cert_data = f.read()
                
                # Try to load as PEM certificate
                try:
                    from cryptography.x509 import load_pem_x509_certificate
                    cert = load_pem_x509_certificate(cert_data, default_backend())
                    self._public_key = cert.public_key()
                    logger.info(f"Loaded public key from certificate: {self.certificate_path}")
                except Exception:
                    # Try loading as PEM public key
                    self._public_key = serialization.load_pem_public_key(
                        cert_data,
                        backend=default_backend()
                    )
                    logger.info(f"Loaded public key from file: {self.certificate_path}")
            except Exception as e:
                logger.error(f"Failed to load certificate: {e}")
                raise
        
        if self.private_key_path and os.path.exists(self.private_key_path):
            try:
                with open(self.private_key_path, "rb") as f:
                    key_data = f.read()
                
                password = self.key_password.encode() if self.key_password else None
                self._private_key = serialization.load_pem_private_key(
                    key_data,
                    password=password,
                    backend=default_backend()
                )
                logger.info(f"Loaded private key from file: {self.private_key_path}")
            except Exception as e:
                logger.error(f"Failed to load private key: {e}")
                raise
    
    @property
    def public_key(self):
        """Get the public key."""
        return self._public_key
    
    @property
    def private_key(self):
        """Get the private key."""
        return self._private_key
    
    def is_valid(self) -> bool:
        """Check if configuration is valid for encryption/decryption."""
        if not self.enabled:
            return False
        
        if self.algorithm == "RSA":
            return self._public_key is not None
        else:  # AES
            return True  # Keys are generated on-demand


class EncryptionService:
    """Service for encrypting and decrypting document data."""
    
    def __init__(self, config: EncryptionConfig):
        """
        Initialize encryption service.
        
        Args:
            config: EncryptionConfig instance
        """
        self.config = config
        self.backend = default_backend()
    
    def encrypt_data(self, data: bytes, associated_data: Optional[bytes] = None) -> Tuple[bytes, bytes, bytes]:
        """
        Encrypt data using configured algorithm.
        
        For RSA: Encrypts an AES key with RSA, then uses AES-256-GCM for data.
        For AES: Uses AES-256-GCM directly.
        
        Args:
            data: Data to encrypt
            associated_data: Optional authenticated data (e.g., document_id, filename)
            
        Returns:
            Tuple of (encrypted_data, iv, tag) for AES or (encrypted_data, encrypted_key, tag) for RSA
            
        Raises:
            ValueError: If encryption is not enabled or configured
        """
        if not self.config.enabled:
            raise ValueError("Encryption is not enabled")
        
        if self.config.algorithm == "RSA":
            return self._encrypt_with_rsa(data, associated_data)
        else:
            return self._encrypt_with_aes(data, associated_data)
    
    def decrypt_data(
        self,
        encrypted_data: bytes,
        iv_or_key: bytes,
        tag: bytes,
        associated_data: Optional[bytes] = None
    ) -> bytes:
        """
        Decrypt data using configured algorithm.
        
        Args:
            encrypted_data: Encrypted data
            iv_or_key: IV (for AES) or encrypted key (for RSA)
            tag: Authentication tag
            associated_data: Optional authenticated data used during encryption
            
        Returns:
            Decrypted data
            
        Raises:
            ValueError: If decryption fails or is not configured
        """
        if not self.config.enabled:
            raise ValueError("Encryption is not enabled")
        
        if self.config.algorithm == "RSA":
            return self._decrypt_with_rsa(encrypted_data, iv_or_key, tag, associated_data)
        else:
            return self._decrypt_with_aes(encrypted_data, iv_or_key, tag, associated_data)
    
    def _encrypt_with_aes(
        self,
        data: bytes,
        associated_data: Optional[bytes] = None
    ) -> Tuple[bytes, bytes, bytes]:
        """Encrypt using AES-256-GCM."""
        try:
            # Generate a random 256-bit key
            key = os.urandom(32)  # 256 bits
            
            # Generate a random 96-bit IV (12 bytes recommended for GCM)
            iv = os.urandom(12)
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(iv),
                backend=self.backend
            )
            encryptor = cipher.encryptor()
            
            # Add associated data if provided
            if associated_data:
                encryptor.authenticate_additional_data(associated_data)
            
            # Encrypt data
            ciphertext = encryptor.update(data) + encryptor.finalize()
            
            # Get the authentication tag
            tag = encryptor.tag
            
            logger.debug(f"Encrypted {len(data)} bytes with AES-256-GCM")
            
            return ciphertext, iv, tag
        
        except Exception as e:
            logger.error(f"AES encryption failed: {e}")
            raise
    
    def _decrypt_with_aes(
        self,
        encrypted_data: bytes,
        iv: bytes,
        tag: bytes,
        associated_data: Optional[bytes] = None
    ) -> bytes:
        """Decrypt using AES-256-GCM."""
        try:
            if not self.config.private_key:
                raise ValueError("Cannot decrypt: private key not available")
            
            # For AES-GCM, we need to recover the key from somewhere
            # In a real implementation, the key would be stored securely (e.g., in a key vault)
            # For now, we'll store the encrypted key with the data
            # This is handled in the storage providers
            
            raise NotImplementedError(
                "Direct AES decryption requires secure key storage. "
                "Use RSA-wrapped AES keys for production."
            )
        
        except Exception as e:
            logger.error(f"AES decryption failed: {e}")
            raise
    
    def _encrypt_with_rsa(
        self,
        data: bytes,
        associated_data: Optional[bytes] = None
    ) -> Tuple[bytes, bytes, bytes]:
        """Encrypt using hybrid RSA+AES approach."""
        try:
            if not self.config.public_key:
                raise ValueError("Cannot encrypt: public key not available")
            
            # Generate AES key for symmetric encryption
            aes_key = os.urandom(32)  # 256 bits
            iv = os.urandom(12)  # 96 bits for GCM
            
            # Encrypt the AES key with RSA public key
            encrypted_aes_key = self.config.public_key.encrypt(
                aes_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # Encrypt data with AES-256-GCM
            cipher = Cipher(
                algorithms.AES(aes_key),
                modes.GCM(iv),
                backend=self.backend
            )
            encryptor = cipher.encryptor()
            
            if associated_data:
                encryptor.authenticate_additional_data(associated_data)
            
            ciphertext = encryptor.update(data) + encryptor.finalize()
            tag = encryptor.tag
            
            # Return: (ciphertext, encrypted_aes_key)
            # IV will be prepended to encrypted_aes_key for storage
            combined_key = iv + encrypted_aes_key
            
            logger.debug(f"Encrypted {len(data)} bytes with RSA+AES-256-GCM")
            
            return ciphertext, combined_key, tag
        
        except Exception as e:
            logger.error(f"RSA encryption failed: {e}")
            raise
    
    def _decrypt_with_rsa(
        self,
        encrypted_data: bytes,
        combined_key: bytes,
        tag: bytes,
        associated_data: Optional[bytes] = None
    ) -> bytes:
        """Decrypt using hybrid RSA+AES approach."""
        try:
            if not self.config.private_key:
                raise ValueError("Cannot decrypt: private key not available")
            
            # Extract IV and encrypted AES key
            iv = combined_key[:12]  # First 12 bytes are IV
            encrypted_aes_key = combined_key[12:]
            
            # Decrypt AES key with RSA private key
            aes_key = self.config.private_key.decrypt(
                encrypted_aes_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # Decrypt data with AES-256-GCM
            cipher = Cipher(
                algorithms.AES(aes_key),
                modes.GCM(iv, tag),
                backend=self.backend
            )
            decryptor = cipher.decryptor()
            
            if associated_data:
                decryptor.authenticate_additional_data(associated_data)
            
            plaintext = decryptor.update(encrypted_data) + decryptor.finalize()
            
            logger.debug(f"Decrypted {len(encrypted_data)} bytes with RSA+AES-256-GCM")
            
            return plaintext
        
        except Exception as e:
            logger.error(f"RSA decryption failed: {e}")
            raise


def generate_test_keys(output_dir: str = "./certs"):
    """
    Generate test RSA key pair for development/testing.
    
    Args:
        output_dir: Directory to save certificate and key files
    """
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=default_backend()
        )
        
        # Generate self-signed certificate
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from datetime import datetime, timedelta
        
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"State"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, u"City"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Cloud Document Archive"),
            x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)
        ).sign(private_key, hashes.SHA256(), default_backend())
        
        # Save certificate
        cert_path = os.path.join(output_dir, "certificate.pem")
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        logger.info(f"Generated certificate: {cert_path}")
        
        # Save private key
        key_path = os.path.join(output_dir, "private_key.pem")
        with open(key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        logger.info(f"Generated private key: {key_path}")
        
        return cert_path, key_path
    
    except Exception as e:
        logger.error(f"Failed to generate test keys: {e}")
        raise


# Global encryption service instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """Get or create the global encryption service instance."""
    global _encryption_service
    
    if _encryption_service is None:
        from app.config import settings
        
        config = EncryptionConfig(
            enabled=settings.encryption_enabled,
            certificate_path=settings.encryption_certificate_path,
            private_key_path=settings.encryption_private_key_path,
            key_password=settings.encryption_key_password,
            algorithm=settings.encryption_algorithm
        )
        _encryption_service = EncryptionService(config)
    
    return _encryption_service


def reset_encryption_service():
    """Reset the global encryption service (useful for testing)."""
    global _encryption_service
    _encryption_service = None
