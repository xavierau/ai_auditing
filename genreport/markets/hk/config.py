"""Hong Kong market configuration."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class HKMarketConfig:
    """Hong Kong market-specific configuration.

    This configuration encapsulates all Hong Kong-specific settings
    including accounting standards, currency, regulatory requirements,
    and formatting preferences.
    """

    # Jurisdiction
    jurisdiction: str = "HK"
    jurisdiction_full_name: str = "Hong Kong"

    # Currency
    currency: str = "HKD"
    currency_symbol: str = "HK$"

    # Accounting Standards
    accounting_standard: str = "HKFRS"  # Hong Kong Financial Reporting Standards
    sme_standard: str = "SME-FRS"  # SME Financial Reporting Standards
    gaap_equivalent: str = "HKFRS"  # Generally Accepted Accounting Principles equivalent

    # Date and Number Formatting
    date_format: str = "DD/MM/YYYY"
    date_format_long: str = "DD MMMM YYYY"
    number_format_decimal: str = ","  # Thousands separator
    number_format_separator: str = "."  # Decimal separator

    # Regulatory Information
    company_ordinance: str = "Companies Ordinance (Cap. 622)"
    regulatory_body: str = "HKICPA"  # Hong Kong Institute of Certified Public Accountants
    regulatory_body_full: str = "Hong Kong Institute of Certified Public Accountants"
    stock_exchange: str = "HKEX"  # Hong Kong Stock Exchange

    # Paths (relative to markets/hk/)
    templates_path: str = "templates/"
    knowledge_base_path: str = "knowledge_base/"
    standards_path: str = "knowledge_base/standards/"

    # SME Thresholds (for determining if SME-FRS applies)
    sme_revenue_threshold: int = 100_000_000  # HKD 100M
    sme_assets_threshold: int = 100_000_000  # HKD 100M
    sme_employees_threshold: int = 100

    # Tax Information
    tax_authority: str = "IRD"  # Inland Revenue Department
    tax_authority_full: str = "Inland Revenue Department"
    corporate_tax_rate: float = 0.165  # 16.5% (standard rate)
    profits_tax_rate_tier1: float = 0.0825  # 8.25% (first HKD 2M)
    profits_tax_threshold: int = 2_000_000  # HKD 2M

    # Audit Requirements
    audit_required_threshold: int = 0  # All companies require audit in HK
    audit_exemption_available: bool = False

    # Language
    primary_language: str = "en"  # English
    secondary_language: str = "zh-HK"  # Traditional Chinese (Hong Kong)

    def to_dict(self) -> Dict[str, any]:
        """Convert configuration to dictionary.

        Returns:
            Dictionary representation of configuration
        """
        return {
            "jurisdiction": self.jurisdiction,
            "jurisdiction_full_name": self.jurisdiction_full_name,
            "currency": self.currency,
            "currency_symbol": self.currency_symbol,
            "accounting_standard": self.accounting_standard,
            "sme_standard": self.sme_standard,
            "date_format": self.date_format,
            "regulatory_body": self.regulatory_body,
            "company_ordinance": self.company_ordinance,
        }

    def is_sme_entity(
        self, revenue: float = None, assets: float = None, employees: int = None
    ) -> bool:
        """Determine if an entity qualifies as SME under HK rules.

        An entity is considered SME if it meets 2 of 3 criteria:
        - Revenue < HKD 100M
        - Assets < HKD 100M
        - Employees < 100

        Args:
            revenue: Annual revenue in HKD
            assets: Total assets in HKD
            employees: Number of employees

        Returns:
            True if entity qualifies as SME, False otherwise
        """
        criteria_met = 0

        if revenue is not None and revenue < self.sme_revenue_threshold:
            criteria_met += 1

        if assets is not None and assets < self.sme_assets_threshold:
            criteria_met += 1

        if employees is not None and employees < self.sme_employees_threshold:
            criteria_met += 1

        return criteria_met >= 2

    def get_applicable_standard(
        self, revenue: float = None, assets: float = None, employees: int = None
    ) -> str:
        """Get the applicable accounting standard for an entity.

        Args:
            revenue: Annual revenue in HKD
            assets: Total assets in HKD
            employees: Number of employees

        Returns:
            Applicable accounting standard (HKFRS or SME-FRS)
        """
        if self.is_sme_entity(revenue, assets, employees):
            return self.sme_standard
        return self.accounting_standard

    def format_currency(self, amount: float) -> str:
        """Format amount as Hong Kong currency.

        Args:
            amount: Amount to format

        Returns:
            Formatted currency string
        """
        return f"{self.currency_symbol} {amount:,.2f}"

    def format_date(self, date: str) -> str:
        """Format date according to Hong Kong conventions.

        Args:
            date: Date string

        Returns:
            Formatted date string
        """
        # Placeholder - actual implementation would parse and format
        return date


# Singleton instance
hk_config = HKMarketConfig()
