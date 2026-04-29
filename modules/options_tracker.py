"""
options_tracker.py — Options Position Tracker
Stores real options contracts you hold (or are tracking).
Calculates live P&L using Black-Scholes, shows all Greeks.
"""

import json
import os
from datetime import date, datetime
from math import log, sqrt, exp

BASE_DIR      = os.path.dirname(os.path.dirname(__file__))
OPTIONS_PATH  = os.path.join(BASE_DIR, "data", "options_positions.json")

RISK_FREE_RATE = 0.053   # ~5.3% (current T-bill rate)


# ══════════════════════════════════════════════════════════════════════════════
# BLACK-SCHOLES ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def _norm_cdf(x: float) -> float:
    """Approximate normal CDF using Abramowitz & Stegun."""
    k = 1.0 / (1.0 + 0.2316419 * abs(x))
    poly = k * (0.319381530
              + k * (-0.356563782
              + k * (1.781477937
              + k * (-1.821255978
              + k * 1.330274429))))
    approx = 1.0 - (1.0 / sqrt(2 * 3.14159265358979323846)) * exp(-0.5 * x * x) * poly
    return approx if x >= 0 else 1.0 - approx


def _norm_pdf(x: float) -> float:
    return (1.0 / sqrt(2 * 3.14159265358979323846)) * exp(-0.5 * x * x)


def black_scholes_full(S: float, K: float, T: float,
                       r: float, sigma: float,
                       option_type: str = "call") -> dict:
    """
    Full Black-Scholes calculation.
    S     = current stock price
    K     = strike price
    T     = time to expiry in YEARS
    r     = risk-free rate
    sigma = implied volatility (e.g. 0.30 for 30%)
    Returns price + all 5 Greeks.
    """
    if T <= 0:
        # At or past expiration — intrinsic value only
        if option_type == "call":
            price = max(S - K, 0)
        else:
            price = max(K - S, 0)
        return {"price": round(price, 4), "delta": 0, "gamma": 0,
                "theta": 0, "vega": 0, "rho": 0}

    d1 = (log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt(T))
    d2 = d1 - sigma * sqrt(T)

    if option_type == "call":
        price = S * _norm_cdf(d1) - K * exp(-r * T) * _norm_cdf(d2)
        delta = _norm_cdf(d1)
        rho   = K * T * exp(-r * T) * _norm_cdf(d2) / 100
    else:
        price = K * exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)
        delta = _norm_cdf(d1) - 1
        rho   = -K * T * exp(-r * T) * _norm_cdf(-d2) / 100

    gamma = _norm_pdf(d1) / (S * sigma * sqrt(T))
    theta = (-(S * _norm_pdf(d1) * sigma) / (2 * sqrt(T))
             - r * K * exp(-r * T) * (_norm_cdf(d2) if option_type == "call" else _norm_cdf(-d2))) / 365
    vega  = S * _norm_pdf(d1) * sqrt(T) / 100

    return {
        "price": round(price, 4),
        "delta": round(delta, 4),
        "gamma": round(gamma, 6),
        "theta": round(theta, 4),
        "vega":  round(vega, 4),
        "rho":   round(rho, 4),
    }


# ══════════════════════════════════════════════════════════════════════════════
# STORAGE
# ══════════════════════════════════════════════════════════════════════════════

def load_options_positions() -> list:
    if not os.path.exists(OPTIONS_PATH):
        return []
    try:
        with open(OPTIONS_PATH) as f:
            return json.load(f).get("positions", [])
    except Exception:
        return []


def save_options_positions(positions: list):
    with open(OPTIONS_PATH, "w") as f:
        json.dump({"positions": positions}, f, indent=2)


def add_options_position(
    symbol: str,
    option_type: str,       # "call" or "put"
    strike: float,
    expiry: str,            # "YYYY-MM-DD"
    contracts: int,
    premium_paid: float,    # price per share (e.g. 3.50 = $350/contract)
    implied_vol: float,     # e.g. 0.35 for 35% IV
    note: str = "",
) -> dict:
    positions = load_options_positions()
    new_pos = {
        "id":            len(positions) + 1,
        "symbol":        symbol.upper(),
        "option_type":   option_type.lower(),
        "strike":        round(strike, 2),
        "expiry":        expiry,
        "contracts":     int(contracts),
        "premium_paid":  round(premium_paid, 4),
        "implied_vol":   round(implied_vol, 4),
        "note":          note,
        "opened":        str(date.today()),
        "status":        "open",
    }
    positions.append(new_pos)
    save_options_positions(positions)
    return new_pos


def close_options_position(position_id: int):
    positions = load_options_positions()
    for p in positions:
        if p.get("id") == position_id:
            p["status"] = "closed"
            p["closed"] = str(date.today())
    save_options_positions(positions)


def delete_options_position(position_id: int):
    positions = load_options_positions()
    positions = [p for p in positions if p.get("id") != position_id]
    save_options_positions(positions)


# ══════════════════════════════════════════════════════════════════════════════
# P&L ENRICHMENT
# ══════════════════════════════════════════════════════════════════════════════

def days_to_expiry(expiry_str: str) -> float:
    """Return days until expiry (can be negative if expired)."""
    try:
        exp_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
        delta    = (exp_date - date.today()).days
        return float(delta)
    except Exception:
        return 0.0


def enrich_options_positions(current_prices: dict) -> list:
    """
    Take all open positions and calculate live Black-Scholes value + P&L.
    current_prices: {symbol: price}
    Returns list of enriched dicts ready for display.
    """
    positions = load_options_positions()
    enriched  = []

    for p in positions:
        sym    = p["symbol"]
        S      = current_prices.get(sym, 0)
        K      = p["strike"]
        T_days = days_to_expiry(p["expiry"])
        T_yrs  = max(T_days / 365, 0)
        sigma  = p["implied_vol"]
        otype  = p["option_type"]
        contracts = p["contracts"]
        premium   = p["premium_paid"]

        row = dict(p)   # copy all stored fields
        row["current_stock_price"] = round(S, 2)
        row["days_to_expiry"]      = int(T_days)
        row["T_years"]             = round(T_yrs, 4)

        if S > 0 and T_yrs >= 0:
            bs = black_scholes_full(S, K, T_yrs, RISK_FREE_RATE, sigma, otype)
            current_value = bs["price"]

            cost_basis    = premium * contracts * 100
            current_worth = current_value * contracts * 100
            pnl_dollar    = current_worth - cost_basis
            pnl_pct       = (pnl_dollar / cost_basis * 100) if cost_basis else 0

            row.update({
                "bs_price":        round(current_value, 4),
                "cost_basis":      round(cost_basis, 2),
                "current_worth":   round(current_worth, 2),
                "pnl_dollar":      round(pnl_dollar, 2),
                "pnl_pct":         round(pnl_pct, 2),
                "delta":           bs["delta"],
                "gamma":           bs["gamma"],
                "theta":           bs["theta"],
                "vega":            bs["vega"],
                "rho":             bs["rho"],
                "intrinsic":       round(max(S - K, 0) if otype == "call" else max(K - S, 0), 2),
                "time_value":      round(current_value - max(S - K if otype == "call" else K - S, 0), 4),
            })

            # In-the-money check
            if otype == "call":
                row["itm"] = S > K
            else:
                row["itm"] = S < K
        else:
            row.update({
                "bs_price": 0, "cost_basis": premium * contracts * 100,
                "current_worth": 0, "pnl_dollar": -(premium * contracts * 100),
                "pnl_pct": -100, "delta": 0, "gamma": 0, "theta": 0,
                "vega": 0, "rho": 0, "intrinsic": 0, "time_value": 0, "itm": False,
            })

        enriched.append(row)

    return enriched


def get_options_summary(enriched: list) -> dict:
    """Portfolio-level summary across all options positions."""
    open_pos  = [p for p in enriched if p.get("status") == "open"]
    total_cost  = sum(p.get("cost_basis", 0) for p in open_pos)
    total_worth = sum(p.get("current_worth", 0) for p in open_pos)
    total_pnl   = sum(p.get("pnl_dollar", 0) for p in open_pos)
    pnl_pct     = (total_pnl / total_cost * 100) if total_cost else 0

    return {
        "total_positions": len(open_pos),
        "total_cost":      round(total_cost, 2),
        "total_worth":     round(total_worth, 2),
        "total_pnl":       round(total_pnl, 2),
        "pnl_pct":         round(pnl_pct, 2),
    }
