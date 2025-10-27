"""Tests for BaseFinancialAgent agentic RAG integration."""

import pytest
from uuid import uuid4
from unittest.mock import Mock, MagicMock, patch

from genreport.core.orchestration.base_agent import BaseFinancialAgent
from genreport.core.orchestration.agent_models import AgentInput, AgentOutput, Source
from genreport.core.orchestration.agentic_rag_agent import AgenticRAGResult, Reference


class MockAgent(BaseFinancialAgent):
    """Mock agent for testing base class methods."""

    @property
    def agent_name(self) -> str:
        return "test_agent"

    @property
    def supported_jurisdictions(self):
        return ["HK"]

    def validate_input(self, agent_input: AgentInput) -> bool:
        return True

    def process(self, agent_input: AgentInput) -> AgentOutput:
        return AgentOutput(
            disclosure_text="Test",
            sources=[],
            confidence_score=0.8,
            completeness_score=0.8,
            warnings=[],
        )

    def post_process(self, output: AgentOutput) -> AgentOutput:
        return output


@pytest.fixture
def mock_rag_orchestrator():
    """Create mock RAG orchestrator."""
    orchestrator = Mock()
    orchestrator.retrieve = Mock()
    orchestrator.query_understanding = Mock()  # Make it detectable as RAGOrchestrator
    return orchestrator


@pytest.fixture
def agent(mock_rag_orchestrator):
    """Create test agent with RAG orchestrator."""
    market_config = Mock()
    tenant_id = uuid4()
    user_id = 1
    job_id = uuid4()

    return MockAgent(
        market_config=market_config,
        retriever=mock_rag_orchestrator,
        tenant_id=tenant_id,
        user_id=user_id,
        job_id=job_id,
    )


class TestAgenticRAGIntegration:
    """Test agentic RAG integration in BaseFinancialAgent."""

    def test_initialization_with_job_id(self, mock_rag_orchestrator):
        """Test agent initialization with job_id."""
        market_config = Mock()
        tenant_id = uuid4()
        user_id = 1
        job_id = uuid4()

        agent = MockAgent(
            market_config=market_config,
            retriever=mock_rag_orchestrator,
            tenant_id=tenant_id,
            user_id=user_id,
            job_id=job_id,
        )

        assert agent.job_id == job_id
        assert agent._agentic_cache == {}

    def test_create_agentic_rag(self, agent):
        """Test _create_agentic_rag method."""
        agentic_agent = agent._create_agentic_rag(max_iterations=2)

        from genreport.core.orchestration.agentic_rag_agent import AgenticRAGAgent

        assert isinstance(agentic_agent, AgenticRAGAgent)
        assert agentic_agent.tenant_id == agent.tenant_id
        assert agentic_agent.user_id == agent.user_id
        assert agentic_agent.max_iterations == 2

    def test_create_agentic_rag_with_non_orchestrator(self):
        """Test _create_agentic_rag fails with non-RAGOrchestrator retriever."""
        market_config = Mock()
        tenant_id = uuid4()
        user_id = 1
        retriever = Mock(spec=['some_other_method'])  # Spec without query_understanding

        agent = MockAgent(
            market_config=market_config,
            retriever=retriever,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        with pytest.raises(ValueError, match="AgenticRAGAgent requires RAGOrchestrator"):
            agent._create_agentic_rag()

    @patch("genreport.core.orchestration.agentic_rag_agent.AgenticRAGAgent")
    def test_fetch_with_agentic_rag(self, mock_agentic_class, agent):
        """Test _fetch_with_agentic_rag method."""
        # Mock AgenticRAGResult
        mock_result = AgenticRAGResult(
            query="test query",
            answer="Test answer with template",
            references=[
                Reference(
                    ref_id=1,
                    source="HKFRS 15, Section 31, p.58",
                    page_number=58,
                    relevance_score=0.92,
                    content_preview="Revenue recognition requirements",
                )
            ],
            total_chunks_retrieved=5,
            unique_chunks=3,
        )

        # Mock AgenticRAGAgent instance
        mock_instance = Mock()
        mock_instance.forward = Mock(return_value=mock_result)
        mock_agentic_class.return_value = mock_instance

        # Call method
        result = agent._fetch_with_agentic_rag(
            query="test query", query_type="template", max_iterations=3
        )

        # Verify result
        assert isinstance(result, AgenticRAGResult)
        assert result.answer == "Test answer with template"
        assert len(result.references) == 1
        assert result.references[0].page_number == 58

        # Verify AgenticRAGAgent was called correctly
        mock_agentic_class.assert_called_once_with(
            rag_orchestrator=agent.retriever,
            tenant_id=agent.tenant_id,
            user_id=agent.user_id,
            max_iterations=3,
        )

    @patch("genreport.core.orchestration.agentic_rag_agent.AgenticRAGAgent")
    def test_fetch_template(self, mock_agentic_class, agent):
        """Test _fetch_template method."""
        # Mock result
        mock_result = AgenticRAGResult(
            query="template query",
            answer="Template text with structure",
            references=[
                Reference(
                    ref_id=1,
                    source="HKFRS 15, Appendix A",
                    relevance_score=0.95,
                    content_preview="Template example",
                )
            ],
            total_chunks_retrieved=3,
            unique_chunks=2,
        )

        mock_instance = Mock()
        mock_instance.forward = Mock(return_value=mock_result)
        mock_agentic_class.return_value = mock_instance

        # Call method
        result = agent._fetch_template("HKFRS 15 revenue disclosure")

        # Verify
        assert isinstance(result, AgenticRAGResult)
        assert "Template" in result.answer
        assert len(result.references) > 0

    @patch("genreport.core.orchestration.agentic_rag_agent.AgenticRAGAgent")
    def test_fetch_requirements(self, mock_agentic_class, agent):
        """Test _fetch_requirements method."""
        # Mock result
        mock_result = AgenticRAGResult(
            query="requirements query",
            answer="Requirements: mandatory disclosures",
            references=[
                Reference(
                    ref_id=1,
                    source="HKFRS 15, Section 31, p.58",
                    page_number=58,
                    relevance_score=0.93,
                    content_preview="Mandatory disclosure requirements",
                )
            ],
            total_chunks_retrieved=4,
            unique_chunks=3,
        )

        mock_instance = Mock()
        mock_instance.forward = Mock(return_value=mock_result)
        mock_agentic_class.return_value = mock_instance

        # Call method
        result = agent._fetch_requirements("HKFRS 15 revenue recognition")

        # Verify
        assert isinstance(result, AgenticRAGResult)
        assert "Requirements" in result.answer
        assert result.references[0].page_number == 58

    @patch("genreport.core.orchestration.agentic_rag_agent.AgenticRAGAgent")
    def test_agentic_caching(self, mock_agentic_class, agent):
        """Test job-level caching for agentic queries."""
        # Mock result
        mock_result = AgenticRAGResult(
            query="test query",
            answer="Cached answer",
            references=[],
            total_chunks_retrieved=1,
            unique_chunks=1,
        )

        mock_instance = Mock()
        mock_instance.forward = Mock(return_value=mock_result)
        mock_agentic_class.return_value = mock_instance

        # First call - should create AgenticRAGAgent
        result1 = agent._fetch_with_agentic_rag("test query", "template")

        # Second call with same query - should use cache
        result2 = agent._fetch_with_agentic_rag("test query", "template")

        # Verify AgenticRAGAgent was only created once
        assert mock_agentic_class.call_count == 1

        # Verify results are the same (cached)
        assert result1 is result2

    def test_clear_agentic_cache(self, agent):
        """Test clearing agentic cache."""
        # Add something to cache
        agent._agentic_cache["test_key"] = "test_value"
        assert len(agent._agentic_cache) == 1

        # Clear cache
        agent.clear_agentic_cache()

        # Verify cache is empty
        assert len(agent._agentic_cache) == 0

    @patch("genreport.core.orchestration.agentic_rag_agent.AgenticRAGAgent")
    def test_fetch_context_with_agentic_mode(self, mock_agentic_class, agent):
        """Test _fetch_context with use_agentic=True."""
        # Mock result
        mock_result = AgenticRAGResult(
            query="context query",
            answer="Context text",
            references=[
                Reference(
                    ref_id=1,
                    source="HKFRS 15, Section 31",
                    relevance_score=0.90,
                    content_preview="Context snippet",
                )
            ],
            total_chunks_retrieved=2,
            unique_chunks=2,
        )

        mock_instance = Mock()
        mock_instance.forward = Mock(return_value=mock_result)
        mock_agentic_class.return_value = mock_instance

        # Call method with agentic mode
        sources = agent._fetch_context("test query", use_agentic=True)

        # Verify Source objects were created from references
        assert isinstance(sources, list)
        assert len(sources) > 0
        assert all(isinstance(s, Source) for s in sources)
        assert sources[0].source_reference == "HKFRS 15, Section 31"
