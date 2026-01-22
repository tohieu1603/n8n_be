"""
Tool Executor - executes tool calls from LLM responses.

Maps LLM tool calls to actual MCP client calls and formats results.
"""

import json
import logging
from typing import Any, Optional
from dataclasses import dataclass

from ..mcp import MCPClient, get_mcp_client

logger = logging.getLogger(__name__)


@dataclass
class ToolCallResult:
    """Result of a tool call execution."""
    tool_name: str
    tool_call_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None

    def to_message(self) -> dict:
        """Convert to message format for LLM API."""
        if self.success:
            content = json.dumps(self.result, ensure_ascii=False) if isinstance(self.result, (dict, list)) else str(self.result)
        else:
            content = json.dumps({"error": self.error}, ensure_ascii=False)

        return {
            "role": "tool",
            "tool_call_id": self.tool_call_id,
            "content": content
        }


class ToolExecutor:
    """
    Executes tool calls from LLM responses.

    Maps tool names to MCP client methods and handles execution.
    """

    def __init__(self, mcp_client: MCPClient = None):
        """
        Initialize tool executor.

        Args:
            mcp_client: MCP client instance (uses singleton if not provided)
        """
        self.mcp_client = mcp_client or get_mcp_client()

        # No more hardcoded mapping - call MCP server directly

    async def execute_tool_calls(self, tool_calls: list[dict]) -> list[ToolCallResult]:
        """
        Execute a list of tool calls.

        Args:
            tool_calls: List of tool call objects from LLM response
                Each has: id, type, function (name, arguments)

        Returns:
            List of ToolCallResult objects
        """
        logger.info(f"[ToolExecutor] Executing {len(tool_calls)} tool calls")
        results = []

        for i, tool_call in enumerate(tool_calls):
            logger.info(f"[ToolExecutor] Processing tool call {i+1}/{len(tool_calls)}: {tool_call}")
            result = await self.execute_single(tool_call)
            logger.info(f"[ToolExecutor] Result: success={result.success}, error={result.error}")
            results.append(result)

        return results

    async def execute_single(self, tool_call: dict) -> ToolCallResult:
        """
        Execute a single tool call.

        Args:
            tool_call: Tool call object with id, type, function

        Returns:
            ToolCallResult
        """
        tool_call_id = tool_call.get("id", "")
        function_info = tool_call.get("function", {})
        tool_name = function_info.get("name", "")

        logger.info(f"[ToolExecutor] Executing tool: {tool_name}, id: {tool_call_id}")

        # Parse arguments
        try:
            arguments_str = function_info.get("arguments", "{}")
            if isinstance(arguments_str, str):
                arguments = json.loads(arguments_str)
            else:
                arguments = arguments_str
        except json.JSONDecodeError:
            return ToolCallResult(
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                success=False,
                error="Invalid JSON arguments"
            )

        # Call MCP server directly with tool name from LLM
        try:
            result = await self.mcp_client.call_tool(tool_name, arguments)
            return ToolCallResult(
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                success=result.success,
                result=result.data,
                error=result.error
            )
        except Exception as e:
            logger.error(f"Tool execution error: {tool_name} - {e}")
            return ToolCallResult(
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                success=False,
                error=str(e)
            )

    # No more hardcoded tool handlers - all tools are called directly via MCP


def format_tool_results_for_prompt(results: list[ToolCallResult]) -> str:
    """
    Format tool results as text for prompt.

    Used when the LLM API doesn't support native tool messages.

    Args:
        results: List of tool call results

    Returns:
        Formatted string with tool results
    """
    lines = ["TOOL RESULTS:", ""]

    for result in results:
        lines.append(f"## {result.tool_name}")
        if result.success:
            if isinstance(result.result, (dict, list)):
                lines.append(json.dumps(result.result, ensure_ascii=False, indent=2))
            else:
                lines.append(str(result.result))
        else:
            lines.append(f"Error: {result.error}")
        lines.append("")

    return "\n".join(lines)


# Singleton instance
_tool_executor: Optional[ToolExecutor] = None


def get_tool_executor() -> ToolExecutor:
    """Get tool executor instance (singleton)."""
    global _tool_executor

    if _tool_executor is None:
        _tool_executor = ToolExecutor()

    return _tool_executor
