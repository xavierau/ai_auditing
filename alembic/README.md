# Database Migrations with Alembic

This directory contains database migrations for the GenReport multi-tenant audit system.

## Prerequisites

- PostgreSQL 14+ installed and running
- PGVector extension available (for vector similarity search)
- Python 3.13+ with dependencies installed

## Initial Setup

1. **Create PostgreSQL database**:
```bash
createdb genreport_dev
```

2. **Enable PGVector extension** (if not done automatically):
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

3. **Configure environment variables** (.env file):
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/genreport_dev
```

## Running Migrations

### Apply all pending migrations
```bash
alembic upgrade head
```

### Rollback last migration
```bash
alembic downgrade -1
```

### Rollback to specific revision
```bash
alembic downgrade 20251017_0001
```

### Check current revision
```bash
alembic current
```

### View migration history
```bash
alembic history --verbose
```

## Creating New Migrations

### Auto-generate migration from model changes
```bash
alembic revision --autogenerate -m "Description of changes"
```

**IMPORTANT**: Always review auto-generated migrations before applying them. Alembic may not detect all changes correctly.

### Create empty migration
```bash
alembic revision -m "Description of changes"
```

## Migration Files

### 20251017_0001-initial_schema.py
Creates the complete database schema:
- Multi-tenant isolation (tenants table)
- Authentication (users, blacklisted_tokens)
- Audit logging (audit_logs)
- Business entities (clients, projects, reports)
- Knowledge base with vector embeddings (knowledge_bases, kb_chunks)
- Enables PGVector extension

### 20251017_0002-seed_accounting_programs.py
Seeds the accounting_programs table with common software for Hong Kong market:
- Xero, QuickBooks, MYOB, Sage 50, SAP Business One
- Oracle NetSuite, Zoho Books, FreshBooks, Wave
- KashFlow, Flexsystem, ACCPAC, Microsoft Dynamics 365

## Best Practices

1. **Test migrations locally** before applying to production
2. **Backup database** before applying migrations in production
3. **Review auto-generated migrations** for correctness
4. **Use transactions** - migrations are wrapped in transactions by default
5. **Test rollback** - ensure downgrade() works correctly
6. **Version control** - commit migration files to git

## Common Issues

### PGVector Extension Not Found
If you get an error about the vector extension:
```bash
# Install pgvector from source or package manager
# Ubuntu/Debian:
sudo apt install postgresql-14-pgvector

# macOS (Homebrew):
brew install pgvector
```

### Migration Already Applied
If you see "Target database is not up to date":
```bash
# Check current version
alembic current

# View history
alembic history

# Stamp database to specific version (DANGEROUS - use with caution)
alembic stamp head
```

### Rollback Failed
If downgrade fails:
1. Check the downgrade() function in the migration file
2. Manually fix database state if needed
3. Stamp to correct version: `alembic stamp <revision>`

## Production Deployment

1. **Backup database**:
```bash
pg_dump genreport_prod > backup_$(date +%Y%m%d_%H%M%S).sql
```

2. **Apply migrations**:
```bash
# Set production database URL
export DATABASE_URL=postgresql://user:pass@prod-host:5432/genreport_prod

# Run migrations
alembic upgrade head
```

3. **Verify migration**:
```bash
alembic current
psql -d genreport_prod -c "SELECT COUNT(*) FROM tenants;"
```

4. **Rollback if needed**:
```bash
alembic downgrade -1
```

## Troubleshooting

### Check Database Connection
```bash
psql $DATABASE_URL -c "SELECT version();"
```

### View All Tables
```bash
psql $DATABASE_URL -c "\dt"
```

### Check PGVector Extension
```bash
psql $DATABASE_URL -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

### Reset Database (Development Only)
```bash
# WARNING: This will delete all data
alembic downgrade base
alembic upgrade head
```
