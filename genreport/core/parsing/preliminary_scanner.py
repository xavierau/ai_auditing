"""Preliminary scanner for Excel working papers using DSPy.

This module implements two-phase LLM parsing:
- Phase 1a: Discover coding system from worksheet names
- Phase 1b: Analyze each worksheet with coding context
"""

from typing import List, Dict, Any
from pathlib import Path
import dspy

from genreport.core.parsing.excel_converter import SecureExcelParser
from genreport.core.parsing.parsing_models import (
    CodingSystemResult,
    WorksheetAnalysisResult,
    PreliminaryScanResult,
)


class CodingSystemAnalyzer(dspy.Signature):
    """Phase 1a: Analyze worksheet names to discover coding system.

    This signature takes a list of worksheet names and identifies:
    - The coding pattern used (e.g., "TB-01", "A-100", hierarchical numbering)
    - Code families and their categories
    - Confidence in the discovered pattern
    """

    worksheet_names: List[str] = dspy.InputField(
        desc="List of all worksheet names from the Excel workbook"
    )

    coding_pattern: str = dspy.OutputField(
        desc="Description of the discovered coding pattern (e.g., 'TB-XX format', 'Hierarchical numbering')"
    )

    code_families: List[Dict[str, Any]] = dspy.OutputField(
        desc="Grouped code families with their characteristics (e.g., [{'prefix': 'TB', 'category': 'Trial Balance'}])"
    )

    confidence: float = dspy.OutputField(
        desc="Confidence score for the coding pattern discovery (0.0 to 1.0)"
    )


class WorksheetAnalyzer(dspy.Signature):
    """Phase 1b: Analyze individual worksheet with coding context.

    This signature analyzes a single worksheet name within the context
    of the discovered coding system to determine its role and importance.
    """

    sheet_name: str = dspy.InputField(desc="Name of the worksheet to analyze")

    worksheet_content: str = dspy.InputField(desc="Content of the worksheet as text")

    coding_pattern: str = dspy.InputField(
        desc="The discovered coding pattern from Phase 1a"
    )

    code_families: List[Dict[str, Any]] = dspy.InputField(
        desc="The discovered code families from Phase 1a"
    )

    is_summary: bool = dspy.OutputField(
        desc="Whether this worksheet is a summary/consolidation sheet. Usually it will contains both income statement and balance sheet data."
    )

    is_supporting: bool = dspy.OutputField(
        desc="Whether this worksheet contains supporting detail"
    )

    referenced_codes: List[str] = dspy.OutputField(
        desc="List of other worksheet codes that this sheet likely references"
    )

    importance_score: float = dspy.OutputField(
        desc="Importance score for this worksheet (0.0 to 1.0, where 1.0 is most important)"
    )

    summary = dspy.OutputField(
        desc="A brief summary of the worksheet's content and role within the coding system."
    )


class PreliminaryScanner:
    """Scanner for preliminary analysis of Excel working papers.

    This scanner performs two-phase LLM analysis
    1. Phase 1a: Discover the coding system from worksheet names (1 API call)
    2. Phase 1b: Analyze each worksheet with coding context (N API calls)

    The scanner is market-agnostic and works with any jurisdiction.

    Example:
        ```python
        scanner = PreliminaryScanner()
        result = scanner.analyze_workbook("workbook.xlsx")

        print(f"Discovered pattern: {result.coding_system.coding_pattern}")
        print(f"Recommended sheets: {result.recommended_sheets}")

        for analysis in result.worksheet_analyses:
            print(f"{analysis.sheet_name}: {analysis.importance_score}")
        ```
    """

    def __init__(self):
        """Initialize preliminary scanner with DSPy modules."""
        # Phase 1a: Coding system analyzer (1 API call per workbook)
        self.coding_analyzer = dspy.ChainOfThought(CodingSystemAnalyzer)

        # Phase 1b: Worksheet analyzer (N API calls per workbook)
        self.worksheet_analyzer = dspy.ChainOfThought(WorksheetAnalyzer)

        self.file_path = ""

        # Excel parser for reading sheet names
        self.excel_parser = SecureExcelParser()

    def _get_sheet_names(self, file_path: str) -> List[str]:
        """Get list of sheet names from Excel file.

        Args:
            file_path: Path to Excel file

        Returns:
            List of sheet names

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Excel file not found: {file_path}")

        self.file_path = file_path

        return self.excel_parser.get_sheet_names(file_path)

    def _discover_coding_system(
        self, sheet_names: List[str]
    ) -> CodingSystemResult:
        """Phase 1a: Discover coding system from worksheet names.

        This makes a single LLM call to analyze all worksheet names
        and identify the coding pattern.

        Args:
            sheet_names: List of all worksheet names

        Returns:
            CodingSystemResult with discovered pattern

        Cost: 1 API call per workbook
        """
        # Call DSPy ChainOfThought module
        response = self.coding_analyzer(worksheet_names=sheet_names)

        # Convert to CodingSystemResult
        return CodingSystemResult(
            coding_pattern=response.coding_pattern,
            code_families=response.code_families,
            confidence=float(response.confidence),
        )

    def _analyze_worksheet_with_context(
        self,
        sheet_name: str,
        coding_pattern: str,
        code_families: List[Dict[str, Any]]
    ) -> WorksheetAnalysisResult:
        """Phase 1b: Analyze single worksheet with coding context.

        This makes one LLM call per worksheet to analyze its role
        within the discovered coding system.

        Args:
            sheet_name: Name of worksheet to analyze
            coding_pattern: Discovered coding pattern from Phase 1a
            code_families: Discovered code families from Phase 1a

        Returns:
            WorksheetAnalysisResult with analysis

        Cost: 1 API call per worksheet
        """

        df = self.excel_parser.parse_single_sheet(
            file_path=self.file_path,
            sheet_name=sheet_name
        )
        df.dropna(how='all', inplace=True)
        df.fillna("",inplace=True)
        md = df.to_markdown()

        print(md)

        # Call DSPy ChainOfThought module with context
        response = self.worksheet_analyzer(
            sheet_name=sheet_name,
            worksheet_content=md,
            coding_pattern=coding_pattern,
            code_families=code_families
        )

        # Convert to WorksheetAnalysisResult
        return WorksheetAnalysisResult(
            sheet_name=sheet_name,
            is_summary=bool(response.is_summary),
            is_supporting=bool(response.is_supporting),
            summary=response.summary,
            referenced_codes=list(response.referenced_codes),
            importance_score=float(response.importance_score),
            analysis_metadata={
                "coding_pattern": coding_pattern,
                "code_families": code_families
            }
        )

    def _adjust_importance_with_network_analysis(
        self,
        worksheet_analyses: List[WorksheetAnalysisResult]
    ) -> List[WorksheetAnalysisResult]:
        """Adjust importance scores based on network centrality.

        This considers:
        1. Incoming references (how many sheets reference THIS sheet) - increases importance
        2. Root nodes (sheets not referenced by others) - increases importance for summaries
        3. Centrality (sheets that are hubs in the network) - increases importance

        Args:
            worksheet_analyses: List of worksheet analyses with initial scores

        Returns:
            List of worksheet analyses with network-adjusted importance scores
        """
        # Build reference graph: who references whom
        incoming_refs = {}  # sheet_name -> count of sheets that reference it
        sheet_names = {analysis.sheet_name for analysis in worksheet_analyses}

        for analysis in worksheet_analyses:
            # Initialize incoming reference count
            if analysis.sheet_name not in incoming_refs:
                incoming_refs[analysis.sheet_name] = 0

            # Count references to other sheets
            for ref_code in analysis.referenced_codes:
                # Find sheets that match this reference code
                matching_sheets = [
                    name for name in sheet_names
                    if ref_code in name or name.startswith(ref_code)
                ]
                for matched in matching_sheets:
                    incoming_refs[matched] = incoming_refs.get(matched, 0) + 1

        # Adjust importance scores based on network position
        adjusted_analyses = []
        max_incoming = max(incoming_refs.values()) if incoming_refs.values() else 1

        for analysis in worksheet_analyses:
            base_score = analysis.importance_score
            incoming_count = incoming_refs.get(analysis.sheet_name, 0)

            # Calculate network adjustment (0.0 to 0.15 bonus)
            if max_incoming > 0:
                # Hub bonus: sheets referenced by many others get higher score
                hub_bonus = (incoming_count / max_incoming) * 0.10

                # Root bonus: sheets not referenced by anyone (likely summary sheets)
                root_bonus = 0.05 if incoming_count == 0 and analysis.is_summary else 0.0

                network_adjustment = hub_bonus + root_bonus
            else:
                network_adjustment = 0.0

            # Apply adjustment (cap at 1.0)
            adjusted_score = min(base_score + network_adjustment, 1.0)

            # Create adjusted analysis (immutable, so create new instance)
            # Handle case where analysis_metadata might be None
            base_metadata = analysis.analysis_metadata or {}

            adjusted_analysis = WorksheetAnalysisResult(
                sheet_name=analysis.sheet_name,
                is_summary=analysis.is_summary,
                is_supporting=analysis.is_supporting,
                summary=analysis.summary,
                referenced_codes=analysis.referenced_codes,
                importance_score=adjusted_score,
                analysis_metadata={
                    **base_metadata,
                    "base_importance": base_score,
                    "network_adjustment": network_adjustment,
                    "incoming_references": incoming_count
                }
            )
            adjusted_analyses.append(adjusted_analysis)

        return adjusted_analyses

    def _select_important_sheets(
        self,
        worksheet_analyses: List[WorksheetAnalysisResult],
        top_n: int = 5,
        importance_threshold: float = 0.7
    ) -> List[str]:
        """Select most important sheets for detailed parsing.

        Args:
            worksheet_analyses: List of worksheet analyses
            top_n: Maximum number of sheets to recommend
            importance_threshold: Minimum importance score (0.0 to 1.0)

        Returns:
            List of recommended sheet names
        """
        # Filter by importance threshold
        important = [
            analysis for analysis in worksheet_analyses
            if analysis.importance_score >= importance_threshold
        ]

        # Sort by importance score (descending)
        important.sort(key=lambda x: x.importance_score, reverse=True)

        # Take top N
        recommended = important[:top_n]

        return [analysis.sheet_name for analysis in recommended]

    def analyze_workbook(self, file_path: str) -> PreliminaryScanResult:
        """Perform preliminary analysis of Excel workbook.

        This is the main entry point for three-phase analysis:
        1. Discovers coding system from all worksheet names (Phase 1a)
        2. Analyzes each worksheet with coding context (Phase 1b)
        3. Adjusts importance scores based on network centrality
        4. Recommends important sheets for detailed parsing

        Args:
            file_path: Path to Excel workbook

        Returns:
            PreliminaryScanResult with complete analysis

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is invalid or empty

        Cost:
            - 1 API call for coding system discovery
            - N API calls for worksheet analysis (where N = number of sheets)
            - Total: N + 1 API calls per workbook

        Example:
            ```python
            scanner = PreliminaryScanner()
            result = scanner.analyze_workbook("workbook.xlsx")

            print(f"Found {result.total_sheets} sheets")
            print(f"Pattern: {result.coding_system.coding_pattern}")
            print(f"Recommended: {result.recommended_sheets}")
            ```
        """
        # Validate file exists
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Excel file not found: {file_path}")

        # Get all sheet names
        sheet_names = self._get_sheet_names(file_path)

        if not sheet_names:
            raise ValueError(f"Workbook has no sheets: {file_path}")

        # Phase 1a: Discover coding system (1 API call)
        coding_system = self._discover_coding_system(sheet_names)

        # Phase 1b: Analyze each worksheet with context (N API calls)
        worksheet_analyses = []
        for sheet_name in sheet_names:
            analysis = self._analyze_worksheet_with_context(
                sheet_name=sheet_name,
                coding_pattern=coding_system.coding_pattern,
                code_families=coding_system.code_families
            )
            worksheet_analyses.append(analysis)

        # Adjust importance scores based on network centrality
        worksheet_analyses = self._adjust_importance_with_network_analysis(worksheet_analyses)

        # Select important sheets for recommendation
        recommended_sheets = self._select_important_sheets(worksheet_analyses)

        # Build complete result
        return PreliminaryScanResult(
            coding_system=coding_system,
            worksheet_analyses=worksheet_analyses,
            recommended_sheets=recommended_sheets,
            total_sheets=len(sheet_names)
        )
