"""Common dependencies for FastAPI endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from genreport.core.database.base import get_db
from genreport.core.database.models import User
from genreport.core.security.jwt_service import get_current_user
from genreport.core.security.tenant_context import get_current_tenant


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user.

    Dependency that ensures the user is active.

    Args:
        current_user: Current authenticated user

    Returns:
        Active user object

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_request_ip(request: Request) -> str:
    """Extract IP address from request.

    Handles X-Forwarded-For header for proxied requests.

    Args:
        request: FastAPI request object

    Returns:
        Client IP address (defaults to 127.0.0.1 for test clients)
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Get first IP in chain
        return forwarded.split(",")[0].strip()

    if request.client:
        host = request.client.host
        # Handle test client which returns "testclient" instead of valid IP
        if host == "testclient":
            return "127.0.0.1"
        return host

    return "127.0.0.1"


def get_user_agent(request: Request) -> Optional[str]:
    """Extract User-Agent header from request.

    Args:
        request: FastAPI request object

    Returns:
        User-Agent string or None
    """
    return request.headers.get("User-Agent")


class CommonDeps:
    """Common dependencies bundled together.

    Usage:
        @router.get("/endpoint")
        async def endpoint(deps: CommonDeps = Depends()):
            # Access deps.db, deps.user, deps.tenant_id, etc.
    """

    def __init__(
        self,
        request: Request,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_active_user),
        tenant_id: UUID = Depends(get_current_tenant),
    ):
        """Initialize common dependencies.

        Args:
            request: FastAPI request
            db: Database session
            user: Current authenticated user
            tenant_id: Current tenant ID
        """
        self.request = request
        self.db = db
        self.user = user
        self.tenant_id = tenant_id
        self.ip_address = get_request_ip(request)
        self.user_agent = get_user_agent(request)
