"""HK Revenue Recognition Agent - Generates HKFRS 15 compliant revenue disclosures.

This agent uses DSPy to generate revenue recognition disclosures following
Hong Kong Financial Reporting Standards (HKFRS 15) or SME-FRS for small entities.
"""

import logging
from typing import List

import dspy
from pydantic import BaseModel, Field

from genreport.core.orchestration.base_agent import BaseFinancialAgent
from genreport.core.orchestration.agent_models import AgentInput, AgentOutput, Source

logger = logging.getLogger(__name__)


# DSPy Signature for Revenue Recognition
class RevenueDisclosureSignature(dspy.Signature):
    """Generate revenue recognition disclosure following HKFRS 15 or SME-FRS."""

    # Inputs
    trial_balance: str = dspy.InputField(
        desc="Trial balance data in JSON format with revenue accounts"
    )
    accounting_policies: str = dspy.InputField(
        desc="Entity's revenue recognition accounting policies"
    )
    accounting_standard: str = dspy.InputField(
        desc="Accounting standard to follow (HKFRS or SME-FRS)"
    )
    context: str = dspy.InputField(
        desc="Relevant guidance from knowledge base on revenue recognition"
    )

    # Outputs
    disclosure: str = dspy.OutputField(
        desc="Complete revenue recognition disclosure text following the accounting standard"
    )
    confidence: float = dspy.OutputField(
        desc="Confidence score (0-1) in the disclosure quality"
    )
    completeness: float = dspy.OutputField(
        desc="Completeness score (0-1) - how much of required disclosure is covered"
    )
    sources_used: str = dspy.OutputField(
        desc="List of source references used (e.g., 'HKFRS 15, paragraph 31')"
    )


class HKRevenueAgent(BaseFinancialAgent):
    """Hong Kong Revenue Recognition Agent.

    Generates revenue recognition disclosures following HKFRS 15 or SME-FRS
    using DSPy for structured generation with knowledge base retrieval.
    """

    def __init__(self, market_config, retriever, tenant_id, user_id):
        """Initialize HK Revenue Agent.

        Args:
            market_config: HK market configuration
            retriever: SecureKBRetriever for knowledge base
            tenant_id: Tenant ID
            user_id: User ID
        """
        super().__init__(market_config, retriever, tenant_id, user_id)

        # Initialize DSPy module (ChainOfThought for reasoning)
        self.dspy_module = dspy.ChainOfThought(RevenueDisclosureSignature)

    @property
    def agent_name(self) -> str:
        """Agent name."""
        return "revenue"

    @property
    def supported_jurisdictions(self) -> List[str]:
        """Supported jurisdictions."""
        return ["HK"]

    def validate_input(self, agent_input: AgentInput) -> bool:
        """Validate input data.

        Args:
            agent_input: Input data to validate

        Returns:
            True if valid, False otherwise
        """
        # Check trial balance exists (can be empty dict, but not None)
        if agent_input.trial_balance is None:
            return False

        return True

    def process(self, agent_input: AgentInput) -> AgentOutput:
        """Process input and generate revenue disclosure.

        Args:
            agent_input: Input data

        Returns:
            Generated disclosure with sources
        """
        try:
            # Validate tenant
            self.validate_tenant(agent_input)

            # Fetch relevant context from knowledge base
            query = self._build_retrieval_query(agent_input)
            sources = self._fetch_context(query)

            # Build context string for DSPy
            context_text = "\n\n".join([s.snippet for s in sources])

            # Prepare inputs for DSPy
            trial_balance_str = str(agent_input.trial_balance)
            policies_str = str(agent_input.accounting_policies or "No specific policies provided")
            standard = self.market_config.accounting_standard

            # Generate disclosure using DSPy
            result = self.dspy_module(
                trial_balance=trial_balance_str,
                accounting_policies=policies_str,
                accounting_standard=standard,
                context=context_text or "No additional context available",
            )

            # Build output
            output = AgentOutput(
                disclosure_text=result.disclosure,
                sources=sources,
                confidence_score=float(result.confidence) if result.confidence else 0.7,
                completeness_score=float(result.completeness) if result.completeness else 0.7,
                warnings=[],
            )

            return output

        except Exception as e:
            logger.error(f"Error processing revenue disclosure: {e}", exc_info=True)

            # Return minimal output with error warning
            return AgentOutput(
                disclosure_text="Revenue recognition disclosure could not be generated due to an error.",
                sources=[],
                confidence_score=0.0,
                completeness_score=0.0,
                warnings=[f"Error during generation: {str(e)}"],
            )

    def post_process(self, output: AgentOutput) -> AgentOutput:
        """Post-process agent output.

        Adds warnings for low confidence or completeness scores.

        Args:
            output: Raw agent output

        Returns:
            Post-processed output
        """
        # Add warning for low confidence
        if output.confidence_score < 0.7:
            output.warnings.append(
                f"Low confidence score ({output.confidence_score:.2f}). "
                "Manual review recommended."
            )

        # Add warning for low completeness
        if output.completeness_score < 0.7:
            output.warnings.append(
                f"Disclosure may be incomplete ({output.completeness_score:.2f}). "
                "Missing data or additional information may be required."
            )

        return output

    def _build_retrieval_query(self, agent_input: AgentInput) -> str:
        """Build retrieval query for knowledge base.

        Args:
            agent_input: Agent input data

        Returns:
            Query string for retrieval
        """
        # Build query based on accounting standard
        standard = self.market_config.accounting_standard

        if standard == "SME-FRS":
            query = "revenue recognition SME-FRS small and medium entities Hong Kong"
        else:  # HKFRS
            query = "revenue recognition HKFRS 15 performance obligations Hong Kong"

        # Add context from policies if available
        if agent_input.accounting_policies:
            policies = agent_input.accounting_policies
            if isinstance(policies, dict) and "revenue_recognition" in policies:
                query += f" {policies['revenue_recognition']}"

        return query
