"""Tests for Report Generation API endpoints.

Following TDD methodology: These tests are written BEFORE implementation.
They define the expected behavior of report generation endpoints.
"""

import pytest
from uuid import uuid4
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

from genreport.api.main import app
from genreport.core.orchestration.agent_models import AgentOutput


client = TestClient(app)


class TestGenerateReportEndpoint:
    """Test POST /api/v1/reports/generate/{project_id} endpoint."""

    @patch("genreport.api.routers.reports.get_current_tenant")
    @patch("genreport.api.routers.reports.get_current_user")
    @patch("genreport.api.routers.reports.get_db")
    @patch("genreport.api.routers.reports.SecureOrchestrator")
    def test_generate_report_success(
        self, mock_orchestrator_class, mock_get_db, mock_get_user, mock_get_tenant
    ):
        """Successful report generation returns 200 with report data."""
        # Setup mocks
        tenant_id = uuid4()
        user_id = 123
        project_id = 1

        mock_get_tenant.return_value = tenant_id
        mock_get_user.return_value = Mock(id=user_id)
        mock_get_db.return_value = Mock()

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
            f"/api/v1/reports/generate/{project_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "report_id" in data
        assert "sections" in data
        assert len(data["sections"]) > 0

    @patch("genreport.api.routers.reports.get_current_tenant")
    @patch("genreport.api.routers.reports.get_current_user")
    def test_generate_report_requires_authentication(
        self, mock_get_user, mock_get_tenant
    ):
        """Endpoint requires authentication."""
        mock_get_user.side_effect = Exception("Unauthorized")

        response = client.post("/api/v1/reports/generate/1")

        # Should return 401 or similar
        assert response.status_code in [401, 403, 500]

    @patch("genreport.api.routers.reports.get_current_tenant")
    @patch("genreport.api.routers.reports.get_current_user")
    @patch("genreport.api.routers.reports.get_db")
    def test_generate_report_tenant_isolation(
        self, mock_get_db, mock_get_user, mock_get_tenant
    ):
        """Cannot generate report for other tenant's project."""
        tenant_id = uuid4()
        mock_get_tenant.return_value = tenant_id
        mock_get_user.return_value = Mock(id=123)

        # Mock database to return project with different tenant
        mock_db = Mock()
        mock_project = Mock()
        mock_project.tenant_id = uuid4()  # Different tenant
        mock_db.query().filter().first.return_value = mock_project
        mock_get_db.return_value = mock_db

        response = client.post(
            "/api/v1/reports/generate/1",
            headers={"Authorization": "Bearer test-token"},
        )

        # Should return 403 Forbidden
        assert response.status_code == 403

    @patch("genreport.api.routers.reports.get_current_tenant")
    @patch("genreport.api.routers.reports.get_current_user")
    @patch("genreport.api.routers.reports.get_db")
    def test_generate_report_project_not_found(
        self, mock_get_db, mock_get_user, mock_get_tenant
    ):
        """Returns 404 if project doesn't exist."""
        mock_get_tenant.return_value = uuid4()
        mock_get_user.return_value = Mock(id=123)

        # Mock database to return None
        mock_db = Mock()
        mock_db.query().filter().first.return_value = None
        mock_get_db.return_value = mock_db

        response = client.post(
            "/api/v1/reports/generate/999",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 404


class TestGetReportEndpoint:
    """Test GET /api/v1/reports/{report_id} endpoint."""

    @patch("genreport.api.routers.reports.get_current_tenant")
    @patch("genreport.api.routers.reports.get_current_user")
    @patch("genreport.api.routers.reports.get_db")
    def test_get_report_success(self, mock_get_db, mock_get_user, mock_get_tenant):
        """Successful retrieval returns report with sections."""
        tenant_id = uuid4()
        mock_get_tenant.return_value = tenant_id
        mock_get_user.return_value = Mock(id=123)

        # Mock database
        mock_db = Mock()
        mock_report = Mock()
        mock_report.id = 1
        mock_report.tenant_id = tenant_id
        mock_report.status = "completed"
        mock_report.sections = []
        mock_db.query().filter().first.return_value = mock_report
        mock_get_db.return_value = mock_db

        response = client.get(
            "/api/v1/reports/1",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["status"] == "completed"

    @patch("genreport.api.routers.reports.get_current_tenant")
    @patch("genreport.api.routers.reports.get_current_user")
    @patch("genreport.api.routers.reports.get_db")
    def test_get_report_tenant_isolation(
        self, mock_get_db, mock_get_user, mock_get_tenant
    ):
        """Cannot access other tenant's report."""
        tenant_id = uuid4()
        mock_get_tenant.return_value = tenant_id
        mock_get_user.return_value = Mock(id=123)

        # Mock database to return report with different tenant
        mock_db = Mock()
        mock_report = Mock()
        mock_report.tenant_id = uuid4()  # Different tenant
        mock_db.query().filter().first.return_value = mock_report
        mock_get_db.return_value = mock_db

        response = client.get(
            "/api/v1/reports/1",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 403

    @patch("genreport.api.routers.reports.get_current_tenant")
    @patch("genreport.api.routers.reports.get_current_user")
    @patch("genreport.api.routers.reports.get_db")
    def test_get_report_not_found(self, mock_get_db, mock_get_user, mock_get_tenant):
        """Returns 404 if report doesn't exist."""
        mock_get_tenant.return_value = uuid4()
        mock_get_user.return_value = Mock(id=123)

        # Mock database to return None
        mock_db = Mock()
        mock_db.query().filter().first.return_value = None
        mock_get_db.return_value = mock_db

        response = client.get(
            "/api/v1/reports/999",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 404


class TestListProjectReportsEndpoint:
    """Test GET /api/v1/reports/project/{project_id} endpoint."""

    @patch("genreport.api.routers.reports.get_current_tenant")
    @patch("genreport.api.routers.reports.get_current_user")
    @patch("genreport.api.routers.reports.get_db")
    def test_list_project_reports(self, mock_get_db, mock_get_user, mock_get_tenant):
        """Lists all reports for a project."""
        tenant_id = uuid4()
        mock_get_tenant.return_value = tenant_id
        mock_get_user.return_value = Mock(id=123)

        # Mock database
        mock_db = Mock()
        mock_project = Mock()
        mock_project.tenant_id = tenant_id
        mock_db.query().filter().first.return_value = mock_project

        # Mock reports query
        mock_reports = [Mock(id=1, status="completed"), Mock(id=2, status="failed")]
        mock_db.query().filter().all.return_value = mock_reports
        mock_get_db.return_value = mock_db

        response = client.get(
            "/api/v1/reports/project/1",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    @patch("genreport.api.routers.reports.get_current_tenant")
    @patch("genreport.api.routers.reports.get_current_user")
    @patch("genreport.api.routers.reports.get_db")
    def test_list_project_reports_tenant_isolation(
        self, mock_get_db, mock_get_user, mock_get_tenant
    ):
        """Cannot list reports for other tenant's project."""
        tenant_id = uuid4()
        mock_get_tenant.return_value = tenant_id
        mock_get_user.return_value = Mock(id=123)

        # Mock database - project belongs to different tenant
        mock_db = Mock()
        mock_project = Mock()
        mock_project.tenant_id = uuid4()  # Different tenant
        mock_db.query().filter().first.return_value = mock_project
        mock_get_db.return_value = mock_db

        response = client.get(
            "/api/v1/reports/project/1",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 403


class TestDeleteReportEndpoint:
    """Test DELETE /api/v1/reports/{report_id} endpoint."""

    @patch("genreport.api.routers.reports.get_current_tenant")
    @patch("genreport.api.routers.reports.get_current_user")
    @patch("genreport.api.routers.reports.get_db")
    def test_delete_report_success(self, mock_get_db, mock_get_user, mock_get_tenant):
        """Successful deletion soft-deletes report."""
        tenant_id = uuid4()
        mock_get_tenant.return_value = tenant_id
        mock_get_user.return_value = Mock(id=123, is_admin=True)

        # Mock database
        mock_db = Mock()
        mock_report = Mock()
        mock_report.id = 1
        mock_report.tenant_id = tenant_id
        mock_report.is_deleted = False
        mock_db.query().filter().first.return_value = mock_report
        mock_get_db.return_value = mock_db

        response = client.delete(
            "/api/v1/reports/1",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        assert mock_report.is_deleted is True

    @patch("genreport.api.routers.reports.get_current_tenant")
    @patch("genreport.api.routers.reports.get_current_user")
    @patch("genreport.api.routers.reports.get_db")
    def test_delete_report_requires_admin(
        self, mock_get_db, mock_get_user, mock_get_tenant
    ):
        """Only admins can delete reports."""
        tenant_id = uuid4()
        mock_get_tenant.return_value = tenant_id
        mock_get_user.return_value = Mock(id=123, is_admin=False)  # Not admin

        # Mock database
        mock_db = Mock()
        mock_report = Mock()
        mock_report.tenant_id = tenant_id
        mock_db.query().filter().first.return_value = mock_report
        mock_get_db.return_value = mock_db

        response = client.delete(
            "/api/v1/reports/1",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 403

    @patch("genreport.api.routers.reports.get_current_tenant")
    @patch("genreport.api.routers.reports.get_current_user")
    @patch("genreport.api.routers.reports.get_db")
    def test_delete_report_tenant_isolation(
        self, mock_get_db, mock_get_user, mock_get_tenant
    ):
        """Cannot delete other tenant's report."""
        tenant_id = uuid4()
        mock_get_tenant.return_value = tenant_id
        mock_get_user.return_value = Mock(id=123, is_admin=True)

        # Mock database - report belongs to different tenant
        mock_db = Mock()
        mock_report = Mock()
        mock_report.tenant_id = uuid4()  # Different tenant
        mock_db.query().filter().first.return_value = mock_report
        mock_get_db.return_value = mock_db

        response = client.delete(
            "/api/v1/reports/1",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 403
