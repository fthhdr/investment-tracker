"""
Investment Tracker Dashboard — Streamlit App
Run with:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys, os

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from modules.portfolio import (
    get_enriched_portfolio, get_portfolio_summary,
    load_transactions, add_holding, log_transaction,
)
from modules.analytics import (
    allocation_pie, allocation_bar, pnl_waterfall,
    pnl_percentage_chart, price_history_chart,
    portfolio_value_history, calculate_portfolio_stats,
)
from modules.monthly_tracker import (
    get_contribution_df, get_monthly_status_summary,
    suggest_allocation, log_monthly_contribution,
    contributions_chart, cumulative_contributions_chart,
    MINIMUM_MONTHLY,
)
from modules.market_data import get_market_movers
from modules.excel_sync import sync_to_excel
from modules.alpaca_connect import (
    is_configured, load_config, save_config,
    get_account_summary, get_alpaca_positions,
    get_recent_orders, place_market_order,
    ALPACA_AVAILABLE,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Investment Tracker 2026",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="auto",   # auto-collapses on mobile, expands on desktop
)

# Suppress deprecation warnings for use_container_width (still functional in this version)
# deprecation.showfileUploaderEncoding removed in Streamlit 1.x+

# ── PWA / Add to Home Screen support ─────────────────────────────────────────
st.markdown("""
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Investment Tracker">
<meta name="theme-color" content="#0D1B2A">
<link rel="apple-touch-icon" href="https://img.icons8.com/fluency/96/stock-share.png">
""", unsafe_allow_html=True)

# ── Custom CSS (Clean & Modern — desktop + mobile responsive) ────────────────
st.markdown("""
<style>
  /* ── Global base ── */
  html, body, [data-testid="stAppViewContainer"] {
    background-color: #F1F5F9 !important;
  }
  .block-container {
    padding: 1.5rem 2rem 3rem !important;
    max-width: 1200px !important;
  }

  /* ── Sidebar: dark navy ── */
  [data-testid="stSidebar"] {
    background-color: #0F172A !important;
  }
  [data-testid="stSidebar"] * {
    color: #CBD5E1 !important;
  }
  [data-testid="stSidebar"] .stMarkdown p,
  [data-testid="stSidebar"] .stCaption {
    color: #64748B !important;
    font-size: 11px !important;
  }
  [data-testid="stSidebar"] h1,
  [data-testid="stSidebar"] h2,
  [data-testid="stSidebar"] h3 {
    color: #F8FAFC !important;
  }

  /* ── Sidebar nav: compact technical style ── */
  [data-testid="stSidebar"] .stRadio > div {
    gap: 0px !important;
  }
  [data-testid="stSidebar"] .stRadio label {
    background: transparent;
    border-radius: 4px;
    padding: 5px 10px !important;
    cursor: pointer;
    transition: background 0.12s;
    display: block !important;
    width: 100% !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    color: #94A3B8 !important;
    line-height: 1.4 !important;
  }
  [data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(255,255,255,0.06) !important;
    color: #CBD5E1 !important;
  }
  [data-testid="stSidebar"] .stRadio [data-checked="true"] ~ label,
  [data-testid="stSidebar"] .stRadio label[data-checked="true"] {
    background: rgba(37,99,235,0.18) !important;
    border-left: 3px solid #3B82F6 !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    padding-left: 7px !important;
  }
  /* Hide radio circles only — not the text labels */
  [data-testid="stSidebar"] .stRadio input[type="radio"] {
    display: none !important;
  }
  /* Hide the circle indicator (first child of BaseWeb radio) */
  [data-testid="stSidebar"] [data-baseweb="radio"] > div:first-child {
    display: none !important;
    width: 0 !important;
    min-width: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
  }
  /* Hide widget label (section title shown by Streamlit above radio) */
  [data-testid="stSidebar"] .stRadio div[data-testid="stWidgetLabel"],
  [data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
    display: none !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
  }
  /* Tighten spacing between radio groups */
  [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div {
    padding-bottom: 0px !important;
    margin-bottom: 0px !important;
  }

  /* ── Hero banner ── */
  .hero-banner {
    background: linear-gradient(135deg, #1D4ED8 0%, #2563EB 50%, #3B82F6 100%);
    border-radius: 14px;
    padding: 28px 32px;
    margin-bottom: 24px;
    color: white;
  }
  .hero-value {
    font-size: 3rem;
    font-weight: 800;
    color: white;
    line-height: 1;
    margin-bottom: 6px;
  }
  .hero-sub { font-size: 1rem; opacity: 0.85; }

  /* ── KPI cards ── */
  .kpi-card {
    background: white;
    border-radius: 10px;
    padding: 18px 20px;
    margin-bottom: 10px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.07);
    border: 1px solid #E2E8F0;
  }
  .kpi-value {
    font-size: 1.8rem;
    font-weight: 700;
    color: #1E293B;
    line-height: 1.1;
  }
  .kpi-label {
    font-size: 0.78rem;
    color: #64748B;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 3px;
  }

  /* ── Metrics ── */
  div[data-testid="stMetricValue"] {
    font-size: 1.4rem !important;
    font-weight: 700 !important;
    color: #1E293B !important;
  }
  div[data-testid="stMetricLabel"] { color: #64748B !important; }
  div[data-testid="stMetricDelta"]  { font-size: 0.82rem !important; }

  /* ── Status colours ── */
  .positive { color: #10B981 !important; }
  .negative { color: #EF4444 !important; }
  .neutral  { color: #64748B !important; }

  /* ── Old dark metric card (kept for legacy pages) ── */
  .metric-card {
    background: white;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    border: 1px solid #E2E8F0;
  }
  .big-metric { font-size: 2rem; font-weight: 700; color: #1E293B; }

  /* ── Mobile quick-summary card ── */
  .mobile-card {
    background: linear-gradient(135deg, #1a2a4a 0%, #0D1B2A 100%);
    border-radius: 14px;
    padding: 16px 18px;
    margin-bottom: 12px;
    border-left: 4px solid #F0B429;
  }
  .mobile-card h3 { color: #F0B429; margin: 0 0 4px 0; font-size: 0.9rem; }
  .mobile-card .val { color: #fff; font-size: 1.8rem; font-weight: 700; }
  .mobile-card .sub { color: #8ba0b4; font-size: 0.82rem; }

  /* ── Plotly ── */
  .js-plotly-plot .plotly, .stPlotlyChart { width: 100% !important; }

  /* ── Mobile responsive ── */
  @media (max-width: 768px) {
    [data-testid="column"] {
      width: 100% !important; flex: 1 1 100% !important; min-width: 100% !important;
    }
    .block-container { padding: 0.75rem 0.75rem 2rem !important; max-width: 100% !important; }
    [data-testid="stSidebar"] { width: 85vw !important; min-width: 260px !important; }
    div[data-testid="stMetricValue"] { font-size: 1.25rem !important; }
    .stButton > button { height: 48px !important; font-size: 1rem !important; width: 100% !important; }
    input[type="text"], input[type="number"], textarea, select { font-size: 1rem !important; }
    .stRadio label { font-size: 1rem !important; padding: 10px 0 !important; display: block !important; }
    [data-testid="stDataFrame"] { overflow-x: auto !important; }
    [data-testid="stDataFrame"] table { font-size: 0.78rem !important; }
    .js-plotly-plot, .plotly { width: 100% !important; }
    .stTabs [data-baseweb="tab"] { font-size: 0.82rem !important; padding: 8px 10px !important; }
    .stProgress > div > div { height: 14px !important; border-radius: 7px !important; }
    .stAlert { font-size: 0.95rem !important; padding: 12px 14px !important; }
    .modebar { display: none !important; }
    h1 { font-size: 1.5rem !important; }
    h2 { font-size: 1.25rem !important; }
    h3 { font-size: 1.1rem !important; }
    .stCaption { font-size: 0.78rem !important; }
    hr { margin: 0.75rem 0 !important; }
    [data-testid="stFormSubmitButton"] > button {
      height: 52px !important; font-size: 1.05rem !important; width: 100% !important;
    }
  }
  @media (max-width: 480px) {
    div[data-testid="stMetricValue"] { font-size: 1.1rem !important; }
    h1 { font-size: 1.25rem !important; }
    .block-container { padding: 0.5rem 0.5rem 2rem !important; }
  }

  /* ── (duplicate mobile section removed) ── */
  @media (max-width: 768px) {
    [data-testid="column"] {
      width: 100% !important;
      flex: 1 1 100% !important;
      min-width: 100% !important;
    }

    /* Reduce main content padding so more fits */
    .block-container {
      padding: 0.75rem 0.75rem 2rem !important;
      max-width: 100% !important;
    }

    /* Sidebar: takes most of the screen when open */
    [data-testid="stSidebar"] {
      width: 85vw !important;
      min-width: 260px !important;
    }

    /* Larger metric values — easier to read at a glance */
    div[data-testid="stMetricValue"] {
      font-size: 1.25rem !important;
    }
    div[data-testid="stMetricLabel"] {
      font-size: 0.78rem !important;
    }
    div[data-testid="stMetricDelta"] {
      font-size: 0.78rem !important;
    }

    /* Big thumb-friendly buttons */
    .stButton > button {
      height: 48px !important;
      font-size: 1rem !important;
      width: 100% !important;
      border-radius: 8px !important;
    }

    /* Form inputs — easier to tap */
    input[type="text"],
    input[type="number"],
    textarea,
    select {
      font-size: 1rem !important;
      height: 44px !important;
    }

    /* Selectbox & text input wrappers */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
      font-size: 1rem !important;
    }

    /* Radio nav items — more spacing for tapping */
    .stRadio label {
      font-size: 1rem !important;
      padding: 10px 0 !important;
      display: block !important;
    }
    .stRadio > div {
      gap: 4px !important;
    }

    /* Expanders — full width, bigger tap target */
    details > summary {
      font-size: 1rem !important;
      padding: 12px 8px !important;
    }

    /* DataFrames — horizontal scroll on small screen */
    [data-testid="stDataFrame"] {
      overflow-x: auto !important;
    }
    [data-testid="stDataFrame"] table {
      font-size: 0.78rem !important;
    }

    /* Plotly charts — full width */
    .js-plotly-plot, .plotly {
      width: 100% !important;
    }

    /* Tabs — smaller text so they don't overflow */
    .stTabs [data-baseweb="tab"] {
      font-size: 0.82rem !important;
      padding: 8px 10px !important;
    }

    /* Progress bars — taller so they're more visible */
    .stProgress > div > div {
      height: 14px !important;
      border-radius: 7px !important;
    }

    /* Alerts / banners — full width, readable */
    .stAlert {
      font-size: 0.95rem !important;
      padding: 12px 14px !important;
    }

    /* Hide the chart icons toolbar on mobile (saves space) */
    .modebar {
      display: none !important;
    }

    /* Section headers */
    h1 { font-size: 1.5rem !important; }
    h2 { font-size: 1.25rem !important; }
    h3 { font-size: 1.1rem !important; }

    /* Captions */
    .stCaption { font-size: 0.78rem !important; }

    /* Dividers */
    hr { margin: 0.75rem 0 !important; }

    /* Form submit button — big green tap target */
    [data-testid="stFormSubmitButton"] > button {
      height: 52px !important;
      font-size: 1.05rem !important;
      width: 100% !important;
    }
  }

  /* ── Extra-small phones (under 480px) ── */
  @media (max-width: 480px) {
    div[data-testid="stMetricValue"] {
      font-size: 1.1rem !important;
    }
    h1 { font-size: 1.25rem !important; }
    .block-container {
      padding: 0.5rem 0.5rem 2rem !important;
    }
    /* Stack metric columns 2x2 instead of 4x1 */
    [data-testid="column"]:nth-child(odd) {
      padding-right: 4px !important;
    }
    [data-testid="column"]:nth-child(even) {
      padding-left: 4px !important;
    }
  }

  /* ── Mobile quick-summary card ── */
  .mobile-card {
    background: linear-gradient(135deg, #1a2a4a 0%, #0D1B2A 100%);
    border-radius: 14px;
    padding: 16px 18px;
    margin-bottom: 12px;
    border-left: 4px solid #F0B429;
  }
  .mobile-card h3 { color: #F0B429; margin: 0 0 4px 0; font-size: 0.9rem; }
  .mobile-card .val { color: #fff; font-size: 1.8rem; font-weight: 700; }
  .mobile-card .sub { color: #8ba0b4; font-size: 0.82rem; }

  /* ── Plotly responsive wrapper ── */
  .js-plotly-plot .plotly {
    width: 100% !important;
  }
  .stPlotlyChart {
    width: 100% !important;
  }
</style>
""", unsafe_allow_html=True)

# ── Grouped sidebar navigation ────────────────────────────────────────────────
st.sidebar.markdown(
    '<div style="padding:16px 16px 4px;font-size:18px;font-weight:700;color:#F8FAFC;'
    'letter-spacing:0.02em">Investment Tracker</div>',
    unsafe_allow_html=True
)
st.sidebar.markdown('<hr style="border-color:#1E3A5F;margin:4px 0 12px"/>', unsafe_allow_html=True)

NAV_GROUPS = {
    "🏠  DASHBOARD": [
        "📊 Overview",
        "📈 Market Data",
        "🌅 Daily Briefing",
    ],
    "💼  MY PORTFOLIO": [
        "💼 Holdings",
        "➕ Add Position",
        "📅 Monthly Tracker",
        "💎 Net Worth Tracker",
    ],
    "📊  ANALYSIS": [
        "🔍 Stock Analysis",
        "📉 Portfolio History",
        "🎲 Monte Carlo",
        "⚙️ Options Calculator",
        "📋 Options Positions",
        "🧾 Tax Lots",
    ],
    "⚡  TRADING": [
        "🦙 Alpaca Trading",
        "🔴 Robinhood Sync",
        "🤖 Auto Trader",
        "📓 Trade Journal",
    ],
    "🛠️  TOOLS": [
        "👀 Watchlist",
        "🔔 Price Alerts",
        "🎯 Watchlist Targets",
        "⚖️ Rebalancing Tool",
        "💰 Contribution Reminder",
        "📤 Export P&L",
    ],
    "🧠  AI": [
        "🧠 AI Insights",
        "💡 What to Buy?",
    ],
}

# ── Nav callback — fires when any radio changes ───────────────────────────────
# LESSON: on_change callbacks run BEFORE the rest of the script on each rerun.
# This is the only reliable way to know WHICH radio group the user clicked in.
def _nav_changed(group_name):
    st.session_state["current_page"] = st.session_state[f"nav_{group_name}"]

# Initialise current page
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "📊 Overview"

# Render grouped nav
for group_name, group_pages in NAV_GROUPS.items():
    st.sidebar.markdown(
        f'<div style="padding:8px 10px 2px;font-size:9.5px;font-weight:700;'
        f'color:#475569;letter-spacing:0.1em;text-transform:uppercase;margin-top:4px">'
        f'{group_name}</div>',
        unsafe_allow_html=True
    )
    # Set index so the radio highlights the currently active page if it's in this group
    cur = st.session_state["current_page"]
    idx = group_pages.index(cur) if cur in group_pages else 0
    st.sidebar.radio(
        label=" ",
        options=group_pages,
        index=idx,
        label_visibility="collapsed",
        key=f"nav_{group_name}",
        on_change=_nav_changed,
        args=(group_name,),
    )

page = st.session_state["current_page"]

st.sidebar.markdown('<hr style="border-color:#1E3A5F;margin:12px 0 6px"/>', unsafe_allow_html=True)
st.sidebar.caption("Data refreshes on page load.")
st.sidebar.caption("Powered by yfinance & CoinGecko")

# ── Load data (cached 5 min) ──────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_portfolio_data():
    df = get_enriched_portfolio()
    return df

@st.cache_data(ttl=300)
def load_tx_data():
    return load_transactions()

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
if page == "📊 Overview":
    st.title("📊 Portfolio Overview")

    with st.spinner("Fetching live prices…"):
        df = load_portfolio_data()
        tx_data = load_tx_data()

    if df.empty:
        st.warning("No portfolio data found. Add positions using the sidebar.")
        st.stop()

    stats = calculate_portfolio_stats(df)
    monthly = get_monthly_status_summary()

    # ── Mobile quick-summary card (shows only on narrow screens via CSS) ──────
    pnl_arrow = "▲" if stats["total_pnl"] >= 0 else "▼"
    pnl_color = "#2ECC71" if stats["total_pnl"] >= 0 else "#E74C3C"
    pnl_sign  = "+" if stats["total_pnl"] >= 0 else ""
    st.markdown(f"""
    <div class="mobile-card">
      <h3>💼 PORTFOLIO SNAPSHOT</h3>
      <div class="val">${stats['total_value']:,.2f}</div>
      <div class="sub" style="color:{pnl_color};">
        {pnl_arrow} {pnl_sign}${stats['total_pnl']:,.2f} ({pnl_sign}{stats['total_return_pct']:.2f}%) all-time
      </div>
      <div class="sub">{stats['num_positions']} positions &nbsp;|&nbsp;
        {"✅ On Track" if monthly['on_track'] else "⚠️ Below Min"} this month
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── KPI row ───────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Portfolio Value", f"${stats['total_value']:,.2f}")
    c2.metric("Total Invested",  f"${stats['total_cost']:,.2f}")
    pnl_sign = "+" if stats["total_pnl"] >= 0 else ""
    c3.metric("Total P&L",
              f"{pnl_sign}${stats['total_pnl']:,.2f}",
              delta=f"{pnl_sign}{stats['total_return_pct']:.2f}%")
    c4.metric("Positions", stats["num_positions"])
    c5.metric("This Month",
              f"${monthly['actual']:,.0f} / ${monthly['planned']:,.0f}",
              delta=f"{'✅ On Track' if monthly['on_track'] else '⚠️ Below Minimum'}")

    st.markdown("---")

    # ── Charts row ────────────────────────────────────────────────────────────
    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.plotly_chart(allocation_pie(df), use_container_width=True)
    with col_r:
        st.plotly_chart(pnl_waterfall(df), use_container_width=True)

    st.plotly_chart(
        portfolio_value_history(tx_data.get("transactions", []), df),
        use_container_width=True,
    )

    # ── Quick stats ───────────────────────────────────────────────────────────
    st.subheader("Quick Highlights")
    hl1, hl2, hl3, hl4 = st.columns(4)
    hl1.metric("Top Winner",    stats.get("top_winner", "—"))
    hl2.metric("Top Loser",     stats.get("top_loser", "—"))
    hl3.metric("Winning Positions", f"{stats['num_positions'] - stats.get('losers', 0)} / {stats['num_positions']}")
    hl4.metric("Largest Allocation", f"{stats.get('concentration', 0):.1f}%")

    # ── Holdings table ────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("All Holdings")

    def color_pnl(val):
        if isinstance(val, float):
            color = "#2ECC71" if val >= 0 else "#E74C3C"
            return f"color: {color}"
        return ""

    styled = df[[
        "Symbol", "Type", "Shares", "Avg Cost", "Current Price",
        "Market Value", "P&L ($)", "P&L (%)", "Allocation %"
    ]].style.map(color_pnl, subset=["P&L ($)", "P&L (%)"]) \
             .format({
                 "Avg Cost": "${:,.2f}",
                 "Current Price": "${:,.2f}",
                 "Market Value": "${:,.2f}",
                 "P&L ($)": "${:+,.2f}",
                 "P&L (%)": "{:+.2f}%",
                 "Allocation %": "{:.1f}%",
             })
    st.dataframe(styled, use_container_width=True, height=380)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: MARKET DATA
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📈 Market Data":
    st.title("📈 Market Data & Movers")

    watchlist_input = st.text_input(
        "Watchlist (comma-separated tickers)",
        value="AAPL, MSFT, NVDA, VOO, QQQ, BTC-USD, ETH-USD, O, SPY, TSLA",
    )
    symbols = [s.strip().upper() for s in watchlist_input.split(",") if s.strip()]

    with st.spinner("Fetching market data…"):
        movers_df = get_market_movers(symbols)

    if not movers_df.empty:
        st.subheader("Daily Movers")
        col_pos, col_neg = st.columns(2)
        gainers = movers_df[movers_df["Daily Change %"] >= 0].sort_values("Daily Change %", ascending=False)
        losers  = movers_df[movers_df["Daily Change %"] < 0].sort_values("Daily Change %")

        with col_pos:
            st.markdown("**📈 Gainers**")
            st.dataframe(
                gainers.style.format({"Price": "${:,.2f}", "Daily Change %": "{:+.2f}%"}),
                use_container_width=True,
            )
        with col_neg:
            st.markdown("**📉 Losers**")
            st.dataframe(
                losers.style.format({"Price": "${:,.2f}", "Daily Change %": "{:+.2f}%"}),
                use_container_width=True,
            )

        # Movers bar chart
        colors = ["#2ECC71" if v >= 0 else "#E74C3C" for v in movers_df["Daily Change %"]]
        fig = go.Figure(go.Bar(
            x=movers_df["Symbol"],
            y=movers_df["Daily Change %"],
            marker_color=colors,
            text=[f"{v:+.2f}%" for v in movers_df["Daily Change %"]],
            textposition="outside",
        ))
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        fig.update_layout(title="Daily % Change — Watchlist", height=380,
                          yaxis_title="Change (%)",
                          margin=dict(t=50, b=40, l=60, r=20))
        st.plotly_chart(fig)
    else:
        st.info("No market data available. Check your internet connection.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: HOLDINGS
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "💼 Holdings":
    st.title("💼 Holdings Detail")
    with st.spinner("Loading portfolio…"):
        df = load_portfolio_data()

    # Filter by asset type
    types = ["All"] + sorted(df["Type"].unique().tolist())
    sel_type = st.selectbox("Filter by Asset Type", types)
    filtered = df if sel_type == "All" else df[df["Type"] == sel_type]

    col_l, col_r = st.columns(2)
    with col_l:
        st.plotly_chart(allocation_bar(filtered), use_container_width=True)
    with col_r:
        st.plotly_chart(pnl_percentage_chart(filtered), use_container_width=True)

    st.subheader("Full Holdings Table")
    st.dataframe(
        filtered.style.format({
            "Avg Cost": "${:,.2f}",
            "Current Price": "${:,.2f}",
            "Market Value": "${:,.2f}",
            "P&L ($)": "${:+,.2f}",
            "P&L (%)": "{:+.2f}%",
            "Allocation %": "{:.1f}%",
        }).map(
            lambda v: "color: #2ECC71" if isinstance(v, float) and v > 0
                      else ("color: #E74C3C" if isinstance(v, float) and v < 0 else ""),
            subset=["P&L ($)", "P&L (%)"],
        ),
        use_container_width=True,
        height=420,
    )

    # Allocation breakdown by type
    st.subheader("Allocation by Asset Type")
    by_type = filtered.groupby("Type").agg(
        Value=("Market Value", "sum"),
        PnL=("P&L ($)", "sum"),
        Count=("Symbol", "count"),
    ).reset_index()
    by_type["Return %"] = ((by_type["PnL"] / (by_type["Value"] - by_type["PnL"])) * 100).round(2)
    st.dataframe(by_type.style.format({
        "Value": "${:,.2f}",
        "PnL": "${:+,.2f}",
        "Return %": "{:+.2f}%",
    }), use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: MONTHLY TRACKER
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📅 Monthly Tracker":
    st.title("📅 Monthly Investment Tracker")

    monthly = get_monthly_status_summary()
    contrib_df = get_contribution_df()

    # ── Status banner ─────────────────────────────────────────────────────────
    if monthly["on_track"]:
        st.success(f"✅ **{monthly['month']}** — You're on track! "
                   f"${monthly['actual']:,.0f} invested of ${monthly['planned']:,.0f} planned.")
    else:
        remaining = monthly["remaining"]
        st.warning(f"⚠️ **{monthly['month']}** — ${monthly['actual']:,.0f} invested. "
                   f"Invest **${remaining:,.0f} more** to hit your ${monthly['planned']:,.0f} target "
                   f"(minimum: ${MINIMUM_MONTHLY:,.0f}).")

    # ── Progress bar ──────────────────────────────────────────────────────────
    pct = min(monthly["pct_complete"] / 100, 1.0)
    st.progress(pct, text=f"{monthly['pct_complete']:.1f}% of monthly goal")

    st.markdown("---")

    # ── Allocation suggester ──────────────────────────────────────────────────
    st.subheader("💡 Allocation Suggester")
    budget = st.slider("Monthly Investment Budget ($)", 500, 5000, 1500, 50)
    alloc = suggest_allocation(budget)
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Stocks (40%)",  f"${alloc['stocks']:,.0f}")
    a2.metric("ETFs (25%)",    f"${alloc['etf']:,.0f}")
    a3.metric("Crypto (20%)",  f"${alloc['crypto']:,.0f}")
    a4.metric("REITs (15%)",   f"${alloc['reit']:,.0f}")

    st.markdown("---")

    # ── Log this month ────────────────────────────────────────────────────────
    st.subheader("Log This Month's Contribution")
    with st.form("log_contribution"):
        col1, col2 = st.columns(2)
        with col1:
            log_planned = st.number_input("Planned ($)", min_value=0.0, value=1500.0, step=50.0)
        with col2:
            log_actual = st.number_input("Actual Invested ($)", min_value=0.0, value=0.0, step=50.0)
        submitted = st.form_submit_button("Save Contribution")
        if submitted:
            log_monthly_contribution(
                monthly["month"], log_planned, log_actual,
                suggest_allocation(log_actual),
            )
            # ── Auto-sync to Excel ────────────────────────────────────────────
            try:
                sync_to_excel()
                st.success("✅ Contribution saved and Excel file updated!")
            except Exception as e:
                st.success("✅ Contribution saved!")
                st.warning(f"Excel sync skipped: {e}")
            st.cache_data.clear()
            st.rerun()

    st.markdown("---")

    # ── Historical charts ─────────────────────────────────────────────────────
    st.subheader("Contribution History")
    st.plotly_chart(contributions_chart(contrib_df), use_container_width=True)
    st.plotly_chart(cumulative_contributions_chart(contrib_df), use_container_width=True)

    st.subheader("Monthly Contribution Table")
    st.dataframe(
        contrib_df.style.format({
            "Planned ($)": "${:,.0f}",
            "Actual ($)": "${:,.0f}",
            "Difference ($)": "${:+,.0f}",
        }).map(
            lambda v: ("color: #2ECC71" if v == "On Track"
                       else "color: #E74C3C" if v == "Under"
                       else "color: #F5A623"),
            subset=["Status"],
        ),
        use_container_width=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: STOCK ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🔍 Stock Analysis":
    st.title("🔍 Stock / Asset Analysis")

    col1, col2 = st.columns([2, 1])
    with col1:
        symbol = st.text_input("Enter ticker symbol", value="AAPL").upper().strip()
    with col2:
        period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)

    if symbol:
        with st.spinner(f"Loading data for {symbol}…"):
            fig = price_history_chart(symbol, period)
        st.plotly_chart(fig)

        from modules.market_data import get_ticker_info
        info = get_ticker_info(symbol)
        if info:
            st.subheader("Company Info")
            i1, i2, i3, i4 = st.columns(4)
            i1.metric("Sector",     info.get("sector", "N/A"))
            i2.metric("P/E Ratio",  f"{info.get('pe_ratio', 'N/A')}")
            i3.metric("Div Yield",  f"{(info.get('dividend_yield') or 0)*100:.2f}%")
            i4.metric("Beta",       f"{info.get('beta', 'N/A')}")
            i5, i6 = st.columns(2)
            i5.metric("52-Week High", f"${info.get('52w_high', 0):,.2f}")
            i6.metric("52-Week Low",  f"${info.get('52w_low', 0):,.2f}")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: WATCHLIST
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "👀 Watchlist":
    st.title("👀 Watchlist")
    st.caption("Stocks you're watching but haven't bought yet. Prices update on page load.")

    from modules.portfolio import load_portfolio
    from modules.market_data import get_bulk_prices, get_market_movers

    raw = load_portfolio()
    watchlist = raw.get("watchlist", [])

    if not watchlist:
        st.info("No watchlist items yet. Add tickers to data/portfolio.json under 'watchlist'.")
        st.stop()

    symbols = [w["symbol"] for w in watchlist]

    with st.spinner("Fetching live prices…"):
        prices  = get_bulk_prices(symbols)
        movers  = get_market_movers(symbols)

    # Build enriched watchlist table
    rows = []
    for w in watchlist:
        sym   = w["symbol"]
        price = prices.get(sym, 0.0)
        chg_row = movers[movers["Symbol"] == sym]
        daily_chg = float(chg_row["Daily Change %"].iloc[0]) if not chg_row.empty else 0.0
        rows.append({
            "Symbol":       sym,
            "Name":         w.get("name", sym),
            "Type":         w.get("type", "stock").upper(),
            "Price":        price,
            "Daily Change %": daily_chg,
            "Note":         w.get("note", ""),
        })

    wl_df = pd.DataFrame(rows)

    # KPI cards — price tiles
    st.subheader("Live Prices")
    cols = st.columns(len(watchlist))
    for i, row in wl_df.iterrows():
        chg = row["Daily Change %"]
        arrow = "▲" if chg >= 0 else "▼"
        color = "normal" if chg >= 0 else "inverse"
        cols[i].metric(
            label=row["Symbol"],
            value=f"${row['Price']:,.2f}",
            delta=f"{arrow} {abs(chg):.2f}%",
            delta_color=color,
        )

    st.markdown("---")

    # Daily change bar chart
    colors = ["#2ECC71" if v >= 0 else "#E74C3C" for v in wl_df["Daily Change %"]]
    fig = go.Figure(go.Bar(
        x=wl_df["Symbol"],
        y=wl_df["Daily Change %"],
        marker_color=colors,
        text=[f"{v:+.2f}%" for v in wl_df["Daily Change %"]],
        textposition="outside",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.update_layout(
        title="Watchlist — Today's Performance",
        yaxis_title="Daily Change (%)",
        height=380,
        margin=dict(t=50, b=40, l=60, r=20),
    )
    st.plotly_chart(fig)

    st.subheader("Watchlist Details")
    st.dataframe(
        wl_df.style.format({
            "Price": "${:,.2f}",
            "Daily Change %": "{:+.2f}%",
        }).map(
            lambda v: "color: #2ECC71" if isinstance(v, float) and v > 0
                      else ("color: #E74C3C" if isinstance(v, float) and v < 0 else ""),
            subset=["Daily Change %"],
        ),
        use_container_width=True,
        height=320,
    )

    st.markdown("---")
    st.caption("💡 When you're ready to buy any of these, go to ➕ Add Position and enter your shares and price.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: ADD POSITION
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "➕ Add Position":
    st.title("➕ Add New Position")
    st.info("Add a new holding to your portfolio. The data will be saved to portfolio.json.")

    with st.form("add_position_form"):
        col1, col2 = st.columns(2)
        with col1:
            new_symbol = st.text_input("Ticker Symbol (e.g. AAPL, BTC-USD)").upper().strip()
            new_name   = st.text_input("Position Name (e.g. Apple Inc.)")
            new_type   = st.selectbox("Asset Type", ["stock", "etf", "crypto", "reit"])
        with col2:
            new_shares   = st.number_input("Shares / Units", min_value=0.0001, value=1.0, step=0.0001, format="%.4f")
            new_cost     = st.number_input("Average Cost per Share ($)", min_value=0.01, value=100.0, step=0.01)
            new_date     = st.date_input("Purchase Date")

        submitted = st.form_submit_button("Add to Portfolio")
        if submitted and new_symbol:
            add_holding(
                symbol=new_symbol,
                name=new_name or new_symbol,
                asset_type=new_type,
                shares=new_shares,
                avg_cost=new_cost,
                purchase_date=str(new_date),
            )
            log_transaction(new_symbol, "BUY", new_shares, new_cost, new_type)
            # ── Auto-sync to Excel ────────────────────────────────────────────
            try:
                sync_to_excel()
                st.success(f"✅ {new_symbol} added to portfolio and Excel file updated!")
            except Exception as e:
                st.success(f"✅ {new_symbol} added to portfolio!")
                st.warning(f"Excel sync skipped: {e}")
            st.cache_data.clear()
        elif submitted:
            st.error("Please enter a ticker symbol.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: ALPACA TRADING
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🦙 Alpaca Trading":
    st.title("🦙 Alpaca Paper Trading")

    # ── Check if alpaca-py is installed ──────────────────────────────────────
    if not ALPACA_AVAILABLE:
        st.error("📦 alpaca-py is not installed yet.")
        st.code("pip3 install alpaca-py", language="bash")
        st.info("Open a second terminal tab in VS Code and run the command above, then restart the app.")
        st.stop()

    # ── API Key Setup ─────────────────────────────────────────────────────────
    st.subheader("🔑 API Key Setup")
    with st.expander("Enter / Update API Keys", expanded=not is_configured()):
        with st.form("alpaca_keys_form"):
            col1, col2 = st.columns(2)
            saved = load_config()
            with col1:
                key_id  = st.text_input("API Key ID (starts with PK...)",
                                        value=saved.get("api_key", ""),
                                        type="default")
            with col2:
                secret  = st.text_input("Secret Key",
                                        value=saved.get("secret_key", ""),
                                        type="password")
            paper_mode = st.checkbox("Paper Trading Mode (recommended)", value=True)
            save_btn = st.form_submit_button("Save Keys")
            if save_btn:
                if key_id and secret:
                    save_config(key_id.strip(), secret.strip(), paper_mode)
                    st.success("✅ Keys saved! Refreshing…")
                    st.rerun()
                else:
                    st.error("Both Key ID and Secret Key are required.")

    if not is_configured():
        st.warning("👆 Enter your Alpaca API keys above to connect.")
        st.markdown("""
        **How to get your API keys:**
        1. Go to → [app.alpaca.markets/paper/dashboard/overview](https://app.alpaca.markets/paper/dashboard/overview)
        2. Scroll to the **API Keys** section
        3. Click **"+"** or **"Generate New Key"**
        4. Copy both the **Key ID** and **Secret Key** (secret shows only once!)
        5. Paste them in the fields above
        """)
        st.stop()

    # ── Connected — show account summary ─────────────────────────────────────
    st.markdown("---")
    st.subheader("📊 Account Summary")

    with st.spinner("Connecting to Alpaca…"):
        acct = get_account_summary()

    if "error" in acct:
        st.error(f"Connection failed: {acct['error']}")
        st.info("Double-check your API keys in the expander above.")
        st.stop()

    mode_badge = "🟡 PAPER TRADING" if acct.get("paper") else "🔴 LIVE TRADING"
    st.caption(f"Status: **{acct.get('status', '—')}**  |  Mode: **{mode_badge}**")

    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Portfolio Value",  f"${acct.get('portfolio_value', 0):,.2f}")
    a2.metric("Cash Available",   f"${acct.get('cash', 0):,.2f}")
    a3.metric("Buying Power",     f"${acct.get('buying_power', 0):,.2f}")
    day_pnl     = acct.get("day_pnl", 0)
    day_pnl_pct = acct.get("day_pnl_pct", 0)
    a4.metric("Today's P&L",
              f"${day_pnl:+,.2f}",
              delta=f"{day_pnl_pct:+.2f}%",
              delta_color="normal" if day_pnl >= 0 else "inverse")

    st.markdown("---")

    # ── Alpaca Positions ──────────────────────────────────────────────────────
    st.subheader("💼 Alpaca Positions")
    with st.spinner("Loading positions…"):
        positions = get_alpaca_positions()

    if positions and "error" not in positions[0]:
        pos_df = pd.DataFrame(positions)
        st.dataframe(
            pos_df.style.format({
                "avg_entry_price": "${:,.2f}",
                "current_price":   "${:,.2f}",
                "market_value":    "${:,.2f}",
                "unrealized_pl":   "${:+,.2f}",
                "unrealized_plpc": "{:+.2f}%",
            }).map(
                lambda v: "color: #2ECC71" if isinstance(v, float) and v > 0
                          else ("color: #E74C3C" if isinstance(v, float) and v < 0 else ""),
                subset=["unrealized_pl", "unrealized_plpc"],
            ),
            use_container_width=True,
            height=320,
        )
    else:
        st.info("No open positions in your Alpaca paper account yet.")

    st.markdown("---")

    # ── Place a Paper Order ───────────────────────────────────────────────────
    st.subheader("📝 Place Paper Order")
    st.caption("Practice buying/selling without real money.")

    with st.form("paper_order_form"):
        oc1, oc2, oc3 = st.columns(3)
        with oc1:
            order_symbol = st.text_input("Ticker", value="AAPL").upper().strip()
        with oc2:
            order_qty  = st.number_input("Shares", min_value=0.001, value=1.0, step=0.001, format="%.3f")
        with oc3:
            order_side = st.selectbox("Side", ["buy", "sell"])
        place_btn = st.form_submit_button("Place Market Order")
        if place_btn and order_symbol:
            with st.spinner("Placing order…"):
                result = place_market_order(order_symbol, order_qty, order_side)
            if result.get("success"):
                st.success(f"✅ Order placed! {order_side.upper()} {order_qty} {order_symbol} — Order ID: {result['order_id']}")
            else:
                st.error(f"Order failed: {result.get('error', 'Unknown error')}")

    st.markdown("---")

    # ── Recent Orders ─────────────────────────────────────────────────────────
    st.subheader("📋 Recent Orders")
    with st.spinner("Loading order history…"):
        orders = get_recent_orders(limit=15)

    if orders and "error" not in orders[0]:
        ord_df = pd.DataFrame(orders)
        st.dataframe(
            ord_df[["submitted_at", "symbol", "side", "filled_qty", "filled_price", "total", "status"]].style.format({
                "filled_price": "${:,.2f}",
                "total":        "${:,.2f}",
            }),
            use_container_width=True,
            height=320,
        )
    else:
        st.info("No recent orders found.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: OPTIONS CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "⚙️ Options Calculator":
    from modules.options_calc import (
        black_scholes, option_pnl, pnl_at_expiry_curve,
        pnl_today_curve, GREEKS_EXPLAINED, days_to_expiry, years_to_expiry,
    )
    from modules.market_data import get_bulk_prices
    import plotly.graph_objects as go
    from datetime import date, timedelta

    st.title("⚙️ Options P&L Calculator")
    st.caption("Powered by Black-Scholes — the same model used by professional traders.")

    st.markdown("---")

    # ── Input panel ───────────────────────────────────────────────────────────
    st.subheader("📋 Option Details")
    col1, col2, col3 = st.columns(3)

    with col1:
        opt_symbol    = st.text_input("Stock Ticker", value="AAPL").upper().strip()
        opt_type      = st.selectbox("Option Type", ["call", "put"])
        opt_contracts = st.number_input("# of Contracts", min_value=1, value=1, step=1)

    with col2:
        opt_strike    = st.number_input("Strike Price ($)", min_value=1.0, value=270.0, step=0.50)
        opt_expiry    = st.date_input("Expiration Date",
                                      value=date.today() + timedelta(days=30),
                                      min_value=date.today())
        opt_premium   = st.number_input("Premium Paid per Share ($)",
                                        min_value=0.01, value=5.00, step=0.01,
                                        help="What you paid for the option (per share). Each contract = 100 shares.")

    with col3:
        # Try to fetch live stock price
        live_prices = get_bulk_prices([opt_symbol])
        live_price  = live_prices.get(opt_symbol, 0.0)
        opt_stock_price = st.number_input(
            "Current Stock Price ($)",
            min_value=0.01,
            value=float(live_price) if live_price > 0 else opt_strike,
            step=0.01,
            help="Auto-filled from live market data. You can adjust manually.",
        )
        opt_vol = st.slider("Implied Volatility (%)", min_value=5, max_value=200,
                            value=35, step=1,
                            help="Expected annualized volatility. 30-50% is typical for individual stocks.")
        opt_rate = st.slider("Risk-Free Rate (%)", min_value=0, max_value=10,
                             value=5, step=1,
                             help="Approximate US Treasury rate.")

    # Convert inputs
    T     = years_to_expiry(opt_expiry)
    DTE   = days_to_expiry(opt_expiry)
    sigma = opt_vol / 100.0
    r     = opt_rate / 100.0

    st.markdown("---")

    # ── Calculate ─────────────────────────────────────────────────────────────
    result = option_pnl(
        S=opt_stock_price, K=opt_strike, T=T, r=r,
        sigma=sigma, option_type=opt_type,
        premium_paid=opt_premium, contracts=opt_contracts,
    )

    # ── KPI metrics ───────────────────────────────────────────────────────────
    st.subheader("📊 Results")

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Option Price Now",   f"${result['current_price']:.4f}")
    k2.metric("You Paid",           f"${result['premium_paid']:.4f}")
    pnl_d = result['pnl_dollar']
    pnl_p = result['pnl_pct']
    k3.metric("P&L ($)",
              f"${pnl_d:+,.2f}",
              delta=f"{pnl_p:+.1f}%",
              delta_color="normal" if pnl_d >= 0 else "inverse")
    k4.metric("Total Cost Basis",   f"${result['cost_basis']:,.2f}")
    k5.metric("Break-Even at Expiry", f"${result['breakeven']:.2f}")

    st.markdown("")
    k6, k7 = st.columns(2)
    k6.metric("Days to Expiry (DTE)", f"{DTE} days")
    k7.metric("Intrinsic / Time Value",
              f"${result['intrinsic']:.4f} / ${result['time_value']:.4f}")

    st.markdown("---")

    # ── Greeks dashboard ──────────────────────────────────────────────────────
    st.subheader("🔢 The Greeks")
    st.caption("These numbers tell you HOW your option will behave as the market moves.")

    g1, g2, g3, g4, g5 = st.columns(5)
    greeks_ui = [
        (g1, "Δ Delta",  result["delta"],  "normal"),
        (g2, "Γ Gamma",  result["gamma"],  "normal"),
        (g3, "Θ Theta",  result["theta"],  "inverse"),
        (g4, "V Vega",   result["vega"],   "normal"),
        (g5, "ρ Rho",    result["rho"],    "normal"),
    ]
    for col, label, val, dc in greeks_ui:
        col.metric(label, f"{val:+.4f}")

    # Plain-English explanations
    with st.expander("📖 What do the Greeks mean? (Plain English)"):
        for key, info in GREEKS_EXPLAINED.items():
            val = result[key]
            st.markdown(f"**{info['symbol']} {info['name']}:  `{val:+.4f}`**")
            st.write(info["plain_english"])
            st.markdown("---")

    st.markdown("---")

    # ── P&L Charts ────────────────────────────────────────────────────────────
    st.subheader("📈 P&L Diagrams")

    tab1, tab2 = st.tabs(["At Expiry (Hockey Stick)", "Today (with Time Value)"])

    expiry_data = pnl_at_expiry_curve(
        opt_stock_price, opt_strike, opt_premium, opt_type, opt_contracts)
    today_data  = pnl_today_curve(
        opt_stock_price, opt_strike, T, r, sigma, opt_type, opt_premium, opt_contracts)

    with tab1:
        colors_exp = ["#2ECC71" if p >= 0 else "#E74C3C" for p in expiry_data["pnls"]]
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(
            x=expiry_data["prices"], y=expiry_data["pnls"],
            mode="lines", name="P&L at Expiry",
            line=dict(color="#F5A623", width=3),
            fill="tozeroy",
            fillcolor="rgba(245,166,35,0.15)",
        ))
        fig1.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
        fig1.add_vline(x=opt_stock_price, line_dash="dot", line_color="#3498DB",
                       annotation_text=f"Current: ${opt_stock_price:.2f}",
                       annotation_position="top right")
        fig1.add_vline(x=result["breakeven"], line_dash="dot", line_color="#2ECC71",
                       annotation_text=f"Break-even: ${result['breakeven']:.2f}",
                       annotation_position="top left")
        fig1.update_layout(
            title=f"{opt_symbol} {opt_type.upper()} ${opt_strike} — P&L at Expiry",
            xaxis_title="Stock Price at Expiry ($)",
            yaxis_title="Profit / Loss ($)",
            height=420,
            plot_bgcolor="#0e1117",
            paper_bgcolor="#0e1117",
            font=dict(color="white"),
        )
        st.plotly_chart(fig1)
        st.caption("The hockey-stick shape is classic options P&L — limited loss on the left, unlimited gain potential on the right (for calls).")

    with tab2:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=today_data["prices"], y=today_data["pnls"],
            mode="lines", name="P&L Today",
            line=dict(color="#9B59B6", width=3),
            fill="tozeroy",
            fillcolor="rgba(155,89,182,0.15)",
        ))
        fig2.add_trace(go.Scatter(
            x=expiry_data["prices"], y=expiry_data["pnls"],
            mode="lines", name="P&L at Expiry",
            line=dict(color="#F5A623", width=2, dash="dash"),
        ))
        fig2.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
        fig2.add_vline(x=opt_stock_price, line_dash="dot", line_color="#3498DB",
                       annotation_text=f"Current: ${opt_stock_price:.2f}",
                       annotation_position="top right")
        fig2.update_layout(
            title=f"{opt_symbol} — P&L Today vs At Expiry",
            xaxis_title="Stock Price ($)",
            yaxis_title="Profit / Loss ($)",
            height=420,
            plot_bgcolor="#0e1117",
            paper_bgcolor="#0e1117",
            font=dict(color="white"),
            legend=dict(x=0.02, y=0.98),
        )
        st.plotly_chart(fig2)
        st.caption("Purple = what your option is worth TODAY at different stock prices. Orange dashed = what it's worth AT expiry. The gap between the curves is time value — it shrinks every day (Theta decay).")

    st.markdown("---")

    # ── Scenario analysis ─────────────────────────────────────────────────────
    st.subheader("🎯 Scenario Analysis")
    st.caption("See how your P&L changes if the stock moves up or down.")

    scenarios = [-20, -15, -10, -5, 0, +5, +10, +15, +20]
    rows = []
    for pct in scenarios:
        new_S   = opt_stock_price * (1 + pct / 100)
        bs_new  = black_scholes(new_S, opt_strike, T, r, sigma, opt_type)
        new_pnl = (bs_new["price"] - opt_premium) * opt_contracts * 100
        rows.append({
            "Stock Move":   f"{pct:+d}%",
            "Stock Price":  round(new_S, 2),
            "Option Price": round(bs_new["price"], 4),
            "P&L ($)":      round(new_pnl, 2),
            "Delta":        round(bs_new["delta"], 4),
        })

    scen_df = pd.DataFrame(rows)
    st.dataframe(
        scen_df.style.format({
            "Stock Price":  "${:,.2f}",
            "Option Price": "${:.4f}",
            "P&L ($)":      "${:+,.2f}",
        }).map(
            lambda v: "color: #2ECC71" if isinstance(v, float) and v > 0
                      else ("color: #E74C3C" if isinstance(v, float) and v < 0 else ""),
            subset=["P&L ($)"],
        ),
        use_container_width=True,
        height=380,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: ROBINHOOD SYNC
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🔴 Robinhood Sync":
    from modules.robinhood_sync import (
        ROBIN_AVAILABLE, ROBIN_ERROR, login, logout, is_logged_in,
        fetch_robinhood_positions, fetch_robinhood_crypto,
        sync_positions_to_portfolio, get_account_summary,
        fetch_robinhood_recent_orders,
    )

    st.title("🔴 Robinhood Auto-Sync")
    st.caption("Import your real Robinhood positions directly into your tracker.")

    if not ROBIN_AVAILABLE:
        st.error("📦 robin_stocks is not installed yet.")
        if ROBIN_ERROR:
            st.code(f"Error detail: {ROBIN_ERROR}", language="text")
        import sys
        st.code(f"Python: {sys.executable}", language="text")
        st.code("pip3 install robin_stocks", language="bash")
        st.info("Open a terminal tab and run the command above, then restart the app.")
        st.stop()

    st.markdown("---")

    # ── Login form ────────────────────────────────────────────────────────────
    logged_in = is_logged_in()

    if not logged_in:
        st.subheader("🔑 Login to Robinhood")
        st.warning("Your credentials are stored **only on your Mac** — never sent to any server.")
        with st.form("rh_login_form"):
            rh_user  = st.text_input("Robinhood Email")
            rh_pass  = st.text_input("Robinhood Password", type="password")
            rh_mfa   = st.text_input("MFA Code (if required — leave blank if not)", value="")
            login_btn = st.form_submit_button("Connect to Robinhood")
            if login_btn:
                with st.spinner("Connecting…"):
                    result = login(rh_user.strip(), rh_pass.strip(), rh_mfa.strip())
                if result.get("success"):
                    st.success("✅ Connected! Refreshing…")
                    st.rerun()
                elif result.get("error") == "MFA_REQUIRED":
                    st.warning("🔐 MFA required — enter the 6-digit code from your authenticator app above and try again.")
                else:
                    st.error(f"Login failed: {result.get('error')}")
        st.stop()

    # ── Connected ─────────────────────────────────────────────────────────────
    st.success("✅ Connected to Robinhood")

    col_logout, _ = st.columns([1, 4])
    if col_logout.button("Logout"):
        logout()
        st.rerun()

    st.markdown("---")

    # ── Account summary ───────────────────────────────────────────────────────
    st.subheader("📊 Robinhood Account")
    with st.spinner("Loading account…"):
        acct = get_account_summary()

    if "error" not in acct:
        a1, a2, a3 = st.columns(3)
        a1.metric("Portfolio Value", f"${acct.get('equity', 0):,.2f}")
        a2.metric("Cash",            f"${acct.get('cash', 0):,.2f}")
        a3.metric("Buying Power",    f"${acct.get('buying_power', 0):,.2f}")

    st.markdown("---")

    # ── Live positions preview ────────────────────────────────────────────────
    st.subheader("💼 Your Robinhood Positions")
    with st.spinner("Fetching positions…"):
        stock_pos  = fetch_robinhood_positions()
        crypto_pos = fetch_robinhood_crypto()
        all_pos    = [p for p in stock_pos + crypto_pos if "error" not in p]

    if all_pos:
        pos_df = pd.DataFrame(all_pos)
        st.dataframe(
            pos_df[["symbol", "name", "type", "shares", "avg_cost"]].style.format({
                "shares":   "{:.6f}",
                "avg_cost": "${:,.2f}",
            }),
            use_container_width=True,
            height=min(60 + len(all_pos) * 40, 400),
        )

        st.markdown("---")
        st.subheader("⬇️ Import into Your Tracker")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ Add New Positions Only", use_container_width=True,
                         help="Only imports symbols you don't already have in your tracker"):
                result = sync_positions_to_portfolio(overwrite=False)
                if "error" in result:
                    st.error(f"Import failed: {result['error']}")
                else:
                    added   = result.get("added", [])
                    skipped = result.get("skipped", [])
                    if added:
                        st.success(f"✅ Added: {', '.join(added)}")
                    if skipped:
                        st.info(f"Already in tracker (skipped): {', '.join(skipped)}")
                    if not added and not skipped:
                        st.info("Nothing to add.")
                    try:
                        sync_to_excel()
                    except Exception:
                        pass
                    st.cache_data.clear()

        with col2:
            st.warning("⚠️ Full Overwrite replaces ALL your current holdings with Robinhood data.")
            if st.button("🔄 Full Overwrite (Replace All)", use_container_width=True,
                         help="Replaces your entire portfolio with what Robinhood shows"):
                result = sync_positions_to_portfolio(overwrite=True)
                if "error" in result:
                    st.error(f"Import failed: {result['error']}")
                else:
                    st.success(f"✅ Portfolio replaced with {len(result.get('added', []))} positions from Robinhood!")
                    try:
                        sync_to_excel()
                    except Exception:
                        pass
                    st.cache_data.clear()
    else:
        st.info("No open positions found in your Robinhood account.")

    st.markdown("---")

    # ── Recent orders ─────────────────────────────────────────────────────────
    st.subheader("📋 Recent Robinhood Orders")
    with st.spinner("Loading order history…"):
        orders = fetch_robinhood_recent_orders(limit=15)

    if orders:
        ord_df = pd.DataFrame(orders)
        st.dataframe(
            ord_df[["date", "symbol", "type", "shares", "price", "total"]].style.format({
                "shares": "{:.6f}",
                "price":  "${:,.2f}",
                "total":  "${:,.2f}",
            }),
            use_container_width=True,
            height=380,
        )
    else:
        st.info("No recent orders found.")

    st.markdown("---")
    st.caption("💡 Tip: Run a sync every time you make a new purchase on Robinhood to keep your tracker up to date.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: PRICE ALERTS  (with Stop-Loss & Take-Profit)
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🔔 Price Alerts":
    from modules.price_alerts import (
        load_alerts, add_alert, delete_alert, delete_alert_by_index,
        toggle_alert, toggle_alert_by_index, check_alerts, get_alert_summary,
    )
    from modules.market_data import get_bulk_prices

    st.title("🔔 Price Alerts — Stop-Loss & Take-Profit")
    st.caption("Protect your positions and lock in gains automatically.")

    # ── Fetch live prices ─────────────────────────────────────────────────────
    alerts = load_alerts()
    symbols = list({a["symbol"] for a in alerts})
    if symbols:
        with st.spinner("Checking live prices…"):
            prices = get_bulk_prices(symbols)
    else:
        prices = {}

    summary   = get_alert_summary(prices)
    triggered = summary["triggered"]

    # ── Triggered alerts banner ───────────────────────────────────────────────
    if triggered:
        sl_triggered = [t for t in triggered if t.get("alert_type") == "stop_loss"]
        tp_triggered = [t for t in triggered if t.get("alert_type") == "take_profit"]
        pa_triggered = [t for t in triggered if t.get("alert_type", "price_alert") == "price_alert"]

        if sl_triggered:
            for t in sl_triggered:
                pnl_txt = f"  |  Loss: ${t.get('total_pnl', 0):+,.2f}" if t.get("total_pnl") else ""
                st.error(
                    f"🛑 **STOP-LOSS HIT — {t['symbol']}** is at **${t['current_price']:,.2f}** "
                    f"(below your stop of ${t['target_price']:,.2f}){pnl_txt}  ➡️ **SELL NOW to limit your loss**"
                )
        if tp_triggered:
            for t in tp_triggered:
                pnl_txt = f"  |  Profit: ${t.get('total_pnl', 0):+,.2f}" if t.get("total_pnl") else ""
                st.success(
                    f"🎯 **TAKE-PROFIT HIT — {t['symbol']}** is at **${t['current_price']:,.2f}** "
                    f"(above your target of ${t['target_price']:,.2f}){pnl_txt}  ➡️ **SELL to lock in gains**"
                )
        if pa_triggered:
            for t in pa_triggered:
                arrow = "📈" if t["condition"] == "above" else "📉"
                st.warning(
                    f"{arrow} **{t['symbol']}** is at **${t['current_price']:,.2f}** — "
                    f"target: {t['condition']} ${t['target_price']:,.2f}  |  {t.get('note','')}"
                )
        st.markdown("---")
    else:
        k1, k2, k3 = st.columns(3)
        k1.metric("Active Alerts", summary["active"])
        k2.metric("Stop-Losses", len(summary["by_type"]["stop_loss"]))
        k3.metric("Take-Profits", len(summary["by_type"]["take_profit"]))
        st.success("✅ All clear — no alerts triggered right now.")

    st.markdown("---")

    # ── Tabs: Add Stop-Loss | Add Take-Profit | Add Price Alert ───────────────
    tab_sl, tab_tp, tab_pa = st.tabs(["🛑 Add Stop-Loss", "🎯 Add Take-Profit", "🔔 Add Price Alert"])

    with tab_sl:
        st.markdown("**Stop-Loss** — Sell automatically if the stock drops to this price. Limits your loss.")
        with st.form("add_sl_form", clear_on_submit=True):
            s1, s2, s3 = st.columns(3)
            sl_sym   = s1.text_input("Ticker", placeholder="AAPL").upper().strip()
            sl_entry = s2.number_input("Entry Price (what you paid)", min_value=0.01, value=150.0, step=0.5)
            sl_stop  = s3.number_input("Stop-Loss Price", min_value=0.01, value=139.5, step=0.5,
                                       help="7–10% below entry is the rule")
            s4, s5 = st.columns(2)
            sl_shares = s4.number_input("Shares You Hold", min_value=0.001, value=10.0, step=1.0)
            sl_note   = s5.text_input("Note", placeholder="e.g. Swing trade hedge")
            if sl_entry > 0 and sl_stop > 0:
                risk_pct = (sl_entry - sl_stop) / sl_entry * 100
                st.caption(f"📉 This stop is **{risk_pct:.1f}% below** your entry. Max loss per share: **${sl_entry - sl_stop:.2f}**")
            sl_submit = st.form_submit_button("🛑 Set Stop-Loss", type="primary")
        if sl_submit and sl_sym:
            add_alert(sl_sym, sl_sym, "below", sl_stop,
                      note=sl_note, alert_type="stop_loss",
                      entry_price=sl_entry, shares=sl_shares)
            st.success(f"🛑 Stop-Loss set: Sell **{sl_sym}** if it drops below **${sl_stop:.2f}**")
            st.rerun()

    with tab_tp:
        st.markdown("**Take-Profit** — Sell automatically when the stock hits your target. Locks in your gains.")
        with st.form("add_tp_form", clear_on_submit=True):
            t1, t2, t3 = st.columns(3)
            tp_sym    = t1.text_input("Ticker", placeholder="AAPL").upper().strip()
            tp_entry  = t2.number_input("Entry Price (what you paid)", min_value=0.01, value=150.0, step=0.5)
            tp_target = t3.number_input("Take-Profit Price", min_value=0.01, value=172.5, step=0.5,
                                        help="At least 2× your stop distance above entry")
            t4, t5 = st.columns(2)
            tp_shares = t4.number_input("Shares You Hold", min_value=0.001, value=10.0, step=1.0)
            tp_note   = t5.text_input("Note", placeholder="e.g. 2:1 target")
            if tp_entry > 0 and tp_target > 0:
                gain_pct = (tp_target - tp_entry) / tp_entry * 100
                profit   = (tp_target - tp_entry) * tp_shares
                st.caption(f"📈 This target is **{gain_pct:.1f}% above** your entry. Potential profit: **${profit:,.2f}**")
            tp_submit = st.form_submit_button("🎯 Set Take-Profit", type="primary")
        if tp_submit and tp_sym:
            add_alert(tp_sym, tp_sym, "above", tp_target,
                      note=tp_note, alert_type="take_profit",
                      entry_price=tp_entry, shares=tp_shares)
            st.success(f"🎯 Take-Profit set: Sell **{tp_sym}** when it hits **${tp_target:.2f}**")
            st.rerun()

    with tab_pa:
        st.markdown("**Price Alert** — Get notified when a stock crosses any price level.")
        with st.form("add_alert_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            alert_symbol = c1.text_input("Ticker Symbol", placeholder="OKLO").upper().strip()
            alert_name   = c1.text_input("Name (optional)", value="")
            alert_cond   = c2.selectbox("Alert me when price is…", ["below", "above"])
            alert_price  = c2.number_input("Target Price ($)", min_value=0.01, value=60.00, step=0.50)
            alert_note   = c3.text_input("Note (optional)", placeholder="e.g. Buy the dip")
            add_btn = st.form_submit_button("🔔 Add Alert", use_container_width=True)
        if add_btn and alert_symbol:
            add_alert(alert_symbol, alert_name or alert_symbol, alert_cond, alert_price, alert_note)
            st.success(f"✅ Alert added: {alert_symbol} {alert_cond} ${alert_price:.2f}")
            st.rerun()

    st.markdown("---")

    # ── All Alerts Table ──────────────────────────────────────────────────────
    st.subheader("📋 Your Active Alerts")

    if not alerts:
        st.info("No alerts yet. Use the tabs above to add your first stop-loss or take-profit.")
    else:
        # Group by type
        type_groups = [
            ("🛑 Stop-Loss Alerts", "stop_loss",   "#E74C3C"),
            ("🎯 Take-Profit Alerts","take_profit", "#2ECC71"),
            ("🔔 Price Alerts",      "price_alert", "#2980B9"),
        ]
        for group_label, atype, gcolor in type_groups:
            group_alerts = [(i, a) for i, a in enumerate(alerts)
                            if a.get("alert_type", "price_alert") == atype]
            if not group_alerts:
                continue

            st.markdown(f"#### {group_label}")
            for i, a in group_alerts:
                sym    = a["symbol"]
                price  = prices.get(sym)
                cond   = a["condition"]
                target = a["target_price"]
                active = a.get("active", True)
                atype_ = a.get("alert_type", "price_alert")

                is_triggered = False
                if price:
                    is_triggered = (cond == "above" and price >= target) or \
                                   (cond == "below" and price <= target)

                if not active:
                    status_icon = "⏸️"
                elif is_triggered:
                    status_icon = "🚨"
                elif atype_ == "stop_loss":
                    status_icon = "🛑"
                elif atype_ == "take_profit":
                    status_icon = "🎯"
                else:
                    status_icon = "👁️"

                col1, col2, col3, col4, col5, col6 = st.columns([1.5, 1, 1.2, 1.4, 2, 1.2])
                col1.markdown(f"**{status_icon} {sym}**")
                col2.markdown(f"`{cond.upper()}`")
                col3.markdown(f"**${target:,.2f}**")

                if price:
                    diff = price - target
                    pct  = (diff / target) * 100
                    col4.metric("Now", f"${price:,.2f}", delta=f"{pct:+.1f}%",
                                delta_color="normal")
                else:
                    col4.markdown("—")

                # Show P&L potential if entry price is set
                entry  = a.get("entry_price", 0)
                shares = a.get("shares", 0)
                if entry > 0 and price:
                    pnl = (price - entry) * shares
                    col5.markdown(f"Current P&L: **{'+'if pnl>=0 else ''}${pnl:,.2f}**  _{a.get('note','')}_")
                else:
                    col5.markdown(f"_{a.get('note', '')}_")

                btn1, btn2 = col6.columns(2)
                if btn1.button("⏸" if active else "▶", key=f"toggle_{i}"):
                    toggle_alert_by_index(i)
                    st.rerun()
                if btn2.button("🗑", key=f"del_{i}"):
                    delete_alert_by_index(i)
                    st.rerun()

                st.divider()

    st.markdown("---")

    # ── Quick-add from watchlist ──────────────────────────────────────────────
    st.subheader("⚡ Quick-Add from Your Watchlist")
    st.caption("Click any stock below to pre-fill the alert form.")

    from modules.portfolio import load_portfolio
    raw       = load_portfolio()
    watchlist = raw.get("watchlist", [])
    wl_symbols = [w["symbol"] for w in watchlist]

    if wl_symbols:
        wl_prices = get_bulk_prices(wl_symbols)
        cols = st.columns(len(watchlist))
        for i, w in enumerate(watchlist):
            sym   = w["symbol"]
            price = wl_prices.get(sym, 0)
            cols[i].metric(sym, f"${price:,.2f}")
        st.caption("Go to the Add New Alert form above and type the symbol to set your target.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: CONTRIBUTION REMINDER
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "💰 Contribution Reminder":
    from modules.contribution_reminder import (
        get_contribution_status, get_weekly_breakdown, get_yearly_projection,
    )

    st.title("💰 Contribution Reminder")
    st.caption("Stay on track with your monthly investment goal.")

    status = get_contribution_status()
    urgency = status["urgency"]

    # ── Main status banner ────────────────────────────────────────────────────
    if urgency == "complete":
        st.success(status["message"])
    elif urgency == "on_track":
        st.success(status["message"])
    elif urgency == "warning":
        st.warning(status["message"])
    elif urgency == "critical":
        st.error(status["message"])
    else:
        st.info(status["message"])

    st.markdown("---")

    # ── KPI metrics ───────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Invested This Month",  f"${status['actual']:,.2f}")
    k2.metric("Monthly Goal",         f"${status['planned']:,.2f}")
    k3.metric("Still Needed",         f"${status['remaining_to_target']:,.2f}")
    k4.metric("Days Left",            f"{status['days_left']} days")

    st.markdown("")

    # ── Progress bars ─────────────────────────────────────────────────────────
    st.subheader("📊 Progress This Month")

    # Month progress bar
    month_pct = min(status["pct_through_month"] / 100, 1.0)
    st.caption(f"📅 You are **{status['pct_through_month']:.0f}%** through {status['month']}")
    st.progress(month_pct)

    # Investment progress bar
    invest_pct = min(status["pct_complete"] / 100, 1.0)
    st.caption(f"💵 You have invested **{status['pct_complete']:.1f}%** of your ${status['planned']:,.0f} goal")
    st.progress(invest_pct)

    # Ahead/behind indicator
    ab = status["ahead_behind"]
    if ab >= 0:
        st.success(f"📈 You are **${ab:,.2f} ahead** of the expected pace for this point in the month.")
    else:
        st.warning(f"📉 You are **${abs(ab):,.2f} behind** the expected pace. Consider investing soon to catch up.")

    st.markdown("---")

    # ── Weekly breakdown ──────────────────────────────────────────────────────
    st.subheader("📆 Weekly Investment Targets")
    weeks = get_weekly_breakdown(status["planned"])

    w_cols = st.columns(4)
    for i, week in enumerate(weeks):
        label  = "🟢 Current Week" if week["is_current"] else ("✅ Past" if week["is_past"] else "⏳ Upcoming")
        w_cols[i].metric(
            label=week["label"],
            value=f"${week['target']:,.0f}",
            delta=label,
            delta_color="normal" if week["is_current"] else "off",
        )

    st.markdown("---")

    # ── Yearly projection ─────────────────────────────────────────────────────
    st.subheader("📈 Full-Year Projection")
    proj = get_yearly_projection(status["actual"], status["planned"])

    p1, p2, p3 = st.columns(3)
    p1.metric("Projected Year Total",  f"${proj['projected_year']:,.0f}")
    p2.metric("Minimum Year Target",   f"${proj['minimum_year']:,.0f}")
    p3.metric("Goal Year Target",      f"${proj['target_year']:,.0f}")

    gap = proj["projected_year"] - proj["target_year"]
    if gap >= 0:
        st.success(f"✅ You're on pace to **exceed** your yearly goal by ${gap:,.0f}!")
    else:
        st.warning(f"⚠️ At current pace, you'll be **${abs(gap):,.0f} short** of your yearly goal. "
                   f"Increase contributions by ~${abs(gap) / max(proj['months_left'], 1):,.0f}/month to close the gap.")

    st.markdown("---")

    # ── Quick action ──────────────────────────────────────────────────────────
    st.subheader("⚡ Quick Actions")
    st.markdown(f"""
    - 📱 **Open Robinhood** and invest **${status['remaining_to_minimum']:,.0f}** to hit the minimum
    - 🎯 Invest **${status['remaining_to_target']:,.0f}** more to fully hit your **${status['planned']:,.0f}** goal
    - 📊 Go to **📅 Monthly Tracker** to log your contribution once done
    - 🔔 Check **🔔 Price Alerts** for any good entry points on your watchlist
    """)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: OPTIONS POSITIONS
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Options Positions":
    from modules.options_tracker import (
        load_options_positions, add_options_position,
        close_options_position, delete_options_position,
        enrich_options_positions, get_options_summary,
    )
    from modules.market_data import get_bulk_prices
    from datetime import date

    st.title("📋 Options Position Tracker")
    st.caption("Track real options contracts with live Black-Scholes P&L and Greeks.")

    # ── Load & enrich positions ───────────────────────────────────────────────
    raw_positions = load_options_positions()
    open_positions = [p for p in raw_positions if p.get("status") == "open"]

    # Get unique symbols for price fetch
    symbols = list({p["symbol"] for p in open_positions})
    live_prices = {}
    if symbols:
        with st.spinner("Fetching live prices…"):
            live_prices = get_bulk_prices(symbols)

    enriched = enrich_options_positions(live_prices)
    open_enriched = [p for p in enriched if p.get("status") == "open"]
    summary = get_options_summary(enriched)

    # ── Portfolio Summary KPIs ────────────────────────────────────────────────
    if open_enriched:
        st.subheader("📊 Options Portfolio Summary")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Open Positions",    summary["total_positions"])
        k2.metric("Total Invested",    f"${summary['total_cost']:,.2f}")
        k3.metric("Current Value",     f"${summary['total_worth']:,.2f}")
        pnl_sign = "+" if summary["total_pnl"] >= 0 else ""
        k4.metric("Total P&L",
                  f"{pnl_sign}${summary['total_pnl']:,.2f}",
                  delta=f"{pnl_sign}{summary['pnl_pct']:.2f}%")

        st.markdown("---")

        # ── Position Cards ────────────────────────────────────────────────────
        st.subheader("📄 Open Positions")

        for p in open_enriched:
            sym   = p["symbol"]
            otype = p["option_type"].upper()
            K     = p["strike"]
            exp   = p["expiry"]
            dte   = p["days_to_expiry"]
            pnl   = p["pnl_dollar"]
            pnl_p = p["pnl_pct"]
            itm   = p.get("itm", False)

            pnl_color  = "🟢" if pnl >= 0 else "🔴"
            itm_badge  = "🎯 ITM" if itm else "📤 OTM"
            dte_badge  = f"⏳ {dte}d left" if dte > 0 else "⚠️ EXPIRED"

            with st.expander(
                f"{pnl_color} **{sym}** — {otype} ${K} exp {exp}  |  "
                f"P&L: {'+'if pnl>=0 else ''}{pnl:.2f} ({pnl_p:+.1f}%)  |  "
                f"{itm_badge}  {dte_badge}",
                expanded=True,
            ):
                col_a, col_b, col_c = st.columns(3)

                with col_a:
                    st.markdown("**📈 Position Details**")
                    st.metric("Stock Price",    f"${p['current_stock_price']:,.2f}")
                    st.metric("Strike",         f"${K:,.2f}")
                    st.metric("Contracts",      p["contracts"])
                    st.metric("Premium Paid",   f"${p['premium_paid']:,.4f}")
                    st.metric("Cost Basis",     f"${p['cost_basis']:,.2f}")

                with col_b:
                    st.markdown("**💰 P&L Breakdown**")
                    st.metric("BS Price (live)", f"${p['bs_price']:,.4f}")
                    st.metric("Current Worth",   f"${p['current_worth']:,.2f}")
                    pnl_delta = f"{'+' if pnl >= 0 else ''}{pnl:.2f}"
                    st.metric("P&L ($)",         pnl_delta,
                              delta=f"{pnl_p:+.2f}%")
                    st.metric("Intrinsic Value", f"${p['intrinsic']:,.4f}")
                    st.metric("Time Value",      f"${p['time_value']:,.4f}")

                with col_c:
                    st.markdown("**🔢 Greeks**")
                    st.metric("Delta  (Δ)", f"{p['delta']:+.4f}",
                              help="Price change per $1 move in stock")
                    st.metric("Gamma  (Γ)", f"{p['gamma']:.6f}",
                              help="Rate of change in Delta")
                    st.metric("Theta  (Θ)", f"{p['theta']:+.4f}",
                              help="Daily time decay ($ per day)")
                    st.metric("Vega   (ν)", f"{p['vega']:+.4f}",
                              help="Price change per 1% IV move")
                    st.metric("Rho    (ρ)", f"{p['rho']:+.4f}",
                              help="Price change per 1% rate move")

                if p.get("note"):
                    st.info(f"📝 Note: {p['note']}")

                # Action buttons
                btn1, btn2, _ = st.columns([1, 1, 4])
                if btn1.button("✅ Close Position", key=f"close_{p['id']}"):
                    close_options_position(p["id"])
                    st.success("Position closed.")
                    st.rerun()
                if btn2.button("🗑 Delete", key=f"del_{p['id']}"):
                    delete_options_position(p["id"])
                    st.rerun()

        st.markdown("---")
    else:
        st.info("No open options positions yet. Add your first position below! 👇")
        st.markdown("---")

    # ── Add New Position Form ─────────────────────────────────────────────────
    st.subheader("➕ Add New Options Position")
    st.caption("Enter the details of an options contract you hold or want to track.")

    with st.form("add_options_form", clear_on_submit=True):
        f1, f2, f3 = st.columns(3)
        sym_in    = f1.text_input("Ticker Symbol", placeholder="AAPL").upper()
        otype_in  = f2.selectbox("Option Type", ["call", "put"])
        contracts_in = f3.number_input("Contracts", min_value=1, value=1, step=1)

        g1, g2, g3 = st.columns(3)
        strike_in  = g1.number_input("Strike Price ($)", min_value=0.01, value=150.0, step=0.5)
        expiry_in  = g2.date_input("Expiration Date", value=date.today())
        premium_in = g3.number_input("Premium Paid (per share)", min_value=0.001,
                                      value=3.50, step=0.01,
                                      help="E.g. 3.50 means you paid $350 per contract")

        h1, h2 = st.columns([1, 2])
        iv_in   = h1.number_input("Implied Volatility (%)", min_value=1.0, value=30.0,
                                   step=1.0,
                                   help="Enter as a percentage, e.g. 30 for 30% IV")
        note_in = h2.text_input("Note (optional)", placeholder="Earnings play, hedge, etc.")

        submitted = st.form_submit_button("Add Position", type="primary")

    if submitted:
        if not sym_in:
            st.error("Please enter a ticker symbol.")
        else:
            pos = add_options_position(
                symbol=sym_in,
                option_type=otype_in,
                strike=strike_in,
                expiry=str(expiry_in),
                contracts=contracts_in,
                premium_paid=premium_in,
                implied_vol=iv_in / 100.0,
                note=note_in,
            )
            st.success(
                f"✅ Added {contracts_in}x {sym_in} ${strike_in} {otype_in.upper()} "
                f"exp {expiry_in} @ ${premium_in:.2f}/share "
                f"(cost basis: ${premium_in * contracts_in * 100:,.2f})"
            )
            st.rerun()

    # ── Closed positions ──────────────────────────────────────────────────────
    closed = [p for p in raw_positions if p.get("status") == "closed"]
    if closed:
        st.markdown("---")
        with st.expander(f"📁 Closed Positions ({len(closed)})", expanded=False):
            for p in closed:
                st.markdown(
                    f"**{p['symbol']}** {p['option_type'].upper()} ${p['strike']} "
                    f"exp {p['expiry']} — Opened {p['opened']} | Closed {p.get('closed', '?')}"
                )


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: PORTFOLIO HISTORY (90-DAY CHART)
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📉 Portfolio History":
    import plotly.graph_objects as go
    from modules.portfolio import get_enriched_portfolio, load_portfolio
    from modules.history_tracker import (
        take_snapshot, load_history, get_history_range,
        get_performance_summary, portfolio_value_chart, pnl_history_chart,
    )
    import yfinance as yf

    st.title("📉 Portfolio History & Performance")
    st.caption("Track your real portfolio value day by day. Snap a daily snapshot to build your history over time.")

    # ── Daily Snapshot ────────────────────────────────────────────────────────
    st.subheader("📸 Daily Snapshot")
    snap_col1, snap_col2 = st.columns([2, 1])
    history = load_history()
    today_str = str(__import__("datetime").date.today())
    today_snapped = any(s["date"] == today_str for s in history)

    with snap_col1:
        if today_snapped:
            today_snap = next(s for s in history if s["date"] == today_str)
            st.success(
                f"✅ Today's snapshot saved — "
                f"Value: **${today_snap['value']:,.2f}** | "
                f"P&L: **{'+'if today_snap['pnl']>=0 else ''}${today_snap['pnl']:,.2f}** "
                f"({today_snap['pnl_pct']:+.2f}%)"
            )
        else:
            st.info("📷 No snapshot taken today yet. Click below to save today's portfolio value.")

    with snap_col2:
        if st.button("📸 Save Today's Snapshot", use_container_width=True, type="primary"):
            with st.spinner("Fetching live prices…"):
                snap = take_snapshot()
            st.success(f"Snapshot saved! Value: ${snap['value']:,.2f} | P&L: {snap['pnl_pct']:+.2f}%")
            st.rerun()

    st.caption(f"Total snapshots saved: **{len(history)}** days of history")
    st.markdown("---")

    # ── Tracked Performance Stats ─────────────────────────────────────────────
    st.subheader("📊 Tracked Performance (From Daily Snapshots)")
    perf_cols = st.columns(3)
    for i, days in enumerate([30, 60, 90]):
        perf = get_performance_summary(days)
        with perf_cols[i]:
            if perf:
                sign = "+" if perf["change"] >= 0 else ""
                st.metric(
                    f"Last {days} Days",
                    f"${perf['end_value']:,.2f}",
                    delta=f"{sign}${perf['change']:,.2f} ({sign}{perf['change_pct']:.2f}%)",
                    delta_color="normal" if perf["change"] >= 0 else "inverse",
                )
            else:
                st.metric(f"Last {days} Days", "—", delta="Not enough data yet")

    st.markdown("---")

    # ── Snapshot Charts ───────────────────────────────────────────────────────
    snap_period = st.radio("Snapshot History Period", ["30 Days", "60 Days", "90 Days"],
                           horizontal=True, index=0)
    snap_days   = {"30 Days": 30, "60 Days": 60, "90 Days": 90}[snap_period]

    st.plotly_chart(portfolio_value_chart(snap_days), use_container_width=True)
    st.plotly_chart(pnl_history_chart(snap_days),     use_container_width=True)
    st.markdown("---")

    # ── Historical Price Chart (yfinance) ─────────────────────────────────────
    st.subheader("📈 Price History by Symbol (yfinance)")
    st.caption("Calculates portfolio value using historical stock prices from yfinance.")

    # ── Data range selector ───────────────────────────────────────────────────
    period_choice = st.radio(
        "Time Range",
        ["30 Days", "60 Days", "90 Days", "6 Months", "1 Year"],
        horizontal=True,
        index=2,
    )
    period_map = {
        "30 Days": ("1mo", 30),
        "60 Days": ("2mo", 60),
        "90 Days": ("3mo", 90),
        "6 Months": ("6mo", 180),
        "1 Year": ("1y", 365),
    }
    yf_period, num_days = period_map[period_choice]

    with st.spinner(f"Building {period_choice} portfolio history…"):
        df = get_enriched_portfolio()
        raw = load_portfolio()
        holdings = raw.get("holdings", [])

    if df.empty or not holdings:
        st.warning("No holdings found. Add positions to see history.")
        st.stop()

    # ── Fetch historical price data for each holding ──────────────────────────
    symbols = [h["symbol"] for h in holdings if not h["symbol"].endswith("-USD")]
    crypto  = [h["symbol"] for h in holdings if h["symbol"].endswith("-USD")]

    all_history = {}

    if symbols:
        try:
            hist_data = yf.download(symbols, period=yf_period,
                                    auto_adjust=True, progress=False)
            if len(symbols) == 1:
                prices = hist_data["Close"]
                all_history[symbols[0]] = prices
            else:
                close = hist_data["Close"]
                for sym in symbols:
                    if sym in close.columns:
                        all_history[sym] = close[sym]
        except Exception as e:
            st.warning(f"Could not fetch stock history: {e}")

    # Add crypto via yfinance
    for sym in crypto:
        try:
            h = yf.download(sym, period=yf_period, auto_adjust=True, progress=False)
            if not h.empty:
                all_history[sym] = h["Close"]
        except Exception:
            pass

    if not all_history:
        st.error("Could not fetch historical data.")
        st.stop()

    # ── Calculate portfolio value for each date ───────────────────────────────
    import pandas as pd
    from functools import reduce

    # Build a DataFrame: date × symbol prices
    frames = []
    for sym, series in all_history.items():
        s = series.reset_index()
        s.columns = ["Date", sym]
        s = s.dropna()
        frames.append(s.set_index("Date"))

    if not frames:
        st.error("No valid price history found.")
        st.stop()

    price_df = pd.concat(frames, axis=1).dropna(how="all")

    if price_df.empty:
        st.warning("No price history available yet. Add positions to your portfolio first.")
        st.stop()

    # Multiply each symbol's price by shares held
    shares_map = {h["symbol"]: float(h.get("shares", 0)) for h in holdings}

    portfolio_values = pd.Series(0.0, index=price_df.index)
    for sym in price_df.columns:
        shares = shares_map.get(sym, 0)
        if shares > 0:
            try:
                portfolio_values = portfolio_values.add(
                    price_df[sym].ffill() * shares,
                    fill_value=0,
                )
            except Exception:
                pass

    portfolio_values = portfolio_values[portfolio_values > 0]

    if portfolio_values.empty:
        st.warning("Not enough data to build history chart.")
        st.stop()

    # ── Build the chart ───────────────────────────────────────────────────────
    start_val = portfolio_values.iloc[0]
    end_val   = portfolio_values.iloc[-1]
    change    = end_val - start_val
    change_pct = (change / start_val * 100) if start_val else 0

    # KPI row
    h1, h2, h3, h4 = st.columns(4)
    h1.metric(f"Value {period_choice} Ago", f"${start_val:,.2f}")
    h2.metric("Value Today",                f"${end_val:,.2f}")
    sign = "+" if change >= 0 else ""
    h3.metric("Change ($)",  f"{sign}${change:,.2f}",
              delta=f"{sign}{change_pct:.2f}%")
    h4.metric("Data Points", len(portfolio_values))

    st.markdown("---")

    # Line color: green if positive, red if negative
    if change >= 0:
        line_color  = "#2ECC71"
        fill_color  = "rgba(46,204,113,0.10)"
    else:
        line_color  = "#E74C3C"
        fill_color  = "rgba(231,76,60,0.10)"

    fig = go.Figure()

    # Fill under the line
    fig.add_trace(go.Scatter(
        x=portfolio_values.index,
        y=portfolio_values.values,
        mode="lines",
        line=dict(color=line_color, width=2.5),
        fill="tozeroy",
        fillcolor=fill_color,
        name="Portfolio Value",
        hovertemplate="<b>%{x|%b %d, %Y}</b><br>Value: $%{y:,.2f}<extra></extra>",
    ))

    # Benchmark: SPY comparison
    try:
        spy = yf.download("SPY", period=yf_period, auto_adjust=True, progress=False)
        if not spy.empty:
            spy_close = spy["Close"].squeeze()
            spy_scale = start_val / spy_close.iloc[0]
            spy_scaled = spy_close * spy_scale
            fig.add_trace(go.Scatter(
                x=spy_scaled.index,
                y=spy_scaled.values,
                mode="lines",
                line=dict(color="#95A5A6", width=1.5, dash="dot"),
                name="SPY (scaled)",
                hovertemplate="<b>%{x|%b %d, %Y}</b><br>SPY (scaled): $%{y:,.2f}<extra></extra>",
            ))
    except Exception:
        pass

    fig.update_layout(
        title=f"Portfolio Value — Last {period_choice}",
        xaxis_title="Date",
        yaxis_title="Portfolio Value ($)",
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font=dict(color="#FAFAFA"),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#2a2f3a", tickprefix="$"),
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(0,0,0,0.4)"),
        hovermode="x unified",
        height=480,
    )

    st.plotly_chart(fig)

    st.markdown("---")

    # ── Per-holding contribution breakdown ────────────────────────────────────
    st.subheader("🧩 Per-Holding Contribution (Today)")
    st.caption("How much each position contributes to the total current value.")

    contrib_data = []
    for h in holdings:
        sym    = h["symbol"]
        shares = float(h.get("shares", 0))
        price  = price_df[sym].iloc[-1] if sym in price_df.columns else 0
        val    = shares * price
        if val > 0:
            contrib_data.append({"Symbol": sym, "Shares": shares,
                                  "Price": round(price, 2),
                                  "Value": round(val, 2)})

    if contrib_data:
        contrib_df = pd.DataFrame(contrib_data).sort_values("Value", ascending=False)
        total_val  = contrib_df["Value"].sum()
        contrib_df["Allocation %"] = (contrib_df["Value"] / total_val * 100).round(1)

        # Mini bar chart
        fig2 = go.Figure(go.Bar(
            x=contrib_df["Symbol"],
            y=contrib_df["Value"],
            marker_color="#3498DB",
            text=contrib_df["Allocation %"].apply(lambda x: f"{x:.1f}%"),
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Value: $%{y:,.2f}<extra></extra>",
        ))
        fig2.update_layout(
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
            font=dict(color="#FAFAFA"),
            yaxis=dict(tickprefix="$", showgrid=True, gridcolor="#2a2f3a"),
            xaxis=dict(showgrid=False),
            height=320,
        )
        st.plotly_chart(fig2)

        st.dataframe(
            contrib_df.style.format({
                "Price": "${:,.2f}", "Value": "${:,.2f}",
                "Allocation %": "{:.1f}%",
            }),
            use_container_width=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: TRADE JOURNAL
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📓 Trade Journal":
    from modules.trade_journal import (
        load_journal, add_trade, close_trade, delete_trade,
        get_journal_stats, STRATEGIES, EMOTIONS, GRADES,
    )
    from datetime import date as dt_date

    st.title("📓 Trade Journal")
    st.caption("Log every trade. Study your wins and losses. This is how you get better.")

    trades = load_journal()
    stats  = get_journal_stats(trades)

    # ── Stats dashboard ───────────────────────────────────────────────────────
    if trades:
        k1, k2, k3, k4, k5, k6 = st.columns(6)
        k1.metric("Total Trades",   stats["total_trades"])
        k2.metric("Win Rate",       f"{stats['win_rate']:.1f}%")
        pnl = stats["total_pnl"]
        k3.metric("Total P&L",      f"{'+'if pnl>=0 else ''}${pnl:,.2f}")
        k4.metric("Avg Win",        f"${stats['avg_win']:,.2f}")
        k5.metric("Avg Loss",       f"${stats['avg_loss']:,.2f}")
        k6.metric("Profit Factor",  f"{stats['profit_factor']:.2f}x")

        # Win/Loss bar
        if stats["wins"] + stats["losses"] > 0:
            win_pct = stats["wins"] / (stats["wins"] + stats["losses"])
            st.caption(f"🟢 {stats['wins']} wins  |  🔴 {stats['losses']} losses  |  ⚪ Open: {stats['open_trades']}")
            st.progress(win_pct)

        st.markdown("---")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_log, tab_open, tab_closed = st.tabs(["➕ Log New Trade", "🟡 Open Trades", "📊 Closed Trades"])

    with tab_log:
        st.markdown("**Fill this out BEFORE you enter the trade — not after.**")
        with st.form("journal_form", clear_on_submit=True):
            r1c1, r1c2, r1c3 = st.columns(3)
            j_sym  = r1c1.text_input("Ticker", placeholder="AAPL").upper().strip()
            j_dir  = r1c2.selectbox("Direction", ["LONG", "SHORT"])
            j_strat = r1c3.selectbox("Strategy", STRATEGIES)

            r2c1, r2c2, r2c3 = st.columns(3)
            j_entry_date  = r2c1.date_input("Entry Date", value=dt_date.today())
            j_entry_price = r2c2.number_input("Entry Price ($)", min_value=0.001, value=150.0, step=0.5)
            j_shares      = r2c3.number_input("Shares", min_value=0.001, value=10.0, step=1.0)

            r3c1, r3c2, r3c3 = st.columns(3)
            j_stop   = r3c1.number_input("Stop-Loss ($)", min_value=0.001, value=139.5, step=0.5)
            j_tp     = r3c2.number_input("Take-Profit ($)", min_value=0.001, value=172.5, step=0.5)
            j_emotion = r3c3.selectbox("Emotion at Entry", EMOTIONS)

            if j_entry_price > 0 and j_stop > 0:
                risk  = abs(j_entry_price - j_stop)
                rew   = abs(j_tp - j_entry_price)
                rr    = rew / risk if risk else 0
                cost  = j_entry_price * j_shares
                max_r = risk * j_shares
                st.caption(
                    f"💰 Cost basis: **${cost:,.2f}**  |  "
                    f"Max risk: **${max_r:,.2f}**  |  "
                    f"R:R ratio: **{rr:.2f}:1** {'✅' if rr >= 2 else '⚠️ Below 2:1 minimum'}"
                )

            j_setup = st.text_area("Why are you taking this trade? (Setup notes)", height=80,
                                   placeholder="Describe the setup: trend, support level, catalyst...")
            j_grade = st.selectbox("Pre-trade grade (how good is this setup?)", GRADES)

            j_exit_price = st.number_input("Exit Price (leave 0 if still open)", min_value=0.0, value=0.0, step=0.5)
            j_exit_date  = st.date_input("Exit Date (if closed)", value=dt_date.today())
            j_lesson     = st.text_area("Lesson / Notes (optional)", height=60)

            submitted = st.form_submit_button("📓 Log Trade", type="primary")

        if submitted and j_sym:
            trade = add_trade(
                symbol=j_sym, direction=j_dir, strategy=j_strat,
                entry_date=str(j_entry_date), entry_price=j_entry_price,
                shares=j_shares, stop_loss=j_stop, take_profit=j_tp,
                exit_date=str(j_exit_date) if j_exit_price > 0 else "",
                exit_price=j_exit_price, emotion=j_emotion,
                grade=j_grade, setup_notes=j_setup, lesson=j_lesson,
            )
            outcome = trade["outcome"]
            if outcome == "win":
                st.success(f"✅ Trade logged! P&L: +${trade['pnl_dollar']:,.2f} WIN")
            elif outcome == "loss":
                st.error(f"📓 Trade logged. P&L: ${trade['pnl_dollar']:,.2f} — loss recorded.")
            else:
                st.info(f"📓 Open trade logged for {j_sym}. Close it when you exit.")
            st.rerun()

    with tab_open:
        open_trades = [t for t in trades if t["outcome"] == "open"]
        if not open_trades:
            st.info("No open trades. Log one above!")
        else:
            for t in open_trades:
                with st.expander(f"🟡 {t['symbol']} — {t['strategy']} | Entry: ${t['entry_price']} | {t['entry_date']}", expanded=True):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Entry", f"${t['entry_price']:,.2f}")
                    c1.metric("Shares", t["shares"])
                    c2.metric("Stop-Loss", f"${t['stop_loss']:,.2f}")
                    c2.metric("Take-Profit", f"${t['take_profit']:,.2f}")
                    c3.metric("R:R Ratio", f"{t['rr_ratio']:.2f}:1")
                    c3.metric("Max Risk", f"${t['max_risk']:,.2f}")

                    if t.get("setup_notes"):
                        st.info(f"📝 Setup: {t['setup_notes']}")

                    st.markdown("**Close this trade:**")
                    with st.form(f"close_{t['id']}"):
                        ex1, ex2 = st.columns(2)
                        ex_price = ex1.number_input("Exit Price ($)", min_value=0.001,
                                                    value=float(t["entry_price"]), step=0.5)
                        ex_date  = ex2.date_input("Exit Date", value=dt_date.today())
                        ex_notes = st.text_input("What happened?", placeholder="Hit stop-loss / took profit / news event...")
                        ex_lesson = st.text_input("Lesson learned", placeholder="What would you do differently?")
                        ex_grade = st.selectbox("How did you execute?", GRADES)
                        if st.form_submit_button("✅ Close Trade", type="primary"):
                            close_trade(t["id"], str(ex_date), ex_price, ex_notes, ex_lesson, ex_grade)
                            st.rerun()

                    if st.button("🗑 Delete", key=f"del_open_{t['id']}"):
                        delete_trade(t["id"])
                        st.rerun()

    with tab_closed:
        closed_trades = [t for t in trades if t["outcome"] in ("win", "loss", "breakeven")]
        if not closed_trades:
            st.info("No closed trades yet.")
        else:
            # Summary table
            import pandas as pd
            rows = []
            for t in reversed(closed_trades):
                rows.append({
                    "Date":     t["exit_date"],
                    "Symbol":   t["symbol"],
                    "Strategy": t["strategy"],
                    "Direction":t["direction"],
                    "Entry":    t["entry_price"],
                    "Exit":     t["exit_price"],
                    "Shares":   t["shares"],
                    "P&L ($)":  t["pnl_dollar"],
                    "P&L (%)":  t["pnl_pct"],
                    "R:R":      t["rr_ratio"],
                    "Grade":    t["grade"][0],
                    "Outcome":  t["outcome"].upper(),
                })

            df_j = pd.DataFrame(rows)

            def color_outcome(val):
                if isinstance(val, float):
                    return "color: #2ECC71" if val >= 0 else "color: #E74C3C"
                return ""

            st.dataframe(
                df_j.style.map(color_outcome, subset=["P&L ($)", "P&L (%)"]).format({
                    "Entry": "${:,.2f}", "Exit": "${:,.2f}",
                    "P&L ($)": "${:+,.2f}", "P&L (%)": "{:+.2f}%",
                    "R:R": "{:.2f}x",
                }),
                use_container_width=True, height=380,
            )

            # Individual detail expanders
            st.markdown("---")
            st.subheader("Trade Details")
            for t in reversed(closed_trades[-10:]):
                icon = "🟢" if t["outcome"] == "win" else "🔴"
                with st.expander(
                    f"{icon} {t['symbol']} — {t['outcome'].upper()} "
                    f"{'+'if t['pnl_dollar']>=0 else ''}${t['pnl_dollar']:,.2f} "
                    f"| {t['entry_date']} → {t['exit_date']}"
                ):
                    d1, d2, d3 = st.columns(3)
                    d1.markdown(f"**Entry:** ${t['entry_price']:,.2f}\n\n**Exit:** ${t['exit_price']:,.2f}\n\n**Shares:** {t['shares']}")
                    d2.markdown(f"**Strategy:** {t['strategy']}\n\n**R:R:** {t['rr_ratio']}:1\n\n**Grade:** {t['grade'][0]}")
                    d3.markdown(f"**Emotion:** {t['emotion']}\n\n**P&L:** {'+'if t['pnl_dollar']>=0 else ''}${t['pnl_dollar']:,.2f} ({t['pnl_pct']:+.2f}%)")
                    if t.get("setup_notes"):
                        st.info(f"📋 Setup: {t['setup_notes']}")
                    if t.get("result_notes"):
                        st.warning(f"📊 Result: {t['result_notes']}")
                    if t.get("lesson"):
                        st.success(f"💡 Lesson: {t['lesson']}")
                    if st.button("🗑 Delete", key=f"del_closed_{t['id']}"):
                        delete_trade(t["id"])
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: DAILY BRIEFING
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🌅 Daily Briefing":
    import yfinance as yf
    import pandas as pd
    from datetime import date as dt_date, datetime as dt_datetime
    from modules.portfolio import get_enriched_portfolio
    from modules.price_alerts import load_alerts, check_alerts
    from modules.market_data import get_bulk_prices
    from modules.contribution_reminder import get_contribution_status

    st.title("🌅 Daily Briefing")
    st.caption(f"Good morning! Here's everything you need to know before the market opens — {dt_date.today().strftime('%A, %B %d, %Y')}")

    with st.spinner("Loading market data…"):
        # ── Market indices ────────────────────────────────────────────────────
        indices = {
            "S&P 500": "^GSPC", "Nasdaq": "^IXIC", "Dow Jones": "^DJI",
            "VIX": "^VIX", "BTC": "BTC-USD", "ETH": "ETH-USD",
        }
        idx_data = {}
        for name, ticker in indices.items():
            try:
                t = yf.Ticker(ticker)
                h = t.history(period="2d")
                if len(h) >= 2:
                    prev  = h["Close"].iloc[-2]
                    curr  = h["Close"].iloc[-1]
                    chg   = curr - prev
                    chg_p = chg / prev * 100
                    idx_data[name] = {"price": curr, "change": chg, "pct": chg_p}
            except Exception:
                pass

    st.subheader("📊 Markets at a Glance")
    cols = st.columns(len(idx_data))
    for i, (name, d) in enumerate(idx_data.items()):
        delta_str = f"{'+' if d['pct']>=0 else ''}{d['pct']:.2f}%"
        cols[i].metric(name, f"${d['price']:,.2f}" if d['price'] > 100 else f"${d['price']:,.4f}",
                       delta=delta_str)

    st.markdown("---")

    # ── Portfolio snapshot ────────────────────────────────────────────────────
    st.subheader("💼 Your Portfolio Today")
    try:
        df_port = get_enriched_portfolio()
        if not df_port.empty:
            total_val  = df_port["Market Value"].sum()
            total_cost = df_port["P&L ($)"].sum() + df_port["Market Value"].sum() - df_port["P&L ($)"].sum()
            total_pnl  = df_port["P&L ($)"].sum()
            p1, p2, p3, p4 = st.columns(4)
            p1.metric("Portfolio Value", f"${total_val:,.2f}")
            p2.metric("Total P&L", f"{'+'if total_pnl>=0 else ''}${total_pnl:,.2f}")
            p3.metric("Positions", len(df_port))
            winners = len(df_port[df_port["P&L ($)"] > 0])
            p4.metric("Winners / Losers", f"{winners} / {len(df_port)-winners}")

            # Top mover
            top = df_port.loc[df_port["P&L (%)"].abs().idxmax()]
            if top["P&L (%)"] > 0:
                st.success(f"🏆 Best performer today: **{top['Symbol']}** +{top['P&L (%)']:.2f}%")
            else:
                st.warning(f"📉 Biggest drag today: **{top['Symbol']}** {top['P&L (%)']:.2f}%")
    except Exception as e:
        st.info("Add positions to see your portfolio snapshot here.")

    st.markdown("---")

    # ── Price alerts check ────────────────────────────────────────────────────
    st.subheader("🔔 Alert Status")
    try:
        alerts = load_alerts()
        if alerts:
            syms   = list({a["symbol"] for a in alerts})
            prices = get_bulk_prices(syms)
            triggered = check_alerts(prices)
            if triggered:
                for t in triggered:
                    atype = t.get("alert_type", "price_alert")
                    if atype == "stop_loss":
                        st.error(f"🛑 STOP-LOSS HIT: **{t['symbol']}** at ${t['current_price']:,.2f} — SELL NOW")
                    elif atype == "take_profit":
                        st.success(f"🎯 TAKE-PROFIT HIT: **{t['symbol']}** at ${t['current_price']:,.2f} — Lock in gains!")
                    else:
                        st.warning(f"🔔 Alert: **{t['symbol']}** hit ${t['current_price']:,.2f}")
            else:
                st.success(f"✅ No alerts triggered. Watching {len([a for a in alerts if a.get('active',True)])} alerts.")
        else:
            st.info("No alerts set. Go to 🔔 Price Alerts to add some.")
    except Exception:
        st.info("Could not load alerts.")

    st.markdown("---")

    # ── Contribution status ───────────────────────────────────────────────────
    st.subheader("💰 Monthly Contribution")
    try:
        cs = get_contribution_status()
        urgency = cs["urgency"]
        if urgency == "complete":
            st.success(cs["message"])
        elif urgency == "on_track":
            st.success(cs["message"])
        elif urgency == "warning":
            st.warning(cs["message"])
        elif urgency == "critical":
            st.error(cs["message"])
        else:
            st.info(cs["message"])
        st.progress(min(cs["pct_complete"] / 100, 1.0))
    except Exception:
        pass

    st.markdown("---")

    # ── Today's checklist ─────────────────────────────────────────────────────
    st.subheader("✅ Daily Checklist")
    checklist = [
        "Check all price alerts and stop-losses above",
        "Review your open trades in 📓 Trade Journal",
        "Check if any positions hit stop-loss or take-profit overnight",
        "Review earnings calendar for any stocks you hold",
        "Check your monthly contribution status",
        "Do NOT trade out of FOMO or emotion today",
    ]
    for item in checklist:
        st.checkbox(item, key=f"chk_{item[:20]}")

    st.markdown("---")

    # ── Watchlist movers ──────────────────────────────────────────────────────
    st.subheader("👀 Watchlist Movers")
    from modules.portfolio import load_portfolio
    raw = load_portfolio()
    wl  = raw.get("watchlist", [])
    if wl:
        wl_syms   = [w["symbol"] for w in wl]
        wl_prices = get_bulk_prices(wl_syms)
        wc = st.columns(min(len(wl), 5))
        for i, w in enumerate(wl[:5]):
            sym = w["symbol"]
            p   = wl_prices.get(sym, 0)
            wc[i].metric(sym, f"${p:,.2f}" if p else "—")
    else:
        st.info("Add stocks to your Watchlist to see them here.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: REBALANCING TOOL
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "⚖️ Rebalancing Tool":
    import pandas as pd
    from modules.portfolio import get_enriched_portfolio

    st.title("⚖️ Portfolio Rebalancing Tool")
    st.caption("See when your allocation has drifted and exactly what to buy or sell to get back on track.")

    # ── Target allocation inputs ──────────────────────────────────────────────
    st.subheader("🎯 Your Target Allocation")
    st.caption("Set your ideal percentages for each asset class. They should add up to 100%.")

    t1, t2, t3, t4 = st.columns(4)
    target_etf    = t1.number_input("ETFs (%)",          min_value=0, max_value=100, value=40, step=5)
    target_stock  = t2.number_input("Stocks (%)",        min_value=0, max_value=100, value=35, step=5)
    target_crypto = t3.number_input("Crypto (%)",        min_value=0, max_value=100, value=10, step=5)
    target_other  = t4.number_input("Other/REIT (%)",    min_value=0, max_value=100, value=15, step=5)

    total_target = target_etf + target_stock + target_crypto + target_other
    if total_target != 100:
        st.warning(f"⚠️ Targets add up to {total_target}% — adjust to exactly 100%")
    else:
        st.success("✅ Targets add up to 100%")

    st.markdown("---")

    # ── Current allocation ────────────────────────────────────────────────────
    with st.spinner("Loading portfolio…"):
        df = get_enriched_portfolio()

    if df.empty:
        st.info("No portfolio data found. Add positions first.")
        st.stop()

    total_value = df["Market Value"].sum()

    # Group by type
    type_map = {"etf": "ETF", "stock": "STOCK", "crypto": "CRYPTO"}
    df["TypeGroup"] = df["Type"].str.upper().map(
        lambda x: "ETF" if x == "ETF" else ("CRYPTO" if x == "CRYPTO" else "STOCK")
    )

    actual = df.groupby("TypeGroup")["Market Value"].sum()
    actual_pct = (actual / total_value * 100).round(1)

    targets = {
        "ETF":    target_etf,
        "STOCK":  target_stock,
        "CRYPTO": target_crypto,
    }

    st.subheader("📊 Current vs Target")
    cols = st.columns(4)
    for i, (atype, tpct) in enumerate(targets.items()):
        curr_pct = actual_pct.get(atype, 0)
        curr_val = actual.get(atype, 0)
        drift    = curr_pct - tpct
        cols[i].metric(
            f"{atype}",
            f"{curr_pct:.1f}%  (${curr_val:,.0f})",
            delta=f"{drift:+.1f}% from {tpct}% target",
            delta_color="inverse" if abs(drift) > 5 else "off",
        )
    cols[3].metric("Total Value", f"${total_value:,.2f}")

    st.markdown("---")

    # ── Rebalancing actions ───────────────────────────────────────────────────
    st.subheader("🔧 What to Do to Rebalance")

    threshold = st.slider("Drift threshold — only flag if off by more than:", 2, 15, 5,
                          help="5% is standard. Below 5% drift is normal, don't overtrade.")

    rebalance_actions = []
    for atype, tpct in targets.items():
        curr_pct = float(actual_pct.get(atype, 0))
        curr_val = float(actual.get(atype, 0))
        target_val = total_value * tpct / 100
        diff_val   = target_val - curr_val
        drift      = curr_pct - tpct

        if abs(drift) < threshold:
            status = "✅ On target"
            action = "No action needed"
        elif drift > 0:
            status = "📉 Overweight — SELL/TRIM"
            action = f"Reduce {atype} by ${abs(diff_val):,.2f}"
        else:
            status = "📈 Underweight — BUY"
            action = f"Add ${abs(diff_val):,.2f} to {atype}"

        rebalance_actions.append({
            "Asset Class": atype,
            "Current %":  f"{curr_pct:.1f}%",
            "Target %":   f"{tpct}%",
            "Drift":      f"{drift:+.1f}%",
            "Status":     status,
            "Action":     action,
        })

    reb_df = pd.DataFrame(rebalance_actions)
    st.dataframe(reb_df, use_container_width=True)

    # ── Per-holding breakdown ─────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📋 Holdings Breakdown")
    st.dataframe(
        df[["Symbol", "Type", "Market Value", "Allocation %"]].sort_values("Market Value", ascending=False).style.format({
            "Market Value": "${:,.2f}", "Allocation %": "{:.1f}%",
        }),
        use_container_width=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: WATCHLIST PRICE TARGETS
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🎯 Watchlist Targets":
    import json
    import pandas as pd
    from modules.portfolio import load_portfolio, PORTFOLIO_PATH
    from modules.market_data import get_bulk_prices

    st.title("🎯 Watchlist Price Targets")
    st.caption("Set a fair-value buy target on each watchlist stock. Get a buy signal when it drops there.")

    raw = load_portfolio()
    watchlist = raw.get("watchlist", [])

    if not watchlist:
        st.info("Your watchlist is empty. Add stocks via the 👀 Watchlist page first.")
        st.stop()

    # Fetch live prices
    syms = [w["symbol"] for w in watchlist]
    with st.spinner("Fetching live prices…"):
        prices = get_bulk_prices(syms)

    # ── Set targets ───────────────────────────────────────────────────────────
    st.subheader("📝 Set Your Buy Targets")
    st.caption("Enter the price you think is a good entry point for each stock.")

    updated = False
    with st.form("targets_form"):
        for w in watchlist:
            sym   = w["symbol"]
            price = prices.get(sym, 0)
            c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.5, 2])
            c1.markdown(f"**{sym}**")
            c2.markdown(f"Now: **${price:,.2f}**" if price else "—")
            current_target = w.get("buy_target", 0)
            new_target = c3.number_input(
                "Buy Target ($)", min_value=0.0, value=float(current_target),
                step=0.5, key=f"target_{sym}", label_visibility="collapsed"
            )
            # Show distance from current price
            if price and new_target > 0:
                dist = (new_target - price) / price * 100
                c4.markdown(f"{'🟢 BUY NOW' if price <= new_target else f'📉 {abs(dist):.1f}% below current'}")
            w["buy_target"] = round(new_target, 2)

        if st.form_submit_button("💾 Save Targets", type="primary"):
            raw["watchlist"] = watchlist
            with open(PORTFOLIO_PATH, "w") as f:
                json.dump(raw, f, indent=2)
            updated = True

    if updated:
        st.success("✅ Targets saved!")
        st.rerun()

    st.markdown("---")

    # ── Buy signals ───────────────────────────────────────────────────────────
    st.subheader("🔔 Buy Signals")
    buy_signals = [w for w in watchlist if w.get("buy_target", 0) > 0 and prices.get(w["symbol"], 0) <= w["buy_target"] and prices.get(w["symbol"], 0) > 0]
    watching    = [w for w in watchlist if w.get("buy_target", 0) > 0 and prices.get(w["symbol"], 0) > w["buy_target"]]
    no_target   = [w for w in watchlist if not w.get("buy_target", 0)]

    if buy_signals:
        for w in buy_signals:
            sym = w["symbol"]; price = prices.get(sym, 0); target = w["buy_target"]
            st.success(f"🟢 **BUY SIGNAL — {sym}** | Current: ${price:,.2f} | Your target: ${target:,.2f} | ✅ AT OR BELOW TARGET")
    if watching:
        st.markdown("**⏳ Watching — waiting for price to drop:**")
        rows = []
        for w in watching:
            sym = w["symbol"]; price = prices.get(sym, 0); target = w["buy_target"]
            gap = (price - target) / target * 100
            rows.append({"Symbol": sym, "Current Price": price, "Buy Target": target, "Gap to Target": f"{gap:.1f}% above"})
        st.dataframe(pd.DataFrame(rows).style.format({"Current Price": "${:,.2f}", "Buy Target": "${:,.2f}"}), use_container_width=True)
    if no_target:
        st.caption(f"No target set for: {', '.join(w['symbol'] for w in no_target)}")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: EXPORT P&L
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📤 Export P&L":
    import pandas as pd
    import io
    from modules.portfolio import get_enriched_portfolio
    from modules.trade_journal import load_journal

    st.title("📤 Export P&L")
    st.caption("Download your portfolio data and trade history for taxes or record keeping.")

    tab_port, tab_journal = st.tabs(["💼 Portfolio Holdings", "📓 Trade Journal"])

    with tab_port:
        st.subheader("Portfolio Holdings Export")
        df = get_enriched_portfolio()
        if df.empty:
            st.info("No portfolio data to export.")
        else:
            export_cols = ["Symbol", "Type", "Shares", "Avg Cost", "Current Price",
                           "Market Value", "P&L ($)", "P&L (%)", "Allocation %"]
            df_export = df[export_cols].copy()

            # Show preview
            st.dataframe(df_export.style.format({
                "Avg Cost": "${:,.2f}", "Current Price": "${:,.2f}",
                "Market Value": "${:,.2f}", "P&L ($)": "${:+,.2f}",
                "P&L (%)": "{:+.2f}%", "Allocation %": "{:.1f}%",
            }), use_container_width=True)

            # Summary
            total_val = df["Market Value"].sum()
            total_pnl = df["P&L ($)"].sum()
            st.metric("Total Portfolio Value", f"${total_val:,.2f}")
            st.metric("Total Unrealized P&L",  f"{'+'if total_pnl>=0 else ''}${total_pnl:,.2f}")

            # CSV download
            csv_buf = io.StringIO()
            df_export.to_csv(csv_buf, index=False)
            st.download_button(
                "📥 Download Holdings CSV",
                data=csv_buf.getvalue(),
                file_name=f"portfolio_holdings_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                type="primary",
            )

    with tab_journal:
        st.subheader("Trade Journal Export")
        trades = load_journal()
        closed = [t for t in trades if t["outcome"] in ("win", "loss", "breakeven")]
        if not closed:
            st.info("No closed trades to export yet.")
        else:
            journal_rows = []
            for t in closed:
                journal_rows.append({
                    "Entry Date": t["entry_date"],
                    "Exit Date":  t["exit_date"],
                    "Symbol":     t["symbol"],
                    "Direction":  t["direction"],
                    "Strategy":   t["strategy"],
                    "Shares":     t["shares"],
                    "Entry Price": t["entry_price"],
                    "Exit Price":  t["exit_price"],
                    "P&L ($)":    t["pnl_dollar"],
                    "P&L (%)":    t["pnl_pct"],
                    "Outcome":    t["outcome"].upper(),
                    "Grade":      t["grade"][0],
                    "R:R Ratio":  t["rr_ratio"],
                    "Lesson":     t.get("lesson", ""),
                })

            df_j = pd.DataFrame(journal_rows)
            st.dataframe(df_j, use_container_width=True)

            wins   = sum(1 for t in closed if t["outcome"] == "win")
            losses = sum(1 for t in closed if t["outcome"] == "loss")
            total_pnl = sum(t["pnl_dollar"] for t in closed)
            j1, j2, j3 = st.columns(3)
            j1.metric("Total Trades", len(closed))
            j2.metric("Win Rate", f"{wins/(wins+losses)*100:.1f}%" if wins+losses else "—")
            j3.metric("Total Realized P&L", f"{'+'if total_pnl>=0 else ''}${total_pnl:,.2f}")

            csv_buf2 = io.StringIO()
            df_j.to_csv(csv_buf2, index=False)
            st.download_button(
                "📥 Download Trade Journal CSV",
                data=csv_buf2.getvalue(),
                file_name=f"trade_journal_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                type="primary",
            )


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: NET WORTH TRACKER
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "💎 Net Worth Tracker":
    import json
    import pandas as pd
    import plotly.graph_objects as go
    from datetime import date as dt_date

    NET_WORTH_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data", "net_worth.json"
    )

    def load_nw():
        if not os.path.exists(NET_WORTH_PATH):
            return {"snapshots": [], "categories": {}}
        with open(NET_WORTH_PATH) as f:
            return json.load(f)

    def save_nw(data):
        with open(NET_WORTH_PATH, "w") as f:
            json.dump(data, f, indent=2)

    st.title("💎 Net Worth Tracker")
    st.caption("Track your total wealth — investments, savings, assets, and debts — all in one place.")

    nw_data = load_nw()

    # ── Input form ────────────────────────────────────────────────────────────
    st.subheader("📥 Log Today's Net Worth Snapshot")
    st.caption("Update this monthly. Fill in your actual balances.")

    with st.form("net_worth_form", clear_on_submit=False):
        st.markdown("**Assets (what you own)**")
        a1, a2, a3 = st.columns(3)
        nw_checking  = a1.number_input("Checking Account ($)", min_value=0.0, value=0.0, step=100.0)
        nw_savings   = a2.number_input("Savings / E-Fund ($)",  min_value=0.0, value=0.0, step=100.0)
        nw_invest    = a3.number_input("Investment Portfolio ($)", min_value=0.0, value=0.0, step=100.0)
        b1, b2, b3 = st.columns(3)
        nw_crypto    = b1.number_input("Crypto ($)",            min_value=0.0, value=0.0, step=50.0)
        nw_car       = b2.number_input("Car Value ($)",          min_value=0.0, value=0.0, step=500.0)
        nw_other_asset = b3.number_input("Other Assets ($)",    min_value=0.0, value=0.0, step=100.0)

        st.markdown("**Debts (what you owe)**")
        c1, c2, c3 = st.columns(3)
        nw_car_loan  = c1.number_input("Car Loan ($)",          min_value=0.0, value=0.0, step=100.0)
        nw_cc        = c2.number_input("Credit Card Debt ($)",  min_value=0.0, value=0.0, step=100.0)
        nw_other_debt = c3.number_input("Other Debt ($)",       min_value=0.0, value=0.0, step=100.0)

        nw_note = st.text_input("Note (optional)", placeholder="e.g. Got a raise, paid off card...")
        nw_submit = st.form_submit_button("💾 Save Snapshot", type="primary")

    if nw_submit:
        total_assets = nw_checking + nw_savings + nw_invest + nw_crypto + nw_car + nw_other_asset
        total_debts  = nw_car_loan + nw_cc + nw_other_debt
        net_worth    = total_assets - total_debts
        snapshot = {
            "date":          str(dt_date.today()),
            "checking":      nw_checking,
            "savings":       nw_savings,
            "investments":   nw_invest,
            "crypto":        nw_crypto,
            "car_value":     nw_car,
            "other_assets":  nw_other_asset,
            "total_assets":  round(total_assets, 2),
            "car_loan":      nw_car_loan,
            "credit_cards":  nw_cc,
            "other_debts":   nw_other_debt,
            "total_debts":   round(total_debts, 2),
            "net_worth":     round(net_worth, 2),
            "note":          nw_note,
        }
        nw_data.setdefault("snapshots", []).append(snapshot)
        save_nw(nw_data)
        st.success(f"✅ Net Worth snapshot saved: **{'+'if net_worth>=0 else ''}${net_worth:,.2f}**")
        st.rerun()

    st.markdown("---")

    snapshots = nw_data.get("snapshots", [])
    if not snapshots:
        st.info("No snapshots yet. Log your first one above!")
        st.stop()

    # ── Latest snapshot KPIs ──────────────────────────────────────────────────
    latest = snapshots[-1]
    prev   = snapshots[-2] if len(snapshots) >= 2 else None

    st.subheader("📊 Current Net Worth")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Net Worth", f"${latest['net_worth']:,.2f}",
              delta=f"${latest['net_worth']-prev['net_worth']:+,.2f} since last" if prev else None)
    k2.metric("Total Assets",  f"${latest['total_assets']:,.2f}")
    k3.metric("Total Debts",   f"${latest['total_debts']:,.2f}")
    k4.metric("Snapshots Logged", len(snapshots))

    st.markdown("---")

    # ── Net worth chart ───────────────────────────────────────────────────────
    st.subheader("📈 Net Worth Over Time")
    df_nw = pd.DataFrame(snapshots)
    df_nw["date"] = pd.to_datetime(df_nw["date"])

    fig_nw = go.Figure()
    fig_nw.add_trace(go.Scatter(
        x=df_nw["date"], y=df_nw["net_worth"],
        mode="lines+markers",
        line=dict(color="#2ECC71", width=2.5),
        fill="tozeroy",
        fillcolor="rgba(46,204,113,0.10)",
        name="Net Worth",
        hovertemplate="<b>%{x|%b %d, %Y}</b><br>Net Worth: $%{y:,.2f}<extra></extra>",
    ))
    fig_nw.add_trace(go.Bar(
        x=df_nw["date"], y=df_nw["total_assets"],
        name="Assets", marker_color="rgba(41,128,185,0.4)",
    ))
    fig_nw.add_trace(go.Bar(
        x=df_nw["date"], y=[-v for v in df_nw["total_debts"]],
        name="Debts", marker_color="rgba(231,76,60,0.4)",
    ))
    fig_nw.update_layout(
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        font=dict(color="#FAFAFA"),
        yaxis=dict(tickprefix="$", showgrid=True, gridcolor="#2a2f3a"),
        xaxis=dict(showgrid=False),
        barmode="overlay",
        hovermode="x unified",
        height=400,
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(0,0,0,0.4)"),
    )
    st.plotly_chart(fig_nw, use_container_width=True)

    # ── History table ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📋 Snapshot History")
    display_df = df_nw[["date","total_assets","total_debts","net_worth","note"]].copy()
    display_df.columns = ["Date","Assets","Debts","Net Worth","Note"]
    display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d")
    st.dataframe(display_df.style.format({
        "Assets": "${:,.2f}", "Debts": "${:,.2f}", "Net Worth": "${:,.2f}",
    }), use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: AUTO TRADER
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🤖 Auto Trader":
    from modules.auto_trader import (
        get_account, get_positions, place_order, get_current_price,
        load_rules, add_rule, delete_rule, toggle_rule,
        check_and_execute_rules, get_trade_log,
        get_trading_mode, set_trading_mode,
    )

    st.title("🤖 Auto Trader")

    # ── Trading Mode Banner ───────────────────────────────────────────────────
    is_paper = get_trading_mode()
    if is_paper:
        st.success("🟡 **PAPER TRADING MODE** — No real money is used. Safe to test rules and strategies.")
    else:
        st.error("🔴 **LIVE TRADING MODE** — Real money is at risk. All orders execute with actual funds.")

    # ── Trading Mode Toggle ───────────────────────────────────────────────────
    with st.expander("⚙️ Switch Trading Mode", expanded=False):
        st.markdown("### Trading Mode Settings")
        current_mode = "📄 Paper Trading (simulated)" if is_paper else "💸 Live Trading (real money)"
        st.info(f"**Current Mode:** {current_mode}")

        if is_paper:
            st.markdown("""
            **Ready to go live?** Before switching, make sure:
            - ✅ Your strategy has been tested in paper mode
            - ✅ You have a **live** Alpaca account (not just paper)
            - ✅ You have real funds deposited in Alpaca
            - ✅ Your live API keys are entered (different from paper keys)
            - ✅ You understand all orders will use **real money**
            """)
            st.warning("⚠️ Switching to live trading means all orders — including auto-trade rules — will use real money.")
            confirm1 = st.checkbox("I understand this will trade with real money")
            confirm2 = st.checkbox("I have tested my strategy in paper mode")
            confirm3 = st.checkbox("I have my live Alpaca API keys configured")
            if st.button("🔴 Switch to LIVE Trading", type="primary",
                         disabled=not (confirm1 and confirm2 and confirm3)):
                result = set_trading_mode(paper=False)
                if result.get("success"):
                    st.success("Switched to LIVE trading mode. Page refreshing…")
                    st.rerun()
                else:
                    st.error(result.get("error"))
        else:
            st.markdown("Switch back to paper trading to test strategies safely without risking real money.")
            if st.button("🟡 Switch Back to PAPER Trading", type="secondary"):
                result = set_trading_mode(paper=True)
                if result.get("success"):
                    st.success("Switched back to Paper trading mode.")
                    st.rerun()

    st.caption("Set rules to automatically buy or sell stocks when price conditions are met.")

    # ── Account summary ───────────────────────────────────────────────────────
    with st.spinner("Loading Alpaca account…"):
        acct = get_account()

    if "error" in acct:
        st.error(f"Alpaca connection error: {acct['error']}")
        st.stop()

    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Cash", f"${acct['cash']:,.2f}")
    col2.metric("📈 Portfolio Value", f"${acct['portfolio_value']:,.2f}")
    col3.metric("🛒 Buying Power", f"${acct['buying_power']:,.2f}")
    st.markdown("---")

    # ── Current positions ─────────────────────────────────────────────────────
    st.subheader("💼 Alpaca Positions")
    positions = get_positions()
    if positions and "error" not in positions[0]:
        import pandas as pd
        df_pos = pd.DataFrame(positions)
        df_pos.columns = ["Symbol","Qty","Avg Cost","Price","Mkt Value","P&L","P&L %"]
        st.dataframe(df_pos.style.format({
            "Avg Cost": "${:,.2f}", "Price": "${:,.2f}",
            "Mkt Value": "${:,.2f}", "P&L": "${:,.2f}", "P&L %": "{:.2f}%"
        }), use_container_width=True)
    else:
        st.info("No open positions in Alpaca yet.")

    st.markdown("---")

    # ── Manual order ──────────────────────────────────────────────────────────
    st.subheader("⚡ Place Order Now")
    with st.form("manual_order_form"):
        col1, col2, col3 = st.columns(3)
        sym  = col1.text_input("Symbol", placeholder="AAPL").upper()
        qty  = col2.number_input("Shares", min_value=0.001, value=1.0, step=0.001, format="%.3f")
        side = col3.selectbox("Action", ["buy", "sell"])
        submit_order = st.form_submit_button("🚀 Place Order", use_container_width=True)
        if submit_order and sym:
            price = get_current_price(sym)
            st.write(f"Current price of **{sym}**: ${price:,.2f} | Total: ${price * qty:,.2f}")
            result = place_order(sym, qty, side)
            if result.get("success"):
                st.success(f"✅ Order placed! {side.upper()} {qty} shares of {sym} — Order ID: {result['order_id']}")
            else:
                st.error(f"Order failed: {result.get('error')}")

    st.markdown("---")

    # ── Auto rules ────────────────────────────────────────────────────────────
    st.subheader("🎯 Auto-Trade Rules")
    st.caption("Rules run automatically every 5 minutes when the alert monitor is active.")

    with st.expander("➕ Add New Rule", expanded=False):
        with st.form("add_rule_form"):
            col1, col2 = st.columns(2)
            r_sym   = col1.text_input("Symbol", placeholder="AAPL").upper()
            r_type  = col2.selectbox("Rule Type", [
                "price_drop — Buy if price drops below $X",
                "price_rise — Sell if price rises above $X",
                "pct_drop  — Buy if price drops X% from now",
                "pct_rise  — Sell if price rises X% from now",
            ])
            col3, col4 = st.columns(2)
            r_val  = col3.number_input("Trigger Value ($  or %)", min_value=0.01, value=100.0)
            r_qty  = col4.number_input("Shares", min_value=0.001, value=1.0, step=0.001, format="%.3f")
            r_note = st.text_input("Note (optional)")
            add_btn = st.form_submit_button("Add Rule", use_container_width=True)
            if add_btn and r_sym:
                rtype_key = r_type.split(" ")[0].strip()
                rule = add_rule(r_sym, rtype_key, r_val, r_qty, r_note)
                st.success(f"✅ Rule added: {rtype_key} for {r_sym} at {r_val}")
                st.rerun()

    # Display existing rules
    rules = load_rules()
    if rules:
        for r in rules:
            status = "🟢 Active" if r.get("active") else "⏸ Paused"
            triggered = "✅ TRIGGERED" if r.get("triggered") else ""
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                col1.markdown(f"**{r['symbol']}** — {r['rule_type']} @ {r['trigger_value']} | {r['qty']} shares {triggered}")
                col2.markdown(f"{status} | Side: **{r['side'].upper()}**")
                if col3.button("Toggle", key=f"tog_{r['id']}"):
                    toggle_rule(r["id"])
                    st.rerun()
                if col4.button("🗑️", key=f"del_{r['id']}"):
                    delete_rule(r["id"])
                    st.rerun()
    else:
        st.info("No auto-trade rules yet. Add one above to get started.")

    st.markdown("---")

    # ── Run rules now ─────────────────────────────────────────────────────────
    st.subheader("▶️ Run Rules Now")
    if st.button("🔍 Check & Execute All Rules", use_container_width=True):
        with st.spinner("Checking rules…"):
            executed = check_and_execute_rules()
        if executed:
            for e in executed:
                if e.get("success"):
                    st.success(f"✅ Executed: {e['side'].upper()} {e['qty']} {e['symbol']} @ ${e['price']:,.2f}")
                else:
                    st.error(f"Failed: {e.get('error')}")
        else:
            st.info("No rules triggered at current prices.")

    st.markdown("---")

    # ── Trade log ─────────────────────────────────────────────────────────────
    st.subheader("📋 Auto-Trade Log")
    log = get_trade_log()
    if log:
        import pandas as pd
        df_log = pd.DataFrame(log)
        st.dataframe(df_log, use_container_width=True)
    else:
        st.info("No auto trades executed yet.")

# ═════════════════════════════════════════════════════════════════════════════
# PAGE: Tax Lots
# ═════════════════════════════════════════════════════════════════════════════
elif page == "🧾 Tax Lots":
    import pandas as pd
    from modules.tax_lots import (
        load_lots, add_lot, delete_lot, enrich_lot,
        get_tax_summary, sell_recommendation,
    )

    st.title("🧾 Tax Lot Tracker")
    st.caption("Track purchase dates, holding periods, and estimated capital gains tax for each position.")

    # ── Tax summary ───────────────────────────────────────────────────────────
    lots = load_lots()

    if lots:
        # Get live prices for all symbols in lots
        symbols_in_lots = list({l["symbol"] for l in lots})
        prices = {}
        with st.spinner("Fetching live prices…"):
            try:
                import yfinance as yf
                for sym in symbols_in_lots:
                    t = yf.Ticker(sym)
                    h = t.history(period="2d")
                    if not h.empty:
                        prices[sym] = float(h["Close"].iloc[-1])
            except Exception:
                pass

        summary = get_tax_summary(prices)

        st.subheader("💰 Tax Summary")
        t1, t2, t3, t4 = st.columns(4)
        t1.metric("Total Unrealized Gain", f"${summary['total_unrealized']:,.2f}")
        t2.metric("Short-Term Gains (22%)", f"${summary['short_term_gains']:,.2f}",
                  help="Held < 1 year — taxed as ordinary income")
        t3.metric("Long-Term Gains (15%)", f"${summary['long_term_gains']:,.2f}",
                  help="Held ≥ 1 year — lower preferred tax rate")
        t4.metric("Total Estimated Tax", f"${summary['total_est_tax']:,.2f}",
                  delta=f"Save ${summary['tax_savings_if_lt']:,.2f} if all long-term",
                  delta_color="off")

        st.markdown("---")

        # ── Lots table ────────────────────────────────────────────────────────
        st.subheader("📋 All Tax Lots")
        enriched_lots = [enrich_lot(l, prices.get(l["symbol"], 0)) for l in lots]
        df_lots = pd.DataFrame(enriched_lots)

        display_cols = ["symbol", "shares", "cost_per_share", "cost_basis",
                        "current_value", "unrealized_gain", "gain_pct",
                        "days_held", "term", "tax_rate", "est_tax", "purchase_date"]
        df_display = df_lots[[c for c in display_cols if c in df_lots.columns]].copy()
        df_display.columns = ["Symbol", "Shares", "Cost/Share", "Cost Basis",
                               "Cur Value", "Gain $", "Gain %",
                               "Days Held", "Term", "Tax Rate", "Est Tax", "Purchase Date"]

        # Color-code by term
        def highlight_term(row):
            if "Long" in str(row.get("Term", "")):
                return ["background-color: rgba(46,204,113,0.08)"] * len(row)
            return ["background-color: rgba(231,76,60,0.08)"] * len(row)

        st.dataframe(
            df_display.style
                .format({
                    "Shares": "{:.4f}", "Cost/Share": "${:,.2f}",
                    "Cost Basis": "${:,.2f}", "Cur Value": "${:,.2f}",
                    "Gain $": "${:+,.2f}", "Gain %": "{:+.2f}%",
                    "Est Tax": "${:,.2f}",
                })
                .apply(highlight_term, axis=1),
            use_container_width=True,
        )

        # ── Days to long-term ─────────────────────────────────────────────────
        short_term = [l for l in enriched_lots if l["days_held"] < 365]
        if short_term:
            st.markdown("---")
            st.subheader("⏳ Short-Term Lots — Days Until Long-Term Status")
            st.caption("These lots qualify for the lower 15% long-term rate once held for 365 days.")
            for l in sorted(short_term, key=lambda x: x["days_to_lt"]):
                pct = (l["days_held"] / 365) * 100
                st.markdown(f"**{l['symbol']}** — {l['days_held']} days held, "
                            f"{l['days_to_lt']} days to go (bought {l['purchase_date']})")
                st.progress(min(pct / 100, 1.0))

        # ── Delete lot ────────────────────────────────────────────────────────
        st.markdown("---")
        st.subheader("🗑️ Remove a Lot")
        lot_options = {f"#{l['id']} — {l['symbol']} | {l['shares']} shares @ ${l['cost_per_share']} | {l['purchase_date']}": l["id"] for l in lots}
        del_choice  = st.selectbox("Select lot to remove", list(lot_options.keys()))
        if st.button("Remove Lot", type="secondary"):
            delete_lot(lot_options[del_choice])
            st.success("Lot removed.")
            st.rerun()

    else:
        st.info("No tax lots added yet. Add your first lot below.")

    # ── Add lot ───────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("➕ Add Tax Lot")
    st.caption("Add each purchase separately if you bought in multiple batches (dollar-cost averaging).")

    with st.form("add_lot_form"):
        col1, col2 = st.columns(2)
        lot_sym   = col1.text_input("Symbol", placeholder="AAPL").upper()
        lot_date  = col2.date_input("Purchase Date", value=__import__("datetime").date.today())
        col3, col4 = st.columns(2)
        lot_shares = col3.number_input("Shares Purchased", min_value=0.0001, value=1.0, format="%.4f")
        lot_cost   = col4.number_input("Cost Per Share ($)", min_value=0.01, value=100.0, format="%.2f")
        lot_note   = st.text_input("Note (optional)", placeholder="e.g. DCA buy, earnings dip purchase")
        add_lot_btn = st.form_submit_button("Add Lot", use_container_width=True, type="primary")

        if add_lot_btn and lot_sym:
            result = add_lot(lot_sym, lot_shares, lot_cost, str(lot_date), lot_note)
            st.success(
                f"✅ Added: {lot_shares} shares of {lot_sym} @ ${lot_cost:.2f} "
                f"on {lot_date} — Cost basis: ${result['cost_basis']:,.2f}"
            )
            st.rerun()

    # ── Sell recommendation ───────────────────────────────────────────────────
    if lots:
        st.markdown("---")
        st.subheader("💡 Tax-Efficient Sell Order")
        st.caption("When selling, consider selling long-term lots first to pay the lower 15% rate instead of 22%.")
        rec_sym = st.selectbox("Choose symbol to analyze", sorted({l["symbol"] for l in lots}))
        if rec_sym:
            prices_rec = {}
            try:
                import yfinance as yf
                t = yf.Ticker(rec_sym)
                h = t.history(period="2d")
                if not h.empty:
                    prices_rec[rec_sym] = float(h["Close"].iloc[-1])
            except Exception:
                pass
            recs = sell_recommendation(rec_sym, prices_rec.get(rec_sym, 0))
            if recs:
                st.markdown(f"**Recommended sell order for {rec_sym}** (most tax-efficient first):")
                for i, r in enumerate(recs, 1):
                    emoji = "✅" if r["days_held"] >= 365 else "⚠️"
                    st.markdown(
                        f"{i}. {emoji} **{r['shares']} shares** — "
                        f"Bought {r['purchase_date']} ({r['days_held']} days) — "
                        f"{r['term']} — Est tax if sold: **${r['est_tax']:,.2f}**"
                    )

# ═════════════════════════════════════════════════════════════════════════════
# PAGE: AI Insights (Claude API)
# ═════════════════════════════════════════════════════════════════════════════
elif page == "🧠 AI Insights":
    import json as _json
    from modules.portfolio import load_portfolio, get_enriched_portfolio

    st.title("🧠 AI Portfolio Insights")
    st.caption("Ask Claude anything about your portfolio in plain English. Powered by the Anthropic Claude API.")

    # ── API Key setup ─────────────────────────────────────────────────────────
    AI_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "data", "ai_config.json")

    def load_ai_config():
        if os.path.exists(AI_CONFIG_PATH):
            with open(AI_CONFIG_PATH) as f:
                return _json.load(f)
        return {}

    def save_ai_config(api_key):
        with open(AI_CONFIG_PATH, "w") as f:
            _json.dump({"anthropic_api_key": api_key}, f)

    ai_cfg = load_ai_config()
    api_key = ai_cfg.get("anthropic_api_key", "")

    with st.expander("🔑 Claude API Key", expanded=not api_key):
        st.markdown("""
        **How to get your Claude API key:**
        1. Go to [console.anthropic.com](https://console.anthropic.com)
        2. Sign in and click **API Keys** in the sidebar
        3. Click **Create Key** → copy the key (starts with `sk-ant-...`)
        4. Paste it below — stored locally only, never sent anywhere except Anthropic
        """)
        with st.form("ai_key_form"):
            new_key = st.text_input("Anthropic API Key", value=api_key,
                                    type="password", placeholder="sk-ant-api03-...")
            if st.form_submit_button("Save Key"):
                if new_key.strip():
                    save_ai_config(new_key.strip())
                    st.success("✅ API key saved!")
                    st.rerun()

    if not api_key:
        st.warning("Enter your Claude API key above to enable AI insights.")
        st.stop()

    # ── Build portfolio context for Claude ────────────────────────────────────
    def build_portfolio_context() -> str:
        try:
            raw      = load_portfolio()
            holdings = raw.get("holdings", [])
            if not holdings:
                return "Portfolio is empty."

            lines = ["PORTFOLIO HOLDINGS:"]
            total_cost = 0.0
            for h in holdings:
                sym    = h.get("symbol", "")
                shares = float(h.get("shares", 0))
                cost   = float(h.get("avg_cost", 0))
                cost_b = shares * cost
                total_cost += cost_b
                lines.append(f"  {sym}: {shares} shares @ avg ${cost:.2f} (cost basis ${cost_b:,.2f})")

            lines.append(f"\nTotal cost basis: ${total_cost:,.2f}")
            lines.append(f"Number of positions: {len(holdings)}")
            lines.append(f"Data as of: {str(__import__('datetime').date.today())}")
            return "\n".join(lines)
        except Exception as e:
            return f"Could not load portfolio: {e}"

    portfolio_context = build_portfolio_context()

    # ── Suggested questions ───────────────────────────────────────────────────
    st.subheader("💡 Try asking:")
    suggestions = [
        "What is my most concentrated position?",
        "Am I well diversified?",
        "Which position has the highest cost basis?",
        "What would a 10% market drop do to my portfolio?",
        "Give me 3 tips to improve my portfolio",
        "What sectors am I missing?",
    ]
    cols = st.columns(3)
    for i, suggestion in enumerate(suggestions):
        with cols[i % 3]:
            if st.button(suggestion, use_container_width=True, key=f"sug_{i}"):
                st.session_state["ai_question"] = suggestion

    st.markdown("---")

    # ── Chat interface ────────────────────────────────────────────────────────
    st.subheader("💬 Ask Claude")

    if "ai_chat_history" not in st.session_state:
        st.session_state["ai_chat_history"] = []

    # Show chat history
    for msg in st.session_state["ai_chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input
    default_q = st.session_state.pop("ai_question", "")
    question  = st.chat_input("Ask anything about your portfolio…")
    if not question and default_q:
        question = default_q

    if question:
        # Show user message
        st.session_state["ai_chat_history"].append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        # Call Claude API
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                try:
                    import anthropic
                    client = anthropic.Anthropic(api_key=api_key)

                    system_prompt = f"""You are a helpful financial assistant analyzing a personal investment portfolio.
You have access to the following portfolio data:

{portfolio_context}

Guidelines:
- Give specific, actionable insights based on the actual data
- Keep answers concise and clear — 2-4 short paragraphs maximum
- Use numbers from the portfolio where relevant
- Flag risks honestly but constructively
- You are NOT a licensed financial advisor — remind the user if they ask for specific buy/sell advice
- Focus on education and analysis, not predictions"""

                    messages = [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state["ai_chat_history"]
                    ]

                    response = client.messages.create(
                        model="claude-haiku-4-5-20251001",
                        max_tokens=1024,
                        system=system_prompt,
                        messages=messages,
                    )
                    answer = response.content[0].text
                    st.markdown(answer)
                    st.session_state["ai_chat_history"].append(
                        {"role": "assistant", "content": answer}
                    )

                except ImportError:
                    st.error("Install the Anthropic library: `pip install anthropic --break-system-packages`")
                except Exception as e:
                    err = str(e)
                    if "401" in err or "authentication" in err.lower():
                        st.error("Invalid API key. Check your key in the expander above.")
                    elif "429" in err:
                        st.error("Rate limit hit. Wait a moment and try again.")
                    else:
                        st.error(f"Error: {err}")

    # Clear chat button
    if st.session_state.get("ai_chat_history"):
        if st.button("🗑️ Clear Chat History", type="secondary"):
            st.session_state["ai_chat_history"] = []
            st.rerun()

    st.markdown("---")
    st.caption("🔒 Your portfolio data is sent to Anthropic's Claude API when you ask a question. "
               "Claude does not store your data. See [Anthropic's privacy policy](https://www.anthropic.com/privacy).")
