"""
Prompt building module for chat API.

This module handles:
- System prompt construction
- Memory/conversation history management
- User request formatting
- Final prompt assembly for LLM API calls
"""

from .builder import PromptBuilder
from .n8n_teacher import N8N_TEACHER_PROMPT

__all__ = ["PromptBuilder", "N8N_TEACHER_PROMPT"]
