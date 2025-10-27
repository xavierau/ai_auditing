# Sprint 4 Follow-Up Tasks

**Date:** 2025-10-18
**Status:** Active TODOs
**Related Commits:** 8b2fee1, 4c22fd0

This document tracks follow-up tasks identified during Sprint 4 implementation that should be completed in future work sessions.

---

## High Priority

### 1. Refactor API Tests to Use Real Authentication

**File:** `tests/api/test_reports.py`
**Issue:** Tests currently use mocking pattern which doesn't align with existing codebase patterns.

**Current State:**
- 12 test cases using `@patch` decorators
- Mocking `get_current_user`, `get_current_tenant`, `get_db`
- Tests fail because FastAPI dependency injection doesn't work well with simple mocks

**Required Changes:**
- Follow pattern from `tests/api/test_files.py`
- Use real authentication flow:
  1. Create test user via fixtures
  2. Login via POST /api/v1/auth/login to get JWT token
  3. Use token in Authorization header for subsequent requests
- Remove all `@patch` decorators
- Use real database fixtures (`db`, `test_user`, `test_project`)

**Example Pattern:**
```python
def test_generate_report_success(
    self, client: TestClient, db: Session, test_user: User, test_project: Project
):
    # Login to get token
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "testpassword123"},
    )
    token = login_response.json()["access_token"]

    # Make authenticated request
    response = client.post(
        f"/api/v1/reports/generate/{test_project.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
```

**Estimated Effort:** 2-3 hours

---

### 2. Implement Actual Data Loading in Report Generation

**File:** `genreport/api/routers/reports.py`
**Function:** `generate_report()` (line ~160)

**Current State:**
```python
# TODO: Load actual trial balance and general ledger data
agent_outputs = orchestrator.run_all_agents(
    project_id=project_id,
    trial_balance={"tenant_id": tenant_id},  # Placeholder
    general_ledger={},  # Placeholder
    accounting_policies={},  # Placeholder
)
```

**Required Changes:**
1. Query `FileMetadata` table to find parsed Excel files for project
2. Load data from parsed Excel files (DuckDB or stored JSON)
3. Extract trial balance data (account codes, balances, descriptions)
4. Extract general ledger data (transactions, journals)
5. Load accounting policies from project configuration
6. Pass real data to `orchestrator.run_all_agents()`

**Dependencies:**
- Sprint 2 Excel parsing must be complete
- DuckDB integration for querying parsed data
- May need to add `parsed_data_path` or similar field to `FileMetadata`

**Estimated Effort:** 4-6 hours

---

### 3. Implement LLM Cost Calculation

**File:** `genreport/api/routers/reports.py`
**Function:** `generate_report()` (line ~240)

**Current State:**
```python
report.cost_usd = 0.0  # TODO: Calculate actual LLM costs
```

**Required Changes:**
1. Aggregate token usage from all `AgentExecution` records for this report
2. Calculate cost based on model pricing:
   - GPT-4: $0.03/1K prompt tokens, $0.06/1K completion tokens
   - GPT-3.5-turbo: $0.0015/1K prompt, $0.002/1K completion
   - Claude-3-Opus: $15/1M prompt, $75/1M completion
3. Sum costs across all agent executions
4. Store in `report.cost_usd`

**Implementation:**
```python
# Query agent executions for this report
executions = db.query(AgentExecution).filter(
    AgentExecution.report_id == report.id
).all()

# Calculate total cost
total_cost = sum(
    execution.cost_usd for execution in executions
    if execution.cost_usd
)

report.cost_usd = total_cost
```

**Estimated Effort:** 1-2 hours

---

## Medium Priority

### 4. Implement Async Report Generation with Celery

**Files:**
- `genreport/api/routers/reports.py`
- `genreport/core/tasks/report_tasks.py` (new)

**Current State:**
- Report generation is synchronous
- Endpoint blocks until all agents complete
- May timeout for large reports (>3 minutes)

**Required Changes:**
1. Create Celery task for report generation
2. Update endpoint to return task ID immediately
3. Create new endpoint GET `/api/v1/reports/status/{task_id}` for polling
4. Store task ID in `GeneratedReport.celery_task_id` field (needs migration)
5. Update `status` field during async execution (generating → completed/failed)

**Benefits:**
- Non-blocking API responses
- Better user experience for long-running reports
- Ability to queue multiple report generations
- Retry support for failed reports

**Estimated Effort:** 6-8 hours

---

### 5. Add `AgentExecution` Population During Report Generation

**File:** `genreport/api/routers/reports.py`
**Function:** `generate_report()` (around line 210)

**Current State:**
- `AgentExecution` model exists but is not populated during report generation
- No audit trail of individual agent runs

**Required Changes:**
1. Before calling `orchestrator.run_agent()`, create `AgentExecution` record
2. Set `started_at = datetime.utcnow()`
3. Set `status = "running"`
4. After agent completes, update:
   - `completed_at`
   - `status = "completed"/"failed"`
   - `prompt_tokens`, `completion_tokens` (from agent output)
   - `cost_usd` (calculated from tokens)
   - `context_size_bytes` (from input size)

**Implementation Location:**
Modify `SecureOrchestrator.run_agent()` to accept optional `report_id` and create `AgentExecution` records.

**Estimated Effort:** 3-4 hours

---

### 6. Add Missing `agent_name` to `AgentOutput`

**File:** `genreport/core/orchestration/agent_models.py`

**Current Issue:**
```python
# In reports.py, we do this hacky check:
agent_name=output.agent_name if hasattr(output, 'agent_name') else section_name,
```

**Required Changes:**
1. Add `agent_name: str` field to `AgentOutput` Pydantic model
2. Ensure all agents populate this field when creating output
3. Remove `hasattr()` check in reports.py

**Estimated Effort:** 1 hour

---

## Low Priority

### 7. Improve Error Handling in Report Generation

**File:** `genreport/api/routers/reports.py`

**Current State:**
- Generic exception handler catches all errors
- Limited context in error messages
- No retry mechanism

**Improvements Needed:**
1. Add specific exception handling for:
   - `CrossTenantDataError` → return 403 with specific message
   - `UnsupportedJurisdictionError` → return 400
   - `ValueError` from agents → return 422
2. Add structured error logging with context:
   - Project ID, tenant ID, jurisdiction
   - Failed agent name
   - Stack trace
3. Consider retry logic for transient failures

**Estimated Effort:** 2-3 hours

---

### 8. Add Report Generation Metrics

**Files:**
- `genreport/api/routers/reports.py`
- New: `genreport/core/metrics/report_metrics.py`

**Metrics to Track:**
1. Reports generated per tenant (counter)
2. Report generation time distribution (histogram)
3. Report generation failures (counter with error type label)
4. Average completeness score (gauge)
5. Average cost per report (gauge)
6. Agent execution time per agent type (histogram)

**Integration:**
- Prometheus metrics export
- Grafana dashboard for monitoring
- Alerts for high failure rates or slow generation

**Estimated Effort:** 4-5 hours

---

### 9. Add Report Versioning

**Current State:**
- Reports can be soft-deleted but not versioned
- Regenerating a report overwrites previous data

**Enhancement:**
1. Add `version` field to `GeneratedReport`
2. Add `parent_report_id` for tracking regenerations
3. Keep previous versions when regenerating
4. UI to compare versions side-by-side

**Estimated Effort:** 6-8 hours

---

### 10. Implement Report Export Formats

**New Feature:**
- Export to PDF
- Export to Word (.docx)
- Export to JSON (for API consumers)

**Dependencies:**
- PDF generation library (WeasyPrint or ReportLab)
- python-docx for Word export
- Template system for formatting

**Estimated Effort:** 8-10 hours

---

## Testing Improvements

### 11. Add Integration Tests for Complete Report Flow

**File:** New `tests/integration/test_report_generation_flow.py`

**Coverage Needed:**
1. End-to-end flow: Upload Excel → Parse → Generate Report → Retrieve
2. Multi-agent execution with real agent implementations
3. Source attribution verification
4. PII detection in generated content
5. Audit log completeness

**Estimated Effort:** 4-6 hours

---

### 12. Add Performance Tests

**File:** New `tests/performance/test_report_generation_performance.py`

**Test Cases:**
1. Report generation time < 3 minutes (SLA)
2. Concurrent report generations (10 simultaneous)
3. Large project with 100+ KB chunks
4. Memory usage during generation
5. Database query count (N+1 prevention)

**Estimated Effort:** 3-4 hours

---

## Documentation Tasks

### 13. Create API Documentation for Report Endpoints

**File:** New `docs/guides/2025-10-XX-report-api-usage.md`

**Content:**
- API endpoint descriptions with examples
- Authentication requirements
- Request/response schemas
- Error codes and meanings
- Rate limiting details
- Best practices for report generation

**Estimated Effort:** 2-3 hours

---

### 14. Create Runbook for Report Generation Failures

**File:** New `docs/guides/2025-10-XX-troubleshooting-report-generation.md`

**Content:**
- Common failure scenarios and solutions
- How to check agent execution logs
- How to manually retry failed reports
- How to investigate PII detection false positives
- Performance troubleshooting

**Estimated Effort:** 2 hours

---

## Database Migrations Needed

### 15. Add Missing Indexes

**File:** New migration

**Indexes to Add:**
1. `idx_report_sections_agent` on `report_sections(agent_name)` - for agent performance queries
2. `idx_agent_executions_status` on `agent_executions(status)` - for monitoring running agents
3. `idx_source_references_kb_chunk` on `source_references(kb_chunk_id)` - for KB usage analytics

**Estimated Effort:** 30 minutes

---

### 16. Add `celery_task_id` Field for Async Support

**File:** New migration

**Changes:**
```sql
ALTER TABLE generated_reports
ADD COLUMN celery_task_id VARCHAR(255);

CREATE INDEX idx_generated_reports_task
ON generated_reports(celery_task_id);
```

**Estimated Effort:** 15 minutes

---

## Code Quality Improvements

### 17. Refactor `generate_report()` Function

**File:** `genreport/api/routers/reports.py`

**Current Issue:**
- Function is 180+ lines long
- Violates Single Responsibility Principle
- Hard to test individual parts

**Refactoring Plan:**
1. Extract `_create_report_record()` helper
2. Extract `_execute_agents()` helper
3. Extract `_store_sections()` helper
4. Extract `_calculate_metrics()` helper
5. Main function orchestrates these helpers

**Estimated Effort:** 2-3 hours

---

### 18. Add Type Hints to All Functions

**Files:** All Sprint 4 files

**Current State:**
- Some type hints missing
- Return types not always specified

**Required:**
- Add return type hints to all functions
- Add parameter type hints where missing
- Run mypy for type checking

**Estimated Effort:** 1-2 hours

---

## Priority Summary

**Critical (Do Next):**
1. Refactor API tests (HIGH - blocks test coverage)
2. Implement data loading (HIGH - blocks real usage)
3. Implement LLM cost calculation (HIGH - needed for monitoring)

**Important (Do Soon):**
4. Async report generation with Celery (MEDIUM - improves UX)
5. Add AgentExecution population (MEDIUM - needed for audit)
6. Add agent_name to AgentOutput (MEDIUM - removes hacky code)

**Nice to Have (Do Later):**
7-18. All other tasks (LOW - enhancements and polish)

---

## Notes

- This document should be updated as tasks are completed
- Mark completed tasks with ✅ and commit hash
- Add new tasks as they are discovered
- Link to related GitHub issues when created
- Estimate effort levels: hours for individual tasks

**Last Updated:** 2025-10-18
**Next Review:** When starting next Sprint 4 work session
