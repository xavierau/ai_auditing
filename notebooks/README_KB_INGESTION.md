# Knowledge Base Ingestion - Quick Start Guide

**Created:** 2025-10-22
**Status:** Ready to use
**Notebook:** `01_kb_ingestion_test.ipynb`

---

## 🎯 Objective

Test and build the GenReport knowledge base using the existing SME-FRF PDF document and the implemented retrieval infrastructure.

---

## 📋 Prerequisites

### 1. Database Setup

Ensure PostgreSQL is running with PGVector extension:

```bash
# Check PostgreSQL
psql -U postgres -d genreport_dev -c "SELECT version();"

# Install PGVector (if not installed)
psql -U postgres -d genreport_dev -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 2. Environment Variables

Ensure `.env` file contains:

```bash
# Database
DATABASE_URL=postgresql://localhost/genreport_dev

# Google Gemini API (for embeddings)
GOOGLE_API_KEY=your_api_key_here

# Embedding configuration
EMBEDDING_PROVIDER=gemini
EMBEDDING_MODEL=models/text-embedding-004
EMBEDDING_DIMENSIONS=768
```

### 3. Python Dependencies

Install required packages:

```bash
source .venv/bin/activate

# Core dependencies (should already be installed)
pip install sqlalchemy
pip install psycopg2-binary
pip install google-generativeai

# PDF processing
pip install PyPDF2

# Jupyter (if not installed)
pip install jupyter notebook ipykernel
```

---

## 🚀 Running the Notebook

### Start Jupyter

```bash
source .venv/bin/activate
cd /Users/xavierau/Code/python/new_ai_auditing
jupyter notebook notebooks/01_kb_ingestion_test.ipynb
```

Or use VSCode with Jupyter extension:

```bash
code notebooks/01_kb_ingestion_test.ipynb
```

### Notebook Structure

The notebook is organized into **13 sections**:

1. **Setup & Imports** - Load dependencies
2. **Database Setup** - Connect to PostgreSQL
3. **Create Test Tenant** - Set up test tenant for HK jurisdiction
4. **Initialize Embedding Service** - Configure Gemini embeddings
5. **Extract Text from PDF** - Parse SME-FRF PDF (1.2MB)
6. **Chunk the Document** - Create overlapping chunks (1000 chars, 200 overlap)
7. **Categorize Chunks** - Classify chunks (definition, requirement, example, etc.)
8. **Create KB Document Entry** - Register document in knowledge_base table
9. **Generate Embeddings & Store** - Process chunks and save to PGVector
10. **Test Retrieval System** - Query the knowledge base
11. **Test Jurisdiction Filtering** - Verify HK/SG isolation
12. **Performance Analysis** - Measure query response times
13. **Database Statistics** - Review ingestion results

---

## ⚙️ Configuration

### Chunk Processing Limit

For **testing**, the notebook processes **50 chunks** by default:

```python
CHUNK_LIMIT = 50  # Process first 50 chunks for testing
```

For **full ingestion**, set to `None`:

```python
CHUNK_LIMIT = None  # Process all chunks (~200-300 total)
```

### Chunk Size & Overlap

Adjust chunking parameters:

```python
chunks = create_chunks(
    pages_text,
    chunk_size=1000,    # Target chunk size in characters
    overlap=200,        # Overlap between chunks
)
```

**Recommendations:**
- **Small chunks (500-800 chars):** Better precision, more chunks
- **Large chunks (1500-2000 chars):** Better context, fewer chunks
- **Overlap (150-300 chars):** Prevents information loss at boundaries

---

## 📊 Expected Results

### Processing Metrics

**SME-FRF Document:**
- **Size:** 1.2 MB
- **Pages:** ~150-200 pages
- **Chunks (50 limit):** 50 chunks
- **Chunks (full):** ~200-300 chunks
- **Processing time (50 chunks):** 2-3 minutes
- **Processing time (full):** 10-15 minutes

### Retrieval Performance

**Query Response Times:**
- **Average:** <200ms per query
- **With cache:** <50ms per query (second query onwards)
- **Top-5 results:** Highly relevant (similarity >0.7)

### Database Storage

**After 50 chunks:**
```
knowledge_base: 1 document
kb_chunks: 50 chunks
Embeddings: 50 × 768 dimensions = 38,400 floats
Storage: ~500 KB (with metadata)
```

**After full ingestion:**
```
knowledge_base: 1 document
kb_chunks: 200-300 chunks
Embeddings: ~230,000 floats
Storage: ~2-3 MB (with metadata)
```

---

## 🧪 Testing Scenarios

### 1. Revenue Recognition

```python
query = "revenue recognition accounting policy"
results = retriever.retrieve(query, top_k=5)
```

**Expected:** Chunks discussing SME-FRS revenue recognition requirements, with similarity >0.75

### 2. Property, Plant & Equipment

```python
query = "property plant equipment depreciation accounting"
results = retriever.retrieve(query, top_k=5)
```

**Expected:** Chunks on fixed assets, depreciation methods, measurement

### 3. Financial Instruments

```python
query = "financial instruments disclosure requirements"
results = retriever.retrieve(query, top_k=5)
```

**Expected:** Chunks on financial instruments recognition, measurement, disclosure

---

## 🔍 Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'PyPDF2'"

```bash
source .venv/bin/activate
pip install PyPDF2
```

### Issue: "GOOGLE_API_KEY not set"

Add to `.env` file:

```bash
GOOGLE_API_KEY=your_actual_api_key_here
```

Get API key from: https://makersuite.google.com/app/apikey

### Issue: "relation 'vector' does not exist"

Install PGVector extension:

```bash
psql -U postgres -d genreport_dev
CREATE EXTENSION IF NOT EXISTS vector;
\q
```

### Issue: "Too many API requests"

Gemini API has rate limits:
- **Free tier:** 60 requests/minute
- **Solution:** Add delays between batch processing or upgrade to paid tier

### Issue: "Embedding dimensions mismatch"

Ensure consistent dimensions:
- **KBChunk.embedding:** VECTOR(768)
- **Gemini text-embedding-004:** 768 dimensions

If using different model, update both:

```python
# Code
embedding_service = EmbeddingService(dimensions=1536)

# Database migration
ALTER TABLE kb_chunks ALTER COLUMN embedding TYPE VECTOR(1536);
```

---

## 📈 Next Steps

### Immediate (After Testing)

1. **Full Ingestion**
   - Set `CHUNK_LIMIT = None`
   - Run full document processing
   - Verify all chunks stored correctly

2. **Quality Review**
   - Sample 10-20 chunks manually
   - Verify content extraction quality
   - Check chunk boundaries (no truncated sentences)

### Short-Term (Week 1)

3. **Additional Documents**
   - HKFRS 15 (Revenue Recognition)
   - HKAS 16 (Property, Plant & Equipment)
   - HKAS 2 (Inventories)
   - HKAS 1 (Presentation of Financial Statements)

4. **Enhanced Categorization**
   - LLM-based chunk classification
   - Extract section headers and numbers
   - Identify cross-references

### Medium-Term (Month 1)

5. **Production Optimization**
   - Batch embedding generation (10x faster)
   - Async ingestion with Celery
   - Monitoring and alerting
   - Automated quality checks

6. **User Testing**
   - Test with real audit queries
   - Tune retrieval parameters (top_k, filters)
   - Collect relevance feedback

---

## 📚 Related Documentation

- **Knowledge Base Schema:** `genreport/core/database/models.py` (KnowledgeBase, KBChunk)
- **Retrieval System:** `genreport/core/retrieval/kb_retriever.py`
- **Embedding Service:** `genreport/core/retrieval/embedding_service.py`
- **Chunk Categorizer:** `genreport/core/retrieval/chunk_categorizer.py`
- **Sprint 3 Report:** `docs/reports/2025-10-18-sprint3-complete.md`

---

## 🎉 Success Criteria

**✅ Knowledge Base is ready when:**

1. ✅ All chunks extracted and stored
2. ✅ Embeddings generated for all chunks
3. ✅ Retrieval returns relevant results (similarity >0.7)
4. ✅ Jurisdiction filtering works correctly (HK only)
5. ✅ Query response time <200ms
6. ✅ No database errors or warnings
7. ✅ Sample queries return expected content

---

**Status:** Ready for testing 🚀

**Last Updated:** 2025-10-22
**Maintainer:** Development Team
