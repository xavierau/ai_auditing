"""Authentication router for login, registration, and token management."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from genreport.core.database.base import get_db
from genreport.core.database.models import Tenant, User
from genreport.core.security.audit_logger import AuditLogger
from genreport.core.security.jwt_service import (
    authenticate_user,
    blacklist_token,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
)
from genreport.api.dependencies import get_request_ip
from genreport.core.utils.config import settings

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def apply_rate_limit(limit: str):
    """Conditionally apply rate limiting based on environment.

    In test environment, rate limiting is disabled.
    In development/production, rate limiting is enforced.
    """
    def decorator(func):
        if settings.is_test:
            # Skip rate limiting in test environment
            return func
        return limiter.limit(limit)(func)
    return decorator


# Pydantic Models for Request/Response
class LoginRequest(BaseModel):
    """Login request model."""

    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """User registration request model."""

    email: EmailStr
    password: str
    full_name: str
    company_name: str
    jurisdiction: str = "HK"


class UserData(BaseModel):
    """User data model for responses."""

    id: int
    email: str
    name: str
    tenant_id: str
    tenant_name: str
    jurisdiction: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token response model."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserData  # Add user data to response


class RefreshRequest(BaseModel):
    """Token refresh request model."""

    refresh_token: str


class LogoutRequest(BaseModel):
    """Logout request model."""

    access_token: str


@router.post("/login", response_model=TokenResponse)
@apply_rate_limit("5/minute")  # Prevent brute force attacks
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),  # OAuth2 form data
    db: Session = Depends(get_db),
):
    """Authenticate user and return JWT tokens.

    Supports OAuth2 password flow (form data with username/password).
    Rate limited to 5 attempts per minute to prevent brute force attacks.

    Args:
        request: FastAPI request
        form_data: OAuth2 form data (username field contains email)
        db: Database session

    Returns:
        Access and refresh tokens with user data

    Raises:
        HTTPException: If authentication fails
    """
    ip_address = get_request_ip(request)

    # OAuth2 uses 'username' field, but we use email
    email = form_data.username
    password = form_data.password

    # Authenticate user
    user = authenticate_user(db, email, password)

    if not user:
        # Log failed attempt
        AuditLogger.log_authentication(
            db=db, user_id=None, tenant_id=None, success=False, ip_address=ip_address
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Log successful login
    AuditLogger.log_authentication(
        db=db,
        user_id=user.id,
        tenant_id=user.tenant_id,
        success=True,
        ip_address=ip_address,
    )

    # Generate tokens
    access_token = create_access_token(user.id, user.tenant_id, user.role)
    refresh_token_str = create_refresh_token(user.id, user.tenant_id)

    # Get token expiration from settings
    from genreport.core.utils.config import settings

    # Get tenant info
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()

    # Prepare user data for response
    user_data = UserData(
        id=user.id,
        email=user.email,
        name=user.full_name,
        tenant_id=str(user.tenant_id),
        tenant_name=tenant.company_name if tenant else "Unknown",
        jurisdiction=tenant.jurisdiction if tenant else "HK",
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        expires_in=settings.access_token_expire_minutes * 60,  # Convert to seconds
        user=user_data,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@apply_rate_limit("3/hour")  # Prevent abuse
async def register(
    request: Request,
    registration: RegisterRequest,
    db: Session = Depends(get_db),
):
    """Register a new user and tenant.

    Creates both a tenant and the first user (admin) for that tenant.
    Rate limited to prevent abuse.

    Args:
        request: FastAPI request
        registration: Registration details
        db: Database session

    Returns:
        Access and refresh tokens for new user

    Raises:
        HTTPException: If email already exists or validation fails
    """
    ip_address = get_request_ip(request)

    # Check if email already exists
    existing_user = db.query(User).filter(User.email == registration.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Validate jurisdiction
    from genreport.core.utils.market_config import validate_jurisdiction

    if not validate_jurisdiction(registration.jurisdiction):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid jurisdiction: {registration.jurisdiction}",
        )

    try:
        # Create tenant
        tenant = Tenant(
            company_name=registration.company_name,
            data_residency_region=registration.jurisdiction,
            jurisdiction=registration.jurisdiction,
            is_active=True,
        )
        db.add(tenant)
        db.flush()  # Get tenant.id

        # Create user (first user is admin)
        user = User(
            tenant_id=tenant.id,
            email=registration.email,
            password_hash=hash_password(registration.password),
            full_name=registration.full_name,
            role="admin",  # First user is admin
            is_active=True,
        )
        db.add(user)
        db.commit()

        # Log registration
        AuditLogger.log_event(
            db=db,
            event_type=AuditLogger.AUTHENTICATION,
            action="REGISTER",
            user_id=user.id,
            tenant_id=tenant.id,
            ip_address=ip_address,
            details={
                "company_name": registration.company_name,
                "jurisdiction": registration.jurisdiction,
            },
            status=AuditLogger.SUCCESS,
        )

        # Generate tokens
        access_token = create_access_token(user.id, user.tenant_id, user.role)
        refresh_token = create_refresh_token(user.id, user.tenant_id)

        from genreport.core.utils.config import settings

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}",
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_request: RefreshRequest,
    db: Session = Depends(get_db),
):
    """Refresh access token using refresh token.

    Args:
        refresh_request: Refresh token
        db: Database session

    Returns:
        New access and refresh tokens

    Raises:
        HTTPException: If refresh token is invalid
    """
    # Decode refresh token
    payload = decode_refresh_token(refresh_request.refresh_token)

    # Get user
    user_id = int(payload.get("sub"))
    user = db.query(User).filter(User.id == user_id).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Generate new tokens
    access_token = create_access_token(user.id, user.tenant_id, user.role)
    new_refresh_token = create_refresh_token(user.id, user.tenant_id)

    # Log token refresh
    AuditLogger.log_event(
        db=db,
        event_type=AuditLogger.AUTHENTICATION,
        action=AuditLogger.TOKEN_REFRESH,
        user_id=user.id,
        tenant_id=user.tenant_id,
        status=AuditLogger.SUCCESS,
    )

    from genreport.core.utils.config import settings

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout")
async def logout(
    logout_request: LogoutRequest,
    db: Session = Depends(get_db),
):
    """Logout user by blacklisting their access token.

    Args:
        logout_request: Access token to blacklist
        db: Database session

    Returns:
        Success message
    """
    try:
        # Decode token to get tenant_id
        from genreport.core.security.jwt_service import decode_access_token

        payload = decode_access_token(logout_request.access_token)
        tenant_id = UUID(payload.get("tenant_id"))
        user_id = int(payload.get("sub"))

        # Blacklist token
        blacklist_token(db, logout_request.access_token, tenant_id)

        # Log logout
        AuditLogger.log_event(
            db=db,
            event_type=AuditLogger.AUTHENTICATION,
            action=AuditLogger.LOGOUT,
            user_id=user_id,
            tenant_id=tenant_id,
            status=AuditLogger.SUCCESS,
        )

        return {"message": "Successfully logged out"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Logout failed: {str(e)}",
        )


@router.get("/csrf-token")
async def get_csrf_token():
    """Get CSRF token for the frontend.

    Returns a simple CSRF token that the frontend can use.
    In production, this should be more sophisticated with token validation.

    Returns:
        CSRF token
    """
    import secrets

    # Generate a random token
    csrf_token = secrets.token_hex(32)

    return {"csrf_token": csrf_token}


# Alternative route for frontend compatibility (matches /api/v1/csrf-token)
# This is registered at the main app level, not in the auth router
