"""Tests for utility functions."""

from datetime import date
from unittest.mock import patch

import pytest

from productive_time_mcp.utils import (
    calculate_period,
    format_hours,
    format_hours_response,
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

    @patch("productive_time_mcp.utils.date")
    def test_month_after_21st_uses_current(self, mock_date):
        """Test month calculation after 21st uses current month."""
        mock_date.today.return_value = date(2024, 2, 25)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        start, end = calculate_period("month")
        assert start == "2024-02-01"
        assert end == "2024-02-29"  # 2024 is leap year

    @patch("productive_time_mcp.utils.date")
    def test_month_before_21st_uses_previous(self, mock_date):
        """Test month calculation before 21st uses previous month."""
        mock_date.today.return_value = date(2024, 2, 15)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        start, end = calculate_period("month")
        assert start == "2024-01-01"
        assert end == "2024-01-31"

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
