"""File encryption service for uploaded documents.

SECURITY: Uses Fernet symmetric encryption with tenant-specific keys.
All files are encrypted at rest with separate keys per tenant.
"""

from typing import Optional
from uuid import UUID

from genreport.core.security.encryption import EncryptionService


class FileEncryptionService:
    """Handles file encryption for uploaded documents.

    SECURITY: Uses tenant-specific encryption keys from KMS.
    Files are encrypted at rest with Fernet symmetric encryption.

    ARCHITECTURE: Facade over EncryptionService for file-specific operations.
    """

    def __init__(self, encryption_service: EncryptionService):
        """Initialize with encryption service dependency.

        Args:
            encryption_service: Base encryption service instance

        SOLID: Dependency injection (DIP - depends on abstraction)
        """
        self.encryption_service = encryption_service

    def encrypt_file(self, file_content: bytes, tenant_id: Optional[str] = None) -> bytes:
        """Encrypt file content using tenant-specific key.

        Args:
            file_content: File content as bytes
            tenant_id: Tenant ID for tenant-specific key (optional)

        Returns:
            Encrypted file content

        SECURITY: Uses Fernet encryption which provides:
        - Authenticated encryption (HMAC for integrity)
        - Timestamp (for key rotation)
        - Unique IV per encryption (prevents pattern analysis)
        """
        return self.encryption_service.encrypt_file(file_content, tenant_id)

    def decrypt_file(
        self, encrypted_content: bytes, tenant_id: Optional[str] = None
    ) -> bytes:
        """Decrypt file content using tenant-specific key.

        Args:
            encrypted_content: Encrypted file content
            tenant_id: Tenant ID for tenant-specific key (optional)

        Returns:
            Decrypted file content

        Raises:
            cryptography.fernet.InvalidToken: If ciphertext is tampered or wrong key
        """
        return self.encryption_service.decrypt_file(encrypted_content, tenant_id)

    def get_encrypted_file_path(
        self, tenant_id: UUID, project_id: int, file_id: UUID
    ) -> str:
        """Generate secure storage path with tenant isolation.

        Args:
            tenant_id: Tenant UUID
            project_id: Project ID
            file_id: File UUID

        Returns:
            Storage path in format: encrypted/{tenant_id}/{project_id}/{file_id}.enc

        SECURITY:
        - Tenant isolation at filesystem level
        - Prevents path traversal (UUIDs don't contain special chars)
        - .enc extension indicates encrypted file
        """
        return f"encrypted/{tenant_id}/{project_id}/{file_id}.enc"
