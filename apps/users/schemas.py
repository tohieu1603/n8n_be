"""
User schemas for API.
"""

from datetime import datetime
from uuid import UUID
from ninja import Schema
from pydantic import Field, ConfigDict


class UserProfileOut(Schema):
    """User profile output - camelCase for frontend compatibility."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id: UUID
    email: str
    name: str | None = None
    role: str
    creditsUsed: float = Field(validation_alias="credits_used", default=0)
    totalSpentUsd: float = Field(validation_alias="total_spent_usd", default=0)
    tokenBalance: int = Field(validation_alias="token_balance", default=0)
    isPro: bool = Field(validation_alias="is_pro", default=False)
    proExpiresAt: datetime | None = Field(validation_alias="pro_expires_at", default=None)
    isEmailVerified: bool = Field(validation_alias="is_email_verified", default=False)
    avatarUrl: str | None = Field(validation_alias="avatar_url", default=None)
    createdAt: datetime = Field(validation_alias="created_at")


class UserUpdateIn(Schema):
    name: str | None = None
