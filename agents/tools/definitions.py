"""
Tool definitions for LLM function calling.

These tools are dynamically loaded from MCP server, not hardcoded.
Format follows OpenAI/Gemini function calling specification.
"""

import logging
from typing import Any, Optional
import asyncio

logger = logging.getLogger(__name__)

# Cached tools from MCP server
_cached_tools: Optional[list[dict[str, Any]]] = None

# Fallback tools if MCP server is unavailable (DEPRECATED)
_FALLBACK_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_n8n_nodes",
            "description": "Tìm kiếm các node n8n phù hợp với yêu cầu. Trả về thông tin chi tiết về nodes bao gồm displayName, description, category và hướng dẫn sử dụng. Sử dụng khi cần tìm node để thực hiện một tác vụ cụ thể như gửi email, gọi API, xử lý dữ liệu, đăng bài lên mạng xã hội, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Từ khóa tìm kiếm (tiếng Anh). Ví dụ: 'send email', 'http request', 'google sheets', 'telegram', 'facebook post'"
                    }
                },
                "required": ["query"]
            }
        }
    },
    # DISABLED: MCP server doesn't support get_node_details/get_node_info
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "get_node_details",
    #         "description": "Lấy thông tin chi tiết về một node n8n cụ thể bao gồm: parameters, credentials cần thiết, inputs/outputs. Sử dụng khi đã biết tên node và cần biết cách cấu hình nó.",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "node_type": {
    #                     "type": "string",
    #                     "description": "Tên type của node. Ví dụ: 'n8n-nodes-base.telegram', 'n8n-nodes-base.httpRequest'"
    #                 }
    #             },
    #             "required": ["node_type"]
    #         }
    #     }
    # },
    {
        "type": "function",
        "function": {
            "name": "list_node_categories",
            "description": "Liệt kê tất cả các category của nodes trong n8n. Sử dụng khi muốn khám phá các loại node có sẵn.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_nodes_by_category",
            "description": "Lấy danh sách nodes trong một category cụ thể. Ví dụ: 'Marketing', 'Communication', 'Data & Storage'",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Tên category. Ví dụ: 'Communication', 'Marketing', 'Data & Storage'"
                    }
                },
                "required": ["category"]
            }
        }
    }
]

# Keep for backward compatibility
N8N_TOOLS = _FALLBACK_TOOLS


def _convert_mcp_tool_to_llm_format(mcp_tool: dict) -> dict:
    """
    Convert MCP tool definition to LLM API format (OpenAI/Gemini).

    MCP format:
    {
        "name": "search_nodes",
        "description": "...",
        "inputSchema": {"type": "object", "properties": {...}}
    }

    LLM format:
    {
        "type": "function",
        "function": {
            "name": "search_nodes",
            "description": "...",
            "parameters": {"type": "object", "properties": {...}}
        }
    }
    """
    return {
        "type": "function",
        "function": {
            "name": mcp_tool.get("name", ""),
            "description": mcp_tool.get("description", ""),
            "parameters": mcp_tool.get("inputSchema", {"type": "object", "properties": {}})
        }
    }


async def _load_tools_from_mcp() -> list[dict[str, Any]]:
    """Load tools from MCP server."""
    try:
        from ..mcp import get_mcp_client

        client = get_mcp_client()
        result = await client.list_tools()

        if result.success and result.data:
            tools_data = result.data
            # MCP returns {"tools": [...]}
            if isinstance(tools_data, dict) and "tools" in tools_data:
                mcp_tools = tools_data["tools"]
                # Convert to LLM format
                llm_tools = [_convert_mcp_tool_to_llm_format(tool) for tool in mcp_tools]
                logger.info(f"[ToolDefinitions] Loaded {len(llm_tools)} tools from MCP server")
                return llm_tools

        logger.warning("[ToolDefinitions] Failed to load tools from MCP, using fallback")
        return _FALLBACK_TOOLS
    except Exception as e:
        logger.error(f"[ToolDefinitions] Error loading tools from MCP: {e}")
        return _FALLBACK_TOOLS


def get_tool_definitions(force_reload: bool = False) -> list[dict[str, Any]]:
    """
    Get tool definitions for LLM API.

    Loads tools from MCP server on first call, then caches.

    Args:
        force_reload: Force reload from MCP server

    Returns:
        List of tool definitions in OpenAI/Gemini format
    """
    global _cached_tools

    # Return cached if available
    if _cached_tools and not force_reload:
        return _cached_tools

    # Load from MCP server
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # No event loop in current thread, create new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tools = loop.run_until_complete(_load_tools_from_mcp())
        loop.close()
    else:
        # Use existing event loop
        tools = loop.run_until_complete(_load_tools_from_mcp())

    _cached_tools = tools
    return tools


def format_tools_for_prompt(tools: list[dict] = None) -> str:
    """
    Format tool definitions as text for prompt injection.

    Used when the LLM API doesn't support native function calling.

    Args:
        tools: Tool definitions (defaults to N8N_TOOLS)

    Returns:
        Formatted string describing available tools
    """
    if tools is None:
        tools = N8N_TOOLS

    lines = ["AVAILABLE TOOLS:", ""]

    for tool in tools:
        func = tool.get("function", {})
        name = func.get("name", "")
        desc = func.get("description", "")
        params = func.get("parameters", {}).get("properties", {})

        lines.append(f"## {name}")
        lines.append(f"Description: {desc}")

        if params:
            lines.append("Parameters:")
            for param_name, param_info in params.items():
                param_desc = param_info.get("description", "")
                param_type = param_info.get("type", "string")
                lines.append(f"  - {param_name} ({param_type}): {param_desc}")

        lines.append("")

    return "\n".join(lines)
