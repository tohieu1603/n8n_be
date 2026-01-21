"""
API Key model - converted from TypeORM ApiKey entity.
"""

import uuid
from django.db import models
from apps.users.models import User


class ApiKey(models.Model):
    """API Key model for programmatic access."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_keys", db_column="userId")
    name = models.CharField(max_length=100)
    key_hash = models.CharField(max_length=64, unique=True, db_column="keyHash")
    key_prefix = models.CharField(max_length=8, db_column="keyPrefix")
    encrypted_key = models.TextField(null=True, blank=True, db_column="encryptedKey")
    last_used_at = models.DateTimeField(null=True, blank=True, db_column="lastUsedAt")
    is_active = models.BooleanField(default=True, db_column="isActive")
    created_at = models.DateTimeField(auto_now_add=True, db_column="createdAt")

    class Meta:
        db_table = "api_keys"

    def __str__(self) -> str:
        return f"{self.name} ({self.key_prefix}...)"
