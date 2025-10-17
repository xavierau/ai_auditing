"""Demonstration of enhanced embedding service with multiple providers.

Shows how to use both Google Gemini and OpenAI embeddings.
"""

from genreport.core.retrieval.embedding_service import EmbeddingService


def demo_gemini_embeddings():
    """Demonstrate Gemini embedding generation."""
    print("\n" + "=" * 60)
    print("Google Gemini Embeddings Demo")
    print("=" * 60)

    try:
        # Initialize with Gemini (default from settings)
        service = EmbeddingService(provider="gemini")

        print(f"\nProvider: {service.get_provider_name()}")
        print(f"Model: {service.get_model_name()}")
        print(f"Dimensions: {service.get_dimensions()}")

        # Test single embedding with different task types
        test_document = """
        Revenue is recognised when the entity satisfies a performance obligation
        by transferring a promised good or service to a customer.
        """

        print("\n1️⃣  Generating embedding for document...")
        doc_embedding = service.generate_embedding(
            test_document, task_type="RETRIEVAL_DOCUMENT"
        )
        print(f"   ✓ Generated {len(doc_embedding)}-dimensional embedding")
        print(f"   First 5 values: {doc_embedding[:5]}")

        # Test query embedding
        test_query = "What is revenue recognition?"

        print("\n2️⃣  Generating embedding for query...")
        query_embedding = service.generate_embedding(test_query, task_type="RETRIEVAL_QUERY")
        print(f"   ✓ Generated {len(query_embedding)}-dimensional embedding")
        print(f"   First 5 values: {query_embedding[:5]}")

        # Test batch embedding
        test_texts = [
            "Revenue from sale of goods",
            "Revenue from rendering of services",
            "Contract modifications and variations",
        ]

        print("\n3️⃣  Generating batch embeddings...")
        batch_embeddings = service.generate_embeddings_batch(test_texts)
        print(f"   ✓ Generated {len(batch_embeddings)} embeddings")
        for i, emb in enumerate(batch_embeddings):
            print(f"   Text {i+1}: {len(emb)} dimensions")

        print("\n✅ Gemini embeddings working successfully!")

    except Exception as e:
        print(f"\n❌ Gemini demo failed: {e}")
        print("   Make sure GOOGLE_API_KEY is set in .env")


def demo_openai_embeddings():
    """Demonstrate OpenAI embedding generation."""
    print("\n" + "=" * 60)
    print("OpenAI Embeddings Demo")
    print("=" * 60)

    try:
        # Initialize with OpenAI
        service = EmbeddingService(provider="openai")

        print(f"\nProvider: {service.get_provider_name()}")
        print(f"Model: {service.get_model_name()}")
        print(f"Dimensions: {service.get_dimensions()}")

        # Test single embedding
        test_text = """
        Lease accounting under HKFRS 16 requires recognition of
        right-of-use assets and lease liabilities.
        """

        print("\n1️⃣  Generating embedding...")
        embedding = service.generate_embedding(test_text)
        print(f"   ✓ Generated {len(embedding)}-dimensional embedding")
        print(f"   First 5 values: {embedding[:5]}")

        # Test batch embedding
        test_texts = [
            "Initial measurement of lease liability",
            "Subsequent measurement of right-of-use asset",
            "Short-term lease exemptions",
        ]

        print("\n2️⃣  Generating batch embeddings...")
        batch_embeddings = service.generate_embeddings_batch(test_texts)
        print(f"   ✓ Generated {len(batch_embeddings)} embeddings")
        for i, emb in enumerate(batch_embeddings):
            print(f"   Text {i+1}: {len(emb)} dimensions")

        print("\n✅ OpenAI embeddings working successfully!")

    except Exception as e:
        print(f"\n❌ OpenAI demo failed: {e}")
        print("   Make sure OPENAI_API_KEY is set in .env")


def demo_configuration_options():
    """Demonstrate different configuration options."""
    print("\n" + "=" * 60)
    print("Configuration Options Demo")
    print("=" * 60)

    print("\n1️⃣  Using settings defaults (from .env):")
    print("   EMBEDDING_PROVIDER=gemini")
    print("   GEMINI_EMBEDDING_MODEL=models/gemini-embedding-001")
    print("   GEMINI_EMBEDDING_DIMENSIONS=1536 (configurable: 128-3072)")

    print("\n2️⃣  Override with custom configuration:")
    print("   service = EmbeddingService(")
    print("       provider='openai',")
    print("       model='text-embedding-3-large',")
    print("       dimensions=3072")
    print("   )")

    print("\n3️⃣  Task-specific embeddings (Gemini only):")
    print("   RETRIEVAL_DOCUMENT - for documents in search corpus")
    print("   RETRIEVAL_QUERY - for search queries")
    print("   SEMANTIC_SIMILARITY - for similarity comparisons")
    print("   CLASSIFICATION - for text classification")
    print("   CLUSTERING - for text clustering")


if __name__ == "__main__":
    print("=" * 60)
    print("Enhanced Embedding Service Demonstration")
    print("Multiple Providers Support")
    print("=" * 60)

    # Show configuration options
    demo_configuration_options()

    # Demo Gemini (default)
    demo_gemini_embeddings()

    # Demo OpenAI (alternative)
    # demo_openai_embeddings()  # Uncomment if you have OpenAI API key

    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)
    print("\nTo use in your code:")
    print("  from genreport.core.retrieval.embedding_service import EmbeddingService")
    print("  service = EmbeddingService()  # Uses settings defaults")
    print("  embedding = service.generate_embedding(text)")
