#!/usr/bin/env python3
"""Routine 5 — Friday weekly review (Fri 17:00 ET).

Self-audit per CLAUDE.md Rule #14. Reads the permanent trade ledger,
slices the last 7 days, computes weekly P&L / win rate / avg R, breaks
out per-ticker behavior, and proposes (but never applies) watchlist
tuning suggestions.

Suggestions only. Strategy is locked per GUARDRAILS — this routine
never edits watchlist.md, GUARDRAILS.md, or CLAUDE.md.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from skills.notify import notify  # noqa: E402
from skills.portfolio import HistoricalTrade, load, read_history  # noqa: E402

STOP_PCT = 0.04  # mirrors GUARDRAILS — used for R calc only
LOOKBACK_DAYS = 7


def planned_risk(t: HistoricalTrade) -> float:
    return t.qty * t.entry * STOP_PCT


def r_multiple(t: HistoricalTrade) -> float:
    risk = planned_risk(t)
    return t.pnl / risk if risk > 0 else 0.0


def main() -> int:
    trades = read_history()
    portfolio = load()
    today = datetime.now().date()
    cutoff = today - timedelta(days=LOOKBACK_DAYS)

    week: list[HistoricalTrade] = []
    for t in trades:
        try:
            d = datetime.strptime(t.date, "%Y-%m-%d").date()
        except ValueError:
            continue
        if d >= cutoff:
            week.append(t)

    if not week:
        body = (
            f"No closed trades in the last {LOOKBACK_DAYS} days. "
            f"Open: {len(portfolio.open_positions)}. "
            f"Cum P&L: ${portfolio.cum_pnl:+,.2f}. "
            f"Paper days: {portfolio.paper_days}/20."
        )
        notify(f"Routine 5 — weekly review {today:%Y-%m-%d}", body)
        print(body)
        return 0

    wins = [t for t in week if t.pnl > 0]
    losses = [t for t in week if t.pnl <= 0]
    weekly_pnl = sum(t.pnl for t in week)
    win_rate = len(wins) / len(week) if week else 0.0
    avg_r = sum(r_multiple(t) for t in week) / len(week)
    avg_win = sum(t.pnl for t in wins) / len(wins) if wins else 0.0
    avg_loss = sum(t.pnl for t in losses) / len(losses) if losses else 0.0
    expectancy = win_rate * avg_win + (1 - win_rate) * avg_loss

    by_ticker: dict[str, list[HistoricalTrade]] = defaultdict(list)
    for t in week:
        by_ticker[t.ticker].append(t)

    ranked = sorted(
        by_ticker.items(),
        key=lambda kv: sum(t.pnl for t in kv[1]),
        reverse=True,
    )
    best = ranked[0]
    worst = ranked[-1]

    # Tuning suggestions (advisory only — never auto-applied).
    suggestions: list[str] = []
    repeat_losers = [
        ticker
        for ticker, ts in by_ticker.items()
        if len(ts) >= 2 and all(t.pnl <= 0 for t in ts)
    ]
    for t in repeat_losers:
        suggestions.append(
            f"Consider removing **{t}** from watchlist — "
            f"{len(by_ticker[t])} losses this week, no wins."
        )
    repeat_winners = [
        (ticker, sum(t.pnl for t in ts))
        for ticker, ts in by_ticker.items()
        if len(ts) >= 2 and all(t.pnl > 0 for t in ts)
    ]
    for ticker, pnl in repeat_winners:
        suggestions.append(
            f"Strong performer **{ticker}** — "
            f"{len(by_ticker[ticker])} wins, ${pnl:+,.2f}. Keep."
        )
    if win_rate < 0.35:
        suggestions.append(
            f"Win rate {win_rate:.0%} is low — review entry signal "
            "calibration with operator before changing GUARDRAILS."
        )
    if not suggestions:
        suggestions.append(
            "No tuning recommended this week — sample size is healthy."
        )

    # Write the report
    report_path = ROOT / "memory" / f"weekly-{today:%Y%m%d}.md"
    lines = [
        f"# Weekly review — week ending {today:%Y-%m-%d}",
        "",
        f"Window: {cutoff:%Y-%m-%d} → {today:%Y-%m-%d} (last {LOOKBACK_DAYS} days)",
        "",
        "## Headline",
        "",
        f"- Trades: **{len(week)}**  ({len(wins)}W / {len(losses)}L)",
        f"- Win rate: **{win_rate:.0%}**",
        f"- Weekly P&L: **${weekly_pnl:+,.2f}**",
        f"- Avg R: **{avg_r:+.2f}R**",
        f"- Avg win / Avg loss: ${avg_win:+,.2f} / ${avg_loss:+,.2f}",
        f"- Expectancy per trade: ${expectancy:+,.2f}",
        f"- Cumulative P&L (lifetime): ${portfolio.cum_pnl:+,.2f}",
        f"- Paper days completed: {portfolio.paper_days}/20",
        "",
        "## Best / worst ticker",
        "",
        f"- 🟢 Best: **{best[0]}** "
        f"({len(best[1])} trades, ${sum(t.pnl for t in best[1]):+,.2f})",
        f"- 🔴 Worst: **{worst[0]}** "
        f"({len(worst[1])} trades, ${sum(t.pnl for t in worst[1]):+,.2f})",
        "",
        "## Per-ticker breakdown",
        "",
        "| Ticker | Trades | W/L | P&L | Avg R |",
        "| ------ | ------ | --- | --- | ----- |",
    ]
    for ticker, ts in ranked:
        w = sum(1 for t in ts if t.pnl > 0)
        l = sum(1 for t in ts if t.pnl <= 0)  # noqa: E741
        pnl = sum(t.pnl for t in ts)
        avg_r_ticker = sum(r_multiple(t) for t in ts) / len(ts)
        lines.append(
            f"| {ticker} | {len(ts)} | {w}/{l} | "
            f"${pnl:+,.2f} | {avg_r_ticker:+.2f}R |"
        )

    lines += ["", "## Tuning suggestions (advisory only)", ""]
    for s in suggestions:
        lines.append(f"- {s}")
    lines += [
        "",
        "> Strategy is locked per GUARDRAILS. Operator must approve any",
        "> watchlist or parameter change. This routine never auto-applies.",
        "",
    ]
    report_path.write_text("\n".join(lines))

    body = (
        f"Week: {len(week)} trades  "
        f"{len(wins)}W/{len(losses)}L  "
        f"P&L ${weekly_pnl:+,.2f}  "
        f"WinRate {win_rate:.0%}  "
        f"AvgR {avg_r:+.2f}  "
        f"Cum ${portfolio.cum_pnl:+,.2f}\n"
        f"Best: {best[0]} (${sum(t.pnl for t in best[1]):+,.2f})  "
        f"Worst: {worst[0]} (${sum(t.pnl for t in worst[1]):+,.2f})"
    )
    notify(f"Routine 5 — weekly review {today:%Y-%m-%d}", body)
    print(body)
    print(f"\nReport: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
