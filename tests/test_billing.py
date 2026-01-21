"""
Tests for Billing API endpoints.
"""

import pytest

from apps.billing.models import Payment, PaymentStatus


@pytest.mark.django_db
class TestBillingAPI:
    """Billing API test cases."""

    def test_get_plans(self, api_client):
        """Test getting available plans (public endpoint)."""
        response = api_client.get("/billing/plans")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 4  # starter, basic, pro, business

        # Check plan structure
        plan = data["data"][0]
        assert "id" in plan
        assert "name" in plan
        assert "credits" in plan
        assert "price_vnd" in plan

    def test_get_payments_empty(self, api_client, auth_headers):
        """Test getting payments when none exist."""
        response = api_client.get("/billing/payments", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] == []

    def test_create_payment(self, api_client, auth_headers):
        """Test creating a payment."""
        response = api_client.post(
            "/billing/payments",
            json={"package_id": "basic"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["packageId"] == "basic"
        assert data["data"]["status"] == "pending"
        assert "transferContent" in data["data"]

    def test_create_payment_invalid_package(self, api_client, auth_headers):
        """Test creating payment with invalid package."""
        response = api_client.post(
            "/billing/payments",
            json={"package_id": "invalid"},
            headers=auth_headers,
        )
        assert response.status_code == 400

    def test_get_payment_by_id(self, api_client, auth_headers, admin_user):
        """Test getting a specific payment."""
        payment = Payment.objects.create(
            user=admin_user,
            package_id="basic",
            amount=199000,
            status=PaymentStatus.PENDING,
            transfer_content="TEST123",
        )

        response = api_client.get(
            f"/billing/payments/{payment.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["packageId"] == "basic"

    def test_payment_access_control(self, api_client, user_auth_headers, admin_user):
        """Test that users can't access other users' payments."""
        payment = Payment.objects.create(
            user=admin_user,
            package_id="pro",
            amount=699000,
            status=PaymentStatus.PENDING,
            transfer_content="ADMIN123",
        )

        response = api_client.get(
            f"/billing/payments/{payment.id}",
            headers=user_auth_headers,
        )
        assert response.status_code == 404


@pytest.mark.django_db
class TestSepayWebhook:
    """SePay webhook test cases."""

    def test_webhook_missing_api_key(self, api_client):
        """Test webhook without API key fails."""
        response = api_client.post(
            "/billing/webhook/sepay",
            json={
                "transferType": "in",
                "content": "TEST123",
                "transferAmount": 199000,
            },
        )
        assert response.status_code == 401

    def test_webhook_invalid_api_key(self, api_client):
        """Test webhook with invalid API key fails."""
        response = api_client.post(
            "/billing/webhook/sepay",
            json={
                "transferType": "in",
                "content": "TEST123",
                "transferAmount": 199000,
            },
            headers={"X-API-Key": "invalid-key"},
        )
        assert response.status_code == 401
