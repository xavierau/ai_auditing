# Sprint 3 Remaining Components - Implementation Plan
## Knowledge Base Retrieval & RAG System

**Date:** 2025-10-18
**Status:** Implementation Ready
**Sprint:** Sprint 3 - Knowledge Base & Basic Generation (Week 2-2.5)
**Architecture:** Hybrid Pattern with Security-First Design

---

## Executive Summary

This document provides a comprehensive implementation plan for the remaining Sprint 3 components, focusing on secure, jurisdiction-aware KB retrieval with Redis caching, access control, and DSPy-based chunk categorization. The implementation follows Clean Architecture principles, SOLID design patterns, and TDD methodology.

**Key Objectives:**
1. Build PGVector-based semantic search with jurisdiction filtering
2. Implement Redis caching layer for embedding optimization (70%+ hit rate target)
3. Create DSPy-powered chunk categorization (80%+ auto-approval rate)
4. Establish comprehensive access control and audit logging
5. Develop FastAPI endpoints for KB management
6. Ensure 100% security test coverage

**Completed (Week 1):**
- ✅ Database schema with jurisdiction support and vector indexes
- ✅ PDF extraction service (pdfplumber)
- ✅ Text chunking service (1000 chars, 200 overlap)
- ✅ Enhanced embedding service (Gemini/OpenAI support)
- ✅ KB ingestion service (orchestration)
- ✅ 453 chunks ingested from SME-FRS document

**Remaining (Week 2-2.5):**
- KB Retriever with PGVector similarity search
- SecureKBRetriever with access control layer
- DSPy Chunk Categorizer for semi-automated approval
- Redis embedding cache with 7-day TTL
- FastAPI KB endpoints with rate limiting
- Comprehensive security and integration tests

---

## Component Dependency Graph

```
Phase 1: Core Retrieval (Foundation)
├── 1. KBRetriever (PGVector + jurisdiction filtering)
│   ├── Depends on: existing EmbeddingService, KBChunk model
│   └── Required by: SecureKBRetriever, API endpoints

Phase 2: Security Layer
├── 2. SecureKBRetriever (Access control wrapper)
│   ├── Depends on: KBRetriever, tenant_context, audit_logger
│   └── Required by: API endpoints, DSPy agents (Sprint 4)

Phase 3: Optimization & Automation
├── 3. EmbeddingCache (Redis layer)
│   ├── Depends on: Redis configuration
│   └── Required by: EmbeddingService enhancement
│
├── 4. ChunkCategorizer (DSPy signature)
│   ├── Depends on: DSPy setup, existing ingestion service
│   └── Required by: Enhanced ingestion endpoint

Phase 4: API Layer
├── 5. KB API Endpoints (FastAPI routes)
│   ├── Depends on: SecureKBRetriever, ChunkCategorizer
│   └── Required by: Frontend (Sprint 5)

Phase 5: Testing & Validation
└── 6. Comprehensive Test Suite
    ├── Unit tests for each component
    ├── Integration tests for end-to-end flows
    └── Security tests (100% coverage)
```

---

## Technical Design Document

### 1. KBRetriever: PGVector Semantic Search

**File:** `/Users/xavierau/Code/python/new_ai_auditing/genreport/core/retrieval/kb_retriever.py`

#### Architecture Decision
- **Pattern:** Repository pattern with domain-driven design
- **Rationale:** Separates vector search logic from security concerns (Single Responsibility Principle)
- **Dependencies:** EmbeddingService (for query embedding), SQLAlchemy (for PGVector queries)

#### Class Design

```python
from typing import List, Dict, Optional
from uuid import UUID
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from genreport.core.database.models import KBChunk, KnowledgeBase
from genreport.core.retrieval.embedding_service import EmbeddingService


class KBRetriever:
    """Jurisdiction-aware knowledge base retrieval using PGVector.

    ARCHITECTURE: This class implements ONLY the retrieval logic.
    Security concerns (access control, audit logging) are handled
    by SecureKBRetriever wrapper (Decorator pattern).

    SOLID Compliance:
    - SRP: Handles only vector similarity search
    - OCP: Open for extension (SecureKBRetriever extends behavior)
    - DIP: Depends on abstractions (EmbeddingService interface)
    """

    def __init__(
        self,
        db: Session,
        jurisdiction: str,
        embedding_service: Optional[EmbeddingService] = None
    ):
        """Initialize KB retriever.

        Args:
            db: Database session (injected)
            jurisdiction: Jurisdiction code (HK, SG, AU)
            embedding_service: Optional embedding service (defaults to configured provider)
        """
        self.db = db
        self.jurisdiction = jurisdiction.upper()
        self.embedding_service = embedding_service or EmbeddingService()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.5,
        chunk_types: Optional[List[str]] = None,
        standards: Optional[List[str]] = None
    ) -> List[Dict]:
        """Retrieve relevant KB chunks using vector similarity.

        Two-step retrieval:
        1. Metadata filtering (jurisdiction, review_status, optional filters)
        2. Vector similarity ranking

        Args:
            query: Search query text
            top_k: Number of results to return
            min_similarity: Minimum cosine similarity threshold (0-1)
            chunk_types: Optional filter by chunk types
            standards: Optional filter by accounting standards

        Returns:
            List of dictionaries with:
            - chunk_id: Chunk ID
            - content: Chunk text content
            - similarity_score: Cosine similarity (0-1)
            - metadata: Chunk metadata (document title, standard, etc.)
            - kb_document_id: Parent document ID
            - jurisdiction: Jurisdiction code

        Raises:
            ValueError: If query is empty or jurisdiction invalid
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if self.jurisdiction not in ["HK", "SG", "AU"]:
            raise ValueError(f"Invalid jurisdiction: {self.jurisdiction}")

        # Step 1: Generate query embedding
        query_embedding = self._generate_query_embedding(query)

        # Step 2: Build base query with metadata filters
        base_query = self._build_base_query(chunk_types, standards)

        # Step 3: Calculate similarity and rank
        results = self._execute_similarity_search(
            base_query,
            query_embedding,
            top_k,
            min_similarity
        )

        return results

    def retrieve_by_standard(
        self,
        standard: str,
        query: str,
        top_k: int = 5
    ) -> List[Dict]:
        """Convenience method to retrieve from specific standard.

        Args:
            standard: Accounting standard (e.g., "HKFRS 15", "SME-FRS")
            query: Search query
            top_k: Number of results

        Returns:
            Filtered retrieval results
        """
        return self.retrieve(
            query=query,
            top_k=top_k,
            standards=[standard]
        )

    def _generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for search query.

        Uses RETRIEVAL_QUERY task type for Gemini to optimize
        for search similarity (vs document encoding).
        """
        return self.embedding_service.generate_embedding(
            text=query,
            task_type="RETRIEVAL_QUERY"  # Gemini-specific optimization
        )

    def _build_base_query(
        self,
        chunk_types: Optional[List[str]],
        standards: Optional[List[str]]
    ):
        """Build base query with metadata filters.

        SECURITY CRITICAL: Jurisdiction filter is MANDATORY.
        All queries MUST filter by jurisdiction to prevent cross-market leakage.
        """
        query = self.db.query(KBChunk).join(KnowledgeBase)

        # MANDATORY: Jurisdiction filter
        query = query.filter(KBChunk.jurisdiction == self.jurisdiction)

        # MANDATORY: Only approved chunks
        query = query.filter(
            KBChunk.review_status.in_(["auto_approved", "reviewed"])
        )

        # MANDATORY: Active documents only
        query = query.filter(KnowledgeBase.is_active == True)

        # Optional: Chunk type filter
        if chunk_types:
            query = query.filter(KBChunk.chunk_type.in_(chunk_types))

        # Optional: Standard filter
        if standards:
            query = query.filter(KnowledgeBase.standard.in_(standards))

        return query

    def _execute_similarity_search(
        self,
        base_query,
        query_embedding: List[float],
        top_k: int,
        min_similarity: float
    ) -> List[Dict]:
        """Execute PGVector similarity search.

        Uses cosine distance with L2 normalization for vector comparison.
        Lower distance = higher similarity.

        Formula: similarity = 1 - (distance / 2)
        """
        # Calculate cosine distance
        # PGVector's <-> operator returns cosine distance
        results = base_query.order_by(
            KBChunk.embedding.cosine_distance(query_embedding)
        ).limit(top_k * 2).all()  # Fetch extra for filtering

        # Convert to dictionaries with similarity scores
        formatted_results = []

        for chunk in results:
            # Calculate similarity score (1 - normalized distance)
            distance = float(chunk.embedding.cosine_distance(query_embedding))
            similarity = 1.0 - (distance / 2.0)  # Normalize to 0-1

            # Apply minimum similarity threshold
            if similarity < min_similarity:
                continue

            formatted_results.append({
                "chunk_id": chunk.id,
                "content": chunk.content,
                "similarity_score": round(similarity, 4),
                "kb_document_id": chunk.kb_document_id,
                "jurisdiction": chunk.jurisdiction,
                "chunk_type": chunk.chunk_type,
                "metadata": {
                    "document_title": chunk.kb_document.title,
                    "standard": chunk.kb_document.standard,
                    "chunk_index": chunk.chunk_index,
                    "confidence_score": chunk.confidence_score,
                    "embedding_model": chunk.embedding_model,
                    **chunk.chunk_metadata
                }
            })

            # Stop when we have enough results
            if len(formatted_results) >= top_k:
                break

        return formatted_results
```

#### Method Signatures Summary
```python
class KBRetriever:
    def __init__(self, db: Session, jurisdiction: str, embedding_service: Optional[EmbeddingService])
    def retrieve(self, query: str, top_k: int = 5, min_similarity: float = 0.5,
                 chunk_types: Optional[List[str]] = None, standards: Optional[List[str]] = None) -> List[Dict]
    def retrieve_by_standard(self, standard: str, query: str, top_k: int = 5) -> List[Dict]
    def _generate_query_embedding(self, query: str) -> List[float]
    def _build_base_query(self, chunk_types: Optional[List[str]], standards: Optional[List[str]])
    def _execute_similarity_search(self, base_query, query_embedding: List[float],
                                   top_k: int, min_similarity: float) -> List[Dict]
```

#### SOLID Principles Application

1. **Single Responsibility Principle (SRP)**
   - Class responsibility: Vector similarity search ONLY
   - Security, caching, and access control are separate concerns

2. **Open/Closed Principle (OCP)**
   - Open for extension via SecureKBRetriever wrapper
   - Closed for modification (stable interface)

3. **Liskov Substitution Principle (LSP)**
   - Can be substituted with enhanced versions (SecureKBRetriever)
   - Maintains contract of retrieve() method

4. **Interface Segregation Principle (ISP)**
   - Focused interface with minimal public methods
   - Optional parameters prevent interface bloat

5. **Dependency Inversion Principle (DIP)**
   - Depends on EmbeddingService abstraction (not concrete implementation)
   - DB session injected (not created internally)

---

### 2. SecureKBRetriever: Access Control Layer

**File:** `/Users/xavierau/Code/python/new_ai_auditing/genreport/core/retrieval/secure_kb_retriever.py`

#### Architecture Decision
- **Pattern:** Decorator pattern over KBRetriever
- **Rationale:** Adds security concerns without modifying core retrieval logic
- **Dependencies:** KBRetriever, AuditLogger, tenant_context

#### Class Design

```python
from typing import List, Dict, Optional
from uuid import UUID
from sqlalchemy.orm import Session
import time

from genreport.core.retrieval.kb_retriever import KBRetriever
from genreport.core.retrieval.embedding_service import EmbeddingService
from genreport.core.security.audit_logger import AuditLogger
from genreport.core.database.models import KnowledgeBase


class SecureKBRetriever:
    """KB retriever with access control and audit logging.

    ARCHITECTURE: Decorator pattern - wraps KBRetriever to add:
    1. Tenant isolation (filter by tenant_id)
    2. Access level enforcement (PUBLIC, TENANT, RESTRICTED)
    3. Comprehensive audit logging

    SECURITY CRITICAL: This class enforces:
    - Multi-tenant isolation
    - User-level access control
    - Audit trail for compliance

    SOLID Compliance:
    - SRP: Adds ONLY security concerns
    - OCP: Extends KBRetriever without modifying it
    - DIP: Depends on KBRetriever abstraction
    """

    def __init__(
        self,
        db: Session,
        jurisdiction: str,
        tenant_id: UUID,
        user_id: int,
        embedding_service: Optional[EmbeddingService] = None
    ):
        """Initialize secure KB retriever.

        Args:
            db: Database session
            jurisdiction: Jurisdiction code (HK, SG, AU)
            tenant_id: Current tenant ID (from context)
            user_id: Current user ID (from JWT)
            embedding_service: Optional embedding service
        """
        self.db = db
        self.jurisdiction = jurisdiction
        self.tenant_id = tenant_id
        self.user_id = user_id

        # Initialize base retriever
        self.base_retriever = KBRetriever(
            db=db,
            jurisdiction=jurisdiction,
            embedding_service=embedding_service
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.5,
        chunk_types: Optional[List[str]] = None,
        standards: Optional[List[str]] = None
    ) -> List[Dict]:
        """Retrieve KB chunks with access control.

        Applies three-layer security:
        1. Jurisdiction filtering (in base retriever)
        2. Tenant isolation (PUBLIC + own tenant)
        3. Access level enforcement
        4. Audit logging

        Args:
            query: Search query
            top_k: Number of results
            min_similarity: Similarity threshold
            chunk_types: Optional chunk type filter
            standards: Optional standards filter

        Returns:
            Filtered results accessible to current user/tenant

        Raises:
            Exception: On retrieval failure (logged to audit)
        """
        start_time = time.time()

        try:
            # Step 1: Get base results (jurisdiction-filtered)
            base_results = self.base_retriever.retrieve(
                query=query,
                top_k=top_k * 2,  # Fetch extra for access filtering
                min_similarity=min_similarity,
                chunk_types=chunk_types,
                standards=standards
            )

            # Step 2: Apply access control filtering
            accessible_results = self._filter_by_access(base_results)

            # Step 3: Limit to requested top_k
            final_results = accessible_results[:top_k]

            # Step 4: Log successful retrieval
            self._log_retrieval_success(query, final_results, start_time)

            return final_results

        except Exception as e:
            # Log retrieval failure
            self._log_retrieval_failure(query, str(e), start_time)
            raise

    def retrieve_by_standard(
        self,
        standard: str,
        query: str,
        top_k: int = 5
    ) -> List[Dict]:
        """Retrieve from specific standard with access control."""
        return self.retrieve(
            query=query,
            top_k=top_k,
            standards=[standard]
        )

    def _filter_by_access(self, results: List[Dict]) -> List[Dict]:
        """Filter results by access permissions.

        Access Rules:
        1. PUBLIC documents (tenant_id IS NULL): Accessible to all
        2. TENANT documents (tenant_id = current_tenant): Accessible to tenant
        3. RESTRICTED documents: Require admin role

        SECURITY CRITICAL: Prevents cross-tenant data leakage.
        """
        accessible = []

        for result in results:
            kb_doc_id = result["kb_document_id"]

            # Fetch document metadata
            kb_doc = self.db.query(KnowledgeBase).filter(
                KnowledgeBase.id == kb_doc_id
            ).first()

            if not kb_doc:
                continue

            # Check access permissions
            if self._can_access_document(kb_doc):
                accessible.append(result)

        return accessible

    def _can_access_document(self, kb_doc: KnowledgeBase) -> bool:
        """Check if current user can access KB document.

        Access Logic:
        - PUBLIC (tenant_id IS NULL): Always accessible
        - TENANT (tenant_id = current): Accessible to tenant members
        - RESTRICTED: Requires admin role (future implementation)
        """
        # PUBLIC documents: accessible to all in jurisdiction
        if kb_doc.tenant_id is None and kb_doc.access_level == "PUBLIC":
            return True

        # TENANT documents: accessible to owning tenant
        if kb_doc.tenant_id == self.tenant_id:
            return True

        # RESTRICTED documents: require admin role
        if kb_doc.access_level == "RESTRICTED":
            # TODO: Implement role-based access control
            # For now, allow access to tenant members
            return kb_doc.tenant_id == self.tenant_id

        return False

    def _log_retrieval_success(
        self,
        query: str,
        results: List[Dict],
        start_time: float
    ) -> None:
        """Log successful KB retrieval for audit trail."""
        response_time_ms = (time.time() - start_time) * 1000

        AuditLogger.log_event(
            db=self.db,
            event_type="KB_RETRIEVAL",
            action="READ",
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            resource_type="knowledge_base",
            details={
                "query": query,
                "jurisdiction": self.jurisdiction,
                "results_count": len(results),
                "response_time_ms": round(response_time_ms, 2),
                "top_similarity": results[0]["similarity_score"] if results else None
            },
            status="SUCCESS"
        )

    def _log_retrieval_failure(
        self,
        query: str,
        error: str,
        start_time: float
    ) -> None:
        """Log failed KB retrieval for security monitoring."""
        response_time_ms = (time.time() - start_time) * 1000

        AuditLogger.log_event(
            db=self.db,
            event_type="KB_RETRIEVAL",
            action="READ",
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            resource_type="knowledge_base",
            details={
                "query": query,
                "jurisdiction": self.jurisdiction,
                "error": error,
                "response_time_ms": round(response_time_ms, 2)
            },
            status="FAILURE"
        )
```

#### Method Signatures Summary
```python
class SecureKBRetriever:
    def __init__(self, db: Session, jurisdiction: str, tenant_id: UUID, user_id: int,
                 embedding_service: Optional[EmbeddingService])
    def retrieve(self, query: str, top_k: int = 5, min_similarity: float = 0.5,
                 chunk_types: Optional[List[str]] = None, standards: Optional[List[str]] = None) -> List[Dict]
    def retrieve_by_standard(self, standard: str, query: str, top_k: int = 5) -> List[Dict]
    def _filter_by_access(self, results: List[Dict]) -> List[Dict]
    def _can_access_document(self, kb_doc: KnowledgeBase) -> bool
    def _log_retrieval_success(self, query: str, results: List[Dict], start_time: float) -> None
    def _log_retrieval_failure(self, query: str, error: str, start_time: float) -> None
```

---

### 3. EmbeddingCache: Redis Caching Layer

**File:** `/Users/xavierau/Code/python/new_ai_auditing/genreport/core/retrieval/embedding_cache.py`

#### Architecture Decision
- **Pattern:** Cache-aside (lazy loading) with fallback to API
- **Rationale:** Reduces embedding API costs, improves retrieval latency
- **Dependencies:** Redis, hashlib (for content hashing)

#### Class Design

```python
import hashlib
import json
from typing import List, Optional, Dict
import redis
from genreport.core.utils.config import settings


class EmbeddingCache:
    """Redis-based embedding cache with SHA256 content hashing.

    ARCHITECTURE: Cache-aside pattern
    - Check cache first (fast path)
    - On miss, compute embedding and cache (slow path)
    - TTL: 7 days for query embeddings, permanent for document embeddings

    PERFORMANCE TARGET: 70%+ cache hit rate

    Cache Key Format:
    embedding:{provider}:{model}:{dimensions}:{content_hash}

    Example:
    embedding:gemini:text-embedding-004:768:a3f2b9c1d4e5...
    """

    def __init__(self):
        """Initialize Redis connection from settings."""
        self.redis_client = redis.from_url(
            settings.redis_url_str,
            password=settings.redis_password,
            decode_responses=False  # Store bytes for embeddings
        )

        # Cache statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "total_requests": 0
        }

    def get_cached_embedding(
        self,
        text: str,
        provider: str,
        model: str,
        dimensions: int
    ) -> Optional[List[float]]:
        """Retrieve embedding from cache.

        Args:
            text: Text content to look up
            provider: Embedding provider (gemini, openai)
            model: Model name
            dimensions: Embedding dimensions

        Returns:
            Cached embedding vector or None if not found
        """
        cache_key = self._generate_cache_key(text, provider, model, dimensions)

        try:
            cached_data = self.redis_client.get(cache_key)

            if cached_data:
                # Cache hit
                self.stats["hits"] += 1
                self.stats["total_requests"] += 1

                # Deserialize embedding
                embedding = json.loads(cached_data)
                return embedding
            else:
                # Cache miss
                self.stats["misses"] += 1
                self.stats["total_requests"] += 1
                return None

        except Exception as e:
            # Cache errors should not break the application
            print(f"Cache retrieval error: {e}")
            self.stats["misses"] += 1
            self.stats["total_requests"] += 1
            return None

    def cache_embedding(
        self,
        text: str,
        embedding: List[float],
        provider: str,
        model: str,
        dimensions: int,
        ttl_days: int = 7
    ) -> None:
        """Cache an embedding vector.

        Args:
            text: Text content
            embedding: Embedding vector to cache
            provider: Embedding provider
            model: Model name
            dimensions: Embedding dimensions
            ttl_days: Time-to-live in days (7 for queries, 0 for documents = permanent)
        """
        cache_key = self._generate_cache_key(text, provider, model, dimensions)

        try:
            # Serialize embedding as JSON
            cached_data = json.dumps(embedding)

            # Set with TTL (0 = no expiration)
            if ttl_days > 0:
                self.redis_client.setex(
                    name=cache_key,
                    time=ttl_days * 24 * 3600,  # Convert days to seconds
                    value=cached_data
                )
            else:
                # Permanent storage for document embeddings
                self.redis_client.set(cache_key, cached_data)

        except Exception as e:
            # Cache errors should not break the application
            print(f"Cache write error: {e}")

    def get_cache_stats(self) -> Dict[str, float]:
        """Get cache performance statistics.

        Returns:
            Dictionary with:
            - hit_rate: Cache hit percentage (0-100)
            - hits: Total cache hits
            - misses: Total cache misses
            - total_requests: Total cache lookups
        """
        if self.stats["total_requests"] == 0:
            hit_rate = 0.0
        else:
            hit_rate = (self.stats["hits"] / self.stats["total_requests"]) * 100

        return {
            "hit_rate": round(hit_rate, 2),
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "total_requests": self.stats["total_requests"]
        }

    def clear_stats(self) -> None:
        """Reset cache statistics."""
        self.stats = {
            "hits": 0,
            "misses": 0,
            "total_requests": 0
        }

    def _generate_cache_key(
        self,
        text: str,
        provider: str,
        model: str,
        dimensions: int
    ) -> str:
        """Generate cache key from content hash.

        Uses SHA256 for collision resistance and consistent hashing.

        Format: embedding:{provider}:{model}:{dimensions}:{content_hash}
        """
        # Hash the text content
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

        # Build cache key
        cache_key = f"embedding:{provider}:{model}:{dimensions}:{content_hash}"

        return cache_key

    def invalidate_cache(self, pattern: str = "embedding:*") -> int:
        """Invalidate cache entries matching pattern.

        Args:
            pattern: Redis key pattern (default: all embeddings)

        Returns:
            Number of keys deleted
        """
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                return deleted
            return 0
        except Exception as e:
            print(f"Cache invalidation error: {e}")
            return 0
```

#### Integration with EmbeddingService

**File Modification:** `/Users/xavierau/Code/python/new_ai_auditing/genreport/core/retrieval/embedding_service.py`

```python
# Add to EmbeddingService.__init__():
from genreport.core.retrieval.embedding_cache import EmbeddingCache

class EmbeddingService:
    def __init__(self, ..., enable_cache: bool = True):
        # ... existing initialization ...

        # Initialize cache
        self.enable_cache = enable_cache
        self.cache = EmbeddingCache() if enable_cache else None

# Modify generate_embedding():
def generate_embedding(
    self, text: str, task_type: Optional[str] = "RETRIEVAL_DOCUMENT"
) -> List[float]:
    """Generate embedding with cache support."""

    # Check cache first
    if self.cache:
        cached_embedding = self.cache.get_cached_embedding(
            text=text,
            provider=self.provider_name,
            model=self.model,
            dimensions=self.dimensions
        )

        if cached_embedding is not None:
            return cached_embedding

    # Cache miss - generate embedding
    embedding = self.provider.generate_embedding(text, task_type)

    # Cache the result
    if self.cache:
        # Query embeddings: 7-day TTL
        # Document embeddings: Permanent (ttl_days=0)
        ttl_days = 7 if task_type == "RETRIEVAL_QUERY" else 0

        self.cache.cache_embedding(
            text=text,
            embedding=embedding,
            provider=self.provider_name,
            model=self.model,
            dimensions=self.dimensions,
            ttl_days=ttl_days
        )

    return embedding
```

#### Method Signatures Summary
```python
class EmbeddingCache:
    def __init__(self)
    def get_cached_embedding(self, text: str, provider: str, model: str, dimensions: int) -> Optional[List[float]]
    def cache_embedding(self, text: str, embedding: List[float], provider: str, model: str,
                       dimensions: int, ttl_days: int = 7) -> None
    def get_cache_stats(self) -> Dict[str, float]
    def clear_stats(self) -> None
    def _generate_cache_key(self, text: str, provider: str, model: str, dimensions: int) -> str
    def invalidate_cache(self, pattern: str = "embedding:*") -> int
```

---

### 4. ChunkCategorizer: DSPy Semi-Automated Approval

**File:** `/Users/xavierau/Code/python/new_ai_auditing/genreport/core/retrieval/chunk_categorizer.py`

#### Architecture Decision
- **Pattern:** DSPy signature with Chain-of-Thought reasoning
- **Rationale:** LLM-powered chunk classification with confidence scoring for auto-approval
- **Dependencies:** DSPy, Pydantic (type safety)

#### DSPy Signature Design

```python
from typing import List
from pydantic import BaseModel, Field
import dspy


class ChunkCategorizationResult(BaseModel):
    """Type-safe output for chunk categorization.

    ARCHITECTURE: Pydantic model ensures type safety and validation
    for DSPy signature outputs.
    """
    chunk_type: str = Field(
        ...,
        description="Chunk category: definition|requirement|example|guidance|disclosure|measurement"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score 0.0-1.0 for auto-approval"
    )
    keywords: List[str] = Field(
        ...,
        description="Key accounting concepts extracted from chunk"
    )
    reasoning: str = Field(
        ...,
        description="Explanation for categorization decision"
    )


class ChunkCategorizerSignature(dspy.Signature):
    """Categorize KB chunks for semi-automated ingestion.

    INPUT: Chunk content with surrounding context
    OUTPUT: Category, confidence, keywords, reasoning

    AUTO-APPROVAL THRESHOLD: 0.85 confidence
    TARGET: 80% auto-approval rate
    """

    # Input fields
    content: str = dspy.InputField(
        desc="Main chunk content to categorize"
    )
    context_before: str = dspy.InputField(
        desc="Previous chunk content for context (if available)"
    )
    context_after: str = dspy.InputField(
        desc="Next chunk content for context (if available)"
    )
    standard: str = dspy.InputField(
        desc="Accounting standard (e.g., HKFRS 15, SME-FRS)"
    )

    # Output fields (Pydantic model ensures type safety)
    chunk_type: str = dspy.OutputField(
        desc="Category: definition|requirement|example|guidance|disclosure|measurement"
    )
    confidence: float = dspy.OutputField(
        desc="Confidence score 0.0 to 1.0 for auto-approval decision"
    )
    keywords: str = dspy.OutputField(
        desc="Comma-separated key accounting concepts (max 5)"
    )
    reasoning: str = dspy.OutputField(
        desc="Brief explanation for this categorization"
    )


class ChunkCategorizer:
    """DSPy-powered chunk categorization for KB ingestion.

    ARCHITECTURE: Chain-of-Thought reasoning improves accuracy
    and provides explainability for manual review.

    AUTO-APPROVAL LOGIC:
    - Confidence >= 0.85: Auto-approve
    - Confidence < 0.85: Flag for manual review

    SOLID Compliance:
    - SRP: Handles only chunk categorization
    - OCP: Can be extended with custom reasoning modules
    - DIP: Depends on DSPy abstraction
    """

    AUTO_APPROVE_THRESHOLD = 0.85

    def __init__(self):
        """Initialize DSPy categorizer with Chain-of-Thought."""
        self.categorizer = dspy.ChainOfThought(ChunkCategorizerSignature)

    def categorize(
        self,
        content: str,
        context_before: str = "",
        context_after: str = "",
        standard: str = "Unknown"
    ) -> ChunkCategorizationResult:
        """Categorize a single chunk.

        Args:
            content: Main chunk content
            context_before: Previous chunk (for context)
            context_after: Next chunk (for context)
            standard: Accounting standard name

        Returns:
            ChunkCategorizationResult with type, confidence, keywords

        Raises:
            ValueError: If content is empty
        """
        if not content or not content.strip():
            raise ValueError("Content cannot be empty")

        # Run DSPy categorization
        result = self.categorizer(
            content=content,
            context_before=context_before,
            context_after=context_after,
            standard=standard
        )

        # Parse keywords (comma-separated to list)
        keywords_list = [
            kw.strip() for kw in result.keywords.split(",")
            if kw.strip()
        ][:5]  # Limit to 5 keywords

        # Build validated result
        return ChunkCategorizationResult(
            chunk_type=result.chunk_type.lower(),
            confidence=float(result.confidence),
            keywords=keywords_list,
            reasoning=result.reasoning
        )

    def should_auto_approve(self, confidence: float) -> bool:
        """Determine if chunk should be auto-approved.

        Args:
            confidence: Confidence score from categorization

        Returns:
            True if confidence >= threshold
        """
        return confidence >= self.AUTO_APPROVE_THRESHOLD

    def categorize_batch(
        self,
        chunks: List[Dict],
        standard: str = "Unknown"
    ) -> List[ChunkCategorizationResult]:
        """Categorize multiple chunks.

        Args:
            chunks: List of dicts with 'content', 'context_before', 'context_after'
            standard: Accounting standard name

        Returns:
            List of categorization results
        """
        results = []

        for chunk in chunks:
            try:
                result = self.categorize(
                    content=chunk["content"],
                    context_before=chunk.get("context_before", ""),
                    context_after=chunk.get("context_after", ""),
                    standard=standard
                )
                results.append(result)
            except Exception as e:
                # Log error but continue processing
                print(f"Error categorizing chunk: {e}")
                # Return low-confidence result for manual review
                results.append(ChunkCategorizationResult(
                    chunk_type="unknown",
                    confidence=0.0,
                    keywords=[],
                    reasoning=f"Categorization failed: {str(e)}"
                ))

        return results
```

#### Integration with KB Ingestion Service

**File Modification:** `/Users/xavierau/Code/python/new_ai_auditing/genreport/core/retrieval/kb_ingestion_service.py`

```python
# Add to imports:
from genreport.core.retrieval.chunk_categorizer import ChunkCategorizer

# Modify KBIngestionService.__init__():
def __init__(self, db: Session, enable_auto_categorization: bool = False):
    self.db = db
    self.pdf_extractor = PDFExtractor()
    self.chunker = ChunkingService(chunk_size=1000, chunk_overlap=200)
    self.embedding_service = EmbeddingService()

    # Optional: Enable DSPy categorization
    self.enable_auto_categorization = enable_auto_categorization
    self.categorizer = ChunkCategorizer() if enable_auto_categorization else None

# Add new method for enhanced ingestion:
def ingest_pdf_with_categorization(
    self,
    pdf_path: str | Path,
    title: str,
    jurisdiction: str,
    standard: Optional[str] = None,
    document_type: str = "standard",
    tenant_id: Optional[UUID] = None,
) -> Dict[str, int]:
    """Ingest PDF with automatic chunk categorization.

    Returns:
        Statistics dict with auto_approved and needs_review counts
    """
    # ... existing extraction and chunking code ...

    # Categorize chunks if enabled
    if self.categorizer:
        categorization_results = self.categorizer.categorize_batch(
            chunks=[
                {
                    "content": chunk.content,
                    "context_before": text_chunks[i-1].content if i > 0 else "",
                    "context_after": text_chunks[i+1].content if i < len(text_chunks)-1 else ""
                }
                for i, chunk in enumerate(text_chunks)
            ],
            standard=standard or "Unknown"
        )
    else:
        categorization_results = None

    # Store chunks with categorization
    auto_approved_count = 0
    needs_review_count = 0

    for i, (chunk, embedding) in enumerate(zip(text_chunks, embeddings)):
        # Get categorization result if available
        if categorization_results:
            cat_result = categorization_results[i]
            chunk_type = cat_result.chunk_type
            confidence_score = cat_result.confidence
            review_status = (
                "auto_approved"
                if self.categorizer.should_auto_approve(cat_result.confidence)
                else "pending_review"
            )

            if review_status == "auto_approved":
                auto_approved_count += 1
            else:
                needs_review_count += 1
        else:
            # Default values if categorization disabled
            chunk_type = None
            confidence_score = 1.0
            review_status = "auto_approved"
            auto_approved_count += 1

        kb_chunk = KBChunk(
            tenant_id=tenant_id,
            jurisdiction=jurisdiction,
            kb_document_id=kb_document.id,
            chunk_index=chunk.chunk_index,
            chunk_type=chunk_type,
            content=chunk.content,
            embedding=embedding,
            embedding_model=self.embedding_service.get_model_name(),
            confidence_score=confidence_score,
            review_status=review_status,
            chunk_metadata={
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,
                "char_count": len(chunk.content),
                "embedding_provider": self.embedding_service.get_provider_name(),
                "embedding_dimensions": self.embedding_service.get_dimensions(),
            },
        )
        self.db.add(kb_chunk)

    self.db.commit()

    return {
        "total_chunks": len(text_chunks),
        "auto_approved": auto_approved_count,
        "needs_review": needs_review_count,
        "approval_rate": (auto_approved_count / len(text_chunks)) * 100
    }
```

---

### 5. KB API Endpoints

**File:** `/Users/xavierau/Code/python/new_ai_auditing/genreport/api/routers/knowledge_base.py`

#### Architecture Decision
- **Pattern:** RESTful API with FastAPI dependency injection
- **Rationale:** Standard HTTP interface for KB operations with proper error handling
- **Dependencies:** SecureKBRetriever, ChunkCategorizer, authentication middleware

#### Route Design

```python
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from genreport.core.database.base import get_db
from genreport.core.security.tenant_context import get_current_tenant
from genreport.core.retrieval.secure_kb_retriever import SecureKBRetriever
from genreport.core.retrieval.kb_ingestion_service import KBIngestionService
from genreport.core.database.models import KnowledgeBase, KBChunk, User
from genreport.api.dependencies.auth import get_current_user


router = APIRouter(prefix="/api/v1/kb", tags=["Knowledge Base"])


# ============================================================================
# Pydantic Models
# ============================================================================

class KBSearchRequest(BaseModel):
    """Request model for KB search."""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    top_k: int = Field(5, ge=1, le=20, description="Number of results")
    min_similarity: float = Field(0.5, ge=0.0, le=1.0, description="Minimum similarity score")
    chunk_types: Optional[List[str]] = Field(None, description="Filter by chunk types")
    standards: Optional[List[str]] = Field(None, description="Filter by accounting standards")


class KBSearchResult(BaseModel):
    """Response model for KB search result."""
    chunk_id: int
    content: str
    similarity_score: float
    kb_document_id: int
    jurisdiction: str
    chunk_type: Optional[str]
    metadata: dict


class KBSearchResponse(BaseModel):
    """Response model for KB search."""
    results: List[KBSearchResult]
    query: str
    jurisdiction: str
    total_results: int


class KBDocumentResponse(BaseModel):
    """Response model for KB document."""
    id: int
    tenant_id: Optional[UUID]
    jurisdiction: str
    title: str
    standard: Optional[str]
    version: Optional[str]
    document_type: Optional[str]
    is_active: bool
    created_at: str
    updated_at: str


class KBIngestionRequest(BaseModel):
    """Request model for KB ingestion."""
    title: str = Field(..., min_length=1, max_length=255)
    jurisdiction: str = Field(..., pattern="^(HK|SG|AU)$")
    standard: Optional[str] = Field(None, max_length=100)
    document_type: str = Field("standard", max_length=50)


class KBIngestionResponse(BaseModel):
    """Response model for KB ingestion."""
    kb_document_id: int
    total_chunks: int
    auto_approved: int
    needs_review: int
    approval_rate: float


class ChunkReviewRequest(BaseModel):
    """Request model for chunk review."""
    approved: bool
    chunk_type: Optional[str] = None


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/search", response_model=KBSearchResponse)
async def search_knowledge_base(
    request: KBSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant)
):
    """Search knowledge base with semantic similarity.

    SECURITY:
    - Requires authentication (JWT)
    - Enforces tenant isolation
    - Filters by user access permissions
    - Audit logs all searches

    PERFORMANCE:
    - Uses Redis embedding cache
    - Target response time: <500ms
    """
    try:
        # Get project jurisdiction from user context (or default to tenant jurisdiction)
        # TODO: Get jurisdiction from project_id parameter
        jurisdiction = "HK"  # Placeholder - should come from project context

        # Initialize secure retriever
        retriever = SecureKBRetriever(
            db=db,
            jurisdiction=jurisdiction,
            tenant_id=tenant_id,
            user_id=current_user.id
        )

        # Perform search
        results = retriever.retrieve(
            query=request.query,
            top_k=request.top_k,
            min_similarity=request.min_similarity,
            chunk_types=request.chunk_types,
            standards=request.standards
        )

        # Format response
        return KBSearchResponse(
            results=[KBSearchResult(**result) for result in results],
            query=request.query,
            jurisdiction=jurisdiction,
            total_results=len(results)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/documents", response_model=List[KBDocumentResponse])
async def list_kb_documents(
    jurisdiction: Optional[str] = None,
    standard: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant)
):
    """List KB documents accessible to current user/tenant.

    SECURITY:
    - Returns PUBLIC documents + tenant-specific documents
    - Filters by jurisdiction if specified
    """
    query = db.query(KnowledgeBase).filter(
        KnowledgeBase.is_active == True
    )

    # Filter by jurisdiction if specified
    if jurisdiction:
        query = query.filter(KnowledgeBase.jurisdiction == jurisdiction.upper())

    # Filter by standard if specified
    if standard:
        query = query.filter(KnowledgeBase.standard == standard)

    # Filter by access permissions
    query = query.filter(
        (KnowledgeBase.tenant_id == tenant_id) | (KnowledgeBase.tenant_id.is_(None))
    )

    # Paginate
    documents = query.offset(skip).limit(limit).all()

    return [
        KBDocumentResponse(
            id=doc.id,
            tenant_id=doc.tenant_id,
            jurisdiction=doc.jurisdiction,
            title=doc.title,
            standard=doc.standard,
            version=doc.version,
            document_type=doc.document_type,
            is_active=doc.is_active,
            created_at=doc.created_at.isoformat(),
            updated_at=doc.updated_at.isoformat()
        )
        for doc in documents
    ]


@router.get("/documents/{document_id}", response_model=KBDocumentResponse)
async def get_kb_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant)
):
    """Get KB document by ID with access control."""
    document = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == document_id,
        KnowledgeBase.is_active == True
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Check access permissions
    if document.tenant_id is not None and document.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this document"
        )

    return KBDocumentResponse(
        id=document.id,
        tenant_id=document.tenant_id,
        jurisdiction=document.jurisdiction,
        title=document.title,
        standard=document.standard,
        version=document.version,
        document_type=document.document_type,
        is_active=document.is_active,
        created_at=document.created_at.isoformat(),
        updated_at=document.updated_at.isoformat()
    )


@router.post("/ingest", response_model=KBIngestionResponse)
async def ingest_kb_document(
    file: UploadFile = File(...),
    metadata: KBIngestionRequest = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant)
):
    """Ingest new KB document (admin only).

    SECURITY:
    - Admin role required (future implementation)
    - File validation (PDF only, max 50MB)
    - Virus scanning (future implementation)

    PROCESSING:
    - PDF extraction → Chunking → Embedding → Categorization
    - Auto-approves chunks with confidence >= 0.85
    """
    # TODO: Check admin role
    # if current_user.role != "admin":
    #     raise HTTPException(status_code=403, detail="Admin access required")

    # Validate file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported"
        )

    # Save uploaded file temporarily
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_file_path = tmp_file.name

    try:
        # Initialize ingestion service with categorization
        ingestion_service = KBIngestionService(
            db=db,
            enable_auto_categorization=True
        )

        # Ingest document
        stats = ingestion_service.ingest_pdf_with_categorization(
            pdf_path=tmp_file_path,
            title=metadata.title,
            jurisdiction=metadata.jurisdiction,
            standard=metadata.standard,
            document_type=metadata.document_type,
            tenant_id=tenant_id if metadata.document_type == "tenant_specific" else None
        )

        return KBIngestionResponse(**stats)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}"
        )
    finally:
        # Clean up temporary file
        import os
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)


@router.get("/pending-review", response_model=List[dict])
async def list_pending_chunks(
    jurisdiction: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant)
):
    """List chunks pending manual review (admin only)."""
    # TODO: Check admin role

    query = db.query(KBChunk).filter(
        KBChunk.review_status == "pending_review"
    )

    # Filter by jurisdiction if specified
    if jurisdiction:
        query = query.filter(KBChunk.jurisdiction == jurisdiction.upper())

    # Filter by tenant
    query = query.filter(
        (KBChunk.tenant_id == tenant_id) | (KBChunk.tenant_id.is_(None))
    )

    chunks = query.order_by(KBChunk.confidence_score.desc()).offset(skip).limit(limit).all()

    return [
        {
            "chunk_id": chunk.id,
            "kb_document_id": chunk.kb_document_id,
            "content": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
            "chunk_type": chunk.chunk_type,
            "confidence_score": chunk.confidence_score,
            "jurisdiction": chunk.jurisdiction
        }
        for chunk in chunks
    ]


@router.post("/review/{chunk_id}")
async def review_chunk(
    chunk_id: int,
    review: ChunkReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant)
):
    """Approve or reject a chunk (admin only)."""
    # TODO: Check admin role

    chunk = db.query(KBChunk).filter(KBChunk.id == chunk_id).first()

    if not chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chunk not found"
        )

    # Check access permissions
    if chunk.tenant_id is not None and chunk.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Update review status
    if review.approved:
        chunk.review_status = "reviewed"
        if review.chunk_type:
            chunk.chunk_type = review.chunk_type
        chunk.reviewed_by = current_user.id
        chunk.reviewed_at = datetime.utcnow()
    else:
        # Reject: mark as inactive
        chunk.review_status = "rejected"
        chunk.reviewed_by = current_user.id
        chunk.reviewed_at = datetime.utcnow()

    db.commit()

    return {"status": "success", "chunk_id": chunk_id, "review_status": chunk.review_status}


@router.delete("/documents/{document_id}")
async def delete_kb_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant)
):
    """Soft-delete KB document (admin only)."""
    # TODO: Check admin role

    document = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == document_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Check access permissions
    if document.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Soft delete
    document.is_active = False
    db.commit()

    return {"status": "success", "document_id": document_id}
```

---

## Testing Strategy

### Test Organization

```
tests/
├── core/
│   └── retrieval/
│       ├── test_kb_retriever.py          # Unit tests
│       ├── test_secure_kb_retriever.py   # Security tests
│       ├── test_embedding_cache.py       # Cache tests
│       ├── test_chunk_categorizer.py     # DSPy tests
│       └── test_kb_integration.py        # Integration tests
│
└── api/
    └── test_knowledge_base_api.py        # API tests
```

### Test Implementation Plan

#### 1. Unit Tests for KBRetriever

**File:** `/Users/xavierau/Code/python/new_ai_auditing/tests/core/retrieval/test_kb_retriever.py`

```python
import pytest
from uuid import uuid4
from genreport.core.retrieval.kb_retriever import KBRetriever
from genreport.core.database.models import KnowledgeBase, KBChunk


def test_retrieve_filters_by_jurisdiction(db_session):
    """Ensure KB retrieval respects jurisdiction boundaries."""
    # Arrange: Create HK and SG chunks
    hk_kb = create_kb_document(db_session, jurisdiction="HK", standard="HKFRS 15")
    sg_kb = create_kb_document(db_session, jurisdiction="SG", standard="SFRS 15")

    hk_chunk = create_kb_chunk(db_session, kb_document_id=hk_kb.id, jurisdiction="HK", content="HK revenue recognition")
    sg_chunk = create_kb_chunk(db_session, kb_document_id=sg_kb.id, jurisdiction="SG", content="SG revenue recognition")

    # Act: Retrieve from HK jurisdiction
    retriever = KBRetriever(db_session, jurisdiction="HK")
    results = retriever.retrieve("revenue recognition")

    # Assert: Only HK chunks returned
    assert all(r["jurisdiction"] == "HK" for r in results)
    assert hk_chunk.id in [r["chunk_id"] for r in results]
    assert sg_chunk.id not in [r["chunk_id"] for r in results]


def test_retrieve_filters_approved_chunks_only(db_session):
    """Ensure only approved chunks are returned."""
    # Arrange: Create approved and pending chunks
    kb = create_kb_document(db_session, jurisdiction="HK")
    approved = create_kb_chunk(db_session, kb_document_id=kb.id, review_status="auto_approved")
    pending = create_kb_chunk(db_session, kb_document_id=kb.id, review_status="pending_review")

    # Act
    retriever = KBRetriever(db_session, jurisdiction="HK")
    results = retriever.retrieve("test query")

    # Assert: Only approved chunks
    chunk_ids = [r["chunk_id"] for r in results]
    assert approved.id in chunk_ids
    assert pending.id not in chunk_ids


def test_retrieve_by_standard_filters_correctly(db_session):
    """Test retrieve_by_standard convenience method."""
    # Arrange
    hkfrs15 = create_kb_document(db_session, jurisdiction="HK", standard="HKFRS 15")
    smefrs = create_kb_document(db_session, jurisdiction="HK", standard="SME-FRS")

    hkfrs15_chunk = create_kb_chunk(db_session, kb_document_id=hkfrs15.id)
    smefrs_chunk = create_kb_chunk(db_session, kb_document_id=smefrs.id)

    # Act
    retriever = KBRetriever(db_session, jurisdiction="HK")
    results = retriever.retrieve_by_standard("HKFRS 15", "revenue")

    # Assert: Only HKFRS 15 chunks
    assert hkfrs15_chunk.id in [r["chunk_id"] for r in results]
    assert smefrs_chunk.id not in [r["chunk_id"] for r in results]


def test_retrieve_raises_on_empty_query(db_session):
    """Test validation for empty query."""
    retriever = KBRetriever(db_session, jurisdiction="HK")

    with pytest.raises(ValueError, match="Query cannot be empty"):
        retriever.retrieve("")


def test_retrieve_raises_on_invalid_jurisdiction(db_session):
    """Test validation for invalid jurisdiction."""
    with pytest.raises(ValueError, match="Invalid jurisdiction"):
        KBRetriever(db_session, jurisdiction="INVALID")
```

#### 2. Security Tests for SecureKBRetriever

**File:** `/Users/xavierau/Code/python/new_ai_auditing/tests/core/retrieval/test_secure_kb_retriever.py`

```python
import pytest
from uuid import uuid4
from genreport.core.retrieval.secure_kb_retriever import SecureKBRetriever
from genreport.core.database.models import AuditLog


def test_tenant_isolation_public_documents(db_session):
    """PUBLIC documents accessible to all tenants."""
    tenant_a = uuid4()
    tenant_b = uuid4()

    # Arrange: Create PUBLIC document
    public_kb = create_kb_document(db_session, tenant_id=None, access_level="PUBLIC", jurisdiction="HK")
    public_chunk = create_kb_chunk(db_session, kb_document_id=public_kb.id, tenant_id=None, jurisdiction="HK")

    # Act: Access from both tenants
    retriever_a = SecureKBRetriever(db_session, "HK", tenant_a, user_id=1)
    retriever_b = SecureKBRetriever(db_session, "HK", tenant_b, user_id=2)

    results_a = retriever_a.retrieve("test")
    results_b = retriever_b.retrieve("test")

    # Assert: Both tenants can access PUBLIC document
    assert public_chunk.id in [r["chunk_id"] for r in results_a]
    assert public_chunk.id in [r["chunk_id"] for r in results_b]


def test_tenant_isolation_tenant_documents(db_session):
    """TENANT documents only accessible to owning tenant."""
    tenant_a = uuid4()
    tenant_b = uuid4()

    # Arrange: Create tenant-specific document
    tenant_a_kb = create_kb_document(db_session, tenant_id=tenant_a, jurisdiction="HK")
    tenant_a_chunk = create_kb_chunk(db_session, kb_document_id=tenant_a_kb.id, tenant_id=tenant_a, jurisdiction="HK")

    # Act: Try to access from both tenants
    retriever_a = SecureKBRetriever(db_session, "HK", tenant_a, user_id=1)
    retriever_b = SecureKBRetriever(db_session, "HK", tenant_b, user_id=2)

    results_a = retriever_a.retrieve("test")
    results_b = retriever_b.retrieve("test")

    # Assert: Only tenant A can access
    assert tenant_a_chunk.id in [r["chunk_id"] for r in results_a]
    assert tenant_a_chunk.id not in [r["chunk_id"] for r in results_b]


def test_audit_logging_on_retrieval(db_session):
    """Ensure all retrievals are audit logged."""
    tenant_id = uuid4()
    user_id = 1

    # Act: Perform retrieval
    retriever = SecureKBRetriever(db_session, "HK", tenant_id, user_id)
    retriever.retrieve("test query")

    # Assert: Audit log created
    logs = db_session.query(AuditLog).filter(
        AuditLog.event_type == "KB_RETRIEVAL",
        AuditLog.user_id == user_id,
        AuditLog.tenant_id == tenant_id
    ).all()

    assert len(logs) > 0
    assert logs[-1].details["query"] == "test query"
    assert logs[-1].details["jurisdiction"] == "HK"
    assert logs[-1].status == "SUCCESS"


def test_audit_logging_on_failure(db_session):
    """Ensure failed retrievals are logged."""
    tenant_id = uuid4()
    user_id = 1

    # Arrange: Create retriever with invalid configuration
    retriever = SecureKBRetriever(db_session, "INVALID", tenant_id, user_id)

    # Act & Assert: Retrieval fails and is logged
    with pytest.raises(Exception):
        retriever.retrieve("test")

    logs = db_session.query(AuditLog).filter(
        AuditLog.event_type == "KB_RETRIEVAL",
        AuditLog.status == "FAILURE"
    ).all()

    assert len(logs) > 0
```

#### 3. Cache Tests for EmbeddingCache

**File:** `/Users/xavierau/Code/python/new_ai_auditing/tests/core/retrieval/test_embedding_cache.py`

```python
import pytest
from genreport.core.retrieval.embedding_cache import EmbeddingCache


def test_cache_miss_returns_none(redis_client):
    """Test cache miss returns None."""
    cache = EmbeddingCache()

    result = cache.get_cached_embedding(
        text="uncached content",
        provider="gemini",
        model="text-embedding-004",
        dimensions=768
    )

    assert result is None
    stats = cache.get_cache_stats()
    assert stats["misses"] == 1


def test_cache_hit_returns_embedding(redis_client):
    """Test cache hit returns correct embedding."""
    cache = EmbeddingCache()
    test_embedding = [0.1, 0.2, 0.3]

    # Cache embedding
    cache.cache_embedding(
        text="test content",
        embedding=test_embedding,
        provider="gemini",
        model="text-embedding-004",
        dimensions=768
    )

    # Retrieve from cache
    result = cache.get_cached_embedding(
        text="test content",
        provider="gemini",
        model="text-embedding-004",
        dimensions=768
    )

    assert result == test_embedding
    stats = cache.get_cache_stats()
    assert stats["hits"] == 1


def test_cache_key_consistency(redis_client):
    """Test same content generates same cache key."""
    cache = EmbeddingCache()

    key1 = cache._generate_cache_key("test", "gemini", "model", 768)
    key2 = cache._generate_cache_key("test", "gemini", "model", 768)

    assert key1 == key2


def test_cache_hit_rate_calculation(redis_client):
    """Test cache statistics accuracy."""
    cache = EmbeddingCache()

    # 3 misses
    for i in range(3):
        cache.get_cached_embedding(f"text{i}", "gemini", "model", 768)

    # Cache 3 embeddings
    for i in range(3):
        cache.cache_embedding(f"text{i}", [0.1, 0.2], "gemini", "model", 768)

    # 2 hits
    cache.get_cached_embedding("text0", "gemini", "model", 768)
    cache.get_cached_embedding("text1", "gemini", "model", 768)

    stats = cache.get_cache_stats()
    assert stats["hits"] == 2
    assert stats["misses"] == 3
    assert stats["hit_rate"] == 40.0  # 2 / 5 = 40%
```

#### 4. DSPy Tests for ChunkCategorizer

**File:** `/Users/xavierau/Code/python/new_ai_auditing/tests/core/retrieval/test_chunk_categorizer.py`

```python
import pytest
from genreport.core.retrieval.chunk_categorizer import ChunkCategorizer, ChunkCategorizationResult


def test_categorizer_returns_valid_result():
    """Test categorizer produces valid result."""
    categorizer = ChunkCategorizer()

    result = categorizer.categorize(
        content="Revenue is recognized when control of goods is transferred to the customer.",
        context_before="HKFRS 15 establishes principles for reporting.",
        context_after="The transaction price is allocated to performance obligations.",
        standard="HKFRS 15"
    )

    assert isinstance(result, ChunkCategorizationResult)
    assert result.chunk_type in ["definition", "requirement", "example", "guidance", "disclosure", "measurement"]
    assert 0.0 <= result.confidence <= 1.0
    assert len(result.keywords) > 0


def test_auto_approval_threshold():
    """Test auto-approval logic."""
    categorizer = ChunkCategorizer()

    assert categorizer.should_auto_approve(0.85) == True
    assert categorizer.should_auto_approve(0.90) == True
    assert categorizer.should_auto_approve(0.84) == False
    assert categorizer.should_auto_approve(0.50) == False


def test_categorize_raises_on_empty_content():
    """Test validation for empty content."""
    categorizer = ChunkCategorizer()

    with pytest.raises(ValueError, match="Content cannot be empty"):
        categorizer.categorize("")


def test_categorize_batch():
    """Test batch categorization."""
    categorizer = ChunkCategorizer()

    chunks = [
        {"content": "Revenue is recognized...", "context_before": "", "context_after": ""},
        {"content": "Lease liability is measured...", "context_before": "", "context_after": ""}
    ]

    results = categorizer.categorize_batch(chunks, standard="HKFRS")

    assert len(results) == 2
    assert all(isinstance(r, ChunkCategorizationResult) for r in results)
```

#### 5. Integration Tests

**File:** `/Users/xavierau/Code/python/new_ai_auditing/tests/core/retrieval/test_kb_integration.py`

```python
import pytest
from uuid import uuid4
from genreport.core.retrieval.kb_ingestion_service import KBIngestionService
from genreport.core.retrieval.secure_kb_retriever import SecureKBRetriever


def test_end_to_end_ingestion_and_retrieval(db_session, test_pdf_path):
    """Test complete workflow: ingest PDF → retrieve chunks."""
    tenant_id = uuid4()

    # Step 1: Ingest PDF
    ingestion_service = KBIngestionService(db_session, enable_auto_categorization=True)
    stats = ingestion_service.ingest_pdf_with_categorization(
        pdf_path=test_pdf_path,
        title="Test Standard",
        jurisdiction="HK",
        standard="HKFRS 15",
        tenant_id=tenant_id
    )

    assert stats["total_chunks"] > 0
    assert stats["auto_approved"] > 0

    # Step 2: Retrieve chunks
    retriever = SecureKBRetriever(db_session, "HK", tenant_id, user_id=1)
    results = retriever.retrieve("revenue recognition")

    assert len(results) > 0
    assert all(r["jurisdiction"] == "HK" for r in results)


def test_retrieval_accuracy_with_embeddings(db_session):
    """Test retrieval accuracy with real embeddings."""
    # Arrange: Create semantically similar and dissimilar chunks
    kb = create_kb_document(db_session, jurisdiction="HK")

    relevant_chunk = create_kb_chunk(
        db_session,
        kb_document_id=kb.id,
        content="Revenue is recognized when control is transferred",
        embedding=generate_test_embedding("revenue recognition control transfer")
    )

    irrelevant_chunk = create_kb_chunk(
        db_session,
        kb_document_id=kb.id,
        content="The sky is blue and grass is green",
        embedding=generate_test_embedding("sky blue grass green")
    )

    # Act: Retrieve with revenue query
    retriever = SecureKBRetriever(db_session, "HK", uuid4(), user_id=1)
    results = retriever.retrieve("revenue recognition", min_similarity=0.5)

    # Assert: Relevant chunk ranked higher
    assert results[0]["chunk_id"] == relevant_chunk.id
    assert irrelevant_chunk.id not in [r["chunk_id"] for r in results]


def test_cache_improves_performance(db_session):
    """Test embedding cache reduces API calls."""
    retriever = SecureKBRetriever(db_session, "HK", uuid4(), user_id=1)

    # First retrieval (cache miss)
    import time
    start = time.time()
    retriever.retrieve("revenue recognition")
    first_duration = time.time() - start

    # Second retrieval (cache hit)
    start = time.time()
    retriever.retrieve("revenue recognition")
    second_duration = time.time() - start

    # Assert: Second retrieval faster
    assert second_duration < first_duration

    # Check cache stats
    cache_stats = retriever.base_retriever.embedding_service.cache.get_cache_stats()
    assert cache_stats["hits"] > 0
```

---

## Implementation Roadmap

### Phase-by-Phase Implementation

#### Phase 1: Core Retrieval (Days 1-2, 16 hours)

**Day 1 (8 hours):**
1. Implement KBRetriever class (4h)
   - Vector similarity search logic
   - Jurisdiction filtering
   - Metadata filtering methods

2. Write unit tests for KBRetriever (4h)
   - Test jurisdiction isolation
   - Test approved chunks filtering
   - Test similarity scoring
   - Test error handling

**Day 2 (8 hours):**
3. Test and debug KBRetriever (3h)
   - Manual testing with ingested SME-FRS data
   - Performance profiling
   - Edge case testing

4. Documentation and code review (1h)

**Definition of Done:**
- [ ] KBRetriever class implemented
- [ ] All unit tests passing (>80% coverage)
- [ ] Manual testing with real data successful
- [ ] Code reviewed and approved

---

#### Phase 2: Security Layer (Days 3-4, 16 hours)

**Day 3 (8 hours):**
1. Implement SecureKBRetriever class (4h)
   - Access control filtering
   - Tenant isolation logic
   - Audit logging integration

2. Write security tests (4h)
   - Test PUBLIC document access
   - Test TENANT document isolation
   - Test audit logging completeness
   - Test cross-tenant prevention

**Day 4 (8 hours):**
3. Security hardening and testing (5h)
   - Penetration testing
   - Edge case security tests
   - Performance testing with security overhead

4. Security documentation (1h)

**Definition of Done:**
- [ ] SecureKBRetriever class implemented
- [ ] 100% security test coverage
- [ ] Audit logging verified
- [ ] Security review passed

---

#### Phase 3: Optimization & Automation (Days 5-6, 16 hours)

**Day 5 (8 hours):**
1. Implement EmbeddingCache class (3h)
   - Redis integration
   - Cache key generation
   - Statistics tracking

2. Integrate cache with EmbeddingService (2h)
   - Modify generate_embedding method
   - Add cache fallback logic

3. Write cache tests (3h)
   - Test cache hits/misses
   - Test TTL expiration
   - Test performance improvement

**Day 6 (8 hours):**
4. Implement ChunkCategorizer (DSPy) (4h)
   - DSPy signature design
   - Chain-of-Thought module
   - Batch categorization

5. Integrate with ingestion service (2h)
   - Modify ingest_pdf method
   - Add auto-approval logic

6. Write DSPy tests (2h)
   - Test categorization accuracy
   - Test auto-approval threshold
   - Test batch processing

**Definition of Done:**
- [ ] EmbeddingCache implemented and tested
- [ ] Cache hit rate >70% in tests
- [ ] ChunkCategorizer implemented
- [ ] Auto-approval rate >80% in tests
- [ ] Integration with ingestion service complete

---

#### Phase 4: API Layer (Days 7-8, 16 hours)

**Day 7 (8 hours):**
1. Implement KB API endpoints (6h)
   - POST /api/v1/kb/search
   - GET /api/v1/kb/documents
   - GET /api/v1/kb/documents/{id}
   - POST /api/v1/kb/ingest

2. Add request/response models (2h)
   - Pydantic models for validation
   - Error handling

**Day 8 (8 hours):**
3. Implement review endpoints (2h)
   - GET /api/v1/kb/pending-review
   - POST /api/v1/kb/review/{chunk_id}
   - DELETE /api/v1/kb/documents/{id}

4. Write API tests (4h)
   - Test all endpoints
   - Test authentication/authorization
   - Test error responses

5. API documentation (2h)
   - OpenAPI/Swagger docs
   - Usage examples

**Definition of Done:**
- [ ] All API endpoints implemented
- [ ] API tests passing (>80% coverage)
- [ ] Authentication/authorization working
- [ ] API documentation complete

---

#### Phase 5: Integration & Testing (Days 9-10, 16 hours)

**Day 9 (8 hours):**
1. Integration testing (5h)
   - End-to-end workflow tests
   - Performance benchmarking
   - Load testing (100 concurrent requests)

2. Bug fixes from integration testing (3h)

**Day 10 (8 hours):**
3. Performance optimization (4h)
   - Query optimization
   - Index tuning
   - Cache tuning

4. Final testing and validation (3h)
   - Regression testing
   - Security validation
   - Performance validation

5. Documentation updates (1h)

**Definition of Done:**
- [ ] All integration tests passing
- [ ] Retrieval speed <500ms
- [ ] Cache hit rate >70%
- [ ] Auto-approval rate >80%
- [ ] All documentation complete

---

## Architecture Decision Records (ADRs)

### ADR-001: PGVector for Similarity Search

**Context:**
Need efficient vector similarity search for 453+ KB chunks with jurisdiction filtering.

**Decision:**
Use PGVector extension for PostgreSQL with cosine distance operator.

**Rationale:**
1. **Performance:** Native PostgreSQL extension, no external service needed
2. **Simplicity:** Same database for metadata and vectors
3. **Filtering:** Efficient compound indexes (jurisdiction + tenant_id + vector)
4. **Scalability:** IVFFlat indexing for <1M vectors (sufficient for our use case)

**Alternatives Considered:**
- **Pinecone/Weaviate:** Added complexity, cost, and network latency
- **FAISS:** Requires separate service and synchronization
- **Elasticsearch:** Overkill for our current scale

**Consequences:**
- ✅ Simpler architecture (one database)
- ✅ Lower operational costs
- ✅ ACID guarantees for KB operations
- ⚠️ May need migration to dedicated vector DB if scale exceeds 1M chunks

---

### ADR-002: Redis for Embedding Cache

**Context:**
Embedding API calls are expensive ($0.0001 per 1K tokens). Need caching to reduce costs and improve latency.

**Decision:**
Use Redis with SHA256 content hashing for embedding cache.

**Rationale:**
1. **Cost Reduction:** 70% cache hit rate = 70% cost savings
2. **Performance:** Sub-millisecond cache lookup vs 100-300ms API call
3. **Simplicity:** Redis already required for Celery/session storage
4. **Persistence:** Redis persistence prevents cache warm-up on restart

**Alternatives Considered:**
- **In-memory cache:** Lost on restart, no sharing across workers
- **Database cache:** Slower than Redis, additional DB load

**Consequences:**
- ✅ Significant cost reduction (estimated $0.15 → $0.05 per report)
- ✅ Faster retrieval (200ms → 50ms average)
- ⚠️ Requires Redis memory management (LRU eviction policy)

---

### ADR-003: DSPy for Chunk Categorization

**Context:**
Need automated chunk categorization to reduce manual review effort (target 80% auto-approval).

**Decision:**
Use DSPy Chain-of-Thought for chunk categorization with confidence-based auto-approval.

**Rationale:**
1. **Accuracy:** CoT reasoning improves categorization quality
2. **Explainability:** Provides reasoning for manual review cases
3. **Flexibility:** Can optimize with DSPy compiler for better performance
4. **Type Safety:** Pydantic integration ensures structured outputs

**Alternatives Considered:**
- **Zero-shot prompting:** Lower accuracy, no confidence scoring
- **Fine-tuned model:** High upfront cost, maintenance burden
- **Rule-based:** Brittle, doesn't generalize across standards

**Consequences:**
- ✅ 80%+ auto-approval rate (estimated based on DSPy benchmarks)
- ✅ Explainable categorization for auditing
- ⚠️ Requires periodic optimization with golden dataset

---

### ADR-004: Decorator Pattern for Security

**Context:**
Need to add security (access control, audit logging) without modifying core retrieval logic.

**Decision:**
Use Decorator pattern (SecureKBRetriever wraps KBRetriever).

**Rationale:**
1. **SRP:** Separates retrieval logic from security concerns
2. **OCP:** Can add security features without modifying KBRetriever
3. **Testability:** Can test retrieval and security independently
4. **Flexibility:** Easy to swap or enhance security logic

**Alternatives Considered:**
- **Monolithic class:** Violates SRP, hard to test
- **Middleware pattern:** Less explicit, harder to reason about security

**Consequences:**
- ✅ Clean separation of concerns
- ✅ Independent testing of retrieval and security
- ✅ Easy to audit security logic
- ⚠️ Slight performance overhead (minimal, <5ms)

---

## Definition of Done Checklist

### Sprint 3 Remaining Components Complete When:

#### Functionality
- [ ] KB retrieval with PGVector similarity search working
- [ ] Jurisdiction filtering enforced in all queries
- [ ] SecureKBRetriever with access control functional
- [ ] Redis embedding cache with 70%+ hit rate
- [ ] DSPy chunk categorizer with 80%+ auto-approval rate
- [ ] All API endpoints functional and documented

#### Security
- [ ] Tenant isolation tested and verified
- [ ] Access control enforced (PUBLIC/TENANT/RESTRICTED)
- [ ] Audit logging complete for all KB operations
- [ ] Security tests passing with 100% coverage
- [ ] No cross-tenant data leakage in tests

#### Performance
- [ ] Retrieval speed <500ms (including embedding generation)
- [ ] Cache hit rate >70% after warm-up period
- [ ] API response time <200ms for search endpoint
- [ ] Load testing passed (100 concurrent requests)

#### Quality
- [ ] Unit test coverage >80% for all components
- [ ] Integration tests passing
- [ ] Security tests passing (100% coverage)
- [ ] Code review completed and approved
- [ ] Documentation complete (code comments + architecture docs)

#### Integration
- [ ] Works with existing Sprint 1-2 components
- [ ] Compatible with Sprint 4 agent requirements
- [ ] Database migrations applied successfully
- [ ] No breaking changes to existing APIs

---

## Risk Assessment & Mitigation

### High-Risk Items

**Risk 1: PGVector Performance Degradation at Scale**
- **Impact:** High (affects core functionality)
- **Likelihood:** Medium (depends on data growth)
- **Mitigation:**
  - Implement IVFFlat indexing after initial data load
  - Monitor query performance with `EXPLAIN ANALYZE`
  - Plan migration to dedicated vector DB if >1M chunks

**Risk 2: Cache Hit Rate Below Target (70%)**
- **Impact:** Medium (higher costs, slower retrieval)
- **Likelihood:** Low (realistic target based on query patterns)
- **Mitigation:**
  - Analyze query patterns in production
  - Adjust TTL based on actual usage
  - Implement cache pre-warming for common queries

**Risk 3: DSPy Auto-Approval Rate Below Target (80%)**
- **Impact:** Medium (more manual review required)
- **Likelihood:** Medium (depends on chunk quality)
- **Mitigation:**
  - Optimize DSPy program with evaluation dataset
  - Adjust confidence threshold based on accuracy
  - Provide clear reasoning for manual review cases

---

## Time Estimates

### Component-Level Estimates

| Component | Implementation | Testing | Documentation | Total |
|-----------|---------------|---------|---------------|-------|
| KBRetriever | 4h | 4h | 1h | 9h |
| SecureKBRetriever | 4h | 4h | 1h | 9h |
| EmbeddingCache | 3h | 3h | 1h | 7h |
| ChunkCategorizer (DSPy) | 4h | 2h | 1h | 7h |
| API Endpoints | 8h | 4h | 2h | 14h |
| Integration Testing | - | 8h | - | 8h |
| Performance Optimization | 4h | 3h | 1h | 8h |
| **Total** | **27h** | **28h** | **7h** | **62h** |

### Sprint Timeline

**Week 2 (Days 6-10):** 40 hours
- Days 1-2: Core Retrieval (16h)
- Days 3-4: Security Layer (16h)
- Days 5: Optimization (8h)

**Week 2.5 (Days 11-12):** 16 hours
- Days 6-7: Automation & API (16h)

**Buffer:** 6 hours for unexpected issues

**Total:** 62 hours (~8 days, 1.5 developers)

---

## Next Steps After Completion

1. **Sprint 4 Integration:**
   - Use SecureKBRetriever in DSPy agents
   - Implement source attribution with KB metadata
   - Build agent factory with jurisdiction-aware retrieval

2. **Production Optimization:**
   - Create IVFFlat indexes on embeddings
   - Tune PostgreSQL configuration for vector search
   - Implement Redis cluster for cache scalability

3. **Monitoring Setup:**
   - Set up cache hit rate monitoring
   - Track retrieval latency (p50, p95, p99)
   - Alert on security violations (cross-tenant attempts)

4. **Documentation:**
   - User guide for KB management
   - API documentation for frontend team
   - Runbook for operational tasks

---

**Document Version:** 1.0
**Last Updated:** 2025-10-18
**Status:** Ready for Implementation
**Estimated Completion:** 2025-10-28 (10 days)
