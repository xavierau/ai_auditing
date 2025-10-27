"""
Check database connection and list tables.
"""

import os
from sqlalchemy import create_engine, inspect, text

# Get database URL from environment
database_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/genreport")

print(f"Connecting to: {database_url}")

try:
    engine = create_engine(database_url)

    # Test connection
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.fetchone()[0]
        print(f"✓ Connected to PostgreSQL")
        print(f"  Version: {version[:50]}...")

        # Check for tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if tables:
            print(f"\n✓ Found {len(tables)} tables:")
            for table in sorted(tables):
                print(f"  - {table}")
        else:
            print("\n❌ No tables found in database")
            print("   Run: alembic upgrade head")

except Exception as e:
    print(f"\n❌ Database connection failed: {e}")
    print("\nPossible issues:")
    print("  1. PostgreSQL is not running")
    print("  2. Database 'genreport' does not exist")
    print("  3. Wrong credentials in DATABASE_URL")
    print("\nTo fix:")
    print("  1. Start PostgreSQL")
    print("  2. Create database: createdb genreport")
    print("  3. Run migrations: alembic upgrade head")
