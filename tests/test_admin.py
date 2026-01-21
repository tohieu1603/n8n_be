"""
Tests for Admin API endpoints.
"""

import pytest

from apps.users.models import User, UserRole
from apps.blog.models import Post, PostStatus


@pytest.mark.django_db
class TestAdminUsersAPI:
    """Admin Users API test cases."""

    def test_list_users_as_admin(self, api_client, auth_headers, admin_user):
        """Test listing users as admin."""
        response = api_client.get("/admin/users", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "users" in data["data"]
        assert "pagination" in data["data"]

    def test_list_users_as_regular_user(self, api_client, user_auth_headers):
        """Test that regular users cannot list users."""
        response = api_client.get("/admin/users", headers=user_auth_headers)
        assert response.status_code == 403

    def test_get_user_stats(self, api_client, auth_headers):
        """Test getting user stats."""
        response = api_client.get("/admin/users/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "totalUsers" in data["data"]

    def test_get_user_by_id(self, api_client, auth_headers, regular_user):
        """Test getting a specific user."""
        response = api_client.get(
            f"/admin/users/{regular_user.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["email"] == regular_user.email

    def test_update_user(self, api_client, auth_headers, regular_user):
        """Test updating a user."""
        response = api_client.put(
            f"/admin/users/{regular_user.id}",
            json={"name": "Updated Name", "tokenBalance": 50000},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "Updated Name"
        assert data["data"]["tokenBalance"] == 50000

    def test_update_user_role(self, api_client, auth_headers, regular_user):
        """Test updating user role."""
        response = api_client.patch(
            f"/admin/users/{regular_user.id}/role",
            json={"role": "admin"},
            headers=auth_headers,
        )
        assert response.status_code == 200

        regular_user.refresh_from_db()
        assert regular_user.role == UserRole.ADMIN

    def test_deactivate_user(self, api_client, auth_headers, regular_user):
        """Test deactivating a user."""
        response = api_client.patch(
            f"/admin/users/{regular_user.id}/status",
            headers=auth_headers,
        )
        assert response.status_code == 200

        regular_user.refresh_from_db()
        assert regular_user.is_active is False


@pytest.mark.django_db
class TestAdminPostsAPI:
    """Admin Posts API test cases."""

    def test_list_posts(self, api_client, auth_headers, admin_user):
        """Test listing posts."""
        # Create a test post
        Post.objects.create(
            title="Test Post",
            slug="test-post",
            status=PostStatus.PUBLISHED,
            author=admin_user,
        )

        response = api_client.get("/admin/posts", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "posts" in data["data"]
        assert "pagination" in data["data"]

    def test_create_post(self, api_client, auth_headers):
        """Test creating a post."""
        response = api_client.post(
            "/admin/posts",
            json={
                "title": "New Post",
                "blocks": [],
                "status": "draft",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["title"] == "New Post"
        assert data["data"]["slug"] == "new-post"

    def test_update_post(self, api_client, auth_headers, admin_user):
        """Test updating a post."""
        post = Post.objects.create(
            title="Original",
            slug="original",
            author=admin_user,
        )

        response = api_client.put(
            f"/admin/posts/{post.id}",
            json={"title": "Updated Title"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["title"] == "Updated Title"

    def test_publish_post(self, api_client, auth_headers, admin_user):
        """Test publishing a post."""
        post = Post.objects.create(
            title="Draft Post",
            slug="draft-post",
            status=PostStatus.DRAFT,
            author=admin_user,
        )

        response = api_client.post(
            f"/admin/posts/{post.id}/publish",
            headers=auth_headers,
        )
        assert response.status_code == 200

        post.refresh_from_db()
        assert post.status == PostStatus.PUBLISHED
        assert post.published_at is not None

    def test_unpublish_post(self, api_client, auth_headers, admin_user):
        """Test unpublishing a post."""
        post = Post.objects.create(
            title="Published Post",
            slug="published-post",
            status=PostStatus.PUBLISHED,
            author=admin_user,
        )

        response = api_client.post(
            f"/admin/posts/{post.id}/unpublish",
            headers=auth_headers,
        )
        assert response.status_code == 200

        post.refresh_from_db()
        assert post.status == PostStatus.DRAFT

    def test_delete_post(self, api_client, auth_headers, admin_user):
        """Test deleting a post."""
        post = Post.objects.create(
            title="To Delete",
            slug="to-delete",
            author=admin_user,
        )

        response = api_client.delete(
            f"/admin/posts/{post.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert not Post.objects.filter(id=post.id).exists()


@pytest.mark.django_db
class TestAdminStatsAPI:
    """Admin Stats API test cases."""

    def test_get_admin_stats(self, api_client, auth_headers):
        """Test getting admin dashboard stats."""
        response = api_client.get("/admin/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "totalUsers" in data["data"]
        assert "totalRevenue" in data["data"]
