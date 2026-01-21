"""
Django Ninja API configuration.
"""

from typing import Any
from ninja import NinjaAPI
from ninja.renderers import JSONRenderer
from ninja.errors import ValidationError, HttpError
from django.http import HttpRequest, HttpResponse
from pydantic import ValidationError as PydanticValidationError


class SuccessWrapperRenderer(JSONRenderer):
    """Wrap all responses in {success: true, data: ...} format for frontend compatibility."""

    def render(self, request: HttpRequest, data: Any, *, response_status: int) -> Any:
        # Don't wrap error responses (they already have success: false)
        if isinstance(data, dict) and "success" in data:
            return super().render(request, data, response_status=response_status)

        # Wrap success responses
        if 200 <= response_status < 300:
            wrapped = {"success": True, "data": data}
        else:
            wrapped = {"success": False, "error": data}

        return super().render(request, wrapped, response_status=response_status)


api = NinjaAPI(
    title="ImageGen API",
    version="2.0.0",
    description="AI Image Generation and Chat API",
    renderer=SuccessWrapperRenderer(),
)


@api.exception_handler(ValidationError)
def validation_errors(request: HttpRequest, exc: ValidationError) -> HttpResponse:
    return api.create_response(
        request,
        {"success": False, "error": exc.errors},
        status=422,
    )


@api.exception_handler(PydanticValidationError)
def pydantic_validation_errors(request: HttpRequest, exc: PydanticValidationError) -> HttpResponse:
    return api.create_response(
        request,
        {"success": False, "error": exc.errors()},
        status=422,
    )


@api.exception_handler(HttpError)
def http_error_handler(request: HttpRequest, exc: HttpError) -> HttpResponse:
    return api.create_response(
        request,
        {"success": False, "error": str(exc)},
        status=exc.status_code,
    )


@api.exception_handler(Exception)
def generic_error_handler(request: HttpRequest, exc: Exception) -> HttpResponse:
    return api.create_response(
        request,
        {"success": False, "error": str(exc)},
        status=500,
    )


# Health check
@api.get("/health")
def health_check(request: HttpRequest) -> dict:
    return {"status": "ok", "version": "2.0.0"}


# Import and register routers
from apps.auth.api import router as auth_router
from apps.users.api import router as users_router
from apps.keys.api import router as keys_router
from apps.billing.api import router as billing_router
from apps.chat.api import router as chat_router
from apps.usage.api import router as usage_router
from apps.blog.api import router as blog_router
from apps.generate.api import router as generate_router
from apps.convert.api import router as convert_router
from apps.admin.api import router as admin_router

api.add_router("/auth", auth_router, tags=["Auth"])
api.add_router("/users", users_router, tags=["Users"])
api.add_router("/keys", keys_router, tags=["API Keys"])
api.add_router("/billing", billing_router, tags=["Billing"])
api.add_router("/chat", chat_router, tags=["Chat"])
api.add_router("/usage", usage_router, tags=["Usage"])
api.add_router("/blog", blog_router, tags=["Blog"])
api.add_router("/generate", generate_router, tags=["Generate"])
api.add_router("/convert", convert_router, tags=["Convert"])
api.add_router("/admin", admin_router, tags=["Admin"])
