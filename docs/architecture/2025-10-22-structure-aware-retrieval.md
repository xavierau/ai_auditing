# Structure-Aware Retrieval Architecture

**Date:** 2025-10-22
**Status:** Design Proposal
**Related:** `2025-10-22-retrieval-optimization-plan.md`

---

## Executive Summary

**Problem:** Current semantic search doesn't leverage document structure, missing how humans actually navigate documents.

**Solution:** Build **document "intelligence"** from table of contents, mimicking human mental maps for navigation.

**Impact:** More accurate retrieval by combining structure knowledge + semantic search.

---

## The Human Navigation Model

### How Accountants Actually Use Documents

**Example: Looking for Revenue Policy Template**

```
Human Process:
1. Recall mental map: "Revenue is Section 23"
2. Know nuance: "Section 23 has REQUIREMENTS, not templates"
3. Navigate: "Templates are in Appendix 2"
4. Cross-reference: "Appendix 2 > Revenue Policy"
5. Find exact text needed

Key Insights:
- Humans use STRUCTURE + SEMANTICS together
- Table of contents creates "mental map"
- Humans understand relationships (Section → Appendix)
- Humans know content types (requirement vs template)
```

**Current System (Pure Semantic Search):**
```
Query: "revenue policy template"
  ↓
Embedding similarity → Top 5 chunks
  ↓
Result: Fragments from Section 23 (requirements)
        Missing: Appendix 2 (actual template)

Problem: No structural awareness!
```

**Proposed System (Structure-Aware):**
```
Query: "revenue policy template"
  ↓
1. Intent: "template"
2. Topic: "revenue"
3. Structure lookup: "revenue" → Section 23
4. Related sections: Section 23 → Appendix 2 (templates)
5. Navigate: Appendix 2 (priority 1), Section 23 (priority 2)
6. Semantic search: Within those sections
  ↓
Result: Appendix 2 revenue template (complete)
```

---

## Architecture Overview

### Three-Layer System

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Document Structure Intelligence                   │
│                                                             │
│  TOC Extraction → Section Classification → Relationship    │
│                    │                         │              │
│                    ├─ Requirement            │              │
│                    ├─ Template               │              │
│                    ├─ Example                ├─ Section 23  │
│                    ├─ Definition             │  relates to  │
│                    └─ Appendix               │  Appendix 2  │
│                                              │              │
│  Output: Document "Mental Map"                             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Query Understanding & Navigation                  │
│                                                             │
│  Query → Intent Detection → Structure Mapping              │
│           │                  │                              │
│           ├─ template        ├─ Navigate to appendices     │
│           ├─ requirement     ├─ Navigate to main sections  │
│           └─ example         └─ Navigate to examples       │
│                                                             │
│  Output: Prioritized Section List                          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Hybrid Retrieval                                  │
│                                                             │
│  Structural Filter → Semantic Search → Re-Rank → Merge     │
│       │                   │               │        │        │
│       │                   │               │        │        │
│  Pages 87-95          Embedding       Boost by   Combine   │
│  (Appendix 2)         Similarity      Intent     Fragments │
│                                                             │
│  Output: Complete, Relevant Answer                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Document Structure Analyzer

**Purpose:** Build hierarchical "intelligence" from table of contents

**Input:** Table of contents (Markdown or extracted from PDF)

**Process:**
```python
# Example TOC input:
toc = """
| Section 17 | Property, Plant and Equipment | 45 |
| Section 23 | Revenue                        | 58 |
| Appendix 2 | Illustrative Financial Statements | 87 |
"""

# Build structure:
analyzer = DocumentStructureAnalyzer()
structure = analyzer.build_document_structure(toc, "HK SME-FRS")

# Output:
{
  "section_17": DocumentSection(
    section_number="17",
    title="Property, Plant and Equipment",
    section_type=SectionType.REQUIREMENT,
    page_start=45,
    topics=["property", "plant", "equipment", "depreciation"],
    related_sections=["appendix_2"]  # Has PPE template
  ),
  "section_23": DocumentSection(
    section_number="23",
    title="Revenue",
    section_type=SectionType.REQUIREMENT,
    page_start=58,
    topics=["revenue", "recognition"],
    related_sections=["appendix_2", "section_11"]
  ),
  "appendix_2": DocumentSection(
    section_number="Appendix 2",
    title="Illustrative Financial Statements",
    section_type=SectionType.TEMPLATE,
    page_start=87,
    topics=["policy", "template", "example"],
    has_templates=True
  )
}
```

**Key Features:**
- **LLM-powered classification:** Uses DSPy to classify section types
- **Relationship detection:** Identifies cross-references (Section → Appendix)
- **Topic extraction:** Extracts main topics from section titles
- **Caching:** Saves structure to JSON for fast loading

---

### 2. Structure-Aware Retriever

**Purpose:** Navigate document like a human would

**Query Flow:**

```python
# Example 1: Template query
retriever = StructureAwareRetriever(db, "HK", tenant_id, embedding_service, structure)

results = retriever.retrieve(
    query="revenue recognition accounting policy wording",
    intent="template",  # User wants a template
    top_k=5
)

# Internal process:
# 1. Intent="template" → Prioritize appendices
# 2. Topic="revenue" → Find Section 23
# 3. Navigate: Appendix 2 (priority 1), Section 23 (priority 2)
# 4. Semantic search within pages 87-95, 58-65
# 5. Boost template chunks +0.3
# 6. Merge adjacent chunks from same section
# 7. Return top 5

# Result: Complete revenue policy template from Appendix 2
```

**Navigation Strategy:**

| Intent | Priority Order | Boosting |
|--------|---------------|----------|
| template | 1. Related appendices<br>2. Main section<br>3. Examples | template +0.3<br>example +0.1 |
| requirement | 1. Main section<br>2. Related requirements | requirement +0.2 |
| example | 1. Example sections<br>2. Appendices<br>3. Main section | example +0.3<br>template +0.1 |
| general | Natural TOC order | No boosting |

---

## Implementation Example

### Step 1: Build Document Structure (One-Time Setup)

```python
# Extract TOC from PDF (notebook or script)
from genreport.core.retrieval.document_structure_analyzer import create_document_index

# Load TOC markdown (from notebook 01, extract TOC pages)
toc_markdown = """
| Section 1 | Scope                              | 12 |
| Section 2 | Accounting Policies                | 14 |
...
| Section 17 | Property, Plant and Equipment    | 45 |
| Section 23 | Revenue                          | 58 |
...
| Appendix 2 | Illustrative Financial Statements| 87 |
"""

# Create index
structure = create_document_index(
    toc_markdown,
    document_title="Hong Kong SME-FRS",
    output_path="genreport/markets/hk/knowledge_base/smefrs_structure.json"
)

# Result saved to JSON, load once at startup
```

### Step 2: Use Structure-Aware Retrieval

```python
from genreport.core.retrieval.structure_aware_retriever import StructureAwareRetriever
from genreport.core.retrieval.document_structure_analyzer import DocumentStructureAnalyzer

# Load structure (fast - from JSON cache)
structure = DocumentStructureAnalyzer.load_structure(
    "genreport/markets/hk/knowledge_base/smefrs_structure.json"
)

# Create retriever
retriever = StructureAwareRetriever(
    db=db,
    jurisdiction="HK",
    tenant_id=tenant_id,
    embedding_service=embedding_service,
    document_structure=structure
)

# Query with structure awareness
results = retriever.retrieve(
    query="depreciation accounting policy template",
    intent="template",
    top_k=5
)

# Explain retrieval strategy (for debugging)
explanation = retriever.explain_retrieval(
    query="depreciation accounting policy template",
    intent="template"
)

print(explanation)
# {
#   "query": "depreciation accounting policy template",
#   "intent": "template",
#   "navigation_path": ["appendix_2", "section_17"],
#   "sections_searched": [
#     {"section_id": "appendix_2", "title": "Illustrative Financial Statements", ...},
#     {"section_id": "section_17", "title": "Property, Plant and Equipment", ...}
#   ],
#   "strategy": "structure_aware",
#   "explanation": "Looking for template for 'depreciation accounting policy template'. Prioritizing appendices and examples in sections: Illustrative Financial Statements, Property Plant and Equipment"
# }
```

---

## Benefits vs Pure Semantic Search

### Comparison Table

| Aspect | Pure Semantic Search | Structure-Aware Search |
|--------|---------------------|----------------------|
| **Understanding** | Embedding similarity only | Structure + semantics |
| **Navigation** | No concept of sections | Follows TOC like human |
| **Content types** | All chunks equal | Templates boosted for template queries |
| **Relationships** | No cross-references | Knows Section 23 → Appendix 2 |
| **Fragmentation** | High (random chunks) | Low (section-aware merging) |
| **Explainability** | Black box | "Searched Appendix 2, Section 17" |
| **Performance** | Fast (single query) | Slightly slower (structure lookup) |

### Expected Improvement

**Test Query: "revenue recognition accounting policy wording for SME-FRS"**

**Pure Semantic Search:**
```
Top result: Section 23 fragment (requirement)
Similarity: 0.739
Has template: NO ❌
Actionable: NO ❌
```

**Structure-Aware Search:**
```
Navigation: "revenue" → Section 23 → Related: Appendix 2
Priority sections: [Appendix 2, Section 23]
Intent: "template" → Boost appendix chunks +0.3

Top result: Appendix 2 revenue policy template
Similarity: 0.72 + 0.3 boost = 1.02 (capped at 1.0)
Has template: YES ✅
Actionable: YES ✅ (complete copy-paste ready text)
```

---

## Implementation Timeline

### Phase 1: Structure Extraction (Week 1)

**Tasks:**
1. Extract TOC from SME-FRS PDF (manual or automated)
2. Test TOC parsing and section classification
3. Build structure index for HK SME-FRS
4. Validate relationships (manual review)

**Deliverable:** `smefrs_structure.json` with complete document map

### Phase 2: Structure-Aware Retrieval (Week 2)

**Tasks:**
1. Implement StructureAwareRetriever
2. Integrate with existing KBRetriever
3. Add navigation logic and boosting
4. Implement chunk merging

**Deliverable:** Working structure-aware retrieval

### Phase 3: Evaluation (Week 3)

**Tasks:**
1. Re-run accountant test queries
2. Compare: pure semantic vs structure-aware
3. Measure: pass rate, fragmentation, relevance
4. Tune boost values and navigation logic

**Deliverable:** Evaluation report with recommendation

---

## Success Metrics

**Target Improvements:**

| Metric | Current (Baseline) | Target (Structure-Aware) |
|--------|-------------------|-------------------------|
| Pass rate (10 queries) | 20% | >60% |
| Template query accuracy | 0% | >80% |
| Fragmentation rate | 40% | <15% |
| Avg similarity (after boost) | 0.745 | >0.80 |
| User can cite section | NO | YES |

---

## Risks & Mitigation

### Risk 1: TOC Extraction Errors

**Impact:** Wrong structure → wrong navigation

**Mitigation:**
- Manual review of extracted structure
- Validate section relationships with LLM
- Fallback to pure semantic if structure lookup fails

### Risk 2: Performance Overhead

**Impact:** Structure lookup + section filtering slower

**Mitigation:**
- Cache structure in memory (JSON is ~100KB)
- Index chunks by page_range for fast filtering
- Measure: target <100ms overhead

### Risk 3: Document Without Clear TOC

**Impact:** Some documents may not have TOC

**Mitigation:**
- Auto-detect TOC presence
- Fallback gracefully to pure semantic search
- Consider generating pseudo-TOC from headings

---

## Future Enhancements

### 1. Multi-Document Structure

Build structure across multiple related documents:
```
SME-FRS (main) → Cross-references → HKFRS 15 (detailed revenue)
                                  → Companies Ordinance (legal)
```

### 2. Learning from User Behavior

Track which sections users navigate to:
```
Query "revenue policy" → Users always go to Appendix 2
  ↓
Update structure: Boost Appendix 2 for "policy" queries
```

### 3. Visual Structure Explorer

UI to show navigation path:
```
Query: "depreciation policy"
  ↓
Navigation: Section 17 → Appendix 2
            [Visual tree diagram]
```

---

## References

- Implementation: `genreport/core/retrieval/document_structure_analyzer.py`
- Retriever: `genreport/core/retrieval/structure_aware_retriever.py`
- **Related Architecture Docs:**
  - `2025-10-22-retrieval-optimization-plan.md` - Overall retrieval optimization strategy
  - `2025-10-23-rag-orchestrator-design.md` - Multi-strategy retrieval orchestration layer
  - `2025-10-23-agentic-rag-react-design.md` - Autonomous ReAct agent implementation

---

## Document History

| Date | Version | Changes |
|------|---------|---------|
| 2025-10-22 | 1.0 | Initial design proposal |
| 2025-10-24 | 1.1 | Added cross-references to related architecture docs |

---

## Conclusion

Structure-aware retrieval mimics human document navigation by:
1. Building "mental map" from TOC
2. Understanding query intent
3. Navigating to relevant sections
4. Combining structure + semantics

**Recommendation:** Implement Phase 1 (structure extraction) and validate with small-scale testing before full deployment.
