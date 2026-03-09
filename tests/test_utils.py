"""Tests for utility functions."""

from datetime import date
from unittest.mock import patch

import pytest

from productive_time_mcp.utils import (
    calculate_period,
    extract_relationship,
    format_hours,
    format_hours_response,
    get_billing_cutoff_day,
    resolve_date_range,
    strip_html_tags,
    DEFAULT_BILLING_CUTOFF_DAY,
    PROJECT_TYPE_INTERNAL,
    PROJECT_TYPE_CLIENT,
)


class TestCalculatePeriod:
    """Tests for calculate_period function."""

    def test_today(self):
        """Test today period."""
        start, end = calculate_period("today")
        today = date.today().isoformat()
        assert start == today
        assert end == today

    def test_week(self):
        """Test week period."""
        start, end = calculate_period("week")
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)

        # Start should be Monday (weekday 0)
        assert start_date.weekday() == 0
        # End should be Sunday (weekday 6)
        assert end_date.weekday() == 6
        # Should be 6 days apart
        assert (end_date - start_date).days == 6

    def test_current_always_returns_current_month(self):
        """Test 'current' always returns current calendar month."""
        with patch("productive_time_mcp.utils.date") as mock_date:
            mock_date.today.return_value = date(2024, 3, 5)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            start, end = calculate_period("current")
            assert start == "2024-03-01"
            assert end == "2024-03-31"

    def test_previous_returns_previous_month(self):
        """Test 'previous' returns previous month."""
        with patch("productive_time_mcp.utils.date") as mock_date:
            mock_date.today.return_value = date(2024, 3, 15)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            start, end = calculate_period("previous")
            assert start == "2024-02-01"
            assert end == "2024-02-29"  # 2024 is leap year

    def test_last_is_alias_for_previous(self):
        """Test 'last' is alias for 'previous'."""
        with patch("productive_time_mcp.utils.date") as mock_date:
            mock_date.today.return_value = date(2024, 3, 15)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            start, end = calculate_period("last")
            assert start == "2024-02-01"
            assert end == "2024-02-29"

    def test_relative_minus_one(self):
        """Test '-1' returns 1 month ago."""
        with patch("productive_time_mcp.utils.date") as mock_date:
            mock_date.today.return_value = date(2024, 3, 15)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            start, end = calculate_period("-1")
            assert start == "2024-02-01"
            assert end == "2024-02-29"

    def test_relative_minus_two(self):
        """Test '-2' returns 2 months ago."""
        with patch("productive_time_mcp.utils.date") as mock_date:
            mock_date.today.return_value = date(2024, 3, 15)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            start, end = calculate_period("-2")
            assert start == "2024-01-01"
            assert end == "2024-01-31"

    def test_relative_minus_three_crosses_year(self):
        """Test '-3' correctly crosses year boundary."""
        with patch("productive_time_mcp.utils.date") as mock_date:
            mock_date.today.return_value = date(2024, 2, 15)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            start, end = calculate_period("-3")
            assert start == "2023-11-01"
            assert end == "2023-11-30"

    @patch("productive_time_mcp.utils.date")
    def test_month_after_cutoff_uses_current(self, mock_date):
        """Test month calculation after cutoff uses current month."""
        mock_date.today.return_value = date(2024, 3, 15)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        # With cutoff day 10, day 15 is after cutoff -> current month
        start, end = calculate_period("month", billing_cutoff_day=10)
        assert start == "2024-03-01"
        assert end == "2024-03-31"

    @patch("productive_time_mcp.utils.date")
    def test_month_before_cutoff_uses_previous(self, mock_date):
        """Test month calculation before cutoff uses previous month."""
        mock_date.today.return_value = date(2024, 3, 5)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        # With cutoff day 10, day 5 is before cutoff -> previous month
        start, end = calculate_period("month", billing_cutoff_day=10)
        assert start == "2024-02-01"
        assert end == "2024-02-29"

    @patch("productive_time_mcp.utils.date")
    def test_month_on_cutoff_day_uses_current(self, mock_date):
        """Test month calculation on cutoff day uses current month."""
        mock_date.today.return_value = date(2024, 3, 10)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        # On cutoff day 10 -> current month
        start, end = calculate_period("month", billing_cutoff_day=10)
        assert start == "2024-03-01"
        assert end == "2024-03-31"

    @patch("productive_time_mcp.utils.date")
    def test_invoice_scenario_feb28(self, mock_date):
        """Test invoice scenario: Feb 28 should show February."""
        mock_date.today.return_value = date(2024, 2, 28)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        # Feb 28 is after cutoff day 10 -> February
        start, end = calculate_period("month", billing_cutoff_day=10)
        assert start == "2024-02-01"
        assert end == "2024-02-29"

    @patch("productive_time_mcp.utils.date")
    def test_invoice_scenario_mar1(self, mock_date):
        """Test invoice scenario: Mar 1 should still show February."""
        mock_date.today.return_value = date(2024, 3, 1)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        # Mar 1 is before cutoff day 10 -> February (previous month)
        start, end = calculate_period("month", billing_cutoff_day=10)
        assert start == "2024-02-01"
        assert end == "2024-02-29"

    @patch("productive_time_mcp.utils.date")
    def test_invoice_scenario_mar9(self, mock_date):
        """Test invoice scenario: Mar 9 should still show February."""
        mock_date.today.return_value = date(2024, 3, 9)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        # Mar 9 is before cutoff day 10 -> February
        start, end = calculate_period("month", billing_cutoff_day=10)
        assert start == "2024-02-01"
        assert end == "2024-02-29"

    @patch("productive_time_mcp.utils.date")
    def test_invoice_scenario_mar10(self, mock_date):
        """Test invoice scenario: Mar 10 should show March."""
        mock_date.today.return_value = date(2024, 3, 10)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        # Mar 10 is on cutoff day 10 -> March
        start, end = calculate_period("month", billing_cutoff_day=10)
        assert start == "2024-03-01"
        assert end == "2024-03-31"

    def test_specific_month(self):
        """Test specific YYYY-MM format."""
        start, end = calculate_period("2024-03")
        assert start == "2024-03-01"
        assert end == "2024-03-31"

    def test_february_leap_year(self):
        """Test February in leap year."""
        start, end = calculate_period("2024-02")
        assert start == "2024-02-01"
        assert end == "2024-02-29"

    def test_february_non_leap_year(self):
        """Test February in non-leap year."""
        start, end = calculate_period("2023-02")
        assert start == "2023-02-01"
        assert end == "2023-02-28"

    def test_default_cutoff_day_is_10(self):
        """Test that default billing cutoff day is 10."""
        assert DEFAULT_BILLING_CUTOFF_DAY == 10


class TestFormatHours:
    """Tests for format_hours function."""

    def test_zero_minutes(self):
        """Test zero minutes."""
        assert format_hours(0) == 0.0

    def test_60_minutes(self):
        """Test 60 minutes = 1 hour."""
        assert format_hours(60) == 1.0

    def test_90_minutes(self):
        """Test 90 minutes = 1.5 hours."""
        assert format_hours(90) == 1.5

    def test_rounding(self):
        """Test rounding to 2 decimal places."""
        # 100 minutes = 1.666... hours
        assert format_hours(100) == 1.67


class TestFormatHoursResponse:
    """Tests for format_hours_response function."""

    def test_empty_data(self):
        """Test with empty data."""
        result = format_hours_response({})
        assert result["worked"] == 0.0
        assert result["client"] == 0.0
        assert result["internal"] == 0.0
        assert result["paid_holiday"] == 0.0
        assert result["unpaid_holiday"] == 0.0
        assert result["total"] == 0.0

    def test_full_data(self):
        """Test with complete data."""
        data = {
            "worked_time": 9600,  # 160 hours
            "client_time": 8400,  # 140 hours
            "internal_time": 1200,  # 20 hours
            "paid_event_time": 0,
            "unpaid_event_time": 0,
        }
        result = format_hours_response(data)
        assert result["worked"] == 160.0
        assert result["client"] == 140.0
        assert result["internal"] == 20.0
        assert result["total"] == 160.0

    def test_with_holidays(self):
        """Test total includes paid holidays."""
        data = {
            "worked_time": 7200,  # 120 hours
            "client_time": 7200,
            "internal_time": 0,
            "paid_event_time": 2400,  # 40 hours
            "unpaid_event_time": 0,
        }
        result = format_hours_response(data)
        assert result["worked"] == 120.0
        assert result["paid_holiday"] == 40.0
        # Total = worked + paid_holiday
        assert result["total"] == 160.0

    def test_include_days(self):
        """Test day calculations."""
        data = {
            "worked_time": 4800,  # 80 hours
            "client_time": 4800,
            "internal_time": 0,
            "paid_event_time": 0,
            "unpaid_event_time": 0,
        }
        result = format_hours_response(data, workday_hours=8, include_days=True)
        assert result["worked_days"] == 10.0
        assert result["total_days"] == 10.0


class TestStripHtmlTags:
    """Tests for strip_html_tags function."""

    def test_basic_tags(self):
        """Test stripping basic HTML tags."""
        result = strip_html_tags("<p>Hello <b>world</b></p>")
        assert result == "Hello world"

    def test_list_items(self):
        """Test converting list items to commas."""
        result = strip_html_tags("<ul><li>Item 1</li><li>Item 2</li></ul>")
        assert result == "Item 1, Item 2,"

    def test_empty_string(self):
        """Test with empty string."""
        result = strip_html_tags("")
        assert result == ""

    def test_plain_text(self):
        """Test with plain text (no HTML)."""
        result = strip_html_tags("Just plain text")
        assert result == "Just plain text"

    def test_nested_tags(self):
        """Test with nested tags."""
        result = strip_html_tags("<div><p>Nested <span>content</span></p></div>")
        assert result == "Nested content"

    def test_whitespace_trimming(self):
        """Test that result is trimmed."""
        result = strip_html_tags("  <p>Text</p>  ")
        assert result == "Text"


class TestResolveDateRange:
    """Tests for resolve_date_range function."""

    def test_explicit_dates(self):
        """Test with explicit after and before dates."""
        start, end = resolve_date_range(
            period="month",
            after="2024-01-01",
            before="2024-01-31",
        )
        assert start == "2024-01-01"
        assert end == "2024-01-31"

    def test_period_fallback(self):
        """Test falling back to period calculation."""
        start, end = resolve_date_range(period="2024-03")
        assert start == "2024-03-01"
        assert end == "2024-03-31"

    def test_partial_dates_uses_period(self):
        """Test that partial dates fall back to period."""
        # Only after provided, not before
        start, end = resolve_date_range(
            period="2024-02",
            after="2024-01-15",
            before=None,
        )
        assert start == "2024-02-01"
        assert end == "2024-02-29"

    def test_custom_billing_cutoff(self):
        """Test with custom billing cutoff day."""
        with patch("productive_time_mcp.utils.date") as mock_date:
            mock_date.today.return_value = date(2024, 3, 5)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            # Day 5 with cutoff 15 should use previous month
            start, end = resolve_date_range(period="month", billing_cutoff_day=15)
            assert start == "2024-02-01"
            assert end == "2024-02-29"


class TestExtractRelationship:
    """Tests for extract_relationship function."""

    def test_relationship_found(self):
        """Test extracting an existing relationship."""
        entry = {
            "relationships": {
                "service": {"data": {"id": "svc-1", "type": "services"}},
            },
        }
        included = {
            "svc-1": {
                "id": "svc-1",
                "type": "services",
                "attributes": {"name": "Development"},
            },
        }

        result = extract_relationship(entry, "service", included, "name")

        assert result is not None
        assert result["id"] == "svc-1"
        assert result["name"] == "Development"

    def test_relationship_not_found(self):
        """Test when relationship doesn't exist."""
        entry = {"relationships": {}}
        included = {}

        result = extract_relationship(entry, "service", included, "name")

        assert result is None

    def test_relationship_not_in_included(self):
        """Test when relationship exists but not in included."""
        entry = {
            "relationships": {
                "service": {"data": {"id": "svc-1", "type": "services"}},
            },
        }
        included = {}  # Empty included

        result = extract_relationship(entry, "service", included, "name")

        assert result is None

    def test_custom_attribute_name(self):
        """Test extracting a custom attribute."""
        entry = {
            "relationships": {
                "task": {"data": {"id": "task-1", "type": "tasks"}},
            },
        }
        included = {
            "task-1": {
                "id": "task-1",
                "type": "tasks",
                "attributes": {"title": "Feature X"},
            },
        }

        result = extract_relationship(entry, "task", included, "title")

        assert result is not None
        assert result["id"] == "task-1"
        assert result["title"] == "Feature X"


class TestProjectTypeConstants:
    """Tests for project type constants."""

    def test_internal_project_type(self):
        """Test internal project type constant."""
        assert PROJECT_TYPE_INTERNAL == "1"

    def test_client_project_type(self):
        """Test client project type constant."""
        assert PROJECT_TYPE_CLIENT == "2"


class TestGetBillingCutoffDay:
    """Tests for get_billing_cutoff_day function."""

    def test_default_value(self, monkeypatch):
        """Test default value when env var not set."""
        monkeypatch.delenv("PRODUCTIVE_BILLING_CUTOFF_DAY", raising=False)
        assert get_billing_cutoff_day() == DEFAULT_BILLING_CUTOFF_DAY

    def test_custom_value(self, monkeypatch):
        """Test custom value from env var."""
        monkeypatch.setenv("PRODUCTIVE_BILLING_CUTOFF_DAY", "15")
        assert get_billing_cutoff_day() == 15

    def test_value_too_low(self, monkeypatch):
        """Test value below valid range returns default with warning."""
        monkeypatch.setenv("PRODUCTIVE_BILLING_CUTOFF_DAY", "0")
        with pytest.warns(UserWarning, match="out of range"):
            result = get_billing_cutoff_day()
        assert result == DEFAULT_BILLING_CUTOFF_DAY

    def test_value_too_high(self, monkeypatch):
        """Test value above valid range returns default with warning."""
        monkeypatch.setenv("PRODUCTIVE_BILLING_CUTOFF_DAY", "29")
        with pytest.warns(UserWarning, match="out of range"):
            result = get_billing_cutoff_day()
        assert result == DEFAULT_BILLING_CUTOFF_DAY

    def test_invalid_value(self, monkeypatch):
        """Test non-integer value returns default."""
        monkeypatch.setenv("PRODUCTIVE_BILLING_CUTOFF_DAY", "not-a-number")
        assert get_billing_cutoff_day() == DEFAULT_BILLING_CUTOFF_DAY

    def test_boundary_value_1(self, monkeypatch):
        """Test minimum valid value (1)."""
        monkeypatch.setenv("PRODUCTIVE_BILLING_CUTOFF_DAY", "1")
        assert get_billing_cutoff_day() == 1

    def test_boundary_value_28(self, monkeypatch):
        """Test maximum valid value (28)."""
        monkeypatch.setenv("PRODUCTIVE_BILLING_CUTOFF_DAY", "28")
        assert get_billing_cutoff_day() == 28


class TestFormatHoursEdgeCases:
    """Additional edge case tests for format_hours."""

    def test_negative_value(self):
        """Test with negative value."""
        result = format_hours(-60)
        assert result == -1.0

    def test_large_value(self):
        """Test with large value (full month)."""
        # 10000 minutes = 166.67 hours
        result = format_hours(10000)
        assert result == 166.67

    def test_float_input(self):
        """Test with float input."""
        result = format_hours(90.5)
        assert result == 1.51
