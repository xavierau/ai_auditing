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
    last_login_at = Column(DateTime, nullable=True)  # Fixed: was last_login
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

    # Hierarchy support
    parent_id = Column(Integer, ForeignKey("knowledge_base.id"), nullable=True)
    section_level = Column(Integer, default=0)  # 0=document, 1=chapter, 2=section
    section_path = Column(String(255), nullable=True)  # e.g., "15.1.2"

    # Versioning support
    effective_date = Column(Date, nullable=True)
    supersedes_id = Column(Integer, ForeignKey("knowledge_base.id"), nullable=True)

    # Access control
    access_level = Column(String(20), default="PUBLIC")  # PUBLIC, TENANT, RESTRICTED
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
        Index("idx_kb_parent", "parent_id"),
        Index("idx_kb_compound_filter", "jurisdiction", "is_active", "tenant_id"),
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
    chunk_index = Column(Integer, nullable=False)
    chunk_type = Column(String(50), nullable=True)  # definition, requirement, example, guidance
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=True)  # Supports both Gemini and OpenAI embeddings
    embedding_model = Column(String(100), nullable=True)  # Track which model generated the embedding

    # Quality metrics for semi-automated approval
    confidence_score = Column(Float, nullable=True)  # LLM confidence 0.0 to 1.0
    review_status = Column(String(50), default="pending")  # auto_approved, pending_review, reviewed
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    # Cross-references
    cross_references = Column(JSONB, nullable=True)  # Links to related sections
    prerequisites = Column(JSONB, nullable=True)  # Required background knowledge

    chunk_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    kb_document = relationship("KnowledgeBase", back_populates="chunks")

    __table_args__ = (
        Index("idx_kb_chunks_tenant", "tenant_id"),
        Index("idx_kb_chunks_jurisdiction", "jurisdiction"),
        Index("idx_kb_chunks_document", "kb_document_id"),
        Index("idx_kb_chunks_review_status", "review_status"),
        Index("idx_kb_chunks_compound_filter", "jurisdiction", "tenant_id", "review_status"),
        # Vector similarity index (created after data is loaded)
        # Index("idx_kb_chunks_embedding", "embedding", postgresql_using="ivfflat",
        #       postgresql_ops={"embedding": "vector_cosine_ops"}),
    )


class FileMetadata(Base):
    """Uploaded file metadata with encryption tracking."""

    __tablename__ = "file_metadata"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    original_filename = Column(String(255), nullable=False)
    storage_path = Column(Text, nullable=False)  # Path to encrypted file
    file_size = Column(Integer, nullable=False)  # Original file size in bytes
    mime_type = Column(String(100), nullable=True)
    encrypted = Column(Boolean, default=True)
    has_macros = Column(Boolean, default=False)  # Detected macros
    parsing_status = Column(
        String(50), default="pending"
    )  # pending, in_progress, completed, failed
    parsing_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    worksheet_analyses = relationship(
        "WorksheetAnalysis", back_populates="file", lazy="dynamic", cascade="all, delete-orphan"
    )
    relationship_maps = relationship(
        "RelationshipMap", back_populates="file", lazy="dynamic", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_file_metadata_tenant", "tenant_id"),
        Index("idx_file_metadata_project", "project_id"),
        Index("idx_file_metadata_status", "parsing_status"),
        Index("idx_file_metadata_created", "created_at"),
    )


class WorksheetAnalysis(Base):
    """Preliminary scanner worksheet analysis results."""

    __tablename__ = "worksheet_analyses"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(
        PGUUID(as_uuid=True), ForeignKey("file_metadata.id", ondelete="CASCADE"), nullable=False
    )
    worksheet_name = Column(String(255), nullable=False)
    is_summary = Column(Boolean, default=False)
    is_supporting = Column(Boolean, default=False)
    referenced_codes = Column(ARRAY(Text), nullable=True)  # Other worksheet codes referenced
    importance_score = Column(Float, nullable=True)  # 0.0 to 1.0
    analysis_metadata = Column(JSONB, nullable=True)  # Additional LLM analysis results
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    file = relationship("FileMetadata", back_populates="worksheet_analyses")

    __table_args__ = (
        Index("idx_worksheet_analyses_tenant", "tenant_id"),
        Index("idx_worksheet_analyses_project", "project_id"),
        Index("idx_worksheet_analyses_file", "file_id"),
        Index("idx_worksheet_analyses_importance", "importance_score"),
    )


class RelationshipMap(Base):
    """Worksheet relationship mapping from preliminary scanner."""

    __tablename__ = "relationship_maps"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(
        PGUUID(as_uuid=True), ForeignKey("file_metadata.id", ondelete="CASCADE"), nullable=False
    )
    coding_system = Column(String(255), nullable=True)  # Discovered coding pattern
    code_families = Column(JSONB, nullable=True)  # Grouped code families from LLM
    relationships = Column(JSONB, nullable=True)  # Complete relationship graph
    recommended_sheets = Column(ARRAY(Text), nullable=True)  # Top-priority worksheets
    confidence_score = Column(Float, nullable=True)  # Overall confidence 0.0 to 1.0
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    file = relationship("FileMetadata", back_populates="relationship_maps")

    __table_args__ = (
        Index("idx_relationship_maps_tenant", "tenant_id"),
        Index("idx_relationship_maps_project", "project_id"),
        Index("idx_relationship_maps_file", "file_id"),
    )


class GeneratedReport(Base):
    """Store complete generated reports from AI agents (Sprint 4)."""

    __tablename__ = "generated_reports"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    generated_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    jurisdiction = Column(String(10), nullable=False)  # HK, SG, AU
    accounting_standard = Column(String(50), nullable=False)  # HKFRS, SME-FRS

    overall_completeness = Column(Float, nullable=True)  # Average across sections
    generation_time_seconds = Column(Float, nullable=True)
    cost_usd = Column(Float, nullable=True)

    status = Column(String(20), default="generating")  # generating, completed, failed
    error_message = Column(Text, nullable=True)

    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    sections = relationship(
        "ReportSection", back_populates="report", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_generated_reports_tenant", "tenant_id"),
        Index("idx_generated_reports_project", "project_id"),
        Index("idx_generated_reports_status", "status"),
    )


class ReportSection(Base):
    """Individual report sections (one per agent) (Sprint 4)."""

    __tablename__ = "report_sections"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    report_id = Column(
        Integer, ForeignKey("generated_reports.id", ondelete="CASCADE"), nullable=False
    )

    section_name = Column(String(100), nullable=False)  # revenue_recognition, ppe, etc.
    agent_name = Column(String(100), nullable=False)  # HKRevenueAgent, etc.

    content = Column(Text, nullable=False)  # Generated disclosure
    standard_used = Column(String(100), nullable=False)  # HKFRS 15, IAS 16, etc.

    completeness_score = Column(Float, nullable=True)  # 0.0 to 1.0
    required_disclosures_met = Column(JSONB, nullable=True)  # List of checklist items

    pii_detected = Column(Boolean, default=False)
    pii_types = Column(JSONB, nullable=True)  # List of PII types found

    execution_time_seconds = Column(Float, nullable=True)
    cost_usd = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    report = relationship("GeneratedReport", back_populates="sections")
    source_references = relationship(
        "SourceReference", back_populates="section", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_report_sections_tenant", "tenant_id"),
        Index("idx_report_sections_report", "report_id"),
    )


class SourceReference(Base):
    """KB chunks used for each section (Sprint 4)."""

    __tablename__ = "source_references"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    section_id = Column(
        Integer, ForeignKey("report_sections.id", ondelete="CASCADE"), nullable=False
    )

    kb_chunk_id = Column(Integer, ForeignKey("kb_chunks.id"), nullable=False)
    similarity_score = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    section = relationship("ReportSection", back_populates="source_references")
    kb_chunk = relationship("KBChunk")

    __table_args__ = (
        Index("idx_source_references_tenant", "tenant_id"),
        Index("idx_source_references_section", "section_id"),
    )


class AgentExecution(Base):
    """Audit trail for agent executions (Sprint 4)."""

    __tablename__ = "agent_executions"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    report_id = Column(Integer, ForeignKey("generated_reports.id"), nullable=False)

    agent_name = Column(String(100), nullable=False)
    section_name = Column(String(100), nullable=False)

    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    status = Column(String(20), nullable=False)  # running, completed, failed
    error_message = Column(Text, nullable=True)

    context_size_bytes = Column(Integer, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    cost_usd = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_agent_executions_tenant", "tenant_id"),
        Index("idx_agent_executions_report", "report_id"),
    )
