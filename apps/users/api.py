"""
Users API endpoints.
"""

from ninja import Router
from django.http import HttpRequest

from utils.auth import AuthBearer, get_current_user
from .schemas import UserProfileOut, UserUpdateIn

router = Router(auth=AuthBearer())


@router.get("/me", response=UserProfileOut)
def get_profile(request: HttpRequest):
    """Get current user profile."""
    user = get_current_user(request)
    return user


@router.put("/me", response=UserProfileOut)
def update_profile(request: HttpRequest, data: UserUpdateIn):
    """Update current user profile."""
    user = get_current_user(request)
    if data.name is not None:
        user.name = data.name
    user.save()
    return user
