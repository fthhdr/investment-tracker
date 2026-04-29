"""
tax_lots.py — Tax Lot Tracker

Tracks purchase date for each holding to determine:
  - Short-term vs. long-term capital gains
  - Estimated tax impact on unrealized gains
  - Tax-efficient sell order suggestions (e.g. sell long-term lots first)

Tax lots are stored in data/tax_lots.json
"""

import json
import os
from datetime import datetime, date

BASE_DIR       = os.path.dirname(os.path.dirname(__file__))
TAX_LOTS_PATH  = os.path.join(BASE_DIR, "data", "tax_lots.json")

# US Capital Gains tax rates (2026 estimates — single filer)
SHORT_TERM_RATE = 0.22   # Short-term: taxed as ordinary income (~22% bracket)
LONG_TERM_RATE  = 0.15   # Long-term: preferred rate (≥1 year held)


# ── Load / Save ───────────────────────────────────────────────────────────────
def load_lots() -> list:
    """Load all tax lots."""
    if not os.path.exists(TAX_LOTS_PATH):
        return []
    with open(TAX_LOTS_PATH) as f:
        return json.load(f).get("lots", [])


def save_lots(lots: list):
    with open(TAX_LOTS_PATH, "w") as f:
        json.dump({"lots": lots, "updated": str(datetime.now())}, f, indent=2)


# ── CRUD ──────────────────────────────────────────────────────────────────────
def add_lot(symbol: str, shares: float, cost_per_share: float,
            purchase_date: str, note: str = "") -> dict:
    """
    Add a tax lot entry.
    purchase_date: "YYYY-MM-DD" string
    Returns the created lot.
    """
    lots = load_lots()
    lot = {
        "id":            len(lots) + 1,
        "symbol":        symbol.upper(),
        "shares":        round(float(shares), 6),
        "cost_per_share":round(float(cost_per_share), 4),
        "cost_basis":    round(float(shares) * float(cost_per_share), 2),
        "purchase_date": purchase_date,
        "note":          note,
        "added":         str(date.today()),
    }
    lots.append(lot)
    save_lots(lots)
    return lot


def delete_lot(lot_id: int):
    lots = [l for l in load_lots() if l.get("id") != lot_id]
    save_lots(lots)


def get_lots_for_symbol(symbol: str) -> list:
    return [l for l in load_lots() if l.get("symbol") == symbol.upper()]


# ── Analysis ──────────────────────────────────────────────────────────────────
def holding_period(purchase_date_str: str) -> int:
    """Return number of days held from purchase_date to today."""
    try:
        pdate = datetime.strptime(purchase_date_str, "%Y-%m-%d").date()
        return (date.today() - pdate).days
    except Exception:
        return 0


def is_long_term(purchase_date_str: str) -> bool:
    """Return True if held >= 365 days (qualifies for long-term capital gains rate)."""
    return holding_period(purchase_date_str) >= 365


def enrich_lot(lot: dict, current_price: float) -> dict:
    """Add calculated fields to a lot dict."""
    shares   = lot["shares"]
    cost_ps  = lot["cost_per_share"]
    cur_val  = round(shares * current_price, 2)
    cost_bas = round(shares * cost_ps, 2)
    gain     = round(cur_val - cost_bas, 2)
    gain_pct = round((gain / cost_bas * 100) if cost_bas else 0, 2)
    days     = holding_period(lot["purchase_date"])
    lt       = days >= 365
    tax_rate = LONG_TERM_RATE if lt else SHORT_TERM_RATE
    est_tax  = round(max(gain, 0) * tax_rate, 2)

    return {
        **lot,
        "current_price":   round(current_price, 4),
        "current_value":   cur_val,
        "unrealized_gain": gain,
        "gain_pct":        gain_pct,
        "days_held":       days,
        "term":            "Long-Term ✅" if lt else "Short-Term ⚠️",
        "tax_rate":        f"{tax_rate*100:.0f}%",
        "est_tax":         est_tax,
        "days_to_lt":      max(0, 365 - days) if not lt else 0,
    }


def get_tax_summary(current_prices: dict) -> dict:
    """
    Summarize unrealized gains by short-term vs. long-term.
    current_prices: {symbol: price} dict
    """
    lots          = load_lots()
    st_gain       = 0.0
    lt_gain       = 0.0
    st_tax        = 0.0
    lt_tax        = 0.0
    total_value   = 0.0
    total_cost    = 0.0

    for lot in lots:
        sym      = lot["symbol"]
        price    = current_prices.get(sym, 0.0)
        enriched = enrich_lot(lot, price)

        gain  = enriched["unrealized_gain"]
        total_value += enriched["current_value"]
        total_cost  += enriched["cost_basis"]

        if enriched["days_held"] >= 365:
            lt_gain += max(gain, 0)
            lt_tax  += enriched["est_tax"]
        else:
            st_gain += max(gain, 0)
            st_tax  += enriched["est_tax"]

    return {
        "total_lots":         len(lots),
        "total_value":        round(total_value, 2),
        "total_cost":         round(total_cost, 2),
        "total_unrealized":   round(total_value - total_cost, 2),
        "short_term_gains":   round(st_gain, 2),
        "long_term_gains":    round(lt_gain, 2),
        "est_short_term_tax": round(st_tax, 2),
        "est_long_term_tax":  round(lt_tax, 2),
        "total_est_tax":      round(st_tax + lt_tax, 2),
        "tax_savings_if_lt":  round(st_gain * (SHORT_TERM_RATE - LONG_TERM_RATE), 2),
    }


def sell_recommendation(symbol: str, current_price: float) -> list:
    """
    Return lots for a symbol sorted by tax-efficiency for selling:
    1. Long-term lots first (lower tax rate)
    2. Within same term, highest cost basis first (reduces taxable gain)
    """
    lots = get_lots_for_symbol(symbol)
    if not lots:
        return []
    enriched = [enrich_lot(l, current_price) for l in lots]
    # Sort: long-term first, then highest cost basis
    enriched.sort(key=lambda x: (0 if x["days_held"] >= 365 else 1, -x["cost_per_share"]))
    return enriched
