"""
Email verification model - converted from TypeORM EmailVerification entity.
"""

import uuid
from django.db import models
from apps.users.models import User


class EmailVerification(models.Model):
    """Email verification codes."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_verifications", db_column="userId")
    code = models.CharField(max_length=6)
    expires_at = models.DateTimeField(db_column="expiresAt")
    is_used = models.BooleanField(default=False, db_column="isUsed")
    created_at = models.DateTimeField(auto_now_add=True, db_column="createdAt")

    class Meta:
        db_table = "email_verifications"

    def __str__(self) -> str:
        return f"Verification for {self.user.email}"
