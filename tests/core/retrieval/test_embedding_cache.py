"""Tests for EmbeddingCache - Redis caching layer for embeddings."""

import pytest
from typing import List
from fakeredis import FakeRedis

from genreport.core.retrieval.embedding_cache import EmbeddingCache


@pytest.fixture
def fake_redis():
    """Provide a fake Redis client for testing."""
    return FakeRedis(decode_responses=False)


class TestEmbeddingCache:
    """Test suite for EmbeddingCache."""

    def test_cache_miss_returns_none(self, fake_redis):
        """Test that cache miss returns None."""
        cache = EmbeddingCache(redis_client=fake_redis)

        text = "This is a test text for embedding"
        result = cache.get_cached_embedding(text)

        assert result is None, "Cache miss should return None"

    def test_cache_hit_returns_embedding(self, fake_redis):
        """Test that cached embedding is retrieved."""
        cache = EmbeddingCache(redis_client=fake_redis)

        text = "Revenue recognition test"
        embedding = [0.1, 0.2, 0.3] * 512  # 1536 dimensions

        # Cache the embedding
        cache.cache_embedding(text, embedding)

        # Retrieve from cache
        cached_embedding = cache.get_cached_embedding(text)

        assert cached_embedding is not None, "Should retrieve cached embedding"
        assert cached_embedding == embedding, "Cached embedding should match original"

    def test_same_text_same_hash(self, fake_redis):
        """Test that same text generates same cache key."""
        cache = EmbeddingCache(redis_client=fake_redis)

        text = "Test text for cache key"
        embedding1 = [0.5] * 1536
        embedding2 = [0.6] * 1536  # Different embedding

        # Cache first embedding
        cache.cache_embedding(text, embedding1)

        # Cache second embedding with same text (should overwrite)
        cache.cache_embedding(text, embedding2)

        # Should get the second embedding
        result = cache.get_cached_embedding(text)
        assert result == embedding2, "Second embedding should overwrite first"

    def test_different_text_different_cache(self, fake_redis):
        """Test that different text generates different cache keys."""
        cache = EmbeddingCache(redis_client=fake_redis)

        text1 = "Revenue recognition"
        text2 = "Lease accounting"
        embedding1 = [0.1] * 1536
        embedding2 = [0.2] * 1536

        # Cache both
        cache.cache_embedding(text1, embedding1)
        cache.cache_embedding(text2, embedding2)

        # Retrieve both
        result1 = cache.get_cached_embedding(text1)
        result2 = cache.get_cached_embedding(text2)

        assert result1 == embedding1, "Should get first embedding"
        assert result2 == embedding2, "Should get second embedding"
        assert result1 != result2, "Different texts should have different embeddings"

    def test_provider_specific_caching(self, fake_redis):
        """Test that different providers have separate cache keys."""
        cache_gemini = EmbeddingCache(provider="gemini", model="models/gemini-embedding-001", redis_client=fake_redis)
        cache_openai = EmbeddingCache(provider="openai", model="text-embedding-ada-002", redis_client=fake_redis)

        text = "Test text"
        embedding_gemini = [0.1] * 1536
        embedding_openai = [0.2] * 1536

        # Cache with both providers
        cache_gemini.cache_embedding(text, embedding_gemini)
        cache_openai.cache_embedding(text, embedding_openai)

        # Should get different embeddings
        result_gemini = cache_gemini.get_cached_embedding(text)
        result_openai = cache_openai.get_cached_embedding(text)

        assert result_gemini == embedding_gemini, "Should get Gemini embedding"
        assert result_openai == embedding_openai, "Should get OpenAI embedding"
        assert result_gemini != result_openai, "Different providers should cache separately"

    def test_whitespace_normalization(self, fake_redis):
        """Test that whitespace differences don't affect caching."""
        cache = EmbeddingCache(redis_client=fake_redis)

        text1 = "Revenue   recognition"
        text2 = "Revenue recognition"
        embedding = [0.5] * 1536

        # Cache with extra whitespace
        cache.cache_embedding(text1, embedding)

        # Should retrieve with normalized whitespace
        result = cache.get_cached_embedding(text2)

        assert result == embedding, "Whitespace differences should be normalized"

    def test_cache_statistics(self, fake_redis):
        """Test cache statistics tracking."""
        cache = EmbeddingCache(redis_client=fake_redis)

        text1 = "Test text 1"
        text2 = "Test text 2"
        embedding = [0.3] * 1536

        # Cache one embedding
        cache.cache_embedding(text1, embedding)

        # Hit
        cache.get_cached_embedding(text1)

        # Miss
        cache.get_cached_embedding(text2)

        # Another hit
        cache.get_cached_embedding(text1)

        stats = cache.get_cache_stats()

        assert stats["hits"] >= 2, "Should track cache hits"
        assert stats["misses"] >= 1, "Should track cache misses"
        assert stats["hit_rate"] > 0, "Should calculate hit rate"

    def test_cache_with_empty_text_raises_error(self, fake_redis):
        """Test that caching empty text raises error."""
        cache = EmbeddingCache(redis_client=fake_redis)

        with pytest.raises(ValueError, match="Text cannot be empty"):
            cache.cache_embedding("", [0.1] * 1536)

        with pytest.raises(ValueError, match="Text cannot be empty"):
            cache.cache_embedding("   ", [0.1] * 1536)

    def test_cache_with_invalid_embedding_raises_error(self, fake_redis):
        """Test that caching invalid embedding raises error."""
        cache = EmbeddingCache(redis_client=fake_redis)

        with pytest.raises(ValueError, match="Embedding cannot be empty"):
            cache.cache_embedding("test", [])

        with pytest.raises(ValueError, match="Embedding must be a list"):
            cache.cache_embedding("test", None)

    def test_ttl_configuration(self, fake_redis):
        """Test that TTL can be configured."""
        # Query embeddings: 7 days TTL
        cache_query = EmbeddingCache(ttl_days=7, redis_client=fake_redis)

        # Document embeddings: No expiry (None)
        cache_doc = EmbeddingCache(ttl_days=None, redis_client=fake_redis)

        # Should not raise errors
        cache_query.cache_embedding("query text", [0.1] * 1536)
        cache_doc.cache_embedding("document text", [0.2] * 1536)

    def test_batch_cache_operations(self, fake_redis):
        """Test caching multiple embeddings at once."""
        cache = EmbeddingCache(redis_client=fake_redis)

        texts = [
            "Revenue recognition",
            "Lease accounting",
            "Inventory valuation",
        ]
        embeddings = [
            [0.1] * 1536,
            [0.2] * 1536,
            [0.3] * 1536,
        ]

        # Batch cache
        for text, embedding in zip(texts, embeddings):
            cache.cache_embedding(text, embedding)

        # Verify all cached
        for text, expected_embedding in zip(texts, embeddings):
            result = cache.get_cached_embedding(text)
            assert result == expected_embedding, f"Should cache {text}"

    def test_cache_clear(self, fake_redis):
        """Test clearing cache."""
        cache = EmbeddingCache(redis_client=fake_redis)

        # Cache some embeddings
        cache.cache_embedding("text1", [0.1] * 1536)
        cache.cache_embedding("text2", [0.2] * 1536)

        # Verify cached
        assert cache.get_cached_embedding("text1") is not None
        assert cache.get_cached_embedding("text2") is not None

        # Clear cache
        cache.clear_cache()

        # Should be empty
        assert cache.get_cached_embedding("text1") is None
        assert cache.get_cached_embedding("text2") is None
