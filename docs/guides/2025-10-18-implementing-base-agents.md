# Implementation Guide: Base Agent Infrastructure

**Date:** 2025-10-18
**Sprint:** Sprint 4 Phase 2
**Estimated Time:** 18 hours (over 2-3 days)
**Developer Level:** Intermediate to Advanced

---

## Overview

This guide provides step-by-step instructions for implementing the base agent infrastructure for Sprint 4. Follow the phases in order, writing tests first (TDD approach) and verifying each component before proceeding.

**Prerequisites:**
- Sprint 1 (Foundation) complete
- Sprint 2 (Excel Processing) complete
- Sprint 3 (Knowledge Base) complete
- Sprint 4 Phase 1 (Security) complete
- Familiarity with Abstract Base Classes (ABC)
- Understanding of Pydantic validation
- Knowledge of dependency injection pattern

**Architecture Reference:** See `docs/architecture/2025-10-18-sprint4-base-agent-infrastructure.md`

---

## Phase 2.1: Pydantic Models (2 hours)

### Step 1: Create Agent Models File

Create the file structure:

```bash
cd /Users/xavierau/Code/python/new_ai_auditing
touch genreport/core/orchestration/agent_models.py
touch tests/core/orchestration/__init__.py
touch tests/core/orchestration/test_agent_models.py
```

### Step 2: Write Model Tests First (TDD)

**File:** `tests/core/orchestration/test_agent_models.py`

```python
"""Tests for agent Pydantic models."""

import pytest
from datetime import datetime, date
from uuid import uuid4, UUID

from genreport.core.orchestration.agent_models import (
    AgentInput,
    AgentOutput,
    Source,
)


class TestAgentInput:
    """Tests for AgentInput model."""

    def test_valid_input(self):
        """Test valid AgentInput creation."""
        input_data = AgentInput(
            project_id=1,
            tenant_id=uuid4(),
            jurisdiction="HK",
            accounting_standard="HKFRS",
            financial_year_end=date(2024, 12, 31),
            trial_balance={"accounts": []},
        )

        assert input_data.project_id == 1
        assert input_data.jurisdiction == "HK"
        assert input_data.accounting_standard == "HKFRS"
        assert input_data.trial_balance is not None

    def test_invalid_jurisdiction(self):
        """Test that invalid jurisdiction raises error."""
        with pytest.raises(ValueError, match="Unsupported jurisdiction"):
            AgentInput(
                project_id=1,
                tenant_id=uuid4(),
                jurisdiction="INVALID",
                accounting_standard="HKFRS",
                financial_year_end=date(2024, 12, 31),
            )

    def test_negative_project_id(self):
        """Test that negative project_id raises error."""
        with pytest.raises(ValueError):
            AgentInput(
                project_id=-1,
                tenant_id=uuid4(),
                jurisdiction="HK",
                accounting_standard="HKFRS",
                financial_year_end=date(2024, 12, 31),
            )

    def test_optional_fields(self):
        """Test that optional fields work correctly."""
        input_data = AgentInput(
            project_id=1,
            tenant_id=uuid4(),
            jurisdiction="HK",
            accounting_standard="HKFRS",
            financial_year_end=date(2024, 12, 31),
            # All financial data fields are optional
        )

        assert input_data.trial_balance is None
        assert input_data.general_ledger is None
        assert input_data.prior_year_data is None

    def test_extra_fields_allowed(self):
        """Test that extra fields are allowed for agent-specific data."""
        input_data = AgentInput(
            project_id=1,
            tenant_id=uuid4(),
            jurisdiction="HK",
            accounting_standard="HKFRS",
            financial_year_end=date(2024, 12, 31),
            # Extra field for lease-specific data
            lease_contracts=[{"id": 1, "amount": 10000}],
        )

        # Should not raise error
        assert hasattr(input_data, "lease_contracts")


class TestSource:
    """Tests for Source model."""

    def test_valid_source(self):
        """Test valid Source creation."""
        source = Source(
            document_id=123,
            chunk_id=456,
            relevance_score=0.95,
            snippet="Revenue is recognized when...",
            standard="HKFRS 15",
            section="15.31",
        )

        assert source.document_id == 123
        assert source.chunk_id == 456
        assert source.relevance_score == 0.95

    def test_citation_generation(self):
        """Test citation property generates correctly."""
        source = Source(
            document_id=123,
            chunk_id=456,
            relevance_score=0.95,
            snippet="Test snippet",
            standard="HKFRS 15",
            section="15.31",
        )

        assert source.citation == "HKFRS 15, Section 15.31"

    def test_citation_without_section(self):
        """Test citation when section is missing."""
        source = Source(
            document_id=123,
            chunk_id=456,
            relevance_score=0.95,
            snippet="Test snippet",
            standard="HKFRS 15",
        )

        assert source.citation == "HKFRS 15"

    def test_invalid_relevance_score(self):
        """Test that relevance_score outside 0-1 raises error."""
        with pytest.raises(ValueError):
            Source(
                document_id=123,
                chunk_id=456,
                relevance_score=1.5,  # Invalid
                snippet="Test snippet",
            )


class TestAgentOutput:
    """Tests for AgentOutput model."""

    def test_valid_output(self):
        """Test valid AgentOutput creation."""
        output = AgentOutput(
            disclosure_text="The Group recognized revenue of HK$10M...",
            section="revenue_recognition",
            completeness_score=0.95,
            confidence_score=0.92,
            agent_name="HKRevenueAgent",
            processing_time_ms=2340.5,
        )

        assert output.disclosure_text is not None
        assert output.section == "revenue_recognition"
        assert 0.0 <= output.completeness_score <= 1.0
        assert 0.0 <= output.confidence_score <= 1.0

    def test_empty_disclosure_text_fails(self):
        """Test that empty disclosure_text raises error."""
        with pytest.raises(ValueError):
            AgentOutput(
                disclosure_text="",  # Invalid
                section="revenue",
                agent_name="TestAgent",
                processing_time_ms=100.0,
            )

    def test_invalid_completeness_score(self):
        """Test that completeness_score outside 0-1 raises error."""
        with pytest.raises(ValueError):
            AgentOutput(
                disclosure_text="Test disclosure",
                section="revenue",
                completeness_score=1.5,  # Invalid
                agent_name="TestAgent",
                processing_time_ms=100.0,
            )

    def test_negative_processing_time(self):
        """Test that negative processing_time raises error."""
        with pytest.raises(ValueError):
            AgentOutput(
                disclosure_text="Test disclosure",
                section="revenue",
                processing_time_ms=-100.0,  # Invalid
                agent_name="TestAgent",
            )

    def test_default_values(self):
        """Test that default values are set correctly."""
        output = AgentOutput(
            disclosure_text="Test disclosure",
            section="revenue",
            agent_name="TestAgent",
            processing_time_ms=100.0,
        )

        assert output.completeness_score == 0.0
        assert output.confidence_score == 0.0
        assert output.pii_detected is False
        assert output.context_validated is False
        assert output.sources == []
        assert output.warnings == []

    def test_serialization(self):
        """Test that model serializes to JSON correctly."""
        output = AgentOutput(
            disclosure_text="Test disclosure",
            section="revenue",
            agent_name="TestAgent",
            processing_time_ms=100.0,
            sources=[
                Source(
                    document_id=123,
                    chunk_id=456,
                    relevance_score=0.95,
                    snippet="Test snippet",
                    standard="HKFRS 15",
                )
            ],
        )

        # Should serialize without error
        json_data = output.model_dump_json()
        assert json_data is not None

        # Should deserialize back
        deserialized = AgentOutput.model_validate_json(json_data)
        assert deserialized.disclosure_text == output.disclosure_text
```

### Step 3: Implement Pydantic Models

**File:** `genreport/core/orchestration/agent_models.py`

```python
"""Agent Pydantic models for type-safe input/output."""

from datetime import datetime, date
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, computed_field, ConfigDict


class AgentInput(BaseModel):
    """Input data for agent processing.

    This model defines the contract for data passed to agents.
    Different agents may require different subsets of this data.
    """

    # Financial Data (ALL OPTIONAL - different agents need different data)
    trial_balance: Optional[Dict[str, Any]] = Field(default=None)
    general_ledger: Optional[Dict[str, Any]] = Field(default=None)
    prior_year_data: Optional[Dict[str, Any]] = Field(default=None)
    accounting_policies: Optional[Dict[str, Any]] = Field(default=None)
    relationship_map: Optional[Dict[str, Any]] = Field(default=None)

    # Project Metadata (REQUIRED)
    project_id: int = Field(gt=0, description="Project ID")
    tenant_id: UUID = Field(description="Tenant UUID for isolation")
    jurisdiction: str = Field(
        pattern=r"^(HK|SG|AU)$", description="Jurisdiction code"
    )
    accounting_standard: str = Field(description="Accounting standard (HKFRS, SFRS, etc.)")
    financial_year_end: date = Field(description="Financial year end date")

    # Entity Information (OPTIONAL)
    entity_type: Optional[str] = Field(default=None, description="SME, Listed, Private")
    revenue: Optional[float] = Field(default=None, ge=0, description="Annual revenue")
    assets: Optional[float] = Field(default=None, ge=0, description="Total assets")
    employees: Optional[int] = Field(default=None, ge=0, description="Number of employees")

    # Allow additional fields for agent-specific data
    model_config = ConfigDict(extra="allow")

    @field_validator("jurisdiction")
    @classmethod
    def validate_jurisdiction(cls, v: str) -> str:
        """Ensure jurisdiction is supported."""
        from genreport.core.utils.market_config import validate_jurisdiction

        if not validate_jurisdiction(v):
            raise ValueError(f"Unsupported jurisdiction: {v}")
        return v


class Source(BaseModel):
    """Reference to knowledge base source."""

    document_id: int = Field(gt=0, description="KB document ID")
    chunk_id: int = Field(gt=0, description="KB chunk ID")
    relevance_score: float = Field(
        ge=0.0, le=1.0, description="Relevance score from retrieval"
    )
    snippet: str = Field(max_length=500, description="Text snippet from source")
    standard: Optional[str] = Field(
        default=None, description="Standard reference (e.g., HKFRS 15)"
    )
    section: Optional[str] = Field(
        default=None, description="Section reference (e.g., 15.1.2)"
    )

    @computed_field
    @property
    def citation(self) -> str:
        """Generate formatted citation.

        Returns:
            Formatted citation string
        """
        if self.standard and self.section:
            return f"{self.standard}, Section {self.section}"
        elif self.standard:
            return self.standard
        else:
            return f"Document {self.document_id}"


class AgentOutput(BaseModel):
    """Output from agent processing."""

    # Generated Content
    disclosure_text: str = Field(min_length=1, description="Generated disclosure text")
    section: str = Field(description="Disclosure section (revenue, ppe, leases, etc.)")

    # Quality Metrics
    completeness_score: float = Field(
        ge=0.0,
        le=1.0,
        default=0.0,
        description="Completeness score (0.0 to 1.0)"
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        default=0.0,
        description="Confidence score (0.0 to 1.0)"
    )

    # Source Attribution
    sources: List[Source] = Field(
        default_factory=list, description="Knowledge base sources used"
    )
    standards_used: List[str] = Field(
        default_factory=list, description="Accounting standards referenced"
    )

    # Security & Compliance
    pii_detected: bool = Field(default=False, description="PII found and redacted")
    pii_types: List[str] = Field(
        default_factory=list, description="Types of PII detected"
    )
    context_validated: bool = Field(
        default=False, description="Context passed validation"
    )

    # Warnings & Recommendations
    warnings: List[str] = Field(
        default_factory=list, description="Warnings about disclosure"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Recommendations for improvement"
    )

    # Metadata
    agent_name: str = Field(description="Name of agent that generated output")
    processing_time_ms: float = Field(ge=0.0, description="Processing time in milliseconds")
    generated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Generation timestamp"
    )

    # Model configuration
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "disclosure_text": "The Group recognized revenue of HK$10.5M...",
                "section": "revenue_recognition",
                "completeness_score": 0.95,
                "confidence_score": 0.92,
                "sources": [
                    {
                        "document_id": 123,
                        "chunk_id": 456,
                        "relevance_score": 0.98,
                        "snippet": "Revenue is recognized when control transfers...",
                        "standard": "HKFRS 15",
                        "section": "15.31",
                    }
                ],
                "standards_used": ["HKFRS 15"],
                "pii_detected": False,
                "context_validated": True,
                "agent_name": "HKRevenueAgent",
                "processing_time_ms": 2340.5,
            }
        }
    )

    @field_validator("completeness_score", "confidence_score")
    @classmethod
    def validate_score(cls, v: float) -> float:
        """Ensure scores are valid percentages."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Score must be between 0.0 and 1.0, got {v}")
        return v
```

### Step 4: Run Tests

```bash
# Run model tests
pytest tests/core/orchestration/test_agent_models.py -v

# Expected: All tests pass
```

**Checkpoint:** All Pydantic model tests should pass before proceeding.

---

## Phase 2.2: BaseFinancialAgent (6 hours)

### Step 5: Write Base Agent Tests First (TDD)

**File:** `tests/core/orchestration/test_base_agent.py`

```python
"""Tests for BaseFinancialAgent abstract class."""

import pytest
from datetime import date
from uuid import uuid4
from unittest.mock import Mock, patch, MagicMock

from genreport.core.orchestration.base_agent import BaseFinancialAgent
from genreport.core.orchestration.agent_models import AgentInput, AgentOutput
from genreport.core.security.context_validator import CrossTenantDataError


# Mock agent for testing abstract base class
class MockFinancialAgent(BaseFinancialAgent):
    """Mock agent for testing base class functionality."""

    @property
    def agent_name(self) -> str:
        return "MockAgent"

    @property
    def disclosure_section(self) -> str:
        return "mock_section"

    @property
    def supported_standards(self) -> list[str]:
        return ["MOCK-STD"]

    def validate_input(self, context: AgentInput) -> bool:
        """Simple validation: check trial_balance exists."""
        return context.trial_balance is not None

    def process(self, context: AgentInput) -> AgentOutput:
        """Mock processing."""
        return AgentOutput(
            disclosure_text="Mock disclosure text",
            section=self.disclosure_section,
            completeness_score=0.9,
            confidence_score=0.85,
            agent_name=self.agent_name,
            processing_time_ms=100.0,
        )

    def post_process(self, output: AgentOutput) -> AgentOutput:
        """Mock post-processing."""
        output.warnings.append("This is a mock warning")
        return output


@pytest.fixture
def mock_market_config():
    """Mock market configuration."""
    config = Mock()
    config.currency = "HKD"
    config.currency_symbol = "HK$"
    config.format_currency = Mock(return_value="HK$ 1,000.00")
    config.format_date = Mock(return_value="31/12/2024")
    return config


@pytest.fixture
def mock_retriever():
    """Mock SecureKBRetriever."""
    retriever = Mock()
    retriever.retrieve = Mock(return_value=[
        {
            "chunk_id": 1,
            "content": "Revenue recognition...",
            "relevance_score": 0.95,
        }
    ])
    return retriever


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock()


@pytest.fixture
def mock_agent(mock_market_config, mock_retriever, mock_db):
    """Create mock agent for testing."""
    tenant_id = uuid4()
    user_id = 1

    agent = MockFinancialAgent(
        market_config=mock_market_config,
        retriever=mock_retriever,
        tenant_id=tenant_id,
        user_id=user_id,
        db=mock_db,
    )

    return agent


@pytest.fixture
def valid_context():
    """Create valid AgentInput."""
    return AgentInput(
        project_id=1,
        tenant_id=uuid4(),
        jurisdiction="HK",
        accounting_standard="HKFRS",
        financial_year_end=date(2024, 12, 31),
        trial_balance={"accounts": []},
    )


class TestBaseFinancialAgent:
    """Tests for BaseFinancialAgent."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that abstract class cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseFinancialAgent(
                market_config=Mock(),
                retriever=Mock(),
                tenant_id=uuid4(),
                user_id=1,
                db=Mock(),
            )

    def test_mock_agent_creation(self, mock_agent):
        """Test that mock agent can be created."""
        assert mock_agent.agent_name == "MockAgent"
        assert mock_agent.disclosure_section == "mock_section"
        assert "MOCK-STD" in mock_agent.supported_standards

    def test_fetch_context(self, mock_agent, mock_retriever):
        """Test _fetch_context calls retriever correctly."""
        results = mock_agent._fetch_context("revenue recognition", top_k=5)

        mock_retriever.retrieve.assert_called_once_with(
            query="revenue recognition",
            top_k=5,
        )
        assert len(results) > 0

    @patch("genreport.core.orchestration.base_agent.ContextValidator")
    def test_validate_context_success(self, mock_validator_class, mock_agent):
        """Test _validate_context succeeds with valid data."""
        # Setup mock validator to return True
        mock_validator = Mock()
        mock_validator.validate.return_value = True
        mock_validator_class.return_value = mock_validator

        context = {"trial_balance": {"tenant_id": mock_agent.tenant_id}}

        # Should not raise
        mock_agent._validate_context(context)

        mock_validator.validate.assert_called_once_with(context)

    @patch("genreport.core.orchestration.base_agent.ContextValidator")
    def test_validate_context_failure(self, mock_validator_class, mock_agent):
        """Test _validate_context raises on cross-tenant data."""
        # Setup mock validator to raise
        mock_validator = Mock()
        mock_validator.validate.side_effect = CrossTenantDataError("Cross-tenant data detected")
        mock_validator_class.return_value = mock_validator

        context = {"trial_balance": {"tenant_id": uuid4()}}  # Wrong tenant

        with pytest.raises(CrossTenantDataError):
            mock_agent._validate_context(context)

    def test_scan_for_pii(self, mock_agent):
        """Test _scan_for_pii detects PII."""
        text = "Contact john@example.com or +852 1234 5678"

        findings = mock_agent._scan_for_pii(text)

        # Should detect email and phone
        assert "email" in findings
        assert "phone_hk" in findings

    def test_redact_pii(self, mock_agent):
        """Test _redact_pii removes PII."""
        text = "Contact john@example.com or +852 1234 5678"

        redacted = mock_agent._redact_pii(text)

        # Should not contain original PII
        assert "john@example.com" not in redacted
        assert "+852 1234 5678" not in redacted

    def test_format_currency(self, mock_agent, mock_market_config):
        """Test _format_currency delegates to market config."""
        result = mock_agent._format_currency(1000.0)

        mock_market_config.format_currency.assert_called_once_with(1000.0)
        assert result == "HK$ 1,000.00"

    def test_format_date(self, mock_agent, mock_market_config):
        """Test _format_date delegates to market config."""
        result = mock_agent._format_date("2024-12-31")

        mock_market_config.format_date.assert_called_once_with("2024-12-31")
        assert result == "31/12/2024"

    @patch("genreport.core.orchestration.base_agent.AuditLogger")
    def test_log_generation(self, mock_audit_logger, mock_agent):
        """Test _log_generation creates audit log."""
        output = AgentOutput(
            disclosure_text="Test disclosure",
            section="revenue",
            completeness_score=0.95,
            agent_name="MockAgent",
            processing_time_ms=100.0,
        )

        mock_agent._log_generation("revenue", output)

        mock_audit_logger.log_event.assert_called_once()
        call_kwargs = mock_audit_logger.log_event.call_args[1]
        assert call_kwargs["event_type"] == "REPORT_GENERATION"
        assert call_kwargs["action"] == "GENERATE_SECTION"
        assert call_kwargs["tenant_id"] == mock_agent.tenant_id

    @patch("genreport.core.orchestration.base_agent.ContextValidator")
    def test_generate_full_pipeline(self, mock_validator_class, mock_agent, valid_context):
        """Test generate() orchestrates full pipeline correctly."""
        # Setup mocks
        mock_validator = Mock()
        mock_validator.validate.return_value = True
        mock_validator_class.return_value = mock_validator

        # Call generate
        output = mock_agent.generate(valid_context)

        # Verify pipeline execution
        assert output.disclosure_text == "Mock disclosure text"
        assert output.context_validated is True
        assert len(output.warnings) > 0  # post_process adds warning

    def test_generate_invalid_input(self, mock_agent):
        """Test generate() raises on invalid input."""
        invalid_context = AgentInput(
            project_id=1,
            tenant_id=uuid4(),
            jurisdiction="HK",
            accounting_standard="HKFRS",
            financial_year_end=date(2024, 12, 31),
            # Missing trial_balance - MockAgent requires it
        )

        with pytest.raises(ValueError, match="Invalid input"):
            mock_agent.generate(invalid_context)

    @patch("genreport.core.orchestration.base_agent.ContextValidator")
    def test_generate_cross_tenant_data(self, mock_validator_class, mock_agent, valid_context):
        """Test generate() raises on cross-tenant data."""
        # Setup validator to raise
        mock_validator = Mock()
        mock_validator.validate.side_effect = CrossTenantDataError("Cross-tenant data")
        mock_validator_class.return_value = mock_validator

        with pytest.raises(CrossTenantDataError):
            mock_agent.generate(valid_context)

    def test_supports_standard(self, mock_agent):
        """Test supports_standard checks correctly."""
        assert mock_agent.supports_standard("MOCK-STD") is True
        assert mock_agent.supports_standard("HKFRS 15") is False

    def test_get_relevant_standards(self, mock_agent, mock_retriever):
        """Test get_relevant_standards returns filtered results."""
        results = mock_agent.get_relevant_standards("revenue recognition")

        assert len(results) > 0
        mock_retriever.retrieve.assert_called()
```

### Step 6: Implement BaseFinancialAgent

**File:** `genreport/core/orchestration/base_agent.py`

```python
"""Base Financial Agent - Abstract base class for all disclosure agents."""

import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from uuid import UUID

from sqlalchemy.orm import Session

from genreport.core.orchestration.agent_models import AgentInput, AgentOutput
from genreport.core.retrieval.secure_kb_retriever import SecureKBRetriever
from genreport.core.security.context_validator import ContextValidator
from genreport.core.security.pii_detector import PIIDetector
from genreport.core.security.audit_logger import AuditLogger


logger = logging.getLogger(__name__)


class BaseFinancialAgent(ABC):
    """Abstract base class for all financial disclosure agents.

    This class provides the contract and common functionality for all
    market-specific agents. Market implementations must inherit from this
    class and implement the abstract methods.

    Architecture:
    - Core (generic) functionality lives here
    - Market-specific logic lives in markets/{jurisdiction}/agents/
    - Dependencies injected via constructor (dependency injection pattern)

    Security:
    - Context validation (prevents cross-tenant data leakage)
    - PII detection and redaction
    - Comprehensive audit logging

    Example:
        >>> class HKRevenueAgent(BaseFinancialAgent):
        ...     def process(self, context):
        ...         # HK-specific revenue recognition logic
        ...         pass
    """

    def __init__(
        self,
        market_config: Any,
        retriever: SecureKBRetriever,
        tenant_id: UUID,
        user_id: int,
        db: Session,
    ) -> None:
        """Initialize base financial agent.

        Args:
            market_config: Market-specific configuration (HKMarketConfig, etc.)
            retriever: Secure KB retriever (jurisdiction-filtered)
            tenant_id: Tenant UUID for isolation and audit
            user_id: User ID for audit logging
            db: Database session for audit logging
        """
        self.market_config = market_config
        self.retriever = retriever
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.db = db

        # Initialize security components
        self.context_validator = ContextValidator(
            expected_tenant_id=tenant_id,
            strict=True,  # Raise exception on violation
        )
        self.pii_detector = PIIDetector()

    # Abstract Properties (must override)

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Agent name for identification.

        Returns:
            Agent name (e.g., "HKRevenueAgent")
        """
        pass

    @property
    @abstractmethod
    def disclosure_section(self) -> str:
        """Disclosure section this agent generates.

        Returns:
            Section name (e.g., "revenue_recognition", "ppe", "leases")
        """
        pass

    @property
    @abstractmethod
    def supported_standards(self) -> List[str]:
        """List of accounting standards this agent supports.

        Returns:
            List of standards (e.g., ["HKFRS 15", "SME-FRS"])
        """
        pass

    # Abstract Methods (must implement)

    @abstractmethod
    def validate_input(self, context: AgentInput) -> bool:
        """Validate that input context has required fields for this agent.

        Args:
            context: Input context

        Returns:
            True if valid

        Raises:
            ValueError: If input is invalid with descriptive message
        """
        pass

    @abstractmethod
    def process(self, context: AgentInput) -> AgentOutput:
        """Core processing logic - generate disclosure.

        This is where market-specific DSPy signatures and modules are used.

        Args:
            context: Validated input context

        Returns:
            Agent output with disclosure and metadata
        """
        pass

    @abstractmethod
    def post_process(self, output: AgentOutput) -> AgentOutput:
        """Post-processing for market-specific formatting/adjustments.

        Args:
            output: Output from process()

        Returns:
            Modified output
        """
        pass

    # Protected Methods (inherited utilities)

    def _fetch_context(
        self,
        query: str,
        top_k: int = 5,
        chunk_types: List[str] = None,
    ) -> List[Dict]:
        """Fetch relevant knowledge base chunks.

        Args:
            query: Search query
            top_k: Maximum number of results
            chunk_types: Optional filter by chunk types

        Returns:
            List of relevant chunks with metadata
        """
        return self.retriever.retrieve(
            query=query,
            top_k=top_k,
            chunk_types=chunk_types,
        )

    def _validate_context(self, context: Dict[str, Any]) -> None:
        """Validate context contains no cross-tenant data.

        Args:
            context: Context dict to validate

        Raises:
            CrossTenantDataError: If violations found
        """
        # This will raise CrossTenantDataError if violations found
        # Audit logging handled automatically by ContextValidator
        self.context_validator.validate(context)

    def _scan_for_pii(self, text: str) -> Dict[str, List[str]]:
        """Scan text for PII.

        Args:
            text: Text to scan

        Returns:
            Dict mapping PII types to matches
        """
        return self.pii_detector.scan(text)

    def _redact_pii(self, text: str) -> str:
        """Redact PII from text.

        Args:
            text: Text to redact

        Returns:
            Sanitized text with PII removed
        """
        return self.pii_detector.redact(text)

    def _log_generation(self, section: str, result: AgentOutput) -> None:
        """Log generation event to audit log.

        Args:
            section: Disclosure section
            result: Agent output
        """
        AuditLogger.log_event(
            db=self.db,
            event_type="REPORT_GENERATION",
            action="GENERATE_SECTION",
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            resource_type="disclosure",
            details={
                "section": section,
                "agent_name": self.agent_name,
                "completeness": result.completeness_score,
                "confidence": result.confidence_score,
                "pii_detected": result.pii_detected,
                "pii_types": result.pii_types,
                "standards_used": result.standards_used,
                "processing_time_ms": result.processing_time_ms,
                "warnings_count": len(result.warnings),
            },
            status="SUCCESS",
        )

    def _format_currency(self, amount: float) -> str:
        """Format currency based on market configuration.

        Args:
            amount: Amount to format

        Returns:
            Formatted currency string
        """
        return self.market_config.format_currency(amount)

    def _format_date(self, date: str) -> str:
        """Format date based on market configuration.

        Args:
            date: Date string to format

        Returns:
            Formatted date string
        """
        return self.market_config.format_date(date)

    # Public Methods (final - not overridable)

    def generate(self, context: AgentInput) -> AgentOutput:
        """Main entry point for disclosure generation.

        This method orchestrates the full pipeline:
        1. Validate input
        2. Validate context security
        3. Process (market-specific)
        4. Scan for PII
        5. Redact PII if found
        6. Post-process
        7. Audit log

        Args:
            context: Input context

        Returns:
            Final agent output

        Raises:
            ValueError: If input validation fails
            CrossTenantDataError: If cross-tenant data detected
        """
        start_time = time.time()

        try:
            # Step 1: Validate input
            if not self.validate_input(context):
                raise ValueError("Invalid input for agent")

            # Step 2: Validate context security
            context_dict = context.model_dump()
            self._validate_context(context_dict)

            # Step 3: Process (market-specific)
            logger.info(
                f"Processing {self.disclosure_section} for tenant {self.tenant_id}"
            )
            output = self.process(context)

            # Mark context as validated
            output.context_validated = True

            # Step 4: Scan for PII
            pii_findings = self._scan_for_pii(output.disclosure_text)

            # Step 5: Redact PII if found
            if pii_findings:
                logger.warning(
                    f"PII detected in {self.agent_name} output: {list(pii_findings.keys())}"
                )
                output.disclosure_text = self._redact_pii(output.disclosure_text)
                output.pii_detected = True
                output.pii_types = list(pii_findings.keys())

            # Step 6: Post-process
            output = self.post_process(output)

            # Update processing time
            processing_time_ms = (time.time() - start_time) * 1000
            output.processing_time_ms = processing_time_ms

            # Step 7: Audit log
            self._log_generation(self.disclosure_section, output)

            return output

        except Exception as e:
            # Log failure
            logger.error(
                f"Agent {self.agent_name} failed: {str(e)}",
                exc_info=True,
            )

            AuditLogger.log_event(
                db=self.db,
                event_type="REPORT_GENERATION",
                action="GENERATE_SECTION",
                user_id=self.user_id,
                tenant_id=self.tenant_id,
                resource_type="disclosure",
                details={
                    "section": self.disclosure_section,
                    "agent_name": self.agent_name,
                    "error": str(e),
                },
                status="FAILURE",
            )

            raise

    def get_relevant_standards(self, query: str, top_k: int = 5) -> List[Dict]:
        """Get relevant standards from knowledge base.

        Public wrapper for knowledge base retrieval.

        Args:
            query: Search query
            top_k: Maximum results

        Returns:
            List of relevant standards (jurisdiction-filtered)
        """
        return self._fetch_context(query, top_k=top_k)

    def supports_standard(self, standard: str) -> bool:
        """Check if agent supports a specific standard.

        Args:
            standard: Standard code (e.g., "HKFRS 15")

        Returns:
            True if supported, False otherwise
        """
        return standard in self.supported_standards
```

### Step 7: Run Base Agent Tests

```bash
# Run base agent tests
pytest tests/core/orchestration/test_base_agent.py -v

# Expected: All tests pass
```

**Checkpoint:** All base agent tests should pass before proceeding.

---

## Phase 2.3: AgentFactory (4 hours)

### Step 8: Write Factory Tests First (TDD)

**File:** `tests/core/orchestration/test_agent_factory.py`

```python
"""Tests for AgentFactory pattern."""

import pytest
from uuid import uuid4
from unittest.mock import Mock, patch

from genreport.core.orchestration.agent_factory import AgentFactory
from genreport.core.orchestration.base_agent import BaseFinancialAgent


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock()


class TestAgentFactory:
    """Tests for AgentFactory."""

    def test_supports_hk_jurisdiction(self):
        """Test that HK jurisdiction is supported."""
        assert AgentFactory.supports_jurisdiction("HK") is True

    def test_unsupported_jurisdiction(self):
        """Test that invalid jurisdiction is not supported."""
        assert AgentFactory.supports_jurisdiction("INVALID") is False

    @patch("genreport.core.orchestration.agent_factory.get_market_config")
    @patch("genreport.core.orchestration.agent_factory.SecureKBRetriever")
    def test_create_hk_agents(self, mock_retriever_class, mock_get_config, mock_db):
        """Test creating HK agents."""
        # Setup mocks
        mock_config = Mock()
        mock_get_config.return_value = mock_config

        mock_retriever = Mock()
        mock_retriever_class.return_value = mock_retriever

        tenant_id = uuid4()
        user_id = 1

        # Create agents
        agents = AgentFactory.create_agents("HK", tenant_id, user_id, mock_db)

        # Verify agents created
        assert isinstance(agents, dict)
        assert "revenue" in agents
        # Note: Other agents will be added in Phase 3

        # Verify each agent is BaseFinancialAgent
        for agent in agents.values():
            assert isinstance(agent, BaseFinancialAgent)

        # Verify config was retrieved
        mock_get_config.assert_called_once_with("HK")

        # Verify retriever was created
        mock_retriever_class.assert_called_once_with(
            db=mock_db,
            jurisdiction="HK",
            tenant_id=tenant_id,
            user_id=user_id,
        )

    def test_create_agents_unsupported_jurisdiction(self, mock_db):
        """Test that unsupported jurisdiction raises error."""
        with pytest.raises(ValueError, match="Unsupported jurisdiction"):
            AgentFactory.create_agents("INVALID", uuid4(), 1, mock_db)

    @patch("genreport.core.orchestration.agent_factory.get_market_config")
    @patch("genreport.core.orchestration.agent_factory.SecureKBRetriever")
    def test_create_single_agent(self, mock_retriever_class, mock_get_config, mock_db):
        """Test creating a single agent."""
        # Setup mocks
        mock_config = Mock()
        mock_get_config.return_value = mock_config

        mock_retriever = Mock()
        mock_retriever_class.return_value = mock_retriever

        tenant_id = uuid4()
        user_id = 1

        # Create single agent
        agent = AgentFactory.create_agent("revenue", "HK", tenant_id, user_id, mock_db)

        # Verify agent created
        assert isinstance(agent, BaseFinancialAgent)
        assert agent.agent_name == "HKRevenueAgent"

    def test_create_agent_invalid_type(self, mock_db):
        """Test that invalid agent type raises error."""
        with pytest.raises(ValueError, match="Unsupported agent type"):
            AgentFactory.create_agent("invalid_type", "HK", uuid4(), 1, mock_db)

    def test_get_available_agents_hk(self):
        """Test getting available agents for HK."""
        agents = AgentFactory.get_available_agents("HK")

        assert isinstance(agents, list)
        assert "revenue" in agents
        # Note: Phase 3 will add: ppe, leases, inventory

    def test_get_available_agents_unsupported(self):
        """Test getting available agents for unsupported jurisdiction."""
        agents = AgentFactory.get_available_agents("INVALID")

        assert isinstance(agents, list)
        assert len(agents) == 0  # Empty list for unsupported
```

### Step 9: Implement AgentFactory

**File:** `genreport/core/orchestration/agent_factory.py`

```python
"""Agent Factory - Creates market-specific agents with dependency injection."""

import logging
from typing import Dict
from uuid import UUID

from sqlalchemy.orm import Session

from genreport.core.orchestration.base_agent import BaseFinancialAgent
from genreport.core.utils.market_config import get_market_config, validate_jurisdiction
from genreport.core.retrieval.secure_kb_retriever import SecureKBRetriever


logger = logging.getLogger(__name__)


class AgentFactory:
    """Factory for creating market-specific financial disclosure agents.

    This factory implements the factory pattern to create agents with
    proper dependency injection. It maintains separation between core
    (market-agnostic) and markets (market-specific) code.

    Architecture:
    - Lazy loading of market-specific modules (imported only when needed)
    - Centralized dependency injection
    - Type-safe return values (Dict[str, BaseFinancialAgent])

    Example:
        >>> agents = AgentFactory.create_agents("HK", tenant_id, user_id, db)
        >>> revenue_agent = agents["revenue"]
        >>> output = revenue_agent.generate(context)
    """

    @staticmethod
    def create_agents(
        jurisdiction: str,
        tenant_id: UUID,
        user_id: int,
        db: Session,
    ) -> Dict[str, BaseFinancialAgent]:
        """Create all agents for a jurisdiction.

        Args:
            jurisdiction: Jurisdiction code (HK, SG, AU)
            tenant_id: Tenant UUID for isolation
            user_id: User ID for audit logging
            db: Database session

        Returns:
            Dict mapping agent names to agent instances
            Example: {"revenue": HKRevenueAgent(...), "ppe": HKPPEAgent(...)}

        Raises:
            ValueError: If jurisdiction is not supported
        """
        # Validate jurisdiction
        if not validate_jurisdiction(jurisdiction):
            supported = ["HK", "SG", "AU"]
            raise ValueError(
                f"Unsupported jurisdiction: {jurisdiction}. "
                f"Supported: {', '.join(supported)}"
            )

        # Get market configuration
        market_config = get_market_config(jurisdiction)

        # Create jurisdiction-aware retriever
        retriever = SecureKBRetriever(
            db=db,
            jurisdiction=jurisdiction,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        # Create market-specific agents
        if jurisdiction == "HK":
            return AgentFactory._create_hk_agents(
                market_config, retriever, tenant_id, user_id, db
            )
        elif jurisdiction == "SG":
            # TODO: Implement Singapore agents (future)
            logger.warning("Singapore agents not yet implemented")
            raise ValueError("Singapore agents not yet implemented")
        elif jurisdiction == "AU":
            # TODO: Implement Australia agents (future)
            logger.warning("Australia agents not yet implemented")
            raise ValueError("Australia agents not yet implemented")
        else:
            raise ValueError(f"Unsupported jurisdiction: {jurisdiction}")

    @staticmethod
    def create_agent(
        agent_type: str,
        jurisdiction: str,
        tenant_id: UUID,
        user_id: int,
        db: Session,
    ) -> BaseFinancialAgent:
        """Create a single agent of specified type.

        Args:
            agent_type: Agent type (revenue, ppe, leases, inventory)
            jurisdiction: Jurisdiction code
            tenant_id: Tenant UUID
            user_id: User ID
            db: Database session

        Returns:
            Agent instance

        Raises:
            ValueError: If agent_type or jurisdiction not supported
        """
        # Create all agents for jurisdiction
        agents = AgentFactory.create_agents(jurisdiction, tenant_id, user_id, db)

        # Get requested agent
        if agent_type not in agents:
            available = list(agents.keys())
            raise ValueError(
                f"Unsupported agent type: {agent_type}. "
                f"Available for {jurisdiction}: {', '.join(available)}"
            )

        return agents[agent_type]

    @staticmethod
    def get_available_agents(jurisdiction: str) -> list[str]:
        """Get list of available agent types for jurisdiction.

        Args:
            jurisdiction: Jurisdiction code

        Returns:
            List of agent type names
            Example: ["revenue", "ppe", "leases", "inventory"]
        """
        if not validate_jurisdiction(jurisdiction):
            return []

        # Return agent types based on jurisdiction
        if jurisdiction == "HK":
            # Phase 2: Only revenue agent implemented
            # Phase 3 will add: ppe, leases, inventory
            return ["revenue"]
        elif jurisdiction == "SG":
            # TODO: Future implementation
            return []
        elif jurisdiction == "AU":
            # TODO: Future implementation
            return []
        else:
            return []

    @staticmethod
    def supports_jurisdiction(jurisdiction: str) -> bool:
        """Check if jurisdiction is supported.

        Args:
            jurisdiction: Jurisdiction code

        Returns:
            True if supported, False otherwise
        """
        return validate_jurisdiction(jurisdiction)

    # Private helper methods for creating market-specific agents

    @staticmethod
    def _create_hk_agents(
        market_config,
        retriever: SecureKBRetriever,
        tenant_id: UUID,
        user_id: int,
        db: Session,
    ) -> Dict[str, BaseFinancialAgent]:
        """Create Hong Kong agents.

        This method uses lazy loading to import HK-specific agents
        only when needed.

        Args:
            market_config: HKMarketConfig instance
            retriever: Secure KB retriever
            tenant_id: Tenant UUID
            user_id: User ID
            db: Database session

        Returns:
            Dict of HK agents
        """
        # Lazy import of HK-specific agents
        # This prevents circular dependencies and reduces startup time
        from genreport.markets.hk.agents.revenue_agent import HKRevenueAgent

        # Phase 2: Only revenue agent implemented
        # Phase 3 will add:
        # from genreport.markets.hk.agents.ppe_agent import HKPPEAgent
        # from genreport.markets.hk.agents.lease_agent import HKLeaseAgent
        # from genreport.markets.hk.agents.inventory_agent import HKInventoryAgent

        agents = {
            "revenue": HKRevenueAgent(
                market_config=market_config,
                retriever=retriever,
                tenant_id=tenant_id,
                user_id=user_id,
                db=db,
            ),
            # Phase 3: Add more agents
            # "ppe": HKPPEAgent(...),
            # "leases": HKLeaseAgent(...),
            # "inventory": HKInventoryAgent(...),
        }

        logger.info(f"Created {len(agents)} HK agents for tenant {tenant_id}")

        return agents
```

### Step 10: Create Stub HK Revenue Agent

For testing purposes, create a minimal stub implementation of HKRevenueAgent:

```bash
mkdir -p genreport/markets/hk/agents
touch genreport/markets/hk/agents/__init__.py
touch genreport/markets/hk/agents/revenue_agent.py
```

**File:** `genreport/markets/hk/agents/revenue_agent.py`

```python
"""HK Revenue Agent - STUB for Phase 2 testing.

This is a minimal stub implementation to allow factory testing.
Full implementation will be done in Sprint 4 Phase 3.
"""

from genreport.core.orchestration.base_agent import BaseFinancialAgent
from genreport.core.orchestration.agent_models import AgentInput, AgentOutput


class HKRevenueAgent(BaseFinancialAgent):
    """Hong Kong Revenue Recognition Agent (STUB).

    Full implementation in Sprint 4 Phase 3.
    """

    @property
    def agent_name(self) -> str:
        return "HKRevenueAgent"

    @property
    def disclosure_section(self) -> str:
        return "revenue_recognition"

    @property
    def supported_standards(self) -> list[str]:
        return ["HKFRS 15", "SME-FRS"]

    def validate_input(self, context: AgentInput) -> bool:
        """Validate input has revenue data."""
        # Stub: Just check trial_balance exists
        return context.trial_balance is not None

    def process(self, context: AgentInput) -> AgentOutput:
        """Process revenue disclosure - STUB."""
        # Stub: Return minimal output
        return AgentOutput(
            disclosure_text="[STUB] Revenue disclosure will be implemented in Phase 3",
            section=self.disclosure_section,
            completeness_score=0.0,
            confidence_score=0.0,
            agent_name=self.agent_name,
            processing_time_ms=0.0,
            standards_used=["HKFRS 15"],
        )

    def post_process(self, output: AgentOutput) -> AgentOutput:
        """Post-process - STUB."""
        # Stub: No processing
        return output
```

### Step 11: Run Factory Tests

```bash
# Run factory tests
pytest tests/core/orchestration/test_agent_factory.py -v

# Expected: All tests pass
```

**Checkpoint:** All factory tests should pass before proceeding.

---

## Phase 2.4: Integration Testing (4 hours)

### Step 12: Write Integration Tests

**File:** `tests/core/orchestration/test_agent_integration.py`

```python
"""Integration tests for agent infrastructure."""

import pytest
from datetime import date
from uuid import uuid4

from genreport.core.orchestration.agent_factory import AgentFactory
from genreport.core.orchestration.agent_models import AgentInput
from genreport.core.database.models import Tenant, User
from genreport.core.database.base import get_db


@pytest.fixture
def test_tenant(db):
    """Create test tenant."""
    tenant = Tenant(
        company_name="Test Company",
        data_residency_region="HK",
        jurisdiction="HK",
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@pytest.fixture
def test_user(db, test_tenant):
    """Create test user."""
    user = User(
        tenant_id=test_tenant.id,
        email="test@example.com",
        password_hash="hashed",
        full_name="Test User",
        role="auditor",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestAgentIntegration:
    """Integration tests for agent infrastructure."""

    def test_end_to_end_agent_creation(self, db, test_tenant, test_user):
        """Test end-to-end agent creation and usage."""
        # Create agents via factory
        agents = AgentFactory.create_agents(
            jurisdiction="HK",
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            db=db,
        )

        # Verify agents created
        assert "revenue" in agents

        # Get revenue agent
        revenue_agent = agents["revenue"]
        assert revenue_agent.agent_name == "HKRevenueAgent"

    def test_agent_generate_with_stub(self, db, test_tenant, test_user):
        """Test agent generate method with stub implementation."""
        # Create agent
        agent = AgentFactory.create_agent(
            agent_type="revenue",
            jurisdiction="HK",
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            db=db,
        )

        # Create valid context
        context = AgentInput(
            project_id=1,
            tenant_id=test_tenant.id,
            jurisdiction="HK",
            accounting_standard="HKFRS",
            financial_year_end=date(2024, 12, 31),
            trial_balance={"accounts": []},
        )

        # Generate disclosure
        output = agent.generate(context)

        # Verify output
        assert output.disclosure_text is not None
        assert output.section == "revenue_recognition"
        assert output.context_validated is True
        assert "HKRevenueAgent" in output.agent_name

    def test_multi_tenant_isolation(self, db):
        """Test that agents are isolated per tenant."""
        # Create two tenants
        tenant_a = Tenant(
            company_name="Company A",
            data_residency_region="HK",
            jurisdiction="HK",
        )
        tenant_b = Tenant(
            company_name="Company B",
            data_residency_region="HK",
            jurisdiction="HK",
        )
        db.add_all([tenant_a, tenant_b])
        db.commit()

        # Create users for each tenant
        user_a = User(
            tenant_id=tenant_a.id,
            email="user_a@example.com",
            password_hash="hashed",
            role="auditor",
        )
        user_b = User(
            tenant_id=tenant_b.id,
            email="user_b@example.com",
            password_hash="hashed",
            role="auditor",
        )
        db.add_all([user_a, user_b])
        db.commit()

        # Create agents for each tenant
        agents_a = AgentFactory.create_agents("HK", tenant_a.id, user_a.id, db)
        agents_b = AgentFactory.create_agents("HK", tenant_b.id, user_b.id, db)

        # Verify agents have different tenant IDs
        assert agents_a["revenue"].tenant_id == tenant_a.id
        assert agents_b["revenue"].tenant_id == tenant_b.id
        assert agents_a["revenue"].tenant_id != agents_b["revenue"].tenant_id
```

### Step 13: Run Integration Tests

```bash
# Run integration tests
pytest tests/core/orchestration/test_agent_integration.py -v

# Run all orchestration tests
pytest tests/core/orchestration/ -v

# Expected: All tests pass
```

**Checkpoint:** All integration tests should pass.

---

## Phase 2.5: Documentation (2 hours)

### Step 14: Update Package Exports

**File:** `genreport/core/orchestration/__init__.py`

```python
"""Orchestration package - Agent infrastructure."""

from genreport.core.orchestration.base_agent import BaseFinancialAgent
from genreport.core.orchestration.agent_models import AgentInput, AgentOutput, Source
from genreport.core.orchestration.agent_factory import AgentFactory

__all__ = [
    "BaseFinancialAgent",
    "AgentInput",
    "AgentOutput",
    "Source",
    "AgentFactory",
]
```

### Step 15: Create Usage Guide

**File:** `docs/guides/2025-10-18-using-base-agents.md`

[Create comprehensive usage guide with examples]

### Step 16: Run Full Test Suite

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=genreport.core.orchestration --cov-report=html

# Expected: All tests pass, coverage >80%
```

---

## Verification Checklist

Before marking Phase 2 complete, verify:

- [ ] All Pydantic models implemented with validation
- [ ] All model tests passing
- [ ] BaseFinancialAgent implemented with all abstract methods
- [ ] Mock agent tests passing
- [ ] AgentFactory implemented with HK support
- [ ] Factory tests passing
- [ ] Stub HKRevenueAgent created
- [ ] Integration tests passing
- [ ] Package exports updated
- [ ] Code follows SOLID principles
- [ ] No hardcoded jurisdictions in core/
- [ ] Security integration working (context validation, PII)
- [ ] Audit logging working
- [ ] Documentation complete

---

## Common Issues and Solutions

### Issue 1: Import Errors

**Problem:** Circular import errors when creating agents

**Solution:** Use lazy imports in factory methods (import inside method, not at module level)

### Issue 2: Mock Testing Abstract Class

**Problem:** Cannot instantiate abstract class for testing

**Solution:** Create MockFinancialAgent that implements all abstract methods

### Issue 3: Pydantic Validation Errors

**Problem:** Validation errors with nested models

**Solution:** Use `model_dump()` to convert to dict, check field definitions

### Issue 4: Database Session in Tests

**Problem:** Database session conflicts in tests

**Solution:** Use pytest fixtures with proper cleanup

---

## Next Steps (Phase 3)

After Phase 2 is complete, proceed to Sprint 4 Phase 3:

1. **Implement HK Revenue Agent** (full DSPy implementation)
2. **Implement HK PPE Agent**
3. **Implement HK Lease Agent**
4. **Implement HK Inventory Agent**
5. **Create Orchestrator** (coordinates all agents)

---

**Document Version:** 1.0
**Last Updated:** 2025-10-18
**Author:** Solution Architect
**Estimated Total Time:** 18 hours
