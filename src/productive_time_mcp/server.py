"""FastMCP server for Productive.io time tracking."""

from mcp.server.fastmcp import FastMCP

from .api import get_client
from .utils import (
    PROJECT_TYPE_INTERNAL,
    extract_relationship,
    format_hours,
    format_hours_response,
    get_billing_cutoff_day,
    resolve_date_range,
    strip_html_tags,
)

# Create the MCP server
mcp = FastMCP(
    "productive-time",
    dependencies=["httpx", "python-dateutil"],
)


# ============================================================================
# People Tools
# ============================================================================


@mcp.tool()
async def get_person(query: str) -> dict:
    """
    Find a person by name or email.

    Args:
        query: Name or email to search for (e.g., "John Doe" or "john.doe@company.com")

    Returns:
        Person data including id, name, email
    """
    client = get_client()
    response = await client.get("people", {"filter[query]": query})

    if not response.get("data"):
        return {"error": f"No person found matching '{query}'"}

    person = response["data"][0]
    attrs = person.get("attributes", {})

    return {
        "id": person["id"],
        "name": f"{attrs.get('first_name', '')} {attrs.get('last_name', '')}".strip(),
        "email": attrs.get("email"),
        "title": attrs.get("title"),
    }


# ============================================================================
# Time Reports Tools
# ============================================================================


@mcp.tool()
async def get_time_reports(
    person_id: str | None = None,
    period: str = "month",
    after: str | None = None,
    before: str | None = None,
) -> dict:
    """
    Get hours summary for a person over a period.

    Args:
        person_id: Person ID (defaults to current user if PRODUCTIVE_USER_ID is set)
        period: Period specification:
            - "today": Current day
            - "week": Current week (Mon-Sun)
            - "month": Auto-selected based on billing cutoff day
            - "current": Current calendar month
            - "previous" / "last": Previous month
            - "-N": N months ago (e.g., "-2")
            - "YYYY-MM": Specific month
        after: Start date override (ISO format)
        before: End date override (ISO format)

    Returns:
        Hours breakdown: worked, client, internal, paid_holiday, unpaid_holiday, total
    """
    client = get_client()
    target_person = person_id or client.user_id

    if not target_person:
        return {"error": "person_id is required (or set PRODUCTIVE_USER_ID)"}

    start_date, end_date = resolve_date_range(period, after, before, get_billing_cutoff_day())

    params = {
        "filter[after]": start_date,
        "filter[before]": end_date,
        "filter[person_id]": target_person,
    }

    response = await client.get("reports/time_reports", params)

    if not response.get("data"):
        return {
            "person_id": target_person,
            "period": {"start": start_date, "end": end_date},
            "hours": format_hours_response({}),
        }

    data = response["data"][0].get("attributes", {})

    return {
        "person_id": target_person,
        "period": {"start": start_date, "end": end_date},
        "hours": format_hours_response(data),
    }


@mcp.tool()
async def get_time_entries(
    person_id: str | None = None,
    period: str = "month",
    after: str | None = None,
    before: str | None = None,
    project_type_id: str | None = None,
) -> dict:
    """
    List time entries for a person over a period.

    Args:
        person_id: Person ID (defaults to current user)
        period: Period specification:
            - "today": Current day
            - "week": Current week (Mon-Sun)
            - "month": Auto-selected based on billing cutoff day
            - "current": Current calendar month
            - "previous" / "last": Previous month
            - "-N": N months ago (e.g., "-2")
            - "YYYY-MM": Specific month
        after: Start date override (ISO format)
        before: End date override (ISO format)
        project_type_id: Filter by project type ("1" = internal, "2" = client)

    Returns:
        List of time entries with date, hours, note, service
    """
    client = get_client()
    target_person = person_id or client.user_id

    if not target_person:
        return {"error": "person_id is required (or set PRODUCTIVE_USER_ID)"}

    start_date, end_date = resolve_date_range(period, after, before, get_billing_cutoff_day())

    params = {
        "filter[after]": start_date,
        "filter[before]": end_date,
        "filter[person_id]": target_person,
    }

    if project_type_id:
        params["filter[project_type_id]"] = project_type_id

    response = await client.get("reports/time_entry_reports", params)

    entries = []
    for entry in response.get("data", []):
        attrs = entry.get("attributes", {})
        entries.append({
            "id": entry["id"],
            "date": attrs.get("date"),
            "hours": format_hours(attrs.get("time", 0)),
            "note": attrs.get("note"),
            "billable": attrs.get("billable"),
        })

    return {
        "person_id": target_person,
        "period": {"start": start_date, "end": end_date},
        "entries": entries,
        "count": len(entries),
    }


@mcp.tool()
async def get_my_hours(period: str = "month") -> dict:
    """
    Get current user's hours summary for a period.

    Requires PRODUCTIVE_USER_ID environment variable to be set.

    Args:
        period: Period specification:
            - "today": Current day
            - "week": Current week (Mon-Sun)
            - "month": Auto-selected based on billing cutoff day
            - "current": Current calendar month
            - "previous" / "last": Previous month
            - "-N": N months ago (e.g., "-2")
            - "YYYY-MM": Specific month

    Returns:
        Hours breakdown: worked, client, internal, paid_holiday, unpaid_holiday, total
    """
    client = get_client()

    if not client.user_id:
        return {"error": "PRODUCTIVE_USER_ID environment variable is required"}

    return await get_time_reports(person_id=client.user_id, period=period)


@mcp.tool()
async def get_employee_hours(
    name: str,
    period: str | None = None,
    include_internal_notes: bool = True,
) -> dict:
    """
    Get hours summary for any employee by name.

    This is the primary tool for checking team member workload.

    Args:
        name: Employee name or email (e.g., "John Doe" or "john.doe@company.com")
        period: Period specification (optional, defaults to auto-selected billing period):
            - "month": Auto-selected based on billing cutoff day (default)
            - "current": Current calendar month
            - "previous" / "last": Previous month
            - "-N": N months ago (e.g., "-2")
            - "YYYY-MM": Specific month
        include_internal_notes: Whether to fetch notes from internal time entries

    Returns:
        Complete hours summary including:
        - worked, client, internal, paid_holiday, unpaid_holiday, total
        - internal_notes (if include_internal_notes=True and has internal hours)
    """
    # Step 1: Find person by name
    person_result = await get_person(name)
    if "error" in person_result:
        return person_result

    person_id = person_result["id"]
    person_name = person_result["name"]

    # Step 2: Calculate period (default to "month" which uses billing cutoff logic)
    target_period = period if period else "month"

    # Step 3: Get time reports
    report = await get_time_reports(person_id=person_id, period=target_period)
    if "error" in report:
        return report

    result = {
        "person": {
            "id": person_id,
            "name": person_name,
            "email": person_result.get("email"),
        },
        "period": report["period"],
        "hours": report["hours"],
    }

    # Step 4: If has internal hours and include_internal_notes, get details
    if include_internal_notes and report["hours"]["internal"] > 0:
        entries = await get_time_entries(
            person_id=person_id,
            period=target_period,
            project_type_id=PROJECT_TYPE_INTERNAL,
        )

        internal_notes = []
        for entry in entries.get("entries", []):
            # Extract real ID from composite report ID
            # "time-entry-report-time_entry-133939949-hash" → "133939949"
            entry_id = entry["id"]
            if entry_id.startswith("time-entry-report"):
                parts = entry_id.split("-")
                actual_id = parts[4] if len(parts) > 4 else entry_id
            else:
                actual_id = entry_id

            # Fetch full entry details to get note and service name
            entry_details = await get_time_entry(actual_id)
            if "error" not in entry_details:
                note = entry_details.get("note")
                if note:
                    internal_notes.append({
                        "date": entry_details.get("date"),
                        "hours": entry_details.get("hours"),
                        "service": entry_details.get("service", {}).get("name"),
                        "note": strip_html_tags(note),
                    })

        if internal_notes:
            result["internal_notes"] = internal_notes

    return result


# ============================================================================
# Time Entry CRUD Tools
# ============================================================================


@mcp.tool()
async def get_time_entry(entry_id: str) -> dict:
    """
    Get a single time entry with full details.

    Args:
        entry_id: The time entry ID

    Returns:
        Time entry details including service and task information
    """
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

    result = {
        "id": entry["id"],
        "date": attrs.get("date"),
        "hours": format_hours(attrs.get("time", 0)),
        "note": attrs.get("note"),
        "billable": attrs.get("billable"),
    }

    # Add service info if available
    service = extract_relationship(entry, "service", included, "name")
    if service:
        result["service"] = service

    # Add task info if available
    task_rel = extract_relationship(entry, "task", included, "title")
    if task_rel:
        result["task"] = {"id": task_rel["id"], "title": task_rel["title"]}

    return result


@mcp.tool()
async def create_time_entry(
    date: str,
    hours: float,
    service_id: str,
    note: str = "",
    task_id: str | None = None,
    person_id: str | None = None,
) -> dict:
    """
    Create a new time entry in Productive.

    Args:
        date: Date for the time entry (ISO format: YYYY-MM-DD)
        hours: Number of hours to log
        service_id: Service ID to log time against
        note: Description/note for the time entry
        task_id: Optional task ID to associate with the entry
        person_id: Person ID (defaults to current user)

    Returns:
        Created time entry details
    """
    client = get_client()
    target_person = person_id or client.user_id

    if not target_person:
        return {"error": "person_id is required (or set PRODUCTIVE_USER_ID)"}

    payload = {
        "data": {
            "type": "time_entries",
            "attributes": {
                "date": date,
                "time": int(hours * 60),  # Convert hours to minutes
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


@mcp.tool()
async def update_time_entry(
    entry_id: str,
    hours: float | None = None,
    note: str | None = None,
    date: str | None = None,
) -> dict:
    """
    Update an existing time entry.

    Args:
        entry_id: The time entry ID to update
        hours: New hours value (optional)
        note: New note (optional)
        date: New date (optional)

    Returns:
        Updated time entry details
    """
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


@mcp.tool()
async def delete_time_entry(entry_id: str) -> dict:
    """
    Delete a time entry.

    Args:
        entry_id: The time entry ID to delete

    Returns:
        Confirmation of deletion
    """
    client = get_client()
    await client.delete(f"time_entries/{entry_id}")

    return {
        "deleted": True,
        "id": entry_id,
    }
