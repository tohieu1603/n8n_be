"""
Chat schemas for API.
"""

from datetime import datetime
from uuid import UUID
from typing import Any
from ninja import Schema
from pydantic import Field, ConfigDict


class ChatMessageOut(Schema):
    """Chat message output - camelCase for frontend."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    role: str
    content: str
    metadata: dict[str, Any] | None = None
    tokensUsed: int | None = Field(validation_alias="tokens_used", default=None)
    createdAt: datetime = Field(validation_alias="created_at")


class ConversationOut(Schema):
    """Conversation output - camelCase for frontend."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    title: str
    agentId: str = Field(validation_alias="agent_id")
    createdAt: datetime = Field(validation_alias="created_at")
    updatedAt: datetime = Field(validation_alias="updated_at")


class ConversationDetailOut(Schema):
    """Conversation detail with messages."""

    id: UUID
    title: str
    agentId: str
    messages: list[ChatMessageOut]
    createdAt: datetime
    updatedAt: datetime


class CreateConversationIn(Schema):
    title: str | None = None
    agentId: str = Field(default="general_base", alias="agent_id")


class UpdateConversationIn(Schema):
    title: str


class ChatMessageIn(Schema):
    """Single message in chat request."""

    role: str
    content: str


class ChatIn(Schema):
    """Chat request input - matches frontend format."""

    messages: list[ChatMessageIn]
    agentId: str | None = None
    imageUrl: str | None = None
    systemPrompt: str | None = None
    conversationId: str | None = None


class ChatUsageOut(Schema):
    """Usage info in response."""

    promptTokens: int = 0
    completionTokens: int = 0
    totalTokens: int = 0
    cost: float = 0


class ChatOut(Schema):
    """Chat response."""

    message: str
    usage: ChatUsageOut
    conversationId: UUID | None = None
