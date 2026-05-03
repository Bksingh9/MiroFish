#!/usr/bin/env python3
"""Backtest the strategy registry across the watchlist.

Usage:
    cd my-aios
    python3 scripts/backtest.py [--days N] [--strategy NAME] [--tickers AAPL,MSFT]

Defaults: 500 days, every registered strategy, full watchlist.

Output: summary table to stdout + memory/backtest-YYYYMMDD.md report.

In dry_run, uses synthetic patterns (deterministic — useful for
verifying the engine, NOT for strategy validation). Switch to
TRADING_MODE=paper with valid Alpaca keys to backtest on real bars.
"""

from __future__ import annotations

import argparse
import os
import re
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
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--days", type=int, default=500)
    p.add_argument("--strategy", default=None,
                   help="Run a single strategy by name (e.g. mean_reversion)")
    p.add_argument("--tickers", default=None,
                   help="Comma-separated overrides (default = watchlist)")
    args = p.parse_args()

    from skills.backtest import run_all, stats
    from skills.data_provider import get_closes
    from skills.strategies import STRATEGIES

    strategies = STRATEGIES
    if args.strategy:
        strategies = [s for s in STRATEGIES if s.__name__ == args.strategy]
        if not strategies:
            print(f"unknown strategy: {args.strategy}", file=sys.stderr)
            print("available:", ", ".join(s.__name__ for s in STRATEGIES))
            return 2

    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
    else:
        valid = re.compile(r"^[A-Z]{1,5}(\.[A-Z])?$")
        tickers = [
            line.split("#", 1)[0].strip().upper()
            for line in (ROOT / "memory" / "watchlist.md").read_text().splitlines()
            if valid.match(line.split("#", 1)[0].strip())
        ]

    mode = os.getenv("TRADING_MODE", "dry_run")
    print(f"Backtest — {len(tickers)} tickers, {args.days} days, "
          f"{len(strategies)} strategies, mode={mode}")
    if mode == "dry_run":
        print("⚠️  dry_run uses synthetic patterns — these results are for engine")
        print("   validation only. Set TRADING_MODE=paper to backtest real bars.")
    print()

    def loader(t: str):
        return get_closes(t, days=args.days)

    trades_by_strat = run_all(tickers, loader, strategies)
    summaries = [stats(name, trades) for name, trades in trades_by_strat.items()]
    summaries.sort(key=lambda s: s.expectancy_r, reverse=True)

    # Print table
    header = f"{'Strategy':<18}{'Trades':>7}{'WR%':>6}{'AvgR':>8}{'Exp':>8}{'Tot%':>9}{'Win%':>8}{'Loss%':>8}{'MaxDD':>7}"
    print(header)
    print("-" * len(header))
    for s in summaries:
        print(
            f"{s.strategy:<18}"
            f"{s.trades:>7}"
            f"{int(s.win_rate * 100):>6}"
            f"{s.avg_r:>+8.2f}"
            f"{s.expectancy_r:>+8.2f}"
            f"{s.total_pnl_pct:>+9.2f}"
            f"{s.avg_win_pct * 100:>+8.2f}"
            f"{s.avg_loss_pct * 100:>+8.2f}"
            f"{s.max_consec_losses:>7}"
        )

    # Markdown report
    report_path = ROOT / "memory" / f"backtest-{datetime.now():%Y%m%d}.md"
    lines = [
        f"# Backtest report — {datetime.now():%Y-%m-%d}",
        "",
        f"- Mode: `{mode}`",
        f"- Window: {args.days} days",
        f"- Universe: {len(tickers)} tickers",
        f"- Strategies tested: {len(strategies)}",
        "",
    ]
    if mode == "dry_run":
        lines += [
            "> ⚠️ **Synthetic data warning** — dry_run uses deterministic price",
            "> patterns crafted to fire each strategy at least once. The win",
            "> rates and expectancy below reflect those patterns, not real",
            "> markets. Treat this as engine validation only. Run with",
            "> `TRADING_MODE=paper` and valid Alpaca keys for real backtests.",
            "",
        "## Summary (ranked by expectancy in R)",
        "",
        "| Strategy | Trades | WR% | AvgR | ExpR | Total% | AvgWin% | AvgLoss% | MaxConsLoss |",
        "| -------- | ------ | --- | ---- | ---- | ------ | ------- | -------- | ----------- |",
    ]
    for s in summaries:
        lines.append(
            f"| {s.strategy} | {s.trades} | {s.win_rate * 100:.0f} | "
            f"{s.avg_r:+.2f} | {s.expectancy_r:+.2f} | "
            f"{s.total_pnl_pct:+.2f} | {s.avg_win_pct * 100:+.2f} | "
            f"{s.avg_loss_pct * 100:+.2f} | {s.max_consec_losses} |"
        )
    lines += [
        "",
        "## Notes",
        "",
        "- `Total%` assumes 10% sizing per trade; cumulative simple sum, no compounding.",
        "- `ExpR` is expectancy in stop multiples — positive means edge.",
        "- Stops use close-through approximation; real fills may slip further.",
        "- Strategies with positive `ExpR` and `Trades >= 30` are candidates",
        "  for live deployment per GUARDRAILS §3.",
    ]
    report_path.write_text("\n".join(lines) + "\n")
    print(f"\nReport: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
