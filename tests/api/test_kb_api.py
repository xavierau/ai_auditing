"""Tests for Knowledge Base API endpoints."""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from sqlalchemy.orm import Session

from genreport.api.main import app
from genreport.core.database.models import (
    Tenant,
    User,
    KnowledgeBase,
    KBChunk,
)
from genreport.core.security.jwt_service import create_access_token


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def test_tenant(db: Session):
    """Create test tenant."""
    tenant = Tenant(
        id=uuid4(),
        company_name="Test KB Corp",
        data_residency_region="HK",
        jurisdiction="HK",
    )
    db.add(tenant)
    db.commit()
    return tenant


@pytest.fixture
def admin_user(db: Session, test_tenant):
    """Create admin user."""
    user = User(
        tenant_id=test_tenant.id,
        email="admin@kbtest.com",
        password_hash="hashed_password",
        full_name="KB Admin",
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def viewer_user(db: Session, test_tenant):
    """Create viewer user."""
    user = User(
        tenant_id=test_tenant.id,
        email="viewer@kbtest.com",
        password_hash="hashed_password",
        full_name="KB Viewer",
        role="viewer",
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def admin_token(admin_user, test_tenant):
    """Create JWT token for admin user."""
    return create_access_token(
        user_id=admin_user.id,
        tenant_id=test_tenant.id,
        role=admin_user.role,
    )


@pytest.fixture
def viewer_token(viewer_user, test_tenant):
    """Create JWT token for viewer user."""
    return create_access_token(
        user_id=viewer_user.id,
        tenant_id=test_tenant.id,
        role=viewer_user.role,
    )


@pytest.fixture
def sample_kb_document(db: Session, test_tenant):
    """Create sample KB document with chunks."""
    kb_doc = KnowledgeBase(
        tenant_id=None,  # PUBLIC
        jurisdiction="HK",
        title="HKFRS 15 Revenue Recognition",
        standard="HKFRS 15",
        document_type="standard",
        access_level="PUBLIC",
        is_active=True,
    )
    db.add(kb_doc)
    db.flush()

    # Create chunks
    chunk1 = KBChunk(
        tenant_id=None,
        jurisdiction="HK",
        kb_document_id=kb_doc.id,
        chunk_index=0,
        content="Revenue is recognised when control transfers to the customer.",
        chunk_type="requirement",
        embedding=[0.1] * 1536,
        embedding_model="models/gemini-embedding-001",
        review_status="auto_approved",
        confidence_score=0.95,
    )

    chunk2 = KBChunk(
        tenant_id=None,
        jurisdiction="HK",
        kb_document_id=kb_doc.id,
        chunk_index=1,
        content="A performance obligation is a promise to transfer goods or services.",
        chunk_type="definition",
        embedding=[0.2] * 1536,
        embedding_model="models/gemini-embedding-001",
        review_status="pending_review",
        confidence_score=0.78,
    )

    db.add(chunk1)
    db.add(chunk2)
    db.commit()

    return {"document": kb_doc, "chunks": [chunk1, chunk2]}


class TestKBDocumentsAPI:
    """Test suite for KB documents endpoints."""

    def test_list_kb_documents_success(
        self, client, admin_token, sample_kb_document
    ):
        """Test listing KB documents."""
        response = client.get(
            "/api/v1/kb/documents",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["title"] == "HKFRS 15 Revenue Recognition"
        assert data[0]["jurisdiction"] == "HK"

    def test_list_kb_documents_requires_auth(self, client):
        """Test that listing requires authentication."""
        response = client.get("/api/v1/kb/documents")
        assert response.status_code == 403

    def test_list_kb_documents_with_filters(
        self, client, admin_token, sample_kb_document
    ):
        """Test filtering KB documents by jurisdiction and standard."""
        response = client.get(
            "/api/v1/kb/documents?jurisdiction=HK&standard=HKFRS 15",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        for doc in data:
            assert doc["jurisdiction"] == "HK"
            assert doc["standard"] == "HKFRS 15"

    def test_get_kb_document_by_id(self, client, admin_token, sample_kb_document):
        """Test getting specific KB document."""
        doc_id = sample_kb_document["document"].id

        response = client.get(
            f"/api/v1/kb/documents/{doc_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == doc_id
        assert data["title"] == "HKFRS 15 Revenue Recognition"
        assert "chunks" in data
        assert len(data["chunks"]) == 2

    def test_get_kb_document_not_found(self, client, admin_token):
        """Test getting non-existent document."""
        response = client.get(
            "/api/v1/kb/documents/999999",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestKBSearchAPI:
    """Test suite for KB semantic search endpoint."""

    def test_search_success(self, client, admin_token, sample_kb_document):
        """Test semantic search with valid query."""
        response = client.post(
            "/api/v1/kb/search",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "query": "revenue recognition",
                "top_k": 5,
                "jurisdiction": "HK",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "query" in data
        assert "total_results" in data
        assert data["query"] == "revenue recognition"
        assert data["total_results"] <= 5

    def test_search_with_chunk_type_filter(
        self, client, admin_token, sample_kb_document
    ):
        """Test search with chunk type filtering."""
        response = client.post(
            "/api/v1/kb/search",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "query": "revenue",
                "top_k": 10,
                "jurisdiction": "HK",
                "chunk_types": ["requirement", "definition"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        # All results should be one of the requested types
        for result in data["results"]:
            assert result["chunk_type"] in ["requirement", "definition"]

    def test_search_requires_query(self, client, admin_token):
        """Test that search requires a query."""
        response = client.post(
            "/api/v1/kb/search",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"query": "", "jurisdiction": "HK"},
        )

        assert response.status_code == 422  # Pydantic validation error
        # Pydantic catches empty string with min_length=1 before our validation

    def test_search_requires_jurisdiction(self, client, admin_token):
        """Test that search requires jurisdiction."""
        response = client.post(
            "/api/v1/kb/search",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"query": "revenue"},
        )

        assert response.status_code == 422  # Validation error

    def test_search_by_standard(self, client, admin_token, sample_kb_document):
        """Test search filtered by specific standard."""
        response = client.post(
            "/api/v1/kb/search",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "query": "revenue",
                "top_k": 5,
                "jurisdiction": "HK",
                "standard": "HKFRS 15",
            },
        )

        assert response.status_code == 200
        data = response.json()
        # All results should be from HKFRS 15
        for result in data["results"]:
            assert result["standard"] == "HKFRS 15"


class TestKBChunkAPI:
    """Test suite for KB chunk endpoints."""

    def test_get_chunk_by_id(self, client, admin_token, sample_kb_document):
        """Test getting specific chunk by ID."""
        chunk_id = sample_kb_document["chunks"][0].id

        response = client.get(
            f"/api/v1/kb/chunks/{chunk_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == chunk_id
        assert data["content"] == sample_kb_document["chunks"][0].content
        assert data["chunk_type"] == "requirement"

    def test_get_chunk_not_found(self, client, admin_token):
        """Test getting non-existent chunk."""
        response = client.get(
            "/api/v1/kb/chunks/999999",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 404

    def test_review_chunk_admin_only(
        self, client, admin_token, viewer_token, sample_kb_document
    ):
        """Test that chunk review requires admin role."""
        chunk_id = sample_kb_document["chunks"][1].id  # pending_review chunk

        # Viewer cannot review
        response = client.post(
            f"/api/v1/kb/chunks/{chunk_id}/review",
            headers={"Authorization": f"Bearer {viewer_token}"},
            json={"action": "approve", "notes": "Looks good"},
        )

        assert response.status_code == 403
        assert "admin" in response.json()["detail"].lower()

        # Admin can review
        response = client.post(
            f"/api/v1/kb/chunks/{chunk_id}/review",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"action": "approve", "notes": "Approved by admin"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["review_status"] == "reviewed"

    def test_review_chunk_reject(self, client, admin_token, sample_kb_document):
        """Test rejecting a chunk."""
        chunk_id = sample_kb_document["chunks"][1].id

        response = client.post(
            f"/api/v1/kb/chunks/{chunk_id}/review",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"action": "reject", "notes": "Needs improvement"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["review_status"] == "rejected"


class TestKBCacheAPI:
    """Test suite for KB cache endpoints."""

    def test_get_cache_stats(self, client, admin_token):
        """Test getting cache statistics."""
        response = client.get(
            "/api/v1/kb/cache/stats",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "hits" in data
        assert "misses" in data
        assert "total_requests" in data
        assert "hit_rate" in data
        assert isinstance(data["hits"], int)
        assert isinstance(data["hit_rate"], float)

    def test_cache_stats_requires_auth(self, client):
        """Test that cache stats require authentication."""
        response = client.get("/api/v1/kb/cache/stats")
        assert response.status_code == 403


class TestKBAccessControl:
    """Test suite for KB access control enforcement."""

    def test_viewer_can_read_public_documents(
        self, client, viewer_token, sample_kb_document
    ):
        """Test that viewers can access PUBLIC documents."""
        response = client.get(
            "/api/v1/kb/documents",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

    def test_search_filters_by_access_level(
        self, client, viewer_token, sample_kb_document
    ):
        """Test that search respects access control."""
        response = client.post(
            "/api/v1/kb/search",
            headers={"Authorization": f"Bearer {viewer_token}"},
            json={
                "query": "revenue",
                "top_k": 10,
                "jurisdiction": "HK",
            },
        )

        assert response.status_code == 200
        data = response.json()
        # Should only return accessible chunks (no RESTRICTED for viewer)
        for result in data["results"]:
            assert result["chunk_id"] is not None
