"""
Document Structure Analyzer - Build "intelligence" about document organization.

This module creates a hierarchical understanding of document structure,
similar to how humans build mental maps from table of contents.
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import dspy


class SectionType(str, Enum):
    """Types of document sections."""
    FRAMEWORK = "framework"  # General principles
    REQUIREMENT = "requirement"  # Specific disclosure/recognition rules
    EXAMPLE = "example"  # Illustrative examples
    TEMPLATE = "template"  # Ready-to-use policy/disclosure templates
    DEFINITION = "definition"  # Definitions and terminology
    APPENDIX = "appendix"  # Supplementary material
    TOC = "table_of_contents"  # Navigation structure


@dataclass
class DocumentSection:
    """Represents a section in the document hierarchy."""

    section_id: str  # e.g., "section_23", "appendix_2"
    section_number: Optional[str]  # e.g., "23", "Appendix 2"
    title: str  # e.g., "Revenue"
    section_type: SectionType
    parent_id: Optional[str]  # Parent section ID
    page_start: int
    page_end: Optional[int]

    # Semantic metadata
    topics: List[str]  # ["revenue", "recognition", "disclosure"]
    related_sections: List[str]  # ["appendix_2", "section_11"]

    # Content hints
    has_requirements: bool = False
    has_examples: bool = False
    has_templates: bool = False

    # Hierarchy
    children: List['DocumentSection'] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []


class TOCEntry(dspy.Signature):
    """Extract table of contents entry with semantic understanding."""

    toc_line: str = dspy.InputField(desc="Line from table of contents")
    document_title: str = dspy.InputField(desc="Document title for context")

    section_number: str = dspy.OutputField(desc="Section number (e.g., '17', 'Appendix 2')")
    section_title: str = dspy.OutputField(desc="Section title")
    section_type: str = dspy.OutputField(desc="One of: framework, requirement, example, template, definition, appendix")
    main_topics: str = dspy.OutputField(desc="Comma-separated main topics covered (e.g., 'revenue, recognition')")
    page_number: str = dspy.OutputField(desc="Page number from TOC")


class SectionRelationshipAnalyzer(dspy.Signature):
    """Analyze relationships between sections (e.g., Section 23 -> Appendix 2)."""

    section_title: str = dspy.InputField(desc="Section title (e.g., 'Revenue')")
    section_type: str = dspy.InputField(desc="Section type")
    all_sections: str = dspy.InputField(desc="List of all sections in document")

    related_sections: str = dspy.OutputField(
        desc="Comma-separated section IDs that are related (e.g., 'appendix_2,section_11'). "
             "Include: templates for this topic, examples, cross-references"
    )
    reasoning: str = dspy.OutputField(desc="Why these sections are related")


class DocumentStructureAnalyzer:
    """
    Builds hierarchical "intelligence" about document structure.

    Similar to how humans build mental maps from TOC:
    1. Extract document structure
    2. Classify section types
    3. Identify relationships between sections
    4. Build navigation index
    """

    def __init__(self):
        self.toc_extractor = dspy.ChainOfThought(TOCEntry)
        self.relationship_analyzer = dspy.ChainOfThought(SectionRelationshipAnalyzer)

    def extract_toc_from_markdown(self, markdown: str) -> List[str]:
        """
        Extract table of contents lines from markdown.

        Looks for patterns like:
        - Section 17 | Property, Plant and Equipment | 45
        - Appendix 2 | Illustrative Financial Statements | 87
        """
        toc_lines = []

        # Pattern 1: Markdown table rows
        table_pattern = r"\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(\d+)\s*\|"
        for match in re.finditer(table_pattern, markdown):
            section_num = match.group(1).strip()
            section_title = match.group(2).strip()
            page_num = match.group(3).strip()

            if section_num and section_title:
                toc_lines.append(f"{section_num} | {section_title} | {page_num}")

        # Pattern 2: List format
        list_pattern = r"^\s*[-*]\s*(.+?)\s+\.+\s+(\d+)\s*$"
        for line in markdown.split("\n"):
            match = re.match(list_pattern, line)
            if match:
                toc_lines.append(f"{match.group(1)} | {match.group(2)}")

        return toc_lines

    def build_document_structure(
        self,
        toc_markdown: str,
        document_title: str = "Accounting Standard"
    ) -> Dict[str, DocumentSection]:
        """
        Build hierarchical document structure from table of contents.

        Returns:
            Dict of section_id -> DocumentSection
        """
        toc_lines = self.extract_toc_from_markdown(toc_markdown)

        if not toc_lines:
            return {}

        sections = {}

        for toc_line in toc_lines:
            try:
                # Use LLM to extract structured data
                result = self.toc_extractor(
                    toc_line=toc_line,
                    document_title=document_title
                )

                # Create section ID
                section_id = self._create_section_id(result.section_number)

                # Parse topics
                topics = [t.strip() for t in result.main_topics.split(",")]

                # Create section
                section = DocumentSection(
                    section_id=section_id,
                    section_number=result.section_number,
                    title=result.section_title,
                    section_type=SectionType(result.section_type),
                    parent_id=None,  # Will set in second pass
                    page_start=int(result.page_number) if result.page_number.isdigit() else 1,
                    page_end=None,  # Will infer from next section
                    topics=topics,
                    related_sections=[],
                )

                sections[section_id] = section

            except Exception as e:
                print(f"⚠️ Failed to parse TOC line: {toc_line} - {e}")
                continue

        # Second pass: identify relationships
        self._identify_relationships(sections)

        return sections

    def _create_section_id(self, section_number: str) -> str:
        """Create normalized section ID."""
        # "17" -> "section_17"
        # "Appendix 2" -> "appendix_2"
        normalized = section_number.lower().replace(" ", "_")

        if normalized.startswith("appendix"):
            return normalized
        else:
            return f"section_{normalized}"

    def _identify_relationships(self, sections: Dict[str, DocumentSection]):
        """
        Identify relationships between sections using LLM.

        E.g., Section 23 (Revenue) relates to:
        - Appendix 2 (has revenue policy template)
        - Section 11 (Financial Instruments - revenue from contracts)
        """
        all_sections_str = "\n".join([
            f"{s.section_id}: {s.title} ({s.section_type})"
            for s in sections.values()
        ])

        for section_id, section in sections.items():
            try:
                result = self.relationship_analyzer(
                    section_title=section.title,
                    section_type=section.section_type.value,
                    all_sections=all_sections_str
                )

                # Parse related section IDs
                related_ids = [
                    r.strip()
                    for r in result.related_sections.split(",")
                    if r.strip() in sections
                ]

                section.related_sections = related_ids

            except Exception as e:
                print(f"⚠️ Failed to analyze relationships for {section_id}: {e}")
                continue

    def get_navigation_path(
        self,
        sections: Dict[str, DocumentSection],
        query: str,
        query_intent: str = "general"
    ) -> List[str]:
        """
        Get navigation path for query (like human would).

        Args:
            sections: Document structure
            query: User query
            query_intent: "template", "requirement", "example", "general"

        Returns:
            List of section IDs to search, in priority order
        """
        # Strategy 1: Direct topic match
        query_lower = query.lower()
        primary_sections = []

        for section_id, section in sections.items():
            # Check if query matches section topics
            if any(topic in query_lower for topic in section.topics):
                primary_sections.append(section_id)

        # Strategy 2: Intent-based expansion
        navigation_path = []

        for section_id in primary_sections:
            section = sections[section_id]

            # If looking for template, prioritize appendices
            if query_intent == "template":
                # Add related appendices first
                for related_id in section.related_sections:
                    related = sections.get(related_id)
                    if related and related.section_type == SectionType.APPENDIX:
                        navigation_path.append(related_id)

                # Then add the main section
                navigation_path.append(section_id)

            # If looking for requirements, prioritize requirement sections
            elif query_intent == "requirement":
                navigation_path.append(section_id)

                # Add related requirement sections
                for related_id in section.related_sections:
                    related = sections.get(related_id)
                    if related and related.section_type == SectionType.REQUIREMENT:
                        navigation_path.append(related_id)

            # General: use natural order
            else:
                navigation_path.append(section_id)
                navigation_path.extend(section.related_sections)

        # Remove duplicates while preserving order
        seen = set()
        unique_path = []
        for section_id in navigation_path:
            if section_id not in seen:
                seen.add(section_id)
                unique_path.append(section_id)

        return unique_path

    def save_structure(self, sections: Dict[str, DocumentSection], output_path: str):
        """Save document structure to JSON for caching."""
        import json

        # Convert to serializable format
        structure_data = {
            section_id: {
                "section_number": section.section_number,
                "title": section.title,
                "section_type": section.section_type.value,
                "page_start": section.page_start,
                "page_end": section.page_end,
                "topics": section.topics,
                "related_sections": section.related_sections,
            }
            for section_id, section in sections.items()
        }

        with open(output_path, 'w') as f:
            json.dump(structure_data, f, indent=2)

    @staticmethod
    def load_structure(input_path: str) -> Dict[str, DocumentSection]:
        """Load document structure from JSON."""
        import json

        with open(input_path, 'r') as f:
            structure_data = json.load(f)

        sections = {}
        for section_id, data in structure_data.items():
            section = DocumentSection(
                section_id=section_id,
                section_number=data["section_number"],
                title=data["title"],
                section_type=SectionType(data["section_type"]),
                parent_id=None,
                page_start=data["page_start"],
                page_end=data.get("page_end"),
                topics=data["topics"],
                related_sections=data["related_sections"],
            )
            sections[section_id] = section

        return sections


def create_document_index(
    toc_markdown: str,
    document_title: str,
    output_path: Optional[str] = None
) -> Dict[str, DocumentSection]:
    """
    Convenience function to create document index from TOC.

    Usage:
        toc = read_toc_from_pdf()
        index = create_document_index(toc, "HK SME-FRS", "smefrs_index.json")
    """
    analyzer = DocumentStructureAnalyzer()
    sections = analyzer.build_document_structure(toc_markdown, document_title)

    if output_path:
        analyzer.save_structure(sections, output_path)
        print(f"✅ Document structure saved to {output_path}")

    return sections
