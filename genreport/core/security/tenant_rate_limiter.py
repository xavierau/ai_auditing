"""Tenant Rate Limiter - Per-tenant rate limiting with Redis.

This module provides rate limiting functionality to prevent abuse
and ensure fair resource allocation across tenants.

Usage:
    limiter = TenantRateLimiter()
    limiter.check_limit(tenant_id, "report_generation")

    # Or use decorator
    @rate_limit(calls=100, period="hour", operation="generate_report")
    def generate_report(tenant_id: str):
        ...
"""

import logging
from typing import Dict, Optional
from uuid import UUID
from functools import wraps

from fastapi import HTTPException
from redis.exceptions import RedisError

from genreport.core.database.redis_client import redis_client

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""

    pass


class RateLimitConfig:
    """Configuration for a rate limit."""

    PERIOD_SECONDS = {
        "second": 1,
        "minute": 60,
        "hour": 3600,
        "day": 86400,
    }

    def __init__(self, calls: int, period: str):
        """Initialize rate limit config.

        Args:
            calls: Number of calls allowed
            period: Time period (second, minute, hour, day)

        Raises:
            ValueError: If period is invalid
        """
        if period not in self.PERIOD_SECONDS:
            raise ValueError(
                f"Invalid period: {period}. "
                f"Must be one of: {list(self.PERIOD_SECONDS.keys())}"
            )

        self.calls = calls
        self.period = period
        self.window_seconds = self.PERIOD_SECONDS[period]


class TenantRateLimiter:
    """Rate limiter with per-tenant and per-operation quotas.

    Uses Redis for distributed rate limiting with sliding window algorithm.
    """

    def __init__(
        self,
        default_config: Optional[RateLimitConfig] = None,
        configs: Optional[Dict[str, RateLimitConfig]] = None,
        fail_open: bool = True,
    ):
        """Initialize rate limiter.

        Args:
            default_config: Default rate limit config (if None, uses 100/hour)
            configs: Operation-specific configs
            fail_open: If True, allow requests when Redis fails.
                      If False, deny requests when Redis fails.
        """
        self.default_config = default_config or RateLimitConfig(calls=100, period="hour")
        self.configs = configs or {}
        self.fail_open = fail_open

    def check_limit(self, tenant_id: UUID, operation: str) -> bool:
        """Check if request is within rate limit.

        Args:
            tenant_id: Tenant making the request
            operation: Operation being performed

        Returns:
            True if within limit

        Raises:
            RateLimitExceeded: If rate limit exceeded
        """
        config = self._get_config(operation)
        key = self._get_redis_key(tenant_id, operation)

        try:
            # Get current count
            current = redis_client.get(key)

            if current is None:
                # First request - initialize counter
                redis_client.incr(key)
                redis_client.expire(key, config.window_seconds)
                return True

            current_count = int(current)

            # Check if limit exceeded
            if current_count >= config.calls:
                raise RateLimitExceeded(
                    f"Rate limit exceeded: {config.calls} calls per {config.period}. "
                    f"Please try again later."
                )

            # Increment counter
            redis_client.incr(key)
            return True

        except RedisError as e:
            logger.error(f"Redis error in rate limiter: {e}")

            if self.fail_open:
                # Allow request when Redis fails
                logger.warning(f"Rate limiter failing open due to Redis error")
                return True
            else:
                # Deny request when Redis fails
                raise RateLimitExceeded(
                    "Service unavailable. Please try again later."
                )

    def get_remaining(self, tenant_id: UUID, operation: str) -> int:
        """Get remaining quota for tenant.

        Args:
            tenant_id: Tenant ID
            operation: Operation name

        Returns:
            Number of remaining calls
        """
        config = self._get_config(operation)
        key = self._get_redis_key(tenant_id, operation)

        try:
            current = redis_client.get(key)

            if current is None:
                return config.calls

            current_count = int(current)
            remaining = max(0, config.calls - current_count)

            return remaining

        except RedisError as e:
            logger.error(f"Redis error getting remaining quota: {e}")
            return config.calls if self.fail_open else 0

    def get_reset_time(self, tenant_id: UUID, operation: str) -> int:
        """Get seconds until quota resets.

        Args:
            tenant_id: Tenant ID
            operation: Operation name

        Returns:
            Seconds until reset (0 if no limit active)
        """
        key = self._get_redis_key(tenant_id, operation)

        try:
            ttl = redis_client.ttl(key)

            # -2 means key doesn't exist, -1 means no expiration
            if ttl < 0:
                return 0

            return ttl

        except RedisError as e:
            logger.error(f"Redis error getting reset time: {e}")
            return 0

    def get_quota_info(self, tenant_id: UUID, operation: str) -> Dict:
        """Get complete quota information.

        Args:
            tenant_id: Tenant ID
            operation: Operation name

        Returns:
            Dict with limit, used, remaining, reset_seconds, period
        """
        config = self._get_config(operation)
        key = self._get_redis_key(tenant_id, operation)

        try:
            current = redis_client.get(key)
            used = int(current) if current else 0
            remaining = max(0, config.calls - used)
            reset_seconds = self.get_reset_time(tenant_id, operation)

            return {
                "limit": config.calls,
                "used": used,
                "remaining": remaining,
                "reset_seconds": reset_seconds,
                "period": config.period,
            }

        except RedisError as e:
            logger.error(f"Redis error getting quota info: {e}")
            return {
                "limit": config.calls,
                "used": 0,
                "remaining": config.calls if self.fail_open else 0,
                "reset_seconds": 0,
                "period": config.period,
            }

    def clear_quota(self, tenant_id: UUID, operation: str) -> None:
        """Clear rate limit quota for specific operation.

        Args:
            tenant_id: Tenant ID
            operation: Operation name
        """
        key = self._get_redis_key(tenant_id, operation)

        try:
            redis_client.delete(key)
            logger.info(f"Cleared quota for tenant {tenant_id}, operation {operation}")

        except RedisError as e:
            logger.error(f"Redis error clearing quota: {e}")

    def clear_all_quotas(self, tenant_id: UUID) -> None:
        """Clear all rate limit quotas for tenant.

        Args:
            tenant_id: Tenant ID
        """
        try:
            # Find all keys for this tenant
            pattern = f"rate_limit:{tenant_id}:*"
            keys = redis_client.keys(pattern)

            if keys:
                redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} quotas for tenant {tenant_id}")

        except RedisError as e:
            logger.error(f"Redis error clearing all quotas: {e}")

    def _get_redis_key(self, tenant_id: UUID, operation: str) -> str:
        """Generate Redis key for tenant and operation.

        Args:
            tenant_id: Tenant ID
            operation: Operation name

        Returns:
            Redis key string
        """
        return f"rate_limit:{tenant_id}:{operation}"

    def _get_config(self, operation: str) -> RateLimitConfig:
        """Get rate limit config for operation.

        Args:
            operation: Operation name

        Returns:
            RateLimitConfig for this operation
        """
        return self.configs.get(operation, self.default_config)


def rate_limit(calls: int, period: str, operation: str):
    """Decorator for rate limiting functions.

    Usage:
        @rate_limit(calls=100, period="hour", operation="generate_report")
        def generate_report(tenant_id: str, ...):
            ...

    Args:
        calls: Number of calls allowed
        period: Time period (second, minute, hour, day)
        operation: Operation name

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract tenant_id from function arguments
            # Assumes first argument or kwarg is tenant_id
            tenant_id = None

            if args and len(args) > 0:
                tenant_id = args[0]
            elif "tenant_id" in kwargs:
                tenant_id = kwargs["tenant_id"]

            if not tenant_id:
                raise ValueError("tenant_id not found in function arguments")

            # Convert to UUID if string
            if isinstance(tenant_id, str):
                tenant_id = UUID(tenant_id)

            # Create limiter and check
            config = RateLimitConfig(calls=calls, period=period)
            limiter = TenantRateLimiter(default_config=config)

            try:
                limiter.check_limit(tenant_id, operation)
            except RateLimitExceeded as e:
                raise HTTPException(
                    status_code=429,
                    detail=str(e),
                    headers={"Retry-After": str(limiter.get_reset_time(tenant_id, operation))},
                )

            return func(*args, **kwargs)

        return wrapper

    return decorator
