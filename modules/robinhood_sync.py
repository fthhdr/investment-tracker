"""
robinhood_sync.py — Robinhood account sync using direct API calls.

Bypasses robin_stocks entirely (which broke when Robinhood changed their
OAuth token_type format in 2025). Uses requests + Robinhood's REST API.

Auth flow:
  1. POST /oauth2/token/ with credentials → get access_token
  2. If MFA required, re-POST with mfa_code
  3. Use Bearer token for all subsequent requests
"""

import json
import os
import requests
from datetime import datetime, date

BASE_DIR       = os.path.dirname(os.path.dirname(__file__))
PORTFOLIO_PATH = os.path.join(BASE_DIR, "data", "portfolio.json")
RH_CACHE_PATH  = os.path.join(BASE_DIR, "data", "robinhood_cache.json")
SESSION_PATH   = os.path.join(BASE_DIR, "data", "rh_session.json")

# Robinhood API constants
RH_BASE        = "https://api.robinhood.com"
RH_CLIENT_ID   = "c82SH0WZOsabOXGP2sxqcj34FxkvfnWRZBKlBjFS"
RH_DEVICE_TOKEN = "fhoefhwof83hf"   # static device token (standard for 3rd-party clients)

HEADERS = {
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/x-www-form-urlencoded",
    "X-Robinhood-API-Version": "1.431.4",
    "Connection": "keep-alive",
    "User-Agent": "Robinhood/823 (iPhone; iOS 16.0; Scale/2.00)",
}

ROBIN_AVAILABLE = True
ROBIN_ERROR     = ""


# ── Session helpers ───────────────────────────────────────────────────────────
def _save_session(token_data: dict):
    os.makedirs(os.path.dirname(SESSION_PATH), exist_ok=True)
    with open(SESSION_PATH, "w") as f:
        json.dump({**token_data, "saved_at": str(datetime.now())}, f, indent=2)


def _load_session() -> dict:
    if os.path.exists(SESSION_PATH):
        with open(SESSION_PATH) as f:
            return json.load(f)
    return {}


def _auth_headers(token: str) -> dict:
    h = dict(HEADERS)
    h["Authorization"] = f"Bearer {token}"
    h["Content-Type"]  = "application/json"
    return h


def _get_token() -> str:
    """Return saved access token, or empty string if none."""
    session = _load_session()
    return session.get("access_token", "")


# ── Auth ─────────────────────────────────────────────────────────────────────
def login(username: str, password: str, mfa_code: str = "") -> dict:
    """
    Login to Robinhood via direct OAuth2 API call.
    Returns {"success": True} or {"success": False, "error": "..."}.
    If MFA is required, returns {"success": False, "error": "MFA_REQUIRED"}.
    """
    payload = {
        "client_id":     RH_CLIENT_ID,
        "expires_in":    "86400",
        "grant_type":    "password",
        "password":      password,
        "scope":         "internal",
        "username":      username,
        "challenge_type": "sms",
        "device_token":  RH_DEVICE_TOKEN,
    }
    if mfa_code:
        payload["mfa_code"] = mfa_code

    try:
        resp = requests.post(
            f"{RH_BASE}/oauth2/token/",
            data=payload,
            headers=HEADERS,
            timeout=15,
        )
        data = resp.json()

        # MFA required
        if data.get("mfa_required") or resp.status_code == 401 and "mfa" in str(data).lower():
            return {"success": False, "error": "MFA_REQUIRED"}

        # Challenge (device verification)
        if "challenge" in data:
            challenge_id = data["challenge"].get("id", "")
            return {"success": False, "error": f"DEVICE_CHALLENGE:{challenge_id}"}

        # Success — any of these fields mean we're logged in
        access_token = (
            data.get("access_token") or
            data.get("token") or
            data.get("oauth_token")
        )
        if access_token:
            _save_session(data)
            return {"success": True}

        # Unknown failure
        err = data.get("detail") or data.get("error") or str(data)
        return {"success": False, "error": err}

    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "No internet connection. Check your network."}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timed out. Try again."}
    except Exception as e:
        return {"success": False, "error": str(e)}


def logout():
    """Clear saved session."""
    if os.path.exists(SESSION_PATH):
        os.remove(SESSION_PATH)


def is_logged_in() -> bool:
    """Check if there's a saved access token."""
    return bool(_get_token())


# ── Account summary ───────────────────────────────────────────────────────────
def get_account_summary() -> dict:
    """Get portfolio value, buying power, and cash from Robinhood."""
    token = _get_token()
    if not token:
        return {"error": "Not logged in"}
    try:
        # Get account info
        acct_resp = requests.get(
            f"{RH_BASE}/accounts/",
            headers=_auth_headers(token),
            timeout=15,
        )
        acct_data = acct_resp.json()
        accounts  = acct_data.get("results", [acct_data])
        acct      = accounts[0] if accounts else {}

        # Get portfolio
        port_resp = requests.get(
            f"{RH_BASE}/portfolios/",
            headers=_auth_headers(token),
            timeout=15,
        )
        port_data = port_resp.json()
        port      = port_data.get("results", [port_data])
        port      = port[0] if port else {}

        return {
            "total_value":    float(port.get("equity", 0)              or 0),
            "buying_power":   float(acct.get("buying_power", 0)        or 0),
            "cash":           float(acct.get("cash", 0)                or 0),
            "market_value":   float(port.get("market_value", 0)        or 0),
            "total_return":   float(port.get("adjusted_equity_previous_close", 0) or 0),
            "percent_return": float(port.get("total_return_percent", 0) or 0),
        }
    except Exception as e:
        return {"error": str(e)}


# ── Positions ─────────────────────────────────────────────────────────────────
def _resolve_instrument(instrument_url: str, token: str) -> dict:
    """Fetch instrument details (symbol, name) from Robinhood."""
    try:
        resp = requests.get(instrument_url, headers=_auth_headers(token), timeout=10)
        return resp.json()
    except Exception:
        return {}


def _get_quote(symbol: str, token: str) -> float:
    """Fetch latest price for a stock symbol."""
    try:
        resp = requests.get(
            f"{RH_BASE}/quotes/{symbol}/",
            headers=_auth_headers(token),
            timeout=10,
        )
        data = resp.json()
        return float(data.get("last_trade_price") or data.get("last_extended_hours_trade_price") or 0)
    except Exception:
        return 0.0


def fetch_robinhood_positions() -> list:
    """Get all open stock positions with live prices and P&L."""
    token = _get_token()
    if not token:
        return [{"error": "Not logged in"}]
    try:
        resp = requests.get(
            f"{RH_BASE}/positions/?nonzero=true",
            headers=_auth_headers(token),
            timeout=15,
        )
        positions = resp.json().get("results", [])
        result = []
        for p in positions:
            try:
                quantity = float(p.get("quantity", 0) or 0)
                if quantity <= 0:
                    continue
                instrument = _resolve_instrument(p["instrument"], token)
                symbol     = instrument.get("symbol", "UNKNOWN")
                name       = instrument.get("simple_name") or instrument.get("name", symbol)
                avg_cost   = float(p.get("average_buy_price", 0) or 0)
                cur_price  = _get_quote(symbol, token)
                mkt_value  = quantity * cur_price
                cost_basis = quantity * avg_cost
                pnl        = mkt_value - cost_basis
                pnl_pct    = (pnl / cost_basis * 100) if cost_basis else 0

                result.append({
                    "symbol":     symbol,
                    "name":       name,
                    "shares":     round(quantity, 6),
                    "avg_cost":   round(avg_cost, 4),
                    "cur_price":  round(cur_price, 4),
                    "mkt_value":  round(mkt_value, 2),
                    "cost_basis": round(cost_basis, 2),
                    "pnl":        round(pnl, 2),
                    "pnl_pct":    round(pnl_pct, 2),
                    "type":       "stock",
                })
            except Exception:
                continue
        return result
    except Exception as e:
        return [{"error": str(e)}]


def fetch_robinhood_crypto() -> list:
    """Get all open crypto positions from Robinhood."""
    token = _get_token()
    if not token:
        return [{"error": "Not logged in"}]
    try:
        resp = requests.get(
            f"{RH_BASE}/nummus/positions/?nonzero=true",
            headers=_auth_headers(token),
            timeout=15,
        )
        # nummus is Robinhood's crypto endpoint — may redirect
        if resp.status_code == 404:
            resp = requests.get(
                f"{RH_BASE}/crypto/portfolios/",
                headers=_auth_headers(token),
                timeout=15,
            )
        positions = resp.json().get("results", [])
        result = []
        for p in positions:
            try:
                currency  = p.get("currency", {})
                symbol    = currency.get("code", "")
                name      = currency.get("name", symbol)
                quantity  = float(p.get("quantity", 0) or 0)
                if quantity <= 0:
                    continue
                cost_bases = p.get("cost_bases", [{}])
                cb_total   = float((cost_bases[0].get("direct_cost_basis") or 0)) if cost_bases else 0
                avg_cost   = cb_total / quantity if quantity else 0

                # Crypto quote
                quote_resp = requests.get(
                    f"{RH_BASE}/marketdata/forex/quotes/{symbol}USD/",
                    headers=_auth_headers(token),
                    timeout=10,
                )
                quote_data = quote_resp.json()
                cur_price  = float(quote_data.get("mark_price") or quote_data.get("bid_price") or 0)

                mkt_value  = quantity * cur_price
                cost_basis = quantity * avg_cost
                pnl        = mkt_value - cost_basis
                pnl_pct    = (pnl / cost_basis * 100) if cost_basis else 0

                result.append({
                    "symbol":     symbol,
                    "name":       name,
                    "shares":     round(quantity, 8),
                    "avg_cost":   round(avg_cost, 4),
                    "cur_price":  round(cur_price, 4),
                    "mkt_value":  round(mkt_value, 2),
                    "cost_basis": round(cost_basis, 2),
                    "pnl":        round(pnl, 2),
                    "pnl_pct":    round(pnl_pct, 2),
                    "type":       "crypto",
                })
            except Exception:
                continue
        return result
    except Exception as e:
        return [{"error": str(e)}]


# ── Recent orders ─────────────────────────────────────────────────────────────
def fetch_robinhood_recent_orders(limit: int = 20) -> list:
    """Get recent stock orders from Robinhood."""
    token = _get_token()
    if not token:
        return [{"error": "Not logged in"}]
    try:
        resp   = requests.get(
            f"{RH_BASE}/orders/",
            headers=_auth_headers(token),
            timeout=15,
        )
        orders = resp.json().get("results", [])
        result = []
        for o in orders[:limit]:
            try:
                instrument = _resolve_instrument(o["instrument"], token)
                symbol     = instrument.get("symbol", "")
                result.append({
                    "symbol":   symbol,
                    "side":     o.get("side", ""),
                    "quantity": float(o.get("quantity", 0) or 0),
                    "price":    float(o.get("average_price", 0) or 0),
                    "state":    o.get("state", ""),
                    "date":     (o.get("last_transaction_at", "") or "")[:10],
                })
            except Exception:
                continue
        return result
    except Exception as e:
        return [{"error": str(e)}]


# ── Sync to portfolio.json ────────────────────────────────────────────────────
def sync_positions_to_portfolio(overwrite: bool = False) -> dict:
    """
    Merge Robinhood stock + crypto positions into portfolio.json.
    overwrite=True replaces all holdings; False merges/updates existing.
    """
    positions = fetch_robinhood_positions()
    crypto    = fetch_robinhood_crypto()
    all_pos   = [p for p in (positions + crypto) if "error" not in p]

    if not all_pos:
        err = (positions + crypto)[0].get("error", "No positions found") if (positions + crypto) else "No positions found"
        return {"error": err}

    if os.path.exists(PORTFOLIO_PATH):
        with open(PORTFOLIO_PATH) as f:
            portfolio = json.load(f)
    else:
        portfolio = {"holdings": []}

    holdings        = [] if overwrite else portfolio.get("holdings", [])
    added, updated  = [], []

    for pos in all_pos:
        sym      = pos["symbol"]
        existing = next((h for h in holdings if h.get("symbol") == sym), None)
        if existing:
            existing["shares"]   = pos["shares"]
            existing["avg_cost"] = pos["avg_cost"]
            existing["source"]   = "robinhood"
            existing["synced"]   = str(date.today())
            updated.append(sym)
        else:
            holdings.append({
                "symbol":   sym,
                "name":     pos["name"],
                "shares":   pos["shares"],
                "avg_cost": pos["avg_cost"],
                "type":     pos.get("type", "stock"),
                "source":   "robinhood",
                "synced":   str(date.today()),
            })
            added.append(sym)

    portfolio["holdings"]    = holdings
    portfolio["last_synced"] = str(datetime.now())

    with open(PORTFOLIO_PATH, "w") as f:
        json.dump(portfolio, f, indent=2)

    # Save raw cache for debugging
    with open(RH_CACHE_PATH, "w") as f:
        json.dump({"positions": all_pos, "synced": str(datetime.now())}, f, indent=2)

    return {"added": added, "updated": updated, "total": len(holdings)}
