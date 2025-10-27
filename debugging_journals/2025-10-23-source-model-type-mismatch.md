# Source Model Type Mismatch: UUID vs Integer

**Date:** 2025-10-23
**Issue:** ValidationError when creating Source objects from ContextChunk
**Status:** ✅ Fixed
**Files Modified:** `genreport/core/orchestration/agent_models.py`

## Issue Description

### Symptoms
When running the agent integration demo in notebook (Cell 19), creating `Source` objects failed with:

```
ValidationError: 2 validation errors for Source
document_id
  UUID input should be a string, bytes or UUID object [type=uuid_type, input_value=8, input_type=int]
chunk_id
  UUID input should be a string, bytes or UUID object [type=uuid_type, input_value=807, input_type=int]
```

**Code that failed:**
```python
for chunk in rag_result.chunks:
    source = Source(
        document_id=chunk.document_id,  # int from ContextChunk
        chunk_id=chunk.chunk_id,        # int from ContextChunk
        relevance_score=chunk.relevance_score,
        snippet=chunk.content,
    )
```

### Root Cause

**Type Mismatch in Model Definitions:**

1. **Database models** use `Integer` IDs:
   ```python
   # genreport/core/database/models.py
   class KBChunk(Base):
       id = Column(Integer, primary_key=True)  # Integer ID
       kb_document_id = Column(Integer, ForeignKey("knowledge_base.id"))

   class KnowledgeBase(Base):
       id = Column(Integer, primary_key=True)  # Integer ID
   ```

2. **RAG models** use `int` types:
   ```python
   # genreport/core/orchestration/rag_models.py
   class ContextChunk(BaseModel):
       chunk_id: int = Field(...)      # int type
       document_id: int = Field(...)   # int type
   ```

3. **Agent models** expected `UUID` types (INCORRECT):
   ```python
   # genreport/core/orchestration/agent_models.py - BEFORE
   class Source(BaseModel):
       document_id: UUID = Field(...)  # ❌ UUID type (wrong!)
       chunk_id: UUID = Field(...)     # ❌ UUID type (wrong!)
   ```

**The Problem:** `Source` was defined with `UUID` types but the entire system uses `int` IDs. This was a design inconsistency that made it impossible to create `Source` objects from actual database results.

## Solution

### Fix: Change Source Model to Use Integer IDs

Updated `Source` model to match the database and RAG model types:

```python
# genreport/core/orchestration/agent_models.py - AFTER
class Source(BaseModel):
    """Reference to a knowledge base document chunk.

    Provides traceability from generated disclosure back to source material.
    """

    document_id: int = Field(..., description="KB document ID (integer from database)")
    chunk_id: int = Field(..., description="Document chunk ID (integer from database)")
    relevance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Relevance score from retriever (0-1)",
    )
    snippet: str = Field(
        ...,
        min_length=1,
        description="Text snippet from the chunk",
    )
```

**Benefits:**
1. ✅ **Type consistency:** All models use `int` for IDs
2. ✅ **Works with database:** Matches actual database schema
3. ✅ **No conversion needed:** Direct mapping from ContextChunk → Source
4. ✅ **Backward compatible:** Existing agent code works unchanged

## Troubleshooting Workflow

1. ✅ **Reproduce the issue:** Run Cell 19 (agent integration demo)
2. ✅ **Identify error:** ValidationError on `Source` creation
3. ✅ **Trace type flow:**
   - Database: Integer IDs
   - ContextChunk: int types
   - Source: UUID types (MISMATCH!)
4. ✅ **Understand design intent:** IDs should be integers (database is source of truth)
5. ✅ **Implement fix:** Change `Source` model to use `int` instead of `UUID`
6. ✅ **Verify fix:** Re-run Cell 19 - Source objects created successfully

## Why This Happened

This appears to be a **design documentation mismatch**:

1. **Initial design docs** may have specified UUIDs for traceability
2. **Actual database implementation** used Integer IDs (more common, better performance)
3. **RAG models** correctly followed database schema (int types)
4. **Agent models** followed initial design docs (UUID types)

**Result:** Type mismatch between layers.

## Impact Analysis

### Code Affected

**✅ Fixed automatically:**
- `BaseFinancialAgent._fetch_context()` - Creates Source objects
- `notebooks/04_agentic_rag.ipynb` (Cell 19) - Agent integration demo
- All future agents that use Source model

**✅ No changes needed:**
- `ContextChunk` already uses `int` (correct)
- Database models already use `Integer` (correct)
- RAG orchestrator already returns `int` IDs (correct)

## Prevention Strategies

### 1. Type Consistency Validation

Add a test to verify type consistency across layers:

```python
# tests/test_type_consistency.py
def test_id_types_are_consistent():
    """Ensure all models use consistent ID types."""
    from genreport.core.database.models import KBChunk, KnowledgeBase
    from genreport.core.orchestration.rag_models import ContextChunk
    from genreport.core.orchestration.agent_models import Source

    # Database uses Integer
    assert KBChunk.id.type.python_type == int
    assert KnowledgeBase.id.type.python_type == int

    # RAG models use int
    assert ContextChunk.model_fields["chunk_id"].annotation == int
    assert ContextChunk.model_fields["document_id"].annotation == int

    # Agent models use int (not UUID)
    assert Source.model_fields["chunk_id"].annotation == int
    assert Source.model_fields["document_id"].annotation == int
```

### 2. Integration Test for Source Creation

Add test to ensure Source objects can be created from real data:

```python
def test_source_creation_from_context_chunk():
    """Ensure Source can be created from ContextChunk."""
    # Create ContextChunk (simulating RAG result)
    chunk = ContextChunk(
        content="Test content",
        source_reference="Test source",
        relevance_score=0.9,
        chunk_type=ContentType.REQUIREMENT,
        chunk_id=123,         # int from database
        document_id=456,      # int from database
        section_context="Test section",
        is_mandatory=True,
        cross_references=[],
    )

    # Should be able to create Source without ValidationError
    source = Source(
        document_id=chunk.document_id,
        chunk_id=chunk.chunk_id,
        relevance_score=chunk.relevance_score,
        snippet=chunk.content,
    )

    assert source.document_id == 456
    assert source.chunk_id == 123
    assert isinstance(source.document_id, int)
    assert isinstance(source.chunk_id, int)
```

### 3. Documentation Alignment

Update architecture docs to reflect actual types:

```markdown
# docs/architecture/agent-models.md

## Source Model

**ID Types:** Integer (not UUID)

Rationale:
- Database uses Integer primary keys for performance
- Simpler joins and queries
- Easier debugging (readable IDs)
- Consistent with existing schema

If UUID traceability is needed, add separate UUID columns:
```python
class KBChunk(Base):
    id = Column(Integer, primary_key=True)      # DB primary key
    uuid = Column(UUID, unique=True, index=True)  # External reference
```
```

### 4. Type Hints in Comments

Add type hints to clarify expectations:

```python
class Source(BaseModel):
    """Reference to a knowledge base document chunk.

    Note: IDs are integers matching database schema (KBChunk.id, KnowledgeBase.id).
    Do NOT use UUID types here - the database uses Integer primary keys.
    """

    document_id: int = Field(..., description="KB document ID (from knowledge_base.id)")
    chunk_id: int = Field(..., description="Chunk ID (from kb_chunks.id)")
```

## Related Code Files

**Modified:**
- `genreport/core/orchestration/agent_models.py:18-19` - Changed UUID to int

**Related (no changes needed):**
- `genreport/core/database/models.py` - KBChunk, KnowledgeBase (already int)
- `genreport/core/orchestration/rag_models.py` - ContextChunk (already int)
- `genreport/core/orchestration/base_agent.py` - _fetch_context() (now works)
- `notebooks/04_agentic_rag.ipynb` (Cell 19) - Agent demo (now works)

## Testing Recommendations

### Unit Tests

```python
def test_source_model_accepts_integers():
    """Ensure Source model accepts integer IDs."""
    source = Source(
        document_id=123,  # int, not UUID
        chunk_id=456,     # int, not UUID
        relevance_score=0.85,
        snippet="Test snippet",
    )

    assert source.document_id == 123
    assert source.chunk_id == 456
    assert isinstance(source.document_id, int)
    assert isinstance(source.chunk_id, int)

def test_source_model_rejects_uuids():
    """Ensure Source model rejects UUID inputs."""
    from uuid import uuid4

    with pytest.raises(ValidationError):
        Source(
            document_id=uuid4(),  # UUID should fail
            chunk_id=uuid4(),     # UUID should fail
            relevance_score=0.85,
            snippet="Test snippet",
        )
```

### Integration Tests

```python
def test_agent_fetch_context_returns_valid_sources():
    """Ensure agent _fetch_context returns valid Source objects."""
    # Create agent with RAG orchestrator
    agent = create_test_agent(...)

    # Fetch context
    sources = agent._fetch_context("test query")

    # Verify all sources are valid
    assert len(sources) > 0
    for source in sources:
        assert isinstance(source, Source)
        assert isinstance(source.document_id, int)
        assert isinstance(source.chunk_id, int)
        assert 0.0 <= source.relevance_score <= 1.0
        assert len(source.snippet) > 0
```

## Links to Related Docs

**Architecture:**
- `docs/architecture/2025-10-23-rag-orchestrator-design.md` - RAG orchestrator
- `docs/architecture/agent-models.md` - Agent input/output models (needs update)

**Implementation:**
- `docs/reports/2025-10-23-notebook-04-improvements-complete.md` - Notebook improvements
- `docs/reports/2025-10-23-source-model-type-mismatch.md` - This file

**Notebooks:**
- `notebooks/04_agentic_rag.ipynb` (Cell 19) - Agent integration demo (now works)

---

**Issue:** ✅ Resolved
**Fix verified:** Source objects can now be created from ContextChunk data
**Prevention:** Add type consistency tests and documentation updates
