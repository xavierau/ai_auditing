#!/usr/bin/env python3
"""Generate secure keys for GenReport application.

This script generates:
1. SECRET_KEY - Random 64-character hex string for app security
2. JWT_SECRET_KEY - Random 64-character hex string for JWT signing
3. ENCRYPTION_KEY - Fernet-compatible base64-encoded key for field encryption

Usage:
    python scripts/generate_keys.py

Output:
    Displays the generated keys in .env format
"""

import secrets
from cryptography.fernet import Fernet


def generate_secret_key(length: int = 64) -> str:
    """Generate a secure random hex string.

    Args:
        length: Length of the hex string (default: 64 characters)

    Returns:
        Random hex string suitable for SECRET_KEY or JWT_SECRET_KEY
    """
    return secrets.token_hex(length // 2)


def generate_encryption_key() -> str:
    """Generate a Fernet-compatible encryption key.

    Returns:
        Base64-encoded 32-byte key suitable for Fernet encryption
    """
    return Fernet.generate_key().decode()


def main():
    """Generate and display all required keys."""
    print("=" * 80)
    print("GenReport Security Keys Generator")
    print("=" * 80)
    print()
    print("⚠️  SECURITY WARNING:")
    print("   - Keep these keys secret and never commit them to version control")
    print("   - Use different keys for development, staging, and production")
    print("   - Store production keys in a secure secrets manager (e.g., AWS Secrets Manager)")
    print()
    print("=" * 80)
    print()

    # Generate keys
    secret_key = generate_secret_key(64)
    jwt_secret_key = generate_secret_key(64)
    encryption_key = generate_encryption_key()

    # Display in .env format
    print("# Copy these to your .env file:")
    print()
    print(f"SECRET_KEY={secret_key}")
    print(f"JWT_SECRET_KEY={jwt_secret_key}")
    print(f"ENCRYPTION_KEY={encryption_key}")
    print()
    print("=" * 80)
    print()
    print("✅ Keys generated successfully!")
    print()
    print("Next steps:")
    print("1. Copy the keys above to your .env file")
    print("2. Remove the placeholder keys from .env")
    print("3. Never commit .env to version control")
    print("4. Generate different keys for each environment (dev/staging/prod)")
    print()


if __name__ == "__main__":
    main()
