"""
Test suite for knowledge base retrieval using real accountant query patterns.

This module defines gold-standard test cases based on actual accountant workflows
to measure retrieval quality objectively.
"""

from dataclasses import dataclass
from typing import List, Literal
import pytest


@dataclass
class GoldStandardQuery:
    """A test query with expected results for measuring retrieval quality."""

    query: str
    intent: Literal["template", "requirement", "example", "reference", "general"]

    # Expected results
    expected_section: str  # e.g., "Section 17.1" or "Appendix 2"
    expected_content_type: str  # "requirement", "template", "example", "definition"

    # Quality criteria
    must_include_keywords: List[str]  # These MUST appear in top result
    must_not_fragment: bool  # True if answer should be complete (not split across chunks)
    min_similarity_score: float  # Minimum acceptable similarity

    # Human judgment
    description: str  # What accountant is trying to accomplish
    ideal_chunk_size: int  # How many chars the ideal answer should be


# Real-world accountant test queries
ACCOUNTANT_TEST_QUERIES = [

    # === SCENARIO 1: Looking for accounting policy templates ===
    GoldStandardQuery(
        query="revenue recognition accounting policy wording for SME-FRS",
        intent="template",
        expected_section="Appendix 2",
        expected_content_type="template",
        must_include_keywords=["revenue", "measured", "fair value", "consideration"],
        must_not_fragment=True,  # Template should be complete
        min_similarity_score=0.75,
        description="Accountant needs copy-paste ready policy text for financial statements",
        ideal_chunk_size=800,  # Full accounting policy
    ),

    GoldStandardQuery(
        query="depreciation accounting policy template",
        intent="template",
        expected_section="Appendix 2",
        expected_content_type="template",
        must_include_keywords=["depreciation", "straight-line", "useful life"],
        must_not_fragment=True,
        min_similarity_score=0.72,
        description="Need boilerplate depreciation policy text",
        ideal_chunk_size=600,
    ),

    # === SCENARIO 2: Disclosure requirements lookup ===
    GoldStandardQuery(
        query="what disclosures are required for property plant and equipment under SME-FRS",
        intent="requirement",
        expected_section="Section 17",
        expected_content_type="requirement",
        must_include_keywords=["disclose", "depreciation method", "useful life", "carrying amount"],
        must_not_fragment=True,  # All requirements should be together
        min_similarity_score=0.70,
        description="Creating disclosure checklist for fixed assets note",
        ideal_chunk_size=1500,  # Complete section with all requirements
    ),

    GoldStandardQuery(
        query="SME-FRS related party transaction disclosure requirements",
        intent="requirement",
        expected_section="Section 33",
        expected_content_type="requirement",
        must_include_keywords=["related party", "disclose", "nature", "transaction"],
        must_not_fragment=True,
        min_similarity_score=0.72,
        description="Responding to audit query about related parties",
        ideal_chunk_size=1200,
    ),

    GoldStandardQuery(
        query="inventory disclosure requirements SME-FRS",
        intent="requirement",
        expected_section="Section 13",
        expected_content_type="requirement",
        must_include_keywords=["inventory", "carrying amount", "cost formula"],
        must_not_fragment=True,
        min_similarity_score=0.70,
        description="Preparing inventory note disclosure",
        ideal_chunk_size=1000,
    ),

    # === SCENARIO 3: Looking for examples ===
    GoldStandardQuery(
        query="example of statement of changes in equity format",
        intent="example",
        expected_section="Appendix 2",
        expected_content_type="example",
        must_include_keywords=["share capital", "retained earnings"],
        must_not_fragment=True,  # Table should be complete
        min_similarity_score=0.68,
        description="Need illustrative table format",
        ideal_chunk_size=2000,  # Tables can be large
    ),

    # === SCENARIO 4: Checking exemptions/scope ===
    GoldStandardQuery(
        query="is segment reporting required under SME-FRS",
        intent="reference",
        expected_section="Section 1",
        expected_content_type="requirement",
        must_include_keywords=["SME-FRS", "scope"],
        must_not_fragment=False,  # Can be brief
        min_similarity_score=0.65,
        description="Defending why segment reporting not included",
        ideal_chunk_size=500,
    ),

    GoldStandardQuery(
        query="what is a qualifying entity under new companies ordinance",
        intent="reference",
        expected_section="SME-FRF",
        expected_content_type="definition",
        must_include_keywords=["qualifying", "entity", "size test"],
        must_not_fragment=True,  # Definition + criteria together
        min_similarity_score=0.70,
        description="Determining if client qualifies for SME-FRS",
        ideal_chunk_size=1000,
    ),

    # === SCENARIO 5: Technical accounting questions ===
    GoldStandardQuery(
        query="how to account for leases under SME-FRS",
        intent="general",
        expected_section="Section 20",
        expected_content_type="requirement",
        must_include_keywords=["lease", "lessee", "lessor"],
        must_not_fragment=True,
        min_similarity_score=0.68,
        description="Understanding lease accounting treatment",
        ideal_chunk_size=2000,  # Complex topic needs full section
    ),

    GoldStandardQuery(
        query="financial instruments basic approach SME-FRS",
        intent="general",
        expected_section="Section 11",
        expected_content_type="requirement",
        must_include_keywords=["financial instrument", "basic"],
        must_not_fragment=True,
        min_similarity_score=0.68,
        description="Choosing between basic/comprehensive approach",
        ideal_chunk_size=1500,
    ),
]


# Metrics for evaluation
@dataclass
class RetrievalMetrics:
    """Metrics to evaluate retrieval quality."""

    query: str

    # Relevance
    top1_similarity: float
    top1_has_all_keywords: bool
    top1_correct_section: bool

    # Completeness
    is_fragmented: bool  # True if answer split across multiple chunks
    total_relevant_chars: int  # Combined chars of all relevant chunks

    # Ranking quality
    mrr: float  # Mean Reciprocal Rank (1/rank of first correct result)
    ndcg_at_5: float  # Normalized Discounted Cumulative Gain

    # Overall
    passed: bool  # True if meets all quality criteria
    failure_reason: str = ""


def evaluate_retrieval(
    retriever,
    test_queries: List[GoldStandardQuery]
) -> List[RetrievalMetrics]:
    """
    Evaluate retrieval system against gold standard queries.

    Args:
        retriever: KBRetriever instance
        test_queries: List of gold standard test queries

    Returns:
        List of metrics for each query
    """
    results = []

    for test_query in test_queries:
        # Retrieve
        retrieved_chunks = retriever.retrieve(test_query.query, top_k=10)

        if not retrieved_chunks:
            results.append(RetrievalMetrics(
                query=test_query.query,
                top1_similarity=0.0,
                top1_has_all_keywords=False,
                top1_correct_section=False,
                is_fragmented=True,
                total_relevant_chars=0,
                mrr=0.0,
                ndcg_at_5=0.0,
                passed=False,
                failure_reason="No results returned"
            ))
            continue

        top_result = retrieved_chunks[0]

        # Check keyword coverage
        has_all_keywords = all(
            kw.lower() in top_result['content'].lower()
            for kw in test_query.must_include_keywords
        )

        # Check section correctness (need to add section metadata to chunks)
        # For now, use simple string matching
        correct_section = test_query.expected_section.lower() in str(top_result.get('chunk_metadata', '')).lower()

        # Check fragmentation
        # If top result is < 70% of ideal size, likely fragmented
        is_fragmented = (
            test_query.must_not_fragment and
            len(top_result['content']) < (test_query.ideal_chunk_size * 0.7)
        )

        # Calculate MRR (simplified - just checking if top result is correct)
        mrr = 1.0 if (has_all_keywords and top_result['similarity_score'] >= test_query.min_similarity_score) else 0.0

        # Pass/fail
        passed = (
            top_result['similarity_score'] >= test_query.min_similarity_score and
            has_all_keywords and
            not is_fragmented
        )

        failure_reasons = []
        if top_result['similarity_score'] < test_query.min_similarity_score:
            failure_reasons.append(f"Low similarity: {top_result['similarity_score']:.3f} < {test_query.min_similarity_score}")
        if not has_all_keywords:
            failure_reasons.append("Missing required keywords")
        if is_fragmented:
            failure_reasons.append(f"Fragmented: {len(top_result['content'])} chars < ideal {test_query.ideal_chunk_size}")

        results.append(RetrievalMetrics(
            query=test_query.query,
            top1_similarity=top_result['similarity_score'],
            top1_has_all_keywords=has_all_keywords,
            top1_correct_section=correct_section,
            is_fragmented=is_fragmented,
            total_relevant_chars=len(top_result['content']),
            mrr=mrr,
            ndcg_at_5=0.0,  # TODO: Implement NDCG
            passed=passed,
            failure_reason="; ".join(failure_reasons) if failure_reasons else ""
        ))

    return results


def print_evaluation_report(metrics: List[RetrievalMetrics]):
    """Print human-readable evaluation report."""

    print("\n" + "="*80)
    print("KNOWLEDGE BASE RETRIEVAL EVALUATION REPORT")
    print("="*80)

    total = len(metrics)
    passed = sum(1 for m in metrics if m.passed)

    print(f"\nOverall: {passed}/{total} queries passed ({passed/total*100:.1f}%)")
    print(f"Average MRR: {sum(m.mrr for m in metrics)/total:.3f}")
    print(f"Average top-1 similarity: {sum(m.top1_similarity for m in metrics)/total:.3f}")

    print("\n" + "-"*80)
    print("DETAILED RESULTS:")
    print("-"*80)

    for i, metric in enumerate(metrics, 1):
        status = "✅ PASS" if metric.passed else "❌ FAIL"
        print(f"\n{i}. {status}")
        print(f"   Query: {metric.query}")
        print(f"   Similarity: {metric.top1_similarity:.3f}")
        print(f"   Keywords: {'✓' if metric.top1_has_all_keywords else '✗'}")
        print(f"   Fragmented: {'✗ Yes' if metric.is_fragmented else '✓ No'}")
        print(f"   Content size: {metric.total_relevant_chars} chars")

        if not metric.passed:
            print(f"   Failure: {metric.failure_reason}")

    print("\n" + "="*80)

    # Categorize failures
    fragmentation_failures = sum(1 for m in metrics if m.is_fragmented)
    keyword_failures = sum(1 for m in metrics if not m.top1_has_all_keywords)
    similarity_failures = sum(1 for m in metrics if m.top1_similarity < 0.70)

    print("\nFAILURE ANALYSIS:")
    print(f"  Fragmentation issues: {fragmentation_failures}")
    print(f"  Missing keywords: {keyword_failures}")
    print(f"  Low similarity: {similarity_failures}")
    print("="*80 + "\n")
