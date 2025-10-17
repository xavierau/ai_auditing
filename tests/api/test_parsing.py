"""Tests for parsing API endpoints.

Following TDD approach - these tests define expected parsing behavior with security.
"""

import pytest
from io import BytesIO
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4

from genreport.core.database.models import User, Project, FileMetadata


class TestParsingEndpoint:
    """Test suite for parsing endpoint."""

    def test_parse_project_success(
        self, client: TestClient, db: Session, test_user: User, test_project: Project
    ):
        """Test successful parsing initiation."""
        # First upload a file
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "testpassword123"},
        )
        token = login_response.json()["access_token"]

        file = BytesIO(b"PK\x03\x04")
        upload_response = client.post(
            f"/api/v1/files/upload",
            files={"file": ("workbook.xlsx", file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"project_id": test_project.id},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert upload_response.status_code == 200

        # Now trigger parsing
        response = client.post(
            f"/api/v1/parsing/projects/{test_project.id}/parse",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 202  # Accepted (async processing)
        data = response.json()

        assert data["status"] == "parsing_started"
        assert data["project_id"] == test_project.id
        assert "task_id" in data or "message" in data

    def test_parse_requires_authentication(
        self, client: TestClient, test_project: Project
    ):
        """Test that parsing requires authentication."""
        response = client.post(
            f"/api/v1/parsing/projects/{test_project.id}/parse",
        )

        # Tenant middleware returns 403 when no auth token provided
        assert response.status_code == 403

    def test_parse_nonexistent_project(
        self, client: TestClient, db: Session, test_user: User
    ):
        """Test parsing non-existent project fails."""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "testpassword123"},
        )
        token = login_response.json()["access_token"]

        response = client.post(
            f"/api/v1/parsing/projects/99999/parse",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    def test_parse_project_without_file(
        self, client: TestClient, db: Session, test_user: User, test_project: Project
    ):
        """Test parsing project without uploaded file fails."""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "testpassword123"},
        )
        token = login_response.json()["access_token"]

        response = client.post(
            f"/api/v1/parsing/projects/{test_project.id}/parse",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
        assert "file" in response.json()["detail"].lower()

    def test_parse_tenant_isolation(
        self, client: TestClient, db: Session, test_user: User, second_tenant_user: User
    ):
        """Test that users cannot parse other tenant's projects."""
        from genreport.core.database.models import Client, Project
        from datetime import date

        # Create project for second tenant
        second_client = Client(
            tenant_id=second_tenant_user.tenant_id,
            company_name="Second Client",
            contact_email="second@client.com",
        )
        db.add(second_client)
        db.flush()

        second_project = Project(
            tenant_id=second_tenant_user.tenant_id,
            client_id=second_client.id,
            project_name="Second Project",
            jurisdiction="HK",
            financial_year_end=date(2024, 12, 31),
        )
        db.add(second_project)
        db.commit()

        # Login as first tenant user
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "testpassword123"},
        )
        token = login_response.json()["access_token"]

        # Try to parse second tenant's project
        response = client.post(
            f"/api/v1/parsing/projects/{second_project.id}/parse",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404  # Project not found (tenant filter)

    def test_get_parsing_status(
        self, client: TestClient, db: Session, test_user: User, test_project: Project
    ):
        """Test getting parsing status."""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "testpassword123"},
        )
        token = login_response.json()["access_token"]

        response = client.get(
            f"/api/v1/parsing/projects/{test_project.id}/status",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert data["status"] in ["not_started", "parsing", "completed", "failed"]

    def test_get_relationship_map(
        self, client: TestClient, db: Session, test_user: User, test_project: Project
    ):
        """Test getting relationship map after parsing."""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "testpassword123"},
        )
        token = login_response.json()["access_token"]

        response = client.get(
            f"/api/v1/parsing/projects/{test_project.id}/relationship-map",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Should return 404 if not yet parsed, or 200 with map if parsed
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "coding_system" in data
            assert "relationships" in data
