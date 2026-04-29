"""
market_data.py — Fetches live and historical market data
Sources: yfinance (stocks, ETFs, REITs, crypto) + CoinGecko (crypto fallback)
"""

import yfinance as yf
import pandas as pd
import requests
import json
from datetime import datetime, timedelta
import time


# ── Stocks / ETFs / REITs / Crypto via yfinance ──────────────────────────────

def get_current_price(symbol: str) -> float:
    """Return the latest price for any yfinance-supported symbol."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        price = info.last_price
        if price and price > 0:
            return round(float(price), 4)
    except Exception:
        pass
    # fallback: last closing price
    try:
        hist = yf.download(symbol, period="2d", progress=False, auto_adjust=True)
        if not hist.empty:
            return round(float(hist["Close"].iloc[-1]), 4)
    except Exception:
        pass
    return 0.0


def get_bulk_prices(symbols: list[str]) -> dict[str, float]:
    """Fetch prices for multiple symbols in one call."""
    prices = {}
    try:
        data = yf.download(symbols, period="2d", progress=False, auto_adjust=True)
        if len(symbols) == 1:
            # Single-symbol download returns a Series under "Close"
            sym = symbols[0]
            prices[sym] = round(float(data["Close"].iloc[-1]), 4)
        else:
            close = data["Close"]
            for sym in symbols:
                if sym in close.columns:
                    val = close[sym].dropna()
                    if not val.empty:
                        prices[sym] = round(float(val.iloc[-1]), 4)
    except Exception:
        # Fallback: fetch one by one
        for sym in symbols:
            prices[sym] = get_current_price(sym)
    return prices


def get_historical_data(symbol: str, period: str = "1y") -> pd.DataFrame:
    """Return OHLCV history for charting. period: 1d,5d,1mo,3mo,6mo,1y,2y,5y."""
    try:
        df = yf.download(symbol, period=period, progress=False, auto_adjust=True)
        df.index = pd.to_datetime(df.index)
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        return df
    except Exception as e:
        print(f"Error fetching history for {symbol}: {e}")
        return pd.DataFrame()


def get_ticker_info(symbol: str) -> dict:
    """Return basic info dict for a ticker (name, sector, market cap, etc.)."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return {
            "name": info.get("longName", symbol),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE", None),
            "dividend_yield": info.get("dividendYield", 0),
            "52w_high": info.get("fiftyTwoWeekHigh", 0),
            "52w_low": info.get("fiftyTwoWeekLow", 0),
            "beta": info.get("beta", None),
            "currency": info.get("currency", "USD"),
        }
    except Exception:
        return {}


# ── Crypto via CoinGecko (free API, no key required) ─────────────────────────

COINGECKO_IDS = {
    "BTC-USD": "bitcoin",
    "ETH-USD": "ethereum",
    "SOL-USD": "solana",
    "ADA-USD": "cardano",
    "DOGE-USD": "dogecoin",
    "XRP-USD": "ripple",
    "BNB-USD": "binancecoin",
    "AVAX-USD": "avalanche-2",
    "DOT-USD": "polkadot",
}


def get_crypto_price_coingecko(symbol: str) -> float:
    """Fallback: fetch crypto price from CoinGecko public API."""
    coin_id = COINGECKO_IDS.get(symbol.upper())
    if not coin_id:
        return 0.0
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        resp = requests.get(url, timeout=8)
        data = resp.json()
        return float(data[coin_id]["usd"])
    except Exception:
        return 0.0


def get_market_movers(symbols: list[str]) -> pd.DataFrame:
    """Return a DataFrame with daily change % for a list of symbols."""
    rows = []
    try:
        tickers = yf.download(symbols, period="5d", progress=False, auto_adjust=True)
        close = tickers["Close"] if len(symbols) > 1 else tickers[["Close"]]
        if len(symbols) == 1:
            close.columns = symbols
        for sym in symbols:
            if sym in close.columns:
                series = close[sym].dropna()
                if len(series) >= 2:
                    prev = float(series.iloc[-2])
                    curr = float(series.iloc[-1])
                    chg = ((curr - prev) / prev) * 100
                    rows.append({"Symbol": sym, "Price": round(curr, 2), "Daily Change %": round(chg, 2)})
    except Exception:
        pass
    return pd.DataFrame(rows)


# ── Options pricing (Black-Scholes approximation) ────────────────────────────

import math


def black_scholes_price(S, K, T, r, sigma, option_type="call") -> float:
    """Compute Black-Scholes option price.
    S=current price, K=strike, T=years to expiry, r=risk-free rate, sigma=volatility
    """
    if T <= 0:
        intrinsic = max(S - K, 0) if option_type == "call" else max(K - S, 0)
        return intrinsic
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    def N(x):
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    if option_type == "call":
        return S * N(d1) - K * math.exp(-r * T) * N(d2)
    else:
        return K * math.exp(-r * T) * N(-d2) - S * N(-d1)


def estimate_option_value(option: dict, underlying_price: float) -> dict:
    """Given an option position dict and the current underlying price, estimate current value."""
    try:
        expiry = datetime.strptime(option["expiry"], "%Y-%m-%d")
        T = max((expiry - datetime.now()).days / 365, 0)
        K = option["strike"]
        r = 0.045  # risk-free rate approx
        sigma = 0.30  # implied vol estimate (30% default)
        bs_price = black_scholes_price(underlying_price, K, T, r, sigma,
                                       option_type=option["contract_type"].lower())
        contracts = option["contracts"]
        premium_paid = option["premium_paid"]
        current_value = bs_price * contracts * 100
        cost_basis = premium_paid * contracts * 100
        pnl = current_value - cost_basis
        return {
            "bs_price": round(bs_price, 2),
            "current_value": round(current_value, 2),
            "cost_basis": round(cost_basis, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round((pnl / cost_basis) * 100, 2) if cost_basis else 0,
            "days_to_expiry": int(T * 365),
        }
    except Exception as e:
        return {"error": str(e), "current_value": 0, "pnl": 0}
