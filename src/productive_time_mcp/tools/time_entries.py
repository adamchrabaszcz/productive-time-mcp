"""Time entry CRUD operations."""

from ..api import get_client
from ..utils import format_hours


async def get_time_entry(entry_id: str) -> dict:
    """Get a single time entry with full details."""
    client = get_client()
    response = await client.get(
        f"time_entries/{entry_id}",
        {"include": "service,task,person"},
    )

    if not response.get("data"):
        return {"error": f"Time entry {entry_id} not found"}

    entry = response["data"]
    attrs = entry.get("attributes", {})

    # Extract included resources
    included = {item["id"]: item for item in response.get("included", [])}
    relationships = entry.get("relationships", {})

    result = {
        "id": entry["id"],
        "date": attrs.get("date"),
        "hours": format_hours(attrs.get("time", 0)),
        "note": attrs.get("note"),
        "billable": attrs.get("billable"),
    }

    # Add service info if available
    service_rel = relationships.get("service", {}).get("data")
    if service_rel and service_rel["id"] in included:
        service = included[service_rel["id"]]
        result["service"] = {
            "id": service["id"],
            "name": service.get("attributes", {}).get("name"),
        }

    # Add task info if available
    task_rel = relationships.get("task", {}).get("data")
    if task_rel and task_rel["id"] in included:
        task = included[task_rel["id"]]
        result["task"] = {
            "id": task["id"],
            "title": task.get("attributes", {}).get("title"),
        }

    return result


async def create_time_entry(
    date: str,
    hours: float,
    service_id: str,
    note: str = "",
    task_id: str | None = None,
    person_id: str | None = None,
) -> dict:
    """Create a new time entry in Productive."""
    client = get_client()
    target_person = person_id or client.user_id

    if not target_person:
        return {"error": "person_id is required (or set PRODUCTIVE_USER_ID)"}

    payload = {
        "data": {
            "type": "time_entries",
            "attributes": {
                "date": date,
                "time": int(hours * 60),
                "note": note,
            },
            "relationships": {
                "person": {"data": {"type": "people", "id": target_person}},
                "service": {"data": {"type": "services", "id": service_id}},
            },
        }
    }

    if task_id:
        payload["data"]["relationships"]["task"] = {
            "data": {"type": "tasks", "id": task_id}
        }

    response = await client.post("time_entries", payload)
    entry = response["data"]
    attrs = entry.get("attributes", {})

    return {
        "created": True,
        "id": entry["id"],
        "date": attrs.get("date"),
        "hours": format_hours(attrs.get("time", 0)),
        "note": attrs.get("note"),
    }


async def update_time_entry(
    entry_id: str,
    hours: float | None = None,
    note: str | None = None,
    date: str | None = None,
) -> dict:
    """Update an existing time entry."""
    client = get_client()

    attributes = {}
    if hours is not None:
        attributes["time"] = int(hours * 60)
    if note is not None:
        attributes["note"] = note
    if date is not None:
        attributes["date"] = date

    if not attributes:
        return {"error": "At least one field (hours, note, date) must be provided"}

    payload = {
        "data": {
            "type": "time_entries",
            "id": entry_id,
            "attributes": attributes,
        }
    }

    response = await client.patch(f"time_entries/{entry_id}", payload)
    entry = response["data"]
    attrs = entry.get("attributes", {})

    return {
        "updated": True,
        "id": entry["id"],
        "date": attrs.get("date"),
        "hours": format_hours(attrs.get("time", 0)),
        "note": attrs.get("note"),
    }


async def delete_time_entry(entry_id: str) -> dict:
    """Delete a time entry."""
    client = get_client()
    await client.delete(f"time_entries/{entry_id}")

    return {
        "deleted": True,
        "id": entry_id,
    }
