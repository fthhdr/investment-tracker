"""
price_alerts.py — Price alert system with Stop-Loss & Take-Profit support.
alert_type options:
  "price_alert" — general price target (above or below)
  "stop_loss"   — sell signal when price drops BELOW target (protects from big losses)
  "take_profit" — sell signal when price rises ABOVE target (locks in gains)
"""

import json
import os
from datetime import date

BASE_DIR    = os.path.dirname(os.path.dirname(__file__))
ALERTS_PATH = os.path.join(BASE_DIR, "data", "price_alerts.json")


def load_alerts() -> list:
    if not os.path.exists(ALERTS_PATH):
        return []
    with open(ALERTS_PATH) as f:
        return json.load(f).get("alerts", [])


def save_alerts(alerts: list):
    with open(ALERTS_PATH, "w") as f:
        json.dump({"alerts": alerts}, f, indent=2)


def add_alert(symbol: str, name: str, condition: str,
              target_price: float, note: str = "",
              alert_type: str = "price_alert",
              entry_price: float = 0.0,
              shares: float = 0.0) -> dict:
    """
    Add a new alert.
    alert_type: "price_alert" | "stop_loss" | "take_profit"
    entry_price / shares: used for stop-loss and take-profit P&L calculations.
    condition is auto-set for stop_loss ("below") and take_profit ("above").
    """
    if alert_type == "stop_loss":
        condition = "below"
    elif alert_type == "take_profit":
        condition = "above"

    alerts = load_alerts()
    new_alert = {
        "symbol":       symbol.upper(),
        "name":         name,
        "condition":    condition,
        "target_price": round(target_price, 2),
        "alert_type":   alert_type,
        "entry_price":  round(entry_price, 2),
        "shares":       round(shares, 6),
        "note":         note,
        "active":       True,
        "created":      str(date.today()),
    }
    alerts.append(new_alert)
    save_alerts(alerts)
    return new_alert


def delete_alert(symbol: str, condition: str, target_price: float):
    """Remove a specific alert."""
    alerts = load_alerts()
    alerts = [
        a for a in alerts
        if not (a["symbol"] == symbol.upper()
                and a["condition"] == condition
                and abs(a["target_price"] - target_price) < 0.01)
    ]
    save_alerts(alerts)


def delete_alert_by_index(index: int):
    """Remove an alert by its list index."""
    alerts = load_alerts()
    if 0 <= index < len(alerts):
        alerts.pop(index)
    save_alerts(alerts)


def toggle_alert(symbol: str, condition: str, target_price: float):
    """Enable or disable an alert without deleting it."""
    alerts = load_alerts()
    for a in alerts:
        if (a["symbol"] == symbol.upper()
                and a["condition"] == condition
                and abs(a["target_price"] - target_price) < 0.01):
            a["active"] = not a["active"]
    save_alerts(alerts)


def toggle_alert_by_index(index: int):
    """Toggle active state by list index."""
    alerts = load_alerts()
    if 0 <= index < len(alerts):
        alerts[index]["active"] = not alerts[index].get("active", True)
    save_alerts(alerts)


def check_alerts(prices: dict) -> list:
    """
    Check all active alerts against current prices.
    prices: {symbol: current_price}
    Returns list of triggered alerts.
    """
    alerts    = load_alerts()
    triggered = []
    for a in alerts:
        if not a.get("active", True):
            continue
        sym   = a["symbol"]
        price = prices.get(sym)
        if price is None:
            continue
        cond   = a["condition"]
        target = a["target_price"]
        hit    = (cond == "above" and price >= target) or \
                 (cond == "below" and price <= target)
        if hit:
            enriched = dict(a)
            enriched["current_price"] = price
            enriched["triggered"]     = True
            # Calculate P&L if we have entry info
            entry  = a.get("entry_price", 0)
            shares = a.get("shares", 0)
            if entry > 0 and shares > 0:
                enriched["pnl_per_share"] = round(price - entry, 2)
                enriched["total_pnl"]     = round((price - entry) * shares, 2)
                enriched["pnl_pct"]       = round((price - entry) / entry * 100, 2)
            triggered.append(enriched)
    return triggered


def get_alert_summary(prices: dict) -> dict:
    """Returns counts and triggered list for dashboard display."""
    alerts    = load_alerts()
    active    = [a for a in alerts if a.get("active", True)]
    triggered = check_alerts(prices)
    by_type   = {
        "price_alert": [a for a in alerts if a.get("alert_type", "price_alert") == "price_alert"],
        "stop_loss":   [a for a in alerts if a.get("alert_type") == "stop_loss"],
        "take_profit": [a for a in alerts if a.get("alert_type") == "take_profit"],
    }
    return {
        "total":         len(alerts),
        "active":        len(active),
        "triggered":     triggered,
        "trigger_count": len(triggered),
        "by_type":       by_type,
    }
