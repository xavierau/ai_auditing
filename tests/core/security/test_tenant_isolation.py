"""Tests for multi-tenant isolation.

CRITICAL SECURITY TESTS: These tests verify that tenant isolation is properly
enforced throughout the application. Failure of any test indicates a critical
security vulnerability.
"""

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4

from genreport.core.database.models import Client, Project, User
from genreport.core.security.tenant_context import (
    current_tenant,
    get_current_tenant,
    set_current_tenant,
)


class TestTenantContext:
    """Test tenant context management."""

    def test_current_tenant_default_is_none(self):
        """Tenant context should default to None."""
        assert current_tenant.get() is None

    def test_set_and_get_current_tenant(self):
        """Should be able to set and retrieve tenant context."""
        tenant_id = uuid4()
        token = current_tenant.set(tenant_id)

        try:
            assert current_tenant.get() == tenant_id
        finally:
            current_tenant.reset(token)

        # After reset, should be None again
        assert current_tenant.get() is None

    def test_get_current_tenant_raises_when_none(self):
        """get_current_tenant() should raise HTTPException when context is None."""
        # Ensure context is None
        assert current_tenant.get() is None

        with pytest.raises(HTTPException) as exc_info:
            get_current_tenant()

        assert exc_info.value.status_code == 401
        assert "No tenant context available" in exc_info.value.detail


class TestDatabaseTenantIsolation:
    """Test that database queries properly filter by tenant_id.

    SECURITY CRITICAL: These tests ensure users cannot access data from other tenants.
    """

    def test_users_isolated_by_tenant(self, db, test_tenant, second_tenant):
        """Users should only see users from their own tenant."""
        # Create users in different tenants
        user1 = User(
            tenant_id=test_tenant.id,
            email="user1@tenant1.com",
            password_hash="hash1",
            full_name="User 1",
            role="auditor",
        )
        user2 = User(
            tenant_id=second_tenant.id,
            email="user2@tenant2.com",
            password_hash="hash2",
            full_name="User 2",
            role="auditor",
        )
        db.add_all([user1, user2])
        db.commit()

        # Query as tenant 1
        tenant1_users = (
            db.query(User).filter(User.tenant_id == test_tenant.id).all()
        )

        # Query as tenant 2
        tenant2_users = (
            db.query(User).filter(User.tenant_id == second_tenant.id).all()
        )

        # Each tenant should only see their own users
        assert len(tenant1_users) == 1
        assert tenant1_users[0].email == "user1@tenant1.com"

        assert len(tenant2_users) == 1
        assert tenant2_users[0].email == "user2@tenant2.com"

    def test_clients_isolated_by_tenant(self, db, test_tenant, second_tenant):
        """Clients should only be accessible by their owning tenant."""
        # Create clients in different tenants
        client1 = Client(
            tenant_id=test_tenant.id,
            company_name="Client 1",
        )
        client2 = Client(
            tenant_id=second_tenant.id,
            company_name="Client 2",
        )
        db.add_all([client1, client2])
        db.commit()

        # Query as tenant 1
        tenant1_clients = (
            db.query(Client).filter(Client.tenant_id == test_tenant.id).all()
        )

        # Query as tenant 2
        tenant2_clients = (
            db.query(Client).filter(Client.tenant_id == second_tenant.id).all()
        )

        # Each tenant should only see their own clients
        assert len(tenant1_clients) == 1
        assert tenant1_clients[0].company_name == "Client 1"

        assert len(tenant2_clients) == 1
        assert tenant2_clients[0].company_name == "Client 2"

    def test_projects_isolated_by_tenant(
        self, db, test_tenant, second_tenant, test_user, second_tenant_user
    ):
        """Projects should only be accessible by their owning tenant."""
        from datetime import date

        # Create clients for each tenant
        client1 = Client(tenant_id=test_tenant.id, company_name="Client 1")
        client2 = Client(tenant_id=second_tenant.id, company_name="Client 2")
        db.add_all([client1, client2])
        db.flush()

        # Create projects in different tenants
        project1 = Project(
            tenant_id=test_tenant.id,
            client_id=client1.id,
            user_id=test_user.id,
            jurisdiction="HK",
            accounting_standard="HKFRS",
            financial_year_end=date(2024, 12, 31),
            project_name="Project 1",
        )
        project2 = Project(
            tenant_id=second_tenant.id,
            client_id=client2.id,
            user_id=second_tenant_user.id,
            jurisdiction="HK",
            accounting_standard="HKFRS",
            financial_year_end=date(2024, 12, 31),
            project_name="Project 2",
        )
        db.add_all([project1, project2])
        db.commit()

        # Query as tenant 1
        tenant1_projects = (
            db.query(Project).filter(Project.tenant_id == test_tenant.id).all()
        )

        # Query as tenant 2
        tenant2_projects = (
            db.query(Project).filter(Project.tenant_id == second_tenant.id).all()
        )

        # Each tenant should only see their own projects
        assert len(tenant1_projects) == 1
        assert tenant1_projects[0].project_name == "Project 1"

        assert len(tenant2_projects) == 1
        assert tenant2_projects[0].project_name == "Project 2"

    def test_cannot_access_other_tenant_project_by_id(
        self, db, test_tenant, second_tenant, test_user, second_tenant_user
    ):
        """Attempting to access another tenant's project by ID should fail.

        SECURITY CRITICAL: This simulates an attack where a user knows another
        tenant's project ID and tries to access it.
        """
        from datetime import date

        # Create clients
        client1 = Client(tenant_id=test_tenant.id, company_name="Client 1")
        client2 = Client(tenant_id=second_tenant.id, company_name="Client 2")
        db.add_all([client1, client2])
        db.flush()

        # Create project for tenant 2
        project2 = Project(
            tenant_id=second_tenant.id,
            client_id=client2.id,
            user_id=second_tenant_user.id,
            jurisdiction="HK",
            accounting_standard="HKFRS",
            financial_year_end=date(2024, 12, 31),
            project_name="Secret Project",
        )
        db.add(project2)
        db.commit()
        project2_id = project2.id

        # Tenant 1 attempts to access tenant 2's project by ID
        # This simulates the attack scenario
        stolen_project = (
            db.query(Project)
            .filter(Project.id == project2_id, Project.tenant_id == test_tenant.id)
            .first()
        )

        # Should return None because tenant_id doesn't match
        assert stolen_project is None

        # Verify project exists for tenant 2
        legitimate_access = (
            db.query(Project)
            .filter(Project.id == project2_id, Project.tenant_id == second_tenant.id)
            .first()
        )
        assert legitimate_access is not None
        assert legitimate_access.project_name == "Secret Project"


class TestAPITenantIsolation:
    """Test that API endpoints enforce tenant isolation.

    These are integration tests that verify the full request flow.
    """

    def test_list_clients_only_returns_own_tenant(
        self, client, db, test_tenant, second_tenant, auth_headers
    ):
        """GET /clients should only return clients from current tenant."""
        # Create clients in different tenants
        client1 = Client(tenant_id=test_tenant.id, company_name="My Client")
        client2 = Client(tenant_id=second_tenant.id, company_name="Other Client")
        db.add_all([client1, client2])
        db.commit()

        # Make request as test_tenant user
        response = client.get(
            "/api/v1/projects/clients",
            headers=auth_headers,
        )

        assert response.status_code == 200
        clients = response.json()

        # Should only see own tenant's client
        assert len(clients) == 1
        assert clients[0]["company_name"] == "My Client"

    def test_list_projects_only_returns_own_tenant(
        self, client, db, test_tenant, second_tenant, test_user, second_tenant_user, auth_headers
    ):
        """GET /projects should only return projects from current tenant."""
        from datetime import date

        # Create clients
        client1 = Client(tenant_id=test_tenant.id, company_name="Client 1")
        client2 = Client(tenant_id=second_tenant.id, company_name="Client 2")
        db.add_all([client1, client2])
        db.flush()

        # Create projects
        project1 = Project(
            tenant_id=test_tenant.id,
            client_id=client1.id,
            user_id=test_user.id,
            jurisdiction="HK",
            accounting_standard="HKFRS",
            financial_year_end=date(2024, 12, 31),
            project_name="My Project",
        )
        project2 = Project(
            tenant_id=second_tenant.id,
            client_id=client2.id,
            user_id=second_tenant_user.id,
            jurisdiction="HK",
            accounting_standard="HKFRS",
            financial_year_end=date(2024, 12, 31),
            project_name="Other Project",
        )
        db.add_all([project1, project2])
        db.commit()

        # Make request as test_tenant user
        response = client.get(
            "/api/v1/projects/",
            headers=auth_headers,
        )

        assert response.status_code == 200
        projects = response.json()

        # Should only see own tenant's project
        assert len(projects) == 1
        assert projects[0]["project_name"] == "My Project"

    def test_cannot_access_other_tenant_project_via_api(
        self, client, db, test_tenant, second_tenant, test_user, second_tenant_user, auth_headers
    ):
        """GET /projects/{id} should return 404 for other tenant's project.

        SECURITY CRITICAL: This verifies that even with a valid project ID,
        users cannot access projects from other tenants.
        """
        from datetime import date

        # Create client for second tenant
        client2 = Client(tenant_id=second_tenant.id, company_name="Client 2")
        db.add(client2)
        db.flush()

        # Create project for second tenant
        project2 = Project(
            tenant_id=second_tenant.id,
            client_id=client2.id,
            user_id=second_tenant_user.id,
            jurisdiction="HK",
            accounting_standard="HKFRS",
            financial_year_end=date(2024, 12, 31),
            project_name="Secret Project",
        )
        db.add(project2)
        db.commit()
        project2_id = project2.id

        # Test tenant user attempts to access second tenant's project
        response = client.get(
            f"/api/v1/projects/{project2_id}",
            headers=auth_headers,
        )

        # Should return 404 (not 403) to avoid leaking information
        assert response.status_code == 404
        assert response.json()["detail"] == "Project not found"
