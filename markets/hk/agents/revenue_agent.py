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
    template: str = dspy.InputField(
        desc="Disclosure template with formatting requirements and structure guidance from standards"
    )
    requirements: str = dspy.InputField(
        desc="Mandatory and optional disclosure requirements from accounting standards with source references"
    )
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
        desc="Additional relevant guidance from knowledge base on revenue recognition"
    )

    # Outputs
    disclosure: str = dspy.OutputField(
        desc="Complete revenue recognition disclosure text following the template and requirements"
    )
    confidence: float = dspy.OutputField(
        desc="Confidence score (0-1) in the disclosure quality"
    )
    completeness: float = dspy.OutputField(
        desc="Completeness score (0-1) - how much of required disclosure is covered"
    )
    sources_used: str = dspy.OutputField(
        desc="List of source references used (e.g., 'HKFRS 15, paragraph 31, p.58')"
    )


class HKRevenueAgent(BaseFinancialAgent):
    """Hong Kong Revenue Recognition Agent.

    Generates revenue recognition disclosures following HKFRS 15 or SME-FRS
    using DSPy for structured generation with knowledge base retrieval.
    """

    def __init__(self, market_config, retriever, tenant_id, user_id, job_id=None):
        """Initialize HK Revenue Agent.

        Args:
            market_config: HK market configuration
            retriever: RAGOrchestrator for knowledge base
            tenant_id: Tenant ID
            user_id: User ID
            job_id: Optional job ID for caching
        """
        super().__init__(market_config, retriever, tenant_id, user_id, job_id)

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
        """Process input and generate revenue disclosure using agentic RAG workflow.

        Workflow:
        1. Fetch template using AgenticRAG (autonomous reasoning)
        2. Fetch requirements using AgenticRAG (autonomous reasoning)
        3. Fetch additional context using AgenticRAG (if needed)
        4. Generate disclosure using DSPy with template + requirements + context
        5. Track all sources for audit trail

        Args:
            agent_input: Input data

        Returns:
            Generated disclosure with sources from all agentic searches
        """
        try:
            # Validate tenant
            self.validate_tenant(agent_input)

            # Determine disclosure type based on standard
            standard = self.market_config.accounting_standard
            disclosure_type = self._get_disclosure_type(standard)

            # Step 1: Fetch template using AgenticRAG
            logger.info(f"[{self.agent_name}] Fetching template for {disclosure_type}")
            template_result = self._fetch_template(disclosure_type)
            template_text = template_result.answer

            # Step 2: Fetch requirements using AgenticRAG
            logger.info(f"[{self.agent_name}] Fetching requirements for {disclosure_type}")
            requirements_result = self._fetch_requirements(disclosure_type)
            requirements_text = requirements_result.answer

            # Step 3: Fetch additional context using AgenticRAG
            query = self._build_retrieval_query(agent_input)
            logger.info(f"[{self.agent_name}] Fetching additional context")
            sources = self._fetch_context(query, use_agentic=True)

            # Build context string for DSPy
            context_text = "\n\n".join([s.snippet for s in sources])

            # Prepare inputs for DSPy
            trial_balance_str = str(agent_input.trial_balance)
            policies_str = str(agent_input.accounting_policies or "No specific policies provided")

            # Generate disclosure using DSPy with template + requirements
            logger.info(f"[{self.agent_name}] Generating disclosure with DSPy")
            result = self.dspy_module(
                template=template_text,
                requirements=requirements_text,
                trial_balance=trial_balance_str,
                accounting_policies=policies_str,
                accounting_standard=standard,
                context=context_text or "No additional context available",
            )

            # Combine all sources from agentic searches
            all_sources = self._combine_agentic_sources(
                template_result, requirements_result, sources
            )

            # Build output
            output = AgentOutput(
                disclosure_text=result.disclosure,
                sources=all_sources,
                confidence_score=float(result.confidence) if result.confidence else 0.7,
                completeness_score=float(result.completeness) if result.completeness else 0.7,
                warnings=[],
            )

            logger.info(
                f"[{self.agent_name}] Generation complete: "
                f"{len(all_sources)} sources, "
                f"confidence={output.confidence_score:.2f}, "
                f"completeness={output.completeness_score:.2f}"
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

    def _get_disclosure_type(self, standard: str) -> str:
        """Get disclosure type description based on accounting standard.

        Args:
            standard: Accounting standard (HKFRS or SME-FRS)

        Returns:
            Disclosure type description
        """
        if standard == "SME-FRS":
            return "SME-FRS Section 23 Revenue disclosure for small and medium entities"
        else:  # HKFRS
            return "HKFRS 15 Revenue from Contracts with Customers disclosure"

    def _combine_agentic_sources(
        self,
        template_result,
        requirements_result,
        context_sources: List[Source],
    ) -> List[Source]:
        """Combine sources from multiple agentic RAG searches.

        Args:
            template_result: AgenticRAGResult from template fetch
            requirements_result: AgenticRAGResult from requirements fetch
            context_sources: Source objects from context fetch

        Returns:
            Combined list of Source objects with proper attribution
        """
        from genreport.core.orchestration.agentic_rag_agent import AgenticRAGResult

        all_sources = []

        # Add sources from template result
        for ref in template_result.references:
            source = Source(
                document_id=0,  # Metadata from agentic search
                chunk_id=ref.ref_id,
                relevance_score=ref.relevance_score,
                snippet=ref.content_preview,
                source_reference=ref.source,
            )
            all_sources.append(source)

        # Add sources from requirements result
        for ref in requirements_result.references:
            source = Source(
                document_id=0,  # Metadata from agentic search
                chunk_id=ref.ref_id,
                relevance_score=ref.relevance_score,
                snippet=ref.content_preview,
                source_reference=ref.source,
            )
            all_sources.append(source)

        # Add context sources (already Source objects)
        all_sources.extend(context_sources)

        # Deduplicate by source_reference
        seen = set()
        unique_sources = []
        for source in all_sources:
            key = source.source_reference or f"{source.document_id}:{source.chunk_id}"
            if key not in seen:
                seen.add(key)
                unique_sources.append(source)

        logger.info(
            f"[{self.agent_name}] Combined sources: "
            f"{len(template_result.references)} template + "
            f"{len(requirements_result.references)} requirements + "
            f"{len(context_sources)} context = "
            f"{len(unique_sources)} unique sources"
        )

        return unique_sources
