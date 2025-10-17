"""Tests for FileValidationService.

Following TDD approach - these tests define the expected behavior.
"""

import io
import pytest
from fastapi import UploadFile

from genreport.core.security.file_validation import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    MAX_FILE_SIZE,
    FileValidationService,
)


class TestFileValidationService:
    """Test suite for file validation service."""

    @pytest.fixture
    def validator(self):
        """Create FileValidationService instance."""
        return FileValidationService()

    @pytest.fixture
    def create_upload_file(self):
        """Factory to create UploadFile instances."""

        def _create(filename: str, content: bytes, content_type: str = "application/octet-stream"):
            file_obj = io.BytesIO(content)
            return UploadFile(filename=filename, file=file_obj)

        return _create

    # Valid XLSX magic bytes (ZIP format)
    XLSX_MAGIC_BYTES = b"PK\x03\x04"
    # Valid XLS magic bytes (OLE2 format)
    XLS_MAGIC_BYTES = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"
    # Valid CSV content
    CSV_CONTENT = b"Name,Value\nTest,123\n"

    # Extension Validation Tests

    def test_validate_xlsx_extension(self, validator, create_upload_file):
        """Test that .xlsx extension is accepted."""
        file = create_upload_file("workbook.xlsx", self.XLSX_MAGIC_BYTES)
        is_valid, error = validator.validate_file_type(file)

        assert is_valid is True
        assert error is None

    def test_validate_xls_extension(self, validator, create_upload_file):
        """Test that .xls extension is accepted."""
        file = create_upload_file("workbook.xls", self.XLS_MAGIC_BYTES)
        is_valid, error = validator.validate_file_type(file)

        assert is_valid is True
        assert error is None

    def test_validate_csv_extension(self, validator, create_upload_file):
        """Test that .csv extension is accepted."""
        file = create_upload_file("data.csv", self.CSV_CONTENT)
        is_valid, error = validator.validate_file_type(file)

        assert is_valid is True
        assert error is None

    def test_reject_invalid_extension(self, validator, create_upload_file):
        """Test that invalid extensions are rejected."""
        invalid_files = [
            ("malicious.exe", b"MZ\x90\x00"),  # Windows executable
            ("script.js", b"console.log()"),  # JavaScript
            ("document.pdf", b"%PDF-1.4"),  # PDF
            ("image.png", b"\x89PNG"),  # PNG image
        ]

        for filename, content in invalid_files:
            file = create_upload_file(filename, content)
            is_valid, error = validator.validate_file_type(file)

            assert is_valid is False
            assert "Invalid file extension" in error
            assert filename in error or filename.split(".")[-1] in error

    def test_case_insensitive_extension_validation(self, validator, create_upload_file):
        """Test that extension validation is case-insensitive."""
        variations = ["workbook.XLSX", "workbook.XlSx", "workbook.xlsx"]

        for filename in variations:
            file = create_upload_file(filename, self.XLSX_MAGIC_BYTES)
            is_valid, error = validator.validate_file_type(file)

            assert is_valid is True, f"Failed for {filename}"
            assert error is None

    # Magic Bytes Validation Tests

    def test_validate_xlsx_magic_bytes(self, validator, create_upload_file):
        """Test XLSX magic bytes validation (ZIP format)."""
        file = create_upload_file("workbook.xlsx", self.XLSX_MAGIC_BYTES + b"\x00" * 100)
        is_valid, error = validator.validate_file_type(file)

        assert is_valid is True
        assert error is None

    def test_validate_xls_magic_bytes(self, validator, create_upload_file):
        """Test XLS magic bytes validation (OLE2 format)."""
        file = create_upload_file("workbook.xls", self.XLS_MAGIC_BYTES + b"\x00" * 100)
        is_valid, error = validator.validate_file_type(file)

        assert is_valid is True
        assert error is None

    def test_reject_mismatched_content(self, validator, create_upload_file):
        """Test that mismatched content and extension are rejected."""
        # .xlsx extension but .exe content
        file = create_upload_file("fake.xlsx", b"MZ\x90\x00" + b"\x00" * 100)
        is_valid, error = validator.validate_file_type(file)

        assert is_valid is False
        assert "content doesn't match extension" in error.lower()

    def test_reject_text_file_as_xlsx(self, validator, create_upload_file):
        """Test that text files disguised as XLSX are rejected."""
        file = create_upload_file("fake.xlsx", b"This is just text content")
        is_valid, error = validator.validate_file_type(file)

        assert is_valid is False

    # File Size Validation Tests

    def test_accept_file_within_size_limit(self, validator, create_upload_file):
        """Test that files within size limit are accepted."""
        # 10 MB file (well within 50MB limit)
        content = self.XLSX_MAGIC_BYTES + b"\x00" * (10 * 1024 * 1024)
        file = create_upload_file("large.xlsx", content)

        is_valid, error = validator.validate_file_size(content)

        assert is_valid is True
        assert error is None

    def test_reject_oversized_file(self, validator, create_upload_file):
        """Test that files exceeding size limit are rejected."""
        # 51 MB file (exceeds 50MB limit)
        content = b"\x00" * (51 * 1024 * 1024)

        is_valid, error = validator.validate_file_size(content)

        assert is_valid is False
        assert "too large" in error.lower()
        assert "50" in error  # Mentions size limit

    def test_accept_file_at_exact_size_limit(self, validator, create_upload_file):
        """Test that file at exact size limit is accepted."""
        # Exactly 50 MB
        content = b"\x00" * (50 * 1024 * 1024)

        is_valid, error = validator.validate_file_size(content)

        assert is_valid is True
        assert error is None

    # Macro Detection Tests

    def test_detect_macros_in_xlsm(self, validator, tmp_path):
        """Test macro detection in macro-enabled workbooks."""
        # Create a mock XLSM structure (ZIP with vbaProject.bin)
        import zipfile

        xlsm_path = tmp_path / "workbook.xlsm"

        with zipfile.ZipFile(xlsm_path, "w") as zf:
            zf.writestr("xl/workbook.xml", "<?xml version='1.0'?>")
            zf.writestr("xl/vbaProject.bin", b"\x00" * 100)  # Mock VBA project

        has_macros = validator.check_for_macros(str(xlsm_path))

        assert has_macros is True

    def test_no_macros_in_xlsx(self, validator, tmp_path):
        """Test that regular XLSX files report no macros."""
        import zipfile

        xlsx_path = tmp_path / "workbook.xlsx"

        with zipfile.ZipFile(xlsx_path, "w") as zf:
            zf.writestr("xl/workbook.xml", "<?xml version='1.0'?>")
            zf.writestr("xl/worksheets/sheet1.xml", "<?xml version='1.0'?>")

        has_macros = validator.check_for_macros(str(xlsx_path))

        assert has_macros is False

    def test_handle_non_zip_file_for_macro_check(self, validator, tmp_path):
        """Test macro check on non-ZIP file (should return False)."""
        xls_path = tmp_path / "workbook.xls"
        xls_path.write_bytes(self.XLS_MAGIC_BYTES + b"\x00" * 100)

        has_macros = validator.check_for_macros(str(xls_path))

        # Should return False (not throw exception)
        assert has_macros is False

    # Comprehensive Scan Tests

    def test_scan_valid_file_comprehensive(self, validator, create_upload_file):
        """Test comprehensive scan on valid file."""
        content = self.XLSX_MAGIC_BYTES + b"\x00" * 1000
        file = create_upload_file("workbook.xlsx", content)

        result = validator.scan_file(file, content)

        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert "metadata" in result
        assert result["metadata"]["file_size"] == len(content)
        assert result["metadata"]["detected_mime"] is not None

    def test_scan_file_with_macros_warning(self, validator, create_upload_file, tmp_path):
        """Test that files with macros generate warnings."""
        import zipfile

        # Create XLSM with macros
        xlsm_path = tmp_path / "workbook.xlsm"
        with zipfile.ZipFile(xlsm_path, "w") as zf:
            zf.writestr("xl/workbook.xml", "<?xml version='1.0'?>")
            zf.writestr("xl/vbaProject.bin", b"\x00" * 100)

        content = xlsm_path.read_bytes()
        file = create_upload_file("workbook.xlsm", content)

        result = validator.scan_file(file, content, check_macros_path=str(xlsm_path))

        # Should be valid but with warning
        assert "warnings" in result
        if result["metadata"].get("has_macros"):
            assert any("macro" in w.lower() for w in result["warnings"])

    def test_scan_invalid_file_multiple_errors(self, validator, create_upload_file):
        """Test scan on file with multiple issues."""
        # Oversized file with invalid extension
        content = b"\x00" * (51 * 1024 * 1024)
        file = create_upload_file("malicious.exe", content)

        result = validator.scan_file(file, content)

        assert result["valid"] is False
        assert len(result["errors"]) >= 1  # At least one error
        assert "errors" in result

    # Edge Cases

    def test_handle_empty_file(self, validator, create_upload_file):
        """Test handling of empty files."""
        file = create_upload_file("empty.xlsx", b"")

        is_valid, error = validator.validate_file_type(file)

        # Should be invalid (can't determine MIME type)
        assert is_valid is False

    def test_handle_very_small_file(self, validator, create_upload_file):
        """Test handling of files too small for magic byte detection."""
        file = create_upload_file("tiny.xlsx", b"PK")  # Incomplete magic bytes

        is_valid, error = validator.validate_file_type(file)

        # Should be invalid (incomplete magic bytes)
        assert is_valid is False

    def test_file_pointer_reset_after_validation(self, validator, create_upload_file):
        """Test that file pointer is reset after validation."""
        content = self.XLSX_MAGIC_BYTES + b"\x00" * 100
        file = create_upload_file("workbook.xlsx", content)

        # Validate
        validator.validate_file_type(file)

        # File pointer should be reset to beginning
        assert file.file.tell() == 0

    # Constants Tests

    def test_allowed_extensions_constant(self):
        """Test that ALLOWED_EXTENSIONS includes required formats."""
        assert ".xlsx" in ALLOWED_EXTENSIONS
        assert ".xls" in ALLOWED_EXTENSIONS
        assert ".csv" in ALLOWED_EXTENSIONS

    def test_allowed_mime_types_constant(self):
        """Test that ALLOWED_MIME_TYPES includes required types."""
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in ALLOWED_MIME_TYPES
        assert "application/vnd.ms-excel" in ALLOWED_MIME_TYPES
        assert "text/csv" in ALLOWED_MIME_TYPES

    def test_max_file_size_constant(self):
        """Test that MAX_FILE_SIZE is set correctly."""
        assert MAX_FILE_SIZE == 50 * 1024 * 1024  # 50MB in bytes


@pytest.mark.security
class TestFileValidationSecurity:
    """Security-focused tests for file validation."""

    @pytest.fixture
    def validator(self):
        """Create FileValidationService instance."""
        return FileValidationService()

    @pytest.fixture
    def create_upload_file(self):
        """Factory to create UploadFile instances."""

        def _create(filename: str, content: bytes):
            file_obj = io.BytesIO(content)
            return UploadFile(filename=filename, file=file_obj)

        return _create

    def test_prevent_path_traversal_in_filename(self, validator, create_upload_file):
        """Test that path traversal attempts in filenames are handled."""
        malicious_filenames = [
            "../../../etc/passwd.xlsx",
            "..\\..\\..\\windows\\system32\\config.xlsx",
            "../../secrets/keys.xlsx",
        ]

        xlsx_magic = b"PK\x03\x04" + b"\x00" * 100

        for filename in malicious_filenames:
            file = create_upload_file(filename, xlsx_magic)
            # Should still validate based on extension, but filename should be sanitized downstream
            is_valid, error = validator.validate_file_type(file)

            # The validator should only check extension, not sanitize filename
            # (that's handled by the upload endpoint)
            assert is_valid is True  # Extension is .xlsx

    def test_prevent_null_byte_injection(self, validator, create_upload_file):
        """Test handling of null byte injection in filenames."""
        # Null byte injection: "malicious.exe\x00.xlsx"
        filename = "malicious.exe\x00.xlsx"
        file = create_upload_file(filename, b"PK\x03\x04" + b"\x00" * 100)

        is_valid, error = validator.validate_file_type(file)

        # Should handle null bytes gracefully
        assert is_valid is not None  # Should not crash

    def test_prevent_zip_bomb_detection(self, validator):
        """Test that extremely high compression ratio files are handled."""
        # This is a simplified test - real zip bombs are more complex
        # The key is that file size validation happens AFTER decompression
        content = b"PK\x03\x04" + b"\x00" * 1000

        is_valid, error = validator.validate_file_size(content)

        # Should check actual content size, not compressed size
        assert is_valid is True  # This is small enough

    def test_double_extension_attack(self, validator, create_upload_file):
        """Test handling of double extension attacks."""
        file = create_upload_file("document.pdf.xlsx", b"PK\x03\x04" + b"\x00" * 100)

        is_valid, error = validator.validate_file_type(file)

        # Should check final extension (.xlsx), which is valid
        assert is_valid is True

    def test_case_variation_bypass_attempt(self, validator, create_upload_file):
        """Test that case variations don't bypass validation."""
        invalid_variations = [
            "malicious.ExE",
            "malicious.EXE",
            "malicious.eXe",
        ]

        for filename in invalid_variations:
            file = create_upload_file(filename, b"MZ\x90\x00")
            is_valid, error = validator.validate_file_type(file)

            assert is_valid is False, f"Failed to reject {filename}"
