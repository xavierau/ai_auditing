"""Centralized audit logging for security events."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AuditLogger:
    """Centralized audit logging service.

    SECURITY: This class provides a unified interface for logging all
    security-relevant events. Audit logs are immutable and provide a
    complete trail of system access and modifications.

    Event Types:
        - AUTHENTICATION: Login, logout, token refresh
        - AUTHORIZATION: Permission checks, role changes
        - DATA_ACCESS: Read, query operations
        - DATA_MODIFICATION: Create, update, delete operations
        - FILE_OPERATION: Upload, download, delete files
        - SECURITY_VIOLATION: Failed auth, cross-tenant access attempts
        - SYSTEM: Configuration changes, migrations
    """

    # Event type constants
    AUTHENTICATION = "AUTHENTICATION"
    AUTHORIZATION = "AUTHORIZATION"
    DATA_ACCESS = "DATA_ACCESS"
    DATA_MODIFICATION = "DATA_MODIFICATION"
    FILE_OPERATION = "FILE_OPERATION"
    SECURITY_VIOLATION = "SECURITY_VIOLATION"
    SYSTEM = "SYSTEM"

    # Action constants
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    TOKEN_REFRESH = "TOKEN_REFRESH"
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    UPLOAD = "UPLOAD"
    DOWNLOAD = "DOWNLOAD"
    PERMISSION_CHECK = "PERMISSION_CHECK"
    CROSS_TENANT_ATTEMPT = "CROSS_TENANT_ATTEMPT"

    # Status constants
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"

    @staticmethod
    def log_event(
        db: Session,
        event_type: str,
        action: str,
        user_id: Optional[int] = None,
        tenant_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status: str = "SUCCESS",
    ) -> None:
        """Log a security event.

        Args:
            db: Database session
            event_type: Type of event (use class constants)
            action: Action performed (use class constants)
            user_id: ID of user who performed action
            tenant_id: Tenant ID for multi-tenant isolation
            resource_type: Type of resource affected (project, file, report, etc.)
            resource_id: ID of affected resource
            ip_address: IP address of requestor
            user_agent: User agent string
            details: Additional event details as JSON
            status: SUCCESS or FAILURE
        """
        try:
            from genreport.core.database.models import AuditLog

            audit_log = AuditLog(
                tenant_id=tenant_id,
                user_id=user_id,
                event_type=event_type,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details,
                status=status,
                created_at=datetime.utcnow(),
            )

            db.add(audit_log)
            db.commit()

            # Also log to application logger for real-time monitoring
            log_message = (
                f"AUDIT: {event_type}.{action} - "
                f"user={user_id} tenant={tenant_id} "
                f"resource={resource_type}:{resource_id} "
                f"status={status}"
            )
            if status == AuditLogger.SUCCESS:
                logger.info(log_message, extra={"audit_event": True})
            else:
                logger.warning(log_message, extra={"audit_event": True})

        except Exception as e:
            # CRITICAL: Audit logging failure should not break the application
            # but must be logged for investigation
            logger.error(f"Failed to write audit log: {str(e)}", exc_info=True)

    @staticmethod
    def log_authentication(
        db: Session, user_id: Optional[int], tenant_id: UUID, success: bool, ip_address: str
    ) -> None:
        """Log authentication attempt.

        Args:
            db: Database session
            user_id: User ID if authentication succeeded
            tenant_id: Tenant ID
            success: Whether authentication succeeded
            ip_address: IP address of login attempt
        """
        AuditLogger.log_event(
            db=db,
            event_type=AuditLogger.AUTHENTICATION,
            action=AuditLogger.LOGIN,
            user_id=user_id if success else None,
            tenant_id=tenant_id,
            ip_address=ip_address,
            status=AuditLogger.SUCCESS if success else AuditLogger.FAILURE,
        )

    @staticmethod
    def log_data_access(
        db: Session,
        user_id: int,
        tenant_id: UUID,
        resource_type: str,
        resource_id: int,
        action: str,
        ip_address: str,
    ) -> None:
        """Log data access event.

        Args:
            db: Database session
            user_id: User performing the access
            tenant_id: Tenant ID
            resource_type: Type of resource (project, client, etc.)
            resource_id: ID of resource
            action: Action performed (READ, UPDATE, DELETE)
            ip_address: IP address
        """
        AuditLogger.log_event(
            db=db,
            event_type=AuditLogger.DATA_ACCESS,
            action=action,
            user_id=user_id,
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
        )

    @staticmethod
    def log_file_operation(
        db: Session,
        user_id: int,
        tenant_id: UUID,
        action: str,
        filename: str,
        file_size: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """Log file upload/download operation.

        Args:
            db: Database session
            user_id: User performing operation
            tenant_id: Tenant ID
            action: UPLOAD or DOWNLOAD
            filename: Name of file
            file_size: Size of file in bytes
            ip_address: IP address
        """
        details = {"filename": filename}
        if file_size:
            details["file_size"] = file_size

        AuditLogger.log_event(
            db=db,
            event_type=AuditLogger.FILE_OPERATION,
            action=action,
            user_id=user_id,
            tenant_id=tenant_id,
            resource_type="file",
            ip_address=ip_address,
            details=details,
        )

    @staticmethod
    def log_security_violation(
        db: Session,
        event_description: str,
        user_id: Optional[int] = None,
        tenant_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log security violation.

        This should be called for any security-related failures:
        - Cross-tenant access attempts
        - Failed permission checks
        - Invalid tokens
        - Suspicious activity

        Args:
            db: Database session
            event_description: Description of the violation
            user_id: User ID if known
            tenant_id: Tenant ID if known
            ip_address: IP address
            details: Additional details
        """
        if details is None:
            details = {}
        details["description"] = event_description

        AuditLogger.log_event(
            db=db,
            event_type=AuditLogger.SECURITY_VIOLATION,
            action="VIOLATION",
            user_id=user_id,
            tenant_id=tenant_id,
            ip_address=ip_address,
            details=details,
            status=AuditLogger.FAILURE,
        )

        # Also log as critical for immediate alerting
        logger.critical(
            f"SECURITY VIOLATION: {event_description}",
            extra={
                "user_id": user_id,
                "tenant_id": str(tenant_id) if tenant_id else None,
                "ip_address": ip_address,
                "details": details,
            },
        )
