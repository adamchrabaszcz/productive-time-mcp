"""Tests for utility functions."""

from datetime import date
from unittest.mock import patch

import pytest

from productive_time_mcp.utils import (
    calculate_period,
    format_hours,
    format_hours_response,
    DEFAULT_BILLING_CUTOFF_DAY,
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
