# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**GenReport** is an AI-powered audit report generation system designed for multi-market support (Hong Kong, Singapore, Australia) with enterprise-grade security and compliance. The system uses LLM-powered agents to analyze Excel working papers and generate audit disclosures following jurisdiction-specific accounting standards (HKFRS, SME-FRS, SFRS, AASB).

**Current Status:** Planning Phase - Implementation follows a 6-sprint, 19-week master plan
**Architecture:** Pragmatic Hybrid Architecture with tenant isolation and multi-region support

## Core Architecture Principles

### Hybrid Architecture Pattern

The codebase follows a **strict separation** between generic (market-agnostic) and market-specific code:

```
genreport/
├── core/              # GENERIC - Works for ANY market
│   ├── parsing/       # Excel processing (market-agnostic)
│   ├── orchestration/ # Agent orchestration (base classes)
│   ├── retrieval/     # RAG system (jurisdiction-filtered)
│   ├── security/      # Tenant isolation, encryption, audit
│   └── database/      # Multi-tenant data models
│
├── markets/           # MARKET-SPECIFIC implementations
│   ├── hk/           # Hong Kong (HKFRS, SME-FRS)
│   ├── sg/           # Singapore (future)
│   └── au/           # Australia (future)
│
├── api/              # FastAPI application
└── tests/
    ├── core/         # Generic tests
    └── markets/      # Market-specific tests
```

**CRITICAL RULES:**
- **NEVER** hardcode jurisdiction-specific logic in `core/`
- **ALWAYS** use dependency injection for market configs
- **NO** direct imports from `markets/` in `core/` modules
- Market-specific code lives ONLY in `markets/{jurisdiction}/`

### Multi-Tenant Isolation

**Every table MUST have `tenant_id`** for complete tenant isolation:
- All database queries MUST filter by `tenant_id`
- Use `ContextVar[UUID]` for tenant context throughout request lifecycle
- Validate context to prevent cross-tenant data leakage
- Audit log ALL data access events

### Security-First Design

The system implements defense-in-depth:
1. **Application Layer:** XSS/CSRF protection, input sanitization, rate limiting
2. **Authentication Layer:** JWT with refresh tokens, RBAC
3. **Tenant Isolation:** Middleware-enforced tenant context
4. **Encryption Layer:** KMS-managed keys, field-level encryption
5. **Audit Layer:** Comprehensive logging of all security events

## Database Schema Conventions

### Required Fields for All Tables
```sql
CREATE TABLE example_table (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    -- table-specific fields
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_example_tenant ON example_table(tenant_id);
```

### Multi-Market Fields
Projects and market-aware tables include:
- `jurisdiction` VARCHAR(10) - 'HK', 'SG', 'AU'
- `accounting_standard` VARCHAR(50) - 'HKFRS', 'SME-FRS', 'SFRS', 'AASB'

## Using Specialized Sub-Agents

This project leverages specialized agents for different implementation tasks. **ALWAYS** use the appropriate sub-agent for complex work:

### @solution-architect - Architecture & Implementation Planning

**USE FOR:**
- Designing implementation plans for new features or sprints
- Breaking down complex business requirements into technical components
- Creating architecture decision records (ADRs)
- Refactoring plans following SOLID principles
- System design and component interaction planning

**EXAMPLE USAGE:**
```
User: "We need to implement Sprint 1 - Foundation and Multi-tenant Infrastructure"

Claude: I'll use the @solution-architect agent to create a detailed technical implementation plan.

@solution-architect
Create a comprehensive implementation plan for Sprint 1 including:
- Multi-tenant database schema with tenant isolation
- JWT authentication with refresh tokens
- Tenant context middleware
- Encryption service with KMS integration
- Audit logging infrastructure
- Security headers and rate limiting

Reference: docs/sprint_1_foundation.md for requirements
Follow: Clean Architecture, SOLID principles, TDD approach
```

**DELIVERABLES:**
- Step-by-step implementation plan
- Component dependencies and initialization order
- Test strategy for each component
- Architecture decision rationale

### @dspy-expert - DSPy Program Development

**USE FOR:**
- Designing and implementing DSPy signatures with Pydantic models
- Creating DSPy modules (ChainOfThought, ReAct, etc.)
- Optimizing DSPy programs with evaluation metrics
- Composing complex multi-agent DSPy workflows
- Troubleshooting DSPy-specific issues

**EXAMPLE USAGE:**
```
User: "Implement the Revenue Recognition Agent using DSPy for Hong Kong market"

Claude: I'll use the @dspy-expert agent to design the DSPy-based revenue agent.

@dspy-expert
Design and implement a DSPy-based Revenue Recognition Agent with:
- Input: trial balance data, accounting context, jurisdiction (HK)
- Output: HKFRS 15 or SME-FRS compliant revenue disclosure
- Requirements:
  * Use Pydantic models for type safety
  * Include source attribution
  * Generate completeness score
  * Support both HKFRS 15 and SME-FRS based on entity type
  * Follow SOLID principles with proper composition

Reference: markets/hk/agents/ for market-specific implementation
Context: core/orchestration/base_agent.py for base class pattern
```

**DELIVERABLES:**
- DSPy signatures with proper Pydantic models
- Module composition with error handling
- Evaluation metrics for optimization
- Integration with retriever and market config

### @react-best-practices-expert - React/Frontend Development

**USE FOR:**
- Implementing market-aware UI components (Sprint 5)
- Managing useEffect for data fetching and side effects
- Creating reusable, composable components
- Implementing XSS/CSRF protection in React
- Performance optimization (memoization, virtualization)

**EXAMPLE USAGE:**
```
User: "Create the report review interface with market-aware formatting"

Claude: I'll use the @react-best-practices-expert agent for proper React implementation.

@react-best-practices-expert
Implement a report review interface with:
- Market-aware currency and date formatting (HKD/SGD/AUD)
- Side-by-side comparison (generated vs. manual sections)
- XSS protection with DOMPurify
- CSRF token handling
- Proper useEffect management for data fetching
- Modular, composable component design

Requirements:
- No prop drilling (use context for market config)
- Memoize expensive formatting operations
- Handle loading/error states properly
```

### @bug-hunter - Bug Investigation & Resolution

**USE FOR:**
- Investigating complex bugs and mysterious errors
- Cross-tenant data leakage issues
- Performance degradation problems
- Race conditions in async operations
- Integration failures between components

**EXAMPLE USAGE:**
```
User: "Users are seeing data from other tenants intermittently"

Claude: This is a critical security issue. I'll use the @bug-hunter agent to investigate.

@bug-hunter
Investigate tenant isolation breach:
- Symptom: Users intermittently see data from other tenants
- Context: Multi-tenant FastAPI application with tenant_id filtering
- Components to check:
  * Tenant middleware (core/security/tenant_context.py)
  * Database queries in repositories
  * Context propagation in async operations
  * Celery background tasks

Provide: Root cause analysis, reproduction steps, and recommended fix
```

### @security-audit - Security Analysis & Testing

**USE FOR:**
- Security code reviews (especially Sprint 1, 6)
- Penetration testing preparation
- OWASP Top 10 vulnerability assessment
- Compliance validation (ISO 27001, SOC 2)
- Security test case design

**EXAMPLE USAGE:**
```
User: "Review the file upload security implementation"

Claude: I'll use security audit capabilities to review this critical component.

@security-audit
Security review of file upload implementation:
- Components: api/routers/files.py, core/security/file_encryption.py
- Check for:
  * File type validation (extension + magic bytes)
  * File size limits enforcement
  * Encryption at rest with tenant-specific keys
  * Path traversal vulnerabilities
  * Macro detection in Excel files
  * Audit logging completeness

Provide: Vulnerability assessment and remediation recommendations
```

### @code-reviewer - Code Quality & Best Practices

**USE FOR:**
- Reviewing completed implementations against requirements
- Ensuring SOLID principles adherence
- Validating test coverage
- Checking for code smells and anti-patterns
- Verifying hybrid architecture separation (core/ vs markets/)

**EXAMPLE USAGE:**
```
User: "Review the market config factory implementation"

Claude: I'll use the @code-reviewer agent to ensure quality.

@code-reviewer
Review: core/orchestration/agent_factory.py and markets/hk/config.py

Validate:
- No hardcoded jurisdictions in core/
- Proper dependency injection pattern
- SOLID principles compliance (especially OCP, DIP)
- Test coverage >80%
- Error handling for unsupported jurisdictions
- Documentation completeness
```

### Agent Selection Decision Tree

```
START: What type of task?

├─ Planning/Design
│  └─ Use @solution-architect
│     - Feature implementation plans
│     - Architecture decisions
│     - Refactoring strategies
│
├─ DSPy Development
│  └─ Use @dspy-expert
│     - Agent signatures & modules
│     - RAG system design
│     - LLM program optimization
│
├─ React/Frontend
│  └─ Use @react-best-practices-expert
│     - UI components
│     - State management
│     - Performance optimization
│
├─ Bug/Issue
│  └─ Use @bug-hunter
│     - Systematic investigation
│     - Root cause analysis
│     - Reproduction steps
│
├─ Security Concern
│  └─ Use @security-audit
│     - Vulnerability assessment
│     - Compliance validation
│     - Security testing
│
└─ Code Review
   └─ Use @code-reviewer
      - Quality validation
      - Best practices check
      - Test coverage review
```

## Specialized Agent Usage

When implementing complex features, use specialized sub-agents for their domain expertise:

### When to Use Sub-Agents

**@dspy-expert** - Use for all DSPy-related code:
- Designing DSPy signatures with Pydantic models
- Creating DSPy modules and programs
- Implementing agent chains and retrievers
- Optimizing DSPy programs with metrics
- Debugging DSPy-specific issues

Example:
```
User: "Implement the revenue recognition agent using DSPy"
Assistant: [Invokes @dspy-expert with context about HK market requirements]
```

**@solution-architect** - Use for implementation planning:
- Breaking down complex business requirements into technical components
- Designing Clean Architecture solutions
- Creating TDD implementation strategies
- Planning refactoring approaches
- Reviewing architecture for SOLID principles

Example:
```
User: "Plan the implementation of Sprint 2 Excel processing"
Assistant: [Invokes @solution-architect with Sprint 2 requirements]
```

**@bug-hunter** - Use for systematic debugging:
- Investigating production issues
- Root cause analysis for complex bugs
- Performance problem diagnosis
- Integration failure investigation

**@security-audit** - Use for security reviews:
- OWASP Top 10 analysis
- Compliance gap analysis (ISO 27001, SOC 2)
- Penetration testing review
- Security architecture assessment

### Agent Invocation Pattern

1. **Identify the domain:** Determine which specialized agent best fits the task
2. **Provide context:** Include relevant files, requirements, and constraints
3. **Receive expert guidance:** Agent provides domain-specific implementation
4. **Integrate solution:** Apply the agent's recommendations to the codebase

### Example Workflow

**Implementing a DSPy Agent:**
```
1. User: "Create the HK revenue recognition agent"
2. Claude: [Invokes @dspy-expert]
3. Expert provides: DSPy signature, module structure, optimization strategy
4. Claude: Implements code following expert guidance
5. Claude: [Invokes @dspy-expert for review if needed]
```

**Planning Major Features:**
```
1. User: "Implement the knowledge base RAG system"
2. Claude: [Invokes @solution-architect]
3. Architect provides: Component breakdown, interfaces, testing strategy
4. Claude: Implements following the plan with TDD
5. Result: Clean, testable, SOLID-compliant implementation
```

## Development Workflow

### Setting Up Development Environment

```bash
# Python 3.13+ required (see pyproject.toml)
uv venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install dependencies (when requirements.txt exists)
uv pip install -r requirements.txt

# Database setup (PostgreSQL with PGVector)
# Configure DATABASE_URL in .env
alembic upgrade head

# Redis (for caching and Celery)
# Configure REDIS_URL in .env

# Run migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=genreport --cov-report=html

# Run specific test categories
pytest tests/core/          # Generic tests only
pytest tests/markets/hk/    # Hong Kong-specific tests
pytest -m security          # Security tests only

# Run security validation
pytest tests/test_tenant_isolation.py -v
```

### Common Development Tasks

**Create a new market-specific agent:**
1. **Use @dspy-expert** to design the DSPy signature and module
2. **Use @solution-architect** to plan the integration with base classes
3. Implement base class in `core/orchestration/base_agent.py` (if needed)
4. Create market implementation in `markets/{jurisdiction}/agents/`
5. Register in `AgentFactory.create_agents()` method
6. Add tests in `tests/markets/{jurisdiction}/`
7. **Use @code-reviewer** to validate implementation quality

**Add a new market (e.g., Singapore):**
1. **Use @solution-architect** to create implementation plan for new market
2. Create `markets/sg/` directory structure
3. Define `SGMarketConfig` in `markets/sg/config.py`
4. Update `get_market_config()` factory function
5. **Use @dspy-expert** to implement market-specific agents
6. Implement validators and templates
7. Update database migrations to support SG jurisdiction
8. Add comprehensive test coverage
9. **Use @code-reviewer** to ensure no core/ contamination

**Implement encryption for sensitive fields:**
```python
from core.security.encryption import EncryptedString

class SensitiveModel(Base):
    sensitive_field = Column(EncryptedString(255))
```

**Debug tenant isolation issues:**
1. **Use @bug-hunter** to investigate systematically
2. Check tenant context middleware
3. Validate database query filters
4. Review async operation context propagation
5. Run tenant isolation test suite

**Implement a new sprint:**
1. **Use @solution-architect** to create detailed implementation plan
2. Review sprint documentation in `docs/sprint_N_*.md`
3. Create architecture doc in `docs/architecture/YYYY-MM-DD-sprint-N.md`
4. Implement components using appropriate agents (@dspy-expert, etc.)
5. Write tests (TDD approach)
6. **Use @code-reviewer** for quality validation
7. **Use @security-audit** if sprint involves security components
8. Update implementation guides in `docs/guides/`

## Security Best Practices

### Tenant Context Enforcement

**ALWAYS** use tenant context in database queries:
```python
from core.security.tenant_context import get_current_tenant

def get_project(db: Session, project_id: int):
    tenant_id = get_current_tenant()
    return db.query(Project).filter(
        Project.id == project_id,
        Project.tenant_id == tenant_id  # REQUIRED
    ).first()
```

### Audit Logging

Log ALL security-relevant events:
```python
from core.security.audit_logger import AuditLogger

AuditLogger.log_event(
    db=db,
    event_type="DATA_ACCESS",
    action="READ",
    user_id=current_user.id,
    tenant_id=tenant_id,
    resource_type="project",
    resource_id=project_id,
    ip_address=request.client.host
)
```

### Input Validation

- Strip Excel formulas before processing
- Validate file types using both extension AND magic bytes
- Detect and block macros in uploaded files
- Sanitize all user input for XSS prevention
- Enforce file size limits (50MB for Excel files)

### PII Detection

Scan generated content for PII before storage:
```python
from core.security.pii_detector import PIIDetector

detector = PIIDetector()
content = detector.redact(generated_text)
```

## Sprint Implementation Guide

The project follows a **6-sprint master plan** documented in `docs/master_sprint_plan.md`:

1. **Sprint 1 (4.5 weeks):** Foundation + Multi-tenant infrastructure + Security
2. **Sprint 2 (2.5 weeks):** Excel processing with encryption
3. **Sprint 3 (2.5 weeks):** Knowledge Base with jurisdiction filtering
4. **Sprint 4 (3.5 weeks):** AI agents with market-awareness
5. **Sprint 5 (2.5 weeks):** Review interface with market-specific templates
6. **Sprint 6 (3.5 weeks):** Production deployment + penetration testing

### Sprint Implementation Workflow (Using Sub-Agents)

**Phase 1: Planning**
1. Read detailed sprint documentation in `docs/sprint_N_*.md`
2. **Use @solution-architect** to create comprehensive implementation plan
   - Break down sprint into components
   - Identify dependencies and initialization order
   - Create test strategy
   - Plan architecture decision records

**Phase 2: Architecture Documentation**
3. Create architecture doc in `docs/architecture/YYYY-MM-DD-sprint-N-*.md`
   - Document design decisions and rationale
   - Define component interfaces
   - Specify security requirements
   - Include database schema changes

**Phase 3: Implementation**
4. Implement components using specialized agents:
   - **@dspy-expert** for AI agents and RAG components (Sprint 3, 4)
   - **@react-best-practices-expert** for UI components (Sprint 5)
   - **@security-audit** for security components (Sprint 1, 6)
5. Write tests BEFORE implementation (TDD)
6. Follow Definition of Done checklist exactly

**Phase 4: Quality Assurance**
7. **Use @code-reviewer** to validate:
   - SOLID principles adherence
   - Test coverage >80%
   - Hybrid architecture separation (no core/ contamination)
   - Security best practices
8. **Use @security-audit** to verify:
   - Tenant isolation (Sprint 1, 2, 3, 4)
   - Encryption implementation (Sprint 1, 2)
   - Input validation (Sprint 2, 5)
   - OWASP Top 10 compliance (Sprint 6)

**Phase 5: Documentation**
9. Update implementation guides in `docs/guides/YYYY-MM-DD-*.md`
10. Create debugging journal if issues were encountered

### Sprint-Specific Agent Recommendations

**Sprint 1 (Foundation + Security):**
- Primary: @solution-architect (architecture planning)
- Required: @security-audit (multi-tenant isolation, encryption)
- Review: @code-reviewer (middleware, security components)

**Sprint 2 (Excel Processing):**
- Primary: @solution-architect (two-phase parsing design)
- Required: @dspy-expert (LLM parsing signatures)
- Security: @security-audit (file validation, sanitization)

**Sprint 3 (Knowledge Base):**
- Primary: @dspy-expert (RAG system, embeddings)
- Planning: @solution-architect (vector DB schema)
- Security: @security-audit (jurisdiction filtering, access control)

**Sprint 4 (AI Agents):**
- Primary: @dspy-expert (agent signatures, modules, composition)
- Planning: @solution-architect (agent factory pattern)
- Security: @security-audit (PII detection, context validation)
- Review: @code-reviewer (hybrid architecture compliance)

**Sprint 5 (Frontend):**
- Primary: @react-best-practices-expert (UI components, state management)
- Planning: @solution-architect (component architecture)
- Security: @security-audit (XSS/CSRF protection)

**Sprint 6 (Production):**
- Primary: @security-audit (penetration testing, compliance)
- Planning: @solution-architect (deployment architecture)
- Review: @code-reviewer (final quality check)

## Testing Requirements

### Coverage Targets
- Unit tests: >80% coverage required
- Security tests: 100% coverage for isolation and encryption
- Integration tests: All API endpoints with tenant context

### Security Test Requirements
```python
# MANDATORY security tests for all features:
def test_tenant_isolation():
    """Ensure no cross-tenant data access"""

def test_context_validation():
    """Ensure context contains no mixed tenant data"""

def test_audit_logging():
    """Ensure security events are logged"""
```

### Market-Agnostic Validation
```python
def test_no_hardcoded_jurisdictions_in_core():
    """Ensure core/ has no market-specific code"""
    for file in get_python_files('core/'):
        content = read_file(file)
        assert 'Hong Kong' not in content
        assert 'HKFRS' not in content
        assert 'Singapore' not in content
```

## Key Implementation Patterns

### Agent Factory Pattern
```python
# core/orchestration/agent_factory.py
class AgentFactory:
    @staticmethod
    def create_agents(jurisdiction: str, tenant_id: UUID, user_id: int):
        config = get_market_config(jurisdiction)
        retriever = SecureKBRetriever(jurisdiction, tenant_id, user_id)

        if jurisdiction == "HK":
            from markets.hk.agents import HKRevenueAgent
            return {"revenue": HKRevenueAgent(config, retriever, tenant_id)}
        elif jurisdiction == "SG":
            # Future implementation
            pass
```

### Secure Context Packaging
```python
class SecureOrchestrator:
    def package_context(self) -> dict:
        context = {
            "trial_balance": get_data(self.project_id, self.tenant_id),
            "general_ledger": get_data(self.project_id, self.tenant_id),
        }

        # MANDATORY: Validate no cross-tenant data
        validator = ContextValidator(self.tenant_id)
        if not validator.validate(context):
            raise SecurityError("Cross-tenant data detected")

        return context
```

## Documentation Standards

Follow the structured documentation approach defined in global CLAUDE.md:

```
docs/
├── architecture/            # Design decisions (create BEFORE implementation)
│   └── YYYY-MM-DD-topic.md
├── guides/                  # Implementation guides (create DURING development)
│   └── YYYY-MM-DD-topic.md
└── reports/                 # Status reports
    └── YYYY-MM-DD-topic.md

debugging_journals/          # MANDATORY after fixing bugs
└── YYYY-MM-DD-issue-description.md
```

**When implementing major features:**
1. Create architecture doc BEFORE coding
2. Update implementation guides DURING development
3. Create debugging journal if fixing bugs
4. Review and update existing docs when making changes

## Performance Targets

- Report generation: <3 minutes end-to-end
- API response time: <200ms (auth endpoints)
- Database query time: <100ms (with proper indexes)
- Excel parsing: <45 seconds per workbook
- Cost per report: <$0.50 (LLM costs)

## Compliance Requirements

The system must maintain compliance readiness for:
- **ISO 27001:** Multi-tenant isolation, encryption, audit logging
- **SOC 2 Type II:** Security controls, monitoring, incident response
- **GDPR:** Data residency, right to deletion, data portability
- **PDPA (HK/SG):** Local data residency enforcement
- **Privacy Act (AU):** Disclosure controls

## Error Handling

Follow these patterns for consistent error handling:

```python
# API endpoints
@router.post("/endpoint")
async def endpoint(tenant_id: UUID = Depends(get_current_tenant)):
    try:
        result = process_data()

        # Audit success
        AuditLogger.log_event(db, "EVENT", "ACTION", tenant_id=tenant_id, status="SUCCESS")

        return result
    except ValidationError as e:
        logger.warning(f"Validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except SecurityError as e:
        logger.error(f"Security violation: {e}")
        AuditLogger.log_event(db, "SECURITY_VIOLATION", "ACTION", tenant_id=tenant_id, status="FAILURE")
        raise HTTPException(status_code=403, detail="Access denied")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
```

## Agent Collaboration Best Practices

### When to Use Multiple Agents

**Sequential Agent Usage (Recommended):**
```
1. @solution-architect → Create implementation plan
2. @dspy-expert → Implement DSPy components
3. @code-reviewer → Review implementation quality
4. @security-audit → Validate security (if applicable)
```

**Example Multi-Agent Workflow:**
```
User: "Implement the Revenue Recognition Agent for Hong Kong"

Claude:
Step 1: I'll use @solution-architect to plan the implementation
  @solution-architect
  Plan implementation for HK Revenue Recognition Agent:
  - Base class design with dependency injection
  - DSPy signature structure
  - Integration with retriever and market config
  - Test strategy (unit, integration, security)
  Reference: docs/sprint_4_agents.md

Step 2: I'll use @dspy-expert to implement the DSPy components
  @dspy-expert
  Implement DSPy Revenue Recognition Agent based on plan from @solution-architect
  - Create Pydantic models for input/output
  - Design signature with proper field descriptions
  - Implement module composition
  - Add error handling and validation

Step 3: I'll use @code-reviewer to validate the implementation
  @code-reviewer
  Review implementation of HKRevenueAgent:
  - Verify SOLID principles compliance
  - Check test coverage >80%
  - Validate no hardcoded jurisdictions
  - Ensure proper error handling

Step 4: I'll use @security-audit to check security aspects
  @security-audit
  Security review of HKRevenueAgent:
  - Verify PII detection and redaction
  - Check context validation (no cross-tenant data)
  - Validate source attribution security
```

### Providing Context to Agents

**ALWAYS include:**
1. **Relevant files:** Provide full file paths for context
2. **Sprint documentation:** Reference `docs/sprint_N_*.md`
3. **Architecture constraints:** Hybrid architecture rules, security requirements
4. **Existing patterns:** Point to similar implementations

**GOOD Agent Invocation:**
```
@dspy-expert
Implement DSPy signature for Excel worksheet analysis (Sprint 2)

Context:
- Sprint doc: docs/sprint_2_excel_processor.md (two-phase LLM parsing)
- Base pattern: core/parsing/preliminary_scanner.py (existing structure)
- Input: List of worksheet names, coding patterns
- Output: Worksheet analysis with importance scores

Requirements:
- Use Pydantic models for type safety
- Follow existing CodingSystemAnalyzer pattern
- Must be market-agnostic (no HK-specific logic)
- Cost target: <$0.15 per workbook
```

**BAD Agent Invocation:**
```
@dspy-expert
Create a DSPy thing for worksheets
```

### Agent Communication Pattern

Agents return results to Claude. Claude should:
1. **Summarize** the agent's findings for the user
2. **Apply** the recommendations from the agent
3. **Chain** to next agent if needed
4. **Document** the decisions made

**Example:**
```
Claude: The @solution-architect agent has created a comprehensive plan with
5 main components and identified 3 critical dependencies. Here's the summary:
[summarize key points]

Now I'll proceed with implementing the first component using @dspy-expert...
```

## Critical Reminders

1. **NEVER** skip tenant_id in database queries
2. **ALWAYS** validate file types using magic bytes, not just extensions
3. **ALWAYS** encrypt files at rest using tenant-specific keys
4. **NEVER** log sensitive data (PII, credentials, tokens)
5. **ALWAYS** use the agent factory pattern for market-specific agents
6. **NEVER** import from `markets/` in `core/` modules
7. **ALWAYS** write security tests alongside feature tests
8. **NEVER** commit secrets or credentials to version control
9. **ALWAYS** use appropriate sub-agents for complex implementation tasks
10. **ALWAYS** provide sufficient context when invoking agents

## Resource References

- Master Sprint Plan: `docs/master_sprint_plan.md`
- Sprint Details: `docs/sprint_N_*.md` (N=1-6)
- Database Schema: See Sprint 1 documentation
- Security Architecture: See Sprint 1 and Sprint 6 documentation
- Market Config Examples: `markets/hk/config.py`
