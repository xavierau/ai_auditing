"""
SME-FRS Document Structure
Generated from SME-FRF & SME-FRS (March 2025) PDF

This file contains the hierarchical structure of the Hong Kong SME-FRS standard,
including section relationships, topics, and metadata for intelligent retrieval.
"""

from genreport.core.retrieval.document_structure_analyzer import (
    DocumentSection,
    SectionType,
)


# Complete SME-FRS document structure
SME_FRS_STRUCTURE = {
    "section_1": DocumentSection(
        section_id="section_1",
        section_number="1",
        title="Presentation of Financial Statements",
        section_type=SectionType.FRAMEWORK,
        parent_id=None,
        page_start=1,
        page_end=None,  # Inferred as next section start - 1
        topics=["presentation", "financial statements", "statement of financial position", "balance sheet", "income statement", "comprehensive income"],
        related_sections=["appendix_2", "appendix_3"],
        has_requirements=True,
        has_examples=False,
        has_templates=True,
    ),

    "section_2": DocumentSection(
        section_id="section_2",
        section_number="2",
        title="Accounting Policies, Changes in Accounting Estimates and Errors",
        section_type=SectionType.REQUIREMENT,
        parent_id=None,
        page_start=2,
        page_end=None,
        topics=["accounting policy", "policy change", "estimates", "errors", "prior period adjustments", "retrospective application"],
        related_sections=["appendix_2"],
        has_requirements=True,
        has_examples=True,
        has_templates=False,
    ),

    "section_3": DocumentSection(
        section_id="section_3",
        section_number="3",
        title="Property, Plant and Equipment",
        section_type=SectionType.REQUIREMENT,
        parent_id=None,
        page_start=3,
        page_end=None,
        topics=["property", "plant", "equipment", "ppe", "fixed assets", "depreciation", "revaluation", "cost model"],
        related_sections=["section_9", "appendix_2"],
        has_requirements=True,
        has_examples=True,
        has_templates=True,
    ),

    "section_4": DocumentSection(
        section_id="section_4",
        section_number="4",
        title="Intangible Assets (other than goodwill)",
        section_type=SectionType.REQUIREMENT,
        parent_id=None,
        page_start=4,
        page_end=None,
        topics=["intangible", "intangible assets", "amortization", "software", "licenses", "patents", "trademarks"],
        related_sections=["section_9", "section_18", "appendix_2"],
        has_requirements=True,
        has_examples=True,
        has_templates=False,
    ),

    "section_5": DocumentSection(
        section_id="section_5",
        section_number="5",
        title="Leases",
        section_type=SectionType.REQUIREMENT,
        parent_id=None,
        page_start=5,
        page_end=None,
        topics=["lease", "lessee", "lessor", "operating lease", "finance lease", "right-of-use", "rou"],
        related_sections=["section_3", "appendix_2"],
        has_requirements=True,
        has_examples=True,
        has_templates=True,
    ),

    "section_6": DocumentSection(
        section_id="section_6",
        section_number="6",
        title="Investments",
        section_type=SectionType.REQUIREMENT,
        parent_id=None,
        page_start=6,
        page_end=None,
        topics=["investments", "financial instruments", "fair value", "cost", "available-for-sale", "equity instruments"],
        related_sections=["section_20", "section_21", "appendix_2"],
        has_requirements=True,
        has_examples=True,
        has_templates=False,
    ),

    "section_7": DocumentSection(
        section_id="section_7",
        section_number="7",
        title="Inventories",
        section_type=SectionType.REQUIREMENT,
        parent_id=None,
        page_start=7,
        page_end=None,
        topics=["inventory", "inventories", "stock", "cost", "net realizable value", "nrv", "fifo", "weighted average"],
        related_sections=["section_9", "appendix_2"],
        has_requirements=True,
        has_examples=True,
        has_templates=True,
    ),

    "section_8": DocumentSection(
        section_id="section_8",
        section_number="8",
        title="Construction Contracts",
        section_type=SectionType.REQUIREMENT,
        parent_id=None,
        page_start=8,
        page_end=None,
        topics=["construction", "contracts", "percentage of completion", "contract revenue", "contract costs"],
        related_sections=["section_11", "appendix_2"],
        has_requirements=True,
        has_examples=True,
        has_templates=False,
    ),

    "section_9": DocumentSection(
        section_id="section_9",
        section_number="9",
        title="Impairment of Assets",
        section_type=SectionType.REQUIREMENT,
        parent_id=None,
        page_start=9,
        page_end=None,
        topics=["impairment", "recoverable amount", "value in use", "fair value less costs to sell", "impairment loss"],
        related_sections=["section_3", "section_4", "section_7", "appendix_1"],
        has_requirements=True,
        has_examples=True,
        has_templates=False,
    ),

    "section_10": DocumentSection(
        section_id="section_10",
        section_number="10",
        title="Provisions, Contingent Liabilities and Contingent Assets",
        section_type=SectionType.REQUIREMENT,
        parent_id=None,
        page_start=10,
        page_end=None,
        topics=["provisions", "contingent liabilities", "contingent assets", "probable", "possible", "warranty", "restructuring"],
        related_sections=["appendix_1", "appendix_2"],
        has_requirements=True,
        has_examples=True,
        has_templates=True,
    ),

    "section_11": DocumentSection(
        section_id="section_11",
        section_number="11",
        title="Revenue",
        section_type=SectionType.REQUIREMENT,
        parent_id=None,
        page_start=11,
        page_end=None,
        topics=["revenue", "revenue recognition", "sale of goods", "rendering of services", "interest", "dividends", "royalties"],
        related_sections=["section_8", "appendix_1", "appendix_2"],
        has_requirements=True,
        has_examples=True,
        has_templates=True,
    ),

    "section_12": DocumentSection(
        section_id="section_12",
        section_number="12",
        title="Government Grants and Other Government Assistance",
        section_type=SectionType.REQUIREMENT,
        parent_id=None,
        page_start=12,
        page_end=None,
        topics=["government grants", "government assistance", "deferred income", "subsidies"],
        related_sections=["appendix_2"],
        has_requirements=True,
        has_examples=True,
        has_templates=False,
    ),

    "section_13": DocumentSection(
        section_id="section_13",
        section_number="13",
        title="Borrowing Costs",
        section_type=SectionType.REQUIREMENT,
        parent_id=None,
        page_start=13,
        page_end=None,
        topics=["borrowing costs", "interest", "capitalization", "qualifying asset"],
        related_sections=["section_3", "appendix_2"],
        has_requirements=True,
        has_examples=True,
        has_templates=False,
    ),

    "section_14": DocumentSection(
        section_id="section_14",
        section_number="14",
        title="Income Taxes",
        section_type=SectionType.REQUIREMENT,
        parent_id=None,
        page_start=14,
        page_end=None,
        topics=["income tax", "tax", "deferred tax", "current tax", "temporary differences", "tax expense"],
        related_sections=["appendix_2"],
        has_requirements=True,
        has_examples=True,
        has_templates=True,
    ),

    "section_15": DocumentSection(
        section_id="section_15",
        section_number="15",
        title="The Effects of Changes in Foreign Exchange Rates",
        section_type=SectionType.REQUIREMENT,
        parent_id=None,
        page_start=15,
        page_end=None,
        topics=["foreign exchange", "foreign currency", "functional currency", "presentation currency", "translation", "exchange differences"],
        related_sections=["appendix_2"],
        has_requirements=True,
        has_examples=True,
        has_templates=False,
    ),

    "section_16": DocumentSection(
        section_id="section_16",
        section_number="16",
        title="Related Party Disclosures",
        section_type=SectionType.REQUIREMENT,
        parent_id=None,
        page_start=16,
        page_end=None,
        topics=["related party", "related party transactions", "key management personnel", "compensation", "directors"],
        related_sections=["appendix_2"],
        has_requirements=True,
        has_examples=True,
        has_templates=True,
    ),

    "section_17": DocumentSection(
        section_id="section_17",
        section_number="17",
        title="Events After the End of the Reporting Period",
        section_type=SectionType.REQUIREMENT,
        parent_id=None,
        page_start=17,
        page_end=None,
        topics=["events after reporting period", "subsequent events", "adjusting events", "non-adjusting events", "post balance sheet events"],
        related_sections=["appendix_2"],
        has_requirements=True,
        has_examples=True,
        has_templates=False,
    ),

    "section_18": DocumentSection(
        section_id="section_18",
        section_number="18",
        title="Business Combinations and Goodwill",
        section_type=SectionType.REQUIREMENT,
        parent_id=None,
        page_start=18,
        page_end=None,
        topics=["business combination", "goodwill", "acquisition", "merger", "purchase method", "fair value"],
        related_sections=["section_4", "section_9", "section_19", "appendix_2"],
        has_requirements=True,
        has_examples=True,
        has_templates=False,
    ),

    "section_19": DocumentSection(
        section_id="section_19",
        section_number="19",
        title="Consolidated and Company-level Financial Statements",
        section_type=SectionType.REQUIREMENT,
        parent_id=None,
        page_start=19,
        page_end=None,
        topics=["consolidation", "consolidated financial statements", "parent", "subsidiary", "control", "non-controlling interest"],
        related_sections=["section_18", "section_20", "section_21", "appendix_2", "appendix_3"],
        has_requirements=True,
        has_examples=True,
        has_templates=True,
    ),

    "section_20": DocumentSection(
        section_id="section_20",
        section_number="20",
        title="Investments in Associates",
        section_type=SectionType.REQUIREMENT,
        parent_id=None,
        page_start=20,
        page_end=None,
        topics=["associates", "equity method", "significant influence", "investments"],
        related_sections=["section_6", "section_19", "appendix_2"],
        has_requirements=True,
        has_examples=True,
        has_templates=False,
    ),

    "section_21": DocumentSection(
        section_id="section_21",
        section_number="21",
        title="Interests in Joint Ventures and Other Forms of Joint Arrangements",
        section_type=SectionType.REQUIREMENT,
        parent_id=None,
        page_start=21,
        page_end=None,
        topics=["joint ventures", "joint arrangements", "joint control", "equity method"],
        related_sections=["section_6", "section_19", "appendix_2"],
        has_requirements=True,
        has_examples=True,
        has_templates=False,
    ),

    "section_22": DocumentSection(
        section_id="section_22",
        section_number="22",
        title="Cash Flow Statement (optional)",
        section_type=SectionType.FRAMEWORK,
        parent_id=None,
        page_start=22,
        page_end=None,
        topics=["cash flow", "cash flow statement", "operating activities", "investing activities", "financing activities"],
        related_sections=["appendix_2", "appendix_3"],
        has_requirements=False,
        has_examples=True,
        has_templates=True,
    ),

    "appendix_1": DocumentSection(
        section_id="appendix_1",
        section_number="Appendix 1",
        title="Examples of Application",
        section_type=SectionType.EXAMPLE,
        parent_id=None,
        page_start=None,
        page_end=None,
        topics=[
            "provisions examples",
            "revenue recognition examples",
            "impairment allocation",
            "new co disclosure requirements"
        ],
        related_sections=[
            "section_9",   # Impairment
            "section_10",  # Provisions
            "section_11",  # Revenue
        ],
        has_requirements=False,
        has_examples=True,
        has_templates=False,
    ),

    "appendix_2": DocumentSection(
        section_id="appendix_2",
        section_number="Appendix 2",
        title="Illustrative Company-Level Financial Statements",
        section_type=SectionType.TEMPLATE,
        parent_id=None,
        page_start=None,
        page_end=None,
        topics=[
            "company-level financial statements",
            "illustrative statements",
            "disclosure templates",
            "accounting policy templates",
            "notes to financial statements"
        ],
        related_sections=[
            "section_1",   # Presentation
            "section_2",   # Accounting Policies
            "section_3",   # PPE
            "section_5",   # Leases
            "section_7",   # Inventories
            "section_10",  # Provisions
            "section_11",  # Revenue
            "section_14",  # Income Taxes
            "section_16",  # Related Parties
            "section_19",  # Consolidated statements
        ],
        has_requirements=False,
        has_examples=False,
        has_templates=True,
    ),

    "appendix_3": DocumentSection(
        section_id="appendix_3",
        section_number="Appendix 3",
        title="Illustrative Consolidated Financial Statements",
        section_type=SectionType.TEMPLATE,
        parent_id=None,
        page_start=None,
        page_end=None,
        topics=[
            "consolidated financial statements",
            "illustrative consolidated statements",
            "group accounts",
            "consolidation templates"
        ],
        related_sections=[
            "section_1",   # Presentation
            "section_18",  # Business Combinations
            "section_19",  # Consolidated Statements
            "section_20",  # Associates
            "section_21",  # Joint Ventures
        ],
        has_requirements=False,
        has_examples=False,
        has_templates=True,
    ),
}


def get_section(section_id: str) -> DocumentSection:
    """
    Get a section by its ID.

    Args:
        section_id: Section identifier (e.g., "section_11", "appendix_2")

    Returns:
        DocumentSection object

    Raises:
        KeyError: If section not found
    """
    return SME_FRS_STRUCTURE[section_id]


def get_sections_by_topic(topic: str) -> list[DocumentSection]:
    """
    Find all sections related to a specific topic.

    Args:
        topic: Topic keyword (e.g., "revenue", "lease", "impairment")

    Returns:
        List of matching DocumentSection objects
    """
    topic_lower = topic.lower()
    matches = []

    for section in SME_FRS_STRUCTURE.values():
        if any(topic_lower in t.lower() for t in section.topics):
            matches.append(section)

    return matches


def get_sections_by_type(section_type: SectionType) -> list[DocumentSection]:
    """
    Get all sections of a specific type.

    Args:
        section_type: Type filter (FRAMEWORK, REQUIREMENT, EXAMPLE, TEMPLATE)

    Returns:
        List of matching DocumentSection objects
    """
    return [
        section
        for section in SME_FRS_STRUCTURE.values()
        if section.section_type == section_type
    ]


def get_navigation_path(query: str, intent: str = "general") -> list[str]:
    """
    Get recommended navigation path for a query.

    This mimics how a human would navigate the document:
    1. Find sections matching the query topic
    2. Based on intent, prioritize certain section types
    3. Include related sections

    Args:
        query: User query (e.g., "revenue recognition")
        intent: Query intent - "template", "requirement", "example", "general"

    Returns:
        List of section IDs in recommended reading order
    """
    query_lower = query.lower()
    primary_sections = []

    # Find matching sections
    for section_id, section in SME_FRS_STRUCTURE.items():
        if any(topic in query_lower for topic in section.topics):
            primary_sections.append(section_id)

    if not primary_sections:
        return []

    # Build navigation path based on intent
    navigation_path = []

    for section_id in primary_sections:
        section = SME_FRS_STRUCTURE[section_id]

        if intent == "template":
            # Prioritize templates (appendices) first
            for related_id in section.related_sections:
                related = SME_FRS_STRUCTURE.get(related_id)
                if related and related.section_type == SectionType.TEMPLATE:
                    navigation_path.append(related_id)

            # Then add the main section
            navigation_path.append(section_id)

        elif intent == "example":
            # Add main section first, then examples
            navigation_path.append(section_id)
            for related_id in section.related_sections:
                related = SME_FRS_STRUCTURE.get(related_id)
                if related and related.section_type == SectionType.EXAMPLE:
                    navigation_path.append(related_id)

        elif intent == "requirement":
            # Focus on requirement sections
            navigation_path.append(section_id)
            for related_id in section.related_sections:
                related = SME_FRS_STRUCTURE.get(related_id)
                if related and related.section_type == SectionType.REQUIREMENT:
                    navigation_path.append(related_id)

        else:  # general
            # Natural order: main section + all related
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


# Example usage for testing
if __name__ == "__main__":
    print("SME-FRS Document Structure")
    print("=" * 80)
    print(f"Total sections: {len(SME_FRS_STRUCTURE)}")
    print()

    # Test topic search
    print("Example: Find sections about 'revenue'")
    revenue_sections = get_sections_by_topic("revenue")
    for section in revenue_sections:
        print(f"  - {section.section_id}: {section.title}")
    print()

    # Test navigation path
    print("Example: Navigation path for 'revenue recognition' with template intent")
    path = get_navigation_path("revenue recognition", intent="template")
    print(f"  Recommended path: {' -> '.join(path)}")
    print()

    # Test section types
    print("Example: All template sections")
    templates = get_sections_by_type(SectionType.TEMPLATE)
    for section in templates:
        print(f"  - {section.section_id}: {section.title}")
