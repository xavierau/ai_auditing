"""
Trial Balance Disclosure Orchestrator - Module 3 (Wrapper)

Coordinates the trial balance analysis and disclosure requirement determination.
Integrates Module 1 (TrialBalanceParser) and Module 2 (DisclosureRequirementAnalyzer).

This orchestrator:
1. Extracts raw trial balance from WorksheetAnalysis
2. Parses and classifies accounts using Module 1
3. Analyzes disclosure requirements using Module 2
4. Returns structured disclosure plan for agent execution

Author: GenReport Team
Date: 2025-10-25
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from uuid import UUID
from sqlalchemy.orm import Session
import dspy

from genreport.core.database.models import WorksheetAnalysis, Project
from genreport.core.orchestration.trial_balance_parser import (
    DSPyTrialBalanceParser,
    StructuredTrialBalance,
)
from genreport.core.orchestration.disclosure_requirement_analyzer import (
    DSPyDisclosureRequirementAnalyzer,
    DisclosureAnalysisResult,
    DisclosureRequirement,
)
from genreport.core.orchestration.rag_orchestrator import RAGOrchestrator
from genreport.core.security.audit_logger import AuditLogger


class DisclosurePlan(BaseModel):
    """
    Complete disclosure plan for a project.

    Contains structured trial balance, disclosure requirements, and agent assignments.
    """

    project_id: int
    tenant_id: UUID
    jurisdiction: str
    accounting_standard: str

    structured_trial_balance: StructuredTrialBalance
    disclosure_analysis: DisclosureAnalysisResult

    agent_execution_plan: Dict[str, Any] = Field(
        default_factory=dict,
        description="Execution plan for each agent with assigned accounts"
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Orchestration metadata and statistics"
    )


class TrialBalanceDisclosureOrchestrator:
    """
    Orchestrator for trial balance analysis and disclosure requirement determination.

    Coordinates Module 1 (TrialBalanceParser) and Module 2 (DisclosureRequirementAnalyzer)
    to create a complete disclosure plan for financial agents.

    Architecture:
    1. Extract trial balance from WorksheetAnalysis (database)
    2. Parse and classify accounts (Module 1)
    3. Determine disclosure requirements (Module 2)
    4. Create agent execution plan
    5. Audit log the disclosure plan
    """

    def __init__(
        self,
        db: Session,
        rag_orchestrator: RAGOrchestrator,
        tenant_id: UUID,
        user_id: int,
        lm: Optional[dspy.LM] = None,
    ):
        """
        Initialize orchestrator with database and dependencies.

        Args:
            db: Database session
            rag_orchestrator: RAG orchestrator for knowledge base access
            tenant_id: Tenant UUID
            user_id: User ID
            lm: Optional DSPy language model
        """
        self.db = db
        self.rag_orchestrator = rag_orchestrator
        self.tenant_id = tenant_id
        self.user_id = user_id

        # Initialize Module 1: Trial Balance Parser
        self.parser = DSPyTrialBalanceParser(lm=lm)

        # Initialize Module 2: Disclosure Requirement Analyzer
        self.analyzer = DSPyDisclosureRequirementAnalyzer(
            rag_orchestrator=rag_orchestrator,
            tenant_id=tenant_id,
            user_id=user_id,
            lm=lm,
        )

    async def create_disclosure_plan(
        self,
        project_id: int,
    ) -> DisclosurePlan:
        """
        Create complete disclosure plan for a project (async with parallelization).

        Workflow:
        1. Get project metadata (jurisdiction, accounting standard)
        2. Extract trial balance from WorksheetAnalysis
        3. Parse and classify accounts (Module 1)
        4. Analyze disclosure requirements (Module 2) - ASYNC with parallelization
        5. Create agent execution plan
        6. Audit log the plan

        Args:
            project_id: Project ID

        Returns:
            DisclosurePlan with structured trial balance and disclosure requirements

        Raises:
            ValueError: If project not found or trial balance missing
        """
        # Step 1: Get project metadata
        project = self._get_project(project_id)

        # Step 2: Extract raw trial balance
        raw_trial_balance = self._extract_trial_balance(project_id)

        # Step 3: Parse and classify accounts (Module 1)
        structured_trial_balance = self.parser.parse(
            raw_trial_balance=raw_trial_balance,
            jurisdiction=project.jurisdiction,
            tenant_id=self.tenant_id,
            project_id=project_id,
        )

        # Step 4: Analyze disclosure requirements (Module 2) - ASYNC
        disclosure_analysis = await self.analyzer.analyze(
            structured_trial_balance=structured_trial_balance,
            jurisdiction=project.jurisdiction,
            accounting_standard=project.accounting_standard,
        )

        # Step 5: Create agent execution plan
        agent_execution_plan = self._create_agent_execution_plan(
            disclosure_analysis=disclosure_analysis,
            structured_trial_balance=structured_trial_balance,
        )

        # Step 6: Create disclosure plan
        disclosure_plan = DisclosurePlan(
            project_id=project_id,
            tenant_id=self.tenant_id,
            jurisdiction=project.jurisdiction,
            accounting_standard=project.accounting_standard,
            structured_trial_balance=structured_trial_balance,
            disclosure_analysis=disclosure_analysis,
            agent_execution_plan=agent_execution_plan,
            metadata={
                "total_accounts": structured_trial_balance.total_accounts,
                "material_accounts": sum(1 for acc in structured_trial_balance.accounts if acc.is_material),
                "accounts_requiring_disclosure": disclosure_analysis.accounts_requiring_disclosure,
                "agents_assigned": len(disclosure_analysis.agent_assignments),
            },
        )

        # Step 7: Audit log
        self._audit_log_disclosure_plan(disclosure_plan)

        return disclosure_plan

    def _get_project(self, project_id: int) -> Project:
        """
        Get project from database with tenant isolation.

        Args:
            project_id: Project ID

        Returns:
            Project instance

        Raises:
            ValueError: If project not found or belongs to different tenant
        """
        project = (
            self.db.query(Project)
            .filter(
                Project.id == project_id,
                Project.tenant_id == self.tenant_id,
            )
            .first()
        )

        if not project:
            raise ValueError(
                f"Project {project_id} not found for tenant {self.tenant_id}"
            )

        return project

    def _extract_trial_balance(self, project_id: int) -> List[Dict[str, Any]]:
        """
        Extract trial balance data from WorksheetAnalysis.

        Looks for summary worksheet analysis with trial balance data in analysis_metadata.

        Args:
            project_id: Project ID

        Returns:
            List of trial balance account dictionaries

        Raises:
            ValueError: If trial balance not found
        """
        # Find summary worksheet
        summary_worksheet = (
            self.db.query(WorksheetAnalysis)
            .filter(
                WorksheetAnalysis.project_id == project_id,
                WorksheetAnalysis.tenant_id == self.tenant_id,
                WorksheetAnalysis.is_summary == True,
            )
            .first()
        )

        if not summary_worksheet:
            raise ValueError(
                f"No summary worksheet found for project {project_id}"
            )

        # Extract trial balance from analysis_metadata
        trial_balance_data = summary_worksheet.analysis_metadata.get("trial_balance")

        if not trial_balance_data:
            raise ValueError(
                f"No trial balance data found in summary worksheet for project {project_id}"
            )

        # Convert to expected format
        raw_trial_balance = []
        for account in trial_balance_data:
            raw_trial_balance.append({
                "code": account.get("code", ""),
                "name": account.get("name", ""),
                "balance": float(account.get("balance", 0.0)),
                "debit_credit": account.get("debit_credit", "DR"),
            })

        return raw_trial_balance

    def _create_agent_execution_plan(
        self,
        disclosure_analysis: DisclosureAnalysisResult,
        structured_trial_balance: StructuredTrialBalance,
    ) -> Dict[str, Any]:
        """
        Create execution plan for financial agents.

        Maps each agent to:
        - Assigned account codes
        - Disclosure requirements
        - Account details for context

        Args:
            disclosure_analysis: Disclosure requirements from Module 2
            structured_trial_balance: Structured trial balance from Module 1

        Returns:
            Agent execution plan dictionary
        """
        agent_plan = {}

        # Create account lookup
        account_lookup = {
            acc.code: acc
            for acc in structured_trial_balance.accounts
        }

        # For each agent assignment
        for agent_name, account_codes in disclosure_analysis.agent_assignments.items():
            agent_plan[agent_name] = {
                "account_codes": account_codes,
                "accounts": [
                    {
                        "code": code,
                        "name": account_lookup[code].name,
                        "balance": account_lookup[code].balance,
                        "account_type": account_lookup[code].account_type,
                        "category": account_lookup[code].category,
                    }
                    for code in account_codes
                    if code in account_lookup
                ],
                "disclosure_requirements": [
                    {
                        "account_code": req.account_code,
                        "disclosure_type": req.disclosure_type,
                        "applicable_standard": req.applicable_standard,
                        "disclosure_details": req.disclosure_details,
                    }
                    for req in disclosure_analysis.disclosure_requirements
                    if req.account_code in account_codes and req.requires_disclosure
                ],
            }

        return agent_plan

    def _audit_log_disclosure_plan(self, disclosure_plan: DisclosurePlan):
        """
        Audit log the disclosure plan creation.

        Args:
            disclosure_plan: Created disclosure plan
        """
        AuditLogger.log_event(
            db=self.db,
            event_type="DISCLOSURE_PLAN_CREATED",
            action="CREATE",
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            resource_type="disclosure_plan",
            resource_id=disclosure_plan.project_id,
            ip_address=None,  # Could be passed from request context
            metadata={
                "total_accounts": disclosure_plan.metadata["total_accounts"],
                "accounts_requiring_disclosure": disclosure_plan.metadata["accounts_requiring_disclosure"],
                "agents_assigned": disclosure_plan.metadata["agents_assigned"],
                "jurisdiction": disclosure_plan.jurisdiction,
                "accounting_standard": disclosure_plan.accounting_standard,
            },
        )

    def get_disclosure_requirements_for_agent(
        self,
        disclosure_plan: DisclosurePlan,
        agent_name: str,
    ) -> List[DisclosureRequirement]:
        """
        Get disclosure requirements for a specific agent.

        Args:
            disclosure_plan: Disclosure plan
            agent_name: Agent name (e.g., 'revenue', 'inventory')

        Returns:
            List of disclosure requirements assigned to this agent
        """
        account_codes = disclosure_plan.disclosure_analysis.agent_assignments.get(
            agent_name, []
        )

        return [
            req
            for req in disclosure_plan.disclosure_analysis.disclosure_requirements
            if req.account_code in account_codes and req.requires_disclosure
        ]
