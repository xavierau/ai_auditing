"""Tests for SecureExcelParser.

Following TDD approach - these tests define the expected behavior.
"""

import pytest
import pandas as pd
import openpyxl
from pathlib import Path
from tempfile import NamedTemporaryFile


@pytest.fixture
def sample_excel_file():
    """Create a temporary Excel file for testing."""
    # Create a simple Excel workbook
    wb = openpyxl.Workbook()

    # Sheet 1: Trial Balance
    ws1 = wb.active
    ws1.title = "Trial Balance"
    ws1['A1'] = "Account"
    ws1['B1'] = "Debit"
    ws1['C1'] = "Credit"
    ws1['A2'] = "Cash"
    ws1['B2'] = 1000
    ws1['C2'] = 0
    ws1['A3'] = "Accounts Payable"
    ws1['B3'] = 0
    ws1['C3'] = 500

    # Sheet 2: GL Detail
    ws2 = wb.create_sheet("GL Detail")
    ws2['A1'] = "Date"
    ws2['B1'] = "Description"
    ws2['C1'] = "Amount"
    ws2['A2'] = "2024-01-01"
    ws2['B2'] = "Opening Balance"
    ws2['C2'] = 1000

    # Save to temporary file
    with NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        wb.save(tmp.name)
        return tmp.name


@pytest.fixture
def excel_file_with_formulas():
    """Create Excel file with formulas for testing sanitization."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Formulas"

    # Add some formulas
    ws['A1'] = "Value"
    ws['B1'] = "Formula"
    ws['A2'] = 10
    ws['B2'] = "=SUM(A2:A10)"
    ws['A3'] = 20
    ws['B3'] = "=A2*2"
    ws['A4'] = "=HYPERLINK('http://evil.com', 'Click')"

    with NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        wb.save(tmp.name)
        return tmp.name


@pytest.fixture
def excel_file_with_xss():
    """Create Excel file with XSS attempts."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "XSS Test"

    ws['A1'] = "Clean"
    ws['A2'] = "<script>alert('xss')</script>"
    ws['A3'] = "javascript:alert('xss')"
    ws['A4'] = "onclick=alert('xss')"

    with NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        wb.save(tmp.name)
        return tmp.name


class TestSecureExcelParser:
    """Test suite for SecureExcelParser."""

    def test_parse_excel_returns_dict_with_worksheets(self, sample_excel_file):
        """Test that parse_excel_safe returns correct structure."""
        from genreport.core.parsing.excel_converter import SecureExcelParser

        parser = SecureExcelParser()
        result = parser.parse_excel_safe(sample_excel_file)

        # Should return dictionary with expected keys
        assert isinstance(result, dict)
        assert "worksheets" in result
        assert "sheet_names" in result
        assert "total_sheets" in result

    def test_parse_excel_reads_all_sheets(self, sample_excel_file):
        """Test that all sheets are read."""
        from genreport.core.parsing.excel_converter import SecureExcelParser

        parser = SecureExcelParser()
        result = parser.parse_excel_safe(sample_excel_file)

        # Should have 2 sheets
        assert result["total_sheets"] == 2
        assert len(result["sheet_names"]) == 2
        assert "Trial Balance" in result["sheet_names"]
        assert "GL Detail" in result["sheet_names"]

    def test_worksheets_are_dataframes(self, sample_excel_file):
        """Test that worksheets are returned as pandas DataFrames."""
        from genreport.core.parsing.excel_converter import SecureExcelParser

        parser = SecureExcelParser()
        result = parser.parse_excel_safe(sample_excel_file)

        # Each worksheet should be a DataFrame
        for sheet_name, df in result["worksheets"].items():
            assert isinstance(df, pd.DataFrame)

    def test_parse_excel_preserves_data(self, sample_excel_file):
        """Test that data is correctly preserved."""
        from genreport.core.parsing.excel_converter import SecureExcelParser

        parser = SecureExcelParser()
        result = parser.parse_excel_safe(sample_excel_file)

        # Check Trial Balance data
        tb_df = result["worksheets"]["Trial Balance"]
        assert len(tb_df) == 2  # 2 data rows (excluding header)
        assert "Account" in tb_df.columns
        assert "Cash" in tb_df["Account"].values

    def test_parse_excel_strips_formulas(self, excel_file_with_formulas):
        """Test that Excel formulas are stripped."""
        from genreport.core.parsing.excel_converter import SecureExcelParser

        parser = SecureExcelParser()
        result = parser.parse_excel_safe(excel_file_with_formulas)

        df = result["worksheets"]["Formulas"]

        # Check that formulas are stripped (pandas reads formula results, not formulas)
        # But we should ensure InputSanitizer is applied
        for col in df.columns:
            for value in df[col]:
                if isinstance(value, str):
                    # Should not start with = after sanitization
                    assert not value.startswith("=")

    def test_parse_excel_sanitizes_xss(self, excel_file_with_xss):
        """Test that XSS attempts are sanitized."""
        from genreport.core.parsing.excel_converter import SecureExcelParser

        parser = SecureExcelParser()
        result = parser.parse_excel_safe(excel_file_with_xss)

        df = result["worksheets"]["XSS Test"]

        # Convert all values to strings for checking
        all_values = []
        for col in df.columns:
            all_values.extend([str(v) for v in df[col] if pd.notna(v)])

        # XSS patterns should be removed
        for value in all_values:
            assert "<script>" not in value.lower()
            assert "javascript:" not in value.lower()
            assert "onclick=" not in value.lower()

    def test_parse_nonexistent_file_raises_error(self):
        """Test that parsing nonexistent file raises error."""
        from genreport.core.parsing.excel_converter import SecureExcelParser

        parser = SecureExcelParser()

        with pytest.raises(Exception):  # Should raise FileNotFoundError or similar
            parser.parse_excel_safe("nonexistent_file.xlsx")

    def test_parse_invalid_file_raises_error(self, tmp_path):
        """Test that parsing invalid file raises error."""
        from genreport.core.parsing.excel_converter import SecureExcelParser

        # Create a text file, not Excel
        text_file = tmp_path / "not_excel.xlsx"
        text_file.write_text("This is not an Excel file")

        parser = SecureExcelParser()

        with pytest.raises(Exception):  # Should raise parsing error
            parser.parse_excel_safe(str(text_file))

    def test_get_sheet_names_returns_list(self, sample_excel_file):
        """Test that get_sheet_names returns list of sheet names."""
        from genreport.core.parsing.excel_converter import SecureExcelParser

        parser = SecureExcelParser()
        sheet_names = parser.get_sheet_names(sample_excel_file)

        assert isinstance(sheet_names, list)
        assert len(sheet_names) == 2
        assert "Trial Balance" in sheet_names
        assert "GL Detail" in sheet_names

    def test_parse_empty_sheet(self):
        """Test parsing sheet with no data."""
        from genreport.core.parsing.excel_converter import SecureExcelParser

        # Create Excel with empty sheet
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Empty"

        with NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            wb.save(tmp.name)

            parser = SecureExcelParser()
            result = parser.parse_excel_safe(tmp.name)

            # Should still parse successfully
            assert "Empty" in result["sheet_names"]
            assert isinstance(result["worksheets"]["Empty"], pd.DataFrame)

    def test_parse_sheet_with_merged_cells(self):
        """Test parsing sheet with merged cells."""
        from genreport.core.parsing.excel_converter import SecureExcelParser

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Merged"

        ws['A1'] = "Title"
        ws.merge_cells('A1:C1')
        ws['A2'] = "Data"
        ws['B2'] = 100
        ws['C2'] = 200

        with NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            wb.save(tmp.name)

            parser = SecureExcelParser()
            result = parser.parse_excel_safe(tmp.name)

            # Should parse without error
            assert "Merged" in result["worksheets"]
            assert isinstance(result["worksheets"]["Merged"], pd.DataFrame)


class TestSecureExcelParserIntegration:
    """Integration tests for SecureExcelParser with InputSanitizer."""

    def test_parser_uses_input_sanitizer(self, excel_file_with_formulas):
        """Test that SecureExcelParser uses InputSanitizer for sanitization."""
        from genreport.core.parsing.excel_converter import SecureExcelParser

        parser = SecureExcelParser()
        result = parser.parse_excel_safe(excel_file_with_formulas)

        # Verify sanitization was applied
        df = result["worksheets"]["Formulas"]

        # All string values should be sanitized
        for col in df.columns:
            for value in df[col]:
                if isinstance(value, str):
                    # Should not have formula prefixes
                    assert not value.startswith("=")
                    assert not value.startswith("+")
                    assert not value.startswith("@")

    def test_parser_handles_unicode(self):
        """Test that parser handles Unicode characters."""
        from genreport.core.parsing.excel_converter import SecureExcelParser

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Unicode"
        ws['A1'] = "Language"  # Header
        ws['A2'] = "中文"
        ws['A3'] = "日本語"
        ws['A4'] = "한국어"
        ws['A5'] = "Ελληνικά"

        with NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            wb.save(tmp.name)

            parser = SecureExcelParser()
            result = parser.parse_excel_safe(tmp.name)

            df = result["worksheets"]["Unicode"]

            # Unicode should be preserved in both headers and values
            # Convert all values to a single list for checking
            all_content = df.values.flatten().tolist() + df.columns.tolist()
            all_content_str = [str(v) for v in all_content]

            assert "中文" in all_content_str
            assert "日本語" in all_content_str
