"""Initial schema with all tables and PGVector extension

Revision ID: 20251017_0001
Revises:
Create Date: 2025-10-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '20251017_0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables for multi-tenant audit system."""

    # Enable PGVector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Create tenants table (root entity for multi-tenancy)
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('company_name', sa.String(255), nullable=False),
        sa.Column('data_residency_region', sa.String(10), nullable=False),
        sa.Column('jurisdiction', sa.String(10), nullable=False),
        sa.Column('subscription_tier', sa.String(50), nullable=False, server_default='basic'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('settings', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_tenants_company_name', 'tenants', ['company_name'])
    op.create_index('ix_tenants_jurisdiction', 'tenants', ['jurisdiction'])

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='viewer'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_users_tenant_id', 'users', ['tenant_id'])
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_role', 'users', ['role'])

    # Create blacklisted_tokens table
    op.create_table(
        'blacklisted_tokens',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token', sa.Text, nullable=False),
        sa.Column('blacklisted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_blacklisted_tokens_token', 'blacklisted_tokens', ['token'])
    op.create_index('ix_blacklisted_tokens_tenant_id', 'blacklisted_tokens', ['tenant_id'])
    op.create_index('ix_blacklisted_tokens_expires_at', 'blacklisted_tokens', ['expires_at'])

    # Create audit_logs table (immutable security audit trail)
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', sa.Integer, nullable=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', sa.Integer, nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('details', postgresql.JSONB, nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_audit_logs_tenant_id', 'audit_logs', ['tenant_id'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_event_type', 'audit_logs', ['event_type'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    op.create_index('ix_audit_logs_resource', 'audit_logs', ['resource_type', 'resource_id'])

    # Create clients table
    op.create_table(
        'clients',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_name', sa.String(255), nullable=False),
        sa.Column('registration_number', sa.String(100), nullable=True),
        sa.Column('address', sa.Text, nullable=True),
        sa.Column('industry', sa.String(100), nullable=True),
        sa.Column('contact_person', sa.String(255), nullable=True),
        sa.Column('contact_email', sa.String(255), nullable=True),
        sa.Column('contact_phone', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_clients_tenant_id', 'clients', ['tenant_id'])
    op.create_index('ix_clients_company_name', 'clients', ['company_name'])

    # Create accounting_programs table
    op.create_table(
        'accounting_programs',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('jurisdiction', sa.String(10), nullable=False),
        sa.Column('vendor', sa.String(100), nullable=True),
        sa.Column('is_cloud_based', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('data_export_formats', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_accounting_programs_jurisdiction', 'accounting_programs', ['jurisdiction'])
    op.create_index('ix_accounting_programs_name', 'accounting_programs', ['name'])

    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', sa.Integer, nullable=False),
        sa.Column('user_id', sa.Integer, nullable=False),
        sa.Column('jurisdiction', sa.String(10), nullable=False, server_default='HK'),
        sa.Column('accounting_standard', sa.String(50), nullable=False, server_default='HKFRS'),
        sa.Column('financial_year_end', sa.Date, nullable=False),
        sa.Column('project_name', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('relationship_map', postgresql.JSONB, nullable=True),
        sa.Column('directors_names', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('accounting_program_id', sa.Integer, nullable=True),
        sa.Column('trial_balance_file', sa.String(500), nullable=True),
        sa.Column('supporting_documents', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['accounting_program_id'], ['accounting_programs.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_projects_tenant_id', 'projects', ['tenant_id'])
    op.create_index('ix_projects_client_id', 'projects', ['client_id'])
    op.create_index('ix_projects_user_id', 'projects', ['user_id'])
    op.create_index('ix_projects_status', 'projects', ['status'])
    op.create_index('ix_projects_jurisdiction', 'projects', ['jurisdiction'])

    # Create reports table
    op.create_table(
        'reports',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', sa.Integer, nullable=False),
        sa.Column('user_id', sa.Integer, nullable=False),
        sa.Column('report_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_reports_tenant_id', 'reports', ['tenant_id'])
    op.create_index('ix_reports_project_id', 'reports', ['project_id'])
    op.create_index('ix_reports_status', 'reports', ['status'])
    op.create_index('ix_reports_report_type', 'reports', ['report_type'])

    # Create knowledge_bases table
    op.create_table(
        'knowledge_bases',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('jurisdiction', sa.String(10), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('subcategory', sa.String(100), nullable=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('source', sa.String(255), nullable=True),
        sa.Column('effective_date', sa.Date, nullable=True),
        sa.Column('last_updated', sa.Date, nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_knowledge_bases_jurisdiction', 'knowledge_bases', ['jurisdiction'])
    op.create_index('ix_knowledge_bases_category', 'knowledge_bases', ['category'])

    # Create kb_chunks table (for RAG with vector embeddings)
    op.create_table(
        'kb_chunks',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('knowledge_base_id', sa.Integer, nullable=False),
        sa.Column('chunk_text', sa.Text, nullable=False),
        sa.Column('chunk_index', sa.Integer, nullable=False),
        # PGVector column - 1536 dimensions for OpenAI ada-002
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['knowledge_base_id'], ['knowledge_bases.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_kb_chunks_knowledge_base_id', 'kb_chunks', ['knowledge_base_id'])
    # Create vector index for similarity search (cosine distance)
    op.execute(
        'CREATE INDEX ix_kb_chunks_embedding ON kb_chunks '
        'USING ivfflat (embedding vector_cosine_ops) '
        'WITH (lists = 100)'
    )


def downgrade() -> None:
    """Drop all tables in reverse order."""

    # Drop tables in reverse order of creation
    op.drop_table('kb_chunks')
    op.drop_table('knowledge_bases')
    op.drop_table('reports')
    op.drop_table('projects')
    op.drop_table('accounting_programs')
    op.drop_table('clients')
    op.drop_table('audit_logs')
    op.drop_table('blacklisted_tokens')
    op.drop_table('users')
    op.drop_table('tenants')

    # Drop PGVector extension
    op.execute('DROP EXTENSION IF EXISTS vector')
