"""Utility functions for date handling and formatting."""

import re
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

# Default cutoff day for billing period logic
DEFAULT_BILLING_CUTOFF_DAY = 10


def get_month_range(target_date: date) -> tuple[str, str]:
    """Get the first and last day of a month containing target_date."""
    start = target_date.replace(day=1)
    next_month = start + relativedelta(months=1)
    end = next_month - timedelta(days=1)
    return start.isoformat(), end.isoformat()


def calculate_period(
    period: str = "month",
    billing_cutoff_day: int = DEFAULT_BILLING_CUTOFF_DAY,
) -> tuple[str, str]:
    """
    Calculate date range for a given period.

    Automatic period selection for invoice processing:
    - Before billing_cutoff_day: defaults to previous month
    - From billing_cutoff_day onwards: defaults to current month

    Example with billing_cutoff_day=10:
        Mar 1-9:   → February (still in invoice window)
        Mar 10-31: → March (new period)

    Args:
        period: One of:
            - "today": Current day
            - "week": Current week (Mon-Sun)
            - "month" / "current": Current billing period (auto-selected)
            - "previous" / "last": Previous month
            - "-N": N months ago (e.g., "-2" for 2 months ago)
            - "YYYY-MM": Specific month
        billing_cutoff_day: Day of month when new billing period activates (1-28).
            Before this day: defaults to previous month.
            From this day onwards: defaults to current month.

    Returns:
        Tuple of (start_date, end_date) in ISO format
    """
    today = date.today()

    # Today
    if period == "today":
        return today.isoformat(), today.isoformat()

    # Current week (Monday to Sunday)
    if period == "week":
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        return start.isoformat(), end.isoformat()

    # Explicit current month (ignores billing cutoff)
    if period == "current":
        return get_month_range(today)

    # Previous month
    if period in ("previous", "last"):
        prev_month = today.replace(day=1) - timedelta(days=1)
        return get_month_range(prev_month)

    # Relative months: -1, -2, -3, etc.
    if re.match(r"^-\d+$", period):
        months_ago = abs(int(period))
        target = today - relativedelta(months=months_ago)
        return get_month_range(target)

    # Default "month" - uses billing cutoff logic
    if period == "month":
        if today.day >= billing_cutoff_day:
            # We're past cutoff, use current month
            return get_month_range(today)
        else:
            # Before cutoff, still processing previous month
            prev_month = today.replace(day=1) - timedelta(days=1)
            return get_month_range(prev_month)

    # Explicit YYYY-MM format
    if len(period) == 7 and "-" in period:
        try:
            year, month = map(int, period.split("-"))
            target = date(year, month, 1)
            return get_month_range(target)
        except ValueError:
            pass

    # Unknown format - fall back to default month logic
    return calculate_period("month", billing_cutoff_day)


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
