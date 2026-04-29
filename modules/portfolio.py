"""
portfolio.py — Portfolio loading, enrichment, and P&L calculations
"""

import json
import os
import pandas as pd
from datetime import datetime
from modules.market_data import get_bulk_prices, estimate_option_value

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def load_portfolio() -> dict:
    path = os.path.join(DATA_DIR, "portfolio.json")
    with open(path, "r") as f:
        return json.load(f)


def load_transactions() -> dict:
    path = os.path.join(DATA_DIR, "transactions.json")
    with open(path, "r") as f:
        return json.load(f)


def save_portfolio(data: dict):
    path = os.path.join(DATA_DIR, "portfolio.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def save_transactions(data: dict):
    path = os.path.join(DATA_DIR, "transactions.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ── Portfolio enrichment ──────────────────────────────────────────────────────

def get_enriched_portfolio() -> pd.DataFrame:
    """Return a DataFrame of all holdings with live prices, P&L, and allocation."""
    raw = load_portfolio()
    holdings = raw.get("holdings", [])
    options = raw.get("options", [])

    # Collect symbols for bulk price fetch
    symbols = [h["symbol"] for h in holdings]
    underlying_symbols = list({o["symbol"] for o in options})
    all_symbols = list(set(symbols + underlying_symbols))
    prices = get_bulk_prices(all_symbols)

    rows = []

    # Regular holdings
    for h in holdings:
        sym = h["symbol"]
        price = prices.get(sym, 0.0)
        cost = h["avg_cost"]
        shares = h["shares"]
        market_value = price * shares
        cost_basis = cost * shares
        pnl = market_value - cost_basis
        pnl_pct = ((price - cost) / cost) * 100 if cost else 0

        rows.append({
            "Symbol": sym,
            "Name": h.get("name", sym),
            "Type": h["type"].upper(),
            "Shares": shares,
            "Avg Cost": cost,
            "Current Price": price,
            "Market Value": round(market_value, 2),
            "Cost Basis": round(cost_basis, 2),
            "P&L ($)": round(pnl, 2),
            "P&L (%)": round(pnl_pct, 2),
            "Purchase Date": h.get("purchase_date", ""),
        })

    # Options
    for o in options:
        sym = o["symbol"]
        underlying_price = prices.get(sym, 0.0)
        opt_val = estimate_option_value(o, underlying_price)

        rows.append({
            "Symbol": o.get("name", sym),
            "Name": o.get("name", f"{sym} {o['contract_type']}"),
            "Type": "OPTIONS",
            "Shares": f"{o['contracts']} contracts",
            "Avg Cost": o["premium_paid"],
            "Current Price": opt_val.get("bs_price", 0),
            "Market Value": opt_val.get("current_value", 0),
            "Cost Basis": opt_val.get("cost_basis", 0),
            "P&L ($)": opt_val.get("pnl", 0),
            "P&L (%)": opt_val.get("pnl_pct", 0),
            "Purchase Date": o.get("purchase_date", ""),
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        total_value = df["Market Value"].sum()
        df["Allocation %"] = ((df["Market Value"] / total_value) * 100).round(2)
    return df


def get_portfolio_summary(df: pd.DataFrame) -> dict:
    """High-level portfolio KPIs."""
    if df.empty:
        return {}
    total_value = df["Market Value"].sum()
    total_cost = df["Cost Basis"].sum()
    total_pnl = df["P&L ($)"].sum()
    total_pnl_pct = ((total_value - total_cost) / total_cost) * 100 if total_cost else 0

    by_type = df.groupby("Type").agg(
        Value=("Market Value", "sum"),
        PnL=("P&L ($)", "sum")
    ).reset_index()

    return {
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 2),
        "by_type": by_type,
        "num_positions": len(df),
        "winners": len(df[df["P&L ($)"] > 0]),
        "losers": len(df[df["P&L ($)"] < 0]),
        "as_of": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def add_holding(symbol: str, name: str, asset_type: str, shares: float,
                avg_cost: float, purchase_date: str = None):
    """Add or update a holding in portfolio.json."""
    data = load_portfolio()
    purchase_date = purchase_date or datetime.now().strftime("%Y-%m-%d")

    if asset_type == "options":
        # Handled separately
        return

    for h in data["holdings"]:
        if h["symbol"] == symbol:
            # Weighted average cost
            total_shares = h["shares"] + shares
            h["avg_cost"] = round(
                (h["avg_cost"] * h["shares"] + avg_cost * shares) / total_shares, 4
            )
            h["shares"] = round(total_shares, 6)
            save_portfolio(data)
            return

    data["holdings"].append({
        "symbol": symbol,
        "name": name,
        "type": asset_type,
        "shares": shares,
        "avg_cost": avg_cost,
        "purchase_date": purchase_date,
    })
    save_portfolio(data)


def log_transaction(symbol: str, tx_type: str, shares: float, price: float,
                    asset_type: str):
    """Append a transaction to transactions.json."""
    data = load_transactions()
    tx = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "symbol": symbol,
        "type": tx_type,
        "shares": shares,
        "price": price,
        "total": round(shares * price, 2),
        "asset_type": asset_type,
    }
    data["transactions"].append(tx)
    save_transactions(data)
