"""Time reporting tools."""

import re

from ..api import get_client
from ..utils import calculate_period, format_hours, format_hours_response
from .people import get_person
from .time_entries import get_time_entry


async def get_time_reports(
    person_id: str | None = None,
    period: str = "month",
    after: str | None = None,
    before: str | None = None,
) -> dict:
    """Get hours summary for a person over a period."""
    client = get_client()
    target_person = person_id or client.user_id

    if not target_person:
        return {"error": "person_id is required (or set PRODUCTIVE_USER_ID)"}

    # Calculate date range
    if after and before:
        start_date, end_date = after, before
    else:
        start_date, end_date = calculate_period(period)

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


async def get_time_entries(
    person_id: str | None = None,
    period: str = "month",
    after: str | None = None,
    before: str | None = None,
    project_type_id: str | None = None,
) -> dict:
    """List time entries for a person over a period.

    Args:
        project_type_id: Filter by project type (1 = internal, 2 = client)
    """
    client = get_client()
    target_person = person_id or client.user_id

    if not target_person:
        return {"error": "person_id is required (or set PRODUCTIVE_USER_ID)"}

    # Calculate date range
    if after and before:
        start_date, end_date = after, before
    else:
        start_date, end_date = calculate_period(period)

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
        # Extract entry ID from the composite ID format (e.g., "date-person-service-task-entry")
        entry_id = entry["id"].split("-")[-1] if "-" in entry["id"] else entry["id"]
        attrs = entry.get("attributes", {})
        entries.append({
            "id": entry_id,
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


async def get_my_hours(period: str = "month") -> dict:
    """Get current user's hours summary for a period."""
    client = get_client()

    if not client.user_id:
        return {"error": "PRODUCTIVE_USER_ID environment variable is required"}

    return await get_time_reports(person_id=client.user_id, period=period)


async def get_employee_hours(
    name: str,
    month: str | None = None,
    include_internal_notes: bool = True,
) -> dict:
    """
    Get hours summary for any employee by name.

    This is the primary tool for checking team member workload.
    """
    # Step 1: Find person by name
    person_result = await get_person(name)
    if "error" in person_result:
        return person_result

    person_id = person_result["id"]
    person_name = person_result["name"]

    # Step 2: Calculate period
    period = month if month else "month"

    # Step 3: Get time reports
    report = await get_time_reports(person_id=person_id, period=period)
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
        # Use project_type_id=1 for internal projects (matching n8n workflow)
        entries = await get_time_entries(
            person_id=person_id,
            period=period,
            project_type_id="1",
        )

        internal_notes = []
        for entry in entries.get("entries", []):
            # Fetch full entry details to get note and service name
            entry_details = await get_time_entry(entry["id"])
            if "error" not in entry_details:
                note = entry_details.get("note")
                if note:
                    # Strip HTML tags from note (same as n8n workflow)
                    clean_note = re.sub(r"</li>", ", ", note)
                    clean_note = re.sub(r"<[^>]+>", "", clean_note)
                    internal_notes.append({
                        "date": entry_details.get("date"),
                        "hours": entry_details.get("hours"),
                        "service": entry_details.get("service", {}).get("name"),
                        "note": clean_note.strip(),
                    })

        if internal_notes:
            result["internal_notes"] = internal_notes

    return result
