"""Tests for Agent Pydantic Models - Input/Output schemas for AI agents.

Following TDD methodology: These tests are written BEFORE implementation.
They define the expected behavior of agent models.
"""

import pytest
from uuid import uuid4
from pydantic import ValidationError

from genreport.core.orchestration.agent_models import (
    Source,
    AgentInput,
    AgentOutput,
)


class TestSource:
    """Test Source model - references to knowledge base documents."""

    def test_create_valid_source(self):
        """Create source with all required fields."""
        source = Source(
            document_id=uuid4(),
            chunk_id=uuid4(),
            relevance_score=0.85,
            snippet="Revenue is recognized when control transfers to customer.",
        )

        assert source.document_id is not None
        assert source.chunk_id is not None
        assert source.relevance_score == 0.85
        assert "Revenue is recognized" in source.snippet

    def test_relevance_score_validation(self):
        """Relevance score must be between 0 and 1."""
        # Valid scores
        Source(
            document_id=uuid4(),
            chunk_id=uuid4(),
            relevance_score=0.0,
            snippet="Test",
        )
        Source(
            document_id=uuid4(),
            chunk_id=uuid4(),
            relevance_score=1.0,
            snippet="Test",
        )

        # Invalid: > 1
        with pytest.raises(ValidationError):
            Source(
                document_id=uuid4(),
                chunk_id=uuid4(),
                relevance_score=1.5,
                snippet="Test",
            )

        # Invalid: < 0
        with pytest.raises(ValidationError):
            Source(
                document_id=uuid4(),
                chunk_id=uuid4(),
                relevance_score=-0.1,
                snippet="Test",
            )

    def test_snippet_required(self):
        """Snippet cannot be empty."""
        with pytest.raises(ValidationError):
            Source(
                document_id=uuid4(),
                chunk_id=uuid4(),
                relevance_score=0.8,
                snippet="",
            )

    def test_source_serialization(self):
        """Source can be serialized to dict."""
        doc_id = uuid4()
        chunk_id = uuid4()

        source = Source(
            document_id=doc_id,
            chunk_id=chunk_id,
            relevance_score=0.9,
            snippet="HKFRS 15 revenue recognition",
        )

        data = source.model_dump()

        assert data["document_id"] == doc_id
        assert data["chunk_id"] == chunk_id
        assert data["relevance_score"] == 0.9
        assert data["snippet"] == "HKFRS 15 revenue recognition"


class TestAgentInput:
    """Test AgentInput model - input data for agents."""

    def test_create_minimal_input(self):
        """Create input with only required fields."""
        tenant_id = uuid4()

        agent_input = AgentInput(
            tenant_id=tenant_id,
            project_id=1,
            trial_balance={"revenue": 1000000},
        )

        assert agent_input.tenant_id == tenant_id
        assert agent_input.project_id == 1
        assert agent_input.trial_balance == {"revenue": 1000000}
        assert agent_input.general_ledger is None
        assert agent_input.accounting_policies is None

    def test_create_complete_input(self):
        """Create input with all fields."""
        tenant_id = uuid4()

        agent_input = AgentInput(
            tenant_id=tenant_id,
            project_id=1,
            trial_balance={"revenue": 1000000},
            general_ledger={"entries": []},
            accounting_policies={"revenue_recognition": "point_in_time"},
            prior_year_data={"revenue": 900000},
            entity_info={"name": "ABC Ltd", "jurisdiction": "HK"},
        )

        assert agent_input.general_ledger is not None
        assert agent_input.accounting_policies is not None
        assert agent_input.prior_year_data is not None
        assert agent_input.entity_info["jurisdiction"] == "HK"

    def test_trial_balance_required(self):
        """Trial balance is required."""
        with pytest.raises(ValidationError):
            AgentInput(
                tenant_id=uuid4(),
                project_id=1,
            )

    def test_project_id_positive(self):
        """Project ID must be positive."""
        with pytest.raises(ValidationError):
            AgentInput(
                tenant_id=uuid4(),
                project_id=0,
                trial_balance={},
            )

        with pytest.raises(ValidationError):
            AgentInput(
                tenant_id=uuid4(),
                project_id=-1,
                trial_balance={},
            )


class TestAgentOutput:
    """Test AgentOutput model - output from agents."""

    def test_create_minimal_output(self):
        """Create output with only required fields."""
        output = AgentOutput(
            disclosure_text="Revenue recognition policy follows HKFRS 15.",
            sources=[],
            confidence_score=0.85,
            completeness_score=0.90,
        )

        assert "HKFRS 15" in output.disclosure_text
        assert output.sources == []
        assert output.confidence_score == 0.85
        assert output.completeness_score == 0.90
        assert output.warnings == []

    def test_create_complete_output(self):
        """Create output with all fields."""
        source = Source(
            document_id=uuid4(),
            chunk_id=uuid4(),
            relevance_score=0.9,
            snippet="HKFRS 15 guidance",
        )

        output = AgentOutput(
            disclosure_text="Revenue disclosure text",
            sources=[source],
            confidence_score=0.85,
            completeness_score=0.90,
            warnings=["Missing contract liability details"],
        )

        assert len(output.sources) == 1
        assert output.sources[0].relevance_score == 0.9
        assert len(output.warnings) == 1

    def test_confidence_score_validation(self):
        """Confidence score must be between 0 and 1."""
        # Valid
        AgentOutput(
            disclosure_text="Test",
            sources=[],
            confidence_score=0.0,
            completeness_score=0.8,
        )

        AgentOutput(
            disclosure_text="Test",
            sources=[],
            confidence_score=1.0,
            completeness_score=0.8,
        )

        # Invalid: > 1
        with pytest.raises(ValidationError):
            AgentOutput(
                disclosure_text="Test",
                sources=[],
                confidence_score=1.1,
                completeness_score=0.8,
            )

        # Invalid: < 0
        with pytest.raises(ValidationError):
            AgentOutput(
                disclosure_text="Test",
                sources=[],
                confidence_score=-0.1,
                completeness_score=0.8,
            )

    def test_completeness_score_validation(self):
        """Completeness score must be between 0 and 1."""
        # Valid
        AgentOutput(
            disclosure_text="Test",
            sources=[],
            confidence_score=0.8,
            completeness_score=0.0,
        )

        AgentOutput(
            disclosure_text="Test",
            sources=[],
            confidence_score=0.8,
            completeness_score=1.0,
        )

        # Invalid: > 1
        with pytest.raises(ValidationError):
            AgentOutput(
                disclosure_text="Test",
                sources=[],
                confidence_score=0.8,
                completeness_score=1.5,
            )

    def test_disclosure_text_not_empty(self):
        """Disclosure text cannot be empty."""
        with pytest.raises(ValidationError):
            AgentOutput(
                disclosure_text="",
                sources=[],
                confidence_score=0.8,
                completeness_score=0.9,
            )

    def test_output_serialization(self):
        """Output can be serialized to dict."""
        source = Source(
            document_id=uuid4(),
            chunk_id=uuid4(),
            relevance_score=0.88,
            snippet="Test snippet",
        )

        output = AgentOutput(
            disclosure_text="Test disclosure",
            sources=[source],
            confidence_score=0.75,
            completeness_score=0.82,
            warnings=["Warning 1"],
        )

        data = output.model_dump()

        assert data["disclosure_text"] == "Test disclosure"
        assert len(data["sources"]) == 1
        assert data["sources"][0]["relevance_score"] == 0.88
        assert data["confidence_score"] == 0.75
        assert data["completeness_score"] == 0.82
        assert data["warnings"] == ["Warning 1"]


class TestAgentModelIntegration:
    """Test integration between models."""

    def test_output_with_multiple_sources(self):
        """Output can contain multiple sources."""
        sources = [
            Source(
                document_id=uuid4(),
                chunk_id=uuid4(),
                relevance_score=0.9,
                snippet="Source 1",
            ),
            Source(
                document_id=uuid4(),
                chunk_id=uuid4(),
                relevance_score=0.85,
                snippet="Source 2",
            ),
            Source(
                document_id=uuid4(),
                chunk_id=uuid4(),
                relevance_score=0.8,
                snippet="Source 3",
            ),
        ]

        output = AgentOutput(
            disclosure_text="Multi-source disclosure",
            sources=sources,
            confidence_score=0.88,
            completeness_score=0.92,
        )

        assert len(output.sources) == 3
        assert all(isinstance(s, Source) for s in output.sources)

    def test_round_trip_serialization(self):
        """Models can be serialized and deserialized."""
        # Create output
        original = AgentOutput(
            disclosure_text="Test disclosure",
            sources=[
                Source(
                    document_id=uuid4(),
                    chunk_id=uuid4(),
                    relevance_score=0.9,
                    snippet="Test",
                )
            ],
            confidence_score=0.85,
            completeness_score=0.90,
            warnings=["Warning"],
        )

        # Serialize to dict
        data = original.model_dump()

        # Deserialize back
        restored = AgentOutput(**data)

        assert restored.disclosure_text == original.disclosure_text
        assert len(restored.sources) == len(original.sources)
        assert restored.confidence_score == original.confidence_score
        assert restored.completeness_score == original.completeness_score
        assert restored.warnings == original.warnings
