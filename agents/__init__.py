"""
Agents module - handles prompt building, memory management, and tool calling.

Structure:
- configs/: YAML files with agent configurations
- memory/: Memory management (conversation history)
- mcp/: MCP client for n8n integration
- tools/: Tool definitions and executor
- builder.py: Prompt building logic
"""

from .builder import PromptBuilder, get_prompt_builder
from .memory import MemoryManager
from .mcp import MCPClient, get_mcp_client, start_mcp_server, stop_mcp_server
from .tools import get_tool_definitions, ToolExecutor, get_tool_executor

__all__ = [
    "PromptBuilder",
    "get_prompt_builder",
    "MemoryManager",
    "MCPClient",
    "get_mcp_client",
    "start_mcp_server",
    "stop_mcp_server",
    "get_tool_definitions",
    "ToolExecutor",
    "get_tool_executor",
]
