"""Tests for Report Generation API endpoints.

Following TDD methodology: These tests are written BEFORE implementation.
They define the expected behavior of report generation endpoints.
"""

import pytest
from uuid import uuid4
from unittest.mock import Mock, patch, MagicMock

from genreport.core.orchestration.agent_models import AgentOutput


class TestGenerateReportEndpoint:
    """Test POST /api/v1/reports/generate/{project_id} endpoint."""

    @patch("genreport.api.routers.reports.SecureOrchestrator")
    def test_generate_report_success(
        self, mock_orchestrator_class, client, test_project, auth_headers
    ):
        """Successful report generation returns 200 with report data."""
        # Mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.run_all_agents.return_value = {
            "revenue": AgentOutput(
                disclosure_text="Revenue disclosure",
                sources=[],
                confidence_score=0.9,
                completeness_score=0.85,
                warnings=[],
            )
        }
        mock_orchestrator_class.return_value = mock_orchestrator

        # Make request
        response = client.post(
            f"/api/v1/reports/generate/{test_project.id}",
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "report_id" in data
        assert "sections" in data
        assert len(data["sections"]) > 0

    def test_generate_report_requires_authentication(self, client):
        """Endpoint requires authentication."""
        response = client.post("/api/v1/reports/generate/1")

        # Should return 401 Unauthorized
        assert response.status_code == 401

    def test_generate_report_tenant_isolation(
        self, client, test_project, second_tenant_auth_headers
    ):
        """Cannot generate report for other tenant's project."""
        response = client.post(
            f"/api/v1/reports/generate/{test_project.id}",
            headers=second_tenant_auth_headers,
        )

        # Should return 403 Forbidden (different tenant trying to access project)
        assert response.status_code == 403

    def test_generate_report_project_not_found(self, client, auth_headers):
        """Returns 404 if project doesn't exist."""
        response = client.post(
            "/api/v1/reports/generate/999999",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestGetReportEndpoint:
    """Test GET /api/v1/reports/{report_id} endpoint."""

    def test_get_report_success(self, client, db, test_project, test_user, auth_headers):
        """Successful retrieval returns report with sections."""
        from genreport.core.database.models import GeneratedReport

        # Create a real report in the database
        report = GeneratedReport(
            tenant_id=test_project.tenant_id,
            project_id=test_project.id,
            jurisdiction="HK",
            accounting_standard="HKFRS",
            overall_completeness=0.85,
            generation_time_seconds=45.2,
            cost_usd=0.35,
            status="completed",
            generated_by=test_user.id,
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        response = client.get(
            f"/api/v1/reports/{report.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == report.id
        assert data["status"] == "completed"

    def test_get_report_tenant_isolation(
        self, client, db, test_project, test_user, second_tenant, second_tenant_auth_headers
    ):
        """Cannot access other tenant's report."""
        from genreport.core.database.models import GeneratedReport

        # Create report for first tenant
        report = GeneratedReport(
            tenant_id=test_project.tenant_id,
            project_id=test_project.id,
            jurisdiction="HK",
            accounting_standard="HKFRS",
            overall_completeness=0.85,
            generation_time_seconds=45.2,
            cost_usd=0.35,
            status="completed",
            generated_by=test_user.id,
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        # Try to access with second tenant's credentials
        response = client.get(
            f"/api/v1/reports/{report.id}",
            headers=second_tenant_auth_headers,
        )

        assert response.status_code == 403

    def test_get_report_not_found(self, client, auth_headers):
        """Returns 404 if report doesn't exist."""
        response = client.get(
            "/api/v1/reports/999999",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestListProjectReportsEndpoint:
    """Test GET /api/v1/reports/project/{project_id} endpoint."""

    def test_list_project_reports(self, client, db, test_project, test_user, auth_headers):
        """Lists all reports for a project."""
        from genreport.core.database.models import GeneratedReport

        # Create some reports for the project
        report1 = GeneratedReport(
            tenant_id=test_project.tenant_id,
            project_id=test_project.id,
            jurisdiction="HK",
            accounting_standard="HKFRS",
            overall_completeness=0.85,
            generation_time_seconds=45.2,
            cost_usd=0.35,
            status="completed",
            generated_by=test_user.id,
        )
        report2 = GeneratedReport(
            tenant_id=test_project.tenant_id,
            project_id=test_project.id,
            jurisdiction="HK",
            accounting_standard="HKFRS",
            overall_completeness=0.75,
            generation_time_seconds=50.1,
            cost_usd=0.40,
            status="failed",
            generated_by=test_user.id,
        )
        db.add_all([report1, report2])
        db.commit()

        response = client.get(
            f"/api/v1/reports/project/{test_project.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_list_project_reports_tenant_isolation(
        self, client, test_project, second_tenant_auth_headers
    ):
        """Cannot list reports for other tenant's project."""
        response = client.get(
            f"/api/v1/reports/project/{test_project.id}",
            headers=second_tenant_auth_headers,
        )

        assert response.status_code == 403


class TestDeleteReportEndpoint:
    """Test DELETE /api/v1/reports/{report_id} endpoint."""

    def test_delete_report_success(
        self, client, db, test_project, test_admin_user, admin_auth_headers
    ):
        """Successful deletion soft-deletes report."""
        from genreport.core.database.models import GeneratedReport

        # Create a report
        report = GeneratedReport(
            tenant_id=test_project.tenant_id,
            project_id=test_project.id,
            jurisdiction="HK",
            accounting_standard="HKFRS",
            overall_completeness=0.85,
            generation_time_seconds=45.2,
            cost_usd=0.35,
            status="completed",
            generated_by=test_admin_user.id,
            is_deleted=False,
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        response = client.delete(
            f"/api/v1/reports/{report.id}",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        db.refresh(report)
        assert report.is_deleted is True

    def test_delete_report_requires_admin(
        self, client, db, test_project, test_user, auth_headers
    ):
        """Only admins can delete reports."""
        from genreport.core.database.models import GeneratedReport

        # Create a report
        report = GeneratedReport(
            tenant_id=test_project.tenant_id,
            project_id=test_project.id,
            jurisdiction="HK",
            accounting_standard="HKFRS",
            overall_completeness=0.85,
            generation_time_seconds=45.2,
            cost_usd=0.35,
            status="completed",
            generated_by=test_user.id,
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        # Try to delete with non-admin user
        response = client.delete(
            f"/api/v1/reports/{report.id}",
            headers=auth_headers,  # Regular user, not admin
        )

        assert response.status_code == 403

    def test_delete_report_tenant_isolation(
        self, client, db, test_project, test_user, second_tenant_auth_headers
    ):
        """Cannot delete other tenant's report."""
        from genreport.core.database.models import GeneratedReport

        # Create report for first tenant
        report = GeneratedReport(
            tenant_id=test_project.tenant_id,
            project_id=test_project.id,
            jurisdiction="HK",
            accounting_standard="HKFRS",
            overall_completeness=0.85,
            generation_time_seconds=45.2,
            cost_usd=0.35,
            status="completed",
            generated_by=test_user.id,
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        # Try to delete with second tenant's admin credentials
        response = client.delete(
            f"/api/v1/reports/{report.id}",
            headers=second_tenant_auth_headers,
        )

        assert response.status_code == 403
