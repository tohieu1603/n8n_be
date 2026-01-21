"""
Generate schemas for API.
"""

from ninja import Schema


class GenerateIn(Schema):
    prompt: str
    aspect_ratio: str = "1:1"
    model: str = "flux-1.1-pro"


class GenerateOut(Schema):
    task_id: str
    status: str


class GenerateStatusOut(Schema):
    status: str
    output: str | None = None
    error: str | None = None
