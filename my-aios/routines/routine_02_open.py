#!/usr/bin/env python3
"""Routine 2 — Market open execution (09:35 ET).

Reads today's pre-market report, picks the top candidates ranked by
RSI, sizes positions per GUARDRAILS, and submits bracket orders.

GUARDRAILS enforced:
- Re-reads paper-only / live-allowed gate before any order
- Caps at MAX_POSITIONS concurrent
- 10% of equity per trade, hard −4% stop / +8% target
- Pre-trade intent logged to logs/intent-YYYYMMDD.log
- Pre-trade Slack/Discord ping

Dry-run: no API calls, simulates fills at the report's close price,
updates memory/portfolio.md.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from skills.account import get_account, is_market_open  # noqa: E402
from skills.guardrails import (  # noqa: E402
    GuardrailError,
    build_plan,
    check_can_trade,
    log_intent,
)
from skills.notify import notify  # noqa: E402
from skills.orders import submit_bracket  # noqa: E402
from skills.portfolio import Position, load, save  # noqa: E402


# Rank | Ticker | Strategy | Score | Close | Detail
CANDIDATE_ROW = re.compile(
    r"^\|\s*\d+\s*\|\s*([A-Z.]+)\s*\|\s*([a-z_]+)\s*\|\s*([\d.]+)\s*\|\s*\$([\d.]+)\s*\|"
)


def latest_premarket_report() -> Path | None:
    reports = sorted((ROOT / "memory").glob("premarket-*.md"))
    return reports[-1] if reports else None


def parse_candidates(report: Path) -> list[tuple[str, float, str, float]]:
    """Return [(ticker, close, strategy, score)] from the candidates table."""
    out: list[tuple[str, float, str, float]] = []
    in_section = False
    for line in report.read_text().splitlines():
        if line.startswith("## Ranked candidates") or line.startswith("## Candidates"):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if not in_section:
            continue
        m = CANDIDATE_ROW.match(line)
        if m:
            out.append((m.group(1), float(m.group(4)), m.group(2), float(m.group(3))))
    return out


def main() -> int:
    report = latest_premarket_report()
    if report is None:
        notify("Routine 2 skipped", "No pre-market report found. Run Routine 1 first.")
        print("FATAL: no premarket-*.md in memory/", file=sys.stderr)
        return 2

    candidates = parse_candidates(report)
    if not candidates:
        notify(
            f"Routine 2 — {datetime.now():%Y-%m-%d}",
            f"No candidates in {report.name}. Standing down.",
        )
        print(f"No candidates in {report.name}; nothing to do.")
        return 0

    portfolio = load()

    import os as _os
    portfolio.mode = _os.getenv("TRADING_MODE", portfolio.mode)

    # Refresh equity/buying power from the broker in paper/live so
    # sizing reflects reality, not stale portfolio.md.
    try:
        acct = get_account()
        portfolio.equity = acct.equity
        portfolio.buying_power = acct.buying_power
        if acct.trading_blocked:
            notify(
                "Routine 2 halted",
                "Alpaca reports trading_blocked=True. Standing down.",
            )
            return 1
    except Exception as e:  # noqa: BLE001 — never abandon
        notify(
            "Routine 2 — broker sync failed",
            f"{type(e).__name__}: {e}\nFalling back to portfolio.md state.",
        )

    if not is_market_open():
        notify(
            f"Routine 2 — {datetime.now():%Y-%m-%d}",
            "Market closed. No entries.",
        )
        print("Market closed; nothing to do.")
        return 0

    open_count = len(portfolio.open_positions)
    held = {p.ticker for p in portfolio.open_positions}
    today = datetime.now().strftime("%Y-%m-%d")

    fills: list[str] = []
    skipped: list[str] = []

    for ticker, price, strategy, score in candidates:
        if ticker in held:
            skipped.append(f"{ticker}: already held")
            continue
        try:
            check_can_trade(open_count)
        except GuardrailError as e:
            skipped.append(str(e))
            break  # cap reached → stop trying

        try:
            plan = build_plan(ticker, price, portfolio.equity)
        except GuardrailError as e:
            skipped.append(f"{ticker}: {e}")
            continue

        log_intent(plan, note=f"{strategy}@{score} from {report.name}")

        try:
            fill = submit_bracket(plan)
        except Exception as e:  # noqa: BLE001 — never abandon
            skipped.append(f"{ticker}: order failed — {e}")
            continue

        portfolio.open_positions.append(
            Position(
                ticker=fill.ticker,
                qty=fill.qty,
                entry=fill.fill_price,
                stop=fill.stop,
                target=fill.target,
                opened=today,
            )
        )
        portfolio.buying_power -= fill.qty * fill.fill_price
        portfolio.total_trades += 1
        open_count += 1
        fills.append(
            f"{fill.ticker} x{fill.qty} @ ${fill.fill_price:.2f} "
            f"(stop ${fill.stop:.2f} / tgt ${fill.target:.2f})"
        )

    save(portfolio)

    body_lines = []
    if fills:
        body_lines.append("Filled:")
        body_lines += [f"  • {f}" for f in fills]
    if skipped:
        body_lines.append("Skipped:")
        body_lines += [f"  • {s}" for s in skipped]
    if not fills and not skipped:
        body_lines.append("Nothing to do.")

    notify(f"Routine 2 — open {datetime.now():%Y-%m-%d}", "\n".join(body_lines))
    print("\n".join(body_lines))
    print(f"\nPortfolio now: {len(portfolio.open_positions)} open positions, "
          f"${portfolio.buying_power:,.2f} buying power left.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
