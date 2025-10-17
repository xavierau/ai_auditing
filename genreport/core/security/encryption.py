"""Encryption service for field-level encryption and file encryption."""

import base64
from typing import Dict, Optional

from cryptography.fernet import Fernet
from sqlalchemy import String, TypeDecorator

from genreport.core.utils.config import settings


class EncryptionService:
    """Handles field-level and file encryption with tenant-specific keys.

    SECURITY: Uses Fernet (symmetric encryption) with keys managed by KMS.
    Each tenant can have its own encryption key for data isolation.
    """

    def __init__(self):
        """Initialize encryption service with KMS client (placeholder for now)."""
        self.kms_client = None  # TODO: Initialize AWS KMS client
        self._cipher_cache: Dict[str, Fernet] = {}
        self._default_key = settings.encryption_key

    def get_cipher(self, tenant_id: Optional[str] = None) -> Fernet:
        """Get Fernet cipher for encryption/decryption.

        Args:
            tenant_id: Optional tenant ID for tenant-specific key.
                      If None, uses default encryption key.

        Returns:
            Fernet cipher instance
        """
        # Use default key if no tenant specified
        if not tenant_id:
            cache_key = "default"
        else:
            cache_key = tenant_id

        # Return cached cipher if available
        if cache_key in self._cipher_cache:
            return self._cipher_cache[cache_key]

        # Get encryption key
        if tenant_id:
            key = self._get_key_from_kms(tenant_id)
        else:
            key = base64.urlsafe_b64decode(self._default_key.encode())

        # Create and cache cipher
        cipher = Fernet(key)
        self._cipher_cache[cache_key] = cipher
        return cipher

    def _get_key_from_kms(self, tenant_id: str) -> bytes:
        """Retrieve tenant-specific encryption key from KMS.

        TODO: Implement actual KMS integration
        For now, uses the default key for all tenants.

        Args:
            tenant_id: Tenant ID to retrieve key for

        Returns:
            Encryption key as bytes
        """
        # TODO: Implement AWS KMS integration
        # Example implementation:
        # response = self.kms_client.decrypt(
        #     CiphertextBlob=encrypted_key,
        #     KeyId=settings.aws_kms_key_id
        # )
        # return response['Plaintext']

        # Placeholder: Use default key for all tenants
        return base64.urlsafe_b64decode(self._default_key.encode())

    def encrypt(self, value: str, tenant_id: Optional[str] = None) -> str:
        """Encrypt a string value.

        Args:
            value: Plain text value to encrypt
            tenant_id: Optional tenant ID for tenant-specific key

        Returns:
            Base64-encoded encrypted value
        """
        if not value:
            return value

        cipher = self.get_cipher(tenant_id)
        encrypted = cipher.encrypt(value.encode())
        return base64.b64encode(encrypted).decode()

    def decrypt(self, value: str, tenant_id: Optional[str] = None) -> str:
        """Decrypt an encrypted value.

        Args:
            value: Base64-encoded encrypted value
            tenant_id: Optional tenant ID for tenant-specific key

        Returns:
            Decrypted plain text value
        """
        if not value:
            return value

        cipher = self.get_cipher(tenant_id)
        encrypted = base64.b64decode(value.encode())
        return cipher.decrypt(encrypted).decode()

    def encrypt_file(self, file_content: bytes, tenant_id: Optional[str] = None) -> bytes:
        """Encrypt file content.

        Args:
            file_content: File content as bytes
            tenant_id: Optional tenant ID for tenant-specific key

        Returns:
            Encrypted file content
        """
        if not file_content:
            return file_content

        cipher = self.get_cipher(tenant_id)
        return cipher.encrypt(file_content)

    def decrypt_file(self, encrypted_content: bytes, tenant_id: Optional[str] = None) -> bytes:
        """Decrypt file content.

        Args:
            encrypted_content: Encrypted file content
            tenant_id: Optional tenant ID for tenant-specific key

        Returns:
            Decrypted file content
        """
        if not encrypted_content:
            return encrypted_content

        cipher = self.get_cipher(tenant_id)
        return cipher.decrypt(encrypted_content)


# Global encryption service instance
encryption_service = EncryptionService()


class EncryptedString(TypeDecorator):
    """SQLAlchemy type decorator for automatic field-level encryption.

    Usage:
        class User(Base):
            ssn = Column(EncryptedString(255))

    SECURITY: Automatically encrypts on write and decrypts on read.
    Uses tenant context to determine encryption key.
    """

    impl = String
    cache_ok = True

    def __init__(self, *args, **kwargs):
        """Initialize with underlying String type."""
        super().__init__(*args, **kwargs)
        self._encryption_service = encryption_service

    def process_bind_param(self, value, dialect):
        """Encrypt value when writing to database.

        Args:
            value: Plain text value
            dialect: SQL dialect (unused)

        Returns:
            Encrypted value
        """
        if value is not None:
            try:
                from genreport.core.security.tenant_context import current_tenant

                tenant_id = current_tenant.get()
                tenant_id_str = str(tenant_id) if tenant_id else None
                return self._encryption_service.encrypt(value, tenant_id_str)
            except Exception:
                # Fallback to no tenant context (e.g., in migrations)
                return self._encryption_service.encrypt(value, None)
        return value

    def process_result_value(self, value, dialect):
        """Decrypt value when reading from database.

        Args:
            value: Encrypted value
            dialect: SQL dialect (unused)

        Returns:
            Decrypted plain text value
        """
        if value is not None:
            try:
                from genreport.core.security.tenant_context import current_tenant

                tenant_id = current_tenant.get()
                tenant_id_str = str(tenant_id) if tenant_id else None
                return self._encryption_service.decrypt(value, tenant_id_str)
            except Exception:
                # Fallback to no tenant context (e.g., in migrations)
                return self._encryption_service.decrypt(value, None)
        return value


def generate_encryption_key() -> str:
    """Generate a new Fernet encryption key.

    Returns:
        Base64-encoded encryption key

    Example:
        >>> key = generate_encryption_key()
        >>> print(f"ENCRYPTION_KEY={key}")
    """
    return Fernet.generate_key().decode()
