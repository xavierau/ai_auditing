# Running Sprint 1 Tests
**Date**: 2025-10-17
**Topic**: Testing Sprint 1 Implementation Completeness

---

## Prerequisites

### 1. Install Dependencies

```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install all dependencies including test dependencies
uv pip install -e ".[dev]"
```

### 2. PostgreSQL Setup

**Tests use PostgreSQL** (not SQLite) to properly test PostgreSQL-specific features like JSONB, INET, ARRAY, and pgvector.

```bash
# Ensure PostgreSQL is running
# macOS (if installed via Homebrew):
brew services start postgresql@16

# Linux:
sudo systemctl start postgresql

# Windows:
# Start PostgreSQL service from Services panel
```

**Option A: Use Development Database (Quick Start)**
```bash
# Tests will use your development database from .env
# Tables are created/dropped for each test
DATABASE_URL=postgresql://user:pass@localhost:5432/genreport
```

**Option B: Use Separate Test Database (Recommended)**
```bash
# Create a test database
createdb genreport_test

# Set TEST_DATABASE_URL environment variable
export TEST_DATABASE_URL=postgresql://user:pass@localhost:5432/genreport_test

# Or add to .env.test:
TEST_DATABASE_URL=postgresql://user:pass@localhost:5432/genreport_test
```

### 3. Verify Configuration

Ensure your `.env` file has all required settings:

```bash
# Security Keys (generate with: python scripts/generate_keys.py)
SECRET_KEY=<secure-random-hex>
JWT_SECRET_KEY=<secure-random-hex>
ENCRYPTION_KEY=<fernet-key>

# Database (PostgreSQL required)
DATABASE_URL=postgresql://user:pass@localhost:5432/genreport

# Optional: Separate test database
TEST_DATABASE_URL=postgresql://user:pass@localhost:5432/genreport_test

# Redis (required for some features)
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

---

## Running Tests

### Run All Sprint 1 Tests

```bash
# Run all tests with verbose output
pytest tests/ -v

# Run with progress bar
pytest tests/ -v --tb=short
```

**Expected Output**:
```
tests/core/security/test_tenant_isolation.py::TestTenantContext::test_current_tenant_default_is_none PASSED
tests/core/security/test_tenant_isolation.py::TestTenantContext::test_set_and_get_current_tenant PASSED
...
tests/api/test_projects.py::TestRoleBasedAccessControl::test_auditor_can_create_and_delete PASSED

========================= 51 passed in 3.45s =========================
```

### Run Specific Test Categories

**1. Tenant Isolation Tests (Critical Security)**
```bash
pytest tests/core/security/test_tenant_isolation.py -v
```

Expected: **10 tests pass** (all critical security tests)

**2. Authentication Tests**
```bash
pytest tests/api/test_auth.py -v
```

Expected: **19 tests pass** (login, register, refresh, logout, RBAC)

**3. Projects API Tests**
```bash
pytest tests/api/test_projects.py -v
```

Expected: **22 tests pass** (CRUD, tenant isolation, RBAC)

### Run by Test Class

```bash
# Tenant isolation tests only
pytest tests/core/security/test_tenant_isolation.py::TestDatabaseTenantIsolation -v

# Authentication tests only
pytest tests/api/test_auth.py::TestLogin -v

# RBAC tests only
pytest tests/api/test_projects.py::TestRoleBasedAccessControl -v
```

### Run Specific Test

```bash
# Run a single test by name
pytest tests/core/security/test_tenant_isolation.py::TestAPITenantIsolation::test_cannot_access_other_tenant_project_via_api -v
```

---

## Coverage Report

### Generate Coverage Report

```bash
# Run tests with coverage
pytest tests/ --cov=genreport --cov-report=term-missing

# Generate HTML coverage report
pytest tests/ --cov=genreport --cov-report=html

# Open coverage report in browser
open htmlcov/index.html  # macOS
# Or on Linux: xdg-open htmlcov/index.html
# Or on Windows: start htmlcov/index.html
```

**Expected Coverage**:
- Overall: ~85%
- Security modules: >90%
- API routers: >80%
- Database models: >70%

### Coverage by Module

```bash
# Show coverage for specific modules
pytest tests/ --cov=genreport.core.security --cov-report=term-missing
pytest tests/ --cov=genreport.api --cov-report=term-missing
```

---

## Test Output Formats

### Detailed Output

```bash
# Show full test output with print statements
pytest tests/ -v -s

# Show only failures with full traceback
pytest tests/ --tb=long

# Show short traceback
pytest tests/ --tb=short

# Show one-line summaries
pytest tests/ --tb=line
```

### Parallel Execution

```bash
# Run tests in parallel (faster)
pytest tests/ -n auto

# Run with 4 workers
pytest tests/ -n 4
```

---

## Verifying Sprint 1 Completeness

### Run Complete Test Suite

```bash
# Run all tests with coverage and generate report
pytest tests/ -v --cov=genreport --cov-report=term-missing --cov-report=html

# Expected results:
# - 51 tests pass
# - 0 failures
# - Coverage >85%
```

### Checklist for Sprint 1 Completion

Run each category and verify all pass:

```bash
# 1. Tenant Isolation (10 tests)
pytest tests/core/security/test_tenant_isolation.py -v
# ✅ All 10 should pass

# 2. Authentication (19 tests)
pytest tests/api/test_auth.py -v
# ✅ All 19 should pass

# 3. Projects API (22 tests)
pytest tests/api/test_projects.py -v
# ✅ All 22 should pass
```

### Generate Test Report

```bash
# Generate JUnit XML report (for CI/CD)
pytest tests/ --junitxml=test-results.xml

# Generate JSON report
pytest tests/ --json-report --json-report-file=test-results.json
```

---

## Common Issues & Solutions

### Issue 1: Import Errors

**Error**:
```
ImportError: cannot import name 'app' from 'genreport.api.main'
```

**Solution**:
```bash
# Ensure package is installed in editable mode
uv pip install -e .

# Or reinstall
uv pip install -e ".[dev]"
```

### Issue 2: Database Connection Errors

**Error**:
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solution**:
```bash
# Ensure PostgreSQL is running
brew services start postgresql@16  # macOS
sudo systemctl start postgresql    # Linux

# Verify connection
psql -U your_user -d genreport -c "SELECT 1;"

# Check DATABASE_URL in .env is correct
# Format: postgresql://username:password@localhost:5432/database_name
```

### Issue 2a: PostgreSQL Type Errors (JSONB, INET, etc.)

**Error**:
```
sqlalchemy.exc.CompileError: Compiler can't render element of type JSONB
```

**Solution**:
This means tests are using SQLite instead of PostgreSQL. Verify:
```bash
# Check tests/conftest.py imports settings
grep "from genreport.core.utils.config import settings" tests/conftest.py

# Tests should use: settings.database_url_str
# Not: "sqlite:///:memory:"
```

### Issue 3: Missing Dependencies

**Error**:
```
ModuleNotFoundError: No module named 'pytest'
```

**Solution**:
```bash
# Install test dependencies
uv pip install pytest pytest-cov httpx

# Or install everything
uv pip install -e ".[dev]"
```

### Issue 4: Fixtures Not Found

**Error**:
```
fixture 'auth_headers' not found
```

**Solution**:
Ensure `tests/conftest.py` exists and is being loaded. Pytest automatically discovers `conftest.py` files.

### Issue 5: Tests Failing Due to Missing Environment Variables

**Error**:
```
ValidationError: SECRET_KEY field required
```

**Solution**:
```bash
# Generate keys
python scripts/generate_keys.py

# Update .env with generated keys
SECRET_KEY=<generated-key>
JWT_SECRET_KEY=<generated-key>
ENCRYPTION_KEY=<generated-key>
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: genreport_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    env:
      DATABASE_URL: postgresql://postgres:postgres@localhost:5432/genreport_test
      SECRET_KEY: test-secret-key-for-ci
      JWT_SECRET_KEY: test-jwt-secret-key-for-ci
      ENCRYPTION_KEY: test-encryption-key-for-ci==
      REDIS_URL: redis://localhost:6379/0
      CELERY_BROKER_URL: redis://localhost:6379/1
      CELERY_RESULT_BACKEND: redis://localhost:6379/2

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'

    - name: Install dependencies
      run: |
        pip install uv
        uv pip install -e ".[dev]"

    - name: Run tests with coverage
      run: |
        pytest tests/ --cov=genreport --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

---

## Performance Benchmarks

Expected test execution times:

| Test Suite | Tests | Time |
|------------|-------|------|
| Tenant Isolation | 10 | ~1.2s |
| Authentication | 19 | ~1.8s |
| Projects API | 22 | ~2.1s |
| **Total** | **51** | **~5s** |

With parallel execution (`-n auto`):
- **Total time**: ~2-3s

---

## Next Steps

After all tests pass:

1. **Review coverage report**
   ```bash
   pytest --cov=genreport --cov-report=html
   open htmlcov/index.html
   ```

2. **Check for untested code**
   - Identify modules with <80% coverage
   - Add tests for edge cases

3. **Run linter**
   ```bash
   ruff check genreport/
   ruff format genreport/
   ```

4. **Run type checker**
   ```bash
   mypy genreport/
   ```

5. **Ready for Sprint 2!**
   All Sprint 1 tests passing = foundation is solid ✅

---

## Quick Reference

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=genreport --cov-report=html

# Run specific category
pytest tests/core/security/ -v
pytest tests/api/ -v

# Run parallel (faster)
pytest tests/ -n auto

# Generate report
pytest tests/ --junitxml=test-results.xml
```

---

**Sprint 1 Success Criteria**:
- ✅ All 51 tests pass
- ✅ Coverage >85%
- ✅ No security test failures
- ✅ All tenant isolation tests pass
- ✅ All authentication tests pass
- ✅ All RBAC tests pass
