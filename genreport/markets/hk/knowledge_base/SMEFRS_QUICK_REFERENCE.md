# SME-FRS Quick Reference Card

## Document Structure at a Glance

### Core Sections (Most Frequently Used)

| Section | Title | Common Queries |
|---------|-------|----------------|
| 1 | Presentation of Financial Statements | "financial statement presentation", "balance sheet format" |
| 3 | Property, Plant and Equipment | "ppe depreciation", "fixed assets", "revaluation" |
| 5 | Leases | "lease accounting", "right-of-use assets" |
| 7 | Inventories | "inventory valuation", "nrv", "stock costing" |
| 9 | Impairment | "impairment testing", "recoverable amount" |
| 10 | Provisions | "warranty provisions", "contingent liabilities" |
| 11 | Revenue | "revenue recognition", "sale of goods" |
| 14 | Income Taxes | "deferred tax", "tax expense" |
| 16 | Related Parties | "related party transactions", "directors compensation" |
| 19 | Consolidation | "consolidated statements", "subsidiary accounting" |

### Appendices (Templates & Examples)

| Appendix | Title | When to Use |
|----------|-------|-------------|
| 1 | Examples | Need practical illustrations |
| 2 | Company-Level Statements | Need disclosure templates |
| 3 | Consolidated Statements | Need group consolidation templates |

## Navigation Shortcuts

### Common Query Patterns

```python
# "Show me revenue recognition policy wording"
get_navigation_path("revenue policy", intent="template")
→ ["appendix_2", "section_11"]

# "Example of impairment calculation"
get_navigation_path("impairment", intent="example")
→ ["section_9", "appendix_1"]

# "What are the lease accounting rules?"
get_navigation_path("lease", intent="requirement")
→ ["section_5", "section_3"]

# "Everything about inventories"
get_navigation_path("inventory", intent="general")
→ ["section_7", "section_9", "appendix_2"]
```

## Section Relationships Cheat Sheet

### PPE (Section 3)
- **Impairment testing** → Section 9
- **Borrowing costs** → Section 13
- **Depreciation policy** → Appendix 2

### Revenue (Section 11)
- **Construction contracts** → Section 8
- **Practical examples** → Appendix 1
- **Disclosure template** → Appendix 2

### Leases (Section 5)
- **Right-of-use as PPE** → Section 3
- **Lease disclosures** → Appendix 2

### Consolidation (Section 19)
- **Business combinations** → Section 18
- **Associates** → Section 20
- **Joint ventures** → Section 21
- **Group statements** → Appendix 3

### Impairment (Section 9)
- **PPE impairment** → Section 3
- **Intangibles impairment** → Section 4
- **Inventory NRV** → Section 7
- **Allocation example** → Appendix 1

## Topic → Section Quick Map

### A-F
- **Accounting policies** → Section 2
- **Associates** → Section 20
- **Borrowing costs** → Section 13
- **Business combinations** → Section 18
- **Cash flow** → Section 22
- **Consolidation** → Section 19
- **Construction** → Section 8
- **Contingent liabilities** → Section 10
- **Depreciation** → Section 3
- **Disclosure templates** → Appendix 2
- **Examples** → Appendix 1
- **Foreign exchange** → Section 15

### G-P
- **Goodwill** → Section 18
- **Government grants** → Section 12
- **Impairment** → Section 9
- **Income tax** → Section 14
- **Intangibles** → Section 4
- **Inventories** → Section 7
- **Investments** → Section 6
- **Joint ventures** → Section 21
- **Leases** → Section 5
- **PPE** → Section 3
- **Presentation** → Section 1
- **Provisions** → Section 10

### R-Z
- **Related parties** → Section 16
- **Revenue** → Section 11
- **Subsequent events** → Section 17
- **Tax** → Section 14

## Intent Detection Keywords

### Template Intent
Keywords: "template", "wording", "disclosure", "policy text", "sample", "format"
→ Start with Appendix 2 or 3

### Example Intent
Keywords: "example", "illustration", "practical", "case", "scenario"
→ Start with Appendix 1

### Requirement Intent
Keywords: "requirement", "rule", "must", "shall", "criteria", "condition"
→ Stay in main sections

### General Intent
Keywords: "explain", "what is", "how to", "understand", "comprehensive"
→ Full navigation path

## File Locations

```
Structure Definition:
  genreport/markets/hk/knowledge_base/smefrs_structure.py

Usage:
  from genreport.markets.hk.knowledge_base.smefrs_structure import (
      get_section,
      get_sections_by_topic,
      get_navigation_path,
  )
```

## Quick Tests

```bash
# Test the structure
python genreport/markets/hk/knowledge_base/smefrs_structure.py

# View parsed structure
cat notebooks/smefrs_structure.json

# Read comprehensive guide
cat docs/guides/2025-10-23-smefrs-document-structure.md
```

---

**Last Updated:** 2025-10-23
**Document Version:** SME-FRF & SME-FRS (March 2025)
