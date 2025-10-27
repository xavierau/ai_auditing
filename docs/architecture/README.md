# GenReport Architecture Documentation

This directory contains the architectural design documents for the GenReport AI-powered audit report generation system.

**Last Updated:** 2025-10-24

---

## Quick Reference

### Active Architecture Documents

All documents are organized by topic and include cross-references for easy navigation.

#### 0. System Flow Overview (START HERE!)
**File:** `2025-10-26-system-flow-diagram.md`
- **Purpose:** Complete end-to-end system flow from Excel upload to DOCX download
- **Status:** ✅ Active - Current architecture with new trial balance modules
- **Key Topics:**
  - 6-phase processing pipeline (upload → parse → analyze → retrieve → generate → export)
  - NEW: Trial Balance Disclosure System (3 modules) integration
  - Module-level interaction diagrams
  - Data flow and timing characteristics
  - Before/after comparison (hardcoded vs. dynamic analysis)
- **When to Use:** MANDATORY starting point for understanding system architecture
- **Related:** All other architecture documents build upon this foundation

#### 1. Frontend Design System
**File:** `2025-10-18-genreport-design-system.md`
- **Purpose:** Complete design system specification for React frontend
- **Status:** ✅ Active - Currently in use
- **Key Topics:**
  - Color palette and jurisdiction-specific theming (HK=blue, SG=green, AU=amber)
  - Typography system (Inter + JetBrains Mono)
  - Spacing scale (4px base unit)
  - shadcn/ui component library integration
  - WCAG 2.1 AA accessibility compliance
- **When to Use:** MANDATORY reference before implementing ANY frontend component
- **Related:** Frontend implementation in `frontend/` directory

#### 2. Knowledge Base Retrieval Architecture

**2a. Retrieval Optimization Plan**
- **File:** `2025-10-22-retrieval-optimization-plan.md`
- **Purpose:** Overall strategy for optimizing knowledge base retrieval
- **Status:** ✅ Implemented
- **Key Topics:**
  - Semantic chunking (300-5000 chars, section-aware)
  - Enhanced metadata (section context, content types)
  - Multi-stage retrieval pipeline
  - Evaluation framework with accountant test queries
- **When to Use:** Understanding overall retrieval strategy and evaluation metrics

**2b. Structure-Aware Retrieval**
- **File:** `2025-10-22-structure-aware-retrieval.md`
- **Purpose:** Detailed design for leveraging document TOC for navigation
- **Status:** ✅ Implemented
- **Key Topics:**
  - Document structure intelligence from TOC
  - Human-like navigation patterns
  - Intent-based section prioritization (template/requirement/example)
  - Chunk merging to reduce fragmentation
- **When to Use:** Implementing or understanding structure-based document navigation
- **Implementation:** `genreport/core/retrieval/document_structure_analyzer.py`, `structure_aware_retriever.py`

#### 3. RAG System Architecture

**3a. RAG Orchestrator**
- **File:** `2025-10-23-rag-orchestrator-design.md`
- **Purpose:** Coordination layer for multi-strategy retrieval
- **Status:** ✅ Implemented
- **Key Topics:**
  - Query understanding and intent detection
  - Strategy selection (semantic, structure-aware, hybrid)
  - Multi-stage retrieval pipeline
  - Re-ranking and chunk merging
  - Caching with Redis (15-min TTL)
  - Observability and audit logging
- **When to Use:** Understanding the retrieval orchestration layer
- **Implementation:** `genreport/core/orchestration/rag_orchestrator.py`
- **Dependencies:** Requires structure-aware retriever, semantic chunking

**3b. Agentic RAG with DSPy ReAct**
- **File:** `2025-10-23-agentic-rag-react-design.md`
- **Purpose:** Autonomous ReAct agent for iterative reasoning and retrieval
- **Status:** ✅ Implemented
- **Key Topics:**
  - DSPy ReAct pattern (THINK→ACT→OBSERVE→DECIDE→SYNTHESIZE)
  - Tool-based design (search_knowledge_base, search_by_section)
  - Query rewriting and iterative refinement
  - Complete source traceability
  - BootstrapFewShot optimization
- **When to Use:** Implementing autonomous AI agents with reasoning capabilities
- **Implementation:** `genreport/core/orchestration/agentic_rag_agent.py`
- **Dependencies:** Requires RAG orchestrator
- **Demo:** See `notebooks/04_agentic_rag_demo.py`

---

## Document Relationships

```
Retrieval Foundation
├── 2025-10-22-retrieval-optimization-plan.md
│   └── Overall strategy and evaluation
│
├── 2025-10-22-structure-aware-retrieval.md
│   └── Document TOC-based navigation
│
└── RAG System
    ├── 2025-10-23-rag-orchestrator-design.md
    │   └── Multi-strategy orchestration layer
    │
    └── 2025-10-23-agentic-rag-react-design.md
        └── Autonomous ReAct agent (depends on orchestrator)

Frontend
└── 2025-10-18-genreport-design-system.md
    └── Complete design system specification
```

---

## Architecture Principles

All architecture documents follow these core principles:

### 1. Hybrid Architecture Pattern
- **Generic Core:** Market-agnostic code in `genreport/core/`
- **Market-Specific:** Jurisdiction-specific implementations in `genreport/markets/{hk,sg,au}/`
- **NO hardcoded jurisdictions** in core modules

### 2. Security-First Design
- Multi-tenant isolation (all tables have `tenant_id`)
- Encryption at rest with KMS-managed keys
- Comprehensive audit logging
- PII detection and redaction
- XSS/CSRF protection in frontend

### 3. Test-Driven Development
- >80% test coverage requirement
- Security tests for tenant isolation
- Integration tests for all API endpoints
- Performance benchmarks

### 4. Clean Architecture (SOLID Principles)
- Single Responsibility Principle
- Open/Closed Principle
- Dependency Injection
- Interface Segregation

---

## Reading Guide

### For New Developers
**Start here:**
1. `2025-10-18-genreport-design-system.md` - Understand UI/UX standards
2. `2025-10-22-retrieval-optimization-plan.md` - Grasp retrieval strategy
3. `2025-10-23-rag-orchestrator-design.md` - Learn system architecture

### For Frontend Developers
**MANDATORY reading:**
- `2025-10-18-genreport-design-system.md` - Design system (MUST follow exactly)

**Recommended:**
- Review `frontend/` directory for implementation examples
- Check CLAUDE.md for frontend verification protocol

### For Backend Developers
**Core retrieval system:**
1. `2025-10-22-retrieval-optimization-plan.md` - Strategy overview
2. `2025-10-22-structure-aware-retrieval.md` - Structure navigation
3. `2025-10-23-rag-orchestrator-design.md` - Orchestration layer

**AI agent development:**
- `2025-10-23-agentic-rag-react-design.md` - DSPy ReAct pattern
- `genreport/core/orchestration/base_agent.py` - Base agent class

### For Architecture Review
**All documents include:**
- Architecture Decision Records (ADRs)
- Success metrics and evaluation criteria
- Security considerations
- Performance targets
- Implementation status

---

## Document Versioning

All architecture documents use this versioning convention:
- **v1.0** - Initial design/proposal
- **v1.1+** - Updates, cross-references, implementation status

See **Document History** section at the end of each document for changelog.

---

## Contributing

When updating architecture documentation:

1. **Read existing docs first** - Check for related documents and cross-reference them
2. **Follow naming convention** - Use `YYYY-MM-DD-topic-description.md` format
3. **Add Document History** - Include version number and changes
4. **Cross-reference related docs** - Link to foundation and dependent architectures
5. **Update this README** - Add new documents to the appropriate section

---

## Implementation Status

| Document | Implementation Status | Location |
|----------|----------------------|----------|
| Design System | ✅ Active | `frontend/` |
| Retrieval Optimization | ✅ Implemented | `genreport/core/retrieval/` |
| Structure-Aware Retrieval | ✅ Implemented | `genreport/core/retrieval/structure_aware_retriever.py` |
| RAG Orchestrator | ✅ Implemented | `genreport/core/orchestration/rag_orchestrator.py` |
| Agentic RAG | ✅ Implemented | `genreport/core/orchestration/agentic_rag_agent.py` |

**Implementation Reports:** See `docs/reports/` for detailed deployment and completion reports.

---

## Questions?

- **Architecture questions:** Review related documents and cross-references
- **Implementation guidance:** Check `docs/guides/` for step-by-step tutorials
- **Debugging:** See `debugging_journals/` for troubleshooting guides
- **Status updates:** Check `docs/reports/` for sprint completion reports

---

**Maintained by:** Architecture Team
**Last Review:** 2025-10-24
**Next Review:** As needed when new architecture documents are added
