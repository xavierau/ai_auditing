"""FastAPI application entry point with security middleware."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from genreport.core.security.tenant_context import TenantMiddleware
from genreport.core.utils.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events.

    Handles startup and shutdown events for the application.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} in {settings.app_env} mode")
    logger.info(f"Debug mode: {settings.debug}")

    # TODO: Initialize services
    # - Database connection pool verification
    # - Redis connection verification
    # - LLM client initialization
    # - Langfuse initialization

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.app_name}")

    # TODO: Cleanup
    # - Close database connections
    # - Close Redis connections
    # - Flush logs


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="AI-powered audit report generation system with multi-market support",
    version=settings.api_version,
    docs_url="/docs" if settings.debug else None,  # Disable docs in production
    redoc_url="/redoc" if settings.debug else None,
    openapi_url=f"/api/{settings.api_version}/openapi.json",
    lifespan=lifespan,
)

# Trusted Host Middleware (Security Layer 1)
# Prevents Host header attacks
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.trusted_hosts_list,
    )

# CORS Middleware (Security Layer 2)
# Configure Cross-Origin Resource Sharing
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-Page-Count"],
)

# Tenant Isolation Middleware (Security Layer 3)
# CRITICAL: Extracts tenant from JWT and enforces isolation
app.add_middleware(TenantMiddleware)

# Rate Limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Security Headers Middleware (Security Layer 4)
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses.

    SECURITY: These headers protect against common web vulnerabilities.
    """
    response = await call_next(request)

    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"

    # XSS Protection (for older browsers)
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Force HTTPS
    if not settings.debug:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

    # Content Security Policy
    if not settings.debug:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )

    # Referrer Policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Permissions Policy (formerly Feature-Policy)
    response.headers["Permissions-Policy"] = (
        "geolocation=(), "
        "microphone=(), "
        "camera=(), "
        "payment=(), "
        "usb=(), "
        "magnetometer=(), "
        "gyroscope=()"
    )

    return response


# Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed error messages."""
    logger.warning(f"Validation error: {exc.errors()}")

    # Convert bytes to strings in errors for JSON serialization
    def convert_bytes(obj):
        """Recursively convert bytes to strings in nested structures."""
        if isinstance(obj, bytes):
            try:
                return obj.decode('utf-8')
            except UnicodeDecodeError:
                return str(obj)
        elif isinstance(obj, dict):
            return {k: convert_bytes(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_bytes(item) for item in obj]
        return obj

    errors = convert_bytes(exc.errors())
    body = convert_bytes(exc.body)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": errors,
            "body": body,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)

    # Don't expose internal errors in production
    if settings.is_production:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": str(exc),
                "type": type(exc).__name__,
            },
        )


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.api_version,
        "environment": settings.app_env,
        "docs": "/docs" if settings.debug else "disabled",
    }


# Health check endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for load balancers.

    Returns 200 if the application is running.
    """
    return {"status": "healthy"}


@app.get("/readiness", tags=["Health"])
async def readiness_check():
    """Readiness check endpoint.

    Returns 200 if the application is ready to serve traffic.
    Checks database, Redis, and other critical dependencies.
    """
    # TODO: Add actual readiness checks
    # - Database connectivity
    # - Redis connectivity
    # - External API availability

    return {
        "status": "ready",
        "checks": {
            "database": "ok",  # TODO: Implement actual check
            "redis": "ok",  # TODO: Implement actual check
        },
    }


# Include routers
from genreport.api.routers import auth, files, projects, parsing, kb, reports

app.include_router(
    auth.router, prefix=f"/api/{settings.api_version}/auth", tags=["Authentication"]
)
app.include_router(
    projects.router, prefix=f"/api/{settings.api_version}/projects", tags=["Projects"]
)
app.include_router(
    files.router, prefix=f"/api/{settings.api_version}/files", tags=["Files"]
)
app.include_router(
    parsing.router, prefix=f"/api/{settings.api_version}/parsing", tags=["Parsing"]
)
app.include_router(
    kb.router, prefix=f"/api/{settings.api_version}/kb", tags=["Knowledge Base"]
)
app.include_router(
    reports.router, tags=["Reports"]  # reports.router already has prefix
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "genreport.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
