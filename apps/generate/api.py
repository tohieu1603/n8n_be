"""
Image generation API endpoints - converted from generate.controller.ts
"""

import httpx
from django.conf import settings
from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError

from utils.auth import AuthBearer, get_current_user
from apps.usage.models import UsageLog, ActionType
from .schemas import GenerateIn, GenerateOut, GenerateStatusOut

router = Router(auth=AuthBearer())

# Model costs (credits per generation)
MODEL_COSTS = {
    "flux-1.1-pro": 10,
    "flux-schnell": 5,
    "flux-dev": 8,
    "ideogram": 15,
}


@router.post("/", response=GenerateOut)
async def generate_image(request: HttpRequest, data: GenerateIn):
    """Generate an image using Replicate API."""
    user = get_current_user(request)

    # Check credits
    cost = MODEL_COSTS.get(data.model, 10)
    if user.token_balance < cost:
        raise HttpError(400, "Insufficient credits")

    # Call Replicate API
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.replicate.com/v1/predictions",
            headers={
                "Authorization": f"Token {settings.REPLICATE_API_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "version": get_model_version(data.model),
                "input": {
                    "prompt": data.prompt,
                    "aspect_ratio": data.aspect_ratio,
                },
            },
            timeout=30.0,
        )

    if response.status_code != 201:
        raise HttpError(500, "Failed to start image generation")

    result = response.json()
    task_id = result["id"]

    # Deduct credits
    user.token_balance -= cost
    await user.asave()

    # Log usage
    await UsageLog.objects.acreate(
        user=user,
        action=ActionType.GENERATE_IMAGE,
        credits_used=cost,
        metadata={
            "prompt": data.prompt,
            "task_id": task_id,
            "model": data.model,
            "aspect_ratio": data.aspect_ratio,
        },
    )

    return GenerateOut(task_id=task_id, status="starting")


@router.get("/status/{task_id}", response=GenerateStatusOut)
async def get_generation_status(request: HttpRequest, task_id: str):
    """Get image generation status."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.replicate.com/v1/predictions/{task_id}",
            headers={
                "Authorization": f"Token {settings.REPLICATE_API_TOKEN}",
            },
            timeout=10.0,
        )

    if response.status_code != 200:
        raise HttpError(404, "Task not found")

    result = response.json()
    status = result["status"]

    output = None
    error = None

    if status == "succeeded":
        output = result.get("output")
        if isinstance(output, list):
            output = output[0] if output else None
    elif status == "failed":
        error = result.get("error", "Generation failed")

    return GenerateStatusOut(status=status, output=output, error=error)


def get_model_version(model: str) -> str:
    """Get Replicate model version ID."""
    versions = {
        "flux-1.1-pro": "black-forest-labs/flux-1.1-pro",
        "flux-schnell": "black-forest-labs/flux-schnell",
        "flux-dev": "black-forest-labs/flux-dev",
    }
    return versions.get(model, versions["flux-1.1-pro"])
