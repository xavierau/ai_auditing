# GenReport System Flow: Excel Upload to DOCX Download

**Date:** 2025-10-26
**Status:** Current Architecture
**Version:** 2.0 (with Trial Balance Disclosure Modules)

---

## Complete System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React + TypeScript)                       │
│                                                                              │
│  User Actions:                                                               │
│  1. Upload Excel workbook                                                    │
│  2. Trigger report generation                                                │
│  3. Review generated report                                                  │
│  4. Download DOCX file                                                       │
└────────────┬────────────────────────────────────────────────────────────────┘
             │
             │ HTTP/REST API
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FASTAPI BACKEND                                     │
│                                                                              │
│  API Routers:                                                                │
│  • /api/files          - File upload & management                           │
│  • /api/projects       - Project CRUD                                       │
│  • /api/reports        - Report generation & retrieval                      │
│  • /api/export         - DOCX export                                        │
└─────┬───────────────────────────────────────┬───────────────────────────────┘
      │                                       │
      │ 1. Excel Upload                       │ 4. Export Request
      ▼                                       ▼
┌─────────────────────────────────┐  ┌──────────────────────────────────────┐
│   FILE ENCRYPTION SERVICE       │  │      EXPORT SERVICE                  │
│                                 │  │                                      │
│  • Encrypt uploaded file        │  │  • Generate DOCX from report        │
│  • Store in encrypted storage   │  │  • Apply market-specific template   │
│  • Tenant-specific keys (KMS)   │  │  • Include jurisdiction formatting  │
└─────────┬───────────────────────┘  └──────────────────────────────────────┘
          │                                                  ▲
          │ Trigger parsing                                 │
          ▼                                                 │
┌─────────────────────────────────────────────────────────┐│
│         PHASE 1: EXCEL PARSING                          ││
│                                                          ││
│  ┌────────────────────────────────────────────────────┐ ││
│  │  PreliminaryScanner (DSPy-based)                   │ ││
│  │                                                     │ ││
│  │  1. Detect coding system (hierarchical/flat/mixed) │ ││
│  │  2. Identify code families                         │ ││
│  │  3. Analyze worksheets:                            │ ││
│  │     - Identify summary worksheet                   │ ││
│  │     - Identify supporting worksheets               │ ││
│  │     - Extract referenced codes                     │ ││
│  │     - Calculate importance scores                  │ ││
│  │  4. Store WorksheetAnalysis records                │ ││
│  │  5. Store RelationshipMap                          │ ││
│  └────────────────────────────────────────────────────┘ ││
│                                                          ││
│  Output: WorksheetAnalysis + RelationshipMap in DB      ││
└─────────────┬────────────────────────────────────────────┘│
              │                                             │
              │ Report generation triggered                 │
              ▼                                             │
┌─────────────────────────────────────────────────────────┐│
│    PHASE 2: TRIAL BALANCE DISCLOSURE SYSTEM (NEW!)     ││
│                                                          ││
│  ┌────────────────────────────────────────────────────┐ ││
│  │  Module 3: TrialBalanceDisclosureOrchestrator      │ ││
│  │  (Wrapper - Coordinates Modules 1 & 2)             │ ││
│  │                                                     │ ││
│  │  Step 1: Extract Trial Balance                     │ ││
│  │    • Query WorksheetAnalysis (is_summary=True)     │ ││
│  │    • Extract analysis_metadata['trial_balance']    │ ││
│  │                                                     │ ││
│  │  Step 2: Invoke Module 1 ──────────┐               │ ││
│  └────────────────────────────────────┼───────────────┘ ││
│                                       ▼                  ││
│  ┌────────────────────────────────────────────────────┐ ││
│  │  Module 1: TrialBalanceParser (DSPy)               │ ││
│  │                                                     │ ││
│  │  For each account:                                 │ ││
│  │    ┌─────────────────────────────────────────────┐ │ ││
│  │    │ AccountClassificationSignature (DSPy)       │ │ ││
│  │    │  Input: code, name, debit_credit            │ │ ││
│  │    │  Output: account_type, category, reasoning  │ │ ││
│  │    └─────────────────────────────────────────────┘ │ ││
│  │                                                     │ ││
│  │    ┌─────────────────────────────────────────────┐ │ ││
│  │    │ MaterialityAssessmentSignature (DSPy)       │ │ ││
│  │    │  Input: code, name, balance, total_assets   │ │ ││
│  │    │  Output: is_material, materiality_%         │ │ ││
│  │    └─────────────────────────────────────────────┘ │ ││
│  │                                                     │ ││
│  │  Output: StructuredTrialBalance                    │ ││
│  │    • All accounts classified by type & category    │ ││
│  │    • Materiality assessed                          │ ││
│  │    • Totals calculated                             │ ││
│  └────────────────────┬───────────────────────────────┘ ││
│                       │                                  ││
│  Step 3: Invoke Module 2                                ││
│                       ▼                                  ││
│  ┌────────────────────────────────────────────────────┐ ││
│  │  Module 2: DisclosureRequirementAnalyzer (DSPy)    │ ││
│  │                                                     │ ││
│  │  For each material account:                        │ ││
│  │    ┌─────────────────────────────────────────────┐ │ ││
│  │    │ DSPy ReAct Module                           │ │ ││
│  │    │                                             │ │ ││
│  │    │ THINK: What disclosure might be required?  │ │ ││
│  │    │   ▼                                         │ │ ││
│  │    │ ACT: Search knowledge base ─────────────────┼─┼─┼──┐
│  │    │   │   (via SearchKnowledgeBaseTool)         │ │ │  │
│  │    │   ▼                                         │ │ │  │
│  │    │ OBSERVE: Review search results              │ │ │  │
│  │    │   ▼                                         │ │ │  │
│  │    │ DECIDE: Is disclosure required?             │ │ │  │
│  │    │   ▼                                         │ │ │  │
│  │    │ SYNTHESIZE: Complete requirement +          │ │ │  │
│  │    │             agent assignment                │ │ │  │
│  │    └─────────────────────────────────────────────┘ │ │  │
│  │                                                     │ │  │
│  │  Output: DisclosureAnalysisResult                  │ │  │
│  │    • Disclosure requirements per account           │ │  │
│  │    • Agent assignments (revenue, inventory, etc.)  │ │  │
│  │    • Source references from knowledge base         │ │  │
│  └────────────────────┬───────────────────────────────┘ │  │
│                       │                                  │  │
│  Step 4: Create Disclosure Plan                         │  │
│                       ▼                                  │  │
│  ┌────────────────────────────────────────────────────┐ │  │
│  │  Output: DisclosurePlan                            │ │  │
│  │                                                     │ │  │
│  │  • StructuredTrialBalance                          │ │  │
│  │  • DisclosureAnalysisResult                        │ │  │
│  │  • Agent Execution Plan:                           │ │  │
│  │    {                                               │ │  │
│  │      "revenue": {                                  │ │  │
│  │        "accounts": [4000, 4100],                   │ │  │
│  │        "requirements": [...]                       │ │  │
│  │      },                                            │ │  │
│  │      "inventory": {                                │ │  │
│  │        "accounts": [1300],                         │ │  │
│  │        "requirements": [...]                       │ │  │
│  │      }                                             │ │  │
│  │    }                                               │ │  │
│  └────────────────────┬───────────────────────────────┘ │  │
└────────────────────────┼──────────────────────────────────┘  │
                        │                                     │
                        │ DisclosurePlan ready                │
                        ▼                                     │
┌─────────────────────────────────────────────────────────┐  │
│           PHASE 3: KNOWLEDGE BASE RAG SYSTEM            │  │
│                                                          │  │
│  ┌────────────────────────────────────────────────────┐ │  │
│  │  RAG Orchestrator                                  │ │◄─┘
│  │                                                     │ │
│  │  1. Query Understanding                            │ │
│  │     - Detect intent (template/requirement/example) │ │
│  │     - Expand query with synonyms                   │ │
│  │                                                     │ │
│  │  2. Strategy Selection                             │ │
│  │     - Semantic (fast)                              │ │
│  │     - Structure-aware (accurate)                   │ │
│  │     - Hybrid (balanced)                            │ │
│  │                                                     │ │
│  │  3. Retrieval Execution                            │ │
│  │     ┌─────────────────────────────────────────┐    │ │
│  │     │ KBRetriever (Semantic Search)           │    │ │
│  │     │  • PGVector cosine similarity           │    │ │
│  │     │  • Jurisdiction filtering (HK/SG/AU)    │    │ │
│  │     │  • Tenant isolation                     │    │ │
│  │     └─────────────────────────────────────────┘    │ │
│  │                                                     │ │
│  │     ┌─────────────────────────────────────────┐    │ │
│  │     │ StructureAwareRetriever                 │    │ │
│  │     │  • TOC-based navigation                 │    │ │
│  │     │  • Section context awareness            │    │ │
│  │     │  • Chunk merging                        │    │ │
│  │     └─────────────────────────────────────────┘    │ │
│  │                                                     │ │
│  │  4. Re-ranking & Context Assembly                  │ │
│  │  5. Caching (Redis, 15-min TTL)                    │ │
│  └────────────────────┬───────────────────────────────┘ │
│                       │                                  │
│  ┌────────────────────▼───────────────────────────────┐ │
│  │  Agentic RAG Agent (DSPy ReAct)                    │ │
│  │                                                     │ │
│  │  Tools:                                            │ │
│  │    • search_knowledge_base(query, top_k)           │ │
│  │    • search_by_section(section_name)               │ │
│  │                                                     │ │
│  │  Process:                                          │ │
│  │    THINK → ACT → OBSERVE → DECIDE → SYNTHESIZE    │ │
│  │                                                     │ │
│  │  Output: Context with source attribution          │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────┬────────────────────────────────────────────┘
              │
              │ Retrieved context
              ▼
┌─────────────────────────────────────────────────────────┐
│        PHASE 4: FINANCIAL AGENTS (DSPy-based)           │
│                                                          │
│  SecureOrchestrator coordinates agents based on         │
│  DisclosurePlan from Phase 2                            │
│                                                          │
│  For each assigned agent in DisclosurePlan:             │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Market-Specific Financial Agents                  │ │
│  │                                                     │ │
│  │  ┌──────────────────────────────────────────────┐  │ │
│  │  │ HKRevenueAgent                               │  │ │
│  │  │  • Input: DisclosurePlan.revenue accounts    │  │ │
│  │  │  • Retrieves: HKFRS 15 / SME-FRS Section 23  │  │ │
│  │  │  • Generates: Revenue disclosure note        │  │ │
│  │  └──────────────────────────────────────────────┘  │ │
│  │                                                     │ │
│  │  ┌──────────────────────────────────────────────┐  │ │
│  │  │ HKInventoryAgent                             │  │ │
│  │  │  • Input: DisclosurePlan.inventory accounts  │  │ │
│  │  │  • Retrieves: SME-FRS Section 13             │  │ │
│  │  │  • Generates: Inventory disclosure note      │  │ │
│  │  └──────────────────────────────────────────────┘  │ │
│  │                                                     │ │
│  │  ┌──────────────────────────────────────────────┐  │ │
│  │  │ HKProvisionsAgent                            │  │ │
│  │  │  • Input: DisclosurePlan.provisions accounts │  │ │
│  │  │  • Retrieves: SME-FRS Section 21             │  │ │
│  │  │  • Generates: Provisions disclosure note     │  │ │
│  │  └──────────────────────────────────────────────┘  │ │
│  │                                                     │ │
│  │  ... (other agents as assigned by DisclosurePlan)  │ │
│  │                                                     │ │
│  │  Each agent:                                       │ │
│  │    1. Validates inputs (context validation)        │ │
│  │    2. Retrieves relevant standards (via RAG)       │ │
│  │    3. Generates disclosure (DSPy module)           │ │
│  │    4. Verifies completeness                        │ │
│  │    5. Detects PII (redaction if needed)            │ │
│  │    6. Returns AgentOutput with sources             │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  Output: List of AgentOutput (one per agent)            │
│    • Generated disclosure text                          │
│    • Source references                                  │
│    • Completeness score                                 │
│    • Confidence level                                   │
└─────────────┬────────────────────────────────────────────┘
              │
              │ All agent outputs collected
              ▼
┌─────────────────────────────────────────────────────────┐
│           PHASE 5: REPORT ASSEMBLY                      │
│                                                          │
│  SecureOrchestrator:                                    │
│    1. Collect all AgentOutput results                   │
│    2. Assemble into Report structure                    │
│    3. Store in database:                                │
│       - Report.content (JSON)                           │
│       - Report.status = 'completed'                     │
│       - Report.metadata (agents used, timing)           │
│    4. Audit log report generation                       │
│                                                          │
│  Output: Report record in database                      │
└─────────────┬────────────────────────────────────────────┘
              │
              │ User requests download
              ▼
┌─────────────────────────────────────────────────────────┐
│           PHASE 6: DOCX EXPORT                          │
│                                                          │
│  Export Service:                                        │
│    1. Load Report from database                         │
│    2. Select market-specific template                   │
│       - HK: HKFRS/SME-FRS template                      │
│       - SG: SFRS template                               │
│       - AU: AASB template                               │
│    3. Generate DOCX using python-docx:                  │
│       - Apply jurisdiction formatting                   │
│       - Include all disclosure sections                 │
│       - Format tables and numbers                       │
│       - Add headers/footers                             │
│    4. Return DOCX file to frontend                      │
│                                                          │
│  Output: DOCX file download                             │
└─────────────────────────────────────────────────────────┘
```

---

## Key Module Interactions

### Module Communication Flow

```
WorksheetAnalysis (DB)
         │
         ├──────────────────────────────────────────┐
         │                                          │
         ▼                                          ▼
  ┌─────────────────┐                    ┌──────────────────┐
  │ Module 3        │                    │ RAG Orchestrator │
  │ (Orchestrator)  │                    │                  │
  └────────┬────────┘                    └────────┬─────────┘
           │                                      │
           │ Extract TB                           │
           ▼                                      │
  ┌─────────────────┐                            │
  │ Module 1        │                            │
  │ (Parser)        │                            │
  │                 │                            │
  │ Output: STB     │                            │
  └────────┬────────┘                            │
           │                                      │
           │ STB                                  │
           ▼                                      │
  ┌─────────────────┐                            │
  │ Module 2        │◄───────────────────────────┘
  │ (Analyzer)      │  Knowledge base search
  │                 │
  │ Output: DAR     │
  └────────┬────────┘
           │
           │ DAR
           ▼
  ┌─────────────────┐
  │ Module 3        │
  │ (Orchestrator)  │
  │                 │
  │ Output: DP      │
  └────────┬────────┘
           │
           │ Disclosure Plan
           ▼
  ┌─────────────────┐
  │ Financial       │
  │ Agents          │
  │ (Revenue, etc.) │
  └─────────────────┘

Legend:
  TB  = Trial Balance
  STB = StructuredTrialBalance
  DAR = DisclosureAnalysisResult
  DP  = DisclosurePlan
```

---

## Data Flow Summary

### 1. Excel Upload → Parsing
```
Excel File
    → FileEncryption (encrypt, store)
    → PreliminaryScanner (analyze worksheets)
    → WorksheetAnalysis + RelationshipMap (DB)
```

### 2. Report Generation → Trial Balance Analysis (NEW!)
```
WorksheetAnalysis
    → Module 3: Extract trial balance
    → Module 1: Parse & classify accounts
    → Module 2: Determine disclosure requirements (ReAct)
    → Module 3: Create DisclosurePlan
```

### 3. Disclosure Plan → Agent Execution
```
DisclosurePlan
    → SecureOrchestrator
    → For each agent in plan:
        → Retrieve context (RAG Orchestrator)
        → Generate disclosure (Financial Agent)
    → Collect AgentOutputs
```

### 4. Report Assembly → Export
```
AgentOutputs
    → Assemble Report
    → Store in DB
    → Export to DOCX (market-specific template)
    → Download
```

---

## Key Improvements with New Modules

### Before (Hardcoded Logic)
```python
# ❌ Old approach in SecureOrchestrator
if account_code.startswith('4'):
    agents_to_run.append('revenue')
elif account_code.startswith('13'):
    agents_to_run.append('inventory')
```

### After (Dynamic Analysis)
```python
# ✅ New approach with Trial Balance Disclosure System
disclosure_plan = orchestrator.create_disclosure_plan(project_id)

# disclosure_plan.agent_execution_plan:
# {
#   "revenue": {
#     "accounts": [4000, 4100],  # Determined by Module 2 ReAct
#     "requirements": [...]
#   },
#   "inventory": {
#     "accounts": [1300],  # Determined by Module 2 ReAct
#     "requirements": [...]
#   }
# }

for agent_name, plan in disclosure_plan.agent_execution_plan.items():
    agent = agents[agent_name]
    result = agent.process(plan['accounts'], plan['requirements'])
```

---

## Module Responsibilities

| Module | Responsibility | Input | Output |
|--------|---------------|-------|--------|
| **Module 1: TrialBalanceParser** | Parse and classify accounts | Raw trial balance | StructuredTrialBalance |
| **Module 2: DisclosureRequirementAnalyzer** | Determine disclosure requirements using ReAct | StructuredTrialBalance | DisclosureAnalysisResult |
| **Module 3: TrialBalanceDisclosureOrchestrator** | Coordinate both modules | Project ID | DisclosurePlan |
| **RAG Orchestrator** | Retrieve accounting standards | Query | Context chunks |
| **Agentic RAG Agent** | Autonomous retrieval with reasoning | Query | Context with attribution |
| **Financial Agents** | Generate disclosures | Accounts + requirements | Disclosure text |
| **SecureOrchestrator** | Overall report coordination | Project ID | Complete Report |

---

## Performance Characteristics

| Phase | Time | Bottleneck | Optimization |
|-------|------|-----------|--------------|
| Excel Parsing | 30-60s | DSPy worksheet analysis | Parallel processing |
| Trial Balance Analysis | 1-2 min | Module 2 ReAct (KB searches) | Cache results, reduce max_iters |
| Knowledge Retrieval | 3-5s per query | Embedding generation | Redis cache (80% hit rate) |
| Agent Execution | 10-30s per agent | LLM generation | Parallel agent execution |
| DOCX Export | 2-5s | Template rendering | Pre-compiled templates |
| **Total** | **2-4 min** | Agent execution | Concurrent processing |

---

## Security Checkpoints

Each phase enforces multi-tenant security:

1. **File Upload:** Tenant-specific encryption keys
2. **Parsing:** Tenant ID in all WorksheetAnalysis records
3. **Trial Balance Analysis:** Tenant context validation
4. **Knowledge Retrieval:** Jurisdiction + tenant filtering
5. **Agent Execution:** Context validation (no cross-tenant data)
6. **Report Storage:** Tenant ID in Report table
7. **Export:** Verify user has access to report's tenant

All operations are audit logged.

---

**Last Updated:** 2025-10-26
**Next Review:** When adding new markets (SG/AU) or agents
