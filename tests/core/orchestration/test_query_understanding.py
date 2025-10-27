"""Unit tests for query understanding module.

Tests intent detection, query expansion, and keyword extraction.
"""

import pytest

from genreport.core.orchestration.query_understanding import QueryUnderstanding
from genreport.core.orchestration.rag_models import QueryIntent


class TestQueryUnderstanding:
    """Test QueryUnderstanding class."""

    @pytest.fixture
    def query_understanding(self):
        """Create QueryUnderstanding instance."""
        return QueryUnderstanding()

    def test_detect_intent_template(self, query_understanding):
        """Test template intent detection."""
        # Explicit "template" keyword
        assert (
            query_understanding.detect_intent("revenue recognition template")
            == QueryIntent.TEMPLATE
        )

        # "policy" keyword
        assert (
            query_understanding.detect_intent("depreciation accounting policy")
            == QueryIntent.TEMPLATE
        )

        # "wording" keyword
        assert (
            query_understanding.detect_intent("revenue recognition wording")
            == QueryIntent.TEMPLATE
        )

        # "boilerplate" keyword
        assert (
            query_understanding.detect_intent("PPE boilerplate disclosure")
            == QueryIntent.TEMPLATE
        )

    def test_detect_intent_requirement(self, query_understanding):
        """Test requirement intent detection."""
        # "required" keyword
        assert (
            query_understanding.detect_intent("what disclosures are required for PPE")
            == QueryIntent.REQUIREMENT
        )

        # "mandatory" keyword
        assert (
            query_understanding.detect_intent("mandatory revenue disclosures")
            == QueryIntent.REQUIREMENT
        )

        # "must disclose" phrase
        assert (
            query_understanding.detect_intent("what must be disclosed for leases")
            == QueryIntent.REQUIREMENT
        )

        # "disclosure requirements" phrase
        assert (
            query_understanding.detect_intent("inventory disclosure requirements")
            == QueryIntent.REQUIREMENT
        )

    def test_detect_intent_example(self, query_understanding):
        """Test example intent detection."""
        # "example" keyword
        assert (
            query_understanding.detect_intent("revenue recognition example")
            == QueryIntent.EXAMPLE
        )

        # "illustrative" keyword
        assert (
            query_understanding.detect_intent("illustrative lease disclosure")
            == QueryIntent.EXAMPLE
        )

        # "sample" keyword
        assert (
            query_understanding.detect_intent("sample PPE note")
            == QueryIntent.EXAMPLE
        )

    def test_detect_intent_definition(self, query_understanding):
        """Test definition intent detection."""
        # "what is" phrase
        assert (
            query_understanding.detect_intent("what is fair value")
            == QueryIntent.DEFINITION
        )

        # "define" keyword
        assert (
            query_understanding.detect_intent("define deferred revenue")
            == QueryIntent.DEFINITION
        )

        # "meaning of" phrase
        assert (
            query_understanding.detect_intent("meaning of recoverable amount")
            == QueryIntent.DEFINITION
        )

    def test_detect_intent_general(self, query_understanding):
        """Test general intent detection (default fallback)."""
        # No specific keywords
        assert (
            query_understanding.detect_intent("revenue recognition")
            == QueryIntent.GENERAL
        )

        # Accounting term without intent keywords
        assert (
            query_understanding.detect_intent("property plant equipment")
            == QueryIntent.GENERAL
        )

        # Short query
        assert query_understanding.detect_intent("inventory") == QueryIntent.GENERAL

    def test_detect_intent_case_insensitive(self, query_understanding):
        """Test that intent detection is case-insensitive."""
        # Uppercase
        assert (
            query_understanding.detect_intent("REVENUE TEMPLATE")
            == QueryIntent.TEMPLATE
        )

        # Mixed case
        assert (
            query_understanding.detect_intent("What Is Fair Value")
            == QueryIntent.DEFINITION
        )

    def test_expand_query_template(self, query_understanding):
        """Test query expansion for template intent."""
        expansions = query_understanding.expand_query(
            "revenue recognition", QueryIntent.TEMPLATE
        )

        # Should include original query
        assert "revenue recognition" in expansions

        # Should include template-specific expansions
        assert any("accounting policy" in exp for exp in expansions)
        assert any("illustrative wording" in exp for exp in expansions)

    def test_expand_query_requirement(self, query_understanding):
        """Test query expansion for requirement intent."""
        expansions = query_understanding.expand_query("PPE", QueryIntent.REQUIREMENT)

        # Should include original
        assert "PPE" in expansions

        # Should include requirement-specific expansions
        assert any("disclosure requirements" in exp for exp in expansions)
        assert any("mandatory disclosures" in exp for exp in expansions)

    def test_expand_query_example(self, query_understanding):
        """Test query expansion for example intent."""
        expansions = query_understanding.expand_query("leases", QueryIntent.EXAMPLE)

        # Should include original
        assert "leases" in expansions

        # Should include example-specific expansions
        assert any("example" in exp for exp in expansions)
        assert any("illustration" in exp for exp in expansions)

    def test_expand_query_general_no_expansion(self, query_understanding):
        """Test that general queries are not expanded."""
        expansions = query_understanding.expand_query("revenue", QueryIntent.GENERAL)

        # Should only include original query
        assert expansions == ["revenue"]

    def test_expand_query_definition_no_expansion(self, query_understanding):
        """Test that definition queries are not expanded."""
        expansions = query_understanding.expand_query(
            "fair value", QueryIntent.DEFINITION
        )

        # Should only include original query
        assert expansions == ["fair value"]

    def test_extract_keywords(self, query_understanding):
        """Test keyword extraction."""
        keywords = query_understanding.extract_keywords(
            "What are the disclosure requirements for PPE?"
        )

        # Should extract meaningful terms
        assert "disclosure" in keywords
        assert "requirements" in keywords
        assert "ppe" in keywords

        # Should remove stopwords
        assert "what" not in keywords
        assert "are" not in keywords
        assert "the" not in keywords
        assert "for" not in keywords

    def test_extract_keywords_removes_short_words(self, query_understanding):
        """Test that short words (<3 chars) are removed."""
        keywords = query_understanding.extract_keywords("I am PPE is OK")

        # Should remove short words
        assert "i" not in keywords  # 1 char
        assert "am" not in keywords  # 2 chars
        assert "is" not in keywords  # 2 chars
        assert "ok" not in keywords  # 2 chars

        # Should keep longer words (that aren't stopwords)
        assert "ppe" in keywords  # 3 chars

    def test_extract_keywords_deduplication(self, query_understanding):
        """Test that keywords are deduplicated."""
        keywords = query_understanding.extract_keywords(
            "revenue revenue recognition revenue"
        )

        # Should deduplicate
        assert keywords.count("revenue") == 1
        assert keywords.count("recognition") == 1

    def test_extract_keywords_preserves_order(self, query_understanding):
        """Test that first occurrence order is preserved."""
        keywords = query_understanding.extract_keywords(
            "revenue inventory depreciation"
        )

        # Should preserve order
        assert keywords == ["revenue", "inventory", "depreciation"]

    def test_is_accounting_term(self, query_understanding):
        """Test accounting term identification."""
        # Known accounting terms
        assert query_understanding.is_accounting_term("revenue") is True
        assert query_understanding.is_accounting_term("depreciation") is True
        assert query_understanding.is_accounting_term("inventory") is True
        assert query_understanding.is_accounting_term("goodwill") is True
        assert query_understanding.is_accounting_term("PPE") is True

        # Case-insensitive
        assert query_understanding.is_accounting_term("REVENUE") is True
        assert query_understanding.is_accounting_term("Revenue") is True

        # Non-accounting terms
        assert query_understanding.is_accounting_term("hello") is False
        assert query_understanding.is_accounting_term("world") is False
        assert query_understanding.is_accounting_term("test") is False

    def test_extract_keywords_empty_query(self, query_understanding):
        """Test keyword extraction from empty query."""
        keywords = query_understanding.extract_keywords("")
        assert keywords == []

    def test_extract_keywords_only_stopwords(self, query_understanding):
        """Test keyword extraction from query with only stopwords."""
        keywords = query_understanding.extract_keywords("the and or is are")
        assert keywords == []

    def test_detect_intent_priority(self, query_understanding):
        """Test that more specific intents take priority."""
        # "template" is more specific than general
        assert (
            query_understanding.detect_intent("revenue template")
            == QueryIntent.TEMPLATE
        )

        # "required" is more specific than general
        assert (
            query_understanding.detect_intent("revenue required")
            == QueryIntent.REQUIREMENT
        )

        # If multiple intent keywords, first match wins
        # (template patterns checked before requirement patterns)
        assert (
            query_understanding.detect_intent("revenue template required")
            == QueryIntent.TEMPLATE
        )
