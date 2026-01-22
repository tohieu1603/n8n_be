import logging
from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class ChatConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.chat"

    def ready(self):
        """Called when the app is ready."""
        # Start MCP server if enabled
        mcp_enabled = getattr(settings, "MCP_ENABLED", True)

        if mcp_enabled:
            try:
                from agents import start_mcp_server
                start_mcp_server()
                logger.info("[Chat] MCP server started on app ready")
            except Exception as e:
                logger.error(f"[Chat] Failed to start MCP server: {e}")
