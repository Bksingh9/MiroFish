#!/usr/bin/env python3
"""Routine 1 — Pre-market research (07:00 ET).

For every ticker in the watchlist:
  - Pull 80 days of daily closes
  - Compute RSI(14) and SMA(50)
  - Flag candidates where RSI < 35 AND close > SMA(50)

Writes a ranked report to memory/premarket-YYYYMMDD.md and pings
Slack/Discord with the top candidates.

Runs in dry-run mode by default. No orders are placed.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

# Make `skills/` importable when run from any cwd.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from skills.data_provider import get_closes  # noqa: E402
from skills.indicators import rsi, sma  # noqa: E402
from skills.notify import notify  # noqa: E402

RSI_THRESHOLD = 35.0
SMA_PERIOD = 50
RSI_PERIOD = 14
HISTORY_DAYS = 80


def load_watchlist(path: Path) -> list[str]:
    import re

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


def scan(tickers: list[str]) -> list[dict]:
    rows: list[dict] = []
    for t in tickers:
        try:
            closes = get_closes(t, days=HISTORY_DAYS)
        except Exception as e:  # noqa: BLE001 — never abandon
            rows.append({"ticker": t, "error": str(e)})
            continue

        last = closes[-1]
        r = rsi(closes, RSI_PERIOD)
        s = sma(closes, SMA_PERIOD)
        if r is None or s is None:
            rows.append({"ticker": t, "error": "insufficient history"})
            continue

        signal = (r < RSI_THRESHOLD) and (last > s)
        rows.append(
            {
                "ticker": t,
                "close": last,
                "rsi": round(r, 2),
                "sma50": round(s, 2),
                "above_sma": last > s,
                "signal": signal,
            }
        )
    return rows


def render_report(rows: list[dict], when: datetime) -> str:
    candidates = [r for r in rows if r.get("signal")]
    candidates.sort(key=lambda r: r["rsi"])

    lines = [
        f"# Pre-market scan — {when:%Y-%m-%d %H:%M %Z}",
        "",
        f"Mode: `{os.getenv('TRADING_MODE', 'dry_run')}`  ",
        f"Watchlist size: {len(rows)}  ",
        f"Signals: **{len(candidates)}**",
        "",
        "## Candidates (RSI<35 and close>SMA50)",
        "",
    ]
    if not candidates:
        lines.append("_No candidates today._")
    else:
        lines.append("| Rank | Ticker | Close | RSI(14) | SMA(50) |")
        lines.append("| ---- | ------ | ----- | ------- | ------- |")
        for i, r in enumerate(candidates, 1):
            lines.append(
                f"| {i} | {r['ticker']} | ${r['close']:.2f} | "
                f"{r['rsi']:.2f} | ${r['sma50']:.2f} |"
            )

    lines += ["", "## Full scan", "", "| Ticker | Close | RSI | SMA50 | Signal |"]
    lines.append("| ------ | ----- | --- | ----- | ------ |")
    for r in rows:
        if "error" in r:
            lines.append(f"| {r['ticker']} | — | — | — | ERROR: {r['error']} |")
            continue
        flag = "✅" if r["signal"] else ""
        lines.append(
            f"| {r['ticker']} | ${r['close']:.2f} | {r['rsi']:.2f} | "
            f"${r['sma50']:.2f} | {flag} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    when = datetime.now()
    watchlist_path = ROOT / os.getenv("WATCHLIST_PATH", "memory/watchlist.md")
    if not watchlist_path.exists():
        print(f"FATAL: watchlist not found at {watchlist_path}", file=sys.stderr)
        return 2

    tickers = load_watchlist(watchlist_path)
    rows = scan(tickers)
    report = render_report(rows, when)

    out_path = ROOT / "memory" / f"premarket-{when:%Y%m%d}.md"
    out_path.write_text(report)

    candidates = [r for r in rows if r.get("signal")]
    summary = (
        f"{len(candidates)} candidate(s) of {len(tickers)}: "
        + ", ".join(f"{r['ticker']}@RSI{r['rsi']:.1f}" for r in candidates[:5])
        if candidates
        else f"No candidates today ({len(tickers)} scanned)."
    )

    notify(f"Pre-market scan {when:%Y-%m-%d}", summary)
    print(report)
    print(f"\nReport written to: {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
