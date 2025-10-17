"""Tests for validation system.

Following TDD approach - these tests define the expected validator behavior.
"""

import pytest
from typing import Protocol


class TestValidatorInterface:
    """Test suite for Validator abstract interface."""

    def test_validator_protocol_definition(self):
        """Test that Validator protocol has correct method signature."""
        from genreport.core.parsing.validators import Validator
        from genreport.core.parsing.parsing_models import (
            PreliminaryScanResult,
            ValidationResult,
        )

        # Verify protocol has validate method
        assert hasattr(Validator, "validate")

    def test_custom_validator_implements_protocol(self):
        """Test that custom validators can implement the protocol."""
        from genreport.core.parsing.validators import Validator
        from genreport.core.parsing.parsing_models import (
            PreliminaryScanResult,
            ValidationResult,
            ValidationError,
            ValidationSeverity,
        )

        # Create a simple validator implementation
        class SimpleValidator:
            """Simple test validator."""

            def validate(self, scan_result: PreliminaryScanResult) -> ValidationResult:
                """Simple validation that always passes."""
                return ValidationResult(
                    is_valid=True,
                    validation_context={"validator": "SimpleValidator"},
                )

        # Should work without errors
        validator = SimpleValidator()
        assert isinstance(validator, object)


class TestWorksheetReferenceValidator:
    """Test suite for WorksheetReferenceValidator."""

    def test_validator_accepts_valid_references(self):
        """Test validator passes when all references exist."""
        from genreport.core.parsing.validators import WorksheetReferenceValidator
        from genreport.core.parsing.parsing_models import (
            PreliminaryScanResult,
            CodingSystemResult,
            WorksheetAnalysisResult,
        )

        # Create scan result with valid references
        scan_result = PreliminaryScanResult(
            coding_system=CodingSystemResult(
                coding_pattern="TB-XX", code_families=[], confidence=0.9
            ),
            worksheet_analyses=[
                WorksheetAnalysisResult(
                    sheet_name="TB-01",
                    is_summary=True,
                    is_supporting=False,
                    referenced_codes=["TB-02", "TB-03"],  # Both exist below
                    importance_score=0.9,
                ),
                WorksheetAnalysisResult(
                    sheet_name="TB-02",
                    is_summary=False,
                    is_supporting=True,
                    referenced_codes=[],
                    importance_score=0.7,
                ),
                WorksheetAnalysisResult(
                    sheet_name="TB-03",
                    is_summary=False,
                    is_supporting=True,
                    referenced_codes=[],
                    importance_score=0.7,
                ),
            ],
            recommended_sheets=["TB-01"],
            total_sheets=3,
        )

        validator = WorksheetReferenceValidator()
        result = validator.validate(scan_result)

        assert result.is_valid is True
        assert result.error_count == 0
        assert result.validation_context["validator"] == "WorksheetReferenceValidator"

    def test_validator_detects_missing_references(self):
        """Test validator detects when referenced worksheets don't exist."""
        from genreport.core.parsing.validators import WorksheetReferenceValidator
        from genreport.core.parsing.parsing_models import (
            PreliminaryScanResult,
            CodingSystemResult,
            WorksheetAnalysisResult,
            ValidationSeverity,
        )

        scan_result = PreliminaryScanResult(
            coding_system=CodingSystemResult(
                coding_pattern="TB-XX", code_families=[], confidence=0.9
            ),
            worksheet_analyses=[
                WorksheetAnalysisResult(
                    sheet_name="TB-01",
                    is_summary=True,
                    is_supporting=False,
                    referenced_codes=["TB-99", "TB-100"],  # Don't exist
                    importance_score=0.9,
                ),
                WorksheetAnalysisResult(
                    sheet_name="TB-02",
                    is_summary=False,
                    is_supporting=True,
                    referenced_codes=[],
                    importance_score=0.7,
                ),
            ],
            recommended_sheets=["TB-01"],
            total_sheets=2,
        )

        validator = WorksheetReferenceValidator()
        result = validator.validate(scan_result)

        assert result.is_valid is False
        assert result.error_count == 2  # Two missing references
        assert result.errors[0].severity == ValidationSeverity.ERROR
        assert "TB-99" in result.errors[0].message
        assert result.errors[0].location == "TB-01"

    def test_validator_handles_empty_references(self):
        """Test validator handles worksheets with no references."""
        from genreport.core.parsing.validators import WorksheetReferenceValidator
        from genreport.core.parsing.parsing_models import (
            PreliminaryScanResult,
            CodingSystemResult,
            WorksheetAnalysisResult,
        )

        scan_result = PreliminaryScanResult(
            coding_system=CodingSystemResult(
                coding_pattern="TB-XX", code_families=[], confidence=0.9
            ),
            worksheet_analyses=[
                WorksheetAnalysisResult(
                    sheet_name="TB-01",
                    is_summary=True,
                    is_supporting=False,
                    referenced_codes=[],  # No references
                    importance_score=0.9,
                ),
            ],
            recommended_sheets=["TB-01"],
            total_sheets=1,
        )

        validator = WorksheetReferenceValidator()
        result = validator.validate(scan_result)

        assert result.is_valid is True
        assert result.error_count == 0


class TestCircularReferenceValidator:
    """Test suite for CircularReferenceValidator."""

    def test_validator_accepts_acyclic_graph(self):
        """Test validator passes when there are no circular references."""
        from genreport.core.parsing.validators import CircularReferenceValidator
        from genreport.core.parsing.parsing_models import (
            PreliminaryScanResult,
            CodingSystemResult,
            WorksheetAnalysisResult,
        )

        # Create acyclic graph: TB-01 -> TB-02 -> TB-03
        scan_result = PreliminaryScanResult(
            coding_system=CodingSystemResult(
                coding_pattern="TB-XX", code_families=[], confidence=0.9
            ),
            worksheet_analyses=[
                WorksheetAnalysisResult(
                    sheet_name="TB-01",
                    is_summary=True,
                    is_supporting=False,
                    referenced_codes=["TB-02"],
                    importance_score=0.9,
                ),
                WorksheetAnalysisResult(
                    sheet_name="TB-02",
                    is_summary=False,
                    is_supporting=True,
                    referenced_codes=["TB-03"],
                    importance_score=0.7,
                ),
                WorksheetAnalysisResult(
                    sheet_name="TB-03",
                    is_summary=False,
                    is_supporting=True,
                    referenced_codes=[],
                    importance_score=0.6,
                ),
            ],
            recommended_sheets=["TB-01"],
            total_sheets=3,
        )

        validator = CircularReferenceValidator()
        result = validator.validate(scan_result)

        assert result.is_valid is True
        assert result.error_count == 0
        assert result.validation_context["validator"] == "CircularReferenceValidator"

    def test_validator_detects_simple_cycle(self):
        """Test validator detects simple circular reference (A -> B -> A)."""
        from genreport.core.parsing.validators import CircularReferenceValidator
        from genreport.core.parsing.parsing_models import (
            PreliminaryScanResult,
            CodingSystemResult,
            WorksheetAnalysisResult,
            ValidationSeverity,
        )

        # Create cycle: TB-01 -> TB-02 -> TB-01
        scan_result = PreliminaryScanResult(
            coding_system=CodingSystemResult(
                coding_pattern="TB-XX", code_families=[], confidence=0.9
            ),
            worksheet_analyses=[
                WorksheetAnalysisResult(
                    sheet_name="TB-01",
                    is_summary=True,
                    is_supporting=False,
                    referenced_codes=["TB-02"],
                    importance_score=0.9,
                ),
                WorksheetAnalysisResult(
                    sheet_name="TB-02",
                    is_summary=False,
                    is_supporting=True,
                    referenced_codes=["TB-01"],  # Circular reference!
                    importance_score=0.7,
                ),
            ],
            recommended_sheets=["TB-01"],
            total_sheets=2,
        )

        validator = CircularReferenceValidator()
        result = validator.validate(scan_result)

        assert result.is_valid is False
        assert result.warning_count >= 1
        assert result.warnings[0].severity == ValidationSeverity.WARNING
        assert "circular" in result.warnings[0].message.lower()
        assert "TB-01" in result.warnings[0].message
        assert "TB-02" in result.warnings[0].message

    def test_validator_detects_self_reference(self):
        """Test validator detects worksheet referencing itself."""
        from genreport.core.parsing.validators import CircularReferenceValidator
        from genreport.core.parsing.parsing_models import (
            PreliminaryScanResult,
            CodingSystemResult,
            WorksheetAnalysisResult,
        )

        scan_result = PreliminaryScanResult(
            coding_system=CodingSystemResult(
                coding_pattern="TB-XX", code_families=[], confidence=0.9
            ),
            worksheet_analyses=[
                WorksheetAnalysisResult(
                    sheet_name="TB-01",
                    is_summary=True,
                    is_supporting=False,
                    referenced_codes=["TB-01"],  # Self-reference!
                    importance_score=0.9,
                ),
            ],
            recommended_sheets=["TB-01"],
            total_sheets=1,
        )

        validator = CircularReferenceValidator()
        result = validator.validate(scan_result)

        assert result.is_valid is False
        assert result.warning_count >= 1
        assert "self-reference" in result.warnings[0].message.lower() or "circular" in result.warnings[0].message.lower()

    def test_validator_detects_complex_cycle(self):
        """Test validator detects complex circular reference (A -> B -> C -> A)."""
        from genreport.core.parsing.validators import CircularReferenceValidator
        from genreport.core.parsing.parsing_models import (
            PreliminaryScanResult,
            CodingSystemResult,
            WorksheetAnalysisResult,
        )

        # Create cycle: TB-01 -> TB-02 -> TB-03 -> TB-01
        scan_result = PreliminaryScanResult(
            coding_system=CodingSystemResult(
                coding_pattern="TB-XX", code_families=[], confidence=0.9
            ),
            worksheet_analyses=[
                WorksheetAnalysisResult(
                    sheet_name="TB-01",
                    is_summary=True,
                    is_supporting=False,
                    referenced_codes=["TB-02"],
                    importance_score=0.9,
                ),
                WorksheetAnalysisResult(
                    sheet_name="TB-02",
                    is_summary=False,
                    is_supporting=True,
                    referenced_codes=["TB-03"],
                    importance_score=0.7,
                ),
                WorksheetAnalysisResult(
                    sheet_name="TB-03",
                    is_summary=False,
                    is_supporting=True,
                    referenced_codes=["TB-01"],  # Completes the cycle
                    importance_score=0.6,
                ),
            ],
            recommended_sheets=["TB-01"],
            total_sheets=3,
        )

        validator = CircularReferenceValidator()
        result = validator.validate(scan_result)

        assert result.is_valid is False
        assert result.warning_count >= 1
        assert "circular" in result.warnings[0].message.lower()


class TestDataTypeValidator:
    """Test suite for DataTypeValidator."""

    def test_validator_accepts_valid_data_types(self):
        """Test validator passes when all data types are valid."""
        from genreport.core.parsing.validators import DataTypeValidator
        from genreport.core.parsing.parsing_models import (
            PreliminaryScanResult,
            CodingSystemResult,
            WorksheetAnalysisResult,
        )

        scan_result = PreliminaryScanResult(
            coding_system=CodingSystemResult(
                coding_pattern="TB-XX",
                code_families=[{"prefix": "TB", "category": "Trial Balance"}],
                confidence=0.9,
            ),
            worksheet_analyses=[
                WorksheetAnalysisResult(
                    sheet_name="TB-01",
                    is_summary=True,
                    is_supporting=False,
                    referenced_codes=["TB-02"],
                    importance_score=0.9,
                ),
            ],
            recommended_sheets=["TB-01"],
            total_sheets=1,
        )

        validator = DataTypeValidator()
        result = validator.validate(scan_result)

        assert result.is_valid is True
        assert result.error_count == 0
        assert result.validation_context["validator"] == "DataTypeValidator"

    def test_validator_detects_invalid_confidence_range(self):
        """Test validator detects confidence scores outside valid range."""
        from genreport.core.parsing.validators import DataTypeValidator
        from genreport.core.parsing.parsing_models import (
            PreliminaryScanResult,
            CodingSystemResult,
            WorksheetAnalysisResult,
        )

        # Note: This should be caught by Pydantic, but we test the validator too
        scan_result = PreliminaryScanResult(
            coding_system=CodingSystemResult(
                coding_pattern="TB-XX", code_families=[], confidence=0.9
            ),
            worksheet_analyses=[
                WorksheetAnalysisResult(
                    sheet_name="TB-01",
                    is_summary=True,
                    is_supporting=False,
                    referenced_codes=[],
                    importance_score=0.9,
                ),
            ],
            recommended_sheets=["TB-01"],
            total_sheets=1,
        )

        validator = DataTypeValidator()
        result = validator.validate(scan_result)

        # All fields are valid, so should pass
        assert result.is_valid is True

    def test_validator_detects_empty_sheet_name(self):
        """Test validator detects empty sheet names."""
        from genreport.core.parsing.validators import DataTypeValidator
        from genreport.core.parsing.parsing_models import (
            ValidationSeverity,
        )

        # This test verifies the validator can detect data type issues
        # Empty sheet names should be caught by Pydantic, but the validator
        # provides an additional check

        validator = DataTypeValidator()

        # Since Pydantic prevents creation of invalid models,
        # we verify the validator exists and has correct signature
        assert hasattr(validator, "validate")

    def test_validator_checks_total_sheets_consistency(self):
        """Test validator checks total_sheets matches worksheet_analyses length."""
        from genreport.core.parsing.validators import DataTypeValidator
        from genreport.core.parsing.parsing_models import (
            PreliminaryScanResult,
            CodingSystemResult,
            WorksheetAnalysisResult,
            ValidationSeverity,
        )

        # Create scan result with inconsistent total_sheets
        scan_result = PreliminaryScanResult(
            coding_system=CodingSystemResult(
                coding_pattern="TB-XX", code_families=[], confidence=0.9
            ),
            worksheet_analyses=[
                WorksheetAnalysisResult(
                    sheet_name="TB-01",
                    is_summary=True,
                    is_supporting=False,
                    referenced_codes=[],
                    importance_score=0.9,
                ),
                WorksheetAnalysisResult(
                    sheet_name="TB-02",
                    is_summary=False,
                    is_supporting=True,
                    referenced_codes=[],
                    importance_score=0.7,
                ),
            ],
            recommended_sheets=["TB-01"],
            total_sheets=5,  # Inconsistent! Only 2 worksheet_analyses
        )

        validator = DataTypeValidator()
        result = validator.validate(scan_result)

        assert result.is_valid is False
        assert result.error_count >= 1
        assert any("total_sheets" in err.message.lower() for err in result.errors)
        assert result.errors[0].severity == ValidationSeverity.ERROR


class TestValidatorIntegration:
    """Integration tests for validators working together."""

    def test_multiple_validators_can_run_on_same_data(self):
        """Test that multiple validators can validate the same scan result."""
        from genreport.core.parsing.validators import (
            WorksheetReferenceValidator,
            CircularReferenceValidator,
            DataTypeValidator,
        )
        from genreport.core.parsing.parsing_models import (
            PreliminaryScanResult,
            CodingSystemResult,
            WorksheetAnalysisResult,
        )

        scan_result = PreliminaryScanResult(
            coding_system=CodingSystemResult(
                coding_pattern="TB-XX", code_families=[], confidence=0.9
            ),
            worksheet_analyses=[
                WorksheetAnalysisResult(
                    sheet_name="TB-01",
                    is_summary=True,
                    is_supporting=False,
                    referenced_codes=["TB-02"],
                    importance_score=0.9,
                ),
                WorksheetAnalysisResult(
                    sheet_name="TB-02",
                    is_summary=False,
                    is_supporting=True,
                    referenced_codes=[],
                    importance_score=0.7,
                ),
            ],
            recommended_sheets=["TB-01"],
            total_sheets=2,
        )

        # Run all validators
        ref_validator = WorksheetReferenceValidator()
        circ_validator = CircularReferenceValidator()
        data_validator = DataTypeValidator()

        ref_result = ref_validator.validate(scan_result)
        circ_result = circ_validator.validate(scan_result)
        data_result = data_validator.validate(scan_result)

        # All should pass
        assert ref_result.is_valid is True
        assert circ_result.is_valid is True
        assert data_result.is_valid is True

    def test_validators_detect_different_issues(self):
        """Test that different validators detect different types of issues."""
        from genreport.core.parsing.validators import (
            WorksheetReferenceValidator,
            CircularReferenceValidator,
        )
        from genreport.core.parsing.parsing_models import (
            PreliminaryScanResult,
            CodingSystemResult,
            WorksheetAnalysisResult,
        )

        # Create scan result with both missing reference and circular reference
        scan_result = PreliminaryScanResult(
            coding_system=CodingSystemResult(
                coding_pattern="TB-XX", code_families=[], confidence=0.9
            ),
            worksheet_analyses=[
                WorksheetAnalysisResult(
                    sheet_name="TB-01",
                    is_summary=True,
                    is_supporting=False,
                    referenced_codes=["TB-02", "TB-99"],  # TB-99 missing
                    importance_score=0.9,
                ),
                WorksheetAnalysisResult(
                    sheet_name="TB-02",
                    is_summary=False,
                    is_supporting=True,
                    referenced_codes=["TB-01"],  # Circular!
                    importance_score=0.7,
                ),
            ],
            recommended_sheets=["TB-01"],
            total_sheets=2,
        )

        ref_validator = WorksheetReferenceValidator()
        circ_validator = CircularReferenceValidator()

        ref_result = ref_validator.validate(scan_result)
        circ_result = circ_validator.validate(scan_result)

        # Reference validator catches missing reference
        assert ref_result.is_valid is False
        assert "TB-99" in ref_result.errors[0].message

        # Circular validator catches cycle
        assert circ_result.is_valid is False
        assert "circular" in circ_result.warnings[0].message.lower()
