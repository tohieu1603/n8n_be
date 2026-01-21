"""
Pytest configuration and fixtures.
"""

import json
import pytest
from django.test import Client

from apps.users.models import User, UserRole


class APIClient:
    """Wrapper around Django test client for API testing."""

    def __init__(self):
        self.client = Client()

    def _make_request(self, method, path, data=None, headers=None):
        """Make HTTP request."""
        kwargs = {"content_type": "application/json"}

        if headers:
            kwargs.update(headers)

        if data:
            kwargs["data"] = json.dumps(data)

        # Prepend /api if not present
        if not path.startswith("/api"):
            path = f"/api{path}"

        response = getattr(self.client, method.lower())(path, **kwargs)
        return APIResponse(response)

    def get(self, path, headers=None, **kwargs):
        return self._make_request("GET", path, headers=headers)

    def post(self, path, json=None, headers=None, **kwargs):
        return self._make_request("POST", path, data=json, headers=headers)

    def put(self, path, json=None, headers=None, **kwargs):
        return self._make_request("PUT", path, data=json, headers=headers)

    def patch(self, path, json=None, headers=None, **kwargs):
        return self._make_request("PATCH", path, data=json, headers=headers)

    def delete(self, path, headers=None, **kwargs):
        return self._make_request("DELETE", path, headers=headers)


class APIResponse:
    """Wrapper around Django response for easier testing."""

    def __init__(self, response):
        self._response = response
        self.status_code = response.status_code

    def json(self):
        return json.loads(self._response.content)


@pytest.fixture
def api_client():
    """API test client."""
    return APIClient()


@pytest.fixture
def admin_user(db):
    """Create admin user for testing."""
    user = User.objects.create(
        email="admin@test.com",
        name="Admin User",
        role=UserRole.ADMIN,
        is_email_verified=True,
        token_balance=100000,
    )
    user.set_password("Admin@123456")
    user.save()
    return user


@pytest.fixture
def regular_user(db):
    """Create regular user for testing."""
    user = User.objects.create(
        email="user@test.com",
        name="Regular User",
        role=UserRole.USER,
        is_email_verified=True,
        token_balance=10000,
    )
    user.set_password("User@123456")
    user.save()
    return user


def create_token(user):
    """Create JWT token for user."""
    import jwt
    from datetime import datetime, timedelta, timezone
    from django.conf import settings

    payload = {
        "userId": str(user.id),
        "email": user.email,
        "role": user.role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


@pytest.fixture
def auth_headers(admin_user):
    """Get auth headers for admin user."""
    token = create_token(admin_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


@pytest.fixture
def user_auth_headers(regular_user):
    """Get auth headers for regular user."""
    token = create_token(regular_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}
