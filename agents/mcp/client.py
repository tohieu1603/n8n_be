"""
MCP Client - communicates with n8n-mcp server via stdio.

The n8n-mcp server provides tools to:
- Search n8n nodes
- Get node details (parameters, inputs, outputs)
- Get workflow templates

This client starts the MCP server once and keeps it running for all requests.
"""

import json
import subprocess
import asyncio
import logging
import shutil
import sys
import threading
import time
from typing import Optional, Any
from dataclasses import dataclass
from queue import Queue, Empty

logger = logging.getLogger(__name__)


@dataclass
class MCPToolResult:
    """Result from an MCP tool call."""
    success: bool
    data: Any = None
    error: Optional[str] = None


class MCPClient:
    """
    Client for n8n-mcp server.

    Starts the MCP server as a persistent process and communicates via stdio.
    """

    def __init__(self, server_command: list[str] = None, auto_start: bool = True):
        """
        Initialize MCP client.

        Args:
            server_command: Command to start MCP server
            auto_start: Whether to start the server immediately
        """
        self.server_command = server_command or ["npx", "-y", "n8n-mcp"]
        self._process: Optional[subprocess.Popen] = None
        self._request_id = 0
        self._lock = threading.Lock()
        self._response_queue: Queue = Queue()
        self._reader_thread: Optional[threading.Thread] = None
        self._running = False
        self._initialized = False

        logger.info(f"[MCP] Initialized with command: {self.server_command}")

        if auto_start:
            self.start_server()

    def _get_request_id(self) -> int:
        """Get next request ID."""
        self._request_id += 1
        return self._request_id

    def _check_npx_available(self) -> tuple[bool, str]:
        """Check if npx is available in PATH."""
        npx_name = "npx.cmd" if sys.platform == "win32" else "npx"
        npx_path = shutil.which(npx_name)

        if npx_path:
            return True, npx_path

        if sys.platform == "win32":
            npx_path = shutil.which("npx")
            if npx_path:
                return True, npx_path

        return False, ""

    def start_server(self) -> bool:
        """
        Start the MCP server process.

        Returns:
            True if server started successfully
        """
        if self._running and self._process and self._process.poll() is None:
            logger.info("[MCP] Server already running")
            return True

        npx_available, npx_path = self._check_npx_available()
        if not npx_available:
            logger.error("[MCP] npx not found. Please install Node.js")
            return False

        try:
            logger.info(f"[MCP] Starting server: {' '.join(self.server_command)}")

            # Start process with pipes
            if sys.platform == "win32":
                self._process = subprocess.Popen(
                    self.server_command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True,
                    bufsize=0,
                )
            else:
                self._process = subprocess.Popen(
                    self.server_command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=0,
                )

            self._running = True

            # Start reader thread
            self._reader_thread = threading.Thread(target=self._read_stdout, daemon=True)
            self._reader_thread.start()

            # Start stderr reader thread
            self._stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
            self._stderr_thread.start()

            # Wait for server to be ready
            time.sleep(1.0)

            if self._process.poll() is not None:
                logger.error(f"[MCP] Server process died with code: {self._process.returncode}")
                return False

            logger.info("[MCP] Server started successfully")
            self._initialized = True
            return True

        except Exception as e:
            logger.exception(f"[MCP] Failed to start server: {e}")
            return False

    def _read_stdout(self):
        """Read stdout from MCP server in a separate thread."""
        buffer = ""
        while self._running and self._process:
            try:
                if self._process.stdout is None:
                    break

                char = self._process.stdout.read(1)
                if not char:
                    if self._process.poll() is not None:
                        logger.warning("[MCP] Server process ended")
                        break
                    continue

                char = char.decode('utf-8', errors='ignore')
                buffer += char

                # Check for complete JSON line
                if char == '\n':
                    line = buffer.strip()
                    buffer = ""

                    if line.startswith('{'):
                        try:
                            response = json.loads(line)
                            self._response_queue.put(response)
                            logger.debug(f"[MCP] Received response: {line[:200]}")
                        except json.JSONDecodeError:
                            logger.debug(f"[MCP] Non-JSON line: {line[:100]}")
                    elif line:
                        logger.debug(f"[MCP] Server output: {line[:100]}")

            except Exception as e:
                if self._running:
                    logger.error(f"[MCP] Error reading stdout: {e}")
                break

    def _read_stderr(self):
        """Read stderr from MCP server."""
        while self._running and self._process:
            try:
                if self._process.stderr is None:
                    break

                line = self._process.stderr.readline()
                if not line:
                    if self._process.poll() is not None:
                        break
                    continue

                line = line.decode('utf-8', errors='ignore').strip()
                if line:
                    # Log but don't treat as error - n8n-mcp outputs info to stderr
                    logger.debug(f"[MCP] stderr: {line[:200]}")

            except Exception as e:
                if self._running:
                    logger.error(f"[MCP] Error reading stderr: {e}")
                break

    def stop_server(self):
        """Stop the MCP server process."""
        self._running = False

        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except:
                try:
                    self._process.kill()
                except:
                    pass
            self._process = None

        logger.info("[MCP] Server stopped")

    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running and self._process and self._process.poll() is None

    def _ensure_server_running(self) -> bool:
        """Ensure server is running, restart if needed."""
        if not self.is_running():
            logger.warning("[MCP] Server not running, attempting restart...")
            return self.start_server()
        return True

    def _send_request(self, method: str, params: dict = None) -> MCPToolResult:
        """
        Send a synchronous request to MCP server.

        Args:
            method: JSON-RPC method name
            params: Method parameters

        Returns:
            MCPToolResult
        """
        if not self._ensure_server_running():
            return MCPToolResult(success=False, error="MCP server not running")

        request = {
            "jsonrpc": "2.0",
            "id": self._get_request_id(),
            "method": method,
            "params": params or {}
        }

        request_id = request["id"]
        logger.info(f"[MCP] Sending request {request_id}: {method}")

        try:
            with self._lock:
                # Clear old responses
                while not self._response_queue.empty():
                    try:
                        self._response_queue.get_nowait()
                    except Empty:
                        break

                # Send request
                request_json = json.dumps(request) + "\n"
                self._process.stdin.write(request_json.encode())
                self._process.stdin.flush()

            # Wait for response
            try:
                response = self._response_queue.get(timeout=30.0)
            except Empty:
                logger.error(f"[MCP] Timeout waiting for response to request {request_id}")
                return MCPToolResult(success=False, error="Request timeout")

            # Check for error
            if "error" in response:
                error_msg = response["error"].get("message", "Unknown error")
                logger.error(f"[MCP] Server error: {error_msg}")
                return MCPToolResult(success=False, error=error_msg)

            logger.info(f"[MCP] Request {request_id} successful")
            return MCPToolResult(success=True, data=response.get("result"))

        except Exception as e:
            logger.exception(f"[MCP] Request error: {e}")
            return MCPToolResult(success=False, error=str(e))

    async def _call_server(self, method: str, params: dict = None) -> MCPToolResult:
        """
        Call MCP server method (async wrapper).

        Args:
            method: JSON-RPC method name
            params: Method parameters

        Returns:
            MCPToolResult
        """
        # Run sync method in executor to not block event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._send_request, method, params)

    async def list_tools(self) -> MCPToolResult:
        """List available tools from MCP server."""
        return await self._call_server("tools/list")

    async def call_tool(self, tool_name: str, arguments: dict = None) -> MCPToolResult:
        """
        Call an MCP tool.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            MCPToolResult
        """
        logger.info(f"[MCP] Calling tool: {tool_name}")
        return await self._call_server("tools/call", {
            "name": tool_name,
            "arguments": arguments or {}
        })

    # Convenience methods

    async def search_nodes(self, query: str) -> MCPToolResult:
        """Search n8n nodes by query."""
        return await self.call_tool("search_nodes", {"query": query})

    async def get_node_info(self, node_type: str) -> MCPToolResult:
        """Get detailed information about a specific node."""
        return await self.call_tool("get_node_info", {"nodeType": node_type})

    async def list_node_categories(self) -> MCPToolResult:
        """List all node categories."""
        return await self.call_tool("list_node_categories")

    async def get_nodes_by_category(self, category: str) -> MCPToolResult:
        """Get nodes in a specific category."""
        return await self.call_tool("get_nodes_by_category", {"category": category})

    def __del__(self):
        """Cleanup on deletion."""
        self.stop_server()


# Singleton instance
_mcp_client: Optional[MCPClient] = None
_mcp_lock = threading.Lock()


def get_mcp_client(server_command: list[str] = None) -> MCPClient:
    """
    Get MCP client instance (singleton).

    Starts the MCP server if not already running.

    Args:
        server_command: Optional custom server command

    Returns:
        MCPClient instance
    """
    global _mcp_client

    with _mcp_lock:
        if _mcp_client is None:
            _mcp_client = MCPClient(server_command)
            logger.info("[MCP] Created new MCPClient instance")

    return _mcp_client


def start_mcp_server():
    """Start the MCP server (call this on Django startup)."""
    client = get_mcp_client()
    if client.start_server():
        logger.info("[MCP] Server started on Django startup")
    else:
        logger.error("[MCP] Failed to start server on Django startup")


def stop_mcp_server():
    """Stop the MCP server (call this on Django shutdown)."""
    global _mcp_client
    if _mcp_client:
        _mcp_client.stop_server()
        _mcp_client = None
        logger.info("[MCP] Server stopped on Django shutdown")
