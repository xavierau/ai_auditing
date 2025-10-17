#!/usr/bin/env python3
"""Database management CLI for GenReport.

Provides convenient commands for database operations including
migrations, seeding, and cleanup.

Usage:
    python scripts/db_manager.py migrate      # Run all pending migrations
    python scripts/db_manager.py rollback     # Rollback last migration
    python scripts/db_manager.py reset        # Reset database (dev only)
    python scripts/db_manager.py seed         # Seed test data (dev only)
    python scripts/db_manager.py status       # Show migration status
"""

import sys
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from genreport.core.utils.config import settings


def run_alembic(args: list[str]) -> int:
    """Run alembic command.

    Args:
        args: Alembic command arguments

    Returns:
        Exit code
    """
    cmd = ["alembic"] + args
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def migrate():
    """Apply all pending migrations."""
    print("Applying migrations...")
    return run_alembic(["upgrade", "head"])


def rollback():
    """Rollback last migration."""
    print("Rolling back last migration...")
    return run_alembic(["downgrade", "-1"])


def reset():
    """Reset database (development only)."""
    if settings.is_production:
        print("ERROR: Cannot reset database in production!")
        return 1

    print("WARNING: This will delete all data!")
    response = input("Are you sure? (yes/no): ")

    if response.lower() != "yes":
        print("Aborted.")
        return 0

    print("Resetting database...")
    # Rollback all migrations
    code = run_alembic(["downgrade", "base"])
    if code != 0:
        return code

    # Apply all migrations
    return run_alembic(["upgrade", "head"])


def seed():
    """Seed test data (development only)."""
    if settings.is_production:
        print("ERROR: Cannot seed test data in production!")
        return 1

    print("Seeding test data...")

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from uuid import uuid4
    from genreport.core.database.models import Tenant, User
    from genreport.core.security.jwt_service import hash_password

    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Check if test tenant already exists
        existing = db.query(Tenant).filter(
            Tenant.company_name == "Test Company"
        ).first()

        if existing:
            print("Test data already exists.")
            return 0

        # Create test tenant
        tenant = Tenant(
            id=uuid4(),
            company_name="Test Company",
            data_residency_region="HK",
            jurisdiction="HK",
            is_active=True,
        )
        db.add(tenant)
        db.flush()

        # Create test users
        admin = User(
            tenant_id=tenant.id,
            email="admin@test.com",
            password_hash=hash_password("admin123"),
            full_name="Admin User",
            role="admin",
            is_active=True,
        )
        auditor = User(
            tenant_id=tenant.id,
            email="auditor@test.com",
            password_hash=hash_password("auditor123"),
            full_name="Auditor User",
            role="auditor",
            is_active=True,
        )
        viewer = User(
            tenant_id=tenant.id,
            email="viewer@test.com",
            password_hash=hash_password("viewer123"),
            full_name="Viewer User",
            role="viewer",
            is_active=True,
        )

        db.add_all([admin, auditor, viewer])
        db.commit()

        print("\nTest data created successfully!")
        print(f"\nTenant ID: {tenant.id}")
        print("\nTest Users:")
        print("  Admin:   admin@test.com / admin123")
        print("  Auditor: auditor@test.com / auditor123")
        print("  Viewer:  viewer@test.com / viewer123")

        return 0

    except Exception as e:
        db.rollback()
        print(f"ERROR: Failed to seed data: {e}")
        return 1
    finally:
        db.close()


def status():
    """Show migration status."""
    print("Current migration status:")
    print()
    run_alembic(["current"])
    print()
    print("Migration history:")
    return run_alembic(["history"])


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    command = sys.argv[1]

    commands = {
        "migrate": migrate,
        "rollback": rollback,
        "reset": reset,
        "seed": seed,
        "status": status,
    }

    if command not in commands:
        print(f"ERROR: Unknown command: {command}")
        print(__doc__)
        return 1

    return commands[command]()


if __name__ == "__main__":
    sys.exit(main())
