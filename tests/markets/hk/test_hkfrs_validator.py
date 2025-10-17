"""Tests for HK HKFRS Validator.

Following TDD approach - these tests define expected HK-specific validation behavior.
"""

import pytest
from genreport.core.parsing.parsing_models import (
    PreliminaryScanResult,
    CodingSystemResult,
    WorksheetAnalysisResult,
    ValidationSeverity,
)


class TestHKFRSValidatorInitialization:
    """Test suite for HKFRSValidator initialization."""

    def test_validator_accepts_hk_config(self):
        """Test that HKFRSValidator accepts HKMarketConfig."""
        from genreport.markets.hk.config import HKMarketConfig
        from genreport.markets.hk.validators.hkfrs_validator import HKFRSValidator

        config = HKMarketConfig()
        validator = HKFRSValidator(config)

        assert validator is not None
        assert validator.config == config

    def test_validator_has_default_config(self):
        """Test that validator can use default HK config if none provided."""
        from genreport.markets.hk.validators.hkfrs_validator import HKFRSValidator

        validator = HKFRSValidator()

        assert validator is not None
        assert validator.config is not None
        assert validator.config.jurisdiction == "HK"


class TestHKFRSValidatorStandardSelection:
    """Test suite for validating correct accounting standard selection."""

    def test_validator_accepts_hkfrs_for_large_entity(self):
        """Test that HKFRS is accepted for entities above SME thresholds."""
        from genreport.markets.hk.validators.hkfrs_validator import HKFRSValidator
        from genreport.markets.hk.config import HKMarketConfig

        config = HKMarketConfig()
        validator = HKFRSValidator(config)

        # Create scan result with entity metadata (large entity)
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
            scan_metadata={
                "jurisdiction": "HK",
                "accounting_standard": "HKFRS",
                "entity_revenue": 150_000_000,  # Above SME threshold
                "entity_assets": 120_000_000,  # Above SME threshold
            },
        )

        result = validator.validate(scan_result)

        assert result.is_valid is True
        assert result.error_count == 0

    def test_validator_warns_if_sme_uses_hkfrs(self):
        """Test that validator warns if SME-qualified entity uses HKFRS."""
        from genreport.markets.hk.validators.hkfrs_validator import HKFRSValidator

        validator = HKFRSValidator()

        # Create scan result for SME entity using HKFRS (not optimal)
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
            scan_metadata={
                "jurisdiction": "HK",
                "accounting_standard": "HKFRS",
                "entity_revenue": 80_000_000,  # Below SME threshold
                "entity_assets": 70_000_000,  # Below SME threshold
                "entity_employees": 50,  # Below SME threshold
            },
        )

        result = validator.validate(scan_result)

        # Should warn but not error (HKFRS is still valid, just not optimal)
        assert result.is_valid is True
        assert result.warning_count >= 1
        assert any("SME-FRS" in warn.message for warn in result.warnings)

    def test_validator_accepts_sme_frs_for_sme_entity(self):
        """Test that SME-FRS is accepted for entities below SME thresholds."""
        from genreport.markets.hk.validators.hkfrs_validator import HKFRSValidator

        validator = HKFRSValidator()

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
            scan_metadata={
                "jurisdiction": "HK",
                "accounting_standard": "SME-FRS",
                "entity_revenue": 80_000_000,
                "entity_assets": 70_000_000,
                "entity_employees": 50,
            },
        )

        result = validator.validate(scan_result)

        assert result.is_valid is True
        assert result.error_count == 0

    def test_validator_errors_if_large_entity_uses_sme_frs(self):
        """Test that validator errors if large entity uses SME-FRS."""
        from genreport.markets.hk.validators.hkfrs_validator import HKFRSValidator

        validator = HKFRSValidator()

        # Large entity using SME-FRS (not allowed)
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
            scan_metadata={
                "jurisdiction": "HK",
                "accounting_standard": "SME-FRS",
                "entity_revenue": 150_000_000,  # Above SME threshold
                "entity_assets": 120_000_000,  # Above SME threshold
            },
        )

        result = validator.validate(scan_result)

        assert result.is_valid is False
        assert result.error_count >= 1
        assert any("not qualify" in err.message or "HKFRS" in err.message for err in result.errors)


class TestHKFRSValidatorJurisdictionChecks:
    """Test suite for jurisdiction-specific validation."""

    def test_validator_accepts_hk_jurisdiction(self):
        """Test that validator accepts HK jurisdiction."""
        from genreport.markets.hk.validators.hkfrs_validator import HKFRSValidator

        validator = HKFRSValidator()

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
            scan_metadata={
                "jurisdiction": "HK",
                "accounting_standard": "HKFRS",
            },
        )

        result = validator.validate(scan_result)

        assert result.is_valid is True

    def test_validator_errors_if_wrong_jurisdiction(self):
        """Test that validator errors if jurisdiction is not HK."""
        from genreport.markets.hk.validators.hkfrs_validator import HKFRSValidator

        validator = HKFRSValidator()

        # Singapore jurisdiction (wrong validator)
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
            scan_metadata={
                "jurisdiction": "SG",  # Wrong jurisdiction!
                "accounting_standard": "SFRS",
            },
        )

        result = validator.validate(scan_result)

        assert result.is_valid is False
        assert result.error_count >= 1
        assert any("Hong Kong" in err.message or "HK" in err.message for err in result.errors)

    def test_validator_warns_if_currency_not_hkd(self):
        """Test that validator warns if currency is not HKD for HK jurisdiction."""
        from genreport.markets.hk.validators.hkfrs_validator import HKFRSValidator

        validator = HKFRSValidator()

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
            scan_metadata={
                "jurisdiction": "HK",
                "accounting_standard": "HKFRS",
                "currency": "USD",  # Not HKD!
            },
        )

        result = validator.validate(scan_result)

        # Warning, not error (functional currency can differ from jurisdiction)
        assert result.is_valid is True
        assert result.warning_count >= 1
        assert any("HKD" in warn.message or "currency" in warn.message.lower() for warn in result.warnings)


class TestHKFRSValidatorMissingMetadata:
    """Test suite for handling missing metadata."""

    def test_validator_warns_if_no_accounting_standard_specified(self):
        """Test that validator warns if accounting standard is missing."""
        from genreport.markets.hk.validators.hkfrs_validator import HKFRSValidator

        validator = HKFRSValidator()

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
            scan_metadata={
                "jurisdiction": "HK",
                # Missing accounting_standard
            },
        )

        result = validator.validate(scan_result)

        assert result.is_valid is True
        assert result.warning_count >= 1
        assert any("accounting standard" in warn.message.lower() for warn in result.warnings)

    def test_validator_handles_missing_entity_metrics_gracefully(self):
        """Test that validator handles missing entity metrics without crashing."""
        from genreport.markets.hk.validators.hkfrs_validator import HKFRSValidator

        validator = HKFRSValidator()

        # No entity metrics provided
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
            scan_metadata={
                "jurisdiction": "HK",
                "accounting_standard": "HKFRS",
                # No revenue, assets, or employees
            },
        )

        result = validator.validate(scan_result)

        # Should not crash - should warn about inability to verify SME status
        assert result is not None
        assert result.info_messages or result.warnings  # Should have some message


class TestHKFRSValidatorComplianceChecks:
    """Test suite for HK-specific compliance validation."""

    def test_validator_checks_hkicpa_compliance(self):
        """Test that validator provides info about HKICPA compliance requirements."""
        from genreport.markets.hk.validators.hkfrs_validator import HKFRSValidator

        validator = HKFRSValidator()

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
            scan_metadata={
                "jurisdiction": "HK",
                "accounting_standard": "HKFRS",
            },
        )

        result = validator.validate(scan_result)

        # Should include info about HKICPA compliance
        assert result.info_messages or result.validation_context
        assert result.validation_context.get("regulatory_body") == "HKICPA"


class TestHKFRSValidatorIntegration:
    """Integration tests for HKFRSValidator with ValidationEngine."""

    def test_validator_implements_validator_protocol(self):
        """Test that HKFRSValidator implements the Validator protocol."""
        from genreport.markets.hk.validators.hkfrs_validator import HKFRSValidator
        from genreport.core.parsing.validators import Validator
        from typing import Protocol, runtime_checkable

        validator = HKFRSValidator()

        # Should have validate method
        assert hasattr(validator, "validate")
        assert callable(validator.validate)

    def test_validator_works_with_validation_engine(self):
        """Test that HKFRSValidator can be used in ValidationEngine."""
        from genreport.markets.hk.validators.hkfrs_validator import HKFRSValidator
        from genreport.core.parsing.validation_engine import ValidationEngine
        from genreport.core.parsing.validators import DataTypeValidator

        validators = [
            DataTypeValidator(),  # Generic validator
            HKFRSValidator(),  # Market-specific validator
        ]

        engine = ValidationEngine(validators=validators)

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
            scan_metadata={
                "jurisdiction": "HK",
                "accounting_standard": "HKFRS",
            },
        )

        result = engine.validate(scan_result)

        # Both validators should run
        assert result.validation_context["validators_run"] == 2
        assert "HKFRSValidator" in result.validation_context["validator_names"]
        assert "DataTypeValidator" in result.validation_context["validator_names"]
