"""Database models with multi-tenant support."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID as PGUUID
from sqlalchemy.orm import relationship

from genreport.core.database.base import Base


class Tenant(Base):
    """Tenant model for multi-tenant isolation."""

    __tablename__ = "tenants"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    company_name = Column(String(255), nullable=False)
    data_residency_region = Column(String(50), nullable=False)  # HK, SG, AU
    jurisdiction = Column(String(10), default="HK")
    subscription_tier = Column(String(50), default="standard")
    encryption_key_id = Column(String(255), nullable=True)  # Reference to KMS key
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="tenant", lazy="dynamic")
    projects = relationship("Project", back_populates="tenant", lazy="dynamic")
    clients = relationship("Client", back_populates="tenant", lazy="dynamic")

    __table_args__ = (Index("idx_tenants_region", "data_residency_region"),)


class User(Base):
    """User model with tenant association."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), default="auditor")  # admin, auditor, viewer
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    projects = relationship("Project", back_populates="user", lazy="dynamic")
    audit_logs = relationship("AuditLog", back_populates="user", lazy="dynamic")

    __table_args__ = (
        Index("idx_users_tenant_id", "tenant_id"),
        Index("idx_users_email", "email"),
    )


class BlacklistedToken(Base):
    """Blacklisted JWT tokens for logout/revocation."""

    __tablename__ = "blacklisted_tokens"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    token_jti = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_blacklisted_tokens_jti", "token_jti"),
        Index("idx_blacklisted_tokens_expires", "expires_at"),
    )


class AuditLog(Base):
    """Audit log for security events."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    event_type = Column(String(100), nullable=False)  # AUTHENTICATION, DATA_ACCESS, etc.
    action = Column(String(100), nullable=False)  # LOGIN, CREATE, READ, UPDATE, DELETE
    resource_type = Column(String(50), nullable=True)  # project, file, report, etc.
    resource_id = Column(Integer, nullable=True)
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    details = Column(JSONB, nullable=True)
    status = Column(String(50), nullable=True)  # SUCCESS, FAILURE
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_logs_tenant", "tenant_id"),
        Index("idx_audit_logs_user", "user_id"),
        Index("idx_audit_logs_event", "event_type"),
        Index("idx_audit_logs_created", "created_at"),
    )


class Client(Base):
    """Client company model."""

    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    company_name = Column(String(255), nullable=False)
    registration_number = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    industry = Column(String(100), nullable=True)
    contact_person = Column(String(255), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    client_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="clients")
    projects = relationship("Project", back_populates="client", lazy="dynamic")

    __table_args__ = (
        Index("idx_clients_tenant", "tenant_id"),
        Index("idx_clients_name", "company_name"),
    )


class AccountingProgram(Base):
    """Accounting software/program reference."""

    __tablename__ = "accounting_programs"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    version = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    projects = relationship("Project", back_populates="accounting_program", lazy="dynamic")


class Project(Base):
    """Project model with hybrid architecture support."""

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=True)
    accounting_program_id = Column(
        Integer, ForeignKey("accounting_programs.id"), nullable=True
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Hybrid Architecture fields
    jurisdiction = Column(String(10), default="HK")
    accounting_standard = Column(String(50), default="HKFRS")

    # Project details
    financial_year_end = Column(Date, nullable=False)
    directors_names = Column(ARRAY(Text), nullable=True)
    project_name = Column(String(255), nullable=True)
    status = Column(String(50), default="draft")  # draft, in_progress, completed
    working_papers_path = Column(Text, nullable=True)
    relationship_map = Column(JSONB, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="projects")
    client = relationship("Client", back_populates="projects")
    accounting_program = relationship("AccountingProgram", back_populates="projects")
    user = relationship("User", back_populates="projects")
    reports = relationship("Report", back_populates="project", lazy="dynamic")

    __table_args__ = (
        Index("idx_projects_tenant", "tenant_id"),
        Index("idx_projects_jurisdiction", "jurisdiction"),
        Index("idx_projects_client", "client_id"),
        Index("idx_projects_user", "user_id"),
        Index("idx_projects_status", "status"),
    )


class Report(Base):
    """Generated report model."""

    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    report_type = Column(String(50), nullable=True)
    content = Column(JSONB, nullable=True)
    generated_content = Column(Text, nullable=True)
    template_version = Column(String(50), nullable=True)
    generation_status = Column(String(50), default="pending")
    generation_started_at = Column(DateTime, nullable=True)
    generation_completed_at = Column(DateTime, nullable=True)
    source_references = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="reports")

    __table_args__ = (
        Index("idx_reports_tenant", "tenant_id"),
        Index("idx_reports_project", "project_id"),
        Index("idx_reports_status", "generation_status"),
    )


class KnowledgeBase(Base):
    """Knowledge base documents with jurisdiction support."""

    __tablename__ = "knowledge_base"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True
    )  # NULL for shared standards
    jurisdiction = Column(String(10), nullable=False)  # HK, SG, AU
    title = Column(String(255), nullable=False)
    standard = Column(String(100), nullable=True)  # HKFRS 15, SME-FRS, etc.
    version = Column(String(50), nullable=True)
    document_type = Column(String(50), nullable=True)  # standard, guidance, case_study
    source_file_path = Column(Text, nullable=True)
    raw_content = Column(Text, nullable=True)
    effective_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    kb_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    chunks = relationship("KBChunk", back_populates="kb_document", lazy="dynamic")

    __table_args__ = (
        Index("idx_kb_tenant", "tenant_id"),
        Index("idx_kb_jurisdiction", "jurisdiction"),
        Index("idx_kb_standard", "standard"),
        Index("idx_kb_active", "is_active"),
    )


class KBChunk(Base):
    """Knowledge base chunks with embeddings."""

    __tablename__ = "kb_chunks"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    jurisdiction = Column(String(10), nullable=False)
    kb_document_id = Column(
        Integer, ForeignKey("knowledge_base.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index = Column(Integer, nullable=True)
    chunk_type = Column(String(50), nullable=True)
    content = Column(Text, nullable=True)
    embedding = Column(Vector(1536), nullable=True)  # OpenAI ada-002 dimensions
    chunk_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    kb_document = relationship("KnowledgeBase", back_populates="chunks")

    __table_args__ = (
        Index("idx_kb_chunks_tenant", "tenant_id"),
        Index("idx_kb_chunks_jurisdiction", "jurisdiction"),
        Index("idx_kb_chunks_document", "kb_document_id"),
        # Vector similarity index (created after data is loaded)
        # Index("idx_kb_chunks_embedding", "embedding", postgresql_using="ivfflat",
        #       postgresql_ops={"embedding": "vector_cosine_ops"}),
    )
