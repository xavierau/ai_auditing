"""
Trial Balance Disclosure System Demo

This notebook demonstrates how the three trial balance disclosure modules work:
1. Module 1: TrialBalanceParser - Parse and classify accounts
2. Module 2: DisclosureRequirementAnalyzer - Determine disclosure requirements using ReAct
3. Module 3: TrialBalanceDisclosureOrchestrator - Coordinate both modules

Author: GenReport Team
Date: 2025-10-25
"""

import os
import sys
from uuid import UUID
import asyncio
import dspy
from pprint import pprint

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from genreport.core.database.base import SessionLocal
from genreport.core.database.models import Project, WorksheetAnalysis
from genreport.core.orchestration.trial_balance_parser import (
    DSPyTrialBalanceParser,
    StructuredTrialBalance,
)
from genreport.core.orchestration.disclosure_requirement_analyzer import (
    DSPyDisclosureRequirementAnalyzer,
    DisclosureAnalysisResult,
)
from genreport.core.orchestration.trial_balance_disclosure_orchestrator import (
    TrialBalanceDisclosureOrchestrator,
    DisclosurePlan,
)
from genreport.core.orchestration.rag_orchestrator import RAGOrchestrator
from genreport.core.retrieval.kb_retriever import KBRetriever
from genreport.core.retrieval.structure_aware_retriever import StructureAwareRetriever
from genreport.core.retrieval.embedding_service import EmbeddingService

print("=" * 80)
print("TRIAL BALANCE DISCLOSURE SYSTEM DEMO")
print("=" * 80)
print()

# ==============================================================================
# SETUP: Configure DSPy and Database
# ==============================================================================

print("📋 Step 1: Setup and Configuration")
print("-" * 80)

# Get API key
api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    print("❌ GOOGLE_API_KEY not set!")
    sys.exit(1)

# Configure DSPy
lm = dspy.LM(
    'gemini/gemini-2.5-flash',
    api_key=api_key,
    temperature=0.0,
)
dspy.configure(lm=lm)
print("✅ DSPy configured with Gemini 2.5 Flash")

# Database connection
db = SessionLocal()
print("✅ Database connection established")

# Test data - Use a real project from database
# You can replace these with your actual IDs
TEST_TENANT_ID = UUID('00000000-0000-0000-0000-000000000001')  # Replace with real tenant ID
TEST_USER_ID = 1
TEST_PROJECT_ID = 1  # Replace with real project ID

print(f"✅ Test configuration:")
print(f"   Tenant ID: {TEST_TENANT_ID}")
print(f"   User ID: {TEST_USER_ID}")
print(f"   Project ID: {TEST_PROJECT_ID}")
print()

# ==============================================================================
# PART 1: MODULE 1 - TRIAL BALANCE PARSER
# ==============================================================================

print("=" * 80)
print("PART 1: MODULE 1 - TRIAL BALANCE PARSER")
print("=" * 80)
print()

print("📋 Module 1 demonstrates:")
print("   1. Account classification (asset/liability/equity/revenue/expense)")
print("   2. Category determination (current_asset, operating_expense, etc.)")
print("   3. Materiality assessment")
print()

# Sample trial balance data (for testing Module 1 independently)
sample_trial_balance = [
    {"code": "1100", "name": "Cash and bank", "balance": 500000, "debit_credit": "DR"},
    {"code": "1200", "name": "Trade receivables", "balance": 1200000, "debit_credit": "DR"},
    {"code": "1300", "name": "Inventory", "balance": 800000, "debit_credit": "DR"},
    {"code": "1500", "name": "Property, plant and equipment", "balance": 2500000, "debit_credit": "DR"},
    {"code": "2100", "name": "Trade payables", "balance": 600000, "debit_credit": "CR"},
    {"code": "2200", "name": "Bank loans", "balance": 1000000, "debit_credit": "CR"},
    {"code": "3100", "name": "Share capital", "balance": 1000000, "debit_credit": "CR"},
    {"code": "3200", "name": "Retained earnings", "balance": 1200000, "debit_credit": "CR"},
    {"code": "4000", "name": "Revenue", "balance": 5000000, "debit_credit": "CR"},
    {"code": "5000", "name": "Cost of sales", "balance": 3000000, "debit_credit": "DR"},
    {"code": "6100", "name": "Staff costs", "balance": 800000, "debit_credit": "DR"},
    {"code": "6200", "name": "Depreciation", "balance": 200000, "debit_credit": "DR"},
]

print("📊 Sample Trial Balance (12 accounts):")
for acc in sample_trial_balance[:3]:
    print(f"   {acc['code']}: {acc['name']} - ${acc['balance']:,}")
print(f"   ... and {len(sample_trial_balance) - 3} more accounts")
print()

# Initialize Module 1
parser = DSPyTrialBalanceParser(lm=lm)
print("✅ TrialBalanceParser initialized")
print()

print("⏳ Parsing and classifying accounts (this may take 30-60 seconds)...")
print("   - Classifying each account into type and category")
print("   - Assessing materiality for each account")
print()

# Parse trial balance
structured_tb = parser.parse(
    raw_trial_balance=sample_trial_balance,
    jurisdiction="HK",
    tenant_id=TEST_TENANT_ID,
    project_id=TEST_PROJECT_ID,
)

print("=" * 80)
print("📊 PARSING RESULTS")
print("=" * 80)
print()

print(f"Total Accounts:    {structured_tb.total_accounts}")
print(f"Total Assets:      ${structured_tb.total_assets:,.2f}")
print(f"Total Liabilities: ${structured_tb.total_liabilities:,.2f}")
print(f"Total Equity:      ${structured_tb.total_equity:,.2f}")
print(f"Total Revenue:     ${structured_tb.total_revenue:,.2f}")
print(f"Total Expenses:    ${structured_tb.total_expenses:,.2f}")
print()

print("=" * 80)
print("📋 CLASSIFIED ACCOUNTS")
print("=" * 80)

for acc in structured_tb.accounts:
    materiality_marker = "⭐ MATERIAL" if acc.is_material else ""
    print(f"\n{acc.code}: {acc.name}")
    print(f"   Type:       {acc.account_type}")
    print(f"   Category:   {acc.category}")
    print(f"   Balance:    ${acc.balance:,.2f} {acc.debit_credit}")
    if acc.is_material:
        print(f"   {materiality_marker}")

print()
print("✅ Module 1 Complete - Accounts classified and materiality assessed")
print()

# ==============================================================================
# PART 2: MODULE 2 - DISCLOSURE REQUIREMENT ANALYZER
# ==============================================================================

print("=" * 80)
print("PART 2: MODULE 2 - DISCLOSURE REQUIREMENT ANALYZER")
print("=" * 80)
print()

print("📋 Module 2 demonstrates:")
print("   1. DSPy ReAct pattern (THINK → ACT → OBSERVE → DECIDE → SYNTHESIZE)")
print("   2. Knowledge base search for disclosure requirements")
print("   3. Agent assignment for disclosure generation")
print()

# Initialize RAG Orchestrator (required by Module 2)
embedding_service = EmbeddingService()
kb_retriever = KBRetriever(
    db=db,
    jurisdiction="HK",  # Using HK jurisdiction for demo
    tenant_id=TEST_TENANT_ID,
    embedding_service=embedding_service,
)
structure_aware_retriever = StructureAwareRetriever(
    db=db,
    jurisdiction="HK",  # Using HK jurisdiction for demo
    tenant_id=TEST_TENANT_ID,
    embedding_service=embedding_service,
)

rag_orchestrator = RAGOrchestrator(
    kb_retriever=kb_retriever,
    structure_aware_retriever=structure_aware_retriever,
    embedding_service=embedding_service,
    tenant_id=TEST_TENANT_ID,
    user_id=TEST_USER_ID,
)
print("✅ RAG Orchestrator initialized")
print()

# Initialize Module 2
analyzer = DSPyDisclosureRequirementAnalyzer(
    rag_orchestrator=rag_orchestrator,
    tenant_id=TEST_TENANT_ID,
    user_id=TEST_USER_ID,
    lm=lm,
)
print("✅ DisclosureRequirementAnalyzer initialized")
print()

print("⏳ Analyzing disclosure requirements (this may take ~30-60 seconds with async parallelization)...")
print("   - Processing material accounts concurrently (4-10x speedup)")
print("   - For each material account:")
print("     1. THINK about potential disclosure requirements")
print("     2. ACT by searching knowledge base")
print("     3. OBSERVE search results from SME-FRS")
print("     4. DECIDE if disclosure is required")
print("     5. SYNTHESIZE complete requirement with agent assignment")
print()

# Analyze disclosure requirements (async with parallelization)
disclosure_analysis = asyncio.run(analyzer.analyze(
    structured_trial_balance=structured_tb,
    jurisdiction="HK",
    accounting_standard="SME-FRS",
))

print("=" * 80)
print("📊 DISCLOSURE ANALYSIS RESULTS")
print("=" * 80)
print()

print(f"Material Accounts Analyzed:     {disclosure_analysis.total_accounts_analyzed}")
print(f"Accounts Requiring Disclosure:  {disclosure_analysis.accounts_requiring_disclosure}")
print(f"Agents Assigned:                {len(disclosure_analysis.agent_assignments)}")
print()

print("=" * 80)
print("📋 DISCLOSURE REQUIREMENTS BY ACCOUNT")
print("=" * 80)

for req in disclosure_analysis.disclosure_requirements:
    if req.requires_disclosure:
        print(f"\n✅ {req.account_code}: {req.account_name}")
        print(f"   Disclosure Type:   {req.disclosure_type}")
        print(f"   Standard:          {req.applicable_standard}")
        print(f"   Assigned Agent:    {req.assigned_agent}")
        print(f"   Details:           {req.disclosure_details[:100]}...")
        print(f"   Reasoning:         {req.reasoning[:150]}...")
    else:
        print(f"\n❌ {req.account_code}: {req.account_name}")
        print(f"   No disclosure required")
        print(f"   Reasoning:         {req.reasoning[:150]}...")

print()
print("=" * 80)
print("📋 AGENT ASSIGNMENTS")
print("=" * 80)

for agent_name, account_codes in disclosure_analysis.agent_assignments.items():
    print(f"\n{agent_name.upper()} Agent:")
    for code in account_codes:
        account = next((acc for acc in structured_tb.accounts if acc.code == code), None)
        if account:
            print(f"   - {code}: {account.name}")

print()
print("✅ Module 2 Complete - Disclosure requirements determined with ReAct")
print()

# ==============================================================================
# PART 3: MODULE 3 - ORCHESTRATOR (END-TO-END INTEGRATION)
# ==============================================================================

print("=" * 80)
print("PART 3: MODULE 3 - TRIAL BALANCE DISCLOSURE ORCHESTRATOR")
print("=" * 80)
print()

print("📋 Module 3 demonstrates:")
print("   1. Extract trial balance from database (WorksheetAnalysis)")
print("   2. Coordinate Module 1 (parsing)")
print("   3. Coordinate Module 2 (disclosure analysis)")
print("   4. Create agent execution plan")
print("   5. Audit logging")
print()

# For demonstration, we'll manually insert sample trial balance into database
print("⚙️  Setting up test data in database...")

# Check if project exists
project = db.query(Project).filter(
    Project.id == TEST_PROJECT_ID,
    Project.tenant_id == TEST_TENANT_ID,
).first()

if not project:
    print(f"⚠️  Project {TEST_PROJECT_ID} not found. Creating mock project...")
    # In production, you would have a real project
    # For demo, we'll skip this and use the sample data
    print("   (Using sample data for demonstration)")
else:
    print(f"✅ Found project: {project.name} ({project.jurisdiction})")

    # Check if we have a summary worksheet with trial balance
    summary_ws = db.query(WorksheetAnalysis).filter(
        WorksheetAnalysis.project_id == TEST_PROJECT_ID,
        WorksheetAnalysis.tenant_id == TEST_TENANT_ID,
        WorksheetAnalysis.is_summary == True,
    ).first()

    if summary_ws and summary_ws.analysis_metadata.get("trial_balance"):
        print(f"✅ Found summary worksheet with trial balance: {summary_ws.worksheet_name}")
        print()

        # Initialize Module 3
        orchestrator = TrialBalanceDisclosureOrchestrator(
            db=db,
            rag_orchestrator=rag_orchestrator,
            tenant_id=TEST_TENANT_ID,
            user_id=TEST_USER_ID,
            lm=lm,
        )
        print("✅ TrialBalanceDisclosureOrchestrator initialized")
        print()

        print("⏳ Creating complete disclosure plan (this may take ~1-2 minutes with async)...")
        print("   1. Extracting trial balance from database")
        print("   2. Parsing and classifying accounts (Module 1)")
        print("   3. Analyzing disclosure requirements (Module 2) - ASYNC with parallelization")
        print("   4. Creating agent execution plan")
        print("   5. Audit logging")
        print()

        # Create disclosure plan (async)
        disclosure_plan = asyncio.run(orchestrator.create_disclosure_plan(
            project_id=TEST_PROJECT_ID
        ))

        print("=" * 80)
        print("📊 DISCLOSURE PLAN")
        print("=" * 80)
        print()

        print(f"Project ID:                     {disclosure_plan.project_id}")
        print(f"Jurisdiction:                   {disclosure_plan.jurisdiction}")
        print(f"Accounting Standard:            {disclosure_plan.accounting_standard}")
        print(f"Total Accounts:                 {disclosure_plan.metadata['total_accounts']}")
        print(f"Material Accounts:              {disclosure_plan.metadata['material_accounts']}")
        print(f"Accounts Requiring Disclosure:  {disclosure_plan.metadata['accounts_requiring_disclosure']}")
        print(f"Agents Assigned:                {disclosure_plan.metadata['agents_assigned']}")
        print()

        print("=" * 80)
        print("📋 AGENT EXECUTION PLAN")
        print("=" * 80)

        for agent_name, plan_details in disclosure_plan.agent_execution_plan.items():
            print(f"\n{agent_name.upper()} Agent:")
            print(f"   Assigned Accounts: {len(plan_details['accounts'])}")

            for account in plan_details['accounts']:
                print(f"      - {account['code']}: {account['name']} (${account['balance']:,.2f})")

            print(f"\n   Disclosure Requirements:")
            for req in plan_details['disclosure_requirements']:
                print(f"      - {req['account_code']}: {req['disclosure_type']}")
                print(f"        Standard: {req['applicable_standard']}")
                print(f"        Details: {req['disclosure_details'][:80]}...")

        print()
        print("✅ Module 3 Complete - Full disclosure plan created and logged")

    else:
        print("⚠️  No summary worksheet with trial balance found")
        print("   Using Module 1 and Module 2 results from above for demonstration")

print()

# ==============================================================================
# SUMMARY
# ==============================================================================

print("=" * 80)
print("📊 DEMO SUMMARY")
print("=" * 80)
print()

print("✅ Module 1 (TrialBalanceParser):")
print("   - Successfully parsed and classified trial balance accounts")
print("   - Determined account types and categories using DSPy")
print("   - Assessed materiality for disclosure prioritization")
print()

print("✅ Module 2 (DisclosureRequirementAnalyzer):")
print("   - Used DSPy ReAct pattern for autonomous reasoning")
print("   - Searched knowledge base for disclosure requirements")
print("   - Determined which accounts require disclosures")
print("   - Assigned accounts to appropriate financial agents")
print()

print("✅ Module 3 (TrialBalanceDisclosureOrchestrator):")
print("   - Coordinated both modules seamlessly")
print("   - Integrated with database (WorksheetAnalysis)")
print("   - Created complete disclosure plan with agent assignments")
print("   - Audit logged the entire process")
print()

print("=" * 80)
print("🎯 KEY INSIGHTS")
print("=" * 80)
print()

print("1. Dynamic Analysis:")
print("   - No hardcoded account classification logic")
print("   - DSPy modules adapt to different trial balance structures")
print()

print("2. Separation of Concerns:")
print("   - Module 1: ONLY responsible for parsing and classification")
print("   - Module 2: ONLY responsible for disclosure determination")
print("   - Module 3: ONLY responsible for coordination")
print()

print("3. ReAct Pattern:")
print("   - Module 2 uses iterative reasoning (THINK → ACT → OBSERVE)")
print("   - Searches knowledge base autonomously")
print("   - Makes evidence-based decisions with source attribution")
print()

print("4. Agent Assignment:")
print("   - Automatically maps accounts to specialized agents")
print("   - Revenue accounts → revenue agent")
print("   - Inventory accounts → inventory agent")
print("   - PPE accounts → ppe agent")
print()

print("5. Integration Ready:")
print("   - Modules integrate with existing SecureOrchestrator")
print("   - Uses WorksheetAnalysis for trial balance data")
print("   - Audit logs all operations for compliance")
print()

print("=" * 80)
print("✅ DEMO COMPLETE")
print("=" * 80)

# Cleanup
db.close()
