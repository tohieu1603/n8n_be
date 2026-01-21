"""
User model - converted from TypeORM User entity.
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager


class UserRole(models.TextChoices):
    USER = "user", "User"
    ADMIN = "admin", "Admin"


class UserManager(BaseUserManager):
    def create_user(self, email: str, password: str | None = None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra_fields):
        extra_fields.setdefault("role", UserRole.ADMIN)
        extra_fields.setdefault("is_active", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser):
    """User model matching TypeORM entity."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    role = models.CharField(max_length=10, choices=UserRole.choices, default=UserRole.USER)

    # Map to camelCase columns from TypeORM
    credits_used = models.DecimalField(max_digits=10, decimal_places=4, default=0, db_column="creditsUsed")
    total_spent_usd = models.DecimalField(max_digits=10, decimal_places=4, default=0, db_column="totalSpentUsd")
    token_balance = models.BigIntegerField(default=0, db_column="tokenBalance")

    is_pro = models.BooleanField(default=False, db_column="isPro")
    pro_expires_at = models.DateTimeField(null=True, blank=True, db_column="proExpiresAt")

    is_active = models.BooleanField(default=True, db_column="isActive")
    is_email_verified = models.BooleanField(default=False, db_column="isEmailVerified")

    # Google OAuth fields
    google_id = models.CharField(max_length=255, null=True, blank=True, db_column="googleId")
    avatar_url = models.URLField(max_length=500, null=True, blank=True, db_column="avatarUrl")

    # Welcome bonus tracking
    has_received_welcome_bonus = models.BooleanField(default=False, db_column="hasReceivedWelcomeBonus")

    created_at = models.DateTimeField(auto_now_add=True, db_column="createdAt")
    updated_at = models.DateTimeField(auto_now=True, db_column="updatedAt")
    last_login = models.DateTimeField(null=True, blank=True, db_column="last_login")

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"

    def __str__(self) -> str:
        return self.email
