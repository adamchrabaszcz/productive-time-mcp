"""Tests for MCP tool functions."""

from unittest.mock import AsyncMock, patch

import pytest

from productive_time_mcp.api import reset_client, set_client, ProductiveClient
from productive_time_mcp.server import (
    get_person,
    get_time_reports,
    get_time_entries,
    get_my_hours,
    get_employee_hours,
    get_time_entry,
    create_time_entry,
    update_time_entry,
    delete_time_entry,
)


@pytest.fixture(autouse=True)
def reset_api_client():
    """Reset API client before and after each test."""
    reset_client()
    yield
    reset_client()


@pytest.fixture
def mock_client(monkeypatch):
    """Create a mock client with mocked HTTP methods."""
    monkeypatch.setenv("PRODUCTIVE_API_TOKEN", "test-token")
    monkeypatch.setenv("PRODUCTIVE_ORG_ID", "test-org")
    monkeypatch.setenv("PRODUCTIVE_USER_ID", "user-123")

    client = ProductiveClient()
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.patch = AsyncMock()
    client.delete = AsyncMock()
    set_client(client)
    return client


class TestGetPerson:
    """Tests for get_person tool."""

    @pytest.mark.asyncio
    async def test_get_person_found(self, mock_client):
        """Test finding a person successfully."""
        mock_client.get.return_value = {
            "data": [{
                "id": "123",
                "type": "people",
                "attributes": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": "john.doe@example.com",
                    "title": "Developer",
                },
            }]
        }

        result = await get_person("John Doe")

        assert result["id"] == "123"
        assert result["name"] == "John Doe"
        assert result["email"] == "john.doe@example.com"
        assert result["title"] == "Developer"
        mock_client.get.assert_called_once_with("people", {"filter[query]": "John Doe"})

    @pytest.mark.asyncio
    async def test_get_person_not_found(self, mock_client):
        """Test when person is not found."""
        mock_client.get.return_value = {"data": []}

        result = await get_person("Unknown Person")

        assert "error" in result
        assert "No person found" in result["error"]


class TestGetTimeReports:
    """Tests for get_time_reports tool."""

    @pytest.mark.asyncio
    async def test_get_time_reports_success(self, mock_client):
        """Test getting time reports successfully."""
        mock_client.get.return_value = {
            "data": [{
                "id": "1",
                "type": "time_reports",
                "attributes": {
                    "worked_time": 9600,  # 160 hours
                    "client_time": 8400,
                    "internal_time": 1200,
                    "paid_event_time": 0,
                    "unpaid_event_time": 0,
                },
            }]
        }

        result = await get_time_reports(person_id="123", after="2024-03-01", before="2024-03-31")

        assert result["person_id"] == "123"
        assert result["hours"]["worked"] == 160.0
        assert result["hours"]["client"] == 140.0
        assert result["hours"]["internal"] == 20.0

    @pytest.mark.asyncio
    async def test_get_time_reports_no_person_id(self, mock_client, monkeypatch):
        """Test error when no person_id and no user_id."""
        monkeypatch.delenv("PRODUCTIVE_USER_ID", raising=False)
        reset_client()
        monkeypatch.setenv("PRODUCTIVE_API_TOKEN", "test-token")
        monkeypatch.setenv("PRODUCTIVE_ORG_ID", "test-org")

        client = ProductiveClient()
        client.get = AsyncMock()
        set_client(client)

        result = await get_time_reports()

        assert "error" in result
        assert "person_id is required" in result["error"]


class TestGetTimeEntries:
    """Tests for get_time_entries tool."""

    @pytest.mark.asyncio
    async def test_get_time_entries_success(self, mock_client):
        """Test getting time entries successfully."""
        mock_client.get.return_value = {
            "data": [
                {
                    "id": "entry-1",
                    "type": "time_entry_reports",
                    "attributes": {
                        "date": "2024-03-01",
                        "time": 480,  # 8 hours
                        "note": "Test note",
                        "billable": True,
                    },
                },
                {
                    "id": "entry-2",
                    "type": "time_entry_reports",
                    "attributes": {
                        "date": "2024-03-02",
                        "time": 240,  # 4 hours
                        "note": None,
                        "billable": False,
                    },
                },
            ]
        }

        result = await get_time_entries(person_id="123", after="2024-03-01", before="2024-03-31")

        assert result["person_id"] == "123"
        assert result["count"] == 2
        assert len(result["entries"]) == 2
        assert result["entries"][0]["hours"] == 8.0
        assert result["entries"][1]["hours"] == 4.0

    @pytest.mark.asyncio
    async def test_get_time_entries_with_project_filter(self, mock_client):
        """Test filtering entries by project type."""
        mock_client.get.return_value = {"data": []}

        await get_time_entries(person_id="123", project_type_id="1")

        call_args = mock_client.get.call_args
        assert call_args[0][0] == "reports/time_entry_reports"
        assert call_args[0][1]["filter[project_type_id]"] == "1"


class TestGetMyHours:
    """Tests for get_my_hours tool."""

    @pytest.mark.asyncio
    async def test_get_my_hours_success(self, mock_client):
        """Test getting current user's hours."""
        mock_client.get.return_value = {
            "data": [{
                "id": "1",
                "type": "time_reports",
                "attributes": {
                    "worked_time": 4800,
                    "client_time": 4800,
                    "internal_time": 0,
                    "paid_event_time": 0,
                    "unpaid_event_time": 0,
                },
            }]
        }

        result = await get_my_hours(after="2024-03-04", before="2024-03-10")

        assert result["hours"]["worked"] == 80.0
        assert result["period"]["start"] == "2024-03-04"
        assert result["period"]["end"] == "2024-03-10"

    @pytest.mark.asyncio
    async def test_get_my_hours_no_user_id(self, mock_client, monkeypatch):
        """Test error when PRODUCTIVE_USER_ID is not set."""
        monkeypatch.delenv("PRODUCTIVE_USER_ID", raising=False)
        reset_client()
        monkeypatch.setenv("PRODUCTIVE_API_TOKEN", "test-token")
        monkeypatch.setenv("PRODUCTIVE_ORG_ID", "test-org")

        client = ProductiveClient()
        client.get = AsyncMock()
        set_client(client)

        result = await get_my_hours()

        assert "error" in result
        assert "PRODUCTIVE_USER_ID" in result["error"]


class TestGetEmployeeHours:
    """Tests for get_employee_hours tool."""

    @pytest.mark.asyncio
    async def test_get_employee_hours_success(self, mock_client):
        """Test getting employee hours by name."""
        # Mock get_person response
        mock_client.get.side_effect = [
            # First call: get_person
            {
                "data": [{
                    "id": "emp-123",
                    "type": "people",
                    "attributes": {
                        "first_name": "Jane",
                        "last_name": "Smith",
                        "email": "jane@example.com",
                    },
                }]
            },
            # Second call: get_time_reports
            {
                "data": [{
                    "id": "1",
                    "type": "time_reports",
                    "attributes": {
                        "worked_time": 9600,
                        "client_time": 9600,
                        "internal_time": 0,
                        "paid_event_time": 0,
                        "unpaid_event_time": 0,
                    },
                }]
            },
        ]

        result = await get_employee_hours("Jane Smith", include_internal_notes=False)

        assert result["person"]["id"] == "emp-123"
        assert result["person"]["name"] == "Jane Smith"
        assert result["hours"]["worked"] == 160.0

    @pytest.mark.asyncio
    async def test_get_employee_hours_with_internal_notes(self, mock_client):
        """Test getting employee hours with internal notes."""
        mock_client.get.side_effect = [
            # get_person
            {
                "data": [{
                    "id": "emp-123",
                    "type": "people",
                    "attributes": {
                        "first_name": "Jane",
                        "last_name": "Smith",
                        "email": "jane@example.com",
                    },
                }]
            },
            # get_time_reports
            {
                "data": [{
                    "id": "1",
                    "type": "time_reports",
                    "attributes": {
                        "worked_time": 9600,
                        "client_time": 8400,
                        "internal_time": 1200,  # 20 hours internal
                        "paid_event_time": 0,
                        "unpaid_event_time": 0,
                    },
                }]
            },
            # get_time_entries (internal)
            {
                "data": [{
                    "id": "entry-1",
                    "type": "time_entry_reports",
                    "attributes": {
                        "date": "2024-03-01",
                        "time": 480,
                        "note": "<p>Internal work</p>",
                        "billable": False,
                    },
                }]
            },
            # get_time_entry (full details)
            {
                "data": {
                    "id": "entry-1",
                    "type": "time_entries",
                    "attributes": {
                        "date": "2024-03-01",
                        "time": 480,
                        "note": "<p>Internal <b>work</b></p>",
                        "billable": False,
                    },
                    "relationships": {
                        "service": {"data": {"id": "svc-1", "type": "services"}},
                    },
                },
                "included": [{
                    "id": "svc-1",
                    "type": "services",
                    "attributes": {"name": "Admin"},
                }],
            },
        ]

        result = await get_employee_hours("Jane Smith", include_internal_notes=True)

        assert "internal_notes" in result
        assert len(result["internal_notes"]) == 1
        assert result["internal_notes"][0]["note"] == "Internal work"
        assert result["internal_notes"][0]["service"] == "Admin"


class TestGetTimeEntry:
    """Tests for get_time_entry tool."""

    @pytest.mark.asyncio
    async def test_get_time_entry_success(self, mock_client):
        """Test getting a time entry successfully."""
        mock_client.get.return_value = {
            "data": {
                "id": "entry-1",
                "type": "time_entries",
                "attributes": {
                    "date": "2024-03-01",
                    "time": 480,
                    "note": "Test work",
                    "billable": True,
                },
                "relationships": {
                    "service": {"data": {"id": "svc-1", "type": "services"}},
                    "task": {"data": {"id": "task-1", "type": "tasks"}},
                },
            },
            "included": [
                {"id": "svc-1", "type": "services", "attributes": {"name": "Development"}},
                {"id": "task-1", "type": "tasks", "attributes": {"title": "Feature X"}},
            ],
        }

        result = await get_time_entry("entry-1")

        assert result["id"] == "entry-1"
        assert result["hours"] == 8.0
        assert result["note"] == "Test work"
        assert result["service"]["name"] == "Development"
        assert result["task"]["title"] == "Feature X"

    @pytest.mark.asyncio
    async def test_get_time_entry_not_found(self, mock_client):
        """Test when time entry is not found."""
        mock_client.get.return_value = {"data": None}

        result = await get_time_entry("invalid-id")

        assert "error" in result
        assert "not found" in result["error"]


class TestCreateTimeEntry:
    """Tests for create_time_entry tool."""

    @pytest.mark.asyncio
    async def test_create_time_entry_success(self, mock_client):
        """Test creating a time entry successfully."""
        mock_client.post.return_value = {
            "data": {
                "id": "new-entry-1",
                "type": "time_entries",
                "attributes": {
                    "date": "2024-03-01",
                    "time": 480,
                    "note": "New work",
                },
            }
        }

        result = await create_time_entry(
            date="2024-03-01",
            hours=8.0,
            service_id="svc-1",
            note="New work",
        )

        assert result["created"] is True
        assert result["id"] == "new-entry-1"
        assert result["hours"] == 8.0

    @pytest.mark.asyncio
    async def test_create_time_entry_no_person(self, mock_client, monkeypatch):
        """Test error when no person_id available."""
        monkeypatch.delenv("PRODUCTIVE_USER_ID", raising=False)
        reset_client()
        monkeypatch.setenv("PRODUCTIVE_API_TOKEN", "test-token")
        monkeypatch.setenv("PRODUCTIVE_ORG_ID", "test-org")

        client = ProductiveClient()
        client.post = AsyncMock()
        set_client(client)

        result = await create_time_entry(
            date="2024-03-01",
            hours=8.0,
            service_id="svc-1",
        )

        assert "error" in result
        assert "person_id is required" in result["error"]


class TestUpdateTimeEntry:
    """Tests for update_time_entry tool."""

    @pytest.mark.asyncio
    async def test_update_time_entry_success(self, mock_client):
        """Test updating a time entry successfully."""
        mock_client.patch.return_value = {
            "data": {
                "id": "entry-1",
                "type": "time_entries",
                "attributes": {
                    "date": "2024-03-01",
                    "time": 540,  # 9 hours
                    "note": "Updated note",
                },
            }
        }

        result = await update_time_entry(
            entry_id="entry-1",
            hours=9.0,
            note="Updated note",
        )

        assert result["updated"] is True
        assert result["hours"] == 9.0
        assert result["note"] == "Updated note"

    @pytest.mark.asyncio
    async def test_update_time_entry_no_fields(self, mock_client):
        """Test error when no fields provided."""
        result = await update_time_entry(entry_id="entry-1")

        assert "error" in result
        assert "At least one field" in result["error"]


class TestDeleteTimeEntry:
    """Tests for delete_time_entry tool."""

    @pytest.mark.asyncio
    async def test_delete_time_entry_success(self, mock_client):
        """Test deleting a time entry successfully."""
        mock_client.delete.return_value = {}

        result = await delete_time_entry("entry-1")

        assert result["deleted"] is True
        assert result["id"] == "entry-1"
        mock_client.delete.assert_called_once_with("time_entries/entry-1")
