"""Tenant context management for multi-tenant isolation."""

from contextvars import ContextVar
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

# Context variable to store current tenant ID throughout request lifecycle
current_tenant: ContextVar[Optional[UUID]] = ContextVar("current_tenant", default=None)


class TenantMiddleware(BaseHTTPMiddleware):
    """Middleware to extract and validate tenant context from JWT.

    SECURITY: This middleware is critical for multi-tenant isolation.
    It extracts the tenant_id from the JWT token and stores it in a
    ContextVar that persists throughout the request lifecycle.
    """

    # Public endpoints that don't require tenant context
    PUBLIC_PATHS = {
        "/",
        "/health",
        "/readiness",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
        "/api/v1/auth/logout",
    }

    async def dispatch(self, request: Request, call_next):
        """Extract tenant from JWT and set context."""
        # Skip tenant validation for public endpoints
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)

        try:
            # Extract tenant from JWT
            tenant_id = await self._extract_tenant_from_jwt(request)

            # If no tenant_id found, let the endpoint dependencies handle authentication
            # The middleware only enforces tenant context when a valid JWT is present
            if tenant_id:
                # Set tenant context for the request
                token = current_tenant.set(tenant_id)

                try:
                    # Process request with tenant context set
                    response = await call_next(request)
                    return response
                finally:
                    # Clean up context after request
                    current_tenant.reset(token)
            else:
                # No tenant context available - let request proceed
                # Endpoint dependencies (get_current_user) will handle authentication
                response = await call_next(request)
                return response

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Tenant context error: {str(e)}"
            )

    async def _extract_tenant_from_jwt(self, request: Request) -> Optional[UUID]:
        """Extract tenant_id from JWT token.

        This is a placeholder that will be integrated with the JWT auth service.
        The JWT payload should contain tenant_id after successful authentication.
        """
        # Get authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        # Extract token
        token = auth_header.split(" ")[1]

        # TODO: Decode JWT and extract tenant_id
        # This will be implemented in genreport.core.security.jwt_service
        # For now, this is a placeholder
        try:
            from genreport.core.security.jwt_service import decode_access_token

            payload = decode_access_token(token)
            tenant_id_str = payload.get("tenant_id")
            if tenant_id_str:
                return UUID(tenant_id_str)
        except ImportError:
            # JWT service not yet implemented
            pass
        except Exception:
            # Invalid token or tenant_id
            pass

        return None


def get_current_tenant() -> UUID:
    """Get current tenant ID from context.

    SECURITY: This function is used throughout the application to ensure
    all database queries and operations are scoped to the current tenant.

    Raises:
        HTTPException: If no tenant context is set (should never happen
                      after middleware, but provides defense in depth)

    Returns:
        UUID: Current tenant ID
    """
    tenant_id = current_tenant.get()
    if not tenant_id:
        raise HTTPException(
            status_code=401, detail="No tenant context available. Authentication required."
        )
    return tenant_id


def set_tenant_context(tenant_id: UUID) -> None:
    """Manually set tenant context.

    WARNING: This should only be used in background tasks or testing.
    Normal request flow uses TenantMiddleware to set context automatically.

    Args:
        tenant_id: Tenant ID to set in context
    """
    current_tenant.set(tenant_id)


def clear_tenant_context() -> None:
    """Clear tenant context.

    WARNING: This should only be used in background tasks or testing.
    """
    current_tenant.set(None)


# Alias for backward compatibility
set_current_tenant = set_tenant_context
