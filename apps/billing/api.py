"""
Billing API endpoints - converted from billing.controller.ts
"""

import uuid
from datetime import datetime, timedelta, timezone

from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError

from utils.auth import AuthBearer, get_current_user
from .models import Payment, PaymentStatus
from .schemas import PaymentOut, CreatePaymentIn, CreatePaymentOut, PlansOut, WebhookIn

router = Router()

# Pricing plans
PLANS = [
    {"id": "starter", "name": "Starter", "credits": 100, "price_vnd": 49000, "price_usd": 2.0},
    {
        "id": "basic",
        "name": "Basic",
        "credits": 500,
        "price_vnd": 199000,
        "price_usd": 8.0,
        "popular": True,
    },
    {"id": "pro", "name": "Pro", "credits": 2000, "price_vnd": 699000, "price_usd": 28.0},
    {"id": "business", "name": "Business", "credits": 10000, "price_vnd": 2999000, "price_usd": 120.0},
]


@router.get("/plans", response=list[PlansOut])
def get_plans(request: HttpRequest):
    """Get available pricing plans."""
    return [PlansOut(**p) for p in PLANS]


@router.get("/payments", response=list[PaymentOut], auth=AuthBearer())
def get_payments(request: HttpRequest):
    """Get user's payment history."""
    user = get_current_user(request)
    payments = Payment.objects.filter(user=user).order_by("-created_at")[:50]
    return list(payments)


@router.post("/payments", response=CreatePaymentOut, auth=AuthBearer())
def create_payment(request: HttpRequest, data: CreatePaymentIn):
    """Create a new payment."""
    user = get_current_user(request)

    plan = next((p for p in PLANS if p["id"] == data.plan_id), None)
    if not plan:
        raise HttpError(400, "Invalid plan ID")

    transaction_id = f"IMG{uuid.uuid4().hex[:12].upper()}"

    payment = Payment.objects.create(
        user=user,
        transaction_id=transaction_id,
        amount=plan["price_vnd"],
        credits=plan["credits"],
        plan_id=plan["id"],
        description=f"{plan['name']} - {plan['credits']} credits",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )

    # TODO: Generate QR code via SePay API

    return CreatePaymentOut(
        payment=PaymentOut(
            id=payment.id,
            transaction_id=payment.transaction_id,
            amount=float(payment.amount),
            credits=payment.credits,
            plan_id=payment.plan_id,
            description=payment.description,
            status=payment.status,
            qr_code=payment.qr_code,
            expires_at=payment.expires_at,
            completed_at=payment.completed_at,
            created_at=payment.created_at,
        ),
        qr_code_url=None,
    )


@router.get("/payments/{payment_id}", response=PaymentOut, auth=AuthBearer())
def get_payment(request: HttpRequest, payment_id: str):
    """Get payment details."""
    user = get_current_user(request)

    try:
        payment = Payment.objects.get(id=payment_id, user=user)
    except Payment.DoesNotExist:
        raise HttpError(404, "Payment not found")

    return payment


@router.post("/webhook/sepay")
def sepay_webhook(request: HttpRequest, data: WebhookIn):
    """Handle SePay webhook for payment confirmation."""
    # Find matching payment
    payment = Payment.objects.filter(
        transaction_id=data.referenceCode,
        status=PaymentStatus.PENDING,
    ).first()

    if not payment:
        return {"success": False, "message": "Payment not found"}

    if data.transferAmount < float(payment.amount):
        return {"success": False, "message": "Insufficient amount"}

    # Update payment status
    payment.status = PaymentStatus.COMPLETED
    payment.completed_at = datetime.now(timezone.utc)
    payment.metadata = {
        "bank_code": data.gateway,
        "reference": data.referenceCode,
        "description": data.description,
    }
    payment.save()

    # Add credits to user
    user = payment.user
    user.token_balance += payment.credits
    user.save()

    return {"success": True, "message": "Payment confirmed"}
