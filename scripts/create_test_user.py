"""
Create a test user for authentication testing.

Usage:
    python scripts/create_test_user.py
"""

from genreport.core.database.base import SessionLocal
from genreport.core.database.models import Tenant, User
from genreport.core.security.jwt_service import hash_password


def create_test_user():
    """Create a test user and tenant for development/testing."""
    db = SessionLocal()

    try:
        # Check if test user already exists
        existing_user = db.query(User).filter(User.email == "test@genreport.com").first()
        if existing_user:
            print("✓ Test user already exists")
            print(f"  Email: {existing_user.email}")
            print(f"  Tenant ID: {existing_user.tenant_id}")
            return

        # Check if test tenant exists
        existing_tenant = db.query(Tenant).filter(Tenant.company_name == "Test Audit Firm").first()

        if existing_tenant:
            tenant = existing_tenant
            print("✓ Test tenant already exists")
        else:
            # Create test tenant
            tenant = Tenant(
                company_name="Test Audit Firm",
                data_residency_region="HK",
                jurisdiction="HK",
                is_active=True,
            )
            db.add(tenant)
            db.flush()
            print("✓ Created test tenant")

        # Create test user
        user = User(
            tenant_id=tenant.id,
            email="test@genreport.com",
            password_hash=hash_password("password123"),  # Simple test password
            full_name="Test User",
            role="admin",
            is_active=True,
        )
        db.add(user)
        db.commit()

        print("\n✅ Test user created successfully!")
        print("\nLogin Credentials:")
        print("  Email: test@genreport.com")
        print("  Password: password123")
        print(f"\nTenant: {tenant.company_name}")
        print(f"Jurisdiction: {tenant.jurisdiction}")
        print(f"User Role: {user.role}")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error creating test user: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_test_user()
