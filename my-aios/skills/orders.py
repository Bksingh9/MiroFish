"""Bracket order submission and position close. dry_run simulates fills."""

from __future__ import annotations

import os
from dataclasses import dataclass

from .guardrails import TradePlan


@dataclass
class CloseResult:
    ticker: str
    qty: int
    exit_price: float
    broker_order_id: str | None


@dataclass
class Fill:
    ticker: str
    qty: int
    fill_price: float
    stop: float
    target: float
    broker_order_id: str | None  # None in dry_run


def submit_bracket(plan: TradePlan) -> Fill:
    mode = os.getenv("TRADING_MODE", "dry_run").lower()

    if mode == "dry_run":
        return Fill(
            ticker=plan.ticker,
            qty=plan.qty,
            fill_price=plan.entry,
            stop=plan.stop,
            target=plan.target,
            broker_order_id=None,
        )

    try:
        from alpaca.trading.client import TradingClient
        from alpaca.trading.enums import OrderClass, OrderSide, TimeInForce
        from alpaca.trading.requests import (
            LimitOrderRequest,
            StopLossRequest,
            TakeProfitRequest,
        )
    except ImportError as e:
        raise RuntimeError(
            "alpaca-py not installed. `pip install alpaca-py` or run in dry_run."
        ) from e

    key = os.environ["ALPACA_API_KEY"]
    secret = os.environ["ALPACA_API_SECRET"]
    paper = mode == "paper"
    client = TradingClient(key, secret, paper=paper)

    req = LimitOrderRequest(
        symbol=plan.ticker,
        qty=plan.qty,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY,
        limit_price=plan.entry,
        order_class=OrderClass.BRACKET,
        take_profit=TakeProfitRequest(limit_price=plan.target),
        stop_loss=StopLossRequest(stop_price=plan.stop),
    )
    order = client.submit_order(req)

    return Fill(
        ticker=plan.ticker,
        qty=plan.qty,
        fill_price=float(order.filled_avg_price or plan.entry),
        stop=plan.stop,
        target=plan.target,
        broker_order_id=str(order.id),
    )


def close_position(ticker: str, qty: int, price: float) -> CloseResult:
    """Market-close an open position.

    dry_run: simulates a fill at the supplied price.
    paper/live: submits a market sell on Alpaca.
    """
    mode = os.getenv("TRADING_MODE", "dry_run").lower()

    if mode == "dry_run":
        return CloseResult(
            ticker=ticker, qty=qty, exit_price=price, broker_order_id=None
        )

    try:
        from alpaca.trading.client import TradingClient
        from alpaca.trading.enums import OrderSide, TimeInForce
        from alpaca.trading.requests import MarketOrderRequest
    except ImportError as e:
        raise RuntimeError(
            "alpaca-py not installed. `pip install alpaca-py` or run in dry_run."
        ) from e

    key = os.environ["ALPACA_API_KEY"]
    secret = os.environ["ALPACA_API_SECRET"]
    paper = mode == "paper"
    client = TradingClient(key, secret, paper=paper)

    req = MarketOrderRequest(
        symbol=ticker,
        qty=qty,
        side=OrderSide.SELL,
        time_in_force=TimeInForce.DAY,
    )
    order = client.submit_order(req)
    return CloseResult(
        ticker=ticker,
        qty=qty,
        exit_price=float(order.filled_avg_price or price),
        broker_order_id=str(order.id),
    )
