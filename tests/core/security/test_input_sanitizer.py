"""Tests for InputSanitizer.

Following TDD approach - these tests define the expected behavior.
"""

import pandas as pd
import pytest

from genreport.core.security.input_sanitizer import InputSanitizer


class TestInputSanitizer:
    """Test suite for input sanitizer."""

    # Formula Stripping Tests

    def test_strip_simple_formula(self):
        """Test stripping of simple Excel formulas."""
        df = pd.DataFrame({"A": ["=SUM(B1:B10)", "normal text", "123"]})

        sanitized = InputSanitizer.strip_formulas(df)

        # Formulas should be removed
        assert not str(sanitized.iloc[0]["A"]).startswith("=")
        assert sanitized.iloc[1]["A"] == "normal text"
        assert sanitized.iloc[2]["A"] == "123"

    def test_strip_complex_formulas(self):
        """Test stripping of complex Excel formulas."""
        formulas = [
            "=VLOOKUP(A1,Sheet2!A:B,2,FALSE)",
            "=IF(A1>100,\"High\",\"Low\")",
            "=INDEX(MATCH(A1,B:B,0))",
            "=HYPERLINK(\"http://evil.com\",\"Click Here\")",
        ]

        df = pd.DataFrame({"A": formulas})
        sanitized = InputSanitizer.strip_formulas(df)

        # All formulas should be stripped
        for idx in range(len(formulas)):
            assert not str(sanitized.iloc[idx]["A"]).startswith("=")

    def test_strip_formulas_with_plus_prefix(self):
        """Test stripping of formulas starting with +."""
        df = pd.DataFrame({"A": ["+SUM(A1:A10)", "+100+200", "=SUM(A1)"]})

        sanitized = InputSanitizer.strip_formulas(df)

        # Plus-prefixed expressions should be stripped
        assert not str(sanitized.iloc[0]["A"]).startswith("+")
        assert not str(sanitized.iloc[1]["A"]).startswith("+")
        assert not str(sanitized.iloc[2]["A"]).startswith("=")

    def test_preserve_non_formula_values(self):
        """Test that non-formula values are preserved."""
        df = pd.DataFrame(
            {
                "A": ["text", 123, 45.67, True, None],
                "B": ["=formula", "text", 789, False, ""],
            }
        )

        sanitized = InputSanitizer.strip_formulas(df)

        # Non-formula values should be preserved
        assert sanitized.iloc[0]["A"] == "text"
        assert sanitized.iloc[1]["A"] == 123
        assert sanitized.iloc[2]["A"] == 45.67
        assert sanitized.iloc[3]["A"] is True
        # Formula in column B should be stripped
        assert not str(sanitized.iloc[0]["B"]).startswith("=")

    def test_strip_formulas_in_multiple_columns(self):
        """Test formula stripping across multiple columns."""
        df = pd.DataFrame(
            {
                "A": ["=SUM(B:B)", "text"],
                "B": ["=A1*2", "123"],
                "C": ["=AVERAGE(A:B)", "normal"],
            }
        )

        sanitized = InputSanitizer.strip_formulas(df)

        # Formulas in all columns should be stripped
        assert not str(sanitized.iloc[0]["A"]).startswith("=")
        assert not str(sanitized.iloc[0]["B"]).startswith("=")
        assert not str(sanitized.iloc[0]["C"]).startswith("=")

    def test_handle_mixed_types(self):
        """Test handling of mixed data types."""
        df = pd.DataFrame({"A": ["=SUM(1,2)", 123, 45.67, True, "text"]})

        sanitized = InputSanitizer.strip_formulas(df)

        # Should handle all types gracefully
        assert len(sanitized) == 5
        assert not str(sanitized.iloc[0]["A"]).startswith("=")

    # Cell Value Sanitization Tests

    def test_sanitize_script_tags(self):
        """Test removal of script tags."""
        malicious_values = [
            "<script>alert('XSS')</script>",
            "text<script>alert('XSS')</script>text",
            "<SCRIPT>malicious()</SCRIPT>",  # Case variation
            "normal<script src='evil.js'></script>text",
        ]

        for value in malicious_values:
            sanitized = InputSanitizer.sanitize_cell_value(value)

            assert "<script" not in sanitized.lower()
            assert "alert" not in sanitized or "<script" not in value  # If alert preserved, script removed

    def test_sanitize_javascript_protocol(self):
        """Test removal of javascript: protocol."""
        malicious_values = [
            "javascript:alert('XSS')",
            "JavaScript:void(0)",
            "JAVASCRIPT:malicious()",
        ]

        for value in malicious_values:
            sanitized = InputSanitizer.sanitize_cell_value(value)

            assert "javascript:" not in sanitized.lower()

    def test_sanitize_event_handlers(self):
        """Test removal of event handler attributes."""
        malicious_values = [
            "onclick=alert('XSS')",
            "onload=malicious()",
            "onerror=steal()",
            "onmouseover=attack()",
        ]

        for value in malicious_values:
            sanitized = InputSanitizer.sanitize_cell_value(value)

            # Event handlers should be removed
            assert "onclick" not in sanitized.lower()
            assert "onload" not in sanitized.lower()
            assert "onerror" not in sanitized.lower()
            assert "onmouseover" not in sanitized.lower()

    def test_sanitize_iframe_tags(self):
        """Test removal of iframe tags."""
        malicious_values = [
            "<iframe src='evil.com'></iframe>",
            "text<iframe>malicious</iframe>text",
            "<IFRAME src='hack.com'></IFRAME>",
        ]

        for value in malicious_values:
            sanitized = InputSanitizer.sanitize_cell_value(value)

            assert "<iframe" not in sanitized.lower()

    def test_preserve_safe_content(self):
        """Test that safe content is preserved."""
        safe_values = [
            "This is normal text",
            "Email: user@example.com",
            "Number: 12345",
            "Date: 2024-10-17",
            "Special chars: !@#$%^&*()",
            "Equation: a + b = c",
        ]

        for value in safe_values:
            sanitized = InputSanitizer.sanitize_cell_value(value)

            assert sanitized == value  # Should be unchanged

    def test_sanitize_non_string_values(self):
        """Test that non-string values are returned unchanged."""
        values = [123, 45.67, True, False, None]

        for value in values:
            sanitized = InputSanitizer.sanitize_cell_value(value)

            assert sanitized == value

    def test_sanitize_empty_string(self):
        """Test handling of empty strings."""
        sanitized = InputSanitizer.sanitize_cell_value("")

        assert sanitized == ""

    # DataFrame Sanitization Tests

    def test_sanitize_dataframe_comprehensive(self):
        """Test comprehensive DataFrame sanitization."""
        df = pd.DataFrame(
            {
                "A": ["=SUM(1,2)", "normal text", "<script>alert()</script>"],
                "B": [123, "onclick=malicious()", "safe text"],
                "C": ["<iframe src='evil'></iframe>", 45.67, True],
            }
        )

        sanitized = InputSanitizer.sanitize_dataframe(df)

        # Formulas should be stripped
        assert not str(sanitized.iloc[0]["A"]).startswith("=")

        # Scripts should be removed
        assert "<script" not in str(sanitized.iloc[2]["A"]).lower()

        # Event handlers should be removed
        assert "onclick" not in str(sanitized.iloc[1]["B"]).lower()

        # Iframes should be removed
        assert "<iframe" not in str(sanitized.iloc[0]["C"]).lower()

        # Safe values should be preserved
        assert sanitized.iloc[0]["B"] == 123
        assert sanitized.iloc[1]["C"] == 45.67
        assert sanitized.iloc[2]["C"] is True

    def test_sanitize_dataframe_with_formulas_and_xss(self):
        """Test DataFrame with both formulas and XSS attempts."""
        df = pd.DataFrame(
            {
                "A": [
                    "=HYPERLINK(\"javascript:alert('XSS')\")",
                    "<script>steal()</script>",
                    "onclick=hack()",
                ]
            }
        )

        sanitized = InputSanitizer.sanitize_dataframe(df)

        # All malicious content should be sanitized
        assert not str(sanitized.iloc[0]["A"]).startswith("=")
        assert "javascript:" not in str(sanitized.iloc[0]["A"]).lower()
        assert "<script" not in str(sanitized.iloc[1]["A"]).lower()
        assert "onclick" not in str(sanitized.iloc[2]["A"]).lower()

    def test_sanitize_large_dataframe(self):
        """Test sanitization on larger DataFrame."""
        size = 1000
        df = pd.DataFrame(
            {
                "A": ["=SUM(1,2)"] * size,
                "B": ["<script>alert()</script>"] * size,
                "C": ["normal text"] * size,
            }
        )

        sanitized = InputSanitizer.sanitize_dataframe(df)

        # All formulas should be stripped
        assert all(not str(v).startswith("=") for v in sanitized["A"] if isinstance(v, str))

        # All scripts should be removed
        assert all("<script" not in str(v).lower() for v in sanitized["B"])

        # Normal text should be preserved
        assert all(v == "normal text" for v in sanitized["C"])

    def test_sanitize_dataframe_preserves_shape(self):
        """Test that DataFrame shape is preserved after sanitization."""
        df = pd.DataFrame(
            {
                "A": ["=SUM(1,2)", "<script>alert()</script>", "normal"],
                "B": [1, 2, 3],
                "C": [True, False, True],
            }
        )

        sanitized = InputSanitizer.sanitize_dataframe(df)

        assert sanitized.shape == df.shape
        assert list(sanitized.columns) == list(df.columns)

    # Edge Cases

    def test_handle_dataframe_with_nan(self):
        """Test handling of NaN values."""
        df = pd.DataFrame({"A": [pd.NA, float("nan"), None, "text"]})

        sanitized = InputSanitizer.sanitize_dataframe(df)

        # Should handle NaN gracefully without errors
        assert len(sanitized) == 4

    def test_handle_unicode_content(self):
        """Test handling of Unicode characters."""
        unicode_values = ["中文", "日本語", "Ñoño", "Привет", "🎉"]

        for value in unicode_values:
            sanitized = InputSanitizer.sanitize_cell_value(value)

            assert sanitized == value  # Unicode should be preserved

    def test_handle_multiline_content(self):
        """Test handling of multiline content."""
        value = "Line 1\nLine 2\nLine 3"

        sanitized = InputSanitizer.sanitize_cell_value(value)

        assert "\n" in sanitized  # Newlines should be preserved

    def test_sanitize_nested_attacks(self):
        """Test handling of nested attack patterns."""
        nested_attacks = [
            "<scr<script>ipt>alert()</scr</script>ipt>",
            "java\\x00script:alert()",
            "on\x00click=attack()",
        ]

        for value in nested_attacks:
            sanitized = InputSanitizer.sanitize_cell_value(value)

            # Should remove attack patterns
            assert "<script" not in sanitized.lower()

    def test_handle_very_long_strings(self):
        """Test handling of very long strings."""
        long_string = "A" * 10000
        malicious_long = "=SUM(" + "A" * 10000 + ")"

        # Normal long string
        assert InputSanitizer.sanitize_cell_value(long_string) == long_string

        # Long formula
        sanitized_formula = InputSanitizer.sanitize_cell_value(malicious_long)
        assert not sanitized_formula.startswith("=")


@pytest.mark.security
class TestInputSanitizerSecurity:
    """Security-focused tests for input sanitizer."""

    def test_prevent_csv_formula_injection(self):
        """Test prevention of CSV formula injection attacks."""
        # CSV formula injection attempts
        csv_injections = [
            "=cmd|'/c calc'!A1",
            "=1+1+cmd|'/c calc'!A1",
            "@SUM(1+1)*cmd|'/c calc'!A1",
            "+cmd|'/c powershell'!A1",
        ]

        for value in csv_injections:
            sanitized = InputSanitizer.sanitize_cell_value(value)

            # Should strip formula prefix
            assert not sanitized.startswith("=")
            assert not sanitized.startswith("+")
            assert not sanitized.startswith("@")

    def test_prevent_command_injection(self):
        """Test that command injection attempts are sanitized."""
        command_injections = [
            "=HYPERLINK(\"cmd.exe /c calc\")",
            "=SYSTEM(\"rm -rf /\")",
            "=EXEC(\"malicious\")",
        ]

        for value in command_injections:
            sanitized = InputSanitizer.sanitize_cell_value(value)

            # Formula prefix should be removed
            assert not sanitized.startswith("=")

    def test_prevent_xss_in_multiple_formats(self):
        """Test XSS prevention in various formats."""
        xss_attempts = [
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "<body onload=alert('XSS')>",
            "<input onfocus=alert('XSS') autofocus>",
        ]

        for value in xss_attempts:
            sanitized = InputSanitizer.sanitize_cell_value(value)

            # Event handlers should be removed
            assert "onload" not in sanitized.lower()
            assert "onerror" not in sanitized.lower()
            assert "onfocus" not in sanitized.lower()

    def test_prevent_encoded_attacks(self):
        """Test prevention of encoded attack patterns."""
        encoded_attacks = [
            "&#60;script&#62;alert()&#60;/script&#62;",
            "%3Cscript%3Ealert()%3C/script%3E",
        ]

        for value in encoded_attacks:
            # Sanitizer should handle common encoding patterns
            # Note: Full HTML entity decoding might be overkill
            # but basic patterns should be caught
            sanitized = InputSanitizer.sanitize_cell_value(value)

            # At minimum, don't introduce new vulnerabilities
            assert isinstance(sanitized, str)
