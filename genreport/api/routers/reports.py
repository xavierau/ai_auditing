"""Report Generation API Endpoints (Sprint 4 Phase 5).

These endpoints handle AI-powered report generation using SecureOrchestrator.
All endpoints enforce tenant isolation and audit logging.
"""

import logging
from typing import List
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from genreport.core.database.base import get_db
from genreport.core.database.models import (
    GeneratedReport,
    ReportSection,
    SourceReference,
    AgentExecution,
    Project,
    User,
)
from genreport.core.orchestration.secure_orchestrator import SecureOrchestrator
from genreport.core.orchestration.agent_models import AgentOutput
from genreport.core.security.tenant_context import get_current_tenant
from genreport.core.security.audit_logger import AuditLogger
from genreport.core.security.jwt_service import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


# Pydantic Models for API

class SourceReferenceResponse(BaseModel):
    """Source reference response model."""
    kb_chunk_id: int
    similarity_score: float


class ReportSectionResponse(BaseModel):
    """Report section response model."""
    id: int
    section_name: str
    agent_name: str
    content: str
    standard_used: str
    confidence_score: float
    completeness_score: float
    required_disclosures_met: dict
    warnings: List[str]
    pii_detected: bool
    pii_types: dict | None
    source_references: List[SourceReferenceResponse]

    class Config:
        from_attributes = True


class GeneratedReportResponse(BaseModel):
    """Generated report response model."""
    id: int
    tenant_id: UUID
    project_id: int
    generated_by: int
    jurisdiction: str
    accounting_standard: str
    overall_completeness: float
    generation_time_seconds: float
    cost_usd: float
    status: str
    error_message: str | None
    created_at: datetime
    sections: List[ReportSectionResponse]

    class Config:
        from_attributes = True


class GenerateReportResponse(BaseModel):
    """Response for report generation endpoint."""
    report_id: int
    sections: List[ReportSectionResponse]
    status: str
    overall_completeness: float
    generation_time_seconds: float


# Endpoints

@router.post("/generate/{project_id}", response_model=GenerateReportResponse)
async def generate_report(
    project_id: int,
    tenant_id: UUID = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate AI-powered audit report for a project.

    This endpoint:
    1. Validates the project belongs to the tenant
    2. Creates SecureOrchestrator for the project's jurisdiction
    3. Runs all agents to generate disclosure sections
    4. Stores results in database with audit trail

    Args:
        project_id: Project ID to generate report for
        tenant_id: Current tenant (from middleware)
        current_user: Current user (from auth)
        db: Database session

    Returns:
        Generated report with all sections

    Raises:
        HTTPException 404: Project not found
        HTTPException 403: Project belongs to different tenant
    """
    start_time = datetime.utcnow()

    # Verify project exists and belongs to tenant
    project = db.query(Project).filter(
        Project.id == project_id,
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    if project.tenant_id != tenant_id:
        logger.warning(
            f"Tenant isolation violation attempt: tenant={tenant_id} "
            f"tried to access project={project_id} owned by tenant={project.tenant_id}"
        )
        AuditLogger.log_event(
            db=db,
            event_type="SECURITY_VIOLATION",
            action="ACCESS_DENIED",
            user_id=current_user.id,
            tenant_id=tenant_id,
            resource_type="project",
            resource_id=project_id,
            status="FAILURE",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Create report record
    report = GeneratedReport(
        tenant_id=tenant_id,
        project_id=project_id,
        generated_by=current_user.id,
        jurisdiction=project.jurisdiction,
        accounting_standard=project.accounting_standard,
        status="generating",
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    try:
        # Create orchestrator
        orchestrator = SecureOrchestrator(
            jurisdiction=project.jurisdiction,
            tenant_id=tenant_id,
            user_id=current_user.id,
            db=db,
        )

        # Run all agents
        # TODO: Load actual trial balance and general ledger data
        agent_outputs = orchestrator.run_all_agents(
            project_id=project_id,
            trial_balance={"tenant_id": tenant_id},  # Placeholder
            general_ledger={},  # Placeholder
            accounting_policies={},  # Placeholder
        )

        # Store sections and source references
        sections_data = []
        total_completeness = 0.0

        for section_name, output in agent_outputs.items():
            # Create section
            section = ReportSection(
                tenant_id=tenant_id,
                report_id=report.id,
                section_name=section_name,
                agent_name=output.agent_name if hasattr(output, 'agent_name') else section_name,
                content=output.disclosure_text,
                standard_used=output.standard_used if hasattr(output, 'standard_used') else project.accounting_standard,
                confidence_score=output.confidence_score,
                completeness_score=output.completeness_score,
                required_disclosures_met=output.required_disclosures if hasattr(output, 'required_disclosures') else {},
                warnings=output.warnings,
                pii_detected=len(output.warnings) > 0 and any("PII" in w for w in output.warnings),
                pii_types={} if not any("PII" in w for w in output.warnings) else {"detected": True},
            )
            db.add(section)
            db.flush()  # Get section.id

            # Store source references
            source_refs = []
            for source in output.sources:
                source_ref = SourceReference(
                    tenant_id=tenant_id,
                    section_id=section.id,
                    kb_chunk_id=source.get("chunk_id") or source.get("kb_chunk_id"),
                    similarity_score=source.get("score", 0.0),
                )
                db.add(source_ref)
                source_refs.append(SourceReferenceResponse(
                    kb_chunk_id=source_ref.kb_chunk_id,
                    similarity_score=source_ref.similarity_score,
                ))

            total_completeness += output.completeness_score

            sections_data.append(ReportSectionResponse(
                id=section.id,
                section_name=section.section_name,
                agent_name=section.agent_name,
                content=section.content,
                standard_used=section.standard_used,
                confidence_score=section.confidence_score,
                completeness_score=section.completeness_score,
                required_disclosures_met=section.required_disclosures_met,
                warnings=section.warnings,
                pii_detected=section.pii_detected,
                pii_types=section.pii_types,
                source_references=source_refs,
            ))

        # Calculate metrics
        end_time = datetime.utcnow()
        generation_time = (end_time - start_time).total_seconds()
        overall_completeness = total_completeness / len(agent_outputs) if agent_outputs else 0.0

        # Update report
        report.status = "completed"
        report.overall_completeness = overall_completeness
        report.generation_time_seconds = generation_time
        report.cost_usd = 0.0  # TODO: Calculate actual LLM costs
        db.commit()

        # Audit log success
        AuditLogger.log_event(
            db=db,
            event_type="REPORT_GENERATION",
            action="GENERATE",
            user_id=current_user.id,
            tenant_id=tenant_id,
            resource_type="generated_report",
            resource_id=report.id,
            status="SUCCESS",
        )

        logger.info(
            f"Report generated successfully: report_id={report.id}, "
            f"project_id={project_id}, sections={len(sections_data)}, "
            f"completeness={overall_completeness:.2f}, time={generation_time:.2f}s"
        )

        return GenerateReportResponse(
            report_id=report.id,
            sections=sections_data,
            status="completed",
            overall_completeness=overall_completeness,
            generation_time_seconds=generation_time,
        )

    except Exception as e:
        # Update report with error
        report.status = "failed"
        report.error_message = str(e)
        db.commit()

        # Audit log failure
        AuditLogger.log_event(
            db=db,
            event_type="REPORT_GENERATION",
            action="GENERATE",
            user_id=current_user.id,
            tenant_id=tenant_id,
            resource_type="generated_report",
            resource_id=report.id,
            status="FAILURE",
        )

        logger.error(f"Report generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {str(e)}",
        )


@router.get("/{report_id}", response_model=GeneratedReportResponse)
async def get_report(
    report_id: int,
    tenant_id: UUID = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a generated report by ID.

    Args:
        report_id: Report ID
        tenant_id: Current tenant (from middleware)
        current_user: Current user (from auth)
        db: Database session

    Returns:
        Generated report with sections

    Raises:
        HTTPException 404: Report not found
        HTTPException 403: Report belongs to different tenant
    """
    report = db.query(GeneratedReport).filter(
        GeneratedReport.id == report_id,
        GeneratedReport.is_deleted == False,
    ).first()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found",
        )

    if report.tenant_id != tenant_id:
        logger.warning(
            f"Tenant isolation violation attempt: tenant={tenant_id} "
            f"tried to access report={report_id} owned by tenant={report.tenant_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return report


@router.get("/project/{project_id}", response_model=List[GeneratedReportResponse])
async def list_project_reports(
    project_id: int,
    tenant_id: UUID = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all reports for a project.

    Args:
        project_id: Project ID
        tenant_id: Current tenant (from middleware)
        current_user: Current user (from auth)
        db: Database session

    Returns:
        List of generated reports

    Raises:
        HTTPException 404: Project not found
        HTTPException 403: Project belongs to different tenant
    """
    # Verify project exists and belongs to tenant
    project = db.query(Project).filter(
        Project.id == project_id,
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    if project.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Get all reports for project
    reports = db.query(GeneratedReport).filter(
        GeneratedReport.project_id == project_id,
        GeneratedReport.tenant_id == tenant_id,
        GeneratedReport.is_deleted == False,
    ).all()

    return reports


@router.delete("/{report_id}")
async def delete_report(
    report_id: int,
    tenant_id: UUID = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft delete a generated report (admin only).

    Args:
        report_id: Report ID to delete
        tenant_id: Current tenant (from middleware)
        current_user: Current user (from auth)
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException 403: User is not admin or report belongs to different tenant
        HTTPException 404: Report not found
    """
    # Check admin permission
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete reports",
        )

    report = db.query(GeneratedReport).filter(
        GeneratedReport.id == report_id,
        GeneratedReport.is_deleted == False,
    ).first()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found",
        )

    if report.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Soft delete
    report.is_deleted = True
    db.commit()

    # Audit log
    AuditLogger.log_event(
        db=db,
        event_type="REPORT_DELETION",
        action="DELETE",
        user_id=current_user.id,
        tenant_id=tenant_id,
        resource_type="generated_report",
        resource_id=report_id,
        status="SUCCESS",
    )

    logger.info(f"Report deleted: report_id={report_id}, user={current_user.id}")

    return {"message": f"Report {report_id} deleted successfully"}
