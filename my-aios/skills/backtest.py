"""Walk-forward backtest engine.

Pure-stdlib. Takes a strategy function and a price series, simulates
entries+exits using the universal bracket exit (-4% / +8%), returns
trades and summary stats.

Approximation: bars are daily closes only (no high/low). A position
exits when:
  • next close ≤ stop  → exit at stop  (assumed gap-down to stop)
  • next close ≥ target → exit at target
  • neither hit before MAX_HOLD bars → exit at close at hold limit
This is conservative for stops (close-through assumption underestimates
slippage) and exact for targets.

For more realistic backtesting use intraday bars from Alpaca and
adjust the exit logic to check high/low against stop/target.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Callable

from .strategies import Signal

STOP_PCT = 0.04
TARGET_PCT = 0.08
MAX_HOLD = 30  # bars — swing trades shouldn't drag forever
MIN_BARS = 210  # need history for SMA200 + MACD


@dataclass
class BTTrade:
    ticker: str
    strategy: str
    entry_idx: int
    exit_idx: int
    entry: float
    exit: float
    stop: float
    target: float
    pnl_pct: float
    r_multiple: float
    reason: str


@dataclass
class BTStats:
    strategy: str
    trades: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl_pct: float = 0.0  # cumulative % return assuming 10% per trade
    avg_r: float = 0.0
    expectancy_r: float = 0.0
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    max_consec_losses: int = 0

    @property
    def win_rate(self) -> float:
        return self.wins / self.trades if self.trades else 0.0


StratFn = Callable[[str, Sequence[float]], Signal | None]


def backtest_strategy(
    ticker: str, closes: Sequence[float], strategy: StratFn
) -> list[BTTrade]:
    """Walk forward through `closes`. Open a position whenever the
    strategy fires and no position is open; close on stop/target/hold.
    """
    trades: list[BTTrade] = []
    n = len(closes)
    if n < MIN_BARS + 2:
        return trades

    in_pos = False
    entry_idx = 0
    entry_price = stop = target = 0.0

    for i in range(MIN_BARS, n - 1):
        if in_pos:
            nxt = closes[i + 1]
            held = i + 1 - entry_idx
            exit_price: float | None = None
            reason = ""
            if nxt <= stop:
                exit_price, reason = stop, "STOP"
            elif nxt >= target:
                exit_price, reason = target, "TARGET"
            elif held >= MAX_HOLD:
                exit_price, reason = nxt, "HOLD_LIMIT"
            if exit_price is not None:
                pnl_pct = (exit_price - entry_price) / entry_price
                risk_pct = STOP_PCT
                trades.append(
                    BTTrade(
                        ticker=ticker,
                        strategy=strategy.__name__,
                        entry_idx=entry_idx,
                        exit_idx=i + 1,
                        entry=entry_price,
                        exit=exit_price,
                        stop=stop,
                        target=target,
                        pnl_pct=pnl_pct,
                        r_multiple=pnl_pct / risk_pct,
                        reason=reason,
                    )
                )
                in_pos = False
            continue

        # not in position — look for entry
        sig = strategy(ticker, closes[: i + 1])
        if sig is not None:
            entry_idx = i + 1
            if entry_idx >= n:
                break
            entry_price = closes[entry_idx]
            stop = round(entry_price * (1 - STOP_PCT), 2)
            target = round(entry_price * (1 + TARGET_PCT), 2)
            in_pos = True

    return trades


def stats(strategy_name: str, trades: list[BTTrade]) -> BTStats:
    s = BTStats(strategy=strategy_name)
    if not trades:
        return s
    s.trades = len(trades)
    wins = [t for t in trades if t.pnl_pct > 0]
    losses = [t for t in trades if t.pnl_pct <= 0]
    s.wins = len(wins)
    s.losses = len(losses)
    s.avg_r = sum(t.r_multiple for t in trades) / len(trades)
    s.avg_win_pct = sum(t.pnl_pct for t in wins) / len(wins) if wins else 0.0
    s.avg_loss_pct = sum(t.pnl_pct for t in losses) / len(losses) if losses else 0.0
    # Cumulative % assuming each trade sized at 10% of equity
    s.total_pnl_pct = sum(t.pnl_pct * 0.10 for t in trades) * 100
    s.expectancy_r = (
        s.win_rate * (s.avg_win_pct / STOP_PCT)
        + (1 - s.win_rate) * (s.avg_loss_pct / STOP_PCT)
    )
    streak = 0
    max_streak = 0
    for t in trades:
        if t.pnl_pct <= 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    s.max_consec_losses = max_streak
    return s


def run_all(
    tickers: list[str],
    bar_loader: Callable[[str], Sequence[float]],
    strategies: list[StratFn],
) -> dict[str, list[BTTrade]]:
    """Run every strategy across every ticker. Returns trades per strategy."""
    out: dict[str, list[BTTrade]] = {s.__name__: [] for s in strategies}
    for t in tickers:
        try:
            closes = bar_loader(t)
        except Exception:  # noqa: BLE001
            continue
        if len(closes) < MIN_BARS + 2:
            continue
        for strat in strategies:
            trades = backtest_strategy(t, closes, strat)
            out[strat.__name__].extend(trades)
    return out
