#!/usr/bin/env python3
"""Routine 4 — End-of-day summary (16:15 ET).

Reconciles open positions with current price one last time, snapshots
the day's results to memory/eod-YYYYMMDD.md, archives closed trades to
the permanent trade-history.md ledger, increments the paper-day
counter, and notifies.

This routine is the boundary between today and tomorrow. After it
runs, closed_today is empty and any positions still open carry over.
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
from skills.portfolio import Closed, archive_closed, load, save  # noqa: E402


def main() -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    portfolio = load()

    # Final stop/target sweep — late-day moves can still trigger.
    still_open = []
    for pos in portfolio.open_positions:
        price = get_intraday_price(pos.ticker, pos.entry)
        if price <= pos.stop:
            result = close_position(pos.ticker, pos.qty, pos.stop)
            pnl = (result.exit_price - pos.entry) * pos.qty
            portfolio.closed_today.append(
                Closed(pos.ticker, pos.qty, pos.entry, result.exit_price, pnl, "STOP_LOSS")
            )
            portfolio.cum_pnl += pnl
            portfolio.buying_power += result.exit_price * pos.qty
        elif price >= pos.target:
            result = close_position(pos.ticker, pos.qty, pos.target)
            pnl = (result.exit_price - pos.entry) * pos.qty
            portfolio.closed_today.append(
                Closed(pos.ticker, pos.qty, pos.entry, result.exit_price, pnl, "TAKE_PROFIT")
            )
            portfolio.cum_pnl += pnl
            portfolio.buying_power += result.exit_price * pos.qty
        else:
            still_open.append(pos)

    portfolio.open_positions = still_open

    # Day stats
    daily_pnl = sum(c.pnl for c in portfolio.closed_today)
    closed_count = len(portfolio.closed_today)
    wins = sum(1 for c in portfolio.closed_today if c.pnl > 0)
    losses = sum(1 for c in portfolio.closed_today if c.pnl <= 0)

    # Snapshot daily report
    eod_path = ROOT / "memory" / f"eod-{datetime.now():%Y%m%d}.md"
    lines = [
        f"# End-of-day summary — {today}",
        "",
        f"- Closed trades today: {closed_count}  ({wins}W / {losses}L)",
        f"- Daily P&L: ${daily_pnl:+,.2f}",
        f"- Cumulative P&L: ${portfolio.cum_pnl:+,.2f}",
        f"- Open carrying overnight: {len(still_open)}",
        "",
        "## Closed today",
        "",
        "| Ticker | Qty | Entry | Exit | P&L | Reason |",
        "| ------ | --- | ----- | ---- | --- | ------ |",
    ]
    if not portfolio.closed_today:
        lines.append("| _none_ |     |       |      |     |        |")
    else:
        for c in portfolio.closed_today:
            lines.append(
                f"| {c.ticker} | {c.qty} | ${c.entry:.2f} | "
                f"${c.exit:.2f} | ${c.pnl:+.2f} | {c.reason} |"
            )

    lines += ["", "## Carrying overnight", "",
              "| Ticker | Qty | Entry | Stop | Target | Opened |",
              "| ------ | --- | ----- | ---- | ------ | ------ |"]
    if not still_open:
        lines.append("| _none_ |     |       |      |        |        |")
    else:
        for p in still_open:
            lines.append(
                f"| {p.ticker} | {p.qty} | ${p.entry:.2f} | "
                f"${p.stop:.2f} | ${p.target:.2f} | {p.opened} |"
            )
    eod_path.write_text("\n".join(lines) + "\n")

    # Archive closed trades to permanent ledger, then roll over.
    archive_closed(portfolio.closed_today, today)
    portfolio.closed_today = []
    portfolio.paper_days += 1
    save(portfolio)

    body = (
        f"{closed_count} closed ({wins}W/{losses}L)  "
        f"Day P&L ${daily_pnl:+,.2f}  Cum ${portfolio.cum_pnl:+,.2f}  "
        f"Carrying {len(still_open)}  "
        f"Paper day {portfolio.paper_days}/20"
    )
    notify(f"Routine 4 — EOD {today}", body)
    print(body)
    print(f"\nReport: {eod_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
