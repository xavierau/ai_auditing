"""Tests for ContextValidator - Cross-tenant data detection.

Following TDD methodology: These tests are written BEFORE implementation.
They define the expected behavior of ContextValidator.
"""

import pytest
from uuid import uuid4, UUID
from unittest.mock import Mock, patch

from genreport.core.security.context_validator import (
    ContextValidator,
    CrossTenantDataError,
)


class TestContextValidatorBasicValidation:
    """Test basic context validation scenarios."""

    def test_valid_context_single_tenant(self):
        """All data belongs to same tenant - should pass."""
        tenant_id = uuid4()
        validator = ContextValidator(tenant_id)

        context = {
            "trial_balance": {"tenant_id": tenant_id, "data": []},
            "general_ledger": {"tenant_id": tenant_id, "data": []},
            "project_metadata": {"tenant_id": tenant_id, "name": "Project A"},
        }

        # Should return True (valid)
        assert validator.validate(context) is True

    def test_empty_context_passes(self):
        """Empty context is valid."""
        tenant_id = uuid4()
        validator = ContextValidator(tenant_id)

        context = {}

        assert validator.validate(context) is True

    def test_context_without_tenant_id_passes(self):
        """Data without tenant_id field is allowed (may be constants, configs, etc.)."""
        tenant_id = uuid4()
        validator = ContextValidator(tenant_id)

        context = {
            "constants": {"TAX_RATE": 0.16},
            "config": {"jurisdiction": "HK"},
        }

        assert validator.validate(context) is True


class TestContextValidatorCrossTenantDetection:
    """Test detection of cross-tenant data contamination."""

    def test_detect_cross_tenant_in_top_level_dict(self):
        """Top-level dict with wrong tenant_id - should fail."""
        tenant_a = uuid4()
        tenant_b = uuid4()
        validator = ContextValidator(tenant_a)

        context = {
            "trial_balance": {"tenant_id": tenant_a, "data": []},
            "general_ledger": {"tenant_id": tenant_b, "data": []},  # Wrong tenant!
        }

        assert validator.validate(context) is False

    def test_detect_cross_tenant_in_nested_dict(self):
        """Nested dict with wrong tenant_id - should fail."""
        tenant_a = uuid4()
        tenant_b = uuid4()
        validator = ContextValidator(tenant_a)

        context = {
            "trial_balance": {
                "tenant_id": tenant_a,
                "metadata": {
                    "created_by": {"tenant_id": tenant_b, "user_id": 1}  # Nested wrong tenant!
                },
            }
        }

        assert validator.validate(context) is False

    def test_detect_cross_tenant_in_list(self):
        """List item with wrong tenant_id - should fail."""
        tenant_a = uuid4()
        tenant_b = uuid4()
        validator = ContextValidator(tenant_a)

        context = {
            "projects": [
                {"tenant_id": tenant_a, "name": "Project A"},
                {"tenant_id": tenant_b, "name": "Project B"},  # Wrong tenant in list!
            ]
        }

        assert validator.validate(context) is False

    def test_detect_cross_tenant_deeply_nested(self):
        """Deeply nested wrong tenant_id - should fail."""
        tenant_a = uuid4()
        tenant_b = uuid4()
        validator = ContextValidator(tenant_a)

        context = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {"tenant_id": tenant_b}  # Deep nesting
                    }
                }
            }
        }

        assert validator.validate(context) is False


class TestContextValidatorViolationReporting:
    """Test violation reporting and details."""

    def test_get_violations_returns_details(self):
        """Violations should include path and tenant_id details."""
        tenant_a = uuid4()
        tenant_b = uuid4()
        validator = ContextValidator(tenant_a)

        context = {
            "trial_balance": {"tenant_id": tenant_b, "data": []}
        }

        # Validate returns False
        assert validator.validate(context) is False

        # Get violations
        violations = validator.get_violations()

        assert len(violations) == 1
        assert violations[0]["path"] == "trial_balance"
        assert violations[0]["found_tenant_id"] == str(tenant_b)
        assert violations[0]["expected_tenant_id"] == str(tenant_a)

    def test_multiple_violations_all_reported(self):
        """All violations should be reported."""
        tenant_a = uuid4()
        tenant_b = uuid4()
        tenant_c = uuid4()
        validator = ContextValidator(tenant_a)

        context = {
            "trial_balance": {"tenant_id": tenant_b, "data": []},
            "general_ledger": {"tenant_id": tenant_c, "data": []},
        }

        assert validator.validate(context) is False

        violations = validator.get_violations()
        assert len(violations) == 2


class TestContextValidatorAuditLogging:
    """Test audit logging integration."""

    @patch("genreport.core.security.audit_logger.AuditLogger.log_event")
    @patch("genreport.core.database.base.get_db")
    def test_validation_failure_logs_security_violation(
        self, mock_get_db, mock_audit_log
    ):
        """Failed validation creates audit log entry."""
        tenant_a = uuid4()
        tenant_b = uuid4()
        validator = ContextValidator(tenant_a)

        context = {
            "trial_balance": {"tenant_id": tenant_b, "data": []}
        }

        # Mock database session
        mock_db = Mock()
        mock_get_db.return_value = mock_db

        # Validate
        validator.validate(context)

        # Should have logged security violation
        mock_audit_log.assert_called_once()
        call_kwargs = mock_audit_log.call_args[1]

        assert call_kwargs["event_type"] == "SECURITY_VIOLATION"
        assert call_kwargs["action"] == "CROSS_TENANT_DATA_DETECTED"
        assert call_kwargs["tenant_id"] == tenant_a
        assert call_kwargs["status"] == "FAILURE"
        assert "violations" in call_kwargs["details"]

    @patch("genreport.core.security.audit_logger.AuditLogger.log_event")
    def test_validation_success_no_audit_log(self, mock_audit_log):
        """Successful validation does not create audit log."""
        tenant_id = uuid4()
        validator = ContextValidator(tenant_id)

        context = {
            "trial_balance": {"tenant_id": tenant_id, "data": []}
        }

        validator.validate(context)

        # Should NOT have logged (only log violations)
        mock_audit_log.assert_not_called()


class TestContextValidatorUUIDHandling:
    """Test handling of UUID objects vs strings."""

    def test_uuid_object_matches_uuid_string(self):
        """UUID object should match string representation."""
        tenant_id = uuid4()
        validator = ContextValidator(tenant_id)

        context = {
            "trial_balance": {"tenant_id": str(tenant_id), "data": []},  # String
            "general_ledger": {"tenant_id": tenant_id, "data": []},  # UUID object
        }

        assert validator.validate(context) is True

    def test_uuid_string_matches_uuid_object(self):
        """String UUID in validator should match UUID objects in data."""
        tenant_id = uuid4()
        validator = ContextValidator(str(tenant_id))  # String tenant_id

        context = {
            "trial_balance": {"tenant_id": tenant_id, "data": []},  # UUID object
        }

        assert validator.validate(context) is True


class TestContextValidatorEdgeCases:
    """Test edge cases and error handling."""

    def test_none_values_ignored(self):
        """None values should be ignored (not validated)."""
        tenant_id = uuid4()
        validator = ContextValidator(tenant_id)

        context = {
            "trial_balance": None,
            "general_ledger": {"tenant_id": tenant_id, "data": []},
        }

        assert validator.validate(context) is True

    def test_list_of_primitives_allowed(self):
        """List of primitives (no dicts) should be allowed."""
        tenant_id = uuid4()
        validator = ContextValidator(tenant_id)

        context = {
            "account_codes": ["1000", "2000", "3000"],
            "amounts": [100.0, 200.0, 300.0],
        }

        assert validator.validate(context) is True

    def test_mixed_valid_invalid_data(self):
        """Context with both valid and invalid data should fail."""
        tenant_a = uuid4()
        tenant_b = uuid4()
        validator = ContextValidator(tenant_a)

        context = {
            "valid_section": {"tenant_id": tenant_a, "data": []},
            "invalid_section": {"tenant_id": tenant_b, "data": []},
        }

        assert validator.validate(context) is False


class TestContextValidatorStrictMode:
    """Test strict mode behavior (optional enhancement)."""

    def test_strict_mode_raises_exception_on_violation(self):
        """In strict mode, validation should raise exception instead of returning False."""
        tenant_a = uuid4()
        tenant_b = uuid4()
        validator = ContextValidator(tenant_a, strict=True)

        context = {
            "trial_balance": {"tenant_id": tenant_b, "data": []}
        }

        with pytest.raises(CrossTenantDataError) as exc_info:
            validator.validate(context)

        assert "cross-tenant data detected" in str(exc_info.value).lower()
        assert str(tenant_b) in str(exc_info.value)
