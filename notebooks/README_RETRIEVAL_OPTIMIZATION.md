# Knowledge Base Retrieval Optimization - Quick Start

This guide helps you run the baseline evaluation and compare chunking strategies.

---

## Prerequisites

1. **Complete notebook 01** (`01_kb_ingestion_test.ipynb`)
2. **Have `pages_markdown` data available**

---

## Step 1: Save Data from Notebook 01

If you haven't already, add this cell to the end of `01_kb_ingestion_test.ipynb` and run it:

```python
import json

# Save pages_markdown to JSON for use in other notebooks
output_path = "smefrf.json"

with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(pages_markdown, f, ensure_ascii=False, indent=2)

print(f"✅ Saved {len(pages_markdown)} pages to {output_path}")
```

This creates `smefrf.json` that notebook 02 will use.

---

## Step 2: Run Baseline Evaluation

Open `02_semantic_chunking_evaluation.ipynb` and run all cells sequentially.

**What it does:**

1. **Loads the document** from `smefrf.json`
2. **Compares chunking strategies:**
   - Old: Fixed 1000 chars
   - New: Semantic sections (300-5000 chars)
3. **Generates semantic chunks** with enhanced metadata
4. **Ingests test collection** (first 100 chunks)
5. **Runs evaluation suite** with 10 accountant test queries
6. **Generates comparison report**

**Expected runtime:** 15-20 minutes (mostly embedding generation)

---

## Step 3: Review Results

After running notebook 02, you'll see:

### Chunking Comparison

```
OLD STRATEGY (Fixed 1000 chars):
   Total chunks: 527
   Avg size: 1053 chars
   Section context: NO
   Content typing: NO

NEW STRATEGY (Semantic sections):
   Total chunks: ~200-300 (fewer, larger)
   Avg size: ~1500 chars
   Section context: YES ✅
   Content typing: YES ✅
   Chunks with section numbers: ~150
```

### Evaluation Report

```
KNOWLEDGE BASE RETRIEVAL EVALUATION REPORT
==========================================

Overall: 6/10 queries passed (60%)
Average MRR: 0.65
Average top-1 similarity: 0.72

DETAILED RESULTS:
-----------------

1. ✅ PASS
   Query: revenue recognition accounting policy
   Similarity: 0.78
   Keywords: ✓
   Fragmented: ✓ No

2. ❌ FAIL
   Query: fixed asset disclosure requirements
   Similarity: 0.68
   Keywords: ✗
   Fragmented: ✗ Yes (only 800 chars, expected 1500)
   Failure: Fragmented; Missing required keywords

...
```

---

## Step 4: Interpret Results

### Good Signs (Proceed with Implementation)

- ✅ Pass rate improves with semantic chunking
- ✅ Fragmentation rate decreases
- ✅ Section context helps with relevance
- ✅ Content type classification is accurate (>90%)

### Warning Signs (Need More Tuning)

- ⚠️ Pass rate doesn't improve significantly
- ⚠️ Large chunks (>3000 chars) have lower similarity
- ⚠️ Content type classification <80% accurate
- ⚠️ Query time increases significantly

### Bad Signs (Reconsider Approach)

- ❌ Pass rate decreases
- ❌ More fragmentation than before
- ❌ Query time >500ms
- ❌ Embeddings for large chunks are poor quality

---

## Step 5: Next Steps Based on Results

### If Results are GOOD → Week 2 Implementation

1. Run semantic chunking on **full document** (all chunks, not just 100)
2. Execute database migration
3. Implement intent-aware retrieval
4. Deploy to dev environment for testing

### If Results are MIXED → Tuning Phase

1. Adjust chunk size parameters:
   ```python
   semantic_chunker = SemanticChunker(
       min_chunk_size=500,      # Increase if too many tiny chunks
       max_chunk_size=4000,     # Decrease if embeddings are poor
       target_chunk_size=1200,  # Adjust based on avg performance
   )
   ```

2. Tune content type classification (use LLM if rule-based is <90%)

3. Re-run evaluation

### If Results are BAD → Alternative Approaches

Consider:
- **Hierarchical chunking:** Parent chunk (full section) + child chunks (paragraphs)
- **Hybrid approach:** Mix of fixed-size and semantic for different content types
- **Query expansion:** Improve query understanding before retrieval
- **Post-retrieval merging:** Merge fragments after retrieval instead of during chunking

---

## Files Reference

**Implementation:**
- `genreport/core/retrieval/semantic_chunker.py` - Semantic chunking logic
- `genreport/core/retrieval/kb_retriever.py` - Retrieval system (existing)

**Testing:**
- `tests/retrieval/test_accountant_queries.py` - Gold-standard test queries and evaluation framework
- `notebooks/02_semantic_chunking_evaluation.ipynb` - End-to-end evaluation

**Documentation:**
- `docs/architecture/2025-10-22-retrieval-optimization-plan.md` - Detailed implementation plan
- `docs/reports/2025-10-22-retrieval-optimization-summary.md` - Executive summary

---

## Troubleshooting

### Issue: "smefrf.json not found"

**Solution:** Run notebook 01 and add the JSON export cell (see Step 1)

### Issue: "Module not found: semantic_chunker"

**Solution:**
```bash
cd /Users/xavierau/Code/python/new_ai_auditing
source .venv/bin/activate
# Verify path
echo $PYTHONPATH
# Should include project root
```

### Issue: "Database error: kb_chunks table missing columns"

**Solution:** Database migration not run yet. This is expected - new columns will be added in Week 2.

For now, evaluation uses existing `chunk_metadata` JSON field.

### Issue: "Embedding generation too slow"

**Solution:** Reduce `CHUNK_LIMIT` in notebook:
```python
CHUNK_LIMIT = 50  # Instead of 100
```

### Issue: "Evaluation shows 0% pass rate"

**Possible causes:**
1. No chunks ingested (check database)
2. Retriever not finding any results (check jurisdiction filter)
3. Test queries don't match document content (check query keywords)

**Debug:**
```python
# In notebook, add debug cell:
db = SessionLocal()
chunk_count = db.query(KBChunk).filter(KBChunk.jurisdiction == "HK").count()
print(f"Total HK chunks in DB: {chunk_count}")

# Test single query
retriever = KBRetriever(db, "HK", TENANT_ID, embedding_service)
results = retriever.retrieve("revenue", top_k=5)
print(f"Found {len(results)} results for 'revenue'")
```

---

## Quick Commands

**Run evaluation:**
```bash
cd notebooks
jupyter notebook 02_semantic_chunking_evaluation.ipynb
```

**Run tests (after implementation):**
```bash
pytest tests/retrieval/test_accountant_queries.py -v
```

**Check database:**
```bash
psql $DATABASE_URL
> SELECT COUNT(*) FROM kb_chunks WHERE jurisdiction = 'HK';
> SELECT chunk_type, COUNT(*) FROM kb_chunks GROUP BY chunk_type;
```

---

## Expected Timeline

- **Step 1:** 5 minutes (save JSON)
- **Step 2:** 20 minutes (run notebook)
- **Step 3:** 10 minutes (review results)
- **Step 4:** 15 minutes (interpret and decide)
- **Step 5:** Varies (proceed with Week 2 or tune)

**Total:** ~1 hour for complete baseline evaluation

---

## Success Criteria Reminder

For **GO decision** to Week 2 implementation:

- ✅ Semantic chunking shows **improvement** over fixed-size (any amount)
- ✅ No **major performance degradation** (query time <500ms)
- ✅ Section context extraction **works** (>70% chunks have section numbers)
- ✅ Content type classification **reasonable** (>70% accuracy on manual review)

**It doesn't have to be perfect** - we'll tune in Week 3!

---

## Questions?

Refer to:
- **Architecture plan:** `docs/architecture/2025-10-22-retrieval-optimization-plan.md`
- **Summary:** `docs/reports/2025-10-22-retrieval-optimization-summary.md`
- **Code:** `genreport/core/retrieval/semantic_chunker.py`
