"""Unit tests for strategy selection module.

Tests strategy selection logic based on intent and query characteristics.
"""

import pytest
from uuid import uuid4

from genreport.core.orchestration.strategy_selection import StrategySelector
from genreport.core.orchestration.rag_models import (
    QueryIntent,
    RAGQuery,
    RetrievalStrategy,
)


class TestStrategySelector:
    """Test StrategySelector class."""

    @pytest.fixture
    def selector_with_structure(self):
        """Create selector with document structure available."""
        return StrategySelector(has_document_structure=True)

    @pytest.fixture
    def selector_without_structure(self):
        """Create selector without document structure."""
        return StrategySelector(has_document_structure=False)

    def test_template_intent_selects_structure_aware(self, selector_with_structure):
        """Test that TEMPLATE intent selects STRUCTURE_AWARE strategy."""
        query = RAGQuery(
            query_text="depreciation policy template",
            top_k=5,
            tenant_id=uuid4(),
            user_id=1,
        )

        strategy = selector_with_structure.select_strategy(
            query, QueryIntent.TEMPLATE
        )

        assert strategy == RetrievalStrategy.STRUCTURE_AWARE

    def test_requirement_intent_selects_hybrid(self, selector_with_structure):
        """Test that REQUIREMENT intent selects HYBRID strategy."""
        query = RAGQuery(
            query_text="PPE disclosure requirements",
            top_k=5,
            tenant_id=uuid4(),
            user_id=1,
        )

        strategy = selector_with_structure.select_strategy(
            query, QueryIntent.REQUIREMENT
        )

        assert strategy == RetrievalStrategy.HYBRID

    def test_example_intent_selects_hybrid(self, selector_with_structure):
        """Test that EXAMPLE intent selects HYBRID strategy."""
        query = RAGQuery(
            query_text="revenue recognition example",
            top_k=5,
            tenant_id=uuid4(),
            user_id=1,
        )

        strategy = selector_with_structure.select_strategy(query, QueryIntent.EXAMPLE)

        assert strategy == RetrievalStrategy.HYBRID

    def test_definition_intent_selects_structure_aware(self, selector_with_structure):
        """Test that DEFINITION intent selects STRUCTURE_AWARE strategy."""
        query = RAGQuery(
            query_text="what is fair value",
            top_k=5,
            tenant_id=uuid4(),
            user_id=1,
        )

        strategy = selector_with_structure.select_strategy(
            query, QueryIntent.DEFINITION
        )

        assert strategy == RetrievalStrategy.STRUCTURE_AWARE

    def test_short_general_query_selects_semantic(self, selector_with_structure):
        """Test that short GENERAL queries select SEMANTIC strategy."""
        query = RAGQuery(
            query_text="revenue recognition",  # 2 words (≤5)
            top_k=5,
            tenant_id=uuid4(),
            user_id=1,
        )

        strategy = selector_with_structure.select_strategy(query, QueryIntent.GENERAL)

        assert strategy == RetrievalStrategy.SEMANTIC

    def test_long_general_query_selects_hybrid(self, selector_with_structure):
        """Test that long GENERAL queries select HYBRID strategy."""
        query = RAGQuery(
            query_text="revenue recognition policy for long term contracts",  # 7 words (>5)
            top_k=5,
            tenant_id=uuid4(),
            user_id=1,
        )

        strategy = selector_with_structure.select_strategy(query, QueryIntent.GENERAL)

        assert strategy == RetrievalStrategy.HYBRID

    def test_no_structure_fallback_to_semantic(self, selector_without_structure):
        """Test that all queries fall back to SEMANTIC when no structure available."""
        # TEMPLATE intent
        query_template = RAGQuery(
            query_text="revenue template",
            top_k=5,
            tenant_id=uuid4(),
            user_id=1,
        )
        assert (
            selector_without_structure.select_strategy(query_template, QueryIntent.TEMPLATE)
            == RetrievalStrategy.SEMANTIC
        )

        # REQUIREMENT intent
        query_requirement = RAGQuery(
            query_text="PPE requirements",
            top_k=5,
            tenant_id=uuid4(),
            user_id=1,
        )
        assert (
            selector_without_structure.select_strategy(
                query_requirement, QueryIntent.REQUIREMENT
            )
            == RetrievalStrategy.SEMANTIC
        )

        # GENERAL intent
        query_general = RAGQuery(
            query_text="inventory",
            top_k=5,
            tenant_id=uuid4(),
            user_id=1,
        )
        assert (
            selector_without_structure.select_strategy(query_general, QueryIntent.GENERAL)
            == RetrievalStrategy.SEMANTIC
        )

    def test_explicit_strategy_override(self, selector_with_structure):
        """Test that explicit strategy in filters overrides auto-selection."""
        query = RAGQuery(
            query_text="revenue template",
            top_k=5,
            filters={"strategy": "semantic"},  # Explicit override
            tenant_id=uuid4(),
            user_id=1,
        )

        strategy = selector_with_structure.select_strategy(
            query, QueryIntent.TEMPLATE
        )

        # Should use explicit strategy, not auto-selected STRUCTURE_AWARE
        assert strategy == RetrievalStrategy.SEMANTIC

    def test_invalid_explicit_strategy_uses_auto(self, selector_with_structure):
        """Test that invalid explicit strategy falls back to auto-selection."""
        query = RAGQuery(
            query_text="revenue template",
            top_k=5,
            filters={"strategy": "invalid_strategy"},  # Invalid
            tenant_id=uuid4(),
            user_id=1,
        )

        strategy = selector_with_structure.select_strategy(
            query, QueryIntent.TEMPLATE
        )

        # Should fall back to auto-selection (STRUCTURE_AWARE for template)
        assert strategy == RetrievalStrategy.STRUCTURE_AWARE

    def test_explain_selection_template(self, selector_with_structure):
        """Test strategy explanation for template queries."""
        query = RAGQuery(
            query_text="depreciation policy",
            top_k=5,
            tenant_id=uuid4(),
            user_id=1,
        )

        explanation = selector_with_structure.explain_selection(
            query, QueryIntent.TEMPLATE, RetrievalStrategy.STRUCTURE_AWARE
        )

        assert "template" in explanation.lower()
        assert "structure" in explanation.lower()

    def test_explain_selection_requirement(self, selector_with_structure):
        """Test strategy explanation for requirement queries."""
        query = RAGQuery(
            query_text="PPE disclosures",
            top_k=5,
            tenant_id=uuid4(),
            user_id=1,
        )

        explanation = selector_with_structure.explain_selection(
            query, QueryIntent.REQUIREMENT, RetrievalStrategy.HYBRID
        )

        assert "requirement" in explanation.lower()
        assert "hybrid" in explanation.lower()

    def test_explain_selection_short_general(self, selector_with_structure):
        """Test strategy explanation for short general queries."""
        query = RAGQuery(
            query_text="revenue",  # 1 word
            top_k=5,
            tenant_id=uuid4(),
            user_id=1,
        )

        explanation = selector_with_structure.explain_selection(
            query, QueryIntent.GENERAL, RetrievalStrategy.SEMANTIC
        )

        assert "short" in explanation.lower() or "general" in explanation.lower()
        assert "semantic" in explanation.lower()

    def test_explain_selection_no_structure(self, selector_without_structure):
        """Test strategy explanation when structure not available."""
        query = RAGQuery(
            query_text="revenue template",
            top_k=5,
            tenant_id=uuid4(),
            user_id=1,
        )

        explanation = selector_without_structure.explain_selection(
            query, QueryIntent.TEMPLATE, RetrievalStrategy.SEMANTIC
        )

        assert "structure not available" in explanation.lower() or "fallback" in explanation.lower()

    def test_get_alternative_strategies(self, selector_with_structure):
        """Test getting alternative strategies."""
        query = RAGQuery(
            query_text="revenue",
            top_k=5,
            tenant_id=uuid4(),
            user_id=1,
        )

        alternatives = selector_with_structure.get_alternative_strategies(
            query, QueryIntent.GENERAL, RetrievalStrategy.SEMANTIC
        )

        # Should have alternatives
        assert len(alternatives) > 0

        # Should not include the selected strategy
        assert not any("SEMANTIC:" in alt for alt in alternatives)

        # Should include other strategies
        assert any("STRUCTURE_AWARE:" in alt for alt in alternatives)
        assert any("HYBRID:" in alt for alt in alternatives)

    def test_get_alternative_strategies_no_structure(self, selector_without_structure):
        """Test alternatives when structure not available."""
        query = RAGQuery(
            query_text="revenue",
            top_k=5,
            tenant_id=uuid4(),
            user_id=1,
        )

        alternatives = selector_without_structure.get_alternative_strategies(
            query, QueryIntent.GENERAL, RetrievalStrategy.SEMANTIC
        )

        # Should only have semantic alternative (no structure-aware or hybrid)
        assert len(alternatives) == 0  # No alternatives when structure unavailable

    def test_estimate_performance_semantic(self, selector_with_structure):
        """Test performance estimation for semantic strategy."""
        perf = selector_with_structure.estimate_performance(RetrievalStrategy.SEMANTIC)

        assert "fast" in perf["latency"].lower()
        assert "500ms" in perf["latency"].lower()

    def test_estimate_performance_structure_aware(self, selector_with_structure):
        """Test performance estimation for structure-aware strategy."""
        perf = selector_with_structure.estimate_performance(
            RetrievalStrategy.STRUCTURE_AWARE
        )

        assert "medium" in perf["latency"].lower()

    def test_estimate_performance_hybrid(self, selector_with_structure):
        """Test performance estimation for hybrid strategy."""
        perf = selector_with_structure.estimate_performance(RetrievalStrategy.HYBRID)

        assert "medium" in perf["latency"].lower() or "slow" in perf["latency"].lower()
        assert "best" in perf["accuracy"].lower()
