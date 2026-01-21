"""
API Key schemas for API.
"""

from datetime import datetime
from uuid import UUID
from ninja import Schema


class ApiKeyOut(Schema):
    id: UUID
    name: str
    key: str  # Masked key
    can_reveal: bool
    created_at: datetime
    last_used_at: datetime | None


class ApiKeyCreateIn(Schema):
    name: str


class ApiKeyCreateOut(Schema):
    api_key: ApiKeyOut
    key: str  # Full key, only returned once


class ApiKeyRevealOut(Schema):
    key: str
