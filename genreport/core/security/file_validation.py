"""File validation service with defense-in-depth approach.

SECURITY: Validates both extension and magic bytes to prevent file type spoofing.
Detects macros in Excel files and enforces size limits.
"""

import zipfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import magic
from fastapi import UploadFile

# Constants
ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv"}
ALLOWED_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # XLSX
    "application/vnd.ms-excel",  # XLS
    "text/csv",  # CSV
    "text/plain",  # CSV files sometimes report as plain text
    "application/octet-stream",  # Sometimes Excel files report as this
    "application/zip",  # XLSX is ZIP-based
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB in bytes


class FileValidationService:
    """File validation with defense-in-depth approach.

    SECURITY: Validates both extension and magic bytes to prevent
    file type spoofing. Detects macros in Excel files.

    ARCHITECTURE: Market-agnostic security component.
    """

    def validate_file_type(self, file: UploadFile) -> Tuple[bool, Optional[str]]:
        """Validate file type using extension and magic bytes.

        Args:
            file: FastAPI UploadFile to validate

        Returns:
            Tuple of (is_valid, error_message)
            - (True, None) if file is valid
            - (False, "error description") if file is invalid
        """
        # Step 1: Check extension
        if not file.filename:
            return False, "Filename is missing"

        file_ext = Path(file.filename).suffix.lower()

        if file_ext not in ALLOWED_EXTENSIONS:
            return (
                False,
                f"Invalid file extension '{file_ext}' for file '{file.filename}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
            )

        # Step 2: Check actual content type (magic bytes)
        try:
            # Read first 2KB for magic byte detection
            file.file.seek(0)
            content_sample = file.file.read(2048)
            file.file.seek(0)  # Reset file pointer

            # Handle empty files
            if len(content_sample) == 0:
                return False, "File is empty"

            # Detect MIME type from content
            mime = magic.from_buffer(content_sample, mime=True)

            # Validate MIME type
            if mime not in ALLOWED_MIME_TYPES:
                # Special case: XLSX files are ZIP-based
                if file_ext == ".xlsx" and mime == "application/zip":
                    return True, None

                return (
                    False,
                    f"File content doesn't match extension. Detected MIME: {mime}",
                )

            # Special validation: text/plain MIME should only be accepted for CSV files
            if mime == "text/plain" and file_ext != ".csv":
                return (
                    False,
                    f"File content doesn't match extension. Detected MIME: {mime}",
                )

            return True, None

        except Exception as e:
            return False, f"Failed to validate file type: {str(e)}"

    def validate_file_size(self, content: bytes) -> Tuple[bool, Optional[str]]:
        """Ensure file size is within limits.

        Args:
            content: File content as bytes

        Returns:
            Tuple of (is_valid, error_message)
        """
        file_size = len(content)

        if file_size > MAX_FILE_SIZE:
            size_mb = file_size / (1024 * 1024)
            limit_mb = MAX_FILE_SIZE / (1024 * 1024)
            return (
                False,
                f"File too large ({size_mb:.1f} MB). Maximum allowed: {limit_mb:.0f} MB",
            )

        return True, None

    def check_for_macros(self, file_path: str) -> bool:
        """Detect VBA macros in Excel files (XLSX only).

        Args:
            file_path: Path to Excel file

        Returns:
            True if macros detected, False otherwise

        SECURITY: Macros can contain malicious code. Detection allows
        for warnings or rejection based on policy.
        """
        try:
            with zipfile.ZipFile(file_path, "r") as zip_ref:
                # XLSX files with macros have vbaProject.bin
                if "xl/vbaProject.bin" in zip_ref.namelist():
                    return True
        except (zipfile.BadZipFile, FileNotFoundError):
            # Not a valid ZIP file or file doesn't exist
            # XLS files aren't ZIP-based, so this is expected
            pass

        return False

    def scan_file(
        self,
        file: UploadFile,
        content: bytes,
        check_macros_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Comprehensive file scan.

        Args:
            file: FastAPI UploadFile to validate
            content: File content as bytes
            check_macros_path: Optional path to temp file for macro checking

        Returns:
            Dict with validation results:
            {
                "valid": bool,
                "errors": List[str],
                "warnings": List[str],
                "metadata": {
                    "detected_mime": str,
                    "file_size": int,
                    "has_macros": bool
                }
            }
        """
        errors = []
        warnings = []
        metadata: Dict[str, Any] = {
            "file_size": len(content),
            "detected_mime": None,
            "has_macros": False,
        }

        # Validate file type
        is_valid_type, type_error = self.validate_file_type(file)
        if not is_valid_type:
            errors.append(type_error)
        else:
            # Get MIME type for metadata
            try:
                file.file.seek(0)
                content_sample = file.file.read(2048)
                file.file.seek(0)
                metadata["detected_mime"] = magic.from_buffer(content_sample, mime=True)
            except Exception:
                metadata["detected_mime"] = "unknown"

        # Validate file size
        is_valid_size, size_error = self.validate_file_size(content)
        if not is_valid_size:
            errors.append(size_error)

        # Check for macros if path provided
        if check_macros_path:
            has_macros = self.check_for_macros(check_macros_path)
            metadata["has_macros"] = has_macros

            if has_macros:
                warnings.append(
                    "File contains VBA macros. Macros will be stripped during processing."
                )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "metadata": metadata,
        }


# ============================================================================
# Standalone Functions for FastAPI Dependency Injection
# ============================================================================

# Singleton instance for standalone functions
_file_validator = FileValidationService()


def validate_file_type(file: UploadFile) -> None:
    """Standalone function to validate file type.

    This function wraps FileValidationService.validate_file_type() for use
    in FastAPI routers without dependency injection.

    Args:
        file: FastAPI UploadFile to validate

    Raises:
        HTTPException: 400 status code if validation fails

    Example:
        ```python
        @router.post("/upload")
        async def upload_file(file: UploadFile = File(...)):
            validate_file_type(file)  # Raises HTTPException if invalid
            # Continue processing...
        ```
    """
    from fastapi import HTTPException

    is_valid, error_msg = _file_validator.validate_file_type(file)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)


def check_file_size(content: bytes, max_size: int) -> None:
    """Standalone function to check file size.

    This function wraps FileValidationService.validate_file_size() for use
    in FastAPI routers without dependency injection.

    Args:
        content: File content as bytes
        max_size: Maximum allowed file size (unused, uses MAX_FILE_SIZE constant)

    Raises:
        HTTPException: 400 status code if validation fails

    Note:
        The max_size parameter is kept for API compatibility but the function
        uses the global MAX_FILE_SIZE constant for consistent enforcement.

    Example:
        ```python
        content = await file.read()
        check_file_size(content, MAX_FILE_SIZE)  # Raises HTTPException if too large
        ```
    """
    from fastapi import HTTPException

    is_valid, error_msg = _file_validator.validate_file_size(content)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
