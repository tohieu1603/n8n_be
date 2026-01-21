"""
Auth schemas for API.
"""

from ninja import Schema
from apps.users.schemas import UserProfileOut


class LoginIn(Schema):
    email: str
    password: str


class RegisterIn(Schema):
    email: str
    password: str
    name: str | None = None


class AuthOut(Schema):
    user: UserProfileOut
    token: str


class VerifyEmailIn(Schema):
    code: str


class ResendVerificationIn(Schema):
    email: str


class GoogleAuthIn(Schema):
    credential: str


class MessageOut(Schema):
    message: str
