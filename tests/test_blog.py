"""
Tests for Blog API endpoints.
"""

import pytest

from apps.blog.models import Post, PostStatus


@pytest.mark.django_db
class TestBlogAPI:
    """Blog public API test cases."""

    def test_list_published_posts(self, api_client, admin_user):
        """Test listing only published posts."""
        # Create posts with different statuses
        Post.objects.create(
            title="Published Post",
            slug="published-post",
            status=PostStatus.PUBLISHED,
            author=admin_user,
        )
        Post.objects.create(
            title="Draft Post",
            slug="draft-post",
            status=PostStatus.DRAFT,
            author=admin_user,
        )

        response = api_client.get("/blog/")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Should only return published posts
        assert len(data["data"]) == 1
        assert data["data"][0]["title"] == "Published Post"

    def test_get_post_by_slug(self, api_client, admin_user):
        """Test getting a post by slug."""
        post = Post.objects.create(
            title="Test Post",
            slug="test-post",
            excerpt="Test excerpt",
            status=PostStatus.PUBLISHED,
            author=admin_user,
        )

        response = api_client.get("/blog/test-post")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["title"] == "Test Post"
        assert data["data"]["excerpt"] == "Test excerpt"

    def test_get_post_increments_view_count(self, api_client, admin_user):
        """Test that getting a post increments view count."""
        post = Post.objects.create(
            title="View Test",
            slug="view-test",
            status=PostStatus.PUBLISHED,
            author=admin_user,
            view_count=0,
        )

        # Get post twice
        api_client.get("/blog/view-test")
        api_client.get("/blog/view-test")

        post.refresh_from_db()
        assert post.view_count == 2

    def test_get_nonexistent_post(self, api_client):
        """Test getting a non-existent post returns 404."""
        response = api_client.get("/blog/nonexistent-slug")
        assert response.status_code == 404

    def test_filter_posts_by_category(self, api_client, admin_user):
        """Test filtering posts by category."""
        Post.objects.create(
            title="Tech Post",
            slug="tech-post",
            category="tech",
            status=PostStatus.PUBLISHED,
            author=admin_user,
        )
        Post.objects.create(
            title="News Post",
            slug="news-post",
            category="news",
            status=PostStatus.PUBLISHED,
            author=admin_user,
        )

        response = api_client.get("/blog/?category=tech")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["category"] == "tech"

    def test_filter_featured_posts(self, api_client, admin_user):
        """Test filtering featured posts."""
        Post.objects.create(
            title="Featured Post",
            slug="featured-post",
            is_featured=True,
            status=PostStatus.PUBLISHED,
            author=admin_user,
        )
        Post.objects.create(
            title="Regular Post",
            slug="regular-post",
            is_featured=False,
            status=PostStatus.PUBLISHED,
            author=admin_user,
        )

        response = api_client.get("/blog/?featured=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["isFeatured"] is True

    def test_post_tags_parsing(self, api_client, admin_user):
        """Test that tags are parsed correctly."""
        # Create post with string tags (legacy format)
        post = Post.objects.create(
            title="Tags Test",
            slug="tags-test",
            tags="tag1,tag2,tag3",
            status=PostStatus.PUBLISHED,
            author=admin_user,
        )

        response = api_client.get("/blog/tags-test")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["tags"] == ["tag1", "tag2", "tag3"]

    def test_post_with_list_tags(self, api_client, admin_user):
        """Test post with list tags format."""
        Post.objects.create(
            title="List Tags",
            slug="list-tags",
            tags=["tag1", "tag2"],
            status=PostStatus.PUBLISHED,
            author=admin_user,
        )

        response = api_client.get("/blog/list-tags")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["tags"] == ["tag1", "tag2"]

    def test_pagination(self, api_client, admin_user):
        """Test pagination works."""
        # Create 5 posts
        for i in range(5):
            Post.objects.create(
                title=f"Post {i}",
                slug=f"post-{i}",
                status=PostStatus.PUBLISHED,
                author=admin_user,
            )

        response = api_client.get("/blog/?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2

        response = api_client.get("/blog/?limit=2&offset=2")
        data = response.json()
        assert len(data["data"]) == 2
