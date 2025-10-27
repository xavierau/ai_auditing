"""
Market Isolation Tests

Validates hybrid architecture principles:
- No hardcoded jurisdictions in core/
- Proper config switching between markets
- KB filtering by jurisdiction
- Template selection by market

Sprint 6 Phase 1
"""

import pytest
from pathlib import Path
from uuid import uuid4

from genreport.core.database.models import Jurisdiction
from genreport.core.export import MarketAwareDocxGenerator


class TestMarketIsolation:
    """Test suite for hybrid architecture market isolation"""

    def test_no_hardcoded_hk_in_core(self):
        """Verify core/ has no Hong Kong specific hardcoded values"""

        core_path = Path(__file__).parent.parent.parent / "genreport" / "core"

        # Terms that should NOT appear in core/
        hardcoded_markets = [
            'Hong Kong',
            'HKFRS',  # Should use config, not hardcoded
            'HKICPA',
            'HK$',  # Should use currency formatter
        ]

        violations = []

        # Scan all Python files in core/
        for py_file in core_path.rglob("*.py"):
            content = py_file.read_text()

            for term in hardcoded_markets:
                if term in content:
                    violations.append(f"Found '{term}' in {py_file.relative_to(core_path)}")

        assert len(violations) == 0, f"Hardcoded market values found:\n" + "\n".join(violations)

    def test_no_hardcoded_sg_in_core(self):
        """Verify core/ has no Singapore specific hardcoded values"""

        core_path = Path(__file__).parent.parent.parent / "genreport" / "core"

        hardcoded_markets = [
            'Singapore',
            'SFRS',
            'S$',
            'ACRA',
        ]

        violations = []

        for py_file in core_path.rglob("*.py"):
            content = py_file.read_text()

            for term in hardcoded_markets:
                if term in content:
                    violations.append(f"Found '{term}' in {py_file.relative_to(core_path)}")

        assert len(violations) == 0, f"Hardcoded market values found:\n" + "\n".join(violations)

    def test_no_hardcoded_au_in_core(self):
        """Verify core/ has no Australia specific hardcoded values"""

        core_path = Path(__file__).parent.parent.parent / "genreport" / "core"

        hardcoded_markets = [
            'Australia',
            'AASB',
            'A$',
            'ASIC',
        ]

        violations = []

        for py_file in core_path.rglob("*.py"):
            content = py_file.read_text()

            for term in hardcoded_markets:
                if term in content:
                    violations.append(f"Found '{term}' in {py_file.relative_to(core_path)}")

        assert len(violations) == 0, f"Hardcoded market values found:\n" + "\n".join(violations)

    def test_jurisdiction_enum_values(self):
        """Test Jurisdiction enum has expected values"""

        assert Jurisdiction.HK.value == "HK"
        assert Jurisdiction.SG.value == "SG"
        assert Jurisdiction.AU.value == "AU"

        # Should have exactly 3 jurisdictions
        assert len(list(Jurisdiction)) == 3

    def test_docx_generator_market_switching(self):
        """Test DOCX generator correctly switches between markets"""

        # Test HK
        hk_generator = MarketAwareDocxGenerator(Jurisdiction.HK)
        assert hk_generator.jurisdiction == Jurisdiction.HK
        assert 'hk' in str(hk_generator.templates_path).lower()

        # Test SG
        sg_generator = MarketAwareDocxGenerator(Jurisdiction.SG)
        assert sg_generator.jurisdiction == Jurisdiction.SG
        assert 'sg' in str(sg_generator.templates_path).lower()

        # Test AU
        au_generator = MarketAwareDocxGenerator(Jurisdiction.AU)
        assert au_generator.jurisdiction == Jurisdiction.AU
        assert 'au' in str(au_generator.templates_path).lower()

    def test_currency_formatting_per_market(self):
        """Test currency formatting respects market"""

        amount = 1234567.89

        # HK
        hk_gen = MarketAwareDocxGenerator(Jurisdiction.HK)
        hk_formatted = hk_gen._format_currency(amount, 'HKD')
        assert hk_formatted == 'HK$1,234,567.89'

        # SG
        sg_gen = MarketAwareDocxGenerator(Jurisdiction.SG)
        sg_formatted = sg_gen._format_currency(amount, 'SGD')
        assert sg_formatted == 'S$1,234,567.89'

        # AU
        au_gen = MarketAwareDocxGenerator(Jurisdiction.AU)
        au_formatted = au_gen._format_currency(amount, 'AUD')
        assert au_formatted == 'A$1,234,567.89'

    def test_date_formatting_consistent_across_markets(self):
        """Test date formatting is consistent for HK, SG, AU"""

        from datetime import datetime
        test_date = datetime(2024, 12, 31)

        # All markets should use DD/MM/YYYY
        hk_gen = MarketAwareDocxGenerator(Jurisdiction.HK)
        assert hk_gen._format_date(test_date) == '31/12/2024'

        sg_gen = MarketAwareDocxGenerator(Jurisdiction.SG)
        assert sg_gen._format_date(test_date) == '31/12/2024'

        au_gen = MarketAwareDocxGenerator(Jurisdiction.AU)
        assert au_gen._format_date(test_date) == '31/12/2024'

    def test_template_paths_market_specific(self):
        """Verify template paths are in correct market directories"""

        hk_gen = MarketAwareDocxGenerator(Jurisdiction.HK)
        assert 'markets/hk/templates' in str(hk_gen.templates_path)

        sg_gen = MarketAwareDocxGenerator(Jurisdiction.SG)
        assert 'markets/sg/templates' in str(sg_gen.templates_path)

        au_gen = MarketAwareDocxGenerator(Jurisdiction.AU)
        assert 'markets/au/templates' in str(au_gen.templates_path)


class TestKBJurisdictionFiltering:
    """Test Knowledge Base filtering by jurisdiction"""

    def test_kb_chunk_has_jurisdiction_field(self):
        """Verify KB chunks include jurisdiction field"""
        from genreport.core.database.models import KBChunk

        # Check model has jurisdiction column
        assert hasattr(KBChunk, 'jurisdiction')

        # Should be a string column
        jurisdiction_col = KBChunk.__table__.columns['jurisdiction']
        assert jurisdiction_col.type.python_type == str

    def test_kb_document_has_jurisdiction_field(self):
        """Verify KB documents include jurisdiction field"""
        from genreport.core.database.models import KnowledgeBase

        # Check model has jurisdiction column
        assert hasattr(KnowledgeBase, 'jurisdiction')

        # Should be a required field (not nullable)
        jurisdiction_col = KnowledgeBase.__table__.columns['jurisdiction']
        assert not jurisdiction_col.nullable


class TestTenantDataIsolation:
    """Test tenant data cannot cross tenant boundaries"""

    def test_project_has_tenant_id(self):
        """Verify Project model has tenant_id"""
        from genreport.core.database.models import Project

        assert hasattr(Project, 'tenant_id')

        # Should be required (not nullable)
        tenant_id_col = Project.__table__.columns['tenant_id']
        assert not tenant_id_col.nullable

    def test_file_metadata_has_tenant_id(self):
        """Verify FileMetadata model has tenant_id"""
        from genreport.core.database.models import FileMetadata

        assert hasattr(FileMetadata, 'tenant_id')

        # Should be required
        tenant_id_col = FileMetadata.__table__.columns['tenant_id']
        assert not tenant_id_col.nullable

    def test_generated_report_has_tenant_id(self):
        """Verify GeneratedReport model has tenant_id"""
        from genreport.core.database.models import GeneratedReport

        assert hasattr(GeneratedReport, 'tenant_id')

        # Should be required
        tenant_id_col = GeneratedReport.__table__.columns['tenant_id']
        assert not tenant_id_col.nullable


class TestMarketConfigPattern:
    """Test market configuration follows dependency injection pattern"""

    def test_hk_market_config_exists(self):
        """Verify Hong Kong market config exists"""
        from genreport.markets.hk.config import HKMarketConfig

        config = HKMarketConfig()

        assert config.jurisdiction == "HK"
        assert config.currency == "HKD"
        assert len(config.accounting_standards) > 0

    def test_market_config_is_injectable(self):
        """Verify market config can be injected into components"""

        # Config should not be a singleton - each component gets its own
        from genreport.markets.hk.config import HKMarketConfig

        config1 = HKMarketConfig()
        config2 = HKMarketConfig()

        # Different instances (not singleton pattern)
        assert config1 is not config2

        # But same values
        assert config1.jurisdiction == config2.jurisdiction
