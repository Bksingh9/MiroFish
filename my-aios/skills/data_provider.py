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

    Patterns live at the END of the series so indicators that read the
    most recent N bars see the right setup. seed%5 chooses the pattern:

      0 → mean reversion (35-day ramp into 15-day pullback at the end)
      1 → breakout (slow ramp ending on a new 20-day high)
      2 → trend pullback (long uptrend, recent 4-day dip onto 20DMA)
      3 → MACD bullish cross (uptrend, recent dip + bounce)
      4 → no signal (drifting cycle)
    """
    seed = sum(ord(c) for c in ticker)
    base = 50.0 + (seed % 200)
    bucket = seed % 5

    if bucket == 0:
        # Mean reversion. Action at end: 35-bar ramp, 15-bar decline.
        # Verified to land RSI≈33 and close just above SMA50.
        action = 50
        prefix = max(days - action, 0)
        closes: list[float] = [round(base, 2)] * prefix
        for i in range(35):
            closes.append(round(base + (i + 1) * 78.0 / 35, 2))
        peak = base + 78.0
        for i in range(15):
            closes.append(round(peak - (i + 1) * 2.0, 2))
        return closes[-days:]

    if bucket == 1:
        # Breakout. Long quiet base, 20-bar consolidation, final 1-bar
        # poke above prior 20-day high. Light momentum keeps RSI < 75.
        closes: list[float] = []
        for i in range(days - 22):
            closes.append(round(base + math.sin(i * 0.25) * 1.5, 2))
        # Tight consolidation, 21 bars so the LAST bar can break it
        for i in range(21):
            closes.append(round(base + 6.0 + math.sin(i * 0.4) * 0.6, 2))
        prior_top = max(closes[-21:])
        closes.append(round(prior_top + 0.30, 2))
        return closes[-days:]

    if bucket == 2:
        # Trend pullback. Long uptrend, recent 8-bar dip onto the 20DMA.
        # Deeper dip pushes RSI into the 40-55 zone.
        closes = []
        for i in range(days - 8):
            closes.append(round(base + i * 0.25 + math.sin(i * 0.05) * 0.5, 2))
        peak = closes[-1]
        for i in range(8):
            closes.append(round(peak - (i + 1) * 0.45, 2))
        return closes

    if bucket == 3:
        # MACD bullish cross. Long uptrend, deep 12-bar dip, 4-bar
        # sharp recovery — flips MACD above signal in the last bar.
        closes = []
        for i in range(days - 16):
            closes.append(round(base + i * 0.18, 2))
        peak = closes[-1]
        for i in range(12):
            closes.append(round(peak - (i + 1) * 0.55, 2))
        bottom = closes[-1]
        for i in range(4):
            closes.append(round(bottom + (i + 1) * 1.4, 2))
        return closes

    # Bucket 4: drifting cycle, no signal.
    closes = []
    for i in range(days):
        trend = i * 0.05
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
