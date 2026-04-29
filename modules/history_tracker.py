"""
history_tracker.py — Daily Portfolio Snapshot & Historical Performance

Saves a daily snapshot of portfolio value to data/portfolio_history.json.
Provides 30/60/90-day performance charts and trend analysis.

Run take_snapshot() once per day (or call from the app) to build history over time.
"""

import json
import os
from datetime import datetime, date, timedelta

BASE_DIR      = os.path.dirname(os.path.dirname(__file__))
HISTORY_PATH  = os.path.join(BASE_DIR, "data", "portfolio_history.json")
PORTFOLIO_PATH = os.path.join(BASE_DIR, "data", "portfolio.json")


# ── Load / save history ───────────────────────────────────────────────────────
def load_history() -> list:
    """Load all historical snapshots. Returns list of {date, value, cost, pnl, pnl_pct} dicts."""
    if not os.path.exists(HISTORY_PATH):
        return []
    with open(HISTORY_PATH) as f:
        return json.load(f).get("snapshots", [])


def save_history(snapshots: list):
    with open(HISTORY_PATH, "w") as f:
        json.dump({"snapshots": snapshots, "updated": str(datetime.now())}, f, indent=2)


# ── Snapshot ──────────────────────────────────────────────────────────────────
def take_snapshot(total_value: float = None, total_cost: float = None) -> dict:
    """
    Record today's portfolio value.
    If values not passed, calculates them from portfolio.json + live prices.
    Returns the saved snapshot dict.
    """
    today = str(date.today())

    # Calculate from portfolio if not provided
    if total_value is None or total_cost is None:
        total_value, total_cost = _calc_portfolio_value()

    pnl     = total_value - total_cost
    pnl_pct = (pnl / total_cost * 100) if total_cost else 0.0

    snapshot = {
        "date":    today,
        "value":   round(total_value, 2),
        "cost":    round(total_cost, 2),
        "pnl":     round(pnl, 2),
        "pnl_pct": round(pnl_pct, 4),
    }

    snapshots = load_history()

    # Replace today's snapshot if already exists
    snapshots = [s for s in snapshots if s.get("date") != today]
    snapshots.append(snapshot)

    # Keep last 2 years of data (730 days)
    snapshots = sorted(snapshots, key=lambda x: x["date"])[-730:]
    save_history(snapshots)

    return snapshot


def _calc_portfolio_value() -> tuple:
    """Calculate total portfolio value and cost from portfolio.json + yfinance."""
    if not os.path.exists(PORTFOLIO_PATH):
        return 0.0, 0.0
    with open(PORTFOLIO_PATH) as f:
        data = json.load(f)

    holdings    = data.get("holdings", [])
    total_value = 0.0
    total_cost  = 0.0

    try:
        import yfinance as yf
        for h in holdings:
            sym    = h.get("symbol", "")
            shares = float(h.get("shares", 0) or 0)
            cost   = float(h.get("avg_cost", 0) or 0)
            if shares <= 0 or not sym:
                continue
            try:
                t = yf.Ticker(sym)
                hist = t.history(period="2d")
                if not hist.empty:
                    price = float(hist["Close"].iloc[-1])
                    total_value += price * shares
                    total_cost  += cost * shares
            except Exception:
                total_cost += cost * shares
    except ImportError:
        pass

    return total_value, total_cost


# ── Filtering ─────────────────────────────────────────────────────────────────
def get_history_range(days: int = 30) -> list:
    """Return snapshots from the last N days."""
    snapshots  = load_history()
    cutoff     = str(date.today() - timedelta(days=days))
    return [s for s in snapshots if s["date"] >= cutoff]


def get_performance_summary(days: int = 30) -> dict:
    """
    Return performance stats for the last N days:
    start_value, end_value, change, change_pct, high, low, num_days
    """
    snaps = get_history_range(days)
    if not snaps:
        return {}

    values    = [s["value"] for s in snaps]
    start_val = snaps[0]["value"]
    end_val   = snaps[-1]["value"]
    change    = end_val - start_val
    change_pct= (change / start_val * 100) if start_val else 0

    return {
        "start_value":  start_val,
        "end_value":    end_val,
        "change":       round(change, 2),
        "change_pct":   round(change_pct, 2),
        "high":         max(values),
        "low":          min(values),
        "num_days":     len(snaps),
        "period":       f"{days}d",
    }


# ── Charts ────────────────────────────────────────────────────────────────────
def portfolio_value_chart(days: int = 30):
    """
    Returns a Plotly figure: portfolio value over the last N days.
    """
    import plotly.graph_objects as go

    snaps = get_history_range(days)

    if not snaps:
        fig = go.Figure()
        fig.add_annotation(
            text="No history yet. Snapshots are saved daily.",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(color="#8ba0b4", size=14)
        )
        fig.update_layout(
            paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
            height=300, margin=dict(l=20, r=20, t=30, b=20),
        )
        return fig

    dates  = [s["date"] for s in snaps]
    values = [s["value"] for s in snaps]
    costs  = [s["cost"]  for s in snaps]

    start_val = values[0] if values else 0
    color     = "#2ECC71" if values[-1] >= start_val else "#E74C3C"

    fig = go.Figure()

    # Cost basis area
    fig.add_trace(go.Scatter(
        x=dates, y=costs,
        fill="tozeroy", fillcolor="rgba(100,116,139,0.15)",
        line=dict(color="rgba(100,116,139,0.4)", width=1, dash="dot"),
        name="Cost Basis", hovertemplate="%{x}: $%{y:,.2f}<extra>Cost Basis</extra>",
    ))

    # Portfolio value line
    fig.add_trace(go.Scatter(
        x=dates, y=values,
        fill="tonexty", fillcolor=f"rgba({'46,204,113' if color == '#2ECC71' else '231,76,60'},0.15)",
        line=dict(color=color, width=2.5),
        name="Portfolio Value",
        hovertemplate="%{x}: $%{y:,.2f}<extra>Value</extra>",
        mode="lines",
    ))

    fig.update_layout(
        title=dict(text=f"Portfolio Value — Last {days} Days", font=dict(color="#e2e8f0", size=15)),
        paper_bgcolor="#0e1117", plot_bgcolor="#151c27",
        height=320,
        margin=dict(l=10, r=10, t=40, b=20),
        hovermode="x unified",
        xaxis=dict(showgrid=False, color="#64748b", tickfont=dict(size=10)),
        yaxis=dict(
            showgrid=True, gridcolor="#1e2a3a", color="#64748b",
            tickprefix="$", tickformat=",.0f", tickfont=dict(size=10),
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1, font=dict(color="#94a3b8", size=10),
        ),
    )
    return fig


def pnl_history_chart(days: int = 30):
    """Returns a Plotly bar chart of daily P&L change."""
    import plotly.graph_objects as go

    snaps = get_history_range(days)
    if len(snaps) < 2:
        fig = go.Figure()
        fig.add_annotation(
            text="Need at least 2 days of data to show P&L chart.",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(color="#8ba0b4", size=13)
        )
        fig.update_layout(
            paper_bgcolor="#0e1117", plot_bgcolor="#0e1117", height=260,
            margin=dict(l=20, r=20, t=30, b=20),
        )
        return fig

    dates   = [s["date"] for s in snaps[1:]]
    changes = [
        round(snaps[i]["value"] - snaps[i-1]["value"], 2)
        for i in range(1, len(snaps))
    ]
    colors  = ["#2ECC71" if c >= 0 else "#E74C3C" for c in changes]

    fig = go.Figure(go.Bar(
        x=dates, y=changes,
        marker_color=colors,
        hovertemplate="%{x}: %{y:+$,.2f}<extra></extra>",
        name="Daily Change",
    ))
    fig.update_layout(
        title=dict(text=f"Daily Value Change — Last {days} Days", font=dict(color="#e2e8f0", size=15)),
        paper_bgcolor="#0e1117", plot_bgcolor="#151c27",
        height=260,
        margin=dict(l=10, r=10, t=40, b=20),
        xaxis=dict(showgrid=False, color="#64748b", tickfont=dict(size=10)),
        yaxis=dict(
            showgrid=True, gridcolor="#1e2a3a", color="#64748b",
            tickprefix="$", zeroline=True, zerolinecolor="#334155",
            tickfont=dict(size=10),
        ),
        showlegend=False,
    )
    return fig
