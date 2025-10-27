# Agentic RAG with ReAct Pattern Design

**Date:** 2025-10-23
**Status:** 🎯 Design Phase
**Objective:** True agentic RAG system with reasoning, query rewriting, and iterative search

## Overview

The current RAG Orchestrator is a **smart retrieval coordinator** that selects strategies. What we need is a **ReAct Agent** that can:

1. **Think**: Analyze the query and decide what information is needed
2. **Act**: Execute retrieval with rewritten queries
3. **Observe**: Review results and decide if more information is needed
4. **Iterate**: Perform additional searches if necessary
5. **Synthesize**: Build final result with proper references

## Implementation Approach: DSPy ReAct (Recommended)

**We use `dspy.ReAct` instead of manually implementing a for-loop.**

**Why DSPy ReAct?**
- ✅ Automatic THINK→ACT→OBSERVE→DECIDE cycle
- ✅ Built-in tool calling with proper formatting
- ✅ Proven ReAct prompting patterns from research
- ✅ Optimizable with `dspy.BootstrapFewShot`
- ✅ ~10 lines of code vs. ~100 for manual loop
- ✅ Better reasoning and error handling

**Code Comparison:**

```python
# ❌ Manual For-Loop (complex, not optimizable)
for iteration in range(max_iterations):
    analysis = reasoner.reason_about_query(query)
    results = actor.execute_retrieval(query)
    assessment = reasoner.assess_results(query, results)
    if not assessment.need_more_info:
        break
    query = reasoner.rewrite_query(query, assessment.gaps)

# ✅ DSPy ReAct (simple, optimizable)
result = react_agent(question=query)
```

**Agent Tools:**
1. `search_knowledge_base(query)` - Search accounting standards KB
2. `search_by_section(section_name, query)` - Search specific section

DSPy automatically manages the reasoning loop, tool calls, and trace logging.

## Current vs. Desired Architecture

### Current: Smart Orchestrator (Not True Agentic)

```
User Query
    ↓
Query Understanding (rule-based intent detection)
    ↓
Strategy Selection (fixed rules)
    ↓
Single Retrieval (semantic/structure-aware/hybrid)
    ↓
Results (no iteration, no reasoning)
```

**Limitations:**
- ❌ No reasoning about what information is actually needed
- ❌ No query rewriting or refinement
- ❌ No iteration or follow-up searches
- ❌ No result quality assessment
- ❌ No autonomous decision-making

### Desired: ReAct Agent (True Agentic RAG)

```
User Query
    ↓
┌─────────────────────────────────────────────┐
│ ReAct Agent (Reasoning Loop)                │
│                                             │
│  1. THINK: What do I need to find?         │
│     - Analyze query intent                  │
│     - Decompose into sub-questions          │
│     - Plan retrieval strategy               │
│     ↓                                       │
│  2. ACT: Execute retrieval                  │
│     - Rewrite query for better results      │
│     - Select optimal strategy               │
│     - Execute RAG Engine search             │
│     ↓                                       │
│  3. OBSERVE: Review results                 │
│     - Assess result quality                 │
│     - Check if query is answered            │
│     - Identify information gaps             │
│     ↓                                       │
│  4. DECIDE: Need more information?          │
│     - Yes → Loop back to THINK (new query)  │
│     - No → Proceed to SYNTHESIZE            │
│     ↓                                       │
│  5. SYNTHESIZE: Build final result          │
│     - Combine all retrieved chunks          │
│     - Add proper references                 │
│     - Generate coherent response            │
└─────────────────────────────────────────────┘
    ↓
Final Result with References
```

**Benefits:**
- ✅ Autonomous reasoning about information needs
- ✅ Query rewriting for better retrieval
- ✅ Iterative search until satisfied
- ✅ Quality assessment of results
- ✅ True agent autonomy

## DSPy ReAct Agent Implementation

```python
from dspy.functional import Tool

class AgenticRAGAgent(dspy.Module):
    """ReAct Agent using DSPy's built-in ReAct module.

    DSPy automatically handles:
    - THINK: Reasoning about next action
    - ACT: Calling tools (search_knowledge_base, search_by_section)
    - OBSERVE: Reviewing tool outputs
    - DECIDE: Whether to continue or finish
    """

    def __init__(
        self,
        rag_orchestrator: RAGOrchestrator,
        tenant_id: UUID,
        user_id: int,
        max_iterations: int = 3,
    ):
        super().__init__()
        self.rag_orchestrator = rag_orchestrator
        self.tenant_id = tenant_id
        self.user_id = user_id

        # Define tools for the agent
        self.tools = [
            Tool(
                name="search_knowledge_base",
                description=(
                    "Search the accounting standards knowledge base. "
                    "Use this when you need specific information about "
                    "accounting standards, requirements, or policy templates. "
                    "Input: search query (string). "
                    "Output: relevant chunks with sources."
                ),
                func=self._retrieve_knowledge,
            ),
            Tool(
                name="search_by_section",
                description=(
                    "Search within a specific section of the standards. "
                    "Use this when you know which section to look in "
                    "(e.g., 'Section 23 Revenue', 'Appendix 2'). "
                    "Input: section_name, query. "
                    "Output: relevant chunks from that section."
                ),
                func=self._retrieve_by_section,
            ),
        ]

        # DSPy ReAct handles the entire reasoning loop
        self.react_agent = dspy.ReAct(
            signature="question -> answer: str, references: list[str]",
            tools=self.tools,
            max_iters=max_iterations,
        )

    def _retrieve_knowledge(self, query: str) -> str:
        """Tool function: Search knowledge base.

        Returns formatted results for the agent to observe.
        """
        rag_query = RAGQuery(
            query_text=query,
            top_k=5,
            strategy=RetrievalStrategy.HYBRID,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
        )

        result = self.rag_orchestrator.retrieve(rag_query)

        # Format results for agent observation
        if not result.chunks:
            return "No results found."

        formatted = []
        for i, chunk in enumerate(result.chunks[:5], 1):
            formatted.append(
                f"[{i}] {chunk.source_reference}\n"
                f"Relevance: {chunk.relevance_score:.3f}\n"
                f"Content: {chunk.content[:300]}...\n"
            )

        return "\n".join(formatted)

    def _retrieve_by_section(self, section_name: str, query: str) -> str:
        """Tool function: Search within specific section.

        Returns formatted results from the specified section.
        """
        rag_query = RAGQuery(
            query_text=query,
            top_k=3,
            strategy=RetrievalStrategy.STRUCTURE_AWARE,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            section_filter=section_name,  # Assume RAGQuery supports this
        )

        result = self.rag_orchestrator.retrieve(rag_query)

        if not result.chunks:
            return f"No results found in section '{section_name}'."

        formatted = []
        for i, chunk in enumerate(result.chunks[:3], 1):
            formatted.append(
                f"[{i}] {chunk.source_reference}\n"
                f"Content: {chunk.content[:200]}...\n"
            )

        return "\n".join(formatted)

    def forward(self, query: str) -> AgenticRAGResult:
        """Execute ReAct loop for query answering.

        DSPy ReAct automatically handles:
        - THINK: Reasoning about next action
        - ACT: Calling tools (search_knowledge_base, search_by_section)
        - OBSERVE: Reviewing tool outputs
        - DECIDE: Whether to continue or finish
        """

        # DSPy ReAct handles the entire loop automatically
        result = self.react_agent(question=query)

        # Parse the trace to build search history
        search_history = self._extract_search_history(result)

        # Extract references from the answer
        references = self._extract_references(result.answer)

        return AgenticRAGResult(
            query=query,
            answer=result.answer,
            references=references,
            search_history=search_history,
            total_iterations=len(search_history),
            total_chunks_retrieved=sum(h.get("results_count", 0) for h in search_history),
            unique_chunks=len(references),
            final_quality_score=0.85,  # Could be computed from result confidence
        )

    def _extract_search_history(self, result) -> List[dict]:
        """Extract search history from ReAct trace."""
        # DSPy ReAct provides trace of actions
        history = []

        # Parse the trace (DSPy stores this in result metadata)
        if hasattr(result, "trajectory"):
            for i, step in enumerate(result.trajectory, 1):
                history.append({
                    "iteration": i,
                    "thought": step.get("thought", ""),
                    "action": step.get("action", ""),
                    "observation": step.get("observation", "")[:100],
                    "results_count": 5,  # Approximate
                })

        return history

    def _extract_references(self, answer: str) -> List[Reference]:
        """Extract references from answer text.

        Looks for patterns like [1], [2], etc. and matches them
        to the search results.
        """
        import re

        # Find all [N] patterns in answer
        ref_pattern = r'\[(\d+)\]'
        ref_nums = set(re.findall(ref_pattern, answer))

        references = []
        for i, ref_num in enumerate(sorted(ref_nums, key=int), 1):
            references.append(Reference(
                ref_id=int(ref_num),
                source=f"Source {ref_num}",  # Would be extracted from search results
                relevance_score=0.85,  # Would be from actual search
                content_preview="Content preview...",
            ))

        return references

    def _deduplicate_chunks(self, chunks: List[RetrievalChunk]) -> List[RetrievalChunk]:
        """Remove duplicate chunks by chunk_id."""
        seen = set()
        unique = []
        for chunk in chunks:
            if chunk.chunk_id not in seen:
                seen.add(chunk.chunk_id)
                unique.append(chunk)
        return unique

    def _build_references(self, chunks: List[RetrievalChunk]) -> List[Reference]:
        """Build structured references from chunks."""
        references = []
        for i, chunk in enumerate(chunks, 1):
            references.append(Reference(
                ref_id=i,
                source=chunk.source_reference,
                relevance_score=chunk.relevance_score,
                content_preview=chunk.content[:150],
            ))
        return references
```

## Data Models

```python
from pydantic import BaseModel, Field
from typing import List

class Reference(BaseModel):
    """Structured reference to source material."""
    ref_id: int = Field(..., description="Reference number [1], [2], etc.")
    source: str = Field(..., description="Source reference (e.g., 'HKFRS 15, Section 31')")
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    content_preview: str = Field(..., description="Preview of content")

class AgenticRAGResult(BaseModel):
    """Final result from agentic RAG with DSPy ReAct."""
    query: str = Field(..., description="Original user query")
    answer: str = Field(..., description="Synthesized answer from ReAct agent")
    references: List[Reference] = Field(..., description="Source references")
    search_history: List[dict] = Field(..., description="ReAct trace: thoughts, actions, observations")
    total_iterations: int = Field(..., description="Number of ReAct iterations")
    total_chunks_retrieved: int = Field(..., description="Total chunks retrieved across all searches")
    unique_chunks: int = Field(..., description="Unique chunks after deduplication")
    final_quality_score: float = Field(..., description="Quality assessment (0-1)")
```

## Example Workflow with DSPy ReAct

### Query: "What are the revenue recognition policy requirements for a SaaS company in Hong Kong?"

**DSPy ReAct Trace:**

```
Question: What are the revenue recognition policy requirements for a SaaS company in Hong Kong?

Thought 1: I need to find information about revenue recognition under Hong Kong
accounting standards, specifically for SaaS/software companies. Let me search
for HKFRS 15 requirements.

Action 1: search_knowledge_base("revenue recognition HKFRS 15 SaaS software subscription")

Observation 1:
[1] HKFRS 15, Section 31 - Contract identification
Relevance: 0.92
Content: Revenue is recognised when a performance obligation is satisfied by
transferring control of a promised good or service to a customer...

[2] HKFRS 15, Section 31.5 - Performance obligations
Relevance: 0.89
Content: For software arrangements, entities need to identify distinct performance
obligations. Subscription-based services typically represent a single performance
obligation satisfied over time...

Thought 2: Good start, but I need more specific guidance on SaaS implementation
and policy wording. Let me search for performance obligation analysis for software.

Action 2: search_knowledge_base("performance obligation software subscription timing recognition")

Observation 2:
[3] HKFRS 15, Section 31.8 - Recognition timing
Relevance: 0.88
Content: For services provided over time, revenue is recognised based on the
progress towards complete satisfaction of the performance obligation...

[4] Appendix 1, Example 23 - Software revenue
Relevance: 0.78
Content: Example: Software company provides cloud-based accounting software on
a subscription basis. The entity grants the customer access to the software
over the subscription period...

Thought 3: I have good technical requirements, but still missing the accounting
policy template wording. Let me search the appendices for policy templates.

Action 3: search_by_section("Appendix 2", "revenue recognition policy template")

Observation 3:
[5] Appendix 2, Template - Revenue recognition policy
Relevance: 0.95
Content: The Group recognises revenue from software subscriptions over the
subscription period as access to the software is provided. Revenue from
implementation services is recognised when the service is complete...

Finish[
Answer: For a SaaS company in Hong Kong, revenue recognition must follow HKFRS 15.
Key requirements include:

1. Identify the contract with the customer [1]
2. Identify performance obligations - for SaaS, typically:
   - Right to access software (over time)
   - Implementation services (point in time or over time) [2]
3. Determine transaction price [3]
4. Allocate price to performance obligations
5. Recognize revenue when performance obligations are satisfied [4]

For subscription revenue, recognize over the subscription period. For implementation,
assess whether it's distinct or part of combined performance obligation [5].

Recommended policy wording: "The Group recognises revenue from software subscriptions
over the subscription period as access to the software is provided. Revenue from
implementation services is recognised when the service is complete..." [6]

References:
[1] HKFRS 15, Section 31
[2] HKFRS 15, Section 31.5
[3] HKFRS 15, Section 31.8
[4] Appendix 1, Example 23
[5] Appendix 2, Template
]
```

**Key Benefits of DSPy ReAct:**

1. **Natural Language Thoughts:** DSPy generates human-readable reasoning
2. **Automatic Tool Selection:** Agent decides which tool to use (search_knowledge_base vs. search_by_section)
3. **Dynamic Stopping:** Agent decides when enough information is gathered
4. **Better Formatting:** Clean Finish[answer + references] output
5. **Trace Logging:** Complete reasoning trace for debugging and audit

## Implementation Plan

### Phase 1: Tool Implementation (Week 1, Days 1-2)
- [ ] Implement `_retrieve_knowledge()` tool function
- [ ] Implement `_retrieve_by_section()` tool function
- [ ] Test tools independently with RAG orchestrator
- [ ] Format tool outputs for agent observation

### Phase 2: DSPy ReAct Agent (Week 1, Days 3-4)
- [ ] Set up DSPy ReAct with tool definitions
- [ ] Implement `AgenticRAGAgent` class
- [ ] Test ReAct loop with simple queries
- [ ] Verify THINK→ACT→OBSERVE→DECIDE cycle

### Phase 3: Result Processing (Week 1, Day 5)
- [ ] Implement `_extract_search_history()` from ReAct trace
- [ ] Implement `_extract_references()` from answer text
- [ ] Build `AgenticRAGResult` from ReAct output
- [ ] Test result formatting

### Phase 4: Integration (Week 2, Days 1-2)
- [ ] Integrate with existing RAG Orchestrator
- [ ] Update `BaseFinancialAgent` to use AgenticRAG
- [ ] Add configuration for agentic vs. simple mode
- [ ] Update notebook 04 to demonstrate ReAct

### Phase 5: Optimization (Week 2, Days 3-5)
- [ ] Create evaluation dataset (10-20 test queries)
- [ ] Use `dspy.BootstrapFewShot` to optimize ReAct prompts
- [ ] Benchmark vs. non-agentic baseline
- [ ] Add caching for repeated tool calls

### Phase 6: Production Readiness (Week 3)
- [ ] Add comprehensive error handling
- [ ] Implement timeout safeguards
- [ ] Add audit logging for agent decisions
- [ ] Performance testing and latency optimization

## Performance Considerations

### Latency Impact

**Non-Agentic (Current):**
- Single retrieval: 500ms-1.5s
- Total: <2s

**Agentic (New):**
- Reasoning overhead: ~500ms per iteration
- Retrieval: 500ms-1.5s per iteration
- 3 iterations: ~3-7 seconds total

**Mitigation:**
- Cache reasoning for similar queries
- Parallel retrieval when possible
- Early stopping when quality threshold met

### Cost Impact

**Current:**
- Single LLM call for understanding: ~$0.001
- Retrieval: Database query cost

**Agentic:**
- 3 iterations × 3 reasoning steps: ~$0.01-0.02 per query
- Synthesis: ~$0.005

**Total:** ~$0.015-0.025 per agentic query

**Mitigation:**
- Use smaller model for reasoning (GPT-4o-mini)
- Cache common reasoning patterns
- Optimize prompts to reduce tokens

## Evaluation Metrics

1. **Answer Quality:**
   - Completeness: Does it answer all aspects?
   - Accuracy: Are references correct?
   - Relevance: Is information pertinent?

2. **Efficiency:**
   - Average iterations to satisfaction
   - Retrieval redundancy rate
   - Quality score progression

3. **User Satisfaction:**
   - Reference usefulness
   - Answer clarity
   - Citation accuracy

## Next Steps

### Immediate Actions
1. **Design Review:** Review this architecture (approved ✅)
2. **DSPy Setup:** Set up DSPy environment and configure LLM (Gemini/GPT-4o)
3. **Tool Implementation:** Implement `_retrieve_knowledge()` and `_retrieve_by_section()` tools
4. **Prototype:** Build minimal DSPy ReAct agent with 2 tools
5. **Integration:** Connect to existing RAG Orchestrator

### Week 1 Deliverables
- ✅ Working DSPy ReAct agent prototype
- ✅ Tool functions integrated with RAG orchestrator
- ✅ Example trace showing THINK→ACT→OBSERVE→DECIDE cycle
- ✅ Unit tests for tool functions

### Week 2 Deliverables
- ✅ Full `AgenticRAGAgent` implementation
- ✅ Result processing and reference extraction
- ✅ Integration with `BaseFinancialAgent`
- ✅ Updated notebook 04 demonstrating ReAct

### Week 3 Deliverables
- ✅ Evaluation dataset (10-20 test queries)
- ✅ DSPy optimization with `BootstrapFewShot`
- ✅ Performance comparison: agentic vs. non-agentic
- ✅ Production-ready implementation with audit logging

---

## Related Documentation

**Foundation Architecture:**
- `2025-10-22-retrieval-optimization-plan.md` - Overall retrieval strategy and semantic chunking
- `2025-10-22-structure-aware-retrieval.md` - Document structure navigation using TOC
- `2025-10-23-rag-orchestrator-design.md` - Multi-strategy retrieval orchestration layer (required dependency)

**Implementation Status:**
- See `docs/reports/2025-10-24-agentic-rag-integration-complete.md` for deployment details
- See `notebooks/04_agentic_rag_demo.py` for working demonstration

---

## Document History

| Date | Version | Changes |
|------|---------|---------|
| 2025-10-23 | 1.0 | Initial agentic RAG design with DSPy ReAct |
| 2025-10-24 | 1.1 | Added cross-references and implementation status |

---

## Summary

**Key Decision: Use DSPy ReAct Instead of Manual Loop**

**Why DSPy ReAct?**
- ✅ **10 lines vs. 100 lines** - Dramatically simpler implementation
- ✅ **Proven patterns** - Research-backed ReAct prompting
- ✅ **Optimizable** - Can learn from examples with `BootstrapFewShot`
- ✅ **Automatic reasoning** - THINK→ACT→OBSERVE→DECIDE handled by DSPy
- ✅ **Tool-based** - Clean separation between agent and retrieval logic
- ✅ **Traceable** - Full reasoning trace for debugging and audit

**What We're Building:**
- True agentic RAG with autonomous reasoning
- Query rewriting and iterative search
- Proper source attribution and references
- Integration with existing RAG Orchestrator
- Market-agnostic design (works for HK, SG, AU)

**Impact:**
- Better answer quality through iterative refinement
- Complete source traceability for audit compliance
- Reduced manual intervention for complex queries
- Foundation for future agent enhancements
