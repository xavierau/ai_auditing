"""Redis client for caching and rate limiting.

Provides a singleton Redis client instance for the application.
"""

import redis
from genreport.core.utils.config import settings


def get_redis_client() -> redis.Redis:
    """Get Redis client instance.

    Returns:
        Redis client
    """
    # Convert Pydantic RedisDsn to string
    redis_url = str(settings.redis_url)

    return redis.Redis.from_url(
        redis_url,
        decode_responses=False,  # Return bytes for compatibility
    )


# Singleton instance
redis_client = get_redis_client()
