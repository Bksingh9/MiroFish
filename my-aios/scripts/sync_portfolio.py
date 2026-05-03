#!/usr/bin/env python3
"""Reconcile memory/portfolio.md with the live Alpaca account.

Run on demand (e.g. after a manual trade in the Alpaca UI, or after
rebuilding state on a fresh VPS). Pulls account snapshot + open
positions, replaces the open-positions table, leaves closed_today
and lifetime stats untouched.

In dry_run this is a no-op (broker is the markdown file itself).
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _load_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())


def main() -> int:
    _load_env()
    from skills.account import get_account, get_positions  # noqa: E402
    from skills.portfolio import Position, load, save  # noqa: E402
    from skills.guardrails import STOP_PCT, TARGET_PCT  # noqa: E402

    mode = os.getenv("TRADING_MODE", "dry_run").lower()
    if mode == "dry_run":
        print("dry_run — broker is portfolio.md itself, nothing to sync.")
        return 0

    print(f"Syncing from Alpaca ({mode}) ...")

    try:
        acct = get_account()
        positions = get_positions()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL — {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    portfolio = load()
    portfolio.mode = mode
    portfolio.equity = acct.equity
    portfolio.buying_power = acct.buying_power

    today = datetime.now().strftime("%Y-%m-%d")
    portfolio.open_positions = [
        Position(
            ticker=p.ticker,
            qty=p.qty,
            entry=p.avg_entry,
            stop=round(p.avg_entry * (1 - STOP_PCT), 2),
            target=round(p.avg_entry * (1 + TARGET_PCT), 2),
            opened=today,  # broker doesn't expose entry date in basic call
        )
        for p in positions
    ]
    save(portfolio)

    print(f"  equity:        ${acct.equity:,.2f}")
    print(f"  buying_power:  ${acct.buying_power:,.2f}")
    print(f"  positions:     {len(positions)}")
    for p in positions:
        print(
            f"    • {p.ticker} x{p.qty} @ ${p.avg_entry:.2f}  "
            f"mv ${p.market_value:,.2f}  upl ${p.unrealized_pnl:+,.2f}"
        )
    print(f"\nportfolio.md updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
