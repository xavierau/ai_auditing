# Agentic RAG Integration Guide

**Date:** 2025-10-24
**Status:** ✅ Complete
**Related Docs:**
- Architecture: `docs/architecture/2025-10-18-sprint4-implementation-plan.md`
- Agentic RAG Agent: `notebooks/04_agentic_rag.ipynb`

## Overview

This guide explains how AgenticRAGAgent is integrated with BaseFinancialAgent to provide autonomous template and requirements retrieval for audit report generation.

### Key Concept

When generating audit reports, financial agents (HKRevenueAgent, HKDepreciationAgent, etc.) need to:
1. **Fetch templates** - Get disclosure templates with formatting guidance
2. **Fetch requirements** - Get accounting requirements (mandatory/optional items)
3. **Fetch context** - Get additional guidance for specific scenarios

**AgenticRAGAgent** uses DSPy ReAct to autonomously reason about what information is needed, perform iterative searches, and synthesize comprehensive answers with proper source attribution.

## Architecture

### Integration Flow

```
User Request: "Generate revenue disclosure for Project X"
    ↓
AgentFactory.create_agents(jurisdiction="HK", job_id=job_123)
    ↓
    ├─ Creates RAGOrchestrator
    └─ Creates HKRevenueAgent(retriever=RAGOrchestrator, job_id=job_123)
        ↓
HKRevenueAgent.process(agent_input)
    ↓
    ├─ Step 1: agent._fetch_template("HKFRS 15 revenue disclosure")
    │   └─ Creates AgenticRAGAgent on-demand
    │       └─ ReAct: THINK → ACT → OBSERVE → DECIDE (max 3 iterations)
    │           └─ Returns: template text + references with page numbers
    │
    ├─ Step 2: agent._fetch_requirements("HKFRS 15 revenue recognition")
    │   └─ Uses AgenticRAGAgent (cached if same job)
    │       └─ ReAct: autonomous reasoning
    │           └─ Returns: requirements text + references
    │
    ├─ Step 3: agent._fetch_context("revenue policy", use_agentic=True)
    │   └─ Uses AgenticRAGAgent for company-specific context
    │       └─ Returns: Source objects with attribution
    │
    ├─ Step 4: Generate disclosure with DSPy
    │   └─ DSPy receives:
    │       - template (from Step 1)
    │       - requirements (from Step 2)
    │       - trial_balance (from agent_input)
    │       - accounting_policies (from agent_input)
    │       - context (from Step 3)
    │   └─ Returns: disclosure text + confidence + completeness
    │
    └─ Step 5: Combine all sources for audit trail
        └─ Returns: AgentOutput with disclosure + all references
```

## Implementation Details

### BaseFinancialAgent Extensions

**File:** `genreport/core/orchestration/base_agent.py`

Added methods:

#### 1. `_create_agentic_rag(max_iterations=3)` → AgenticRAGAgent
Creates AgenticRAGAgent on-demand using the existing retriever.

**Validation:** Ensures retriever is RAGOrchestrator (has `query_understanding` attribute).

#### 2. `_fetch_with_agentic_rag(query, query_type, max_iterations=3)` → AgenticRAGResult
Core method that:
- Generates cache key from query + query_type + max_iterations
- Checks job-level cache (`self._agentic_cache`)
- Creates AgenticRAGAgent and runs ReAct loop
- Caches result for job duration
- Returns AgenticRAGResult with answer + references

#### 3. `_fetch_template(disclosure_type)` → AgenticRAGResult
Convenience method for fetching templates.

**Query Format:**
```python
"Find the disclosure template and formatting requirements for {disclosure_type}. "
"Include examples, structure guidance, and any mandatory sections required by the standard."
```

#### 4. `_fetch_requirements(disclosure_type)` → AgenticRAGResult
Convenience method for fetching requirements.

**Query Format:**
```python
"What are the accounting requirements for {disclosure_type}? "
"Include mandatory disclosures, optional items, presentation requirements, "
"and any specific conditions or thresholds that apply."
```

#### 5. `_fetch_context(query, top_k=5, use_agentic=True)` → List[Source]
Enhanced to support agentic mode:
- `use_agentic=True`: Uses AgenticRAGAgent for autonomous reasoning
- `use_agentic=False`: Uses simple RAGOrchestrator retrieval (legacy)

Converts AgenticRAGResult.references to Source objects for compatibility.

#### 6. `clear_agentic_cache()` → None
Clears job-level cache. Call when:
- Starting a new job
- Source files change
- Line items are updated

### HKRevenueAgent Integration

**File:** `markets/hk/agents/revenue_agent.py`

#### Updated DSPy Signature

```python
class RevenueDisclosureSignature(dspy.Signature):
    """Generate revenue recognition disclosure following HKFRS 15 or SME-FRS."""

    # NEW: Added template and requirements inputs
    template: str = dspy.InputField(
        desc="Disclosure template with formatting requirements and structure guidance from standards"
    )
    requirements: str = dspy.InputField(
        desc="Mandatory and optional disclosure requirements from accounting standards with source references"
    )

    # Existing fields
    trial_balance: str = dspy.InputField(...)
    accounting_policies: str = dspy.InputField(...)
    accounting_standard: str = dspy.InputField(...)
    context: str = dspy.InputField(...)

    # Outputs (unchanged)
    disclosure: str = dspy.OutputField(...)
    confidence: float = dspy.OutputField(...)
    completeness: float = dspy.OutputField(...)
    sources_used: str = dspy.OutputField(...)
```

#### Updated process() Method

**Old workflow:**
```python
def process(self, agent_input):
    # 1. Fetch context
    sources = self._fetch_context(query)

    # 2. Generate disclosure
    result = self.dspy_module(
        trial_balance=...,
        accounting_policies=...,
        accounting_standard=...,
        context=context_text,
    )

    return AgentOutput(disclosure_text=result.disclosure, sources=sources)
```

**New agentic workflow:**
```python
def process(self, agent_input):
    # 1. Fetch template using AgenticRAG
    template_result = self._fetch_template("HKFRS 15 revenue disclosure")
    template_text = template_result.answer

    # 2. Fetch requirements using AgenticRAG
    requirements_result = self._fetch_requirements("HKFRS 15 revenue recognition")
    requirements_text = requirements_result.answer

    # 3. Fetch context using AgenticRAG
    sources = self._fetch_context(query, use_agentic=True)
    context_text = "\n\n".join([s.snippet for s in sources])

    # 4. Generate disclosure with template + requirements
    result = self.dspy_module(
        template=template_text,              # NEW
        requirements=requirements_text,      # NEW
        trial_balance=...,
        accounting_policies=...,
        accounting_standard=...,
        context=context_text,
    )

    # 5. Combine all sources for audit trail
    all_sources = self._combine_agentic_sources(
        template_result, requirements_result, sources
    )

    return AgentOutput(
        disclosure_text=result.disclosure,
        sources=all_sources,  # All references from agentic searches
        confidence_score=result.confidence,
        completeness_score=result.completeness,
    )
```

#### Helper Methods

**`_get_disclosure_type(standard)` → str**
Maps accounting standard to disclosure type description:
- `"HKFRS"` → `"HKFRS 15 Revenue from Contracts with Customers disclosure"`
- `"SME-FRS"` → `"SME-FRS Section 23 Revenue disclosure for small and medium entities"`

**`_combine_agentic_sources(template_result, requirements_result, context_sources)` → List[Source]**
Combines references from all agentic searches:
1. Extracts references from template_result.references
2. Extracts references from requirements_result.references
3. Adds context_sources (already Source objects)
4. Deduplicates by source_reference
5. Returns combined list for audit trail

### Job-Level Caching

**Cache Key Format:**
```python
cache_key = hashlib.md5(f"{query_type}:{query}:{max_iterations}".encode()).hexdigest()
```

**Cache Scope:**
- Stored in `agent._agentic_cache` (dict)
- Lifetime: Single job (same `job_id`)
- Invalidation: When source files/line items change (new `job_id`)

**Example:**
```python
# Job 1 - First run
agent = HKRevenueAgent(..., job_id=uuid4())
template1 = agent._fetch_template("HKFRS 15 revenue disclosure")  # Cache MISS - runs AgenticRAG
requirements1 = agent._fetch_requirements("HKFRS 15 revenue recognition")  # Cache MISS

# Job 1 - Second disclosure (same job)
template2 = agent._fetch_template("HKFRS 15 revenue disclosure")  # Cache HIT - instant
requirements2 = agent._fetch_requirements("HKFRS 15 revenue recognition")  # Cache HIT

# Job 2 - After source files change
agent.clear_agentic_cache()  # Or create new agent with new job_id
template3 = agent._fetch_template("HKFRS 15 revenue disclosure")  # Cache MISS - re-runs
```

### AgentFactory Updates

**File:** `genreport/core/orchestration/agent_factory.py`

#### New Parameters

```python
@staticmethod
def create_agents(
    jurisdiction: str,
    tenant_id: UUID,
    user_id: int,
    db: Session,
    job_id: Optional[UUID] = None,  # NEW: For agentic RAG caching
    cache_client: Optional[any] = None,
    enable_caching: bool = True,
    enable_structure_aware: bool = True,
) -> Dict[str, BaseFinancialAgent]:
    ...

    # Pass job_id to agents
    agents = {
        "revenue": HKRevenueAgent(
            market_config=market_config,
            retriever=rag_orchestrator,
            tenant_id=tenant_id,
            user_id=user_id,
            job_id=job_id,  # NEW
        ),
        ...
    }
```

## Usage Examples

### Example 1: Basic Usage

```python
from uuid import uuid4
from genreport.core.orchestration.agent_factory import AgentFactory

# Create agents with job_id for caching
job_id = uuid4()
agents = AgentFactory.create_agents(
    jurisdiction="HK",
    tenant_id=tenant_id,
    user_id=user_id,
    db=db,
    job_id=job_id,  # Agentic cache scoped to this job
)

# Get revenue agent
revenue_agent = agents["revenue"]

# Generate disclosure - uses agentic RAG internally
agent_input = AgentInput(
    tenant_id=tenant_id,
    project_id=123,
    trial_balance={"revenue": 1000000},
    accounting_policies={"revenue_recognition": "Point in time"},
)

output = revenue_agent.process(agent_input)

# Inspect sources (includes all agentic references)
for source in output.sources:
    print(f"[{source.chunk_id}] {source.source_reference} (score: {source.relevance_score:.3f})")
```

### Example 2: Manual Agentic RAG Usage

```python
# Create agent
agent = HKRevenueAgent(
    market_config=hk_config,
    retriever=rag_orchestrator,
    tenant_id=tenant_id,
    user_id=user_id,
    job_id=uuid4(),
)

# Step 1: Fetch template
template_result = agent._fetch_template("HKFRS 15 revenue disclosure")
print(f"Template: {template_result.answer[:200]}...")
print(f"References: {len(template_result.references)}")

# Step 2: Fetch requirements
requirements_result = agent._fetch_requirements("HKFRS 15 revenue recognition")
print(f"Requirements: {requirements_result.answer[:200]}...")
print(f"References: {len(requirements_result.references)}")

# Step 3: Fetch context
sources = agent._fetch_context("performance obligations", use_agentic=True)
print(f"Context sources: {len(sources)}")
```

### Example 3: Cache Management

```python
# Create agent for job
job_id = uuid4()
agent = HKRevenueAgent(..., job_id=job_id)

# Process multiple disclosures (benefits from caching)
for project in projects:
    agent_input = AgentInput(...)
    output = agent.process(agent_input)  # Reuses cached template & requirements

# Source files changed - invalidate cache
agent.clear_agentic_cache()

# OR create new agent with new job_id
new_job_id = uuid4()
agent = HKRevenueAgent(..., job_id=new_job_id)
```

## Testing

**Test Files:**
- `tests/core/orchestration/test_base_agent_agentic.py` - BaseFinancialAgent methods (9 tests)
- `tests/markets/hk/agents/test_revenue_agent_agentic.py` - HKRevenueAgent integration

**Test Coverage:**
- ✅ Agent initialization with job_id
- ✅ Creating AgenticRAGAgent on-demand
- ✅ Fetching templates with autonomous reasoning
- ✅ Fetching requirements with page numbers
- ✅ Job-level caching (cache hit/miss)
- ✅ Cache clearing
- ✅ Source combination and deduplication
- ✅ End-to-end agentic workflow

**Run Tests:**
```bash
# Run all agentic tests
pytest tests/core/orchestration/test_base_agent_agentic.py -v
pytest tests/markets/hk/agents/test_revenue_agent_agentic.py -v

# With coverage
pytest tests/core/orchestration/test_base_agent_agentic.py --cov=genreport.core.orchestration.base_agent
```

## Performance Considerations

### Cost

**Per Disclosure (without caching):**
- Template fetch: 1-3 LLM calls (ReAct iterations)
- Requirements fetch: 1-3 LLM calls
- Context fetch: 1-3 LLM calls
- Disclosure generation: 1 LLM call
- **Total: 4-10 LLM calls**

**With Job-Level Caching:**
- First disclosure: 4-10 calls
- Subsequent disclosures (same job): 1 call (only generation)
- **Cost reduction: 75-90% for multi-disclosure jobs**

### Latency

**Per Disclosure (without caching):**
- Template fetch: ~2-5 seconds
- Requirements fetch: ~2-5 seconds
- Context fetch: ~2-5 seconds
- Disclosure generation: ~3-8 seconds
- **Total: ~9-23 seconds**

**With Job-Level Caching:**
- First disclosure: 9-23 seconds
- Subsequent disclosures: 3-8 seconds (cached)
- **Latency reduction: 65-85% for multi-disclosure jobs**

### Optimization Tips

1. **Use consistent job_id** for related disclosures
2. **Set max_iterations appropriately:**
   - Simple queries: `max_iterations=2`
   - Complex queries: `max_iterations=3` (default)
   - Very complex: `max_iterations=4-5` (use sparingly)
3. **Clear cache when source changes:**
   ```python
   if source_files_changed:
       agent.clear_agentic_cache()
       # OR create new agent with new job_id
   ```

## Benefits

### 1. Autonomous Reasoning
AgenticRAGAgent automatically:
- Determines what information is needed
- Performs iterative searches
- Assesses result quality
- Decides if more searches are needed
- Synthesizes comprehensive answers

### 2. Complete Source Attribution
Every piece of information includes:
- Source reference (e.g., "HKFRS 15, Section 31, p.58")
- Page number (extracted automatically)
- Relevance score
- Content preview

### 3. Job-Level Efficiency
Cache prevents redundant agentic reasoning:
- Templates cached per job
- Requirements cached per job
- 75-90% cost reduction for multi-disclosure jobs

### 4. Quality Improvement
Templates and requirements ensure:
- Correct structure and formatting
- Complete mandatory disclosures
- Consistent style across disclosures
- Compliance with accounting standards

### 5. Audit Trail
Complete transparency:
- All sources tracked
- Reasoning steps logged
- Page numbers for verification
- Facilitates manual review

## Troubleshooting

### Issue: "AgenticRAGAgent requires RAGOrchestrator"

**Cause:** Retriever is not RAGOrchestrator.

**Solution:**
```python
# Use AgentFactory (automatically creates RAGOrchestrator)
agents = AgentFactory.create_agents(jurisdiction="HK", ...)

# OR manually create RAGOrchestrator
rag_orchestrator = RAGOrchestrator(db=db, jurisdiction="HK", ...)
agent = HKRevenueAgent(retriever=rag_orchestrator, ...)
```

### Issue: High latency for first disclosure

**Cause:** No caching - AgenticRAGAgent runs full ReAct loops.

**Expected Behavior:** First disclosure is slower (9-23s), subsequent ones are faster (3-8s).

**Solution:** This is normal. Use job-level caching for efficiency.

### Issue: Cached results not updating after KB changes

**Cause:** Cache not cleared after knowledge base updates.

**Solution:**
```python
# After KB update
agent.clear_agentic_cache()

# OR create new agent with new job_id
new_job_id = uuid4()
agent = HKRevenueAgent(..., job_id=new_job_id)
```

### Issue: AgenticRAG returns insufficient context

**Cause:** `max_iterations` too low for complex queries.

**Solution:**
```python
# Increase max_iterations for complex queries
template_result = agent._fetch_with_agentic_rag(
    query="complex query requiring multiple searches",
    query_type="template",
    max_iterations=5,  # Increase from default 3
)
```

## Next Steps

1. **Implement for other agents:**
   - HKInventoryAgent
   - HKDepreciationAgent
   - HKProvisionsAgent

2. **Add agentic modes:**
   - Simple mode: use_agentic=False (fast, cheap)
   - Agentic mode: use_agentic=True (intelligent, comprehensive)

3. **Monitor performance:**
   - Log agentic query latency
   - Track cache hit rates
   - Measure cost per disclosure

4. **Optimize caching:**
   - Add Redis for cross-job caching
   - Implement TTL-based invalidation
   - Cache at tenant level (with KB version tracking)

## References

- **AgenticRAGAgent:** `genreport/core/orchestration/agentic_rag_agent.py`
- **BaseFinancialAgent:** `genreport/core/orchestration/base_agent.py`
- **HKRevenueAgent:** `markets/hk/agents/revenue_agent.py`
- **AgentFactory:** `genreport/core/orchestration/agent_factory.py`
- **Demo Notebook:** `notebooks/04_agentic_rag.ipynb`
- **Test Suite:** `tests/core/orchestration/test_base_agent_agentic.py`

---

**Status:** ✅ Production-ready
**Test Coverage:** 9/9 tests passing (100%)
**Integration:** Complete for HKRevenueAgent
