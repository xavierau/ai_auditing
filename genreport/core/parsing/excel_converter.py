"""Secure Excel parser with sanitization.

This module provides secure parsing of Excel files with built-in sanitization
to prevent formula injection and XSS attacks.
"""

from typing import Dict, List, Any
import pandas as pd
from pathlib import Path

from genreport.core.security.input_sanitizer import InputSanitizer


class SecureExcelParser:
    """Secure Excel parser with automatic sanitization.

    This parser reads Excel files and applies security sanitization to:
    - Strip Excel formulas (prevents formula injection)
    - Remove XSS patterns (prevents script injection)
    - Sanitize all cell values

    Example:
        ```python
        parser = SecureExcelParser()
        result = parser.parse_excel_safe("workbook.xlsx")

        # Access worksheets as DataFrames
        tb_df = result["worksheets"]["Trial Balance"]
        print(f"Found {result['total_sheets']} sheets")
        ```
    """

    def __init__(self):
        """Initialize secure Excel parser."""
        self.sanitizer = InputSanitizer()

    def get_sheet_names(self, file_path: str) -> List[str]:
        """Get list of sheet names from Excel file.

        Args:
            file_path: Path to Excel file

        Returns:
            List of sheet names

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not a valid Excel file
        """
        try:
            xls = pd.ExcelFile(file_path)
            return xls.sheet_names
        except FileNotFoundError:
            raise FileNotFoundError(f"Excel file not found: {file_path}")
        except Exception as e:
            raise ValueError(f"Failed to read Excel file: {str(e)}")

    def parse_excel_safe(self, file_path: str) -> Dict[str, Any]:
        """Parse Excel file with security sanitization.

        This method:
        1. Reads all sheets from the Excel file
        2. Applies formula stripping to prevent injection
        3. Sanitizes all cell values for XSS prevention
        4. Returns sanitized DataFrames

        Args:
            file_path: Path to Excel file

        Returns:
            Dictionary containing:
                - worksheets: Dict[str, pd.DataFrame] - Sanitized worksheets
                - sheet_names: List[str] - List of sheet names
                - total_sheets: int - Total number of sheets

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not a valid Excel file

        Example:
            ```python
            parser = SecureExcelParser()
            result = parser.parse_excel_safe("workbook.xlsx")

            for sheet_name, df in result["worksheets"].items():
                print(f"{sheet_name}: {len(df)} rows")
            ```
        """
        # Validate file exists
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Excel file not found: {file_path}")

        try:
            # Read Excel file
            xls = pd.ExcelFile(file_path)

            worksheets = {}
            for sheet_name in xls.sheet_names:
                # Read sheet
                df = pd.read_excel(xls, sheet_name=sheet_name)

                # Apply sanitization to DataFrame
                df = self.sanitizer.strip_formulas(df)

                # Sanitize all cells
                for col in df.columns:
                    df[col] = df[col].apply(self.sanitizer.sanitize_cell_value)

                worksheets[sheet_name] = df

            return {
                "worksheets": worksheets,
                "sheet_names": xls.sheet_names,
                "total_sheets": len(xls.sheet_names),
            }

        except Exception as e:
            if "not found" in str(e).lower():
                raise FileNotFoundError(f"Excel file not found: {file_path}")
            raise ValueError(f"Failed to parse Excel file: {str(e)}")

    def parse_single_sheet(
        self, file_path: str, sheet_name: str
    ) -> pd.DataFrame:
        """Parse a single sheet from Excel file.

        Args:
            file_path: Path to Excel file
            sheet_name: Name of sheet to parse

        Returns:
            Sanitized DataFrame for the specified sheet

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If sheet doesn't exist or file is invalid
        """
        try:
            # Read specific sheet
            df = pd.read_excel(file_path, sheet_name=sheet_name)

            # Apply sanitization
            df = self.sanitizer.strip_formulas(df)

            for col in df.columns:
                df[col] = df[col].apply(self.sanitizer.sanitize_cell_value)

            return df

        except FileNotFoundError:
            raise FileNotFoundError(f"Excel file not found: {file_path}")
        except ValueError as e:
            if "Worksheet" in str(e):
                raise ValueError(f"Sheet '{sheet_name}' not found in {file_path}")
            raise
        except Exception as e:
            raise ValueError(f"Failed to parse sheet '{sheet_name}': {str(e)}")
