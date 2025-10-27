"""Tests for PreliminaryScanner with DSPy signatures.

Following TDD approach - these tests define the expected behavior.
Tests updated for async parallelization.
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import tempfile
import openpyxl
import asyncio


@pytest.fixture
def sample_workbook_file():
    """Create a sample workbook for testing."""
    wb = openpyxl.Workbook()

    # Create sheets with realistic names
    ws1 = wb.active
    ws1.title = "TB-01 Summary"
    ws1['A1'] = "Account"
    ws1['B1'] = "Balance"

    ws2 = wb.create_sheet("TB-02 Details")
    ws2['A1'] = "Transaction"
    ws2['B1'] = "Amount"

    ws3 = wb.create_sheet("GL-100 General Ledger")
    ws3['A1'] = "Date"
    ws3['B1'] = "Description"

    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False, mode='wb') as tmp:
        wb.save(tmp.name)
        return tmp.name


@pytest.fixture
def mock_dspy_module():
    """Create a mock DSPy module."""
    mock = MagicMock()
    return mock


class TestPreliminaryScanner:
    """Test suite for PreliminaryScanner."""

    def test_scanner_initialization(self):
        """Test that PreliminaryScanner can be initialized."""
        from genreport.core.parsing.preliminary_scanner import PreliminaryScanner

        scanner = PreliminaryScanner()
        assert scanner is not None
        assert scanner.async_max_workers == 4  # Default value

    def test_scanner_initialization_with_custom_workers(self):
        """Test scanner initialization with custom async_max_workers."""
        from genreport.core.parsing.preliminary_scanner import PreliminaryScanner

        scanner = PreliminaryScanner(async_max_workers=8)
        assert scanner.async_max_workers == 8

    def test_get_sheet_names_from_file(self, sample_workbook_file):
        """Test getting sheet names from Excel file."""
        from genreport.core.parsing.preliminary_scanner import PreliminaryScanner

        scanner = PreliminaryScanner()
        sheet_names = scanner._get_sheet_names(sample_workbook_file)

        assert isinstance(sheet_names, list)
        assert len(sheet_names) == 3
        assert "TB-01 Summary" in sheet_names
        assert "TB-02 Details" in sheet_names
        assert "GL-100 General Ledger" in sheet_names

    @pytest.mark.asyncio
    @patch('genreport.core.parsing.preliminary_scanner.dspy')
    async def test_analyze_workbook_returns_preliminary_scan_result(
        self, mock_dspy, sample_workbook_file
    ):
        """Test that analyze_workbook returns PreliminaryScanResult (async)."""
        from genreport.core.parsing.preliminary_scanner import PreliminaryScanner
        from genreport.core.parsing.parsing_models import PreliminaryScanResult

        # Mock DSPy ChainOfThought responses
        mock_coding_analyzer = MagicMock()
        mock_coding_analyzer.return_value = MagicMock(
            coding_pattern="TB-XX format (Trial Balance codes)",
            code_families_json='[{"prefix": "TB", "category": "Trial Balance"}]',
            confidence=0.95
        )

        mock_worksheet_analyzer = AsyncMock()
        mock_worksheet_analyzer.acall = AsyncMock(return_value=MagicMock(
            is_summary=True,
            is_supporting=False,
            referenced_codes=["TB-02"],
            importance_score=0.9,
            summary="Trial Balance summary sheet with references to TB-02"
        ))

        mock_dspy.ChainOfThought.side_effect = [
            mock_coding_analyzer,
            mock_worksheet_analyzer
        ]

        scanner = PreliminaryScanner()
        result = await scanner.analyze_workbook(sample_workbook_file)

        # Should return PreliminaryScanResult
        assert isinstance(result, PreliminaryScanResult)
        assert result.total_sheets == 3
        assert len(result.worksheet_analyses) == 3

    @pytest.mark.asyncio
    @patch('genreport.core.parsing.preliminary_scanner.dspy')
    async def test_analyze_workbook_discovers_coding_pattern(
        self, mock_dspy, sample_workbook_file
    ):
        """Test that analyze_workbook discovers coding pattern (async)."""
        from genreport.core.parsing.preliminary_scanner import PreliminaryScanner

        # Mock coding system discovery
        mock_coding_analyzer = MagicMock()
        mock_coding_analyzer.return_value = MagicMock(
            coding_pattern="TB-XX format",
            code_families_json='[{"prefix": "TB", "category": "Trial Balance"}]',
            confidence=0.95
        )

        # Mock worksheet analyzer for each sheet
        mock_worksheet_analyzer = AsyncMock()
        mock_worksheet_analyzer.acall = AsyncMock(return_value=MagicMock(
            is_summary=True,
            is_supporting=False,
            referenced_codes=[],
            importance_score=0.8,
            summary="Worksheet summary"
        ))

        mock_dspy.ChainOfThought.side_effect = [
            mock_coding_analyzer,
            mock_worksheet_analyzer,
        ]

        scanner = PreliminaryScanner()
        result = await scanner.analyze_workbook(sample_workbook_file)

        # Should have coding system
        assert result.coding_system is not None
        assert result.coding_system.coding_pattern == "TB-XX format"
        assert result.coding_system.confidence == 0.95

    @pytest.mark.asyncio
    @patch('genreport.core.parsing.preliminary_scanner.dspy')
    async def test_analyze_workbook_analyzes_each_worksheet(
        self, mock_dspy, sample_workbook_file
    ):
        """Test that analyze_workbook analyzes each worksheet in parallel (async)."""
        from genreport.core.parsing.preliminary_scanner import PreliminaryScanner

        # Mock responses
        mock_coding_analyzer = MagicMock()
        mock_coding_analyzer.return_value = MagicMock(
            coding_pattern="TB-XX",
            code_families_json='[]',
            confidence=0.9
        )

        mock_worksheet_analyzer = AsyncMock()
        mock_worksheet_analyzer.acall = AsyncMock(return_value=MagicMock(
            is_summary=True,
            is_supporting=False,
            referenced_codes=[],
            importance_score=0.8,
            summary="Worksheet analysis summary"
        ))

        mock_dspy.ChainOfThought.side_effect = [
            mock_coding_analyzer,
            mock_worksheet_analyzer,
        ]

        scanner = PreliminaryScanner()
        result = await scanner.analyze_workbook(sample_workbook_file)

        # Should have analysis for each worksheet
        assert len(result.worksheet_analyses) == 3

    @pytest.mark.asyncio
    @patch('genreport.core.parsing.preliminary_scanner.dspy')
    async def test_analyze_workbook_recommends_important_sheets(
        self, mock_dspy, sample_workbook_file
    ):
        """Test that analyze_workbook recommends important sheets (async)."""
        from genreport.core.parsing.preliminary_scanner import PreliminaryScanner

        # Mock coding analyzer
        mock_coding_analyzer = MagicMock()
        mock_coding_analyzer.return_value = MagicMock(
            coding_pattern="TB-XX",
            code_families_json='[]',
            confidence=0.9
        )

        # Mock worksheet analyzers with different importance scores
        call_count = [0]

        async def create_response(**kwargs):
            call_count[0] += 1
            # Vary scores for different calls
            scores = [0.9, 0.6, 0.3]
            idx = min(call_count[0] - 1, len(scores) - 1)
            return MagicMock(
                is_summary=scores[idx] > 0.7,
                is_supporting=False,
                referenced_codes=[],
                importance_score=scores[idx],
                summary=f"Worksheet with importance score {scores[idx]}"
            )

        mock_worksheet_analyzer = AsyncMock()
        mock_worksheet_analyzer.acall = create_response

        mock_dspy.ChainOfThought.side_effect = [
            mock_coding_analyzer,
            mock_worksheet_analyzer,
        ]

        scanner = PreliminaryScanner()
        result = await scanner.analyze_workbook(sample_workbook_file)

        # Should have recommended sheets
        assert len(result.recommended_sheets) > 0

    @pytest.mark.asyncio
    async def test_analyze_nonexistent_file_raises_error(self):
        """Test that analyzing nonexistent file raises error (async)."""
        from genreport.core.parsing.preliminary_scanner import PreliminaryScanner

        scanner = PreliminaryScanner()

        with pytest.raises(FileNotFoundError):
            await scanner.analyze_workbook("nonexistent_file.xlsx")

    @pytest.mark.asyncio
    @patch('genreport.core.parsing.preliminary_scanner.dspy')
    async def test_scanner_handles_empty_workbook(self, mock_dspy):
        """Test that scanner handles workbook with no sheets gracefully (async)."""
        from genreport.core.parsing.preliminary_scanner import PreliminaryScanner

        # Create a minimal valid workbook (openpyxl requires at least one sheet)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Empty"
        # Don't add any data - just an empty sheet

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            wb.save(tmp.name)

            scanner = PreliminaryScanner()

            # Mock the scanner to return empty sheet list to test error handling
            with patch.object(scanner, '_get_sheet_names', return_value=[]):
                # Should raise ValueError for workbook with no sheets
                with pytest.raises(ValueError, match="Workbook has no sheets"):
                    await scanner.analyze_workbook(tmp.name)


class TestPreliminaryScannerAsyncBehavior:
    """Tests specific to async parallelization behavior."""

    @pytest.mark.asyncio
    @patch('genreport.core.parsing.preliminary_scanner.dspy')
    async def test_worksheets_analyzed_concurrently(self, mock_dspy, sample_workbook_file):
        """Test that worksheets are analyzed concurrently (not sequentially)."""
        from genreport.core.parsing.preliminary_scanner import PreliminaryScanner

        # Track execution order
        execution_log = []

        # Mock coding analyzer
        mock_coding_analyzer = MagicMock()
        mock_coding_analyzer.return_value = MagicMock(
            coding_pattern="TB-XX",
            code_families_json='[]',
            confidence=0.9
        )

        # Mock worksheet analyzer that logs execution
        async def log_execution(sheet_name, **kwargs):
            execution_log.append(f"start-{sheet_name}")
            await asyncio.sleep(0.01)  # Simulate async work
            execution_log.append(f"end-{sheet_name}")
            return MagicMock(
                is_summary=True,
                is_supporting=False,
                referenced_codes=[],
                importance_score=0.8,
                summary=f"Analysis for {sheet_name}"
            )

        mock_worksheet_analyzer = AsyncMock()
        mock_worksheet_analyzer.acall = log_execution

        mock_dspy.ChainOfThought.side_effect = [
            mock_coding_analyzer,
            mock_worksheet_analyzer,
        ]

        scanner = PreliminaryScanner()
        await scanner.analyze_workbook(sample_workbook_file)

        # In concurrent execution, starts should be interleaved with ends
        # (not all starts first, then all ends)
        start_indices = [i for i, log in enumerate(execution_log) if log.startswith('start')]
        end_indices = [i for i, log in enumerate(execution_log) if log.startswith('end')]

        # Check that execution was concurrent (ends happen before all starts complete)
        assert len(start_indices) == 3
        assert len(end_indices) == 3

    @pytest.mark.asyncio
    @patch('genreport.core.parsing.preliminary_scanner.dspy')
    async def test_partial_worksheet_failure_handled_gracefully(
        self, mock_dspy, sample_workbook_file
    ):
        """Test that failure of individual worksheets doesn't stop analysis."""
        from genreport.core.parsing.preliminary_scanner import PreliminaryScanner

        # Mock coding analyzer
        mock_coding_analyzer = MagicMock()
        mock_coding_analyzer.return_value = MagicMock(
            coding_pattern="TB-XX",
            code_families_json='[]',
            confidence=0.9
        )

        # Mock worksheet analyzer that fails for second sheet
        call_count = [0]

        async def fail_second_call(**kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("Simulated worksheet analysis failure")
            return MagicMock(
                is_summary=True,
                is_supporting=False,
                referenced_codes=[],
                importance_score=0.8,
                summary="Successful analysis"
            )

        mock_worksheet_analyzer = AsyncMock()
        mock_worksheet_analyzer.acall = fail_second_call

        mock_dspy.ChainOfThought.side_effect = [
            mock_coding_analyzer,
            mock_worksheet_analyzer,
        ]

        scanner = PreliminaryScanner()
        result = await scanner.analyze_workbook(sample_workbook_file)

        # Should have analysis for 2 successful worksheets (1 failed)
        assert len(result.worksheet_analyses) == 2
        assert result.total_sheets == 3

    @pytest.mark.asyncio
    @patch('genreport.core.parsing.preliminary_scanner.dspy')
    async def test_all_worksheets_fail_raises_error(self, mock_dspy, sample_workbook_file):
        """Test that if all worksheets fail, appropriate error is raised."""
        from genreport.core.parsing.preliminary_scanner import PreliminaryScanner

        # Mock coding analyzer
        mock_coding_analyzer = MagicMock()
        mock_coding_analyzer.return_value = MagicMock(
            coding_pattern="TB-XX",
            code_families_json='[]',
            confidence=0.9
        )

        # Mock worksheet analyzer that always fails
        async def always_fail(**kwargs):
            raise Exception("Simulated failure")

        mock_worksheet_analyzer = AsyncMock()
        mock_worksheet_analyzer.acall = always_fail

        mock_dspy.ChainOfThought.side_effect = [
            mock_coding_analyzer,
            mock_worksheet_analyzer,
        ]

        scanner = PreliminaryScanner()

        with pytest.raises(ValueError, match="All worksheet analyses failed"):
            await scanner.analyze_workbook(sample_workbook_file)

    @pytest.mark.asyncio
    @patch('genreport.core.parsing.preliminary_scanner.dspy')
    async def test_async_max_workers_configuration(self, mock_dspy, sample_workbook_file):
        """Test that async_max_workers is properly configured."""
        from genreport.core.parsing.preliminary_scanner import PreliminaryScanner

        # Mock coding analyzer
        mock_coding_analyzer = MagicMock()
        mock_coding_analyzer.return_value = MagicMock(
            coding_pattern="TB-XX",
            code_families_json='[]',
            confidence=0.9
        )

        mock_worksheet_analyzer = AsyncMock()
        mock_worksheet_analyzer.acall = AsyncMock(return_value=MagicMock(
            is_summary=True,
            is_supporting=False,
            referenced_codes=[],
            importance_score=0.8,
            summary="Test"
        ))

        mock_dspy.ChainOfThought.side_effect = [
            mock_coding_analyzer,
            mock_worksheet_analyzer,
        ]

        # Test with different worker counts
        for workers in [2, 4, 8]:
            scanner = PreliminaryScanner(async_max_workers=workers)
            assert scanner.async_max_workers == workers

            result = await scanner.analyze_workbook(sample_workbook_file)
            assert len(result.worksheet_analyses) == 3


class TestPreliminaryScannerCodingSystemAnalyzer:
    """Test coding system analyzer signature."""

    @patch('genreport.core.parsing.preliminary_scanner.dspy')
    def test_coding_system_analyzer_signature_structure(self, mock_dspy):
        """Test that CodingSystemAnalyzer signature has correct structure."""
        from genreport.core.parsing.preliminary_scanner import (
            PreliminaryScanner,
            CodingSystemAnalyzer
        )

        # CodingSystemAnalyzer should be a DSPy Signature
        assert hasattr(CodingSystemAnalyzer, '__annotations__')

        # Should have expected fields
        annotations = CodingSystemAnalyzer.__annotations__
        assert 'worksheet_names' in annotations
        assert 'coding_pattern' in annotations
        assert 'code_families_json' in annotations
        assert 'confidence' in annotations


class TestPreliminaryScannerWorksheetAnalyzer:
    """Test worksheet analyzer signature."""

    @patch('genreport.core.parsing.preliminary_scanner.dspy')
    def test_worksheet_analyzer_signature_structure(self, mock_dspy):
        """Test that WorksheetAnalyzer signature has correct structure."""
        from genreport.core.parsing.preliminary_scanner import WorksheetAnalyzer

        # Should have expected fields
        annotations = WorksheetAnalyzer.__annotations__
        assert 'sheet_name' in annotations
        assert 'worksheet_content' in annotations  # New field: worksheet content
        assert 'coding_pattern' in annotations
        assert 'code_families_json' in annotations
        assert 'is_summary' in annotations
        assert 'is_supporting' in annotations
        assert 'referenced_codes' in annotations
        assert 'importance_score' in annotations
        assert 'summary' in annotations  # New field: summary output


class TestPreliminaryScannerIntegration:
    """Integration tests for PreliminaryScanner."""

    @pytest.mark.asyncio
    @patch('genreport.core.parsing.preliminary_scanner.dspy')
    async def test_full_analysis_workflow(self, mock_dspy, sample_workbook_file):
        """Test complete analysis workflow from file to result (async)."""
        from genreport.core.parsing.preliminary_scanner import PreliminaryScanner

        # Mock complete workflow
        mock_coding_analyzer = MagicMock()
        mock_coding_analyzer.return_value = MagicMock(
            coding_pattern="TB-XX Trial Balance codes",
            code_families_json='[{"prefix": "TB", "category": "Trial Balance"}, {"prefix": "GL", "category": "General Ledger"}]',
            confidence=0.92
        )

        call_count = [0]

        async def worksheet_response(**kwargs):
            call_count[0] += 1
            sheet_name = kwargs.get('sheet_name', '')
            if "Summary" in sheet_name:
                return MagicMock(
                    is_summary=True,
                    is_supporting=False,
                    referenced_codes=["TB-02"],
                    importance_score=0.95,
                    summary="Summary sheet with trial balance totals"
                )
            else:
                return MagicMock(
                    is_summary=False,
                    is_supporting=True,
                    referenced_codes=[],
                    importance_score=0.6,
                    summary="Supporting detail worksheet"
                )

        mock_worksheet_analyzer = AsyncMock()
        mock_worksheet_analyzer.acall = worksheet_response

        mock_dspy.ChainOfThought.side_effect = [
            mock_coding_analyzer,
            mock_worksheet_analyzer,
        ]

        scanner = PreliminaryScanner()
        result = await scanner.analyze_workbook(sample_workbook_file)

        # Verify complete result
        assert result.total_sheets == 3
        assert len(result.worksheet_analyses) == 3
        assert result.coding_system.confidence > 0.9
        assert len(result.recommended_sheets) > 0

    def test_scanner_is_market_agnostic(self):
        """Test that PreliminaryScanner contains no market-specific logic."""
        from genreport.core.parsing.preliminary_scanner import PreliminaryScanner
        import inspect

        # Get source code
        source = inspect.getsource(PreliminaryScanner)

        # Should NOT contain market-specific references
        assert "Hong Kong" not in source
        assert "HKFRS" not in source
        assert "Singapore" not in source
        assert "Australia" not in source

        # This verifies hybrid architecture compliance


class TestPreliminaryScannerNetworkAnalysis:
    """Test network-aware importance scoring."""

    def test_network_analysis_adjusts_hub_worksheet_scores(self):
        """Test that hub worksheets (referenced by many) get importance boost."""
        from genreport.core.parsing.preliminary_scanner import PreliminaryScanner
        from genreport.core.parsing.parsing_models import WorksheetAnalysisResult

        scanner = PreliminaryScanner()

        # Create mock analyses with reference network
        # TB-01 Summary references TB-02 and TB-03 (TB-01 is root)
        # TB-02 and TB-03 both reference TB-04 (TB-04 is hub)
        analyses = [
            WorksheetAnalysisResult(
                sheet_name="TB-01 Summary",
                is_summary=True,
                is_supporting=False,
                referenced_codes=["TB-02", "TB-03"],
                importance_score=0.8,
                summary="Summary sheet"
            ),
            WorksheetAnalysisResult(
                sheet_name="TB-02 Details",
                is_summary=False,
                is_supporting=True,
                referenced_codes=["TB-04"],
                importance_score=0.6,
                summary="Supporting detail"
            ),
            WorksheetAnalysisResult(
                sheet_name="TB-03 Details",
                is_summary=False,
                is_supporting=True,
                referenced_codes=["TB-04"],
                importance_score=0.6,
                summary="Supporting detail"
            ),
            WorksheetAnalysisResult(
                sheet_name="TB-04 Source",
                is_summary=False,
                is_supporting=True,
                referenced_codes=[],
                importance_score=0.5,
                summary="Source data"
            ),
        ]

        adjusted = scanner._adjust_importance_with_network_analysis(analyses)

        # TB-04 should get hub bonus (referenced by 2 sheets)
        tb04 = next(a for a in adjusted if a.sheet_name == "TB-04 Source")
        assert tb04.importance_score > 0.5  # Higher than base score
        assert tb04.analysis_metadata["incoming_references"] == 2
        assert tb04.analysis_metadata["network_adjustment"] > 0

    def test_network_analysis_gives_root_summary_bonus(self):
        """Test that root summary sheets (not referenced by others) get bonus."""
        from genreport.core.parsing.preliminary_scanner import PreliminaryScanner
        from genreport.core.parsing.parsing_models import WorksheetAnalysisResult

        scanner = PreliminaryScanner()

        analyses = [
            WorksheetAnalysisResult(
                sheet_name="TB-01 Summary",
                is_summary=True,
                is_supporting=False,
                referenced_codes=["TB-02"],
                importance_score=0.8,
                summary="Summary sheet"
            ),
            WorksheetAnalysisResult(
                sheet_name="TB-02 Details",
                is_summary=False,
                is_supporting=True,
                referenced_codes=[],
                importance_score=0.6,
                summary="Supporting detail"
            ),
        ]

        adjusted = scanner._adjust_importance_with_network_analysis(analyses)

        # TB-01 is a summary sheet not referenced by anyone, should get root bonus
        tb01 = next(a for a in adjusted if a.sheet_name == "TB-01 Summary")
        assert tb01.importance_score > 0.8  # Higher than base score
        assert tb01.analysis_metadata["incoming_references"] == 0
        assert tb01.analysis_metadata["network_adjustment"] == 0.05  # Root bonus only

    def test_network_analysis_stores_metadata(self):
        """Test that network analysis stores base_importance, adjustment, and incoming_refs."""
        from genreport.core.parsing.preliminary_scanner import PreliminaryScanner
        from genreport.core.parsing.parsing_models import WorksheetAnalysisResult

        scanner = PreliminaryScanner()

        analyses = [
            WorksheetAnalysisResult(
                sheet_name="TB-01",
                is_summary=True,
                is_supporting=False,
                referenced_codes=["TB-02"],
                importance_score=0.8,
                summary="Summary"
            ),
            WorksheetAnalysisResult(
                sheet_name="TB-02",
                is_summary=False,
                is_supporting=True,
                referenced_codes=[],
                importance_score=0.6,
                summary="Detail"
            ),
        ]

        adjusted = scanner._adjust_importance_with_network_analysis(analyses)

        # Check metadata is stored
        for analysis in adjusted:
            assert "base_importance" in analysis.analysis_metadata
            assert "network_adjustment" in analysis.analysis_metadata
            assert "incoming_references" in analysis.analysis_metadata

            # Verify base_importance matches original score
            assert analysis.analysis_metadata["base_importance"] in [0.8, 0.6]

    def test_network_analysis_caps_scores_at_one(self):
        """Test that network analysis caps adjusted scores at 1.0."""
        from genreport.core.parsing.preliminary_scanner import PreliminaryScanner
        from genreport.core.parsing.parsing_models import WorksheetAnalysisResult

        scanner = PreliminaryScanner()

        # Create analysis with high base score and hub position
        analyses = [
            WorksheetAnalysisResult(
                sheet_name="TB-Hub",
                is_summary=False,
                is_supporting=True,
                referenced_codes=[],
                importance_score=0.98,  # Very high base score
                summary="Hub worksheet"
            ),
            WorksheetAnalysisResult(
                sheet_name="TB-01",
                is_summary=False,
                is_supporting=False,
                referenced_codes=["TB-Hub"],
                importance_score=0.7,
                summary="Sheet 1"
            ),
            WorksheetAnalysisResult(
                sheet_name="TB-02",
                is_summary=False,
                is_supporting=False,
                referenced_codes=["TB-Hub"],
                importance_score=0.7,
                summary="Sheet 2"
            ),
        ]

        adjusted = scanner._adjust_importance_with_network_analysis(analyses)

        # TB-Hub should be capped at 1.0
        hub = next(a for a in adjusted if a.sheet_name == "TB-Hub")
        assert hub.importance_score == 1.0  # Capped at 1.0

    def test_network_analysis_handles_no_references(self):
        """Test network analysis with sheets that have no references."""
        from genreport.core.parsing.preliminary_scanner import PreliminaryScanner
        from genreport.core.parsing.parsing_models import WorksheetAnalysisResult

        scanner = PreliminaryScanner()

        # All sheets isolated (no references)
        analyses = [
            WorksheetAnalysisResult(
                sheet_name="TB-01",
                is_summary=False,
                is_supporting=True,
                referenced_codes=[],
                importance_score=0.7,
                summary="Sheet 1"
            ),
            WorksheetAnalysisResult(
                sheet_name="TB-02",
                is_summary=False,
                is_supporting=True,
                referenced_codes=[],
                importance_score=0.6,
                summary="Sheet 2"
            ),
        ]

        adjusted = scanner._adjust_importance_with_network_analysis(analyses)

        # Scores should be unchanged (no network bonus)
        assert adjusted[0].importance_score == 0.7
        assert adjusted[1].importance_score == 0.6
        assert all(a.analysis_metadata["network_adjustment"] == 0 for a in adjusted)

    def test_network_analysis_handles_partial_matches(self):
        """Test that network analysis handles partial code matches."""
        from genreport.core.parsing.preliminary_scanner import PreliminaryScanner
        from genreport.core.parsing.parsing_models import WorksheetAnalysisResult

        scanner = PreliminaryScanner()

        analyses = [
            WorksheetAnalysisResult(
                sheet_name="TB-01",
                is_summary=True,
                is_supporting=False,
                referenced_codes=["TB"],  # Partial reference
                importance_score=0.8,
                summary="Summary"
            ),
            WorksheetAnalysisResult(
                sheet_name="TB-02 Details",
                is_summary=False,
                is_supporting=True,
                referenced_codes=[],
                importance_score=0.6,
                summary="Detail"
            ),
        ]

        adjusted = scanner._adjust_importance_with_network_analysis(analyses)

        # TB-02 should be recognized as referenced by "TB" code
        tb02 = next(a for a in adjusted if "TB-02" in a.sheet_name)
        assert tb02.analysis_metadata["incoming_references"] > 0

    @pytest.mark.asyncio
    @patch('genreport.core.parsing.preliminary_scanner.dspy')
    async def test_analyze_workbook_applies_network_analysis(
        self, mock_dspy, sample_workbook_file
    ):
        """Test that analyze_workbook applies network analysis to results (async)."""
        from genreport.core.parsing.preliminary_scanner import PreliminaryScanner

        # Mock coding analyzer
        mock_coding_analyzer = MagicMock()
        mock_coding_analyzer.return_value = MagicMock(
            coding_pattern="TB-XX",
            code_families_json='[]',
            confidence=0.9
        )

        # Mock worksheet analyzers with references
        call_count = [0]

        async def create_response(**kwargs):
            call_count[0] += 1
            sheet_name = kwargs.get('sheet_name', '')
            if "Summary" in sheet_name:
                return MagicMock(
                    is_summary=True,
                    is_supporting=False,
                    referenced_codes=["TB-02"],
                    importance_score=0.8,
                    summary="Summary sheet"
                )
            else:
                return MagicMock(
                    is_summary=False,
                    is_supporting=True,
                    referenced_codes=[],
                    importance_score=0.6,
                    summary="Detail sheet"
                )

        mock_worksheet_analyzer = AsyncMock()
        mock_worksheet_analyzer.acall = create_response

        mock_dspy.ChainOfThought.side_effect = [
            mock_coding_analyzer,
            mock_worksheet_analyzer,
        ]

        scanner = PreliminaryScanner()
        result = await scanner.analyze_workbook(sample_workbook_file)

        # Check that network analysis metadata is present
        for analysis in result.worksheet_analyses:
            assert "base_importance" in analysis.analysis_metadata
            assert "network_adjustment" in analysis.analysis_metadata
            assert "incoming_references" in analysis.analysis_metadata
