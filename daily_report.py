"""
daily_report.py — Morning daily report sent to your iPhone via ntfy.sh
Runs automatically every day at 8am (set up via LaunchAgent).

Sends:
  - Portfolio total value & daily change
  - Top holdings with P&L
  - Market overview (S&P 500, NASDAQ, DOW)
  - Any active price alerts summary
  - Motivational reminder
"""

import json
import os
import sys
import urllib.request
import base64
from datetime import datetime, date

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH  = os.path.join(BASE_DIR, "data", "monitor_config.json")
PORTFOLIO_PATH = os.path.join(BASE_DIR, "data", "portfolio.json")
ALERTS_PATH  = os.path.join(BASE_DIR, "data", "price_alerts.json")
NTFY_SERVER  = "https://ntfy.sh"


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}


def load_portfolio() -> list:
    if not os.path.exists(PORTFOLIO_PATH):
        return []
    with open(PORTFOLIO_PATH) as f:
        return json.load(f).get("holdings", [])


def load_alerts() -> list:
    if not os.path.exists(ALERTS_PATH):
        return []
    with open(ALERTS_PATH) as f:
        return json.load(f).get("alerts", [])


def get_price(symbol: str) -> float:
    """Fetch live price using yfinance."""
    try:
        import yfinance as yf
        t = yf.Ticker(symbol)
        h = t.history(period="2d")
        if not h.empty:
            return float(h["Close"].iloc[-1])
    except Exception:
        pass
    return 0.0


def get_day_change(symbol: str) -> tuple:
    """Returns (current_price, prev_close, change_pct)."""
    try:
        import yfinance as yf
        t = yf.Ticker(symbol)
        h = t.history(period="2d")
        if len(h) >= 2:
            cur  = float(h["Close"].iloc[-1])
            prev = float(h["Close"].iloc[-2])
            pct  = (cur - prev) / prev * 100
            return cur, prev, pct
    except Exception:
        pass
    return 0.0, 0.0, 0.0


def _encode_header(value: str) -> str:
    try:
        value.encode("latin-1")
        return value
    except UnicodeEncodeError:
        encoded = base64.b64encode(value.encode("utf-8")).decode("ascii")
        return f"=?utf-8?b?{encoded}?="


def send_notification(topic: str, title: str, message: str,
                      priority: str = "default", tags: str = "bell"):
    url  = f"{NTFY_SERVER}/{topic}"
    data = message.encode("utf-8")
    req  = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Title",        _encode_header(title))
    req.add_header("Priority",     priority)
    req.add_header("Tags",         tags)
    req.add_header("Content-Type", "text/plain; charset=utf-8")
    try:
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        print(f"Notification failed: {e}")
        return False


def build_report() -> tuple:
    """Build the daily report. Returns (title, message)."""
    today     = date.today().strftime("%A, %b %d")
    now_hour  = datetime.now().hour
    greeting  = "Good morning" if now_hour < 12 else ("Good afternoon" if now_hour < 17 else "Good evening")

    lines = [f"{greeting}, Royan! Here's your daily briefing for {today}.\n"]

    # ── Market overview ───────────────────────────────────────────────────────
    lines.append("📊 MARKETS TODAY")
    indices = {
        "S&P 500": "^GSPC",
        "NASDAQ":  "^IXIC",
        "DOW":     "^DJI",
    }
    for name, sym in indices.items():
        cur, prev, pct = get_day_change(sym)
        if cur > 0:
            arrow = "▲" if pct >= 0 else "▼"
            lines.append(f"  {arrow} {name}: {pct:+.2f}%")

    # ── Portfolio summary ─────────────────────────────────────────────────────
    holdings = load_portfolio()
    lines.append("\n💼 YOUR PORTFOLIO")
    total_value  = 0.0
    total_cost   = 0.0
    holding_lines = []

    for h in holdings:
        sym    = h.get("symbol", "")
        shares = float(h.get("shares", 0))
        cost   = float(h.get("avg_cost", 0))
        if shares <= 0 or not sym:
            continue
        price = get_price(sym)
        if price <= 0:
            continue
        mkt_val    = price * shares
        cost_basis = cost * shares
        pnl        = mkt_val - cost_basis
        pnl_pct    = (pnl / cost_basis * 100) if cost_basis else 0
        total_value += mkt_val
        total_cost  += cost_basis
        arrow = "▲" if pnl >= 0 else "▼"
        holding_lines.append(
            f"  {arrow} {sym}: ${mkt_val:,.2f} ({pnl_pct:+.1f}%)"
        )

    total_pnl     = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0
    arrow_total   = "▲" if total_pnl >= 0 else "▼"
    lines.append(f"  Total: ${total_value:,.2f} {arrow_total} ({total_pnl_pct:+.1f}%)")
    lines.extend(holding_lines[:5])  # show top 5

    # ── Active alerts ─────────────────────────────────────────────────────────
    alerts = [a for a in load_alerts() if a.get("active", True)]
    if alerts:
        lines.append(f"\n🔔 ACTIVE ALERTS: {len(alerts)}")
        for a in alerts[:3]:
            lines.append(f"  {a['symbol']} {a['condition']} ${a['target_price']:,.2f}")

    # ── Motivational close ────────────────────────────────────────────────────
    lines.append("\n💪 Stay disciplined. Stick to your plan. Make today count!")

    title   = f"📈 Daily Briefing — {today}"
    message = "\n".join(lines)
    return title, message


def main():
    cfg   = load_config()
    topic = cfg.get("ntfy_topic", "")

    if not topic:
        print("No ntfy topic configured. Run alert_monitor.py first to set it up.")
        sys.exit(1)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Building daily report…")
    title, message = build_report()

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sending to {topic}…")
    success = send_notification(topic, title, message, priority="default", tags="sunrise")

    if success:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Daily report sent successfully!")
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Failed to send report.")


if __name__ == "__main__":
    main()
