"""Integration tests for agent orchestration.

These tests verify the complete workflow from SecureOrchestrator
through agents to final output, testing all components together.
"""

import pytest
from uuid import uuid4
from unittest.mock import Mock, patch

from genreport.core.orchestration.secure_orchestrator import SecureOrchestrator
from genreport.core.orchestration.agent_models import AgentOutput


class TestSecureOrchestrationIntegration:
    """Integration tests for complete orchestration workflow."""

    @patch("markets.hk.agents.revenue_agent.dspy")
    @patch("genreport.core.orchestration.agent_factory.get_market_config")
    @patch("genreport.core.orchestration.agent_factory.SecureKBRetriever")
    def test_hk_revenue_agent_end_to_end(
        self, mock_retriever_class, mock_config, mock_dspy
    ):
        """Test complete HK revenue agent workflow."""
        # Setup mocks
        mock_config.return_value = Mock(
            jurisdiction="HK",
            accounting_standard="HKFRS",
        )

        mock_retriever = Mock()
        mock_retriever.retrieve.return_value = [
            {
                "document_id": uuid4(),
                "chunk_id": uuid4(),
                "score": 0.95,
                "text": "HKFRS 15 revenue recognition guidance",
            }
        ]
        mock_retriever_class.return_value = mock_retriever

        # Mock DSPy
        mock_cot = Mock()
        mock_cot.return_value = Mock(
            disclosure="Revenue is recognized at the point in time when control transfers.",
            confidence=0.92,
            completeness=0.88,
            sources_used="HKFRS 15",
        )
        mock_dspy.ChainOfThought = Mock(return_value=mock_cot)

        # Create orchestrator
        tenant_id = uuid4()
        orchestrator = SecureOrchestrator(
            jurisdiction="HK",
            tenant_id=tenant_id,
            user_id=123,
            db=Mock(),
        )

        # Execute agent
        output = orchestrator.run_agent(
            agent_type="revenue",
            project_id=1,
            trial_balance={"revenue": 1000000, "tenant_id": tenant_id},
            accounting_policies={"revenue_recognition": "point_in_time"},
        )

        # Verify output
        assert isinstance(output, AgentOutput)
        assert len(output.disclosure_text) > 0
        assert output.confidence_score > 0.0
        assert output.completeness_score > 0.0
        assert len(output.sources) > 0

        # Verify retriever was called
        mock_retriever.retrieve.assert_called()

        # Verify DSPy was invoked
        mock_cot.assert_called_once()

    @patch("markets.hk.agents.inventory_agent.dspy")
    @patch("markets.hk.agents.revenue_agent.dspy")
    @patch("markets.hk.agents.provisions_agent.dspy")
    @patch("genreport.core.orchestration.agent_factory.get_market_config")
    @patch("genreport.core.orchestration.agent_factory.SecureKBRetriever")
    def test_run_all_hk_agents_integration(
        self,
        mock_retriever_class,
        mock_config,
        mock_provisions_dspy,
        mock_revenue_dspy,
        mock_inventory_dspy,
    ):
        """Test running all HK agents together."""
        # Setup common mocks
        mock_config.return_value = Mock(
            jurisdiction="HK",
            accounting_standard="HKFRS",
        )

        mock_retriever = Mock()
        mock_retriever.retrieve.return_value = [
            {
                "document_id": uuid4(),
                "chunk_id": uuid4(),
                "score": 0.9,
                "text": "HKFRS guidance",
            }
        ]
        mock_retriever_class.return_value = mock_retriever

        # Mock DSPy for each agent
        for mock_dspy in [mock_revenue_dspy, mock_inventory_dspy, mock_provisions_dspy]:
            mock_cot = Mock()
            mock_cot.return_value = Mock(
                disclosure="Disclosure text",
                confidence=0.85,
                completeness=0.80,
                sources_used="HKFRS",
            )
            mock_dspy.ChainOfThought = Mock(return_value=mock_cot)

        # Create orchestrator
        tenant_id = uuid4()
        orchestrator = SecureOrchestrator(
            jurisdiction="HK",
            tenant_id=tenant_id,
            user_id=123,
            db=Mock(),
        )

        # Run all agents
        outputs = orchestrator.run_all_agents(
            project_id=1,
            trial_balance={
                "revenue": 1000000,
                "inventory": 500000,
                "provisions": 100000,
                "tenant_id": tenant_id,
            },
        )

        # Verify all agents ran
        assert len(outputs) == 3
        assert "revenue" in outputs
        assert "inventory" in outputs
        assert "provisions" in outputs

        # Verify all outputs valid
        for agent_type, output in outputs.items():
            assert isinstance(output, AgentOutput)
            assert len(output.disclosure_text) > 0
            assert output.confidence_score > 0.0
            assert output.completeness_score > 0.0

    @patch("markets.hk.agents.revenue_agent.dspy")
    @patch("genreport.core.orchestration.agent_factory.get_market_config")
    @patch("genreport.core.orchestration.agent_factory.SecureKBRetriever")
    def test_context_validation_in_workflow(
        self, mock_retriever_class, mock_config, mock_dspy
    ):
        """Test that context validation catches cross-tenant data."""
        # Setup mocks
        mock_config.return_value = Mock(
            jurisdiction="HK",
            accounting_standard="HKFRS",
        )
        mock_retriever_class.return_value = Mock(retrieve=Mock(return_value=[]))

        # Create orchestrator
        tenant_id = uuid4()
        orchestrator = SecureOrchestrator(
            jurisdiction="HK",
            tenant_id=tenant_id,
            user_id=123,
            db=Mock(),
        )

        # Try to run agent with wrong tenant data
        from genreport.core.security.context_validator import CrossTenantDataError

        with pytest.raises(CrossTenantDataError):
            orchestrator.run_agent(
                agent_type="revenue",
                project_id=1,
                trial_balance={
                    "revenue": 1000000,
                    "tenant_id": uuid4(),  # WRONG TENANT
                },
            )

    @patch("markets.hk.agents.revenue_agent.dspy")
    @patch("genreport.core.orchestration.agent_factory.get_market_config")
    @patch("genreport.core.orchestration.agent_factory.SecureKBRetriever")
    def test_pii_detection_in_workflow(
        self, mock_retriever_class, mock_config, mock_dspy
    ):
        """Test that PII detection adds warnings to output."""
        # Setup mocks
        mock_config.return_value = Mock(
            jurisdiction="HK",
            accounting_standard="HKFRS",
        )

        mock_retriever = Mock()
        mock_retriever.retrieve.return_value = [
            {
                "document_id": uuid4(),
                "chunk_id": uuid4(),
                "score": 0.9,
                "text": "HKFRS 15 guidance",
            }
        ]
        mock_retriever_class.return_value = mock_retriever

        # Mock DSPy to return disclosure WITH PII
        mock_cot = Mock()
        mock_cot.return_value = Mock(
            disclosure="Contact john.doe@example.com for questions.",  # EMAIL PII
            confidence=0.85,
            completeness=0.80,
            sources_used="HKFRS 15",
        )
        mock_dspy.ChainOfThought = Mock(return_value=mock_cot)

        # Create orchestrator
        tenant_id = uuid4()
        orchestrator = SecureOrchestrator(
            jurisdiction="HK",
            tenant_id=tenant_id,
            user_id=123,
            db=Mock(),
        )

        # Execute agent
        output = orchestrator.run_agent(
            agent_type="revenue",
            project_id=1,
            trial_balance={"revenue": 1000000, "tenant_id": tenant_id},
        )

        # Verify PII warning added
        assert len(output.warnings) > 0
        assert any("PII" in w or "email" in w for w in output.warnings)

    @patch("markets.hk.agents.revenue_agent.dspy")
    @patch("genreport.core.orchestration.agent_factory.get_market_config")
    @patch("genreport.core.orchestration.agent_factory.SecureKBRetriever")
    def test_low_confidence_warning_in_workflow(
        self, mock_retriever_class, mock_config, mock_dspy
    ):
        """Test that low confidence scores add warnings."""
        # Setup mocks
        mock_config.return_value = Mock(
            jurisdiction="HK",
            accounting_standard="HKFRS",
        )

        mock_retriever = Mock()
        mock_retriever.retrieve.return_value = []
        mock_retriever_class.return_value = mock_retriever

        # Mock DSPy to return LOW confidence
        mock_cot = Mock()
        mock_cot.return_value = Mock(
            disclosure="Revenue disclosure with low confidence.",
            confidence=0.5,  # LOW
            completeness=0.6,  # LOW
            sources_used="",
        )
        mock_dspy.ChainOfThought = Mock(return_value=mock_cot)

        # Create orchestrator
        tenant_id = uuid4()
        orchestrator = SecureOrchestrator(
            jurisdiction="HK",
            tenant_id=tenant_id,
            user_id=123,
            db=Mock(),
        )

        # Execute agent
        output = orchestrator.run_agent(
            agent_type="revenue",
            project_id=1,
            trial_balance={"revenue": 1000000, "tenant_id": tenant_id},
        )

        # Verify warnings added for low scores
        assert len(output.warnings) > 0
        assert any("confidence" in w.lower() for w in output.warnings)
        assert any("incomplete" in w.lower() or "missing" in w.lower() for w in output.warnings)


class TestAgentFactoryIntegration:
    """Test agent factory creation and lifecycle."""

    @patch("genreport.core.orchestration.agent_factory.get_market_config")
    @patch("genreport.core.orchestration.agent_factory.SecureKBRetriever")
    def test_factory_creates_all_hk_agents(
        self, mock_retriever_class, mock_config
    ):
        """Test that factory creates all HK agents correctly."""
        from genreport.core.orchestration.agent_factory import AgentFactory

        mock_config.return_value = Mock(
            jurisdiction="HK",
            accounting_standard="HKFRS",
        )
        mock_retriever_class.return_value = Mock()

        agents = AgentFactory.create_agents(
            jurisdiction="HK",
            tenant_id=uuid4(),
            user_id=123,
            db=Mock(),
        )

        # Verify all expected agents created
        assert "revenue" in agents
        assert "inventory" in agents
        assert "provisions" in agents

        # Verify agent names
        assert agents["revenue"].agent_name == "revenue"
        assert agents["inventory"].agent_name == "inventory"
        assert agents["provisions"].agent_name == "provisions"

    @patch("genreport.core.orchestration.agent_factory.get_market_config")
    @patch("genreport.core.orchestration.agent_factory.SecureKBRetriever")
    def test_factory_shares_retriever_instance(
        self, mock_retriever_class, mock_config
    ):
        """Test that all agents share the same retriever instance."""
        from genreport.core.orchestration.agent_factory import AgentFactory

        mock_config.return_value = Mock(
            jurisdiction="HK",
            accounting_standard="HKFRS",
        )

        mock_retriever = Mock()
        mock_retriever_class.return_value = mock_retriever

        agents = AgentFactory.create_agents(
            jurisdiction="HK",
            tenant_id=uuid4(),
            user_id=123,
            db=Mock(),
        )

        # All agents should share same retriever
        assert agents["revenue"].retriever == mock_retriever
        assert agents["inventory"].retriever == mock_retriever
        assert agents["provisions"].retriever == mock_retriever


class TestErrorHandlingIntegration:
    """Test error handling across integrated components."""

    @patch("genreport.core.orchestration.agent_factory.get_market_config")
    @patch("genreport.core.orchestration.agent_factory.SecureKBRetriever")
    def test_unsupported_jurisdiction_error(
        self, mock_retriever_class, mock_config
    ):
        """Test error when using unsupported jurisdiction."""
        from genreport.core.orchestration.agent_factory import (
            UnsupportedJurisdictionError,
        )

        with pytest.raises(UnsupportedJurisdictionError, match="not supported"):
            SecureOrchestrator(
                jurisdiction="US",  # Not supported
                tenant_id=uuid4(),
                user_id=123,
                db=Mock(),
            )

    @patch("markets.hk.agents.revenue_agent.dspy")
    @patch("genreport.core.orchestration.agent_factory.get_market_config")
    @patch("genreport.core.orchestration.agent_factory.SecureKBRetriever")
    def test_retriever_error_handled_gracefully(
        self, mock_retriever_class, mock_config, mock_dspy
    ):
        """Test that retriever errors are handled gracefully."""
        # Setup mocks
        mock_config.return_value = Mock(
            jurisdiction="HK",
            accounting_standard="HKFRS",
        )

        # Retriever raises error
        mock_retriever = Mock()
        mock_retriever.retrieve.side_effect = Exception("Retriever error")
        mock_retriever_class.return_value = mock_retriever

        # Create orchestrator
        tenant_id = uuid4()
        orchestrator = SecureOrchestrator(
            jurisdiction="HK",
            tenant_id=tenant_id,
            user_id=123,
            db=Mock(),
        )

        # Execute agent - should not crash, but may have warnings
        output = orchestrator.run_agent(
            agent_type="revenue",
            project_id=1,
            trial_balance={"revenue": 1000000, "tenant_id": tenant_id},
        )

        # Should still return output (may have low confidence/warnings)
        assert isinstance(output, AgentOutput)
