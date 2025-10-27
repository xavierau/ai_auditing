"""AgentFactory - Factory pattern for creating market-specific agents.

This module provides the factory interface for creating agents based on jurisdiction.
It handles lazy loading of market-specific implementations and dependency injection.
"""

import logging
from typing import Dict, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from genreport.core.orchestration.base_agent import BaseFinancialAgent
from genreport.core.orchestration.rag_orchestrator import RAGOrchestrator
from genreport.core.retrieval.embedding_service import EmbeddingService
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
        job_id: Optional[UUID] = None,
        cache_client: Optional[any] = None,
        enable_caching: bool = True,
        enable_structure_aware: bool = True,
    ) -> Dict[str, BaseFinancialAgent]:
        """Create all agents for specified jurisdiction with RAG orchestration.

        Args:
            jurisdiction: Jurisdiction code (HK, SG, AU)
            tenant_id: Tenant making the request
            user_id: User making the request
            db: Database session for retriever
            job_id: Optional job ID for agentic RAG caching (invalidated when source files change)
            cache_client: Optional Redis client for caching (default: auto-create)
            enable_caching: Enable Redis caching (default: True)
            enable_structure_aware: Enable structure-aware retrieval (default: True)

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

        # Create embedding service
        embedding_service = EmbeddingService()

        # Load document structure if available
        document_structure = None
        if enable_structure_aware:
            document_structure = AgentFactory._load_document_structure(jurisdiction)

        # Create Redis cache client if needed
        if enable_caching and cache_client is None:
            try:
                from genreport.core.database.redis_client import get_redis_client
                cache_client = get_redis_client()
                logger.info(
                    f"Created Redis cache client for jurisdiction {jurisdiction}"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to create Redis client, caching disabled: {e}"
                )
                cache_client = None
                enable_caching = False

        # Create RAG Orchestrator
        rag_orchestrator = RAGOrchestrator(
            db=db,
            jurisdiction=jurisdiction,
            tenant_id=tenant_id,
            user_id=user_id,
            embedding_service=embedding_service,
            document_structure=document_structure,
            cache_client=cache_client,
            enable_structure_aware=enable_structure_aware,
            enable_caching=enable_caching,
        )

        logger.info(
            f"Created RAG Orchestrator for {jurisdiction} "
            f"(caching={enable_caching}, structure_aware={document_structure is not None})"
        )

        # Lazy load market-specific agents
        if jurisdiction == "HK":
            return AgentFactory._create_hk_agents(
                market_config=market_config,
                rag_orchestrator=rag_orchestrator,
                tenant_id=tenant_id,
                user_id=user_id,
                job_id=job_id,
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
    def _load_document_structure(jurisdiction: str) -> Optional[Dict]:
        """Load document structure for jurisdiction.

        Args:
            jurisdiction: Jurisdiction code (HK, SG, AU)

        Returns:
            Document structure dict or None if not available
        """
        try:
            if jurisdiction == "HK":
                from markets.hk.knowledge_base.smefrs_structure import (
                    SME_FRS_STRUCTURE,
                )

                logger.info(
                    f"Loaded SME-FRS structure with {len(SME_FRS_STRUCTURE)} sections"
                )
                return SME_FRS_STRUCTURE
            elif jurisdiction == "SG":
                # Future: Load SG document structure
                logger.info("SG document structure not yet available")
                return None
            elif jurisdiction == "AU":
                # Future: Load AU document structure
                logger.info("AU document structure not yet available")
                return None
            else:
                logger.warning(f"No document structure loader for {jurisdiction}")
                return None
        except Exception as e:
            logger.warning(
                f"Failed to load document structure for {jurisdiction}: {e}"
            )
            return None

    @staticmethod
    def _create_hk_agents(
        market_config,
        rag_orchestrator: RAGOrchestrator,
        tenant_id: UUID,
        user_id: int,
        job_id: Optional[UUID] = None,
    ) -> Dict[str, BaseFinancialAgent]:
        """Create Hong Kong agents with RAG orchestration.

        Args:
            market_config: HK market configuration
            rag_orchestrator: RAGOrchestrator instance
            tenant_id: Tenant ID
            user_id: User ID
            job_id: Optional job ID for agentic RAG caching

        Returns:
            Dict of agent_type -> agent instance
        """
        # Lazy import to avoid loading all markets
        from markets.hk.agents.revenue_agent import HKRevenueAgent
        from markets.hk.agents.inventory_agent import HKInventoryAgent
        from markets.hk.agents.provisions_agent import HKProvisionsAgent

        # Create agent instances with RAG orchestrator and job_id
        agents = {
            "revenue": HKRevenueAgent(
                market_config=market_config,
                retriever=rag_orchestrator,
                tenant_id=tenant_id,
                user_id=user_id,
                job_id=job_id,
            ),
            "inventory": HKInventoryAgent(
                market_config=market_config,
                retriever=rag_orchestrator,
                tenant_id=tenant_id,
                user_id=user_id,
                job_id=job_id,
            ),
            "provisions": HKProvisionsAgent(
                market_config=market_config,
                retriever=rag_orchestrator,
                tenant_id=tenant_id,
                user_id=user_id,
                job_id=job_id,
            ),
        }

        logger.info(
            f"Created {len(agents)} HK agents with job_id={job_id} for agentic RAG caching"
        )

        return agents
