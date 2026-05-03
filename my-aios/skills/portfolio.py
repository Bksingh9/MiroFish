"""Portfolio state I/O.

Reads and rewrites memory/portfolio.md. Format is a markdown table
that's both human-readable and machine-parseable. The file is the
single source of truth for paper account state in dry_run mode.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORTFOLIO_PATH = ROOT / "memory" / "portfolio.md"


@dataclass
class Position:
    ticker: str
    qty: int
    entry: float
    stop: float
    target: float
    opened: str  # YYYY-MM-DD


@dataclass
class Closed:
    ticker: str
    qty: int
    entry: float
    exit: float
    pnl: float
    reason: str


@dataclass
class HistoricalTrade:
    date: str
    ticker: str
    qty: int
    entry: float
    exit: float
    pnl: float
    reason: str


@dataclass
class Portfolio:
    mode: str = "dry_run"
    equity: float = 10000.0
    buying_power: float = 10000.0
    last_updated: str = "never"
    open_positions: list[Position] = field(default_factory=list)
    closed_today: list[Closed] = field(default_factory=list)
    total_trades: int = 0
    cum_pnl: float = 0.0
    paper_days: int = 0


def _parse_table(lines: list[str], start: int) -> tuple[list[list[str]], int]:
    rows: list[list[str]] = []
    i = start
    while i < len(lines) and lines[i].lstrip().startswith("|"):
        cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
        rows.append(cells)
        i += 1
    return rows, i


def _money(s: str) -> float:
    return float(s.replace("$", "").replace(",", "").strip())


def load() -> Portfolio:
    if not PORTFOLIO_PATH.exists():
        return Portfolio()

    text = PORTFOLIO_PATH.read_text()
    p = Portfolio()

    m = re.search(r"-\s*Mode:\s*`?([\w_]+)`?", text)
    if m:
        p.mode = m.group(1)
    m = re.search(r"-\s*Equity:\s*\$?([\d_,.]+)", text)
    if m:
        try:
            p.equity = _money(m.group(1))
        except ValueError:
            pass
    m = re.search(r"-\s*Buying power:\s*\$?([\d_,.]+)", text)
    if m:
        try:
            p.buying_power = _money(m.group(1))
        except ValueError:
            pass
    m = re.search(r"-\s*Last updated:\s*(.+)", text)
    if m:
        p.last_updated = m.group(1).strip()
    m = re.search(r"-\s*Total trades:\s*(\d+)", text)
    if m:
        p.total_trades = int(m.group(1))
    m = re.search(r"-\s*Cumulative P&L:\s*\$?\+?(-?[\d.,]+)", text)
    if m:
        try:
            p.cum_pnl = _money(m.group(1))
        except ValueError:
            pass
    m = re.search(r"-\s*Paper days completed:\s*(\d+)", text)
    if m:
        p.paper_days = int(m.group(1))

    lines = text.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("## Open positions"):
            j = i + 1
            while j < len(lines) and not lines[j].lstrip().startswith("| Ticker"):
                j += 1
            if j >= len(lines):
                continue
            rows, _ = _parse_table(lines, j + 2)
            for r in rows:
                if len(r) < 7 or r[0] in ("_none_", ""):
                    continue
                p.open_positions.append(
                    Position(
                        ticker=r[0],
                        qty=int(r[1]),
                        entry=_money(r[2]),
                        stop=_money(r[3]),
                        target=_money(r[4]),
                        opened=r[6],
                    )
                )
        elif stripped.startswith("## Closed today"):
            j = i + 1
            while j < len(lines) and not lines[j].lstrip().startswith("| Ticker"):
                j += 1
            if j >= len(lines):
                continue
            rows, _ = _parse_table(lines, j + 2)
            for r in rows:
                if len(r) < 6 or r[0] in ("_none_", ""):
                    continue
                p.closed_today.append(
                    Closed(
                        ticker=r[0],
                        qty=int(r[1]),
                        entry=_money(r[2]),
                        exit=_money(r[3]),
                        pnl=_money(r[4].replace("+", "")),
                        reason=r[5],
                    )
                )

    return p


def save(p: Portfolio) -> None:
    p.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Portfolio — Paper Account",
        "",
        "> Authoritative state for the paper portfolio. Updated by routines 2/3/4.",
        "> Live state lives in `portfolio-live.md` (gitignored) once we go live.",
        "",
        "## Account",
        "",
        f"- Mode: `{p.mode}`",
        f"- Equity: ${p.equity:,.2f}",
        f"- Buying power: ${p.buying_power:,.2f}",
        f"- Last updated: {p.last_updated}",
        "",
        "## Open positions",
        "",
        "| Ticker | Qty | Entry | Stop | Target | P&L | Opened |",
        "| ------ | --- | ----- | ---- | ------ | --- | ------ |",
    ]
    if not p.open_positions:
        lines.append("| _none_ |     |       |      |        |     |        |")
    else:
        for pos in p.open_positions:
            lines.append(
                f"| {pos.ticker} | {pos.qty} | ${pos.entry:.2f} | "
                f"${pos.stop:.2f} | ${pos.target:.2f} | — | {pos.opened} |"
            )

    lines += [
        "",
        "## Closed today",
        "",
        "| Ticker | Qty | Entry | Exit | P&L | Reason |",
        "| ------ | --- | ----- | ---- | --- | ------ |",
    ]
    if not p.closed_today:
        lines.append("| _none_ |     |       |      |     |        |")
    else:
        for c in p.closed_today:
            lines.append(
                f"| {c.ticker} | {c.qty} | ${c.entry:.2f} | "
                f"${c.exit:.2f} | ${c.pnl:+.2f} | {c.reason} |"
            )

    lines += [
        "",
        "## Lifetime stats",
        "",
        f"- Total trades: {p.total_trades}",
        "- Win rate: —",
        "- Avg R: —",
        f"- Cumulative P&L: ${p.cum_pnl:+,.2f}",
        f"- Paper days completed: {p.paper_days} / 20 required for live",
        "",
    ]
    PORTFOLIO_PATH.write_text("\n".join(lines))


HISTORY_PATH = ROOT / "memory" / "trade-history.md"


def read_history() -> list[HistoricalTrade]:
    """Parse memory/trade-history.md back into trade records."""
    if not HISTORY_PATH.exists():
        return []
    trades: list[HistoricalTrade] = []
    for line in HISTORY_PATH.read_text().splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 7 or cells[0] in ("Date", "----"):
            continue
        try:
            trades.append(
                HistoricalTrade(
                    date=cells[0],
                    ticker=cells[1],
                    qty=int(cells[2]),
                    entry=_money(cells[3]),
                    exit=_money(cells[4]),
                    pnl=_money(cells[5].replace("+", "")),
                    reason=cells[6],
                )
            )
        except (ValueError, IndexError):
            continue
    return trades


def archive_closed(closed: list[Closed], session_date: str) -> None:
    """Append today's closed trades to memory/trade-history.md.

    Creates the file with a header on first call. Each row is a single
    closed trade so the file accumulates a permanent ledger.
    """
    if not closed:
        return
    new_file = not HISTORY_PATH.exists()
    with HISTORY_PATH.open("a") as f:
        if new_file:
            f.write("# Trade History\n\n")
            f.write("> Permanent ledger of all closed trades. Append-only.\n\n")
            f.write("| Date | Ticker | Qty | Entry | Exit | P&L | Reason |\n")
            f.write("| ---- | ------ | --- | ----- | ---- | --- | ------ |\n")
        for c in closed:
            f.write(
                f"| {session_date} | {c.ticker} | {c.qty} | "
                f"${c.entry:.2f} | ${c.exit:.2f} | "
                f"${c.pnl:+.2f} | {c.reason} |\n"
            )
