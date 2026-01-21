"""
JWT Authentication utilities for Django Ninja.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from django.conf import settings
from django.http import HttpRequest
from ninja.security import HttpBearer

from apps.users.models import User


class AuthBearer(HttpBearer):
    """JWT Bearer token authentication."""

    def authenticate(self, request: HttpRequest, token: str) -> User | None:
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )
            user_id = payload.get("userId")
            if not user_id:
                return None

            # Use sync_to_async for async compatibility
            from asgiref.sync import sync_to_async
            import asyncio

            def get_user_sync():
                return User.objects.filter(id=user_id, is_active=True).first()

            # Check if we're in async context
            try:
                loop = asyncio.get_running_loop()
                # We're in async context - but authenticate is sync, so just do sync query
                # Django will handle it properly
                user = User.objects.filter(id=user_id, is_active=True).first()
            except RuntimeError:
                # No running loop - sync context
                user = User.objects.filter(id=user_id, is_active=True).first()

            if user:
                request.auth_user = user
            return user
        except jwt.InvalidTokenError:
            return None


class OptionalAuthBearer(HttpBearer):
    """Optional JWT authentication - doesn't fail if no token."""

    def authenticate(self, request: HttpRequest, token: str) -> User | None:
        if not token:
            return None
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )
            user_id = payload.get("userId")
            if not user_id:
                return None

            user = User.objects.filter(id=user_id, is_active=True).first()
            if user:
                request.auth_user = user
            return user
        except jwt.InvalidTokenError:
            return None


def get_current_user(request: HttpRequest) -> User:
    """Get authenticated user from request."""
    return getattr(request, "auth_user", request.auth)


def create_token(user: User) -> str:
    """Create JWT token for user."""
    payload = {
        "userId": str(user.id),
        "email": user.email,
        "role": user.role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str) -> dict[str, Any] | None:
    """Verify JWT token and return payload."""
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.InvalidTokenError:
        return None
