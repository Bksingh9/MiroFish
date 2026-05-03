"""Strategy registry.

Each strategy is a pure function: closes (list[float]) -> Signal | None.
A Signal carries the strategy name, the latest close (for sizing), and a
score in [0, 1] used to rank candidates when multiple strategies fire on
the same ticker or when more candidates than MAX_POSITIONS are available.

Adding a new strategy:
  1. Write a function that returns Signal | None.
  2. Append to STRATEGIES at the bottom of this file.
  3. Backtest with `scripts/backtest.py <name>` and confirm positive
     expectancy on at least 6 months of bars before enabling.
  4. Note the strategy in CLAUDE.md "Active Strategies".

All strategies share the same exit (bracketed −4% / +8%) per
GUARDRAILS §3. Strategy variation is on entry only.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .indicators import highest, macd, rsi, sma


@dataclass
class Signal:
    strategy: str
    ticker: str
    close: float
    score: float  # 0..1, higher = better
    detail: str


# ---------- 1. Mean reversion (the original) ---------- #
def mean_reversion(ticker: str, closes: Sequence[float]) -> Signal | None:
    if len(closes) < 51:
        return None
    last = closes[-1]
    r = rsi(closes, 14)
    s50 = sma(closes, 50)
    if r is None or s50 is None:
        return None
    if r < 35 and last > s50:
        # Score: deeper RSI + more above SMA = better
        rsi_score = (35 - r) / 35  # 0..1
        sma_score = min((last - s50) / s50, 0.10) / 0.10  # cap at 10%
        return Signal(
            strategy="mean_reversion",
            ticker=ticker,
            close=last,
            score=round(0.7 * rsi_score + 0.3 * sma_score, 3),
            detail=f"RSI={r:.1f} close>SMA50 by {((last/s50)-1)*100:.1f}%",
        )
    return None


# ---------- 2. Trend pullback ---------- #
def trend_pullback(ticker: str, closes: Sequence[float]) -> Signal | None:
    """In a confirmed uptrend (50>200 SMA), buy a pullback to the 20DMA."""
    if len(closes) < 201:
        return None
    last = closes[-1]
    s20 = sma(closes, 20)
    s50 = sma(closes, 50)
    s200 = sma(closes, 200)
    r = rsi(closes, 14)
    if None in (s20, s50, s200, r):
        return None
    in_uptrend = s50 > s200 and last > s200
    near_20dma = 0.99 * s20 <= last <= 1.02 * s20
    rsi_zone = 40 <= r <= 55
    if in_uptrend and near_20dma and rsi_zone:
        # Score: higher when MA stack is wider (stronger trend)
        trend_strength = min((s50 - s200) / s200, 0.15) / 0.15
        return Signal(
            strategy="trend_pullback",
            ticker=ticker,
            close=last,
            score=round(0.6 * trend_strength + 0.4 * (1 - abs(r - 47.5) / 7.5), 3),
            detail=f"trend OK, RSI={r:.1f}, close near 20DMA ({s20:.2f})",
        )
    return None


# ---------- 3. 20-day breakout ---------- #
def breakout(ticker: str, closes: Sequence[float]) -> Signal | None:
    """New 20-day high with the trend filter on (close > 50DMA)."""
    if len(closes) < 51:
        return None
    last = closes[-1]
    prior_high = highest(closes[:-1], 20)
    s50 = sma(closes, 50)
    r = rsi(closes, 14)
    if None in (prior_high, s50, r):
        return None
    if last > prior_high and last > s50 and 55 <= r <= 80:
        breakout_strength = min((last - prior_high) / prior_high, 0.05) / 0.05
        rsi_fit = 1 - abs(r - 67.5) / 12.5
        return Signal(
            strategy="breakout",
            ticker=ticker,
            close=last,
            score=round(0.7 * breakout_strength + 0.3 * rsi_fit, 3),
            detail=f"new 20d high, RSI={r:.1f}, close>SMA50",
        )
    return None


# ---------- 4. MACD bullish cross ---------- #
def macd_cross(ticker: str, closes: Sequence[float]) -> Signal | None:
    """MACD line crossed above signal line within the last 2 bars,
    above the 200DMA filter (no counter-trend trades)."""
    if len(closes) < 210:
        return None
    last = closes[-1]
    s200 = sma(closes, 200)
    if s200 is None or last < s200:
        return None
    prev = macd(closes[:-1])
    curr = macd(closes)
    if prev is None or curr is None:
        return None
    pm, ps, _ = prev
    cm, cs, ch = curr
    crossed_up = pm <= ps and cm > cs
    if crossed_up and ch > 0:
        # Score: histogram strength relative to price
        hist_score = min(abs(ch) / last, 0.01) / 0.01
        return Signal(
            strategy="macd_cross",
            ticker=ticker,
            close=last,
            score=round(0.5 + 0.5 * hist_score, 3),
            detail=f"MACD cross above signal, hist={ch:.3f}, > SMA200",
        )
    return None


STRATEGIES = [
    mean_reversion,
    trend_pullback,
    breakout,
    macd_cross,
]


def scan(ticker: str, closes: Sequence[float]) -> list[Signal]:
    """Run every registered strategy against one ticker. Returns all hits."""
    out: list[Signal] = []
    for strat in STRATEGIES:
        sig = strat(ticker, closes)
        if sig is not None:
            out.append(sig)
    return out
