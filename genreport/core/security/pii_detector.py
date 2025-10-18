"""PII Detector - Detects and redacts Personally Identifiable Information.

This module provides PII detection and redaction for Hong Kong context,
ensuring that AI-generated content does not expose sensitive personal information.

Usage:
    detector = PIIDetector()
    findings = detector.scan(text)
    redacted_text = detector.redact(text)
"""

import re
from typing import Dict, List, Optional, Set
from enum import Enum


class PIIType(str, Enum):
    """Types of PII that can be detected."""

    HKID = "hkid"  # Hong Kong Identity Card
    PHONE_HK = "phone_hk"  # Hong Kong phone numbers
    PHONE_INTL = "phone_intl"  # International phone numbers
    EMAIL = "email"  # Email addresses
    CREDIT_CARD = "credit_card"  # Credit card numbers
    BANK_ACCOUNT = "bank_account"  # Bank account numbers
    ADDRESS = "address"  # Physical addresses


class PIIDetector:
    """Detects and redacts PII from text.

    Supports multiple PII types with configurable redaction strategies.
    """

    # Default PII patterns for Hong Kong context
    DEFAULT_PATTERNS = {
        # HKID: Standard format (letter + 6 digits + check digit in parentheses)
        PIIType.HKID: r'[A-Z]\d{6}\([0-9A]\)',
        PIIType.PHONE_HK: r'\+852\s?\d{4}\s?\d{4}',
        # International phone: exclude +852 (handled by PHONE_HK), flexible digit groups
        PIIType.PHONE_INTL: r'\+(?!852[\s\d])\d{1,3}(?:\s?\d{3,4}){1,3}',
        PIIType.EMAIL: r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        PIIType.CREDIT_CARD: r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}',
        PIIType.BANK_ACCOUNT: r'\d{3}-\d{6}-\d{3}',
        PIIType.ADDRESS: r'\d+[A-Za-z\s,]+(?:Street|Road|Avenue|Drive|Lane|Floor)',
    }

    def __init__(self, enabled_types: Optional[List[PIIType]] = None):
        """Initialize PII detector.

        Args:
            enabled_types: List of PII types to detect. If None, all types are enabled.
        """
        self.patterns: Dict[str, str] = {}
        self.redaction_strategies: Dict[str, str] = {}

        # Set up enabled types
        if enabled_types is None:
            enabled_types = list(PIIType)

        # Load default patterns for enabled types
        for pii_type in enabled_types:
            if pii_type in self.DEFAULT_PATTERNS:
                self.patterns[pii_type] = self.DEFAULT_PATTERNS[pii_type]

                # Set default redaction strategy
                if pii_type == PIIType.EMAIL:
                    self.redaction_strategies[pii_type] = "partial_email"
                elif pii_type in [PIIType.PHONE_HK, PIIType.PHONE_INTL]:
                    self.redaction_strategies[pii_type] = "keep_last_4"
                else:
                    self.redaction_strategies[pii_type] = "full"

    def add_pattern(
        self,
        name: str,
        pattern: str,
        redaction_strategy: str = "full"
    ) -> None:
        """Add a custom PII pattern.

        Args:
            name: Name of the PII type
            pattern: Regex pattern to detect
            redaction_strategy: How to redact ("full", "partial_email", "keep_last_4")
        """
        self.patterns[name] = pattern
        self.redaction_strategies[name] = redaction_strategy

    def scan(self, text: Optional[str]) -> Dict[str, List[str]]:
        """Scan text for PII.

        Args:
            text: Text to scan

        Returns:
            Dict mapping PII type to list of matches
        """
        if not text:
            return {}

        findings: Dict[str, List[str]] = {}

        for pii_type, pattern in self.patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                findings[pii_type] = matches

        return findings

    def redact(self, text: Optional[str]) -> str:
        """Redact PII from text.

        Args:
            text: Text to redact

        Returns:
            Text with PII redacted
        """
        if not text:
            return ""

        redacted = text

        for pii_type, pattern in self.patterns.items():
            strategy = self.redaction_strategies.get(pii_type, "full")

            if strategy == "partial_email":
                redacted = re.sub(
                    pattern,
                    lambda m: self._partial_redact_email(m.group()),
                    redacted
                )
            elif strategy == "keep_last_4":
                redacted = re.sub(
                    pattern,
                    lambda m: self._keep_last_4(m.group()),
                    redacted
                )
            else:  # full redaction
                redacted = re.sub(pattern, '[REDACTED]', redacted)

        return redacted

    def has_pii(self, text: Optional[str]) -> bool:
        """Check if text contains any PII.

        Args:
            text: Text to check

        Returns:
            True if PII found, False otherwise
        """
        findings = self.scan(text)
        return len(findings) > 0

    def get_summary(self, findings: Dict[str, List[str]]) -> Dict[str, int]:
        """Get summary of PII findings.

        Args:
            findings: Results from scan()

        Returns:
            Dict mapping PII type to count, plus "total" key
        """
        summary = {pii_type: len(matches) for pii_type, matches in findings.items()}
        summary["total"] = sum(summary.values())
        return summary

    def _partial_redact_email(self, email: str) -> str:
        """Partially redact email (keep first 2 chars and domain).

        Args:
            email: Email address to redact

        Returns:
            Partially redacted email
        """
        try:
            local, domain = email.split('@')
            if len(local) > 2:
                return f"{local[:2]}***@{domain}"
            else:
                return f"***@{domain}"
        except Exception:
            return '[REDACTED]'

    def _keep_last_4(self, value: str) -> str:
        """Keep last 4 characters, mask the rest.

        Args:
            value: Value to partially redact

        Returns:
            Value with last 4 chars preserved
        """
        # Remove spaces and dashes for counting
        cleaned = value.replace(' ', '').replace('-', '')

        if len(cleaned) >= 4:
            return f"***{value[-4:]}"
        else:
            return "***"
