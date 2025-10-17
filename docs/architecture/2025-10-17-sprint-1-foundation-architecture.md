# Sprint 1 Foundation Architecture

**Date:** 2025-10-17
**Status:** In Progress
**Sprint:** Sprint 1 - Foundation & Multi-Tenant Infrastructure

## Overview

This document captures the architectural decisions and implementation details for Sprint 1, establishing the foundation for the GenReport AI-powered audit report generation system.

## Architecture Decisions

### 1. Hybrid Architecture Pattern

**Decision:** Strict separation between generic (core/) and market-specific (markets/) code

**Rationale:**
- Enables rapid market expansion (3-4 weeks vs 12 weeks per new market)
- Single codebase for all markets reduces maintenance burden
- Shared improvements benefit all markets
- Zero code duplication across markets

**Implementation:**
```
genreport/
├── core/              # Generic, market-agnostic
├── markets/hk/        # Hong Kong specific
├── markets/sg/        # Singapore (future)
└── markets/au/        # Australia (future)
```

**Rules Enforced:**
- NO hardcoded jurisdiction logic in core/
- NO direct imports from markets/ in core/
- ALL market-specific logic via dependency injection
- Market configs injected through factory pattern

### 2. Multi-Tenant Isolation

**Decision:** Every table includes `tenant_id` with middleware-enforced context

**Rationale:**
- Prevents cross-tenant data leakage
- Simplifies compliance (ISO 27001, SOC 2)
- Enables per-tenant encryption keys
- Supports multi-region deployment

**Implementation:**
- `ContextVar[UUID]` for tenant context throughout request lifecycle
- Middleware extracts tenant from JWT and sets context
- All database queries MUST filter by `tenant_id`
- Context validation prevents cross-tenant data in agent context

**Security Controls:**
- Tenant context middleware validates JWT
- Cross-tenant access blocked at database level
- Audit logging for all tenant context changes
- Periodic validation scans for missing tenant_id filters

### 3. Database Schema Design

**Decision:** PostgreSQL with PGVector extension, normalized schema with proper indexes

**Key Tables:**
- `tenants`: Multi-tenant root entity
- `users`: Per-tenant users with RBAC
- `projects`: Core entity with jurisdiction support
- `clients`: Client companies
- `knowledge_base`: Jurisdiction-aware KB documents
- `kb_chunks`: Vector embeddings with jurisdiction filter
- `audit_logs`: Comprehensive security event logging
- `blacklisted_tokens`: JWT revocation support

**Indexes Created:**
- `tenant_id` on ALL tables (performance + isolation)
- `jurisdiction` on projects, KB tables (market filtering)
- `email` on users (login performance)
- `created_at` on audit_logs (compliance queries)
- Vector similarity index on kb_chunks (future, after data load)

### 4. Security-First Design

**Decision:** Defense-in-depth with five security layers

**Layers:**
1. **Application Layer**
   - XSS/CSRF protection via security headers
   - Input sanitization for all user input
   - Rate limiting on auth endpoints (5/minute)

2. **Authentication Layer**
   - JWT with refresh tokens
   - RBAC with role-based permissions
   - Token blacklisting for logout
   - Bcrypt password hashing

3. **Tenant Isolation Layer**
   - Middleware-enforced tenant context
   - Cross-tenant validation
   - Data residency enforcement

4. **Encryption Layer**
   - KMS-managed encryption keys
   - Field-level encryption for sensitive data
   - Encrypted file storage
   - TLS for data in transit

5. **Audit Layer**
   - Comprehensive event logging
   - Security event monitoring
   - Immutable audit trail

### 5. Configuration Management

**Decision:** Pydantic Settings with environment variables

**Rationale:**
- Type-safe configuration
- Validation at startup
- Environment-based configuration (dev/staging/prod)
- Secrets never in code

**Implementation:**
- `.env.example` as template
- Settings cached with @lru_cache()
- Separate configs for different environments
- Validation errors fail fast at startup

## Component Architecture

### Database Layer

**Models** (`genreport/core/database/models.py`):
- SQLAlchemy ORM models
- All tables inherit from Base
- Relationships defined for ORM navigation
- Proper indexes for performance

**Base** (`genreport/core/database/base.py`):
- Engine configuration with connection pooling
- Session management
- `get_db()` dependency for FastAPI

### Security Layer

**Components to Implement:**
1. Tenant Context (`core/security/tenant_context.py`)
   - ContextVar for tenant storage
   - Middleware for tenant extraction
   - `get_current_tenant()` utility

2. Encryption Service (`core/security/encryption.py`)
   - KMS integration for key management
   - Fernet cipher for field-level encryption
   - EncryptedString SQLAlchemy type

3. Audit Logger (`core/security/audit_logger.py`)
   - Centralized logging interface
   - Event type constants
   - Async logging for performance

### Market Configuration

**Hong Kong Config** (`markets/hk/config.py`):
```python
@dataclass
class HKMarketConfig:
    jurisdiction: str = "HK"
    currency: str = "HKD"
    accounting_standard: str = "HKFRS"
    sme_standard: str = "SME-FRS"
    date_format: str = "DD/MM/YYYY"
```

**Factory Pattern**:
```python
def get_market_config(jurisdiction: str) -> MarketConfig:
    if jurisdiction == "HK":
        return HKMarketConfig()
    # Future: SG, AU
```

## Technology Stack

### Core Technologies
- **Python:** 3.13+
- **Web Framework:** FastAPI 0.115+
- **Database:** PostgreSQL 14+ with PGVector
- **ORM:** SQLAlchemy 2.0+
- **Migrations:** Alembic 1.13+
- **Caching:** Redis 7+
- **Background Jobs:** Celery 5.4+

### Authentication & Security
- **JWT:** python-jose with cryptography
- **Password Hashing:** passlib with bcrypt
- **Encryption:** cryptography (Fernet)
- **Rate Limiting:** slowapi

### AI & LLM
- **Framework:** DSPy 2.5+
- **LLM Provider:** OpenAI (gpt-4o-mini)
- **Observability:** Langfuse

### Testing
- **Framework:** pytest 8.3+
- **Coverage:** pytest-cov (target: 80%+)
- **Async Testing:** pytest-asyncio
- **Mocking:** pytest-mock

## Database Schema

### Entity Relationship Diagram

```
Tenant (1) ──────── (*) User
  │                      │
  │                      │
  ├──────── (*) Project ─┤
  │              │
  │              │
  ├──────── (*) Client ──┤
  │
  ├──────── (*) KnowledgeBase ──── (*) KBChunk
  │
  └──────── (*) AuditLog

Project (*) ──────── (1) AccountingProgram
Project (1) ──────── (*) Report
```

### Key Fields

**Multi-Tenant Support:**
- ALL tables: `tenant_id UUID`
- ALL tables: `created_at`, `updated_at`

**Hybrid Architecture:**
- Projects: `jurisdiction`, `accounting_standard`
- KnowledgeBase: `jurisdiction`
- KBChunks: `jurisdiction`

**Security:**
- Users: `password_hash`, `role`, `is_active`
- AuditLogs: `event_type`, `action`, `ip_address`, `status`
- BlacklistedTokens: `token_jti`, `expires_at`

## Performance Considerations

### Database Optimization
- Connection pooling (pool_size=20, max_overflow=10)
- Strategic indexes on all foreign keys
- Indexes on filtering columns (tenant_id, jurisdiction, status)
- pool_pre_ping to handle stale connections

### Caching Strategy
- Redis for session storage
- Redis for rate limiting counters
- Future: Cache market configs (rarely change)
- Future: Cache KB embeddings lookup results

### Query Optimization
- Lazy loading for relationships (avoid N+1)
- Eager loading when needed (joinedload)
- Proper use of indexes
- Query result pagination

## Security Considerations

### OWASP Top 10 Mitigations

1. **Injection:** SQLAlchemy parameterized queries, input validation
2. **Broken Authentication:** JWT with refresh tokens, rate limiting
3. **Sensitive Data Exposure:** Encryption at rest, TLS in transit
4. **XML External Entities:** N/A (no XML processing)
5. **Broken Access Control:** RBAC, tenant isolation
6. **Security Misconfiguration:** Security headers, no debug in prod
7. **XSS:** Input sanitization, CSP headers
8. **Insecure Deserialization:** Pydantic validation
9. **Vulnerable Components:** Dependency scanning (future)
10. **Insufficient Logging:** Comprehensive audit logs

### Data Protection

**At Rest:**
- Field-level encryption for PII
- Encrypted file storage
- KMS-managed keys per tenant

**In Transit:**
- TLS 1.3 for all connections
- Strict transport security headers
- Certificate pinning (future)

**Access Control:**
- Role-based permissions
- Tenant isolation at DB level
- Cross-tenant validation

## Testing Strategy

### Unit Tests
- Models: Field validation, relationships
- Security: Encryption, audit logging
- Config: Settings validation

### Integration Tests
- API endpoints with tenant context
- Database operations with isolation
- Authentication flows

### Security Tests (MANDATORY)
```python
def test_tenant_isolation()
def test_context_validation()
def test_audit_logging()
def test_encryption_at_rest()
def test_no_hardcoded_jurisdictions_in_core()
```

## Migration Strategy

### Initial Migration
1. Create all tables with indexes
2. Create PGVector extension
3. Insert accounting_programs seed data
4. Create default admin tenant (development only)

### Future Migrations
- Version controlled via Alembic
- Tested in staging before production
- Rollback plan for each migration
- Zero-downtime deployment strategy

## Deployment Considerations

### Environment Variables Required
- DATABASE_URL
- REDIS_URL
- SECRET_KEY
- JWT_SECRET_KEY
- ENCRYPTION_KEY
- OPENAI_API_KEY

### Infrastructure Requirements
- PostgreSQL 14+ with PGVector extension
- Redis 7+
- Python 3.13+ runtime
- 2GB+ RAM minimum

### Monitoring
- Health check endpoints
- Structured logging with Structlog
- Langfuse for LLM observability
- Future: Prometheus metrics

## Next Steps

### Sprint 1 Remaining Tasks
1. ✅ Database models created
2. ⏳ Implement Alembic migrations
3. ⏳ Build security layer (tenant context, encryption, audit)
4. ⏳ Implement JWT authentication
5. ⏳ Create market configuration system
6. ⏳ Build FastAPI app with middleware
7. ⏳ Create API routers
8. ⏳ Write comprehensive tests
9. ⏳ Complete documentation

### Sprint 2 Dependencies
- Encryption service (for file encryption)
- Tenant context (for file isolation)
- Audit logging (for file operations)
- Market configuration (for validators)

## References

- Master Sprint Plan: `docs/master_sprint_plan.md`
- Sprint 1 Details: `docs/sprint_1_foundation.md`
- CLAUDE.md: Architecture principles and patterns
- Database Schema: This document, section "Database Schema"
