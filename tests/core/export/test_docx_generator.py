"""
Tests for Market-Aware DOCX Generator

Test TDD methodology - tests written to verify DOCX generation with
market-specific formatting.
"""

import pytest
from pathlib import Path
from datetime import datetime
from docx import Document
from docx.document import Document as DocumentType

from genreport.core.export import MarketAwareDocxGenerator
from genreport.core.database.models import Jurisdiction


class TestMarketAwareDocxGenerator:
    """Test suite for MarketAwareDocxGenerator"""

    @pytest.fixture
    def sample_hk_data(self):
        """Sample Hong Kong project data"""
        return {
            'project_name': 'ABC Holdings Limited - Annual Audit 2024',
            'client_name': 'ABC Holdings Limited',
            'currency': 'HKD',
            'jurisdiction': 'HK',
            'accounting_standard': 'HKFRS 15',
            'financial_year_end': datetime(2024, 12, 31),
            'revenue': 15000000.00,
            'amount': 15000000.00,
            'sections': [
                {
                    'title': 'Revenue Recognition',
                    'content': 'The Company recognizes revenue when control transfers to customers.'
                }
            ]
        }

    @pytest.fixture
    def sample_sg_data(self):
        """Sample Singapore project data"""
        return {
            'project_name': 'Singapore Tech Pte Ltd - Q3 Review',
            'client_name': 'Singapore Tech Pte Ltd',
            'currency': 'SGD',
            'jurisdiction': 'SG',
            'accounting_standard': 'SFRS',
            'financial_year_end': datetime(2024, 9, 30),
            'revenue': 8500000.00,
            'amount': 8500000.00,
        }

    def test_generator_initialization_hk(self):
        """Test generator initializes correctly for Hong Kong"""
        generator = MarketAwareDocxGenerator(Jurisdiction.HK)

        assert generator.jurisdiction == Jurisdiction.HK
        assert 'hk' in str(generator.templates_path).lower()

    def test_generator_initialization_sg(self):
        """Test generator initializes correctly for Singapore"""
        generator = MarketAwareDocxGenerator(Jurisdiction.SG)

        assert generator.jurisdiction == Jurisdiction.SG
        assert 'sg' in str(generator.templates_path).lower()

    def test_generator_initialization_au(self):
        """Test generator initializes correctly for Australia"""
        generator = MarketAwareDocxGenerator(Jurisdiction.AU)

        assert generator.jurisdiction == Jurisdiction.AU
        assert 'au' in str(generator.templates_path).lower()

    def test_generate_creates_document(self, sample_hk_data, tmp_path):
        """Test generate() creates a DOCX document"""
        generator = MarketAwareDocxGenerator(Jurisdiction.HK)
        output_path = tmp_path / "test_report.docx"

        doc = generator.generate(sample_hk_data, output_path=output_path)

        assert isinstance(doc, DocumentType)
        assert output_path.exists()

    def test_generate_includes_project_name(self, sample_hk_data, tmp_path):
        """Test generated document includes project name"""
        generator = MarketAwareDocxGenerator(Jurisdiction.HK)
        output_path = tmp_path / "test_report.docx"

        generator.generate(sample_hk_data, output_path=output_path)

        # Read document and check content
        doc = Document(str(output_path))
        text_content = '\n'.join([para.text for para in doc.paragraphs])

        assert sample_hk_data['project_name'] in text_content

    def test_generate_includes_client_name(self, sample_hk_data, tmp_path):
        """Test generated document includes client name"""
        generator = MarketAwareDocxGenerator(Jurisdiction.HK)
        output_path = tmp_path / "test_report.docx"

        generator.generate(sample_hk_data, output_path=output_path)

        doc = Document(str(output_path))
        text_content = '\n'.join([para.text for para in doc.paragraphs])

        assert sample_hk_data['client_name'] in text_content

    def test_format_currency_hkd(self):
        """Test HKD currency formatting"""
        generator = MarketAwareDocxGenerator(Jurisdiction.HK)

        formatted = generator._format_currency(15000000.00, 'HKD')

        assert formatted == 'HK$15,000,000.00'

    def test_format_currency_sgd(self):
        """Test SGD currency formatting"""
        generator = MarketAwareDocxGenerator(Jurisdiction.SG)

        formatted = generator._format_currency(8500000.00, 'SGD')

        assert formatted == 'S$8,500,000.00'

    def test_format_currency_aud(self):
        """Test AUD currency formatting"""
        generator = MarketAwareDocxGenerator(Jurisdiction.AU)

        formatted = generator._format_currency(12000000.00, 'AUD')

        assert formatted == 'A$12,000,000.00'

    def test_format_date_dd_mm_yyyy(self):
        """Test date formatting for HK/SG/AU (DD/MM/YYYY)"""
        generator = MarketAwareDocxGenerator(Jurisdiction.HK)
        test_date = datetime(2024, 12, 31)

        formatted = generator._format_date(test_date)

        assert formatted == '31/12/2024'

    def test_get_date_format_hk(self):
        """Test date format string for Hong Kong"""
        generator = MarketAwareDocxGenerator(Jurisdiction.HK)

        format_string = generator._get_date_format()

        assert format_string == '%d/%m/%Y'

    def test_get_date_format_sg(self):
        """Test date format string for Singapore"""
        generator = MarketAwareDocxGenerator(Jurisdiction.SG)

        format_string = generator._get_date_format()

        assert format_string == '%d/%m/%Y'

    def test_get_date_format_au(self):
        """Test date format string for Australia"""
        generator = MarketAwareDocxGenerator(Jurisdiction.AU)

        format_string = generator._get_date_format()

        assert format_string == '%d/%m/%Y'

    def test_validate_report_data_valid(self, sample_hk_data):
        """Test validation passes for valid data"""
        generator = MarketAwareDocxGenerator(Jurisdiction.HK)

        # Should not raise
        generator._validate_report_data(sample_hk_data)

    def test_validate_report_data_missing_project_name(self):
        """Test validation fails when project_name missing"""
        generator = MarketAwareDocxGenerator(Jurisdiction.HK)
        invalid_data = {
            'client_name': 'Test Client',
            'currency': 'HKD',
            'financial_year_end': datetime.now()
        }

        with pytest.raises(ValueError, match="project_name"):
            generator._validate_report_data(invalid_data)

    def test_validate_report_data_missing_currency(self):
        """Test validation fails when currency missing"""
        generator = MarketAwareDocxGenerator(Jurisdiction.HK)
        invalid_data = {
            'project_name': 'Test Project',
            'client_name': 'Test Client',
            'financial_year_end': datetime.now()
        }

        with pytest.raises(ValueError, match="currency"):
            generator._validate_report_data(invalid_data)

    def test_generate_with_sections(self, sample_hk_data, tmp_path):
        """Test document generation includes sections"""
        generator = MarketAwareDocxGenerator(Jurisdiction.HK)
        output_path = tmp_path / "test_report.docx"

        generator.generate(sample_hk_data, output_path=output_path)

        doc = Document(str(output_path))
        text_content = '\n'.join([para.text for para in doc.paragraphs])

        # Check section title and content are present
        assert 'Revenue Recognition' in text_content
        assert 'control transfers to customers' in text_content

    def test_generate_singapore_project(self, sample_sg_data, tmp_path):
        """Test document generation for Singapore project"""
        generator = MarketAwareDocxGenerator(Jurisdiction.SG)
        output_path = tmp_path / "sg_report.docx"

        doc = generator.generate(sample_sg_data, output_path=output_path)

        assert isinstance(doc, DocumentType)
        assert output_path.exists()

        # Verify content
        doc = Document(str(output_path))
        text_content = '\n'.join([para.text for para in doc.paragraphs])

        assert 'Singapore Tech Pte Ltd' in text_content
        assert 'SG' in text_content or 'Singapore' in text_content
