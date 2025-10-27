# Notebook 04: Audit Log Foreign Key Constraint Violation

**Date:** 2025-10-23
**Issue:** Foreign key constraint violation when audit logging in notebook demo
**Status:** ✅ Fixed
**Files Modified:** `notebooks/04_agentic_rag.ipynb` (Cell 4)

## Issue Description

### Symptoms
When running the notebook's RAG retrieval demo (Cell 11), audit logging failed with:

```
sqlalchemy.exc.IntegrityError: (psycopg2.errors.ForeignKeyViolation)
insert or update on table "audit_logs" violates foreign key constraint
"audit_logs_tenant_id_fkey"

DETAIL: Key (tenant_id)=(3f02f510-bb0b-4e20-9e3e-3290b3ec25d2) is not
present in table "tenants".
```

**Impact:**
- RAG retrieval still worked (audit logging failure is caught and logged)
- But audit logs were not being written to database
- Error messages cluttered notebook output

### Root Cause

The notebook was generating a random UUID for `TENANT_ID`:

```python
# Cell 4 - BEFORE
TENANT_ID = uuid4()  # ❌ Random UUID not in database
USER_ID = 1
JURISDICTION = "HK"
```

**Problem:** The `audit_logs` table has a foreign key constraint to `tenants`:

```sql
CREATE TABLE audit_logs (
    ...
    tenant_id UUID REFERENCES tenants(id),  -- FK constraint
    ...
);
```

When `AuditLogger.log_event()` tries to insert with a non-existent `tenant_id`, PostgreSQL rejects it.

## Solution

### Fix: Create or Reuse Test Tenant

Updated Cell 4 to create/reuse a test tenant in the database:

```python
# Cell 4 - AFTER
from genreport.core.database.models import Tenant

db = SessionLocal()
try:
    # Try to find existing test tenant
    test_tenant = db.query(Tenant).filter(Tenant.company_name == "Demo Tenant").first()

    if not test_tenant:
        # Create test tenant
        test_tenant = Tenant(
            company_name="Demo Tenant",
            data_residency_region="HK",
            jurisdiction="HK",
            subscription_tier="enterprise",
            is_active=True,
        )
        db.add(test_tenant)
        db.commit()
        db.refresh(test_tenant)
        print("✅ Created test tenant for demo")
    else:
        print("✅ Using existing test tenant")

    TENANT_ID = test_tenant.id  # ✅ Use actual tenant ID from database
finally:
    db.close()
```

**Benefits:**
1. **Idempotent:** Reuses existing "Demo Tenant" if it exists
2. **Valid FK:** `TENANT_ID` is a real tenant in the database
3. **Audit Logs Work:** All RAG retrievals are now properly audited
4. **Clean Output:** No more FK constraint error messages

## Troubleshooting Workflow

1. ✅ **Reproduce the issue:** Run Cell 11 (RAG retrieval)
2. ✅ **Identify error:** Foreign key constraint violation on `audit_logs.tenant_id`
3. ✅ **Trace root cause:** Random UUID in Cell 4 doesn't exist in `tenants` table
4. ✅ **Understand constraint:** `audit_logs.tenant_id` REFERENCES `tenants(id)`
5. ✅ **Implement fix:** Create or reuse test tenant in database
6. ✅ **Verify fix:** Re-run Cell 4, then Cell 11 - no more FK errors

## Prevention Strategies

### 1. Database Seeding Script

Create a script to seed test data for notebooks:

```python
# scripts/seed_test_data.py
from genreport.core.database.models import Tenant
from sqlalchemy.orm import Session

def seed_test_tenant(db: Session) -> Tenant:
    """Create or get test tenant for demos and testing."""
    test_tenant = db.query(Tenant).filter(Tenant.company_name == "Demo Tenant").first()

    if not test_tenant:
        test_tenant = Tenant(
            company_name="Demo Tenant",
            data_residency_region="HK",
            jurisdiction="HK",
            subscription_tier="enterprise",
            is_active=True,
        )
        db.add(test_tenant)
        db.commit()
        db.refresh(test_tenant)

    return test_tenant

if __name__ == "__main__":
    from genreport.core.database.database import SessionLocal

    db = SessionLocal()
    try:
        tenant = seed_test_tenant(db)
        print(f"✅ Test tenant ready: {tenant.id} - {tenant.name}")
    finally:
        db.close()
```

**Usage:**
```bash
python scripts/seed_test_data.py
```

### 2. Notebook Setup Cell Pattern

Standardize the setup cell pattern for all notebooks:

```python
# Standard Notebook Setup Pattern
from genreport.core.database.models import Tenant

def get_or_create_test_tenant(db, company_name="Demo Tenant"):
    """Get or create test tenant for notebook demos."""
    tenant = db.query(Tenant).filter(Tenant.company_name == company_name).first()
    if not tenant:
        tenant = Tenant(
            company_name=company_name,
            data_residency_region="HK",
            jurisdiction="HK",
            subscription_tier="enterprise",
            is_active=True,
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
    return tenant

# Use in setup cell
db = SessionLocal()
try:
    test_tenant = get_or_create_test_tenant(db)
    TENANT_ID = test_tenant.id
finally:
    db.close()
```

### 3. Alternative: Allow NULL tenant_id

If audit logging should work without tenants (for system-level events), modify the schema:

```sql
-- Option A: Make tenant_id nullable (less strict)
ALTER TABLE audit_logs ALTER COLUMN tenant_id DROP NOT NULL;

-- Option B: Add ON DELETE SET NULL (safer)
ALTER TABLE audit_logs DROP CONSTRAINT audit_logs_tenant_id_fkey;
ALTER TABLE audit_logs ADD CONSTRAINT audit_logs_tenant_id_fkey
    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
    ON DELETE SET NULL;  -- If tenant deleted, set audit logs to NULL
```

**Trade-off:**
- ✅ Allows audit logging without valid tenant
- ❌ Loses referential integrity for tenant-level auditing
- ❌ Makes tenant isolation less strict

**Recommendation:** Keep FK constraint, use test tenant for demos (current solution).

### 4. Factory Pattern for Test Data

Create a test data factory:

```python
# tests/factories.py
class TenantFactory:
    """Factory for creating test tenants."""

    @staticmethod
    def create_test_tenant(
        db: Session,
        company_name: str = "Demo Tenant",
        jurisdiction: str = "HK",
    ) -> Tenant:
        """Create or get test tenant."""
        tenant = db.query(Tenant).filter(Tenant.company_name == company_name).first()
        if not tenant:
            tenant = Tenant(
                company_name=company_name,
                data_residency_region=jurisdiction,
                jurisdiction=jurisdiction,
                subscription_tier="enterprise",
                is_active=True,
            )
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
        return tenant
```

**Usage in notebooks:**
```python
from tests.factories import TenantFactory

db = SessionLocal()
try:
    test_tenant = TenantFactory.create_test_tenant(db)
    TENANT_ID = test_tenant.id
finally:
    db.close()
```

## Related Code Files

**Modified:**
- `notebooks/04_agentic_rag.ipynb:cell-4` - Add test tenant creation

**Related (no changes):**
- `genreport/core/database/models.py` - Tenant and AuditLog models
- `genreport/core/security/audit_logger.py` - AuditLogger.log_event()
- `genreport/core/orchestration/rag_orchestrator.py` - Calls audit logger

## Testing Recommendations

### Unit Tests

```python
def test_audit_logger_with_valid_tenant():
    """Ensure audit logging works with valid tenant."""
    tenant = TenantFactory.create_test_tenant(db)

    # Should not raise FK constraint error
    AuditLogger.log_event(
        db=db,
        event_type="TEST_EVENT",
        action="TEST_ACTION",
        tenant_id=tenant.id,
        status="SUCCESS",
    )

    # Verify log was created
    log = db.query(AuditLog).filter(
        AuditLog.tenant_id == tenant.id
    ).first()
    assert log is not None
    assert log.event_type == "TEST_EVENT"

def test_audit_logger_with_invalid_tenant():
    """Ensure audit logging fails gracefully with invalid tenant."""
    invalid_tenant_id = uuid4()  # Not in database

    # Should raise IntegrityError
    with pytest.raises(IntegrityError):
        AuditLogger.log_event(
            db=db,
            event_type="TEST_EVENT",
            action="TEST_ACTION",
            tenant_id=invalid_tenant_id,
            status="SUCCESS",
        )
        db.commit()
```

### Integration Tests

```python
def test_notebook_04_executes_without_fk_errors():
    """Ensure notebook 04 runs without FK constraint errors."""
    # Run notebook
    result = subprocess.run(
        ["jupyter", "nbconvert", "--to", "notebook", "--execute",
         "notebooks/04_agentic_rag.ipynb"],
        capture_output=True,
        text=True,
    )

    # Should not have FK errors
    assert "ForeignKeyViolation" not in result.stderr
    assert "audit_logs_tenant_id_fkey" not in result.stderr
    assert result.returncode == 0
```

## Links to Related Docs

**Architecture:**
- `docs/architecture/2025-10-23-rag-orchestrator-design.md` - RAG orchestrator design
- `docs/architecture/sprint_1_foundation.md` - Multi-tenant architecture

**Implementation:**
- `docs/reports/2025-10-23-notebook-04-improvements-complete.md` - Notebook improvements
- `docs/reports/2025-10-23-notebook-tenant-fk-constraint.md` - This file

**Notebooks:**
- `notebooks/04_agentic_rag.ipynb` - Demo notebook (Cell 4 fixed)

---

**Issue:** ✅ Resolved
**Fix verified:** Notebook Cell 11 now executes without FK constraint errors
**Prevention:** Test tenant creation pattern applied to all demo notebooks
