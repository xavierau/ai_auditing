"""Tests for projects API endpoints.

Tests cover:
- Client CRUD operations
- Project CRUD operations
- Tenant isolation
- Role-based access control
- Audit logging
- Validation rules
"""

import pytest
from datetime import date

from genreport.core.database.models import AuditLog, Client, Project


class TestClientEndpoints:
    """Test client management endpoints."""

    def test_create_client_success(self, client, db, auth_headers, test_tenant):
        """Auditor should be able to create a client."""
        response = client.post(
            "/api/v1/projects/clients",
            headers=auth_headers,
            json={
                "company_name": "New Client Ltd",
                "registration_number": "12345678",
                "address": "123 Test St, Hong Kong",
                "industry": "Technology",
                "contact_person": "John Doe",
                "contact_email": "john@newclient.com",
                "contact_phone": "+852 1234 5678",
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["company_name"] == "New Client Ltd"
        assert data["registration_number"] == "12345678"
        assert data["industry"] == "Technology"
        assert "id" in data

        # Verify client in database
        db_client = db.query(Client).filter(Client.id == data["id"]).first()
        assert db_client is not None
        assert db_client.tenant_id == test_tenant.id
        assert db_client.company_name == "New Client Ltd"

    def test_create_client_requires_auth(self, client, db):
        """Creating a client requires authentication."""
        response = client.post(
            "/api/v1/projects/clients",
            json={"company_name": "Test Client"},
        )

        # HTTPBearer returns 403 when no credentials provided
        assert response.status_code == 403

    def test_create_client_creates_audit_log(
        self, client, db, auth_headers, test_user, test_tenant
    ):
        """Creating a client should create audit log."""
        # Clear existing audit logs
        db.query(AuditLog).delete()
        db.commit()

        response = client.post(
            "/api/v1/projects/clients",
            headers=auth_headers,
            json={
                "company_name": "Audit Test Client",
                "industry": "Finance",
            },
        )

        assert response.status_code == 201
        client_id = response.json()["id"]

        # Check audit log
        audit_logs = db.query(AuditLog).all()
        assert len(audit_logs) == 1
        assert audit_logs[0].event_type == "DATA_ACCESS"
        assert audit_logs[0].action == "CREATE"
        assert audit_logs[0].resource_type == "client"
        assert audit_logs[0].resource_id == client_id
        assert audit_logs[0].user_id == test_user.id
        assert audit_logs[0].tenant_id == test_tenant.id

    def test_list_clients_success(self, client, db, auth_headers, test_tenant):
        """Should list all clients for current tenant."""
        # Create test clients
        client1 = Client(tenant_id=test_tenant.id, company_name="Client A")
        client2 = Client(tenant_id=test_tenant.id, company_name="Client B")
        db.add_all([client1, client2])
        db.commit()

        response = client.get(
            "/api/v1/projects/clients",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        company_names = [c["company_name"] for c in data]
        assert "Client A" in company_names
        assert "Client B" in company_names

    def test_list_clients_pagination(self, client, db, auth_headers, test_tenant):
        """Should support pagination."""
        # Create 10 test clients
        for i in range(10):
            db.add(Client(tenant_id=test_tenant.id, company_name=f"Client {i}"))
        db.commit()

        # Get first page
        response = client.get(
            "/api/v1/projects/clients?skip=0&limit=5",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

        # Get second page
        response = client.get(
            "/api/v1/projects/clients?skip=5&limit=5",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5


class TestProjectEndpoints:
    """Test project management endpoints."""

    def test_create_project_success(
        self, client, db, auth_headers, test_tenant, test_user
    ):
        """Auditor should be able to create a project."""
        # Create client first
        db_client = Client(tenant_id=test_tenant.id, company_name="Test Client")
        db.add(db_client)
        db.commit()
        db.refresh(db_client)

        response = client.post(
            "/api/v1/projects/",
            headers=auth_headers,
            json={
                "client_id": db_client.id,
                "jurisdiction": "HK",
                "accounting_standard": "HKFRS",
                "financial_year_end": "2024-12-31",
                "project_name": "FY2024 Audit",
                "directors_names": ["Alice Wong", "Bob Chan"],
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["client_id"] == db_client.id
        assert data["jurisdiction"] == "HK"
        assert data["accounting_standard"] == "HKFRS"
        assert data["financial_year_end"] == "2024-12-31"
        assert data["project_name"] == "FY2024 Audit"
        assert data["status"] == "draft"

        # Verify in database
        db_project = db.query(Project).filter(Project.id == data["id"]).first()
        assert db_project is not None
        assert db_project.tenant_id == test_tenant.id
        assert db_project.user_id == test_user.id
        assert db_project.directors_names == ["Alice Wong", "Bob Chan"]

    def test_create_project_invalid_client(self, client, db, auth_headers):
        """Creating a project with non-existent client should fail."""
        response = client.post(
            "/api/v1/projects/",
            headers=auth_headers,
            json={
                "client_id": 99999,
                "jurisdiction": "HK",
                "accounting_standard": "HKFRS",
                "financial_year_end": "2024-12-31",
            },
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Client not found"

    def test_create_project_client_from_other_tenant(
        self, client, db, auth_headers, second_tenant
    ):
        """Cannot create project for client from another tenant."""
        # Create client in second tenant
        other_client = Client(tenant_id=second_tenant.id, company_name="Other Client")
        db.add(other_client)
        db.commit()

        response = client.post(
            "/api/v1/projects/",
            headers=auth_headers,
            json={
                "client_id": other_client.id,
                "jurisdiction": "HK",
                "accounting_standard": "HKFRS",
                "financial_year_end": "2024-12-31",
            },
        )

        # Should fail because client doesn't belong to user's tenant
        assert response.status_code == 404
        assert response.json()["detail"] == "Client not found"

    def test_create_project_invalid_jurisdiction(
        self, client, db, auth_headers, test_tenant
    ):
        """Creating a project with invalid jurisdiction should fail."""
        # Create client
        db_client = Client(tenant_id=test_tenant.id, company_name="Test Client")
        db.add(db_client)
        db.commit()

        response = client.post(
            "/api/v1/projects/",
            headers=auth_headers,
            json={
                "client_id": db_client.id,
                "jurisdiction": "INVALID",
                "accounting_standard": "HKFRS",
                "financial_year_end": "2024-12-31",
            },
        )

        assert response.status_code == 400
        assert "Invalid jurisdiction" in response.json()["detail"]

    def test_create_project_creates_audit_log(
        self, client, db, auth_headers, test_tenant, test_user
    ):
        """Creating a project should create audit log."""
        # Create client
        db_client = Client(tenant_id=test_tenant.id, company_name="Test Client")
        db.add(db_client)
        db.commit()

        # Clear existing audit logs
        db.query(AuditLog).delete()
        db.commit()

        response = client.post(
            "/api/v1/projects/",
            headers=auth_headers,
            json={
                "client_id": db_client.id,
                "jurisdiction": "HK",
                "accounting_standard": "HKFRS",
                "financial_year_end": "2024-12-31",
            },
        )

        assert response.status_code == 201
        project_id = response.json()["id"]

        # Check audit log
        audit_logs = db.query(AuditLog).all()
        assert len(audit_logs) == 1
        assert audit_logs[0].event_type == "DATA_ACCESS"
        assert audit_logs[0].action == "CREATE"
        assert audit_logs[0].resource_type == "project"
        assert audit_logs[0].resource_id == project_id
        assert audit_logs[0].user_id == test_user.id
        assert audit_logs[0].tenant_id == test_tenant.id

    def test_list_projects_success(
        self, client, db, auth_headers, test_tenant, test_user
    ):
        """Should list all projects for current tenant."""
        # Create client
        db_client = Client(tenant_id=test_tenant.id, company_name="Test Client")
        db.add(db_client)
        db.flush()

        # Create test projects
        project1 = Project(
            tenant_id=test_tenant.id,
            client_id=db_client.id,
            user_id=test_user.id,
            jurisdiction="HK",
            accounting_standard="HKFRS",
            financial_year_end=date(2024, 12, 31),
            project_name="Project A",
        )
        project2 = Project(
            tenant_id=test_tenant.id,
            client_id=db_client.id,
            user_id=test_user.id,
            jurisdiction="HK",
            accounting_standard="HKFRS",
            financial_year_end=date(2024, 12, 31),
            project_name="Project B",
        )
        db.add_all([project1, project2])
        db.commit()

        response = client.get(
            "/api/v1/projects/",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        project_names = [p["project_name"] for p in data]
        assert "Project A" in project_names
        assert "Project B" in project_names

    def test_list_projects_filter_by_status(
        self, client, db, auth_headers, test_tenant, test_user
    ):
        """Should filter projects by status."""
        # Create client
        db_client = Client(tenant_id=test_tenant.id, company_name="Test Client")
        db.add(db_client)
        db.flush()

        # Create projects with different statuses
        draft_project = Project(
            tenant_id=test_tenant.id,
            client_id=db_client.id,
            user_id=test_user.id,
            jurisdiction="HK",
            accounting_standard="HKFRS",
            financial_year_end=date(2024, 12, 31),
            status="draft",
        )
        completed_project = Project(
            tenant_id=test_tenant.id,
            client_id=db_client.id,
            user_id=test_user.id,
            jurisdiction="HK",
            accounting_standard="HKFRS",
            financial_year_end=date(2024, 12, 31),
            status="completed",
        )
        db.add_all([draft_project, completed_project])
        db.commit()

        # Filter by draft
        response = client.get(
            "/api/v1/projects/?status_filter=draft",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "draft"

    def test_get_project_success(
        self, client, db, auth_headers, test_tenant, test_user
    ):
        """Should get project by ID."""
        # Create client and project
        db_client = Client(tenant_id=test_tenant.id, company_name="Test Client")
        db.add(db_client)
        db.flush()

        project = Project(
            tenant_id=test_tenant.id,
            client_id=db_client.id,
            user_id=test_user.id,
            jurisdiction="HK",
            accounting_standard="HKFRS",
            financial_year_end=date(2024, 12, 31),
            project_name="Test Project",
        )
        db.add(project)
        db.commit()
        db.refresh(project)

        response = client.get(
            f"/api/v1/projects/{project.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project.id
        assert data["project_name"] == "Test Project"

    def test_get_project_creates_audit_log(
        self, client, db, auth_headers, test_tenant, test_user
    ):
        """Getting a project should create audit log."""
        # Create client and project
        db_client = Client(tenant_id=test_tenant.id, company_name="Test Client")
        db.add(db_client)
        db.flush()

        project = Project(
            tenant_id=test_tenant.id,
            client_id=db_client.id,
            user_id=test_user.id,
            jurisdiction="HK",
            accounting_standard="HKFRS",
            financial_year_end=date(2024, 12, 31),
        )
        db.add(project)
        db.commit()

        # Clear audit logs
        db.query(AuditLog).delete()
        db.commit()

        response = client.get(
            f"/api/v1/projects/{project.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200

        # Check audit log
        audit_logs = db.query(AuditLog).all()
        assert len(audit_logs) == 1
        assert audit_logs[0].action == "READ"
        assert audit_logs[0].resource_type == "project"
        assert audit_logs[0].resource_id == project.id

    def test_get_project_not_found(self, client, db, auth_headers):
        """Getting non-existent project should return 404."""
        response = client.get(
            "/api/v1/projects/99999",
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Project not found"

    def test_delete_project_success(
        self, client, db, auth_headers, test_tenant, test_user
    ):
        """Auditor should be able to delete a project."""
        # Create client and project
        db_client = Client(tenant_id=test_tenant.id, company_name="Test Client")
        db.add(db_client)
        db.flush()

        project = Project(
            tenant_id=test_tenant.id,
            client_id=db_client.id,
            user_id=test_user.id,
            jurisdiction="HK",
            accounting_standard="HKFRS",
            financial_year_end=date(2024, 12, 31),
        )
        db.add(project)
        db.commit()
        project_id = project.id

        response = client.delete(
            f"/api/v1/projects/{project_id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify project is deleted
        deleted_project = db.query(Project).filter(Project.id == project_id).first()
        assert deleted_project is None

    def test_delete_project_creates_audit_log(
        self, client, db, auth_headers, test_tenant, test_user
    ):
        """Deleting a project should create audit log."""
        # Create client and project
        db_client = Client(tenant_id=test_tenant.id, company_name="Test Client")
        db.add(db_client)
        db.flush()

        project = Project(
            tenant_id=test_tenant.id,
            client_id=db_client.id,
            user_id=test_user.id,
            jurisdiction="HK",
            accounting_standard="HKFRS",
            financial_year_end=date(2024, 12, 31),
        )
        db.add(project)
        db.commit()
        project_id = project.id

        # Clear audit logs
        db.query(AuditLog).delete()
        db.commit()

        response = client.delete(
            f"/api/v1/projects/{project_id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Check audit log (created before deletion)
        audit_logs = db.query(AuditLog).all()
        assert len(audit_logs) == 1
        assert audit_logs[0].action == "DELETE"
        assert audit_logs[0].resource_type == "project"
        assert audit_logs[0].resource_id == project_id

    def test_delete_project_not_found(self, client, db, auth_headers):
        """Deleting non-existent project should return 404."""
        response = client.delete(
            "/api/v1/projects/99999",
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Project not found"


class TestRoleBasedAccessControl:
    """Test RBAC for project endpoints."""

    def test_viewer_cannot_create_client(self, client, db, test_tenant):
        """Viewer role should not be able to create clients."""
        from genreport.core.database.models import User
        from genreport.core.security.jwt_service import create_access_token, hash_password

        # Create viewer user
        viewer = User(
            tenant_id=test_tenant.id,
            email="viewer@example.com",
            password_hash=hash_password("password123"),
            full_name="Viewer User",
            role="viewer",
            is_active=True,
        )
        db.add(viewer)
        db.commit()

        # Get viewer token
        viewer_token = create_access_token(viewer.id, viewer.tenant_id, viewer.role)
        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

        response = client.post(
            "/api/v1/projects/clients",
            headers=viewer_headers,
            json={"company_name": "Test Client"},
        )

        # Should be forbidden (403) because viewer doesn't have auditor role
        assert response.status_code == 403

    def test_viewer_cannot_create_project(self, client, db, test_tenant):
        """Viewer role should not be able to create projects."""
        from genreport.core.database.models import User
        from genreport.core.security.jwt_service import create_access_token, hash_password

        # Create viewer user
        viewer = User(
            tenant_id=test_tenant.id,
            email="viewer@example.com",
            password_hash=hash_password("password123"),
            full_name="Viewer User",
            role="viewer",
            is_active=True,
        )
        db.add(viewer)
        db.commit()

        # Create client
        db_client = Client(tenant_id=test_tenant.id, company_name="Test Client")
        db.add(db_client)
        db.commit()

        # Get viewer token
        viewer_token = create_access_token(viewer.id, viewer.tenant_id, viewer.role)
        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

        response = client.post(
            "/api/v1/projects/",
            headers=viewer_headers,
            json={
                "client_id": db_client.id,
                "jurisdiction": "HK",
                "accounting_standard": "HKFRS",
                "financial_year_end": "2024-12-31",
            },
        )

        assert response.status_code == 403

    def test_viewer_cannot_delete_project(
        self, client, db, test_tenant, test_user
    ):
        """Viewer role should not be able to delete projects."""
        from genreport.core.database.models import User
        from genreport.core.security.jwt_service import create_access_token, hash_password

        # Create viewer user
        viewer = User(
            tenant_id=test_tenant.id,
            email="viewer@example.com",
            password_hash=hash_password("password123"),
            full_name="Viewer User",
            role="viewer",
            is_active=True,
        )
        db.add(viewer)
        db.commit()

        # Create project
        db_client = Client(tenant_id=test_tenant.id, company_name="Test Client")
        db.add(db_client)
        db.flush()

        project = Project(
            tenant_id=test_tenant.id,
            client_id=db_client.id,
            user_id=test_user.id,
            jurisdiction="HK",
            accounting_standard="HKFRS",
            financial_year_end=date(2024, 12, 31),
        )
        db.add(project)
        db.commit()

        # Get viewer token
        viewer_token = create_access_token(viewer.id, viewer.tenant_id, viewer.role)
        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

        response = client.delete(
            f"/api/v1/projects/{project.id}",
            headers=viewer_headers,
        )

        assert response.status_code == 403

    def test_auditor_can_create_and_delete(
        self, client, db, auth_headers, test_tenant, test_user
    ):
        """Auditor role should be able to create and delete."""
        # Create client
        response = client.post(
            "/api/v1/projects/clients",
            headers=auth_headers,
            json={"company_name": "Test Client"},
        )
        assert response.status_code == 201

        # Create project
        db_client = Client(tenant_id=test_tenant.id, company_name="Test Client 2")
        db.add(db_client)
        db.commit()

        response = client.post(
            "/api/v1/projects/",
            headers=auth_headers,
            json={
                "client_id": db_client.id,
                "jurisdiction": "HK",
                "accounting_standard": "HKFRS",
                "financial_year_end": "2024-12-31",
            },
        )
        assert response.status_code == 201
        project_id = response.json()["id"]

        # Delete project
        response = client.delete(
            f"/api/v1/projects/{project_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204
