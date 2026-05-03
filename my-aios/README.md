# my-aios — Mode B (Trading Bot)

Autonomous swing-trading AIOS. US equities only, paper-first.
Strategy: **RSI(14) < 35 AND close > SMA(50)**, hard −4% stop, +8% take profit,
max 4 positions, 10% per trade.

> Read `CLAUDE.md` for the operator contract and `GUARDRAILS.md` for hard limits.
> Both files take precedence over this README.

---

## Status

| Component                | Status       |
| ------------------------ | ------------ |
| Folder scaffold          | ✅ Done       |
| CLAUDE.md / GUARDRAILS.md| ✅ Done       |
| Routine 1 — Pre-market   | ✅ Done (dry-run verified) |
| Routine 2 — Market open  | ✅ Done (dry-run verified) |
| Routine 3 — Midday scan  | ✅ Done (dry-run verified) |
| Routine 4 — End-of-day   | ✅ Done (dry-run verified) |
| Routine 5 — Friday review| ⏳ Next       |
| Alpaca connection        | 🚫 Blocker    |
| VPS provisioned          | 🚫 Blocker    |
| Slack/Discord webhook    | 🚫 Blocker    |

---

## Quickstart (local)

```bash
# 1. Configure environment
cp .env.example .env
#   leave TRADING_MODE=dry_run for now

# 2. Run Routine 1 — Pre-market research
python3 routines/routine_01_premarket.py
```

Dry-run uses a deterministic synthetic price series (no API keys needed)
that's tuned to fire ~6 candidates from the seeded watchlist so you can
verify the full pipeline end-to-end.

Output:
- `memory/premarket-YYYYMMDD.md` — ranked report
- Slack/Discord ping (or stdout stub if no webhook configured)

---

## Going to paper

1. Get Alpaca paper API keys: <https://app.alpaca.markets/paper/dashboard/overview>
2. `pip install alpaca-py`
3. Set `.env`:
   ```
   TRADING_MODE=paper
   ALPACA_API_KEY=...
   ALPACA_API_SECRET=...
   ```
4. Re-run Routine 1. It should now pull real Alpaca daily bars.

---

## Going to live (DO NOT until §1 of GUARDRAILS.md is satisfied)

Requires:
- 20+ consecutive paper days with cumulative positive P&L
- Operator types `GO LIVE CONFIRMED` in the operator channel
- `TRADING_MODE=live` and `ALPACA_BASE_URL=https://api.alpaca.markets`

---

## Deploy to VPS (cron)

When the VPS is ready (Hetzner CX22 or DO $6 droplet, Ubuntu 24.04):

```bash
# On the VPS, as the deploy user
git clone <this-repo> ~/my-aios && cd ~/my-aios/my-aios
python3 -m venv .venv && source .venv/bin/activate
pip install alpaca-py
cp .env.example .env  # then edit secrets

# Crontab (times in ET — set TZ in crontab or convert to UTC)
crontab -e
```

Suggested crontab (UTC, assuming summer ET = UTC−4):

```cron
TZ=America/New_York
PATH=/home/deploy/my-aios/my-aios/.venv/bin:/usr/bin

# 1. Pre-market research        (07:00 ET, weekdays)
0 7 * * 1-5  cd /home/deploy/my-aios/my-aios && python routines/routine_01_premarket.py >> logs/cron.log 2>&1

# 2. Market open execution      (09:35 ET)
35 9 * * 1-5 cd /home/deploy/my-aios/my-aios && python routines/routine_02_open.py >> logs/cron.log 2>&1

# 3. Midday scan                (12:30 ET)
30 12 * * 1-5 cd /home/deploy/my-aios/my-aios && python routines/routine_03_midday.py >> logs/cron.log 2>&1

# 4. End-of-day summary         (16:15 ET)
15 16 * * 1-5 cd /home/deploy/my-aios/my-aios && python routines/routine_04_eod.py >> logs/cron.log 2>&1

# 5. Friday weekly review       (Fri 17:00 ET)
0 17 * * 5   cd /home/deploy/my-aios/my-aios && python routines/routine_05_friday.py >> logs/cron.log 2>&1
```

---

## Folder Map

```
my-aios/
├── CLAUDE.md          ← master config (read first)
├── GUARDRAILS.md      ← hard limits (never bypass)
├── README.md          ← you are here
├── .env.example       ← environment template
├── skills/            ← reusable functions
│   ├── indicators.py    RSI, SMA
│   ├── data_provider.py dry-run / Alpaca data resolver
│   └── notify.py        Slack/Discord webhook
├── memory/            ← persistent markdown state
│   ├── watchlist.md     universe scanned by Routine 1
│   ├── portfolio.md     paper portfolio
│   └── premarket-*.md   daily scan reports (generated)
├── routines/
│   └── routine_01_premarket.py
├── templates/         ← reusable scaffolds (TODO)
├── clients/           ← reserved for Mode A
└── logs/              ← run logs (gitignored)
```

---

## 5-minute Demo Script

> Use this when showing the system to anyone (operator, prospective client).

1. **Show the contract** — open `CLAUDE.md`, point at the strategy table
   and the cron table. (30s)
2. **Show the guardrails** — open `GUARDRAILS.md`, point at §1 (paper
   only) and §2 (position limits). (30s)
3. **Run Routine 1 live** —
   `TRADING_MODE=dry_run python3 routines/routine_01_premarket.py`. (60s)
4. **Open the generated report** — `memory/premarket-YYYYMMDD.md`,
   show the candidate table. (60s)
5. **Show notification** — point at the stubbed Slack message in
   stdout, explain that with a webhook this fires to the channel. (30s)
6. **Show the watchlist** — open `memory/watchlist.md`, explain that
   editing this file changes the universe. (30s)
7. **Wrap** — explain the next 4 routines (open, midday, EOD,
   Friday) and the path to live trading. (60s)
