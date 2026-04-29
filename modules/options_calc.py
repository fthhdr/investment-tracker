"""
options_calc.py — Full options P&L calculator with Black-Scholes & Greeks.
Calculates: Call/Put price, Delta, Gamma, Theta, Vega, Rho
"""

import math
from datetime import datetime, date
import numpy as np


# ══════════════════════════════════════════════════════════════════════════════
# MATH HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _norm_cdf(x: float) -> float:
    """Standard normal cumulative distribution function."""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0


def _norm_pdf(x: float) -> float:
    """Standard normal probability density function."""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


# ══════════════════════════════════════════════════════════════════════════════
# BLACK-SCHOLES CORE
# ══════════════════════════════════════════════════════════════════════════════

def black_scholes(S: float, K: float, T: float, r: float,
                  sigma: float, option_type: str = "call") -> dict:
    """
    Full Black-Scholes calculation returning price AND all Greeks.

    Parameters
    ----------
    S     : Current stock price
    K     : Strike price
    T     : Time to expiration in years (e.g. 30 days = 30/365)
    r     : Risk-free interest rate (e.g. 0.05 = 5%)
    sigma : Implied volatility (e.g. 0.30 = 30%)
    option_type : "call" or "put"

    Returns
    -------
    dict with keys: price, delta, gamma, theta, vega, rho, d1, d2
    """
    if T <= 0:
        # Expired option — intrinsic value only
        intrinsic = max(S - K, 0) if option_type.lower() == "call" else max(K - S, 0)
        return {
            "price": intrinsic, "delta": 0.0, "gamma": 0.0,
            "theta": 0.0, "vega": 0.0, "rho": 0.0,
            "d1": 0.0, "d2": 0.0, "intrinsic": intrinsic, "time_value": 0.0,
        }

    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    if option_type.lower() == "call":
        price = S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
        delta = _norm_cdf(d1)
        rho   = K * T * math.exp(-r * T) * _norm_cdf(d2) / 100
        theta = (
            -(S * _norm_pdf(d1) * sigma) / (2 * math.sqrt(T))
            - r * K * math.exp(-r * T) * _norm_cdf(d2)
        ) / 365  # per day
    else:  # put
        price = K * math.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)
        delta = _norm_cdf(d1) - 1
        rho   = -K * T * math.exp(-r * T) * _norm_cdf(-d2) / 100
        theta = (
            -(S * _norm_pdf(d1) * sigma) / (2 * math.sqrt(T))
            + r * K * math.exp(-r * T) * _norm_cdf(-d2)
        ) / 365  # per day

    gamma = _norm_pdf(d1) / (S * sigma * math.sqrt(T))
    vega  = S * _norm_pdf(d1) * math.sqrt(T) / 100  # per 1% vol change

    intrinsic  = max(S - K, 0) if option_type.lower() == "call" else max(K - S, 0)
    time_value = max(price - intrinsic, 0)

    return {
        "price":      round(price, 4),
        "delta":      round(delta, 4),
        "gamma":      round(gamma, 6),
        "theta":      round(theta, 4),
        "vega":       round(vega, 4),
        "rho":        round(rho, 4),
        "d1":         round(d1, 4),
        "d2":         round(d2, 4),
        "intrinsic":  round(intrinsic, 4),
        "time_value": round(time_value, 4),
    }


# ══════════════════════════════════════════════════════════════════════════════
# P&L CALCULATOR
# ══════════════════════════════════════════════════════════════════════════════

def option_pnl(S: float, K: float, T: float, r: float, sigma: float,
               option_type: str, premium_paid: float, contracts: int = 1) -> dict:
    """
    Calculate current P&L for an open options position.

    Parameters
    ----------
    premium_paid : What you originally paid per share (e.g. $2.50)
    contracts    : Number of contracts (each contract = 100 shares)

    Returns
    -------
    dict with P&L info plus all Greeks from Black-Scholes
    """
    bs      = black_scholes(S, K, T, r, sigma, option_type)
    curr_px = bs["price"]

    cost_basis   = premium_paid * contracts * 100
    curr_value   = curr_px     * contracts * 100
    pnl_dollar   = curr_value - cost_basis
    pnl_pct      = (pnl_dollar / cost_basis * 100) if cost_basis else 0

    # Break-even at expiry
    if option_type.lower() == "call":
        breakeven = K + premium_paid
    else:
        breakeven = K - premium_paid

    return {
        "current_price":  curr_px,
        "premium_paid":   premium_paid,
        "cost_basis":     round(cost_basis, 2),
        "current_value":  round(curr_value, 2),
        "pnl_dollar":     round(pnl_dollar, 2),
        "pnl_pct":        round(pnl_pct, 2),
        "breakeven":      round(breakeven, 2),
        "contracts":      contracts,
        "intrinsic":      bs["intrinsic"],
        "time_value":     bs["time_value"],
        "delta":          bs["delta"],
        "gamma":          bs["gamma"],
        "theta":          bs["theta"],
        "vega":           bs["vega"],
        "rho":            bs["rho"],
    }


# ══════════════════════════════════════════════════════════════════════════════
# P&L ACROSS PRICE RANGE (for chart)
# ══════════════════════════════════════════════════════════════════════════════

def pnl_at_expiry_curve(S: float, K: float, premium_paid: float,
                        option_type: str, contracts: int = 1,
                        price_range_pct: float = 0.30) -> dict:
    """
    Returns lists of stock prices and corresponding P&L at expiry.
    Used to draw the hockey-stick P&L diagram.
    """
    lo = S * (1 - price_range_pct)
    hi = S * (1 + price_range_pct)
    prices = [lo + (hi - lo) * i / 200 for i in range(201)]

    if option_type.lower() == "call":
        pnls = [(max(p - K, 0) - premium_paid) * contracts * 100 for p in prices]
    else:
        pnls = [(max(K - p, 0) - premium_paid) * contracts * 100 for p in prices]

    return {"prices": prices, "pnls": pnls}


def pnl_today_curve(S: float, K: float, T: float, r: float, sigma: float,
                    option_type: str, premium_paid: float,
                    contracts: int = 1, price_range_pct: float = 0.30) -> dict:
    """
    Returns P&L TODAY (not at expiry) across a range of stock prices.
    Shows time value still included.
    """
    lo = S * (1 - price_range_pct)
    hi = S * (1 + price_range_pct)
    prices = [lo + (hi - lo) * i / 200 for i in range(201)]

    pnls = []
    for p in prices:
        bs = black_scholes(p, K, T, r, sigma, option_type)
        pnl = (bs["price"] - premium_paid) * contracts * 100
        pnls.append(pnl)

    return {"prices": prices, "pnls": pnls}


# ══════════════════════════════════════════════════════════════════════════════
# GREEKS EXPLANATION (for UI tooltips)
# ══════════════════════════════════════════════════════════════════════════════

GREEKS_EXPLAINED = {
    "delta": {
        "symbol": "Δ",
        "name":   "Delta",
        "plain_english": (
            "How much the option price moves when the stock moves $1. "
            "Example: Delta of 0.50 means if stock goes up $1, your option gains ~$0.50. "
            "Calls have positive delta (0 to 1), Puts have negative delta (-1 to 0)."
        ),
    },
    "gamma": {
        "symbol": "Γ",
        "name":   "Gamma",
        "plain_english": (
            "How fast Delta changes when the stock moves $1. "
            "High gamma means your delta (and risk) changes quickly. "
            "Options near expiry and near the strike price have the highest gamma."
        ),
    },
    "theta": {
        "symbol": "Θ",
        "name":   "Theta (Time Decay)",
        "plain_english": (
            "How much the option loses in value each day just from time passing. "
            "Example: Theta of -0.05 means your option loses $5 per contract per day "
            "even if the stock doesn't move. This is why options buyers hate weekends!"
        ),
    },
    "vega": {
        "symbol": "V",
        "name":   "Vega",
        "plain_english": (
            "How much the option price changes when volatility moves 1%. "
            "Example: Vega of 0.10 means if implied volatility rises 1%, "
            "your option gains $0.10 (or $10 per contract). "
            "High vega = sensitive to market uncertainty."
        ),
    },
    "rho": {
        "symbol": "ρ",
        "name":   "Rho",
        "plain_english": (
            "How much the option price changes when interest rates move 1%. "
            "Usually the least impactful Greek for short-term options. "
            "Calls have positive rho (benefit from rising rates), "
            "Puts have negative rho."
        ),
    },
}


def days_to_expiry(expiry_date: date) -> int:
    """Return number of calendar days until expiration."""
    today = date.today()
    delta = expiry_date - today
    return max(delta.days, 0)


def years_to_expiry(expiry_date: date) -> float:
    """Return fraction of a year until expiration."""
    return days_to_expiry(expiry_date) / 365.0
