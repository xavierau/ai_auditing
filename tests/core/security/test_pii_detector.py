"""Tests for PIIDetector - PII detection and redaction.

Following TDD methodology: These tests are written BEFORE implementation.
They define the expected behavior of PIIDetector for Hong Kong context.
"""

import pytest

from genreport.core.security.pii_detector import PIIDetector, PIIType


class TestPIIDetectorHKID:
    """Test detection of Hong Kong Identity Card numbers."""

    def test_detect_valid_hkid(self):
        """Detect standard HKID format."""
        detector = PIIDetector()
        text = "John's HKID is A123456(7)"

        findings = detector.scan(text)

        assert PIIType.HKID in findings
        assert "A123456(7)" in findings[PIIType.HKID]

    def test_detect_multiple_hkid(self):
        """Detect multiple HKIDs in text."""
        detector = PIIDetector()
        text = "Employee A: A123456(7), Employee B: B987654(3)"

        findings = detector.scan(text)

        assert len(findings[PIIType.HKID]) == 2
        assert "A123456(7)" in findings[PIIType.HKID]
        assert "B987654(3)" in findings[PIIType.HKID]

    def test_redact_hkid_full(self):
        """Fully redact HKID numbers."""
        detector = PIIDetector()
        text = "Contact A123456(7) for details"

        redacted = detector.redact(text)

        assert "A123456(7)" not in redacted
        assert "[REDACTED]" in redacted

    def test_no_hkid_detection(self):
        """No false positives for invalid patterns."""
        detector = PIIDetector()
        # Invalid: wrong number of digits, no check digit format
        text = "Model number X12345 is available"

        findings = detector.scan(text)

        assert PIIType.HKID not in findings


class TestPIIDetectorPhoneNumbers:
    """Test detection of phone numbers."""

    def test_detect_hk_phone_with_country_code(self):
        """Detect HK phone with +852."""
        detector = PIIDetector()
        text = "Call us at +852 1234 5678"

        findings = detector.scan(text)

        assert PIIType.PHONE_HK in findings
        assert "+852 1234 5678" in findings[PIIType.PHONE_HK]

    def test_detect_hk_phone_no_spaces(self):
        """Detect HK phone without spaces."""
        detector = PIIDetector()
        text = "Call +85212345678"

        findings = detector.scan(text)

        assert PIIType.PHONE_HK in findings

    def test_detect_international_phone(self):
        """Detect international phone numbers."""
        detector = PIIDetector()
        text = "US office: +1 555 123 4567"

        findings = detector.scan(text)

        assert PIIType.PHONE_INTL in findings

    def test_redact_phone_keep_last_4(self):
        """Redact phone but keep last 4 digits."""
        detector = PIIDetector()
        text = "Call +852 1234 5678"

        redacted = detector.redact(text)

        assert "+852 1234 5678" not in redacted
        assert "5678" in redacted  # Last 4 digits preserved
        assert "***" in redacted  # Masked portion

    def test_multiple_phone_numbers(self):
        """Detect multiple phones in text."""
        detector = PIIDetector()
        text = "HK: +852 1234 5678, SG: +65 9876 5432"

        findings = detector.scan(text)

        # Should detect both
        assert len(findings[PIIType.PHONE_HK]) + len(findings.get(PIIType.PHONE_INTL, [])) >= 2


class TestPIIDetectorEmail:
    """Test detection of email addresses."""

    def test_detect_standard_email(self):
        """Detect standard email format."""
        detector = PIIDetector()
        text = "Contact john.doe@example.com for info"

        findings = detector.scan(text)

        assert PIIType.EMAIL in findings
        assert "john.doe@example.com" in findings[PIIType.EMAIL]

    def test_detect_email_with_numbers(self):
        """Detect email with numbers."""
        detector = PIIDetector()
        text = "Email: user123@company456.com"

        findings = detector.scan(text)

        assert PIIType.EMAIL in findings

    def test_redact_email_partial(self):
        """Partially redact email (keep first 2 chars and domain)."""
        detector = PIIDetector()
        text = "Email: john@example.com"

        redacted = detector.redact(text)

        assert "john@example.com" not in redacted
        assert "jo***@example.com" in redacted  # First 2 chars + domain preserved

    def test_redact_short_email(self):
        """Handle email with short local part."""
        detector = PIIDetector()
        text = "Email: a@example.com"

        redacted = detector.redact(text)

        # Short emails get fully masked local part
        assert "a@example.com" not in redacted
        assert "***@example.com" in redacted

    def test_multiple_emails(self):
        """Detect multiple emails."""
        detector = PIIDetector()
        text = "CC: john@example.com, jane@company.org"

        findings = detector.scan(text)

        assert len(findings[PIIType.EMAIL]) == 2


class TestPIIDetectorCreditCard:
    """Test detection of credit card numbers."""

    def test_detect_credit_card_with_spaces(self):
        """Detect credit card with spaces."""
        detector = PIIDetector()
        text = "Card: 1234 5678 9012 3456"

        findings = detector.scan(text)

        assert PIIType.CREDIT_CARD in findings

    def test_detect_credit_card_with_dashes(self):
        """Detect credit card with dashes."""
        detector = PIIDetector()
        text = "Card: 1234-5678-9012-3456"

        findings = detector.scan(text)

        assert PIIType.CREDIT_CARD in findings

    def test_detect_credit_card_no_separators(self):
        """Detect credit card without separators."""
        detector = PIIDetector()
        text = "Card: 1234567890123456"

        findings = detector.scan(text)

        assert PIIType.CREDIT_CARD in findings

    def test_redact_credit_card_full(self):
        """Fully redact credit card numbers."""
        detector = PIIDetector()
        text = "Pay with 1234 5678 9012 3456"

        redacted = detector.redact(text)

        assert "1234 5678 9012 3456" not in redacted
        assert "[REDACTED]" in redacted


class TestPIIDetectorBankAccount:
    """Test detection of bank account numbers (HK format)."""

    def test_detect_hk_bank_account(self):
        """Detect HK bank account format."""
        detector = PIIDetector()
        text = "Account: 123-456789-123"

        findings = detector.scan(text)

        assert PIIType.BANK_ACCOUNT in findings

    def test_redact_bank_account(self):
        """Fully redact bank account numbers."""
        detector = PIIDetector()
        text = "Transfer to 123-456789-123"

        redacted = detector.redact(text)

        assert "123-456789-123" not in redacted
        assert "[REDACTED]" in redacted


class TestPIIDetectorAddress:
    """Test detection of physical addresses."""

    def test_detect_street_address(self):
        """Detect street addresses."""
        detector = PIIDetector()
        text = "Office at 123 Nathan Road, Kowloon"

        findings = detector.scan(text)

        assert PIIType.ADDRESS in findings

    def test_detect_floor_address(self):
        """Detect addresses with floor numbers."""
        detector = PIIDetector()
        text = "Visit us at 5th Floor, 88 Queensway"

        findings = detector.scan(text)

        assert PIIType.ADDRESS in findings

    def test_redact_address(self):
        """Fully redact physical addresses."""
        detector = PIIDetector()
        text = "Located at 123 Des Voeux Road Central"

        redacted = detector.redact(text)

        assert "123 Des Voeux Road Central" not in redacted
        assert "[REDACTED]" in redacted


class TestPIIDetectorMultipleTypes:
    """Test detection of multiple PII types in same text."""

    def test_scan_multiple_pii_types(self):
        """Detect multiple PII types in single text."""
        detector = PIIDetector()
        text = (
            "Contact John at john@example.com or +852 1234 5678. "
            "HKID: A123456(7). Office: 123 Nathan Road."
        )

        findings = detector.scan(text)

        assert PIIType.EMAIL in findings
        assert PIIType.PHONE_HK in findings
        assert PIIType.HKID in findings
        assert PIIType.ADDRESS in findings
        assert len(findings) == 4

    def test_redact_all_pii_types(self):
        """Redact all PII types from text."""
        detector = PIIDetector()
        text = (
            "Contact john@example.com or +852 1234 5678. "
            "HKID: A123456(7)."
        )

        redacted = detector.redact(text)

        # Original PII should be gone
        assert "john@example.com" not in redacted
        assert "+852 1234 5678" not in redacted
        assert "A123456(7)" not in redacted

        # Redacted versions should be present
        assert "jo***@example.com" in redacted  # Email partial
        assert "5678" in redacted  # Phone last 4
        assert "[REDACTED]" in redacted  # HKID full


class TestPIIDetectorEdgeCases:
    """Test edge cases and error handling."""

    def test_no_pii_returns_original(self):
        """Text without PII should be unchanged."""
        detector = PIIDetector()
        text = "The revenue recognition policy follows HKFRS 15."

        redacted = detector.redact(text)

        assert redacted == text

    def test_empty_string(self):
        """Handle empty string."""
        detector = PIIDetector()

        findings = detector.scan("")
        redacted = detector.redact("")

        assert findings == {}
        assert redacted == ""

    def test_none_value(self):
        """Handle None value gracefully."""
        detector = PIIDetector()

        findings = detector.scan(None)
        redacted = detector.redact(None)

        assert findings == {}
        assert redacted == ""

    def test_very_long_text(self):
        """Handle very long text efficiently."""
        detector = PIIDetector()
        text = "Normal text. " * 1000 + "HKID: A123456(7)"

        findings = detector.scan(text)

        assert PIIType.HKID in findings

    def test_special_characters_in_text(self):
        """Handle special characters."""
        detector = PIIDetector()
        text = "Email: john+test@example.com, Info: 123-456-789"

        findings = detector.scan(text)

        assert PIIType.EMAIL in findings


class TestPIIDetectorConfiguration:
    """Test detector configuration options."""

    def test_custom_patterns(self):
        """Allow custom PII patterns."""
        detector = PIIDetector()

        # Add custom pattern for Singapore NRIC
        detector.add_pattern(
            "NRIC",
            r'[STFG]\d{7}[A-Z]',
            redaction_strategy="full"
        )

        text = "NRIC: S1234567D"
        findings = detector.scan(text)

        assert "NRIC" in findings

    def test_disable_specific_detection(self):
        """Allow disabling specific PII types."""
        detector = PIIDetector(enabled_types=[PIIType.EMAIL, PIIType.PHONE_HK])

        text = "Email: john@example.com, HKID: A123456(7)"
        findings = detector.scan(text)

        # Email detected
        assert PIIType.EMAIL in findings
        # HKID should NOT be detected (disabled)
        assert PIIType.HKID not in findings


class TestPIIDetectorPerformance:
    """Test performance characteristics."""

    def test_scan_is_fast(self):
        """Scanning should be fast even with many patterns."""
        import time

        detector = PIIDetector()
        text = "This is a long text. " * 100

        start = time.time()
        findings = detector.scan(text)
        duration = time.time() - start

        # Should complete in under 100ms
        assert duration < 0.1

    def test_redact_is_fast(self):
        """Redaction should be fast."""
        import time

        detector = PIIDetector()
        text = "Contact john@example.com at +852 1234 5678. " * 50

        start = time.time()
        redacted = detector.redact(text)
        duration = time.time() - start

        # Should complete in under 100ms
        assert duration < 0.1


class TestPIIDetectorReporting:
    """Test reporting capabilities."""

    def test_get_pii_summary(self):
        """Get summary of PII found."""
        detector = PIIDetector()
        text = (
            "john@example.com, jane@example.com, "
            "+852 1234 5678, A123456(7)"
        )

        findings = detector.scan(text)
        summary = detector.get_summary(findings)

        assert summary[PIIType.EMAIL] == 2
        assert summary[PIIType.PHONE_HK] == 1
        assert summary[PIIType.HKID] == 1
        assert summary["total"] == 4

    def test_has_pii_check(self):
        """Check if text has any PII."""
        detector = PIIDetector()

        text_with_pii = "Email: john@example.com"
        text_without_pii = "Revenue recognition policy"

        assert detector.has_pii(text_with_pii) is True
        assert detector.has_pii(text_without_pii) is False
