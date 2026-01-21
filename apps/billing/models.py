"""
Payment model - converted from TypeORM Payment entity.
"""

import uuid
from django.db import models
from apps.users.models import User


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    EXPIRED = "expired", "Expired"


class Payment(models.Model):
    """Payment record for billing."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payments", db_column="userId")
    transaction_id = models.CharField(max_length=255, db_column="transactionId")
    amount = models.DecimalField(max_digits=12, decimal_places=0)  # VND
    credits = models.IntegerField(default=0)
    plan_id = models.CharField(max_length=100, db_column="planId")
    description = models.TextField()
    status = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING
    )
    qr_code = models.TextField(null=True, blank=True, db_column="qrCode")
    expires_at = models.DateTimeField(null=True, blank=True, db_column="expiresAt")
    completed_at = models.DateTimeField(null=True, blank=True, db_column="completedAt")
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_column="createdAt")

    class Meta:
        db_table = "payments"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user.email} - {self.amount} VND - {self.status}"
