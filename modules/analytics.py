"""
analytics.py — Performance metrics, risk analysis, and chart data preparation
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from modules.market_data import get_historical_data


# ── Colour palette ────────────────────────────────────────────────────────────
COLORS = {
    "STOCK":   "#4F86C6",
    "ETF":     "#54C6A4",
    "CRYPTO":  "#F5A623",
    "REIT":    "#9B59B6",
    "OPTIONS": "#E74C3C",
    "gain":    "#2ECC71",
    "loss":    "#E74C3C",
    "neutral": "#95A5A6",
}

TYPE_COLORS = [COLORS["STOCK"], COLORS["ETF"], COLORS["CRYPTO"],
               COLORS["REIT"], COLORS["OPTIONS"]]


# ── Allocation charts ─────────────────────────────────────────────────────────

def allocation_pie(df: pd.DataFrame) -> go.Figure:
    """Donut chart: portfolio allocation by asset type."""
    by_type = df.groupby("Type")["Market Value"].sum().reset_index()
    fig = px.pie(
        by_type, values="Market Value", names="Type",
        hole=0.45,
        color="Type",
        color_discrete_map=COLORS,
        title="Portfolio Allocation by Asset Type",
    )
    fig.update_traces(textposition="outside", textinfo="percent+label")
    fig.update_layout(showlegend=True, height=420, margin=dict(t=50, b=20, l=20, r=20))
    return fig


def allocation_bar(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar: individual holdings by market value."""
    sorted_df = df.sort_values("Market Value", ascending=True).tail(15)
    colors = [COLORS.get(t, "#4F86C6") for t in sorted_df["Type"]]
    fig = go.Figure(go.Bar(
        x=sorted_df["Market Value"],
        y=sorted_df["Symbol"],
        orientation="h",
        marker_color=colors,
        text=[f"${v:,.0f}" for v in sorted_df["Market Value"]],
        textposition="outside",
    ))
    fig.update_layout(
        title="Holdings by Market Value",
        xaxis_title="Market Value ($)",
        height=420,
        margin=dict(t=50, b=20, l=120, r=60),
    )
    return fig


# ── P&L charts ────────────────────────────────────────────────────────────────

def pnl_waterfall(df: pd.DataFrame) -> go.Figure:
    """Waterfall chart showing P&L contribution of each position."""
    sorted_df = df.sort_values("P&L ($)", ascending=False)
    colors = [COLORS["gain"] if v >= 0 else COLORS["loss"] for v in sorted_df["P&L ($)"]]
    fig = go.Figure(go.Bar(
        x=sorted_df["Symbol"],
        y=sorted_df["P&L ($)"],
        marker_color=colors,
        text=[f"${v:+,.0f}" for v in sorted_df["P&L ($)"]],
        textposition="outside",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.update_layout(
        title="P&L by Position",
        yaxis_title="Unrealized P&L ($)",
        height=420,
        margin=dict(t=50, b=80, l=60, r=20),
    )
    return fig


def pnl_percentage_chart(df: pd.DataFrame) -> go.Figure:
    """Bar chart of P&L % by position."""
    sorted_df = df.sort_values("P&L (%)", ascending=False)
    colors = [COLORS["gain"] if v >= 0 else COLORS["loss"] for v in sorted_df["P&L (%)"]]
    fig = go.Figure(go.Bar(
        x=sorted_df["Symbol"],
        y=sorted_df["P&L (%)"],
        marker_color=colors,
        text=[f"{v:+.1f}%" for v in sorted_df["P&L (%)"]],
        textposition="outside",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.update_layout(
        title="P&L % by Position",
        yaxis_title="Unrealized Return (%)",
        height=400,
        margin=dict(t=50, b=80, l=60, r=20),
    )
    return fig


# ── Historical price chart ────────────────────────────────────────────────────

def price_history_chart(symbol: str, period: str = "1y") -> go.Figure:
    """Candlestick + volume chart for a given symbol."""
    df = get_historical_data(symbol, period)
    if df.empty:
        fig = go.Figure()
        fig.update_layout(title=f"No data available for {symbol}")
        return fig

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.03,
    )
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"], high=df["High"],
        low=df["Low"],  close=df["Close"],
        name=symbol,
        increasing_line_color=COLORS["gain"],
        decreasing_line_color=COLORS["loss"],
    ), row=1, col=1)

    vol_colors = [COLORS["gain"] if c >= o else COLORS["loss"]
                  for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(
        x=df.index, y=df["Volume"],
        marker_color=vol_colors, name="Volume", opacity=0.6,
    ), row=2, col=1)

    # 20/50-day MAs
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    fig.add_trace(go.Scatter(x=df.index, y=df["MA20"],
                             line=dict(color="orange", width=1.2),
                             name="MA20"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MA50"],
                             line=dict(color="blue", width=1.2),
                             name="MA50"), row=1, col=1)

    fig.update_layout(
        title=f"{symbol} — Price History ({period})",
        xaxis_rangeslider_visible=False,
        height=520,
        margin=dict(t=50, b=20, l=60, r=20),
    )
    return fig


def portfolio_value_history(transactions: list, current_df: pd.DataFrame) -> go.Figure:
    """Approximate portfolio value over time from transaction history."""
    if not transactions:
        return go.Figure()

    tx_df = pd.DataFrame(transactions)
    tx_df["date"] = pd.to_datetime(tx_df["date"])
    tx_df = tx_df.sort_values("date")

    total_invested = tx_df["total"].sum()
    total_value = current_df["Market Value"].sum() if not current_df.empty else 0

    # Build date points: one per transaction + today
    today = pd.Timestamp.now().normalize()
    unique_dates = sorted(tx_df["date"].dt.normalize().unique().tolist() + [today])

    cost_series = []
    for d in unique_dates:
        cost = tx_df[tx_df["date"].dt.normalize() <= d]["total"].sum()
        cost_series.append({"Date": d, "Invested": round(cost, 2)})

    cost_df = pd.DataFrame(cost_series).drop_duplicates("Date")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=cost_df["Date"], y=cost_df["Invested"],
        fill="tozeroy", name="Total Invested",
        line=dict(color="#4F86C6", width=2),
        fillcolor="rgba(79,134,198,0.15)",
        mode="lines+markers",
    ))
    fig.add_hline(
        y=total_value, line_dash="dot",
        annotation_text=f"Current Value: ${total_value:,.0f}",
        line_color=COLORS["gain"] if total_value >= total_invested else COLORS["loss"],
    )
    fig.update_layout(
        title="Cumulative Capital Invested vs. Current Portfolio Value",
        yaxis_title="Value ($)",
        height=380,
        margin=dict(t=50, b=20, l=60, r=20),
    )
    return fig


# ── Risk / stats ──────────────────────────────────────────────────────────────

def calculate_portfolio_stats(df: pd.DataFrame) -> dict:
    """Return basic risk stats."""
    if df.empty:
        return {}
    total_value = df["Market Value"].sum()
    total_cost  = df["Cost Basis"].sum()
    top_winner  = df.loc[df["P&L ($)"].idxmax()]
    top_loser   = df.loc[df["P&L ($)"].idxmin()]
    concentration = df["Allocation %"].max()

    return {
        "total_value":    round(total_value, 2),
        "total_cost":     round(total_cost, 2),
        "total_pnl":      round(total_value - total_cost, 2),
        "total_return_pct": round(((total_value - total_cost) / total_cost) * 100, 2) if total_cost else 0,
        "top_winner":     f"{top_winner['Symbol']} (+${top_winner['P&L ($)']:,.0f})",
        "top_loser":      f"{top_loser['Symbol']} (${top_loser['P&L ($)']:,.0f})",
        "concentration":  round(concentration, 1),
        "num_positions":  len(df),
    }
