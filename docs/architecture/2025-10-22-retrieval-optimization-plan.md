# Knowledge Base Retrieval Optimization Plan

**Date:** 2025-10-22
**Status:** Planning
**Sprint:** Knowledge Base Enhancement
**Author:** Architecture Team

---

## Executive Summary

Current "plain" chunking (fixed 1000 chars) + semantic search is insufficient for accountant workflows. This document outlines a **phased approach** to optimize retrieval for real-world usage patterns with **measurable success criteria**.

**Key Insight:** Accountants need **complete, actionable content** (templates, requirement checklists, worked examples), not fragmented theoretical explanations.

---

## Problem Statement

### Current System Limitations

1. **Fragmentation:** Fixed 1000-char chunks split semantic units
   - Templates broken across 2-3 chunks
   - Requirement lists incomplete
   - Examples lack context

2. **No Content Classification:** All chunks treated equally
   - Can't prioritize templates over definitions
   - Can't boost requirement chunks for compliance queries

3. **Missing Hierarchical Context:**
   - No section number tracking
   - No parent-child relationships
   - No cross-references

4. **Poor Relevance for Accountant Queries:**
   - Query: "revenue policy template" → Returns theory, not boilerplate text
   - Query: "fixed asset disclosures" → Returns partial requirements list

### Impact on User Experience

**Scenario:** Accountant preparing year-end financial statements

```
Current System:
  Query: "depreciation accounting policy template"
  Result: Chunk 245 (800 chars) - First half of policy ❌
          Chunk 67 (900 chars) - Definition of depreciation ❌
          Chunk 189 (750 chars) - Second half of policy ❌

  User has to manually piece together → Time wasted, errors introduced

Desired System:
  Query: "depreciation accounting policy template"
  Result: Complete policy template (1800 chars) from Appendix 2 ✅
          Section reference: "Appendix 2, page 87" ✅
          Content type: Template (ready to copy-paste) ✅
```

---

## Solution Architecture

### Phase 1: Semantic Chunking (Week 1-2)

**Objective:** Replace fixed-size chunking with section-aware semantic chunking.

**Implementation:**

```python
SemanticChunker:
  - Min chunk size: 300 chars (skip noise)
  - Max chunk size: 5000 chars (keep templates intact)
  - Target chunk size: 1500 chars (optimal for most content)
  - Overlap: 200 chars (paragraph-based, not fixed)

  Features:
  ✓ Extract section hierarchy (Section 17.1 > PPE > Disclosures)
  ✓ Detect semantic units (tables, lists, numbered requirements)
  ✓ Classify content type (template, requirement, example, definition)
  ✓ Preserve parent-child relationships
  ✓ Extract section numbers for citations
```

**Success Metrics:**

| Metric | Current | Target |
|--------|---------|--------|
| Avg chunk size | 1053 chars | 1500 chars |
| Min chunk size | 13 chars | 300 chars |
| Chunks with section context | 0% | >80% |
| Chunks with content type | 0% | 100% |

### Phase 2: Enhanced Metadata (Week 2)

**Objective:** Enrich chunks with retrieval-optimized metadata.

**New Metadata Fields:**

```python
chunk_metadata = {
    # Section context
    "section_number": "17.1",
    "section_title": "Property, Plant and Equipment",
    "parent_section": "Section 17",
    "heading_level": 2,

    # Content classification
    "content_type": "requirement",  # vs template/example/definition
    "is_mandatory": True,
    "has_exemptions": False,

    # Retrieval hints
    "disclosure_category": "tangible_assets",
    "keywords": ["depreciation", "useful life", "carrying amount"],
    "cross_references": ["Section 13", "Appendix 2"],
}
```

**Database Migration:**

```sql
-- Add new columns to kb_chunks table
ALTER TABLE kb_chunks
  ADD COLUMN section_number VARCHAR(20),
  ADD COLUMN section_title TEXT,
  ADD COLUMN parent_section TEXT,
  ADD COLUMN is_mandatory BOOLEAN DEFAULT FALSE;

-- Add index for section-based filtering
CREATE INDEX idx_kb_chunks_section ON kb_chunks(section_number, jurisdiction);
```

### Phase 3: Multi-Stage Retrieval (Week 3)

**Objective:** Implement intent-aware retrieval pipeline.

**Retrieval Pipeline:**

```
Stage 1: Query Intent Detection
  Input: "Give me revenue policy template"
  Output: intent="template", category="revenue"

Stage 2: Semantic Search (Vector Similarity)
  Top 20 candidates by embedding similarity

Stage 3: Re-Ranking by Intent
  Boost template chunks +0.3
  Boost requirement chunks +0.1
  Penalize definition chunks -0.1

Stage 4: Chunk Merging
  If top results from same section, merge them
  Return COMPLETE section, not fragments

Stage 5: Format for Accountant
  Extract: section_reference, content_type, is_mandatory
  Add: cross-references, related examples
```

**Intent Detection:**

```python
def detect_intent(query: str) -> str:
    if "template" in query or "wording" in query:
        return "template"
    elif "required" in query or "disclosure" in query:
        return "requirement"
    elif "example" in query or "illustrative" in query:
        return "example"
    else:
        return "general"
```

### Phase 4: Evaluation Framework (Week 3)

**Objective:** Measure retrieval quality objectively using gold-standard accountant queries.

**Test Suite:**

- 10+ real-world accountant queries
- Expected results defined (section, content type, keywords)
- Metrics: relevance, completeness, fragmentation

**Metrics:**

```python
@dataclass
class RetrievalMetrics:
    top1_similarity: float
    top1_has_all_keywords: bool
    top1_correct_section: bool
    is_fragmented: bool
    mrr: float  # Mean Reciprocal Rank
    ndcg_at_5: float  # Normalized Discounted Cumulative Gain
    passed: bool
```

**Success Criteria:**

| Metric | Current (Baseline) | Target |
|--------|-------------------|--------|
| Pass rate (10 test queries) | TBD | >80% |
| Avg similarity score | TBD | >0.75 |
| Fragmentation rate | TBD | <10% |
| MRR (Mean Reciprocal Rank) | TBD | >0.85 |

---

## Implementation Plan

### Week 1: Foundation

**Tasks:**

1. ✅ Create `semantic_chunker.py` with section-aware logic
2. ✅ Create `test_accountant_queries.py` with gold-standard test suite
3. ✅ Create evaluation notebook `02_semantic_chunking_evaluation.ipynb`
4. Run baseline evaluation with current system
5. Document baseline metrics

**Deliverables:**

- Baseline metrics report
- Semantic chunker implementation
- Test framework ready

### Week 2: Implementation

**Tasks:**

1. Run semantic chunking on full SME-FRS document
2. Create database migration for new metadata fields
3. Ingest chunks with enhanced metadata
4. Implement intent detection module
5. Implement re-ranking logic

**Deliverables:**

- Full SME-FRS ingested with semantic chunks
- Enhanced KBRetriever with intent-aware retrieval
- Updated API endpoints to expose section metadata

### Week 3: Evaluation & Tuning

**Tasks:**

1. Run evaluation suite against new system
2. Compare metrics: old vs new
3. Tune parameters:
   - Chunk size thresholds
   - Re-ranking boost values
   - Intent detection rules
4. Document improvements
5. A/B test with sample users (if available)

**Deliverables:**

- Evaluation report with before/after comparison
- Tuned parameters documented
- Decision: deploy or iterate

---

## Measurement Methodology

### Automated Testing

```bash
# Run evaluation suite
pytest tests/retrieval/test_accountant_queries.py -v

# Output:
# ✅ PASS: 8/10 queries (80%)
# ❌ FAIL: 2/10 queries
#   - "inventory disclosure requirements" (fragmented)
#   - "lease accounting example" (wrong content type)
```

### Manual Quality Review

**Sample 20 random chunks:**

- Verify content type classification accuracy
- Check section number extraction
- Validate parent-child relationships

**Test with real accountants (if available):**

- Give 5 common tasks
- Measure: time to find answer, satisfaction score
- Compare old vs new system

### Regression Testing

**Ensure we don't break existing functionality:**

- All existing tests still pass
- No performance degradation (query time < 200ms)
- No security regressions (tenant isolation intact)

---

## Risks & Mitigation

### Risk 1: Semantic Chunking Creates TOO LARGE Chunks

**Impact:** Large chunks (>5000 chars) may dilute embedding quality

**Mitigation:**
- Set hard max at 5000 chars
- Split large sections at paragraph boundaries
- Use hierarchical chunking (parent chunk + child chunks)

### Risk 2: Content Type Classification Inaccurate

**Impact:** Wrong chunks boosted, poor results

**Mitigation:**
- Use LLM-based classification during ingestion (expensive but accurate)
- Manual review of sample classifications
- Allow manual override in admin interface

### Risk 3: Performance Degradation

**Impact:** Multi-stage retrieval slower than simple vector search

**Mitigation:**
- Benchmark each stage (<50ms target)
- Cache intent detection results
- Use database indexes for metadata filtering
- Consider async processing for non-critical stages

### Risk 4: Backward Compatibility

**Impact:** Existing chunks need migration

**Mitigation:**
- Run both systems in parallel during transition
- Gradual migration (document by document)
- Keep old chunks as fallback

---

## Success Criteria (Definition of Done)

**Phase 1-2 Complete When:**

- ✅ Semantic chunker generates 80%+ chunks with section context
- ✅ Database migration complete, no data loss
- ✅ Full SME-FRS document ingested with new strategy
- ✅ All existing tests pass

**Phase 3-4 Complete When:**

- ✅ Evaluation suite shows 80%+ pass rate (vs baseline)
- ✅ Avg similarity score improves by >0.10
- ✅ Fragmentation rate reduces by >50%
- ✅ Query time remains <200ms (no performance regression)
- ✅ Manual review confirms classification accuracy >90%

**Production Ready When:**

- ✅ A/B test shows user preference for new system
- ✅ Documentation updated (API docs, user guide)
- ✅ Rollback plan tested and verified
- ✅ Monitoring and alerting configured

---

## Next Steps

1. **Run baseline evaluation** (notebook 02)
2. **Review results** with team
3. **Decide on go/no-go** for semantic chunking
4. If go: **Execute Week 1 tasks**
5. **Weekly checkpoint meetings** to review metrics

---

## Appendix A: Example Test Queries

See `tests/retrieval/test_accountant_queries.py` for full list.

**Sample queries:**

1. "revenue recognition accounting policy wording for SME-FRS"
   - Expected: Template from Appendix 2, complete, ready to copy-paste

2. "what disclosures are required for property plant and equipment"
   - Expected: Section 17 requirements list, all mandatory items

3. "example of statement of changes in equity format"
   - Expected: Illustrative table from Appendix 2, complete

4. "is segment reporting required under SME-FRS"
   - Expected: Section 1 scope, exemption confirmed, brief answer

---

## Appendix B: Monitoring Plan

**Key Metrics to Track in Production:**

```python
# Query performance
query_latency_ms: histogram
queries_per_minute: counter
failed_queries: counter

# Quality metrics
avg_similarity_score: gauge
fragmentation_rate: gauge
user_satisfaction_score: gauge (from feedback)

# Content metrics
chunks_by_content_type: counter
chunks_by_section: counter
missing_metadata_chunks: counter
```

**Alerts:**

- Query latency >500ms (P2)
- Failed queries >5% (P1)
- Avg similarity <0.60 (P2)
- Fragmentation >20% (P3)

---

## Related Documentation

- **Structure-Aware Retrieval**: `2025-10-22-structure-aware-retrieval.md` - Detailed design for leveraging document TOC for navigation
- **RAG Orchestrator**: `2025-10-23-rag-orchestrator-design.md` - Coordination layer implementing multi-strategy retrieval
- **Agentic RAG**: `2025-10-23-agentic-rag-react-design.md` - Autonomous ReAct agent using RAG orchestrator

## Document History

| Date | Version | Changes |
|------|---------|---------|
| 2025-10-22 | 1.0 | Initial plan created |
| 2025-10-24 | 1.1 | Added cross-references to related architecture docs |
