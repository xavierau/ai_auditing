"""RAG Orchestrator Agent - Intelligent retrieval coordination.

This is the main orchestrator that coordinates the entire RAG pipeline:
1. Query understanding (intent detection)
2. Cache lookup (if enabled)
3. Strategy selection (semantic/structure-aware/hybrid)
4. Retrieval execution
5. Re-ranking by intent
6. Chunk merging (defragmentation)
7. Context assembly
8. Cache storage
9. Audit logging

Phase 1 Implementation: Semantic retrieval only
Phase 2: Add structure-aware and hybrid strategies
Phase 3: Add caching and observability
"""

import hashlib
import json
import logging
import time
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from genreport.core.orchestration.query_understanding import QueryUnderstanding
from genreport.core.orchestration.rag_models import (
    ContentType,
    ContextChunk,
    QueryIntent,
    RAGQuery,
    RAGResult,
    RetrievalCandidate,
    RetrievalStrategy,
    StrategyExplanation,
)
from genreport.core.orchestration.strategy_selection import StrategySelector
from genreport.core.retrieval.embedding_service import EmbeddingService
from genreport.core.retrieval.kb_retriever import KBRetriever

logger = logging.getLogger(__name__)


class RAGOrchestrator:
    """Production RAG orchestrator with multi-strategy support.

    Coordinates the entire RAG pipeline from query understanding to
    context assembly, with intelligent strategy selection and caching.

    Phase 1: Semantic retrieval only
    Phase 2: Structure-aware and hybrid strategies
    Phase 3: Caching and observability

    Attributes:
        db: Database session
        jurisdiction: Jurisdiction code (HK, SG, AU)
        tenant_id: Tenant UUID for isolation
        user_id: User ID for audit logging
        embedding_service: Embedding service for query vectors
        document_structure: Optional document structure for structure-aware retrieval
        cache_client: Optional Redis client for caching
        enable_structure_aware: Whether structure-aware retrieval is available
        enable_caching: Whether caching is enabled
    """

    def __init__(
        self,
        db: Session,
        jurisdiction: str,
        tenant_id: UUID,
        user_id: int,
        embedding_service: EmbeddingService,
        document_structure: Optional[Dict] = None,
        cache_client: Optional[any] = None,  # Redis client
        enable_structure_aware: bool = True,
        enable_caching: bool = True,
    ):
        """Initialize RAG orchestrator with dependencies.

        Args:
            db: Database session
            jurisdiction: Jurisdiction code (HK, SG, AU)
            tenant_id: Tenant UUID
            user_id: User ID
            embedding_service: Embedding service
            document_structure: Optional document structure for structure-aware
            cache_client: Optional Redis client
            enable_structure_aware: Enable structure-aware retrieval
            enable_caching: Enable caching
        """
        self.db = db
        self.jurisdiction = jurisdiction
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.embedding_service = embedding_service
        self.document_structure = document_structure
        self.cache_client = cache_client
        self.enable_structure_aware = enable_structure_aware
        self.enable_caching = enable_caching

        # Initialize sub-components
        self.query_understanding = QueryUnderstanding()
        self.strategy_selector = StrategySelector(
            has_document_structure=document_structure is not None
        )

        # Initialize retrievers
        self.kb_retriever = KBRetriever(
            db=db,
            jurisdiction=jurisdiction,
            tenant_id=tenant_id,
            embedding_service=embedding_service,
        )

        # Structure-aware retriever (Phase 2)
        self.structure_aware_retriever = None
        if enable_structure_aware and document_structure:
            from genreport.core.retrieval.structure_aware_retriever import (
                StructureAwareRetriever,
            )

            self.structure_aware_retriever = StructureAwareRetriever(
                db=db,
                jurisdiction=jurisdiction,
                tenant_id=tenant_id,
                embedding_service=embedding_service,
                document_structure=document_structure,
            )

        logger.info(
            f"RAG Orchestrator initialized for jurisdiction={jurisdiction}, "
            f"tenant_id={tenant_id}, structure_aware={self.structure_aware_retriever is not None}"
        )

    def retrieve(
        self,
        query: RAGQuery,
        strategy: RetrievalStrategy = RetrievalStrategy.AUTO,
    ) -> RAGResult:
        """Main retrieval method coordinating the entire pipeline.

        Pipeline stages:
        1. Query understanding (intent detection)
        2. Cache lookup (if enabled) - Phase 3
        3. Strategy selection
        4. Retrieval execution
        5. Re-ranking by intent
        6. Chunk merging
        7. Context assembly
        8. Cache storage (if enabled) - Phase 3
        9. Audit logging - Phase 3

        Args:
            query: RAG query with filters
            strategy: Explicit strategy or AUTO for auto-selection

        Returns:
            RAGResult with assembled context chunks

        Raises:
            ValueError: If query is invalid
        """
        start_time = time.time()

        # Stage 1: Query understanding
        detected_intent = query.intent or self.query_understanding.detect_intent(
            query.query_text
        )

        logger.info(
            f"Query: '{query.query_text}' | Intent: {detected_intent.value}"
        )

        # Stage 2: Cache lookup
        if self.enable_caching and self.cache_client:
            cache_key = self._generate_cache_key(query, detected_intent)
            cached_result = self._check_cache(cache_key)
            if cached_result:
                cached_result.cache_hit = True
                logger.info(f"Cache HIT for query: '{query.query_text}'")
                return cached_result

        # Stage 3: Strategy selection
        if strategy == RetrievalStrategy.AUTO:
            selected_strategy = self.strategy_selector.select_strategy(
                query, detected_intent
            )
        else:
            selected_strategy = strategy

        logger.info(f"Strategy selected: {selected_strategy.value}")

        # Stage 4: Retrieval execution
        candidates = self._execute_retrieval(query, detected_intent, selected_strategy)

        logger.info(f"Retrieved {len(candidates)} candidates")

        # Stage 5: Re-ranking by intent
        candidates = self._rerank_by_intent(candidates, detected_intent)

        # Stage 6: Chunk merging
        if len(candidates) > 1:
            candidates = self._merge_related_chunks(candidates)

        # Stage 7: Context assembly
        result = self._assemble_context(candidates, query)
        result.query_intent = detected_intent
        result.strategy_used = selected_strategy
        result.total_candidates = len(candidates)
        result.cache_hit = False

        # Stage 8: Cache storage
        if self.enable_caching and self.cache_client:
            cache_key = self._generate_cache_key(query, detected_intent)
            self._store_cache(cache_key, result)

        # Stage 9: Audit logging
        duration_ms = (time.time() - start_time) * 1000
        result.retrieval_time_ms = duration_ms

        logger.info(
            f"Retrieval complete: {len(result.chunks)} chunks in {duration_ms:.0f}ms"
        )

        # Log to audit system
        self._log_retrieval(query, result, duration_ms)

        return result

    def _execute_retrieval(
        self,
        query: RAGQuery,
        intent: QueryIntent,
        strategy: RetrievalStrategy,
    ) -> List[RetrievalCandidate]:
        """Execute retrieval with selected strategy.

        Supports three strategies:
        - SEMANTIC: Fast vector similarity search
        - STRUCTURE_AWARE: Document structure navigation
        - HYBRID: Combined semantic + structure

        Args:
            query: RAG query
            intent: Detected intent
            strategy: Selected strategy

        Returns:
            List of retrieval candidates

        Raises:
            ValueError: If strategy is unsupported
        """
        if strategy == RetrievalStrategy.SEMANTIC:
            return self._execute_semantic_retrieval(query)

        elif strategy == RetrievalStrategy.STRUCTURE_AWARE:
            return self._execute_structure_aware_retrieval(query, intent)

        elif strategy == RetrievalStrategy.HYBRID:
            return self._execute_hybrid_retrieval(query, intent)

        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def _execute_semantic_retrieval(
        self,
        query: RAGQuery,
    ) -> List[RetrievalCandidate]:
        """Execute pure semantic retrieval using KBRetriever.

        Args:
            query: RAG query

        Returns:
            List of candidates from semantic search
        """
        # Extract filters
        chunk_types = query.filters.get("chunk_types") if query.filters else None

        # Call existing KBRetriever
        results = self.kb_retriever.retrieve(
            query=query.query_text,
            top_k=query.top_k * 2,  # Get more candidates for re-ranking
            chunk_types=chunk_types,
        )

        # Convert to RetrievalCandidate format
        candidates = []
        for result in results:
            # Map chunk_type string to ContentType enum
            try:
                chunk_type = ContentType(result["chunk_type"])
            except ValueError:
                # Unknown chunk type, default to GUIDANCE
                chunk_type = ContentType.GUIDANCE

            candidate = RetrievalCandidate(
                chunk_id=result["chunk_id"],
                content=result["content"],
                similarity_score=result["similarity_score"],
                relevance_score=result["similarity_score"],  # Initially same
                chunk_type=chunk_type,
                section_number=result.get("section_number"),
                section_title=result.get("section_title"),
                page_num=result.get("page_num"),
                document_title=result["document_title"],
                standard=result["standard"],
                jurisdiction=result["jurisdiction"],
                metadata={
                    "kb_document_id": result["kb_document_id"] if result["kb_document_id"] is not None else 0,
                    "chunk_index": result.get("chunk_index"),
                    "confidence_score": result.get("confidence_score"),
                    "review_status": result.get("review_status"),
                },
            )
            candidates.append(candidate)

        return candidates

    def _rerank_by_intent(
        self,
        candidates: List[RetrievalCandidate],
        intent: QueryIntent,
    ) -> List[RetrievalCandidate]:
        """Re-rank candidates based on query intent.

        Applies intent-specific boosting to relevance scores.

        Args:
            candidates: Initial candidates
            intent: Query intent

        Returns:
            Re-ranked candidates
        """
        # Intent-based boost factors
        boost_factors = {
            QueryIntent.TEMPLATE: {
                ContentType.TEMPLATE: 0.3,
                ContentType.EXAMPLE: 0.1,
                ContentType.REQUIREMENT: -0.05,
            },
            QueryIntent.REQUIREMENT: {
                ContentType.REQUIREMENT: 0.2,
                ContentType.DISCLOSURE: 0.15,
                ContentType.TEMPLATE: -0.1,
            },
            QueryIntent.EXAMPLE: {
                ContentType.EXAMPLE: 0.3,
                ContentType.TEMPLATE: 0.1,
                ContentType.DEFINITION: -0.05,
            },
            QueryIntent.DEFINITION: {
                ContentType.DEFINITION: 0.3,
                ContentType.GUIDANCE: 0.1,
            },
            QueryIntent.GENERAL: {},  # No boosting
        }

        boosts = boost_factors.get(intent, {})

        # Apply boosts
        for candidate in candidates:
            boost = boosts.get(candidate.chunk_type, 0.0)
            candidate.relevance_score = min(1.0, candidate.similarity_score + boost)

        # Re-sort by relevance_score
        candidates.sort(key=lambda c: c.relevance_score, reverse=True)

        return candidates

    def _merge_related_chunks(
        self,
        candidates: List[RetrievalCandidate],
    ) -> List[RetrievalCandidate]:
        """Merge adjacent chunks from the same section.

        Reduces fragmentation by combining related content.

        Args:
            candidates: Ranked candidates

        Returns:
            Candidates with merged chunks where appropriate
        """
        merged_candidates = []
        skip_indices = set()

        for i, candidate in enumerate(candidates):
            if i in skip_indices:
                continue

            # Check if next candidate should be merged
            if i + 1 < len(candidates):
                next_candidate = candidates[i + 1]

                # Merge conditions
                same_section = (
                    candidate.section_number
                    and candidate.section_number == next_candidate.section_number
                )
                similar_score = (
                    abs(candidate.relevance_score - next_candidate.relevance_score)
                    < 0.05
                )
                adjacent_chunks = abs(candidate.chunk_id - next_candidate.chunk_id) <= 2

                if same_section and similar_score and adjacent_chunks:
                    # Merge chunks
                    merged_content = candidate.content + "\n\n" + next_candidate.content

                    merged_candidate = candidate.model_copy()
                    merged_candidate.content = merged_content
                    merged_candidate.is_merged = True
                    merged_candidate.merged_from = [
                        candidate.chunk_id,
                        next_candidate.chunk_id,
                    ]

                    merged_candidates.append(merged_candidate)
                    skip_indices.add(i + 1)
                    continue

            # No merge, add as-is
            merged_candidates.append(candidate)

        return merged_candidates

    def _assemble_context(
        self,
        candidates: List[RetrievalCandidate],
        query: RAGQuery,
    ) -> RAGResult:
        """Assemble final context for agent consumption.

        Converts RetrievalCandidates to ContextChunks with rich metadata.

        Args:
            candidates: Re-ranked and merged candidates
            query: Original query

        Returns:
            RAGResult with assembled context
        """
        context_chunks = []

        for candidate in candidates[: query.top_k]:
            # Build source reference
            source_ref_parts = [candidate.standard]
            if candidate.section_number:
                source_ref_parts.append(f"Section {candidate.section_number}")
            if candidate.page_num:
                source_ref_parts.append(f"p.{candidate.page_num}")

            source_reference = ", ".join(source_ref_parts)

            # Extract section context
            section_context = candidate.section_title if candidate.section_title else None

            # Determine if mandatory
            is_mandatory = (
                candidate.chunk_type == ContentType.REQUIREMENT
                and "shall" in candidate.content.lower()
            )

            # Build context chunk
            # Ensure document_id is an integer (never None)
            doc_id = candidate.metadata.get("kb_document_id")
            if doc_id is None:
                doc_id = 0  # Default to 0 if no document ID

            context_chunk = ContextChunk(
                content=candidate.content,
                source_reference=source_reference,
                relevance_score=candidate.relevance_score,
                chunk_type=candidate.chunk_type,
                chunk_id=candidate.chunk_id,
                document_id=int(doc_id),  # Ensure it's an integer
                section_context=section_context,
                is_mandatory=is_mandatory,
                cross_references=candidate.metadata.get("cross_references", []),
            )
            context_chunks.append(context_chunk)

        # Build result
        result = RAGResult(
            chunks=context_chunks,
            query_intent=QueryIntent.GENERAL,  # Will be set by caller
            strategy_used=RetrievalStrategy.AUTO,  # Will be set by caller
            total_candidates=len(candidates),
            cache_hit=False,
            retrieval_time_ms=0.0,  # Will be set by caller
            metadata={
                "query": query.query_text,
                "top_k": query.top_k,
                "filters": query.filters or {},
            },
        )

        return result

    def explain_strategy(self, query: RAGQuery) -> StrategyExplanation:
        """Explain retrieval strategy for debugging/transparency.

        Args:
            query: RAG query

        Returns:
            Strategy explanation with rationale
        """
        # Detect intent
        detected_intent = query.intent or self.query_understanding.detect_intent(
            query.query_text
        )

        # Select strategy
        selected_strategy = self.strategy_selector.select_strategy(query, detected_intent)

        # Get explanation
        rationale = self.strategy_selector.explain_selection(
            query, detected_intent, selected_strategy
        )

        # Get alternatives
        alternative_strategies = self.strategy_selector.get_alternative_strategies(
            query, detected_intent, selected_strategy
        )

        explanation = StrategyExplanation(
            query=query.query_text,
            detected_intent=detected_intent,
            selected_strategy=selected_strategy,
            rationale=rationale,
            sections_searched=[],  # Populated if structure-aware used
            filters_applied=query.filters or {},
            alternative_strategies=alternative_strategies,
        )

        return explanation

    def _execute_structure_aware_retrieval(
        self,
        query: RAGQuery,
        intent: QueryIntent,
    ) -> List[RetrievalCandidate]:
        """Execute structure-aware retrieval using StructureAwareRetriever.

        Falls back to semantic if structure-aware retriever not available.

        Args:
            query: RAG query
            intent: Detected intent

        Returns:
            List of candidates from structure-aware search
        """
        if not self.structure_aware_retriever:
            logger.warning(
                "Structure-aware retriever not available, falling back to semantic"
            )
            return self._execute_semantic_retrieval(query)

        # Extract filters
        chunk_types = query.filters.get("chunk_types") if query.filters else None

        # Call StructureAwareRetriever
        try:
            results = self.structure_aware_retriever.retrieve(
                query=query.query_text,
                intent=intent.value,
                top_k=query.top_k * 2,  # Get more candidates for re-ranking
                use_structure=True,
            )

            # Convert to RetrievalCandidate format
            candidates = []
            for result in results:
                # Map chunk_type string to ContentType enum
                try:
                    chunk_type = ContentType(result["chunk_type"])
                except (ValueError, KeyError):
                    # Unknown chunk type, default to GUIDANCE
                    chunk_type = ContentType.GUIDANCE

                candidate = RetrievalCandidate(
                    chunk_id=result["chunk_id"],
                    content=result["content"],
                    similarity_score=result["similarity_score"],
                    relevance_score=result["similarity_score"],  # Initially same
                    chunk_type=chunk_type,
                    section_number=result.get("section_number"),
                    section_title=result.get("section_title"),
                    page_num=result.get("page_num"),
                    document_title=result["document_title"],
                    standard=result["standard"],
                    jurisdiction=result["jurisdiction"],
                    metadata={
                        "kb_document_id": result.get("kb_document_id"),
                        "chunk_index": result.get("chunk_index"),
                        "confidence_score": result.get("confidence_score"),
                        "review_status": result.get("review_status"),
                    },
                )
                candidates.append(candidate)

            return candidates

        except Exception as e:
            logger.error(f"Structure-aware retrieval failed: {e}, falling back to semantic")
            return self._execute_semantic_retrieval(query)

    def _execute_hybrid_retrieval(
        self,
        query: RAGQuery,
        intent: QueryIntent,
    ) -> List[RetrievalCandidate]:
        """Execute hybrid retrieval combining semantic and structure-aware.

        Merges and deduplicates results from both strategies.

        Args:
            query: RAG query
            intent: Detected intent

        Returns:
            List of merged candidates
        """
        # Get semantic results
        semantic_results = self._execute_semantic_retrieval(query)

        # Get structure-aware results (if available)
        if self.structure_aware_retriever:
            try:
                structure_results = self._execute_structure_aware_retrieval(query, intent)
            except Exception as e:
                logger.warning(f"Structure-aware retrieval failed in hybrid mode: {e}")
                structure_results = []
        else:
            structure_results = []

        # Merge and deduplicate
        merged_results = self._merge_results(semantic_results, structure_results)

        return merged_results

    def _merge_results(
        self,
        semantic_results: List[RetrievalCandidate],
        structure_results: List[RetrievalCandidate],
    ) -> List[RetrievalCandidate]:
        """Merge and deduplicate results from semantic and structure-aware retrieval.

        Strategy:
        1. Create a map of chunk_id -> best candidate
        2. For duplicates, keep the one with higher relevance score
        3. Sort by relevance score descending

        Args:
            semantic_results: Results from semantic retrieval
            structure_results: Results from structure-aware retrieval

        Returns:
            Merged and deduplicated candidates
        """
        # Map chunk_id -> candidate (keep best score)
        candidates_map: Dict[int, RetrievalCandidate] = {}

        # Add semantic results
        for candidate in semantic_results:
            candidates_map[candidate.chunk_id] = candidate

        # Add structure results, keeping higher score if duplicate
        for candidate in structure_results:
            chunk_id = candidate.chunk_id

            if chunk_id in candidates_map:
                # Duplicate: keep higher relevance score
                existing = candidates_map[chunk_id]
                if candidate.relevance_score > existing.relevance_score:
                    candidates_map[chunk_id] = candidate
            else:
                # New candidate
                candidates_map[chunk_id] = candidate

        # Convert to list and sort by relevance
        merged = list(candidates_map.values())
        merged.sort(key=lambda c: c.relevance_score, reverse=True)

        logger.info(
            f"Hybrid retrieval merged {len(semantic_results)} semantic + "
            f"{len(structure_results)} structure = {len(merged)} unique candidates"
        )

        return merged

    # ========================================================================
    # Phase 3: Caching Methods
    # ========================================================================

    def _generate_cache_key(
        self,
        query: RAGQuery,
        intent: QueryIntent,
    ) -> str:
        """Generate deterministic cache key for query.

        Cache key includes:
        - Query text (lowercased)
        - Top K
        - Intent
        - Jurisdiction
        - Tenant ID
        - Filters (if any)

        Args:
            query: RAG query
            intent: Detected intent

        Returns:
            Cache key string (prefixed with "rag:cache:")
        """
        # Build cache key components
        key_parts = [
            query.query_text.lower().strip(),
            str(query.top_k),
            intent.value,
            self.jurisdiction,
            str(query.tenant_id),
        ]

        # Add filters if present
        if query.filters:
            key_parts.append(json.dumps(query.filters, sort_keys=True))

        # Hash for consistent key length
        key_str = "|".join(key_parts)
        key_hash = hashlib.sha256(key_str.encode()).hexdigest()[:16]

        return f"rag:cache:{self.jurisdiction}:{key_hash}"

    def _check_cache(self, cache_key: str) -> Optional[RAGResult]:
        """Check Redis cache for cached result.

        Args:
            cache_key: Cache key

        Returns:
            Cached result or None
        """
        if not self.cache_client:
            return None

        try:
            cached_data = self.cache_client.get(cache_key)
            if cached_data:
                # Deserialize JSON to RAGResult
                result_dict = json.loads(cached_data)
                result = RAGResult(**result_dict)
                logger.debug(f"Cache hit: {cache_key}")
                return result
        except Exception as e:
            logger.warning(f"Cache retrieval error: {e}")

        return None

    def _store_cache(self, cache_key: str, result: RAGResult) -> None:
        """Store result in Redis cache.

        Args:
            cache_key: Cache key
            result: Result to cache
        """
        if not self.cache_client:
            return

        try:
            # Serialize to JSON
            result_json = result.model_dump_json()

            # Store with TTL (15 minutes = 900 seconds)
            self.cache_client.setex(cache_key, 900, result_json)
            logger.debug(f"Cached result: {cache_key}")
        except Exception as e:
            logger.warning(f"Cache storage error: {e}")

    # ========================================================================
    # Phase 3: Audit Logging
    # ========================================================================

    def _log_retrieval(
        self,
        query: RAGQuery,
        result: RAGResult,
        duration_ms: float,
    ) -> None:
        """Log retrieval event for audit trail.

        Args:
            query: RAG query
            result: Retrieval result
            duration_ms: Retrieval duration
        """
        metadata = {
            "query": query.query_text,
            "intent": result.query_intent.value,
            "strategy": result.strategy_used.value,
            "top_k": query.top_k,
            "results_returned": len(result.chunks),
            "total_candidates": result.total_candidates,
            "cache_hit": result.cache_hit,
            "duration_ms": duration_ms,
            "jurisdiction": self.jurisdiction,
            "project_id": query.project_id,
        }

        # Log to audit system (integrates with existing AuditLogger)
        try:
            from genreport.core.security.audit_logger import AuditLogger

            AuditLogger.log_event(
                db=self.db,
                event_type="RAG_RETRIEVAL",
                action="RETRIEVE_CONTEXT",
                user_id=query.user_id,
                tenant_id=query.tenant_id,
                resource_type="knowledge_base",
                resource_id=None,  # Not specific to one resource
                details=metadata,  # Renamed from metadata to details
                status="SUCCESS",
            )
        except Exception as e:
            # Don't fail retrieval if audit logging fails
            logger.error(f"Audit logging failed: {e}")
