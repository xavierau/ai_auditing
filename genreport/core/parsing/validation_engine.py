"""ValidationEngine for orchestrating multiple validators.

This module provides the ValidationEngine class that coordinates multiple
validators and aggregates their results following the Composite pattern.

Architecture:
- ValidationEngine: Orchestrates multiple validators
- Accepts any validator implementing the Validator protocol
- Aggregates results from all validators
- Handles validator exceptions gracefully
- Market-agnostic by design

Example:
    ```python
    from genreport.core.parsing.validation_engine import ValidationEngine
    from genreport.core.parsing.validators import (
        WorksheetReferenceValidator,
        CircularReferenceValidator,
        DataTypeValidator,
    )

    # Create engine with validators
    validators = [
        WorksheetReferenceValidator(),
        CircularReferenceValidator(),
        DataTypeValidator(),
    ]

    engine = ValidationEngine(validators=validators)

    # Run validation
    result = engine.validate(scan_result)

    if not result.is_valid:
        print(f"Found {result.error_count} errors")
        for error in result.errors:
            print(f"  {error.severity}: {error.message}")
    ```
"""

from typing import List
import logging

from genreport.core.parsing.validators import Validator
from genreport.core.parsing.parsing_models import (
    PreliminaryScanResult,
    ValidationResult,
    ValidationError,
    ValidationSeverity,
)

logger = logging.getLogger(__name__)


class ValidationEngine:
    """Orchestrates multiple validators following the Composite pattern.

    The ValidationEngine runs multiple validators on a PreliminaryScanResult
    and aggregates their results into a single ValidationResult. It handles
    validator exceptions gracefully and continues processing remaining validators.

    Attributes:
        validators: List of validator instances to run

    Example:
        ```python
        engine = ValidationEngine(validators=[
            WorksheetReferenceValidator(),
            CircularReferenceValidator(),
        ])

        result = engine.validate(scan_result)
        ```
    """

    def __init__(self, validators: List[Validator]):
        """Initialize ValidationEngine with list of validators.

        Args:
            validators: List of validator instances implementing Validator protocol
        """
        self.validators = validators

    def validate(self, scan_result: PreliminaryScanResult) -> ValidationResult:
        """Run all validators and aggregate results.

        This method runs each validator sequentially, aggregates errors,
        warnings, and info messages, and handles exceptions gracefully.
        If any validator raises an exception, it is caught and converted
        to an error message, and processing continues with remaining validators.

        Args:
            scan_result: The preliminary scan result to validate

        Returns:
            ValidationResult with aggregated errors, warnings, and info messages
        """
        all_errors: List[ValidationError] = []
        all_warnings: List[ValidationError] = []
        all_info_messages: List[ValidationError] = []
        validator_names: List[str] = []
        validators_run = 0

        for validator in self.validators:
            try:
                # Get validator name
                validator_name = validator.__class__.__name__
                validator_names.append(validator_name)

                # Run validator
                result = validator.validate(scan_result)
                validators_run += 1

                # Aggregate results
                all_errors.extend(result.errors)
                all_warnings.extend(result.warnings)
                all_info_messages.extend(result.info_messages)

                logger.debug(
                    f"{validator_name}: "
                    f"{result.error_count} errors, "
                    f"{result.warning_count} warnings"
                )

            except Exception as e:
                # Handle validator exceptions gracefully
                validator_name = validator.__class__.__name__
                validator_names.append(validator_name)
                validators_run += 1

                logger.error(f"{validator_name} raised exception: {e}", exc_info=True)

                # Convert exception to error
                all_errors.append(
                    ValidationError(
                        severity=ValidationSeverity.CRITICAL,
                        message=f"Validator '{validator_name}' failed with exception: {str(e)}",
                        field="validator_execution",
                        suggestion=f"Check validator implementation or contact support",
                        metadata={"validator": validator_name, "exception_type": type(e).__name__},
                    )
                )

        # Determine overall validity
        is_valid = len(all_errors) == 0

        # Build aggregated result
        return ValidationResult(
            is_valid=is_valid,
            errors=all_errors,
            warnings=all_warnings,
            info_messages=all_info_messages,
            validation_context={
                "validators_run": validators_run,
                "validator_names": validator_names,
                "total_errors": len(all_errors),
                "total_warnings": len(all_warnings),
                "total_info": len(all_info_messages),
            },
        )
