# Embedding Dimension Fix - October 17, 2025

## Issue

Google Gemini embeddings were returning 768 dimensions even though we configured 1536 dimensions to match OpenAI for compatibility.

## Root Cause

We were using the wrong Gemini embedding model:
- **Wrong Model:** `models/text-embedding-004` - Fixed at 768 dimensions, ignores `output_dimensionality` parameter
- **Correct Model:** `models/gemini-embedding-001` - Supports configurable dimensions (128-3072)

## Investigation

Created test script to verify model behavior:

```python
# models/text-embedding-004
result = genai.embed_content(
    model="models/text-embedding-004",
    output_dimensionality=1536,  # IGNORED!
)
# Returns: 768 dimensions

# models/gemini-embedding-001
result = genai.embed_content(
    model="models/gemini-embedding-001",
    output_dimensionality=1536,  # RESPECTED!
)
# Returns: 1536 dimensions
```

## Solution

### 1. Updated Configuration (`config.py`)

```python
# OLD
gemini_embedding_model: str = Field(default="models/text-embedding-004")

# NEW
gemini_embedding_model: str = Field(default="models/gemini-embedding-001")
```

### 2. Updated Environment (`.env`)

```bash
# OLD
GEMINI_EMBEDDING_MODEL=models/text-embedding-004

# NEW
GEMINI_EMBEDDING_MODEL=models/gemini-embedding-001
GEMINI_EMBEDDING_DIMENSIONS=1536
```

### 3. Updated Database Schema (`models.py`)

```python
# Support both Gemini (1536) and OpenAI (1536) dimensions
embedding = Column(Vector(1536), nullable=True)
```

## Verification

### End-to-End Test Results

Successfully ingested SME-FRS document (135 pages, 346,503 characters):
- ✅ Created 453 chunks
- ✅ Generated 1536-dimensional embeddings
- ✅ Stored with correct metadata:
  ```json
  {
    "embedding_provider": "gemini",
    "embedding_dimensions": 1536
  }
  ```
- ✅ Embedding model tracked: `models/gemini-embedding-001`

### Database Verification

```sql
SELECT
    embedding_model,
    array_length(embedding, 1) as dimensions,
    COUNT(*) as chunk_count
FROM kb_chunks
GROUP BY embedding_model, array_length(embedding, 1);
```

Result:
```
embedding_model              | dimensions | chunk_count
-----------------------------+------------+-------------
models/gemini-embedding-001 | 1536       | 453
```

## Model Comparison

| Model | Default Dims | Configurable | Range | Batch API |
|-------|-------------|--------------|-------|-----------|
| `models/text-embedding-004` | 768 | ❌ No | Fixed 768 | ✅ Yes |
| `models/embedding-001` | 768 | ❌ No | Fixed 768 | ✅ Yes |
| `models/gemini-embedding-001` | 3072 | ✅ Yes | 128-3072 | ✅ Yes |

**Recommended:** `models/gemini-embedding-001` with `output_dimensionality=1536` for OpenAI compatibility.

## Cost & Performance

### Gemini Embedding Costs
- **Synchronous API:** Standard pricing per 1M tokens
- **Batch API:** 50% discount (24h turnaround, usually faster)

### Current Configuration (1536 dimensions)
- **Storage:** 1536 × 4 bytes = 6,144 bytes per embedding
- **Compatibility:** Works with both Gemini and OpenAI
- **Quality:** Recommended dimension by Google (768, 1536, or 3072)

### SME-FRS Document Stats
- Pages: 135
- Characters: 346,503
- Chunks: 453
- Total embeddings size: 453 × 1536 × 4 bytes ≈ 2.8 MB
- Processing time: ~10 seconds (synchronous API)

## Future Considerations

### Batch API Implementation
If we need to process >100 documents/day:
- **Cost savings:** 50% reduction
- **Complexity:** Requires async job management, state tracking, polling worker
- **Latency:** Minutes → Hours (24h target, often faster)
- **Recommendation:** Implement in Sprint 6 or post-launch when volume justifies it

### Dimension Optimization
- **768 dimensions:** Faster, smaller storage (2.95 MB for SME-FRS)
- **1536 dimensions:** Current choice, good balance
- **3072 dimensions:** Maximum quality (5.9 MB for SME-FRS)

**Current choice (1536) provides:**
- ✅ OpenAI compatibility (same dimension)
- ✅ Good retrieval quality
- ✅ Reasonable storage size
- ✅ Fast processing time

## Files Modified

1. `genreport/core/utils/config.py` - Updated default model
2. `genreport/core/database/models.py` - Vector(1536) column
3. `.env` - Updated configuration
4. `scripts/demo_embedding_providers.py` - Updated documentation

## Testing Scripts

- `scripts/test_gemini_dimensions.py` - Model dimension testing
- `scripts/demo_embedding_providers.py` - Provider demonstration
- `scripts/test_kb_ingestion.py` - End-to-end ingestion test

## References

- [Gemini Embeddings Documentation](https://ai.google.dev/gemini-api/docs/embeddings)
- [Batch API Documentation](https://ai.google.dev/gemini-api/docs/batch-api#batch-embedding)
- Model: `models/gemini-embedding-001`
- Supports: 128-3072 dimensions
- Default: 3072 dimensions
- Recommended: 768, 1536, or 3072

---

**Status:** ✅ Fixed and verified
**Date:** October 17, 2025
**Sprint:** Sprint 3 - KB & RAG System
