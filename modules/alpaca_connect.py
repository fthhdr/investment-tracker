"""
alpaca_connect.py — Connects your investment tracker to Alpaca Paper Trading.
Fetches real-time account info, positions, and order history from Alpaca.
"""

import os
import json
from datetime import datetime, timedelta

# ── Try importing alpaca-py ────────────────────────────────────────────────────
try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest, GetOrdersRequest
    from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
    from alpaca.data.timeframe import TimeFrame
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False

# ── Config file path ───────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "data", "alpaca_config.json")


# ══════════════════════════════════════════════════════════════════════════════
# CONFIG MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

def load_config() -> dict:
    """Load saved Alpaca API keys from file."""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {"api_key": "", "secret_key": "", "paper": True}


def save_config(api_key: str, secret_key: str, paper: bool = True):
    """Save Alpaca API keys to config file."""
    config = {"api_key": api_key, "secret_key": secret_key, "paper": paper}
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def is_configured() -> bool:
    """Check if API keys are saved and non-empty."""
    config = load_config()
    return bool(config.get("api_key") and config.get("secret_key"))


# ══════════════════════════════════════════════════════════════════════════════
# CLIENT FACTORY
# ══════════════════════════════════════════════════════════════════════════════

def get_trading_client() -> "TradingClient | None":
    """Return an authenticated TradingClient, or None if not configured."""
    if not ALPACA_AVAILABLE:
        return None
    config = load_config()
    if not config.get("api_key"):
        return None
    return TradingClient(
        api_key=config["api_key"],
        secret_key=config["secret_key"],
        paper=config.get("paper", True),
    )


def get_data_client() -> "StockHistoricalDataClient | None":
    """Return an authenticated data client for market quotes/bars."""
    if not ALPACA_AVAILABLE:
        return None
    config = load_config()
    if not config.get("api_key"):
        return None
    return StockHistoricalDataClient(
        api_key=config["api_key"],
        secret_key=config["secret_key"],
    )


# ══════════════════════════════════════════════════════════════════════════════
# ACCOUNT INFO
# ══════════════════════════════════════════════════════════════════════════════

def get_account_summary() -> dict:
    """
    Returns key account metrics from Alpaca.
    Example return:
    {
        "portfolio_value": 200000.00,
        "cash": 195000.00,
        "buying_power": 380000.00,
        "equity": 200000.00,
        "day_pnl": 250.00,
        "day_pnl_pct": 0.125,
        "status": "ACTIVE"
    }
    """
    client = get_trading_client()
    if client is None:
        return {"error": "Not connected. Enter your API keys in the Settings tab."}

    try:
        acct = client.get_account()
        portfolio_value = float(acct.portfolio_value)
        last_equity     = float(acct.last_equity)
        day_pnl         = portfolio_value - last_equity
        day_pnl_pct     = (day_pnl / last_equity * 100) if last_equity else 0

        return {
            "portfolio_value": portfolio_value,
            "cash":            float(acct.cash),
            "buying_power":    float(acct.buying_power),
            "equity":          float(acct.equity),
            "day_pnl":         day_pnl,
            "day_pnl_pct":     day_pnl_pct,
            "status":          str(acct.status),
            "account_number":  acct.account_number,
            "paper":           load_config().get("paper", True),
        }
    except Exception as e:
        return {"error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# POSITIONS
# ══════════════════════════════════════════════════════════════════════════════

def get_alpaca_positions() -> list:
    """
    Returns all open positions from Alpaca as a list of dicts.
    Each dict has: symbol, qty, avg_entry_price, current_price,
                   market_value, unrealized_pl, unrealized_plpc, side
    """
    client = get_trading_client()
    if client is None:
        return []

    try:
        positions = client.get_all_positions()
        result = []
        for p in positions:
            result.append({
                "symbol":            p.symbol,
                "qty":               float(p.qty),
                "avg_entry_price":   float(p.avg_entry_price),
                "current_price":     float(p.current_price),
                "market_value":      float(p.market_value),
                "unrealized_pl":     float(p.unrealized_pl),
                "unrealized_plpc":   float(p.unrealized_plpc) * 100,  # convert to %
                "side":              str(p.side),
            })
        return result
    except Exception as e:
        return [{"error": str(e)}]


# ══════════════════════════════════════════════════════════════════════════════
# ORDER HISTORY
# ══════════════════════════════════════════════════════════════════════════════

def get_recent_orders(limit: int = 20) -> list:
    """
    Returns the most recent closed/filled orders from Alpaca.
    """
    client = get_trading_client()
    if client is None:
        return []

    try:
        req = GetOrdersRequest(
            status=QueryOrderStatus.CLOSED,
            limit=limit,
            nested=False,
        )
        orders = client.get_orders(filter=req)
        result = []
        for o in orders:
            filled_qty   = float(o.filled_qty) if o.filled_qty else 0
            filled_price = float(o.filled_avg_price) if o.filled_avg_price else 0
            result.append({
                "id":          str(o.id),
                "symbol":      o.symbol,
                "side":        str(o.side),
                "qty":         float(o.qty) if o.qty else 0,
                "filled_qty":  filled_qty,
                "filled_price": filled_price,
                "total":       filled_qty * filled_price,
                "status":      str(o.status),
                "submitted_at": str(o.submitted_at)[:19] if o.submitted_at else "",
                "filled_at":   str(o.filled_at)[:19] if o.filled_at else "",
                "type":        str(o.order_type),
            })
        return result
    except Exception as e:
        return [{"error": str(e)}]


# ══════════════════════════════════════════════════════════════════════════════
# PLACE ORDER (paper trading)
# ══════════════════════════════════════════════════════════════════════════════

def place_market_order(symbol: str, qty: float, side: str = "buy") -> dict:
    """
    Place a paper market order.
    side: "buy" or "sell"
    Returns order confirmation dict or error dict.
    """
    client = get_trading_client()
    if client is None:
        return {"error": "Not connected."}

    try:
        order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        req = MarketOrderRequest(
            symbol=symbol.upper(),
            qty=qty,
            side=order_side,
            time_in_force=TimeInForce.DAY,
        )
        order = client.submit_order(order_data=req)
        return {
            "success": True,
            "order_id": str(order.id),
            "symbol":   order.symbol,
            "qty":      float(order.qty),
            "side":     str(order.side),
            "status":   str(order.status),
        }
    except Exception as e:
        return {"error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# LIVE QUOTE
# ══════════════════════════════════════════════════════════════════════════════

def get_live_quote(symbol: str) -> dict:
    """
    Get the latest bid/ask quote for a stock symbol.
    """
    client = get_data_client()
    if client is None:
        return {}

    try:
        req    = StockLatestQuoteRequest(symbol_or_symbols=symbol.upper())
        quotes = client.get_stock_latest_quote(req)
        q      = quotes[symbol.upper()]
        return {
            "symbol":    symbol.upper(),
            "bid":       float(q.bid_price),
            "ask":       float(q.ask_price),
            "mid":       (float(q.bid_price) + float(q.ask_price)) / 2,
            "timestamp": str(q.timestamp)[:19],
        }
    except Exception as e:
        return {"error": str(e)}
