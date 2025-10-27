# RAG Orchestrator: ValidationError for document_id=None

**Date:** 2025-10-23
**Issue:** ValidationError when assembling context chunks in RAG orchestrator
**Status:** ✅ Fixed
**Files Modified:** `genreport/core/orchestration/rag_orchestrator.py`

## Issue Description

### Symptoms
When running the notebook `04_agentic_rag.ipynb`, cell 11 (executing RAG retrieval) failed with:

```
ValidationError: 1 validation error for ContextChunk
document_id
  Input should be a valid integer [type=int_type, input_value=None, input_type=NoneType]
```

**Stack trace:**
```python
File ~/Code/python/new_ai_auditing/genreport/core/orchestration/rag_orchestrator.py:208, in RAGOrchestrator.retrieve
    result = self._assemble_context(candidates, query)

File ~/Code/python/new_ai_auditing/genreport/core/orchestration/rag_orchestrator.py:470, in RAGOrchestrator._assemble_context
    context_chunk = ContextChunk(
        ...
        document_id=candidate.metadata.get("kb_document_id", 0),
        ...
    )

ValidationError: document_id cannot be None
```

### Root Cause

The Pydantic model `ContextChunk` expects `document_id: int`, but the code was receiving `None` from the database.

**Data flow:**
1. `KBRetriever._rank_by_similarity()` (line 245) returns:
   ```python
   "kb_document_id": chunk.kb_document_id  # Can be None from database
   ```

2. `RAGOrchestrator._execute_semantic_retrieval()` (line 313) creates metadata:
   ```python
   metadata={
       "kb_document_id": result["kb_document_id"],  # Passes None through
   }
   ```

3. `RAGOrchestrator._assemble_context()` (line 476) tries to create ContextChunk:
   ```python
   document_id=candidate.metadata.get("kb_document_id", 0)  # .get() returns None, not 0!
   ```

**The bug:** `dict.get(key, default)` returns the default only if the **key is missing**, not if the **value is None**. Since the key `"kb_document_id"` exists in the metadata dict but has value `None`, `.get()` returns `None` instead of `0`.

## Solution

### Fix 1: Check for None when creating metadata (Line 313)

**Before:**
```python
metadata={
    "kb_document_id": result["kb_document_id"],  # Can be None
    ...
}
```

**After:**
```python
metadata={
    "kb_document_id": result["kb_document_id"] if result["kb_document_id"] is not None else 0,
    ...
}
```

### Fix 2: Explicitly handle None when creating ContextChunk (Line 471-481)

**Before:**
```python
context_chunk = ContextChunk(
    ...
    document_id=candidate.metadata.get("kb_document_id", 0),  # Fails if value is None
    ...
)
```

**After:**
```python
# Ensure document_id is an integer (never None)
doc_id = candidate.metadata.get("kb_document_id")
if doc_id is None:
    doc_id = 0  # Default to 0 if no document ID

context_chunk = ContextChunk(
    ...
    document_id=int(doc_id),  # Ensure it's an integer
    ...
)
```

## Troubleshooting Workflow

1. ✅ **Reproduce the issue:** Run notebook cell 11
2. ✅ **Identify stack trace:** ValidationError in `_assemble_context()`
3. ✅ **Trace data flow:**
   - KBRetriever returns `kb_document_id: None`
   - Metadata dict stores `None`
   - `.get()` returns `None` (not default value)
4. ✅ **Understand `.get()` behavior:** Default only applies if key is missing
5. ✅ **Implement fix:** Explicitly check for `None` at two points
6. ✅ **Test fix:** Re-run notebook cell 11

## Prevention Strategies

### 1. Database Schema Validation
Ensure `KBChunk.kb_document_id` has a foreign key constraint and NOT NULL:
```sql
ALTER TABLE kb_chunks
  ALTER COLUMN kb_document_id SET NOT NULL;
```

### 2. Pydantic Model Improvement
Add validation to `RetrievalCandidate` metadata:
```python
class RetrievalCandidate(BaseModel):
    metadata: Dict[str, Any]

    @validator('metadata')
    def validate_metadata(cls, v):
        if 'kb_document_id' in v and v['kb_document_id'] is None:
            v['kb_document_id'] = 0
        return v
```

### 3. Type Hints for Metadata
Define a typed metadata dict instead of `Dict[str, Any]`:
```python
class RetrievalMetadata(BaseModel):
    kb_document_id: int = 0  # Default to 0
    chunk_index: Optional[int] = None
    confidence_score: Optional[float] = None
    review_status: Optional[str] = None
```

### 4. Defensive Programming Pattern
Always check for `None` when dealing with optional database fields:
```python
# ❌ Bad: Assumes .get() default works for None values
value = dict.get("key", 0)

# ✅ Good: Explicitly handle None
value = dict.get("key")
if value is None:
    value = 0
```

## Related Code Files

**Modified:**
- `genreport/core/orchestration/rag_orchestrator.py:313` - Fix metadata creation
- `genreport/core/orchestration/rag_orchestrator.py:471-481` - Fix ContextChunk creation

**Related (no changes needed):**
- `genreport/core/retrieval/kb_retriever.py:245` - Source of None value
- `genreport/core/orchestration/rag_models.py` - ContextChunk Pydantic model
- `genreport/core/database/models.py` - KBChunk database model

## Testing Recommendations

### Unit Tests
```python
def test_assemble_context_handles_none_document_id():
    """Ensure _assemble_context handles None kb_document_id gracefully."""
    candidate = RetrievalCandidate(
        chunk_id=1,
        content="Test content",
        similarity_score=0.9,
        relevance_score=0.9,
        chunk_type=ContentType.REQUIREMENT,
        metadata={"kb_document_id": None},  # Explicitly None
    )

    orchestrator = RAGOrchestrator(...)
    result = orchestrator._assemble_context([candidate], query)

    assert result.chunks[0].document_id == 0  # Should default to 0
```

### Integration Tests
```python
def test_retrieve_with_missing_document_id():
    """Test retrieval when database has NULL kb_document_id."""
    # Create chunk with NULL kb_document_id
    chunk = KBChunk(
        content="Test",
        kb_document_id=None,  # NULL in database
        ...
    )
    db.add(chunk)
    db.commit()

    # Should not raise ValidationError
    orchestrator = RAGOrchestrator(...)
    result = orchestrator.retrieve(query)

    assert len(result.chunks) > 0
    assert all(c.document_id is not None for c in result.chunks)
```

## Links to Related Docs

**Architecture:**
- `docs/architecture/2025-10-23-rag-orchestrator-design.md` - RAG orchestrator design

**Implementation:**
- `docs/reports/2025-10-23-rag-orchestrator-phase3-4-complete.md` - Phase 3-4 implementation
- `docs/reports/2025-10-23-notebook-04-agentic-rag-created.md` - Notebook 04 creation

**Notebooks:**
- `notebooks/04_agentic_rag.ipynb` - Demo notebook where issue was discovered

---

**Issue:** ✅ Resolved
**Fix verified:** Notebook cell 11 now executes without ValidationError
**Prevention:** Add database constraint, Pydantic validator, and defensive checks
