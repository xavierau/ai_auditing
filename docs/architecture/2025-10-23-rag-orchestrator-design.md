# RAG Orchestrator Agent - Architecture Design

**Date:** 2025-10-23
**Status:** Approved for Implementation
**Sprint:** Sprint 4 Enhancement
**Author:** Solution Architect Agent

## Executive Summary

The RAG Orchestrator Agent is a sophisticated coordination layer that transforms the current direct retrieval usage pattern into an intelligent, multi-strategy retrieval system. This agent sits between market-specific financial agents and the underlying retrieval components, providing query understanding, strategy selection, context assembly, and quality assurance.

**Key Benefits:**
- Centralized retrieval intelligence (no duplication across agents)
- Intent-aware retrieval (templates vs requirements vs examples)
- Multi-strategy support (semantic, structure-aware, hybrid)
- Query optimization and caching
- Comprehensive observability and audit trail

## 1. System Context

```
┌────────────────────────────────────────────────────────────────┐
│                    Market-Specific Agents                      │
│  (HKRevenueAgent, HKInventoryAgent, SGRevenueAgent, etc.)     │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     │ Simple API: orchestrator.retrieve(query, intent, filters)
                     │
┌────────────────────▼───────────────────────────────────────────┐
│               RAG ORCHESTRATOR AGENT                           │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Query Understanding                                      │ │
│  │ - Intent detection (template/requirement/example)       │ │
│  │ - Query expansion                                        │ │
│  │ - Filter validation                                      │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Strategy Selection                                       │ │
│  │ - Pure semantic (fast)                                   │ │
│  │ - Structure-aware (accurate)                             │ │
│  │ - Hybrid (balanced)                                      │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Retrieval Execution                                      │ │
│  │ - Multi-stage retrieval                                  │ │
│  │ - Re-ranking by intent                                   │ │
│  │ - Chunk merging (defragmentation)                        │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Context Assembly                                         │ │
│  │ - Format for agent consumption                           │ │
│  │ - Add metadata (sections, types)                         │ │
│  │ - PII detection                                          │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Observability                                            │ │
│  │ - Metrics (latency, cache hits)                          │ │
│  │ - Audit logging                                          │ │
│  │ - Query explanation                                      │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     │ Dependencies
                     │
┌────────────────────▼───────────────────────────────────────────┐
│              Retrieval Components                              │
│                                                                 │
│  • KBRetriever (semantic search)                               │
│  • StructureAwareRetriever (document navigation)               │
│  • ChunkCategorizer (content classification)                   │
│  • DocumentStructureAnalyzer (TOC intelligence)                │
│  • EmbeddingService (query embeddings)                         │
│  • Redis (caching layer)                                       │
└─────────────────────────────────────────────────────────────────┘
```

## 2. Component Architecture

### 2.1 Core Components

**RAGOrchestrator (Main Class)**
- Location: `genreport/core/orchestration/rag_orchestrator.py`
- Responsibility: Coordinate entire RAG pipeline
- Dependencies: KBRetriever, StructureAwareRetriever, EmbeddingService, Redis

**QueryUnderstanding**
- Location: `genreport/core/orchestration/query_understanding.py`
- Responsibility: Intent detection and query expansion
- Method: Rule-based pattern matching (future: LLM-based)

**StrategySelector**
- Location: `genreport/core/orchestration/strategy_selection.py`
- Responsibility: Select optimal retrieval strategy
- Logic: Intent-based + query complexity

**Data Models**
- Location: `genreport/core/orchestration/rag_models.py`
- Models: RAGQuery, RAGResult, ContextChunk, QueryIntent, RetrievalStrategy

### 2.2 Retrieval Pipeline Stages

**Stage 1: Query Understanding**
- Detect intent (template/requirement/example/definition/general)
- Expand query with synonyms
- Extract keywords

**Stage 2: Cache Lookup**
- Generate cache key (tenant-aware)
- Check Redis for cached results
- Return if cache hit

**Stage 3: Strategy Selection**
- Select strategy based on intent and query complexity
- Template intent → Structure-aware
- Requirement intent → Hybrid
- General (short) → Semantic
- General (complex) → Hybrid

**Stage 4: Retrieval Execution**
- Execute selected strategy
- Semantic: KBRetriever
- Structure-aware: StructureAwareRetriever
- Hybrid: Both + merge

**Stage 5: Re-ranking**
- Apply intent-specific boost factors
- Template queries boost template chunks
- Requirement queries boost requirement chunks

**Stage 6: Chunk Merging**
- Merge adjacent chunks from same section
- Reduces fragmentation
- Improves completeness

**Stage 7: Context Assembly**
- Convert to ContextChunk format
- Add metadata (source references, section context)
- Format for agent consumption

**Stage 8: PII Detection (Optional)**
- Scan for PII in retrieved content
- Flag for review if detected

**Stage 9: Cache Storage**
- Store result in Redis (15-minute TTL)
- Tenant-aware cache key

**Stage 10: Audit Logging**
- Log retrieval event
- Include: query, intent, strategy, latency, results count

## 3. Data Models

### 3.1 Input Model

```python
class RAGQuery(BaseModel):
    query_text: str              # Natural language query
    top_k: int = 5               # Number of results
    intent: Optional[QueryIntent] # Explicit intent (or auto-detect)
    filters: Optional[Dict]      # Filters (chunk_types, standards, sections)
    tenant_id: UUID              # Tenant ID for isolation
    user_id: int                 # User ID for audit
    project_id: Optional[int]    # Project context
```

### 3.2 Output Model

```python
class RAGResult(BaseModel):
    chunks: List[ContextChunk]   # Retrieved context chunks
    query_intent: QueryIntent    # Detected/provided intent
    strategy_used: RetrievalStrategy  # Strategy used
    total_candidates: int        # Candidates before re-ranking
    cache_hit: bool              # Whether cached
    retrieval_time_ms: float     # Latency
    metadata: Dict[str, Any]     # Additional metadata
```

### 3.3 Context Chunk Model

```python
class ContextChunk(BaseModel):
    content: str                 # Chunk text
    source_reference: str        # Human-readable source
    relevance_score: float       # 0-1 relevance
    chunk_type: ContentType      # template/requirement/example/etc
    chunk_id: int                # Database ID
    document_id: int             # Source document ID
    section_context: Optional[str]  # Section name
    is_mandatory: Optional[bool]    # Mandatory requirement?
    cross_references: List[str]     # Related sections
```

## 4. Architectural Decision Records

### ADR-001: RAG Orchestrator as Separate Component

**Decision:** Create separate RAG Orchestrator Agent between agents and retrieval components.

**Rationale:**
- Single Responsibility Principle
- DRY (avoid duplication across agents)
- Easier to add new strategies
- Independent testing

**Consequences:**
- ✅ Centralized retrieval intelligence
- ✅ Easier maintenance
- ⚠️ Additional abstraction layer

### ADR-002: Intent-Based Strategy Selection

**Decision:** Detect query intent and select strategy accordingly.

**Rationale:**
- Templates found more accurately with structure navigation
- Simple queries don't need structure overhead
- Requirements benefit from hybrid approach

**Consequences:**
- ✅ Improved relevance for domain queries
- ⚠️ Intent detection may be imperfect (mitigated with fallback)

### ADR-003: Redis Caching with 15-Minute TTL

**Decision:** Cache RAG results in Redis with 15-minute TTL.

**Rationale:**
- KB content changes infrequently
- Cache hit rate >80% expected for common queries
- 15 minutes balances freshness vs efficiency

**Consequences:**
- ✅ 5-10x speedup for cached queries
- ⚠️ Manual cache invalidation needed on KB updates

### ADR-004: Pydantic Models for Type Safety

**Decision:** Use Pydantic for all data structures.

**Rationale:**
- Type safety prevents runtime errors
- Automatic validation
- Self-documenting
- JSON serialization

**Consequences:**
- ✅ Fewer bugs, better DX
- ⚠️ Additional dependency (already used in FastAPI)

### ADR-005: Chunk Merging for Defragmentation

**Decision:** Merge adjacent chunks from same section with similar relevance.

**Rationale:**
- Fixed-size chunking fragments semantic units
- Accountants need complete content
- Reduces manual piecing together

**Consequences:**
- ✅ Reduces fragmentation rate by >50%
- ⚠️ Merged chunks may exceed token limits (mitigated by max size check)

## 5. Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Semantic retrieval latency | <500ms | N/A |
| Structure-aware latency | <1s | N/A |
| Cache hit rate | >80% | N/A |
| Average relevance score | >0.7 | N/A |
| Chunk merging rate | 30-50% | N/A |

## 6. Security Considerations

### Tenant Isolation
- All queries MUST filter by `tenant_id`
- Cache keys MUST include `tenant_id`
- Audit logs MUST record `tenant_id`

### Audit Logging
- Log ALL retrieval operations
- Include: query, intent, strategy, results count, latency
- Integrate with existing AuditLogger

### PII Detection
- Optionally scan retrieved content for PII
- Flag for review if detected
- Integrate with existing PIIDetector

## 7. Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1)
- Data models with validation
- Query understanding (rule-based)
- Strategy selector (semantic only)
- Basic RAGOrchestrator with semantic retrieval
- Unit tests (>80% coverage)

### Phase 2: Multi-Strategy Retrieval (Week 2)
- Structure-aware retrieval integration
- Hybrid retrieval implementation
- Re-ranking and merging logic
- Context assembly
- Integration tests

### Phase 3: Performance & Caching (Week 3)
- Redis caching with tenant-aware keys
- Performance optimization
- Audit logging integration
- Observability (metrics, explain methods)
- Security tests

### Phase 4: Agent Integration (Week 4)
- Update AgentFactory
- Update market-specific agents (HK revenue, inventory)
- Backward compatibility layer
- End-to-end tests

### Phase 5: Production Readiness (Week 5)
- Monitoring and alerting
- Production deployment guide
- Troubleshooting runbook
- Performance tuning
- A/B testing

## 8. Testing Strategy

### Unit Tests
- Query understanding (intent detection)
- Strategy selection logic
- Cache key generation
- Re-ranking boost factors
- Chunk merging conditions

### Integration Tests
- Structure-aware retrieval with document structure
- Hybrid retrieval combines strategies
- Chunk merging reduces fragmentation
- Audit logging creates records

### Security Tests
- Tenant isolation (different tenants)
- Cache respects tenant boundaries
- Audit log records all retrievals
- No cross-tenant data leakage

### Performance Tests
- Semantic retrieval latency <500ms
- Structure-aware latency <1s
- Cache hit speedup 5-10x
- Benchmark against baselines

## 9. Observability

### Key Metrics
- `rag_retrieval_duration_seconds` (latency by strategy, intent)
- `rag_retrieval_total` (count by strategy, intent, cache_hit)
- `rag_cache_hit_rate` (cache effectiveness)
- `rag_avg_relevance_score` (quality by intent)

### Alert Rules
- **P1 (Critical):** Error rate >5%, cache completely unavailable
- **P2 (Warning):** Latency >1s (p95), cache hit rate <60%
- **P3 (Info):** Unusual query patterns, high fragmentation

### Logging
- Structured logging with context
- Log level: INFO for successful retrievals
- Log level: WARNING for cache errors
- Log level: ERROR for retrieval failures

## 10. Future Enhancements

### LLM-Based Intent Detection
- Replace rule-based with LLM classifier (GPT-4o-mini)
- More accurate for complex queries
- Handles paraphrasing better

### Query Rewriting
- Use LLM to rewrite queries for better retrieval
- Example: "PPE depreciation" → "Property, plant and equipment depreciation disclosure requirements"

### Hybrid Retrieval with BM25
- Combine BM25 (lexical) + embeddings (semantic)
- Better for exact keyword matches (e.g., "HKFRS 15")

### User Feedback Loop
- Allow users to rate retrieved chunks
- Use feedback to tune boost factors
- Identify problematic queries
- Retrain embeddings (if custom model)

### Multi-Document Retrieval
- Retrieve from multiple standards (HKFRS 15 + SME-FRS)
- Support entity transitions

## 11. Integration Examples

### Before (Direct Retrieval)
```python
class HKRevenueAgent(BaseFinancialAgent):
    def process(self, agent_input: AgentInput) -> AgentOutput:
        # Direct retriever call
        query = self._build_retrieval_query(agent_input)
        sources = self._fetch_context(query)
        context_text = "\n\n".join([s.snippet for s in sources])
```

### After (Orchestrator Integration)
```python
class HKRevenueAgent(BaseFinancialAgent):
    def __init__(self, market_config, rag_orchestrator, tenant_id, user_id):
        super().__init__(market_config, rag_orchestrator, tenant_id, user_id)

    def process(self, agent_input: AgentInput) -> AgentOutput:
        # Build RAG query
        rag_query = RAGQuery(
            query_text=self._build_retrieval_query(agent_input),
            top_k=5,
            intent=QueryIntent.REQUIREMENT,
            filters={"chunk_types": ["requirement", "template", "example"]},
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            project_id=agent_input.project_id,
        )

        # Call orchestrator
        rag_result = self.retriever.retrieve(rag_query)

        # Convert to Source objects for backward compatibility
        sources = [
            Source(
                document_id=UUID(int=chunk.document_id),
                chunk_id=UUID(int=chunk.chunk_id),
                relevance_score=chunk.relevance_score,
                snippet=chunk.content,
            )
            for chunk in rag_result.chunks
        ]

        context_text = "\n\n".join([chunk.content for chunk in rag_result.chunks])
```

## 12. References

**Related Architecture Documentation:**
- `2025-10-22-retrieval-optimization-plan.md` - Overall retrieval optimization strategy and evaluation framework
- `2025-10-22-structure-aware-retrieval.md` - Structure-based navigation using document TOC
- `2025-10-23-agentic-rag-react-design.md` - Autonomous ReAct agent layer built on this orchestrator

**Implementation References:**
- Base agent pattern: `genreport/core/orchestration/base_agent.py`
- Existing retrievers: `genreport/core/retrieval/`
- Agent examples: `markets/hk/agents/`

## 13. Document History

| Date | Version | Changes |
|------|---------|---------|
| 2025-10-23 | 1.0 | Initial RAG orchestrator design |
| 2025-10-24 | 1.1 | Added cross-references to related architecture docs |

## 14. Approval

- [x] Architecture reviewed by Solution Architect Agent
- [x] Implementation completed (see implementation reports in docs/reports/)
- [x] Security requirements validated
- [x] Performance targets agreed upon

---

**Next Steps:**
1. See `2025-10-23-agentic-rag-react-design.md` for autonomous agent layer
2. Review implementation reports in `docs/reports/` for deployment status
3. Monitor performance metrics and tune as needed
