# Sprint 3 Implementation Plan - Executive Summary

**Date:** 2025-10-18
**Status:** Ready for Implementation
**Duration:** 10 days (62 hours)
**Developers:** 1.5 FTE

---

## What's Been Completed (Week 1)

✅ Database schema with Sprint 3 enhancements
✅ PDF extraction service (pdfplumber)
✅ Text chunking service (1000 chars, 200 overlap)
✅ Enhanced embedding service (Gemini/OpenAI support)
✅ KB ingestion service (orchestration)
✅ 453 chunks ingested from SME-FRS document

**Result:** Foundation complete. Ready for retrieval, security, and API layers.

---

## What Needs to Be Built (Week 2-2.5)

### 1. KB Retriever (Core Retrieval)
**File:** `genreport/core/retrieval/kb_retriever.py`

**Purpose:** PGVector-based semantic search with jurisdiction filtering

**Key Features:**
- Vector similarity search using cosine distance
- Two-step retrieval (metadata filter → semantic ranking)
- MANDATORY jurisdiction filtering (HK/SG/AU)
- Only returns approved chunks (auto_approved, reviewed)
- Support for chunk type and standard filtering

**Time:** 9 hours (4h impl + 4h test + 1h docs)

---

### 2. SecureKBRetriever (Security Layer)
**File:** `genreport/core/retrieval/secure_kb_retriever.py`

**Purpose:** Add access control and audit logging to base retriever

**Key Features:**
- Decorator pattern over KBRetriever
- Tenant isolation (PUBLIC + own tenant only)
- Access level enforcement (PUBLIC/TENANT/RESTRICTED)
- Comprehensive audit logging (success + failure)
- User-level access control

**Time:** 9 hours (4h impl + 4h test + 1h docs)

---

### 3. EmbeddingCache (Performance Optimization)
**File:** `genreport/core/retrieval/embedding_cache.py`

**Purpose:** Redis caching to reduce embedding API costs by 70%

**Key Features:**
- SHA256 content hashing for cache keys
- 7-day TTL for query embeddings
- Permanent storage for document embeddings
- Cache statistics tracking (hit rate, hits, misses)
- Integration with EmbeddingService

**Target:** 70%+ cache hit rate

**Time:** 7 hours (3h impl + 3h test + 1h docs)

---

### 4. ChunkCategorizer (Semi-Automated Approval)
**File:** `genreport/core/retrieval/chunk_categorizer.py`

**Purpose:** DSPy-powered chunk categorization for auto-approval

**Key Features:**
- DSPy Chain-of-Thought signature
- Categories: definition|requirement|example|guidance|disclosure|measurement
- Confidence-based auto-approval (threshold: 0.85)
- Pydantic models for type safety
- Batch processing support

**Target:** 80%+ auto-approval rate

**Time:** 7 hours (4h impl + 2h test + 1h docs)

---

### 5. KB API Endpoints (FastAPI Routes)
**File:** `genreport/api/routers/knowledge_base.py`

**Purpose:** RESTful API for KB operations

**Endpoints:**
- `POST /api/v1/kb/search` - Semantic search with jurisdiction filtering
- `GET /api/v1/kb/documents` - List KB documents
- `GET /api/v1/kb/documents/{id}` - Get document details
- `POST /api/v1/kb/ingest` - Ingest new PDF (admin only)
- `GET /api/v1/kb/pending-review` - List chunks needing review
- `POST /api/v1/kb/review/{chunk_id}` - Approve/reject chunk
- `DELETE /api/v1/kb/documents/{id}` - Soft-delete document

**Time:** 14 hours (8h impl + 4h test + 2h docs)

---

### 6. Integration & Performance Testing
**Files:** `tests/core/retrieval/test_kb_integration.py`

**Purpose:** End-to-end testing and performance validation

**Tests:**
- End-to-end workflow (ingest → retrieve)
- Retrieval accuracy with real embeddings
- Cache performance improvement validation
- Load testing (100 concurrent requests)
- Security validation (100% coverage)

**Time:** 16 hours (8h testing + 4h optimization + 4h docs)

---

## Implementation Order (Critical Path)

```
Phase 1: Foundation (Days 1-2)
└── KBRetriever (REQUIRED for all other components)

Phase 2: Security (Days 3-4)
└── SecureKBRetriever (REQUIRED for API endpoints)

Phase 3: Optimization (Days 5-6)
├── EmbeddingCache (parallel with categorizer)
└── ChunkCategorizer (parallel with cache)

Phase 4: API (Days 7-8)
└── KB API Endpoints (requires SecureKBRetriever)

Phase 5: Testing (Days 9-10)
└── Integration tests + Performance optimization
```

---

## Key Architecture Decisions

### ADR-001: PGVector for Similarity Search
**Decision:** Use PGVector extension for PostgreSQL

**Why:**
- Same database for metadata and vectors (simpler architecture)
- Efficient compound indexes (jurisdiction + tenant_id + vector)
- ACID guarantees for KB operations
- No external service needed

**Trade-off:** May need dedicated vector DB if scale exceeds 1M chunks

---

### ADR-002: Redis for Embedding Cache
**Decision:** Redis with SHA256 content hashing

**Why:**
- 70% cache hit rate = 70% cost reduction
- Sub-millisecond lookup vs 100-300ms API call
- Already required for Celery/sessions
- Persistent cache across restarts

**Trade-off:** Requires memory management (LRU eviction)

---

### ADR-003: DSPy for Chunk Categorization
**Decision:** DSPy Chain-of-Thought with confidence-based auto-approval

**Why:**
- CoT reasoning improves accuracy
- Explainable categorization for manual review
- Pydantic integration ensures type safety
- Can optimize with DSPy compiler

**Trade-off:** Requires periodic optimization with golden dataset

---

### ADR-004: Decorator Pattern for Security
**Decision:** SecureKBRetriever wraps KBRetriever

**Why:**
- Clean separation of retrieval and security concerns (SRP)
- Can test independently
- Easy to audit security logic
- Flexible to enhance security features

**Trade-off:** Minimal performance overhead (<5ms)

---

## SOLID Principles Application

### Single Responsibility Principle (SRP)
- **KBRetriever:** ONLY handles vector similarity search
- **SecureKBRetriever:** ONLY adds security concerns
- **EmbeddingCache:** ONLY manages cache operations
- **ChunkCategorizer:** ONLY categorizes chunks

### Open/Closed Principle (OCP)
- KBRetriever open for extension (SecureKBRetriever)
- EmbeddingService extended with cache support (no modification)
- API endpoints use dependency injection for flexibility

### Liskov Substitution Principle (LSP)
- SecureKBRetriever can substitute KBRetriever
- Maintains same interface contract

### Interface Segregation Principle (ISP)
- Focused interfaces with minimal public methods
- Optional parameters prevent interface bloat

### Dependency Inversion Principle (DIP)
- Depends on abstractions (EmbeddingService interface)
- DB session and services injected (not created internally)

---

## Testing Strategy

### Unit Tests (>80% coverage)
- `test_kb_retriever.py` - Jurisdiction filtering, similarity search
- `test_secure_kb_retriever.py` - Access control, audit logging
- `test_embedding_cache.py` - Cache hits/misses, TTL
- `test_chunk_categorizer.py` - Categorization accuracy

### Security Tests (100% coverage)
- Tenant isolation (PUBLIC vs TENANT documents)
- Cross-tenant data leakage prevention
- Audit logging completeness
- Access level enforcement

### Integration Tests
- End-to-end workflow (ingest → retrieve)
- Retrieval accuracy with real embeddings
- Cache performance improvement
- Load testing (100 concurrent requests)

### Performance Benchmarks
- Retrieval speed: <500ms (target)
- Cache hit rate: >70% (target)
- Auto-approval rate: >80% (target)
- API response time: <200ms (search endpoint)

---

## Definition of Done

### Functionality
- [ ] KB retrieval with PGVector working
- [ ] Jurisdiction filtering enforced
- [ ] SecureKBRetriever with access control functional
- [ ] Redis embedding cache operational
- [ ] DSPy chunk categorizer working
- [ ] All API endpoints functional

### Security
- [ ] Tenant isolation verified
- [ ] Access control enforced
- [ ] Audit logging complete
- [ ] Security tests passing (100%)
- [ ] No cross-tenant data leakage

### Performance
- [ ] Retrieval speed <500ms
- [ ] Cache hit rate >70%
- [ ] API response time <200ms
- [ ] Load testing passed

### Quality
- [ ] Unit test coverage >80%
- [ ] Integration tests passing
- [ ] Security tests passing (100%)
- [ ] Code review completed
- [ ] Documentation complete

---

## Time Estimates

| Phase | Hours | Days |
|-------|-------|------|
| Phase 1: Core Retrieval | 9h | 1.1 days |
| Phase 2: Security Layer | 9h | 1.1 days |
| Phase 3: Optimization | 14h | 1.8 days |
| Phase 4: API Layer | 14h | 1.8 days |
| Phase 5: Integration | 16h | 2.0 days |
| **Total** | **62h** | **7.8 days** |

**With buffer:** 10 days (1.5 developers)

---

## Risk Mitigation

### High-Risk Items

**Risk 1: PGVector Performance at Scale**
- **Mitigation:** Implement IVFFlat indexing, monitor query performance

**Risk 2: Cache Hit Rate Below Target**
- **Mitigation:** Analyze query patterns, adjust TTL, pre-warm common queries

**Risk 3: DSPy Auto-Approval Rate Below Target**
- **Mitigation:** Optimize with evaluation dataset, adjust confidence threshold

---

## Next Steps After Completion

1. **Sprint 4 Integration:**
   - Use SecureKBRetriever in DSPy agents
   - Implement source attribution with KB metadata

2. **Production Optimization:**
   - Create IVFFlat indexes on embeddings
   - Tune PostgreSQL for vector search
   - Implement Redis cluster

3. **Monitoring Setup:**
   - Cache hit rate monitoring
   - Retrieval latency tracking
   - Security violation alerts

---

## Files Created

### Implementation Files
- `genreport/core/retrieval/kb_retriever.py` (new)
- `genreport/core/retrieval/secure_kb_retriever.py` (new)
- `genreport/core/retrieval/embedding_cache.py` (new)
- `genreport/core/retrieval/chunk_categorizer.py` (new)
- `genreport/api/routers/knowledge_base.py` (new)
- `genreport/core/retrieval/embedding_service.py` (modified - cache integration)
- `genreport/core/retrieval/kb_ingestion_service.py` (modified - categorization)

### Test Files
- `tests/core/retrieval/test_kb_retriever.py` (new)
- `tests/core/retrieval/test_secure_kb_retriever.py` (new)
- `tests/core/retrieval/test_embedding_cache.py` (new)
- `tests/core/retrieval/test_chunk_categorizer.py` (new)
- `tests/core/retrieval/test_kb_integration.py` (new)
- `tests/api/test_knowledge_base_api.py` (new)

### Documentation
- `docs/architecture/2025-10-18-sprint3-remaining-implementation.md` (this document)
- `docs/reports/2025-10-18-sprint3-implementation-plan-summary.md` (summary)

---

## Questions Before Implementation

1. **Redis Configuration:** Is Redis already running and configured in `.env`?
2. **Admin Role:** Should we implement role-based access control now or defer to Sprint 6?
3. **File Storage:** Where should ingested PDFs be stored (local, S3, encrypted)?
4. **Rate Limiting:** Should we add rate limiting to KB endpoints now?
5. **DSPy Setup:** Is DSPy already configured with the default LLM provider?

---

**Document Version:** 1.0
**Created By:** Solution Architect Agent
**Review Status:** Ready for Implementation
**Estimated Completion:** 2025-10-28 (10 days from start)
