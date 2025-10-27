"""
Disclosure Requirement Analyzer - Module 2

Responsible for determining disclosure requirements for each trial balance account.
Uses DSPy ReAct pattern with tools to:
1. Query knowledge base for disclosure requirements
2. Analyze account characteristics against requirements
3. Map accounts to appropriate financial agents
4. Generate structured disclosure requirements

Author: GenReport Team
Date: 2025-10-25
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from uuid import UUID
import asyncio
import logging
import dspy

from genreport.core.orchestration.trial_balance_parser import (
    TrialBalanceAccount,
    StructuredTrialBalance,
)
from genreport.core.orchestration.rag_orchestrator import (
    RAGOrchestrator,
    RAGQuery,
    QueryIntent,
)

logger = logging.getLogger(__name__)


class DisclosureRequirement(BaseModel):
    """Structured disclosure requirement for a trial balance account."""

    account_code: str = Field(..., description="Account code")
    account_name: str = Field(..., description="Account name")
    requires_disclosure: bool = Field(..., description="Whether disclosure is required")

    disclosure_type: Optional[str] = Field(
        None,
        description="Type of disclosure (e.g., 'note', 'policy', 'breakdown')"
    )

    applicable_standard: Optional[str] = Field(
        None,
        description="Accounting standard requiring disclosure (e.g., 'HKFRS 15', 'SME-FRS Section 13')"
    )

    disclosure_details: str = Field(
        default="",
        description="Specific disclosure requirements and content"
    )

    assigned_agent: Optional[str] = Field(
        None,
        description="Agent responsible for generating this disclosure (e.g., 'revenue', 'inventory')"
    )

    source_references: List[str] = Field(
        default_factory=list,
        description="Knowledge base sources used for this determination"
    )

    reasoning: str = Field(
        default="",
        description="Explanation of why this disclosure is/isn't required"
    )


class DisclosureAnalysisResult(BaseModel):
    """Complete disclosure requirement analysis for all trial balance accounts."""

    total_accounts_analyzed: int
    accounts_requiring_disclosure: int
    disclosure_requirements: List[DisclosureRequirement]

    agent_assignments: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Map of agent name to list of account codes"
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Analysis context and statistics"
    )


class SearchKnowledgeBaseTool:
    """Tool for searching knowledge base for disclosure requirements."""

    def __init__(self, rag_orchestrator: RAGOrchestrator, tenant_id: UUID, user_id: int):
        self.rag_orchestrator = rag_orchestrator
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.name = "search_knowledge_base"
        self.desc = "Search the knowledge base for accounting disclosure requirements and standards"

    def __call__(self, query: str, top_k: int = 5) -> str:
        """
        Search knowledge base for disclosure requirements.

        Args:
            query: Natural language query
            top_k: Number of results to return

        Returns:
            Formatted search results with source references
        """
        rag_query = RAGQuery(
            query_text=query,
            top_k=top_k,
            intent=QueryIntent.REQUIREMENT,
            filters={"chunk_types": ["requirement", "template", "disclosure"]},
            tenant_id=self.tenant_id,
            user_id=self.user_id,
        )

        result = self.rag_orchestrator.retrieve(rag_query)

        # Format results
        formatted_results = []
        for i, chunk in enumerate(result.chunks, 1):
            formatted_results.append(
                f"[{i}] {chunk.source_reference}\n"
                f"Type: {chunk.chunk_type}\n"
                f"Content: {chunk.content}\n"
                f"Relevance: {chunk.relevance_score:.2f}\n"
            )

        return "\n".join(formatted_results)


class DisclosureRequirementSignature(dspy.Signature):
    """
    Determine disclosure requirements for a trial balance account using ReAct pattern.

    The agent should:
    1. THINK about what disclosure might be required
    2. ACT by searching knowledge base
    3. OBSERVE the search results
    4. DECIDE if disclosure is required
    5. SYNTHESIZE the complete requirement
    """

    account_code: str = dspy.InputField(description="Account code")
    account_name: str = dspy.InputField(description="Account name")
    account_type: str = dspy.InputField(description="Account type (asset/liability/etc)")
    category: str = dspy.InputField(description="Account category")
    balance: float = dspy.InputField(description="Account balance")
    is_material: bool = dspy.InputField(description="Whether account is material")
    jurisdiction: Literal["HK", "SG", "AU"] = dspy.InputField(description="Jurisdiction (HK/SG/AU)")
    accounting_standard: str = dspy.InputField(description="Accounting standard (HKFRS/SME-FRS/etc)")


    reasoning: str = dspy.OutputField(
        description="Detailed explanation with source references"
    )
    requires_disclosure: bool = dspy.OutputField(
        description="True if disclosure is required"
    )
    disclosure_type: str = dspy.OutputField(
        description="Type of disclosure (note/policy/breakdown) or 'none'"
    )
    applicable_standard: str = dspy.OutputField(
        description="Accounting standard requiring disclosure or 'none'"
    )
    disclosure_details: str = dspy.OutputField(
        description="Specific disclosure requirements and content"
    )
    assigned_agent: str = dspy.OutputField(
        description="Agent responsible (revenue/inventory/ppe/etc) or 'none'"
    )


class DSPyDisclosureRequirementAnalyzer:
    """
    DSPy ReAct-based disclosure requirement analyzer.

    Uses ReAct pattern to:
    1. Think about potential disclosure requirements
    2. Search knowledge base for relevant standards
    3. Analyze account against requirements
    4. Determine if disclosure is needed
    5. Assign to appropriate agent
    """

    def __init__(
        self,
        rag_orchestrator: RAGOrchestrator,
        tenant_id: UUID,
        user_id: int,
        lm: Optional[dspy.LM] = None,
        async_max_workers: int = 4,
    ):
        """
        Initialize analyzer with RAG orchestrator and DSPy configuration.

        Args:
            rag_orchestrator: RAG orchestrator for knowledge base access
            tenant_id: Tenant UUID
            user_id: User ID
            lm: Optional DSPy language model
            async_max_workers: Max concurrent LLM API calls (default: 4)
        """
        if lm:
            dspy.configure(lm=lm, async_max_workers=async_max_workers)

        self.rag_orchestrator = rag_orchestrator
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.async_max_workers = async_max_workers

        # Create ReAct module with search tool
        self.search_tool = SearchKnowledgeBaseTool(
            rag_orchestrator=rag_orchestrator,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        self.disclosure_analyzer = dspy.ReAct(
            DisclosureRequirementSignature,
            tools=[self.search_tool],
            max_iters=3,  # Allow up to 3 search iterations
        )

    async def analyze(
        self,
        structured_trial_balance: StructuredTrialBalance,
        jurisdiction: str,
        accounting_standard: str,
    ) -> DisclosureAnalysisResult:
        """
        Analyze all accounts to determine disclosure requirements (async with parallelization).

        Processes material accounts concurrently using DSPy's acall() for significant
        performance improvements (4-10x speedup for 20-50 accounts).

        Args:
            structured_trial_balance: Parsed and classified trial balance
            jurisdiction: Jurisdiction code (HK/SG/AU)
            accounting_standard: Accounting standard (HKFRS/SME-FRS/etc)

        Returns:
            DisclosureAnalysisResult with requirements for all accounts
        """
        disclosure_requirements: List[DisclosureRequirement] = []
        agent_assignments: Dict[str, List[str]] = {}

        # Filter material accounts
        material_accounts = [
            acc for acc in structured_trial_balance.accounts
            if acc.is_material
        ]

        if not material_accounts:
            # No accounts to analyze
            return DisclosureAnalysisResult(
                total_accounts_analyzed=0,
                accounts_requiring_disclosure=0,
                disclosure_requirements=[],
                agent_assignments={},
                metadata={
                    "jurisdiction": jurisdiction,
                    "accounting_standard": accounting_standard,
                    "total_accounts": structured_trial_balance.total_accounts,
                    "total_assets": structured_trial_balance.total_assets,
                },
            )

        # Define async task for analyzing a single account
        async def analyze_account(account: TrialBalanceAccount):
            """Analyze a single account asynchronously."""
            try:
                # Use acall() for async DSPy execution
                result = await self.disclosure_analyzer.acall(
                    account_code=account.code,
                    account_name=account.name,
                    account_type=account.account_type,
                    category=account.category,
                    balance=account.balance,
                    is_material=account.is_material,
                    jurisdiction=jurisdiction,
                    accounting_standard=accounting_standard,
                )
                return account, result

            except Exception as e:
                # Log error but continue processing other accounts
                logger.error(
                    f"Failed to analyze account {account.code} ({account.name}): {e}",
                    exc_info=True,
                )
                # Re-raise to be caught by gather with return_exceptions=True
                raise

        # Create tasks for all material accounts
        tasks = [analyze_account(acc) for acc in material_accounts]

        # Run all analyses concurrently with error resilience
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for result in results:
            if isinstance(result, Exception):
                # Log error and continue (already logged in analyze_account)
                logger.warning(f"Skipping account due to analysis error: {result}")
                continue

            account, analysis = result

            # Create disclosure requirement
            requirement = DisclosureRequirement(
                account_code=account.code,
                account_name=account.name,
                requires_disclosure=analysis.requires_disclosure,
                disclosure_type=analysis.disclosure_type if analysis.requires_disclosure else None,
                applicable_standard=analysis.applicable_standard if analysis.requires_disclosure else None,
                disclosure_details=analysis.disclosure_details,
                assigned_agent=analysis.assigned_agent if analysis.requires_disclosure else None,
                reasoning=analysis.reasoning,
                source_references=[],  # Could extract from reasoning
            )

            disclosure_requirements.append(requirement)

            # Track agent assignments
            if analysis.requires_disclosure and analysis.assigned_agent != "none":
                if analysis.assigned_agent not in agent_assignments:
                    agent_assignments[analysis.assigned_agent] = []
                agent_assignments[analysis.assigned_agent].append(account.code)

        accounts_requiring_disclosure = sum(
            1 for req in disclosure_requirements if req.requires_disclosure
        )

        return DisclosureAnalysisResult(
            total_accounts_analyzed=len(material_accounts),
            accounts_requiring_disclosure=accounts_requiring_disclosure,
            disclosure_requirements=disclosure_requirements,
            agent_assignments=agent_assignments,
            metadata={
                "jurisdiction": jurisdiction,
                "accounting_standard": accounting_standard,
                "total_accounts": structured_trial_balance.total_accounts,
                "total_assets": structured_trial_balance.total_assets,
            },
        )

    async def analyze_single_account(
        self,
        account: TrialBalanceAccount,
        jurisdiction: str,
        accounting_standard: str,
    ) -> DisclosureRequirement:
        """
        Analyze a single account for disclosure requirements (async).

        Args:
            account: Trial balance account
            jurisdiction: Jurisdiction code
            accounting_standard: Accounting standard

        Returns:
            DisclosureRequirement for this account
        """
        result = await self.disclosure_analyzer.acall(
            account_code=account.code,
            account_name=account.name,
            account_type=account.account_type,
            category=account.category,
            balance=account.balance,
            is_material=account.is_material,
            jurisdiction=jurisdiction,
            accounting_standard=accounting_standard,
        )

        return DisclosureRequirement(
            account_code=account.code,
            account_name=account.name,
            requires_disclosure=result.requires_disclosure,
            disclosure_type=result.disclosure_type if result.requires_disclosure else None,
            applicable_standard=result.applicable_standard if result.requires_disclosure else None,
            disclosure_details=result.disclosure_details,
            assigned_agent=result.assigned_agent if result.requires_disclosure else None,
            reasoning=result.reasoning,
            source_references=[],
        )
