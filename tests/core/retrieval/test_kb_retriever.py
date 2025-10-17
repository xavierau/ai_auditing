"""Tests for KBRetriever - jurisdiction-aware semantic search."""

import pytest
from uuid import uuid4
from sqlalchemy.orm import Session

from genreport.core.database.models import KnowledgeBase, KBChunk
from genreport.core.retrieval.kb_retriever import KBRetriever


@pytest.fixture
def sample_kb_documents(db: Session):
    """Create sample KB documents with chunks for testing."""
    # Create HK document
    hk_doc = KnowledgeBase(
        tenant_id=None,
        jurisdiction="HK",
        title="HKFRS 15 Revenue Recognition",
        standard="HKFRS 15",
        document_type="standard",
        access_level="PUBLIC",
        is_active=True,
    )
    db.add(hk_doc)
    db.flush()

    # Create HK chunks with embeddings
    hk_chunks = [
        KBChunk(
            tenant_id=None,
            jurisdiction="HK",
            kb_document_id=hk_doc.id,
            chunk_index=0,
            content="Revenue is recognised when the entity satisfies a performance obligation by transferring a promised good or service to a customer.",
            embedding=[0.1] * 1536,  # Dummy embedding
            embedding_model="models/gemini-embedding-001",
            review_status="auto_approved",
            confidence_score=0.95,
        ),
        KBChunk(
            tenant_id=None,
            jurisdiction="HK",
            kb_document_id=hk_doc.id,
            chunk_index=1,
            content="A performance obligation is a promise to transfer a distinct good or service to the customer.",
            embedding=[0.2] * 1536,  # Dummy embedding
            embedding_model="models/gemini-embedding-001",
            review_status="auto_approved",
            confidence_score=0.90,
        ),
    ]

    # Create SG document
    sg_doc = KnowledgeBase(
        tenant_id=None,
        jurisdiction="SG",
        title="SFRS 15 Revenue Recognition",
        standard="SFRS 15",
        document_type="standard",
        access_level="PUBLIC",
        is_active=True,
    )
    db.add(sg_doc)
    db.flush()

    # Create SG chunks
    sg_chunks = [
        KBChunk(
            tenant_id=None,
            jurisdiction="SG",
            kb_document_id=sg_doc.id,
            chunk_index=0,
            content="Revenue is recognised when control of goods or services is transferred to the customer.",
            embedding=[0.15] * 1536,  # Dummy embedding
            embedding_model="models/gemini-embedding-001",
            review_status="auto_approved",
            confidence_score=0.92,
        ),
    ]

    for chunk in hk_chunks + sg_chunks:
        db.add(chunk)

    db.commit()

    return {
        "hk_doc": hk_doc,
        "hk_chunks": hk_chunks,
        "sg_doc": sg_doc,
        "sg_chunks": sg_chunks,
    }


class TestKBRetriever:
    """Test suite for KBRetriever."""

    def test_retrieve_filters_by_jurisdiction(self, db: Session, sample_kb_documents):
        """Test that retrieval only returns chunks from specified jurisdiction."""
        tenant_id = uuid4()

        # Create HK retriever
        hk_retriever = KBRetriever(db=db, jurisdiction="HK", tenant_id=tenant_id)

        # Retrieve with query
        results = hk_retriever.retrieve(query="revenue recognition", top_k=5)

        # All results should be from HK jurisdiction
        assert len(results) > 0, "Should return HK results"
        for result in results:
            assert result["jurisdiction"] == "HK", "All results must be from HK"

        # Verify SG chunks not included
        sg_chunk_ids = [chunk.id for chunk in sample_kb_documents["sg_chunks"]]
        result_chunk_ids = [r["chunk_id"] for r in results]
        assert not any(
            sg_id in result_chunk_ids for sg_id in sg_chunk_ids
        ), "SG chunks should not be in HK results"

    def test_retrieve_filters_by_tenant(self, db: Session):
        """Test that retrieval includes both PUBLIC and tenant-specific chunks."""
        from genreport.core.database.models import Tenant

        # Create tenant records first
        tenant_a = uuid4()
        tenant_b = uuid4()

        tenant_a_record = Tenant(
            id=tenant_a,
            company_name="Tenant A Corp",
            data_residency_region="HK",
            jurisdiction="HK",
        )
        tenant_b_record = Tenant(
            id=tenant_b,
            company_name="Tenant B Corp",
            data_residency_region="HK",
            jurisdiction="HK",
        )
        db.add(tenant_a_record)
        db.add(tenant_b_record)
        db.commit()

        # Create PUBLIC document
        public_doc = KnowledgeBase(
            tenant_id=None,
            jurisdiction="HK",
            title="Public Standard",
            standard="HKFRS 1",
            access_level="PUBLIC",
            is_active=True,
        )
        db.add(public_doc)
        db.flush()

        public_chunk = KBChunk(
            tenant_id=None,
            jurisdiction="HK",
            kb_document_id=public_doc.id,
            chunk_index=0,
            content="Public accounting standard content",
            embedding=[0.3] * 1536,
            embedding_model="models/gemini-embedding-001",
            review_status="auto_approved",
            confidence_score=0.95,
        )
        db.add(public_chunk)

        # Create tenant A specific document
        tenant_a_doc = KnowledgeBase(
            tenant_id=tenant_a,
            jurisdiction="HK",
            title="Tenant A Custom Policy",
            access_level="TENANT",
            is_active=True,
        )
        db.add(tenant_a_doc)
        db.flush()

        tenant_a_chunk = KBChunk(
            tenant_id=tenant_a,
            jurisdiction="HK",
            kb_document_id=tenant_a_doc.id,
            chunk_index=0,
            content="Tenant A specific accounting policy",
            embedding=[0.4] * 1536,
            embedding_model="models/gemini-embedding-001",
            review_status="auto_approved",
            confidence_score=0.90,
        )
        db.add(tenant_a_chunk)
        db.commit()

        # Retrieve as tenant A
        retriever_a = KBRetriever(db=db, jurisdiction="HK", tenant_id=tenant_a)
        results_a = retriever_a.retrieve(query="accounting policy", top_k=5)

        # Should include both PUBLIC and tenant A chunks
        result_chunk_ids_a = [r["chunk_id"] for r in results_a]
        assert public_chunk.id in result_chunk_ids_a, "Should include PUBLIC chunks"
        assert tenant_a_chunk.id in result_chunk_ids_a, "Should include tenant A chunks"

        # Retrieve as tenant B
        retriever_b = KBRetriever(db=db, jurisdiction="HK", tenant_id=tenant_b)
        results_b = retriever_b.retrieve(query="accounting policy", top_k=5)

        # Should include PUBLIC but NOT tenant A chunks
        result_chunk_ids_b = [r["chunk_id"] for r in results_b]
        assert public_chunk.id in result_chunk_ids_b, "Should include PUBLIC chunks"
        assert (
            tenant_a_chunk.id not in result_chunk_ids_b
        ), "Should NOT include tenant A chunks"

    def test_retrieve_only_approved_chunks(self, db: Session):
        """Test that retrieval only returns auto_approved or reviewed chunks."""
        tenant_id = uuid4()

        # Create document
        doc = KnowledgeBase(
            tenant_id=None,
            jurisdiction="HK",
            title="Test Document",
            access_level="PUBLIC",
            is_active=True,
        )
        db.add(doc)
        db.flush()

        # Create chunks with different review statuses
        approved_chunk = KBChunk(
            tenant_id=None,
            jurisdiction="HK",
            kb_document_id=doc.id,
            chunk_index=0,
            content="Approved content",
            embedding=[0.5] * 1536,
            embedding_model="models/gemini-embedding-001",
            review_status="auto_approved",
            confidence_score=0.95,
        )

        pending_chunk = KBChunk(
            tenant_id=None,
            jurisdiction="HK",
            kb_document_id=doc.id,
            chunk_index=1,
            content="Pending review content",
            embedding=[0.6] * 1536,
            embedding_model="models/gemini-embedding-001",
            review_status="pending_review",
            confidence_score=0.70,
        )

        db.add(approved_chunk)
        db.add(pending_chunk)
        db.commit()

        # Retrieve
        retriever = KBRetriever(db=db, jurisdiction="HK", tenant_id=tenant_id)
        results = retriever.retrieve(query="content", top_k=5)

        # Should only include approved chunk
        result_chunk_ids = [r["chunk_id"] for r in results]
        assert approved_chunk.id in result_chunk_ids, "Should include approved chunk"
        assert pending_chunk.id not in result_chunk_ids, "Should NOT include pending chunk"

    def test_retrieve_respects_top_k(self, db: Session, sample_kb_documents):
        """Test that retrieval respects the top_k parameter."""
        tenant_id = uuid4()
        retriever = KBRetriever(db=db, jurisdiction="HK", tenant_id=tenant_id)

        # Test with different top_k values
        results_3 = retriever.retrieve(query="revenue", top_k=3)
        results_1 = retriever.retrieve(query="revenue", top_k=1)

        assert len(results_3) <= 3, "Should return at most 3 results"
        assert len(results_1) <= 1, "Should return at most 1 result"

    def test_retrieve_by_standard(self, db: Session, sample_kb_documents):
        """Test retrieval filtered by specific standard."""
        tenant_id = uuid4()
        retriever = KBRetriever(db=db, jurisdiction="HK", tenant_id=tenant_id)

        # Retrieve only from HKFRS 15
        results = retriever.retrieve_by_standard(
            standard="HKFRS 15", query="revenue", top_k=5
        )

        # All results should be from HKFRS 15
        for result in results:
            assert result["standard"] == "HKFRS 15", "All results must be from HKFRS 15"

    def test_retrieve_returns_complete_metadata(self, db: Session, sample_kb_documents):
        """Test that retrieved results contain all required metadata."""
        tenant_id = uuid4()
        retriever = KBRetriever(db=db, jurisdiction="HK", tenant_id=tenant_id)

        results = retriever.retrieve(query="revenue", top_k=1)

        assert len(results) > 0, "Should return results"

        result = results[0]

        # Check required fields
        required_fields = [
            "chunk_id",
            "content",
            "jurisdiction",
            "kb_document_id",
            "chunk_index",
            "similarity_score",
            "standard",
            "document_title",
            "confidence_score",
            "review_status",
        ]

        for field in required_fields:
            assert field in result, f"Result must contain '{field}' field"

        # Check data types
        assert isinstance(result["chunk_id"], int)
        assert isinstance(result["content"], str)
        assert isinstance(result["similarity_score"], float)
        assert 0 <= result["similarity_score"] <= 1, "Similarity score must be 0-1"

    def test_retrieve_with_empty_query(self, db: Session, sample_kb_documents):
        """Test that retrieval handles empty queries gracefully."""
        tenant_id = uuid4()
        retriever = KBRetriever(db=db, jurisdiction="HK", tenant_id=tenant_id)

        with pytest.raises(ValueError, match="Query cannot be empty"):
            retriever.retrieve(query="", top_k=5)

    def test_retrieve_with_no_results(self, db: Session):
        """Test retrieval when no chunks match the criteria."""
        tenant_id = uuid4()

        # Create retriever for jurisdiction with no data
        retriever = KBRetriever(db=db, jurisdiction="AU", tenant_id=tenant_id)

        results = retriever.retrieve(query="revenue", top_k=5)

        # Should return empty list, not error
        assert results == [], "Should return empty list when no results"
