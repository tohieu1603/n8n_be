"""
Usage API endpoints - converted from usage.controller.ts
"""

from django.db.models import Sum, Count
from django.http import HttpRequest
from ninja import Router

from utils.auth import AuthBearer, get_current_user
from .models import UsageLog
from .schemas import UsageLogOut, UsageStatsOut

router = Router(auth=AuthBearer())


@router.get("/", response=list[UsageLogOut])
def get_usage(request: HttpRequest, limit: int = 50, offset: int = 0):
    """Get usage logs for current user."""
    user = get_current_user(request)
    logs = UsageLog.objects.filter(user=user).order_by("-created_at")[offset : offset + limit]
    return [UsageLogOut.from_orm(log) for log in logs]


@router.get("/stats", response=UsageStatsOut)
def get_stats(request: HttpRequest):
    """Get usage statistics for current user."""
    user = get_current_user(request)

    stats = UsageLog.objects.filter(user=user).aggregate(
        total_credits=Sum("credits_used"),
        total_cost=Sum("cost_usd"),
        total_actions=Count("id"),
    )

    actions_by_type = dict(
        UsageLog.objects.filter(user=user)
        .values("action")
        .annotate(count=Count("id"))
        .values_list("action", "count")
    )

    return UsageStatsOut(
        totalCredits=float(stats["total_credits"] or 0),
        totalCost=float(stats["total_cost"] or 0),
        totalActions=stats["total_actions"] or 0,
        actionsByType=actions_by_type,
    )
