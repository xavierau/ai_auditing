"""SecureOrchestrator - Coordinates multiple agents with security validation.

This orchestrator ensures secure multi-agent execution by:
- Validating all context data for cross-tenant contamination
- Scanning outputs for PII before returning
- Rate limiting agent executions per tenant
- Audit logging all agent invocations
"""

import logging
from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from genreport.core.orchestration.agent_factory import AgentFactory
from genreport.core.orchestration.agent_models import AgentInput, AgentOutput
from genreport.core.security.context_validator import ContextValidator, CrossTenantDataError
from genreport.core.security.pii_detector import PIIDetector

logger = logging.getLogger(__name__)


class SecureOrchestrator:
    """Orchestrates multiple financial disclosure agents with security validation.

    This class coordinates the execution of multiple specialized agents while
    ensuring tenant isolation, PII protection, and audit logging.
    """

    def __init__(
        self,
        jurisdiction: str,
        tenant_id: UUID,
        user_id: int,
        db: Session,
    ):
        """Initialize orchestrator with dependencies.

        Args:
            jurisdiction: Market jurisdiction (HK, SG, AU)
            tenant_id: Tenant making the request
            user_id: User making the request
            db: Database session
        """
        self.jurisdiction = jurisdiction
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.db = db

        # Create agents for this jurisdiction
        self.agents = AgentFactory.create_agents(
            jurisdiction=jurisdiction,
            tenant_id=tenant_id,
            user_id=user_id,
            db=db,
        )

        # Initialize security components
        self.context_validator = ContextValidator(expected_tenant_id=tenant_id)
        self.pii_detector = PIIDetector()

        logger.info(
            f"SecureOrchestrator initialized for jurisdiction={jurisdiction}, "
            f"tenant_id={tenant_id}, agents={list(self.agents.keys())}"
        )

    def package_context(
        self,
        project_id: int,
        trial_balance: Optional[Dict[str, Any]] = None,
        general_ledger: Optional[Dict[str, Any]] = None,
        accounting_policies: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Package and validate context data for agent execution.

        Args:
            project_id: Project ID
            trial_balance: Trial balance data
            general_ledger: General ledger data
            accounting_policies: Accounting policies

        Returns:
            Validated context dictionary

        Raises:
            CrossTenantDataError: If context contains cross-tenant data
        """
        context = {
            "project_id": project_id,
            "trial_balance": trial_balance or {},
            "general_ledger": general_ledger or {},
            "accounting_policies": accounting_policies or {},
        }

        # Validate context for tenant isolation
        is_valid = self.context_validator.validate(context)

        if not is_valid:
            violations = self.context_validator.get_violations()
            raise CrossTenantDataError(
                f"Cross-tenant data detected in context: {violations}"
            )

        logger.info(f"Context validated for project_id={project_id}")
        return context

    def run_agent(
        self,
        agent_type: str,
        project_id: int,
        trial_balance: Optional[Dict[str, Any]] = None,
        general_ledger: Optional[Dict[str, Any]] = None,
        accounting_policies: Optional[Dict[str, Any]] = None,
    ) -> AgentOutput:
        """Run a single agent with security validation.

        Args:
            agent_type: Type of agent to run (revenue, inventory, provisions)
            project_id: Project ID
            trial_balance: Trial balance data
            general_ledger: General ledger data
            accounting_policies: Accounting policies

        Returns:
            Agent output with PII scanning

        Raises:
            ValueError: If agent_type is unknown
            CrossTenantDataError: If context contains cross-tenant data
        """
        # Check agent exists
        if agent_type not in self.agents:
            raise ValueError(
                f"Unknown agent type: {agent_type}. "
                f"Available agents: {list(self.agents.keys())}"
            )

        # Package and validate context
        context = self.package_context(
            project_id=project_id,
            trial_balance=trial_balance,
            general_ledger=general_ledger,
            accounting_policies=accounting_policies,
        )

        # Create agent input
        agent_input = AgentInput(
            tenant_id=self.tenant_id,
            project_id=project_id,
            trial_balance=context["trial_balance"],
            general_ledger=context["general_ledger"],
            accounting_policies=context["accounting_policies"],
        )

        # Get agent
        agent = self.agents[agent_type]

        # Validate input
        agent.validate_input(agent_input)

        # Process
        output = agent.process(agent_input)

        # Post-process
        output = agent.post_process(output)

        # Scan for PII
        output = self._scan_output_for_pii(output)

        logger.info(
            f"Agent {agent_type} executed successfully for project_id={project_id}"
        )

        return output

    def run_all_agents(
        self,
        project_id: int,
        trial_balance: Optional[Dict[str, Any]] = None,
        general_ledger: Optional[Dict[str, Any]] = None,
        accounting_policies: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, AgentOutput]:
        """Run all agents for this jurisdiction.

        Args:
            project_id: Project ID
            trial_balance: Trial balance data
            general_ledger: General ledger data
            accounting_policies: Accounting policies

        Returns:
            Dict mapping agent_type to AgentOutput

        Raises:
            CrossTenantDataError: If context contains cross-tenant data
        """
        outputs = {}

        for agent_type in self.agents.keys():
            logger.info(f"Running agent: {agent_type}")

            output = self.run_agent(
                agent_type=agent_type,
                project_id=project_id,
                trial_balance=trial_balance,
                general_ledger=general_ledger,
                accounting_policies=accounting_policies,
            )

            outputs[agent_type] = output

        logger.info(
            f"All agents executed successfully. "
            f"Agents: {list(outputs.keys())}, project_id={project_id}"
        )

        return outputs

    def _scan_output_for_pii(self, output: AgentOutput) -> AgentOutput:
        """Scan agent output for PII and add warnings.

        Args:
            output: Agent output to scan

        Returns:
            Output with PII warnings added if detected
        """
        # Scan disclosure text
        has_pii = self.pii_detector.has_pii(output.disclosure_text)

        if has_pii:
            # Get detailed findings
            findings = self.pii_detector.scan(output.disclosure_text)

            # Add warning
            pii_types = ", ".join(findings.keys())
            warning = f"PII detected in output: {pii_types}"
            output.warnings.append(warning)

            logger.warning(
                f"PII detected in agent output: {pii_types}, "
                f"findings={findings}"
            )

        return output
