"""Agentic RAG Agent using DSPy ReAct Pattern.

This module implements a true agentic RAG system that uses DSPy's built-in
ReAct module for autonomous reasoning, query rewriting, and iterative search.

Key Features:
- THINK: DSPy automatically reasons about what information is needed
- ACT: Executes retrieval using defined tools
- OBSERVE: Reviews results and assesses quality
- DECIDE: Determines if more searches are needed
- SYNTHESIZE: Builds final answer with proper references

The agent uses two tools:
1. search_knowledge_base: General semantic/hybrid search
2. search_by_section: Structure-aware search within specific sections
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
import logging
import re

import dspy
from pydantic import BaseModel, Field

from genreport.core.orchestration.rag_orchestrator import RAGOrchestrator
from genreport.core.orchestration.rag_models import RAGQuery, RetrievalStrategy

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================


class Reference(BaseModel):
    """Structured reference to source material."""

    ref_id: int = Field(..., description="Reference number [1], [2], etc.")
    source: str = Field(
        ..., description="Source reference (e.g., 'HKFRS 15, Section 31, p.58')"
    )
    page_number: Optional[int] = Field(None, description="Page number in source document")
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    content_preview: str = Field(..., description="Preview of content")


class AgenticRAGResult(BaseModel):
    """Final result from agentic RAG with DSPy ReAct.

    Note: For detailed monitoring (traces, latency, costs), use LangSmith, LangFuse, or MLFlow.
    This model focuses on the essential outputs: answer with proper citations.
    """

    query: str = Field(..., description="Original user query")
    answer: str = Field(..., description="Synthesized answer from ReAct agent")
    references: List[Reference] = Field(..., description="Source references with [1], [2] markers")
    total_chunks_retrieved: int = Field(
        ..., description="Total chunks retrieved across all searches"
    )
    unique_chunks: int = Field(..., description="Unique chunks after deduplication")


# ============================================================================
# DSPy ReAct Agent
# ============================================================================


class AgenticRAGAgent(dspy.Module):
    """ReAct Agent using DSPy's built-in ReAct module.

    DSPy automatically handles:
    - THINK: Reasoning about next action
    - ACT: Calling tools (search_knowledge_base, search_by_section)
    - OBSERVE: Reviewing tool outputs
    - DECIDE: Whether to continue or finish

    Example:
        >>> orchestrator = RAGOrchestrator(...)
        >>> agent = AgenticRAGAgent(
        ...     rag_orchestrator=orchestrator,
        ...     tenant_id=tenant_id,
        ...     user_id=user_id,
        ...     max_iterations=3,
        ... )
        >>> result = agent.forward("What are HKFRS 15 revenue recognition requirements?")
        >>> print(result.answer)
        >>> print(f"References: {len(result.references)}")
    """

    def __init__(
        self,
        rag_orchestrator: RAGOrchestrator,
        tenant_id: UUID,
        user_id: int,
        max_iterations: int = 3,
    ):
        """Initialize the agentic RAG agent.

        Args:
            rag_orchestrator: RAG orchestrator for retrieval
            tenant_id: Tenant making the request
            user_id: User making the request
            max_iterations: Maximum ReAct iterations (default: 3)
        """
        super().__init__()
        self.rag_orchestrator = rag_orchestrator
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.max_iterations = max_iterations

        # Track all chunks retrieved for final result
        self._all_chunks = []

        # Define tools for the agent
        tools = [
            dspy.Tool(
                func=self._retrieve_knowledge,
                name="search_knowledge_base",
                desc=(
                    "Search the accounting standards knowledge base. "
                    "Use this when you need specific information about "
                    "accounting standards, requirements, or policy templates. "
                    "Args: query (str) - search query. "
                    "Returns: relevant chunks with sources and relevance scores."
                ),
            ),
            dspy.Tool(
                func=self._retrieve_by_section,
                name="search_by_section",
                desc=(
                    "Search within a specific section of the standards. "
                    "Use this when you know which section to look in "
                    "(e.g., 'Section 23 Revenue', 'Appendix 2'). "
                    "Args: section_name (str), query (str). "
                    "Returns: relevant chunks from that section."
                ),
            ),
        ]

        # DSPy ReAct handles the entire reasoning loop
        self.react_agent = dspy.ReAct(
            signature="question -> answer",
            tools=tools,
            max_iters=self.max_iterations,
        )

    def _retrieve_knowledge(self, query: str) -> str:
        """Tool function: Search knowledge base.

        Returns formatted results for the agent to observe.

        Args:
            query: Search query

        Returns:
            Formatted search results with sources and relevance scores
        """
        logger.info(f"[Tool: search_knowledge_base] Query: {query}")

        rag_query = RAGQuery(
            query_text=query,
            top_k=5,
            strategy=RetrievalStrategy.HYBRID,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
        )

        result = self.rag_orchestrator.retrieve(rag_query)

        # Track chunks for final result
        self._all_chunks.extend(result.chunks)

        # Format results for agent observation
        if not result.chunks:
            return "No results found."

        formatted = []
        for i, chunk in enumerate(result.chunks[:5], 1):
            formatted.append(
                f"[{i}] {chunk.source_reference}\n"
                f"Relevance: {chunk.relevance_score:.3f}\n"
                f"Content: {chunk.content[:300]}...\n"
            )

        logger.info(f"[Tool: search_knowledge_base] Retrieved {len(result.chunks)} chunks")
        return "\n".join(formatted)

    def _retrieve_by_section(self, section_name: str, query: str) -> str:
        """Tool function: Search within specific section.

        Returns formatted results from the specified section.

        Args:
            section_name: Section to search (e.g., "Section 23", "Appendix 2")
            query: Search query

        Returns:
            Formatted search results from the section
        """
        logger.info(
            f"[Tool: search_by_section] Section: {section_name}, Query: {query}"
        )

        rag_query = RAGQuery(
            query_text=f"{section_name} {query}",  # Include section in query
            top_k=3,
            strategy=RetrievalStrategy.STRUCTURE_AWARE,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
        )

        result = self.rag_orchestrator.retrieve(rag_query)

        # Track chunks for final result
        self._all_chunks.extend(result.chunks)

        if not result.chunks:
            return f"No results found in section '{section_name}'."

        formatted = []
        for i, chunk in enumerate(result.chunks[:3], 1):
            formatted.append(
                f"[{i}] {chunk.source_reference}\n"
                f"Content: {chunk.content[:200]}...\n"
            )

        logger.info(
            f"[Tool: search_by_section] Retrieved {len(result.chunks)} chunks from section"
        )
        return "\n".join(formatted)

    def forward(self, query: str) -> AgenticRAGResult:
        """Execute ReAct loop for query answering.

        DSPy ReAct automatically handles:
        - THINK: Reasoning about next action
        - ACT: Calling tools (search_knowledge_base, search_by_section)
        - OBSERVE: Reviewing tool outputs
        - DECIDE: Whether to continue or finish

        Note: For detailed monitoring (traces, latency, costs), integrate LangSmith/LangFuse/MLFlow.

        Args:
            query: User query

        Returns:
            AgenticRAGResult with answer and source references
        """
        logger.info(f"[AgenticRAGAgent] Starting ReAct loop for query: {query}")

        # Reset chunk tracking
        self._all_chunks = []

        try:
            # DSPy ReAct handles the entire loop automatically
            result = self.react_agent(question=query)

            # Extract answer (DSPy ReAct returns a Prediction object)
            answer = result.answer if hasattr(result, "answer") else str(result)

            # Deduplicate chunks
            unique_chunks = self._deduplicate_chunks(self._all_chunks)

            # Build references from all retrieved chunks
            # The chunks are numbered [1], [2], [3] in order of retrieval
            references = self._build_references(unique_chunks)

            logger.info(
                f"[AgenticRAGAgent] Completed: "
                f"{len(self._all_chunks)} total chunks, {len(unique_chunks)} unique, "
                f"{len(references)} references"
            )

            return AgenticRAGResult(
                query=query,
                answer=answer,
                references=references,
                total_chunks_retrieved=len(self._all_chunks),
                unique_chunks=len(unique_chunks),
            )

        except Exception as e:
            logger.error(f"[AgenticRAGAgent] Error during ReAct loop: {e}", exc_info=True)
            # Return fallback result
            return AgenticRAGResult(
                query=query,
                answer=f"Error during retrieval: {str(e)}",
                references=[],
                total_chunks_retrieved=0,
                unique_chunks=0,
            )

    def _build_references(self, chunks: List[Any]) -> List[Reference]:
        """Build references from retrieved chunks.

        Creates a numbered reference list [1], [2], [3], ... from all unique chunks
        retrieved during the ReAct loop. These can be cited in the answer.

        Extracts page numbers from source_reference if present (e.g., 'HKFRS 15, Section 31, p.58').

        Args:
            chunks: Unique chunks retrieved (after deduplication)

        Returns:
            List of Reference objects numbered sequentially with page numbers
        """
        references = []
        for i, chunk in enumerate(chunks, 1):
            # Extract page number from source_reference if present
            page_num = None
            source_ref = chunk.source_reference

            # Try to extract page number from patterns like "p.58", "page 58", "pp. 58-60"
            page_match = re.search(r'p\.?\s*(\d+)', source_ref, re.IGNORECASE)
            if page_match:
                page_num = int(page_match.group(1))

            references.append(
                Reference(
                    ref_id=i,
                    source=source_ref,
                    page_number=page_num,
                    relevance_score=chunk.relevance_score,
                    content_preview=chunk.content[:150],
                )
            )
        return references

    def _deduplicate_chunks(self, chunks: List[Any]) -> List[Any]:
        """Remove duplicate chunks by chunk_id.

        Args:
            chunks: List of chunks

        Returns:
            Deduplicated list of chunks
        """
        seen = set()
        unique = []
        for chunk in chunks:
            if chunk.chunk_id not in seen:
                seen.add(chunk.chunk_id)
                unique.append(chunk)
        return unique
