"""Australia market configuration (Placeholder for future implementation)."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class AUMarketConfig:
    """Australia market-specific configuration.

    TODO: Implement full Australia market configuration in Sprint 2+ / Market expansion.
    This is a placeholder to support the factory pattern.
    """

    # Jurisdiction
    jurisdiction: str = "AU"
    jurisdiction_full_name: str = "Australia"

    # Currency
    currency: str = "AUD"
    currency_symbol: str = "A$"

    # Accounting Standards
    accounting_standard: str = "AASB"  # Australian Accounting Standards Board
    sme_standard: str = "AASB for Special Purpose Financial Statements"
    gaap_equivalent: str = "AASB"

    # Date and Number Formatting
    date_format: str = "DD/MM/YYYY"
    date_format_long: str = "DD MMMM YYYY"
    number_format_decimal: str = ","
    number_format_separator: str = "."

    # Regulatory Information
    company_ordinance: str = "Corporations Act 2001"
    regulatory_body: str = "CPA Australia / CA ANZ"
    regulatory_body_full: str = "CPA Australia / Chartered Accountants Australia and New Zealand"
    stock_exchange: str = "ASX"  # Australian Securities Exchange

    # Paths
    templates_path: str = "templates/"
    knowledge_base_path: str = "knowledge_base/"
    standards_path: str = "knowledge_base/standards/"

    # Language
    primary_language: str = "en"
    secondary_language: str = "en"  # English only

    def to_dict(self) -> Dict[str, any]:
        """Convert configuration to dictionary."""
        return {
            "jurisdiction": self.jurisdiction,
            "jurisdiction_full_name": self.jurisdiction_full_name,
            "currency": self.currency,
            "currency_symbol": self.currency_symbol,
            "accounting_standard": self.accounting_standard,
            "date_format": self.date_format,
            "regulatory_body": self.regulatory_body,
        }


# Singleton instance
au_config = AUMarketConfig()
