# Sprint 4: Base Agent Infrastructure - Architecture Design

**Date:** 2025-10-18
**Sprint Phase:** Phase 2 - Base Infrastructure
**Status:** Design Complete - Ready for Implementation
**Version:** 1.0

---

## Executive Summary

This document specifies the base agent infrastructure for Sprint 4 (AI Agents with Market-Awareness). The design provides market-agnostic base classes that HK-specific agents will inherit from in Phase 3. All infrastructure follows Clean Architecture principles, SOLID principles, and maintains strict separation between core (market-agnostic) and markets (market-specific) code.

### Key Architectural Decisions

1. **Dependency Injection Pattern**: Market configs and retrievers injected via constructors
2. **Abstract Base Class**: `BaseFinancialAgent` defines contract, market implementations provide specifics
3. **Factory Pattern**: `AgentFactory` creates market-specific agents with lazy loading
4. **Pydantic Models**: Type-safe input/output with comprehensive validation
5. **Security First**: Built-in context validation, PII detection, and audit logging

### Integration Points

- **SecureKBRetriever** (Sprint 3): Provides jurisdiction-filtered knowledge base access
- **ContextValidator** (Sprint 4 Phase 1): Ensures no cross-tenant data leakage
- **PIIDetector** (Sprint 4 Phase 1): Redacts sensitive information from generated content
- **Market Configs**: Injected via `get_market_config()` factory function

---

## Component Architecture

### 1. BaseFinancialAgent (Abstract Base Class)

**Location:** `genreport/core/orchestration/base_agent.py`

#### Class Diagram

```
┌────────────────────────────────────────────────────────────┐
│                  BaseFinancialAgent (ABC)                   │
├────────────────────────────────────────────────────────────┤
│ Properties:                                                 │
│  - market_config: MarketConfig                              │
│  - retriever: SecureKBRetriever                             │
│  - tenant_id: UUID                                          │
│  - user_id: int                                             │
│  - context_validator: ContextValidator                      │
│  - pii_detector: PIIDetector                                │
│  - db: Session                                              │
│                                                             │
│ Abstract Properties (must override):                        │
│  + agent_name: str                                          │
│  + disclosure_section: str                                  │
│  + supported_standards: List[str]                           │
│                                                             │
│ Abstract Methods (must implement):                          │
│  + process(context: AgentInput) -> AgentOutput             │
│  + validate_input(context: AgentInput) -> bool             │
│  + post_process(output: AgentOutput) -> AgentOutput        │
│                                                             │
│ Protected Methods (inherited):                              │
│  # _fetch_context(query: str, top_k: int) -> List[Dict]    │
│  # _validate_context(context: Dict) -> None                │
│  # _scan_for_pii(text: str) -> Dict                        │
│  # _redact_pii(text: str) -> str                           │
│  # _log_generation(section: str, result: Dict) -> None     │
│  # _format_currency(amount: float) -> str                  │
│  # _format_date(date: str) -> str                          │
│                                                             │
│ Public Methods (final):                                     │
│  + generate(context: AgentInput) -> AgentOutput            │
│  + get_relevant_standards(query: str) -> List[Dict]        │
│  + supports_standard(standard: str) -> bool                │
└────────────────────────────────────────────────────────────┘
         ▲
         │ inherits
         │
┌────────┴────────────────────────────────────────────────────┐
│                    Market-Specific Agents                    │
│  (markets/hk/agents/, markets/sg/agents/, etc.)              │
│                                                              │
│  - HKRevenueAgent                                            │
│  - HKPPEAgent                                                │
│  - HKLeaseAgent                                              │
│  - HKInventoryAgent                                          │
└──────────────────────────────────────────────────────────────┘
```

#### Method Responsibilities

**Abstract Methods (Market-Specific Implementations):**

1. **`process(context: AgentInput) -> AgentOutput`**
   - Core business logic for generating disclosure
   - Uses DSPy signatures and modules (market-specific)
   - Returns structured output with disclosure text and metadata

2. **`validate_input(context: AgentInput) -> bool`**
   - Validates that input context has required fields for this agent
   - Example: Revenue agent needs `trial_balance` with revenue accounts
   - Raises `ValueError` with descriptive message if invalid

3. **`post_process(output: AgentOutput) -> AgentOutput`**
   - Market-specific formatting, adjustments
   - Additional validation or enrichment
   - Returns modified output

**Protected Methods (Inherited Utilities):**

1. **`_fetch_context(query: str, top_k: int) -> List[Dict]`**
   - Wrapper around `self.retriever.retrieve()`
   - Automatically filtered by jurisdiction
   - Returns knowledge base chunks

2. **`_validate_context(context: Dict) -> None`**
   - Uses `ContextValidator` to ensure no cross-tenant data
   - Raises `SecurityError` if violations found
   - Mandatory call before processing

3. **`_scan_for_pii(text: str) -> Dict`**
   - Uses `PIIDetector.scan()` to find PII
   - Returns dict of PII types found
   - Used for audit logging

4. **`_redact_pii(text: str) -> str`**
   - Uses `PIIDetector.redact()` to remove PII
   - Returns sanitized text
   - Applied to all generated content

5. **`_log_generation(section: str, result: Dict) -> None`**
   - Creates audit log entry for generation event
   - Logs completeness score, PII detection status
   - Tenant-specific logging

6. **`_format_currency(amount: float) -> str`**
   - Delegates to `self.market_config.format_currency()`
   - Market-aware currency formatting

7. **`_format_date(date: str) -> str`**
   - Delegates to `self.market_config.format_date()`
   - Market-aware date formatting

**Public Methods (Final - Not Overridable):**

1. **`generate(context: AgentInput) -> AgentOutput`**
   - Main entry point for report generation
   - Orchestrates the full pipeline:
     1. Validate input (calls `validate_input()`)
     2. Validate context security (calls `_validate_context()`)
     3. Process (calls `process()` - market-specific)
     4. Scan for PII (calls `_scan_for_pii()`)
     5. Redact PII if found (calls `_redact_pii()`)
     6. Post-process (calls `post_process()`)
     7. Audit log (calls `_log_generation()`)
   - Returns final `AgentOutput`

2. **`get_relevant_standards(query: str) -> List[Dict]`**
   - Public wrapper for knowledge base retrieval
   - Returns jurisdiction-filtered standards

3. **`supports_standard(standard: str) -> bool`**
   - Checks if agent supports a specific standard
   - Used for dynamic agent selection

#### Constructor Signature

```python
def __init__(
    self,
    market_config: Any,  # HKMarketConfig, SGMarketConfig, etc.
    retriever: SecureKBRetriever,
    tenant_id: UUID,
    user_id: int,
    db: Session,
) -> None:
    """Initialize base financial agent.

    Args:
        market_config: Market-specific configuration object
        retriever: Secure KB retriever (jurisdiction-filtered)
        tenant_id: Tenant UUID for isolation and audit
        user_id: User ID for audit logging
        db: Database session for audit logging
    """
```

---

### 2. Agent Pydantic Models

**Location:** `genreport/core/orchestration/agent_models.py`

#### Model Hierarchy

```python
# Input Models
class AgentInput(BaseModel):
    """Input data for agent processing."""

    # Financial Data (ALL OPTIONAL - different agents need different data)
    trial_balance: Optional[Dict[str, Any]] = Field(default=None)
    general_ledger: Optional[Dict[str, Any]] = Field(default=None)
    prior_year_data: Optional[Dict[str, Any]] = Field(default=None)
    accounting_policies: Optional[Dict[str, Any]] = Field(default=None)
    relationship_map: Optional[Dict[str, Any]] = Field(default=None)

    # Project Metadata (REQUIRED)
    project_id: int = Field(gt=0)
    tenant_id: UUID
    jurisdiction: str = Field(pattern=r"^(HK|SG|AU)$")
    accounting_standard: str
    financial_year_end: date

    # Entity Information
    entity_type: Optional[str] = Field(default=None)  # SME, Listed, Private
    revenue: Optional[float] = Field(default=None, ge=0)
    assets: Optional[float] = Field(default=None, ge=0)
    employees: Optional[int] = Field(default=None, ge=0)

    # Agent-Specific Data (extensible via extra fields)
    model_config = ConfigDict(extra="allow")  # Allow additional fields

    @field_validator("jurisdiction")
    @classmethod
    def validate_jurisdiction(cls, v: str) -> str:
        """Ensure jurisdiction is supported."""
        from genreport.core.utils.market_config import validate_jurisdiction
        if not validate_jurisdiction(v):
            raise ValueError(f"Unsupported jurisdiction: {v}")
        return v


# Output Models
class Source(BaseModel):
    """Reference to knowledge base source."""

    document_id: int = Field(gt=0)
    chunk_id: int = Field(gt=0)
    relevance_score: float = Field(ge=0.0, le=1.0)
    snippet: str = Field(max_length=500)
    standard: Optional[str] = None  # HKFRS 15, SME-FRS, etc.
    section: Optional[str] = None  # Section reference (e.g., "15.1.2")

    @computed_field
    @property
    def citation(self) -> str:
        """Generate formatted citation."""
        if self.standard and self.section:
            return f"{self.standard}, Section {self.section}"
        elif self.standard:
            return self.standard
        else:
            return f"Document {self.document_id}"


class AgentOutput(BaseModel):
    """Output from agent processing."""

    # Generated Content
    disclosure_text: str = Field(min_length=1)
    section: str  # revenue_recognition, ppe, leases, etc.

    # Quality Metrics
    completeness_score: float = Field(ge=0.0, le=1.0, default=0.0)
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)

    # Source Attribution
    sources: List[Source] = Field(default_factory=list)
    standards_used: List[str] = Field(default_factory=list)

    # Security & Compliance
    pii_detected: bool = Field(default=False)
    pii_types: List[str] = Field(default_factory=list)
    context_validated: bool = Field(default=False)

    # Warnings & Recommendations
    warnings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

    # Metadata
    agent_name: str
    processing_time_ms: float = Field(ge=0.0)
    generated_at: datetime = Field(default_factory=datetime.utcnow)

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
                        "section": "15.31"
                    }
                ],
                "standards_used": ["HKFRS 15"],
                "pii_detected": False,
                "context_validated": True,
                "agent_name": "HKRevenueAgent",
                "processing_time_ms": 2340.5
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

#### Validation Rules

**AgentInput Validation:**
- `jurisdiction`: Must be HK, SG, or AU
- `project_id`: Must be positive integer
- `tenant_id`: Must be valid UUID
- Financial data fields are optional (different agents need different data)
- Extra fields allowed for agent-specific data (e.g., lease-specific data for lease agent)

**AgentOutput Validation:**
- `disclosure_text`: Must be non-empty string
- `completeness_score`, `confidence_score`: Must be 0.0 to 1.0
- `sources`: Each source must have valid document_id, chunk_id, relevance_score
- `processing_time_ms`: Must be non-negative

---

### 3. AgentFactory Pattern

**Location:** `genreport/core/orchestration/agent_factory.py`

#### Factory Design

```
┌──────────────────────────────────────────────────────────────┐
│                        AgentFactory                           │
├──────────────────────────────────────────────────────────────┤
│ Static Methods:                                               │
│  + create_agents(jurisdiction, tenant_id, user_id, db)       │
│    -> Dict[str, BaseFinancialAgent]                          │
│                                                               │
│  + create_agent(agent_type, jurisdiction, tenant_id,         │
│                 user_id, db) -> BaseFinancialAgent           │
│                                                               │
│  + get_available_agents(jurisdiction) -> List[str]           │
│                                                               │
│  + supports_jurisdiction(jurisdiction) -> bool                │
│                                                               │
│ Private Methods:                                              │
│  - _create_hk_agents(config, retriever, tenant_id,           │
│                      user_id, db) -> Dict                    │
│  - _create_sg_agents(...) -> Dict  # Future                  │
│  - _create_au_agents(...) -> Dict  # Future                  │
└──────────────────────────────────────────────────────────────┘
```

#### Implementation Strategy

**Key Design Decisions:**

1. **Lazy Loading of Market Modules**
   - Market-specific agents only imported when needed
   - Prevents circular dependencies
   - Reduces startup time

2. **Centralized Agent Creation**
   - Single source of truth for agent instantiation
   - Ensures consistent dependency injection
   - Simplifies testing (easy to mock factory)

3. **Graceful Degradation**
   - Returns empty dict for unsupported jurisdictions with warning
   - Allows system to continue with partial functionality
   - Logs warnings for missing agent types

4. **Type Safety**
   - Returns `Dict[str, BaseFinancialAgent]` for type checking
   - Agent names as keys (e.g., "revenue", "ppe", "leases")

#### Factory Method Signatures

```python
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

@staticmethod
def get_available_agents(jurisdiction: str) -> List[str]:
    """Get list of available agent types for jurisdiction.

    Args:
        jurisdiction: Jurisdiction code

    Returns:
        List of agent type names
        Example: ["revenue", "ppe", "leases", "inventory"]
    """

@staticmethod
def supports_jurisdiction(jurisdiction: str) -> bool:
    """Check if jurisdiction is supported.

    Args:
        jurisdiction: Jurisdiction code

    Returns:
        True if supported, False otherwise
    """
```

#### Dependency Injection Flow

```
AgentFactory.create_agents("HK", tenant_id, user_id, db)
    │
    ├─> Get market config: get_market_config("HK") -> HKMarketConfig
    │
    ├─> Create retriever: SecureKBRetriever(db, "HK", tenant_id, user_id)
    │
    ├─> Import market-specific agents (lazy loading):
    │   from genreport.markets.hk.agents import (
    │       HKRevenueAgent,
    │       HKPPEAgent,
    │       HKLeaseAgent,
    │       HKInventoryAgent
    │   )
    │
    └─> Create agent instances with injected dependencies:
        {
            "revenue": HKRevenueAgent(config, retriever, tenant_id, user_id, db),
            "ppe": HKPPEAgent(config, retriever, tenant_id, user_id, db),
            "leases": HKLeaseAgent(config, retriever, tenant_id, user_id, db),
            "inventory": HKInventoryAgent(config, retriever, tenant_id, user_id, db),
        }
```

---

## Security Integration

### Context Validation

**Location:** `genreport/core/security/context_validator.py` (existing)

**Integration in BaseFinancialAgent:**

```python
def _validate_context(self, context: Dict[str, Any]) -> None:
    """Validate context has no cross-tenant data.

    Raises:
        SecurityError: If cross-tenant data detected
    """
    validator = ContextValidator(
        expected_tenant_id=self.tenant_id,
        strict=True  # Raise exception on violation
    )

    # This will raise CrossTenantDataError if violations found
    validator.validate(context)

    # Audit logging is handled automatically by ContextValidator
```

**Mandatory Call:** The `generate()` method ALWAYS calls `_validate_context()` before processing.

### PII Detection and Redaction

**Location:** `genreport/core/security/pii_detector.py` (existing)

**Integration in BaseFinancialAgent:**

```python
def _scan_for_pii(self, text: str) -> Dict[str, List[str]]:
    """Scan text for PII.

    Returns:
        Dict of PII types found
    """
    return self.pii_detector.scan(text)

def _redact_pii(self, text: str) -> str:
    """Redact PII from text.

    Returns:
        Sanitized text
    """
    return self.pii_detector.redact(text)
```

**Automatic Application:** The `generate()` method ALWAYS scans and redacts PII from `disclosure_text`.

### Audit Logging

**Location:** `genreport/core/security/audit_logger.py` (existing)

**Integration in BaseFinancialAgent:**

```python
def _log_generation(self, section: str, result: AgentOutput) -> None:
    """Log generation event to audit log."""
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
```

---

## Testing Strategy

### 1. BaseFinancialAgent Tests

**Location:** `tests/core/orchestration/test_base_agent.py`

**Challenge:** Cannot instantiate abstract class directly

**Solution:** Create `MockFinancialAgent` concrete implementation for testing

```python
class MockFinancialAgent(BaseFinancialAgent):
    """Mock agent for testing base class functionality."""

    @property
    def agent_name(self) -> str:
        return "MockAgent"

    @property
    def disclosure_section(self) -> str:
        return "mock_section"

    @property
    def supported_standards(self) -> List[str]:
        return ["MOCK-STD"]

    def validate_input(self, context: AgentInput) -> bool:
        # Simple validation: just check trial_balance exists
        return context.trial_balance is not None

    def process(self, context: AgentInput) -> AgentOutput:
        # Mock processing: return simple disclosure
        return AgentOutput(
            disclosure_text="Mock disclosure text",
            section=self.disclosure_section,
            completeness_score=0.9,
            confidence_score=0.85,
            agent_name=self.agent_name,
            processing_time_ms=100.0,
        )

    def post_process(self, output: AgentOutput) -> AgentOutput:
        # Mock post-processing: add a warning
        output.warnings.append("This is a mock warning")
        return output
```

**Test Cases:**

1. **Test Abstract Properties** (verify mock provides them)
2. **Test Protected Methods:**
   - `_fetch_context()` calls retriever correctly
   - `_validate_context()` raises on cross-tenant data
   - `_scan_for_pii()` detects PII correctly
   - `_redact_pii()` removes PII
   - `_log_generation()` creates audit log
   - `_format_currency()` delegates to market config
   - `_format_date()` delegates to market config

3. **Test Public Methods:**
   - `generate()` orchestrates full pipeline correctly
   - `generate()` calls validate_input, _validate_context, process, _scan_for_pii, _redact_pii, post_process, _log_generation in order
   - `generate()` raises on invalid input
   - `generate()` raises on cross-tenant data
   - `get_relevant_standards()` returns filtered results
   - `supports_standard()` checks correctly

4. **Test Security Integration:**
   - Context validation catches cross-tenant data
   - PII detection finds common patterns
   - PII redaction removes sensitive data
   - Audit logging captures all events

### 2. Pydantic Models Tests

**Location:** `tests/core/orchestration/test_agent_models.py`

**Test Cases:**

1. **AgentInput Validation:**
   - Valid input passes validation
   - Invalid jurisdiction raises error
   - Negative project_id raises error
   - Invalid UUID raises error
   - Optional fields work correctly
   - Extra fields allowed (ConfigDict extra="allow")

2. **AgentOutput Validation:**
   - Valid output passes validation
   - Empty disclosure_text raises error
   - Scores outside 0.0-1.0 raise error
   - Negative processing_time_ms raises error
   - Source model validation works

3. **Source Model:**
   - Citation property generates correctly
   - Relevance score validation works

4. **Serialization:**
   - Models serialize to JSON correctly
   - Models deserialize from JSON correctly
   - Dates/UUIDs handle correctly

### 3. AgentFactory Tests

**Location:** `tests/core/orchestration/test_agent_factory.py`

**Test Cases:**

1. **HK Jurisdiction (Implemented):**
   - `create_agents("HK", ...)` returns all HK agents
   - Returned agents are correct types
   - Agents have market_config injected
   - Agents have retriever injected
   - `create_agent("revenue", "HK", ...)` returns HKRevenueAgent
   - `get_available_agents("HK")` returns correct list
   - `supports_jurisdiction("HK")` returns True

2. **Unsupported Jurisdictions:**
   - `create_agents("INVALID", ...)` raises ValueError
   - `create_agent("revenue", "INVALID", ...)` raises ValueError
   - `supports_jurisdiction("INVALID")` returns False

3. **Future Jurisdictions (SG, AU):**
   - `get_available_agents("SG")` returns empty list (until implemented)
   - `create_agents("SG", ...)` raises ValueError (until implemented)

4. **Dependency Injection:**
   - Market config is correct type (HKMarketConfig for HK)
   - Retriever has correct jurisdiction filter
   - Tenant ID and user ID passed correctly
   - Database session passed correctly

### 4. Integration Tests

**Location:** `tests/core/orchestration/test_agent_integration.py`

**Test Cases:**

1. **End-to-End Agent Creation:**
   - Factory creates agent with all dependencies
   - Agent can retrieve from knowledge base
   - Agent can generate disclosure (using mock)
   - Audit logs created correctly

2. **Security Integration:**
   - Agent validates context before processing
   - Agent detects and redacts PII
   - Audit logs capture security events

3. **Multi-Tenant Isolation:**
   - Agent A (tenant 1) cannot access tenant 2 data
   - Cross-tenant context raises SecurityError

---

## Implementation Sequence

### Phase 2.1: Pydantic Models (2 hours)

**Files to Create:**
1. `genreport/core/orchestration/agent_models.py`

**Tests to Create:**
1. `tests/core/orchestration/test_agent_models.py`

**Tasks:**
- [ ] Create `AgentInput` with all fields and validation
- [ ] Create `Source` with citation property
- [ ] Create `AgentOutput` with all fields and validation
- [ ] Write comprehensive validation tests
- [ ] Test serialization/deserialization

### Phase 2.2: BaseFinancialAgent (6 hours)

**Files to Create:**
1. `genreport/core/orchestration/base_agent.py`

**Tests to Create:**
1. `tests/core/orchestration/test_base_agent.py`

**Tasks:**
- [ ] Create abstract base class with all abstract methods
- [ ] Implement protected helper methods
- [ ] Implement `generate()` orchestration method
- [ ] Create `MockFinancialAgent` for testing
- [ ] Test all protected methods
- [ ] Test `generate()` pipeline
- [ ] Test security integration

### Phase 2.3: AgentFactory (4 hours)

**Files to Create:**
1. `genreport/core/orchestration/agent_factory.py`

**Tests to Create:**
1. `tests/core/orchestration/test_agent_factory.py`

**Tasks:**
- [ ] Create factory class with static methods
- [ ] Implement `create_agents()` for HK jurisdiction
- [ ] Implement `create_agent()` for single agent creation
- [ ] Implement `get_available_agents()`
- [ ] Implement `supports_jurisdiction()`
- [ ] Test HK agent creation
- [ ] Test error handling for unsupported jurisdictions
- [ ] Test dependency injection

### Phase 2.4: Integration Testing (4 hours)

**Tests to Create:**
1. `tests/core/orchestration/test_agent_integration.py`

**Tasks:**
- [ ] End-to-end agent creation and usage
- [ ] Security integration tests
- [ ] Multi-tenant isolation verification
- [ ] Performance benchmarks (baseline)

### Phase 2.5: Documentation (2 hours)

**Files to Update:**
1. `docs/guides/2025-10-18-using-base-agents.md` (create)
2. `README.md` (add agent architecture section)

**Tasks:**
- [ ] Write implementation guide for market-specific agents
- [ ] Document dependency injection pattern
- [ ] Create examples for extending BaseFinancialAgent
- [ ] Update architecture diagrams

---

## File Structure Summary

```
genreport/
├── core/
│   ├── orchestration/
│   │   ├── __init__.py                # Export base classes
│   │   ├── base_agent.py              # BaseFinancialAgent (abstract)
│   │   ├── agent_models.py            # Pydantic models
│   │   └── agent_factory.py           # AgentFactory
│   │
│   ├── security/                       # Existing (Phase 1 complete)
│   │   ├── context_validator.py       # ✅ Complete
│   │   ├── pii_detector.py            # ✅ Complete
│   │   └── audit_logger.py            # ✅ Complete
│   │
│   └── retrieval/                      # Existing (Sprint 3 complete)
│       └── secure_kb_retriever.py     # ✅ Complete
│
├── markets/
│   └── hk/
│       └── agents/                     # Phase 3 (not yet created)
│           ├── __init__.py
│           ├── revenue_agent.py       # HKRevenueAgent (Phase 3)
│           ├── ppe_agent.py           # HKPPEAgent (Phase 3)
│           ├── lease_agent.py         # HKLeaseAgent (Phase 3)
│           └── inventory_agent.py     # HKInventoryAgent (Phase 3)
│
tests/
└── core/
    └── orchestration/
        ├── __init__.py
        ├── test_agent_models.py       # Pydantic model tests
        ├── test_base_agent.py         # Base class tests (with mock)
        ├── test_agent_factory.py      # Factory pattern tests
        └── test_agent_integration.py  # Integration tests
```

---

## Compliance Checklist

### Clean Architecture

- [x] **Dependency Rule**: Core has no imports from markets
- [x] **Separation of Concerns**: Base classes define contracts, markets implement
- [x] **Dependency Injection**: All market-specific logic injected via constructor
- [x] **Interface Segregation**: Abstract methods only define what's necessary

### SOLID Principles

- [x] **Single Responsibility**: Each class has one clear purpose
  - `BaseFinancialAgent`: Define agent contract and orchestration
  - `AgentFactory`: Create and configure agents
  - `AgentInput/Output`: Data validation and structure

- [x] **Open/Closed**: Open for extension (new markets), closed for modification
  - Add new jurisdictions without changing base classes
  - Add new agent types by inheriting from base

- [x] **Liskov Substitution**: All market agents are substitutable
  - Any `BaseFinancialAgent` can be used interchangeably
  - Factory returns `BaseFinancialAgent` interface

- [x] **Interface Segregation**: Agents only implement what they need
  - Abstract methods focused on core agent behavior
  - No forced implementations of unused methods

- [x] **Dependency Inversion**: Depend on abstractions
  - `BaseFinancialAgent` is abstract interface
  - Market configs injected, not imported
  - Retriever injected, not instantiated

### Security

- [x] **Context Validation**: Mandatory before processing
- [x] **PII Detection**: Automatic scanning and redaction
- [x] **Audit Logging**: All generation events logged
- [x] **Tenant Isolation**: Enforced via context validator

### Testing

- [x] **TDD Approach**: Tests defined before implementation
- [x] **Unit Tests**: Each component tested in isolation
- [x] **Integration Tests**: Components tested together
- [x] **Security Tests**: Context validation, PII detection tested

---

## Next Steps (Phase 3)

After base infrastructure is complete and tested:

1. **Implement HK Revenue Agent** (Sprint 4 Phase 3)
   - Create `HKRevenueAgent` extending `BaseFinancialAgent`
   - Implement DSPy signature for revenue recognition
   - Add HKFRS 15 vs SME-FRS logic
   - Comprehensive tests

2. **Implement Additional HK Agents**
   - `HKPPEAgent` (Property, Plant, Equipment)
   - `HKLeaseAgent` (HKFRS 16)
   - `HKInventoryAgent`

3. **Create Orchestrator** (Sprint 4 Phase 4)
   - `SecureOrchestrator` to coordinate all agents
   - Parallel agent execution
   - Result aggregation

---

## Architectural Decision Records

### ADR 1: Dependency Injection Over Service Locator

**Decision:** Use constructor injection for market configs and retrievers

**Rationale:**
- Makes dependencies explicit
- Easier to test (inject mocks)
- Follows SOLID (Dependency Inversion Principle)
- No hidden dependencies

**Alternatives Considered:**
- Service locator pattern (rejected - hidden dependencies)
- Singleton market configs (rejected - hard to test)

**Consequences:**
- Slightly more verbose instantiation
- Clearer dependency graph
- Better testability

### ADR 2: Abstract Base Class Over Protocol

**Decision:** Use ABC (Abstract Base Class) instead of typing.Protocol

**Rationale:**
- Enforces implementation of abstract methods at class definition
- Provides shared implementation (protected methods)
- Better runtime validation
- Clearer inheritance hierarchy

**Alternatives Considered:**
- `typing.Protocol` (rejected - no shared implementation, duck typing)
- Concrete base class with NotImplementedError (rejected - not enforced)

**Consequences:**
- Market agents MUST inherit from base class
- Cannot use duck typing
- Better IDE support for abstract methods

### ADR 3: Factory Pattern for Agent Creation

**Decision:** Use AgentFactory static methods over direct instantiation

**Rationale:**
- Single source of truth for agent creation
- Centralizes dependency injection logic
- Easier to add new jurisdictions
- Lazy loading of market-specific modules

**Alternatives Considered:**
- Direct instantiation (rejected - scattered dependency logic)
- Builder pattern (rejected - overkill for this use case)

**Consequences:**
- All agents created via factory
- Factory becomes critical component
- Easier to mock in tests

### ADR 4: Pydantic for Input/Output Validation

**Decision:** Use Pydantic BaseModel for AgentInput and AgentOutput

**Rationale:**
- Type safety with runtime validation
- Automatic serialization/deserialization
- Clear schema documentation
- IDE autocomplete support

**Alternatives Considered:**
- Plain dicts (rejected - no validation, no types)
- Dataclasses (rejected - no validation)
- Custom validation classes (rejected - reinventing wheel)

**Consequences:**
- Must import pydantic
- Validation errors are Pydantic exceptions
- JSON schema generation available

### ADR 5: Final generate() Method

**Decision:** Make `generate()` final (not overridable) in base class

**Rationale:**
- Enforces consistent security checks (context validation, PII)
- Ensures audit logging always happens
- Prevents market implementations from bypassing security
- Template method pattern

**Alternatives Considered:**
- Allow overriding (rejected - security risk)
- Use hooks instead (rejected - harder to enforce order)

**Consequences:**
- Market agents cannot override generate()
- Must implement process() instead
- Security guarantees maintained

---

## Performance Targets

### Agent Creation (via Factory)

- **Target:** <50ms per agent creation
- **Measurement:** Time from factory call to agent ready
- **Optimization:** Lazy import of market modules

### Knowledge Base Retrieval

- **Target:** <100ms for top-5 retrieval
- **Measurement:** Time for `_fetch_context()` call
- **Dependency:** SecureKBRetriever performance (Sprint 3)

### Context Validation

- **Target:** <10ms for typical context (5-10 nested dicts)
- **Measurement:** Time for `_validate_context()` call
- **Dependency:** ContextValidator performance (Phase 1)

### PII Detection

- **Target:** <50ms for 1000-word disclosure
- **Measurement:** Time for `_scan_for_pii()` and `_redact_pii()`
- **Dependency:** PIIDetector performance (Phase 1)

---

## Risk Analysis

### Risk 1: Abstract Class Testing Complexity

**Impact:** Medium
**Probability:** Medium

**Mitigation:**
- Create MockFinancialAgent for testing
- Test all protected methods thoroughly
- Integration tests with real HK agents (Phase 3)

### Risk 2: Market Config Type Safety

**Impact:** Low
**Probability:** Low

**Issue:** `market_config` typed as `Any` due to different market types

**Mitigation:**
- Document expected market config interface
- Runtime validation in base class constructor
- Market-specific agents type-hint correctly

### Risk 3: Factory Method Maintenance

**Impact:** Medium
**Probability:** Medium

**Issue:** Factory needs updating for each new jurisdiction or agent

**Mitigation:**
- Clear documentation for adding new jurisdictions
- Comprehensive tests for factory methods
- Consider plugin architecture for future (beyond Sprint 4)

---

## Conclusion

This base agent infrastructure provides a solid foundation for market-specific agent implementations in Phase 3. The design strictly adheres to Clean Architecture and SOLID principles, maintains security-first approach, and provides clear separation between core (market-agnostic) and market-specific code.

**Key Achievements:**
1. Market-agnostic base classes with dependency injection
2. Type-safe Pydantic models with comprehensive validation
3. Factory pattern for flexible agent creation
4. Built-in security (context validation, PII detection, audit logging)
5. Comprehensive testing strategy

**Next Steps:**
- Implement Pydantic models (Phase 2.1)
- Implement BaseFinancialAgent (Phase 2.2)
- Implement AgentFactory (Phase 2.3)
- Integration testing (Phase 2.4)
- Documentation (Phase 2.5)
- Move to Phase 3: HK-specific agent implementations

---

**Document Version:** 1.0
**Last Updated:** 2025-10-18
**Author:** Solution Architect
**Status:** Design Complete - Ready for Implementation
