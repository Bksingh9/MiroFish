#!/usr/bin/env python3
"""One-shot Alpaca validator. Run from any host with internet egress.

Usage:
    cd my-aios
    python3 scripts/check_alpaca.py

Reports auth, account status, market clock, and a sample bar pull.
Prints PASS / FAIL for each step. No orders are placed.
"""

from __future__ import annotations

import os
import sys
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


def _mask(s: str) -> str:
    if len(s) <= 8:
        return "*" * len(s)
    return s[:4] + "*" * (len(s) - 8) + s[-4:]


def main() -> int:
    _load_env()

    print("Alpaca check — runs in 4 steps, no orders placed.")
    print("=" * 60)

    # 1. Env
    print("\n[1/4] Environment")
    key = os.getenv("ALPACA_API_KEY", "").strip()
    secret = os.getenv("ALPACA_API_SECRET", "").strip()
    mode = os.getenv("TRADING_MODE", "dry_run").lower()
    if not key or not secret:
        print("  FAIL — ALPACA_API_KEY or ALPACA_API_SECRET missing in .env")
        return 1
    if mode == "live":
        print("  FAIL — TRADING_MODE=live. Refusing to validate against live.")
        print("         This script is for paper validation only.")
        return 1
    print(f"  PASS — Key {_mask(key)}, Secret {_mask(secret)}, mode={mode}")

    # 2. SDK
    print("\n[2/4] alpaca-py import")
    try:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame
        from alpaca.trading.client import TradingClient
    except ImportError:
        print("  FAIL — alpaca-py not installed. Run: pip install alpaca-py")
        return 1
    print("  PASS")

    # 3. Auth + account info
    print("\n[3/4] Trading API — auth + account")
    try:
        tc = TradingClient(key, secret, paper=True)
        acct = tc.get_account()
    except Exception as e:  # noqa: BLE001
        print(f"  FAIL — {type(e).__name__}: {e}")
        print("         Common causes:")
        print("           • Wrong key/secret pair (regenerate in dashboard)")
        print("           • Network blocked (firewall, proxy, sandbox)")
        print("           • Wrong base URL (paper vs live)")
        return 1
    print(f"  PASS — account_id={acct.id}")
    print(f"         status:        {acct.status}")
    print(f"         equity:        ${float(acct.equity):,.2f}")
    print(f"         buying_power:  ${float(acct.buying_power):,.2f}")
    print(f"         cash:          ${float(acct.cash):,.2f}")
    print(f"         pdt:           {acct.pattern_day_trader}")
    print(f"         trading_blocked: {acct.trading_blocked}")

    if acct.trading_blocked:
        print("  WARN — trading is blocked on this account")

    # Market clock
    try:
        clock = tc.get_clock()
        print(f"         market_open:   {clock.is_open}")
        print(f"         next_open:     {clock.next_open}")
    except Exception as e:  # noqa: BLE001
        print(f"  WARN — clock fetch failed: {e}")

    # 4. Market data smoke test
    print("\n[4/4] Market Data API — fetch 5d AAPL daily bars")
    try:
        from datetime import UTC, datetime, timedelta

        dc = StockHistoricalDataClient(key, secret)
        end = datetime.now(UTC)
        req = StockBarsRequest(
            symbol_or_symbols="AAPL",
            timeframe=TimeFrame.Day,
            start=end - timedelta(days=10),
            end=end,
        )
        bars = dc.get_stock_bars(req).data.get("AAPL", [])
        if not bars:
            print("  WARN — no bars returned (market may be closed during fetch window)")
        else:
            last = bars[-1]
            print(f"  PASS — {len(bars)} bars, last close ${float(last.close):,.2f} on {last.timestamp:%Y-%m-%d}")
    except Exception as e:  # noqa: BLE001
        print(f"  FAIL — {type(e).__name__}: {e}")
        return 1

    print("\n" + "=" * 60)
    print("All checks passed. Paper mode is wired correctly.")
    print("\nNext steps:")
    print("  python3 routines/routine_01_premarket.py")
    print("  python3 scripts/sync_portfolio.py     # pull real broker state")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
