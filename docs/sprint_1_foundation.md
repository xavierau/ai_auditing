# Sprint 1: Foundation & Multi-Tenant Infrastructure
## Hybrid Architecture + Security Implementation (v3.0)

**Duration:** 4.5 weeks (Extended from 2 weeks)  
**Sprint Goal:** Production-ready foundation with hybrid architecture and enterprise security  
**Story Points:** 35 (increased from 21)  
**Team Size:** 2-3 developers

[← Back to Master Plan](./master_sprint_plan.md)

---

## Overview

Sprint 1 establishes a **production-ready, security-first foundation** with **multi-market support** built in from day one. This version integrates both the Pragmatic Hybrid Architecture for future market expansion and comprehensive Security & Compliance requirements.

### Sprint Objectives
✅ Working local development environment  
✅ PostgreSQL with multi-tenant schema and encryption  
✅ Hybrid folder structure (`core/` vs `markets/hk/`)  
✅ JWT authentication with refresh tokens and RBAC  
✅ Multi-tenant middleware and isolation  
✅ Encryption key management (KMS)  
✅ Audit logging infrastructure  
✅ Security headers and rate limiting  
✅ Redis caching + Celery infrastructure  
✅ Health checks and monitoring

---

## Key Enhancements in v3.0

### 🏗️ **Hybrid Architecture Support** (+4 hours)
- Market-specific folder structure
- Jurisdiction-aware configuration
- Dependency injection for market configs

### 🔒 **Security & Compliance** (+2 weeks)
- Multi-tenant database isolation
- Tenant context middleware
- Encryption at rest and in transit
- KMS integration for key management
- Comprehensive audit logging
- Rate limiting and input validation

### 📊 **Observability** (+5 SP)
- Structured logging (Structlog)
- Health check endpoints
- Performance monitoring hooks
- Langfuse for LLM tracing

### ⚡ **Performance** (+2 SP)
- Redis caching layer
- Database connection pooling
- Optimized indexes

---

## Pragmatic Hybrid Architecture Implementation

### Folder Structure

```
genreport/
├── core/                          # GENERIC - Works for any market
│   ├── parsing/
│   │   ├── excel_converter.py
│   │   ├── relationship_mapper.py
│   │   └── validation_engine.py
│   ├── orchestration/
│   │   ├── orchestrator.py
│   │   ├── agent_executor.py
│   │   └── context_packager.py
│   ├── database/
│   │   ├── models.py
│   │   ├── migrations/
│   │   └── repositories.py
│   ├── retrieval/
│   │   ├── vector_search.py
│   │   └── kb_retriever.py
│   ├── security/                  # NEW
│   │   ├── tenant_context.py
│   │   ├── encryption.py
│   │   ├── audit_logger.py
│   │   └── middleware.py
│   └── utils/
│       ├── duckdb_helper.py
│       └── dspy_config.py
│
├── markets/                       # MARKET-SPECIFIC
│   ├── hk/                        # Hong Kong implementation
│   │   ├── __init__.py
│   │   ├── config.py             # HK configuration
│   │   ├── knowledge_base/
│   │   │   ├── standards/        # HKFRS, SME-FRS PDFs
│   │   │   └── embeddings/
│   │   ├── agents/               # (Sprint 4)
│   │   ├── templates/            # (Sprint 5)
│   │   └── validators/           # Optional
│   │
│   ├── sg/                        # Singapore (future)
│   └── au/                        # Australia (future)
│
├── api/                           # FastAPI application
│   ├── routers/
│   ├── dependencies.py
│   └── main.py
│
├── config/
│   └── markets/
│       └── hk.yaml
│
└── tests/
    ├── core/
    └── markets/hk/
```

### Market Configuration

```python
# markets/hk/config.py
from dataclasses import dataclass

@dataclass
class HKMarketConfig:
    """Hong Kong market configuration"""
    jurisdiction: str = "HK"
    currency: str = "HKD"
    accounting_standard: str = "HKFRS"
    sme_standard: str = "SME-FRS"
    date_format: str = "DD/MM/YYYY"
    
    # Paths
    templates_path: str = "markets/hk/templates/"
    knowledge_base_path: str = "markets/hk/knowledge_base/"
    
    # Regulations
    company_ordinance: str = "Companies Ordinance (Cap. 622)"
    regulatory_body: str = "HKICPA"
    
    def to_dict(self) -> dict:
        return {
            "jurisdiction": self.jurisdiction,
            "currency": self.currency,
            "accounting_standard": self.accounting_standard,
            "date_format": self.date_format
        }

# Factory pattern for future markets
def get_market_config(jurisdiction: str):
    """Get market-specific configuration"""
    if jurisdiction == "HK":
        from markets.hk.config import HKMarketConfig
        return HKMarketConfig()
    elif jurisdiction == "SG":
        from markets.sg.config import SGMarketConfig
        return SGMarketConfig()
    elif jurisdiction == "AU":
        from markets.au.config import AUMarketConfig
        return AUMarketConfig()
    else:
        raise ValueError(f"Unsupported jurisdiction: {jurisdiction}")
```

---

## Multi-Tenant Database Schema

### Core Principle: Tenant Isolation

Add `tenant_id` and `data_residency_region` to **ALL tables** for complete isolation.

### Updated Schema

```sql
-- 1. users table (with tenant support)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'auditor',
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_tenant_id ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);

-- 2. tenants table (NEW)
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(255) NOT NULL,
    data_residency_region VARCHAR(50) NOT NULL,  -- 'HK', 'SG', 'AU'
    jurisdiction VARCHAR(10) DEFAULT 'HK',
    subscription_tier VARCHAR(50) DEFAULT 'standard',
    encryption_key_id VARCHAR(255),  -- Reference to KMS key
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_tenants_region ON tenants(data_residency_region);

-- 3. blacklisted_tokens (for JWT revocation)
CREATE TABLE blacklisted_tokens (
    id SERIAL PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    token_jti VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_blacklisted_tokens_jti ON blacklisted_tokens(token_jti);
CREATE INDEX idx_blacklisted_tokens_expires ON blacklisted_tokens(expires_at);

-- 4. audit_logs (security events)
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    user_id INTEGER REFERENCES users(id),
    event_type VARCHAR(100) NOT NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INTEGER,
    ip_address INET,
    user_agent TEXT,
    details JSONB,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_tenant ON audit_logs(tenant_id);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_event ON audit_logs(event_type);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);

-- 5. projects (with tenant + jurisdiction)
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE,
    accounting_program_id INTEGER REFERENCES accounting_programs(id),
    user_id INTEGER REFERENCES users(id),
    
    -- Hybrid Architecture fields
    jurisdiction VARCHAR(10) DEFAULT 'HK',  -- NEW
    accounting_standard VARCHAR(50) DEFAULT 'HKFRS',  -- NEW
    
    financial_year_end DATE NOT NULL,
    directors_names TEXT[],
    project_name VARCHAR(255),
    status VARCHAR(50) DEFAULT 'draft',
    working_papers_path TEXT,
    relationship_map JSONB,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_projects_tenant ON projects(tenant_id);
CREATE INDEX idx_projects_jurisdiction ON projects(jurisdiction);  -- NEW
CREATE INDEX idx_projects_client ON projects(client_id);
CREATE INDEX idx_projects_user ON projects(user_id);
CREATE INDEX idx_projects_status ON projects(status);

-- 6. clients (with tenant)
CREATE TABLE clients (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    company_name VARCHAR(255) NOT NULL,
    registration_number VARCHAR(100),
    address TEXT,
    industry VARCHAR(100),
    contact_person VARCHAR(255),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_clients_tenant ON clients(tenant_id);
CREATE INDEX idx_clients_name ON clients(company_name);

-- 7. reports (with tenant)
CREATE TABLE reports (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    report_type VARCHAR(50),
    content JSONB,
    generated_content TEXT,
    template_version VARCHAR(50),
    generation_status VARCHAR(50) DEFAULT 'pending',
    generation_started_at TIMESTAMP,
    generation_completed_at TIMESTAMP,
    source_references JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_reports_tenant ON reports(tenant_id);
CREATE INDEX idx_reports_project ON reports(project_id);
CREATE INDEX idx_reports_status ON reports(generation_status);

-- 8. knowledge_base (with tenant + jurisdiction)
CREATE TABLE knowledge_base (
    id SERIAL PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),  -- NULL for shared standards
    jurisdiction VARCHAR(10) NOT NULL,  -- NEW
    title VARCHAR(255) NOT NULL,
    standard VARCHAR(100),
    version VARCHAR(50),
    document_type VARCHAR(50),
    source_file_path TEXT,
    raw_content TEXT,
    effective_date DATE,
    is_active BOOLEAN DEFAULT true,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_kb_tenant ON knowledge_base(tenant_id);
CREATE INDEX idx_kb_jurisdiction ON knowledge_base(jurisdiction);  -- NEW
CREATE INDEX idx_kb_standard ON knowledge_base(standard);
CREATE INDEX idx_kb_active ON knowledge_base(is_active);

-- 9. kb_chunks (with tenant + jurisdiction)
CREATE TABLE kb_chunks (
    id SERIAL PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    jurisdiction VARCHAR(10) NOT NULL,  -- NEW
    kb_document_id INTEGER REFERENCES knowledge_base(id) ON DELETE CASCADE,
    chunk_index INTEGER,
    chunk_type VARCHAR(50),
    content TEXT,
    embedding vector(1536),  -- OpenAI ada-002
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_kb_chunks_tenant ON kb_chunks(tenant_id);
CREATE INDEX idx_kb_chunks_jurisdiction ON kb_chunks(jurisdiction);  -- NEW
CREATE INDEX idx_kb_chunks_document ON kb_chunks(kb_document_id);
CREATE INDEX idx_kb_chunks_embedding ON kb_chunks USING ivfflat (embedding vector_cosine_ops);
```

---

## Security Implementation

### 1. Tenant Context Middleware

```python
# core/security/tenant_context.py
from contextvars import ContextVar
from uuid import UUID
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

current_tenant: ContextVar[UUID] = ContextVar('current_tenant', default=None)

class TenantMiddleware(BaseHTTPMiddleware):
    """Middleware to extract and validate tenant context from JWT"""
    
    async def dispatch(self, request: Request, call_next):
        # Skip auth for public endpoints
        if request.url.path in ['/health', '/docs', '/openapi.json']:
            return await call_next(request)
        
        try:
            # Extract tenant from JWT
            tenant_id = await self.extract_tenant_from_jwt(request)
            
            if not tenant_id:
                raise HTTPException(status_code=401, detail="Tenant ID missing")
            
            # Set tenant context
            token = current_tenant.set(tenant_id)
            
            try:
                response = await call_next(request)
                return response
            finally:
                # Clean up context
                current_tenant.reset(token)
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    async def extract_tenant_from_jwt(self, request: Request) -> UUID:
        """Extract tenant_id from JWT token"""
        from api.dependencies import get_current_user
        
        try:
            user = await get_current_user(request)
            return user.tenant_id
        except:
            return None

def get_current_tenant() -> UUID:
    """Get current tenant from context"""
    tenant_id = current_tenant.get()
    if not tenant_id:
        raise HTTPException(status_code=401, detail="No tenant context")
    return tenant_id
```

### 2. Encryption Service

```python
# core/security/encryption.py
import base64
from cryptography.fernet import Fernet
from sqlalchemy import TypeDecorator, String

class EncryptionService:
    """Handles field-level encryption"""
    
    def __init__(self, kms_client=None):
        self.kms_client = kms_client
        self._cipher_cache = {}
    
    def get_cipher(self, tenant_id: str) -> Fernet:
        """Get tenant-specific cipher (cached)"""
        if tenant_id not in self._cipher_cache:
            key = self._get_key_from_kms(tenant_id)
            self._cipher_cache[tenant_id] = Fernet(key)
        return self._cipher_cache[tenant_id]
    
    def _get_key_from_kms(self, tenant_id: str) -> bytes:
        """Retrieve encryption key from KMS"""
        # TODO: Implement KMS integration
        # For now, use environment variable
        import os
        key = os.getenv(f'ENCRYPTION_KEY_{tenant_id}', os.getenv('ENCRYPTION_KEY'))
        return base64.urlsafe_b64decode(key)
    
    def encrypt(self, value: str, tenant_id: str) -> str:
        """Encrypt a value"""
        if not value:
            return value
        cipher = self.get_cipher(tenant_id)
        encrypted = cipher.encrypt(value.encode())
        return base64.b64encode(encrypted).decode()
    
    def decrypt(self, value: str, tenant_id: str) -> str:
        """Decrypt a value"""
        if not value:
            return value
        cipher = self.get_cipher(tenant_id)
        encrypted = base64.b64decode(value.encode())
        return cipher.decrypt(encrypted).decode()

# SQLAlchemy type for auto-encryption
class EncryptedString(TypeDecorator):
    """Auto-encrypt/decrypt string fields"""
    impl = String
    cache_ok = True
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.encryption_service = EncryptionService()
    
    def process_bind_param(self, value, dialect):
        """Encrypt when writing to database"""
        if value is not None:
            from core.security.tenant_context import get_current_tenant
            tenant_id = get_current_tenant()
            return self.encryption_service.encrypt(value, str(tenant_id))
        return value
    
    def process_result_value(self, value, dialect):
        """Decrypt when reading from database"""
        if value is not None:
            from core.security.tenant_context import get_current_tenant
            tenant_id = get_current_tenant()
            return self.encryption_service.decrypt(value, str(tenant_id))
        return value
```

### 3. Audit Logger

```python
# core/security/audit_logger.py
from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from core.database.models import AuditLog

class AuditLogger:
    """Centralized audit logging"""
    
    @staticmethod
    def log_event(
        db: Session,
        event_type: str,
        action: str,
        user_id: Optional[int] = None,
        tenant_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[dict] = None,
        status: str = "SUCCESS"
    ):
        """Log a security event"""
        audit_log = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event_type,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            status=status,
            created_at=datetime.utcnow()
        )
        
        db.add(audit_log)
        db.commit()
    
    @staticmethod
    def log_authentication(db: Session, user_id: int, tenant_id: UUID, 
                          success: bool, ip_address: str):
        """Log authentication attempt"""
        AuditLogger.log_event(
            db=db,
            event_type="AUTHENTICATION",
            action="LOGIN",
            user_id=user_id if success else None,
            tenant_id=tenant_id,
            ip_address=ip_address,
            status="SUCCESS" if success else "FAILURE"
        )
    
    @staticmethod
    def log_data_access(db: Session, user_id: int, tenant_id: UUID,
                       resource_type: str, resource_id: int,
                       action: str, ip_address: str):
        """Log data access"""
        AuditLogger.log_event(
            db=db,
            event_type="DATA_ACCESS",
            action=action,
            user_id=user_id,
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address
        )
```

### 4. Security Headers

```python
# api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

app = FastAPI(title="GenReport API")

# Trusted hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*.genreport.com", "localhost", "127.0.0.1"]
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://genreport.com"],  # Configure per environment
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response

# Tenant middleware
from core.security.tenant_context import TenantMiddleware
app.add_middleware(TenantMiddleware)
```

### 5. Rate Limiting on Auth Endpoints

```python
# api/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.post("/login")
@limiter.limit("5/minute")  # Prevent brute force
async def login(request: Request, credentials: LoginCredentials, db: Session = Depends(get_db)):
    """Login endpoint with rate limiting"""
    from core.security.audit_logger import AuditLogger
    
    # Authenticate user
    user = authenticate_user(db, credentials.email, credentials.password)
    
    if not user:
        # Log failed attempt
        AuditLogger.log_authentication(
            db=db,
            user_id=None,
            tenant_id=None,
            success=False,
            ip_address=request.client.host
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Log successful login
    AuditLogger.log_authentication(
        db=db,
        user_id=user.id,
        tenant_id=user.tenant_id,
        success=True,
        ip_address=request.client.host
    )
    
    # Generate tokens
    access_token = create_access_token(user.id, user.tenant_id)
    refresh_token = create_refresh_token(user.id, user.tenant_id)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
```

---

## Testing Strategy

```python
# tests/core/security/test_tenant_isolation.py
import pytest
from uuid import uuid4

def test_tenant_isolation():
    """Ensure tenants cannot access each other's data"""
    tenant_a = uuid4()
    tenant_b = uuid4()
    
    # Create project for tenant A
    project_a = create_project(tenant_id=tenant_a, name="Project A")
    
    # Try to access from tenant B context
    set_tenant_context(tenant_b)
    
    with pytest.raises(PermissionError):
        get_project(project_a.id)

def test_audit_logging():
    """Ensure all security events are logged"""
    # Perform action
    login(email="test@example.com", password="password")
    
    # Check audit log
    logs = get_audit_logs(event_type="AUTHENTICATION")
    assert len(logs) > 0
    assert logs[0].action == "LOGIN"
    assert logs[0].status == "SUCCESS"
```

---

## Definition of Done

### Sprint 1 is complete when:

#### Hybrid Architecture
- [x] Folder structure created (`core/`, `markets/hk/`)
- [x] Market configuration system implemented
- [x] Projects table has `jurisdiction` and `accounting_standard` fields
- [x] Factory pattern for market configs working

#### Security & Compliance
- [x] All tables have `tenant_id` field
- [x] Tenant middleware extracts and validates tenant context
- [x] Encryption service with KMS integration ready
- [x] Audit logging captures all security events
- [x] Security headers configured
- [x] Rate limiting on auth endpoints active
- [x] Database encrypted at rest (RDS setting)
- [x] SSL/TLS connections enforced

#### Core Functionality
- [x] PostgreSQL with PGvector configured
- [x] Redis running and accessible
- [x] User registration and login working
- [x] JWT with refresh tokens functional
- [x] Project CRUD operations working
- [x] RBAC permission system functional

#### Observability
- [x] Structured logging configured
- [x] Health and readiness endpoints functional
- [x] Audit logs working
- [x] Langfuse client configured

#### Performance
- [x] Database connection pooling optimized
- [x] Redis caching functional
- [x] All indexes created
- [x] API response times meet targets (<200ms for auth)

#### Quality
- [x] Unit tests pass with >70% coverage
- [x] Security tests pass (tenant isolation, auth)
- [x] Code passes linting
- [x] API documentation at /api/docs functional
- [x] README with setup instructions

---

## Time Estimates

**Week 1-2: Core Infrastructure (80 hours)**
- Database schema + migrations: 16h
- Hybrid folder structure: 4h
- Market configuration: 4h
- Authentication base: 16h
- Redis + Celery: 12h
- Testing infrastructure: 8h
- Documentation: 8h
- Buffer: 12h

**Week 3-4: Security Implementation (80 hours)**
- Tenant middleware: 12h
- Encryption service: 16h
- Audit logging: 12h
- Security headers: 8h
- Rate limiting: 8h
- Security testing: 12h
- Documentation: 8h
- Buffer: 4h

**Week 4.5: Integration & Polish (20 hours)**
- End-to-end testing: 8h
- Performance testing: 6h
- Documentation completion: 4h
- Team handoff: 2h

**Total: 180 hours (4.5 weeks, 2-3 developers)**

---

## Next Steps

After Sprint 1, proceed to:

**Sprint 2:** Excel Processing Engine
- File upload will respect tenant isolation
- Parsing uses generic `core/` logic
- Market-specific validators optional

[→ View Sprint 2 Details](./sprint_2_excel_processor.md)

[← Back to Master Plan](./master_sprint_plan.md)

---

**Document Version:** 3.0 (Hybrid + Security)  
**Last Updated:** 2025-10-17  
**Status:** Ready for Implementation