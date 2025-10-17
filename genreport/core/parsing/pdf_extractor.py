"""PDF text extraction utility for KB ingestion.

Simple PDF text extractor that reads PDF files and extracts text content.
"""

from pathlib import Path
from typing import Optional

import pdfplumber


class PDFExtractor:
    """Extract text from PDF files."""

    def extract_text(self, pdf_path: str | Path) -> str:
        """Extract all text from a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text content as a single string

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            Exception: If PDF extraction fails
        """
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            with pdfplumber.open(pdf_path) as pdf:
                text_pages = []

                for page_num, page in enumerate(pdf.pages, start=1):
                    page_text = page.extract_text()

                    if page_text:
                        # Add page number marker
                        text_pages.append(f"--- Page {page_num} ---\n{page_text}")

                full_text = "\n\n".join(text_pages)
                return full_text

        except Exception as e:
            raise Exception(f"Failed to extract text from PDF: {e}") from e

    def extract_metadata(self, pdf_path: str | Path) -> dict:
        """Extract PDF metadata.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary with PDF metadata

        """
        pdf_path = Path(pdf_path)

        try:
            with pdfplumber.open(pdf_path) as pdf:
                return {
                    "num_pages": len(pdf.pages),
                    "metadata": pdf.metadata or {},
                }

        except Exception as e:
            return {"error": str(e)}
