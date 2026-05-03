"""Account & broker-position sync.

Wraps Alpaca account / positions so routines can use real broker state
in paper and live modes. dry_run returns a default $10k account.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class AccountSnapshot:
    equity: float
    buying_power: float
    cash: float
    status: str
    trading_blocked: bool


@dataclass
class BrokerPosition:
    ticker: str
    qty: int
    avg_entry: float
    market_value: float
    unrealized_pnl: float


def _client():
    try:
        from alpaca.trading.client import TradingClient
    except ImportError as e:
        raise RuntimeError(
            "alpaca-py not installed. `pip install alpaca-py` or run in dry_run."
        ) from e

    key = os.environ["ALPACA_API_KEY"]
    secret = os.environ["ALPACA_API_SECRET"]
    paper = os.getenv("TRADING_MODE", "dry_run").lower() == "paper"
    return TradingClient(key, secret, paper=paper)


def get_account() -> AccountSnapshot:
    mode = os.getenv("TRADING_MODE", "dry_run").lower()

    if mode == "dry_run":
        return AccountSnapshot(
            equity=10000.0,
            buying_power=10000.0,
            cash=10000.0,
            status="ACTIVE",
            trading_blocked=False,
        )

    acct = _client().get_account()
    return AccountSnapshot(
        equity=float(acct.equity),
        buying_power=float(acct.buying_power),
        cash=float(acct.cash),
        status=str(acct.status),
        trading_blocked=bool(acct.trading_blocked),
    )


def get_positions() -> list[BrokerPosition]:
    mode = os.getenv("TRADING_MODE", "dry_run").lower()

    if mode == "dry_run":
        return []  # dry_run state lives in portfolio.md only

    positions = _client().get_all_positions()
    out: list[BrokerPosition] = []
    for p in positions:
        out.append(
            BrokerPosition(
                ticker=p.symbol,
                qty=int(float(p.qty)),
                avg_entry=float(p.avg_entry_price),
                market_value=float(p.market_value),
                unrealized_pnl=float(p.unrealized_pl),
            )
        )
    return out


def is_market_open() -> bool:
    """True if US equities market is currently open. dry_run returns True."""
    mode = os.getenv("TRADING_MODE", "dry_run").lower()
    if mode == "dry_run":
        return True
    try:
        return bool(_client().get_clock().is_open)
    except Exception:  # noqa: BLE001
        return False
