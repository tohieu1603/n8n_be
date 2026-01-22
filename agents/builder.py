"""
Prompt Builder - assembles prompts from config, memory, and user input.

Flow:
1. Load agent config from YAML
2. Get conversation memory
3. Build system prompt
4. Assemble final messages for LLM API
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import yaml

from .memory import MemoryManager, MemoryConfig


@dataclass
class AgentConfig:
    """Agent configuration loaded from YAML."""
    name: str
    description: str
    version: int
    role: str
    rules: str
    output_format: str
    memory: MemoryConfig
    tools_guidance: str = ""  # Guidance for using tools


class PromptBuilder:
    """
    Builds prompts for LLM API calls.

    Combines:
    - System prompt (from YAML config)
    - Memory context (conversation history)
    - User request (current message)
    """

    def __init__(self, agent_name: str = "n8n_teacher"):
        """
        Initialize prompt builder.

        Args:
            agent_name: Name of agent config file (without .yaml)
        """
        self.agent_name = agent_name
        self.config = self._load_config(agent_name)
        self.memory_manager = MemoryManager(self.config.memory)

    def _load_config(self, agent_name: str) -> AgentConfig:
        """Load agent configuration from YAML file."""
        # Get config file path
        config_dir = Path(__file__).parent / "configs"
        config_path = config_dir / f"{agent_name}.yaml"

        if not config_path.exists():
            raise FileNotFoundError(f"Agent config not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Parse memory config
        memory_data = data.get("memory", {})
        memory_config = MemoryConfig(
            max_messages=memory_data.get("max_messages", 10),
            summarize_after=memory_data.get("summarize_after", 20),
            include_summary=memory_data.get("include_summary", True)
        )

        return AgentConfig(
            name=data.get("name", agent_name),
            description=data.get("description", ""),
            version=data.get("version", 1),
            role=data.get("role", ""),
            rules=data.get("rules", ""),
            output_format=data.get("output_format", ""),
            memory=memory_config,
            tools_guidance=data.get("tools_guidance", "")
        )

    def build_system_prompt(self) -> str:
        """
        Build system prompt from config components.

        Returns:
            Complete system prompt string
        """
        parts = []

        if self.config.role:
            parts.append(self.config.role.strip())

        if self.config.tools_guidance:
            parts.append(self.config.tools_guidance.strip())

        if self.config.rules:
            parts.append(self.config.rules.strip())

        if self.config.output_format:
            parts.append(self.config.output_format.strip())

        return "\n\n".join(parts)

    def build_messages(
        self,
        user_message: str,
        conversation_messages: list = None,
        conversation_summary: Optional[str] = None,
        image_url: Optional[str] = None
    ) -> list[dict]:
        """
        Build complete messages array for LLM API.

        Args:
            user_message: Current user message
            conversation_messages: List of previous messages (dicts with role, content)
            conversation_summary: Summary of older conversation
            image_url: Optional image URL for multimodal

        Returns:
            List of message dicts for LLM API
        """
        messages = []

        # 1. System prompt
        system_prompt = self.build_system_prompt()
        messages.append({
            "role": "system",
            "content": system_prompt
        })

        # 2. Conversation summary (if exists)
        if conversation_summary:
            messages.append({
                "role": "system",
                "content": f"Tóm tắt conversation trước:\n{conversation_summary}"
            })

        # 3. Conversation history
        if conversation_messages:
            for msg in conversation_messages:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })

        # 4. Current user message
        if image_url:
            # Multimodal message with image
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": user_message},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            })
        else:
            messages.append({
                "role": "user",
                "content": user_message
            })

        return messages

    def build_from_request(
        self,
        user_message: str,
        conversation_id: Optional[str],
        messages_model,
        conversation_model,
        image_url: Optional[str] = None
    ) -> tuple[list[dict], Optional[object]]:
        """
        Build messages from a chat request.

        This is the main entry point for building prompts.

        Args:
            user_message: Current user message
            conversation_id: UUID of conversation (None for new)
            messages_model: ChatMessage Django model
            conversation_model: ChatConversation Django model
            image_url: Optional image URL

        Returns:
            Tuple of (messages list, conversation object or None)
        """
        # Get memory context
        context = self.memory_manager.get_conversation_context(
            conversation_id,
            messages_model,
            conversation_model
        )

        # Format previous messages
        history = self.memory_manager.format_messages_for_api(
            context["messages"]
        )

        # Build final messages
        messages = self.build_messages(
            user_message=user_message,
            conversation_messages=history,
            conversation_summary=context["summary"],
            image_url=image_url
        )

        return messages, context["conversation"]


# Singleton instance for default agent
_default_builder: Optional[PromptBuilder] = None


def get_prompt_builder(agent_name: str = "n8n_teacher") -> PromptBuilder:
    """
    Get prompt builder instance.

    Uses singleton pattern for default agent.

    Args:
        agent_name: Name of agent config

    Returns:
        PromptBuilder instance
    """
    global _default_builder

    if agent_name == "n8n_teacher":
        if _default_builder is None:
            _default_builder = PromptBuilder(agent_name)
        return _default_builder

    return PromptBuilder(agent_name)
