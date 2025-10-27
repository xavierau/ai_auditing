"""
Export API Router

Handles DOCX report export with market-specific templates.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from uuid import UUID
from pathlib import Path
import tempfile
from datetime import datetime

from genreport.core.database.base import get_db
from genreport.api.dependencies import get_current_user
from genreport.core.security.tenant_context import get_current_tenant
from genreport.core.security.audit_logger import AuditLogger
from genreport.core.database.models import User, Project, Jurisdiction
from genreport.core.export import MarketAwareDocxGenerator


router = APIRouter(prefix="/export", tags=["export"])


@router.post("/projects/{project_id}/docx")
async def export_project_report(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant)
) -> FileResponse:
    """
    Export project report as DOCX using market-specific template.

    Args:
        project_id: Project ID to export
        db: Database session
        current_user: Authenticated user
        tenant_id: Current tenant context

    Returns:
        FileResponse with generated DOCX file

    Raises:
        HTTPException: If project not found or access denied
    """
    # Get project with tenant isolation
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.tenant_id == tenant_id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Convert jurisdiction string to enum
    try:
        jurisdiction_enum = Jurisdiction(project.jurisdiction)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid jurisdiction: {project.jurisdiction}")

    # Build report data
    report_data = {
        'project_name': project.project_name,
        'client_name': project.client.company_name if project.client else 'Unknown',
        'currency': project.currency,
        'jurisdiction': project.jurisdiction,
        'accounting_standard': project.accounting_standard,
        'financial_year_end': project.financial_year_end,
        'created_at': project.created_at,
        'status': project.status,
    }

    # Add revenue if available
    if project.revenue:
        report_data['revenue'] = float(project.revenue)
        report_data['amount'] = float(project.revenue)
        report_data['total'] = float(project.revenue)

    # TODO: Add actual report sections from database
    # For now, include placeholder sections
    report_data['sections'] = [
        {
            'title': 'Revenue Recognition',
            'content': f"""The Company recognizes revenue when control of goods or services is transferred to customers.

For the year ended {project.financial_year_end.strftime('%d %B %Y')}, total revenue amounted to {project.currency} {project.revenue:,.2f}.

Revenue is recognized in accordance with {project.accounting_standard}."""
        }
    ]

    try:
        # Generate DOCX
        generator = MarketAwareDocxGenerator(jurisdiction_enum)

        # Create temporary file
        temp_dir = Path(tempfile.gettempdir())
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"{project.project_name.replace(' ', '_')}_{timestamp}.docx"
        output_path = temp_dir / output_filename

        # Generate document
        generator.generate(report_data, output_path=output_path)

        # Audit log
        AuditLogger.log_event(
            db=db,
            event_type="EXPORT",
            action="DOCX_EXPORT",
            user_id=current_user.id,
            tenant_id=tenant_id,
            resource_type="project",
            resource_id=project_id,
            metadata={
                'project_name': project.project_name,
                'jurisdiction': project.jurisdiction,
                'filename': output_filename
            }
        )

        # Return file
        return FileResponse(
            path=str(output_path),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=output_filename,
            headers={
                "Content-Disposition": f'attachment; filename="{output_filename}"'
            }
        )

    except Exception as e:
        # Log error
        AuditLogger.log_event(
            db=db,
            event_type="EXPORT",
            action="DOCX_EXPORT_FAILED",
            user_id=current_user.id,
            tenant_id=tenant_id,
            resource_type="project",
            resource_id=project_id,
            metadata={'error': str(e)}
        )
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")
