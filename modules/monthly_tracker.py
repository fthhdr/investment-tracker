"""
monthly_tracker.py — Monthly contribution planner and tracker
"""

import json
import os
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# Default allocation strategy (adjustable)
DEFAULT_ALLOCATION = {
    "stocks": 0.40,   # 40%
    "etf":    0.25,   # 25%
    "crypto": 0.20,   # 20%
    "reit":   0.15,   # 15%
}

MINIMUM_MONTHLY = 500.00  # absolute minimum monthly investment


def load_contributions() -> list:
    path = os.path.join(DATA_DIR, "transactions.json")
    with open(path, "r") as f:
        data = json.load(f)
    return data.get("monthly_contributions", [])


def save_contributions(contributions: list):
    path = os.path.join(DATA_DIR, "transactions.json")
    with open(path, "r") as f:
        data = json.load(f)
    data["monthly_contributions"] = contributions
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_current_month_key() -> str:
    return datetime.now().strftime("%Y-%m")


def get_contribution_df() -> pd.DataFrame:
    contributions = load_contributions()
    rows = []
    for c in contributions:
        month = c["month"]
        planned = c.get("planned", 0)
        actual = c.get("actual", 0)
        diff = actual - planned
        status = "On Track" if actual >= planned else ("Pending" if actual == 0 else "Under")
        rows.append({
            "Month": month,
            "Planned ($)": planned,
            "Actual ($)": actual,
            "Difference ($)": round(diff, 2),
            "Status": status,
        })
    return pd.DataFrame(rows)


def suggest_allocation(monthly_budget: float, allocation: dict = None) -> dict:
    """Given a monthly budget, return suggested allocation by asset class."""
    if not allocation:
        allocation = DEFAULT_ALLOCATION
    return {k: round(v * monthly_budget, 2) for k, v in allocation.items()}


def log_monthly_contribution(month: str, planned: float, actual: float, allocated: dict):
    """Record or update a monthly contribution entry."""
    contributions = load_contributions()
    for c in contributions:
        if c["month"] == month:
            c["planned"] = planned
            c["actual"] = actual
            c["allocated"] = allocated
            save_contributions(contributions)
            return
    contributions.append({
        "month": month,
        "planned": planned,
        "actual": actual,
        "allocated": allocated,
    })
    save_contributions(contributions)


def contributions_chart(df: pd.DataFrame) -> go.Figure:
    """Grouped bar: planned vs actual monthly contributions."""
    if df.empty:
        return go.Figure()
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["Month"], y=df["Planned ($)"],
        name="Planned", marker_color="#4F86C6",
        opacity=0.7,
    ))
    fig.add_trace(go.Bar(
        x=df["Month"], y=df["Actual ($)"],
        name="Actual", marker_color="#2ECC71",
        opacity=0.9,
    ))
    fig.add_hline(y=MINIMUM_MONTHLY, line_dash="dash",
                  annotation_text=f"Minimum (${MINIMUM_MONTHLY:,.0f})",
                  line_color="#E74C3C")
    fig.update_layout(
        title="Monthly Investment Contributions — Planned vs Actual",
        yaxis_title="Amount ($)",
        barmode="group",
        height=380,
        margin=dict(t=50, b=40, l=60, r=20),
    )
    return fig


def cumulative_contributions_chart(df: pd.DataFrame) -> go.Figure:
    """Line chart of cumulative invested capital."""
    if df.empty:
        return go.Figure()
    df = df.copy()
    df["Cumulative Invested"] = df["Actual ($)"].cumsum()
    df["Cumulative Planned"] = df["Planned ($)"].cumsum()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["Month"], y=df["Cumulative Planned"],
        name="Planned", line=dict(color="#4F86C6", width=2, dash="dash"),
    ))
    fig.add_trace(go.Scatter(
        x=df["Month"], y=df["Cumulative Invested"],
        name="Actual Invested", line=dict(color="#2ECC71", width=2.5),
        fill="tozeroy", fillcolor="rgba(46,204,113,0.1)",
    ))
    fig.update_layout(
        title="Cumulative Investment Progress",
        yaxis_title="Total Invested ($)",
        height=360,
        margin=dict(t=50, b=40, l=60, r=20),
    )
    return fig


def get_monthly_status_summary() -> dict:
    """Quick status summary for the current month."""
    contributions = load_contributions()
    current = get_current_month_key()
    for c in contributions:
        if c["month"] == current:
            actual = c.get("actual", 0)
            planned = c.get("planned", MINIMUM_MONTHLY)
            remaining = max(planned - actual, 0)
            return {
                "month": current,
                "planned": planned,
                "actual": actual,
                "remaining": remaining,
                "on_track": actual >= MINIMUM_MONTHLY,
                "pct_complete": round((actual / planned) * 100, 1) if planned else 0,
                "allocated": c.get("allocated", {}),
            }
    return {
        "month": current,
        "planned": MINIMUM_MONTHLY,
        "actual": 0,
        "remaining": MINIMUM_MONTHLY,
        "on_track": False,
        "pct_complete": 0,
        "allocated": {},
    }
