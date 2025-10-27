"""Data models for RAG Orchestrator Agent.

This module defines Pydantic models for type-safe RAG orchestration:
- QueryIntent: Intent classification for queries
- RetrievalStrategy: Strategy selection options
- ContentType: Content type classification
- RAGQuery: Input query model
- RetrievalCandidate: Intermediate retrieval result
- ContextChunk: Final context chunk for agent consumption
- RAGResult: Complete orchestrator result
- StrategyExplanation: Debugging/transparency model

All models use Pydantic for validation and type safety.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Enums
# ============================================================================


class QueryIntent(str, Enum):
    """Query intent classification for accounting document retrieval.

    Different intents require different retrieval strategies:
    - TEMPLATE: Looking for copy-paste templates (→ structure-aware)
    - REQUIREMENT: Looking for disclosure requirements (→ hybrid)
    - EXAMPLE: Looking for illustrative examples (→ semantic/hybrid)
    - DEFINITION: Looking for term definitions (→ semantic)
    - GENERAL: General knowledge query (→ auto-select)
    """

    TEMPLATE = "template"
    REQUIREMENT = "requirement"
    EXAMPLE = "example"
    DEFINITION = "definition"
    GENERAL = "general"


class RetrievalStrategy(str, Enum):
    """Retrieval strategy selection.

    - AUTO: Auto-select based on query and intent
    - SEMANTIC: Pure semantic search (fast, good for simple queries)
    - STRUCTURE_AWARE: Structure-guided navigation (accurate for templates)
    - HYBRID: Semantic + structure combined (balanced, best for requirements)
    """

    AUTO = "auto"
    SEMANTIC = "semantic"
    STRUCTURE_AWARE = "structure_aware"
    HYBRID = "hybrid"


class ContentType(str, Enum):
    """Content type classification for knowledge base chunks.

    Used for re-ranking and filtering based on query intent.
    """

    TEMPLATE = "template"
    REQUIREMENT = "requirement"
    EXAMPLE = "example"
    DEFINITION = "definition"
    GUIDANCE = "guidance"
    DISCLOSURE = "disclosure"
    MEASUREMENT = "measurement"


# ============================================================================
# Input Models
# ============================================================================


class RAGQuery(BaseModel):
    """Input query for RAG orchestrator.

    Attributes:
        query_text: Natural language query (3-500 chars)
        top_k: Number of results to return (1-20, default: 5)
        intent: Optional explicit intent (auto-detect if None)
        filters: Optional filters (chunk_types, standards, sections)
        tenant_id: Tenant making the request (for isolation)
        user_id: User making the request (for audit)
        project_id: Optional project context
    """

    query_text: str = Field(
        ...,
        description="Natural language query",
        min_length=3,
        max_length=500,
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of results to return",
    )
    intent: Optional[QueryIntent] = Field(
        None,
        description="Explicit intent (auto-detect if None)",
    )
    filters: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional filters (chunk_types, standards, sections)",
    )
    tenant_id: UUID = Field(
        ...,
        description="Tenant ID for isolation",
    )
    user_id: int = Field(
        ...,
        description="User ID for audit logging",
    )
    project_id: Optional[int] = Field(
        None,
        description="Optional project context",
    )

    @field_validator("query_text")
    @classmethod
    def validate_query_not_empty(cls, v: str) -> str:
        """Ensure query has meaningful text (not just whitespace)."""
        if not v.strip():
            raise ValueError("query_text cannot be empty or whitespace")
        return v.strip()


# ============================================================================
# Intermediate Models
# ============================================================================


class RetrievalCandidate(BaseModel):
    """Intermediate retrieval candidate before final assembly.

    Used internally during retrieval pipeline for re-ranking and merging.

    Attributes:
        chunk_id: Database chunk ID
        content: Chunk text content
        similarity_score: Semantic similarity score (0-1)
        relevance_score: Final score after re-ranking (0-1)
        chunk_type: Content type classification
        section_number: Section number (e.g., "17.1")
        section_title: Section title
        page_num: Page number in source document
        document_title: Source document title
        standard: Accounting standard (e.g., "HKFRS 15")
        jurisdiction: Jurisdiction code (HK, SG, AU)
        metadata: Additional metadata (parent_section, cross_refs, etc.)
        is_merged: Whether chunk was merged from adjacent chunks
        merged_from: List of original chunk IDs if merged
    """

    chunk_id: int = Field(..., description="Database chunk ID")
    content: str = Field(..., description="Chunk text content")
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    chunk_type: ContentType = Field(..., description="Content type")
    section_number: Optional[str] = Field(None, description="Section number")
    section_title: Optional[str] = Field(None, description="Section title")
    page_num: Optional[int] = Field(None, description="Page number")
    document_title: str = Field(..., description="Source document title")
    standard: str = Field(..., description="Accounting standard")
    jurisdiction: str = Field(..., description="Jurisdiction code")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )
    is_merged: bool = Field(
        default=False,
        description="Whether merged from adjacent chunks",
    )
    merged_from: Optional[List[int]] = Field(
        None,
        description="Original chunk IDs if merged",
    )


# ============================================================================
# Output Models
# ============================================================================


class ContextChunk(BaseModel):
    """Final context chunk for agent consumption.

    This is the format that market-specific agents receive.
    Rich metadata helps agents understand context and source attribution.

    Attributes:
        content: Chunk text content
        source_reference: Human-readable source (e.g., 'HKFRS 15, Section 31, p.58')
        relevance_score: Final relevance score (0-1)
        chunk_type: Content type classification
        chunk_id: Database chunk ID for traceability
        document_id: Source KB document ID
        section_context: Section context (e.g., 'Property, Plant and Equipment')
        is_mandatory: Whether content represents mandatory requirements
        cross_references: Cross-references to related sections
    """

    content: str = Field(..., description="Chunk text content")
    source_reference: str = Field(
        ...,
        description="Human-readable source (e.g., 'HKFRS 15, Section 31, p.58')",
    )
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    chunk_type: ContentType = Field(..., description="Content type")
    chunk_id: int = Field(..., description="Database chunk ID for traceability")
    document_id: int = Field(..., description="Source KB document ID")
    section_context: Optional[str] = Field(
        None,
        description="Section context (e.g., 'Property, Plant and Equipment')",
    )
    is_mandatory: Optional[bool] = Field(
        None,
        description="Whether content represents mandatory requirements",
    )
    cross_references: List[str] = Field(
        default_factory=list,
        description="Cross-references to related sections",
    )


class RAGResult(BaseModel):
    """Final RAG orchestrator result.

    Contains assembled context chunks with comprehensive metadata for
    observability and debugging.

    Attributes:
        chunks: Retrieved and processed context chunks
        query_intent: Detected or provided query intent
        strategy_used: Retrieval strategy that was used
        total_candidates: Total candidates before re-ranking
        cache_hit: Whether result came from cache
        retrieval_time_ms: Total retrieval time in milliseconds
        metadata: Additional metadata (sections searched, filters applied, etc.)
    """

    chunks: List[ContextChunk] = Field(
        ...,
        description="Retrieved and processed context chunks",
    )
    query_intent: QueryIntent = Field(
        ...,
        description="Detected or provided query intent",
    )
    strategy_used: RetrievalStrategy = Field(
        ...,
        description="Retrieval strategy that was used",
    )
    total_candidates: int = Field(
        ...,
        description="Total candidates before re-ranking",
    )
    cache_hit: bool = Field(
        default=False,
        description="Whether result came from cache",
    )
    retrieval_time_ms: float = Field(
        ...,
        description="Total retrieval time in milliseconds",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (sections searched, filters, etc.)",
    )


class StrategyExplanation(BaseModel):
    """Explanation of retrieval strategy for debugging.

    Provides transparency into how the orchestrator made decisions.
    Useful for debugging poor results and understanding behavior.

    Attributes:
        query: Original query text
        detected_intent: Detected intent
        selected_strategy: Selected retrieval strategy
        rationale: Human-readable explanation of strategy selection
        sections_searched: Sections that were searched (if structure-aware)
        filters_applied: Filters that were applied
        alternative_strategies: Alternative strategies considered
    """

    query: str = Field(..., description="Original query text")
    detected_intent: QueryIntent = Field(..., description="Detected intent")
    selected_strategy: RetrievalStrategy = Field(..., description="Selected strategy")
    rationale: str = Field(
        ...,
        description="Human-readable explanation of strategy selection",
    )
    sections_searched: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Sections that were searched (if structure-aware)",
    )
    filters_applied: Dict[str, Any] = Field(
        default_factory=dict,
        description="Filters that were applied",
    )
    alternative_strategies: List[str] = Field(
        default_factory=list,
        description="Alternative strategies considered",
    )
