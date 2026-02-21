#!/usr/bin/env python
"""
Script to generate encryption certificates for the Cloud Document Archive.

This script generates self-signed X.509 certificates and RSA keys for development
and testing purposes. For production, use certificates from a trusted Certificate Authority.

Usage:
    python generate_encryption_keys.py
    python generate_encryption_keys.py --output-dir /path/to/certs --key-size 4096
"""

import argparse
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend
except ImportError:
    print("Error: cryptography library not installed")
    print("Install it with: pip install cryptography")
    sys.exit(1)


def generate_keys(
    output_dir: str = "./certs",
    key_size: int = 4096,
    days_valid: int = 365,
    encrypt_key: bool = False,
    key_password: str = None,
    interactive: bool = True
):
    """
    Generate RSA key pair and self-signed X.509 certificate.
    
    Args:
        output_dir: Directory to save generated files
        key_size: RSA key size (2048, 4096, or 8192 bits)
        days_valid: Number of days the certificate is valid
        encrypt_key: Whether to encrypt the private key
        key_password: Password for encrypted private key
        interactive: Ask for certificate details interactively
        
    Returns:
        Tuple of (certificate_path, private_key_path)
    """
    # Validate key size
    if key_size not in [2048, 4096, 8192]:
        raise ValueError("Key size must be 2048, 4096, or 8192 bits")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n{'='*60}")
    print("Cloud Document Archive - Encryption Certificate Generator")
    print(f"{'='*60}\n")
    
    # Get certificate details
    if interactive:
        print("Enter certificate details (press Enter for defaults):")
        country = input("Country [US]: ").strip() or "US"
        state = input("State/Province [California]: ").strip() or "California"
        locality = input("City [San Francisco]: ").strip() or "San Francisco"
        org = input("Organization [Cloud Archive Inc]: ").strip() or "Cloud Archive Inc"
        common_name = input("Common Name [archive.local]: ").strip() or "archive.local"
    else:
        country = "US"
        state = "California"
        locality = "San Francisco"
        org = "Cloud Archive Inc"
        common_name = "archive.local"
    
    print(f"\nGenerating {key_size}-bit RSA key pair...")
    
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend()
    )
    
    print("✓ Private key generated")
    
    # Create certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, country),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, state),
        x509.NameAttribute(NameOID.LOCALITY_NAME, locality),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, org),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])
    
    print("Generating self-signed certificate...")
    
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
        datetime.utcnow() + timedelta(days=days_valid)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName(common_name),
            x509.DNSName("localhost"),
            x509.DNSName("127.0.0.1"),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256(), default_backend())
    
    print("✓ Certificate generated")
    
    # Save certificate
    cert_path = os.path.join(output_dir, "certificate.pem")
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    os.chmod(cert_path, 0o644)
    print(f"✓ Certificate saved: {cert_path}")
    
    # Save private key
    key_path = os.path.join(output_dir, "private_key.pem")
    
    if encrypt_key and key_password:
        encryption = serialization.BestAvailableEncryption(key_password.encode())
        print(f"Encrypting private key with password...")
    else:
        encryption = serialization.NoEncryption()
    
    with open(key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption
        ))
    
    os.chmod(key_path, 0o600)
    print(f"✓ Private key saved: {key_path}")
    
    # Display certificate info
    print(f"\n{'='*60}")
    print("Certificate Information")
    print(f"{'='*60}")
    print(f"Subject: {cert.subject.rfc4514_string()}")
    print(f"Issuer: {cert.issuer.rfc4514_string()}")
    print(f"Serial Number: {cert.serial_number}")
    print(f"Not Valid Before: {cert.not_valid_before}")
    print(f"Not Valid After: {cert.not_valid_after}")
    print(f"Key Size: {key_size} bits")
    print(f"Public Key Algorithm: {cert.public_key_algorithm}")
    print(f"Signature Algorithm: {cert.signature_algorithm_oid._name}")
    
    print(f"\n{'='*60}")
    print("Configuration")
    print(f"{'='*60}")
    print("\nAdd to config.yaml:")
    config = f"""
encryption:
  enabled: true
  algorithm: RSA
  certificate_path: {cert_path}
  private_key_path: {key_path}"""
    
    if encrypt_key and key_password:
        config += f"\n  key_password: {key_password}"
    
    print(config)
    
    print(f"\nOr set environment variables:")
    env = f"""
export ENCRYPTION_ENABLED=true
export ENCRYPTION_ALGORITHM=RSA
export ENCRYPTION_CERTIFICATE_PATH={cert_path}
export ENCRYPTION_PRIVATE_KEY_PATH={key_path}"""
    
    if encrypt_key and key_password:
        env += f"\nexport ENCRYPTION_KEY_PASSWORD={key_password}"
    
    print(env)
    
    print(f"\n{'='*60}")
    print("Security Notes")
    print(f"{'='*60}")
    print(f"✓ Certificate is public (644): {cert_path}")
    print(f"✓ Private key is restricted (600): {key_path}")
    print("⚠  Keep the private key secure!")
    print("⚠  Do NOT commit private key to version control!")
    print("⚠  For production, use certificates from a trusted CA!")
    
    print(f"\n{'='*60}\n")
    
    return cert_path, key_path


def verify_certificate(cert_path: str, key_path: str):
    """
    Verify that certificate and private key match.
    
    Args:
        cert_path: Path to certificate file
        key_path: Path to private key file
    """
    try:
        # Load certificate
        with open(cert_path, "rb") as f:
            cert_data = f.read()
        from cryptography.x509 import load_pem_x509_certificate
        cert = load_pem_x509_certificate(cert_data, default_backend())
        
        # Load private key
        with open(key_path, "rb") as f:
            key_data = f.read()
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
        private_key = load_pem_private_key(key_data, password=None, backend=default_backend())
        
        # Compare public keys
        cert_public = cert.public_key()
        key_public = private_key.public_key()
        
        cert_numbers = cert_public.public_numbers()
        key_numbers = key_public.public_numbers()
        
        if (cert_numbers.n == key_numbers.n and 
            cert_numbers.e == key_numbers.e):
            print("✓ Certificate and private key match!")
            return True
        else:
            print("✗ Certificate and private key do NOT match!")
            return False
    
    except Exception as e:
        print(f"✗ Error verifying certificate: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate encryption certificates for Cloud Document Archive"
    )
    parser.add_argument(
        "--output-dir",
        default="./certs",
        help="Directory to save certificates (default: ./certs)"
    )
    parser.add_argument(
        "--key-size",
        type=int,
        default=4096,
        choices=[2048, 4096, 8192],
        help="RSA key size in bits (default: 4096)"
    )
    parser.add_argument(
        "--days-valid",
        type=int,
        default=365,
        help="Days the certificate is valid (default: 365)"
    )
    parser.add_argument(
        "--encrypt-key",
        action="store_true",
        help="Encrypt private key with password"
    )
    parser.add_argument(
        "--key-password",
        help="Password for encrypted private key"
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Use default certificate details without prompting"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify existing certificate and key"
    )
    
    args = parser.parse_args()
    
    try:
        if args.verify:
            # Verify mode
            cert_path = os.path.join(args.output_dir, "certificate.pem")
            key_path = os.path.join(args.output_dir, "private_key.pem")
            
            if not os.path.exists(cert_path) or not os.path.exists(key_path):
                print(f"✗ Certificate or key not found in {args.output_dir}")
                sys.exit(1)
            
            verify_certificate(cert_path, key_path)
        else:
            # Generate mode
            if args.encrypt_key and not args.key_password:
                # Prompt for password
                import getpass
                args.key_password = getpass.getpass("Enter password for private key: ")
                confirm = getpass.getpass("Confirm password: ")
                if args.key_password != confirm:
                    print("✗ Passwords do not match!")
                    sys.exit(1)
            
            cert_path, key_path = generate_keys(
                output_dir=args.output_dir,
                key_size=args.key_size,
                days_valid=args.days_valid,
                encrypt_key=args.encrypt_key,
                key_password=args.key_password,
                interactive=not args.non_interactive
            )
            
            # Verify the generated files
            verify_certificate(cert_path, key_path)
    
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
