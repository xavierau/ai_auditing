# Full Document Ingestion Guide

**Date:** 2025-10-22
**Status:** Ready to Execute
**Estimated Time:** 10-15 minutes

---

## Overview

Notebook 01 has been updated to ingest the **complete SME-FRS PDF** (527 chunks covering all pages) instead of just the first 50 chunks. This is required for proper testing of the structure-aware retrieval system.

## Problem

Currently, only **13 pages** (50 chunks) of the SME-FRS document are in the database. This means:
- Template queries can't find Appendix 2 (pages 87-120) because it's not ingested yet
- Requirement queries can't find Section 17 (Property, Plant & Equipment, pages 45-52)
- Structure-aware retrieval returns empty results because page ranges don't match

## Solution

Run notebook 01 with the updated settings to ingest ALL 527 chunks.

---

## Steps to Execute

### 1. Open Notebook 01

```bash
jupyter notebook notebooks/01_kb_ingestion_test.ipynb
```

### 2. Run Cells in Sequence

**Important:** Run cells **26, 27, 28** in order:

- **Cell 26:** Creates KB document (auto-deletes existing)
- **Cell 27:** Markdown heading (skip)
- **Cell 28:** **Processes ALL 527 chunks** (changed from 50)

### 3. Monitor Progress

Cell 28 will print progress every 50 chunks:

```
Processing all chunks...

✅ Processed 50/527 chunks
✅ Processed 100/527 chunks
✅ Processed 150/527 chunks
...
✅ Processed 527/527 chunks

✅ Successfully ingested 527 chunks
   Document ID: 6
   Status: completed
```

**Expected Time:** ~10-15 minutes (depends on Gemini API speed)

---

## What Changed

### Before (Cell 28):
```python
CHUNK_LIMIT = 50  # Only first 50 chunks
```

### After (Cell 28):
```python
CHUNK_LIMIT = None  # Process ALL chunks
```

### Additional Improvements:
- Batch commits every 50 chunks (prevents memory issues)
- Auto-deletes existing document (clean re-ingestion)
- Better progress reporting

---

## Verification

After ingestion completes, verify in database:

```sql
-- Check total chunks
SELECT COUNT(*) FROM kb_chunks WHERE jurisdiction = 'HK';
-- Expected: 527 (or more if run multiple times)

-- Check page range
SELECT MIN((chunk_metadata->>'page_num')::int),
       MAX((chunk_metadata->>'page_num')::int)
FROM kb_chunks
WHERE jurisdiction = 'HK';
-- Expected: 1 - 133 (full document range)

-- Check document
SELECT id, title, created_at
FROM knowledge_base
WHERE title = 'Hong Kong SME-FRS (December 2021)';
```

---

## Next Steps After Ingestion

Once the full document is ingested:

### 1. Re-run Notebook 02 (Semantic Chunking Evaluation)

```bash
jupyter notebook notebooks/02_semantic_chunking_evaluation.ipynb
```

**Expected Improvements:**
- Pass rate: 20% → **60%+** (with full document)
- More relevant results for template queries
- Better coverage of all accounting topics

### 2. Re-run Notebook 03 (Structure-Aware Comparison)

```bash
jupyter notebook notebooks/03_structure_aware_retrieval_test.ipynb
```

**Expected Results:**
- Structure-aware retrieval will now return results (not empty)
- Template queries will rank Appendix 2 as #1 (not #3)
- Explainable navigation paths: "Searched Appendix 2, Section 17"

### 3. Update Document Structure (if needed)

If page numbers in the database don't match the hardcoded structure in notebook 03, update the `document_structure` dictionary to match actual page ranges.

---

## Troubleshooting

### Issue: "Document already exists"

**Solution:** Cell 26 now auto-deletes existing documents. If you see this message, it will automatically clean up and re-ingest.

### Issue: Slow ingestion

**Cause:** Gemini API rate limits or network latency

**Solution:**
- Wait for completion (it will finish)
- Check API quotas at https://aistudio.google.com/app/apikey
- Embedding generation is the bottleneck (~1-2 seconds per chunk)

### Issue: Memory errors

**Solution:** The notebook now commits every 50 chunks to prevent memory issues. If it still fails, restart kernel and re-run from cell 26.

---

## Files Modified

1. **notebooks/01_kb_ingestion_test.ipynb**
   - Cell 26: Auto-delete existing document
   - Cell 28: Changed CHUNK_LIMIT from 50 to None

---

## Expected Outcome

After completion:

✅ **527 chunks** ingested covering the **complete SME-FRS document**
✅ **Page range:** 1-133 (full coverage)
✅ **Sections available:**
   - Section 1-2 (Scope, Accounting Policies)
   - Section 13 (Inventories)
   - Section 17 (Property, Plant & Equipment)
   - Section 20 (Leases)
   - Section 23 (Revenue)
   - Section 33 (Related Party Disclosures)
   - **Appendix 2 (Illustrative Financial Statements)** ← Critical for template queries

✅ Ready for structure-aware retrieval testing with real data
