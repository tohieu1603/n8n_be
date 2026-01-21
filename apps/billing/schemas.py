"""
Billing schemas for API.
"""

from datetime import datetime
from uuid import UUID
from typing import Any
from ninja import Schema


class PaymentOut(Schema):
    id: UUID
    transaction_id: str
    amount: float
    credits: int
    plan_id: str
    description: str
    status: str
    qr_code: str | None
    expires_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class CreatePaymentIn(Schema):
    plan_id: str


class CreatePaymentOut(Schema):
    payment: PaymentOut
    qr_code_url: str | None


class WebhookIn(Schema):
    id: int
    gateway: str
    transaction_date: str
    account_number: str
    code: str | None
    content: str
    transferType: str
    transferAmount: float
    accumulated: float
    subAccount: str | None
    referenceCode: str
    description: str


class PlansOut(Schema):
    id: str
    name: str
    credits: int
    price_vnd: int
    price_usd: float
    popular: bool = False
