"""Reset and initialize database with all tables from models.

This script is for development purposes to quickly bootstrap the database.
For production, use Alembic migrations.
"""

from sqlalchemy import text

from genreport.core.database.base import Base, engine
from genreport.core.database.models import *  # noqa: F403, F401


def reset_database():
    """Drop all tables and recreate from models."""
    print("Resetting database...")

    # Drop all tables
    with engine.connect() as conn:
        # Get all tables
        result = conn.execute(text("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
        """))
        tables = [row[0] for row in result]

        for table in tables:
            try:
                conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                print(f"✓ Dropped {table}")
            except Exception as e:
                print(f"✗ Error dropping {table}: {e}")

        conn.commit()

    # Create all tables from models
    print("\nCreating tables from models...")
    Base.metadata.create_all(bind=engine)
    print("✓ All tables created successfully")

    # Verify tables
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """))
        tables = [row[0] for row in result]
        print(f"\nCreated {len(tables)} tables:")
        for table in tables:
            print(f"  - {table}")


if __name__ == "__main__":
    reset_database()
