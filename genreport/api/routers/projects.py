"""Projects router for CRUD operations on audit projects."""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from genreport.api.dependencies import CommonDeps
from genreport.core.database.models import Client, Project
from genreport.core.security.audit_logger import AuditLogger
from genreport.core.security.jwt_service import require_auditor

router = APIRouter()


# Pydantic Models
class ClientCreate(BaseModel):
    """Client creation model."""

    company_name: str
    registration_number: Optional[str] = None
    address: Optional[str] = None
    industry: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None


class ClientResponse(BaseModel):
    """Client response model."""

    id: int
    company_name: str
    registration_number: Optional[str]
    industry: Optional[str]

    class Config:
        from_attributes = True


class ProjectCreate(BaseModel):
    """Project creation model."""

    client_id: int
    jurisdiction: str = "HK"
    accounting_standard: str = "HKFRS"
    financial_year_end: date
    project_name: Optional[str] = None
    directors_names: Optional[List[str]] = None


class ProjectResponse(BaseModel):
    """Project response model."""

    id: int
    client_id: int
    jurisdiction: str
    accounting_standard: str
    financial_year_end: date
    project_name: Optional[str]
    status: str

    class Config:
        from_attributes = True


@router.post("/clients", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    client_data: ClientCreate,
    deps: CommonDeps = Depends(),
    _: None = Depends(require_auditor),
):
    """Create a new client.

    Requires auditor role or higher.

    Args:
        client_data: Client details
        deps: Common dependencies (db, user, tenant_id, etc.)

    Returns:
        Created client

    Raises:
        HTTPException: If validation fails
    """
    # Create client
    client = Client(
        tenant_id=deps.tenant_id,
        company_name=client_data.company_name,
        registration_number=client_data.registration_number,
        address=client_data.address,
        industry=client_data.industry,
        contact_person=client_data.contact_person,
        contact_email=client_data.contact_email,
        contact_phone=client_data.contact_phone,
    )

    deps.db.add(client)
    deps.db.commit()
    deps.db.refresh(client)

    # Audit log
    AuditLogger.log_data_access(
        db=deps.db,
        user_id=deps.user.id,
        tenant_id=deps.tenant_id,
        resource_type="client",
        resource_id=client.id,
        action=AuditLogger.CREATE,
        ip_address=deps.ip_address,
    )

    return client


@router.get("/clients", response_model=List[ClientResponse])
async def list_clients(
    deps: CommonDeps = Depends(),
    skip: int = 0,
    limit: int = 100,
):
    """List all clients for current tenant.

    Args:
        deps: Common dependencies
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of clients
    """
    clients = (
        deps.db.query(Client)
        .filter(Client.tenant_id == deps.tenant_id)
        .offset(skip)
        .limit(limit)
        .all()
    )

    return clients


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    deps: CommonDeps = Depends(),
    _: None = Depends(require_auditor),
):
    """Create a new audit project.

    Requires auditor role or higher.

    Args:
        project_data: Project details
        deps: Common dependencies

    Returns:
        Created project

    Raises:
        HTTPException: If client doesn't exist or validation fails
    """
    # Verify client exists and belongs to tenant
    client = (
        deps.db.query(Client)
        .filter(Client.id == project_data.client_id, Client.tenant_id == deps.tenant_id)
        .first()
    )

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    # Validate jurisdiction
    from genreport.core.utils.market_config import validate_jurisdiction

    if not validate_jurisdiction(project_data.jurisdiction):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid jurisdiction: {project_data.jurisdiction}",
        )

    # Create project
    project = Project(
        tenant_id=deps.tenant_id,
        client_id=project_data.client_id,
        user_id=deps.user.id,
        jurisdiction=project_data.jurisdiction,
        accounting_standard=project_data.accounting_standard,
        financial_year_end=project_data.financial_year_end,
        project_name=project_data.project_name,
        directors_names=project_data.directors_names,
        status="draft",
    )

    deps.db.add(project)
    deps.db.commit()
    deps.db.refresh(project)

    # Audit log
    AuditLogger.log_data_access(
        db=deps.db,
        user_id=deps.user.id,
        tenant_id=deps.tenant_id,
        resource_type="project",
        resource_id=project.id,
        action=AuditLogger.CREATE,
        ip_address=deps.ip_address,
    )

    return project


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    deps: CommonDeps = Depends(),
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
):
    """List all projects for current tenant.

    Args:
        deps: Common dependencies
        skip: Number of records to skip
        limit: Maximum number of records to return
        status_filter: Optional status filter (draft, in_progress, completed)

    Returns:
        List of projects
    """
    query = deps.db.query(Project).filter(Project.tenant_id == deps.tenant_id)

    if status_filter:
        query = query.filter(Project.status == status_filter)

    projects = query.offset(skip).limit(limit).all()

    return projects


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    deps: CommonDeps = Depends(),
):
    """Get a specific project by ID.

    Args:
        project_id: Project ID
        deps: Common dependencies

    Returns:
        Project details

    Raises:
        HTTPException: If project not found
    """
    project = (
        deps.db.query(Project)
        .filter(Project.id == project_id, Project.tenant_id == deps.tenant_id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Audit log
    AuditLogger.log_data_access(
        db=deps.db,
        user_id=deps.user.id,
        tenant_id=deps.tenant_id,
        resource_type="project",
        resource_id=project.id,
        action=AuditLogger.READ,
        ip_address=deps.ip_address,
    )

    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    deps: CommonDeps = Depends(),
    _: None = Depends(require_auditor),
):
    """Delete a project.

    Requires auditor role or higher.

    Args:
        project_id: Project ID to delete
        deps: Common dependencies

    Raises:
        HTTPException: If project not found
    """
    project = (
        deps.db.query(Project)
        .filter(Project.id == project_id, Project.tenant_id == deps.tenant_id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Audit log before deletion
    AuditLogger.log_data_access(
        db=deps.db,
        user_id=deps.user.id,
        tenant_id=deps.tenant_id,
        resource_type="project",
        resource_id=project.id,
        action=AuditLogger.DELETE,
        ip_address=deps.ip_address,
    )

    deps.db.delete(project)
    deps.db.commit()

    return None
