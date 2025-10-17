"""Embedding Cache - Redis caching layer for embeddings.

Provides cost-efficient caching of embeddings with:
- SHA256 content-based cache keys
- Provider and model-specific caching
- Configurable TTL (Time To Live)
- Cache statistics tracking
- Whitespace normalization
"""

import hashlib
import json
import re
from typing import List, Optional, Dict

import redis

from genreport.core.utils.config import settings


class EmbeddingCache:
    """Redis-based cache for embeddings.

    Cache Key Format:
        embedding:{provider}:{model}:{dimensions}:{content_hash}

    Features:
    - Content-based hashing (SHA256)
    - Provider/model separation
    - TTL support (default: 7 days for queries, permanent for documents)
    - Hit/miss statistics
    - Whitespace normalization

    Example:
        >>> cache = EmbeddingCache(provider="gemini", model="models/gemini-embedding-001")
        >>> embedding = cache.get_cached_embedding("revenue recognition")
        >>> if embedding is None:
        ...     embedding = generate_embedding("revenue recognition")
        ...     cache.cache_embedding("revenue recognition", embedding)
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        dimensions: Optional[int] = None,
        ttl_days: Optional[int] = 7,
        redis_client: Optional[redis.Redis] = None,
    ):
        """Initialize embedding cache.

        Args:
            provider: Embedding provider (gemini, openai). Uses settings default if None.
            model: Model name. Uses settings default if None.
            dimensions: Embedding dimensions. Uses settings default if None.
            ttl_days: Time to live in days. None = no expiry (permanent).
            redis_client: Optional custom Redis client. Uses settings default if None.
        """
        self.provider = provider or settings.embedding_provider
        self.model = model or settings.embedding_model
        self.dimensions = dimensions or settings.embedding_dimensions
        self.ttl_days = ttl_days

        # Initialize Redis client
        if redis_client:
            self.redis = redis_client
        else:
            self.redis = redis.Redis.from_url(
                settings.redis_url_str,
                decode_responses=False,  # We'll handle JSON encoding
            )

        # Statistics tracking
        self._stats_key = f"embedding_cache_stats:{self.provider}:{self.model}"

    def get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """Get cached embedding for text.

        Args:
            text: Text content to lookup

        Returns:
            Cached embedding vector or None if not found

        Raises:
            ValueError: If text is empty
        """
        if not text or len(text.strip()) == 0:
            return None

        # Generate cache key
        cache_key = self._generate_cache_key(text)

        try:
            # Attempt to retrieve from cache
            cached_data = self.redis.get(cache_key)

            if cached_data:
                # Cache hit
                self._increment_stat("hits")
                embedding = json.loads(cached_data)
                return embedding
            else:
                # Cache miss
                self._increment_stat("misses")
                return None

        except Exception as e:
            # Log error but don't fail the operation
            print(f"Cache retrieval error: {e}")
            self._increment_stat("errors")
            return None

    def cache_embedding(self, text: str, embedding: List[float]) -> bool:
        """Cache an embedding.

        Args:
            text: Text content (used for cache key)
            embedding: Embedding vector to cache

        Returns:
            True if successfully cached, False otherwise

        Raises:
            ValueError: If text or embedding is invalid
        """
        # Validate inputs
        if not text or len(text.strip()) == 0:
            raise ValueError("Text cannot be empty")

        if not isinstance(embedding, list):
            raise ValueError("Embedding must be a list")

        if not embedding:
            raise ValueError("Embedding cannot be empty")

        # Generate cache key
        cache_key = self._generate_cache_key(text)

        try:
            # Serialize embedding to JSON
            embedding_json = json.dumps(embedding)

            # Calculate TTL in seconds (None = no expiry)
            ttl_seconds = None
            if self.ttl_days is not None:
                ttl_seconds = self.ttl_days * 24 * 60 * 60

            # Store in Redis
            if ttl_seconds:
                self.redis.setex(cache_key, ttl_seconds, embedding_json)
            else:
                self.redis.set(cache_key, embedding_json)

            return True

        except Exception as e:
            # Log error but don't fail the operation
            print(f"Cache storage error: {e}")
            self._increment_stat("errors")
            return False

    def get_cache_stats(self) -> Dict[str, float]:
        """Get cache statistics.

        Returns:
            Dict with hits, misses, errors, and hit_rate
        """
        try:
            stats_data = self.redis.hgetall(self._stats_key)

            # Decode bytes to strings and convert to int
            hits = int(stats_data.get(b"hits", b"0"))
            misses = int(stats_data.get(b"misses", b"0"))
            errors = int(stats_data.get(b"errors", b"0"))

            total = hits + misses
            hit_rate = (hits / total) if total > 0 else 0.0

            return {
                "hits": hits,
                "misses": misses,
                "errors": errors,
                "total_requests": total,
                "hit_rate": hit_rate,
            }

        except Exception as e:
            print(f"Error retrieving cache stats: {e}")
            return {
                "hits": 0,
                "misses": 0,
                "errors": 0,
                "total_requests": 0,
                "hit_rate": 0.0,
            }

    def clear_cache(self) -> bool:
        """Clear all cached embeddings for this provider/model.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Find all keys matching this provider/model
            pattern = f"embedding:{self.provider}:{self.model}:*"
            keys = self.redis.keys(pattern)

            if keys:
                self.redis.delete(*keys)

            # Reset statistics
            self.redis.delete(self._stats_key)

            return True

        except Exception as e:
            print(f"Cache clear error: {e}")
            return False

    def _generate_cache_key(self, text: str) -> str:
        """Generate cache key from text content.

        Uses SHA256 hash of normalized text to ensure:
        - Same content = same key
        - Different whitespace = same key
        - Provider/model separation

        Args:
            text: Text content

        Returns:
            Cache key string
        """
        # Normalize whitespace
        normalized_text = self._normalize_text(text)

        # Generate SHA256 hash
        content_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()

        # Construct cache key
        cache_key = f"embedding:{self.provider}:{self.model}:{self.dimensions}:{content_hash}"

        return cache_key

    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistent caching.

        - Strips leading/trailing whitespace
        - Collapses multiple spaces to single space
        - Converts to lowercase for case-insensitive matching

        Args:
            text: Raw text

        Returns:
            Normalized text
        """
        # Strip and collapse whitespace
        normalized = re.sub(r"\s+", " ", text.strip())

        # Lowercase for case-insensitive matching
        normalized = normalized.lower()

        return normalized

    def _increment_stat(self, stat_name: str):
        """Increment a cache statistic.

        Args:
            stat_name: Statistic name (hits, misses, errors)
        """
        try:
            self.redis.hincrby(self._stats_key, stat_name, 1)
        except Exception as e:
            print(f"Error updating cache stats: {e}")
