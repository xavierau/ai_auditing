"""Tests for authentication endpoints.

Tests cover:
- User login with valid/invalid credentials
- User registration with tenant creation
- Token refresh
- Token logout/blacklisting
- Rate limiting
- Audit logging
"""

import pytest
from fastapi.testclient import TestClient

from genreport.core.database.models import AuditLog, Tenant, User
from genreport.core.security.jwt_service import decode_access_token, hash_password


class TestLogin:
    """Test login endpoint."""

    def test_login_success(self, client, db, test_user):
        """Valid credentials should return tokens."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 1800  # 30 minutes in seconds

        # Verify access token payload
        payload = decode_access_token(data["access_token"])
        assert payload["sub"] == str(test_user.id)
        assert payload["tenant_id"] == str(test_user.tenant_id)
        assert payload["role"] == "auditor"

    def test_login_invalid_email(self, client, db):
        """Invalid email should return 401."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "password123",
            },
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect email or password"

    def test_login_invalid_password(self, client, db, test_user):
        """Invalid password should return 401."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect email or password"

    def test_login_inactive_user(self, client, db, test_user):
        """Inactive user should not be able to login."""
        # Deactivate user
        test_user.is_active = False
        db.commit()

        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123",
            },
        )

        assert response.status_code == 401

    def test_login_creates_audit_log_success(self, client, db, test_user):
        """Successful login should create audit log."""
        # Clear existing audit logs
        db.query(AuditLog).delete()
        db.commit()

        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123",
            },
        )

        assert response.status_code == 200

        # Check audit log
        audit_logs = db.query(AuditLog).all()
        assert len(audit_logs) == 1
        assert audit_logs[0].event_type == "AUTHENTICATION"
        assert audit_logs[0].action == "LOGIN"
        assert audit_logs[0].user_id == test_user.id
        assert audit_logs[0].tenant_id == test_user.tenant_id
        assert audit_logs[0].status == "SUCCESS"

    def test_login_creates_audit_log_failure(self, client, db):
        """Failed login should create audit log."""
        # Clear existing audit logs
        db.query(AuditLog).delete()
        db.commit()

        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "password123",
            },
        )

        assert response.status_code == 401

        # Check audit log
        audit_logs = db.query(AuditLog).all()
        assert len(audit_logs) == 1
        assert audit_logs[0].event_type == "AUTHENTICATION"
        assert audit_logs[0].action == "LOGIN"
        assert audit_logs[0].user_id is None
        assert audit_logs[0].tenant_id is None
        assert audit_logs[0].status == "FAILURE"


class TestRegister:
    """Test registration endpoint."""

    def test_register_success(self, client, db):
        """Valid registration should create tenant and user."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "newpassword123",
                "full_name": "New User",
                "company_name": "New Company",
                "jurisdiction": "HK",
            },
        )

        assert response.status_code == 201
        data = response.json()

        # Check response structure
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

        # Verify tenant was created
        tenant = db.query(Tenant).filter(Tenant.company_name == "New Company").first()
        assert tenant is not None
        assert tenant.jurisdiction == "HK"
        assert tenant.is_active is True

        # Verify user was created
        user = db.query(User).filter(User.email == "newuser@example.com").first()
        assert user is not None
        assert user.full_name == "New User"
        assert user.role == "admin"  # First user is admin
        assert user.tenant_id == tenant.id
        assert user.is_active is True

    def test_register_duplicate_email(self, client, db, test_user):
        """Registration with existing email should fail."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",  # Already exists
                "password": "password123",
                "full_name": "Duplicate User",
                "company_name": "Duplicate Company",
                "jurisdiction": "HK",
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Email already registered"

    def test_register_invalid_jurisdiction(self, client, db):
        """Registration with invalid jurisdiction should fail."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "password123",
                "full_name": "New User",
                "company_name": "New Company",
                "jurisdiction": "INVALID",
            },
        )

        assert response.status_code == 400
        assert "Invalid jurisdiction" in response.json()["detail"]

    def test_register_creates_audit_log(self, client, db):
        """Registration should create audit log."""
        # Clear existing audit logs
        db.query(AuditLog).delete()
        db.commit()

        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "password123",
                "full_name": "New User",
                "company_name": "New Company",
                "jurisdiction": "HK",
            },
        )

        assert response.status_code == 201

        # Check audit log
        audit_logs = db.query(AuditLog).filter(AuditLog.action == "REGISTER").all()
        assert len(audit_logs) == 1
        assert audit_logs[0].event_type == "AUTHENTICATION"
        assert audit_logs[0].status == "SUCCESS"


class TestRefreshToken:
    """Test token refresh endpoint."""

    def test_refresh_token_success(self, client, db, test_user):
        """Valid refresh token should return new tokens."""
        # Login to get refresh token
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123",
            },
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

        # New tokens should be different from original
        assert data["access_token"] != login_response.json()["access_token"]
        assert data["refresh_token"] != refresh_token

    def test_refresh_token_invalid(self, client, db):
        """Invalid refresh token should return 401."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"},
        )

        assert response.status_code == 401

    def test_refresh_token_inactive_user(self, client, db, test_user):
        """Refresh token for inactive user should fail."""
        # Login to get refresh token
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123",
            },
        )
        refresh_token = login_response.json()["refresh_token"]

        # Deactivate user
        test_user.is_active = False
        db.commit()

        # Attempt refresh
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 401
        assert "User not found or inactive" in response.json()["detail"]


class TestLogout:
    """Test logout endpoint."""

    def test_logout_success(self, client, db, test_user):
        """Logout should blacklist the access token."""
        from genreport.core.database.models import BlacklistedToken

        # Login to get access token
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123",
            },
        )
        access_token = login_response.json()["access_token"]

        # Logout
        response = client.post(
            "/api/v1/auth/logout",
            json={"access_token": access_token},
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Successfully logged out"

        # Verify token is blacklisted - extract JTI from token
        payload = decode_access_token(access_token)
        jti = payload.get("jti")

        blacklisted = (
            db.query(BlacklistedToken)
            .filter(BlacklistedToken.token_jti == jti)
            .first()
        )
        assert blacklisted is not None
        assert blacklisted.tenant_id == test_user.tenant_id

    def test_logout_invalid_token(self, client, db):
        """Logout with invalid token should return 400."""
        response = client.post(
            "/api/v1/auth/logout",
            json={"access_token": "invalid_token"},
        )

        assert response.status_code == 400

    def test_logout_creates_audit_log(self, client, db, test_user):
        """Logout should create audit log."""
        # Clear existing audit logs
        db.query(AuditLog).delete()
        db.commit()

        # Login to get access token
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123",
            },
        )
        access_token = login_response.json()["access_token"]

        # Logout
        response = client.post(
            "/api/v1/auth/logout",
            json={"access_token": access_token},
        )

        assert response.status_code == 200

        # Check audit log (skip login log, find logout)
        audit_logs = db.query(AuditLog).filter(AuditLog.action == "LOGOUT").all()
        assert len(audit_logs) == 1
        assert audit_logs[0].event_type == "AUTHENTICATION"
        assert audit_logs[0].user_id == test_user.id
        assert audit_logs[0].status == "SUCCESS"


class TestRoleBasedAccess:
    """Test role-based access control."""

    def test_admin_role_in_token(self, client, db, test_admin_user):
        """Admin user should have admin role in token."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@example.com",
                "password": "adminpassword123",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify role in token
        payload = decode_access_token(data["access_token"])
        assert payload["role"] == "admin"

    def test_auditor_role_in_token(self, client, db, test_user):
        """Auditor user should have auditor role in token."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify role in token
        payload = decode_access_token(data["access_token"])
        assert payload["role"] == "auditor"

    def test_first_registered_user_is_admin(self, client, db):
        """First user registered for a tenant should be admin."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "firstuser@example.com",
                "password": "password123",
                "full_name": "First User",
                "company_name": "First Company",
                "jurisdiction": "HK",
            },
        )

        assert response.status_code == 201

        # Check user role
        user = db.query(User).filter(User.email == "firstuser@example.com").first()
        assert user.role == "admin"


class TestPasswordSecurity:
    """Test password hashing and security."""

    def test_password_is_hashed(self, db, test_user):
        """Password should be hashed, not stored in plaintext."""
        # Password should not match plaintext
        assert test_user.password_hash != "testpassword123"

        # Should be bcrypt hash
        assert test_user.password_hash.startswith("$2b$")

    def test_different_passwords_different_hashes(self, db):
        """Same password should produce different hashes (salt)."""
        hash1 = hash_password("password123")
        hash2 = hash_password("password123")

        # Both should be valid bcrypt hashes
        assert hash1.startswith("$2b$")
        assert hash2.startswith("$2b$")

        # But they should be different due to salt
        assert hash1 != hash2
