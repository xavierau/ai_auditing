# Sprint 4 Implementation Plan - AI Agents with Market-Awareness

**Date:** 2025-10-18
**Sprint:** Sprint 4 - AI Agents (3.5 weeks, 134 hours)
**Status:** Planning Phase
**Prerequisites:** Sprint 1, 2, 3 Complete ✅

---

## Executive Summary

Sprint 4 builds production-ready DSPy agents with complete market-awareness and security. Agents automatically use the correct accounting standards based on project jurisdiction and generate high-quality disclosures with source attribution.

### Key Objectives
- ✅ Base agent classes for multi-market support
- ✅ Agent factory pattern for market-specific agents
- ✅ 4 HK agents (Revenue, PPE, Lease, Inventory)
- ✅ Context validation (no cross-tenant data)
- ✅ PII detection and redaction
- ✅ Rate limiting per tenant
- ✅ Secure orchestration with audit trail

### Success Criteria
- Agent quality: >90% completeness score
- Required disclosures: >95% present
- Generation time: <3 minutes end-to-end
- Cost per report: <$0.50
- Security tests: 100% passing
- No hardcoded jurisdictions in `core/`

---

## Architecture Overview

### Hybrid Architecture Compliance

```
genreport/
├── core/orchestration/              # MARKET-AGNOSTIC (new)
│   ├── base_agent.py                # Abstract base agent
│   ├── agent_factory.py             # Factory pattern
│   ├── secure_orchestrator.py       # Coordinates agents
│   └── agent_models.py              # Pydantic models
│
├── core/security/                   # SECURITY COMPONENTS (new)
│   ├── context_validator.py        # Cross-tenant detection
│   ├── pii_detector.py              # PII detection/redaction
│   └── tenant_rate_limiter.py       # Rate limiting
│
├── markets/hk/agents/               # HK-SPECIFIC (new)
│   ├── __init__.py
│   ├── revenue_agent.py             # HKFRS 15 / SME-FRS
│   ├── ppe_agent.py                 # HKFRS 16 / IAS 16
│   ├── lease_agent.py               # HKFRS 16
│   └── inventory_agent.py           # IAS 2
│
├── api/routers/                     # API LAYER (updated)
│   └── reports.py                   # Report generation endpoints
│
└── core/database/models.py          # DATABASE (updated)
    ├── GeneratedReport              # Store agent outputs
    ├── ReportSection                # Individual sections
    └── AgentExecution               # Audit trail
```

### Component Dependencies

```
SecureOrchestrator
├── AgentFactory
│   ├── BaseFinancialAgent (abstract)
│   │   ├── SecureKBRetriever (from Sprint 3) ✅
│   │   ├── MarketConfig (from Sprint 1) ✅
│   │   └── PIIDetector (new)
│   │
│   └── HK Agents (4 agents)
│       ├── HKRevenueAgent
│       ├── HKPPEAgent
│       ├── HKLeaseAgent
│       └── HKInventoryAgent
│
├── ContextValidator (new)
├── TenantRateLimiter (new)
└── AuditLogger (from Sprint 1) ✅
```

---

## Implementation Phases

### Phase 1: Security Foundation (24 hours, Week 1)

**Goal:** Build security infrastructure to prevent cross-tenant data leakage and PII exposure.

#### 1.1: ContextValidator - Cross-Tenant Detection (10 hours)

**File:** `genreport/core/security/context_validator.py`

**Functionality:**
- Recursively inspect context dict for `tenant_id` fields
- Detect mismatches between expected and found tenant_id
- Log security violations with audit trail
- Return validation result with violation details

**DSPy Approach:** NOT APPLICABLE (pure Python security logic)

**Test Cases (TDD):**
```python
def test_valid_context_single_tenant():
    """All data belongs to same tenant - should pass"""

def test_detect_cross_tenant_in_nested_dict():
    """Nested dict with wrong tenant_id - should fail"""

def test_detect_cross_tenant_in_list():
    """List item with wrong tenant_id - should fail"""

def test_validation_logs_security_violation():
    """Failed validation creates audit log entry"""

def test_empty_context_passes():
    """Empty context is valid"""
```

**Database Impact:** None (uses existing AuditLog table)

**Dependencies:**
- Requires: `AuditLogger` (Sprint 1 ✅)
- Required by: `SecureOrchestrator`, all agents

---

#### 1.2: PIIDetector - PII Detection and Redaction (10 hours)

**File:** `genreport/core/security/pii_detector.py`

**Functionality:**
- Detect PII using regex patterns (HKID, phone, email, address, bank accounts)
- Partial redaction for emails (keep domain)
- Full redaction for sensitive IDs
- Return findings dict with PII types and matches

**PII Patterns for Hong Kong:**
```python
PATTERNS = {
    'hkid': r'[A-Z]\d{6}\([0-9A]\)',
    'phone_hk': r'\+852\s?\d{4}\s?\d{4}',
    'phone_intl': r'\+\d{1,3}\s?\d{3,4}\s?\d{4,8}',
    'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    'credit_card': r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}',
    'bank_account': r'\d{3}-\d{6}-\d{3}',
    'address': r'\d+[A-Za-z\s,]+(?:Street|Road|Avenue|Drive|Lane|Floor)',
}
```

**Test Cases (TDD):**
```python
def test_detect_hkid():
    """Detect Hong Kong Identity Card numbers"""

def test_detect_phone_numbers():
    """Detect HK and international phone formats"""

def test_detect_email_addresses():
    """Detect email addresses"""

def test_partial_redact_email():
    """Email: jo***@example.com"""

def test_full_redact_hkid():
    """HKID: [REDACTED]"""

def test_no_pii_returns_original():
    """Text without PII unchanged"""

def test_multiple_pii_types():
    """Detect and redact multiple PII types in one text"""
```

**Database Impact:** None

**Dependencies:**
- Requires: None (standalone)
- Required by: All agents, `SecureOrchestrator`

---

#### 1.3: TenantRateLimiter - Rate Limiting (6 hours)

**File:** `genreport/core/security/tenant_rate_limiter.py`

**Functionality:**
- Redis-backed rate limiting per tenant
- Configurable limits (calls per hour/day/month)
- Sliding window algorithm
- Return remaining quota and reset time

**Configuration:**
```python
RATE_LIMITS = {
    "report_generation": {"calls": 100, "period": "hour"},
    "agent_execution": {"calls": 500, "period": "hour"},
    "kb_search": {"calls": 1000, "period": "hour"},
}
```

**Test Cases (TDD):**
```python
def test_within_limit_allows_request():
    """Request within limit succeeds"""

def test_exceeding_limit_raises_exception():
    """101st request in hour raises HTTPException(429)"""

def test_different_tenants_independent_limits():
    """Tenant A limit doesn't affect Tenant B"""

def test_limit_resets_after_period():
    """After 1 hour, counter resets"""

def test_get_remaining_quota():
    """Can query remaining calls"""
```

**Database Impact:** None (uses Redis)

**Dependencies:**
- Requires: Redis connection (from Sprint 2 ✅)
- Required by: API endpoints

---

### Phase 2: Base Agent Infrastructure (28 hours, Week 1-2)

#### 2.1: BaseFinancialAgent - Abstract Base Class (12 hours)

**File:** `genreport/core/orchestration/base_agent.py`

**Functionality:**
- Abstract base class for all financial agents
- Dependency injection: market_config, retriever, tenant_id
- Common methods: `get_relevant_standards()`, `format_currency()`, `validate_context()`
- Abstract method: `async analyze(context: dict) -> dict`
- PII detection integration
- Source attribution tracking

**Design Pattern:** Template Method Pattern + Dependency Injection

**Test Cases (TDD):**
```python
def test_cannot_instantiate_base_agent_directly():
    """BaseFinancialAgent is abstract"""

def test_get_relevant_standards_filters_by_jurisdiction():
    """KB retrieval uses jurisdiction filtering"""

def test_format_currency_uses_market_config():
    """HKD formatting for HK market"""

def test_validate_context_calls_validator():
    """Delegates to ContextValidator"""

def test_base_agent_has_pii_detector():
    """All agents have PIIDetector instance"""
```

**Database Impact:** None

**Dependencies:**
- Requires: `SecureKBRetriever` (Sprint 3 ✅), `MarketConfig`, `ContextValidator`, `PIIDetector`
- Required by: All market-specific agents

---

#### 2.2: AgentFactory - Factory Pattern (8 hours)

**File:** `genreport/core/orchestration/agent_factory.py`

**Functionality:**
- Static factory method: `create_agents(jurisdiction, tenant_id, user_id)`
- Returns dict of agent name → agent instance
- Dynamically imports market-specific agents
- Initializes agents with correct market config and retriever
- Raises error for unsupported jurisdictions

**Supported Agents by Jurisdiction:**
```python
{
    "HK": {
        "revenue": HKRevenueAgent,
        "ppe": HKPPEAgent,
        "lease": HKLeaseAgent,
        "inventory": HKInventoryAgent
    },
    "SG": {  # Future
        "revenue": SGRevenueAgent,
        # ...
    }
}
```

**Test Cases (TDD):**
```python
def test_create_hk_agents():
    """Creates 4 HK agents with correct config"""

def test_agents_have_hk_retriever():
    """All agents use jurisdiction='HK' retriever"""

def test_unsupported_jurisdiction_raises_error():
    """jurisdiction='XX' raises ValueError"""

def test_factory_no_hardcoded_jurisdictions():
    """Dynamic imports prevent hardcoding"""

def test_agents_share_same_retriever_instance():
    """Efficiency: reuse retriever across agents"""
```

**Database Impact:** None

**Dependencies:**
- Requires: `BaseFinancialAgent`, market configs, `SecureKBRetriever`
- Required by: `SecureOrchestrator`

---

#### 2.3: Agent Pydantic Models (8 hours)

**File:** `genreport/core/orchestration/agent_models.py`

**Functionality:**
- Pydantic models for DSPy signatures
- Input models: `FinancialContext`, `RevenueData`, `PPEData`, etc.
- Output models: `DisclosureOutput`, `SourceReference`, `CompletenessScore`
- Validation logic for required fields
- Serialization helpers

**Key Models:**
```python
class FinancialContext(BaseModel):
    """Input context for agents"""
    trial_balance: List[TrialBalanceRow]
    general_ledger: List[GeneralLedgerRow]
    prior_year: Optional[Dict]
    relationship_map: Dict
    project_metadata: ProjectMetadata

class DisclosureOutput(BaseModel):
    """Agent output"""
    section: str
    content: str
    standard_used: str
    completeness: float  # 0.0 to 1.0
    sources: List[SourceReference]
    pii_detected: bool = False
    pii_types: Optional[List[str]] = None

class SourceReference(BaseModel):
    """KB chunk reference"""
    chunk_id: int
    standard: str
    chunk_type: str
    content_preview: str
    similarity_score: float
```

**Test Cases (TDD):**
```python
def test_financial_context_validates_required_fields():
    """Missing trial_balance raises ValidationError"""

def test_disclosure_output_completeness_range():
    """Completeness must be 0.0-1.0"""

def test_source_reference_serialization():
    """Can serialize to/from dict"""

def test_pii_types_optional_if_not_detected():
    """pii_types=None when pii_detected=False"""
```

**Database Impact:** None (in-memory models)

**Dependencies:**
- Requires: Pydantic
- Required by: All agents, DSPy signatures

---

### Phase 3: HK Agents Implementation (48 hours, Week 2-3)

Each agent follows the same implementation pattern. **Use @dspy-expert agent for each implementation.**

#### 3.1: HKRevenueAgent - Revenue Recognition (12 hours)

**File:** `genreport/markets/hk/agents/revenue_agent.py`

**Accounting Standards:**
- HKFRS 15: Revenue from Contracts with Customers (for non-SME)
- SME-FRS Section 23: Revenue (for SME entities)

**Functionality:**
- Detect if entity is SME (turnover, employees, total assets criteria)
- Select appropriate standard (HKFRS 15 vs SME-FRS)
- Retrieve relevant KB chunks on revenue recognition
- Generate disclosure covering:
  * Revenue recognition policy
  * Performance obligations
  * Transaction price allocation
  * Contract balances (receivables, liabilities)
  * Revenue disaggregation by type
- Calculate completeness score
- Provide source attribution

**DSPy Signature:**
```python
class GenerateRevenueDisclosure(dspy.Signature):
    """Generate HKFRS 15 or SME-FRS revenue disclosure"""

    revenue_data: dict = dspy.InputField(
        desc="Trial balance revenue accounts, GL transactions, prior year comparatives"
    )
    kb_standards: List[dict] = dspy.InputField(
        desc="Relevant KB chunks from HKFRS 15 or SME-FRS"
    )
    accounting_standard: str = dspy.InputField(
        desc="HKFRS 15 or SME-FRS Section 23"
    )
    currency: str = dspy.InputField(desc="HKD")
    entity_type: str = dspy.InputField(desc="SME or non-SME")

    disclosure: str = dspy.OutputField(
        desc="Complete revenue recognition disclosure note"
    )
    completeness_score: float = dspy.OutputField(
        desc="Completeness 0.0-1.0 based on required disclosures present"
    )
    source_references: List[dict] = dspy.OutputField(
        desc="KB chunks used with chunk_id and similarity_score"
    )
    required_disclosures_met: List[str] = dspy.OutputField(
        desc="Checklist of required disclosures present"
    )
```

**Test Cases (TDD):**
```python
def test_revenue_agent_uses_hkfrs15_for_non_sme():
    """Non-SME entity uses HKFRS 15"""

def test_revenue_agent_uses_smefrs_for_sme():
    """SME entity uses SME-FRS Section 23"""

def test_revenue_disclosure_includes_policy():
    """Disclosure includes revenue recognition policy"""

def test_revenue_disclosure_formats_hkd():
    """All amounts in HKD format"""

def test_completeness_score_above_90():
    """Completeness score >0.90 for complete disclosure"""

def test_source_attribution_includes_chunk_ids():
    """Output includes KB chunk IDs used"""

def test_pii_detection_and_redaction():
    """Customer names/emails redacted if present"""

def test_revenue_agent_validates_context():
    """Cross-tenant data raises SecurityError"""
```

**Dependencies:**
- Requires: `BaseFinancialAgent`, `SecureKBRetriever`, `PIIDetector`, `ContextValidator`

---

#### 3.2: HKPPEAgent - Property, Plant & Equipment (12 hours)

**File:** `genreport/markets/hk/agents/ppe_agent.py`

**Accounting Standards:**
- HKFRS 16: Leases (right-of-use assets)
- IAS 16: Property, Plant and Equipment
- IAS 36: Impairment of Assets
- SME-FRS Section 17: Property, Plant and Equipment

**Functionality:**
- Identify PPE categories (land, buildings, equipment, vehicles, etc.)
- Determine measurement model (cost vs revaluation)
- Calculate depreciation (straight-line, reducing balance, etc.)
- Check for impairment indicators
- Generate disclosure covering:
  * Accounting policy for PPE
  * Reconciliation of carrying amounts
  * Depreciation methods and useful lives
  * Revaluation surplus (if applicable)
  * Impairment losses
  * Commitments for acquisition

**DSPy Signature:**
```python
class GeneratePPEDisclosure(dspy.Signature):
    """Generate IAS 16 / SME-FRS PPE disclosure"""

    ppe_data: dict = dspy.InputField(
        desc="PPE balances, depreciation schedule, additions/disposals"
    )
    kb_standards: List[dict] = dspy.InputField(
        desc="Relevant KB chunks from IAS 16, HKFRS 16, IAS 36"
    )
    accounting_standard: str = dspy.InputField(desc="IAS 16 or SME-FRS Section 17")
    currency: str = dspy.InputField(desc="HKD")
    measurement_model: str = dspy.InputField(desc="cost or revaluation")

    disclosure: str = dspy.OutputField(
        desc="Complete PPE disclosure note with reconciliation"
    )
    completeness_score: float = dspy.OutputField()
    source_references: List[dict] = dspy.OutputField()
    required_disclosures_met: List[str] = dspy.OutputField()
```

**Test Cases (TDD):**
```python
def test_ppe_agent_includes_reconciliation():
    """Disclosure includes opening balance → closing balance"""

def test_ppe_agent_categorizes_assets():
    """Separate disclosure for land, buildings, equipment, etc."""

def test_depreciation_methods_disclosed():
    """Disclosure includes depreciation method and useful life"""

def test_revaluation_model_if_applicable():
    """Revaluation surplus disclosed if model used"""

def test_impairment_check():
    """Impairment losses disclosed if present"""
```

**Dependencies:** Same as HKRevenueAgent

---

#### 3.3: HKLeaseAgent - Lease Accounting (12 hours)

**File:** `genreport/markets/hk/agents/lease_agent.py`

**Accounting Standards:**
- HKFRS 16: Leases (for lessees and lessors)
- SME-FRS Section 20: Leases

**Functionality:**
- Identify leases (finance vs operating for SME, all capitalize for HKFRS 16)
- Calculate right-of-use assets and lease liabilities
- Determine discount rate (incremental borrowing rate)
- Generate disclosure covering:
  * Accounting policy for leases
  * Right-of-use assets by class
  * Lease liabilities maturity analysis
  * Lease expense (interest + depreciation)
  * Short-term and low-value lease exemptions
  * Future lease commitments

**DSPy Signature:**
```python
class GenerateLeaseDisclosure(dspy.Signature):
    """Generate HKFRS 16 / SME-FRS lease disclosure"""

    lease_data: dict = dspy.InputField(
        desc="Lease contracts, right-of-use assets, lease liabilities"
    )
    kb_standards: List[dict] = dspy.InputField(
        desc="Relevant KB chunks from HKFRS 16 or SME-FRS Section 20"
    )
    accounting_standard: str = dspy.InputField(desc="HKFRS 16 or SME-FRS Section 20")
    currency: str = dspy.InputField(desc="HKD")
    entity_type: str = dspy.InputField(desc="SME or non-SME")

    disclosure: str = dspy.OutputField(
        desc="Complete lease accounting disclosure"
    )
    completeness_score: float = dspy.OutputField()
    source_references: List[dict] = dspy.OutputField()
    required_disclosures_met: List[str] = dspy.OutputField()
```

**Test Cases (TDD):**
```python
def test_lease_agent_capitalizes_all_for_hkfrs16():
    """HKFRS 16: All leases capitalized (except short-term/low-value)"""

def test_lease_agent_finance_operating_for_sme():
    """SME-FRS: Finance leases capitalized, operating expensed"""

def test_maturity_analysis_disclosed():
    """Disclosure includes lease liability maturity analysis"""

def test_discount_rate_disclosed():
    """Incremental borrowing rate disclosed"""
```

**Dependencies:** Same as HKRevenueAgent

---

#### 3.4: HKInventoryAgent - Inventory Valuation (12 hours)

**File:** `genreport/markets/hk/agents/inventory_agent.py`

**Accounting Standards:**
- IAS 2: Inventories
- SME-FRS Section 13: Inventories

**Functionality:**
- Identify inventory categories (raw materials, WIP, finished goods)
- Determine cost formula (FIFO, weighted average)
- Check for NRV write-downs
- Generate disclosure covering:
  * Accounting policy for inventory
  * Cost formula used
  * Carrying amounts by category
  * Inventory write-downs to NRV
  * Inventory pledged as security

**DSPy Signature:**
```python
class GenerateInventoryDisclosure(dspy.Signature):
    """Generate IAS 2 / SME-FRS inventory disclosure"""

    inventory_data: dict = dspy.InputField(
        desc="Inventory balances, cost formula, NRV adjustments"
    )
    kb_standards: List[dict] = dspy.InputField(
        desc="Relevant KB chunks from IAS 2 or SME-FRS Section 13"
    )
    accounting_standard: str = dspy.InputField(desc="IAS 2 or SME-FRS Section 13")
    currency: str = dspy.InputField(desc="HKD")
    cost_formula: str = dspy.InputField(desc="FIFO or weighted average")

    disclosure: str = dspy.OutputField(
        desc="Complete inventory disclosure note"
    )
    completeness_score: float = dspy.OutputField()
    source_references: List[dict] = dspy.OutputField()
    required_disclosures_met: List[str] = dspy.OutputField()
```

**Test Cases (TDD):**
```python
def test_inventory_agent_discloses_cost_formula():
    """Disclosure states FIFO or weighted average"""

def test_inventory_categories_separated():
    """Raw materials, WIP, finished goods shown separately"""

def test_nrv_write_down_disclosed():
    """Write-downs to NRV disclosed if applicable"""

def test_inventory_pledged_disclosed():
    """Inventory pledged as security disclosed"""
```

**Dependencies:** Same as HKRevenueAgent

---

### Phase 4: Secure Orchestration (20 hours, Week 3)

#### 4.1: SecureOrchestrator - Agent Coordination (14 hours)

**File:** `genreport/core/orchestration/secure_orchestrator.py`

**Functionality:**
- Initialize with project_id, tenant_id, user_id
- Load project to determine jurisdiction
- Create market-specific agents via AgentFactory
- Package context from database with validation
- Determine which agents to trigger based on relationship map
- Execute agents in parallel (where possible)
- Aggregate agent outputs
- Handle partial failures gracefully
- Comprehensive audit logging

**Context Packaging:**
```python
def package_context(self) -> dict:
    """Package context with security validation"""

    # 1. Fetch data (all queries filtered by tenant_id)
    context = {
        "trial_balance": get_trial_balance(self.project_id, self.tenant_id),
        "general_ledger": get_general_ledger(self.project_id, self.tenant_id),
        "prior_year": get_prior_year(self.project_id, self.tenant_id),
        "relationship_map": get_relationship_map(self.project_id, self.tenant_id),
        "project_metadata": {
            "jurisdiction": self.project.jurisdiction,
            "accounting_standard": self.project.accounting_standard,
            "financial_year_end": self.project.financial_year_end,
            "entity_type": self.project.entity_type
        }
    }

    # 2. Validate no cross-tenant data
    validator = ContextValidator(self.tenant_id)
    if not validator.validate(context):
        raise SecurityError("Context validation failed: cross-tenant data detected")

    # 3. Check size limits (prevent huge prompts)
    if self._estimate_context_size(context) > 100_000:  # 100KB limit
        logger.warning("Context too large, truncating...")
        context = self._truncate_context(context)

    return context
```

**Agent Triggering Logic:**
```python
def _map_sections_to_agents(self, relationship_map: dict) -> List[Tuple[str, str]]:
    """Determine which agents to trigger based on relationship map"""

    triggers = []

    if relationship_map.get('has_revenue'):
        triggers.append(("revenue_recognition", "revenue"))

    if relationship_map.get('has_ppe'):
        triggers.append(("property_plant_equipment", "ppe"))

    if relationship_map.get('has_leases'):
        triggers.append(("leases", "lease"))

    if relationship_map.get('has_inventory'):
        triggers.append(("inventory", "inventory"))

    return triggers
```

**Test Cases (TDD):**
```python
def test_orchestrator_packages_valid_context():
    """Context passes ContextValidator"""

def test_orchestrator_raises_on_cross_tenant():
    """Cross-tenant data raises SecurityError"""

def test_orchestrator_triggers_correct_agents():
    """Only triggers agents for sections in relationship map"""

def test_orchestrator_handles_partial_failure():
    """If revenue agent fails, other agents still run"""

def test_orchestrator_audit_logs_all_operations():
    """Audit log entry for each agent execution"""

def test_orchestrator_context_size_limit():
    """Truncates context if too large"""

def test_orchestrator_returns_aggregated_results():
    """Output contains all agent results"""
```

**Database Impact:** None (uses existing models)

**Dependencies:**
- Requires: `AgentFactory`, `ContextValidator`, `AuditLogger`, database access
- Required by: API endpoints

---

#### 4.2: Integration with Existing Sprint 3 Components (6 hours)

**Updates to SecureKBRetriever:**
- Ensure jurisdiction filtering works correctly with agents
- Add agent-specific retrieval methods (e.g., `retrieve_by_topic()`)
- Optimize top_k for agent use cases (5-10 chunks recommended)

**Updates to Embedding Cache:**
- Ensure agent queries benefit from caching
- Monitor cache hit rate during agent execution

**Test Cases:**
```python
def test_agent_kb_retrieval_filtered_by_jurisdiction():
    """HK agent only gets HK standards"""

def test_agent_kb_retrieval_cached():
    """Repeated queries use cache"""

def test_agent_source_attribution_matches_retrieval():
    """Source references match actual KB chunks used"""
```

---

### Phase 5: API Endpoints (16 hours, Week 3)

#### 5.1: Report Generation API (12 hours)

**File:** `genreport/api/routers/reports.py`

**Endpoints:**

1. **POST /api/v1/reports/generate/{project_id}**
   - Initiate report generation (async via Celery)
   - Returns 202 Accepted with task_id
   - Rate limited: 100 calls/hour per tenant
   - Audit logged

2. **GET /api/v1/reports/status/{task_id}**
   - Get generation status (pending, running, completed, failed)
   - Returns progress percentage
   - Returns partial results if available

3. **GET /api/v1/reports/{report_id}**
   - Get complete generated report
   - Returns all sections with metadata
   - Includes completeness scores and source attribution

4. **GET /api/v1/reports/project/{project_id}**
   - List all reports for a project
   - Filtered by tenant_id
   - Pagination support

5. **DELETE /api/v1/reports/{report_id}**
   - Soft delete report
   - Admin only
   - Audit logged

**Test Cases (TDD):**
```python
def test_generate_report_returns_202_with_task_id():
    """Async initiation returns 202 Accepted"""

def test_generate_report_enforces_rate_limit():
    """101st call in hour raises 429"""

def test_generate_report_tenant_isolation():
    """Cannot generate for other tenant's project"""

def test_get_report_status():
    """Status endpoint returns progress"""

def test_get_report_complete():
    """Get endpoint returns all sections"""

def test_get_report_tenant_isolation():
    """Cannot access other tenant's report"""

def test_list_project_reports():
    """List endpoint returns all reports for project"""

def test_delete_report_admin_only():
    """Only admins can delete reports"""
```

**Dependencies:**
- Requires: `SecureOrchestrator`, `TenantRateLimiter`, Celery

---

#### 5.2: Background Task for Report Generation (4 hours)

**File:** `genreport/core/tasks/report_generation_tasks.py`

**Celery Task:**
```python
@celery_app.task(bind=True, max_retries=1)
def generate_report_task(
    self,
    project_id: int,
    tenant_id: str,
    user_id: int
):
    """Background task for report generation"""

    try:
        # Create orchestrator
        orchestrator = SecureOrchestrator(
            project_id=project_id,
            tenant_id=UUID(tenant_id),
            user_id=user_id
        )

        # Generate report
        results = await orchestrator.generate_report()

        # Save to database
        report = save_generated_report(project_id, tenant_id, results)

        # Audit log success
        AuditLogger.log_event(
            db=get_db(),
            event_type="REPORT_GENERATION",
            action="GENERATE",
            user_id=user_id,
            tenant_id=UUID(tenant_id),
            resource_type="generated_report",
            resource_id=report.id,
            status="SUCCESS"
        )

        return {"status": "completed", "report_id": report.id}

    except Exception as e:
        logger.error(f"Report generation failed: {str(e)}", exc_info=True)

        # Audit log failure
        AuditLogger.log_event(
            db=get_db(),
            event_type="REPORT_GENERATION",
            action="GENERATE",
            user_id=user_id,
            tenant_id=UUID(tenant_id),
            resource_type="generated_report",
            details={"error": str(e)},
            status="FAILURE"
        )

        # Retry once
        raise self.retry(exc=e, countdown=60)
```

**Test Cases:**
```python
def test_report_task_success():
    """Successful generation creates database record"""

def test_report_task_retries_on_failure():
    """Failed task retries once"""

def test_report_task_audit_logs():
    """Success and failure both audit logged"""
```

---

### Phase 6: Database Schema Updates (8 hours, Week 3)

#### 6.1: Database Models

**File:** `genreport/core/database/models.py` (update)

**New Models:**

```python
class GeneratedReport(Base):
    """Store complete generated reports"""
    __tablename__ = "generated_reports"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    generated_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    jurisdiction = Column(String(10), nullable=False)  # HK, SG, AU
    accounting_standard = Column(String(50), nullable=False)  # HKFRS, SME-FRS

    overall_completeness = Column(Float, nullable=True)  # Average across sections
    generation_time_seconds = Column(Float, nullable=True)
    cost_usd = Column(Float, nullable=True)

    status = Column(String(20), default="generating")  # generating, completed, failed
    error_message = Column(Text, nullable=True)

    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    sections = relationship("ReportSection", back_populates="report", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_generated_reports_tenant", "tenant_id"),
        Index("idx_generated_reports_project", "project_id"),
        Index("idx_generated_reports_status", "status"),
    )


class ReportSection(Base):
    """Individual report sections (one per agent)"""
    __tablename__ = "report_sections"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    report_id = Column(Integer, ForeignKey("generated_reports.id", ondelete="CASCADE"), nullable=False)

    section_name = Column(String(100), nullable=False)  # revenue_recognition, ppe, etc.
    agent_name = Column(String(100), nullable=False)  # HKRevenueAgent, etc.

    content = Column(Text, nullable=False)  # Generated disclosure
    standard_used = Column(String(100), nullable=False)  # HKFRS 15, IAS 16, etc.

    completeness_score = Column(Float, nullable=True)  # 0.0 to 1.0
    required_disclosures_met = Column(JSONB, nullable=True)  # List of checklist items

    pii_detected = Column(Boolean, default=False)
    pii_types = Column(JSONB, nullable=True)  # List of PII types found

    execution_time_seconds = Column(Float, nullable=True)
    cost_usd = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    report = relationship("GeneratedReport", back_populates="sections")
    source_references = relationship("SourceReference", back_populates="section", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_report_sections_tenant", "tenant_id"),
        Index("idx_report_sections_report", "report_id"),
    )


class SourceReference(Base):
    """KB chunks used for each section"""
    __tablename__ = "source_references"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    section_id = Column(Integer, ForeignKey("report_sections.id", ondelete="CASCADE"), nullable=False)

    kb_chunk_id = Column(Integer, ForeignKey("kb_chunks.id"), nullable=False)
    similarity_score = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    section = relationship("ReportSection", back_populates="source_references")
    kb_chunk = relationship("KBChunk")

    __table_args__ = (
        Index("idx_source_references_tenant", "tenant_id"),
        Index("idx_source_references_section", "section_id"),
    )


class AgentExecution(Base):
    """Audit trail for agent executions"""
    __tablename__ = "agent_executions"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    report_id = Column(Integer, ForeignKey("generated_reports.id"), nullable=False)

    agent_name = Column(String(100), nullable=False)
    section_name = Column(String(100), nullable=False)

    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    status = Column(String(20), nullable=False)  # running, completed, failed
    error_message = Column(Text, nullable=True)

    context_size_bytes = Column(Integer, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    cost_usd = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_agent_executions_tenant", "tenant_id"),
        Index("idx_agent_executions_report", "report_id"),
    )
```

**Migration File:** `alembic/versions/20251018_1800-add_agent_execution_models.py`

**Test Cases:**
```python
def test_generated_report_cascade_delete():
    """Deleting report deletes sections and references"""

def test_report_section_stores_completeness():
    """Completeness score stored correctly"""

def test_source_reference_links_to_kb_chunk():
    """FK relationship to kb_chunks works"""

def test_agent_execution_audit_trail():
    """Agent execution creates audit record"""
```

---

### Phase 7: Testing & Quality Assurance (18 hours, Week 3.5)

#### 7.1: End-to-End Integration Tests (8 hours)

**File:** `tests/integration/test_report_generation.py`

**Test Scenarios:**

```python
def test_e2e_generate_hk_revenue_report():
    """Complete workflow: API → Celery → Agent → Database"""

def test_e2e_multiple_sections():
    """Report with revenue + PPE + lease sections"""

def test_e2e_completeness_above_90():
    """All sections have completeness >0.90"""

def test_e2e_source_attribution():
    """All sections have source references"""

def test_e2e_pii_redaction():
    """PII is redacted in final output"""

def test_e2e_generation_time_under_3min():
    """Complete report generated in <3 minutes"""

def test_e2e_cost_under_50_cents():
    """Total cost <$0.50"""
```

---

#### 7.2: Security Tests (6 hours)

**File:** `tests/security/test_agent_security.py`

**Test Scenarios:**

```python
def test_context_validation_prevents_cross_tenant():
    """Cross-tenant data raises SecurityError"""

def test_pii_detection_all_types():
    """All PII patterns detected"""

def test_rate_limiting_enforced():
    """101st call raises HTTPException(429)"""

def test_audit_logging_complete():
    """All agent executions audit logged"""

def test_agent_tenant_isolation():
    """Agent cannot access other tenant's data"""
```

---

#### 7.3: Performance Tests (4 hours)

**File:** `tests/performance/test_agent_performance.py`

**Test Scenarios:**

```python
def test_revenue_agent_execution_time():
    """Single agent <30 seconds"""

def test_parallel_agent_execution():
    """4 agents in parallel <60 seconds"""

def test_context_packaging_time():
    """Context packaging <5 seconds"""

def test_kb_retrieval_time():
    """KB retrieval <500ms per agent"""
```

---

## Implementation Schedule

### Week 1 (40 hours)
- **Day 1-2:** Phase 1.1-1.3 (Security Foundation) - 24h
- **Day 3-5:** Phase 2.1-2.3 (Base Agent Infrastructure) - 28h
- **Total:** 52h (overage handled by 2-3 developers)

### Week 2 (40 hours)
- **Day 1-2:** Phase 3.1-3.2 (HKRevenueAgent, HKPPEAgent) - 24h
- **Day 3-5:** Phase 3.3-3.4 (HKLeaseAgent, HKInventoryAgent) - 24h
- **Total:** 48h

### Week 3 (40 hours)
- **Day 1-2:** Phase 4 (SecureOrchestrator) - 20h
- **Day 3-4:** Phase 5 (API Endpoints) - 16h
- **Day 5:** Phase 6 (Database Schema) - 8h
- **Total:** 44h

### Week 3.5 (14 hours)
- **Day 1-2:** Phase 7 (Testing & QA) - 18h
- **Total:** 18h

**Grand Total:** 162 hours (fits within 3.5 weeks with 2-3 developers)

---

## Risk Mitigation

### Technical Risks

1. **Agent Quality <90%**
   - Mitigation: Extensive KB content, DSPy optimization, human review loop
   - Contingency: Lower threshold to 85% for Sprint 4, optimize in Sprint 5

2. **Generation Time >3min**
   - Mitigation: Parallel agent execution, context size limits, caching
   - Contingency: Increase timeout to 5min, optimize in production

3. **Cost >$0.50 per report**
   - Mitigation: Use Gemini (cheaper), limit context size, cache embeddings
   - Contingency: Accept higher cost initially, optimize with DSPy training

4. **Cross-Tenant Data Leakage**
   - Mitigation: ContextValidator with 100% test coverage, mandatory validation
   - Contingency: IMMEDIATE FIX if detected, security audit, incident response

### Schedule Risks

1. **Agent Development Takes Longer**
   - Mitigation: Use @dspy-expert agent for each implementation
   - Contingency: Reduce to 3 agents (Revenue, PPE, Inventory), add Lease in Sprint 5

2. **Security Testing Reveals Issues**
   - Mitigation: Security-first approach, early validation
   - Contingency: Extend sprint by 2-3 days if critical security issues found

---

## Definition of Done

Sprint 4 is complete when ALL of the following are met:

### Hybrid Architecture ✅
- [ ] Base agent classes work for any market (no hardcoded jurisdictions)
- [ ] Agent factory creates market-specific agents dynamically
- [ ] 4 HK agents implemented (Revenue, PPE, Lease, Inventory)
- [ ] No hardcoded jurisdictions in `core/orchestration/`
- [ ] Code review confirms architecture compliance

### Security ✅
- [ ] ContextValidator prevents cross-tenant data (100% test coverage)
- [ ] PIIDetector detects and redacts all PII types (100% test coverage)
- [ ] Rate limiting enforced per tenant (tested)
- [ ] Audit logging for all agent operations (tested)
- [ ] Security tests: 100% passing

### Core Functionality ✅
- [ ] DSPy agents generate quality disclosures (completeness >90%)
- [ ] Context packaging with size limits (<100KB)
- [ ] Error handling and retry logic (1 retry)
- [ ] Source attribution working (KB chunk IDs in output)
- [ ] End-to-end generation <3min (tested)
- [ ] Cost per report <$0.50 (tested)

### Quality ✅
- [ ] Agent quality: >90% completeness score (average across all sections)
- [ ] Required disclosures: >95% present (checklist validation)
- [ ] Unit tests: 100% passing (TDD approach)
- [ ] Integration tests: 100% passing (end-to-end workflows)
- [ ] Security tests: 100% passing (cross-tenant, PII, rate limiting)
- [ ] Performance tests: 100% passing (time, cost)
- [ ] Code coverage: >80% for agent code

### Documentation ✅
- [ ] Architecture document (this file)
- [ ] Implementation guide for each agent
- [ ] API endpoint documentation
- [ ] Database schema documentation
- [ ] Security testing guide
- [ ] Deployment guide

---

## Next Steps After Sprint 4

**Sprint 5: Review Interface & Export (2.5 weeks)**
- Market-aware UI (currency formatting, date formatting)
- Side-by-side comparison (generated vs manual)
- Market-specific DOCX templates
- XSS/CSRF protection
- Export to PDF, DOCX, HTML

**Sprint 6: Production Deployment (3.5 weeks)**
- Penetration testing
- Performance optimization
- Monitoring and alerting
- Multi-region deployment (HK, SG, AU)
- Compliance validation (ISO 27001, SOC 2)

---

**Document Status:** ✅ READY FOR IMPLEMENTATION
**Next Action:** Review with user, then begin Phase 1 (Security Foundation)
**Prepared By:** Solution Architect
**Date:** 2025-10-18
