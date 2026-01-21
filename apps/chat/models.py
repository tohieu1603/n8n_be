"""
Chat models - converted from TypeORM ChatConversation and ChatMessage entities.
"""

import uuid
from django.db import models
from apps.users.models import User


class MessageRole(models.TextChoices):
    USER = "user", "User"
    ASSISTANT = "assistant", "Assistant"


class ChatConversation(models.Model):
    """Chat conversation session."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversations", db_column="userId")
    title = models.CharField(max_length=255, default="Cuộc trò chuyện mới")
    agent_id = models.CharField(max_length=100, default="general_base", db_column="agentId")
    created_at = models.DateTimeField(auto_now_add=True, db_column="createdAt")
    updated_at = models.DateTimeField(auto_now=True, db_column="updatedAt")

    class Meta:
        db_table = "chat_conversations"
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.user.email})"


class ChatMessage(models.Model):
    """Chat message in a conversation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        ChatConversation, on_delete=models.CASCADE, related_name="messages", db_column="conversationId"
    )
    role = models.CharField(max_length=20, choices=MessageRole.choices)
    content = models.TextField()
    metadata = models.JSONField(null=True, blank=True)
    tokens_used = models.IntegerField(null=True, blank=True, db_column="tokensUsed")
    created_at = models.DateTimeField(auto_now_add=True, db_column="createdAt")

    class Meta:
        db_table = "chat_messages"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.role}: {self.content[:50]}..."
