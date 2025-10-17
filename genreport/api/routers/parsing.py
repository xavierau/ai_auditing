"""Parsing API endpoints.

This module provides endpoints for initiating Excel parsing, checking status,
and retrieving relationship maps with tenant isolation.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session

from genreport.core.database.base import get_db
from genreport.core.database.models import User, Project, FileMetadata
from genreport.api.dependencies import get_current_user
from genreport.core.security.tenant_context import get_current_tenant
from genreport.core.security.audit_logger import AuditLogger
from genreport.core.security.file_encryption import FileEncryptionService
from genreport.core.security.encryption import encryption_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def parse_file_background(
    project_id: int,
    file_id: UUID,
    tenant_id: UUID,
    user_id: int,
):
    """Trigger Celery task to parse Excel file.

    Args:
        project_id: ID of project
        file_id: UUID of file to parse
        tenant_id: UUID of tenant for isolation
        user_id: ID of user who triggered parsing
    """
    from genreport.core.tasks.parsing_tasks import parse_excel_file_task

    logger.info(f"Queueing Celery task for project {project_id}, file {file_id}")

    # Queue Celery task (convert UUIDs to strings)
    parse_excel_file_task.delay(
        file_id=str(file_id),
        project_id=project_id,
        tenant_id=str(tenant_id),
        user_id=user_id,
    )


@router.post("/projects/{project_id}/parse", status_code=status.HTTP_202_ACCEPTED)
async def parse_project(
    project_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Initiate parsing of project's Excel file.

    Security features:
    - Tenant isolation
    - File ownership verification
    - Background task processing
    - Audit logging

    Args:
        project_id: ID of project to parse
        background_tasks: FastAPI background tasks
        db: Database session
        current_user: Authenticated user
        tenant_id: Current tenant ID from context

    Returns:
        Dictionary with status and project_id

    Raises:
        HTTPException 404: Project not found or no file uploaded
    """
    # Verify project belongs to tenant
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.tenant_id == tenant_id)
        .first()
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get latest file for project
    file_record = (
        db.query(FileMetadata)
        .filter(
            FileMetadata.project_id == project_id,
            FileMetadata.tenant_id == tenant_id,
        )
        .order_by(FileMetadata.created_at.desc())
        .first()
    )

    if not file_record:
        raise HTTPException(status_code=404, detail="No file uploaded for this project")

    # Add background task
    background_tasks.add_task(
        parse_file_background,
        project_id=project_id,
        file_id=file_record.id,
        tenant_id=tenant_id,
        user_id=current_user.id,
    )

    # Update project status (optional)
    project.status = "parsing"
    db.commit()

    # Audit log
    AuditLogger.log_event(
        db=db,
        event_type="PARSING_INITIATED",
        action="CREATE",
        user_id=current_user.id,
        tenant_id=tenant_id,
        resource_type="project",
        resource_id=project_id,
        status="SUCCESS",
        details={
            "project_id": project_id,
            "file_id": str(file_record.id),
        },
    )

    logger.info(
        f"Parsing initiated for project {project_id} "
        f"(file_id={file_record.id}, user_id={current_user.id})"
    )

    return {
        "status": "parsing_started",
        "project_id": project_id,
        "message": "Parsing initiated in background",
    }


@router.get("/projects/{project_id}/status")
async def get_parsing_status(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Get parsing status for a project.

    Security features:
    - Tenant isolation
    - Project ownership verification

    Args:
        project_id: ID of project
        db: Database session
        current_user: Authenticated user
        tenant_id: Current tenant ID from context

    Returns:
        Dictionary with parsing status

    Raises:
        HTTPException 404: Project not found
    """
    # Verify project belongs to tenant
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.tenant_id == tenant_id)
        .first()
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if file exists
    has_file = (
        db.query(FileMetadata)
        .filter(
            FileMetadata.project_id == project_id,
            FileMetadata.tenant_id == tenant_id,
        )
        .first()
        is not None
    )

    # Determine status based on project and file existence
    if not has_file:
        status = "not_started"
    elif project.status == "parsing":
        status = "parsing"
    elif project.status == "completed":
        status = "completed"
    elif project.status == "failed":
        status = "failed"
    else:
        status = "not_started"

    logger.info(f"Parsing status for project {project_id}: {status}")

    return {
        "status": status,
        "project_id": project_id,
    }


@router.get("/projects/{project_id}/relationship-map")
async def get_relationship_map(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Get relationship map for a parsed project.

    Security features:
    - Tenant isolation
    - Project ownership verification

    Args:
        project_id: ID of project
        db: Database session
        current_user: Authenticated user
        tenant_id: Current tenant ID from context

    Returns:
        Dictionary with coding system and relationships

    Raises:
        HTTPException 404: Project not found or not yet parsed
    """
    # Verify project belongs to tenant
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.tenant_id == tenant_id)
        .first()
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # TODO: Retrieve relationship map from database
    # For now, return mock data for testing
    # In Phase 5, this will query the actual relationship map table

    # Check if parsing is complete
    if project.status != "completed":
        raise HTTPException(
            status_code=404,
            detail="Project not yet parsed or parsing failed"
        )

    # Mock relationship map for testing
    relationship_map = {
        "coding_system": "numeric",  # or "alphabetic"
        "relationships": [
            {
                "worksheet": "Trial Balance",
                "importance": "critical",
                "coding_pattern": "numeric",
            }
        ],
    }

    logger.info(f"Retrieved relationship map for project {project_id}")

    return relationship_map
