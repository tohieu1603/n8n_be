"""
Tests for Auth API endpoints.
"""

import pytest
import bcrypt

from apps.users.models import User


def hash_password(password: str) -> str:
    """Hash password using bcrypt (same as auth API)."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


@pytest.fixture
def bcrypt_user(db):
    """Create user with bcrypt password (matching auth API)."""
    user = User.objects.create(
        email="bcrypt@test.com",
        name="Bcrypt User",
        role="admin",
        is_email_verified=True,
        token_balance=100000,
        password=hash_password("Admin@123456"),
    )
    return user


@pytest.mark.django_db
class TestAuthAPI:
    """Auth API test cases."""

    def test_register_success(self, api_client):
        """Test successful user registration."""
        response = api_client.post(
            "/auth/register",
            json={
                "email": "newuser@test.com",
                "password": "NewUser@123456",
                "name": "New User",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "user" in data["data"]
        assert data["data"]["user"]["email"] == "newuser@test.com"

    def test_register_duplicate_email(self, api_client, admin_user):
        """Test registration with existing email fails."""
        response = api_client.post(
            "/auth/register",
            json={
                "email": admin_user.email,
                "password": "Password@123",
                "name": "Duplicate User",
            },
        )
        assert response.status_code == 400

    def test_register_weak_password_still_works(self, api_client):
        """Test registration with weak password (no validation yet)."""
        # Note: Password validation is not implemented in auth API
        response = api_client.post(
            "/auth/register",
            json={
                "email": "weak@test.com",
                "password": "123",
                "name": "Weak Password",
            },
        )
        # Currently accepts weak passwords - validation should be added
        assert response.status_code == 200

    def test_login_success(self, api_client, bcrypt_user):
        """Test successful login with bcrypt password."""
        response = api_client.post(
            "/auth/login",
            json={
                "email": bcrypt_user.email,
                "password": "Admin@123456",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token" in data["data"]
        assert "user" in data["data"]

    def test_login_wrong_password(self, api_client, bcrypt_user):
        """Test login with wrong password fails."""
        response = api_client.post(
            "/auth/login",
            json={
                "email": bcrypt_user.email,
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, api_client):
        """Test login with non-existent user fails."""
        response = api_client.post(
            "/auth/login",
            json={
                "email": "nonexistent@test.com",
                "password": "Password@123",
            },
        )
        assert response.status_code == 401

    def test_get_me_authenticated(self, api_client, auth_headers):
        """Test getting current user when authenticated."""
        response = api_client.get("/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "email" in data["data"]

    def test_get_me_unauthenticated(self, api_client):
        """Test getting current user without auth fails."""
        response = api_client.get("/auth/me")
        assert response.status_code == 401


@pytest.mark.django_db
class TestLoginAfterRegister:
    """Test login flow after registration."""

    def test_can_login_after_register(self, api_client):
        """Test that user can login immediately after registration."""
        # Register
        register_response = api_client.post(
            "/auth/register",
            json={
                "email": "flow@test.com",
                "password": "FlowTest@123",
                "name": "Flow Test",
            },
        )
        assert register_response.status_code == 200

        # Login with same credentials
        login_response = api_client.post(
            "/auth/login",
            json={
                "email": "flow@test.com",
                "password": "FlowTest@123",
            },
        )
        assert login_response.status_code == 200
        data = login_response.json()
        assert data["success"] is True
        assert "token" in data["data"]
