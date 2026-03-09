"""Productive.io API client."""

import os
from typing import Any

import httpx

API_BASE = "https://api.productive.io/api/v2"


class ProductiveClient:
    """HTTP client for Productive.io API."""

    def __init__(
        self,
        api_token: str | None = None,
        org_id: str | None = None,
        user_id: str | None = None,
    ):
        self.api_token = api_token or os.environ.get("PRODUCTIVE_API_TOKEN")
        self.org_id = org_id or os.environ.get("PRODUCTIVE_ORG_ID")
        self.user_id = user_id or os.environ.get("PRODUCTIVE_USER_ID")

        if not self.api_token:
            raise ValueError("PRODUCTIVE_API_TOKEN is required")
        if not self.org_id:
            raise ValueError("PRODUCTIVE_ORG_ID is required")

        self.headers = {
            "X-Auth-Token": self.api_token,
            "X-Organization-Id": self.org_id,
            "Content-Type": "application/vnd.api+json",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make HTTP request to Productive API.

        Args:
            method: HTTP method (get, post, patch, delete)
            endpoint: API endpoint path
            params: Query parameters (for GET requests)
            data: JSON payload (for POST/PATCH requests)

        Returns:
            Response JSON or empty dict for DELETE
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            request_kwargs: dict[str, Any] = {
                "headers": self.headers,
            }
            if params is not None:
                request_kwargs["params"] = params
            if data is not None:
                request_kwargs["json"] = data

            response = await getattr(client, method)(
                f"{API_BASE}/{endpoint}",
                **request_kwargs,
            )
            response.raise_for_status()
            return response.json() if method != "delete" else {}

    async def get(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make GET request to Productive API."""
        return await self._request("get", endpoint, params=params)

    async def post(
        self, endpoint: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Make POST request to Productive API."""
        return await self._request("post", endpoint, data=data)

    async def patch(
        self, endpoint: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Make PATCH request to Productive API."""
        return await self._request("patch", endpoint, data=data)

    async def delete(self, endpoint: str) -> dict[str, Any]:
        """Make DELETE request to Productive API."""
        return await self._request("delete", endpoint)


# Singleton client instance
_client: ProductiveClient | None = None


def get_client() -> ProductiveClient:
    """Get or create the Productive API client."""
    global _client
    if _client is None:
        _client = ProductiveClient()
    return _client


def reset_client() -> None:
    """Reset the client singleton for testing."""
    global _client
    _client = None


def set_client(client: ProductiveClient) -> None:
    """Inject a custom client for testing."""
    global _client
    _client = client
