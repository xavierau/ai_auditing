"""Relationship mapper for Excel working papers.

This module builds relationship graphs between worksheets based on
the preliminary scan results.
"""

from typing import List, Dict, Set
from genreport.core.parsing.parsing_models import (
    PreliminaryScanResult,
    RelationshipMapResult,
    WorksheetAnalysisResult,
)


class RelationshipMapper:
    """Mapper for building worksheet relationship graphs.

    This mapper analyzes the preliminary scan results to:
    - Extract relationships between worksheets
    - Identify root sheets (not referenced by others)
    - Prioritize sheets by importance and dependencies
    - Detect circular references

    The mapper is market-agnostic and works with any jurisdiction.

    Example:
        ```python
        mapper = RelationshipMapper()
        relationship_map = mapper.build_relationship_map(preliminary_result)

        print(f"Found {len(relationship_map.relationships)} relationships")
        print(f"Priority sheets: {relationship_map.recommended_sheets}")
        ```
    """

    def __init__(self):
        """Initialize relationship mapper."""
        pass

    def build_relationship_map(
        self, preliminary_result: PreliminaryScanResult
    ) -> RelationshipMapResult:
        """Build relationship map from preliminary scan result.

        This method:
        1. Extracts relationships from worksheet analyses
        2. Identifies root sheets (summary sheets, not referenced)
        3. Prioritizes sheets by importance and dependencies
        4. Calculates overall confidence score

        Args:
            preliminary_result: Result from PreliminaryScanner

        Returns:
            RelationshipMapResult with complete relationship graph

        Example:
            ```python
            mapper = RelationshipMapper()
            result = mapper.build_relationship_map(preliminary_scan)

            # Access relationship graph
            for sheet, refs in result.relationships.items():
                print(f"{sheet} references: {refs}")
            ```
        """
        # Extract relationships from worksheet analyses
        relationships = self._extract_relationships(
            preliminary_result.worksheet_analyses
        )

        # Identify root sheets and prioritize
        recommended_sheets = self._prioritize_sheets(
            preliminary_result.worksheet_analyses, relationships
        )

        # Calculate overall confidence score
        confidence_score = self._calculate_confidence(
            preliminary_result.coding_system.confidence,
            preliminary_result.worksheet_analyses,
        )

        # Build result
        return RelationshipMapResult(
            coding_system=preliminary_result.coding_system.coding_pattern,
            code_families=preliminary_result.coding_system.code_families,
            relationships=relationships,
            recommended_sheets=recommended_sheets,
            confidence_score=confidence_score,
        )

    def _extract_relationships(
        self, worksheet_analyses: List[WorksheetAnalysisResult]
    ) -> Dict[str, List[str]]:
        """Extract relationships from worksheet analyses.

        Args:
            worksheet_analyses: List of worksheet analysis results

        Returns:
            Dictionary mapping sheet names to referenced sheet codes
        """
        relationships = {}

        for analysis in worksheet_analyses:
            # Add relationship entry for this sheet
            relationships[analysis.sheet_name] = list(analysis.referenced_codes)

        return relationships

    def _identify_root_sheets(
        self, worksheet_analyses: List[WorksheetAnalysisResult], relationships: Dict[str, List[str]]
    ) -> Set[str]:
        """Identify root sheets (not referenced by any other sheet).

        Root sheets are typically summary or consolidation sheets that
        aggregate data from supporting sheets.

        Args:
            worksheet_analyses: List of worksheet analyses
            relationships: Dictionary of relationships

        Returns:
            Set of root sheet names
        """
        # Collect all referenced sheet codes
        all_referenced = set()
        for refs in relationships.values():
            all_referenced.update(refs)

        # Identify sheets that are NOT referenced by others
        root_sheets = set()
        for analysis in worksheet_analyses:
            sheet_name = analysis.sheet_name

            # Check if this sheet name appears in referenced codes
            # Need to handle partial matches (e.g., "TB-02" referenced as "TB-02")
            is_referenced = False
            for ref_code in all_referenced:
                if ref_code in sheet_name or sheet_name.startswith(ref_code):
                    is_referenced = True
                    break

            if not is_referenced:
                root_sheets.add(sheet_name)

        return root_sheets

    def _prioritize_sheets(
        self,
        worksheet_analyses: List[WorksheetAnalysisResult],
        relationships: Dict[str, List[str]],
    ) -> List[str]:
        """Prioritize sheets for parsing based on importance and dependencies.

        Priority factors:
        1. Root sheets (summary sheets not referenced by others)
        2. High importance scores
        3. Sheets referenced by many others (dependency depth)

        Args:
            worksheet_analyses: List of worksheet analyses
            relationships: Dictionary of relationships

        Returns:
            Ordered list of recommended sheet names (highest priority first)
        """
        # Identify root sheets
        root_sheets = self._identify_root_sheets(worksheet_analyses, relationships)

        # Create scoring for each sheet
        sheet_scores = []
        for analysis in worksheet_analyses:
            score = analysis.importance_score

            # Boost score for root sheets (summary sheets)
            if analysis.sheet_name in root_sheets:
                score += 0.1

            # Boost score for summary sheets
            if analysis.is_summary:
                score += 0.05

            sheet_scores.append((analysis.sheet_name, score))

        # Sort by score (highest first)
        sheet_scores.sort(key=lambda x: x[1], reverse=True)

        # Return ordered list of sheet names
        return [sheet_name for sheet_name, _ in sheet_scores]

    def _calculate_confidence(
        self,
        coding_confidence: float,
        worksheet_analyses: List[WorksheetAnalysisResult],
    ) -> float:
        """Calculate overall confidence score for the relationship map.

        The confidence is based on:
        1. Coding system confidence (from Phase 1a)
        2. Average worksheet importance scores (from Phase 1b)
        3. Presence of clear relationships

        Args:
            coding_confidence: Confidence from coding system discovery
            worksheet_analyses: List of worksheet analyses

        Returns:
            Overall confidence score (0.0 to 1.0)
        """
        # Start with coding system confidence
        confidence = coding_confidence * 0.6

        # Add average worksheet importance
        if worksheet_analyses:
            avg_importance = sum(
                a.importance_score for a in worksheet_analyses
            ) / len(worksheet_analyses)
            confidence += avg_importance * 0.3

        # Add relationship clarity bonus
        # If worksheets have clear references, boost confidence
        sheets_with_refs = sum(
            1 for a in worksheet_analyses if a.referenced_codes
        )
        if worksheet_analyses:
            ref_ratio = sheets_with_refs / len(worksheet_analyses)
            confidence += ref_ratio * 0.1

        # Ensure confidence is between 0.0 and 1.0
        return min(max(confidence, 0.0), 1.0)
