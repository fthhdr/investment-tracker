"""
auto_trader.py — Automated Buy/Sell Engine using Alpaca.
Set rules in the app and this module executes trades automatically.

Rule types:
  - price_drop:   Buy X shares if price drops below target
  - price_rise:   Sell X shares if price rises above target
  - pct_drop:     Buy if price drops by X% from a reference price
  - pct_rise:     Sell if price rises by X% from a reference price
"""

import json
import os
from datetime import datetime

BASE_DIR     = os.path.dirname(os.path.dirname(__file__))
CONFIG_PATH  = os.path.join(BASE_DIR, "data", "alpaca_config.json")
RULES_PATH   = os.path.join(BASE_DIR, "data", "auto_trade_rules.json")
LOG_PATH     = os.path.join(BASE_DIR, "data", "auto_trade_log.json")

# ── Alpaca connection ─────────────────────────────────────────────────────────
def get_api():
    """Return an authenticated Alpaca API client."""
    import alpaca_trade_api as tradeapi
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError("Alpaca config not found. Please set up your API keys.")
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    base_url = (
        "https://paper-api.alpaca.markets"
        if cfg.get("paper", True)
        else "https://api.alpaca.markets"
    )
    return tradeapi.REST(cfg["api_key"], cfg["secret_key"], base_url)


def get_trading_mode() -> bool:
    """Return True if paper trading, False if live trading."""
    if not os.path.exists(CONFIG_PATH):
        return True
    with open(CONFIG_PATH) as f:
        return json.load(f).get("paper", True)


def set_trading_mode(paper: bool) -> dict:
    """
    Switch between paper and live trading.
    Updates alpaca_config.json and returns the new config.
    """
    if not os.path.exists(CONFIG_PATH):
        return {"error": "Alpaca config not found. Set up API keys first."}
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    cfg["paper"] = paper
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    mode = "PAPER" if paper else "LIVE"
    return {"success": True, "mode": mode}


def get_account() -> dict:
    """Get Alpaca account info."""
    try:
        api    = get_api()
        acct   = api.get_account()
        is_paper = get_trading_mode()
        return {
            "cash":           float(acct.cash),
            "portfolio_value":float(acct.portfolio_value),
            "buying_power":   float(acct.buying_power),
            "equity":         float(acct.equity),
            "status":         acct.status,
            "paper":          is_paper,
        }
    except Exception as e:
        return {"error": str(e)}


def get_positions() -> list:
    """Get current Alpaca positions."""
    try:
        api       = get_api()
        positions = api.list_positions()
        return [{
            "symbol":    p.symbol,
            "qty":       float(p.qty),
            "avg_cost":  float(p.avg_entry_price),
            "cur_price": float(p.current_price),
            "mkt_value": float(p.market_value),
            "pnl":       float(p.unrealized_pl),
            "pnl_pct":   float(p.unrealized_plpc) * 100,
        } for p in positions]
    except Exception as e:
        return [{"error": str(e)}]


def place_order(symbol: str, qty: float, side: str, order_type: str = "market") -> dict:
    """
    Place a buy or sell order.
    side: "buy" or "sell"
    order_type: "market" or "limit"
    """
    try:
        api    = get_api()
        order  = api.submit_order(
            symbol        = symbol.upper(),
            qty           = qty,
            side          = side,
            type          = order_type,
            time_in_force = "day",
        )
        result = {
            "success":    True,
            "order_id":   order.id,
            "symbol":     order.symbol,
            "qty":        float(order.qty),
            "side":       order.side,
            "status":     order.status,
            "submitted":  str(datetime.now()),
        }
        _log_trade(result)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_current_price(symbol: str) -> float:
    """Get latest price for a symbol via Alpaca."""
    try:
        api   = get_api()
        bars  = api.get_latest_bar(symbol.upper())
        return float(bars.c)
    except Exception:
        try:
            import yfinance as yf
            t = yf.Ticker(symbol)
            h = t.history(period="1d")
            return float(h["Close"].iloc[-1]) if not h.empty else 0.0
        except Exception:
            return 0.0


# ── Rules engine ──────────────────────────────────────────────────────────────
def load_rules() -> list:
    if not os.path.exists(RULES_PATH):
        return []
    with open(RULES_PATH) as f:
        return json.load(f).get("rules", [])


def save_rules(rules: list):
    with open(RULES_PATH, "w") as f:
        json.dump({"rules": rules}, f, indent=2)


def add_rule(symbol: str, rule_type: str, trigger_value: float,
             qty: float, note: str = "") -> dict:
    """
    Add an auto-trade rule.
    rule_type options:
      "price_drop"  — buy if price <= trigger_value
      "price_rise"  — sell if price >= trigger_value
      "pct_drop"    — buy if price drops X% from current
      "pct_rise"    — sell if price rises X% from current
    """
    rules = load_rules()
    ref_price = get_current_price(symbol) if "pct" in rule_type else 0.0
    side  = "buy"  if "drop" in rule_type else "sell"
    rule  = {
        "id":            len(rules) + 1,
        "symbol":        symbol.upper(),
        "rule_type":     rule_type,
        "trigger_value": round(trigger_value, 4),
        "ref_price":     round(ref_price, 4),
        "qty":           round(qty, 6),
        "side":          side,
        "note":          note,
        "active":        True,
        "triggered":     False,
        "created":       str(datetime.now())[:10],
    }
    rules.append(rule)
    save_rules(rules)
    return rule


def delete_rule(rule_id: int):
    rules = [r for r in load_rules() if r.get("id") != rule_id]
    save_rules(rules)


def toggle_rule(rule_id: int):
    rules = load_rules()
    for r in rules:
        if r.get("id") == rule_id:
            r["active"] = not r.get("active", True)
    save_rules(rules)


def check_and_execute_rules() -> list:
    """
    Check all active rules against current prices.
    Execute trades when conditions are met.
    Returns list of executed trades.
    """
    rules    = load_rules()
    executed = []

    for rule in rules:
        if not rule.get("active", True) or rule.get("triggered", False):
            continue

        sym     = rule["symbol"]
        price   = get_current_price(sym)
        if price <= 0:
            continue

        rtype   = rule["rule_type"]
        trigger = rule["trigger_value"]
        ref     = rule.get("ref_price", price)

        # Evaluate condition
        hit = False
        if rtype == "price_drop" and price <= trigger:
            hit = True
        elif rtype == "price_rise" and price >= trigger:
            hit = True
        elif rtype == "pct_drop":
            drop_pct = (ref - price) / ref * 100
            hit = drop_pct >= trigger
        elif rtype == "pct_rise":
            rise_pct = (price - ref) / ref * 100
            hit = rise_pct >= trigger

        if hit:
            result = place_order(sym, rule["qty"], rule["side"])
            result["rule_id"]   = rule["id"]
            result["rule_type"] = rtype
            result["price"]     = price
            executed.append(result)
            # Mark as triggered so it doesn't repeat
            rule["triggered"]      = True
            rule["triggered_at"]   = str(datetime.now())
            rule["triggered_price"]= price

    save_rules(rules)
    return executed


# ── Trade log ─────────────────────────────────────────────────────────────────
def _log_trade(trade: dict):
    log = []
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH) as f:
            log = json.load(f).get("trades", [])
    log.append(trade)
    with open(LOG_PATH, "w") as f:
        json.dump({"trades": log}, f, indent=2)


def get_trade_log() -> list:
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH) as f:
        return json.load(f).get("trades", [])
