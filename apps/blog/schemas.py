"""
Blog schemas for API.
"""

from datetime import datetime
from uuid import UUID
from typing import Any
from ninja import Schema
from pydantic import Field, ConfigDict


class AuthorOut(Schema):
    """Author info embedded in post."""

    id: UUID
    name: str | None = None
    email: str


class PostOut(Schema):
    """Post list output - camelCase for frontend."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    title: str
    slug: str
    excerpt: str | None = None
    coverImage: str | None = Field(validation_alias="cover_image", default=None)
    status: str
    tags: list[str] | None = None
    category: str | None = None
    isFeatured: bool = Field(validation_alias="is_featured", default=False)
    readingTime: int = Field(validation_alias="reading_time", default=0)
    viewCount: int = Field(validation_alias="view_count", default=0)
    authorId: UUID = Field(validation_alias="author_id")
    author: AuthorOut | None = None
    publishedAt: datetime | None = Field(validation_alias="published_at", default=None)
    createdAt: datetime = Field(validation_alias="created_at")
    updatedAt: datetime = Field(validation_alias="updated_at")


class PostDetailOut(PostOut):
    """Post detail output with blocks and SEO."""

    blocks: list[dict[str, Any]] = []
    seoMeta: dict[str, Any] | None = Field(validation_alias="seo_meta", default=None)


class PaginationOut(Schema):
    """Pagination info."""

    page: int
    limit: int
    total: int
    totalPages: int


class PostsListOut(Schema):
    """Paginated posts list response."""

    posts: list[PostOut]
    pagination: PaginationOut


class PostCreateIn(Schema):
    """Post create input."""

    title: str
    slug: str | None = None
    excerpt: str | None = None
    coverImage: str | None = None
    blocks: list[dict[str, Any]] = []
    status: str = "draft"
    tags: list[str] | None = None
    category: str | None = None
    seoMeta: dict[str, Any] | None = None
    isFeatured: bool = False


class PostUpdateIn(Schema):
    """Post update input."""

    title: str | None = None
    slug: str | None = None
    excerpt: str | None = None
    coverImage: str | None = None
    blocks: list[dict[str, Any]] | None = None
    status: str | None = None
    tags: list[str] | None = None
    category: str | None = None
    seoMeta: dict[str, Any] | None = None
    isFeatured: bool | None = None
