"""HK Inventory Agent - Generates HKAS 2 compliant inventory disclosures.

This agent uses DSPy to generate inventory disclosures following
Hong Kong Accounting Standard 2 (HKAS 2) - Inventories.
"""

import logging
from typing import List

import dspy

from genreport.core.orchestration.base_agent import BaseFinancialAgent
from genreport.core.orchestration.agent_models import AgentInput, AgentOutput

logger = logging.getLogger(__name__)


class InventoryDisclosureSignature(dspy.Signature):
    """Generate inventory disclosure following HKAS 2."""

    trial_balance: str = dspy.InputField(desc="Trial balance with inventory data")
    accounting_policies: str = dspy.InputField(desc="Inventory valuation policies")
    accounting_standard: str = dspy.InputField(desc="Accounting standard (HKFRS or SME-FRS)")
    context: str = dspy.InputField(desc="KB guidance on inventory accounting")

    disclosure: str = dspy.OutputField(desc="Inventory disclosure text")
    confidence: float = dspy.OutputField(desc="Confidence score (0-1)")
    completeness: float = dspy.OutputField(desc="Completeness score (0-1)")
    sources_used: str = dspy.OutputField(desc="Source references")


class HKInventoryAgent(BaseFinancialAgent):
    """Hong Kong Inventory Agent."""

    def __init__(self, market_config, retriever, tenant_id, user_id, job_id=None):
        super().__init__(market_config, retriever, tenant_id, user_id, job_id)
        self.dspy_module = dspy.ChainOfThought(InventoryDisclosureSignature)

    @property
    def agent_name(self) -> str:
        return "inventory"

    @property
    def supported_jurisdictions(self) -> List[str]:
        return ["HK"]

    def validate_input(self, agent_input: AgentInput) -> bool:
        return agent_input.trial_balance is not None

    def process(self, agent_input: AgentInput) -> AgentOutput:
        try:
            self.validate_tenant(agent_input)
            sources = self._fetch_context("inventory valuation HKAS 2 Hong Kong")
            context_text = "\n\n".join([s.snippet for s in sources])

            result = self.dspy_module(
                trial_balance=str(agent_input.trial_balance),
                accounting_policies=str(agent_input.accounting_policies or "No specific policies"),
                accounting_standard=self.market_config.accounting_standard,
                context=context_text or "No additional context",
            )

            return AgentOutput(
                disclosure_text=result.disclosure,
                sources=sources,
                confidence_score=float(result.confidence) if result.confidence else 0.7,
                completeness_score=float(result.completeness) if result.completeness else 0.7,
                warnings=[],
            )
        except Exception as e:
            logger.error(f"Error in inventory agent: {e}", exc_info=True)
            return AgentOutput(
                disclosure_text="Inventory disclosure could not be generated.",
                sources=[],
                confidence_score=0.0,
                completeness_score=0.0,
                warnings=[f"Error: {str(e)}"],
            )

    def post_process(self, output: AgentOutput) -> AgentOutput:
        if output.confidence_score < 0.7:
            output.warnings.append(f"Low confidence ({output.confidence_score:.2f})")
        if output.completeness_score < 0.7:
            output.warnings.append(f"Incomplete disclosure ({output.completeness_score:.2f})")
        return output
