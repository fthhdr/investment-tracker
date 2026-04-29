"""
contribution_reminder.py — Monthly contribution reminder system.
Checks if you're on track with your monthly investment goal.
Shows urgency level based on how far into the month you are.
"""

import json
import os
from datetime import date, datetime
import calendar

BASE_DIR       = os.path.dirname(os.path.dirname(__file__))
PORTFOLIO_PATH = os.path.join(BASE_DIR, "data", "transactions.json")

MINIMUM_MONTHLY = 500.0
TARGET_MONTHLY  = 650.0


def get_days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def get_contribution_status() -> dict:
    """
    Returns a detailed status of this month's contribution progress.
    """
    today       = date.today()
    year        = today.year
    month       = today.month
    day         = today.day
    days_in_month = get_days_in_month(year, month)
    days_left   = days_in_month - day
    pct_through = day / days_in_month  # how far through the month we are

    # Load actual contribution data
    try:
        with open(PORTFOLIO_PATH) as f:
            data = json.load(f)
    except Exception:
        data = {}

    contributions = data.get("monthly_contributions", [])
    month_key     = f"{year}-{month:02d}"

    current = next(
        (c for c in contributions if c.get("month") == month_key),
        None
    )

    actual  = current.get("actual", 0) if current else 0
    planned = current.get("planned", TARGET_MONTHLY) if current else TARGET_MONTHLY

    remaining_to_target  = max(planned - actual, 0)
    remaining_to_minimum = max(MINIMUM_MONTHLY - actual, 0)
    pct_complete         = (actual / planned * 100) if planned else 0

    # Expected contribution by now (linear projection)
    expected_by_now = planned * pct_through
    ahead_behind    = actual - expected_by_now  # positive = ahead

    # Urgency level
    if actual >= planned:
        urgency = "complete"
        message = f"🎉 Goal complete! You've invested ${actual:,.0f} this month."
    elif actual >= MINIMUM_MONTHLY:
        urgency = "on_track"
        message = f"✅ Minimum met! ${actual:,.0f} invested. ${remaining_to_target:,.0f} left to hit your ${planned:,.0f} goal."
    elif days_left <= 5 and remaining_to_minimum > 0:
        urgency = "critical"
        message = f"🔴 URGENT: Only {days_left} days left! You need ${remaining_to_minimum:,.0f} more to hit the minimum."
    elif days_left <= 10 and remaining_to_minimum > 0:
        urgency = "warning"
        message = f"⚠️ {days_left} days left this month. Need ${remaining_to_minimum:,.0f} more for minimum, ${remaining_to_target:,.0f} for goal."
    else:
        urgency = "info"
        message = f"📅 {days_left} days left. ${actual:,.0f} invested of ${planned:,.0f} goal."

    return {
        "month":               month_key,
        "today":               str(today),
        "day":                 day,
        "days_in_month":       days_in_month,
        "days_left":           days_left,
        "pct_through_month":   round(pct_through * 100, 1),
        "actual":              actual,
        "planned":             planned,
        "remaining_to_target": round(remaining_to_target, 2),
        "remaining_to_minimum":round(remaining_to_minimum, 2),
        "pct_complete":        round(pct_complete, 1),
        "expected_by_now":     round(expected_by_now, 2),
        "ahead_behind":        round(ahead_behind, 2),
        "urgency":             urgency,
        "message":             message,
        "minimum":             MINIMUM_MONTHLY,
        "target":              planned,
    }


def get_weekly_breakdown(planned: float) -> list:
    """
    Break the monthly goal into weekly targets.
    Shows how much to invest each week to stay on track.
    """
    today         = date.today()
    days_in_month = get_days_in_month(today.year, today.month)
    weeks         = days_in_month / 7

    weekly_target = planned / weeks

    weeks_list = []
    for w in range(1, 5):
        start_day = (w - 1) * 7 + 1
        end_day   = min(w * 7, days_in_month)
        current_week = today.day >= start_day and today.day <= end_day
        past_week    = today.day > end_day
        weeks_list.append({
            "week":         w,
            "label":        f"Week {w} (Day {start_day}–{end_day})",
            "target":       round(weekly_target, 2),
            "is_current":   current_week,
            "is_past":      past_week,
        })
    return weeks_list


def get_yearly_projection(monthly_actual: float, monthly_target: float) -> dict:
    """Project full-year totals based on current pace."""
    today       = date.today()
    months_done = today.month - 1  # completed months this year
    months_left = 12 - today.month + 1

    projected_year = (monthly_actual * months_done) + (monthly_target * months_left)
    minimum_year   = MINIMUM_MONTHLY * 12
    target_year    = monthly_target * 12

    return {
        "projected_year": round(projected_year, 2),
        "minimum_year":   round(minimum_year, 2),
        "target_year":    round(target_year, 2),
        "months_left":    months_left,
    }
