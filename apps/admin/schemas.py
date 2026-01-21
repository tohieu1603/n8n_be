"""
Admin schemas for API.
"""

from datetime import datetime
from uuid import UUID
from ninja import Schema
from pydantic import Field, ConfigDict


class AdminUserOut(Schema):
    """Admin user output - camelCase for frontend."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    email: str
    name: str | None = None
    role: str
    creditsUsed: float = Field(validation_alias="credits_used", default=0)
    tokenBalance: int = Field(validation_alias="token_balance", default=0)
    isPro: bool = Field(validation_alias="is_pro", default=False)
    proExpiresAt: datetime | None = Field(validation_alias="pro_expires_at", default=None)
    isActive: bool = Field(validation_alias="is_active", default=True)
    isEmailVerified: bool = Field(validation_alias="is_email_verified", default=False)
    avatarUrl: str | None = Field(validation_alias="avatar_url", default=None)
    createdAt: datetime = Field(validation_alias="created_at")
    updatedAt: datetime = Field(validation_alias="updated_at")


class AdminUserUpdateIn(Schema):
    role: str | None = None
    tokenBalance: int | None = Field(default=None, alias="token_balance")
    isPro: bool | None = Field(default=None, alias="is_pro")
    isActive: bool | None = Field(default=None, alias="is_active")


class PaginationOut(Schema):
    """Pagination info for list responses."""

    page: int
    limit: int
    total: int
    totalPages: int


class UsersListOut(Schema):
    """Paginated users list response."""

    users: list[AdminUserOut]
    pagination: PaginationOut


class UserStatsOut(Schema):
    """User statistics for admin dashboard."""

    total: int
    active: int
    pro: int
    verified: int
    admins: int


class AdminStatsOut(Schema):
    """Admin dashboard stats - camelCase for frontend."""

    totalUsers: int
    activeUsers: int
    proUsers: int
    totalRevenueUsd: float
    totalGenerations: int
    totalChats: int
