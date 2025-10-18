"""AgentFactory - Factory pattern for creating market-specific agents.

This module provides the factory interface for creating agents based on jurisdiction.
It handles lazy loading of market-specific implementations and dependency injection.
"""

import logging
from typing import Dict
from uuid import UUID
from sqlalchemy.orm import Session

from genreport.core.orchestration.base_agent import BaseFinancialAgent
from genreport.core.retrieval.secure_kb_retriever import SecureKBRetriever
from genreport.core.utils.market_config import get_market_config

logger = logging.getLogger(__name__)


class UnsupportedJurisdictionError(Exception):
    """Raised when jurisdiction is not supported."""

    pass


class AgentFactory:
    """Factory for creating market-specific financial disclosure agents.

    Uses lazy loading to only import agents for the requested jurisdiction.
    Handles dependency injection of market config and retriever.
    """

    # Supported jurisdictions
    SUPPORTED_JURISDICTIONS = ["HK"]  # SG, AU will be added later

    @staticmethod
    def create_agents(
        jurisdiction: str,
        tenant_id: UUID,
        user_id: int,
        db: Session,
    ) -> Dict[str, BaseFinancialAgent]:
        """Create all agents for specified jurisdiction.

        Args:
            jurisdiction: Jurisdiction code (HK, SG, AU)
            tenant_id: Tenant making the request
            user_id: User making the request
            db: Database session for retriever

        Returns:
            Dict mapping agent type to agent instance

        Raises:
            UnsupportedJurisdictionError: If jurisdiction not supported
            ValueError: If parameters invalid
        """
        # Validate inputs
        if not jurisdiction or not jurisdiction.strip():
            raise UnsupportedJurisdictionError("Jurisdiction cannot be empty")

        # Normalize to uppercase
        jurisdiction = jurisdiction.upper()

        # Check if supported
        if jurisdiction not in AgentFactory.SUPPORTED_JURISDICTIONS:
            raise UnsupportedJurisdictionError(
                f"Jurisdiction '{jurisdiction}' is not supported. "
                f"Supported: {AgentFactory.SUPPORTED_JURISDICTIONS}"
            )

        # Get market configuration
        market_config = get_market_config(jurisdiction)

        # Create secure retriever for this jurisdiction/tenant
        retriever = SecureKBRetriever(
            jurisdiction=jurisdiction,
            tenant_id=tenant_id,
            user_id=user_id,
            db=db,
        )

        # Lazy load market-specific agents
        if jurisdiction == "HK":
            return AgentFactory._create_hk_agents(
                market_config=market_config,
                retriever=retriever,
                tenant_id=tenant_id,
                user_id=user_id,
            )
        elif jurisdiction == "SG":
            # Future implementation
            raise UnsupportedJurisdictionError(
                "Singapore agents not yet implemented"
            )
        elif jurisdiction == "AU":
            # Future implementation
            raise UnsupportedJurisdictionError(
                "Australia agents not yet implemented"
            )
        else:
            raise UnsupportedJurisdictionError(
                f"No agent implementation for {jurisdiction}"
            )

    @staticmethod
    def _create_hk_agents(
        market_config,
        retriever,
        tenant_id: UUID,
        user_id: int,
    ) -> Dict[str, BaseFinancialAgent]:
        """Create Hong Kong agents.

        Args:
            market_config: HK market configuration
            retriever: SecureKBRetriever instance
            tenant_id: Tenant ID
            user_id: User ID

        Returns:
            Dict of agent_type -> agent instance
        """
        # Lazy import to avoid loading all markets
        try:
            from markets.hk.agents.revenue_agent import HKRevenueAgent
            from markets.hk.agents.inventory_agent import HKInventoryAgent
            from markets.hk.agents.provisions_agent import HKProvisionsAgent
        except ImportError:
            # Phase 3 will implement these
            # For now, return mock agents for testing
            logger.warning("HK agents not yet implemented, using mock agents for testing")
            from tests.core.orchestration.test_base_agent import TestAgent

            return {
                "revenue": TestAgent(market_config, retriever, tenant_id, user_id),
                "inventory": TestAgent(market_config, retriever, tenant_id, user_id),
                "provisions": TestAgent(market_config, retriever, tenant_id, user_id),
            }

        # Create agent instances
        agents = {
            "revenue": HKRevenueAgent(
                market_config=market_config,
                retriever=retriever,
                tenant_id=tenant_id,
                user_id=user_id,
            ),
            "inventory": HKInventoryAgent(
                market_config=market_config,
                retriever=retriever,
                tenant_id=tenant_id,
                user_id=user_id,
            ),
            "provisions": HKProvisionsAgent(
                market_config=market_config,
                retriever=retriever,
                tenant_id=tenant_id,
                user_id=user_id,
            ),
        }

        return agents
