"""Tests for file upload API endpoints.

Following TDD approach - these tests define expected file upload behavior with security.
"""

import pytest
from io import BytesIO
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4

from genreport.core.database.models import User, Tenant, Project, Client


class TestFileUpload:
    """Test suite for secure file upload endpoint."""

    def test_upload_file_success(
        self, client: TestClient, db: Session, test_user: User, test_project: Project
    ):
        """Test successful file upload with encryption."""
        # Login to get token
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "testpassword123"},
        )
        token = login_response.json()["access_token"]

        # Create mock Excel file
        file_content = b"PK\x03\x04"  # ZIP magic bytes (XLSX)
        file = BytesIO(file_content)

        # Upload file
        response = client.post(
            f"/api/v1/files/upload",
            files={"file": ("workbook.xlsx", file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"project_id": test_project.id},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "file_id" in data
        assert data["filename"] == "workbook.xlsx"
        assert "size" in data

    def test_upload_file_requires_authentication(
        self, client: TestClient, test_project: Project
    ):
        """Test that file upload requires authentication."""
        file = BytesIO(b"PK\x03\x04")

        response = client.post(
            f"/api/v1/files/upload",
            files={"file": ("workbook.xlsx", file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"project_id": test_project.id},
        )

        # Tenant middleware returns 403 when no auth token provided
        assert response.status_code == 403

    def test_upload_file_invalid_extension(
        self, client: TestClient, db: Session, test_user: User, test_project: Project
    ):
        """Test that invalid file extensions are rejected."""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "testpassword123"},
        )
        token = login_response.json()["access_token"]

        # Try to upload .exe file
        file = BytesIO(b"MZ\x90\x00")  # EXE magic bytes

        response = client.post(
            f"/api/v1/files/upload",
            files={"file": ("malicious.exe", file, "application/octet-stream")},
            data={"project_id": test_project.id},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
        assert "extension" in response.json()["detail"].lower()

    def test_upload_file_size_limit(
        self, client: TestClient, db: Session, test_user: User, test_project: Project
    ):
        """Test that files exceeding 50MB are rejected."""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "testpassword123"},
        )
        token = login_response.json()["access_token"]

        # Create file larger than 50MB with proper XLSX magic bytes
        # XLSX files start with PK (ZIP header)
        large_file = BytesIO(b"PK\x03\x04" + b"X" * (51 * 1024 * 1024 - 4))  # 51MB

        response = client.post(
            f"/api/v1/files/upload",
            files={"file": ("large.xlsx", large_file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"project_id": test_project.id},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
        assert "too large" in response.json()["detail"].lower()

    def test_upload_file_creates_audit_log(
        self, client: TestClient, db: Session, test_user: User, test_project: Project
    ):
        """Test that file upload creates audit log entry."""
        from genreport.core.database.models import AuditLog

        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "testpassword123"},
        )
        token = login_response.json()["access_token"]

        file = BytesIO(b"PK\x03\x04")

        response = client.post(
            f"/api/v1/files/upload",
            files={"file": ("workbook.xlsx", file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"project_id": test_project.id},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200

        # Check audit log
        audit_log = (
            db.query(AuditLog)
            .filter(
                AuditLog.tenant_id == test_user.tenant_id,
                AuditLog.event_type == "FILE_UPLOAD",
                AuditLog.action == "CREATE",
            )
            .first()
        )

        assert audit_log is not None
        assert audit_log.user_id == test_user.id

    def test_upload_file_tenant_isolation(
        self, client: TestClient, db: Session, test_user: User
    ):
        """Test that users cannot upload files to other tenant's projects."""
        # Create another tenant and project
        other_tenant = Tenant(
            company_name="Other Tenant",
            data_residency_region="HK",
            jurisdiction="HK",
            is_active=True,
        )
        db.add(other_tenant)
        db.flush()

        other_client_obj = Client(
            tenant_id=other_tenant.id,
            company_name="Other Client",
            contact_email="other@example.com",
        )
        db.add(other_client_obj)
        db.flush()

        from datetime import date

        other_project = Project(
            tenant_id=other_tenant.id,
            client_id=other_client_obj.id,
            project_name="Other Project",
            jurisdiction="HK",
            financial_year_end=date(2024, 12, 31),
        )
        db.add(other_project)
        db.commit()

        # Login as test_user (different tenant)
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "testpassword123"},
        )
        token = login_response.json()["access_token"]

        file = BytesIO(b"PK\x03\x04")

        # Try to upload to other tenant's project
        response = client.post(
            f"/api/v1/files/upload",
            files={"file": ("workbook.xlsx", file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"project_id": other_project.id},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404  # Project not found (due to tenant filter)

    def test_upload_file_nonexistent_project(
        self, client: TestClient, db: Session, test_user: User
    ):
        """Test that uploading to non-existent project fails."""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "testpassword123"},
        )
        token = login_response.json()["access_token"]

        file = BytesIO(b"PK\x03\x04")

        response = client.post(
            f"/api/v1/files/upload",
            files={"file": ("workbook.xlsx", file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"project_id": 99999},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404


class TestFileDownload:
    """Test suite for file download endpoint."""

    def test_download_file_success(
        self, client: TestClient, db: Session, test_user: User, test_project: Project
    ):
        """Test successful file download with decryption."""
        # First upload a file
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "testpassword123"},
        )
        token = login_response.json()["access_token"]

        file_content = b"PK\x03\x04test content"
        file = BytesIO(file_content)

        upload_response = client.post(
            f"/api/v1/files/upload",
            files={"file": ("workbook.xlsx", file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"project_id": test_project.id},
            headers={"Authorization": f"Bearer {token}"},
        )

        file_id = upload_response.json()["file_id"]

        # Download file
        download_response = client.get(
            f"/api/v1/files/{file_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert download_response.status_code == 200
        assert download_response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    def test_download_file_tenant_isolation(
        self, client: TestClient, db: Session, test_user: User, test_project: Project
    ):
        """Test that users cannot download files from other tenants."""
        # Upload file as test_user
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
        file_id = upload_response.json()["file_id"]

        # Create another user in different tenant
        from genreport.core.security.jwt_service import hash_password

        other_tenant = Tenant(
            company_name="Other Tenant",
            data_residency_region="HK",
            jurisdiction="HK",
            is_active=True,
        )
        db.add(other_tenant)
        db.flush()

        other_user = User(
            tenant_id=other_tenant.id,
            email="other@example.com",
            password_hash=hash_password("testpassword123"),
            full_name="Other User",
            role="admin",
            is_active=True,
        )
        db.add(other_user)
        db.commit()

        # Login as other user
        other_login = client.post(
            "/api/v1/auth/login",
            json={"email": other_user.email, "password": "testpassword123"},
        )
        other_token = other_login.json()["access_token"]

        # Try to download file from different tenant
        download_response = client.get(
            f"/api/v1/files/{file_id}",
            headers={"Authorization": f"Bearer {other_token}"},
        )

        assert download_response.status_code == 404  # File not found (due to tenant filter)


class TestFileList:
    """Test suite for listing files."""

    def test_list_project_files(
        self, client: TestClient, db: Session, test_user: User, test_project: Project
    ):
        """Test listing files for a project."""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "testpassword123"},
        )
        token = login_response.json()["access_token"]

        # Upload multiple files
        for i in range(3):
            file = BytesIO(b"PK\x03\x04")
            client.post(
                f"/api/v1/files/upload",
                files={"file": (f"workbook{i}.xlsx", file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={"project_id": test_project.id},
                headers={"Authorization": f"Bearer {token}"},
            )

        # List files
        response = client.get(
            f"/api/v1/files/project/{test_project.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["files"]) == 3
        assert all("file_id" in f for f in data["files"])
        assert all("filename" in f for f in data["files"])
