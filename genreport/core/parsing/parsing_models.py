"""Pydantic models for parsing operations.

These models define the data structures used throughout the two-phase
LLM parsing process for Excel working papers, including validation results.
"""

from typing import List, Dict, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class CodeFamily(BaseModel):
    """Represents a single code family in the coding system.

    Example:
        {
            "prefix": "TB",
            "category": "Trial Balance",
            "description": "Trial balance worksheets",
            "count": 5
        }
    """

    prefix: str = Field(
        ...,
        description="Code prefix or identifier (e.g., 'TB', '1', 'A-100')",
        min_length=1
    )

    category: str = Field(
        ...,
        description="Category or type of this code family (e.g., 'Trial Balance', 'Assets')",
        min_length=1
    )

    description: Optional[str] = Field(
        default=None,
        description="Detailed description of this code family"
    )

    count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Number of worksheets in this family"
    )


class CodingSystemResult(BaseModel):
    """Result of Phase 1a: Coding system discovery.

    This model represents the discovered coding pattern used in worksheet names
    and the identified code families.

    Example:
        {
            "coding_pattern": "A-B-C format (Account-Balance-Category)",
            "code_families": [
                {"prefix": "1", "category": "Assets", "count": 15},
                {"prefix": "2", "category": "Liabilities", "count": 8}
            ],
            "confidence": 0.95
        }
    """

    coding_pattern: str = Field(
        ...,
        description="Description of the discovered coding pattern",
        examples=["A-B-C format", "Hierarchical numbering", "Alphanumeric codes"]
    )

    code_families: List[CodeFamily] = Field(
        ...,
        description="Grouped code families with their characteristics"
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for the coding pattern discovery (0-1)"
    )

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Validate confidence is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v


class WorksheetAnalysisResult(BaseModel):
    """Result of Phase 1b: Individual worksheet analysis.

    This model represents the analysis of a single worksheet within the context
    of the discovered coding system.

    Example:
        {
            "sheet_name": "TB-01",
            "is_summary": true,
            "is_supporting": false,
            "referenced_codes": ["TB-02", "TB-03"],
            "importance_score": 0.9,
            "analysis_metadata": {"category": "Trial Balance", "rows": 150}
        }
    """

    sheet_name: str = Field(
        ...,
        description="Name of the worksheet",
        min_length=1
    )

    is_summary: bool = Field(
        ...,
        description="Whether this worksheet is a summary/consolidation sheet"
    )

    is_supporting: bool = Field(
        ...,
        description="Whether this worksheet contains supporting detail"
    )

    referenced_codes: List[str] = Field(
        default_factory=list,
        description="List of other worksheet codes referenced by this sheet"
    )

    importance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Importance score for this worksheet (0-1)"
    )

    analysis_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata from the LLM analysis"
    )

    summary: Optional[str] = Field(
        default=None,
        description="Brief summary of the worksheet content"
    )

    @field_validator("importance_score")
    @classmethod
    def validate_importance_score(cls, v: float) -> float:
        """Validate importance score is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Importance score must be between 0.0 and 1.0")
        return v


class RelationshipMapResult(BaseModel):
    """Complete relationship map for the workbook.

    This model represents the full relationship graph between worksheets,
    including the coding system and recommended priority sheets.

    Example:
        {
            "coding_system": "A-B-C format",
            "code_families": [{"prefix": "1", "category": "Assets"}],
            "relationships": {
                "TB-01": ["TB-02", "TB-03"],
                "TB-02": ["TB-04"]
            },
            "recommended_sheets": ["TB-01", "TB-02"],
            "confidence_score": 0.88
        }
    """

    coding_system: str = Field(
        ...,
        description="The discovered coding pattern"
    )

    code_families: List[CodeFamily] = Field(
        ...,
        description="Grouped code families"
    )

    relationships: Dict[str, List[str]] = Field(
        ...,
        description="Mapping of worksheet relationships (sheet -> referenced_sheets)"
    )

    recommended_sheets: List[str] = Field(
        ...,
        description="Top-priority worksheets for parsing"
    )

    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall confidence in the relationship mapping (0-1)"
    )

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence_score(cls, v: float) -> float:
        """Validate confidence score is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        return v


class PreliminaryScanResult(BaseModel):
    """Complete result of preliminary scan (Phase 1a + 1b).

    This model aggregates the coding system discovery and all worksheet analyses
    into a single result structure.

    Example:
        {
            "coding_system": {
                "coding_pattern": "A-B-C format",
                "code_families": [...],
                "confidence": 0.95
            },
            "worksheet_analyses": [
                {
                    "sheet_name": "TB-01",
                    "is_summary": true,
                    ...
                }
            ],
            "recommended_sheets": ["TB-01", "TB-02"],
            "total_sheets": 15
        }
    """

    coding_system: CodingSystemResult = Field(
        ...,
        description="Result of coding system discovery (Phase 1a)"
    )

    worksheet_analyses: List[WorksheetAnalysisResult] = Field(
        ...,
        description="List of individual worksheet analyses (Phase 1b)"
    )

    recommended_sheets: List[str] = Field(
        ...,
        description="Top-priority sheets for detailed parsing"
    )

    total_sheets: int = Field(
        ...,
        ge=0,
        description="Total number of sheets in the workbook"
    )

    scan_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata for market-specific validation (jurisdiction, accounting_standard, currency, entity metrics, etc.)"
    )

    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "coding_system": {
                    "coding_pattern": "A-B-C format",
                    "code_families": [
                        {"prefix": "1", "category": "Assets", "count": 10}
                    ],
                    "confidence": 0.95
                },
                "worksheet_analyses": [
                    {
                        "sheet_name": "TB-01",
                        "is_summary": True,
                        "is_supporting": False,
                        "referenced_codes": ["TB-02"],
                        "importance_score": 0.9
                    }
                ],
                "recommended_sheets": ["TB-01", "TB-02"],
                "total_sheets": 15
            }
        }


# ============================================================================
# Validation Models (Phase 3)
# ============================================================================


class ValidationSeverity(str, Enum):
    """Severity levels for validation errors."""

    CRITICAL = "critical"  # Must fix before processing
    ERROR = "error"        # Major issue, processing risky
    WARNING = "warning"    # Minor issue, processing can continue
    INFO = "info"         # Informational message


class ValidationError(BaseModel):
    """Represents a single validation error or warning.

    Example:
        {
            "severity": "error",
            "message": "Worksheet 'TB-99' referenced but not found",
            "location": "TB-01:A5",
            "field": "referenced_codes",
            "suggestion": "Remove invalid reference or create missing worksheet"
        }
    """

    severity: ValidationSeverity = Field(
        ...,
        description="Severity level of the validation issue"
    )

    message: str = Field(
        ...,
        description="Human-readable error message",
        min_length=1
    )

    location: Optional[str] = Field(
        default=None,
        description="Location of the error (worksheet:cell, row number, etc.)"
    )

    field: Optional[str] = Field(
        default=None,
        description="Field or property that failed validation"
    )

    suggestion: Optional[str] = Field(
        default=None,
        description="Suggested fix for the validation issue"
    )

    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context about the error"
    )


class ValidationResult(BaseModel):
    """Result of validation process.

    Example:
        {
            "is_valid": false,
            "errors": [
                {
                    "severity": "error",
                    "message": "Missing trial balance worksheet",
                    "location": "workbook"
                }
            ],
            "warnings": [
                {
                    "severity": "warning",
                    "message": "Circular reference detected"
                }
            ],
            "info_messages": [],
            "validation_context": {
                "validator": "GenericValidator",
                "timestamp": "2024-03-15T10:30:00Z"
            }
        }
    """

    is_valid: bool = Field(
        ...,
        description="Overall validation status (False if any errors present)"
    )

    errors: List[ValidationError] = Field(
        default_factory=list,
        description="List of validation errors (severity: critical, error)"
    )

    warnings: List[ValidationError] = Field(
        default_factory=list,
        description="List of validation warnings (severity: warning)"
    )

    info_messages: List[ValidationError] = Field(
        default_factory=list,
        description="List of informational messages (severity: info)"
    )

    validation_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Context about the validation run (validator type, config, etc.)"
    )

    @property
    def has_critical_errors(self) -> bool:
        """Check if any critical errors exist."""
        return any(
            err.severity == ValidationSeverity.CRITICAL
            for err in self.errors
        )

    @property
    def error_count(self) -> int:
        """Count of errors (critical + error severity)."""
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        """Count of warnings."""
        return len(self.warnings)


class QueryResult(BaseModel):
    """Result of DuckDB query execution.

    Example:
        {
            "columns": ["account_code", "account_name", "balance"],
            "rows": [
                ["1000", "Cash", 50000.00],
                ["1100", "Accounts Receivable", 75000.00]
            ],
            "row_count": 2,
            "query": "SELECT * FROM trial_balance WHERE balance > 0",
            "execution_time_ms": 12.5
        }
    """

    columns: List[str] = Field(
        ...,
        description="Column names in result set"
    )

    rows: List[List[Any]] = Field(
        ...,
        description="Query result rows (each row is a list of values)"
    )

    row_count: int = Field(
        ...,
        ge=0,
        description="Number of rows returned"
    )

    query: str = Field(
        ...,
        description="The SQL query that was executed (for debugging)"
    )

    execution_time_ms: Optional[float] = Field(
        default=None,
        description="Query execution time in milliseconds"
    )

    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional query metadata"
    )
