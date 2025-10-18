"""Context Validator - Prevents cross-tenant data contamination.

This module provides security validation to ensure that context data
passed to AI agents contains no cross-tenant data leakage.

Usage:
    validator = ContextValidator(tenant_id)
    if not validator.validate(context):
        raise SecurityError("Cross-tenant data detected")
"""

from typing import Dict, Any, List, Optional
from uuid import UUID


class CrossTenantDataError(Exception):
    """Raised when cross-tenant data is detected in strict mode."""

    pass


class ContextValidator:
    """Validates that context contains no cross-tenant data.

    Recursively inspects all data structures for tenant_id fields
    and ensures they match the expected tenant_id.
    """

    def __init__(self, expected_tenant_id: UUID, strict: bool = False):
        """Initialize validator.

        Args:
            expected_tenant_id: The tenant_id that all data should belong to
            strict: If True, raises exception on violation instead of returning False
        """
        self.expected_tenant_id = expected_tenant_id
        self.strict = strict
        self._violations: List[Dict[str, Any]] = []

    def validate(self, context: Dict[str, Any]) -> bool:
        """Validate that context contains no cross-tenant data.

        Args:
            context: The context dict to validate

        Returns:
            True if valid, False if cross-tenant data detected

        Raises:
            CrossTenantDataError: If strict=True and violation detected
        """
        # Reset violations
        self._violations = []

        # Recursively check all values
        for key, value in context.items():
            self._check_value(key, value, path=[key])

        # If violations found, handle based on mode
        if self._violations:
            # Log security violation
            self._log_security_violation()

            if self.strict:
                raise CrossTenantDataError(
                    f"Cross-tenant data detected: {len(self._violations)} violation(s). "
                    f"Expected tenant_id={self.expected_tenant_id}, "
                    f"found: {[v['found_tenant_id'] for v in self._violations]}"
                )

            return False

        return True

    def get_violations(self) -> List[Dict[str, Any]]:
        """Get details of detected violations.

        Returns:
            List of violation dicts with path, found_tenant_id, expected_tenant_id
        """
        return self._violations.copy()

    def _check_value(self, key: str, value: Any, path: List[str]) -> None:
        """Recursively check a value for tenant_id mismatches.

        Args:
            key: The key for this value
            value: The value to check
            path: The path to this value (for reporting)
        """
        # Skip None values
        if value is None:
            return

        # Check dictionaries
        if isinstance(value, dict):
            # Check if this dict has a tenant_id field
            if "tenant_id" in value:
                found_tenant_id = value["tenant_id"]

                # Compare tenant_ids (handle both UUID objects and strings)
                if str(found_tenant_id) != str(self.expected_tenant_id):
                    self._violations.append(
                        {
                            "path": " -> ".join(path),
                            "found_tenant_id": str(found_tenant_id),
                            "expected_tenant_id": str(self.expected_tenant_id),
                        }
                    )

            # Recursively check nested dict values
            for k, v in value.items():
                self._check_value(k, v, path + [k])

        # Check lists
        elif isinstance(value, list):
            for idx, item in enumerate(value):
                self._check_value(f"{key}[{idx}]", item, path + [f"[{idx}]"])

    def _log_security_violation(self) -> None:
        """Log security violation via audit logger."""
        try:
            from genreport.core.security.audit_logger import AuditLogger
            from genreport.core.database.base import get_db

            db = get_db()

            AuditLogger.log_event(
                db=db,
                event_type="SECURITY_VIOLATION",
                action="CROSS_TENANT_DATA_DETECTED",
                tenant_id=self.expected_tenant_id,
                resource_type="context",
                details={
                    "violations": self._violations,
                    "violation_count": len(self._violations),
                },
                status="FAILURE",
            )
        except Exception as e:
            # Don't let logging failure prevent validation
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to log security violation: {e}")
