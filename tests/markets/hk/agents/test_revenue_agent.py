"""Tests for HKRevenueAgent - Hong Kong Revenue Recognition Agent.

Following TDD methodology: These tests are written BEFORE implementation.
They define the expected behavior of the HK Revenue Recognition Agent using DSPy.
"""

import pytest
from uuid import uuid4
from unittest.mock import Mock, MagicMock, patch

from genreport.core.orchestration.agent_models import AgentInput, AgentOutput, Source
from markets.hk.agents.revenue_agent import HKRevenueAgent


class TestHKRevenueAgentInitialization:
    """Test HK Revenue Agent initialization."""

    def test_create_with_dependencies(self):
        """Create agent with all dependencies."""
        market_config = Mock()
        market_config.jurisdiction = "HK"
        market_config.accounting_standard = "HKFRS"

        retriever = Mock()
        tenant_id = uuid4()
        user_id = 123

        agent = HKRevenueAgent(
            market_config=market_config,
            retriever=retriever,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        assert agent.market_config == market_config
        assert agent.retriever == retriever
        assert agent.tenant_id == tenant_id
        assert agent.user_id == user_id

    def test_agent_name_is_revenue(self):
        """Agent name should be 'revenue'."""
        agent = HKRevenueAgent(
            market_config=Mock(),
            retriever=Mock(),
            tenant_id=uuid4(),
            user_id=123,
        )

        assert agent.agent_name == "revenue"

    def test_supported_jurisdictions_includes_hk(self):
        """Supported jurisdictions should include HK."""
        agent = HKRevenueAgent(
            market_config=Mock(),
            retriever=Mock(),
            tenant_id=uuid4(),
            user_id=123,
        )

        assert "HK" in agent.supported_jurisdictions


class TestHKRevenueAgentValidation:
    """Test input validation."""

    def test_validate_input_requires_trial_balance(self):
        """Validation requires trial balance with revenue data."""
        agent = HKRevenueAgent(
            market_config=Mock(),
            retriever=Mock(),
            tenant_id=uuid4(),
            user_id=123,
        )

        # Valid input with trial balance
        valid_input = AgentInput(
            tenant_id=agent.tenant_id,
            project_id=1,
            trial_balance={"revenue": 1000000},
        )

        assert agent.validate_input(valid_input) is True

    def test_validate_input_checks_tenant_id(self):
        """Validation checks tenant ID matches."""
        tenant_id = uuid4()
        agent = HKRevenueAgent(
            market_config=Mock(),
            retriever=Mock(),
            tenant_id=tenant_id,
            user_id=123,
        )

        # Mismatched tenant
        wrong_input = AgentInput(
            tenant_id=uuid4(),  # Different tenant
            project_id=1,
            trial_balance={},
        )

        # Should raise error via validate_tenant
        with pytest.raises(ValueError, match="Tenant ID mismatch"):
            agent.validate_tenant(wrong_input)


class TestHKRevenueAgentProcessing:
    """Test agent processing with DSPy."""

    @patch("markets.hk.agents.revenue_agent.dspy")
    def test_process_generates_disclosure(self, mock_dspy):
        """Process should generate revenue disclosure using DSPy."""
        # Mock DSPy ChainOfThought
        mock_cot = Mock()
        mock_cot.return_value = Mock(
            disclosure="Revenue is recognized when control transfers to customer per HKFRS 15.",
            confidence=0.9,
            completeness=0.85,
            sources_used="HKFRS 15, paragraph 31",
        )
        mock_dspy.ChainOfThought = Mock(return_value=mock_cot)

        # Mock retriever
        mock_retriever = Mock()
        mock_retriever.retrieve.return_value = [
            {
                "document_id": uuid4(),
                "chunk_id": uuid4(),
                "score": 0.92,
                "text": "HKFRS 15 revenue recognition guidance",
            }
        ]

        market_config = Mock()
        market_config.jurisdiction = "HK"
        market_config.accounting_standard = "HKFRS"

        agent = HKRevenueAgent(
            market_config=market_config,
            retriever=mock_retriever,
            tenant_id=uuid4(),
            user_id=123,
        )

        agent_input = AgentInput(
            tenant_id=agent.tenant_id,
            project_id=1,
            trial_balance={"revenue": 1000000, "deferred_revenue": 50000},
            accounting_policies={"revenue_recognition": "point_in_time"},
        )

        output = agent.process(agent_input)

        # Verify output structure
        assert isinstance(output, AgentOutput)
        assert len(output.disclosure_text) > 0
        assert "HKFRS 15" in output.disclosure_text or "revenue" in output.disclosure_text.lower()
        assert output.confidence_score >= 0.0
        assert output.confidence_score <= 1.0
        assert output.completeness_score >= 0.0
        assert output.completeness_score <= 1.0

    @patch("markets.hk.agents.revenue_agent.dspy")
    def test_process_includes_sources(self, mock_dspy):
        """Process should include KB sources in output."""
        # Mock DSPy module
        mock_cot = Mock()
        mock_cot.return_value = Mock(
            disclosure="Revenue disclosure",
            confidence=0.9,
            completeness=0.85,
            sources_used="HKFRS 15",
        )
        mock_dspy.ChainOfThought = Mock(return_value=mock_cot)

        mock_retriever = Mock()
        doc_id = uuid4()
        chunk_id = uuid4()

        mock_retriever.retrieve.return_value = [
            {
                "document_id": doc_id,
                "chunk_id": chunk_id,
                "score": 0.95,
                "text": "HKFRS 15 revenue recognition",
            }
        ]

        market_config = Mock()
        market_config.jurisdiction = "HK"
        market_config.accounting_standard = "HKFRS"

        agent = HKRevenueAgent(
            market_config=market_config,
            retriever=mock_retriever,
            tenant_id=uuid4(),
            user_id=123,
        )

        agent_input = AgentInput(
            tenant_id=agent.tenant_id,
            project_id=1,
            trial_balance={"revenue": 1000000},
        )

        output = agent.process(agent_input)

        # Should have sources
        assert len(output.sources) > 0
        assert any(s.document_id == doc_id for s in output.sources)


class TestHKRevenueAgentPostProcessing:
    """Test post-processing of agent output."""

    def test_post_process_adds_warning_for_low_confidence(self):
        """Post-process adds warning when confidence is low."""
        agent = HKRevenueAgent(
            market_config=Mock(),
            retriever=Mock(),
            tenant_id=uuid4(),
            user_id=123,
        )

        low_confidence_output = AgentOutput(
            disclosure_text="Revenue disclosure",
            sources=[],
            confidence_score=0.6,  # Low confidence
            completeness_score=0.8,
        )

        processed = agent.post_process(low_confidence_output)

        # Should add warning
        assert len(processed.warnings) > 0
        assert any("confidence" in w.lower() for w in processed.warnings)

    def test_post_process_adds_warning_for_missing_data(self):
        """Post-process adds warning when completeness is low."""
        agent = HKRevenueAgent(
            market_config=Mock(),
            retriever=Mock(),
            tenant_id=uuid4(),
            user_id=123,
        )

        incomplete_output = AgentOutput(
            disclosure_text="Revenue disclosure",
            sources=[],
            confidence_score=0.85,
            completeness_score=0.6,  # Low completeness
        )

        processed = agent.post_process(incomplete_output)

        # Should add warning
        assert len(processed.warnings) > 0
        assert any("incomplete" in w.lower() or "missing" in w.lower() for w in processed.warnings)

    def test_post_process_no_warning_for_high_scores(self):
        """Post-process does not add warnings when scores are high."""
        agent = HKRevenueAgent(
            market_config=Mock(),
            retriever=Mock(),
            tenant_id=uuid4(),
            user_id=123,
        )

        good_output = AgentOutput(
            disclosure_text="Revenue disclosure",
            sources=[],
            confidence_score=0.9,
            completeness_score=0.9,
        )

        processed = agent.post_process(good_output)

        # Should not add warnings
        assert len(processed.warnings) == 0


class TestHKRevenueAgentMarketSpecific:
    """Test HK market-specific behavior."""

    def test_uses_hkfrs_standard(self):
        """Agent should reference HKFRS 15 for revenue."""
        market_config = Mock()
        market_config.jurisdiction = "HK"
        market_config.accounting_standard = "HKFRS"

        mock_retriever = Mock()
        mock_retriever.retrieve.return_value = []

        agent = HKRevenueAgent(
            market_config=market_config,
            retriever=mock_retriever,
            tenant_id=uuid4(),
            user_id=123,
        )

        # Market config should be used in processing
        assert agent.market_config.accounting_standard == "HKFRS"

    def test_supports_sme_frs(self):
        """Agent should support SME-FRS for small entities."""
        market_config = Mock()
        market_config.jurisdiction = "HK"
        market_config.accounting_standard = "SME-FRS"

        agent = HKRevenueAgent(
            market_config=market_config,
            retriever=Mock(),
            tenant_id=uuid4(),
            user_id=123,
        )

        # Should accept SME-FRS
        assert agent.market_config.accounting_standard == "SME-FRS"


class TestHKRevenueAgentIntegration:
    """Test integration scenarios."""

    def test_complete_workflow(self):
        """Test complete workflow from input to output."""
        market_config = Mock()
        market_config.jurisdiction = "HK"
        market_config.accounting_standard = "HKFRS"

        mock_retriever = Mock()
        mock_retriever.retrieve.return_value = [
            {
                "document_id": uuid4(),
                "chunk_id": uuid4(),
                "score": 0.9,
                "text": "HKFRS 15 guidance",
            }
        ]

        tenant_id = uuid4()

        agent = HKRevenueAgent(
            market_config=market_config,
            retriever=mock_retriever,
            tenant_id=tenant_id,
            user_id=123,
        )

        # Create input
        agent_input = AgentInput(
            tenant_id=tenant_id,
            project_id=1,
            trial_balance={"revenue": 1000000, "deferred_revenue": 50000},
            accounting_policies={"revenue_recognition": "point_in_time"},
        )

        # Validate
        assert agent.validate_input(agent_input) is True

        # Process
        output = agent.process(agent_input)

        assert isinstance(output, AgentOutput)
        assert len(output.disclosure_text) > 0

        # Post-process
        final_output = agent.post_process(output)

        assert isinstance(final_output, AgentOutput)
        assert final_output.disclosure_text == output.disclosure_text


class TestHKRevenueAgentErrorHandling:
    """Test error handling."""

    def test_handle_empty_trial_balance(self):
        """Handle empty trial balance gracefully."""
        agent = HKRevenueAgent(
            market_config=Mock(),
            retriever=Mock(),
            tenant_id=uuid4(),
            user_id=123,
        )

        empty_input = AgentInput(
            tenant_id=agent.tenant_id,
            project_id=1,
            trial_balance={},  # Empty
        )

        # Should still validate (empty is allowed, just not None)
        assert agent.validate_input(empty_input) is True

    def test_handle_retriever_errors(self):
        """Handle retriever errors gracefully."""
        mock_retriever = Mock()
        mock_retriever.retrieve.side_effect = Exception("Retriever error")

        agent = HKRevenueAgent(
            market_config=Mock(),
            retriever=mock_retriever,
            tenant_id=uuid4(),
            user_id=123,
        )

        agent_input = AgentInput(
            tenant_id=agent.tenant_id,
            project_id=1,
            trial_balance={"revenue": 1000000},
        )

        # Should not crash, but may produce output with warnings
        output = agent.process(agent_input)

        assert isinstance(output, AgentOutput)
        # May have warnings about retrieval failure
