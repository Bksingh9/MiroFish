"""Price-history provider.

Resolves to one of three sources based on TRADING_MODE:
  - dry_run → deterministic synthetic series (offline, no deps)
  - paper   → Alpaca historical bars (requires alpaca-py + keys)
  - live    → same as paper

Routine code should never branch on the mode itself — call
`get_closes(ticker, days)` and let the provider decide.
"""

from __future__ import annotations

import math
import os
from collections.abc import Sequence


def _synthetic_closes(ticker: str, days: int) -> list[float]:
    """Deterministic price series seeded by ticker.

    Designed so a few tickers fire the RSI<35 + price>SMA50 signal
    while most don't — enough signal to verify the routine end-to-end.
    """
    seed = sum(ord(c) for c in ticker)
    base = 50.0 + (seed % 200)

    # "Buy zone" tickers: 30 flat / 35 ramp / 15 sustained decline.
    # Tuned so RSI(14) lands ≈33 while close stays modestly above
    # SMA(50). Verified with the indicators in skills/indicators.py.
    if seed % 5 == 0:
        n_flat, n_ramp, n_decline = 30, 35, 15
        assert n_flat + n_ramp + n_decline == days
        peak = base + 78.0
        end_close = peak - n_decline * 2.0  # 2.0/day decline
        closes: list[float] = [round(base, 2)] * n_flat
        for i in range(n_ramp):
            closes.append(round(base + (i + 1) * 78.0 / n_ramp, 2))
        for i in range(n_decline):
            closes.append(round(peak - (i + 1) * 2.0, 2))
        return closes

    # Default: trending series with mild oscillation, no signal.
    closes = []
    for i in range(days):
        trend = i * 0.18
        cycle = math.sin((i + seed) * 0.18) * 4.0
        wobble = math.sin((i + seed) * 0.91) * 1.0
        closes.append(round(base + trend + cycle + wobble, 2))
    return closes


def get_closes(ticker: str, days: int = 80) -> Sequence[float]:
    mode = os.getenv("TRADING_MODE", "dry_run").lower()

    if mode == "dry_run":
        return _synthetic_closes(ticker, days)

    try:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame
    except ImportError as e:
        raise RuntimeError(
            "alpaca-py not installed. `pip install alpaca-py` or run in dry_run."
        ) from e

    key = os.environ["ALPACA_API_KEY"]
    secret = os.environ["ALPACA_API_SECRET"]
    client = StockHistoricalDataClient(key, secret)

    from datetime import UTC, datetime, timedelta

    end = datetime.now(UTC)
    start = end - timedelta(days=days * 2)  # buffer for weekends/holidays
    req = StockBarsRequest(
        symbol_or_symbols=ticker,
        timeframe=TimeFrame.Day,
        start=start,
        end=end,
    )
    bars = client.get_stock_bars(req).data.get(ticker, [])
    closes = [float(b.close) for b in bars][-days:]
    if len(closes) < days // 2:
        raise RuntimeError(f"Insufficient bars for {ticker}: got {len(closes)}")
    return closes


def get_intraday_price(ticker: str, anchor: float) -> float:
    """Current price for an open position.

    dry_run: deterministic drift from the entry anchor designed to
      exercise all three exit branches across a held basket — some
      hit target (+8%+), some stop (−4%−), some sit unrealized.
    paper/live: Alpaca latest trade.
    """
    mode = os.getenv("TRADING_MODE", "dry_run").lower()

    if mode == "dry_run":
        seed = sum(ord(c) for c in ticker)
        bucket = seed % 3
        if bucket == 0:
            return round(anchor * 1.085, 2)  # take-profit hit
        if bucket == 1:
            return round(anchor * 0.955, 2)  # stop hit
        return round(anchor * 1.018, 2)  # unrealized small gain

    try:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockLatestTradeRequest
    except ImportError as e:
        raise RuntimeError(
            "alpaca-py not installed. `pip install alpaca-py` or run in dry_run."
        ) from e

    key = os.environ["ALPACA_API_KEY"]
    secret = os.environ["ALPACA_API_SECRET"]
    client = StockHistoricalDataClient(key, secret)
    req = StockLatestTradeRequest(symbol_or_symbols=ticker)
    trades = client.get_stock_latest_trade(req)
    return float(trades[ticker].price)
