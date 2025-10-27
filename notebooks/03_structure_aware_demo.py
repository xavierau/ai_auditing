"""
Demo: Structure-Aware Retrieval vs Pure Semantic Search

This script demonstrates how structure-aware retrieval mimics human navigation.
"""

# Example: How a human accountant would find "revenue policy template"

print("="*80)
print("DEMO: Human vs Machine Document Navigation")
print("="*80)

# Example Document Structure (simplified SME-FRS)
document_structure = {
    "section_1": {
        "title": "Scope",
        "type": "framework",
        "page_range": (12, 14),
        "topics": ["scope", "entity", "qualifying"],
    },
    "section_17": {
        "title": "Property, Plant and Equipment",
        "type": "requirement",
        "page_range": (45, 52),
        "topics": ["property", "plant", "equipment", "depreciation"],
        "related": ["appendix_2"],  # Has PPE template
    },
    "section_23": {
        "title": "Revenue",
        "type": "requirement",
        "page_range": (58, 65),
        "topics": ["revenue", "recognition", "contract"],
        "related": ["appendix_2", "section_11"],  # Has revenue template, relates to FI
    },
    "appendix_2": {
        "title": "Illustrative Financial Statements",
        "type": "template",
        "page_range": (87, 120),
        "topics": ["policy", "template", "disclosure", "example"],
        "content_includes": ["revenue_policy", "ppe_policy", "inventory_policy"],
    },
}

print("\n📚 Document Structure (Mental Map):")
for section_id, section in document_structure.items():
    print(f"  {section_id}: {section['title']} (pages {section['page_range'][0]}-{section['page_range'][1]})")
    print(f"    Type: {section['type']}")
    print(f"    Topics: {', '.join(section['topics'])}")
    if 'related' in section:
        print(f"    Related: {', '.join(section['related'])}")

print("\n" + "="*80)
print("SCENARIO: User needs 'revenue recognition accounting policy wording'")
print("="*80)

# Method 1: Pure Semantic Search
print("\n🤖 METHOD 1: Pure Semantic Search (Current System)")
print("-"*80)

pure_semantic_results = [
    {"chunk_id": 234, "content": "Section 23.1 Revenue recognition requirements...", "similarity": 0.82, "page": 58},
    {"chunk_id": 235, "content": "Section 23.2 An entity shall recognize revenue...", "similarity": 0.79, "page": 59},
    {"chunk_id": 189, "content": "Revenue Policy Template: Revenue is measured at...", "similarity": 0.74, "page": 92},
    {"chunk_id": 112, "content": "Section 11.3 Financial instruments revenue...", "similarity": 0.71, "page": 38},
    {"chunk_id": 53, "content": "Table of Contents: Revenue... 58", "similarity": 0.68, "page": 5},
]

print("\nTop 5 Results (by similarity only):")
for i, result in enumerate(pure_semantic_results, 1):
    print(f"\n{i}. Chunk #{result['chunk_id']} (similarity: {result['similarity']:.2f})")
    print(f"   Page: {result['page']}")
    print(f"   Content: {result['content'][:80]}...")

print("\n⚠️  Problem:")
print("   - Top result is REQUIREMENT (Section 23.1), not TEMPLATE")
print("   - Actual template (Appendix 2) is #3 with lower similarity")
print("   - User has to manually scan results to find template")

# Method 2: Structure-Aware Search (Proposed)
print("\n\n✨ METHOD 2: Structure-Aware Search (Proposed)")
print("-"*80)

print("\nStep 1: Understand Query")
print("  Intent detected: 'template' (keywords: 'policy wording')")
print("  Topic detected: 'revenue'")

print("\nStep 2: Consult Document Structure")
print("  Topic 'revenue' → Section 23")
print("  Section 23 relates to: Appendix 2 (templates)")

print("\nStep 3: Build Navigation Path")
navigation_path = ["appendix_2", "section_23", "section_11"]
print(f"  Priority order: {' > '.join(navigation_path)}")
print("  Reasoning:")
print("    1. Appendix 2: Intent is 'template', prioritize template sections")
print("    2. Section 23: Main revenue section (fallback)")
print("    3. Section 11: Related section (secondary)")

print("\nStep 4: Search Within Prioritized Sections")
structure_aware_results = [
    {"chunk_id": 189, "content": "Revenue Policy Template: Revenue is measured at...",
     "similarity": 0.74, "boost": 0.3, "final_score": 1.04, "page": 92, "section": "appendix_2"},
    {"chunk_id": 190, "content": "...fair value of consideration received or receivable...",
     "similarity": 0.71, "boost": 0.3, "final_score": 1.01, "page": 92, "section": "appendix_2"},
    {"chunk_id": 234, "content": "Section 23.1 Revenue recognition requirements...",
     "similarity": 0.82, "boost": -0.1, "final_score": 0.72, "page": 58, "section": "section_23"},
    {"chunk_id": 235, "content": "Section 23.2 An entity shall recognize revenue...",
     "similarity": 0.79, "boost": -0.1, "final_score": 0.69, "page": 59, "section": "section_23"},
]

print("\nTop Results (after structural boosting):")
for i, result in enumerate(structure_aware_results, 1):
    print(f"\n{i}. Chunk #{result['chunk_id']} (final score: {result['final_score']:.2f})")
    print(f"   Page: {result['page']} | Section: {result['section']}")
    print(f"   Similarity: {result['similarity']:.2f} + Boost: {result['boost']:+.2f}")
    print(f"   Content: {result['content'][:80]}...")

print("\nStep 5: Merge Adjacent Chunks (from same section)")
print("  Chunks #189 and #190 are adjacent in Appendix 2")
print("  → Merged into single complete template")

print("\n✅ Result:")
print("   - Top result is TEMPLATE from Appendix 2 (correct!)")
print("   - Complete policy text (merged chunks)")
print("   - User gets exactly what they need immediately")

# Comparison
print("\n\n" + "="*80)
print("COMPARISON: Pure Semantic vs Structure-Aware")
print("="*80)

comparison = """
┌────────────────────────┬────────────────────────┬──────────────────────────┐
│ Aspect                 │ Pure Semantic          │ Structure-Aware          │
├────────────────────────┼────────────────────────┼──────────────────────────┤
│ Top result             │ Requirement (wrong)    │ Template (correct) ✅    │
│ Template rank          │ #3 (low priority)      │ #1 (high priority)       │
│ User effort            │ Scan & piece together  │ Immediate answer         │
│ Explainability         │ "High similarity"      │ "Searched Appendix 2"    │
│ Context awareness      │ None                   │ Knows section types      │
│ Cross-reference        │ No                     │ Yes (Sec 23 → App 2)     │
└────────────────────────┴────────────────────────┴──────────────────────────┘
"""
print(comparison)

print("\n💡 Key Insight:")
print("   Humans don't rely on similarity alone - they use STRUCTURE + SEMANTICS")
print("   Structure-aware search mimics this by combining:")
print("     1. Document organization (from TOC)")
print("     2. Query intent (template vs requirement)")
print("     3. Semantic similarity (embedding matching)")

print("\n" + "="*80)
print("END DEMO")
print("="*80)
