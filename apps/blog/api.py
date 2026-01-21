"""
Blog API endpoints - converted from blog routes.
"""

import re
from datetime import datetime, timezone

from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError

from utils.auth import AuthBearer, OptionalAuthBearer, get_current_user
from apps.users.models import UserRole
from .models import Post, PostStatus
from .schemas import PostOut, PostDetailOut, PostCreateIn, PostUpdateIn

router = Router()


def slugify(text: str) -> str:
    """Generate slug from text."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text


@router.get("/", response=list[PostOut])
def list_posts(
    request: HttpRequest,
    status: str | None = None,
    category: str | None = None,
    featured: bool | None = None,
    limit: int = 20,
    offset: int = 0,
):
    """List published posts."""
    queryset = Post.objects.filter(status=PostStatus.PUBLISHED)

    if category:
        queryset = queryset.filter(category=category)
    if featured is not None:
        queryset = queryset.filter(is_featured=featured)

    posts = queryset.order_by("-published_at")[offset : offset + limit]
    return list(posts)


@router.get("/{slug}", response=PostDetailOut)
def get_post(request: HttpRequest, slug: str):
    """Get a post by slug."""
    try:
        post = Post.objects.get(slug=slug)
    except Post.DoesNotExist:
        raise HttpError(404, "Post not found")

    # Increment view count
    post.view_count += 1
    post.save(update_fields=["view_count"])

    return post


@router.post("/", response=PostDetailOut, auth=AuthBearer())
def create_post(request: HttpRequest, data: PostCreateIn):
    """Create a new post (admin only)."""
    user = get_current_user(request)

    if user.role != UserRole.ADMIN:
        raise HttpError(403, "Admin access required")

    slug = data.slug or slugify(data.title)

    # Check unique slug
    if Post.objects.filter(slug=slug).exists():
        slug = f"{slug}-{Post.objects.count() + 1}"

    # Calculate reading time (rough estimate: 200 words/min)
    word_count = sum(
        len(str(block.get("data", {}).get("text", "")).split())
        for block in data.blocks
        if block.get("type") in ["text", "heading", "quote"]
    )
    reading_time = max(1, word_count // 200)

    post = Post.objects.create(
        title=data.title,
        slug=slug,
        excerpt=data.excerpt,
        cover_image=data.cover_image,
        blocks=data.blocks,
        status=data.status,
        tags=data.tags,
        category=data.category,
        seo_meta=data.seo_meta,
        is_featured=data.is_featured,
        reading_time=reading_time,
        author=user,
        published_at=datetime.now(timezone.utc) if data.status == "published" else None,
    )

    return post


@router.put("/{post_id}", response=PostDetailOut, auth=AuthBearer())
def update_post(request: HttpRequest, post_id: str, data: PostUpdateIn):
    """Update a post (admin only)."""
    user = get_current_user(request)

    if user.role != UserRole.ADMIN:
        raise HttpError(403, "Admin access required")

    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        raise HttpError(404, "Post not found")

    # Update fields
    if data.title is not None:
        post.title = data.title
    if data.slug is not None:
        post.slug = data.slug
    if data.excerpt is not None:
        post.excerpt = data.excerpt
    if data.cover_image is not None:
        post.cover_image = data.cover_image
    if data.blocks is not None:
        post.blocks = data.blocks
        # Recalculate reading time
        word_count = sum(
            len(str(block.get("data", {}).get("text", "")).split())
            for block in data.blocks
            if block.get("type") in ["text", "heading", "quote"]
        )
        post.reading_time = max(1, word_count // 200)
    if data.status is not None:
        if data.status == "published" and post.status != "published":
            post.published_at = datetime.now(timezone.utc)
        post.status = data.status
    if data.tags is not None:
        post.tags = data.tags
    if data.category is not None:
        post.category = data.category
    if data.seo_meta is not None:
        post.seo_meta = data.seo_meta
    if data.is_featured is not None:
        post.is_featured = data.is_featured

    post.save()
    return post


@router.delete("/{post_id}", auth=AuthBearer())
def delete_post(request: HttpRequest, post_id: str):
    """Delete a post (admin only)."""
    user = get_current_user(request)

    if user.role != UserRole.ADMIN:
        raise HttpError(403, "Admin access required")

    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        raise HttpError(404, "Post not found")

    post.delete()
    return {"message": "Post deleted"}
