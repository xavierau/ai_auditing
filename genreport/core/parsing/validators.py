"""Validators for Excel parsing results.

This module provides market-agnostic validators that check the integrity
and consistency of parsing results. Validators follow the Open/Closed Principle
and can be composed via dependency injection.

Architecture:
- Validator: Protocol defining the validation interface
- Concrete validators: WorksheetReferenceValidator, CircularReferenceValidator, DataTypeValidator
- Market-specific validators: Implemented in markets/{jurisdiction}/validators/
"""

from typing import Protocol, Set, List, Dict
from genreport.core.parsing.parsing_models import (
    PreliminaryScanResult,
    ValidationResult,
    ValidationError,
    ValidationSeverity,
)


class Validator(Protocol):
    """Protocol for validation components.

    All validators must implement this interface, enabling composition
    and dependency injection in the ValidationEngine.

    Example:
        ```python
        class CustomValidator:
            def validate(self, scan_result: PreliminaryScanResult) -> ValidationResult:
                # Validation logic here
                return ValidationResult(is_valid=True)

        # Usage
        validator = CustomValidator()
        result = validator.validate(scan_result)
        ```
    """

    def validate(self, scan_result: PreliminaryScanResult) -> ValidationResult:
        """Validate a preliminary scan result.

        Args:
            scan_result: The preliminary scan result to validate

        Returns:
            ValidationResult with errors, warnings, and info messages
        """
        ...


class WorksheetReferenceValidator:
    """Validates that all referenced worksheets exist in the workbook.

    This validator checks that every worksheet code mentioned in
    referenced_codes actually exists in the worksheet_analyses list.

    Example:
        ```python
        validator = WorksheetReferenceValidator()
        result = validator.validate(scan_result)

        if not result.is_valid:
            for error in result.errors:
                print(f"{error.location}: {error.message}")
        ```
    """

    def validate(self, scan_result: PreliminaryScanResult) -> ValidationResult:
        """Validate worksheet references.

        Args:
            scan_result: The preliminary scan result to validate

        Returns:
            ValidationResult with errors for missing references
        """
        errors: List[ValidationError] = []

        # Build set of existing worksheet names
        existing_sheets = {
            analysis.sheet_name for analysis in scan_result.worksheet_analyses
        }

        # Check each worksheet's references
        for analysis in scan_result.worksheet_analyses:
            for ref_code in analysis.referenced_codes:
                # Check if reference exists (exact match or partial match)
                matching_sheets = [
                    sheet
                    for sheet in existing_sheets
                    if ref_code in sheet or sheet.startswith(ref_code)
                ]

                if not matching_sheets:
                    errors.append(
                        ValidationError(
                            severity=ValidationSeverity.ERROR,
                            message=f"Worksheet '{analysis.sheet_name}' references '{ref_code}' which does not exist",
                            location=analysis.sheet_name,
                            field="referenced_codes",
                            suggestion=f"Remove reference to '{ref_code}' or add missing worksheet",
                        )
                    )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            validation_context={
                "validator": "WorksheetReferenceValidator",
                "sheets_checked": len(scan_result.worksheet_analyses),
            },
        )


class CircularReferenceValidator:
    """Detects circular references between worksheets using DFS.

    This validator uses depth-first search to detect cycles in the
    worksheet dependency graph. Circular references can cause infinite
    loops in calculation chains and should be flagged as warnings.

    Example:
        ```python
        validator = CircularReferenceValidator()
        result = validator.validate(scan_result)

        if result.warning_count > 0:
            print("Found circular references:")
            for warning in result.warnings:
                print(f"  {warning.message}")
        ```
    """

    def validate(self, scan_result: PreliminaryScanResult) -> ValidationResult:
        """Validate for circular references using DFS.

        Args:
            scan_result: The preliminary scan result to validate

        Returns:
            ValidationResult with warnings for circular references
        """
        errors: List[ValidationError] = []

        # Build adjacency list for graph
        graph: Dict[str, List[str]] = {}
        existing_sheets = {
            analysis.sheet_name for analysis in scan_result.worksheet_analyses
        }

        for analysis in scan_result.worksheet_analyses:
            graph[analysis.sheet_name] = []

            # Add edges for references that exist
            for ref_code in analysis.referenced_codes:
                matching_sheets = [
                    sheet
                    for sheet in existing_sheets
                    if ref_code in sheet or sheet.startswith(ref_code)
                ]
                graph[analysis.sheet_name].extend(matching_sheets)

        # DFS to detect cycles
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        cycles_found: List[List[str]] = []

        def dfs(node: str, path: List[str]) -> None:
            """Depth-first search to detect cycles."""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path.copy())
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start_idx = path.index(neighbor)
                    cycle = path[cycle_start_idx:] + [neighbor]
                    cycles_found.append(cycle)

            rec_stack.remove(node)

        # Run DFS from each node
        for sheet in graph.keys():
            if sheet not in visited:
                dfs(sheet, [])

        # Create errors for each cycle found
        seen_cycles: Set[str] = set()
        for cycle in cycles_found:
            # Normalize cycle representation to avoid duplicates
            cycle_key = "->".join(sorted(set(cycle)))

            if cycle_key not in seen_cycles:
                seen_cycles.add(cycle_key)

                # Check for self-reference
                if len(set(cycle)) == 1:
                    errors.append(
                        ValidationError(
                            severity=ValidationSeverity.WARNING,
                            message=f"Worksheet '{cycle[0]}' contains a self-reference",
                            location=cycle[0],
                            field="referenced_codes",
                            suggestion="Remove self-reference to avoid circular calculation",
                        )
                    )
                else:
                    cycle_path = " -> ".join(cycle)
                    errors.append(
                        ValidationError(
                            severity=ValidationSeverity.WARNING,
                            message=f"Circular reference detected: {cycle_path}",
                            location=cycle[0],
                            field="referenced_codes",
                            suggestion="Break the circular reference by removing one of the dependencies",
                            metadata={"cycle": cycle},
                        )
                    )

        return ValidationResult(
            is_valid=len(errors) == 0,
            warnings=errors,  # Circular references are warnings, not errors
            validation_context={
                "validator": "CircularReferenceValidator",
                "cycles_found": len(cycles_found),
            },
        )


class DataTypeValidator:
    """Validates data types and consistency in parsing results.

    This validator checks:
    - Confidence scores are in valid range (0.0 to 1.0)
    - Importance scores are in valid range (0.0 to 1.0)
    - total_sheets matches actual worksheet count
    - Required fields are not empty

    Example:
        ```python
        validator = DataTypeValidator()
        result = validator.validate(scan_result)

        if not result.is_valid:
            print(f"Found {result.error_count} data type issues")
        ```
    """

    def validate(self, scan_result: PreliminaryScanResult) -> ValidationResult:
        """Validate data types and consistency.

        Args:
            scan_result: The preliminary scan result to validate

        Returns:
            ValidationResult with errors for data type issues
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []

        # Check total_sheets consistency
        actual_count = len(scan_result.worksheet_analyses)
        if scan_result.total_sheets != actual_count:
            errors.append(
                ValidationError(
                    severity=ValidationSeverity.ERROR,
                    message=f"total_sheets ({scan_result.total_sheets}) does not match "
                    f"worksheet_analyses count ({actual_count})",
                    field="total_sheets",
                    suggestion=f"Set total_sheets to {actual_count}",
                )
            )

        # Check coding system confidence (should be caught by Pydantic, but double-check)
        if not (0.0 <= scan_result.coding_system.confidence <= 1.0):
            errors.append(
                ValidationError(
                    severity=ValidationSeverity.ERROR,
                    message=f"Confidence score {scan_result.coding_system.confidence} is outside valid range [0.0, 1.0]",
                    field="coding_system.confidence",
                    suggestion="Set confidence to a value between 0.0 and 1.0",
                )
            )

        # Check each worksheet analysis
        for analysis in scan_result.worksheet_analyses:
            # Check importance score range
            if not (0.0 <= analysis.importance_score <= 1.0):
                errors.append(
                    ValidationError(
                        severity=ValidationSeverity.ERROR,
                        message=f"Importance score {analysis.importance_score} is outside valid range [0.0, 1.0]",
                        location=analysis.sheet_name,
                        field="importance_score",
                        suggestion="Set importance_score to a value between 0.0 and 1.0",
                    )
                )

            # Check sheet name not empty
            if not analysis.sheet_name or analysis.sheet_name.strip() == "":
                errors.append(
                    ValidationError(
                        severity=ValidationSeverity.ERROR,
                        message="Sheet name is empty or contains only whitespace",
                        field="sheet_name",
                        suggestion="Provide a valid sheet name",
                    )
                )

            # Warning if both is_summary and is_supporting are True (unusual but not invalid)
            if analysis.is_summary and analysis.is_supporting:
                warnings.append(
                    ValidationError(
                        severity=ValidationSeverity.WARNING,
                        message=f"Worksheet '{analysis.sheet_name}' is marked as both summary and supporting",
                        location=analysis.sheet_name,
                        field="is_summary, is_supporting",
                        suggestion="Verify this worksheet should have both flags set",
                    )
                )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            validation_context={
                "validator": "DataTypeValidator",
                "sheets_validated": len(scan_result.worksheet_analyses),
            },
        )
