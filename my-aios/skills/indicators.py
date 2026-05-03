"""Indicators. Pure-stdlib so the dry-run path has zero deps."""

from __future__ import annotations

from collections.abc import Sequence


def sma(closes: Sequence[float], period: int) -> float | None:
    if len(closes) < period:
        return None
    window = closes[-period:]
    return sum(window) / period


def sma_series(closes: Sequence[float], period: int) -> list[float | None]:
    out: list[float | None] = []
    for i in range(len(closes)):
        if i + 1 < period:
            out.append(None)
        else:
            out.append(sum(closes[i + 1 - period : i + 1]) / period)
    return out


def rsi(closes: Sequence[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None

    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        change = closes[i] - closes[i - 1]
        if change >= 0:
            gains += change
        else:
            losses -= change

    avg_gain = gains / period
    avg_loss = losses / period

    for i in range(period + 1, len(closes)):
        change = closes[i] - closes[i - 1]
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def ema(closes: Sequence[float], period: int) -> float | None:
    if len(closes) < period:
        return None
    k = 2.0 / (period + 1)
    e = sum(closes[:period]) / period
    for c in closes[period:]:
        e = c * k + e * (1 - k)
    return e


def ema_series(closes: Sequence[float], period: int) -> list[float | None]:
    if len(closes) < period:
        return [None] * len(closes)
    k = 2.0 / (period + 1)
    out: list[float | None] = [None] * (period - 1)
    e = sum(closes[:period]) / period
    out.append(e)
    for c in closes[period:]:
        e = c * k + e * (1 - k)
        out.append(e)
    return out


def macd(
    closes: Sequence[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[float, float, float] | None:
    """Return (macd_line, signal_line, histogram). Standard 12/26/9."""
    if len(closes) < slow + signal:
        return None
    fast_e = ema_series(closes, fast)
    slow_e = ema_series(closes, slow)
    macd_line: list[float] = []
    for f, s in zip(fast_e, slow_e):
        if f is None or s is None:
            continue
        macd_line.append(f - s)
    if len(macd_line) < signal:
        return None
    sig_e = ema_series(macd_line, signal)
    sig = sig_e[-1]
    m = macd_line[-1]
    if sig is None:
        return None
    return m, sig, m - sig


def macd_series(
    closes: Sequence[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> list[tuple[float, float, float] | None]:
    """Per-bar MACD. None where insufficient history."""
    fast_e = ema_series(closes, fast)
    slow_e = ema_series(closes, slow)
    macd_line: list[float | None] = [
        (f - s) if (f is not None and s is not None) else None
        for f, s in zip(fast_e, slow_e)
    ]
    valid_macd = [m for m in macd_line if m is not None]
    sig_partial = ema_series(valid_macd, signal) if valid_macd else []
    out: list[tuple[float, float, float] | None] = []
    sig_idx = 0
    for m in macd_line:
        if m is None:
            out.append(None)
            continue
        s = sig_partial[sig_idx] if sig_idx < len(sig_partial) else None
        sig_idx += 1
        if s is None:
            out.append(None)
        else:
            out.append((m, s, m - s))
    return out


def highest(closes: Sequence[float], period: int) -> float | None:
    if len(closes) < period:
        return None
    return max(closes[-period:])

