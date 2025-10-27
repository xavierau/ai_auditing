# Structure-Aware Retrieval - Proposal Summary

**Date:** 2025-10-22
**Status:** Design Proposal
**Priority:** HIGH
**Next Step:** Validate concept with TOC extraction

---

## TL;DR

**Your Insight:** "Like humans use table of contents to build mental maps, can we give the system 'intelligence' about document structure?"

**Answer:** **YES!** Implement structure-aware retrieval that mimics human navigation.

**Expected Impact:**
- Template query accuracy: 0% → **80%+**
- Pass rate: 20% → **60%+**
- User can cite sections: **YES**
- Explainable results: **"Searched Appendix 2, Section 17"**

---

## The Problem We're Solving

### How Humans Actually Work

```
Human accountant looking for "revenue policy template":

Mental Process:
1. "Revenue is Section 23" (from memory/TOC)
2. "Section 23 has REQUIREMENTS, not templates"  ← Nuance!
3. "Templates are in Appendix 2" (from experience)
4. Navigate: Appendix 2 > Revenue Policy
5. Find complete template immediately

Key: Humans use STRUCTURE + SEMANTIC UNDERSTANDING together
```

### Current System (Pure Semantic Search)

```
Query: "revenue policy template"
  ↓
Embedding similarity → Top 5 chunks
  ↓
Result #1: Section 23.1 (requirement) ❌ WRONG TYPE
Result #2: Section 23.2 (requirement) ❌ WRONG TYPE
Result #3: Appendix 2 (template) ✅ CORRECT but ranked #3

Problem: No structure awareness, returns wrong content type
```

---

## Proposed Solution

### Three-Layer Architecture

**Layer 1: Document Structure Intelligence**
```python
# Build from table of contents (one-time)
structure = {
    "section_23": {
        "title": "Revenue",
        "type": "requirement",
        "page_range": (58, 65),
        "topics": ["revenue", "recognition"],
        "related": ["appendix_2"]  # ← Cross-reference!
    },
    "appendix_2": {
        "title": "Illustrative Financial Statements",
        "type": "template",  # ← Content type!
        "page_range": (87, 120),
        "topics": ["policy", "template"],
    }
}
```

**Layer 2: Query Understanding & Navigation**
```python
Query: "revenue policy template"
  ↓
Intent: "template" (from keywords "policy template")
Topic: "revenue"
  ↓
Navigate: Topic="revenue" → Section 23
          Section 23 relates to → Appendix 2 (templates)
  ↓
Priority: [Appendix 2 (1st), Section 23 (2nd)]
```

**Layer 3: Hybrid Retrieval**
```python
# Search within prioritized sections
results = search_sections(["appendix_2", "section_23"], query)

# Boost by intent
for result in results:
    if result.section == "appendix_2" and intent == "template":
        result.score += 0.3  # Boost template chunks

# Merge adjacent chunks from same section
merge_if_same_section(results)

# Return top results
```

---

## Demo Results

### Pure Semantic Search (Current)

```
Top Results:
1. Section 23.1 (similarity: 0.82) ← Requirement, NOT template
2. Section 23.2 (similarity: 0.79) ← Requirement, NOT template
3. Appendix 2 template (similarity: 0.74) ← CORRECT but low rank

User must: Scan results, identify template manually
```

### Structure-Aware Search (Proposed)

```
Navigation: "revenue" + "template" intent → Appendix 2 (priority 1)

Top Results (after boosting):
1. Appendix 2 template (0.74 + 0.3 = 1.04) ← CORRECT, top rank!
2. Appendix 2 template continued (1.01) ← Adjacent, merged
3. Section 23.1 (0.82 - 0.1 = 0.72) ← Requirements (de-boosted)

User gets: Complete template immediately
```

**Improvement:** Template moves from rank #3 to #1! ✅

---

## Implementation Plan

### Phase 1: TOC Extraction & Structure Building (1 week)

**Tasks:**
1. Extract table of contents from SME-FRS PDF
   - Manual extraction or automated (marker-pdf can detect TOC)
   - Format: Section number | Title | Page number

2. Build document structure using LLM
   - Classify section types (requirement, template, example, definition)
   - Extract topics from titles
   - Identify relationships (Section → Appendix)

3. Save structure to JSON
   - Cache for fast loading
   - Version control for updates

**Deliverable:** `smefrs_structure.json`

```json
{
  "section_23": {
    "section_number": "23",
    "title": "Revenue",
    "section_type": "requirement",
    "page_start": 58,
    "page_end": 65,
    "topics": ["revenue", "recognition", "contract"],
    "related_sections": ["appendix_2", "section_11"]
  },
  "appendix_2": {
    "section_number": "Appendix 2",
    "title": "Illustrative Financial Statements",
    "section_type": "template",
    "page_start": 87,
    "page_end": 120,
    "topics": ["policy", "template", "disclosure"]
  }
}
```

### Phase 2: Implementation (1 week)

**Tasks:**
1. Implement StructureAwareRetriever
2. Add navigation logic (prioritize sections by intent)
3. Add boosting (template chunks +0.3 for template queries)
4. Add chunk merging (combine adjacent fragments)
5. Integrate with existing KBRetriever

**Code created:**
- ✅ `genreport/core/retrieval/document_structure_analyzer.py`
- ✅ `genreport/core/retrieval/structure_aware_retriever.py`

### Phase 3: Evaluation (1 week)

**Tasks:**
1. Re-run accountant test queries (10 queries)
2. Compare: pure semantic vs structure-aware
3. Measure: pass rate, template accuracy, fragmentation
4. Tune boost values and navigation logic

**Target Metrics:**

| Metric | Current | Target |
|--------|---------|--------|
| Overall pass rate | 20% | >60% |
| Template query accuracy | 0% | >80% |
| Fragmentation rate | 40% | <15% |
| Can cite sections | NO | YES |

---

## Benefits

### 1. Accuracy

**Template Queries:**
- Current: Returns requirements (wrong type)
- Structure-aware: Returns templates (correct type) ✅

### 2. Completeness

**Fragmentation:**
- Current: Chunks split randomly
- Structure-aware: Merges adjacent chunks from same section ✅

### 3. Explainability

**Transparency:**
- Current: "Here are top 5 by similarity" (black box)
- Structure-aware: "Searched Appendix 2 (templates), Section 17 (requirements)" ✅

### 4. User Experience

**Workflow:**
- Current: User scans results, pieces together fragments
- Structure-aware: User gets complete answer immediately ✅

---

## Files Created

### Implementation

1. `genreport/core/retrieval/document_structure_analyzer.py`
   - Builds document structure from TOC
   - Classifies section types with LLM
   - Identifies cross-references
   - Navigation path generation

2. `genreport/core/retrieval/structure_aware_retriever.py`
   - Hybrid retrieval (structure + semantics)
   - Intent-based boosting
   - Chunk merging
   - Explainable results

### Documentation

3. `docs/architecture/2025-10-22-structure-aware-retrieval.md`
   - Complete architecture design
   - Implementation details
   - Examples and comparisons

4. `docs/reports/2025-10-22-structure-aware-retrieval-proposal.md`
   - This summary document

5. `notebooks/03_structure_aware_demo.py`
   - Executable demo showing concept
   - Side-by-side comparison

---

## Risks & Mitigation

### Risk 1: TOC Extraction Errors

**Impact:** Wrong structure → wrong navigation

**Mitigation:**
- Manual review of extracted structure
- LLM validation of relationships
- Fallback to pure semantic if structure fails

### Risk 2: Performance Overhead

**Impact:** Structure lookup adds latency

**Mitigation:**
- Cache structure in memory (~100KB JSON)
- Target: <100ms overhead
- Benchmark and optimize

### Risk 3: Documents Without TOC

**Impact:** Some documents may not have clear TOC

**Mitigation:**
- Auto-detect TOC presence
- Generate pseudo-TOC from headings
- Graceful fallback to pure semantic

---

## Next Steps

### Immediate (This Week)

1. ✅ Design completed (structure-aware architecture)
2. ✅ Implementation code written
3. ✅ Demo created
4. **TODO:** Extract TOC from SME-FRS PDF
5. **TODO:** Build structure index (run analyzer)

### Week 1

1. Extract full document TOC
2. Build and validate structure JSON
3. Manual review of section relationships
4. Test navigation logic with sample queries

### Week 2

1. Integrate StructureAwareRetriever
2. Update evaluation notebook
3. Re-run tests with structure awareness enabled
4. Compare results

### Week 3

1. Tune boost values and navigation
2. Final evaluation and recommendation
3. Go/no-go decision for production

---

## Decision Points

### Go/No-Go Criteria

**Proceed to implementation if:**
- ✅ TOC extraction accuracy >90%
- ✅ Section classification accuracy >85%
- ✅ Concept demo shows promise (done!)

**Proceed to production if:**
- ✅ Pass rate improves >30% vs baseline
- ✅ Template query accuracy >70%
- ✅ No performance regression (query time <300ms)
- ✅ User testing shows preference

---

## Conclusion

Your insight about mimicking human TOC-based navigation is **excellent** and **implementable**.

**Key Innovation:** Combining **document structure** (from TOC) + **semantic search** (embeddings) + **intent understanding** (template vs requirement).

**Recommendation:** **Proceed** with Phase 1 (TOC extraction) to validate the approach.

**Expected Outcome:** Significant improvement in retrieval accuracy, especially for template and requirement queries where content type matters.

---

## References

- Architecture doc: `docs/architecture/2025-10-22-structure-aware-retrieval.md`
- Demo script: `notebooks/03_structure_aware_demo.py`
- Implementation: `genreport/core/retrieval/document_structure_analyzer.py`
- Related: `docs/architecture/2025-10-22-retrieval-optimization-plan.md`
