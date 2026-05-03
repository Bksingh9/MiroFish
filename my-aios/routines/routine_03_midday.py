#!/usr/bin/env python3
"""Routine 3 — Midday scan (12:30 ET).

For every open position, fetch the current price and:
  - close at stop if price ≤ stop      (STOP_LOSS)
  - close at target if price ≥ target  (TAKE_PROFIT)
  - else hold and report unrealized P&L

In paper/live mode this is mostly reconciliation — Alpaca's bracket
order will already have triggered. In dry_run we actually execute the
close so portfolio.md stays consistent.

GUARDRAILS: stops/targets are NEVER widened. This routine only closes,
never modifies, open orders.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from skills.data_provider import get_intraday_price  # noqa: E402
from skills.notify import notify  # noqa: E402
from skills.orders import close_position  # noqa: E402
from skills.portfolio import Closed, load, save  # noqa: E402


def main() -> int:
    portfolio = load()
    if not portfolio.open_positions:
        notify(
            f"Routine 3 — midday {datetime.now():%Y-%m-%d}",
            "No open positions. Nothing to scan.",
        )
        print("No open positions.")
        return 0

    still_open = []
    closed_lines: list[str] = []
    held_lines: list[str] = []

    for pos in portfolio.open_positions:
        price = get_intraday_price(pos.ticker, pos.entry)
        unrealized = (price - pos.entry) * pos.qty

        if price <= pos.stop:
            result = close_position(pos.ticker, pos.qty, pos.stop)
            pnl = (result.exit_price - pos.entry) * pos.qty
            portfolio.closed_today.append(
                Closed(
                    ticker=pos.ticker,
                    qty=pos.qty,
                    entry=pos.entry,
                    exit=result.exit_price,
                    pnl=pnl,
                    reason="STOP_LOSS",
                )
            )
            portfolio.cum_pnl += pnl
            portfolio.buying_power += result.exit_price * pos.qty
            closed_lines.append(
                f"STOP {pos.ticker} x{pos.qty} @ ${result.exit_price:.2f} "
                f"(P&L ${pnl:+.2f})"
            )
        elif price >= pos.target:
            result = close_position(pos.ticker, pos.qty, pos.target)
            pnl = (result.exit_price - pos.entry) * pos.qty
            portfolio.closed_today.append(
                Closed(
                    ticker=pos.ticker,
                    qty=pos.qty,
                    entry=pos.entry,
                    exit=result.exit_price,
                    pnl=pnl,
                    reason="TAKE_PROFIT",
                )
            )
            portfolio.cum_pnl += pnl
            portfolio.buying_power += result.exit_price * pos.qty
            closed_lines.append(
                f"TGT {pos.ticker} x{pos.qty} @ ${result.exit_price:.2f} "
                f"(P&L ${pnl:+.2f})"
            )
        else:
            still_open.append(pos)
            held_lines.append(
                f"{pos.ticker} x{pos.qty} entry ${pos.entry:.2f} → "
                f"${price:.2f} ({unrealized:+.2f})"
            )

    portfolio.open_positions = still_open
    save(portfolio)

    body = []
    if closed_lines:
        body.append("Closed:")
        body += [f"  • {line}" for line in closed_lines]
    if held_lines:
        body.append("Holding:")
        body += [f"  • {line}" for line in held_lines]
    body.append(
        f"\nOpen now: {len(still_open)} | "
        f"Cumulative P&L: ${portfolio.cum_pnl:+,.2f} | "
        f"BP: ${portfolio.buying_power:,.2f}"
    )

    notify(f"Routine 3 — midday {datetime.now():%Y-%m-%d}", "\n".join(body))
    print("\n".join(body))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
