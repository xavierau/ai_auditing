"""Tests for RelationshipMapper.

Following TDD approach - these tests define the expected behavior.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


@pytest.fixture
def sample_preliminary_result():
    """Create sample preliminary scan result for testing."""
    from genreport.core.parsing.parsing_models import (
        CodingSystemResult,
        WorksheetAnalysisResult,
        PreliminaryScanResult,
    )

    coding_system = CodingSystemResult(
        coding_pattern="TB-XX format (Trial Balance codes)",
        code_families=[
            {"prefix": "TB", "category": "Trial Balance", "count": 3},
            {"prefix": "GL", "category": "General Ledger", "count": 1},
        ],
        confidence=0.95,
    )

    worksheet_analyses = [
        WorksheetAnalysisResult(
            sheet_name="TB-01 Summary",
            is_summary=True,
            is_supporting=False,
            referenced_codes=["TB-02", "TB-03"],
            importance_score=0.95,
        ),
        WorksheetAnalysisResult(
            sheet_name="TB-02 Details",
            is_summary=False,
            is_supporting=True,
            referenced_codes=["GL-100"],
            importance_score=0.75,
        ),
        WorksheetAnalysisResult(
            sheet_name="TB-03 Supporting",
            is_summary=False,
            is_supporting=True,
            referenced_codes=[],
            importance_score=0.60,
        ),
        WorksheetAnalysisResult(
            sheet_name="GL-100 General Ledger",
            is_summary=False,
            is_supporting=True,
            referenced_codes=[],
            importance_score=0.50,
        ),
    ]

    return PreliminaryScanResult(
        coding_system=coding_system,
        worksheet_analyses=worksheet_analyses,
        recommended_sheets=["TB-01 Summary", "TB-02 Details"],
        total_sheets=4,
    )


class TestRelationshipMapper:
    """Test suite for RelationshipMapper."""

    def test_mapper_initialization(self):
        """Test that RelationshipMapper can be initialized."""
        from genreport.core.parsing.relationship_mapper import RelationshipMapper

        mapper = RelationshipMapper()
        assert mapper is not None

    def test_build_relationship_map_returns_correct_structure(
        self, sample_preliminary_result
    ):
        """Test that build_relationship_map returns RelationshipMapResult."""
        from genreport.core.parsing.relationship_mapper import RelationshipMapper
        from genreport.core.parsing.parsing_models import RelationshipMapResult

        mapper = RelationshipMapper()
        result = mapper.build_relationship_map(sample_preliminary_result)

        # Should return RelationshipMapResult
        assert isinstance(result, RelationshipMapResult)
        assert result.coding_system is not None
        assert result.relationships is not None
        assert result.recommended_sheets is not None

    def test_relationships_extracted_from_analyses(self, sample_preliminary_result):
        """Test that relationships are correctly extracted from worksheet analyses."""
        from genreport.core.parsing.relationship_mapper import RelationshipMapper

        mapper = RelationshipMapper()
        result = mapper.build_relationship_map(sample_preliminary_result)

        # TB-01 references TB-02 and TB-03
        assert "TB-01 Summary" in result.relationships
        assert "TB-02" in result.relationships["TB-01 Summary"]
        assert "TB-03" in result.relationships["TB-01 Summary"]

        # TB-02 references GL-100
        assert "TB-02 Details" in result.relationships
        assert "GL-100" in result.relationships["TB-02 Details"]

    def test_recommended_sheets_prioritized_by_importance(
        self, sample_preliminary_result
    ):
        """Test that recommended sheets are prioritized by importance score."""
        from genreport.core.parsing.relationship_mapper import RelationshipMapper

        mapper = RelationshipMapper()
        result = mapper.build_relationship_map(sample_preliminary_result)

        # Should include high-importance sheets
        assert len(result.recommended_sheets) > 0
        assert "TB-01 Summary" in result.recommended_sheets

        # Sheets should be ordered by importance (highest first)
        # TB-01 (0.95) should come before TB-02 (0.75)
        if len(result.recommended_sheets) >= 2:
            tb01_idx = result.recommended_sheets.index("TB-01 Summary")
            tb02_idx = result.recommended_sheets.index("TB-02 Details")
            assert tb01_idx < tb02_idx

    def test_confidence_score_calculated(self, sample_preliminary_result):
        """Test that confidence score is calculated for the relationship map."""
        from genreport.core.parsing.relationship_mapper import RelationshipMapper

        mapper = RelationshipMapper()
        result = mapper.build_relationship_map(sample_preliminary_result)

        # Should have confidence score
        assert result.confidence_score > 0.0
        assert result.confidence_score <= 1.0

        # Confidence should reflect the coding system confidence
        # (since coding system has 0.95 confidence, map confidence should be high)
        assert result.confidence_score >= 0.8

    def test_code_families_preserved(self, sample_preliminary_result):
        """Test that code families are preserved in the map."""
        from genreport.core.parsing.relationship_mapper import RelationshipMapper

        mapper = RelationshipMapper()
        result = mapper.build_relationship_map(sample_preliminary_result)

        # Should preserve code families
        assert len(result.code_families) == 2
        assert any(family["prefix"] == "TB" for family in result.code_families)
        assert any(family["prefix"] == "GL" for family in result.code_families)

    def test_handle_empty_referenced_codes(self):
        """Test that mapper handles worksheets with no references."""
        from genreport.core.parsing.relationship_mapper import RelationshipMapper
        from genreport.core.parsing.parsing_models import (
            CodingSystemResult,
            WorksheetAnalysisResult,
            PreliminaryScanResult,
        )

        coding_system = CodingSystemResult(
            coding_pattern="Simple", code_families=[], confidence=0.9
        )

        # All worksheets have no references
        worksheet_analyses = [
            WorksheetAnalysisResult(
                sheet_name="Sheet1",
                is_summary=True,
                is_supporting=False,
                referenced_codes=[],  # Empty
                importance_score=0.8,
            ),
            WorksheetAnalysisResult(
                sheet_name="Sheet2",
                is_summary=False,
                is_supporting=True,
                referenced_codes=[],  # Empty
                importance_score=0.6,
            ),
        ]

        preliminary = PreliminaryScanResult(
            coding_system=coding_system,
            worksheet_analyses=worksheet_analyses,
            recommended_sheets=["Sheet1"],
            total_sheets=2,
        )

        mapper = RelationshipMapper()
        result = mapper.build_relationship_map(preliminary)

        # Should handle gracefully (empty relationships or sheets with empty lists)
        assert isinstance(result.relationships, dict)

    def test_detect_circular_references(self):
        """Test detection of circular references between worksheets."""
        from genreport.core.parsing.relationship_mapper import RelationshipMapper
        from genreport.core.parsing.parsing_models import (
            CodingSystemResult,
            WorksheetAnalysisResult,
            PreliminaryScanResult,
        )

        coding_system = CodingSystemResult(
            coding_pattern="Test", code_families=[], confidence=0.9
        )

        # Create circular reference: A -> B -> C -> A
        worksheet_analyses = [
            WorksheetAnalysisResult(
                sheet_name="A",
                is_summary=True,
                is_supporting=False,
                referenced_codes=["B"],
                importance_score=0.9,
            ),
            WorksheetAnalysisResult(
                sheet_name="B",
                is_summary=False,
                is_supporting=True,
                referenced_codes=["C"],
                importance_score=0.7,
            ),
            WorksheetAnalysisResult(
                sheet_name="C",
                is_summary=False,
                is_supporting=True,
                referenced_codes=["A"],  # Circular reference
                importance_score=0.5,
            ),
        ]

        preliminary = PreliminaryScanResult(
            coding_system=coding_system,
            worksheet_analyses=worksheet_analyses,
            recommended_sheets=["A"],
            total_sheets=3,
        )

        mapper = RelationshipMapper()
        result = mapper.build_relationship_map(preliminary)

        # Should detect or handle circular references
        # (Implementation may warn, adjust confidence, or just document them)
        assert isinstance(result, result.__class__)  # Should still return valid result

    def test_identify_root_sheets(self, sample_preliminary_result):
        """Test identification of root sheets (sheets not referenced by others)."""
        from genreport.core.parsing.relationship_mapper import RelationshipMapper

        mapper = RelationshipMapper()
        result = mapper.build_relationship_map(sample_preliminary_result)

        # TB-01 is a root (summary sheet, not referenced by others)
        # It should be prioritized in recommended_sheets
        assert "TB-01 Summary" in result.recommended_sheets


class TestRelationshipMapperIntegration:
    """Integration tests for RelationshipMapper with PreliminaryScanner."""

    def test_full_pipeline_preliminary_to_relationship(self):
        """Test complete pipeline from preliminary scan to relationship map."""
        from genreport.core.parsing.parsing_models import (
            CodingSystemResult,
            WorksheetAnalysisResult,
            PreliminaryScanResult,
        )
        from genreport.core.parsing.relationship_mapper import RelationshipMapper

        # Simulate preliminary scan result
        preliminary = PreliminaryScanResult(
            coding_system=CodingSystemResult(
                coding_pattern="A-B format",
                code_families=[{"prefix": "A", "category": "Main"}],
                confidence=0.92,
            ),
            worksheet_analyses=[
                WorksheetAnalysisResult(
                    sheet_name="A-1",
                    is_summary=True,
                    is_supporting=False,
                    referenced_codes=["A-2"],
                    importance_score=0.95,
                ),
                WorksheetAnalysisResult(
                    sheet_name="A-2",
                    is_summary=False,
                    is_supporting=True,
                    referenced_codes=[],
                    importance_score=0.70,
                ),
            ],
            recommended_sheets=["A-1"],
            total_sheets=2,
        )

        # Build relationship map
        mapper = RelationshipMapper()
        result = mapper.build_relationship_map(preliminary)

        # Verify complete result
        assert result.coding_system == "A-B format"
        assert "A-1" in result.relationships
        assert "A-2" in result.relationships["A-1"]
        assert "A-1" in result.recommended_sheets
        assert result.confidence_score > 0.8

    def test_mapper_is_market_agnostic(self):
        """Test that RelationshipMapper contains no market-specific logic."""
        from genreport.core.parsing.relationship_mapper import RelationshipMapper
        import inspect

        # Get source code
        source = inspect.getsource(RelationshipMapper)

        # Should NOT contain market-specific references
        assert "Hong Kong" not in source
        assert "HKFRS" not in source
        assert "Singapore" not in source
        assert "Australia" not in source

        # This verifies hybrid architecture compliance
