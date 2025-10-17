"""Example usage of ChunkCategorizer for KB ingestion.

This script demonstrates:
1. Basic single-chunk categorization
2. Batch processing for efficiency
3. Integration with KB ingestion pipeline
4. Statistics and monitoring
5. Cost-efficient model selection

Usage:
    python -m genreport.core.retrieval.chunk_categorizer_example
"""

import dspy
from genreport.core.retrieval.chunk_categorizer import (
    ChunkCategorizer,
    ChunkCategorizationInput,
)


def example_single_categorization():
    """Example 1: Categorize a single chunk."""
    print("=" * 80)
    print("Example 1: Single Chunk Categorization")
    print("=" * 80)

    # Configure DSPy with a cost-efficient model
    lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0, max_tokens=500)
    dspy.configure(lm=lm)

    # Initialize categorizer
    categorizer = ChunkCategorizer(auto_approve_threshold=0.85)

    # Example chunk from HKFRS 15
    chunk_content = """
    Revenue is recognised when (or as) the entity satisfies a performance obligation
    by transferring a promised good or service to a customer. A good or service is
    transferred when (or as) the customer obtains control of that good or service.
    """

    result = categorizer.categorize(
        chunk_content=chunk_content.strip(),
        kb_document_title="HKFRS 15 Revenue Recognition",
        chunk_index=25,
    )

    print(f"\n📋 Chunk Type: {result.chunk_type}")
    print(f"🎯 Confidence: {result.confidence_score:.2f}")
    print(f"✅ Review Status: {result.review_status}")
    print(f"\n💭 Reasoning:\n{result.reasoning}")
    print()


def example_batch_categorization():
    """Example 2: Batch categorization for efficiency."""
    print("=" * 80)
    print("Example 2: Batch Categorization")
    print("=" * 80)

    # Configure DSPy with Gemini Flash for cost efficiency
    # Uncomment and add your API key for Gemini:
    # lm = dspy.LM("google/gemini-1.5-flash", api_key="YOUR_API_KEY")
    lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0, max_tokens=500)
    dspy.configure(lm=lm)

    categorizer = ChunkCategorizer(auto_approve_threshold=0.85)

    # Example chunks from HKFRS 15
    chunks = [
        ChunkCategorizationInput(
            chunk_content="Revenue is the gross inflow of economic benefits during the period arising "
            "in the ordinary course of an entity's activities.",
            kb_document_title="HKFRS 15 Revenue Recognition",
            chunk_index=1,
        ),
        ChunkCategorizationInput(
            chunk_content="An entity shall recognize revenue when (or as) it satisfies a performance "
            "obligation by transferring a promised good or service to a customer.",
            kb_document_title="HKFRS 15 Revenue Recognition",
            chunk_index=5,
        ),
        ChunkCategorizationInput(
            chunk_content="For example, if a company sells 100 products for $10 each with a 10% volume "
            "discount, the transaction price would be $900 ($10 × 100 × 0.9).",
            kb_document_title="HKFRS 15 Implementation Guide",
            chunk_index=12,
        ),
        ChunkCategorizationInput(
            chunk_content="An entity shall disclose information about its performance obligations in "
            "contracts with customers, including the timing of satisfaction.",
            kb_document_title="HKFRS 15 Revenue Recognition",
            chunk_index=45,
        ),
        ChunkCategorizationInput(
            chunk_content="Entities should consider all relevant facts and circumstances when determining "
            "whether control has transferred to the customer.",
            kb_document_title="HKFRS 15 Implementation Guide",
            chunk_index=18,
        ),
        ChunkCategorizationInput(
            chunk_content="The transaction price shall be measured at fair value of the consideration "
            "received or receivable, adjusted for the effects of variable consideration.",
            kb_document_title="HKFRS 15 Revenue Recognition",
            chunk_index=28,
        ),
    ]

    # Process batch
    results = categorizer.categorize_batch(chunks, log_progress=True)

    # Display results
    print("\n📊 Batch Results:")
    print("-" * 80)
    for i, result in enumerate(results, start=1):
        status_emoji = "✅" if result.review_status == "auto_approved" else "⚠️"
        print(
            f"{i}. {status_emoji} {result.chunk_type.upper()} "
            f"(confidence: {result.confidence_score:.2f}) - "
            f"{result.review_status}"
        )

    # Calculate statistics
    stats = categorizer.get_statistics(results)
    print("\n📈 Statistics:")
    print("-" * 80)
    print(f"Total Chunks: {stats['total_chunks']}")
    print(f"Auto-Approved: {stats['auto_approved']}")
    print(f"Pending Review: {stats['pending_review']}")
    print(f"Auto-Approval Rate: {stats['auto_approval_rate']:.1f}%")
    print(f"Average Confidence: {stats['avg_confidence']:.2f}")
    print(f"\nChunk Type Distribution:")
    for chunk_type, count in stats["chunk_type_distribution"].items():
        print(f"  - {chunk_type}: {count}")
    print()


def example_integration_with_kb_ingestion():
    """Example 3: Integration with KB ingestion pipeline."""
    print("=" * 80)
    print("Example 3: Integration with KB Ingestion")
    print("=" * 80)

    print("""
    Integration Pattern for KB Ingestion Service:

    ```python
    from genreport.core.retrieval.chunk_categorizer import (
        ChunkCategorizer,
        ChunkCategorizationInput,
    )
    import dspy

    class KBIngestionService:
        def __init__(self, db: Session):
            self.db = db
            # ... other services ...

            # Initialize chunk categorizer with cost-efficient model
            lm = dspy.LM("google/gemini-1.5-flash", api_key=settings.GEMINI_API_KEY)
            self.categorizer = ChunkCategorizer(
                lm=lm,
                auto_approve_threshold=0.85  # 85% auto-approval target
            )

        def ingest_pdf(self, pdf_path: str, title: str, jurisdiction: str, ...):
            # Step 1-3: Extract text, create KB doc, chunk text (existing code)
            # ...

            # Step 4a: Categorize chunks before storing
            print("  4a. Categorizing chunks...")
            categorization_inputs = [
                ChunkCategorizationInput(
                    chunk_content=chunk.content,
                    kb_document_title=title,
                    chunk_index=chunk.chunk_index,
                )
                for chunk in text_chunks
            ]

            categorization_results = self.categorizer.categorize_batch(
                categorization_inputs,
                log_progress=True
            )

            # Step 4b: Generate embeddings and store chunks WITH categorization
            for i in range(0, len(text_chunks), batch_size):
                batch = text_chunks[i : i + batch_size]
                batch_results = categorization_results[i : i + batch_size]

                # Generate embeddings
                embeddings = self.embedding_service.generate_embeddings_batch(
                    [chunk.content for chunk in batch]
                )

                # Create KB chunk records WITH categorization metadata
                for chunk, embedding, cat_result in zip(batch, embeddings, batch_results):
                    kb_chunk = KBChunk(
                        tenant_id=tenant_id,
                        jurisdiction=jurisdiction,
                        kb_document_id=kb_document.id,
                        chunk_index=chunk.chunk_index,
                        content=chunk.content,
                        embedding=embedding,
                        embedding_model=self.embedding_service.get_model_name(),

                        # NEW: Add categorization metadata
                        chunk_type=cat_result.chunk_type,
                        confidence_score=cat_result.confidence_score,
                        review_status=cat_result.review_status,
                        chunk_metadata={
                            **existing_metadata,
                            "categorization_reasoning": cat_result.reasoning,
                            "categorization_timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                    self.db.add(kb_chunk)

            # Log categorization statistics
            stats = self.categorizer.get_statistics(categorization_results)
            print(f"     ✓ Categorization stats: "
                  f"{stats['auto_approved']} auto-approved "
                  f"({stats['auto_approval_rate']:.1f}%), "
                  f"{stats['pending_review']} pending review")

            # Step 5: Commit (existing code)
            # ...
    ```

    Benefits:
    - Chunks are categorized during ingestion (no post-processing needed)
    - High-confidence chunks are auto-approved (80%+ target)
    - Low-confidence chunks are flagged for manual review
    - Categorization reasoning is stored for transparency
    - Cost-efficient: <$0.05 per chunk with Gemini Flash
    """)


def example_cost_efficient_models():
    """Example 4: Cost-efficient model selection."""
    print("=" * 80)
    print("Example 4: Cost-Efficient Model Selection")
    print("=" * 80)

    print("""
    Model Cost Comparison for Chunk Categorization:

    Input: ~500 tokens (chunk content + prompt)
    Output: ~150 tokens (chunk_type + confidence + reasoning)
    Total: ~650 tokens per chunk

    Model Options:

    1. OpenAI GPT-4o-mini (RECOMMENDED for quality/cost balance)
       - Cost: $0.00015 per 1K input, $0.0006 per 1K output
       - Per chunk: ~$0.000165 (~165 requests per $1)
       - Quality: Excellent
       - Speed: Fast
       ✓ RECOMMENDED: Best balance of cost, quality, and reliability

    2. Google Gemini 1.5 Flash (BEST for pure cost optimization)
       - Cost: $0.000075 per 1K input, $0.0003 per 1K output
       - Per chunk: ~$0.000083 (~1,200 requests per $1)
       - Quality: Very good
       - Speed: Very fast
       ✓ RECOMMENDED: Lowest cost option, 2x cheaper than GPT-4o-mini

    3. Anthropic Claude 3.5 Haiku (Premium option)
       - Cost: $0.00025 per 1K input, $0.00125 per 1K output
       - Per chunk: ~$0.000313 (~320 requests per $1)
       - Quality: Excellent
       - Speed: Fast
       - Use for: High-stakes categorization requiring maximum accuracy

    Cost Examples (1000 chunks):
    - GPT-4o-mini: $0.165
    - Gemini Flash: $0.083 ✓ CHEAPEST
    - Claude Haiku: $0.313

    Recommendation:
    - Development/Testing: Gemini Flash (lowest cost)
    - Production: GPT-4o-mini (best quality/cost balance)
    - High-stakes: Claude 3.5 Haiku (maximum accuracy)

    Example configuration:

    ```python
    # Option 1: GPT-4o-mini (balanced)
    lm = dspy.LM("openai/gpt-4o-mini", api_key=settings.OPENAI_API_KEY)

    # Option 2: Gemini Flash (cheapest)
    lm = dspy.LM("google/gemini-1.5-flash", api_key=settings.GEMINI_API_KEY)

    # Option 3: Claude Haiku (premium)
    lm = dspy.LM("anthropic/claude-3-5-haiku-20241022", api_key=settings.ANTHROPIC_API_KEY)

    categorizer = ChunkCategorizer(lm=lm, auto_approve_threshold=0.85)
    ```
    """)


def main():
    """Run all examples."""
    print("\n🚀 ChunkCategorizer Examples\n")

    try:
        # Run examples
        example_single_categorization()
        example_batch_categorization()
        example_integration_with_kb_ingestion()
        example_cost_efficient_models()

        print("✅ All examples completed successfully!")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print(
            "\nNote: You need to configure DSPy with a valid LM "
            "and API key to run these examples."
        )
        print(
            "Set OPENAI_API_KEY or GEMINI_API_KEY environment variable, "
            "or pass api_key to dspy.LM()"
        )


if __name__ == "__main__":
    main()
