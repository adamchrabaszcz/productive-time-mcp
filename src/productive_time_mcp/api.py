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

    async def get(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make GET request to Productive API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{API_BASE}/{endpoint}",
                headers=self.headers,
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def post(
        self, endpoint: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Make POST request to Productive API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE}/{endpoint}",
                headers=self.headers,
                json=data,
            )
            response.raise_for_status()
            return response.json()

    async def patch(
        self, endpoint: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Make PATCH request to Productive API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.patch(
                f"{API_BASE}/{endpoint}",
                headers=self.headers,
                json=data,
            )
            response.raise_for_status()
            return response.json()

    async def delete(self, endpoint: str) -> bool:
        """Make DELETE request to Productive API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{API_BASE}/{endpoint}",
                headers=self.headers,
            )
            response.raise_for_status()
            return True


# Singleton client instance
_client: ProductiveClient | None = None


def get_client() -> ProductiveClient:
    """Get or create the Productive API client."""
    global _client
    if _client is None:
        _client = ProductiveClient()
    return _client
