"""Tests for SecureOrchestrator - Coordinates multiple agents securely.

Following TDD methodology: These tests are written BEFORE implementation.
They define the expected behavior of SecureOrchestrator.
"""

import pytest
from uuid import uuid4
from unittest.mock import Mock, MagicMock, patch

from genreport.core.orchestration.secure_orchestrator import SecureOrchestrator
from genreport.core.orchestration.agent_models import AgentInput, AgentOutput
from genreport.core.security.context_validator import CrossTenantDataError


class TestSecureOrchestratorInitialization:
    """Test orchestrator initialization."""

    def test_create_with_dependencies(self):
        """Create orchestrator with required dependencies."""
        db = Mock()
        tenant_id = uuid4()
        user_id = 123

        orchestrator = SecureOrchestrator(
            jurisdiction="HK",
            tenant_id=tenant_id,
            user_id=user_id,
            db=db,
        )

        assert orchestrator.jurisdiction == "HK"
        assert orchestrator.tenant_id == tenant_id
        assert orchestrator.user_id == user_id
        assert orchestrator.db == db

    def test_agents_created_on_init(self):
        """Agents are created during initialization."""
        with patch("genreport.core.orchestration.secure_orchestrator.AgentFactory") as mock_factory:
            mock_factory.create_agents.return_value = {
                "revenue": Mock(),
                "inventory": Mock(),
            }

            orchestrator = SecureOrchestrator(
                jurisdiction="HK",
                tenant_id=uuid4(),
                user_id=123,
                db=Mock(),
            )

            # Factory should be called
            mock_factory.create_agents.assert_called_once()


class TestSecureOrchestratorContextPackaging:
    """Test secure context packaging."""

    @patch("genreport.core.orchestration.secure_orchestrator.ContextValidator")
    def test_package_context_validates_tenant_id(self, mock_validator_class):
        """Package context validates all data belongs to tenant."""
        mock_validator = Mock()
        mock_validator.validate.return_value = True
        mock_validator_class.return_value = mock_validator

        orchestrator = SecureOrchestrator(
            jurisdiction="HK",
            tenant_id=uuid4(),
            user_id=123,
            db=Mock(),
        )

        context = orchestrator.package_context(
            project_id=1,
            trial_balance={"revenue": 1000000},
            general_ledger={},
        )

        # Validator should be created with tenant_id
        mock_validator_class.assert_called_once()
        # Validate should be called
        mock_validator.validate.assert_called_once()

    @patch("genreport.core.orchestration.secure_orchestrator.ContextValidator")
    def test_package_context_raises_on_cross_tenant_data(self, mock_validator_class):
        """Package context raises error if cross-tenant data detected."""
        mock_validator = Mock()
        mock_validator.validate.return_value = False
        mock_validator.get_violations.return_value = [
            {"path": "trial_balance", "found_tenant_id": "wrong-id"}
        ]
        mock_validator_class.return_value = mock_validator

        orchestrator = SecureOrchestrator(
            jurisdiction="HK",
            tenant_id=uuid4(),
            user_id=123,
            db=Mock(),
        )

        with pytest.raises(CrossTenantDataError):
            orchestrator.package_context(
                project_id=1,
                trial_balance={"tenant_id": uuid4()},  # Wrong tenant
            )


class TestSecureOrchestratorAgentExecution:
    """Test agent execution and coordination."""

    @patch("genreport.core.orchestration.secure_orchestrator.AgentFactory")
    def test_run_agent_executes_single_agent(self, mock_factory):
        """Run single agent and return output."""
        mock_agent = Mock()
        mock_agent.validate_input.return_value = True
        mock_agent.process.return_value = AgentOutput(
            disclosure_text="Revenue disclosure",
            sources=[],
            confidence_score=0.9,
            completeness_score=0.85,
        )
        mock_agent.post_process.return_value = mock_agent.process.return_value

        mock_factory.create_agents.return_value = {"revenue": mock_agent}

        orchestrator = SecureOrchestrator(
            jurisdiction="HK",
            tenant_id=uuid4(),
            user_id=123,
            db=Mock(),
        )

        output = orchestrator.run_agent(
            agent_type="revenue",
            project_id=1,
            trial_balance={"revenue": 1000000},
        )

        assert isinstance(output, AgentOutput)
        assert "Revenue disclosure" in output.disclosure_text
        mock_agent.validate_input.assert_called_once()
        mock_agent.process.assert_called_once()
        mock_agent.post_process.assert_called_once()

    @patch("genreport.core.orchestration.secure_orchestrator.AgentFactory")
    def test_run_all_agents_executes_multiple(self, mock_factory):
        """Run all agents and return dict of outputs."""
        mock_revenue = Mock()
        mock_revenue.agent_name = "revenue"
        mock_revenue.validate_input.return_value = True
        mock_revenue.process.return_value = AgentOutput(
            disclosure_text="Revenue disclosure",
            sources=[],
            confidence_score=0.9,
            completeness_score=0.85,
        )
        mock_revenue.post_process.return_value = mock_revenue.process.return_value

        mock_inventory = Mock()
        mock_inventory.agent_name = "inventory"
        mock_inventory.validate_input.return_value = True
        mock_inventory.process.return_value = AgentOutput(
            disclosure_text="Inventory disclosure",
            sources=[],
            confidence_score=0.88,
            completeness_score=0.90,
        )
        mock_inventory.post_process.return_value = mock_inventory.process.return_value

        mock_factory.create_agents.return_value = {
            "revenue": mock_revenue,
            "inventory": mock_inventory,
        }

        orchestrator = SecureOrchestrator(
            jurisdiction="HK",
            tenant_id=uuid4(),
            user_id=123,
            db=Mock(),
        )

        outputs = orchestrator.run_all_agents(
            project_id=1,
            trial_balance={"revenue": 1000000, "inventory": 500000},
        )

        assert len(outputs) == 2
        assert "revenue" in outputs
        assert "inventory" in outputs
        assert isinstance(outputs["revenue"], AgentOutput)
        assert isinstance(outputs["inventory"], AgentOutput)


class TestSecureOrchestratorErrorHandling:
    """Test error handling in orchestrator."""

    @patch("genreport.core.orchestration.secure_orchestrator.AgentFactory")
    def test_handle_unknown_agent_type(self, mock_factory):
        """Raise error for unknown agent type."""
        mock_factory.create_agents.return_value = {"revenue": Mock()}

        orchestrator = SecureOrchestrator(
            jurisdiction="HK",
            tenant_id=uuid4(),
            user_id=123,
            db=Mock(),
        )

        with pytest.raises(ValueError, match="Unknown agent type"):
            orchestrator.run_agent(
                agent_type="unknown",
                project_id=1,
                trial_balance={},
            )

    @patch("genreport.core.orchestration.secure_orchestrator.AgentFactory")
    def test_handle_agent_processing_error(self, mock_factory):
        """Handle agent processing errors gracefully."""
        mock_agent = Mock()
        mock_agent.validate_input.return_value = True
        mock_agent.process.side_effect = Exception("Agent error")

        mock_factory.create_agents.return_value = {"revenue": mock_agent}

        orchestrator = SecureOrchestrator(
            jurisdiction="HK",
            tenant_id=uuid4(),
            user_id=123,
            db=Mock(),
        )

        # Should raise the exception
        with pytest.raises(Exception, match="Agent error"):
            orchestrator.run_agent(
                agent_type="revenue",
                project_id=1,
                trial_balance={},
            )


class TestSecureOrchestratorPIIScan:
    """Test PII scanning of outputs."""

    @patch("genreport.core.orchestration.secure_orchestrator.PIIDetector")
    @patch("genreport.core.orchestration.secure_orchestrator.AgentFactory")
    def test_scan_outputs_for_pii(self, mock_factory, mock_pii_detector_class):
        """Scan agent outputs for PII."""
        mock_pii = Mock()
        mock_pii.has_pii.return_value = False
        mock_pii_detector_class.return_value = mock_pii

        mock_agent = Mock()
        mock_agent.validate_input.return_value = True
        mock_agent.process.return_value = AgentOutput(
            disclosure_text="Revenue disclosure",
            sources=[],
            confidence_score=0.9,
            completeness_score=0.85,
        )
        mock_agent.post_process.return_value = mock_agent.process.return_value

        mock_factory.create_agents.return_value = {"revenue": mock_agent}

        orchestrator = SecureOrchestrator(
            jurisdiction="HK",
            tenant_id=uuid4(),
            user_id=123,
            db=Mock(),
        )

        output = orchestrator.run_agent(
            agent_type="revenue",
            project_id=1,
            trial_balance={},
        )

        # PII detector should be called
        mock_pii.has_pii.assert_called()

    @patch("genreport.core.orchestration.secure_orchestrator.PIIDetector")
    @patch("genreport.core.orchestration.secure_orchestrator.AgentFactory")
    def test_add_warning_if_pii_detected(self, mock_factory, mock_pii_detector_class):
        """Add warning to output if PII detected."""
        mock_pii = Mock()
        mock_pii.has_pii.return_value = True  # PII found!
        mock_pii.scan.return_value = {"email": ["test@example.com"]}
        mock_pii_detector_class.return_value = mock_pii

        mock_agent = Mock()
        mock_agent.validate_input.return_value = True
        output = AgentOutput(
            disclosure_text="Contact john@example.com",
            sources=[],
            confidence_score=0.9,
            completeness_score=0.85,
            warnings=[],
        )
        mock_agent.process.return_value = output
        mock_agent.post_process.return_value = output

        mock_factory.create_agents.return_value = {"revenue": mock_agent}

        orchestrator = SecureOrchestrator(
            jurisdiction="HK",
            tenant_id=uuid4(),
            user_id=123,
            db=Mock(),
        )

        result = orchestrator.run_agent(
            agent_type="revenue",
            project_id=1,
            trial_balance={},
        )

        # Should have PII warning
        assert any("PII" in w or "email" in w for w in result.warnings)


class TestSecureOrchestratorIntegration:
    """Test integration scenarios."""

    @patch("genreport.core.orchestration.secure_orchestrator.ContextValidator")
    @patch("genreport.core.orchestration.secure_orchestrator.PIIDetector")
    @patch("genreport.core.orchestration.secure_orchestrator.AgentFactory")
    def test_complete_workflow(self, mock_factory, mock_pii_class, mock_validator_class):
        """Test complete workflow from input to output."""
        # Setup mocks
        mock_validator = Mock()
        mock_validator.validate.return_value = True
        mock_validator_class.return_value = mock_validator

        mock_pii = Mock()
        mock_pii.has_pii.return_value = False
        mock_pii_class.return_value = mock_pii

        mock_agent = Mock()
        mock_agent.validate_input.return_value = True
        mock_agent.process.return_value = AgentOutput(
            disclosure_text="Revenue disclosure",
            sources=[],
            confidence_score=0.9,
            completeness_score=0.85,
        )
        mock_agent.post_process.return_value = mock_agent.process.return_value

        mock_factory.create_agents.return_value = {"revenue": mock_agent}

        # Create orchestrator
        tenant_id = uuid4()
        orchestrator = SecureOrchestrator(
            jurisdiction="HK",
            tenant_id=tenant_id,
            user_id=123,
            db=Mock(),
        )

        # Run agent
        output = orchestrator.run_agent(
            agent_type="revenue",
            project_id=1,
            trial_balance={"revenue": 1000000},
        )

        # Verify complete flow
        assert isinstance(output, AgentOutput)
        mock_validator.validate.assert_called()  # Context validated
        mock_agent.validate_input.assert_called()  # Input validated
        mock_agent.process.assert_called()  # Agent processed
        mock_agent.post_process.assert_called()  # Post-processed
        mock_pii.has_pii.assert_called()  # PII scanned
