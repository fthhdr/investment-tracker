"""
daily_summary.py — Your personal morning market briefing.
Run it each morning with:  python3 daily_summary.py

It will print:
  1. Today's date & market status
  2. Your portfolio value & P&L
  3. Each holding's overnight performance
  4. Major market indices (S&P 500, Nasdaq, Dow)
  5. Watchlist movers
  6. A simple action suggestion
"""

import json
import os
import sys
from datetime import datetime, date

# ── make sure modules folder is importable ─────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

import yfinance as yf

# ── paths ──────────────────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(__file__)
PORTFOLIO_PATH = os.path.join(BASE_DIR, "data", "portfolio.json")

# ── colour codes for terminal output ──────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
BOLD   = "\033[1m"
RESET  = "\033[0m"
CYAN   = "\033[96m"


def color(val, positive_is_good=True):
    """Return green for positive, red for negative."""
    if val > 0:
        return GREEN if positive_is_good else RED
    elif val < 0:
        return RED if positive_is_good else GREEN
    return RESET


def fmt_dollar(val):
    sign = "+" if val >= 0 else ""
    return f"{sign}${val:,.2f}"


def fmt_pct(val):
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.2f}%"


def divider(char="─", width=60):
    print(char * width)


def header(text):
    divider("═")
    print(f"  {BOLD}{text}{RESET}")
    divider("═")


# ══════════════════════════════════════════════════════════════════════════════
def load_portfolio():
    with open(PORTFOLIO_PATH) as f:
        return json.load(f)


def fetch_price_and_change(symbol):
    """Return (current_price, prev_close, change_pct) for a symbol."""
    try:
        ticker = yf.Ticker(symbol)
        hist   = ticker.history(period="2d")
        if len(hist) < 2:
            hist = ticker.history(period="5d")
        if len(hist) < 1:
            return None, None, None
        curr  = hist["Close"].iloc[-1]
        prev  = hist["Close"].iloc[-2] if len(hist) >= 2 else curr
        chg   = ((curr - prev) / prev) * 100 if prev else 0
        return round(curr, 4), round(prev, 4), round(chg, 2)
    except Exception:
        return None, None, None


def market_is_open():
    """Simple check — US market is open Mon–Fri."""
    today = date.today()
    return today.weekday() < 5   # 0=Mon … 4=Fri


# ══════════════════════════════════════════════════════════════════════════════
def print_header_banner():
    now = datetime.now()
    print()
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}   📈  DAILY INVESTMENT BRIEFING{RESET}")
    print(f"{BOLD}{CYAN}   {now.strftime('%A, %B %d, %Y  —  %I:%M %p')}{RESET}")
    market_status = f"{GREEN}🟢 Market Open" if market_is_open() else f"{RED}🔴 Market Closed"
    print(f"{BOLD}{CYAN}   {market_status}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")
    print()


def print_portfolio_summary(portfolio):
    header("💼  YOUR PORTFOLIO")
    holdings = portfolio.get("holdings", [])
    if not holdings:
        print("  No holdings found.")
        return

    total_cost  = 0.0
    total_value = 0.0
    rows        = []

    print(f"  {'Symbol':<8} {'Shares':>8} {'Avg Cost':>10} {'Price':>10} {'Value':>10} {'Day Chg':>9} {'Total P&L':>11}")
    divider()

    for h in holdings:
        sym   = h["symbol"]
        shares = h["shares"]
        cost  = h["avg_cost"]
        price, prev, day_chg = fetch_price_and_change(sym)

        if price is None:
            print(f"  {sym:<8}  ⚠️  Could not fetch price")
            continue

        mkt_val  = price * shares
        cost_val = cost  * shares
        pnl      = mkt_val - cost_val
        total_cost  += cost_val
        total_value += mkt_val

        day_chg = day_chg or 0.0
        dc = color(day_chg)
        pc = color(pnl)

        print(
            f"  {sym:<8} {shares:>8.4f} {cost:>10.2f} {price:>10.2f} "
            f"${mkt_val:>8,.2f} "
            f"{dc}{fmt_pct(day_chg):>9}{RESET} "
            f"{pc}{fmt_dollar(pnl):>11}{RESET}"
        )
        rows.append((sym, day_chg, pnl))

    divider()
    total_pnl = total_value - total_cost
    ret_pct   = (total_pnl / total_cost * 100) if total_cost else 0
    tc = color(total_pnl)
    print(f"\n  {'Total Invested':<20} ${total_cost:>10,.2f}")
    print(f"  {'Portfolio Value':<20} ${total_value:>10,.2f}")
    print(f"  {'Total P&L':<20} {tc}{fmt_dollar(total_pnl)}{RESET}  ({tc}{fmt_pct(ret_pct)}{RESET})")
    print()

    # Best & worst today
    if rows:
        best  = max(rows, key=lambda x: x[1])
        worst = min(rows, key=lambda x: x[1])
        print(f"  {GREEN}📈 Best today:   {best[0]}  ({fmt_pct(best[1])}){RESET}")
        print(f"  {RED}📉 Worst today:  {worst[0]}  ({fmt_pct(worst[1])}){RESET}")
    print()


def print_market_indices():
    header("🌍  MARKET INDICES")
    indices = {
        "S&P 500":  "^GSPC",
        "Nasdaq":   "^IXIC",
        "Dow Jones":"^DJI",
        "VIX Fear": "^VIX",
        "Bitcoin":  "BTC-USD",
        "Ethereum": "ETH-USD",
    }
    for name, sym in indices.items():
        price, prev, chg = fetch_price_and_change(sym)
        if price is None:
            print(f"  {name:<14}  ⚠️  unavailable")
            continue
        dc = color(chg)
        print(f"  {name:<14}  ${price:>12,.2f}   {dc}{fmt_pct(chg):>8}{RESET}")
    print()


def print_watchlist(portfolio):
    header("👀  WATCHLIST MOVERS")
    watchlist = portfolio.get("watchlist", [])
    if not watchlist:
        print("  No watchlist items.\n")
        return

    for w in watchlist:
        sym   = w["symbol"]
        name  = w.get("name", sym)
        note  = w.get("note", "")
        price, prev, chg = fetch_price_and_change(sym)
        if price is None:
            print(f"  {sym:<8}  ⚠️  unavailable  — {note}")
            continue
        dc = color(chg)
        arrow = "▲" if chg >= 0 else "▼"
        print(f"  {sym:<8} ${price:>8,.2f}  {dc}{arrow} {fmt_pct(chg):>7}{RESET}   {note}")
    print()


def print_action_suggestions(portfolio):
    header("💡  MORNING ACTION CHECKLIST")
    suggestions = [
        "✅  Review any holdings down >5% — consider adding or holding",
        "✅  Check if this month's investment contribution is on track",
        "✅  Look at your watchlist — any good entry points today?",
        "✅  Set price alerts for any stocks near your target buy price",
        "✅  Review news for your holdings before market open",
    ]
    for s in suggestions:
        print(f"  {s}")
    print()
    print(f"  {YELLOW}📅  Run this script every morning for your daily briefing!{RESET}")
    print()


# ══════════════════════════════════════════════════════════════════════════════
def main():
    print_header_banner()

    try:
        portfolio = load_portfolio()
    except FileNotFoundError:
        print(f"  {RED}❌  portfolio.json not found. Run the app first to set up your portfolio.{RESET}")
        return

    print_portfolio_summary(portfolio)
    print_market_indices()
    print_watchlist(portfolio)
    print_action_suggestions(portfolio)

    print(f"{CYAN}{'='*60}{RESET}")
    print(f"{CYAN}  End of briefing — have a great trading day! 🚀{RESET}")
    print(f"{CYAN}{'='*60}{RESET}\n")


if __name__ == "__main__":
    main()
