"""
MCP (Model Context Protocol) client for n8n integration.

Communicates with n8n-mcp server to get node information.
The server is started once and kept running for all requests.
"""

from .client import MCPClient, get_mcp_client, start_mcp_server, stop_mcp_server

__all__ = ["MCPClient", "get_mcp_client", "start_mcp_server", "stop_mcp_server"]
