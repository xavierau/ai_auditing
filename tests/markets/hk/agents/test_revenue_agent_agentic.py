"""Integration tests for HKRevenueAgent with agentic RAG workflow."""

import pytest
from uuid import uuid4
from unittest.mock import Mock, MagicMock, patch

from markets.hk.agents.revenue_agent import HKRevenueAgent
from genreport.core.orchestration.agent_models import AgentInput, AgentOutput, Source
from genreport.core.orchestration.agentic_rag_agent import AgenticRAGResult, Reference


@pytest.fixture
def mock_market_config():
    """Mock HK market config."""
    config = Mock()
    config.accounting_standard = "HKFRS"
    config.jurisdiction = "HK"
    return config


@pytest.fixture
def mock_rag_orchestrator():
    """Mock RAG orchestrator."""
    orchestrator = Mock()
    orchestrator.retrieve = Mock()
    orchestrator.query_understanding = Mock()  # Make it detectable as RAGOrchestrator
    return orchestrator


@pytest.fixture
def agent(mock_market_config, mock_rag_orchestrator):
    """Create HK revenue agent with mocks."""
    tenant_id = uuid4()
    user_id = 1
    job_id = uuid4()

    return HKRevenueAgent(
        market_config=mock_market_config,
        retriever=mock_rag_orchestrator,
        tenant_id=tenant_id,
        user_id=user_id,
        job_id=job_id,
    )


@pytest.fixture
def agent_input():
    """Create agent input for testing."""
    return AgentInput(
        tenant_id=uuid4(),
        project_id=1,
        trial_balance={"revenue": 1000000, "accounts_receivable": 200000},
        accounting_policies={"revenue_recognition": "Point in time"},
        entity_info={"name": "Test Company HK"},
    )


class TestHKRevenueAgentAgentic:
    """Test HKRevenueAgent with agentic RAG workflow."""

    def test_initialization_with_job_id(
        self, mock_market_config, mock_rag_orchestrator
    ):
        """Test agent initialization with job_id."""
        tenant_id = uuid4()
        user_id = 1
        job_id = uuid4()

        agent = HKRevenueAgent(
            market_config=mock_market_config,
            retriever=mock_rag_orchestrator,
            tenant_id=tenant_id,
            user_id=user_id,
            job_id=job_id,
        )

        assert agent.job_id == job_id
        assert agent.agent_name == "revenue"
        assert "HK" in agent.supported_jurisdictions

    def test_get_disclosure_type_hkfrs(self, agent, mock_market_config):
        """Test _get_disclosure_type with HKFRS standard."""
        mock_market_config.accounting_standard = "HKFRS"

        disclosure_type = agent._get_disclosure_type("HKFRS")

        assert "HKFRS 15" in disclosure_type
        assert "Revenue from Contracts with Customers" in disclosure_type

    def test_get_disclosure_type_smefrs(self, agent):
        """Test _get_disclosure_type with SME-FRS standard."""
        disclosure_type = agent._get_disclosure_type("SME-FRS")

        assert "SME-FRS" in disclosure_type
        assert "Section 23" in disclosure_type

    @patch.object(HKRevenueAgent, "_fetch_template")
    @patch.object(HKRevenueAgent, "_fetch_requirements")
    @patch.object(HKRevenueAgent, "_fetch_context")
    @patch.object(HKRevenueAgent, "validate_tenant")
    def test_process_with_agentic_workflow(
        self,
        mock_validate_tenant,
        mock_fetch_context,
        mock_fetch_requirements,
        mock_fetch_template,
        agent,
        agent_input,
    ):
        """Test process method with complete agentic workflow."""
        # Update agent_input tenant_id to match agent
        agent_input.tenant_id = agent.tenant_id

        # Mock template result
        template_result = AgenticRAGResult(
            query="template query",
            answer="Template: Revenue should be disclosed showing...",
            references=[
                Reference(
                    ref_id=1,
                    source="HKFRS 15, Appendix A, p.120",
                    page_number=120,
                    relevance_score=0.95,
                    content_preview="Template for revenue disclosure",
                )
            ],
            total_chunks_retrieved=3,
            unique_chunks=2,
        )

        # Mock requirements result
        requirements_result = AgenticRAGResult(
            query="requirements query",
            answer="Requirements: 1. Disaggregation of revenue 2. Performance obligations...",
            references=[
                Reference(
                    ref_id=1,
                    source="HKFRS 15, Section 31, p.58",
                    page_number=58,
                    relevance_score=0.93,
                    content_preview="Mandatory disclosure requirements",
                ),
                Reference(
                    ref_id=2,
                    source="HKFRS 15, Section 32, p.60",
                    page_number=60,
                    relevance_score=0.91,
                    content_preview="Contract balances requirements",
                ),
            ],
            total_chunks_retrieved=5,
            unique_chunks=4,
        )

        # Mock context sources
        context_sources = [
            Source(
                document_id=1,
                chunk_id=10,
                relevance_score=0.88,
                snippet="Revenue recognition policy guidance",
                source_reference="HKFRS 15, Section 35",
            )
        ]

        # Setup mocks
        mock_validate_tenant.return_value = None
        mock_fetch_template.return_value = template_result
        mock_fetch_requirements.return_value = requirements_result
        mock_fetch_context.return_value = context_sources

        # Mock DSPy result
        mock_dspy_result = Mock()
        mock_dspy_result.disclosure = "Generated revenue disclosure..."
        mock_dspy_result.confidence = 0.85
        mock_dspy_result.completeness = 0.90
        mock_dspy_result.sources_used = "[1], [2]"

        agent.dspy_module = Mock(return_value=mock_dspy_result)

        # Execute
        output = agent.process(agent_input)

        # Verify template was fetched
        mock_fetch_template.assert_called_once()
        assert "HKFRS 15" in mock_fetch_template.call_args[0][0]

        # Verify requirements were fetched
        mock_fetch_requirements.assert_called_once()
        assert "HKFRS 15" in mock_fetch_requirements.call_args[0][0]

        # Verify context was fetched with agentic mode
        mock_fetch_context.assert_called_once()
        call_kwargs = mock_fetch_context.call_args[1]
        assert call_kwargs.get("use_agentic") is True

        # Verify DSPy was called with template and requirements
        assert agent.dspy_module.called
        dspy_call_kwargs = agent.dspy_module.call_args[1]
        assert "template" in dspy_call_kwargs
        assert "requirements" in dspy_call_kwargs
        assert "Template" in dspy_call_kwargs["template"]
        assert "Requirements" in dspy_call_kwargs["requirements"]

        # Verify output
        assert isinstance(output, AgentOutput)
        assert output.disclosure_text == "Generated revenue disclosure..."
        assert output.confidence_score == 0.85
        assert output.completeness_score == 0.90

        # Verify sources were combined (template + requirements + context)
        # Should have 3 unique sources (1 from template, 2 from requirements, 1 from context)
        assert len(output.sources) >= 3

    def test_combine_agentic_sources(self, agent):
        """Test _combine_agentic_sources method."""
        # Template result
        template_result = AgenticRAGResult(
            query="template",
            answer="Template text",
            references=[
                Reference(
                    ref_id=1,
                    source="HKFRS 15, Appendix A",
                    relevance_score=0.95,
                    content_preview="Template preview",
                )
            ],
            total_chunks_retrieved=1,
            unique_chunks=1,
        )

        # Requirements result
        requirements_result = AgenticRAGResult(
            query="requirements",
            answer="Requirements text",
            references=[
                Reference(
                    ref_id=1,
                    source="HKFRS 15, Section 31, p.58",
                    page_number=58,
                    relevance_score=0.93,
                    content_preview="Requirements preview",
                ),
                Reference(
                    ref_id=2,
                    source="HKFRS 15, Section 32, p.60",
                    page_number=60,
                    relevance_score=0.91,
                    content_preview="Contract balances",
                ),
            ],
            total_chunks_retrieved=2,
            unique_chunks=2,
        )

        # Context sources
        context_sources = [
            Source(
                document_id=1,
                chunk_id=10,
                relevance_score=0.88,
                snippet="Context snippet",
                source_reference="HKFRS 15, Section 35",
            )
        ]

        # Combine
        combined = agent._combine_agentic_sources(
            template_result, requirements_result, context_sources
        )

        # Verify combined sources
        assert len(combined) == 4  # 1 template + 2 requirements + 1 context
        assert all(isinstance(s, Source) for s in combined)

        # Verify source references are preserved
        source_refs = [s.source_reference for s in combined]
        assert "HKFRS 15, Appendix A" in source_refs
        assert "HKFRS 15, Section 31, p.58" in source_refs
        assert "HKFRS 15, Section 32, p.60" in source_refs
        assert "HKFRS 15, Section 35" in source_refs

    def test_combine_agentic_sources_deduplication(self, agent):
        """Test that duplicate sources are removed."""
        # Template and requirements with duplicate source
        template_result = AgenticRAGResult(
            query="template",
            answer="Template text",
            references=[
                Reference(
                    ref_id=1,
                    source="HKFRS 15, Section 31",
                    relevance_score=0.95,
                    content_preview="Template preview",
                )
            ],
            total_chunks_retrieved=1,
            unique_chunks=1,
        )

        requirements_result = AgenticRAGResult(
            query="requirements",
            answer="Requirements text",
            references=[
                Reference(
                    ref_id=1,
                    source="HKFRS 15, Section 31",  # Duplicate
                    relevance_score=0.93,
                    content_preview="Requirements preview",
                )
            ],
            total_chunks_retrieved=1,
            unique_chunks=1,
        )

        context_sources = []

        # Combine
        combined = agent._combine_agentic_sources(
            template_result, requirements_result, context_sources
        )

        # Verify deduplication
        assert len(combined) == 1  # Only one unique source
        assert combined[0].source_reference == "HKFRS 15, Section 31"
