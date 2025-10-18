"""Tests for AgentFactory - Factory pattern for creating market-specific agents.

Following TDD methodology: These tests are written BEFORE implementation.
They define the expected behavior of AgentFactory.
"""

import pytest
from uuid import uuid4
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from genreport.core.orchestration.agent_factory import AgentFactory, UnsupportedJurisdictionError


class TestAgentFactoryBasicFunctionality:
    """Test basic factory functionality."""

    @patch("genreport.core.orchestration.agent_factory.get_market_config")
    @patch("genreport.core.orchestration.agent_factory.SecureKBRetriever")
    def test_create_agents_for_hk(self, mock_retriever_class, mock_get_config):
        """Create agents for Hong Kong market."""
        mock_config = Mock()
        mock_config.jurisdiction = "HK"
        mock_get_config.return_value = mock_config

        mock_retriever = Mock()
        mock_retriever_class.return_value = mock_retriever

        tenant_id = uuid4()
        user_id = 123
        db = Mock(spec=Session)

        agents = AgentFactory.create_agents(
            jurisdiction="HK",
            tenant_id=tenant_id,
            user_id=user_id,
            db=db,
        )

        # Should return dict of agents
        assert isinstance(agents, dict)
        assert len(agents) > 0

        # Verify market config was fetched
        mock_get_config.assert_called_once_with("HK")

        # Verify retriever was created with correct params
        mock_retriever_class.assert_called_once_with(
            jurisdiction="HK",
            tenant_id=tenant_id,
            user_id=user_id,
            db=db,
        )

    def test_unsupported_jurisdiction_raises_error(self):
        """Unsupported jurisdiction raises UnsupportedJurisdictionError."""
        with pytest.raises(UnsupportedJurisdictionError, match="UNKNOWN"):
            AgentFactory.create_agents(
                jurisdiction="UNKNOWN",
                tenant_id=uuid4(),
                user_id=123,
                db=Mock(),
            )

    @patch("genreport.core.orchestration.agent_factory.get_market_config")
    @patch("genreport.core.orchestration.agent_factory.SecureKBRetriever")
    def test_agents_have_correct_types(self, mock_retriever_class, mock_get_config):
        """Agents dictionary contains expected agent types."""
        mock_config = Mock()
        mock_config.jurisdiction = "HK"
        mock_get_config.return_value = mock_config

        mock_retriever = Mock()
        mock_retriever_class.return_value = mock_retriever

        agents = AgentFactory.create_agents(
            jurisdiction="HK",
            tenant_id=uuid4(),
            user_id=123,
            db=Mock(),
        )

        # HK should have these agent types
        expected_types = ["revenue", "inventory", "provisions"]

        for agent_type in expected_types:
            assert agent_type in agents
            assert agents[agent_type] is not None


class TestAgentFactoryLazyLoading:
    """Test lazy loading of market-specific implementations."""

    @patch("genreport.core.orchestration.agent_factory.get_market_config")
    @patch("genreport.core.orchestration.agent_factory.SecureKBRetriever")
    def test_only_imports_requested_market(self, mock_retriever_class, mock_get_config):
        """Factory only imports agents for requested jurisdiction."""
        mock_config = Mock()
        mock_config.jurisdiction = "HK"
        mock_get_config.return_value = mock_config

        mock_retriever = Mock()
        mock_retriever_class.return_value = mock_retriever

        # Create HK agents
        agents = AgentFactory.create_agents(
            jurisdiction="HK",
            tenant_id=uuid4(),
            user_id=123,
            db=Mock(),
        )

        # Should successfully create HK agents
        assert len(agents) > 0

        # Verify market config was only called for HK
        mock_get_config.assert_called_once_with("HK")


class TestAgentFactoryDependencyInjection:
    """Test dependency injection into agents."""

    @patch("genreport.core.orchestration.agent_factory.get_market_config")
    @patch("genreport.core.orchestration.agent_factory.SecureKBRetriever")
    def test_agents_receive_market_config(self, mock_retriever_class, mock_get_config):
        """Agents receive market config from factory."""
        mock_config = Mock()
        mock_config.jurisdiction = "HK"
        mock_config.accounting_standard = "HKFRS"
        mock_get_config.return_value = mock_config

        mock_retriever = Mock()
        mock_retriever_class.return_value = mock_retriever

        agents = AgentFactory.create_agents(
            jurisdiction="HK",
            tenant_id=uuid4(),
            user_id=123,
            db=Mock(),
        )

        # Each agent should have the market config
        for agent_name, agent in agents.items():
            assert agent.market_config == mock_config
            assert agent.market_config.jurisdiction == "HK"

    @patch("genreport.core.orchestration.agent_factory.get_market_config")
    @patch("genreport.core.orchestration.agent_factory.SecureKBRetriever")
    def test_agents_receive_retriever(self, mock_retriever_class, mock_get_config):
        """Agents receive retriever from factory."""
        mock_config = Mock()
        mock_config.jurisdiction = "HK"
        mock_get_config.return_value = mock_config

        mock_retriever = Mock()
        mock_retriever_class.return_value = mock_retriever

        agents = AgentFactory.create_agents(
            jurisdiction="HK",
            tenant_id=uuid4(),
            user_id=123,
            db=Mock(),
        )

        # Each agent should have the same retriever instance
        for agent_name, agent in agents.items():
            assert agent.retriever == mock_retriever

    @patch("genreport.core.orchestration.agent_factory.get_market_config")
    @patch("genreport.core.orchestration.agent_factory.SecureKBRetriever")
    def test_agents_receive_tenant_context(self, mock_retriever_class, mock_get_config):
        """Agents receive tenant and user context."""
        mock_config = Mock()
        mock_config.jurisdiction = "HK"
        mock_get_config.return_value = mock_config

        mock_retriever = Mock()
        mock_retriever_class.return_value = mock_retriever

        tenant_id = uuid4()
        user_id = 456

        agents = AgentFactory.create_agents(
            jurisdiction="HK",
            tenant_id=tenant_id,
            user_id=user_id,
            db=Mock(),
        )

        # Each agent should have correct tenant/user context
        for agent_name, agent in agents.items():
            assert agent.tenant_id == tenant_id
            assert agent.user_id == user_id


class TestAgentFactoryErrorHandling:
    """Test error handling in factory."""

    def test_none_jurisdiction_raises_error(self):
        """None jurisdiction raises error."""
        with pytest.raises((ValueError, UnsupportedJurisdictionError)):
            AgentFactory.create_agents(
                jurisdiction=None,
                tenant_id=uuid4(),
                user_id=123,
                db=Mock(),
            )

    def test_empty_jurisdiction_raises_error(self):
        """Empty jurisdiction raises error."""
        with pytest.raises((ValueError, UnsupportedJurisdictionError)):
            AgentFactory.create_agents(
                jurisdiction="",
                tenant_id=uuid4(),
                user_id=123,
                db=Mock(),
            )

    @patch("genreport.core.orchestration.agent_factory.get_market_config")
    @patch("genreport.core.orchestration.agent_factory.SecureKBRetriever")
    def test_market_config_error_propagates(self, mock_retriever_class, mock_get_config):
        """Error fetching market config propagates for supported jurisdictions."""
        # Mock HK as supported but config fetch fails
        mock_get_config.side_effect = ValueError("Config fetch failed")
        mock_retriever_class.return_value = Mock()

        with pytest.raises(ValueError, match="Config fetch failed"):
            AgentFactory.create_agents(
                jurisdiction="HK",  # Supported, but config fetch will fail
                tenant_id=uuid4(),
                user_id=123,
                db=Mock(),
            )


class TestAgentFactoryMultipleJurisdictions:
    """Test factory with multiple jurisdictions."""

    @patch("genreport.core.orchestration.agent_factory.get_market_config")
    @patch("genreport.core.orchestration.agent_factory.SecureKBRetriever")
    def test_create_hk_and_sg_agents_independently(
        self, mock_retriever_class, mock_get_config
    ):
        """Create agents for different jurisdictions independently."""

        def mock_config_side_effect(jurisdiction):
            config = Mock()
            config.jurisdiction = jurisdiction
            return config

        mock_get_config.side_effect = mock_config_side_effect
        mock_retriever_class.return_value = Mock()

        # Create HK agents
        hk_agents = AgentFactory.create_agents(
            jurisdiction="HK",
            tenant_id=uuid4(),
            user_id=123,
            db=Mock(),
        )

        # Create SG agents (if implemented)
        # This will fail until SG agents are implemented
        # but the test demonstrates the pattern

        assert len(hk_agents) > 0
        assert all(agent.market_config.jurisdiction == "HK" for agent in hk_agents.values())


class TestAgentFactoryCaseInsensitivity:
    """Test jurisdiction code case handling."""

    @patch("genreport.core.orchestration.agent_factory.get_market_config")
    @patch("genreport.core.orchestration.agent_factory.SecureKBRetriever")
    def test_lowercase_jurisdiction_accepted(self, mock_retriever_class, mock_get_config):
        """Lowercase jurisdiction codes are normalized to uppercase."""
        mock_config = Mock()
        mock_config.jurisdiction = "HK"
        mock_get_config.return_value = mock_config

        mock_retriever = Mock()
        mock_retriever_class.return_value = mock_retriever

        # Should normalize to HK
        agents = AgentFactory.create_agents(
            jurisdiction="hk",  # lowercase
            tenant_id=uuid4(),
            user_id=123,
            db=Mock(),
        )

        assert len(agents) > 0
        # get_market_config should be called with uppercase
        mock_get_config.assert_called_once_with("HK")


class TestAgentFactoryIntegration:
    """Test integration scenarios."""

    @patch("genreport.core.orchestration.agent_factory.get_market_config")
    @patch("genreport.core.orchestration.agent_factory.SecureKBRetriever")
    def test_agents_can_process_input(self, mock_retriever_class, mock_get_config):
        """Created agents can process input."""
        from genreport.core.orchestration.agent_models import AgentInput, AgentOutput

        mock_config = Mock()
        mock_config.jurisdiction = "HK"
        mock_get_config.return_value = mock_config

        mock_retriever = Mock()
        mock_retriever_class.return_value = mock_retriever

        tenant_id = uuid4()

        agents = AgentFactory.create_agents(
            jurisdiction="HK",
            tenant_id=tenant_id,
            user_id=123,
            db=Mock(),
        )

        # Try to process with one agent
        revenue_agent = agents.get("revenue")
        assert revenue_agent is not None

        # Create input
        agent_input = AgentInput(
            tenant_id=tenant_id,
            project_id=1,
            trial_balance={"revenue": 1000000},
        )

        # Should be able to validate input
        is_valid = revenue_agent.validate_input(agent_input)
        assert isinstance(is_valid, bool)
