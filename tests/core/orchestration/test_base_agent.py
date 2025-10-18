"""Tests for BaseFinancialAgent - Abstract base class for all agents.

Following TDD methodology: These tests are written BEFORE implementation.
They define the expected behavior of BaseFinancialAgent through a concrete test implementation.
"""

import pytest
from uuid import uuid4
from unittest.mock import Mock, MagicMock, patch
from abc import ABC

from genreport.core.orchestration.base_agent import BaseFinancialAgent
from genreport.core.orchestration.agent_models import AgentInput, AgentOutput, Source


# Test implementation of abstract base class
class TestAgent(BaseFinancialAgent):
    """Concrete implementation for testing BaseFinancialAgent."""

    @property
    def agent_name(self) -> str:
        return "test_agent"

    @property
    def supported_jurisdictions(self) -> list[str]:
        return ["HK", "SG"]

    def process(self, agent_input: AgentInput) -> AgentOutput:
        """Mock implementation of process."""
        return AgentOutput(
            disclosure_text="Test disclosure",
            sources=[],
            confidence_score=0.85,
            completeness_score=0.90,
        )

    def validate_input(self, agent_input: AgentInput) -> bool:
        """Mock implementation of validate_input."""
        return agent_input.trial_balance is not None

    def post_process(self, output: AgentOutput) -> AgentOutput:
        """Mock implementation of post_process."""
        # Add warning if confidence is low
        if output.confidence_score < 0.7:
            output.warnings.append("Low confidence score")
        return output


class TestBaseFinancialAgentInitialization:
    """Test initialization and dependency injection."""

    def test_initialize_with_all_dependencies(self):
        """Initialize agent with all required dependencies."""
        market_config = Mock()
        retriever = Mock()
        tenant_id = uuid4()
        user_id = 123

        agent = TestAgent(
            market_config=market_config,
            retriever=retriever,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        assert agent.market_config == market_config
        assert agent.retriever == retriever
        assert agent.tenant_id == tenant_id
        assert agent.user_id == user_id

    def test_agent_name_property(self):
        """Agent has name property."""
        agent = TestAgent(
            market_config=Mock(),
            retriever=Mock(),
            tenant_id=uuid4(),
            user_id=123,
        )

        assert agent.agent_name == "test_agent"

    def test_supported_jurisdictions_property(self):
        """Agent declares supported jurisdictions."""
        agent = TestAgent(
            market_config=Mock(),
            retriever=Mock(),
            tenant_id=uuid4(),
            user_id=123,
        )

        assert "HK" in agent.supported_jurisdictions
        assert "SG" in agent.supported_jurisdictions


class TestBaseFinancialAgentAbstractMethods:
    """Test that abstract methods must be implemented."""

    def test_cannot_instantiate_base_class_directly(self):
        """Cannot create instance of abstract base class."""
        with pytest.raises(TypeError):
            BaseFinancialAgent(
                market_config=Mock(),
                retriever=Mock(),
                tenant_id=uuid4(),
                user_id=123,
            )

    def test_subclass_must_implement_agent_name(self):
        """Subclass must implement agent_name property."""

        class IncompleteAgent(BaseFinancialAgent):
            @property
            def supported_jurisdictions(self):
                return ["HK"]

            def process(self, agent_input):
                pass

            def validate_input(self, agent_input):
                return True

            def post_process(self, output):
                return output

        with pytest.raises(TypeError):
            IncompleteAgent(
                market_config=Mock(),
                retriever=Mock(),
                tenant_id=uuid4(),
                user_id=123,
            )

    def test_subclass_must_implement_process(self):
        """Subclass must implement process method."""

        class IncompleteAgent(BaseFinancialAgent):
            @property
            def agent_name(self):
                return "incomplete"

            @property
            def supported_jurisdictions(self):
                return ["HK"]

            def validate_input(self, agent_input):
                return True

            def post_process(self, output):
                return output

        with pytest.raises(TypeError):
            IncompleteAgent(
                market_config=Mock(),
                retriever=Mock(),
                tenant_id=uuid4(),
                user_id=123,
            )


class TestBaseFinancialAgentProtectedMethods:
    """Test protected helper methods available to subclasses."""

    @patch("genreport.core.orchestration.base_agent.AuditLogger")
    def test_log_generation_creates_audit_log(self, mock_audit_logger):
        """_log_generation creates audit log entry."""
        agent = TestAgent(
            market_config=Mock(),
            retriever=Mock(),
            tenant_id=uuid4(),
            user_id=123,
        )

        output = AgentOutput(
            disclosure_text="Test",
            sources=[],
            confidence_score=0.85,
            completeness_score=0.90,
        )

        agent._log_generation(
            agent_input=Mock(project_id=1),
            output=output,
            duration_seconds=1.5,
        )

        # Verify audit log was called
        mock_audit_logger.log_event.assert_called_once()

        call_args = mock_audit_logger.log_event.call_args
        assert call_args[1]["event_type"] == "AGENT_GENERATION"
        assert call_args[1]["tenant_id"] == agent.tenant_id
        assert call_args[1]["user_id"] == agent.user_id

    def test_fetch_context_uses_retriever(self):
        """_fetch_context queries retriever with proper tenant context."""
        mock_retriever = Mock()
        mock_retriever.retrieve.return_value = [
            {
                "document_id": uuid4(),
                "chunk_id": uuid4(),
                "score": 0.9,
                "text": "Test context",
            }
        ]

        agent = TestAgent(
            market_config=Mock(),
            retriever=mock_retriever,
            tenant_id=uuid4(),
            user_id=123,
        )

        sources = agent._fetch_context("revenue recognition")

        # Verify retriever was called
        mock_retriever.retrieve.assert_called_once_with("revenue recognition")

        # Verify sources returned
        assert len(sources) > 0
        assert isinstance(sources[0], Source)

    def test_fetch_context_empty_query_returns_empty(self):
        """_fetch_context with empty query returns empty list."""
        agent = TestAgent(
            market_config=Mock(),
            retriever=Mock(),
            tenant_id=uuid4(),
            user_id=123,
        )

        sources = agent._fetch_context("")

        assert sources == []


class TestBaseFinancialAgentWorkflow:
    """Test complete agent workflow."""

    def test_complete_workflow(self):
        """Test complete process from input to output."""
        mock_retriever = Mock()
        mock_retriever.retrieve.return_value = []

        agent = TestAgent(
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

        # Validate input
        assert agent.validate_input(agent_input) is True

        # Process
        output = agent.process(agent_input)

        assert isinstance(output, AgentOutput)
        assert output.disclosure_text == "Test disclosure"
        assert output.confidence_score == 0.85

        # Post-process
        final_output = agent.post_process(output)

        assert isinstance(final_output, AgentOutput)
        # High confidence, no warnings added
        assert len(final_output.warnings) == 0

    def test_post_process_adds_warning_for_low_confidence(self):
        """Post-process adds warning when confidence is low."""
        agent = TestAgent(
            market_config=Mock(),
            retriever=Mock(),
            tenant_id=uuid4(),
            user_id=123,
        )

        low_confidence_output = AgentOutput(
            disclosure_text="Test",
            sources=[],
            confidence_score=0.6,  # Below threshold
            completeness_score=0.8,
        )

        final_output = agent.post_process(low_confidence_output)

        assert "Low confidence score" in final_output.warnings


class TestBaseFinancialAgentTenantIsolation:
    """Test tenant isolation enforcement."""

    def test_agent_bound_to_specific_tenant(self):
        """Agent is bound to specific tenant ID."""
        tenant_a = uuid4()
        tenant_b = uuid4()

        agent_a = TestAgent(
            market_config=Mock(),
            retriever=Mock(),
            tenant_id=tenant_a,
            user_id=123,
        )

        agent_b = TestAgent(
            market_config=Mock(),
            retriever=Mock(),
            tenant_id=tenant_b,
            user_id=456,
        )

        assert agent_a.tenant_id == tenant_a
        assert agent_b.tenant_id == tenant_b
        assert agent_a.tenant_id != agent_b.tenant_id

    def test_input_tenant_id_validation(self):
        """Validate input tenant_id matches agent tenant_id."""
        tenant_id = uuid4()

        agent = TestAgent(
            market_config=Mock(),
            retriever=Mock(),
            tenant_id=tenant_id,
            user_id=123,
        )

        # Matching tenant - valid
        valid_input = AgentInput(
            tenant_id=tenant_id,
            project_id=1,
            trial_balance={},
        )

        assert agent.validate_input(valid_input) is True

        # Mismatched tenant - should be caught by validation
        wrong_tenant_input = AgentInput(
            tenant_id=uuid4(),  # Different tenant
            project_id=1,
            trial_balance={},
        )

        # The base validate_tenant method should detect this
        with pytest.raises(ValueError, match="Tenant ID mismatch"):
            agent.validate_tenant(wrong_tenant_input)


class TestBaseFinancialAgentErrorHandling:
    """Test error handling in agent operations."""

    def test_handle_retriever_error_gracefully(self):
        """Handle retriever errors gracefully."""
        mock_retriever = Mock()
        mock_retriever.retrieve.side_effect = Exception("Retriever error")

        agent = TestAgent(
            market_config=Mock(),
            retriever=mock_retriever,
            tenant_id=uuid4(),
            user_id=123,
        )

        # Should not raise, but return empty sources
        sources = agent._fetch_context("test query")

        assert sources == []

    def test_handle_empty_trial_balance(self):
        """Handle empty trial balance in validation."""
        from pydantic import ValidationError as PydanticValidationError

        agent = TestAgent(
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

        # Should still be valid (not None)
        assert agent.validate_input(empty_input) is True

        # None trial_balance should be caught by Pydantic validation
        with pytest.raises(PydanticValidationError):
            AgentInput(
                tenant_id=agent.tenant_id,
                project_id=1,
                trial_balance=None,  # Invalid: None not allowed
            )
