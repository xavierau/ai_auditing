"""Knowledge Base router for semantic search and KB management."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from genreport.api.dependencies import CommonDeps
from genreport.core.database.models import KnowledgeBase, KBChunk
from genreport.core.retrieval.secure_kb_retriever import SecureKBRetriever
from genreport.core.retrieval.embedding_cache import EmbeddingCache
from genreport.core.security.jwt_service import require_admin
from genreport.core.security.audit_logger import AuditLogger

router = APIRouter()


# Pydantic Models
class KBDocumentResponse(BaseModel):
    """KB document response model."""

    id: int
    title: str
    standard: Optional[str]
    document_type: Optional[str]
    jurisdiction: str
    access_level: str
    is_active: bool
    total_chunks: int

    class Config:
        from_attributes = True


class KBDocumentDetailResponse(BaseModel):
    """KB document detail response with chunks."""

    id: int
    title: str
    standard: Optional[str]
    document_type: Optional[str]
    jurisdiction: str
    access_level: str
    is_active: bool
    chunks: List["KBChunkResponse"]

    class Config:
        from_attributes = True


class KBChunkResponse(BaseModel):
    """KB chunk response model."""

    id: int
    kb_document_id: int
    chunk_index: int
    content: str
    chunk_type: Optional[str]
    review_status: str
    confidence_score: float

    class Config:
        from_attributes = True


class SearchRequest(BaseModel):
    """Semantic search request."""

    query: str = Field(..., min_length=1, description="Search query text")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results")
    jurisdiction: str = Field(..., description="Jurisdiction code (HK, SG, AU)")
    standard: Optional[str] = Field(None, description="Filter by specific standard")
    chunk_types: Optional[List[str]] = Field(
        None, description="Filter by chunk types"
    )


class SearchResponse(BaseModel):
    """Semantic search response."""

    query: str
    jurisdiction: str
    total_results: int
    results: List[dict]


class ChunkReviewRequest(BaseModel):
    """Chunk review request."""

    action: str = Field(..., description="Action: approve or reject")
    notes: Optional[str] = Field(None, description="Review notes")


class CacheStatsResponse(BaseModel):
    """Cache statistics response."""

    hits: int
    misses: int
    errors: int
    total_requests: int
    hit_rate: float


@router.get("/documents", response_model=List[KBDocumentResponse])
async def list_kb_documents(
    deps: CommonDeps = Depends(),
    jurisdiction: Optional[str] = None,
    standard: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
):
    """List KB documents with optional filtering.

    Args:
        deps: Common dependencies
        jurisdiction: Optional jurisdiction filter
        standard: Optional standard filter
        skip: Number of records to skip
        limit: Maximum number of records

    Returns:
        List of KB documents
    """
    # Build query
    query = deps.db.query(KnowledgeBase).filter(KnowledgeBase.is_active == True)

    # Apply filters
    if jurisdiction:
        query = query.filter(KnowledgeBase.jurisdiction == jurisdiction)

    if standard:
        query = query.filter(KnowledgeBase.standard == standard)

    # Get documents
    documents = query.offset(skip).limit(limit).all()

    # Format response with chunk counts
    response = []
    for doc in documents:
        chunk_count = (
            deps.db.query(KBChunk)
            .filter(KBChunk.kb_document_id == doc.id)
            .count()
        )

        response.append(
            {
                "id": doc.id,
                "title": doc.title,
                "standard": doc.standard,
                "document_type": doc.document_type,
                "jurisdiction": doc.jurisdiction,
                "access_level": doc.access_level,
                "is_active": doc.is_active,
                "total_chunks": chunk_count,
            }
        )

    # Audit log
    AuditLogger.log_event(
        db=deps.db,
        event_type="KB_DOCUMENT_LIST",
        action="READ",
        user_id=deps.user.id,
        tenant_id=deps.tenant_id,
        resource_type="knowledge_base",
        details={
            "jurisdiction": jurisdiction,
            "standard": standard,
            "results_count": len(response),
        },
        status="SUCCESS",
    )

    return response


@router.get("/documents/{document_id}", response_model=KBDocumentDetailResponse)
async def get_kb_document(
    document_id: int,
    deps: CommonDeps = Depends(),
):
    """Get specific KB document with all chunks.

    Args:
        document_id: KB document ID
        deps: Common dependencies

    Returns:
        KB document with chunks

    Raises:
        HTTPException: If document not found
    """
    # Get document
    document = (
        deps.db.query(KnowledgeBase)
        .filter(KnowledgeBase.id == document_id, KnowledgeBase.is_active == True)
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="KB document not found",
        )

    # Get all chunks for document
    chunks = (
        deps.db.query(KBChunk)
        .filter(KBChunk.kb_document_id == document_id)
        .order_by(KBChunk.chunk_index)
        .all()
    )

    # Format response
    response = {
        "id": document.id,
        "title": document.title,
        "standard": document.standard,
        "document_type": document.document_type,
        "jurisdiction": document.jurisdiction,
        "access_level": document.access_level,
        "is_active": document.is_active,
        "chunks": [
            {
                "id": chunk.id,
                "kb_document_id": chunk.kb_document_id,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "chunk_type": chunk.chunk_type,
                "review_status": chunk.review_status,
                "confidence_score": chunk.confidence_score,
            }
            for chunk in chunks
        ],
    }

    # Audit log
    AuditLogger.log_event(
        db=deps.db,
        event_type="KB_DOCUMENT_VIEW",
        action="READ",
        user_id=deps.user.id,
        tenant_id=deps.tenant_id,
        resource_type="knowledge_base",
        resource_id=document_id,
        details={
            "jurisdiction": document.jurisdiction,
            "standard": document.standard,
            "chunks_count": len(chunks),
        },
        status="SUCCESS",
    )

    return response


@router.post("/search", response_model=SearchResponse)
async def search_kb(
    search_request: SearchRequest,
    deps: CommonDeps = Depends(),
):
    """Perform semantic search over knowledge base.

    Args:
        search_request: Search parameters
        deps: Common dependencies

    Returns:
        Search results with relevance scores

    Raises:
        HTTPException: If search fails or query invalid
    """
    # Validate query
    if not search_request.query or len(search_request.query.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty",
        )

    try:
        # Create secure retriever
        retriever = SecureKBRetriever(
            db=deps.db,
            jurisdiction=search_request.jurisdiction,
            tenant_id=deps.tenant_id,
            user_id=deps.user.id,
        )

        # Perform search
        if search_request.standard:
            results = retriever.retrieve_by_standard(
                standard=search_request.standard,
                query=search_request.query,
                top_k=search_request.top_k,
            )
        else:
            results = retriever.retrieve(
                query=search_request.query,
                top_k=search_request.top_k,
                chunk_types=search_request.chunk_types,
            )

        # Format response
        response = SearchResponse(
            query=search_request.query,
            jurisdiction=search_request.jurisdiction,
            total_results=len(results),
            results=results,
        )

        return response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        # Log error
        AuditLogger.log_event(
            db=deps.db,
            event_type="KB_SEARCH",
            action="READ",
            user_id=deps.user.id,
            tenant_id=deps.tenant_id,
            resource_type="knowledge_base",
            details={
                "query": search_request.query,
                "error": str(e),
            },
            status="FAILURE",
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed",
        )


@router.get("/chunks/{chunk_id}", response_model=KBChunkResponse)
async def get_kb_chunk(
    chunk_id: int,
    deps: CommonDeps = Depends(),
):
    """Get specific KB chunk by ID.

    Args:
        chunk_id: Chunk ID
        deps: Common dependencies

    Returns:
        KB chunk details

    Raises:
        HTTPException: If chunk not found or not accessible
    """
    # Use SecureKBRetriever to enforce access control
    retriever = SecureKBRetriever(
        db=deps.db,
        jurisdiction="HK",  # Will be filtered by access control
        tenant_id=deps.tenant_id,
        user_id=deps.user.id,
    )

    chunk_data = retriever.get_chunk_by_id(chunk_id)

    if not chunk_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chunk not found or not accessible",
        )

    # Format response
    response = {
        "id": chunk_data["chunk_id"],
        "kb_document_id": chunk_data["kb_document_id"],
        "chunk_index": chunk_data["chunk_index"],
        "content": chunk_data["content"],
        "chunk_type": chunk_data["chunk_type"],
        "review_status": chunk_data["review_status"],
        "confidence_score": chunk_data["confidence_score"],
    }

    return response


@router.post("/chunks/{chunk_id}/review", response_model=KBChunkResponse)
async def review_kb_chunk(
    chunk_id: int,
    review_request: ChunkReviewRequest,
    deps: CommonDeps = Depends(),
    _: None = Depends(require_admin),
):
    """Review and approve/reject a KB chunk.

    Requires admin role.

    Args:
        chunk_id: Chunk ID to review
        review_request: Review action and notes
        deps: Common dependencies

    Returns:
        Updated chunk

    Raises:
        HTTPException: If chunk not found or invalid action
    """
    # Get chunk
    chunk = deps.db.query(KBChunk).filter(KBChunk.id == chunk_id).first()

    if not chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chunk not found",
        )

    # Validate action
    if review_request.action not in ["approve", "reject"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be 'approve' or 'reject'",
        )

    # Update review status
    if review_request.action == "approve":
        chunk.review_status = "reviewed"
    else:
        chunk.review_status = "rejected"

    # Store review notes in metadata
    if not chunk.chunk_metadata:
        chunk.chunk_metadata = {}

    chunk.chunk_metadata["review_notes"] = review_request.notes
    chunk.chunk_metadata["reviewed_by"] = deps.user.id
    chunk.chunk_metadata["reviewed_at"] = datetime.utcnow().isoformat()

    # Mark metadata as modified for SQLAlchemy to detect changes
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(chunk, "chunk_metadata")

    deps.db.commit()
    deps.db.refresh(chunk)

    # Audit log
    AuditLogger.log_event(
        db=deps.db,
        event_type="KB_CHUNK_REVIEW",
        action="UPDATE",
        user_id=deps.user.id,
        tenant_id=deps.tenant_id,
        resource_type="kb_chunk",
        resource_id=chunk_id,
        details={
            "action": review_request.action,
            "new_status": chunk.review_status,
            "notes": review_request.notes,
        },
        status="SUCCESS",
    )

    # Format response
    response = {
        "id": chunk.id,
        "kb_document_id": chunk.kb_document_id,
        "chunk_index": chunk.chunk_index,
        "content": chunk.content,
        "chunk_type": chunk.chunk_type,
        "review_status": chunk.review_status,
        "confidence_score": chunk.confidence_score,
    }

    return response


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats(
    deps: CommonDeps = Depends(),
):
    """Get embedding cache statistics.

    Args:
        deps: Common dependencies

    Returns:
        Cache hit/miss statistics
    """
    # Create cache instance
    cache = EmbeddingCache()

    # Get stats
    stats = cache.get_cache_stats()

    # Audit log
    AuditLogger.log_event(
        db=deps.db,
        event_type="KB_CACHE_STATS",
        action="READ",
        user_id=deps.user.id,
        tenant_id=deps.tenant_id,
        resource_type="cache",
        details={
            "hits": stats["hits"],
            "misses": stats["misses"],
            "hit_rate": stats["hit_rate"],
        },
        status="SUCCESS",
    )

    return CacheStatsResponse(**stats)
