"""
Auth API endpoints - converted from auth.controller.ts
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from django.conf import settings
from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError

from apps.users.models import User
from utils.auth import AuthBearer, create_token, get_current_user
from .models import EmailVerification
from .schemas import LoginIn, RegisterIn, AuthOut, GoogleAuthIn, VerifyEmailIn, MessageOut
from apps.users.schemas import UserProfileOut

logger = logging.getLogger(__name__)

router = Router()


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(password.encode(), hashed.encode())


def generate_verification_code() -> str:
    """Generate 6-digit verification code."""
    return "".join([str(secrets.randbelow(10)) for _ in range(6)])


@router.post("/register", response=AuthOut)
def register(request: HttpRequest, data: RegisterIn):
    """Register a new user."""
    email = data.email.lower().strip()

    # Check if user exists
    if User.objects.filter(email=email).exists():
        raise HttpError(400, "Email already registered")

    # Create user
    user = User.objects.create(
        email=email,
        password=hash_password(data.password),
        name=data.name,
        token_balance=100,  # Welcome bonus
        has_received_welcome_bonus=True,
    )

    # Create verification code
    EmailVerification.objects.create(
        user=user,
        code=generate_verification_code(),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )

    # TODO: Send verification email

    token = create_token(user)
    return AuthOut(user=user, token=token)


@router.post("/login", response=AuthOut)
def login(request: HttpRequest, data: LoginIn):
    """Login with email and password."""
    email = data.email.lower().strip()

    user = User.objects.filter(email=email, is_active=True).first()
    if not user or not user.password:
        raise HttpError(401, "Invalid email or password")

    if not verify_password(data.password, user.password):
        raise HttpError(401, "Invalid email or password")

    token = create_token(user)
    return AuthOut(user=user, token=token)


@router.post("/google/token", response=AuthOut)
def google_login(request: HttpRequest, data: GoogleAuthIn):
    """Verify Google credential and login/register user."""
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests

    try:
        # Verify the Google JWT credential
        idinfo = id_token.verify_oauth2_token(
            data.credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )

        email = idinfo.get("email", "").lower().strip()
        name = idinfo.get("name", "")

        if not email:
            raise HttpError(400, "No email in Google credential")

    except ValueError as e:
        logger.error(f"[GoogleAuth] Token verification failed: {e}")
        raise HttpError(401, "Invalid Google credential")

    # Find or create user
    google_id = idinfo.get("sub", "")
    picture = idinfo.get("picture", "")
    user = User.objects.filter(email=email).first()

    if not user:
        # Create new user from Google
        user = User.objects.create(
            email=email,
            name=name,
            google_id=google_id,
            avatar_url=picture,
            is_email_verified=True,
            token_balance=100,
            has_received_welcome_bonus=True,
        )
        logger.info(f"[GoogleAuth] Created new user: {email}")
    else:
        # Update google_id and avatar if not set
        update_fields = []
        if not user.google_id and google_id:
            user.google_id = google_id
            update_fields.append("google_id")
        if not user.name and name:
            user.name = name
            update_fields.append("name")
        if not user.avatar_url and picture:
            user.avatar_url = picture
            update_fields.append("avatar_url")
        if update_fields:
            user.save(update_fields=update_fields)

    token = create_token(user)
    return AuthOut(user=user, token=token)


@router.post("/verify-email", response=MessageOut, auth=AuthBearer())
def verify_email(request: HttpRequest, data: VerifyEmailIn):
    """Verify email with code."""
    user = get_current_user(request)

    verification = (
        EmailVerification.objects.filter(
            user=user,
            code=data.code,
            is_used=False,
            expires_at__gt=datetime.now(timezone.utc),
        )
        .order_by("-created_at")
        .first()
    )

    if not verification:
        raise HttpError(400, "Invalid or expired verification code")

    verification.is_used = True
    verification.save()

    user.is_email_verified = True
    user.save()

    return MessageOut(message="Email verified successfully")


@router.post("/resend-verification", response=MessageOut, auth=AuthBearer())
def resend_verification(request: HttpRequest):
    """Resend verification email."""
    user = get_current_user(request)

    if user.is_email_verified:
        raise HttpError(400, "Email already verified")

    # Create new verification code
    EmailVerification.objects.create(
        user=user,
        code=generate_verification_code(),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )

    # TODO: Send verification email

    return MessageOut(message="Verification email sent")


@router.get("/me", response=UserProfileOut, auth=AuthBearer())
def get_me(request: HttpRequest):
    """Get current authenticated user."""
    user = get_current_user(request)
    return UserProfileOut.from_orm(user)
