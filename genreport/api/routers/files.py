"""File upload and download API endpoints.

This module provides secure file upload/download with encryption, validation,
and tenant isolation for Excel working papers.
"""

import os
from uuid import uuid4, UUID
from typing import List
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from genreport.core.database.base import get_db
from genreport.core.database.models import User, Project, FileMetadata
from genreport.api.dependencies import get_current_user
from genreport.core.security.tenant_context import get_current_tenant
from genreport.core.security.audit_logger import AuditLogger
from genreport.core.security.file_validation import validate_file_type, check_file_size
from genreport.core.security.file_encryption import FileEncryptionService
from genreport.core.security.encryption import encryption_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# File size limit: 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    project_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Securely upload and encrypt working paper file.

    Security features:
    - File type validation (extension + magic bytes)
    - File size limit (50MB)
    - Encryption at rest with tenant-specific keys
    - Tenant isolation
    - Audit logging

    Args:
        file: Uploaded file (Excel workbook)
        project_id: ID of project to associate file with
        db: Database session
        current_user: Authenticated user
        tenant_id: Current tenant ID from context

    Returns:
        Dictionary with file_id, filename, and size

    Raises:
        HTTPException 400: Invalid file type or size
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

    # Validate file type
    validate_file_type(file)

    # Read file content
    content = await file.read()

    # Check file size
    check_file_size(content, MAX_FILE_SIZE)

    # Encrypt file
    file_encryption = FileEncryptionService(encryption_service)
    encrypted_content = file_encryption.encrypt_file(content, str(tenant_id))

    # Generate secure file path
    file_id = uuid4()
    storage_dir = f"encrypted/{tenant_id}/{project_id}"
    os.makedirs(storage_dir, exist_ok=True)
    storage_path = f"{storage_dir}/{file_id}.enc"

    # Save encrypted file
    with open(storage_path, "wb") as f:
        f.write(encrypted_content)

    # Store metadata in database
    file_record = FileMetadata(
        id=file_id,
        tenant_id=tenant_id,
        project_id=project_id,
        original_filename=file.filename,
        storage_path=storage_path,
        file_size=len(content),
        encrypted=True,
        uploaded_by=current_user.id,
        mime_type=file.content_type,
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)

    # Audit log (convert UUID to string for audit_logs.resource_id)
    AuditLogger.log_event(
        db=db,
        event_type="FILE_UPLOAD",
        action="CREATE",
        user_id=current_user.id,
        tenant_id=tenant_id,
        resource_type="file",
        resource_id=None,  # UUID not compatible with Integer column
        status="SUCCESS",
        details={
            "file_id": str(file_record.id),
            "filename": file.filename,
            "size": len(content),
            "project_id": project_id,
        },
    )

    logger.info(
        f"File uploaded successfully: {file.filename} "
        f"(project_id={project_id}, file_id={file_id})"
    )

    return {
        "file_id": str(file_id),
        "filename": file.filename,
        "size": len(content),
    }


@router.get("/{file_id}")
async def download_file(
    file_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Download and decrypt file.

    Security features:
    - Tenant isolation (can only download own tenant's files)
    - Decryption with tenant-specific keys
    - Audit logging

    Args:
        file_id: ID of file to download
        db: Database session
        current_user: Authenticated user
        tenant_id: Current tenant ID from context

    Returns:
        Decrypted file content with appropriate content-type header

    Raises:
        HTTPException 404: File not found (or belongs to different tenant)
    """
    # Get file metadata (tenant-filtered)
    file_record = (
        db.query(FileMetadata)
        .filter(FileMetadata.id == file_id, FileMetadata.tenant_id == tenant_id)
        .first()
    )

    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    # Read encrypted file
    try:
        with open(file_record.storage_path, "rb") as f:
            encrypted_content = f.read()
    except FileNotFoundError:
        logger.error(f"File not found on disk: {file_record.storage_path}")
        raise HTTPException(
            status_code=500, detail="File not found on storage"
        )

    # Decrypt file
    file_encryption = FileEncryptionService(encryption_service)
    decrypted_content = file_encryption.decrypt_file(
        encrypted_content, str(tenant_id)
    )

    # Audit log (convert UUID to string for audit_logs.resource_id)
    AuditLogger.log_event(
        db=db,
        event_type="FILE_DOWNLOAD",
        action="READ",
        user_id=current_user.id,
        tenant_id=tenant_id,
        resource_type="file",
        resource_id=None,  # UUID not compatible with Integer column
        status="SUCCESS",
        details={
            "file_id": str(file_record.id),
            "filename": file_record.original_filename,
        },
    )

    logger.info(
        f"File downloaded: {file_record.original_filename} "
        f"(file_id={file_id}, user_id={current_user.id})"
    )

    return Response(
        content=decrypted_content,
        media_type=file_record.mime_type
        or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{file_record.original_filename}"'
        },
    )


@router.get("/project/{project_id}")
async def list_project_files(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant),
):
    """List all files for a project.

    Security features:
    - Tenant isolation
    - Project ownership verification

    Args:
        project_id: ID of project
        db: Database session
        current_user: Authenticated user
        tenant_id: Current tenant ID from context

    Returns:
        Dictionary with list of files

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

    # Get files for project
    files = (
        db.query(FileMetadata)
        .filter(
            FileMetadata.project_id == project_id,
            FileMetadata.tenant_id == tenant_id,
        )
        .order_by(FileMetadata.created_at.desc())
        .all()
    )

    return {
        "files": [
            {
                "file_id": str(f.id),
                "filename": f.original_filename,
                "size": f.file_size,
                "uploaded_at": f.created_at.isoformat(),
                "uploaded_by": f.uploaded_by,
            }
            for f in files
        ]
    }


@router.delete("/{file_id}")
async def delete_file(
    file_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Delete file (soft delete or hard delete).

    Security features:
    - Tenant isolation
    - Audit logging

    Args:
        file_id: ID of file to delete
        db: Database session
        current_user: Authenticated user
        tenant_id: Current tenant ID from context

    Returns:
        Success message

    Raises:
        HTTPException 404: File not found
    """
    # Get file metadata (tenant-filtered)
    file_record = (
        db.query(FileMetadata)
        .filter(FileMetadata.id == file_id, FileMetadata.tenant_id == tenant_id)
        .first()
    )

    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    # Delete physical file
    try:
        if os.path.exists(file_record.storage_path):
            os.remove(file_record.storage_path)
    except Exception as e:
        logger.error(f"Failed to delete file from disk: {e}")

    # Delete database record
    db.delete(file_record)
    db.commit()

    # Audit log (convert UUID to string for audit_logs.resource_id)
    AuditLogger.log_event(
        db=db,
        event_type="FILE_DELETE",
        action="DELETE",
        user_id=current_user.id,
        tenant_id=tenant_id,
        resource_type="file",
        resource_id=None,  # UUID not compatible with Integer column
        status="SUCCESS",
        details={
            "file_id": str(file_record.id),
            "filename": file_record.original_filename,
        },
    )

    logger.info(f"File deleted: {file_record.original_filename} (file_id={file_id})")

    return {"message": "File deleted successfully"}
