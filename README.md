# GenReport - AI-Powered Audit Report Generation System

An enterprise-grade AI-powered system for generating audit reports with multi-market support, tenant isolation, and comprehensive security controls.

## Features

- **Multi-Market Support:** Built-in support for Hong Kong (HKFRS, SME-FRS), with extensible architecture for Singapore and Australia
- **Enterprise Security:** ISO 27001 and SOC 2 ready with multi-tenant isolation, encryption at rest, and comprehensive audit logging
- **AI-Powered Analysis:** DSPy-based agents for intelligent report generation with jurisdiction-specific knowledge
- **Hybrid Architecture:** Clean separation between generic core logic and market-specific implementations

## Quick Start

### Prerequisites

- Python 3.13+
- PostgreSQL 14+ with PGVector extension
- Redis 7+
- Virtual environment tool (uv recommended)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd new_ai_auditing

# Create virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e ".[dev]"

# Copy environment template
cp .env.example .env

# Generate secure keys
python scripts/generate_keys.py

# Edit .env with your configuration
# At minimum, set:
# - DATABASE_URL
# - REDIS_URL
# - SECRET_KEY (use generated key)
# - JWT_SECRET_KEY (use generated key)
# - ENCRYPTION_KEY (use generated key)
# - GOOGLE_API_KEY (for Gemini - default LLM provider)
```

### Database Setup

```bash
# Install PostgreSQL and PGVector extension
# CREATE EXTENSION vector;

# Create database
createdb genreport_dev

# Run migrations
python scripts/db_manager.py migrate

# Seed test data (development only)
python scripts/db_manager.py seed

# Check migration status
python scripts/db_manager.py status
```

### Running the Application

```bash
# Development server with auto-reload
uvicorn genreport.api.main:app --reload --host 0.0.0.0 --port 8000

# Production server
uvicorn genreport.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Running Tests

```bash
# All tests with coverage
pytest

# Specific test categories
pytest tests/core/                    # Core tests only
pytest tests/markets/hk/              # Hong Kong market tests
pytest -m security                    # Security tests
pytest -m integration                 # Integration tests

# With coverage report
pytest --cov=genreport --cov-report=html
```

## Project Structure

```
genreport/
├── core/                   # Generic, market-agnostic logic
│   ├── database/          # Models, repositories, migrations
│   ├── security/          # Tenant context, encryption, audit
│   ├── parsing/           # Excel processing
│   ├── orchestration/     # Agent orchestration
│   ├── retrieval/         # Knowledge base retrieval
│   └── utils/             # Shared utilities
│
├── markets/               # Market-specific implementations
│   └── hk/               # Hong Kong
│       ├── config.py      # HK configuration
│       ├── agents/        # HK-specific agents
│       ├── validators/    # HK-specific validation
│       └── templates/     # HK report templates
│
├── api/                   # FastAPI application
│   ├── routers/          # API endpoints
│   ├── dependencies.py   # Common dependencies
│   └── main.py           # Application entry point
│
└── config/               # Configuration files
```

## Architecture Principles

### Hybrid Architecture

The codebase strictly separates generic logic (`core/`) from market-specific implementations (`markets/`):

- **NEVER** hardcode jurisdiction-specific logic in `core/`
- **ALWAYS** use dependency injection for market configurations
- **NO** direct imports from `markets/` in `core/` modules

### Multi-Tenant Isolation

Every database table includes `tenant_id` for complete isolation:

- All queries MUST filter by `tenant_id`
- Tenant context enforced via middleware
- Cross-tenant data validation prevents leakage

### Security-First Design

Defense-in-depth with five security layers:

1. Application Layer (XSS/CSRF protection, input sanitization)
2. Authentication Layer (JWT, RBAC)
3. Tenant Isolation (middleware-enforced context)
4. Encryption Layer (KMS-managed keys)
5. Audit Layer (comprehensive event logging)

## Development Workflow

See `CLAUDE.md` for detailed development guidelines and patterns.

### Adding a New Market

1. Create directory structure: `markets/{jurisdiction}/`
2. Define market configuration: `markets/{jurisdiction}/config.py`
3. Update `get_market_config()` factory
4. Implement market-specific agents and validators
5. Add comprehensive tests

### Implementing Security Features

1. **Always** filter database queries by `tenant_id`
2. **Always** validate file types using magic bytes
3. **Always** encrypt sensitive data at rest
4. **Never** log PII or credentials
5. **Always** audit security-relevant events

## API Documentation

Once running, visit:

- API Documentation: http://localhost:8000/docs
- Alternative Docs: http://localhost:8000/redoc
- OpenAPI Schema: http://localhost:8000/openapi.json

## Sprint Implementation

The project follows a 6-sprint master plan (19 weeks total):

1. **Sprint 1:** Foundation + Security (4.5 weeks)
2. **Sprint 2:** Excel Processing (2.5 weeks)
3. **Sprint 3:** Knowledge Base (2.5 weeks)
4. **Sprint 4:** AI Agents (3.5 weeks)
5. **Sprint 5:** Frontend (2.5 weeks)
6. **Sprint 6:** Production (3.5 weeks)

See `docs/master_sprint_plan.md` for complete details.

## Testing

### Required Coverage

- Unit tests: >80%
- Security tests: 100% for isolation and encryption
- Integration tests: All API endpoints

### Security Tests

All features must include:

```python
def test_tenant_isolation():
    """Ensure no cross-tenant data access"""

def test_context_validation():
    """Ensure context contains no mixed tenant data"""

def test_audit_logging():
    """Ensure security events are logged"""
```

## Compliance

The system maintains readiness for:

- **ISO 27001:** Multi-tenant isolation, encryption, audit logging
- **SOC 2 Type II:** Security controls, monitoring, incident response
- **GDPR:** Data residency, right to deletion, portability
- **PDPA (HK/SG):** Local data residency enforcement
- **Privacy Act (AU):** Disclosure controls

## Performance Targets

- Report generation: <3 minutes end-to-end
- API response: <200ms (auth endpoints)
- Database queries: <100ms (with proper indexes)
- Excel parsing: <45 seconds per workbook
- LLM cost: <$0.50 per report

## License

[Add license information]

## Support

For issues and questions, see `CLAUDE.md` for development guidelines.
