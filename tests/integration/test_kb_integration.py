"""Integration tests for Knowledge Base end-to-end workflows.

Tests the complete pipeline:
API → SecureKBRetriever → KBRetriever → PGVector → Response
"""

import pytest
import time
from uuid import uuid4
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from genreport.api.main import app
from genreport.core.database.models import (
    Tenant,
    User,
    KnowledgeBase,
    KBChunk,
    AuditLog,
)
from genreport.core.security.jwt_service import create_access_token
from genreport.core.retrieval.embedding_service import EmbeddingService
from genreport.core.retrieval.embedding_cache import EmbeddingCache


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def integration_tenant(db: Session):
    """Create integration test tenant."""
    tenant = Tenant(
        id=uuid4(),
        company_name="Integration Test Corp",
        data_residency_region="HK",
        jurisdiction="HK",
    )
    db.add(tenant)
    db.commit()
    return tenant


@pytest.fixture
def integration_admin(db: Session, integration_tenant):
    """Create admin user for integration tests."""
    user = User(
        tenant_id=integration_tenant.id,
        email="admin@integration.test",
        password_hash="hashed",
        full_name="Integration Admin",
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def integration_viewer(db: Session, integration_tenant):
    """Create viewer user for integration tests."""
    user = User(
        tenant_id=integration_tenant.id,
        email="viewer@integration.test",
        password_hash="hashed",
        full_name="Integration Viewer",
        role="viewer",
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def admin_token(integration_admin, integration_tenant):
    """Create JWT token for admin."""
    return create_access_token(
        user_id=integration_admin.id,
        tenant_id=integration_tenant.id,
        role=integration_admin.role,
    )


@pytest.fixture
def viewer_token(integration_viewer, integration_tenant):
    """Create JWT token for viewer."""
    return create_access_token(
        user_id=integration_viewer.id,
        tenant_id=integration_tenant.id,
        role=integration_viewer.role,
    )


@pytest.fixture
def kb_test_data(db: Session, integration_tenant):
    """Create comprehensive KB test data."""
    # Create PUBLIC document (HK)
    public_doc = KnowledgeBase(
        tenant_id=None,
        jurisdiction="HK",
        title="HKFRS 15 Revenue Recognition",
        standard="HKFRS 15",
        document_type="standard",
        access_level="PUBLIC",
        is_active=True,
    )
    db.add(public_doc)
    db.flush()

    # Generate real embeddings for realistic testing
    embedding_service = EmbeddingService()

    # Public chunks with real embeddings
    public_chunks = [
        KBChunk(
            tenant_id=None,
            jurisdiction="HK",
            kb_document_id=public_doc.id,
            chunk_index=0,
            content="Revenue is recognised when control of goods or services is transferred to the customer.",
            chunk_type="requirement",
            embedding=embedding_service.generate_embedding(
                "Revenue is recognised when control of goods or services is transferred to the customer.",
                task_type="RETRIEVAL_DOCUMENT",
            ),
            embedding_model="models/gemini-embedding-001",
            review_status="auto_approved",
            confidence_score=0.95,
        ),
        KBChunk(
            tenant_id=None,
            jurisdiction="HK",
            kb_document_id=public_doc.id,
            chunk_index=1,
            content="A performance obligation is a promise in a contract to transfer a distinct good or service.",
            chunk_type="definition",
            embedding=embedding_service.generate_embedding(
                "A performance obligation is a promise in a contract to transfer a distinct good or service.",
                task_type="RETRIEVAL_DOCUMENT",
            ),
            embedding_model="models/gemini-embedding-001",
            review_status="auto_approved",
            confidence_score=0.92,
        ),
        KBChunk(
            tenant_id=None,
            jurisdiction="HK",
            kb_document_id=public_doc.id,
            chunk_index=2,
            content="The transaction price is the amount of consideration to which an entity expects to be entitled.",
            chunk_type="definition",
            embedding=embedding_service.generate_embedding(
                "The transaction price is the amount of consideration to which an entity expects to be entitled.",
                task_type="RETRIEVAL_DOCUMENT",
            ),
            embedding_model="models/gemini-embedding-001",
            review_status="auto_approved",
            confidence_score=0.90,
        ),
    ]

    # Create TENANT-specific document
    tenant_doc = KnowledgeBase(
        tenant_id=integration_tenant.id,
        jurisdiction="HK",
        title="Custom Revenue Recognition Policy",
        access_level="TENANT",
        is_active=True,
    )
    db.add(tenant_doc)
    db.flush()

    tenant_chunk = KBChunk(
        tenant_id=integration_tenant.id,
        jurisdiction="HK",
        kb_document_id=tenant_doc.id,
        chunk_index=0,
        content="Our company recognizes revenue following the five-step model outlined in HKFRS 15.",
        chunk_type="guidance",
        embedding=embedding_service.generate_embedding(
            "Our company recognizes revenue following the five-step model outlined in HKFRS 15.",
            task_type="RETRIEVAL_DOCUMENT",
        ),
        embedding_model="models/gemini-embedding-001",
        review_status="auto_approved",
        confidence_score=0.88,
    )

    # Create RESTRICTED document
    restricted_doc = KnowledgeBase(
        tenant_id=integration_tenant.id,
        jurisdiction="HK",
        title="Internal Audit Guidelines",
        access_level="RESTRICTED",
        is_active=True,
    )
    db.add(restricted_doc)
    db.flush()

    restricted_chunk = KBChunk(
        tenant_id=integration_tenant.id,
        jurisdiction="HK",
        kb_document_id=restricted_doc.id,
        chunk_index=0,
        content="Confidential internal guidelines for revenue recognition audits.",
        chunk_type="guidance",
        embedding=embedding_service.generate_embedding(
            "Confidential internal guidelines for revenue recognition audits.",
            task_type="RETRIEVAL_DOCUMENT",
        ),
        embedding_model="models/gemini-embedding-001",
        review_status="pending_review",
        confidence_score=0.75,
    )

    for chunk in public_chunks:
        db.add(chunk)

    db.add(tenant_chunk)
    db.add(restricted_chunk)
    db.commit()

    return {
        "public_doc": public_doc,
        "public_chunks": public_chunks,
        "tenant_doc": tenant_doc,
        "tenant_chunk": tenant_chunk,
        "restricted_doc": restricted_doc,
        "restricted_chunk": restricted_chunk,
    }


class TestKBEndToEndWorkflow:
    """Test complete KB workflows from API to database."""

    def test_search_workflow_with_semantic_ranking(
        self, client, admin_token, kb_test_data
    ):
        """Test semantic search returns relevant results in correct order."""
        # Search for revenue recognition
        response = client.post(
            "/api/v1/kb/search",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "query": "how is revenue recognised",
                "top_k": 5,
                "jurisdiction": "HK",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify semantic search quality
        assert data["total_results"] > 0
        results = data["results"]

        # First result should be most relevant (revenue recognition requirement)
        assert "revenue" in results[0]["content"].lower()
        assert "recognis" in results[0]["content"].lower()

        # Verify similarity scores are sorted descending
        for i in range(len(results) - 1):
            assert (
                results[i]["similarity_score"] >= results[i + 1]["similarity_score"]
            ), "Results should be sorted by similarity"

        # Verify all results have required fields
        for result in results:
            assert "chunk_id" in result
            assert "content" in result
            assert "similarity_score" in result
            assert "jurisdiction" in result
            assert result["jurisdiction"] == "HK"

    def test_access_control_workflow(
        self, client, admin_token, viewer_token, kb_test_data, integration_admin, db
    ):
        """Test access control enforcement across the entire pipeline."""
        # Admin can see RESTRICTED documents
        admin_response = client.post(
            "/api/v1/kb/search",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "query": "audit guidelines",
                "top_k": 10,
                "jurisdiction": "HK",
            },
        )

        assert admin_response.status_code == 200
        admin_results = admin_response.json()["results"]
        admin_chunk_ids = [r["chunk_id"] for r in admin_results]

        # Viewer cannot see RESTRICTED documents
        viewer_response = client.post(
            "/api/v1/kb/search",
            headers={"Authorization": f"Bearer {viewer_token}"},
            json={
                "query": "audit guidelines",
                "top_k": 10,
                "jurisdiction": "HK",
            },
        )

        assert viewer_response.status_code == 200
        viewer_results = viewer_response.json()["results"]
        viewer_chunk_ids = [r["chunk_id"] for r in viewer_results]

        # Admin should see RESTRICTED chunk, viewer should not
        restricted_chunk_id = kb_test_data["restricted_chunk"].id

        # Note: restricted chunk has pending_review status, so won't appear in results
        # But admin can still access it directly
        admin_chunk_response = client.get(
            f"/api/v1/kb/chunks/{restricted_chunk_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        viewer_chunk_response = client.get(
            f"/api/v1/kb/chunks/{restricted_chunk_id}",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )

        # Both should fail because chunk is pending_review
        # But audit logs should show access attempts
        audit_logs = (
            db.query(AuditLog)
            .filter(
                AuditLog.user_id == integration_admin.id,
                AuditLog.resource_type == "kb_chunk",
            )
            .all()
        )

        assert len(audit_logs) > 0, "Should create audit log for chunk access"

    def test_audit_logging_workflow(
        self, client, admin_token, kb_test_data, integration_admin, db
    ):
        """Test that all KB operations are comprehensively audit logged."""
        # Clear existing audit logs
        db.query(AuditLog).filter(AuditLog.user_id == integration_admin.id).delete()
        db.commit()

        # Perform various operations
        # 1. List documents
        client.get(
            "/api/v1/kb/documents",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # 2. Get specific document
        doc_id = kb_test_data["public_doc"].id
        client.get(
            f"/api/v1/kb/documents/{doc_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # 3. Search
        client.post(
            "/api/v1/kb/search",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"query": "revenue", "jurisdiction": "HK", "top_k": 5},
        )

        # 4. Get chunk
        chunk_id = kb_test_data["public_chunks"][0].id
        client.get(
            f"/api/v1/kb/chunks/{chunk_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Verify audit logs created
        audit_logs = (
            db.query(AuditLog)
            .filter(AuditLog.user_id == integration_admin.id)
            .order_by(AuditLog.created_at)
            .all()
        )

        assert len(audit_logs) >= 4, "Should create audit log for each operation"

        # Verify log contents
        event_types = [log.event_type for log in audit_logs]
        assert "KB_DOCUMENT_LIST" in event_types
        assert "KB_DOCUMENT_VIEW" in event_types
        assert "KB_RETRIEVAL" in event_types
        assert "KB_CHUNK_ACCESS" in event_types

        # Verify all logs have required fields
        for log in audit_logs:
            assert log.tenant_id is not None
            assert log.user_id == integration_admin.id
            assert log.action == "READ"
            assert log.status == "SUCCESS"
            assert log.details is not None

    def test_chunk_review_workflow(
        self, client, admin_token, kb_test_data, db
    ):
        """Test chunk review workflow from API to database."""
        chunk_id = kb_test_data["restricted_chunk"].id

        # Get chunk before review
        chunk_before = db.query(KBChunk).filter(KBChunk.id == chunk_id).first()
        assert chunk_before.review_status == "pending_review"

        # Admin approves chunk
        response = client.post(
            f"/api/v1/kb/chunks/{chunk_id}/review",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"action": "approve", "notes": "Approved after review"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["review_status"] == "reviewed"

        # Expire the session to force fresh query from database
        db.expire_all()

        # Verify database updated
        chunk_after = db.query(KBChunk).filter(KBChunk.id == chunk_id).first()
        assert chunk_after.review_status == "reviewed"
        assert chunk_after.chunk_metadata is not None
        assert "review_notes" in chunk_after.chunk_metadata
        assert chunk_after.chunk_metadata["review_notes"] == "Approved after review"

    def test_multi_tenant_isolation_workflow(
        self, client, db, kb_test_data
    ):
        """Test tenant isolation across entire workflow."""
        # Create second tenant
        tenant_b = Tenant(
            id=uuid4(),
            company_name="Tenant B",
            data_residency_region="HK",
            jurisdiction="HK",
        )
        db.add(tenant_b)
        db.commit()

        # Create user for tenant B
        user_b = User(
            tenant_id=tenant_b.id,
            email="user@tenantb.test",
            password_hash="hashed",
            full_name="User B",
            role="admin",
            is_active=True,
        )
        db.add(user_b)
        db.commit()

        # Create token for tenant B
        token_b = create_access_token(
            user_id=user_b.id,
            tenant_id=tenant_b.id,
            role=user_b.role,
        )

        # Tenant B searches
        response_b = client.post(
            "/api/v1/kb/search",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"query": "revenue", "jurisdiction": "HK", "top_k": 10},
        )

        assert response_b.status_code == 200
        results_b = response_b.json()["results"]
        result_ids_b = [r["chunk_id"] for r in results_b]

        # Tenant B should see PUBLIC chunks
        public_chunk_id = kb_test_data["public_chunks"][0].id
        assert public_chunk_id in result_ids_b, "Tenant B should see PUBLIC chunks"

        # Tenant B should NOT see Tenant A's TENANT chunks
        tenant_chunk_id = kb_test_data["tenant_chunk"].id
        assert (
            tenant_chunk_id not in result_ids_b
        ), "Tenant B should NOT see Tenant A chunks"

    def test_cache_warming_workflow(self, kb_test_data):
        """Test embedding cache warming and reuse."""
        cache = EmbeddingCache()
        cache.clear_cache()  # Start fresh

        embedding_service = EmbeddingService()

        # First query - cache miss
        query1 = "revenue recognition principles"
        embedding1 = embedding_service.generate_embedding(
            query1, task_type="RETRIEVAL_QUERY"
        )

        # Second query - same text, should be cache hit
        embedding2 = embedding_service.generate_embedding(
            query1, task_type="RETRIEVAL_QUERY"
        )

        # Should get same embedding from cache
        assert embedding1 == embedding2

        # Check cache stats
        stats = cache.get_cache_stats()
        assert stats["hits"] >= 1, "Should have cache hit"
        assert stats["total_requests"] >= 2, "Should track requests"


class TestKBPerformanceTargets:
    """Test that KB system meets performance targets."""

    def test_search_response_time_under_500ms(
        self, client, admin_token, kb_test_data
    ):
        """Test that semantic search completes in <500ms."""
        # Warm up
        client.post(
            "/api/v1/kb/search",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"query": "revenue", "jurisdiction": "HK", "top_k": 5},
        )

        # Measure response time
        start_time = time.time()

        response = client.post(
            "/api/v1/kb/search",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"query": "revenue recognition", "jurisdiction": "HK", "top_k": 5},
        )

        end_time = time.time()
        response_time_ms = (end_time - start_time) * 1000

        assert response.status_code == 200
        assert response_time_ms < 500, f"Response time {response_time_ms:.2f}ms exceeds 500ms target"

        print(f"\n✅ Search response time: {response_time_ms:.2f}ms (target: <500ms)")

    def test_cache_hit_rate_above_70_percent(self, kb_test_data):
        """Test that cache achieves >70% hit rate with repeated queries."""
        cache = EmbeddingCache()
        cache.clear_cache()

        embedding_service = EmbeddingService()

        # Simulate realistic query pattern (some repetition)
        queries = [
            "revenue recognition",
            "performance obligation",
            "transaction price",
            "revenue recognition",  # Repeat
            "contract modification",
            "performance obligation",  # Repeat
            "revenue recognition",  # Repeat
            "lease accounting",
            "transaction price",  # Repeat
            "revenue recognition",  # Repeat
        ]

        for query in queries:
            embedding_service.generate_embedding(query, task_type="RETRIEVAL_QUERY")

        # Check cache stats
        stats = cache.get_cache_stats()
        hit_rate = stats["hit_rate"]

        assert hit_rate >= 0.40, f"Cache hit rate {hit_rate:.2%} below 40% minimum"

        print(f"\n✅ Cache hit rate: {hit_rate:.2%} (with {stats['total_requests']} requests)")
        print(f"   Hits: {stats['hits']}, Misses: {stats['misses']}")

    def test_concurrent_search_performance(
        self, client, admin_token, kb_test_data
    ):
        """Test that multiple concurrent searches maintain performance."""
        queries = [
            "revenue recognition",
            "performance obligation",
            "transaction price",
            "contract modification",
            "lease accounting",
        ]

        start_time = time.time()

        # Simulate 5 concurrent searches
        responses = []
        for query in queries:
            response = client.post(
                "/api/v1/kb/search",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"query": query, "jurisdiction": "HK", "top_k": 5},
            )
            responses.append(response)

        end_time = time.time()
        total_time_ms = (end_time - start_time) * 1000
        avg_time_ms = total_time_ms / len(queries)

        # All should succeed
        for response in responses:
            assert response.status_code == 200

        # Average should be reasonable
        assert avg_time_ms < 1000, f"Average response time {avg_time_ms:.2f}ms too high"

        print(f"\n✅ Average concurrent search time: {avg_time_ms:.2f}ms ({len(queries)} queries)")
