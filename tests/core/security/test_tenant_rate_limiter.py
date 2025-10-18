"""Tests for TenantRateLimiter - Per-tenant rate limiting.

Following TDD methodology: These tests are written BEFORE implementation.
They define the expected behavior of TenantRateLimiter.
"""

import pytest
import time
from uuid import uuid4
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException

from genreport.core.security.tenant_rate_limiter import (
    TenantRateLimiter,
    RateLimitConfig,
    RateLimitExceeded,
)


class TestRateLimitConfig:
    """Test rate limit configuration."""

    def test_create_hourly_limit(self):
        """Create hourly rate limit config."""
        config = RateLimitConfig(calls=100, period="hour")

        assert config.calls == 100
        assert config.period == "hour"
        assert config.window_seconds == 3600

    def test_create_daily_limit(self):
        """Create daily rate limit config."""
        config = RateLimitConfig(calls=1000, period="day")

        assert config.calls == 1000
        assert config.period == "day"
        assert config.window_seconds == 86400

    def test_create_minute_limit(self):
        """Create minute rate limit config."""
        config = RateLimitConfig(calls=10, period="minute")

        assert config.calls == 10
        assert config.period == "minute"
        assert config.window_seconds == 60

    def test_invalid_period_raises_error(self):
        """Invalid period raises ValueError."""
        with pytest.raises(ValueError, match="Invalid period"):
            RateLimitConfig(calls=100, period="week")


class TestTenantRateLimiterBasicFunctionality:
    """Test basic rate limiting functionality."""

    @patch("genreport.core.security.tenant_rate_limiter.redis_client")
    def test_within_limit_allows_request(self, mock_redis):
        """Request within limit should be allowed."""
        mock_redis.get.return_value = b"5"  # 5 requests so far
        mock_redis.incr.return_value = 6

        limiter = TenantRateLimiter()
        tenant_id = uuid4()

        result = limiter.check_limit(tenant_id, "test_operation")

        assert result is True

    @patch("genreport.core.security.tenant_rate_limiter.redis_client")
    def test_exceeding_limit_raises_exception(self, mock_redis):
        """Request exceeding limit should raise RateLimitExceeded."""
        # Already at limit
        mock_redis.get.return_value = b"100"
        mock_redis.incr.return_value = 101

        limiter = TenantRateLimiter(
            default_config=RateLimitConfig(calls=100, period="hour")
        )
        tenant_id = uuid4()

        with pytest.raises(RateLimitExceeded) as exc_info:
            limiter.check_limit(tenant_id, "test_operation")

        assert "Rate limit exceeded" in str(exc_info.value)
        assert "100 calls per hour" in str(exc_info.value)

    @patch("genreport.core.security.tenant_rate_limiter.redis_client")
    def test_first_request_initializes_counter(self, mock_redis):
        """First request should initialize counter."""
        mock_redis.get.return_value = None  # No counter yet
        mock_redis.incr.return_value = 1

        limiter = TenantRateLimiter()
        tenant_id = uuid4()

        result = limiter.check_limit(tenant_id, "test_operation")

        assert result is True
        # Should set expiration on first request
        mock_redis.expire.assert_called_once()


class TestTenantRateLimiterIsolation:
    """Test tenant isolation in rate limiting."""

    @patch("genreport.core.security.tenant_rate_limiter.redis_client")
    def test_different_tenants_independent_limits(self, mock_redis):
        """Different tenants should have independent rate limits."""
        # Mock Redis to track keys independently
        redis_data = {}

        def mock_get(key):
            return redis_data.get(key)

        def mock_incr(key):
            redis_data[key] = redis_data.get(key, 0) + 1
            return redis_data[key]

        mock_redis.get.side_effect = mock_get
        mock_redis.incr.side_effect = mock_incr
        mock_redis.expire.return_value = True

        limiter = TenantRateLimiter(
            default_config=RateLimitConfig(calls=2, period="hour")
        )

        tenant_a = uuid4()
        tenant_b = uuid4()

        # Tenant A makes 2 requests (at limit)
        limiter.check_limit(tenant_a, "test_operation")
        limiter.check_limit(tenant_a, "test_operation")

        # Tenant A's 3rd request should fail
        with pytest.raises(RateLimitExceeded):
            limiter.check_limit(tenant_a, "test_operation")

        # But Tenant B should still be able to make requests
        result = limiter.check_limit(tenant_b, "test_operation")
        assert result is True


class TestTenantRateLimiterOperationSpecific:
    """Test operation-specific rate limits."""

    @patch("genreport.core.security.tenant_rate_limiter.redis_client")
    def test_different_operations_independent_limits(self, mock_redis):
        """Different operations should have independent limits."""
        redis_data = {}

        def mock_get(key):
            return redis_data.get(key)

        def mock_incr(key):
            redis_data[key] = redis_data.get(key, 0) + 1
            return redis_data[key]

        mock_redis.get.side_effect = mock_get
        mock_redis.incr.side_effect = mock_incr
        mock_redis.expire.return_value = True

        limiter = TenantRateLimiter(
            configs={
                "report_generation": RateLimitConfig(calls=2, period="hour"),
                "kb_search": RateLimitConfig(calls=5, period="hour"),
            }
        )

        tenant_id = uuid4()

        # Use up report_generation limit
        limiter.check_limit(tenant_id, "report_generation")
        limiter.check_limit(tenant_id, "report_generation")

        # report_generation should be at limit
        with pytest.raises(RateLimitExceeded):
            limiter.check_limit(tenant_id, "report_generation")

        # But kb_search should still work
        result = limiter.check_limit(tenant_id, "kb_search")
        assert result is True


class TestTenantRateLimiterQuotaReporting:
    """Test quota and limit reporting."""

    @patch("genreport.core.security.tenant_rate_limiter.redis_client")
    def test_get_remaining_quota(self, mock_redis):
        """Get remaining quota for tenant."""
        mock_redis.get.return_value = b"30"  # 30 requests used

        limiter = TenantRateLimiter(
            default_config=RateLimitConfig(calls=100, period="hour")
        )
        tenant_id = uuid4()

        remaining = limiter.get_remaining(tenant_id, "test_operation")

        assert remaining == 70  # 100 - 30

    @patch("genreport.core.security.tenant_rate_limiter.redis_client")
    def test_get_remaining_no_usage(self, mock_redis):
        """Get remaining quota when no requests made yet."""
        mock_redis.get.return_value = None  # No usage yet

        limiter = TenantRateLimiter(
            default_config=RateLimitConfig(calls=100, period="hour")
        )
        tenant_id = uuid4()

        remaining = limiter.get_remaining(tenant_id, "test_operation")

        assert remaining == 100  # Full quota available

    @patch("genreport.core.security.tenant_rate_limiter.redis_client")
    def test_get_reset_time(self, mock_redis):
        """Get time until quota resets."""
        # TTL returns seconds until expiration
        mock_redis.ttl.return_value = 1800  # 30 minutes

        limiter = TenantRateLimiter()
        tenant_id = uuid4()

        reset_seconds = limiter.get_reset_time(tenant_id, "test_operation")

        assert reset_seconds == 1800

    @patch("genreport.core.security.tenant_rate_limiter.redis_client")
    def test_get_quota_info(self, mock_redis):
        """Get complete quota information."""
        mock_redis.get.return_value = b"30"
        mock_redis.ttl.return_value = 1800

        limiter = TenantRateLimiter(
            default_config=RateLimitConfig(calls=100, period="hour")
        )
        tenant_id = uuid4()

        info = limiter.get_quota_info(tenant_id, "test_operation")

        assert info["limit"] == 100
        assert info["used"] == 30
        assert info["remaining"] == 70
        assert info["reset_seconds"] == 1800
        assert info["period"] == "hour"


class TestTenantRateLimiterRedisKeyFormat:
    """Test Redis key formatting."""

    def test_redis_key_includes_tenant_id(self):
        """Redis key should include tenant_id for isolation."""
        limiter = TenantRateLimiter()
        tenant_id = uuid4()

        key = limiter._get_redis_key(tenant_id, "test_operation")

        assert str(tenant_id) in key
        assert "test_operation" in key
        assert "rate_limit" in key

    def test_different_tenants_different_keys(self):
        """Different tenants should have different Redis keys."""
        limiter = TenantRateLimiter()
        tenant_a = uuid4()
        tenant_b = uuid4()

        key_a = limiter._get_redis_key(tenant_a, "test_operation")
        key_b = limiter._get_redis_key(tenant_b, "test_operation")

        assert key_a != key_b

    def test_different_operations_different_keys(self):
        """Different operations should have different Redis keys."""
        limiter = TenantRateLimiter()
        tenant_id = uuid4()

        key_1 = limiter._get_redis_key(tenant_id, "operation_1")
        key_2 = limiter._get_redis_key(tenant_id, "operation_2")

        assert key_1 != key_2


class TestTenantRateLimiterDecorator:
    """Test rate limiting decorator."""

    @patch("genreport.core.security.tenant_rate_limiter.redis_client")
    def test_decorator_allows_within_limit(self, mock_redis):
        """Decorator should allow request within limit."""
        from genreport.core.security.tenant_rate_limiter import rate_limit

        mock_redis.get.return_value = b"5"
        mock_redis.incr.return_value = 6
        mock_redis.expire.return_value = True

        @rate_limit(calls=10, period="hour", operation="test_op")
        def test_function(tenant_id: str):
            return "success"

        tenant_id = str(uuid4())
        result = test_function(tenant_id)

        assert result == "success"

    @patch("genreport.core.security.tenant_rate_limiter.redis_client")
    def test_decorator_raises_on_limit_exceeded(self, mock_redis):
        """Decorator should raise HTTPException when limit exceeded."""
        from genreport.core.security.tenant_rate_limiter import rate_limit

        mock_redis.get.return_value = b"10"
        mock_redis.incr.return_value = 11
        mock_redis.ttl.return_value = 3600  # Return integer for TTL

        @rate_limit(calls=10, period="hour", operation="test_op")
        def test_function(tenant_id: str):
            return "success"

        tenant_id = str(uuid4())

        with pytest.raises(HTTPException) as exc_info:
            test_function(tenant_id)

        assert exc_info.value.status_code == 429


class TestTenantRateLimiterEdgeCases:
    """Test edge cases and error handling."""

    @patch("genreport.core.security.tenant_rate_limiter.redis_client")
    def test_redis_connection_error(self, mock_redis):
        """Handle Redis connection errors gracefully."""
        from redis.exceptions import ConnectionError

        mock_redis.get.side_effect = ConnectionError("Cannot connect")

        limiter = TenantRateLimiter(fail_open=True)
        tenant_id = uuid4()

        # Should allow request when Redis fails and fail_open=True
        result = limiter.check_limit(tenant_id, "test_operation")

        assert result is True

    @patch("genreport.core.security.tenant_rate_limiter.redis_client")
    def test_redis_error_with_fail_closed(self, mock_redis):
        """Deny requests when Redis fails and fail_open=False."""
        from redis.exceptions import ConnectionError

        mock_redis.get.side_effect = ConnectionError("Cannot connect")

        limiter = TenantRateLimiter(fail_open=False)
        tenant_id = uuid4()

        with pytest.raises(RateLimitExceeded, match="Service unavailable"):
            limiter.check_limit(tenant_id, "test_operation")

    @patch("genreport.core.security.tenant_rate_limiter.redis_client")
    def test_negative_ttl_resets_counter(self, mock_redis):
        """Negative TTL (key expired) should reset counter."""
        mock_redis.get.return_value = None  # Key expired
        mock_redis.ttl.return_value = -2  # Key doesn't exist
        mock_redis.incr.return_value = 1

        limiter = TenantRateLimiter()
        tenant_id = uuid4()

        result = limiter.check_limit(tenant_id, "test_operation")

        assert result is True
        # Should set new expiration
        mock_redis.expire.assert_called_once()


class TestTenantRateLimiterConfiguration:
    """Test configuration options."""

    def test_custom_default_config(self):
        """Use custom default configuration."""
        custom_config = RateLimitConfig(calls=50, period="minute")
        limiter = TenantRateLimiter(default_config=custom_config)

        assert limiter.default_config.calls == 50
        assert limiter.default_config.period == "minute"

    def test_operation_specific_configs(self):
        """Use operation-specific configurations."""
        configs = {
            "report_generation": RateLimitConfig(calls=100, period="hour"),
            "kb_search": RateLimitConfig(calls=1000, period="hour"),
        }

        limiter = TenantRateLimiter(configs=configs)

        assert limiter.configs["report_generation"].calls == 100
        assert limiter.configs["kb_search"].calls == 1000

    def test_fallback_to_default_config(self):
        """Unknown operation falls back to default config."""
        limiter = TenantRateLimiter(
            default_config=RateLimitConfig(calls=100, period="hour")
        )

        config = limiter._get_config("unknown_operation")

        assert config.calls == 100
        assert config.period == "hour"


class TestTenantRateLimiterClearQuota:
    """Test clearing quota (admin operations)."""

    @patch("genreport.core.security.tenant_rate_limiter.redis_client")
    def test_clear_quota_for_tenant(self, mock_redis):
        """Clear rate limit quota for specific tenant."""
        limiter = TenantRateLimiter()
        tenant_id = uuid4()

        limiter.clear_quota(tenant_id, "test_operation")

        # Should delete the Redis key
        mock_redis.delete.assert_called_once()

    @patch("genreport.core.security.tenant_rate_limiter.redis_client")
    def test_clear_all_quotas_for_tenant(self, mock_redis):
        """Clear all rate limit quotas for tenant."""
        mock_redis.keys.return_value = [
            b"rate_limit:tenant:test_op1",
            b"rate_limit:tenant:test_op2",
        ]

        limiter = TenantRateLimiter()
        tenant_id = uuid4()

        limiter.clear_all_quotas(tenant_id)

        # Should find and delete all keys for tenant
        mock_redis.keys.assert_called_once()
        assert mock_redis.delete.call_count >= 1
