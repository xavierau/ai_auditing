"""Celery tasks for Excel file parsing with tenant isolation.

This module implements background parsing tasks that maintain strict tenant isolation
and comprehensive error handling with retry logic.
"""

import logging
import tempfile
from pathlib import Path
from typing import Dict, Any
from uuid import UUID

from celery import Task
from sqlalchemy.orm import Session

from genreport.core.tasks import celery_app
from genreport.core.database.base import get_db
from genreport.core.database.models import Project, FileMetadata
from genreport.core.security.tenant_context import current_tenant
from genreport.core.security.audit_logger import AuditLogger
from genreport.core.security.file_encryption import FileEncryptionService
from genreport.core.security.encryption import encryption_service
from genreport.core.parsing.preliminary_scanner import PreliminaryScanner

logger = logging.getLogger(__name__)


class ParseExcelTask(Task):
    """Base task class with error handling."""

    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3, "countdown": 60}  # Retry 3 times, wait 60s
    retry_backoff = True
    retry_backoff_max = 600  # Max 10 minutes backoff
    retry_jitter = True


def _write_temp_file(content: bytes, filename: str) -> Path:
    """Write decrypted content to temp file for processing.

    Args:
        content: File content
        filename: Original filename

    Returns:
        Path to temp file
    """
    suffix = Path(filename).suffix
    temp_file = tempfile.NamedTemporaryFile(
        delete=False, suffix=suffix, prefix="parsing_"
    )
    temp_file.write(content)
    temp_file.close()
    return Path(temp_file.name)


def _cleanup_temp_file(temp_file: Path):
    """Clean up temporary file.

    Args:
        temp_file: Path to temp file
    """
    try:
        if temp_file.exists():
            temp_file.unlink()
            logger.debug(f"Cleaned up temp file: {temp_file}")
    except Exception as e:
        logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")


def _store_worksheet_analyses(
    db: Session, project_id: int, analyses: list, tenant_id: UUID
):
    """Store worksheet analyses in database.

    Args:
        db: Database session
        project_id: Project ID
        analyses: List of worksheet analyses
        tenant_id: Tenant ID for isolation
    """
    # TODO: In Sprint 4, create WorksheetAnalysis model and store
    # For now, this is a placeholder
    logger.info(f"Would store {len(analyses)} worksheet analyses for project {project_id}")


def _store_relationship_map(
    db: Session, project_id: int, relationship_map: dict, tenant_id: UUID
):
    """Store relationship map in database.

    Args:
        db: Database session
        project_id: Project ID
        relationship_map: Relationship map data
        tenant_id: Tenant ID for isolation
    """
    # TODO: In Sprint 4, create RelationshipMap model and store
    # For now, this is a placeholder
    logger.info(f"Would store relationship map for project {project_id}")


@celery_app.task(bind=True, base=ParseExcelTask, name="genreport.core.tasks.parsing_tasks.parse_excel_file_task")
def parse_excel_file_task(
    self,
    file_id: str,
    project_id: int,
    tenant_id: str,
    user_id: int,
) -> Dict[str, Any]:
    """Parse Excel file in background with tenant isolation.

    This task:
    1. Sets tenant context for isolation
    2. Retrieves and decrypts file
    3. Parses with PreliminaryScanner
    4. Stores results in database
    5. Updates project status
    6. Logs audit events

    Args:
        file_id: UUID of file to parse (as string)
        project_id: ID of project
        tenant_id: UUID of tenant (as string) for isolation
        user_id: ID of user who triggered parsing

    Returns:
        Dictionary with parsing results

    Raises:
        Exception: If parsing fails (will trigger retry)
    """
    file_uuid = UUID(file_id)
    tenant_uuid = UUID(tenant_id)

    # Set tenant context for background task
    token = current_tenant.set(tenant_uuid)

    temp_file = None

    try:
        logger.info(
            f"Starting Excel parsing: file_id={file_id}, "
            f"project_id={project_id}, tenant_id={tenant_id}"
        )

        # Get database session
        db = next(get_db())

        try:
            # Verify project belongs to tenant
            project = (
                db.query(Project)
                .filter(Project.id == project_id, Project.tenant_id == tenant_uuid)
                .first()
            )

            if not project:
                raise ValueError(f"Project {project_id} not found for tenant {tenant_id}")

            # Get file metadata
            file_record = (
                db.query(FileMetadata)
                .filter(
                    FileMetadata.id == file_uuid,
                    FileMetadata.tenant_id == tenant_uuid,
                )
                .first()
            )

            if not file_record:
                raise ValueError(f"File {file_id} not found for tenant {tenant_id}")

            # Decrypt file
            logger.info(f"Decrypting file: {file_record.storage_path}")
            with open(file_record.storage_path, "rb") as f:
                encrypted_content = f.read()

            file_encryption = FileEncryptionService(encryption_service)
            decrypted_content = file_encryption.decrypt_file(
                encrypted_content, str(tenant_uuid)
            )

            # Write to temp file for processing
            temp_file = _write_temp_file(decrypted_content, file_record.original_filename)
            logger.info(f"Wrote temp file: {temp_file}")

            # Parse Excel file
            logger.info("Starting preliminary scan...")
            scanner = PreliminaryScanner()
            result = scanner.analyze_workbook(str(temp_file))

            logger.info(
                f"Parsing complete: {len(result.get('worksheet_analyses', []))} worksheets analyzed"
            )

            # Store results
            _store_worksheet_analyses(
                db, project_id, result.get("worksheet_analyses", []), tenant_uuid
            )
            _store_relationship_map(
                db,
                project_id,
                {
                    "coding_system": result.get("coding_system"),
                    "code_families": result.get("code_families"),
                },
                tenant_uuid,
            )

            # Update project status
            project.status = "completed"
            db.commit()

            # Audit log - success
            AuditLogger.log_event(
                db=db,
                event_type="PARSING",
                action="COMPLETE",
                user_id=user_id,
                tenant_id=tenant_uuid,
                resource_type="project",
                resource_id=project_id,
                status="SUCCESS",
                details={
                    "file_id": str(file_uuid),
                    "worksheets_analyzed": len(result.get("worksheet_analyses", [])),
                    "coding_system": result.get("coding_system"),
                },
            )

            logger.info(f"Parsing task completed successfully for project {project_id}")

            return {
                "status": "success",
                "project_id": project_id,
                "worksheets_analyzed": len(result.get("worksheet_analyses", [])),
                "coding_system": result.get("coding_system"),
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Parsing task failed: {str(e)}", exc_info=True)

        # Try to log failure to audit log
        try:
            db = next(get_db())
            try:
                # Update project status
                project = db.query(Project).filter(Project.id == project_id).first()
                if project:
                    project.status = "failed"
                    db.commit()

                # Audit log - failure
                AuditLogger.log_event(
                    db=db,
                    event_type="PARSING",
                    action="COMPLETE",
                    user_id=user_id,
                    tenant_id=tenant_uuid,
                    resource_type="project",
                    resource_id=project_id,
                    status="FAILURE",
                    details={"error": str(e), "file_id": str(file_uuid)},
                )
            finally:
                db.close()
        except Exception as audit_error:
            logger.error(f"Failed to log parsing failure: {audit_error}")

        # Re-raise for Celery retry
        raise

    finally:
        # Cleanup
        if temp_file:
            _cleanup_temp_file(temp_file)
        current_tenant.reset(token)
