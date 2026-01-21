"""
Post model - converted from TypeORM Post entity.
"""

import uuid
from django.db import models
from apps.users.models import User


class PostStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    ARCHIVED = "archived", "Archived"


class Post(models.Model):
    """Blog post model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    excerpt = models.TextField(null=True, blank=True)
    cover_image = models.URLField(max_length=500, null=True, blank=True, db_column="coverImage")
    blocks = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=PostStatus.choices, default=PostStatus.DRAFT)
    tags = models.JSONField(default=list, null=True, blank=True)
    category = models.CharField(max_length=100, null=True, blank=True)
    seo_meta = models.JSONField(null=True, blank=True, db_column="seoMeta")
    is_featured = models.BooleanField(default=False, db_column="isFeatured")
    reading_time = models.IntegerField(default=0, db_column="readingTime")
    view_count = models.IntegerField(default=0, db_column="viewCount")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts", db_column="authorId")
    published_at = models.DateTimeField(null=True, blank=True, db_column="publishedAt")
    created_at = models.DateTimeField(auto_now_add=True, db_column="createdAt")
    updated_at = models.DateTimeField(auto_now=True, db_column="updatedAt")

    class Meta:
        db_table = "posts"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title
