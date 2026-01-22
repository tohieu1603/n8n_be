"""
Workflow API schemas.
"""

from typing import Any
from ninja import Schema


class CreateWorkflowIn(Schema):
    """Request to create a workflow in n8n."""
    workflow: dict[str, Any]  # The n8n workflow JSON


class WorkflowOut(Schema):
    """Response after creating a workflow."""
    success: bool
    workflowId: str | None = None
    workflowUrl: str | None = None
    error: str | None = None
