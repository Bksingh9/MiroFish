"""Runtime enforcement of GUARDRAILS.md.

Every routine that touches money MUST call check_can_trade() and
log_intent() before any order submission.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"

MAX_POSITIONS = 4
MAX_POSITION_PCT = 0.10
MAX_DAILY_LOSS_PCT = 0.05
MAX_WEEKLY_LOSS_PCT = 0.10
STOP_PCT = 0.04
TARGET_PCT = 0.08
PRICE_MIN = 5.0
PRICE_MAX = 500.0


@dataclass
class TradePlan:
    ticker: str
    side: str  # "buy" only for now
    qty: int
    entry: float
    stop: float
    target: float


class GuardrailError(RuntimeError):
    pass


def is_live_allowed() -> bool:
    """Live trading requires explicit go-live note + confirmed env."""
    mode = os.getenv("TRADING_MODE", "dry_run").lower()
    if mode != "live":
        return True  # dry_run/paper always allowed
    go_live = ROOT / "memory" / "go-live.md"
    if not go_live.exists():
        return False
    text = go_live.read_text()
    return "GO LIVE CONFIRMED" in text


def check_can_trade(open_count: int) -> None:
    if not is_live_allowed():
        raise GuardrailError(
            "Live mode requested but memory/go-live.md is missing or "
            "does not contain 'GO LIVE CONFIRMED'."
        )
    if open_count >= MAX_POSITIONS:
        raise GuardrailError(
            f"Max positions reached ({open_count}/{MAX_POSITIONS}); "
            "no new entries this cycle."
        )


def size_position(equity: float, price: float) -> int:
    """Return whole-share qty for a 10%-of-equity position."""
    if not (PRICE_MIN <= price <= PRICE_MAX):
        raise GuardrailError(
            f"Price ${price:.2f} outside allowed range "
            f"[${PRICE_MIN}, ${PRICE_MAX}]"
        )
    dollars = equity * MAX_POSITION_PCT
    return max(int(dollars // price), 0)


def build_plan(ticker: str, price: float, equity: float) -> TradePlan:
    qty = size_position(equity, price)
    if qty < 1:
        raise GuardrailError(
            f"{ticker}: 10% of ${equity:.2f} can't afford 1 share at ${price:.2f}"
        )
    return TradePlan(
        ticker=ticker,
        side="buy",
        qty=qty,
        entry=price,
        stop=round(price * (1 - STOP_PCT), 2),
        target=round(price * (1 + TARGET_PCT), 2),
    )


def log_intent(plan: TradePlan, note: str = "") -> Path:
    """Write trade intent to disk BEFORE any API call. Required by GUARDRAILS §4."""
    LOG_DIR.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    path = LOG_DIR / f"intent-{today}.log"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = (
        f"{ts}\t{plan.side.upper()}\t{plan.ticker}\tqty={plan.qty}\t"
        f"entry=${plan.entry:.2f}\tstop=${plan.stop:.2f}\t"
        f"target=${plan.target:.2f}\tnote={note}\n"
    )
    with path.open("a") as f:
        f.write(line)
    return path
