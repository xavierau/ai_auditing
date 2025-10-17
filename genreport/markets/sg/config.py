"""Singapore market configuration (Placeholder for future implementation)."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class SGMarketConfig:
    """Singapore market-specific configuration.

    TODO: Implement full Singapore market configuration in Sprint 2+ / Market expansion.
    This is a placeholder to support the factory pattern.
    """

    # Jurisdiction
    jurisdiction: str = "SG"
    jurisdiction_full_name: str = "Singapore"

    # Currency
    currency: str = "SGD"
    currency_symbol: str = "S$"

    # Accounting Standards
    accounting_standard: str = "SFRS"  # Singapore Financial Reporting Standards
    sme_standard: str = "SFRS for Small Entities"
    gaap_equivalent: str = "SFRS"

    # Date and Number Formatting
    date_format: str = "DD/MM/YYYY"
    date_format_long: str = "DD MMMM YYYY"
    number_format_decimal: str = ","
    number_format_separator: str = "."

    # Regulatory Information
    company_ordinance: str = "Companies Act (Cap. 50)"
    regulatory_body: str = "ISCA"  # Institute of Singapore Chartered Accountants
    regulatory_body_full: str = "Institute of Singapore Chartered Accountants"
    stock_exchange: str = "SGX"  # Singapore Exchange

    # Paths
    templates_path: str = "templates/"
    knowledge_base_path: str = "knowledge_base/"
    standards_path: str = "knowledge_base/standards/"

    # Language
    primary_language: str = "en"
    secondary_language: str = "zh-CN"  # Simplified Chinese

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
sg_config = SGMarketConfig()
