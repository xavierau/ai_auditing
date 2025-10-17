"""JWT token generation, validation, and authentication service."""

from datetime import datetime, timedelta
from typing import Dict, Optional
from uuid import UUID, uuid4

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from genreport.core.database.base import get_db
from genreport.core.database.models import BlacklistedToken, User
from genreport.core.utils.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token security
security = HTTPBearer()


class AuthenticationError(Exception):
    """Custom exception for authentication failures."""

    pass


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int, tenant_id: UUID, role: str = "auditor") -> str:
    """Create a JWT access token.

    Args:
        user_id: User ID
        tenant_id: Tenant ID for multi-tenant isolation
        role: User role for RBAC

    Returns:
        Encoded JWT token
    """
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    expire = datetime.utcnow() + expires_delta

    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role,
        "type": "access",
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": str(uuid4()),  # Unique token identifier for blacklisting
    }

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: int, tenant_id: UUID) -> str:
    """Create a JWT refresh token.

    Args:
        user_id: User ID
        tenant_id: Tenant ID

    Returns:
        Encoded JWT refresh token
    """
    expires_delta = timedelta(days=settings.refresh_token_expire_days)
    expire = datetime.utcnow() + expires_delta

    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "type": "refresh",
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": str(uuid4()),  # Unique token identifier
    }

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Dict:
    """Decode and validate an access token.

    Args:
        token: JWT token to decode

    Returns:
        Token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )

        # Verify token type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        return payload

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def decode_refresh_token(token: str) -> Dict:
    """Decode and validate a refresh token.

    Args:
        token: JWT refresh token

    Returns:
        Token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )

        # Verify token type
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        return payload

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}",
        )


def is_token_blacklisted(db: Session, token: str) -> bool:
    """Check if a token has been blacklisted.

    Args:
        db: Database session
        token: JWT token to check

    Returns:
        True if token is blacklisted, False otherwise
    """
    try:
        # Extract JTI (JWT ID) from token
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        jti = payload.get("jti")

        if not jti:
            # If no JTI, cannot blacklist (older tokens)
            return False

        # Check database
        blacklisted = (
            db.query(BlacklistedToken).filter(BlacklistedToken.token_jti == jti).first()
        )

        return blacklisted is not None

    except JWTError:
        # Invalid token is effectively blacklisted
        return True


def blacklist_token(db: Session, token: str, tenant_id: UUID) -> None:
    """Blacklist a token (for logout).

    Args:
        db: Database session
        token: JWT token to blacklist
        tenant_id: Tenant ID
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        jti = payload.get("jti")

        if jti:
            # Add to blacklist
            blacklisted = BlacklistedToken(
                tenant_id=tenant_id,
                token_jti=jti,
                expires_at=datetime.fromtimestamp(payload["exp"]),
            )
            db.add(blacklisted)
            db.commit()

    except JWTError:
        # Invalid token, ignore
        pass


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user with email and password.

    Args:
        db: Database session
        email: User email
        password: Plain text password

    Returns:
        User object if authentication succeeds, None otherwise
    """
    user = db.query(User).filter(User.email == email).first()

    if not user:
        return None

    if not user.is_active:
        return None

    if not verify_password(password, user.password_hash):
        return None

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token.

    This is a FastAPI dependency that validates the JWT token,
    checks if it's blacklisted, and returns the user object.

    Args:
        credentials: HTTP Bearer token from request
        db: Database session

    Returns:
        Authenticated user object

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials

    # Check if token is blacklisted
    if is_token_blacklisted(db, token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )

    # Decode token
    payload = decode_access_token(token)

    # Get user from database
    user_id = int(payload.get("sub"))
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        )

    return user


class RoleChecker:
    """Dependency for role-based access control (RBAC).

    Usage:
        @router.get("/admin")
        async def admin_endpoint(user: User = Depends(RoleChecker(["admin"]))):
            ...
    """

    def __init__(self, allowed_roles: list[str]):
        """Initialize role checker.

        Args:
            allowed_roles: List of roles that can access the endpoint
        """
        self.allowed_roles = allowed_roles

    async def __call__(self, user: User = Depends(get_current_user)) -> User:
        """Check if user has required role.

        Args:
            user: Current authenticated user

        Returns:
            User object if authorized

        Raises:
            HTTPException: If user doesn't have required role
        """
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(self.allowed_roles)}",
            )
        return user


# Convenience dependencies for common roles
require_admin = RoleChecker(["admin"])
require_auditor = RoleChecker(["admin", "auditor"])
require_viewer = RoleChecker(["admin", "auditor", "viewer"])
