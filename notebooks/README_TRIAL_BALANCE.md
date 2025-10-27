# Trial Balance Disclosure System Demo

**Notebook:** `05_trial_balance_disclosure_demo.py`
**Created:** 2025-10-25
**Purpose:** Demonstrate the three trial balance disclosure modules

---

## Overview

This notebook demonstrates how the GenReport system dynamically analyzes trial balance data and determines disclosure requirements using DSPy-based autonomous agents.

## Architecture

The system consists of three modules with clear separation of concerns:

```
Module 1: TrialBalanceParser
├── Responsibility: Parse and classify accounts
├── Input: Raw trial balance (code, name, balance)
└── Output: StructuredTrialBalance with classifications

Module 2: DisclosureRequirementAnalyzer
├── Responsibility: Determine disclosure requirements
├── Pattern: DSPy ReAct (THINK → ACT → OBSERVE → DECIDE)
├── Input: StructuredTrialBalance
└── Output: DisclosureAnalysisResult with agent assignments

Module 3: TrialBalanceDisclosureOrchestrator
├── Responsibility: Coordinate both modules
├── Integration: WorksheetAnalysis database
└── Output: Complete DisclosurePlan for agent execution
```

## What Each Module Does

### Module 1: TrialBalanceParser

**File:** `genreport/core/orchestration/trial_balance_parser.py`

**Purpose:** Parse and classify trial balance accounts

**Process:**
1. Takes raw trial balance data (account code, name, balance)
2. Uses DSPy ChainOfThought to classify each account:
   - Account type: asset, liability, equity, revenue, expense
   - Category: current_asset, non_current_liability, operating_expense, etc.
3. Assesses materiality for each account
4. Calculates totals by account type

**Key Components:**
- `AccountClassificationSignature` - DSPy signature for classification
- `MaterialityAssessmentSignature` - DSPy signature for materiality
- `DSPyTrialBalanceParser` - Main parser class

**Example Output:**
```
Account: 1300 - Inventory
  Type: asset
  Category: current_asset
  Balance: $800,000 DR
  Material: ⭐ YES
```

---

### Module 2: DisclosureRequirementAnalyzer

**File:** `genreport/core/orchestration/disclosure_requirement_analyzer.py`

**Purpose:** Determine what disclosures are required for each account

**Process (ReAct Pattern):**
1. **THINK:** Consider what disclosure might be required for this account
2. **ACT:** Search knowledge base for relevant standards (HKFRS, SME-FRS)
3. **OBSERVE:** Review search results and extract requirements
4. **DECIDE:** Determine if disclosure is required based on evidence
5. **SYNTHESIZE:** Create complete requirement with agent assignment

**Key Components:**
- `SearchKnowledgeBaseTool` - DSPy tool for RAG
- `DisclosureRequirementSignature` - DSPy ReAct signature
- `DSPyDisclosureRequirementAnalyzer` - Main analyzer class

**Example ReAct Trace:**
```
Account: 1300 - Inventory

THINK: Inventory is material (15% of assets). Need to check
       disclosure requirements for inventory valuation and measurement.

ACT:   Search knowledge base for "inventory disclosure requirements SME-FRS"

OBSERVE: Found SME-FRS Section 13 - Inventories
         - Requires disclosure of accounting policy
         - Requires breakdown by category
         - Requires write-down information

DECIDE: ✅ Disclosure REQUIRED

SYNTHESIZE:
  - Disclosure Type: note + policy
  - Standard: SME-FRS Section 13
  - Assigned Agent: inventory
  - Details: Disclose inventory accounting policy, categories, and write-downs
```

---

### Module 3: TrialBalanceDisclosureOrchestrator

**File:** `genreport/core/orchestration/trial_balance_disclosure_orchestrator.py`

**Purpose:** Coordinate both modules and integrate with database

**Process:**
1. Extract trial balance from `WorksheetAnalysis` table
2. Call Module 1 to parse and classify accounts
3. Call Module 2 to determine disclosure requirements
4. Create agent execution plan (maps agents to accounts)
5. Audit log the disclosure plan

**Key Components:**
- `DisclosurePlan` - Complete plan with agent assignments
- `TrialBalanceDisclosureOrchestrator` - Main coordinator

**Example Output:**
```
REVENUE Agent:
  Assigned Accounts:
    - 4000: Revenue ($5,000,000)

  Disclosure Requirements:
    - 4000: note + policy
      Standard: HKFRS 15 / SME-FRS Section 23
      Details: Revenue recognition policy and breakdown by category

INVENTORY Agent:
  Assigned Accounts:
    - 1300: Inventory ($800,000)

  Disclosure Requirements:
    - 1300: note + policy
      Standard: SME-FRS Section 13
      Details: Inventory valuation policy and category breakdown
```

---

## Running the Demo

### Prerequisites

1. **Environment Variables:**
   ```bash
   export GOOGLE_API_KEY="your-gemini-api-key"
   ```

2. **Database Setup:**
   - PostgreSQL running with GenReport schema
   - At least one project with uploaded Excel file
   - Summary worksheet with trial balance data

3. **Knowledge Base:**
   - SME-FRS or HKFRS documents ingested
   - Vector embeddings generated
   - Chunks categorized

### Execute the Notebook

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the demo
python notebooks/05_trial_balance_disclosure_demo.py
```

### Expected Output

The demo will run in three parts:

**Part 1: Module 1 Demo (30-60 seconds)**
- Parse sample trial balance with 12 accounts
- Classify each account into type and category
- Assess materiality
- Display structured results

**Part 2: Module 2 Demo (2-3 minutes)**
- Analyze each material account
- Use ReAct pattern to search knowledge base
- Determine disclosure requirements
- Assign accounts to agents
- Display reasoning for each decision

**Part 3: Module 3 Demo (3-5 minutes if database has data)**
- Extract real trial balance from database
- Coordinate both modules
- Create complete disclosure plan
- Display agent execution plan

---

## Configuration

### Test Data Setup

Edit these variables in the notebook to use your own data:

```python
# Line 39-41
TEST_TENANT_ID = UUID('your-tenant-id')
TEST_USER_ID = 1  # Your user ID
TEST_PROJECT_ID = 1  # Your project ID
```

### Sample Trial Balance

The demo includes a sample trial balance (lines 59-70) for testing Module 1 and Module 2:
- 12 accounts across all types (assets, liabilities, equity, revenue, expenses)
- Realistic balances for materiality testing
- Mix of current and non-current items

You can modify this sample data to test different scenarios.

---

## Key Insights from Demo

### 1. No Hardcoded Logic

Unlike traditional systems that hardcode rules like:
```python
if code.startswith('4'):
    return 'revenue'  # ❌ Brittle
```

This system uses DSPy to dynamically classify:
```python
classification = dspy.ChainOfThought(AccountClassificationSignature)
result = classification(
    account_code="4000",
    account_name="Revenue from services"
)
# ✅ Adapts to any account structure
```

### 2. Evidence-Based Decisions

Module 2 doesn't guess - it:
1. Searches knowledge base for relevant standards
2. Extracts specific requirements
3. Makes decisions based on evidence
4. Provides source attribution

### 3. Separation of Concerns

Each module has a single responsibility:
- **Module 1:** Parsing ONLY
- **Module 2:** Disclosure determination ONLY
- **Module 3:** Coordination ONLY

This follows SOLID principles and makes testing/maintenance easier.

### 4. Agent Assignment

The system automatically maps accounts to specialized agents:
- Revenue (4xxx) → `revenue` agent
- Inventory (13xx) → `inventory` agent
- PPE (15xx) → `ppe` agent
- Receivables (12xx) → `receivables` agent

### 5. Audit Trail

Every step is logged:
- Account classifications
- Knowledge base searches
- Disclosure decisions
- Agent assignments

---

## Integration with SecureOrchestrator

The disclosure plan integrates seamlessly with the existing report generation flow:

```python
# SecureOrchestrator.generate_report()

# 1. Create disclosure plan (NEW)
disclosure_plan = TrialBalanceDisclosureOrchestrator.create_disclosure_plan(
    project_id=self.project_id
)

# 2. For each assigned agent, pass relevant accounts
for agent_name, plan_details in disclosure_plan.agent_execution_plan.items():
    agent = self.agents[agent_name]

    # Pass assigned accounts and requirements to agent
    agent_input = AgentInput(
        accounts=plan_details['accounts'],
        requirements=plan_details['disclosure_requirements'],
        # ... other context
    )

    result = agent.process(agent_input)

# 3. Combine results into final report
```

---

## Troubleshooting

### "No summary worksheet found"

**Issue:** Module 3 can't find trial balance in database

**Solution:**
1. Check that WorksheetAnalysis has `is_summary=True` record
2. Verify `analysis_metadata` contains `trial_balance` key
3. Use Module 1 and Module 2 demos independently (they work with sample data)

### "GOOGLE_API_KEY not set"

**Issue:** DSPy can't initialize Gemini

**Solution:**
```bash
export GOOGLE_API_KEY="your-key-here"
```

### "Module 2 taking too long"

**Issue:** ReAct pattern making many knowledge base searches

**Expected:** 2-3 minutes for 5-8 material accounts
- Each account may trigger 1-3 knowledge base searches
- Each search takes 3-5 seconds

**Optimization:** Reduce `max_iters` in disclosure_requirement_analyzer.py:89
```python
self.disclosure_analyzer = dspy.ReAct(
    signature=DisclosureRequirementSignature,
    tools=[self.search_tool],
    max_iters=2,  # Reduce from 3 to 2
)
```

---

## Next Steps

1. **Run the Demo:**
   - Execute with sample data first
   - Then configure with your project data

2. **Review Output:**
   - Check account classifications (Module 1)
   - Review ReAct reasoning (Module 2)
   - Examine agent execution plan (Module 3)

3. **Test Integration:**
   - Integrate with SecureOrchestrator
   - Run end-to-end report generation
   - Verify disclosures match requirements

4. **Optimize:**
   - Tune materiality thresholds
   - Add custom account categories
   - Adjust ReAct max iterations

---

## Related Documentation

- **Architecture:** `docs/architecture/2025-10-23-rag-orchestrator-design.md`
- **Agentic RAG:** `docs/architecture/2025-10-23-agentic-rag-react-design.md`
- **Other Notebooks:**
  - `03_structure_aware_demo.py` - Structure-aware retrieval
  - `04_agentic_rag_demo.py` - Agentic RAG with ReAct

---

**Questions?** See `docs/guides/README.md` for implementation guides.
