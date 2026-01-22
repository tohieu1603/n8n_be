"""
Memory Manager - handles conversation history and context.

Implements memory hierarchy:
- Short-term: Recent messages in context window
- Long-term: Summarized old conversations (database)
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class MemoryConfig:
    """Configuration for memory management."""
    max_messages: int = 10
    summarize_after: int = 20
    include_summary: bool = True


class MemoryManager:
    """
    Manages conversation memory for prompt building.

    Responsibilities:
    - Load recent messages from conversation
    - Summarize old messages when threshold exceeded
    - Format messages for API call
    """

    def __init__(self, config: Optional[MemoryConfig] = None):
        self.config = config or MemoryConfig()

    def get_conversation_context(
        self,
        conversation_id: Optional[str],
        messages_model,
        conversation_model
    ) -> dict:
        """
        Get conversation context for prompt building.

        Args:
            conversation_id: UUID of conversation (None for new)
            messages_model: ChatMessage Django model
            conversation_model: ChatConversation Django model

        Returns:
            dict with keys:
            - conversation: Conversation object or None
            - messages: List of recent messages
            - summary: Conversation summary or None
        """
        if not conversation_id:
            return {
                "conversation": None,
                "messages": [],
                "summary": None
            }

        try:
            conversation = conversation_model.objects.get(id=conversation_id)
        except conversation_model.DoesNotExist:
            return {
                "conversation": None,
                "messages": [],
                "summary": None
            }

        # Get recent messages
        messages = list(
            messages_model.objects
            .filter(conversation_id=conversation_id)
            .order_by("-created_at")[:self.config.max_messages]
        )
        messages.reverse()  # Oldest first

        # Get summary if available
        summary = getattr(conversation, "summary", None)

        return {
            "conversation": conversation,
            "messages": messages,
            "summary": summary if self.config.include_summary else None
        }

    def format_messages_for_api(self, messages: list) -> list[dict]:
        """
        Format database messages for LLM API call.

        Args:
            messages: List of ChatMessage objects

        Returns:
            List of dicts with role and content
        """
        return [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in messages
        ]

    def should_summarize(self, message_count: int) -> bool:
        """Check if conversation should be summarized."""
        return message_count > self.config.summarize_after

    async def create_summary(self, conversation, messages_model, llm_client) -> str:
        """
        Create summary of old messages.

        This is called when message_count > summarize_after.
        Uses LLM to summarize conversation so far.

        Args:
            conversation: Conversation object
            messages_model: ChatMessage model
            llm_client: LLM client for summarization

        Returns:
            Summary string
        """
        # Get all messages except recent ones
        old_messages = list(
            messages_model.objects
            .filter(conversation_id=conversation.id)
            .order_by("created_at")[:-self.config.max_messages]
        )

        if not old_messages:
            return ""

        # Format for summarization
        messages_text = "\n".join([
            f"{msg.role}: {msg.content[:500]}"  # Truncate long messages
            for msg in old_messages
        ])

        # Call LLM to summarize
        summary_prompt = f"""Tóm tắt ngắn gọn cuộc hội thoại sau (tối đa 200 từ):

{messages_text}

Tóm tắt:"""

        # This would call the LLM - implementation depends on your client
        # For now, return placeholder
        # TODO: Implement actual LLM call
        return f"[Summary of {len(old_messages)} messages]"
