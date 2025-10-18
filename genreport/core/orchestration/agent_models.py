"""Agent Pydantic Models - Input/Output schemas for AI agents.

This module defines the data models for agent input and output,
ensuring type safety and validation across the agent system.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class Source(BaseModel):
    """Reference to a knowledge base document chunk.

    Provides traceability from generated disclosure back to source material.
    """

    document_id: UUID = Field(..., description="KB document UUID")
    chunk_id: UUID = Field(..., description="Document chunk UUID")
    relevance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Relevance score from retriever (0-1)",
    )
    snippet: str = Field(
        ...,
        min_length=1,
        description="Text snippet from the chunk",
    )


class AgentInput(BaseModel):
    """Input data for financial disclosure agents.

    Contains all data needed by agents to generate disclosures.
    Market-agnostic - no jurisdiction-specific fields.
    """

    tenant_id: UUID = Field(..., description="Tenant making the request")
    project_id: int = Field(..., gt=0, description="Project ID")
    trial_balance: Dict[str, Any] = Field(
        ...,
        description="Trial balance data",
    )
    general_ledger: Optional[Dict[str, Any]] = Field(
        None,
        description="General ledger entries (optional)",
    )
    accounting_policies: Optional[Dict[str, Any]] = Field(
        None,
        description="Entity accounting policies (optional)",
    )
    prior_year_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Prior year comparative data (optional)",
    )
    entity_info: Optional[Dict[str, Any]] = Field(
        None,
        description="Entity information (name, jurisdiction, etc.)",
    )


class AgentOutput(BaseModel):
    """Output from financial disclosure agents.

    Contains generated disclosure text with sources and quality metrics.
    """

    disclosure_text: str = Field(
        ...,
        min_length=1,
        description="Generated disclosure text",
    )
    sources: List[Source] = Field(
        default_factory=list,
        description="Knowledge base sources used",
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in generation quality (0-1)",
    )
    completeness_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Completeness of disclosure (0-1)",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Warnings about missing data or low confidence",
    )
