"""Tests for API client."""

import os
from unittest.mock import patch, AsyncMock

import pytest
import httpx

from productive_time_mcp.api import (
    ProductiveClient,
    get_client,
    reset_client,
    set_client,
    API_BASE,
)


class TestProductiveClientInit:
    """Tests for ProductiveClient initialization."""

    def test_init_with_env_vars(self, monkeypatch):
        """Test client initialization with environment variables."""
        monkeypatch.setenv("PRODUCTIVE_API_TOKEN", "test-token")
        monkeypatch.setenv("PRODUCTIVE_ORG_ID", "test-org")
        monkeypatch.setenv("PRODUCTIVE_USER_ID", "test-user")

        client = ProductiveClient()

        assert client.api_token == "test-token"
        assert client.org_id == "test-org"
        assert client.user_id == "test-user"
        assert client.headers["X-Auth-Token"] == "test-token"
        assert client.headers["X-Organization-Id"] == "test-org"

    def test_init_with_explicit_params(self, monkeypatch):
        """Test client initialization with explicit parameters."""
        monkeypatch.delenv("PRODUCTIVE_API_TOKEN", raising=False)
        monkeypatch.delenv("PRODUCTIVE_ORG_ID", raising=False)

        client = ProductiveClient(
            api_token="explicit-token",
            org_id="explicit-org",
            user_id="explicit-user",
        )

        assert client.api_token == "explicit-token"
        assert client.org_id == "explicit-org"
        assert client.user_id == "explicit-user"

    def test_init_missing_token_raises(self, monkeypatch):
        """Test that missing API token raises ValueError."""
        monkeypatch.delenv("PRODUCTIVE_API_TOKEN", raising=False)
        monkeypatch.setenv("PRODUCTIVE_ORG_ID", "test-org")

        with pytest.raises(ValueError, match="PRODUCTIVE_API_TOKEN is required"):
            ProductiveClient()

    def test_init_missing_org_raises(self, monkeypatch):
        """Test that missing org ID raises ValueError."""
        monkeypatch.setenv("PRODUCTIVE_API_TOKEN", "test-token")
        monkeypatch.delenv("PRODUCTIVE_ORG_ID", raising=False)

        with pytest.raises(ValueError, match="PRODUCTIVE_ORG_ID is required"):
            ProductiveClient()

    def test_user_id_optional(self, monkeypatch):
        """Test that user_id is optional."""
        monkeypatch.setenv("PRODUCTIVE_API_TOKEN", "test-token")
        monkeypatch.setenv("PRODUCTIVE_ORG_ID", "test-org")
        monkeypatch.delenv("PRODUCTIVE_USER_ID", raising=False)

        client = ProductiveClient()

        assert client.user_id is None


class TestProductiveClientRequests:
    """Tests for ProductiveClient HTTP methods."""

    @pytest.fixture
    def client(self, monkeypatch):
        """Create a test client."""
        monkeypatch.setenv("PRODUCTIVE_API_TOKEN", "test-token")
        monkeypatch.setenv("PRODUCTIVE_ORG_ID", "test-org")
        return ProductiveClient()

    @pytest.mark.asyncio
    async def test_get_request_success(self, client):
        """Test successful GET request."""
        mock_response = {"data": [{"id": "1", "type": "people"}]}

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.get.return_value = AsyncMock(
                json=lambda: mock_response,
                raise_for_status=lambda: None,
            )

            result = await client.get("people", {"filter[query]": "test"})

            assert result == mock_response
            mock_instance.get.assert_called_once_with(
                f"{API_BASE}/people",
                headers=client.headers,
                params={"filter[query]": "test"},
            )

    @pytest.mark.asyncio
    async def test_get_request_http_error(self, client):
        """Test GET request with HTTP error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.get.return_value = AsyncMock(
                raise_for_status=lambda: (_ for _ in ()).throw(
                    httpx.HTTPStatusError(
                        "Not Found",
                        request=AsyncMock(),
                        response=AsyncMock(status_code=404),
                    )
                ),
            )

            with pytest.raises(httpx.HTTPStatusError):
                await client.get("people/invalid")

    @pytest.mark.asyncio
    async def test_post_request_success(self, client):
        """Test successful POST request."""
        mock_response = {"data": {"id": "1", "type": "time_entries"}}
        payload = {"data": {"type": "time_entries", "attributes": {}}}

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.post.return_value = AsyncMock(
                json=lambda: mock_response,
                raise_for_status=lambda: None,
            )

            result = await client.post("time_entries", payload)

            assert result == mock_response
            mock_instance.post.assert_called_once_with(
                f"{API_BASE}/time_entries",
                headers=client.headers,
                json=payload,
            )

    @pytest.mark.asyncio
    async def test_patch_request_success(self, client):
        """Test successful PATCH request."""
        mock_response = {"data": {"id": "1", "type": "time_entries"}}
        payload = {"data": {"type": "time_entries", "id": "1", "attributes": {}}}

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.patch.return_value = AsyncMock(
                json=lambda: mock_response,
                raise_for_status=lambda: None,
            )

            result = await client.patch("time_entries/1", payload)

            assert result == mock_response
            mock_instance.patch.assert_called_once_with(
                f"{API_BASE}/time_entries/1",
                headers=client.headers,
                json=payload,
            )

    @pytest.mark.asyncio
    async def test_delete_request_success(self, client):
        """Test successful DELETE request."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.delete.return_value = AsyncMock(
                raise_for_status=lambda: None,
            )

            result = await client.delete("time_entries/1")

            assert result == {}
            mock_instance.delete.assert_called_once_with(
                f"{API_BASE}/time_entries/1",
                headers=client.headers,
            )


class TestClientSingleton:
    """Tests for client singleton functions."""

    def setup_method(self):
        """Reset client before each test."""
        reset_client()

    def teardown_method(self):
        """Reset client after each test."""
        reset_client()

    def test_get_client_creates_singleton(self, monkeypatch):
        """Test get_client creates and returns singleton."""
        monkeypatch.setenv("PRODUCTIVE_API_TOKEN", "test-token")
        monkeypatch.setenv("PRODUCTIVE_ORG_ID", "test-org")

        client1 = get_client()
        client2 = get_client()

        assert client1 is client2

    def test_reset_client(self, monkeypatch):
        """Test reset_client clears the singleton."""
        monkeypatch.setenv("PRODUCTIVE_API_TOKEN", "test-token")
        monkeypatch.setenv("PRODUCTIVE_ORG_ID", "test-org")

        client1 = get_client()
        reset_client()
        client2 = get_client()

        assert client1 is not client2

    def test_set_client(self, monkeypatch):
        """Test set_client injects custom client."""
        monkeypatch.setenv("PRODUCTIVE_API_TOKEN", "test-token")
        monkeypatch.setenv("PRODUCTIVE_ORG_ID", "test-org")

        custom_client = ProductiveClient(
            api_token="custom-token",
            org_id="custom-org",
        )
        set_client(custom_client)

        result = get_client()

        assert result is custom_client
        assert result.api_token == "custom-token"
