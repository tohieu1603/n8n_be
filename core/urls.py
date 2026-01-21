"""
URL configuration for ImageGen API.
"""

from django.urls import path

from .api import api

urlpatterns = [
    path("api/", api.urls),
]
