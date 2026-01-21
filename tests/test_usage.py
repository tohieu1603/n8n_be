"""
Tests for Usage API endpoints.
"""

import pytest
from datetime import datetime, timezone

from apps.usage.models import UsageLog, ActionType


@pytest.mark.django_db
class TestUsageAPI:
    """Usage API test cases."""

    def test_get_usage_empty(self, api_client, auth_headers):
        """Test getting usage when none exist."""
        response = api_client.get("/usage/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] == []

    def test_get_usage_with_logs(self, api_client, auth_headers, admin_user):
        """Test getting usage with logs."""
        UsageLog.objects.create(
            user=admin_user,
            action=ActionType.CHAT,
            credits_used=10,
            metadata={"model": "test"},
        )

        response = api_client.get("/usage/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["action"] == "chat"

    def test_get_usage_stats(self, api_client, auth_headers, admin_user):
        """Test getting usage stats."""
        # Create some usage logs
        UsageLog.objects.create(
            user=admin_user,
            action=ActionType.CHAT,
            credits_used=10,
        )
        UsageLog.objects.create(
            user=admin_user,
            action=ActionType.IMAGE,
            credits_used=50,
        )
        UsageLog.objects.create(
            user=admin_user,
            action=ActionType.CHAT,
            credits_used=20,
        )

        response = api_client.get("/usage/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["totalCredits"] == 80
        assert data["data"]["totalActions"] == 3
        assert "actionsByType" in data["data"]

    def test_usage_pagination(self, api_client, auth_headers, admin_user):
        """Test usage pagination."""
        # Create multiple logs
        for i in range(15):
            UsageLog.objects.create(
                user=admin_user,
                action=ActionType.CHAT,
                credits_used=i,
            )

        response = api_client.get("/usage/?limit=10", headers=auth_headers)
        data = response.json()
        assert len(data["data"]) == 10

    def test_usage_access_control(self, api_client, user_auth_headers, admin_user):
        """Test that users only see their own usage."""
        # Create usage for admin
        UsageLog.objects.create(
            user=admin_user,
            action=ActionType.CHAT,
            credits_used=100,
        )

        # Regular user should not see admin's usage
        response = api_client.get("/usage/", headers=user_auth_headers)
        data = response.json()
        assert len(data["data"]) == 0
