"""HKFRS Validator for Hong Kong market-specific validation.

This module provides the HKFRSValidator class for validating that Hong Kong
entities are using the appropriate accounting standards (HKFRS vs SME-FRS)
and comply with HKICPA requirements.

Architecture:
- Implements Validator protocol from core/parsing/validators.py
- Market-specific (Hong Kong only)
- Validates accounting standard selection based on SME thresholds
- Checks currency and jurisdiction compliance
- Provides HKICPA compliance information

Example:
    ```python
    from genreport.markets.hk.validators.hkfrs_validator import HKFRSValidator
    from genreport.markets.hk.config import HKMarketConfig

    config = HKMarketConfig()
    validator = HKFRSValidator(config)

    result = validator.validate(scan_result)

    if not result.is_valid:
        print(f"Found {result.error_count} HK compliance errors")
    ```
"""

from typing import List, Optional
import logging

from genreport.markets.hk.config import HKMarketConfig, hk_config
from genreport.core.parsing.parsing_models import (
    PreliminaryScanResult,
    ValidationResult,
    ValidationError,
    ValidationSeverity,
)

logger = logging.getLogger(__name__)


class HKFRSValidator:
    """Validator for Hong Kong HKFRS compliance.

    This validator checks that Hong Kong entities are using the appropriate
    accounting standards based on their size (HKFRS vs SME-FRS) and comply
    with HKICPA requirements. It implements the Validator protocol for use
    with ValidationEngine.

    Validation Rules:
    - Large entities (above SME thresholds) must not use SME-FRS
    - SME entities should use SME-FRS (warning if using HKFRS)
    - Jurisdiction must be HK
    - Currency should be HKD (warning if not)
    - Accounting standard must be specified

    Attributes:
        config: HKMarketConfig instance with HK-specific settings

    Example:
        ```python
        validator = HKFRSValidator()
        result = validator.validate(scan_result)

        if not result.is_valid:
            for error in result.errors:
                print(f"ERROR: {error.message}")
        ```
    """

    def __init__(self, config: Optional[HKMarketConfig] = None):
        """Initialize HKFRSValidator with market config.

        Args:
            config: HKMarketConfig instance (defaults to singleton hk_config)
        """
        self.config = config if config is not None else hk_config

    def validate(self, scan_result: PreliminaryScanResult) -> ValidationResult:
        """Validate Hong Kong market compliance.

        This method checks:
        1. Jurisdiction is HK
        2. Accounting standard is appropriate for entity size
        3. Currency is HKD (warning if not)
        4. All required metadata is present

        Args:
            scan_result: The preliminary scan result to validate

        Returns:
            ValidationResult with HK-specific validation findings
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []
        info_messages: List[ValidationError] = []

        # Extract metadata
        metadata = scan_result.scan_metadata or {}
        jurisdiction = metadata.get("jurisdiction")
        accounting_standard = metadata.get("accounting_standard")
        currency = metadata.get("currency")

        # Entity metrics for SME determination
        revenue = metadata.get("entity_revenue")
        assets = metadata.get("entity_assets")
        employees = metadata.get("entity_employees")

        # Validation 1: Check jurisdiction
        if jurisdiction != "HK":
            errors.append(
                ValidationError(
                    severity=ValidationSeverity.ERROR,
                    message=f"HKFRSValidator is for Hong Kong jurisdiction only, but got '{jurisdiction}'",
                    field="jurisdiction",
                    suggestion="Use the appropriate validator for the specified jurisdiction or set jurisdiction to 'HK'",
                )
            )
            # Stop validation if wrong jurisdiction
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                info_messages=info_messages,
                validation_context={
                    "validator": "HKFRSValidator",
                    "regulatory_body": self.config.regulatory_body,
                },
            )

        # Validation 2: Check accounting standard is specified
        if not accounting_standard:
            warnings.append(
                ValidationError(
                    severity=ValidationSeverity.WARNING,
                    message="No accounting standard specified for Hong Kong entity",
                    field="accounting_standard",
                    suggestion=f"Specify either '{self.config.accounting_standard}' or '{self.config.sme_standard}'",
                )
            )
        else:
            # Validation 3: Check standard selection appropriateness
            self._validate_standard_selection(
                accounting_standard=accounting_standard,
                revenue=revenue,
                assets=assets,
                employees=employees,
                errors=errors,
                warnings=warnings,
            )

        # Validation 4: Check currency (warning, not error)
        if currency and currency != self.config.currency:
            warnings.append(
                ValidationError(
                    severity=ValidationSeverity.WARNING,
                    message=f"Currency is '{currency}' but HKD is standard for Hong Kong entities",
                    field="currency",
                    suggestion=f"Consider using {self.config.currency} for Hong Kong reporting",
                    metadata={"expected_currency": self.config.currency, "actual_currency": currency},
                )
            )

        # Validation 5: Check if we can determine SME status
        if not accounting_standard:
            # Already warned above
            pass
        elif revenue is None and assets is None and employees is None:
            # No entity metrics - cannot verify SME status
            info_messages.append(
                ValidationError(
                    severity=ValidationSeverity.INFO,
                    message="Entity metrics not provided - cannot verify SME qualification",
                    field="entity_metrics",
                    suggestion="Provide revenue, assets, or employees to validate accounting standard selection",
                )
            )

        # Add info about regulatory compliance
        info_messages.append(
            ValidationError(
                severity=ValidationSeverity.INFO,
                message=f"Hong Kong entities must comply with {self.config.regulatory_body_full} standards",
                field="regulatory_compliance",
                metadata={
                    "regulatory_body": self.config.regulatory_body,
                    "company_ordinance": self.config.company_ordinance,
                },
            )
        )

        logger.debug(
            f"HKFRSValidator completed: {len(errors)} errors, {len(warnings)} warnings"
        )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            info_messages=info_messages,
            validation_context={
                "validator": "HKFRSValidator",
                "regulatory_body": self.config.regulatory_body,
                "jurisdiction": self.config.jurisdiction,
                "errors_found": len(errors),
                "warnings_found": len(warnings),
            },
        )

    def _validate_standard_selection(
        self,
        accounting_standard: str,
        revenue: Optional[float],
        assets: Optional[float],
        employees: Optional[int],
        errors: List[ValidationError],
        warnings: List[ValidationError],
    ) -> None:
        """Validate that the accounting standard is appropriate for entity size.

        Args:
            accounting_standard: The accounting standard being used
            revenue: Entity revenue in HKD (optional)
            assets: Entity assets in HKD (optional)
            employees: Number of employees (optional)
            errors: List to append errors to
            warnings: List to append warnings to
        """
        # Check if entity qualifies as SME
        is_sme = self.config.is_sme_entity(revenue, assets, employees)

        # If we have enough data to determine SME status
        if revenue is not None or assets is not None or employees is not None:
            if accounting_standard == self.config.sme_standard:
                # Using SME-FRS
                if not is_sme:
                    # Large entity using SME-FRS (not allowed)
                    errors.append(
                        ValidationError(
                            severity=ValidationSeverity.ERROR,
                            message=f"Entity does not qualify for {self.config.sme_standard} based on size thresholds",
                            field="accounting_standard",
                            suggestion=f"Use {self.config.accounting_standard} for entities exceeding SME thresholds",
                            metadata={
                                "sme_revenue_threshold": self.config.sme_revenue_threshold,
                                "sme_assets_threshold": self.config.sme_assets_threshold,
                                "sme_employees_threshold": self.config.sme_employees_threshold,
                            },
                        )
                    )
            elif accounting_standard == self.config.accounting_standard:
                # Using HKFRS
                if is_sme:
                    # SME entity using HKFRS (allowed but not optimal)
                    warnings.append(
                        ValidationError(
                            severity=ValidationSeverity.WARNING,
                            message=f"Entity qualifies for {self.config.sme_standard} which may be simpler than {self.config.accounting_standard}",
                            field="accounting_standard",
                            suggestion=f"Consider using {self.config.sme_standard} for simplified reporting requirements",
                            metadata={
                                "qualifies_for_sme": True,
                                "current_standard": accounting_standard,
                            },
                        )
                    )
            else:
                # Unrecognized accounting standard for HK
                warnings.append(
                    ValidationError(
                        severity=ValidationSeverity.WARNING,
                        message=f"Unrecognized accounting standard '{accounting_standard}' for Hong Kong",
                        field="accounting_standard",
                        suggestion=f"Expected '{self.config.accounting_standard}' or '{self.config.sme_standard}'",
                        metadata={"provided_standard": accounting_standard},
                    )
                )
