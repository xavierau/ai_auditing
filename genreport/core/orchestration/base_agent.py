"""BaseFinancialAgent - Abstract base class for all financial disclosure agents.

This module defines the base class that all market-specific agents inherit from,
providing common functionality and enforcing a consistent interface.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
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
        job_id: Optional[UUID] = None,
    ):
        """Initialize agent with dependencies.

        Args:
            market_config: Market-specific configuration
            retriever: Knowledge base retriever (SecureKBRetriever or RAGOrchestrator)
            tenant_id: Tenant making the request
            user_id: User making the request
            job_id: Optional job ID for caching (invalidated when source files change)
        """
        self.market_config = market_config
        self.retriever = retriever
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.job_id = job_id

        # Cache for agentic RAG results (job-level)
        self._agentic_cache: Dict[str, Any] = {}

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

    def _fetch_context(
        self, query: str, top_k: int = 5, use_agentic: bool = True
    ) -> List[Source]:
        """Fetch relevant context from knowledge base.

        Protected method available to subclasses for retrieval.
        Works with both RAGOrchestrator (new) and SecureKBRetriever (legacy).

        Args:
            query: Search query for retrieval
            top_k: Number of results to return (default: 5)
            use_agentic: If True and retriever is RAGOrchestrator, use AgenticRAGAgent
                        for autonomous reasoning. If False, use simple retrieval.

        Returns:
            List of Source objects
        """
        if not query or not query.strip():
            return []

        try:
            # Check if retriever is RAGOrchestrator (has retrieve method with RAGQuery)
            if hasattr(self.retriever, "retrieve") and hasattr(
                self.retriever, "query_understanding"
            ):
                # RAGOrchestrator path - can use agentic mode
                if use_agentic:
                    # Use AgenticRAGAgent for complex queries
                    agentic_result = self._fetch_with_agentic_rag(
                        query, query_type="context"
                    )

                    # Convert AgenticRAGResult.references to Source objects
                    sources = []
                    for ref in agentic_result.references:
                        # Extract document_id and chunk_id from ref if available
                        # For now, use ref_id as placeholder
                        source = Source(
                            document_id=0,  # Will be populated from reference metadata
                            chunk_id=ref.ref_id,
                            relevance_score=ref.relevance_score,
                            snippet=ref.content_preview,
                            source_reference=ref.source,
                        )
                        sources.append(source)

                    return sources
                else:
                    # Simple RAGOrchestrator retrieval (non-agentic)
                    from genreport.core.orchestration.rag_models import RAGQuery

                    rag_query = RAGQuery(
                        query_text=query,
                        top_k=top_k,
                        tenant_id=self.tenant_id,
                        user_id=self.user_id,
                    )

                    rag_result = self.retriever.retrieve(rag_query)

                    # Convert RAGResult.chunks to Source objects
                    sources = []
                    for chunk in rag_result.chunks:
                        source = Source(
                            document_id=chunk.document_id,
                            chunk_id=chunk.chunk_id,
                            relevance_score=chunk.relevance_score,
                            snippet=chunk.content,
                        )
                        sources.append(source)

                    return sources

            else:
                # Legacy SecureKBRetriever path
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
            logger.error(f"Error fetching context: {e}", exc_info=True)
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

    def _create_agentic_rag(self, max_iterations: int = 3) -> "AgenticRAGAgent":
        """Create AgenticRAGAgent on-demand using existing retriever.

        This method creates an agentic RAG agent that uses DSPy ReAct for
        autonomous reasoning, query rewriting, and iterative search.

        Args:
            max_iterations: Maximum ReAct iterations (default: 3)

        Returns:
            Configured AgenticRAGAgent instance

        Raises:
            ValueError: If retriever is not RAGOrchestrator
        """
        from genreport.core.orchestration.agentic_rag_agent import AgenticRAGAgent

        # Verify retriever is RAGOrchestrator
        if not (
            hasattr(self.retriever, "retrieve")
            and hasattr(self.retriever, "query_understanding")
        ):
            raise ValueError(
                "AgenticRAGAgent requires RAGOrchestrator as retriever. "
                "Current retriever does not support agentic mode."
            )

        logger.info(
            f"[{self.agent_name}] Creating AgenticRAGAgent with max_iterations={max_iterations}"
        )

        return AgenticRAGAgent(
            rag_orchestrator=self.retriever,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            max_iterations=max_iterations,
        )

    def _fetch_with_agentic_rag(
        self, query: str, query_type: str = "general", max_iterations: int = 3
    ) -> "AgenticRAGResult":
        """Fetch knowledge using AgenticRAGAgent with caching.

        Uses job-level caching to avoid redundant agentic reasoning for the same query.
        Cache is invalidated when source files/line items change (new job_id).

        Args:
            query: Query to process with agentic reasoning
            query_type: Type of query (template, requirement, context, general)
            max_iterations: Maximum ReAct iterations

        Returns:
            AgenticRAGResult with answer and references
        """
        from genreport.core.orchestration.agentic_rag_agent import AgenticRAGResult
        import hashlib

        # Generate cache key
        cache_key = hashlib.md5(
            f"{query_type}:{query}:{max_iterations}".encode()
        ).hexdigest()

        # Check cache
        if cache_key in self._agentic_cache:
            logger.info(
                f"[{self.agent_name}] Cache hit for agentic query: {query[:50]}..."
            )
            return self._agentic_cache[cache_key]

        logger.info(
            f"[{self.agent_name}] Cache miss - running agentic query: {query[:50]}..."
        )

        # Create agentic RAG agent
        agentic_agent = self._create_agentic_rag(max_iterations=max_iterations)

        # Execute agentic reasoning
        result = agentic_agent.forward(query)

        # Cache result (job-level)
        self._agentic_cache[cache_key] = result

        logger.info(
            f"[{self.agent_name}] Agentic query completed: "
            f"{result.total_chunks_retrieved} chunks, {len(result.references)} references"
        )

        return result

    def _fetch_template(self, disclosure_type: str) -> "AgenticRAGResult":
        """Fetch disclosure template using AgenticRAGAgent.

        Uses autonomous reasoning to find the best template for the disclosure type,
        including examples and formatting guidance.

        Args:
            disclosure_type: Type of disclosure (e.g., "HKFRS 15 revenue disclosure")

        Returns:
            AgenticRAGResult with template, examples, and formatting guidance

        Example:
            >>> template_result = self._fetch_template("HKFRS 15 revenue disclosure")
            >>> print(template_result.answer)  # Template with examples
            >>> for ref in template_result.references:
            ...     print(f"[{ref.ref_id}] {ref.source}")
        """
        query = (
            f"Find the disclosure template and formatting requirements for {disclosure_type}. "
            f"Include examples, structure guidance, and any mandatory sections required by the standard."
        )

        logger.info(f"[{self.agent_name}] Fetching template: {disclosure_type}")

        return self._fetch_with_agentic_rag(query, query_type="template")

    def _fetch_requirements(self, disclosure_type: str) -> "AgenticRAGResult":
        """Fetch accounting requirements using AgenticRAGAgent.

        Uses autonomous reasoning to find all relevant requirements, including
        mandatory disclosures, optional items, and presentation guidance.

        Args:
            disclosure_type: Type of disclosure (e.g., "HKFRS 15 revenue recognition")

        Returns:
            AgenticRAGResult with requirements, mandatory items, and guidance

        Example:
            >>> req_result = self._fetch_requirements("HKFRS 15 revenue recognition")
            >>> print(req_result.answer)  # All requirements
            >>> for ref in req_result.references:
            ...     print(f"[{ref.ref_id}] {ref.source}, p.{ref.page_number}")
        """
        query = (
            f"What are the accounting requirements for {disclosure_type}? "
            f"Include mandatory disclosures, optional items, presentation requirements, "
            f"and any specific conditions or thresholds that apply."
        )

        logger.info(f"[{self.agent_name}] Fetching requirements: {disclosure_type}")

        return self._fetch_with_agentic_rag(query, query_type="requirement")

    def clear_agentic_cache(self) -> None:
        """Clear the job-level agentic RAG cache.

        Call this when source files or line items change to invalidate cached results.
        Typically called when starting a new job or when input data is updated.
        """
        logger.info(f"[{self.agent_name}] Clearing agentic RAG cache")
        self._agentic_cache.clear()
