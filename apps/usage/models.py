"""
Usage log model - converted from TypeORM UsageLog entity.
"""

import uuid
from django.db import models
from apps.users.models import User


class ActionType(models.TextChoices):
    GENERATE_IMAGE = "generate_image", "Generate Image"
    LOGIN = "login", "Login"
    LOGOUT = "logout", "Logout"
    REGISTER = "register", "Register"
    CHAT = "chat", "Chat"
    CHAT_STREAM = "chat_stream", "Chat Stream"
    API_CHAT = "api_chat", "API Chat"
    API_CHAT_STREAM = "api_chat_stream", "API Chat Stream"
    API_IMAGE_GENERATION = "api_image_generation", "API Image Generation"
    CONVERT_WORD_TO_PDF = "convert_word_to_pdf", "Convert Word to PDF"
    CONVERT_PDF_TO_WORD = "convert_pdf_to_word", "Convert PDF to Word"
    DOCUMENT_CONVERSION = "document_conversion", "Document Conversion"
    GOOGLE_LOGIN = "google_login", "Google Login"


class UsageLog(models.Model):
    """Usage log for tracking user actions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="usage_logs", db_column="userId")
    action = models.CharField(max_length=50, choices=ActionType.choices)
    credits_used = models.DecimalField(max_digits=10, decimal_places=4, default=0, db_column="creditsUsed")
    cost_usd = models.DecimalField(max_digits=10, decimal_places=4, default=0, db_column="costUsd")
    metadata = models.JSONField(null=True, blank=True)
    success = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, db_column="createdAt")

    class Meta:
        db_table = "usage_logs"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user.email} - {self.action}"
