"""
Tests for API Keys endpoints.
"""

import pytest

from apps.keys.models import ApiKey


@pytest.mark.django_db
class TestKeysAPI:
    """API Keys test cases."""

    def test_list_keys_empty(self, api_client, auth_headers):
        """Test listing keys when none exist."""
        response = api_client.get("/keys/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] == []

    def test_create_key(self, api_client, auth_headers):
        """Test creating a new API key."""
        response = api_client.post(
            "/keys/",
            json={"name": "Test Key"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Test Key"
        assert "key" in data["data"]
        # Key should be fully visible on creation
        assert data["data"]["key"].startswith("sk_")

    def test_list_keys_masked(self, api_client, auth_headers, admin_user):
        """Test that listed keys are masked."""
        # Create a key directly
        ApiKey.objects.create(
            user=admin_user,
            name="Masked Key",
            key_hash="test_hash",
            key_prefix="sk_abc12",
            encrypted_key="encrypted",
        )

        response = api_client.get("/keys/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        # Key should be masked
        assert "..." in data["data"][0]["key"]

    def test_reveal_key(self, api_client, auth_headers, admin_user):
        """Test revealing a key."""
        # Create key via API first
        create_response = api_client.post(
            "/keys/",
            json={"name": "Reveal Test"},
            headers=auth_headers,
        )
        key_id = create_response.json()["data"]["id"]

        # Reveal the key
        response = api_client.post(
            f"/keys/{key_id}/reveal",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["key"].startswith("sk_")

    def test_delete_key(self, api_client, auth_headers, admin_user):
        """Test deleting an API key."""
        key = ApiKey.objects.create(
            user=admin_user,
            name="To Delete",
            key_hash="hash",
            key_prefix="sk_del12",
            encrypted_key="encrypted",
        )

        response = api_client.delete(
            f"/keys/{key.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert not ApiKey.objects.filter(id=key.id).exists()

    def test_key_access_control(self, api_client, user_auth_headers, admin_user):
        """Test that users can't access other users' keys."""
        key = ApiKey.objects.create(
            user=admin_user,
            name="Admin Key",
            key_hash="hash",
            key_prefix="sk_adm12",
            encrypted_key="encrypted",
        )

        # Regular user should not see admin's key
        response = api_client.get("/keys/", headers=user_auth_headers)
        data = response.json()
        assert len(data["data"]) == 0

    def test_unauthenticated_access(self, api_client):
        """Test that unauthenticated users can't access keys."""
        response = api_client.get("/keys/")
        assert response.status_code == 401
