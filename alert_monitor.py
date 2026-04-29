"""
alert_monitor.py — Background alert monitor with push notifications.
Checks your price alerts every 5 minutes and sends a push notification
to your phone when a stop-loss or take-profit is triggered.

Uses ntfy.sh — completely free, no account needed.

HOW TO USE:
1. On your iPhone, go to: https://ntfy.sh
2. Download the ntfy app from the App Store (free)
3. Subscribe to your personal topic: investment-tracker-YOURNAME
   (e.g. investment-tracker-tinkam)
4. Run this script on your Mac:
   python3 alert_monitor.py

Notifications will appear on your phone automatically!
"""

import time
import json
import os
import sys
import base64
import urllib.request
import urllib.parse
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
ALERTS_PATH   = os.path.join(BASE_DIR, "data", "price_alerts.json")
CONFIG_PATH   = os.path.join(BASE_DIR, "data", "monitor_config.json")
CHECK_INTERVAL = 300   # seconds (5 minutes)
NTFY_SERVER   = "https://ntfy.sh"


def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}


def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def load_alerts():
    if not os.path.exists(ALERTS_PATH):
        return []
    with open(ALERTS_PATH) as f:
        return json.load(f).get("alerts", [])


def get_price(symbol: str) -> float:
    """Fetch live price using yfinance."""
    try:
        import yfinance as yf
        t = yf.Ticker(symbol)
        h = t.history(period="1d")
        if not h.empty:
            return float(h["Close"].iloc[-1])
    except Exception:
        pass
    return 0.0


def _encode_header(value: str) -> str:
    """Encode header value using RFC 2047 base64 if it contains non-ASCII chars."""
    try:
        value.encode("latin-1")
        return value
    except UnicodeEncodeError:
        encoded = base64.b64encode(value.encode("utf-8")).decode("ascii")
        return f"=?utf-8?b?{encoded}?="


def send_notification(topic: str, title: str, message: str, priority: str = "high", tags: str = "bell"):
    """Send push notification via ntfy.sh."""
    url = f"{NTFY_SERVER}/{topic}"
    data = message.encode("utf-8")
    req  = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Title",    _encode_header(title))
    req.add_header("Priority", priority)
    req.add_header("Tags",     tags)
    req.add_header("Content-Type", "text/plain; charset=utf-8")
    try:
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        print(f"  ⚠️  Notification failed: {e}")
        return False


def check_and_notify(topic: str, already_triggered: set) -> set:
    alerts = load_alerts()
    active = [a for a in alerts if a.get("active", True)]
    newly_triggered = set()

    for a in active:
        sym    = a["symbol"]
        cond   = a["condition"]
        target = a["target_price"]
        atype  = a.get("alert_type", "price_alert")
        key    = f"{sym}_{cond}_{target}"

        price = get_price(sym)
        if price <= 0:
            continue

        hit = (cond == "above" and price >= target) or \
              (cond == "below" and price <= target)

        if hit and key not in already_triggered:
            newly_triggered.add(key)
            entry  = a.get("entry_price", 0)
            shares = a.get("shares", 0)

            if atype == "stop_loss":
                pnl = (price - entry) * shares if entry > 0 and shares > 0 else 0
                title   = f"🛑 STOP-LOSS HIT — {sym}"
                message = (
                    f"{sym} dropped to ${price:,.2f} — below your stop of ${target:,.2f}\n"
                    f"{'Loss: $'+f'{pnl:,.2f}' if pnl else ''}\n"
                    f"ACTION: Sell {sym} immediately to limit your loss!"
                )
                send_notification(topic, title, message, priority="urgent", tags="rotating_light,chart_with_downwards_trend")
                print(f"  🛑 STOP-LOSS NOTIFICATION SENT: {sym} @ ${price:.2f}")

            elif atype == "take_profit":
                pnl = (price - entry) * shares if entry > 0 and shares > 0 else 0
                title   = f"🎯 TAKE-PROFIT HIT — {sym}"
                message = (
                    f"{sym} reached ${price:,.2f} — above your target of ${target:,.2f}\n"
                    f"{'Profit: $'+f'{pnl:,.2f}' if pnl else ''}\n"
                    f"ACTION: Consider selling {sym} to lock in your gains!"
                )
                send_notification(topic, title, message, priority="high", tags="tada,chart_with_upwards_trend")
                print(f"  🎯 TAKE-PROFIT NOTIFICATION SENT: {sym} @ ${price:.2f}")

            else:
                arrow   = "📈" if cond == "above" else "📉"
                title   = f"{arrow} Price Alert — {sym}"
                message = (
                    f"{sym} is at ${price:,.2f}\n"
                    f"Your alert: {cond} ${target:,.2f}\n"
                    f"Note: {a.get('note', '')}"
                )
                send_notification(topic, title, message, priority="default", tags="bell")
                print(f"  🔔 PRICE ALERT SENT: {sym} @ ${price:.2f}")

    return already_triggered | newly_triggered


def setup():
    print("\n" + "="*55)
    print("  📱 INVESTMENT TRACKER — PUSH NOTIFICATION MONITOR")
    print("="*55)

    cfg = load_config()
    topic = cfg.get("ntfy_topic", "")

    if not topic:
        print("\nFirst-time setup:")
        print("1. Download the ntfy app from the App Store on your iPhone")
        print("2. Choose a unique topic name (e.g. invest-tinkam-2026)")
        print("3. In the ntfy app, tap + and subscribe to that topic name")
        print()
        topic = input("Enter your ntfy topic name: ").strip()
        if not topic:
            print("No topic entered. Exiting.")
            sys.exit(1)
        cfg["ntfy_topic"] = topic
        save_config(cfg)
        print(f"\n✅ Topic saved: {topic}")

    print(f"\n📡 Monitoring alerts → notifications sent to topic: {topic}")
    print(f"⏱  Checking every {CHECK_INTERVAL // 60} minutes")
    print(f"📱 Make sure you subscribed to '{topic}' in the ntfy app")
    print("\nPress Ctrl+C to stop.\n")
    return topic


def main():
    topic = setup()
    already_triggered = set()

    # Send a startup notification
    send_notification(
        topic,
        "✅ Alert Monitor Started",
        f"Investment Tracker is now watching your alerts.\nChecking every {CHECK_INTERVAL//60} minutes.",
        priority="low",
        tags="white_check_mark",
    )

    while True:
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] Checking {len(load_alerts())} alerts…")
        try:
            already_triggered = check_and_notify(topic, already_triggered)
            print(f"[{now}] Done. Next check in {CHECK_INTERVAL//60} min.")
        except Exception as e:
            print(f"[{now}] Error: {e}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
