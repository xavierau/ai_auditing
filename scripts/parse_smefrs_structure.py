#!/usr/bin/env python3
"""
Parse SME-FRS PDF and extract document structure.

This script extracts the table of contents and section structure from the
SME-FRS 1221 PDF document to create a hierarchical navigation index.
"""

import sys
import PyPDF2
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def extract_toc_from_pdf(pdf_path: str) -> str:
    """
    Extract table of contents from PDF.

    The SME-FRS TOC typically appears in the first 10-15 pages.
    """
    toc_text = []

    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)

        print(f"📄 Total pages: {len(pdf_reader.pages)}")

        # Extract first 15 pages (usually contains TOC)
        for page_num in range(min(15, len(pdf_reader.pages))):
            page = pdf_reader.pages[page_num]
            text = page.extract_text()
            toc_text.append(f"\n--- Page {page_num + 1} ---\n{text}")

    return "\n".join(toc_text)


def parse_toc_structure(toc_text: str) -> list:
    """
    Parse TOC text to extract section numbers, titles, and page numbers.

    Looking for patterns like:
    - "Section 1  Presentation of Financial Statements  1.1"
    - "Section 17  Events After the End of the Reporting Period   17.1"
    - "Appendix 2 Illustrative Company-Level Financial Statements"
    """
    import re

    sections = []

    # Pattern 1: "Section <num>  <title>  <page>"
    # Example: "Section 1  Presentation of Financial Statements  1.1"
    # Note: Some sections have space in number (e.g., "Section 1 8" for 18)
    pattern1 = r"Section\s+(\d+\s?\d?)\s+([A-Za-z,\s\-\(\)]+?)\s+(\d+\.\d+)"

    # Pattern 2: "Appendix <num> <title>"
    # Example: "Appendix 2 Illustrative Company-Level Financial Statements"
    pattern2 = r"(Appendix\s+\d+)\s+([A-Za-z,\s\-\(\)]+)"

    for line in toc_text.split("\n"):
        line = line.strip()

        # Try Section pattern
        match = re.search(pattern1, line)
        if match:
            section_num = match.group(1).strip().replace(" ", "")  # Remove space from "1 8" -> "18"
            title = match.group(2).strip()
            page_ref = match.group(3).strip()

            sections.append({
                "section_number": section_num,
                "title": title,
                "page_ref": page_ref,
                "type": "section"
            })
            continue

        # Try Appendix pattern
        match = re.search(pattern2, line)
        if match:
            appendix_num = match.group(1).strip()
            title = match.group(2).strip()

            sections.append({
                "section_number": appendix_num,
                "title": title,
                "page_ref": "N/A",
                "type": "appendix"
            })
            continue

    return sections


def main():
    pdf_path = project_root / "genreport/markets/hk/knowledge_base/docs/smefrf1221.pdf"

    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return

    print(f"📖 Parsing: {pdf_path}")
    print("=" * 80)

    # Extract TOC
    print("\n1️⃣ Extracting table of contents...")
    toc_text = extract_toc_from_pdf(str(pdf_path))

    # Save raw TOC for inspection
    toc_output = project_root / "notebooks/smefrs_toc_raw.txt"
    with open(toc_output, 'w', encoding='utf-8') as f:
        f.write(toc_text)
    print(f"   ✅ Raw TOC saved to: {toc_output}")

    # Parse structure
    print("\n2️⃣ Parsing section structure...")
    sections = parse_toc_structure(toc_text)

    if not sections:
        print("   ⚠️ No sections found. Dumping raw TOC for manual review...")
        print("\n" + "=" * 80)
        print(toc_text[:2000])  # Print first 2000 chars
        print("=" * 80)
        return

    print(f"   ✅ Found {len(sections)} sections")

    # Display structure
    print("\n3️⃣ Document Structure:")
    print("=" * 80)
    for section in sections:
        page_info = f"Page {section['page_ref']}" if section['page_ref'] != "N/A" else "Appendix"
        print(f"   {section['section_number']:>15} | {section['title']:<55} | {page_info}")

    # Save structured data
    import json
    structure_output = project_root / "notebooks/smefrs_structure.json"
    with open(structure_output, 'w', encoding='utf-8') as f:
        json.dump(sections, f, indent=2)
    print(f"\n✅ Structure saved to: {structure_output}")


if __name__ == "__main__":
    main()
