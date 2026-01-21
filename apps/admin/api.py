"""
Admin API endpoints - converted from admin.controller.ts
"""

import math
import re
from datetime import datetime, timezone
from uuid import UUID

from django.db.models import Sum
from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError

from utils.auth import AuthBearer, get_current_user
from apps.users.models import User, UserRole
from apps.usage.models import UsageLog, ActionType
from apps.billing.models import Payment, PaymentStatus
from apps.blog.models import Post, PostStatus
from apps.blog.schemas import (
    PostOut,
    PostDetailOut,
    PostsListOut,
    PostCreateIn,
    PostUpdateIn,
    PaginationOut as PostPaginationOut,
    AuthorOut,
)
from .schemas import (
    AdminUserOut,
    AdminUserUpdateIn,
    AdminStatsOut,
    UsersListOut,
    UserStatsOut,
    PaginationOut,
)

router = Router(auth=AuthBearer())


def require_admin(request: HttpRequest) -> User:
    """Require admin role."""
    user = get_current_user(request)
    if user.role != UserRole.ADMIN:
        raise HttpError(403, "Admin access required")
    return user


@router.get("/stats", response=AdminStatsOut)
def get_stats(request: HttpRequest):
    """Get admin dashboard stats."""
    require_admin(request)

    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    pro_users = User.objects.filter(is_pro=True).count()

    total_revenue = Payment.objects.filter(status=PaymentStatus.COMPLETED).aggregate(
        total=Sum("amount")
    )["total"] or 0
    total_revenue_usd = float(total_revenue) / 25000

    total_generations = UsageLog.objects.filter(action=ActionType.GENERATE_IMAGE).count()
    total_chats = UsageLog.objects.filter(
        action__in=[ActionType.CHAT, ActionType.CHAT_STREAM]
    ).count()

    return AdminStatsOut(
        totalUsers=total_users,
        activeUsers=active_users,
        proUsers=pro_users,
        totalRevenueUsd=total_revenue_usd,
        totalGenerations=total_generations,
        totalChats=total_chats,
    )


# IMPORTANT: /users/stats MUST be before /users/{user_id} to avoid UUID parse error
@router.get("/users/stats", response=UserStatsOut)
def get_user_stats(request: HttpRequest):
    """Get user statistics for admin dashboard."""
    require_admin(request)

    total = User.objects.count()
    active = User.objects.filter(is_active=True).count()
    pro = User.objects.filter(is_pro=True).count()
    verified = User.objects.filter(is_email_verified=True).count()
    admins = User.objects.filter(role=UserRole.ADMIN).count()

    return UserStatsOut(
        total=total,
        active=active,
        pro=pro,
        verified=verified,
        admins=admins,
    )


@router.get("/users", response=UsersListOut)
def list_users(
    request: HttpRequest,
    page: int = 1,
    limit: int = 10,
    search: str | None = None,
    role: str | None = None,
    isActive: bool | None = None,
    isPro: bool | None = None,
    isEmailVerified: bool | None = None,
    sortBy: str = "createdAt",
    sortOrder: str = "DESC",
):
    """List all users with pagination (admin only)."""
    require_admin(request)

    queryset = User.objects.all()

    # Filters
    if search:
        queryset = queryset.filter(email__icontains=search)
    if role:
        queryset = queryset.filter(role=role)
    if isActive is not None:
        queryset = queryset.filter(is_active=isActive)
    if isPro is not None:
        queryset = queryset.filter(is_pro=isPro)
    if isEmailVerified is not None:
        queryset = queryset.filter(is_email_verified=isEmailVerified)

    # Sorting - map camelCase to snake_case
    sort_map = {
        "createdAt": "created_at",
        "updatedAt": "updated_at",
        "email": "email",
        "name": "name",
        "creditsUsed": "credits_used",
    }
    sort_field = sort_map.get(sortBy, "created_at")
    if sortOrder.upper() == "DESC":
        sort_field = f"-{sort_field}"

    queryset = queryset.order_by(sort_field)

    # Pagination
    total = queryset.count()
    total_pages = math.ceil(total / limit) if limit > 0 else 1
    offset = (page - 1) * limit
    users = list(queryset[offset : offset + limit])

    return UsersListOut(
        users=[AdminUserOut.from_orm(u) for u in users],
        pagination=PaginationOut(
            page=page,
            limit=limit,
            total=total,
            totalPages=total_pages,
        ),
    )


@router.get("/users/{user_id}", response=AdminUserOut)
def get_user(request: HttpRequest, user_id: UUID):
    """Get user details (admin only)."""
    require_admin(request)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found")

    return AdminUserOut.from_orm(user)


@router.put("/users/{user_id}", response=AdminUserOut)
def update_user(request: HttpRequest, user_id: UUID, data: AdminUserUpdateIn):
    """Update user (admin only)."""
    require_admin(request)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found")

    if data.role is not None:
        user.role = data.role
    if data.tokenBalance is not None:
        user.token_balance = data.tokenBalance
    if data.isPro is not None:
        user.is_pro = data.isPro
    if data.isActive is not None:
        user.is_active = data.isActive

    user.save()
    return AdminUserOut.from_orm(user)


@router.patch("/users/{user_id}/role", response=AdminUserOut)
def update_user_role(request: HttpRequest, user_id: UUID, data: dict):
    """Update user role (admin only)."""
    require_admin(request)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found")

    if "role" in data:
        user.role = data["role"]
        user.save()

    return AdminUserOut.from_orm(user)


@router.patch("/users/{user_id}/status", response=AdminUserOut)
def update_user_status(request: HttpRequest, user_id: UUID, data: dict):
    """Update user active status (admin only)."""
    require_admin(request)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found")

    if "isActive" in data:
        user.is_active = data["isActive"]
        user.save()

    return AdminUserOut.from_orm(user)


@router.delete("/users/{user_id}")
def delete_user(request: HttpRequest, user_id: UUID):
    """Delete user (admin only)."""
    admin = require_admin(request)

    if admin.id == user_id:
        raise HttpError(400, "Cannot delete yourself")

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found")

    user.is_active = False
    user.save()

    return {"message": "User deactivated"}


# ==================== POSTS ====================


def slugify(text: str) -> str:
    """Generate slug from text."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text


def post_to_out(post: Post) -> PostOut:
    """Convert Post model to PostOut schema with author."""
    author = None
    if post.author:
        author = AuthorOut(id=post.author.id, name=post.author.name, email=post.author.email)

    return PostOut(
        id=post.id,
        title=post.title,
        slug=post.slug,
        excerpt=post.excerpt,
        coverImage=post.cover_image,
        status=post.status,
        tags=post.tags if isinstance(post.tags, list) else [],
        category=post.category,
        isFeatured=post.is_featured,
        readingTime=post.reading_time,
        viewCount=post.view_count,
        authorId=post.author_id,
        author=author,
        publishedAt=post.published_at,
        createdAt=post.created_at,
        updatedAt=post.updated_at,
    )


def post_to_detail(post: Post) -> PostDetailOut:
    """Convert Post model to PostDetailOut schema with author."""
    author = None
    if post.author:
        author = AuthorOut(id=post.author.id, name=post.author.name, email=post.author.email)

    return PostDetailOut(
        id=post.id,
        title=post.title,
        slug=post.slug,
        excerpt=post.excerpt,
        coverImage=post.cover_image,
        status=post.status,
        tags=post.tags if isinstance(post.tags, list) else [],
        category=post.category,
        isFeatured=post.is_featured,
        readingTime=post.reading_time,
        viewCount=post.view_count,
        authorId=post.author_id,
        author=author,
        publishedAt=post.published_at,
        createdAt=post.created_at,
        updatedAt=post.updated_at,
        blocks=post.blocks or [],
        seoMeta=post.seo_meta,
    )


@router.get("/posts", response=PostsListOut)
def list_posts(
    request: HttpRequest,
    page: int = 1,
    limit: int = 10,
    status: str | None = None,
    authorId: str | None = None,
    tag: str | None = None,
    search: str | None = None,
    sortBy: str = "createdAt",
    sortOrder: str = "DESC",
):
    """List all posts with pagination (admin only)."""
    require_admin(request)

    queryset = Post.objects.select_related("author").all()

    # Filters
    if status:
        queryset = queryset.filter(status=status)
    if authorId:
        queryset = queryset.filter(author_id=authorId)
    if search:
        queryset = queryset.filter(title__icontains=search)

    # Sorting
    sort_map = {
        "createdAt": "created_at",
        "updatedAt": "updated_at",
        "publishedAt": "published_at",
        "viewCount": "view_count",
        "title": "title",
    }
    sort_field = sort_map.get(sortBy, "created_at")
    if sortOrder.upper() == "DESC":
        sort_field = f"-{sort_field}"

    queryset = queryset.order_by(sort_field)

    # Pagination
    total = queryset.count()
    total_pages = math.ceil(total / limit) if limit > 0 else 1
    offset = (page - 1) * limit
    posts = list(queryset[offset : offset + limit])

    return PostsListOut(
        posts=[post_to_out(p) for p in posts],
        pagination=PostPaginationOut(
            page=page,
            limit=limit,
            total=total,
            totalPages=total_pages,
        ),
    )


@router.get("/posts/{post_id}", response=PostDetailOut)
def get_post(request: HttpRequest, post_id: UUID):
    """Get post details (admin only)."""
    require_admin(request)

    try:
        post = Post.objects.select_related("author").get(id=post_id)
    except Post.DoesNotExist:
        raise HttpError(404, "Post not found")

    return post_to_detail(post)


@router.post("/posts", response=PostDetailOut)
def create_post(request: HttpRequest, data: PostCreateIn):
    """Create a new post (admin only)."""
    user = require_admin(request)

    slug = data.slug or slugify(data.title)

    # Check unique slug
    if Post.objects.filter(slug=slug).exists():
        slug = f"{slug}-{Post.objects.count() + 1}"

    # Calculate reading time
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
        cover_image=data.coverImage,
        blocks=data.blocks,
        status=data.status,
        tags=data.tags or [],
        category=data.category,
        seo_meta=data.seoMeta,
        is_featured=data.isFeatured,
        reading_time=reading_time,
        author=user,
        published_at=datetime.now(timezone.utc) if data.status == "published" else None,
    )

    return post_to_detail(post)


@router.put("/posts/{post_id}", response=PostDetailOut)
def update_post(request: HttpRequest, post_id: UUID, data: PostUpdateIn):
    """Update a post (admin only)."""
    require_admin(request)

    try:
        post = Post.objects.select_related("author").get(id=post_id)
    except Post.DoesNotExist:
        raise HttpError(404, "Post not found")

    if data.title is not None:
        post.title = data.title
    if data.slug is not None:
        post.slug = data.slug
    if data.excerpt is not None:
        post.excerpt = data.excerpt
    if data.coverImage is not None:
        post.cover_image = data.coverImage
    if data.blocks is not None:
        post.blocks = data.blocks
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
    if data.seoMeta is not None:
        post.seo_meta = data.seoMeta
    if data.isFeatured is not None:
        post.is_featured = data.isFeatured

    post.save()
    return post_to_detail(post)


@router.post("/posts/{post_id}/publish", response=PostDetailOut)
def publish_post(request: HttpRequest, post_id: UUID):
    """Publish a post (admin only)."""
    require_admin(request)

    try:
        post = Post.objects.select_related("author").get(id=post_id)
    except Post.DoesNotExist:
        raise HttpError(404, "Post not found")

    post.status = PostStatus.PUBLISHED
    post.published_at = datetime.now(timezone.utc)
    post.save()

    return post_to_detail(post)


@router.post("/posts/{post_id}/unpublish", response=PostDetailOut)
def unpublish_post(request: HttpRequest, post_id: UUID):
    """Unpublish a post (admin only)."""
    require_admin(request)

    try:
        post = Post.objects.select_related("author").get(id=post_id)
    except Post.DoesNotExist:
        raise HttpError(404, "Post not found")

    post.status = PostStatus.DRAFT
    post.save()

    return post_to_detail(post)


@router.delete("/posts/{post_id}")
def delete_post(request: HttpRequest, post_id: UUID):
    """Delete a post (admin only)."""
    require_admin(request)

    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        raise HttpError(404, "Post not found")

    post.delete()
    return {"message": "Post deleted"}
