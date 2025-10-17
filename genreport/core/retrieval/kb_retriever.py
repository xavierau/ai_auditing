"""KB Retriever - jurisdiction-aware semantic search with PGVector.

Provides semantic search over knowledge base chunks with:
- Mandatory jurisdiction filtering
- Tenant isolation (PUBLIC + own tenant)
- Vector similarity search using PGVector
- Two-step retrieval: metadata filter → semantic ranking
"""

from typing import List, Dict, Optional
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from genreport.core.database.models import KnowledgeBase, KBChunk
from genreport.core.retrieval.embedding_service import EmbeddingService


class KBRetriever:
    """Jurisdiction-aware knowledge base retriever.

    Implements semantic search with:
    - Mandatory jurisdiction filtering (HK, SG, AU)
    - Tenant isolation (includes PUBLIC + own tenant chunks)
    - Only approved chunks (auto_approved or reviewed)
    - PGVector cosine distance similarity

    Example:
        >>> retriever = KBRetriever(db, jurisdiction="HK", tenant_id=tenant_id)
        >>> results = retriever.retrieve("revenue recognition", top_k=5)
    """

    def __init__(
        self,
        db: Session,
        jurisdiction: str,
        tenant_id: UUID,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        """Initialize KB retriever.

        Args:
            db: Database session
            jurisdiction: Jurisdiction code (HK, SG, AU)
            tenant_id: Tenant UUID for access control
            embedding_service: Optional custom embedding service
        """
        self.db = db
        self.jurisdiction = jurisdiction
        self.tenant_id = tenant_id
        self.embedding_service = embedding_service or EmbeddingService()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        chunk_types: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Retrieve relevant chunks using semantic search.

        Two-step process:
        1. Filter by jurisdiction, tenant, and approval status
        2. Rank by vector similarity (cosine distance)

        Args:
            query: Search query text
            top_k: Maximum number of results to return
            chunk_types: Optional filter by chunk types (e.g., ['definition', 'requirement'])

        Returns:
            List of dicts containing chunk data and metadata:
            {
                'chunk_id': int,
                'content': str,
                'similarity_score': float,
                'jurisdiction': str,
                'kb_document_id': int,
                'document_title': str,
                'standard': str,
                'chunk_index': int,
                'chunk_type': str,
                'confidence_score': float,
                'review_status': str,
            }

        Raises:
            ValueError: If query is empty
        """
        if not query or len(query.strip()) == 0:
            raise ValueError("Query cannot be empty")

        # Step 1: Generate query embedding
        query_embedding = self._generate_query_embedding(query)

        # Step 2: Build base query with filters
        base_query = self._build_base_query(chunk_types)

        # Step 3: Rank by similarity using PGVector
        results = self._rank_by_similarity(base_query, query_embedding, top_k)

        return results

    def retrieve_by_standard(
        self,
        standard: str,
        query: str,
        top_k: int = 5,
    ) -> List[Dict]:
        """Retrieve chunks from a specific accounting standard.

        Args:
            standard: Standard code (e.g., 'HKFRS 15', 'SME-FRS')
            query: Search query text
            top_k: Maximum number of results

        Returns:
            List of relevant chunks from the specified standard
        """
        if not query or len(query.strip()) == 0:
            raise ValueError("Query cannot be empty")

        # Generate query embedding
        query_embedding = self._generate_query_embedding(query)

        # Build query with standard filter
        base_query = (
            self.db.query(KBChunk, KnowledgeBase)
            .join(KnowledgeBase, KBChunk.kb_document_id == KnowledgeBase.id)
            .filter(
                KBChunk.jurisdiction == self.jurisdiction,
                or_(
                    KBChunk.tenant_id == self.tenant_id,
                    KBChunk.tenant_id.is_(None),  # Include PUBLIC
                ),
                KBChunk.review_status.in_(["auto_approved", "reviewed"]),
                KnowledgeBase.is_active == True,
                KnowledgeBase.standard == standard,  # Filter by standard
            )
        )

        # Rank by similarity
        results = self._rank_by_similarity(base_query, query_embedding, top_k)

        return results

    def _generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for search query.

        Uses RETRIEVAL_QUERY task type for Gemini to optimize for search.

        Args:
            query: Search query text

        Returns:
            1536-dimensional embedding vector
        """
        # Use RETRIEVAL_QUERY task type for search queries
        embedding = self.embedding_service.generate_embedding(
            query, task_type="RETRIEVAL_QUERY"
        )
        return embedding

    def _build_base_query(self, chunk_types: Optional[List[str]] = None):
        """Build base query with jurisdiction, tenant, and approval filters.

        Implements mandatory security filters:
        - Jurisdiction: Only chunks from specified jurisdiction
        - Tenant: PUBLIC (tenant_id IS NULL) OR own tenant
        - Approval: Only auto_approved or reviewed chunks
        - Active: Only active KB documents

        Args:
            chunk_types: Optional list of chunk types to filter

        Returns:
            SQLAlchemy query object
        """
        query = (
            self.db.query(KBChunk, KnowledgeBase)
            .join(KnowledgeBase, KBChunk.kb_document_id == KnowledgeBase.id)
            .filter(
                # CRITICAL: Jurisdiction filtering
                KBChunk.jurisdiction == self.jurisdiction,
                # CRITICAL: Tenant isolation (PUBLIC + own tenant)
                or_(
                    KBChunk.tenant_id == self.tenant_id,
                    KBChunk.tenant_id.is_(None),  # PUBLIC documents
                ),
                # Only approved chunks
                KBChunk.review_status.in_(["auto_approved", "reviewed"]),
                # Only active documents
                KnowledgeBase.is_active == True,
            )
        )

        # Optional: Filter by chunk types
        if chunk_types:
            query = query.filter(KBChunk.chunk_type.in_(chunk_types))

        return query

    def _rank_by_similarity(
        self,
        base_query,
        query_embedding: List[float],
        top_k: int,
    ) -> List[Dict]:
        """Rank filtered results by vector similarity.

        Uses PGVector's <-> operator for L2 distance (equivalent to cosine for normalized vectors).

        Args:
            base_query: Base query with filters applied
            query_embedding: Query embedding vector
            top_k: Number of results to return

        Returns:
            List of ranked results with similarity scores
        """
        # Calculate cosine distance using PGVector's <-> operator
        # Note: For normalized embeddings, L2 distance ≈ cosine distance
        results = (
            base_query.order_by(
                KBChunk.embedding.l2_distance(query_embedding)
            )
            .limit(top_k)
            .all()
        )

        # Format results
        formatted_results = []
        for chunk, kb_doc in results:
            # Calculate similarity score (1 - normalized_distance)
            # L2 distance is converted to similarity score [0, 1]
            distance = self._calculate_l2_distance(chunk.embedding, query_embedding)
            similarity_score = max(0.0, 1.0 - (distance / 2.0))  # Normalize to [0, 1]

            formatted_results.append(
                {
                    "chunk_id": chunk.id,
                    "content": chunk.content,
                    "similarity_score": similarity_score,
                    "jurisdiction": chunk.jurisdiction,
                    "kb_document_id": chunk.kb_document_id,
                    "document_title": kb_doc.title,
                    "standard": kb_doc.standard,
                    "chunk_index": chunk.chunk_index,
                    "chunk_type": chunk.chunk_type,
                    "confidence_score": chunk.confidence_score,
                    "review_status": chunk.review_status,
                    "embedding_model": chunk.embedding_model,
                }
            )

        return formatted_results

    def _calculate_l2_distance(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate L2 (Euclidean) distance between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            L2 distance (lower is more similar)
        """
        if len(embedding1) != len(embedding2):
            raise ValueError("Embeddings must have the same dimensionality")

        return sum((a - b) ** 2 for a, b in zip(embedding1, embedding2)) ** 0.5

    def get_chunk_by_id(self, chunk_id: int) -> Optional[Dict]:
        """Get a specific chunk by ID with access control.

        Args:
            chunk_id: Chunk ID to retrieve

        Returns:
            Chunk data dict or None if not found or not accessible
        """
        result = (
            self.db.query(KBChunk, KnowledgeBase)
            .join(KnowledgeBase, KBChunk.kb_document_id == KnowledgeBase.id)
            .filter(
                KBChunk.id == chunk_id,
                KBChunk.jurisdiction == self.jurisdiction,
                or_(
                    KBChunk.tenant_id == self.tenant_id,
                    KBChunk.tenant_id.is_(None),
                ),
            )
            .first()
        )

        if not result:
            return None

        chunk, kb_doc = result

        return {
            "chunk_id": chunk.id,
            "content": chunk.content,
            "jurisdiction": chunk.jurisdiction,
            "kb_document_id": chunk.kb_document_id,
            "document_title": kb_doc.title,
            "standard": kb_doc.standard,
            "chunk_index": chunk.chunk_index,
            "chunk_type": chunk.chunk_type,
            "confidence_score": chunk.confidence_score,
            "review_status": chunk.review_status,
            "embedding_model": chunk.embedding_model,
            "created_at": chunk.created_at,
        }
