"""People lookup tools."""

from ..api import get_client


async def get_person(query: str) -> dict:
    """
    Find a person by name or email.

    Args:
        query: Name or email to search for

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
