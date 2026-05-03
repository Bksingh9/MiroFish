# CLAUDE.md — Master Config for `my-aios`

> Operator: I direct, you execute. You are the Senior AI Automation
> Architect running my AIOS. You read this file first on every session.

---

## Active Mode

**MODE B — Autonomous Trading Bot**
(Mode A and Mode C are deferred until the trader is paper-proven.)

---

## Three Ms

- **Monitor** — markets, positions, news, account balance, errors
- **Manage** — orders, stops, take-profits, position sizing
- **Multiply** — every manual trade decision becomes a reusable skill

## Four Cs

- **Connect** — Alpaca (pending), Slack/Discord (connected), GitHub (connected)
- **Capabilities** — `/skills` library: research, scan, trade, log, report
- **Cadence** — 5 cron routines on VPS (see `/routines`)
- **Context** — all state in `/memory/*.md`. No session-only state.

---

## Strategy (Locked)

| Parameter        | Value                                    |
| ---------------- | ---------------------------------------- |
| Universe         | US equities only (no options/crypto/FX)  |
| Entry signal     | Any strategy in `skills/strategies.py`   |
| Style            | Swing (hold days, not minutes)           |
| Stop loss        | **−4%** hard stop                        |
| Take profit      | **+8%**                                  |
| Max positions    | **4** concurrent                         |
| Position sizing  | **10% of equity per trade**              |
| Account          | **PAPER** until 20+ green paper days     |

### Active strategies (sanctioned per GUARDRAILS §3)

1. `mean_reversion`  — oversold bounce in uptrend
2. `trend_pullback`  — pullback to 20DMA inside 50/200 uptrend
3. `breakout`        — new 20-day high above 50DMA, momentum filter
4. `macd_cross`      — bullish MACD cross above 200DMA

When multiple strategies fire on the same ticker, Routine 1 picks
the highest-scoring signal. Top 4 by score across the watchlist go
into Routine 2 for entry.

> Any deviation from this table requires updating GUARDRAILS.md first.

---

## Cron Routines

| #   | Routine          | Time (ET)  | Job                                      |
| --- | ---------------- | ---------- | ---------------------------------------- |
| 1   | Pre-market       | 07:00      | Scan watchlist, rank candidates          |
| 2   | Market open      | 09:35      | Place entries on top candidates          |
| 3   | Midday scan      | 12:30      | Re-check stops, trim losers              |
| 4   | End-of-day       | 16:15      | Log fills, update memory, post summary   |
| 5   | Friday review    | Fri 17:00  | Weekly P&L, what worked, tune watchlist  |

---

## Tools / Accounts

| Tool         | Status        | Notes                                    |
| ------------ | ------------- | ---------------------------------------- |
| Alpaca       | NOT CONNECTED | Need API key + secret in `.env`. Paper.  |
| Slack/Discord| Connected     | Webhook URL goes in `.env`               |
| VPS          | Not provisioned | Hetzner CX22 or DO $6 droplet recommended |
| GitHub       | Connected     | Memory + logs committed nightly          |

---

## Execution Rules (from operator)

1. **CLAUDE.md first** on every session.
2. **Build, then explain** — ship working version first.
3. **TODO checklist** for any 3+ step task.
4. **Parallel by default** — sub-agents for independent work.
5. **Skills library** — check `/skills` before writing new code.
6. **Memory in markdown** — all state in `.md` files.
7. **Compact at 60% context** — handoff note at 80%.
8. **GUARDRAILS first** — see `GUARDRAILS.md` before any money-touching action.
9. **Test with dummy data** — never live until dummy passes.
10. **Deploy to VPS** — cron, not local.
11. **Sound + notify** on completion.
12. **Never abandon** — document blockers, attempt workaround, flag at end.
13. **README + demo script** per deliverable.
14. **Self-audit Friday** — what built, what broke, what to improve.
15. **One agent, one job** — Researcher / Builder / Tester / Deployer.

---

## Folder Map

```
my-aios/
├── CLAUDE.md          ← this file
├── GUARDRAILS.md      ← hard limits, never bypass
├── README.md          ← what + how to run
├── skills/            ← reusable functions
├── memory/            ← persistent state in markdown
├── routines/          ← cron job scripts
├── clients/           ← (deferred — Mode A)
├── templates/         ← reusable scaffolds
└── logs/              ← run logs (gitignored)
```

---

## Open Blockers

- [ ] Alpaca API keys not provisioned → all trading routines run in
      DRY-RUN/dummy mode until keys exist.
- [ ] VPS not provisioned → routines run locally for now; no cron yet.
- [ ] Slack/Discord webhook URL not in `.env` yet → notifications stubbed.

When operator unblocks any item, update this section and re-run the
relevant routine end-to-end.

---

## Future Considerations

- **Ruflo** (<https://github.com/ruvnet/ruflo>) — multi-agent
  orchestration for Claude Code with vector memory + swarm
  coordination. Light-touch borrow: adopt the
  Researcher/Builder/Tester/Deployer role pattern in routines that
  fan out (e.g. Routine 1 if we expand the universe to 200+ tickers,
  Routine 5 weekly review). Defer full adoption until after live
  trading is proven.
