"""Pytest configuration and fixtures for testing."""

import os

# IMPORTANT: Set test environment BEFORE importing settings
# This disables rate limiting and enables other test-specific behavior
os.environ["APP_ENV"] = "test"

import pytest
import bcrypt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from uuid import uuid4

# Import settings module and clear cache to force reload with test environment
from genreport.core.utils.config import get_settings

# Clear the lru_cache to force settings reload with APP_ENV=test
get_settings.cache_clear()

# Now import the rest - settings will be reloaded with APP_ENV=test
from genreport.api.main import app
from genreport.core.database.base import Base, get_db
from genreport.core.database.models import Tenant, User
from genreport.core.security.jwt_service import create_access_token
from genreport.core.utils.config import settings


# Pre-hash test passwords at module level using bcrypt directly
# This avoids passlib/bcrypt compatibility issues in test fixtures
# passlib 1.7.4 is incompatible with bcrypt 4.x due to __about__ module removal
_TEST_PASSWORDS = {
    "testpassword123": bcrypt.hashpw(b"testpassword123", bcrypt.gensalt()).decode('utf-8'),
    "adminpassword123": bcrypt.hashpw(b"adminpassword123", bcrypt.gensalt()).decode('utf-8'),
    "secondpassword123": bcrypt.hashpw(b"secondpassword123", bcrypt.gensalt()).decode('utf-8'),
}

# Monkey-patch jwt_service functions to use bcrypt directly in tests
# This avoids passlib/bcrypt incompatibility
def _test_verify_password(plain_password: str, hashed_password: str) -> bool:
    """Test-specific password verification using bcrypt directly."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def _test_hash_password(password: str) -> str:
    """Test-specific password hashing using bcrypt directly."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Apply monkey-patches to jwt_service module
import genreport.core.security.jwt_service
genreport.core.security.jwt_service.verify_password = _test_verify_password
genreport.core.security.jwt_service.hash_password = _test_hash_password

# Also patch the auth router which imports these functions
# This must happen AFTER importing the main app (which imports the routers)
import genreport.api.routers.auth
genreport.api.routers.auth.hash_password = _test_hash_password


# Use PostgreSQL for testing (same as development/production)
# This allows testing of PostgreSQL-specific features (JSONB, INET, vector, etc.)
# You can override with TEST_DATABASE_URL environment variable for a separate test database
SQLALCHEMY_DATABASE_URL = os.getenv("TEST_DATABASE_URL", settings.database_url_str)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using
    echo=False,  # Set to True for SQL query logging during tests
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test."""
    # Create pgvector extension if not exists
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Create session
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Create a test client with database dependency override."""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_tenant(db):
    """Create a test tenant."""
    tenant = Tenant(
        id=uuid4(),
        company_name="Test Company",
        data_residency_region="HK",
        jurisdiction="HK",
        is_active=True,
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@pytest.fixture
def test_user(db, test_tenant):
    """Create a test user."""
    user = User(
        tenant_id=test_tenant.id,
        email="test@example.com",
        password_hash=_TEST_PASSWORDS["testpassword123"],
        full_name="Test User",
        role="auditor",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_admin_user(db, test_tenant):
    """Create a test admin user."""
    user = User(
        tenant_id=test_tenant.id,
        email="admin@example.com",
        password_hash=_TEST_PASSWORDS["adminpassword123"],
        full_name="Admin User",
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user):
    """Generate an authentication token for test user."""
    return create_access_token(test_user.id, test_user.tenant_id, test_user.role)


@pytest.fixture
def admin_auth_token(test_admin_user):
    """Generate an authentication token for test admin user."""
    return create_access_token(
        test_admin_user.id, test_admin_user.tenant_id, test_admin_user.role
    )


@pytest.fixture
def auth_headers(auth_token):
    """Generate authentication headers."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def admin_auth_headers(admin_auth_token):
    """Generate admin authentication headers."""
    return {"Authorization": f"Bearer {admin_auth_token}"}


@pytest.fixture
def second_tenant(db):
    """Create a second tenant for isolation testing."""
    tenant = Tenant(
        id=uuid4(),
        company_name="Second Company",
        data_residency_region="HK",
        jurisdiction="HK",
        is_active=True,
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@pytest.fixture
def second_tenant_user(db, second_tenant):
    """Create a user for the second tenant."""
    user = User(
        tenant_id=second_tenant.id,
        email="second@example.com",
        password_hash=_TEST_PASSWORDS["secondpassword123"],
        full_name="Second User",
        role="auditor",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def second_tenant_auth_token(second_tenant_user):
    """Generate an authentication token for second tenant user."""
    return create_access_token(
        second_tenant_user.id, second_tenant_user.tenant_id, second_tenant_user.role
    )


@pytest.fixture
def second_tenant_auth_headers(second_tenant_auth_token):
    """Generate authentication headers for second tenant."""
    return {"Authorization": f"Bearer {second_tenant_auth_token}"}


@pytest.fixture
def test_client_obj(db, test_tenant):
    """Create a test client for projects."""
    from genreport.core.database.models import Client

    client = Client(
        tenant_id=test_tenant.id,
        company_name="Test Client Ltd",
        contact_email="client@example.com",
        contact_phone="+852 1234 5678",
        address="123 Test Street, Hong Kong",
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@pytest.fixture
def test_project(db, test_tenant, test_client_obj):
    """Create a test project."""
    from genreport.core.database.models import Project
    from datetime import date

    project = Project(
        tenant_id=test_tenant.id,
        client_id=test_client_obj.id,
        project_name="Test Project 2024",
        jurisdiction="HK",
        accounting_standard="HKFRS",
        financial_year_end=date(2024, 12, 31),
        status="in_progress",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project
