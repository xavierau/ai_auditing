"""Market configuration factory pattern.

This module provides a factory function to get market-specific configurations
without hardcoding jurisdiction logic in the core application.

CRITICAL: This is the ONLY place where market-specific imports are allowed
from core/. All market logic must be injected through this factory.
"""

from typing import Union


def get_market_config(jurisdiction: str) -> Union[any]:
    """Get market-specific configuration.

    This factory function returns the appropriate market configuration
    based on the jurisdiction code. It follows the factory pattern to
    avoid hardcoding market-specific logic throughout the application.

    Args:
        jurisdiction: Jurisdiction code (HK, SG, AU)

    Returns:
        Market configuration object for the specified jurisdiction

    Raises:
        ValueError: If jurisdiction is not supported

    Example:
        >>> config = get_market_config("HK")
        >>> config.currency
        'HKD'
        >>> config.accounting_standard
        'HKFRS'
    """
    if jurisdiction == "HK":
        from genreport.markets.hk.config import HKMarketConfig

        return HKMarketConfig()

    elif jurisdiction == "SG":
        # TODO: Implement Singapore market (Sprint 2+ / Market expansion)
        from genreport.markets.sg.config import SGMarketConfig

        return SGMarketConfig()

    elif jurisdiction == "AU":
        # TODO: Implement Australia market (Sprint 2+ / Market expansion)
        from genreport.markets.au.config import AUMarketConfig

        return AUMarketConfig()

    else:
        supported_jurisdictions = ["HK", "SG", "AU"]
        raise ValueError(
            f"Unsupported jurisdiction: {jurisdiction}. "
            f"Supported jurisdictions: {', '.join(supported_jurisdictions)}"
        )


def get_supported_jurisdictions() -> list[str]:
    """Get list of supported jurisdiction codes.

    Returns:
        List of jurisdiction codes
    """
    return ["HK", "SG", "AU"]


def validate_jurisdiction(jurisdiction: str) -> bool:
    """Validate if a jurisdiction is supported.

    Args:
        jurisdiction: Jurisdiction code to validate

    Returns:
        True if jurisdiction is supported, False otherwise
    """
    return jurisdiction in get_supported_jurisdictions()
