"""Tests for AgenticRAGAgent with DSPy ReAct."""

import pytest
from uuid import uuid4
from unittest.mock import Mock, MagicMock, patch

from genreport.core.orchestration.agentic_rag_agent import (
    AgenticRAGAgent,
    AgenticRAGResult,
    Reference,
)
from genreport.core.orchestration.rag_models import (
    RAGResult,
    ContextChunk,
    ContentType,
    QueryIntent,
)


@pytest.fixture
def mock_rag_orchestrator():
    """Mock RAG orchestrator for testing."""
    orchestrator = Mock()

    # Mock retrieve method
    def mock_retrieve(query):
        # Create mock chunks
        chunks = [
            ContextChunk(
                content="Revenue recognition under HKFRS 15...",
                source_reference="HKFRS 15, Section 31",
                relevance_score=0.92,
                chunk_type=ContentType.REQUIREMENT,
                chunk_id=1,
                document_id=1,
                section_context="Section 31",
                is_mandatory=True,
                cross_references=[],
            ),
            ContextChunk(
                content="Performance obligations for software...",
                source_reference="HKFRS 15, Section 31.5",
                relevance_score=0.89,
                chunk_type=ContentType.REQUIREMENT,
                chunk_id=2,
                document_id=1,
                section_context="Section 31.5",
                is_mandatory=True,
                cross_references=[],
            ),
        ]

        return RAGResult(
            chunks=chunks,
            query_text=query.query_text,
            query_intent=QueryIntent.REQUIREMENT,
            total_candidates=10,
            retrieval_time_ms=500.0,
            cache_hit=False,
            strategy_used="hybrid",
        )

    orchestrator.retrieve = mock_retrieve
    return orchestrator


@pytest.fixture
def agent(mock_rag_orchestrator):
    """Create test agent."""
    return AgenticRAGAgent(
        rag_orchestrator=mock_rag_orchestrator,
        tenant_id=uuid4(),
        user_id=1,
        max_iterations=2,
    )


class TestAgenticRAGAgent:
    """Test suite for AgenticRAGAgent."""

    def test_initialization(self, mock_rag_orchestrator):
        """Test agent initialization."""
        tenant_id = uuid4()
        user_id = 1

        agent = AgenticRAGAgent(
            rag_orchestrator=mock_rag_orchestrator,
            tenant_id=tenant_id,
            user_id=user_id,
            max_iterations=3,
        )

        assert agent.rag_orchestrator == mock_rag_orchestrator
        assert agent.tenant_id == tenant_id
        assert agent.user_id == user_id
        assert agent.max_iterations == 3
        assert len(agent._all_chunks) == 0

    def test_retrieve_knowledge_tool(self, agent):
        """Test _retrieve_knowledge tool function."""
        query = "HKFRS 15 revenue recognition"

        result = agent._retrieve_knowledge(query)

        # Should return formatted string
        assert isinstance(result, str)
        assert "HKFRS 15, Section 31" in result
        assert "Relevance: 0.92" in result
        assert "Revenue recognition" in result

        # Should track chunks
        assert len(agent._all_chunks) == 2

    def test_retrieve_knowledge_no_results(self, mock_rag_orchestrator):
        """Test _retrieve_knowledge when no results."""
        # Mock no results
        mock_rag_orchestrator.retrieve = Mock(
            return_value=RAGResult(
                chunks=[],
                query_text="test",
                query_intent=QueryIntent.REQUIREMENT,
                total_candidates=0,
                retrieval_time_ms=100.0,
                cache_hit=False,
                strategy_used="semantic",
            )
        )

        agent = AgenticRAGAgent(
            rag_orchestrator=mock_rag_orchestrator,
            tenant_id=uuid4(),
            user_id=1,
        )

        result = agent._retrieve_knowledge("test query")

        assert result == "No results found."

    def test_retrieve_by_section_tool(self, agent):
        """Test _retrieve_by_section tool function."""
        section = "Section 23"
        query = "revenue policy"

        result = agent._retrieve_by_section(section, query)

        # Should return formatted string
        assert isinstance(result, str)
        assert "HKFRS 15" in result

        # Should track chunks
        assert len(agent._all_chunks) > 0

    def test_retrieve_by_section_no_results(self, mock_rag_orchestrator):
        """Test _retrieve_by_section when no results."""
        # Mock no results
        mock_rag_orchestrator.retrieve = Mock(
            return_value=RAGResult(
                chunks=[],
                query_text="test",
                query_intent=QueryIntent.REQUIREMENT,
                total_candidates=0,
                retrieval_time_ms=100.0,
                cache_hit=False,
                strategy_used="structure_aware",
            )
        )

        agent = AgenticRAGAgent(
            rag_orchestrator=mock_rag_orchestrator,
            tenant_id=uuid4(),
            user_id=1,
        )

        result = agent._retrieve_by_section("Section 23", "test query")

        assert "No results found in section 'Section 23'" in result

    @patch("genreport.core.orchestration.agentic_rag_agent.dspy.ReAct")
    def test_forward_basic(self, mock_react_class, agent):
        """Test forward method with mocked DSPy ReAct."""
        # Mock ReAct result
        mock_react_result = MagicMock()
        mock_react_result.answer = "Revenue recognition follows HKFRS 15 [1]."
        mock_react_result.trajectory = []

        mock_react_instance = Mock()
        mock_react_instance.return_value = mock_react_result
        mock_react_class.return_value = mock_react_instance

        # Recreate agent with mocked ReAct
        agent.react_agent = mock_react_instance

        # Manually populate chunks for testing
        agent._all_chunks = [
            ContextChunk(
                content="Revenue recognition under HKFRS 15...",
                source_reference="HKFRS 15, Section 31",
                relevance_score=0.92,
                chunk_type=ContentType.REQUIREMENT,
                chunk_id=1,
                document_id=1,
                section_context="Section 31",
                is_mandatory=True,
                cross_references=[],
            ),
        ]

        result = agent.forward("What are HKFRS 15 requirements?")

        # Verify result structure
        assert isinstance(result, AgenticRAGResult)
        assert result.query == "What are HKFRS 15 requirements?"
        assert "HKFRS 15" in result.answer
        assert isinstance(result.references, list)
        assert result.total_chunks_retrieved >= 0
        assert result.unique_chunks >= 0

    def test_build_references(self, agent):
        """Test _build_references method."""
        chunks = [
            ContextChunk(
                content="Content 1",
                source_reference="HKFRS 15, Section 31, p.58",
                relevance_score=0.92,
                chunk_type=ContentType.REQUIREMENT,
                chunk_id=1,
                document_id=1,
                section_context="Section 31",
                is_mandatory=True,
                cross_references=[],
            ),
            ContextChunk(
                content="Content 2",
                source_reference="HKFRS 15, Section 32",
                relevance_score=0.85,
                chunk_type=ContentType.REQUIREMENT,
                chunk_id=2,
                document_id=1,
                section_context="Section 32",
                is_mandatory=True,
                cross_references=[],
            ),
        ]

        references = agent._build_references(chunks)

        # Should build 2 references numbered sequentially
        assert len(references) == 2
        assert references[0].ref_id == 1
        assert references[0].source == "HKFRS 15, Section 31, p.58"
        assert references[0].page_number == 58
        assert references[0].relevance_score == 0.92
        assert references[1].ref_id == 2
        assert references[1].source == "HKFRS 15, Section 32"
        assert references[1].page_number is None  # No page number in source

    def test_build_references_empty(self, agent):
        """Test _build_references with no chunks."""
        chunks = []

        references = agent._build_references(chunks)

        assert len(references) == 0

    def test_deduplicate_chunks(self, agent):
        """Test _deduplicate_chunks method."""
        chunks = [
            ContextChunk(
                content="Content 1",
                source_reference="Source 1",
                relevance_score=0.9,
                chunk_type=ContentType.REQUIREMENT,
                chunk_id=1,
                document_id=1,
                section_context="Section 1",
                is_mandatory=True,
                cross_references=[],
            ),
            ContextChunk(
                content="Content 1 duplicate",
                source_reference="Source 1",
                relevance_score=0.9,
                chunk_type=ContentType.REQUIREMENT,
                chunk_id=1,  # Same chunk_id
                document_id=1,
                section_context="Section 1",
                is_mandatory=True,
                cross_references=[],
            ),
            ContextChunk(
                content="Content 2",
                source_reference="Source 2",
                relevance_score=0.8,
                chunk_type=ContentType.REQUIREMENT,
                chunk_id=2,
                document_id=1,
                section_context="Section 2",
                is_mandatory=True,
                cross_references=[],
            ),
        ]

        unique = agent._deduplicate_chunks(chunks)

        # Should remove duplicate
        assert len(unique) == 2
        assert unique[0].chunk_id == 1
        assert unique[1].chunk_id == 2



class TestDataModels:
    """Test data models."""

    def test_reference_model(self):
        """Test Reference model validation."""
        ref = Reference(
            ref_id=1,
            source="HKFRS 15, Section 31, p.58",
            page_number=58,
            relevance_score=0.92,
            content_preview="Revenue recognition requirements...",
        )

        assert ref.ref_id == 1
        assert ref.source == "HKFRS 15, Section 31, p.58"
        assert ref.page_number == 58
        assert ref.relevance_score == 0.92
        assert ref.content_preview == "Revenue recognition requirements..."

    def test_reference_model_invalid_score(self):
        """Test Reference model with invalid relevance score."""
        with pytest.raises(ValueError):
            Reference(
                ref_id=1,
                source="Test",
                relevance_score=1.5,  # > 1.0
                content_preview="Test",
            )

    def test_agentic_rag_result_model(self):
        """Test AgenticRAGResult model validation."""
        result = AgenticRAGResult(
            query="Test query",
            answer="Test answer",
            references=[],
            total_chunks_retrieved=10,
            unique_chunks=8,
        )

        assert result.query == "Test query"
        assert result.answer == "Test answer"
        assert result.total_chunks_retrieved == 10
        assert result.unique_chunks == 8
