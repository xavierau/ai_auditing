"""Security tests for SecureKBRetriever - access control and audit logging."""

import pytest
from uuid import uuid4
from sqlalchemy.orm import Session

from genreport.core.database.models import (
    KnowledgeBase,
    KBChunk,
    Tenant,
    User,
    AuditLog,
)
from genreport.core.retrieval.secure_kb_retriever import SecureKBRetriever


@pytest.fixture
def test_tenants(db: Session):
    """Create test tenants."""
    tenant_a = Tenant(
        id=uuid4(),
        company_name="Tenant A Corp",
        data_residency_region="HK",
        jurisdiction="HK",
    )
    tenant_b = Tenant(
        id=uuid4(),
        company_name="Tenant B Corp",
        data_residency_region="HK",
        jurisdiction="HK",
    )
    db.add(tenant_a)
    db.add(tenant_b)
    db.commit()

    return {"tenant_a": tenant_a, "tenant_b": tenant_b}


@pytest.fixture
def test_users(db: Session, test_tenants):
    """Create test users."""
    tenant_a = test_tenants["tenant_a"]
    tenant_b = test_tenants["tenant_b"]

    # Tenant A users
    admin_a = User(
        tenant_id=tenant_a.id,
        email="admin@tenanta.com",
        password_hash="hashed",
        full_name="Admin A",
        role="admin",
        is_active=True,
    )
    viewer_a = User(
        tenant_id=tenant_a.id,
        email="viewer@tenanta.com",
        password_hash="hashed",
        full_name="Viewer A",
        role="viewer",
        is_active=True,
    )

    # Tenant B user
    admin_b = User(
        tenant_id=tenant_b.id,
        email="admin@tenantb.com",
        password_hash="hashed",
        full_name="Admin B",
        role="admin",
        is_active=True,
    )

    db.add(admin_a)
    db.add(viewer_a)
    db.add(admin_b)
    db.commit()

    return {
        "admin_a": admin_a,
        "viewer_a": viewer_a,
        "admin_b": admin_b,
    }


@pytest.fixture
def test_kb_documents(db: Session, test_tenants):
    """Create test KB documents with different access levels."""
    tenant_a = test_tenants["tenant_a"]
    tenant_b = test_tenants["tenant_b"]

    # PUBLIC document
    public_doc = KnowledgeBase(
        tenant_id=None,
        jurisdiction="HK",
        title="Public Standard - HKFRS 15",
        standard="HKFRS 15",
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
        content="Revenue is recognised when control transfers.",
        embedding=[0.1] * 1536,
        embedding_model="models/gemini-embedding-001",
        review_status="auto_approved",
        confidence_score=0.95,
    )
    db.add(public_chunk)

    # Tenant A TENANT document
    tenant_a_doc = KnowledgeBase(
        tenant_id=tenant_a.id,
        jurisdiction="HK",
        title="Tenant A Custom Policy",
        access_level="TENANT",
        is_active=True,
    )
    db.add(tenant_a_doc)
    db.flush()

    tenant_a_chunk = KBChunk(
        tenant_id=tenant_a.id,
        jurisdiction="HK",
        kb_document_id=tenant_a_doc.id,
        chunk_index=0,
        content="Tenant A specific policy for revenue.",
        embedding=[0.2] * 1536,
        embedding_model="models/gemini-embedding-001",
        review_status="auto_approved",
        confidence_score=0.90,
    )
    db.add(tenant_a_chunk)

    # Tenant A RESTRICTED document
    restricted_doc = KnowledgeBase(
        tenant_id=tenant_a.id,
        jurisdiction="HK",
        title="Restricted Internal Guideline",
        access_level="RESTRICTED",
        is_active=True,
    )
    db.add(restricted_doc)
    db.flush()

    restricted_chunk = KBChunk(
        tenant_id=tenant_a.id,
        jurisdiction="HK",
        kb_document_id=restricted_doc.id,
        chunk_index=0,
        content="Confidential internal guideline.",
        embedding=[0.3] * 1536,
        embedding_model="models/gemini-embedding-001",
        review_status="auto_approved",
        confidence_score=0.92,
    )
    db.add(restricted_chunk)

    # Tenant B document
    tenant_b_doc = KnowledgeBase(
        tenant_id=tenant_b.id,
        jurisdiction="HK",
        title="Tenant B Custom Policy",
        access_level="TENANT",
        is_active=True,
    )
    db.add(tenant_b_doc)
    db.flush()

    tenant_b_chunk = KBChunk(
        tenant_id=tenant_b.id,
        jurisdiction="HK",
        kb_document_id=tenant_b_doc.id,
        chunk_index=0,
        content="Tenant B specific policy.",
        embedding=[0.4] * 1536,
        embedding_model="models/gemini-embedding-001",
        review_status="auto_approved",
        confidence_score=0.88,
    )
    db.add(tenant_b_chunk)

    db.commit()

    return {
        "public": (public_doc, public_chunk),
        "tenant_a": (tenant_a_doc, tenant_a_chunk),
        "restricted": (restricted_doc, restricted_chunk),
        "tenant_b": (tenant_b_doc, tenant_b_chunk),
    }


class TestSecureKBRetriever:
    """Test suite for SecureKBRetriever access control."""

    def test_public_documents_accessible_to_all(
        self, db: Session, test_users, test_kb_documents
    ):
        """Test that PUBLIC documents are accessible to all tenants."""
        admin_a = test_users["admin_a"]
        admin_b = test_users["admin_b"]

        public_chunk_id = test_kb_documents["public"][1].id

        # Tenant A can access PUBLIC
        retriever_a = SecureKBRetriever(
            db=db,
            jurisdiction="HK",
            tenant_id=admin_a.tenant_id,
            user_id=admin_a.id,
        )
        results_a = retriever_a.retrieve(query="revenue", top_k=10)
        result_ids_a = [r["chunk_id"] for r in results_a]
        assert public_chunk_id in result_ids_a, "Tenant A should access PUBLIC documents"

        # Tenant B can also access PUBLIC
        retriever_b = SecureKBRetriever(
            db=db,
            jurisdiction="HK",
            tenant_id=admin_b.tenant_id,
            user_id=admin_b.id,
        )
        results_b = retriever_b.retrieve(query="revenue", top_k=10)
        result_ids_b = [r["chunk_id"] for r in results_b]
        assert public_chunk_id in result_ids_b, "Tenant B should access PUBLIC documents"

    def test_tenant_documents_isolated(
        self, db: Session, test_users, test_kb_documents
    ):
        """Test that TENANT documents are isolated between tenants."""
        admin_a = test_users["admin_a"]
        admin_b = test_users["admin_b"]

        tenant_a_chunk_id = test_kb_documents["tenant_a"][1].id
        tenant_b_chunk_id = test_kb_documents["tenant_b"][1].id

        # Tenant A retrieval
        retriever_a = SecureKBRetriever(
            db=db,
            jurisdiction="HK",
            tenant_id=admin_a.tenant_id,
            user_id=admin_a.id,
        )
        results_a = retriever_a.retrieve(query="policy", top_k=10)
        result_ids_a = [r["chunk_id"] for r in results_a]

        # Should include own tenant document
        assert tenant_a_chunk_id in result_ids_a, "Tenant A should access own documents"
        # Should NOT include other tenant document
        assert (
            tenant_b_chunk_id not in result_ids_a
        ), "Tenant A should NOT access Tenant B documents"

        # Tenant B retrieval
        retriever_b = SecureKBRetriever(
            db=db,
            jurisdiction="HK",
            tenant_id=admin_b.tenant_id,
            user_id=admin_b.id,
        )
        results_b = retriever_b.retrieve(query="policy", top_k=10)
        result_ids_b = [r["chunk_id"] for r in results_b]

        # Should include own tenant document
        assert tenant_b_chunk_id in result_ids_b, "Tenant B should access own documents"
        # Should NOT include other tenant document
        assert (
            tenant_a_chunk_id not in result_ids_b
        ), "Tenant B should NOT access Tenant A documents"

    def test_restricted_documents_admin_only(
        self, db: Session, test_users, test_kb_documents
    ):
        """Test that RESTRICTED documents are only accessible to admins."""
        admin_a = test_users["admin_a"]
        viewer_a = test_users["viewer_a"]

        restricted_chunk_id = test_kb_documents["restricted"][1].id

        # Admin can access RESTRICTED
        retriever_admin = SecureKBRetriever(
            db=db,
            jurisdiction="HK",
            tenant_id=admin_a.tenant_id,
            user_id=admin_a.id,
        )
        results_admin = retriever_admin.retrieve(query="guideline", top_k=10)
        result_ids_admin = [r["chunk_id"] for r in results_admin]
        assert (
            restricted_chunk_id in result_ids_admin
        ), "Admin should access RESTRICTED documents"

        # Viewer cannot access RESTRICTED
        retriever_viewer = SecureKBRetriever(
            db=db,
            jurisdiction="HK",
            tenant_id=viewer_a.tenant_id,
            user_id=viewer_a.id,
        )
        results_viewer = retriever_viewer.retrieve(query="guideline", top_k=10)
        result_ids_viewer = [r["chunk_id"] for r in results_viewer]
        assert (
            restricted_chunk_id not in result_ids_viewer
        ), "Viewer should NOT access RESTRICTED documents"

    def test_retrieval_audit_logged(self, db: Session, test_users, test_kb_documents):
        """Test that all retrievals are audit logged."""
        admin_a = test_users["admin_a"]

        # Clear existing audit logs for this test
        db.query(AuditLog).filter(AuditLog.user_id == admin_a.id).delete()
        db.commit()

        # Perform retrieval
        retriever = SecureKBRetriever(
            db=db,
            jurisdiction="HK",
            tenant_id=admin_a.tenant_id,
            user_id=admin_a.id,
        )
        results = retriever.retrieve(query="revenue recognition", top_k=5)

        # Check audit log was created
        audit_logs = (
            db.query(AuditLog)
            .filter(
                AuditLog.user_id == admin_a.id,
                AuditLog.event_type == "KB_RETRIEVAL",
            )
            .all()
        )

        assert len(audit_logs) > 0, "Retrieval should create audit log"

        latest_log = audit_logs[-1]
        assert latest_log.action == "READ"
        assert latest_log.tenant_id == admin_a.tenant_id
        assert latest_log.details["query"] == "revenue recognition"
        assert latest_log.details["jurisdiction"] == "HK"
        assert latest_log.details["results_count"] == len(results)
        assert latest_log.status == "SUCCESS"

    def test_access_denial_audit_logged(
        self, db: Session, test_users, test_kb_documents
    ):
        """Test that access denials are logged."""
        viewer_a = test_users["viewer_a"]
        restricted_doc_id = test_kb_documents["restricted"][0].id

        # Clear existing logs
        db.query(AuditLog).filter(AuditLog.user_id == viewer_a.id).delete()
        db.commit()

        # Try to access restricted document
        retriever = SecureKBRetriever(
            db=db,
            jurisdiction="HK",
            tenant_id=viewer_a.tenant_id,
            user_id=viewer_a.id,
        )

        # This should not include restricted chunks
        results = retriever.retrieve(query="confidential", top_k=10)

        # Check audit log
        audit_logs = (
            db.query(AuditLog)
            .filter(
                AuditLog.user_id == viewer_a.id,
                AuditLog.event_type == "KB_RETRIEVAL",
            )
            .all()
        )

        # Should have logged the retrieval (even if restricted was filtered)
        assert len(audit_logs) > 0
        assert audit_logs[-1].status == "SUCCESS"  # Query succeeded, just filtered

    def test_combined_access_levels(
        self, db: Session, test_users, test_kb_documents
    ):
        """Test retrieval with mixed access levels."""
        admin_a = test_users["admin_a"]

        public_chunk_id = test_kb_documents["public"][1].id
        tenant_a_chunk_id = test_kb_documents["tenant_a"][1].id
        restricted_chunk_id = test_kb_documents["restricted"][1].id
        tenant_b_chunk_id = test_kb_documents["tenant_b"][1].id

        # Admin A should see: PUBLIC + TENANT_A + RESTRICTED
        retriever = SecureKBRetriever(
            db=db,
            jurisdiction="HK",
            tenant_id=admin_a.tenant_id,
            user_id=admin_a.id,
        )
        results = retriever.retrieve(query="revenue policy guideline", top_k=20)
        result_ids = [r["chunk_id"] for r in results]

        assert public_chunk_id in result_ids, "Should see PUBLIC"
        assert tenant_a_chunk_id in result_ids, "Should see own TENANT"
        assert restricted_chunk_id in result_ids, "Admin should see RESTRICTED"
        assert tenant_b_chunk_id not in result_ids, "Should NOT see other tenant"
