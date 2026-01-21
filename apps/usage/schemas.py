"""
Usage schemas for API.
"""

from datetime import datetime
from uuid import UUID
from typing import Any
from ninja import Schema
from pydantic import Field, ConfigDict


class UsageLogOut(Schema):
    """Usage log output - camelCase for frontend."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    action: str
    creditsUsed: float = Field(validation_alias="credits_used", default=0)
    costUsd: float = Field(validation_alias="cost_usd", default=0)
    metadata: dict[str, Any] | None = None
    success: bool
    createdAt: datetime = Field(validation_alias="created_at")


class UsageStatsOut(Schema):
    """Usage stats output - camelCase for frontend."""

    totalCredits: float
    totalCost: float
    totalActions: int
    actionsByType: dict[str, int]
