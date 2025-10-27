"""
Market-Aware DOCX Generator

Generates DOCX reports using jurisdiction-specific templates with proper
currency and date formatting.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from genreport.core.database.models import Jurisdiction


class MarketAwareDocxGenerator:
    """
    Generate DOCX reports using market-specific templates.

    Follows hybrid architecture pattern - uses jurisdiction-specific templates
    while maintaining market-agnostic core logic.
    """

    def __init__(self, jurisdiction: Jurisdiction):
        """
        Initialize generator for specific jurisdiction.

        Args:
            jurisdiction: Target jurisdiction (HK, SG, AU)
        """
        self.jurisdiction = jurisdiction
        self.templates_path = self._get_templates_path()

    def _get_templates_path(self) -> Path:
        """
        Get market-specific templates directory.

        Returns:
            Path to jurisdiction templates directory
        """
        base_path = Path(__file__).parent.parent.parent
        return base_path / "markets" / self.jurisdiction.value.lower() / "templates"

    def generate(
        self,
        report_data: Dict[str, Any],
        template_name: str = "audit_report.docx",
        output_path: Optional[Path] = None
    ) -> Document:
        """
        Generate DOCX report from market-specific template.

        Args:
            report_data: Report data including sections, currency, dates
            template_name: Template filename to use
            output_path: Optional path to save document

        Returns:
            Generated Document object

        Raises:
            FileNotFoundError: If template doesn't exist
            ValueError: If required data is missing
        """
        # Validate required data
        self._validate_report_data(report_data)

        # Load template
        template_path = self.templates_path / template_name

        if not template_path.exists():
            # Create blank document if template doesn't exist
            doc = Document()
            self._add_default_structure(doc, report_data)
        else:
            doc = Document(str(template_path))
            # Replace placeholders
            self._replace_placeholders(doc, report_data)

        # Apply market-specific formatting
        self._apply_market_formatting(doc, report_data)

        # Save if output path provided
        if output_path:
            doc.save(str(output_path))

        return doc

    def _validate_report_data(self, data: Dict[str, Any]) -> None:
        """
        Validate required fields in report data.

        Args:
            data: Report data dictionary

        Raises:
            ValueError: If required fields are missing
        """
        required_fields = ['project_name', 'client_name', 'currency', 'financial_year_end']
        missing = [field for field in required_fields if field not in data]

        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

    def _add_default_structure(self, doc: Document, data: Dict[str, Any]) -> None:
        """
        Add default document structure when template doesn't exist.

        Args:
            doc: Document object to modify
            data: Report data
        """
        # Title
        title = doc.add_heading(data['project_name'], 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Client information
        doc.add_heading('Client Information', 1)
        doc.add_paragraph(f"Client: {data['client_name']}")
        doc.add_paragraph(f"Financial Year End: {self._format_date(data['financial_year_end'])}")
        doc.add_paragraph(f"Currency: {data['currency']}")
        doc.add_paragraph(f"Jurisdiction: {self.jurisdiction.value}")

        # Sections
        if 'sections' in data:
            for section in data['sections']:
                doc.add_heading(section.get('title', 'Section'), 1)

                # Add content as paragraphs
                content = section.get('content', '')
                for paragraph in content.split('\n'):
                    if paragraph.strip():
                        doc.add_paragraph(paragraph.strip())

    def _replace_placeholders(self, doc: Document, data: Dict[str, Any]) -> None:
        """
        Replace {{placeholders}} in document with actual data.

        Args:
            doc: Document object to modify
            data: Report data
        """
        # Build replacement map
        replacements = {
            'project_name': data.get('project_name', ''),
            'client_name': data.get('client_name', ''),
            'currency': data.get('currency', ''),
            'jurisdiction': self.jurisdiction.value,
            'accounting_standard': data.get('accounting_standard', ''),
            'date': self._format_date(datetime.now()),
            'financial_year_end': self._format_date(data.get('financial_year_end', '')),
        }

        # Replace in paragraphs
        for paragraph in doc.paragraphs:
            for key, value in replacements.items():
                placeholder = f"{{{{{key}}}}}"
                if placeholder in paragraph.text:
                    paragraph.text = paragraph.text.replace(placeholder, str(value))

        # Replace in tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for key, value in replacements.items():
                        placeholder = f"{{{{{key}}}}}"
                        if placeholder in cell.text:
                            cell.text = cell.text.replace(placeholder, str(value))

    def _apply_market_formatting(self, doc: Document, data: Dict[str, Any]) -> None:
        """
        Apply jurisdiction-specific formatting to document.

        Args:
            doc: Document object to modify
            data: Report data including currency and amounts
        """
        currency = data.get('currency', 'HKD')

        # Format currency values in tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    # Look for currency placeholder patterns
                    if '{{amount' in cell.text or '{{revenue' in cell.text or '{{total' in cell.text:
                        # Extract amount from data
                        for key in ['amount', 'revenue', 'total']:
                            if key in data:
                                formatted = self._format_currency(data[key], currency)
                                cell.text = cell.text.replace(f"{{{{{key}}}}}", formatted)

        # Format dates
        date_format = self._get_date_format()
        for paragraph in doc.paragraphs:
            if '{{date' in paragraph.text:
                formatted_date = datetime.now().strftime(date_format)
                paragraph.text = paragraph.text.replace('{{date}}', formatted_date)

    def _format_currency(self, amount: float, currency: str) -> str:
        """
        Format currency amount for jurisdiction.

        Args:
            amount: Amount to format
            currency: Currency code (HKD, SGD, AUD)

        Returns:
            Formatted currency string
        """
        symbols = {
            'HKD': 'HK$',
            'SGD': 'S$',
            'AUD': 'A$',
        }

        symbol = symbols.get(currency, currency)
        return f"{symbol}{amount:,.2f}"

    def _format_date(self, date: Any) -> str:
        """
        Format date for jurisdiction.

        Args:
            date: Date to format (datetime, string, or None)

        Returns:
            Formatted date string
        """
        if isinstance(date, str):
            try:
                date = datetime.fromisoformat(date.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                return date

        if not isinstance(date, datetime):
            return str(date)

        date_format = self._get_date_format()
        return date.strftime(date_format)

    def _get_date_format(self) -> str:
        """
        Get date format string for jurisdiction.

        Returns:
            strftime format string
        """
        # All target jurisdictions use DD/MM/YYYY
        formats = {
            Jurisdiction.HK: '%d/%m/%Y',
            Jurisdiction.SG: '%d/%m/%Y',
            Jurisdiction.AU: '%d/%m/%Y',
        }
        return formats.get(self.jurisdiction, '%d/%m/%Y')
