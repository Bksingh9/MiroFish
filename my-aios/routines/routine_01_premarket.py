#!/usr/bin/env python3
"""Routine 1 — Pre-market research (07:00 ET).

For every ticker in the watchlist, run every registered strategy in
skills/strategies.py. When multiple strategies fire on the same
ticker, the highest-scoring one wins. Candidates are then sorted
globally by score; the top MAX_POSITIONS go into Routine 2.

Output:
  memory/premarket-YYYYMMDD.md   ranked report
  Slack/Discord ping             top candidates summary

Runs in dry_run by default. No orders are placed.
"""

from __future__ import annotations

import os
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from skills.data_provider import get_closes  # noqa: E402
from skills.notify import notify  # noqa: E402
from skills.strategies import STRATEGIES, Signal, scan  # noqa: E402

HISTORY_DAYS = 250  # enough for SMA200 + MACD


def load_watchlist(path: Path) -> list[str]:
    valid = re.compile(r"^[A-Z]{1,5}(\.[A-Z])?$")
    tickers: list[str] = []
    for raw in path.read_text().splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        candidate = line.upper()
        if valid.match(candidate):
            tickers.append(candidate)
    return tickers


def best_per_ticker(tickers: list[str]) -> tuple[list[Signal], dict[str, str]]:
    """Return (winning_signal_per_ticker, errors_by_ticker)."""
    winners: list[Signal] = []
    errors: dict[str, str] = {}
    for t in tickers:
        try:
            closes = get_closes(t, days=HISTORY_DAYS)
        except Exception as e:  # noqa: BLE001 — never abandon
            errors[t] = str(e)
            continue
        sigs = scan(t, closes)
        if not sigs:
            continue
        winners.append(max(sigs, key=lambda s: s.score))
    winners.sort(key=lambda s: s.score, reverse=True)
    return winners, errors


def render_report(
    winners: list[Signal],
    errors: dict[str, str],
    total: int,
    when: datetime,
) -> str:
    by_strat = Counter(s.strategy for s in winners)
    lines = [
        f"# Pre-market scan — {when:%Y-%m-%d %H:%M %Z}",
        "",
        f"Mode: `{os.getenv('TRADING_MODE', 'dry_run')}`  ",
        f"Watchlist size: {total}  ",
        f"Strategies registered: {len(STRATEGIES)} "
        f"({', '.join(s.__name__ for s in STRATEGIES)})  ",
        f"Tickers with signals: **{len(winners)}**",
        "",
    ]
    if by_strat:
        lines.append("Hits by strategy: " + ", ".join(
            f"{name}={n}" for name, n in by_strat.most_common()
        ))
        lines.append("")

    lines += ["## Ranked candidates", ""]
    if not winners:
        lines.append("_No candidates today._")
    else:
        lines.append("| Rank | Ticker | Strategy | Score | Close | Detail |")
        lines.append("| ---- | ------ | -------- | ----- | ----- | ------ |")
        for i, s in enumerate(winners, 1):
            lines.append(
                f"| {i} | {s.ticker} | {s.strategy} | {s.score} | "
                f"${s.close:.2f} | {s.detail} |"
            )

    if errors:
        lines += ["", "## Errors", ""]
        for t, err in errors.items():
            lines.append(f"- {t}: {err}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    when = datetime.now()
    watchlist_path = ROOT / os.getenv("WATCHLIST_PATH", "memory/watchlist.md")
    if not watchlist_path.exists():
        print(f"FATAL: watchlist not found at {watchlist_path}", file=sys.stderr)
        return 2

    tickers = load_watchlist(watchlist_path)
    winners, errors = best_per_ticker(tickers)
    report = render_report(winners, errors, len(tickers), when)

    out_path = ROOT / "memory" / f"premarket-{when:%Y%m%d}.md"
    out_path.write_text(report)

    summary = (
        f"{len(winners)}/{len(tickers)} hit signals across "
        f"{len(STRATEGIES)} strategies. Top: "
        + ", ".join(f"{s.ticker}({s.strategy[:4]}@{s.score})" for s in winners[:5])
        if winners
        else f"No candidates today ({len(tickers)} scanned)."
    )
    notify(f"Pre-market scan {when:%Y-%m-%d}", summary)
    print(report)
    print(f"\nReport written to: {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
