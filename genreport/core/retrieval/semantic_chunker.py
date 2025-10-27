"""
Semantic chunking strategy optimized for accounting standard documents.

This module implements section-aware chunking that preserves document structure
and keeps semantic units (requirements, templates, examples) together.
"""

import re
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class DocumentSection:
    """Represents a logical section in the document."""

    section_number: Optional[str]  # e.g., "17.1", "Appendix 2"
    section_title: str  # e.g., "Property, Plant and Equipment"
    content: str
    page_num: int
    level: int  # Heading level (1-6)
    parent_section: Optional[str] = None


class SemanticChunker:
    """
    Chunks accounting standard documents while preserving semantic boundaries.

    Key principles:
    1. Keep complete sections together (don't split requirements mid-list)
    2. Preserve templates and examples as complete units
    3. Maintain hierarchical context (parent sections)
    4. Allow variable chunk sizes based on content type
    """

    def __init__(
        self,
        min_chunk_size: int = 300,
        max_chunk_size: int = 5000,
        target_chunk_size: int = 1500,
        overlap_size: int = 200,
    ):
        """
        Initialize semantic chunker.

        Args:
            min_chunk_size: Minimum chunk size (skip smaller fragments)
            max_chunk_size: Maximum chunk size (split if exceeded)
            target_chunk_size: Preferred chunk size
            overlap_size: Overlap between chunks in characters
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.target_chunk_size = target_chunk_size
        self.overlap_size = overlap_size

    def extract_sections(self, markdown: str, page_num: int = 1) -> List[DocumentSection]:
        """
        Extract logical sections from Markdown content.

        Args:
            markdown: Markdown text
            page_num: Page number for tracking

        Returns:
            List of DocumentSection objects
        """
        sections = []
        lines = markdown.split("\n")

        current_section = None
        current_content = []
        section_stack = []  # Track parent sections

        for line in lines:
            # Detect headings
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())

            if heading_match:
                # Save previous section
                if current_section:
                    current_section.content = "\n".join(current_content).strip()
                    if len(current_section.content) >= self.min_chunk_size:
                        sections.append(current_section)

                # Start new section
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip("*_")

                # Extract section number (e.g., "17.1" from "Section 17.1 Title")
                section_num_match = re.search(
                    r"Section\s+(\d+(?:\.\d+)?)|Appendix\s+(\d+)", title
                )
                section_number = None
                if section_num_match:
                    section_number = section_num_match.group(1) or section_num_match.group(2)

                # Update section stack (for parent tracking)
                while section_stack and section_stack[-1][0] >= level:
                    section_stack.pop()

                parent_section = section_stack[-1][1] if section_stack else None

                current_section = DocumentSection(
                    section_number=section_number,
                    section_title=title,
                    content="",
                    page_num=page_num,
                    level=level,
                    parent_section=parent_section,
                )

                section_stack.append((level, title))
                current_content = [line]
            else:
                # Accumulate content
                if line.strip():
                    current_content.append(line)

        # Save final section
        if current_section:
            current_section.content = "\n".join(current_content).strip()
            if len(current_section.content) >= self.min_chunk_size:
                sections.append(current_section)

        return sections

    def is_semantic_unit(self, text: str) -> Tuple[bool, str]:
        """
        Determine if text is a complete semantic unit that should not be split.

        Returns:
            (should_keep_intact, unit_type)
        """
        # Tables - keep intact
        if "|" in text and text.count("|") > 5:
            return (True, "table")

        # Lists with multiple items
        list_items = re.findall(r"^\s*[-*•]\s+.+$", text, re.MULTILINE)
        if len(list_items) >= 3:
            return (True, "list")

        # Numbered requirements
        numbered_items = re.findall(r"^\s*\(\w+\)\s+.+$", text, re.MULTILINE)
        if len(numbered_items) >= 2:
            return (True, "requirements")

        # Code blocks or formulas
        if "```" in text or text.count("$") >= 2:
            return (True, "code_or_formula")

        return (False, "general")

    def detect_content_type(self, section: DocumentSection) -> str:
        """
        Classify section content type.

        Returns:
            One of: "template", "requirement", "example", "definition", "general"
        """
        content_lower = section.content.lower()
        title_lower = section.section_title.lower()

        # Templates (usually in appendices)
        if "appendix" in title_lower and ("illustrative" in content_lower or "example" in title_lower):
            return "template"

        # Requirements (disclosure/recognition/measurement)
        if any(keyword in content_lower for keyword in ["shall disclose", "must", "required", "entity shall"]):
            return "requirement"

        # Examples
        if "example" in title_lower or "illustration" in title_lower:
            return "example"

        # Definitions
        if "definition" in title_lower or content_lower.startswith("for the purpose"):
            return "definition"

        return "general"

    def chunk_document(
        self,
        pages_markdown: Dict[int, str],
        source_file: str,
        jurisdiction: str,
        accounting_standard: str,
    ) -> List[Dict]:
        """
        Create semantic chunks from document.

        Args:
            pages_markdown: Dict of page_num -> Markdown text
            source_file: Source filename
            jurisdiction: Jurisdiction code
            accounting_standard: Accounting standard name

        Returns:
            List of chunk dicts with metadata
        """
        all_sections = []

        # Extract sections from all pages
        for page_num, markdown in sorted(pages_markdown.items()):
            if len(markdown.strip()) < self.min_chunk_size:
                continue

            sections = self.extract_sections(markdown, page_num)
            all_sections.extend(sections)

        # Convert sections to chunks
        chunks = []
        chunk_index = 0

        for section in all_sections:
            # Check if section should be kept intact
            should_keep_intact, unit_type = self.is_semantic_unit(section.content)

            # If section is small enough or is a semantic unit, create single chunk
            if len(section.content) <= self.max_chunk_size or should_keep_intact:
                chunk = self._create_chunk(
                    content=section.content,
                    chunk_index=chunk_index,
                    page_num=section.page_num,
                    section=section,
                    source_file=source_file,
                    jurisdiction=jurisdiction,
                    accounting_standard=accounting_standard,
                )
                chunks.append(chunk)
                chunk_index += 1

            else:
                # Section is too large - split intelligently
                sub_chunks = self._split_large_section(section, chunk_index)

                for sub_chunk_content in sub_chunks:
                    chunk = self._create_chunk(
                        content=sub_chunk_content,
                        chunk_index=chunk_index,
                        page_num=section.page_num,
                        section=section,
                        source_file=source_file,
                        jurisdiction=jurisdiction,
                        accounting_standard=accounting_standard,
                    )
                    chunks.append(chunk)
                    chunk_index += 1

        return chunks

    def _split_large_section(self, section: DocumentSection, start_index: int) -> List[str]:
        """
        Split large section into smaller chunks at paragraph boundaries.

        Args:
            section: DocumentSection to split
            start_index: Starting chunk index

        Returns:
            List of chunk contents
        """
        paragraphs = [p.strip() for p in section.content.split("\n\n") if p.strip()]
        chunks = []
        current_chunk = []
        current_size = 0

        for para in paragraphs:
            para_size = len(para)

            # If adding this para exceeds target, save current chunk
            if current_size + para_size > self.target_chunk_size and current_chunk:
                chunks.append("\n\n".join(current_chunk))

                # Start new chunk with overlap
                overlap_paras = current_chunk[-2:] if len(current_chunk) >= 2 else current_chunk
                current_chunk = overlap_paras + [para]
                current_size = sum(len(p) for p in current_chunk)
            else:
                current_chunk.append(para)
                current_size += para_size

        # Save final chunk
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks

    def _create_chunk(
        self,
        content: str,
        chunk_index: int,
        page_num: int,
        section: DocumentSection,
        source_file: str,
        jurisdiction: str,
        accounting_standard: str,
    ) -> Dict:
        """Create chunk dict with comprehensive metadata."""

        content_type = self.detect_content_type(section)

        return {
            # Core content
            "content": content.strip(),

            # Document structure
            "chunk_index": chunk_index,
            "page_num": page_num,
            "source_file": source_file,

            # Section context
            "section_number": section.section_number,
            "section_title": section.section_title,
            "parent_section": section.parent_section,
            "heading_level": section.level,

            # Market-specific
            "jurisdiction": jurisdiction,
            "accounting_standard": accounting_standard,

            # Content classification
            "content_type": content_type,

            # Content metrics
            "char_count": len(content),
            "has_table": "|" in content and content.count("|") > 5,
            "has_heading": content.lstrip().startswith("#"),
            "has_list": bool(re.search(r"^\s*[-*•]\s+", content, re.MULTILINE)),
            "has_numbered_items": bool(re.search(r"^\s*\(\w+\)\s+", content, re.MULTILINE)),

            # Retrieval optimization
            "chunk_hash": hashlib.md5(content.strip().encode()).hexdigest(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }


def compare_chunking_strategies(
    pages_markdown: Dict[int, str],
    source_file: str = "test.pdf",
    jurisdiction: str = "HK",
    accounting_standard: str = "SME-FRS",
) -> Dict:
    """
    Compare old (fixed-size) vs new (semantic) chunking strategies.

    Returns:
        Comparison statistics
    """
    from datetime import datetime, timezone
    import hashlib

    # Old strategy (from notebook)
    def old_chunking(pages_markdown, chunk_size=1000, overlap=200):
        chunks = []
        chunk_index = 0

        for page_num, markdown in sorted(pages_markdown.items()):
            if not markdown or len(markdown.strip()) < 50:
                continue

            paragraphs = [p.strip() for p in markdown.split("\n\n") if p.strip()]
            current_chunk = ""

            for para in paragraphs:
                if len(current_chunk) + len(para) > chunk_size and current_chunk:
                    chunks.append({
                        "content": current_chunk.strip(),
                        "chunk_index": chunk_index,
                        "char_count": len(current_chunk),
                    })
                    chunk_index += 1

                    recent_paras = current_chunk.split("\n\n")
                    if len(recent_paras) > 2:
                        current_chunk = "\n\n".join(recent_paras[-2:]) + "\n\n" + para
                    else:
                        current_chunk = para
                else:
                    current_chunk += ("\n\n" if current_chunk else "") + para

            if current_chunk.strip():
                chunks.append({
                    "content": current_chunk.strip(),
                    "chunk_index": chunk_index,
                    "char_count": len(current_chunk),
                })
                chunk_index += 1

        return chunks

    # Run both strategies
    old_chunks = old_chunking(pages_markdown)

    semantic_chunker = SemanticChunker()
    new_chunks = semantic_chunker.chunk_document(
        pages_markdown, source_file, jurisdiction, accounting_standard
    )

    # Compare
    return {
        "old_strategy": {
            "total_chunks": len(old_chunks),
            "avg_size": sum(c['char_count'] for c in old_chunks) / len(old_chunks) if old_chunks else 0,
            "min_size": min(c['char_count'] for c in old_chunks) if old_chunks else 0,
            "max_size": max(c['char_count'] for c in old_chunks) if old_chunks else 0,
            "has_section_context": False,
            "has_content_type": False,
        },
        "new_strategy": {
            "total_chunks": len(new_chunks),
            "avg_size": sum(c['char_count'] for c in new_chunks) / len(new_chunks) if new_chunks else 0,
            "min_size": min(c['char_count'] for c in new_chunks) if new_chunks else 0,
            "max_size": max(c['char_count'] for c in new_chunks) if new_chunks else 0,
            "has_section_context": True,
            "has_content_type": True,
            "chunks_with_section_num": sum(1 for c in new_chunks if c.get('section_number')),
            "content_types": {
                ctype: sum(1 for c in new_chunks if c.get('content_type') == ctype)
                for ctype in set(c.get('content_type', 'general') for c in new_chunks)
            },
        },
    }
