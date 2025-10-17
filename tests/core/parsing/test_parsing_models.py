"""Tests for parsing Pydantic models.

Following TDD approach - these tests define the expected behavior.
"""

import pytest
from pydantic import ValidationError as PydanticValidationError
from datetime import datetime


class TestCodingSystemResult:
    """Test suite for CodingSystemResult model."""

    def test_create_valid_coding_system_result(self):
        """Test creation of valid coding system result."""
        from genreport.core.parsing.parsing_models import CodingSystemResult

        result = CodingSystemResult(
            coding_pattern="A-B-C format (Account-Balance-Category)",
            code_families=[
                {"prefix": "1", "category": "Assets"},
                {"prefix": "2", "category": "Liabilities"},
            ],
            confidence=0.95,
        )

        assert result.coding_pattern == "A-B-C format (Account-Balance-Category)"
        assert len(result.code_families) == 2
        assert result.confidence == 0.95

    def test_confidence_must_be_between_0_and_1(self):
        """Test that confidence is validated to be between 0 and 1."""
        from genreport.core.parsing.parsing_models import CodingSystemResult

        # Valid confidence values
        valid_result = CodingSystemResult(
            coding_pattern="test", code_families=[], confidence=0.5
        )
        assert valid_result.confidence == 0.5

        # Invalid confidence > 1
        with pytest.raises(PydanticValidationError):
            CodingSystemResult(coding_pattern="test", code_families=[], confidence=1.5)

        # Invalid confidence < 0
        with pytest.raises(PydanticValidationError):
            CodingSystemResult(coding_pattern="test", code_families=[], confidence=-0.1)

    def test_code_families_is_list_of_dicts(self):
        """Test that code_families accepts list of dictionaries."""
        from genreport.core.parsing.parsing_models import CodingSystemResult

        result = CodingSystemResult(
            coding_pattern="test",
            code_families=[
                {"prefix": "A", "category": "Assets", "count": 10},
                {"prefix": "L", "category": "Liabilities"},
            ],
            confidence=0.8,
        )

        assert isinstance(result.code_families, list)
        assert all(isinstance(item, dict) for item in result.code_families)


class TestWorksheetAnalysisResult:
    """Test suite for WorksheetAnalysisResult model."""

    def test_create_valid_worksheet_analysis(self):
        """Test creation of valid worksheet analysis."""
        from genreport.core.parsing.parsing_models import WorksheetAnalysisResult

        analysis = WorksheetAnalysisResult(
            sheet_name="TB-01",
            is_summary=True,
            is_supporting=False,
            referenced_codes=["TB-02", "TB-03"],
            importance_score=0.9,
            analysis_metadata={"category": "Trial Balance", "rows": 150},
        )

        assert analysis.sheet_name == "TB-01"
        assert analysis.is_summary is True
        assert analysis.is_supporting is False
        assert analysis.referenced_codes == ["TB-02", "TB-03"]
        assert analysis.importance_score == 0.9
        assert analysis.analysis_metadata["category"] == "Trial Balance"

    def test_importance_score_validation(self):
        """Test that importance_score is validated."""
        from genreport.core.parsing.parsing_models import WorksheetAnalysisResult

        # Valid importance score
        valid_analysis = WorksheetAnalysisResult(
            sheet_name="test",
            is_summary=False,
            is_supporting=False,
            referenced_codes=[],
            importance_score=0.7,
        )
        assert valid_analysis.importance_score == 0.7

        # Invalid importance score > 1
        with pytest.raises(PydanticValidationError):
            WorksheetAnalysisResult(
                sheet_name="test",
                is_summary=False,
                is_supporting=False,
                referenced_codes=[],
                importance_score=1.2,
            )

        # Invalid importance score < 0
        with pytest.raises(PydanticValidationError):
            WorksheetAnalysisResult(
                sheet_name="test",
                is_summary=False,
                is_supporting=False,
                referenced_codes=[],
                importance_score=-0.1,
            )

    def test_referenced_codes_defaults_to_empty_list(self):
        """Test that referenced_codes has default empty list."""
        from genreport.core.parsing.parsing_models import WorksheetAnalysisResult

        analysis = WorksheetAnalysisResult(
            sheet_name="test",
            is_summary=False,
            is_supporting=False,
            importance_score=0.5,
        )

        assert analysis.referenced_codes == []

    def test_analysis_metadata_is_optional(self):
        """Test that analysis_metadata is optional."""
        from genreport.core.parsing.parsing_models import WorksheetAnalysisResult

        # Without metadata
        analysis1 = WorksheetAnalysisResult(
            sheet_name="test",
            is_summary=False,
            is_supporting=False,
            importance_score=0.5,
        )
        assert analysis1.analysis_metadata is None

        # With metadata
        analysis2 = WorksheetAnalysisResult(
            sheet_name="test",
            is_summary=False,
            is_supporting=False,
            importance_score=0.5,
            analysis_metadata={"key": "value"},
        )
        assert analysis2.analysis_metadata == {"key": "value"}


class TestRelationshipMapResult:
    """Test suite for RelationshipMapResult model."""

    def test_create_valid_relationship_map(self):
        """Test creation of valid relationship map."""
        from genreport.core.parsing.parsing_models import RelationshipMapResult

        result = RelationshipMapResult(
            coding_system="A-B-C format",
            code_families=[{"prefix": "1", "category": "Assets"}],
            relationships={
                "TB-01": ["TB-02", "TB-03"],
                "TB-02": ["TB-04"],
            },
            recommended_sheets=["TB-01", "TB-02"],
            confidence_score=0.88,
        )

        assert result.coding_system == "A-B-C format"
        assert len(result.code_families) == 1
        assert result.relationships["TB-01"] == ["TB-02", "TB-03"]
        assert len(result.recommended_sheets) == 2
        assert result.confidence_score == 0.88

    def test_confidence_score_validation(self):
        """Test that confidence_score is validated."""
        from genreport.core.parsing.parsing_models import RelationshipMapResult

        # Valid confidence
        valid_result = RelationshipMapResult(
            coding_system="test",
            code_families=[],
            relationships={},
            recommended_sheets=[],
            confidence_score=0.5,
        )
        assert valid_result.confidence_score == 0.5

        # Invalid confidence > 1
        with pytest.raises(PydanticValidationError):
            RelationshipMapResult(
                coding_system="test",
                code_families=[],
                relationships={},
                recommended_sheets=[],
                confidence_score=1.5,
            )

    def test_relationships_is_dict(self):
        """Test that relationships accepts dictionary."""
        from genreport.core.parsing.parsing_models import RelationshipMapResult

        result = RelationshipMapResult(
            coding_system="test",
            code_families=[],
            relationships={"A": ["B", "C"], "D": []},
            recommended_sheets=[],
            confidence_score=0.5,
        )

        assert isinstance(result.relationships, dict)
        assert result.relationships["A"] == ["B", "C"]
        assert result.relationships["D"] == []


class TestPreliminaryScanResult:
    """Test suite for PreliminaryScanResult model."""

    def test_create_complete_preliminary_scan_result(self):
        """Test creation of complete preliminary scan result."""
        from genreport.core.parsing.parsing_models import (
            PreliminaryScanResult,
            CodingSystemResult,
            WorksheetAnalysisResult,
        )

        coding_system = CodingSystemResult(
            coding_pattern="A-B-C", code_families=[], confidence=0.9
        )

        worksheet_analyses = [
            WorksheetAnalysisResult(
                sheet_name="TB-01",
                is_summary=True,
                is_supporting=False,
                importance_score=0.9,
            ),
            WorksheetAnalysisResult(
                sheet_name="TB-02",
                is_summary=False,
                is_supporting=True,
                importance_score=0.6,
            ),
        ]

        result = PreliminaryScanResult(
            coding_system=coding_system,
            worksheet_analyses=worksheet_analyses,
            recommended_sheets=["TB-01"],
            total_sheets=2,
        )

        assert result.coding_system.coding_pattern == "A-B-C"
        assert len(result.worksheet_analyses) == 2
        assert result.recommended_sheets == ["TB-01"]
        assert result.total_sheets == 2

    def test_worksheet_analyses_must_be_list(self):
        """Test that worksheet_analyses must be a list."""
        from genreport.core.parsing.parsing_models import (
            PreliminaryScanResult,
            CodingSystemResult,
            WorksheetAnalysisResult,
        )

        coding_system = CodingSystemResult(
            coding_pattern="test", code_families=[], confidence=0.9
        )

        # Valid with list
        result = PreliminaryScanResult(
            coding_system=coding_system,
            worksheet_analyses=[],
            recommended_sheets=[],
            total_sheets=0,
        )
        assert result.worksheet_analyses == []

        # With actual analyses
        analyses = [
            WorksheetAnalysisResult(
                sheet_name="test", is_summary=False, is_supporting=False, importance_score=0.5
            )
        ]
        result2 = PreliminaryScanResult(
            coding_system=coding_system,
            worksheet_analyses=analyses,
            recommended_sheets=[],
            total_sheets=1,
        )
        assert len(result2.worksheet_analyses) == 1


class TestParsingModelsJsonSerialization:
    """Test JSON serialization of parsing models."""

    def test_coding_system_result_json(self):
        """Test CodingSystemResult JSON serialization."""
        from genreport.core.parsing.parsing_models import CodingSystemResult

        result = CodingSystemResult(
            coding_pattern="test pattern",
            code_families=[{"prefix": "A", "category": "Assets"}],
            confidence=0.85,
        )

        json_data = result.model_dump()

        assert json_data["coding_pattern"] == "test pattern"
        assert json_data["code_families"] == [{"prefix": "A", "category": "Assets"}]
        assert json_data["confidence"] == 0.85

    def test_worksheet_analysis_result_json(self):
        """Test WorksheetAnalysisResult JSON serialization."""
        from genreport.core.parsing.parsing_models import WorksheetAnalysisResult

        analysis = WorksheetAnalysisResult(
            sheet_name="TB-01",
            is_summary=True,
            is_supporting=False,
            referenced_codes=["TB-02"],
            importance_score=0.9,
            analysis_metadata={"rows": 100},
        )

        json_data = analysis.model_dump()

        assert json_data["sheet_name"] == "TB-01"
        assert json_data["is_summary"] is True
        assert json_data["referenced_codes"] == ["TB-02"]
        assert json_data["analysis_metadata"] == {"rows": 100}

    def test_preliminary_scan_result_json(self):
        """Test PreliminaryScanResult JSON serialization."""
        from genreport.core.parsing.parsing_models import (
            PreliminaryScanResult,
            CodingSystemResult,
            WorksheetAnalysisResult,
        )

        result = PreliminaryScanResult(
            coding_system=CodingSystemResult(
                coding_pattern="test", code_families=[], confidence=0.9
            ),
            worksheet_analyses=[
                WorksheetAnalysisResult(
                    sheet_name="test",
                    is_summary=False,
                    is_supporting=False,
                    importance_score=0.5,
                )
            ],
            recommended_sheets=["test"],
            total_sheets=1,
        )

        json_data = result.model_dump()

        assert "coding_system" in json_data
        assert "worksheet_analyses" in json_data
        assert json_data["total_sheets"] == 1


# ============================================================================
# Validation Models Tests (Phase 3)
# ============================================================================


class TestValidationSeverity:
    """Test suite for ValidationSeverity enum."""

    def test_validation_severity_values(self):
        """Test that ValidationSeverity has correct enum values."""
        from genreport.core.parsing.parsing_models import ValidationSeverity

        assert ValidationSeverity.CRITICAL == "critical"
        assert ValidationSeverity.ERROR == "error"
        assert ValidationSeverity.WARNING == "warning"
        assert ValidationSeverity.INFO == "info"

    def test_validation_severity_is_string_enum(self):
        """Test that ValidationSeverity is a string enum."""
        from genreport.core.parsing.parsing_models import ValidationSeverity

        assert isinstance(ValidationSeverity.CRITICAL.value, str)
        assert ValidationSeverity.CRITICAL.value == "critical"


class TestValidationError:
    """Test suite for ValidationError model."""

    def test_create_valid_validation_error(self):
        """Test creation of valid validation error."""
        from genreport.core.parsing.parsing_models import (
            ValidationError,
            ValidationSeverity,
        )

        error = ValidationError(
            severity=ValidationSeverity.ERROR,
            message="Test error message",
            location="TB-01:A5",
            field="referenced_codes",
            suggestion="Fix the reference",
            metadata={"context": "test"},
        )

        assert error.severity == ValidationSeverity.ERROR
        assert error.message == "Test error message"
        assert error.location == "TB-01:A5"
        assert error.field == "referenced_codes"
        assert error.suggestion == "Fix the reference"
        assert error.metadata == {"context": "test"}

    def test_validation_error_minimal_fields(self):
        """Test ValidationError with only required fields."""
        from genreport.core.parsing.parsing_models import (
            ValidationError,
            ValidationSeverity,
        )

        error = ValidationError(
            severity=ValidationSeverity.WARNING, message="Warning message"
        )

        assert error.severity == ValidationSeverity.WARNING
        assert error.message == "Warning message"
        assert error.location is None
        assert error.field is None
        assert error.suggestion is None
        assert error.metadata is None

    def test_validation_error_message_must_not_be_empty(self):
        """Test that message must have at least 1 character."""
        from genreport.core.parsing.parsing_models import (
            ValidationError,
            ValidationSeverity,
        )

        # Valid with message
        valid_error = ValidationError(
            severity=ValidationSeverity.INFO, message="Valid message"
        )
        assert valid_error.message == "Valid message"

        # Invalid with empty message
        with pytest.raises(PydanticValidationError):
            ValidationError(severity=ValidationSeverity.INFO, message="")

    def test_validation_error_all_severity_levels(self):
        """Test ValidationError with all severity levels."""
        from genreport.core.parsing.parsing_models import (
            ValidationError,
            ValidationSeverity,
        )

        for severity in ValidationSeverity:
            error = ValidationError(severity=severity, message=f"Test {severity.value}")
            assert error.severity == severity
            assert severity.value in error.message

    def test_validation_error_json_serialization(self):
        """Test ValidationError JSON serialization."""
        from genreport.core.parsing.parsing_models import (
            ValidationError,
            ValidationSeverity,
        )

        error = ValidationError(
            severity=ValidationSeverity.CRITICAL,
            message="Critical error",
            location="TB-01:B10",
            field="balance",
            suggestion="Check calculation",
        )

        json_data = error.model_dump()

        assert json_data["severity"] == "critical"
        assert json_data["message"] == "Critical error"
        assert json_data["location"] == "TB-01:B10"
        assert json_data["field"] == "balance"
        assert json_data["suggestion"] == "Check calculation"


class TestValidationResult:
    """Test suite for ValidationResult model."""

    def test_create_valid_validation_result(self):
        """Test creation of valid validation result with no errors."""
        from genreport.core.parsing.parsing_models import ValidationResult

        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            info_messages=[],
            validation_context={"validator": "GenericValidator", "version": "1.0"},
        )

        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.info_messages == []
        assert result.validation_context["validator"] == "GenericValidator"

    def test_validation_result_with_errors(self):
        """Test ValidationResult with errors marks is_valid as False."""
        from genreport.core.parsing.parsing_models import (
            ValidationResult,
            ValidationError,
            ValidationSeverity,
        )

        errors = [
            ValidationError(
                severity=ValidationSeverity.ERROR,
                message="Error 1",
            ),
            ValidationError(
                severity=ValidationSeverity.CRITICAL,
                message="Critical error",
            ),
        ]

        result = ValidationResult(is_valid=False, errors=errors)

        assert result.is_valid is False
        assert len(result.errors) == 2
        assert result.error_count == 2

    def test_validation_result_with_warnings_only(self):
        """Test ValidationResult with warnings can still be valid."""
        from genreport.core.parsing.parsing_models import (
            ValidationResult,
            ValidationError,
            ValidationSeverity,
        )

        warnings = [
            ValidationError(
                severity=ValidationSeverity.WARNING,
                message="Warning 1",
            )
        ]

        result = ValidationResult(is_valid=True, warnings=warnings)

        assert result.is_valid is True
        assert len(result.warnings) == 1
        assert result.warning_count == 1
        assert result.error_count == 0

    def test_validation_result_has_critical_errors_property(self):
        """Test has_critical_errors property."""
        from genreport.core.parsing.parsing_models import (
            ValidationResult,
            ValidationError,
            ValidationSeverity,
        )

        # No critical errors
        result1 = ValidationResult(
            is_valid=False,
            errors=[
                ValidationError(severity=ValidationSeverity.ERROR, message="Error")
            ],
        )
        assert result1.has_critical_errors is False

        # With critical errors
        result2 = ValidationResult(
            is_valid=False,
            errors=[
                ValidationError(
                    severity=ValidationSeverity.CRITICAL, message="Critical"
                ),
                ValidationError(severity=ValidationSeverity.ERROR, message="Error"),
            ],
        )
        assert result2.has_critical_errors is True

    def test_validation_result_error_count_property(self):
        """Test error_count property."""
        from genreport.core.parsing.parsing_models import (
            ValidationResult,
            ValidationError,
            ValidationSeverity,
        )

        errors = [
            ValidationError(severity=ValidationSeverity.ERROR, message="Error 1"),
            ValidationError(severity=ValidationSeverity.CRITICAL, message="Critical"),
            ValidationError(severity=ValidationSeverity.ERROR, message="Error 2"),
        ]

        result = ValidationResult(is_valid=False, errors=errors)

        assert result.error_count == 3
        assert len(result.errors) == 3

    def test_validation_result_warning_count_property(self):
        """Test warning_count property."""
        from genreport.core.parsing.parsing_models import (
            ValidationResult,
            ValidationError,
            ValidationSeverity,
        )

        warnings = [
            ValidationError(severity=ValidationSeverity.WARNING, message="Warning 1"),
            ValidationError(severity=ValidationSeverity.WARNING, message="Warning 2"),
        ]

        result = ValidationResult(is_valid=True, warnings=warnings)

        assert result.warning_count == 2
        assert len(result.warnings) == 2

    def test_validation_result_with_all_message_types(self):
        """Test ValidationResult with errors, warnings, and info messages."""
        from genreport.core.parsing.parsing_models import (
            ValidationResult,
            ValidationError,
            ValidationSeverity,
        )

        errors = [
            ValidationError(severity=ValidationSeverity.ERROR, message="Error")
        ]
        warnings = [
            ValidationError(severity=ValidationSeverity.WARNING, message="Warning")
        ]
        info = [ValidationError(severity=ValidationSeverity.INFO, message="Info")]

        result = ValidationResult(
            is_valid=False, errors=errors, warnings=warnings, info_messages=info
        )

        assert result.error_count == 1
        assert result.warning_count == 1
        assert len(result.info_messages) == 1

    def test_validation_result_defaults_to_empty_lists(self):
        """Test that errors, warnings, info_messages default to empty lists."""
        from genreport.core.parsing.parsing_models import ValidationResult

        result = ValidationResult(is_valid=True)

        assert result.errors == []
        assert result.warnings == []
        assert result.info_messages == []
        assert result.error_count == 0
        assert result.warning_count == 0

    def test_validation_result_json_serialization(self):
        """Test ValidationResult JSON serialization."""
        from genreport.core.parsing.parsing_models import (
            ValidationResult,
            ValidationError,
            ValidationSeverity,
        )

        result = ValidationResult(
            is_valid=False,
            errors=[
                ValidationError(
                    severity=ValidationSeverity.ERROR,
                    message="Test error",
                    location="TB-01",
                )
            ],
            warnings=[
                ValidationError(
                    severity=ValidationSeverity.WARNING, message="Test warning"
                )
            ],
            validation_context={"validator": "TestValidator"},
        )

        json_data = result.model_dump()

        assert json_data["is_valid"] is False
        assert len(json_data["errors"]) == 1
        assert json_data["errors"][0]["message"] == "Test error"
        assert len(json_data["warnings"]) == 1
        assert json_data["validation_context"]["validator"] == "TestValidator"


class TestQueryResult:
    """Test suite for QueryResult model."""

    def test_create_valid_query_result(self):
        """Test creation of valid query result."""
        from genreport.core.parsing.parsing_models import QueryResult

        result = QueryResult(
            columns=["account_code", "account_name", "balance"],
            rows=[
                ["1000", "Cash", 50000.00],
                ["1100", "Accounts Receivable", 75000.00],
            ],
            row_count=2,
            query="SELECT * FROM trial_balance WHERE balance > 0",
            execution_time_ms=12.5,
            metadata={"database": "duckdb"},
        )

        assert result.columns == ["account_code", "account_name", "balance"]
        assert len(result.rows) == 2
        assert result.row_count == 2
        assert result.query == "SELECT * FROM trial_balance WHERE balance > 0"
        assert result.execution_time_ms == 12.5
        assert result.metadata["database"] == "duckdb"

    def test_query_result_minimal_fields(self):
        """Test QueryResult with only required fields."""
        from genreport.core.parsing.parsing_models import QueryResult

        result = QueryResult(
            columns=["col1"],
            rows=[["value1"]],
            row_count=1,
            query="SELECT col1 FROM table1",
        )

        assert result.columns == ["col1"]
        assert result.rows == [["value1"]]
        assert result.row_count == 1
        assert result.query == "SELECT col1 FROM table1"
        assert result.execution_time_ms is None
        assert result.metadata is None

    def test_query_result_empty_result_set(self):
        """Test QueryResult with empty result set."""
        from genreport.core.parsing.parsing_models import QueryResult

        result = QueryResult(
            columns=["account_code", "balance"],
            rows=[],
            row_count=0,
            query="SELECT * FROM trial_balance WHERE balance < 0",
        )

        assert result.columns == ["account_code", "balance"]
        assert result.rows == []
        assert result.row_count == 0

    def test_query_result_row_count_validation(self):
        """Test that row_count must be >= 0."""
        from genreport.core.parsing.parsing_models import QueryResult

        # Valid with 0
        valid_result = QueryResult(columns=[], rows=[], row_count=0, query="SELECT 1")
        assert valid_result.row_count == 0

        # Invalid with negative
        with pytest.raises(PydanticValidationError):
            QueryResult(columns=[], rows=[], row_count=-1, query="SELECT 1")

    def test_query_result_with_various_data_types(self):
        """Test QueryResult with various data types in rows."""
        from genreport.core.parsing.parsing_models import QueryResult

        result = QueryResult(
            columns=["id", "name", "balance", "active", "created_date"],
            rows=[
                [1, "Account A", 1000.50, True, "2024-01-01"],
                [2, "Account B", None, False, "2024-01-02"],
            ],
            row_count=2,
            query="SELECT * FROM accounts",
        )

        assert result.rows[0][0] == 1  # int
        assert result.rows[0][1] == "Account A"  # str
        assert result.rows[0][2] == 1000.50  # float
        assert result.rows[0][3] is True  # bool
        assert result.rows[1][2] is None  # None

    def test_query_result_json_serialization(self):
        """Test QueryResult JSON serialization."""
        from genreport.core.parsing.parsing_models import QueryResult

        result = QueryResult(
            columns=["code", "amount"],
            rows=[["1000", 500.00], ["2000", 750.00]],
            row_count=2,
            query="SELECT code, amount FROM table",
            execution_time_ms=8.3,
        )

        json_data = result.model_dump()

        assert json_data["columns"] == ["code", "amount"]
        assert json_data["rows"] == [["1000", 500.00], ["2000", 750.00]]
        assert json_data["row_count"] == 2
        assert json_data["execution_time_ms"] == 8.3


class TestValidationModelsIntegration:
    """Integration tests for validation models working together."""

    def test_validation_result_with_multiple_error_types(self):
        """Test ValidationResult aggregating different error types."""
        from genreport.core.parsing.parsing_models import (
            ValidationResult,
            ValidationError,
            ValidationSeverity,
        )

        errors = [
            ValidationError(
                severity=ValidationSeverity.CRITICAL,
                message="Worksheet 'TB-99' referenced but not found",
                location="TB-01:A5",
                field="referenced_codes",
                suggestion="Remove invalid reference",
            ),
            ValidationError(
                severity=ValidationSeverity.ERROR,
                message="Missing trial balance worksheet",
                location="workbook",
                suggestion="Add TB worksheet",
            ),
        ]

        warnings = [
            ValidationError(
                severity=ValidationSeverity.WARNING,
                message="Circular reference detected",
                location="TB-02",
            )
        ]

        info = [
            ValidationError(
                severity=ValidationSeverity.INFO,
                message="Found 15 worksheets for analysis",
            )
        ]

        result = ValidationResult(
            is_valid=False,
            errors=errors,
            warnings=warnings,
            info_messages=info,
            validation_context={
                "validator": "GenericValidator",
                "timestamp": "2024-03-15T10:30:00Z",
            },
        )

        # Verify aggregation
        assert result.is_valid is False
        assert result.has_critical_errors is True
        assert result.error_count == 2
        assert result.warning_count == 1
        assert len(result.info_messages) == 1

        # Verify details
        assert "TB-99" in result.errors[0].message
        assert result.errors[0].suggestion == "Remove invalid reference"
        assert result.warnings[0].location == "TB-02"
        assert "15 worksheets" in result.info_messages[0].message

    def test_validation_workflow_scenario(self):
        """Test realistic validation workflow scenario."""
        from genreport.core.parsing.parsing_models import (
            ValidationResult,
            ValidationError,
            ValidationSeverity,
        )

        # Scenario: Validating Excel workbook with issues
        validation_errors = []
        validation_warnings = []

        # Check 1: Missing required worksheet
        validation_errors.append(
            ValidationError(
                severity=ValidationSeverity.CRITICAL,
                message="Required worksheet 'Trial Balance' not found",
                location="workbook",
                suggestion="Add 'Trial Balance' worksheet",
            )
        )

        # Check 2: Invalid reference
        validation_warnings.append(
            ValidationError(
                severity=ValidationSeverity.WARNING,
                message="Worksheet 'TB-Old' references deleted sheet 'Archive'",
                location="TB-Old:B5",
                field="formula",
                suggestion="Update or remove reference",
            )
        )

        # Build result
        result = ValidationResult(
            is_valid=False,
            errors=validation_errors,
            warnings=validation_warnings,
            validation_context={
                "validator": "WorkbookValidator",
                "checks_performed": ["structure", "references", "data_types"],
            },
        )

        # Verify workflow results
        assert result.is_valid is False
        assert result.has_critical_errors is True
        assert result.error_count == 1
        assert result.warning_count == 1

        # Verify we can serialize for API response
        json_data = result.model_dump()
        assert "errors" in json_data
        assert "warnings" in json_data
        assert json_data["validation_context"]["validator"] == "WorkbookValidator"
