# Sprint 3: Knowledge Base & Basic Generation
## Hybrid Architecture + Security Implementation (v3.0)

**Duration:** 2.5 weeks (Extended from 2 weeks)  
**Sprint Goal:** Build jurisdiction-aware KB retrieval with encryption and access control  
**Story Points:** 34 (+2 days for security)  
**Team Size:** 2-3 developers

[← Back to Master Plan](./master_sprint_plan.md)

---

## Overview

Sprint 3 builds a **secure, jurisdiction-aware Knowledge Base** that automatically filters content by market. All KB documents are encrypted, access-controlled, and audited.

### Sprint Objectives
✅ Research-driven chunking strategy  
✅ Semi-automated KB ingestion (80% auto-approval)  
✅ Jurisdiction-aware retrieval filtering  
✅ Encrypted KB storage  
✅ Per-tenant access control  
✅ Two-step retrieval (metadata + semantic)  
✅ Embedding caching (70%+ hit rate)  
✅ Template-based generation for static sections

---

## Hybrid Architecture: Jurisdiction-Aware KB

### KB Organization by Market

```
markets/
├── hk/
│   └── knowledge_base/
│       ├── standards/
│       │   ├── hkfrs_15_revenue.pdf
│       │   ├── hkfrs_16_leases.pdf
│       │   ├── sme_frs_framework.pdf
│       │   └── hkicpa_guidance.pdf
│       └── embeddings/
│           └── hkfrs_embeddings_cache.json
│
├── sg/  # Future
│   └── knowledge_base/
│       └── standards/
│           ├── sfrs_15_revenue.pdf
│           └── ...
│
└── au/  # Future
    └── knowledge_base/
        └── standards/
            ├── aasb_15_revenue.pdf
            └── ...
```

### Jurisdiction-Aware Retrieval

```python
# core/retrieval/kb_retriever.py
from typing import List, Dict
from uuid import UUID
import dspy

class KnowledgeBaseRetriever:
    """Jurisdiction-aware KB retrieval"""
    
    def __init__(self, jurisdiction: str, tenant_id: UUID):
        self.jurisdiction = jurisdiction
        self.tenant_id = tenant_id
        self.vector_db = get_vector_database()
    
    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Retrieve relevant chunks filtered by jurisdiction
        
        CRITICAL: Only returns content from the specified jurisdiction
        """
        # Generate query embedding
        query_embedding = self.embed(query)
        
        # Search with jurisdiction filter
        results = self.vector_db.query(
            query_embedding=query_embedding,
            filter={
                "jurisdiction": self.jurisdiction,  # CRITICAL: Market filter
                "tenant_id": str(self.tenant_id),   # Tenant isolation
                "is_active": True
            },
            top_k=top_k
        )
        
        # Log retrieval for audit
        self._log_retrieval(query, results)
        
        return results
    
    def _log_retrieval(self, query: str, results: List[Dict]):
        """Audit log KB retrievals"""
        from core.security.audit_logger import AuditLogger
        
        AuditLogger.log_event(
            db=get_db(),
            event_type="KB_RETRIEVAL",
            action="READ",
            tenant_id=self.tenant_id,
            resource_type="knowledge_base",
            details={
                "query": query,
                "jurisdiction": self.jurisdiction,
                "results_count": len(results)
            }
        )
```

### KB Metadata Schema

```python
# core/database/models.py (Updated for jurisdiction)
from sqlalchemy import Column, Integer, String, Date, Boolean, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID, VECTOR

class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(UUID, nullable=True)  # NULL for shared standards
    jurisdiction = Column(String(10), nullable=False)  # NEW: 'HK', 'SG', 'AU'
    
    title = Column(String(255), nullable=False)
    standard = Column(String(100))  # e.g., "HKFRS 15"
    version = Column(String(50))
    document_type = Column(String(50))
    
    source_file_path = Column(Text)
    raw_content = Column(Text)
    
    # Hierarchy (NEW)
    parent_id = Column(Integer, ForeignKey('knowledge_base.id'))
    section_level = Column(Integer, default=0)
    section_path = Column(String(255))  # e.g., "15.1.2"
    
    # Versioning (NEW)
    effective_date = Column(Date)
    supersedes_id = Column(Integer, ForeignKey('knowledge_base.id'))
    
    is_active = Column(Boolean, default=True)
    metadata = Column(JSONB)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class KBChunk(Base):
    __tablename__ = "kb_chunks"
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(UUID, nullable=True)
    jurisdiction = Column(String(10), nullable=False)  # NEW
    kb_document_id = Column(Integer, ForeignKey('knowledge_base.id', ondelete='CASCADE'))
    
    chunk_index = Column(Integer)
    chunk_type = Column(String(50))  # 'definition', 'requirement', 'example', etc.
    content = Column(Text)
    embedding = Column(VECTOR(1536))  # OpenAI ada-002
    
    # Quality metrics (NEW)
    confidence_score = Column(Float)
    review_status = Column(String(50))  # 'auto_approved', 'pending', 'reviewed'
    
    # Cross-references (NEW)
    cross_references = Column(JSONB)  # Links to related sections
    prerequisites = Column(JSONB)  # Required background knowledge
    
    metadata = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

## Security Implementation

### 1. Encrypted KB Storage

```python
# core/retrieval/secure_kb_manager.py
from core.security.encryption import EncryptionService
from typing import List

class SecureKBManager:
    """Manages encrypted KB documents"""
    
    def __init__(self, tenant_id: UUID):
        self.tenant_id = tenant_id
        self.encryption_service = EncryptionService()
    
    def ingest_document(self, file_path: str, jurisdiction: str, metadata: dict):
        """Ingest and encrypt KB document"""
        
        # Read file
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Encrypt content
        encrypted_content = self.encryption_service.encrypt_file(
            content,
            str(self.tenant_id)
        )
        
        # Store encrypted file
        encrypted_path = self._store_encrypted(encrypted_content, jurisdiction)
        
        # Create KB record
        kb_doc = KnowledgeBase(
            tenant_id=self.tenant_id,
            jurisdiction=jurisdiction,
            title=metadata['title'],
            standard=metadata['standard'],
            source_file_path=encrypted_path,
            metadata=metadata
        )
        
        db.add(kb_doc)
        db.commit()
        
        # Chunk and embed
        self._chunk_and_embed(kb_doc)
        
        return kb_doc.id
    
    def retrieve_document(self, kb_id: int) -> bytes:
        """Retrieve and decrypt KB document"""
        
        kb_doc = db.query(KnowledgeBase).filter(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.tenant_id == self.tenant_id
        ).first()
        
        if not kb_doc:
            raise PermissionError("Document not found or access denied")
        
        # Read encrypted file
        with open(kb_doc.source_file_path, 'rb') as f:
            encrypted_content = f.read()
        
        # Decrypt
        decrypted_content = self.encryption_service.decrypt_file(
            encrypted_content,
            str(self.tenant_id)
        )
        
        # Audit log
        AuditLogger.log_event(
            db=db,
            event_type="KB_ACCESS",
            action="READ",
            tenant_id=self.tenant_id,
            resource_type="knowledge_base",
            resource_id=kb_id
        )
        
        return decrypted_content
```

### 2. Access Control Per Tenant

```python
# core/retrieval/access_control.py
from enum import Enum

class AccessLevel(Enum):
    PUBLIC = 0      # Available to all
    TENANT = 1      # Tenant-specific
    RESTRICTED = 2  # Admin only

class KBAccessControl:
    """Enforce KB access policies"""
    
    @staticmethod
    def can_access(user_id: int, tenant_id: UUID, kb_id: int) -> bool:
        """Check if user can access KB document"""
        
        kb_doc = db.query(KnowledgeBase).get(kb_id)
        
        if not kb_doc:
            return False
        
        # Public documents (shared standards)
        if kb_doc.tenant_id is None and kb_doc.access_level == AccessLevel.PUBLIC:
            return True
        
        # Tenant-specific documents
        if kb_doc.tenant_id == tenant_id:
            return True
        
        # Restricted documents
        if kb_doc.access_level == AccessLevel.RESTRICTED:
            return user_has_admin_role(user_id)
        
        return False
    
    @staticmethod
    def filter_by_access(results: List[Dict], user_id: int, tenant_id: UUID) -> List[Dict]:
        """Filter retrieval results by access permissions"""
        
        accessible = []
        
        for result in results:
            kb_id = result['kb_document_id']
            if KBAccessControl.can_access(user_id, tenant_id, kb_id):
                accessible.append(result)
        
        return accessible

# Usage in retrieval
class SecureKBRetriever(KnowledgeBaseRetriever):
    """KB retriever with access control"""
    
    def __init__(self, jurisdiction: str, tenant_id: UUID, user_id: int):
        super().__init__(jurisdiction, tenant_id)
        self.user_id = user_id
    
    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """Retrieve with access control"""
        
        # Get all matching results
        results = super().retrieve(query, top_k)
        
        # Filter by access permissions
        accessible_results = KBAccessControl.filter_by_access(
            results,
            self.user_id,
            self.tenant_id
        )
        
        return accessible_results
```

### 3. Audit Logging for KB Access

```python
# Every KB operation is logged
class AuditedKBRetriever(SecureKBRetriever):
    """KB retriever with comprehensive audit logging"""
    
    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """Retrieve with full audit trail"""
        
        start_time = time.time()
        
        try:
            results = super().retrieve(query, top_k)
            
            # Log successful retrieval
            AuditLogger.log_event(
                db=get_db(),
                event_type="KB_RETRIEVAL",
                action="READ",
                user_id=self.user_id,
                tenant_id=self.tenant_id,
                resource_type="knowledge_base",
                details={
                    "query": query,
                    "jurisdiction": self.jurisdiction,
                    "results_count": len(results),
                    "response_time_ms": (time.time() - start_time) * 1000
                },
                status="SUCCESS"
            )
            
            return results
            
        except Exception as e:
            # Log failed retrieval
            AuditLogger.log_event(
                db=get_db(),
                event_type="KB_RETRIEVAL",
                action="READ",
                user_id=self.user_id,
                tenant_id=self.tenant_id,
                resource_type="knowledge_base",
                details={
                    "query": query,
                    "jurisdiction": self.jurisdiction,
                    "error": str(e)
                },
                status="FAILURE"
            )
            
            raise
```

---

## Semi-Automated Ingestion

```python
# core/retrieval/kb_ingestion.py
from typing import List, Dict
import dspy

class ChunkCategorizer(dspy.Signature):
    """LLM-based chunk categorization"""
    content: str = dspy.InputField(desc="Chunk content")
    context: str = dspy.InputField(desc="Surrounding context")
    
    chunk_type: str = dspy.OutputField(desc="Category: definition|requirement|example|guidance")
    confidence: float = dspy.OutputField(desc="Confidence 0-1")
    keywords: List[str] = dspy.OutputField(desc="Key concepts")

class SemiAutomatedIngestion:
    """80% auto-approval, 20% manual review"""
    
    AUTO_APPROVE_THRESHOLD = 0.85
    
    def __init__(self, jurisdiction: str):
        self.jurisdiction = jurisdiction
        self.categorizer = dspy.ChainOfThought(ChunkCategorizer)
    
    def ingest_document(self, pdf_path: str, metadata: dict):
        """Ingest document with auto-categorization"""
        
        # Extract and chunk
        chunks = self._extract_and_chunk(pdf_path)
        
        auto_approved = 0
        needs_review = 0
        
        for chunk in chunks:
            # Categorize with LLM
            result = self.categorizer(
                content=chunk['content'],
                context=chunk['context']
            )
            
            # Auto-approve high confidence
            if result.confidence >= self.AUTO_APPROVE_THRESHOLD:
                self._store_chunk(
                    chunk,
                    chunk_type=result.chunk_type,
                    confidence=result.confidence,
                    review_status='auto_approved'
                )
                auto_approved += 1
            else:
                # Flag for manual review
                self._store_chunk(
                    chunk,
                    chunk_type=result.chunk_type,
                    confidence=result.confidence,
                    review_status='pending_review'
                )
                needs_review += 1
        
        return {
            "total_chunks": len(chunks),
            "auto_approved": auto_approved,
            "needs_review": needs_review,
            "approval_rate": auto_approved / len(chunks)
        }
```

---

## Testing Strategy

```python
# tests/test_kb_security.py
import pytest
from uuid import uuid4

def test_jurisdiction_isolation():
    """Ensure KB retrieval respects jurisdiction boundaries"""
    
    # Create HK standard
    hk_standard = create_kb_document(jurisdiction="HK", standard="HKFRS 15")
    
    # Create SG standard
    sg_standard = create_kb_document(jurisdiction="SG", standard="SFRS 15")
    
    # Search from HK context
    hk_retriever = KnowledgeBaseRetriever(jurisdiction="HK", tenant_id=uuid4())
    hk_results = hk_retriever.retrieve("revenue recognition")
    
    # Should only return HK standards
    assert all(r['jurisdiction'] == 'HK' for r in hk_results)
    assert hk_standard.id in [r['kb_document_id'] for r in hk_results]
    assert sg_standard.id not in [r['kb_document_id'] for r in hk_results]

def test_tenant_access_control():
    """Ensure tenants cannot access each other's custom KB"""
    tenant_a = uuid4()
    tenant_b = uuid4()
    
    # Create custom KB for tenant A
    custom_kb = create_kb_document(
        tenant_id=tenant_a,
        jurisdiction="HK",
        title="Custom Accounting Policy"
    )
    
    # Try to access from tenant B
    retriever_b = SecureKBRetriever(
        jurisdiction="HK",
        tenant_id=tenant_b,
        user_id=123
    )
    
    results = retriever_b.retrieve("accounting policy")
    
    # Should NOT include tenant A's custom KB
    assert custom_kb.id not in [r['kb_document_id'] for r in results]

def test_kb_encryption():
    """Ensure KB documents are encrypted at rest"""
    tenant_id = uuid4()
    
    kb_manager = SecureKBManager(tenant_id)
    kb_id = kb_manager.ingest_document(
        "test_standard.pdf",
        jurisdiction="HK",
        metadata={"title": "Test Standard"}
    )
    
    # Read raw file
    kb_doc = db.query(KnowledgeBase).get(kb_id)
    with open(kb_doc.source_file_path, 'rb') as f:
        raw_content = f.read()
    
    # Should be encrypted (not readable)
    assert b"Test Standard" not in raw_content

def test_audit_logging():
    """Ensure KB retrievals are logged"""
    retriever = AuditedKBRetriever(
        jurisdiction="HK",
        tenant_id=uuid4(),
        user_id=1
    )
    
    retriever.retrieve("revenue recognition")
    
    # Check audit log
    logs = db.query(AuditLog).filter(
        AuditLog.event_type == "KB_RETRIEVAL"
    ).all()
    
    assert len(logs) > 0
    assert logs[-1].details['query'] == "revenue recognition"
    assert logs[-1].details['jurisdiction'] == "HK"
```

---

## Definition of Done

### Sprint 3 is complete when:

#### Core Functionality
- [x] KB ingestion pipeline functional
- [x] Semantic search working
- [x] Retrieval accuracy: Top-3 >85%, Top-5 >95%
- [x] Semi-automated ingestion (80% auto-approval)
- [x] Template-based generation for static sections

#### Hybrid Architecture
- [x] KB organized by jurisdiction (`markets/hk/knowledge_base/`)
- [x] Retrieval filtered by project jurisdiction
- [x] No hardcoded market references in core retrieval logic

#### Security
- [x] KB documents encrypted at rest
- [x] Access control enforced (tenant isolation)
- [x] Audit logging for all KB operations
- [x] Jurisdiction filtering working correctly

#### Quality
- [x] Embedding cache hit rate >70%
- [x] Retrieval speed <500ms
- [x] KB quality score >0.70
- [x] All unit and integration tests pass
- [x] Security tests pass

---

## Time Estimates

**Week 1: Research & Ingestion (40 hours)**
- Research & schema design: 16h
- Ingestion pipeline: 12h
- Encryption implementation: 8h
- Testing: 4h

**Week 2: Retrieval & Generation (40 hours)**
- Semantic search: 10h
- Access control: 8h
- Jurisdiction filtering: 6h
- Template generation: 8h
- Testing: 8h

**Week 2.5: Security & Polish (10 hours)**
- Security hardening: 4h
- Performance optimization: 3h
- Documentation: 3h

**Total: 90 hours (2.5 weeks, 2-3 developers)**

---

## Next Steps

After Sprint 3, proceed to:

**Sprint 4:** Advanced AI Report Generation
- Agents use jurisdiction-aware KB retrieval
- Context packaging respects tenant isolation
- Source attribution includes security audit trail

[→ View Sprint 4 Details](./sprint_4_agents.md)

[← Back to Master Plan](./master_sprint_plan.md)

---

**Document Version:** 3.0 (Hybrid + Security)  
**Last Updated:** 2025-10-17  
**Status:** Ready for Implementation