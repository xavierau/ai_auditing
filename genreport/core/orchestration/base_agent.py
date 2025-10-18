"""BaseFinancialAgent - Abstract base class for all financial disclosure agents.

This module defines the base class that all market-specific agents inherit from,
providing common functionality and enforcing a consistent interface.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List
from uuid import UUID

from genreport.core.orchestration.agent_models import AgentInput, AgentOutput, Source
from genreport.core.security.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


class BaseFinancialAgent(ABC):
    """Abstract base class for financial disclosure agents.

    All market-specific agents (HK, SG, AU) inherit from this class.
    Provides dependency injection for market config and retriever.
    """

    def __init__(
        self,
        market_config: Any,
        retriever: Any,
        tenant_id: UUID,
        user_id: int,
    ):
        """Initialize agent with dependencies.

        Args:
            market_config: Market-specific configuration
            retriever: Knowledge base retriever (SecureKBRetriever)
            tenant_id: Tenant making the request
            user_id: User making the request
        """
        self.market_config = market_config
        self.retriever = retriever
        self.tenant_id = tenant_id
        self.user_id = user_id

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Name of the agent (e.g., 'revenue_recognition').

        Returns:
            Agent name string
        """
        pass

    @property
    @abstractmethod
    def supported_jurisdictions(self) -> List[str]:
        """List of supported jurisdictions (e.g., ['HK', 'SG']).

        Returns:
            List of jurisdiction codes
        """
        pass

    @abstractmethod
    def process(self, agent_input: AgentInput) -> AgentOutput:
        """Process input and generate disclosure.

        This is the main method that subclasses implement with their
        market-specific DSPy logic.

        Args:
            agent_input: Input data for generation

        Returns:
            Generated disclosure with sources
        """
        pass

    @abstractmethod
    def validate_input(self, agent_input: AgentInput) -> bool:
        """Validate that input contains required data.

        Args:
            agent_input: Input data to validate

        Returns:
            True if valid, False otherwise
        """
        pass

    @abstractmethod
    def post_process(self, output: AgentOutput) -> AgentOutput:
        """Post-process agent output (add warnings, format, etc.).

        Args:
            output: Raw agent output

        Returns:
            Post-processed output
        """
        pass

    def validate_tenant(self, agent_input: AgentInput) -> None:
        """Validate that input tenant_id matches agent tenant_id.

        Args:
            agent_input: Input to validate

        Raises:
            ValueError: If tenant IDs don't match
        """
        if agent_input.tenant_id != self.tenant_id:
            raise ValueError(
                f"Tenant ID mismatch: expected {self.tenant_id}, "
                f"got {agent_input.tenant_id}"
            )

    def _fetch_context(self, query: str) -> List[Source]:
        """Fetch relevant context from knowledge base.

        Protected method available to subclasses for retrieval.

        Args:
            query: Search query for retrieval

        Returns:
            List of Source objects
        """
        if not query or not query.strip():
            return []

        try:
            # Call retriever (SecureKBRetriever)
            results = self.retriever.retrieve(query)

            # Convert retriever results to Source objects
            sources = []
            for result in results:
                source = Source(
                    document_id=result["document_id"],
                    chunk_id=result["chunk_id"],
                    relevance_score=result["score"],
                    snippet=result["text"],
                )
                sources.append(source)

            return sources

        except Exception as e:
            logger.error(f"Error fetching context: {e}")
            return []

    def _log_generation(
        self,
        agent_input: AgentInput,
        output: AgentOutput,
        duration_seconds: float,
    ) -> None:
        """Log agent generation event for audit trail.

        Protected method available to subclasses.

        Args:
            agent_input: Input that was processed
            output: Generated output
            duration_seconds: Time taken to generate
        """
        metadata = {
            "agent_name": self.agent_name,
            "project_id": agent_input.project_id,
            "confidence_score": output.confidence_score,
            "completeness_score": output.completeness_score,
            "duration_seconds": duration_seconds,
            "source_count": len(output.sources),
            "warning_count": len(output.warnings),
        }

        AuditLogger.log_event(
            db=None,  # Will be passed from orchestrator
            event_type="AGENT_GENERATION",
            action="GENERATE_DISCLOSURE",
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            resource_type="disclosure",
            resource_id=agent_input.project_id,
            metadata=metadata,
            status="SUCCESS",
        )
