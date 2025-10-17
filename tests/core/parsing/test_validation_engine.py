"""Tests for ValidationEngine orchestration.

Following TDD approach - these tests define the expected orchestration behavior.
"""

import pytest


class TestValidationEngine:
    """Test suite for ValidationEngine orchestrator."""

    def test_engine_accepts_list_of_validators(self):
        """Test that ValidationEngine accepts a list of validators."""
        from genreport.core.parsing.validation_engine import ValidationEngine
        from genreport.core.parsing.validators import (
            WorksheetReferenceValidator,
            CircularReferenceValidator,
        )

        validators = [
            WorksheetReferenceValidator(),
            CircularReferenceValidator(),
        ]

        engine = ValidationEngine(validators=validators)

        assert engine is not None
        assert len(engine.validators) == 2

    def test_engine_accepts_empty_validator_list(self):
        """Test that ValidationEngine can be created with no validators."""
        from genreport.core.parsing.validation_engine import ValidationEngine

        engine = ValidationEngine(validators=[])

        assert engine is not None
        assert len(engine.validators) == 0

    def test_engine_runs_single_validator(self):
        """Test that engine runs a single validator and returns results."""
        from genreport.core.parsing.validation_engine import ValidationEngine
        from genreport.core.parsing.validators import WorksheetReferenceValidator
        from genreport.core.parsing.parsing_models import (
            PreliminaryScanResult,
            CodingSystemResult,
            WorksheetAnalysisResult,
        )

        # Create valid scan result
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

        engine = ValidationEngine(validators=[WorksheetReferenceValidator()])
        result = engine.validate(scan_result)

        assert result.is_valid is True
        assert result.error_count == 0
        assert result.validation_context["validators_run"] == 1

    def test_engine_runs_multiple_validators(self):
        """Test that engine runs multiple validators and aggregates results."""
        from genreport.core.parsing.validation_engine import ValidationEngine
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

        validators = [
            WorksheetReferenceValidator(),
            CircularReferenceValidator(),
            DataTypeValidator(),
        ]

        engine = ValidationEngine(validators=validators)
        result = engine.validate(scan_result)

        assert result.is_valid is True
        assert result.error_count == 0
        assert result.validation_context["validators_run"] == 3

    def test_engine_aggregates_errors_from_multiple_validators(self):
        """Test that engine aggregates errors from all validators."""
        from genreport.core.parsing.validation_engine import ValidationEngine
        from genreport.core.parsing.validators import (
            WorksheetReferenceValidator,
            DataTypeValidator,
        )
        from genreport.core.parsing.parsing_models import (
            PreliminaryScanResult,
            CodingSystemResult,
            WorksheetAnalysisResult,
        )

        # Create scan result with multiple issues
        scan_result = PreliminaryScanResult(
            coding_system=CodingSystemResult(
                coding_pattern="TB-XX", code_families=[], confidence=0.9
            ),
            worksheet_analyses=[
                WorksheetAnalysisResult(
                    sheet_name="TB-01",
                    is_summary=True,
                    is_supporting=False,
                    referenced_codes=["TB-99"],  # Missing reference
                    importance_score=0.9,
                ),
            ],
            recommended_sheets=["TB-01"],
            total_sheets=5,  # Inconsistent (should be 1)
        )

        validators = [
            WorksheetReferenceValidator(),  # Will find missing reference
            DataTypeValidator(),  # Will find total_sheets inconsistency
        ]

        engine = ValidationEngine(validators=validators)
        result = engine.validate(scan_result)

        assert result.is_valid is False
        assert result.error_count == 2  # One from each validator
        assert any("TB-99" in err.message for err in result.errors)
        assert any("total_sheets" in err.message for err in result.errors)

    def test_engine_aggregates_warnings_from_multiple_validators(self):
        """Test that engine aggregates warnings from all validators."""
        from genreport.core.parsing.validation_engine import ValidationEngine
        from genreport.core.parsing.validators import (
            CircularReferenceValidator,
            DataTypeValidator,
        )
        from genreport.core.parsing.parsing_models import (
            PreliminaryScanResult,
            CodingSystemResult,
            WorksheetAnalysisResult,
        )

        # Create scan result with warnings
        scan_result = PreliminaryScanResult(
            coding_system=CodingSystemResult(
                coding_pattern="TB-XX", code_families=[], confidence=0.9
            ),
            worksheet_analyses=[
                WorksheetAnalysisResult(
                    sheet_name="TB-01",
                    is_summary=True,
                    is_supporting=True,  # Both flags set (warning)
                    referenced_codes=["TB-02"],
                    importance_score=0.9,
                ),
                WorksheetAnalysisResult(
                    sheet_name="TB-02",
                    is_summary=False,
                    is_supporting=True,
                    referenced_codes=["TB-01"],  # Circular reference (warning)
                    importance_score=0.7,
                ),
            ],
            recommended_sheets=["TB-01"],
            total_sheets=2,
        )

        validators = [
            CircularReferenceValidator(),  # Will find circular reference
            DataTypeValidator(),  # Will find both flags set
        ]

        engine = ValidationEngine(validators=validators)
        result = engine.validate(scan_result)

        # Valid because only warnings (no errors)
        assert result.is_valid is True
        assert result.warning_count >= 2

    def test_engine_is_valid_false_if_any_validator_has_errors(self):
        """Test that engine marks result as invalid if any validator has errors."""
        from genreport.core.parsing.validation_engine import ValidationEngine
        from genreport.core.parsing.validators import (
            WorksheetReferenceValidator,
            CircularReferenceValidator,
        )
        from genreport.core.parsing.parsing_models import (
            PreliminaryScanResult,
            CodingSystemResult,
            WorksheetAnalysisResult,
        )

        # One validator will pass, one will fail
        scan_result = PreliminaryScanResult(
            coding_system=CodingSystemResult(
                coding_pattern="TB-XX", code_families=[], confidence=0.9
            ),
            worksheet_analyses=[
                WorksheetAnalysisResult(
                    sheet_name="TB-01",
                    is_summary=True,
                    is_supporting=False,
                    referenced_codes=["TB-99"],  # Missing reference (error)
                    importance_score=0.9,
                ),
            ],
            recommended_sheets=["TB-01"],
            total_sheets=1,
        )

        validators = [
            WorksheetReferenceValidator(),  # Will fail (missing reference)
            CircularReferenceValidator(),  # Will pass (no cycles)
        ]

        engine = ValidationEngine(validators=validators)
        result = engine.validate(scan_result)

        assert result.is_valid is False
        assert result.error_count >= 1

    def test_engine_with_no_validators_returns_valid_result(self):
        """Test that engine with no validators returns valid result."""
        from genreport.core.parsing.validation_engine import ValidationEngine
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
                    referenced_codes=[],
                    importance_score=0.9,
                ),
            ],
            recommended_sheets=["TB-01"],
            total_sheets=1,
        )

        engine = ValidationEngine(validators=[])
        result = engine.validate(scan_result)

        assert result.is_valid is True
        assert result.error_count == 0
        assert result.warning_count == 0
        assert result.validation_context["validators_run"] == 0

    def test_engine_includes_validator_names_in_context(self):
        """Test that engine includes validator names in validation context."""
        from genreport.core.parsing.validation_engine import ValidationEngine
        from genreport.core.parsing.validators import (
            WorksheetReferenceValidator,
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
                    referenced_codes=[],
                    importance_score=0.9,
                ),
            ],
            recommended_sheets=["TB-01"],
            total_sheets=1,
        )

        validators = [
            WorksheetReferenceValidator(),
            DataTypeValidator(),
        ]

        engine = ValidationEngine(validators=validators)
        result = engine.validate(scan_result)

        assert "validator_names" in result.validation_context
        assert "WorksheetReferenceValidator" in result.validation_context["validator_names"]
        assert "DataTypeValidator" in result.validation_context["validator_names"]

    def test_engine_aggregates_info_messages(self):
        """Test that engine can aggregate info messages from validators."""
        from genreport.core.parsing.validation_engine import ValidationEngine
        from genreport.core.parsing.parsing_models import (
            PreliminaryScanResult,
            CodingSystemResult,
            WorksheetAnalysisResult,
            ValidationResult,
            ValidationError,
            ValidationSeverity,
        )

        # Create custom validator that returns info messages
        class InfoValidator:
            def validate(self, scan_result: PreliminaryScanResult) -> ValidationResult:
                return ValidationResult(
                    is_valid=True,
                    info_messages=[
                        ValidationError(
                            severity=ValidationSeverity.INFO,
                            message=f"Found {len(scan_result.worksheet_analyses)} worksheets",
                        )
                    ],
                    validation_context={"validator": "InfoValidator"},
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
                    referenced_codes=[],
                    importance_score=0.9,
                ),
            ],
            recommended_sheets=["TB-01"],
            total_sheets=1,
        )

        engine = ValidationEngine(validators=[InfoValidator()])
        result = engine.validate(scan_result)

        assert result.is_valid is True
        assert len(result.info_messages) >= 1
        assert "Found 1 worksheets" in result.info_messages[0].message


class TestValidationEngineEdgeCases:
    """Test edge cases and error handling for ValidationEngine."""

    def test_engine_handles_validator_that_raises_exception(self):
        """Test that engine handles validators that raise exceptions gracefully."""
        from genreport.core.parsing.validation_engine import ValidationEngine
        from genreport.core.parsing.parsing_models import (
            PreliminaryScanResult,
            CodingSystemResult,
            WorksheetAnalysisResult,
            ValidationResult,
        )

        # Create validator that raises exception
        class BrokenValidator:
            def validate(self, scan_result: PreliminaryScanResult) -> ValidationResult:
                raise RuntimeError("Validator failed")

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

        engine = ValidationEngine(validators=[BrokenValidator()])

        # Should handle exception and include error in result
        result = engine.validate(scan_result)

        assert result.is_valid is False
        assert result.error_count >= 1
        assert any("exception" in err.message.lower() or "failed" in err.message.lower()
                   for err in result.errors)

    def test_engine_continues_after_validator_exception(self):
        """Test that engine continues running other validators after one fails."""
        from genreport.core.parsing.validation_engine import ValidationEngine
        from genreport.core.parsing.validators import DataTypeValidator
        from genreport.core.parsing.parsing_models import (
            PreliminaryScanResult,
            CodingSystemResult,
            WorksheetAnalysisResult,
            ValidationResult,
        )

        class BrokenValidator:
            def validate(self, scan_result: PreliminaryScanResult) -> ValidationResult:
                raise RuntimeError("Validator failed")

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

        validators = [
            BrokenValidator(),  # Will raise exception
            DataTypeValidator(),  # Should still run
        ]

        engine = ValidationEngine(validators=validators)
        result = engine.validate(scan_result)

        # Should have run 2 validators (even though one failed)
        assert result.validation_context["validators_run"] == 2
        # DataTypeValidator should have completed successfully
        assert "DataTypeValidator" in result.validation_context["validator_names"]

    def test_engine_preserves_error_order(self):
        """Test that engine preserves order of errors from validators."""
        from genreport.core.parsing.validation_engine import ValidationEngine
        from genreport.core.parsing.validators import (
            WorksheetReferenceValidator,
            DataTypeValidator,
        )
        from genreport.core.parsing.parsing_models import (
            PreliminaryScanResult,
            CodingSystemResult,
            WorksheetAnalysisResult,
        )

        # Create result with issues for both validators
        scan_result = PreliminaryScanResult(
            coding_system=CodingSystemResult(
                coding_pattern="TB-XX", code_families=[], confidence=0.9
            ),
            worksheet_analyses=[
                WorksheetAnalysisResult(
                    sheet_name="TB-01",
                    is_summary=True,
                    is_supporting=False,
                    referenced_codes=["TB-99"],  # Missing (caught by RefValidator first)
                    importance_score=0.9,
                ),
            ],
            recommended_sheets=["TB-01"],
            total_sheets=5,  # Inconsistent (caught by DataValidator second)
        )

        validators = [
            WorksheetReferenceValidator(),
            DataTypeValidator(),
        ]

        engine = ValidationEngine(validators=validators)
        result = engine.validate(scan_result)

        # First error should be from WorksheetReferenceValidator
        assert "TB-99" in result.errors[0].message
        # Second error should be from DataTypeValidator
        assert "total_sheets" in result.errors[1].message
