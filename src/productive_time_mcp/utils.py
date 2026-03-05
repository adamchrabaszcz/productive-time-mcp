"""Utility functions for date handling and formatting."""

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


def calculate_period(period: str = "month") -> tuple[str, str]:
    """
    Calculate date range for a given period.

    Smart month logic (matching n8n workflow):
    - After 21st: current month
    - Before 21st: previous month

    Args:
        period: One of "today", "week", "month", or "YYYY-MM" format

    Returns:
        Tuple of (start_date, end_date) in ISO format
    """
    today = date.today()

    if period == "today":
        return today.isoformat(), today.isoformat()

    if period == "week":
        # Start of current week (Monday)
        start = today - timedelta(days=today.weekday())
        # End of current week (Sunday)
        end = start + timedelta(days=6)
        return start.isoformat(), end.isoformat()

    if period == "month":
        # Smart month logic: after 21st use current month, before use previous
        if today.day >= 21:
            target_month = today.replace(day=1)
        else:
            target_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)

        # Get last day of target month
        next_month = target_month + relativedelta(months=1)
        end = next_month - timedelta(days=1)

        return target_month.isoformat(), end.isoformat()

    # Handle YYYY-MM format
    if len(period) == 7 and "-" in period:
        year, month = map(int, period.split("-"))
        start = date(year, month, 1)
        next_month = start + relativedelta(months=1)
        end = next_month - timedelta(days=1)
        return start.isoformat(), end.isoformat()

    # Default to current month if unknown format
    return calculate_period("month")


def format_hours(minutes: int | float) -> float:
    """Convert minutes to hours, rounded to 2 decimal places."""
    return round(float(minutes) / 60, 2)


def format_hours_response(
    data: dict,
    workday_hours: int = 8,
    include_days: bool = False,
) -> dict:
    """
    Format time report data into a readable response.

    Args:
        data: Raw API response attributes
        workday_hours: Hours per workday for day calculations
        include_days: Whether to include day equivalents

    Returns:
        Formatted hours dictionary
    """
    result = {
        "worked": format_hours(data.get("worked_time", 0)),
        "client": format_hours(data.get("client_time", 0)),
        "internal": format_hours(data.get("internal_time", 0)),
        "paid_holiday": format_hours(data.get("paid_event_time", 0)),
        "unpaid_holiday": format_hours(data.get("unpaid_event_time", 0)),
    }

    # Calculate total
    result["total"] = round(
        result["worked"] + result["paid_holiday"],
        2
    )

    if include_days:
        for key in ["worked", "client", "internal", "paid_holiday", "unpaid_holiday", "total"]:
            result[f"{key}_days"] = round(result[key] / workday_hours, 2)

    return result
