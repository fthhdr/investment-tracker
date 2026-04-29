"""
trade_journal.py — Trade Journal module.
Log every trade: entry, exit, strategy, result, lesson learned.
The most important habit for improving as a trader.
"""

import json
import os
from datetime import date, datetime

BASE_DIR      = os.path.dirname(os.path.dirname(__file__))
JOURNAL_PATH  = os.path.join(BASE_DIR, "data", "trade_journal.json")

STRATEGIES = [
    "Swing Trade",
    "Momentum / Breakout",
    "Pullback / Dip Buy",
    "Earnings Play",
    "Trend Follow",
    "Reversal",
    "ETF / Long-Term Buy",
    "Options Play",
    "Crypto Trade",
    "Other",
]

EMOTIONS = ["Calm / Disciplined", "Confident", "Excited / FOMO", "Anxious", "Revenge Trading", "Other"]
GRADES   = ["A — Followed plan perfectly", "B — Minor deviation", "C — Broke a rule", "D — Emotional trade", "F — Should not have entered"]


def load_journal() -> list:
    if not os.path.exists(JOURNAL_PATH):
        return []
    try:
        with open(JOURNAL_PATH) as f:
            return json.load(f).get("trades", [])
    except Exception:
        return []


def save_journal(trades: list):
    with open(JOURNAL_PATH, "w") as f:
        json.dump({"trades": trades}, f, indent=2)


def add_trade(
    symbol:        str,
    direction:     str,       # "LONG" or "SHORT"
    strategy:      str,
    entry_date:    str,
    entry_price:   float,
    shares:        float,
    stop_loss:     float,
    take_profit:   float,
    exit_date:     str  = "",
    exit_price:    float = 0.0,
    emotion:       str  = "Calm / Disciplined",
    grade:         str  = "A — Followed plan perfectly",
    setup_notes:   str  = "",
    result_notes:  str  = "",
    lesson:        str  = "",
) -> dict:
    trades = load_journal()

    cost_basis   = round(entry_price * shares, 2)
    risk_per_share = round(abs(entry_price - stop_loss), 2)
    reward_per_share = round(abs(take_profit - entry_price), 2)
    rr_ratio     = round(reward_per_share / risk_per_share, 2) if risk_per_share else 0
    max_risk     = round(risk_per_share * shares, 2)

    # If exit provided, calculate P&L
    pnl_dollar = 0.0
    pnl_pct    = 0.0
    outcome    = "open"
    if exit_price > 0:
        if direction == "LONG":
            pnl_dollar = round((exit_price - entry_price) * shares, 2)
        else:
            pnl_dollar = round((entry_price - exit_price) * shares, 2)
        pnl_pct = round(pnl_dollar / cost_basis * 100, 2) if cost_basis else 0
        outcome = "win" if pnl_dollar > 0 else ("breakeven" if pnl_dollar == 0 else "loss")

    trade = {
        "id":            len(trades) + 1,
        "symbol":        symbol.upper(),
        "direction":     direction,
        "strategy":      strategy,
        "entry_date":    entry_date,
        "entry_price":   round(entry_price, 4),
        "shares":        round(shares, 6),
        "cost_basis":    cost_basis,
        "stop_loss":     round(stop_loss, 4),
        "take_profit":   round(take_profit, 4),
        "risk_per_share":risk_per_share,
        "reward_per_share": reward_per_share,
        "rr_ratio":      rr_ratio,
        "max_risk":      max_risk,
        "exit_date":     exit_date,
        "exit_price":    round(exit_price, 4),
        "pnl_dollar":    pnl_dollar,
        "pnl_pct":       pnl_pct,
        "outcome":       outcome,
        "emotion":       emotion,
        "grade":         grade,
        "setup_notes":   setup_notes,
        "result_notes":  result_notes,
        "lesson":        lesson,
        "logged":        str(date.today()),
    }
    trades.append(trade)
    save_journal(trades)
    return trade


def close_trade(trade_id: int, exit_date: str, exit_price: float,
                result_notes: str = "", lesson: str = "", grade: str = ""):
    trades = load_journal()
    for t in trades:
        if t.get("id") == trade_id:
            t["exit_date"]    = exit_date
            t["exit_price"]   = round(exit_price, 4)
            if t["direction"] == "LONG":
                t["pnl_dollar"] = round((exit_price - t["entry_price"]) * t["shares"], 2)
            else:
                t["pnl_dollar"] = round((t["entry_price"] - exit_price) * t["shares"], 2)
            cb = t.get("cost_basis", 1)
            t["pnl_pct"]    = round(t["pnl_dollar"] / cb * 100, 2) if cb else 0
            t["outcome"]    = "win" if t["pnl_dollar"] > 0 else ("breakeven" if t["pnl_dollar"] == 0 else "loss")
            if result_notes: t["result_notes"] = result_notes
            if lesson:        t["lesson"]       = lesson
            if grade:         t["grade"]        = grade
    save_journal(trades)


def delete_trade(trade_id: int):
    trades = load_journal()
    trades = [t for t in trades if t.get("id") != trade_id]
    save_journal(trades)


def get_journal_stats(trades: list) -> dict:
    closed = [t for t in trades if t["outcome"] in ("win", "loss", "breakeven")]
    open_  = [t for t in trades if t["outcome"] == "open"]
    wins   = [t for t in closed if t["outcome"] == "win"]
    losses = [t for t in closed if t["outcome"] == "loss"]

    total_pnl    = sum(t["pnl_dollar"] for t in closed)
    win_rate     = len(wins) / len(closed) * 100 if closed else 0
    avg_win      = sum(t["pnl_dollar"] for t in wins)   / len(wins)   if wins   else 0
    avg_loss     = sum(t["pnl_dollar"] for t in losses) / len(losses) if losses else 0
    profit_factor = abs(avg_win / avg_loss) if avg_loss else 0
    avg_rr       = sum(t.get("rr_ratio", 0) for t in trades) / len(trades) if trades else 0
    best_trade   = max(closed, key=lambda t: t["pnl_dollar"]) if closed else None
    worst_trade  = min(closed, key=lambda t: t["pnl_dollar"]) if closed else None

    return {
        "total_trades":   len(trades),
        "closed_trades":  len(closed),
        "open_trades":    len(open_),
        "wins":           len(wins),
        "losses":         len(losses),
        "win_rate":       round(win_rate, 1),
        "total_pnl":      round(total_pnl, 2),
        "avg_win":        round(avg_win, 2),
        "avg_loss":       round(avg_loss, 2),
        "profit_factor":  round(profit_factor, 2),
        "avg_rr":         round(avg_rr, 2),
        "best_trade":     best_trade,
        "worst_trade":    worst_trade,
    }
