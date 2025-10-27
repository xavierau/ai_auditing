"""Unit tests for RAG data models.

Tests Pydantic validation, field constraints, and model serialization.
"""

import pytest
from uuid import uuid4

from genreport.core.orchestration.rag_models import (
    ContentType,
    ContextChunk,
    QueryIntent,
    RAGQuery,
    RAGResult,
    RetrievalCandidate,
    RetrievalStrategy,
    StrategyExplanation,
)


class TestQueryIntent:
    """Test QueryIntent enum."""

    def test_all_intents_defined(self):
        """Test that all expected intents are defined."""
        assert QueryIntent.TEMPLATE == "template"
        assert QueryIntent.REQUIREMENT == "requirement"
        assert QueryIntent.EXAMPLE == "example"
        assert QueryIntent.DEFINITION == "definition"
        assert QueryIntent.GENERAL == "general"


class TestRetrievalStrategy:
    """Test RetrievalStrategy enum."""

    def test_all_strategies_defined(self):
        """Test that all expected strategies are defined."""
        assert RetrievalStrategy.AUTO == "auto"
        assert RetrievalStrategy.SEMANTIC == "semantic"
        assert RetrievalStrategy.STRUCTURE_AWARE == "structure_aware"
        assert RetrievalStrategy.HYBRID == "hybrid"


class TestContentType:
    """Test ContentType enum."""

    def test_all_content_types_defined(self):
        """Test that all expected content types are defined."""
        assert ContentType.TEMPLATE == "template"
        assert ContentType.REQUIREMENT == "requirement"
        assert ContentType.EXAMPLE == "example"
        assert ContentType.DEFINITION == "definition"
        assert ContentType.GUIDANCE == "guidance"
        assert ContentType.DISCLOSURE == "disclosure"
        assert ContentType.MEASUREMENT == "measurement"


class TestRAGQuery:
    """Test RAGQuery input model."""

    def test_valid_query_creation(self):
        """Test creating a valid RAG query."""
        tenant_id = uuid4()
        query = RAGQuery(
            query_text="revenue recognition",
            top_k=5,
            tenant_id=tenant_id,
            user_id=1,
        )

        assert query.query_text == "revenue recognition"
        assert query.top_k == 5
        assert query.tenant_id == tenant_id
        assert query.user_id == 1
        assert query.intent is None  # Auto-detect
        assert query.filters is None
        assert query.project_id is None

    def test_query_with_explicit_intent(self):
        """Test query with explicit intent."""
        query = RAGQuery(
            query_text="revenue template",
            top_k=5,
            intent=QueryIntent.TEMPLATE,
            tenant_id=uuid4(),
            user_id=1,
        )

        assert query.intent == QueryIntent.TEMPLATE

    def test_query_with_filters(self):
        """Test query with filters."""
        query = RAGQuery(
            query_text="revenue",
            top_k=5,
            filters={"chunk_types": ["requirement", "template"]},
            tenant_id=uuid4(),
            user_id=1,
        )

        assert query.filters["chunk_types"] == ["requirement", "template"]

    def test_query_text_strip_whitespace(self):
        """Test that query text is stripped of whitespace."""
        query = RAGQuery(
            query_text="  revenue recognition  ",
            top_k=5,
            tenant_id=uuid4(),
            user_id=1,
        )

        assert query.query_text == "revenue recognition"

    def test_query_text_empty_fails(self):
        """Test that empty query text fails validation."""
        with pytest.raises(ValueError, match="query_text cannot be empty"):
            RAGQuery(
                query_text="   ",  # Only whitespace
                top_k=5,
                tenant_id=uuid4(),
                user_id=1,
            )

    def test_query_text_too_short_fails(self):
        """Test that query text < 3 chars fails validation."""
        with pytest.raises(ValueError):
            RAGQuery(
                query_text="ab",  # Too short
                top_k=5,
                tenant_id=uuid4(),
                user_id=1,
            )

    def test_query_text_too_long_fails(self):
        """Test that query text > 500 chars fails validation."""
        with pytest.raises(ValueError):
            RAGQuery(
                query_text="a" * 501,  # Too long
                top_k=5,
                tenant_id=uuid4(),
                user_id=1,
            )

    def test_top_k_validation(self):
        """Test top_k validation (1-20)."""
        # Valid: 1
        query = RAGQuery(
            query_text="test", top_k=1, tenant_id=uuid4(), user_id=1
        )
        assert query.top_k == 1

        # Valid: 20
        query = RAGQuery(
            query_text="test", top_k=20, tenant_id=uuid4(), user_id=1
        )
        assert query.top_k == 20

        # Invalid: 0
        with pytest.raises(ValueError):
            RAGQuery(
                query_text="test", top_k=0, tenant_id=uuid4(), user_id=1
            )

        # Invalid: 21
        with pytest.raises(ValueError):
            RAGQuery(
                query_text="test", top_k=21, tenant_id=uuid4(), user_id=1
            )


class TestRetrievalCandidate:
    """Test RetrievalCandidate intermediate model."""

    def test_valid_candidate_creation(self):
        """Test creating a valid retrieval candidate."""
        candidate = RetrievalCandidate(
            chunk_id=123,
            content="Revenue is recognized when...",
            similarity_score=0.85,
            relevance_score=0.90,
            chunk_type=ContentType.REQUIREMENT,
            section_number="18.1",
            section_title="Revenue Recognition",
            page_num=42,
            document_title="HKFRS 15",
            standard="HKFRS 15",
            jurisdiction="HK",
        )

        assert candidate.chunk_id == 123
        assert candidate.similarity_score == 0.85
        assert candidate.relevance_score == 0.90
        assert candidate.chunk_type == ContentType.REQUIREMENT
        assert candidate.is_merged is False
        assert candidate.merged_from is None

    def test_merged_candidate(self):
        """Test merged candidate properties."""
        candidate = RetrievalCandidate(
            chunk_id=123,
            content="Merged content...",
            similarity_score=0.85,
            relevance_score=0.90,
            chunk_type=ContentType.TEMPLATE,
            document_title="HKFRS 15",
            standard="HKFRS 15",
            jurisdiction="HK",
            is_merged=True,
            merged_from=[123, 124],
        )

        assert candidate.is_merged is True
        assert candidate.merged_from == [123, 124]

    def test_score_validation(self):
        """Test that scores are validated (0-1 range)."""
        # Valid: 0.0
        candidate = RetrievalCandidate(
            chunk_id=1,
            content="test",
            similarity_score=0.0,
            relevance_score=0.0,
            chunk_type=ContentType.GUIDANCE,
            document_title="Test",
            standard="TEST",
            jurisdiction="HK",
        )
        assert candidate.similarity_score == 0.0

        # Valid: 1.0
        candidate = RetrievalCandidate(
            chunk_id=1,
            content="test",
            similarity_score=1.0,
            relevance_score=1.0,
            chunk_type=ContentType.GUIDANCE,
            document_title="Test",
            standard="TEST",
            jurisdiction="HK",
        )
        assert candidate.similarity_score == 1.0

        # Invalid: >1.0
        with pytest.raises(ValueError):
            RetrievalCandidate(
                chunk_id=1,
                content="test",
                similarity_score=1.5,
                relevance_score=0.8,
                chunk_type=ContentType.GUIDANCE,
                document_title="Test",
                standard="TEST",
                jurisdiction="HK",
            )

        # Invalid: <0.0
        with pytest.raises(ValueError):
            RetrievalCandidate(
                chunk_id=1,
                content="test",
                similarity_score=-0.1,
                relevance_score=0.8,
                chunk_type=ContentType.GUIDANCE,
                document_title="Test",
                standard="TEST",
                jurisdiction="HK",
            )


class TestContextChunk:
    """Test ContextChunk output model."""

    def test_valid_context_chunk_creation(self):
        """Test creating a valid context chunk."""
        chunk = ContextChunk(
            content="Revenue is recognized when...",
            source_reference="HKFRS 15, Section 18.1, p.42",
            relevance_score=0.90,
            chunk_type=ContentType.REQUIREMENT,
            chunk_id=123,
            document_id=5,
        )

        assert chunk.content == "Revenue is recognized when..."
        assert chunk.source_reference == "HKFRS 15, Section 18.1, p.42"
        assert chunk.relevance_score == 0.90
        assert chunk.chunk_type == ContentType.REQUIREMENT
        assert chunk.section_context is None
        assert chunk.is_mandatory is None
        assert chunk.cross_references == []

    def test_context_chunk_with_metadata(self):
        """Test context chunk with full metadata."""
        chunk = ContextChunk(
            content="An entity shall disclose...",
            source_reference="HKFRS 15, Section 18.1, p.42",
            relevance_score=0.95,
            chunk_type=ContentType.REQUIREMENT,
            chunk_id=123,
            document_id=5,
            section_context="Revenue Recognition",
            is_mandatory=True,
            cross_references=["18.2", "18.3", "Appendix A"],
        )

        assert chunk.section_context == "Revenue Recognition"
        assert chunk.is_mandatory is True
        assert len(chunk.cross_references) == 3


class TestRAGResult:
    """Test RAGResult output model."""

    def test_valid_rag_result_creation(self):
        """Test creating a valid RAG result."""
        chunk1 = ContextChunk(
            content="Content 1",
            source_reference="HKFRS 15, p.1",
            relevance_score=0.9,
            chunk_type=ContentType.REQUIREMENT,
            chunk_id=1,
            document_id=1,
        )

        chunk2 = ContextChunk(
            content="Content 2",
            source_reference="HKFRS 15, p.2",
            relevance_score=0.8,
            chunk_type=ContentType.TEMPLATE,
            chunk_id=2,
            document_id=1,
        )

        result = RAGResult(
            chunks=[chunk1, chunk2],
            query_intent=QueryIntent.REQUIREMENT,
            strategy_used=RetrievalStrategy.SEMANTIC,
            total_candidates=10,
            cache_hit=False,
            retrieval_time_ms=250.5,
        )

        assert len(result.chunks) == 2
        assert result.query_intent == QueryIntent.REQUIREMENT
        assert result.strategy_used == RetrievalStrategy.SEMANTIC
        assert result.total_candidates == 10
        assert result.cache_hit is False
        assert result.retrieval_time_ms == 250.5
        assert result.metadata == {}

    def test_rag_result_with_metadata(self):
        """Test RAG result with metadata."""
        result = RAGResult(
            chunks=[],
            query_intent=QueryIntent.GENERAL,
            strategy_used=RetrievalStrategy.HYBRID,
            total_candidates=5,
            cache_hit=True,
            retrieval_time_ms=50.0,
            metadata={
                "query": "revenue",
                "sections_searched": ["18", "19"],
            },
        )

        assert result.cache_hit is True
        assert result.metadata["query"] == "revenue"
        assert result.metadata["sections_searched"] == ["18", "19"]


class TestStrategyExplanation:
    """Test StrategyExplanation model."""

    def test_valid_explanation_creation(self):
        """Test creating a valid strategy explanation."""
        explanation = StrategyExplanation(
            query="revenue recognition template",
            detected_intent=QueryIntent.TEMPLATE,
            selected_strategy=RetrievalStrategy.STRUCTURE_AWARE,
            rationale="Query seeks template wording | Structure-aware navigation prioritizes appendices",
        )

        assert explanation.query == "revenue recognition template"
        assert explanation.detected_intent == QueryIntent.TEMPLATE
        assert explanation.selected_strategy == RetrievalStrategy.STRUCTURE_AWARE
        assert "template wording" in explanation.rationale
        assert explanation.sections_searched == []
        assert explanation.filters_applied == {}
        assert explanation.alternative_strategies == []

    def test_explanation_with_full_data(self):
        """Test explanation with all optional fields."""
        explanation = StrategyExplanation(
            query="revenue",
            detected_intent=QueryIntent.GENERAL,
            selected_strategy=RetrievalStrategy.SEMANTIC,
            rationale="Short general query | Semantic search for speed",
            sections_searched=[
                {"section_id": "18", "section_title": "Revenue"}
            ],
            filters_applied={"chunk_types": ["requirement"]},
            alternative_strategies=[
                "STRUCTURE_AWARE: Document navigation",
                "HYBRID: Combined approach",
            ],
        )

        assert len(explanation.sections_searched) == 1
        assert explanation.filters_applied["chunk_types"] == ["requirement"]
        assert len(explanation.alternative_strategies) == 2
