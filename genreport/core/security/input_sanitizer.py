"""Input sanitization for Excel data.

SECURITY: Removes Excel formulas and potential script injections
to prevent code execution and XSS attacks.
"""

import re
from typing import Any

import pandas as pd


class InputSanitizer:
    """Input sanitization for Excel data.

    SECURITY: Removes Excel formulas and potential script injections
    to prevent code execution and XSS attacks.

    ARCHITECTURE: Market-agnostic security component.
    """

    # Dangerous patterns to remove (case-insensitive)
    DANGEROUS_PATTERNS = [
        r"<script.*?>.*?</script>",  # Script tags with content
        r"<script[^>]*>",  # Opening script tags
        r"</script>",  # Closing script tags
        r"javascript:",  # JavaScript protocol
        r"on\w+\s*=",  # Event handlers (onclick, onload, etc.)
        r"<iframe[^>]*>",  # Opening iframe tags
        r"</iframe>",  # Closing iframe tags
    ]

    @staticmethod
    def strip_formulas(df: pd.DataFrame) -> pd.DataFrame:
        """Remove Excel formulas from DataFrame.

        Args:
            df: Input DataFrame with potential formulas

        Returns:
            DataFrame with formulas stripped

        SECURITY: Excel formulas can contain:
        - Code injection (=cmd|'/c calc'!A1)
        - Data exfiltration (=HYPERLINK)
        - System commands (=SYSTEM)
        """
        df_copy = df.copy()

        for col in df_copy.columns:
            if df_copy[col].dtype == "object":  # Only process string columns
                df_copy[col] = df_copy[col].apply(
                    lambda x: (
                        InputSanitizer._strip_formula_prefix(str(x)) if isinstance(x, str) else x
                    )
                )

        return df_copy

    @staticmethod
    def _strip_formula_prefix(value: str) -> str:
        """Strip formula prefixes (=, +, @) from value.

        Args:
            value: String value that may start with formula prefix

        Returns:
            Value with formula prefix removed
        """
        if value.startswith("=") or value.startswith("+") or value.startswith("@"):
            # Remove the prefix and any leading/trailing whitespace
            return value[1:].strip()

        return value

    @staticmethod
    def sanitize_cell_value(value: Any) -> Any:
        """Sanitize individual cell value.

        Args:
            value: Cell value (any type)

        Returns:
            Sanitized value

        SECURITY: Removes:
        - Formula prefixes (=, +, @)
        - Script tags
        - JavaScript protocol
        - Event handlers (onclick, onload, etc.)
        - iframe tags
        """
        # Only sanitize strings
        if not isinstance(value, str):
            return value

        # Empty strings and whitespace-only strings
        if not value or not value.strip():
            return value

        # Step 1: Strip formula prefixes
        sanitized = InputSanitizer._strip_formula_prefix(value)

        # Step 2: Apply all dangerous pattern removals
        for pattern in InputSanitizer.DANGEROUS_PATTERNS:
            sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)

        return sanitized

    @staticmethod
    def sanitize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Apply complete sanitization to entire DataFrame.

        Args:
            df: Input DataFrame

        Returns:
            Fully sanitized DataFrame (formulas stripped + XSS removed)

        SECURITY: This is the main entry point for sanitizing
        Excel data. It combines formula stripping and XSS prevention.
        """
        # Step 1: Strip formulas
        df_sanitized = InputSanitizer.strip_formulas(df)

        # Step 2: Sanitize cell values for XSS
        for col in df_sanitized.columns:
            df_sanitized[col] = df_sanitized[col].apply(InputSanitizer.sanitize_cell_value)

        return df_sanitized
