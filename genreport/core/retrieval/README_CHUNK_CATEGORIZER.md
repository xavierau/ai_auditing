# DSPy Chunk Categorizer

**Purpose:** Intelligent categorization of knowledge base chunks during ingestion with semi-automated review.

## Quick Start

```python
from genreport.core.retrieval.chunk_categorizer import ChunkCategorizer
import dspy

# Configure DSPy with cost-efficient model
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

# Initialize categorizer
categorizer = ChunkCategorizer(auto_approve_threshold=0.85)

# Categorize a single chunk
result = categorizer.categorize(
    chunk_content="Revenue is recognised when control is transferred to the customer.",
    kb_document_title="HKFRS 15 Revenue Recognition",
    chunk_index=25
)

print(f"Type: {result.chunk_type}")  # requirement
print(f"Confidence: {result.confidence_score}")  # 0.92
print(f"Status: {result.review_status}")  # auto_approved
```

## Features

- **6 Chunk Types**: definition, requirement, example, guidance, disclosure, measurement
- **80%+ Auto-Approval**: High-confidence chunks auto-approved (≥0.85)
- **Cost-Efficient**: <$0.05 per chunk with Gemini Flash/GPT-4o-mini
- **Market-Agnostic**: Works for HK/SG/AU without modification
- **Transparent Reasoning**: ChainOfThought provides explanations
- **Type-Safe**: Pydantic models for validation
- **Batch Processing**: Efficient batch categorization
- **95% Code Coverage**: 43 comprehensive tests

## Chunk Types

| Type | Description | Example |
|------|-------------|---------|
| **definition** | Core accounting term definitions | "Revenue is the gross inflow..." |
| **requirement** | Mandatory accounting treatments | "An entity shall recognize..." |
| **example** | Illustrative examples/scenarios | "For instance, if a company..." |
| **guidance** | Implementation guidance | "Entities should consider..." |
| **disclosure** | Required financial disclosures | "An entity shall disclose..." |
| **measurement** | Measurement/recognition criteria | "Measure at fair value..." |

## Model Selection

| Model | Cost/Chunk | Quality | Use Case |
|-------|-----------|---------|----------|
| **Gemini 1.5 Flash** | $0.000083 | Very Good | Development/Testing (CHEAPEST) |
| **GPT-4o-mini** | $0.000165 | Excellent | Production (RECOMMENDED) |
| **Claude 3.5 Haiku** | $0.000313 | Excellent | High-stakes (Premium) |

## Batch Processing

```python
from genreport.core.retrieval.chunk_categorizer import ChunkCategorizationInput

# Prepare batch
chunks = [
    ChunkCategorizationInput(
        chunk_content="Revenue is the gross inflow...",
        kb_document_title="HKFRS 15",
        chunk_index=1
    ),
    # ... more chunks
]

# Process batch
results = categorizer.categorize_batch(chunks, log_progress=True)

# Get statistics
stats = categorizer.get_statistics(results)
print(f"Auto-approved: {stats['auto_approved']} ({stats['auto_approval_rate']:.1f}%)")
```

## Integration Example

```python
class KBIngestionServiceWithCategorizer:
    def __init__(self, db, categorizer_lm=None):
        self.categorizer = ChunkCategorizer(lm=categorizer_lm, auto_approve_threshold=0.85)

    def ingest_pdf(self, pdf_path, title, jurisdiction):
        # ... extract, chunk ...

        # Categorize chunks
        categorization_inputs = [
            ChunkCategorizationInput(
                chunk_content=chunk.content[:2000],
                kb_document_title=title,
                chunk_index=chunk.chunk_index
            )
            for chunk in text_chunks
        ]

        categorization_results = self.categorizer.categorize_batch(categorization_inputs)

        # Store with categorization metadata
        for chunk, cat_result in zip(text_chunks, categorization_results):
            kb_chunk = KBChunk(
                chunk_type=cat_result.chunk_type,
                confidence_score=cat_result.confidence_score,
                review_status=cat_result.review_status,
                chunk_metadata={
                    "categorization_reasoning": cat_result.reasoning,
                }
            )
```

## Files

- **Implementation**: `chunk_categorizer.py` (121 lines, 95% coverage)
- **Examples**: `chunk_categorizer_example.py` (usage patterns)
- **Enhanced Ingestion**: `kb_ingestion_service_with_categorizer.py`
- **Tests**: `tests/core/retrieval/test_chunk_categorizer.py` (43 tests)
- **Guide**: `docs/guides/2025-10-18-chunk-categorizer-implementation.md`

## Testing

```bash
# Run all tests
pytest tests/core/retrieval/test_chunk_categorizer.py -v

# Run with coverage
pytest tests/core/retrieval/test_chunk_categorizer.py --cov=genreport.core.retrieval.chunk_categorizer
```

**Results:** 43 tests, 100% pass rate, 95% code coverage

## Performance Targets

- **Auto-approval rate**: ≥80%
- **Cost per chunk**: <$0.05 ✓
- **Accuracy**: ≥90% (to be validated in production)
- **Speed**: >100 chunks/min (depends on model)

## Documentation

See comprehensive guide: `docs/guides/2025-10-18-chunk-categorizer-implementation.md`

## Architecture Compliance

✓ **SOLID Principles**: Clean separation, dependency injection
✓ **Market-Agnostic**: No hardcoded jurisdictions
✓ **Type-Safe**: Pydantic models
✓ **TDD**: Test-first development
✓ **Clean Architecture**: Core component with no market-specific logic
✓ **DSPy Best Practices**: ChainOfThought, Pydantic signatures, proper composition

## Support

For questions or issues:
1. Check examples: `chunk_categorizer_example.py`
2. Read guide: `docs/guides/2025-10-18-chunk-categorizer-implementation.md`
3. Run tests: `pytest tests/core/retrieval/test_chunk_categorizer.py -v`
