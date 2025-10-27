"""Query understanding and intent detection for RAG orchestrator.

This module provides query analysis capabilities:
- Intent detection using rule-based pattern matching
- Query expansion with synonyms and related terms
- Keyword extraction for filtering

Future enhancement: Replace rule-based with LLM-based intent detection.
"""

import re
from typing import List

from genreport.core.orchestration.rag_models import QueryIntent


class QueryUnderstanding:
    """Query understanding and intent detection.

    Uses rule-based pattern matching to detect query intent.
    Future enhancement: Use LLM (GPT-4o-mini) for more accurate classification.

    Intent patterns prioritize specific intents over general ones:
    1. TEMPLATE: Looking for copy-paste templates/policies
    2. REQUIREMENT: Looking for mandatory disclosures
    3. EXAMPLE: Looking for illustrative examples
    4. DEFINITION: Looking for term definitions
    5. GENERAL: Default fallback
    """

    # Intent detection patterns (rule-based)
    # Patterns are checked in order, first match wins
    INTENT_PATTERNS = {
        QueryIntent.TEMPLATE: [
            r"\btemplate\b",
            r"\bwording\b",
            r"\bpolicy\b",
            r"\bpolicies\b",
            r"\bboilerplate\b",
            r"\bcopy[- ]paste\b",
            r"\billustrative policy\b",
            r"\billustrative policies\b",
            r"\baccounting policy\b",
            r"\baccounting policies\b",
        ],
        QueryIntent.REQUIREMENT: [
            r"\brequired\b",
            r"\bmandatory\b",
            r"\bmust disclose\b",
            r"\bshall disclose\b",
            r"\bwhat disclosures\b",
            r"\bwhat is required\b",
            r"\bdisclosure requirements\b",
            r"\brequirements for\b",
            r"\bshall be disclosed\b",
            r"\bmust be disclosed\b",
        ],
        QueryIntent.EXAMPLE: [
            r"\bexample\b",
            r"\billustrative\b",
            r"\bsample\b",
            r"\bscenario\b",
            r"\bfor instance\b",
            r"\billustration\b",
            r"\bdemonstration\b",
        ],
        QueryIntent.DEFINITION: [
            r"\bwhat is\b",
            r"\bdefine\b",
            r"\bmeaning of\b",
            r"\bdefinition\b",
            r"\bexplain\b",
            r"\bwhat does.*mean\b",
            r"\bwhat are\b",
        ],
    }

    # Common accounting stopwords (extend as needed)
    STOPWORDS = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "should",
        "could",
        "may",
        "might",
        "must",
        "can",
        "what",
        "how",
        "when",
        "where",
        "why",
        "which",
    }

    def detect_intent(self, query_text: str) -> QueryIntent:
        """Detect query intent using rule-based pattern matching.

        Patterns are checked in priority order:
        1. TEMPLATE (specific templates/policies)
        2. REQUIREMENT (mandatory disclosures)
        3. EXAMPLE (illustrations)
        4. DEFINITION (term explanations)
        5. GENERAL (default fallback)

        Args:
            query_text: Query string

        Returns:
            Detected intent (defaults to GENERAL if no match)

        Examples:
            >>> qu = QueryUnderstanding()
            >>> qu.detect_intent("revenue recognition accounting policy template")
            QueryIntent.TEMPLATE
            >>> qu.detect_intent("what disclosures are required for PPE")
            QueryIntent.REQUIREMENT
            >>> qu.detect_intent("revenue recognition")
            QueryIntent.GENERAL
        """
        query_lower = query_text.lower()

        # Check each intent pattern in priority order
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return intent

        # Default to GENERAL if no patterns match
        return QueryIntent.GENERAL

    def expand_query(
        self,
        query_text: str,
        intent: QueryIntent,
    ) -> List[str]:
        """Expand query with synonyms and related terms.

        Intent-specific expansion helps retrieve more relevant results:
        - TEMPLATE: Add "accounting policy", "illustrative wording"
        - REQUIREMENT: Add "disclosure requirements", "mandatory disclosures"
        - EXAMPLE: Add "example", "illustration"
        - DEFINITION/GENERAL: No expansion (keep focused)

        Args:
            query_text: Original query
            intent: Detected intent

        Returns:
            List of query variations (always includes original)

        Examples:
            >>> qu = QueryUnderstanding()
            >>> qu.expand_query("revenue recognition", QueryIntent.TEMPLATE)
            ['revenue recognition', 'revenue recognition accounting policy', ...]
        """
        expansions = [query_text]  # Always include original

        # Intent-specific expansions
        if intent == QueryIntent.TEMPLATE:
            expansions.append(f"{query_text} accounting policy")
            expansions.append(f"{query_text} illustrative wording")

        elif intent == QueryIntent.REQUIREMENT:
            expansions.append(f"{query_text} disclosure requirements")
            expansions.append(f"{query_text} mandatory disclosures")

        elif intent == QueryIntent.EXAMPLE:
            expansions.append(f"{query_text} example")
            expansions.append(f"{query_text} illustration")

        # DEFINITION and GENERAL: No expansion (keep focused)

        return expansions

    def extract_keywords(self, query_text: str) -> List[str]:
        """Extract key terms from query.

        Removes stopwords and extracts meaningful terms (>2 chars).
        Useful for filtering and highlighting.

        Args:
            query_text: Query string

        Returns:
            List of keywords (lowercased, deduplicated)

        Examples:
            >>> qu = QueryUnderstanding()
            >>> qu.extract_keywords("What are the disclosure requirements for PPE?")
            ['disclosure', 'requirements', 'ppe']
        """
        # Tokenize: extract words (letters only, no numbers/punctuation)
        words = re.findall(r"\b[a-z]+\b", query_text.lower())

        # Filter: remove stopwords and short words
        keywords = [
            w for w in words if w not in self.STOPWORDS and len(w) > 2
        ]

        # Deduplicate while preserving order
        seen = set()
        unique_keywords = []
        for keyword in keywords:
            if keyword not in seen:
                seen.add(keyword)
                unique_keywords.append(keyword)

        return unique_keywords

    def is_accounting_term(self, term: str) -> bool:
        """Check if term is a known accounting concept.

        Simple heuristic: Check for common accounting keywords.
        Future enhancement: Use accounting ontology/taxonomy.

        Args:
            term: Term to check

        Returns:
            True if likely an accounting term

        Examples:
            >>> qu = QueryUnderstanding()
            >>> qu.is_accounting_term("revenue")
            True
            >>> qu.is_accounting_term("hello")
            False
        """
        # Common accounting terms (extend as needed)
        accounting_terms = {
            "revenue",
            "expense",
            "asset",
            "liability",
            "equity",
            "depreciation",
            "amortization",
            "impairment",
            "provision",
            "contingent",
            "lease",
            "inventory",
            "receivable",
            "payable",
            "investment",
            "goodwill",
            "intangible",
            "tangible",
            "financial",
            "disclosure",
            "recognition",
            "measurement",
            "derecognition",
            "consolidation",
            "subsidiary",
            "associate",
            "joint",
            "venture",
            "ppe",
            "property",
            "plant",
            "equipment",
        }

        return term.lower() in accounting_terms
