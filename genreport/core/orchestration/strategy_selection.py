"""Strategy selection for RAG orchestrator.

This module provides intelligent strategy selection based on:
- Query intent (template, requirement, example, etc.)
- Query complexity (short vs long, simple vs complex)
- Available resources (document structure availability)

Strategy Selection Logic:
- TEMPLATE intent + structure available → STRUCTURE_AWARE
- REQUIREMENT intent → HYBRID (semantic + structure)
- GENERAL intent + short query → SEMANTIC (fast)
- Complex query + structure available → HYBRID
- No structure available → SEMANTIC (fallback)
"""

from genreport.core.orchestration.rag_models import (
    QueryIntent,
    RAGQuery,
    RetrievalStrategy,
)


class StrategySelector:
    """Selects optimal retrieval strategy based on query characteristics.

    Decision logic balances accuracy vs performance:
    - SEMANTIC: Fast vector similarity (good for simple queries)
    - STRUCTURE_AWARE: Document navigation (best for templates)
    - HYBRID: Combined approach (best for requirements)

    Attributes:
        has_structure: Whether document structure is available
    """

    def __init__(self, has_document_structure: bool):
        """Initialize strategy selector.

        Args:
            has_document_structure: Whether document structure is available
        """
        self.has_structure = has_document_structure

    def select_strategy(
        self,
        query: RAGQuery,
        intent: QueryIntent,
    ) -> RetrievalStrategy:
        """Select optimal retrieval strategy.

        Decision tree:
        1. If strategy explicitly specified in filters → use it
        2. If no document structure → fallback to SEMANTIC
        3. If TEMPLATE intent → STRUCTURE_AWARE (navigate to appendices)
        4. If REQUIREMENT intent → HYBRID (structure + semantic ranking)
        5. If GENERAL intent:
           - Short query (≤5 words) → SEMANTIC (fast)
           - Complex query (>5 words) → HYBRID (comprehensive)
        6. Default → HYBRID (balanced)

        Args:
            query: RAG query with filters
            intent: Detected query intent

        Returns:
            Selected retrieval strategy

        Examples:
            >>> selector = StrategySelector(has_document_structure=True)
            >>> query = RAGQuery(query_text="PPE template", ...)
            >>> selector.select_strategy(query, QueryIntent.TEMPLATE)
            RetrievalStrategy.STRUCTURE_AWARE
        """
        # 1. Check for explicit strategy override in filters
        if query.filters and "strategy" in query.filters:
            strategy_value = query.filters["strategy"]
            # Validate strategy value
            try:
                return RetrievalStrategy(strategy_value)
            except ValueError:
                # Invalid strategy, continue with auto-selection
                pass

        # 2. Fallback to semantic if no structure available
        if not self.has_structure:
            return RetrievalStrategy.SEMANTIC

        # 3. Intent-based strategy selection
        if intent == QueryIntent.TEMPLATE:
            # Templates benefit most from structure navigation
            # Structure-aware can navigate to appendices/illustrative examples
            return RetrievalStrategy.STRUCTURE_AWARE

        elif intent == QueryIntent.REQUIREMENT:
            # Requirements need both structure and semantic relevance
            # Structure helps find requirement sections
            # Semantic ranking ensures most relevant requirements surface
            return RetrievalStrategy.HYBRID

        elif intent == QueryIntent.EXAMPLE:
            # Examples can be in various locations
            # Hybrid gives best coverage
            return RetrievalStrategy.HYBRID

        elif intent == QueryIntent.DEFINITION:
            # Definitions are usually in specific sections
            # Structure-aware can navigate to definitions section
            return RetrievalStrategy.STRUCTURE_AWARE

        elif intent == QueryIntent.GENERAL:
            # 4. Complexity-based selection for general queries
            word_count = len(query.query_text.split())

            if word_count <= 5:
                # Short general query: optimize for speed
                return RetrievalStrategy.SEMANTIC
            else:
                # Complex general query: optimize for coverage
                return RetrievalStrategy.HYBRID

        # 5. Default: hybrid for balanced performance
        return RetrievalStrategy.HYBRID

    def explain_selection(
        self,
        query: RAGQuery,
        intent: QueryIntent,
        selected_strategy: RetrievalStrategy,
    ) -> str:
        """Generate human-readable explanation of strategy selection.

        Useful for debugging and transparency.

        Args:
            query: RAG query
            intent: Detected intent
            selected_strategy: Selected strategy

        Returns:
            Explanation string with reasoning

        Examples:
            >>> selector = StrategySelector(has_document_structure=True)
            >>> query = RAGQuery(query_text="revenue template", ...)
            >>> explanation = selector.explain_selection(
            ...     query, QueryIntent.TEMPLATE, RetrievalStrategy.STRUCTURE_AWARE
            ... )
            >>> "Query seeks template" in explanation
            True
        """
        reasons = []

        # Explain intent detection
        if intent == QueryIntent.TEMPLATE:
            reasons.append("Query seeks template/policy wording")
            if selected_strategy == RetrievalStrategy.STRUCTURE_AWARE:
                reasons.append(
                    "Structure-aware navigation prioritizes appendices and illustrative sections"
                )

        elif intent == QueryIntent.REQUIREMENT:
            reasons.append("Query seeks disclosure requirements")
            if selected_strategy == RetrievalStrategy.HYBRID:
                reasons.append(
                    "Hybrid combines structure navigation with semantic ranking for comprehensive coverage"
                )

        elif intent == QueryIntent.EXAMPLE:
            reasons.append("Query seeks illustrative examples")
            if selected_strategy == RetrievalStrategy.HYBRID:
                reasons.append("Hybrid search covers examples in multiple locations")

        elif intent == QueryIntent.DEFINITION:
            reasons.append("Query seeks term definition")
            if selected_strategy == RetrievalStrategy.STRUCTURE_AWARE:
                reasons.append("Structure-aware navigates to definitions section")

        elif intent == QueryIntent.GENERAL:
            word_count = len(query.query_text.split())
            if selected_strategy == RetrievalStrategy.SEMANTIC:
                reasons.append(f"Short general query ({word_count} words)")
                reasons.append("Pure semantic search optimizes for speed")
            else:
                reasons.append(f"Complex general query ({word_count} words)")
                reasons.append("Hybrid approach ensures comprehensive coverage")

        # Explain structure availability
        if not self.has_structure:
            reasons.append("Document structure not available (fallback to semantic)")

        # Explain explicit overrides
        if query.filters and "strategy" in query.filters:
            reasons.append(
                f"Strategy explicitly specified: {query.filters['strategy']}"
            )

        # Combine reasons
        if reasons:
            return " | ".join(reasons)
        else:
            return "Default strategy selected based on query characteristics"

    def get_alternative_strategies(
        self,
        query: RAGQuery,
        intent: QueryIntent,
        selected_strategy: RetrievalStrategy,
    ) -> list[str]:
        """Get alternative strategies that could be used.

        Useful for debugging and A/B testing.

        Args:
            query: RAG query
            intent: Detected intent
            selected_strategy: Selected strategy

        Returns:
            List of alternative strategy names with brief descriptions

        Examples:
            >>> selector = StrategySelector(has_document_structure=True)
            >>> query = RAGQuery(query_text="revenue", ...)
            >>> alternatives = selector.get_alternative_strategies(
            ...     query, QueryIntent.GENERAL, RetrievalStrategy.SEMANTIC
            ... )
            >>> len(alternatives) > 0
            True
        """
        alternatives = []

        # List all strategies except the selected one
        all_strategies = [
            RetrievalStrategy.SEMANTIC,
            RetrievalStrategy.STRUCTURE_AWARE,
            RetrievalStrategy.HYBRID,
        ]

        for strategy in all_strategies:
            if strategy == selected_strategy:
                continue

            if strategy == RetrievalStrategy.SEMANTIC:
                alternatives.append(
                    "SEMANTIC: Fast vector similarity search (good for simple queries)"
                )
            elif strategy == RetrievalStrategy.STRUCTURE_AWARE:
                if self.has_structure:
                    alternatives.append(
                        "STRUCTURE_AWARE: Document structure navigation (best for templates)"
                    )
            elif strategy == RetrievalStrategy.HYBRID:
                if self.has_structure:
                    alternatives.append(
                        "HYBRID: Combined semantic + structure (balanced approach)"
                    )

        return alternatives

    def estimate_performance(self, strategy: RetrievalStrategy) -> dict[str, str]:
        """Estimate performance characteristics of a strategy.

        Provides rough estimates for latency and accuracy trade-offs.

        Args:
            strategy: Retrieval strategy to estimate

        Returns:
            Dict with latency and accuracy estimates

        Examples:
            >>> selector = StrategySelector(has_document_structure=True)
            >>> perf = selector.estimate_performance(RetrievalStrategy.SEMANTIC)
            >>> perf["latency"]
            'Fast (<500ms)'
        """
        if strategy == RetrievalStrategy.SEMANTIC:
            return {
                "latency": "Fast (<500ms)",
                "accuracy": "Good for simple queries",
                "coverage": "Broad semantic similarity",
            }
        elif strategy == RetrievalStrategy.STRUCTURE_AWARE:
            return {
                "latency": "Medium (500ms-1s)",
                "accuracy": "Excellent for structured content",
                "coverage": "Focused on relevant sections",
            }
        elif strategy == RetrievalStrategy.HYBRID:
            return {
                "latency": "Medium-Slow (750ms-1.5s)",
                "accuracy": "Best overall",
                "coverage": "Comprehensive (structure + semantic)",
            }
        else:
            return {
                "latency": "Unknown",
                "accuracy": "Unknown",
                "coverage": "Unknown",
            }
