# Trading Playbook — `my-aios` Mode B

US equities, swing trades, paper-first. Pure mechanical strategy —
no discretion, no overrides except the kill switches in §6.

---

## 1. Universe & filters

- US equities only (no options, crypto, FX, futures, OTC, ADRs).
- Price between **$5 and $500**.
- Average daily volume > 500k shares.
- No leveraged ETFs (TQQQ/SQQQ/SOXL/etc.), no inverse, no penny stocks.
- Watchlist lives in `memory/watchlist.md` — one ticker per line.

---

## 2. Entry strategies (any one fires → candidate)

All strategies share the same exit and risk profile. Variation is
on entry signal only.

| #   | Strategy        | Entry condition                                                          |
| --- | --------------- | ------------------------------------------------------------------------ |
| 1   | `mean_reversion`| RSI(14) < 35 **AND** close > SMA(50)                                     |
| 2   | `trend_pullback`| close > SMA(200), SMA(50) > SMA(200), close within 1% of SMA(20), RSI 40–55 |
| 3   | `breakout`      | New 20-day high, close > SMA(50), RSI 55–80                              |
| 4   | `macd_cross`    | MACD line crosses above signal line, close > SMA(200), histogram > 0     |

When multiple strategies fire on the same ticker, the highest-scoring
signal wins. Implementation: `skills/strategies.py`.

---

## 3. Exit (universal)

Every position enters as a **bracket order** at submission:

- **Stop loss**: `entry × 0.96` (–4%). Hard. Never widened.
- **Take profit**: `entry × 1.08` (+8%). Triggers `2R` win.
- **Time stop**: 30 trading days. Anything still open closes at next
  market.
- **No trailing stop** until +4% unrealized. Optional thereafter.

Risk-reward: **1:2** by construction. Strategy-agnostic.

---

## 4. Position sizing & limits

| Limit                       | Value          |
| --------------------------- | -------------- |
| Position size               | 10% of equity  |
| Max concurrent positions    | 4              |
| Max new entries per day     | 4              |
| Daily drawdown kill switch  | −5% of equity  |
| Weekly drawdown kill switch | −10% of equity |

Whole shares only. If 10% of equity can't afford 1 share at the
entry price, skip the candidate (price too high for the account).

---

## 5. Daily flow (cron, US Eastern)

| Time   | Routine                  | What it does                                            |
| ------ | ------------------------ | ------------------------------------------------------- |
| 07:00  | `routine_01_premarket`   | Scan watchlist with all 4 strategies, rank by score     |
| 09:35  | `routine_02_open`        | Submit brackets on top 4 candidates (after open + dust) |
| 12:30  | `routine_03_midday`      | Reconcile open positions, log unrealized P&L            |
| 16:15  | `routine_04_eod`         | Sweep stops/targets, archive closed trades, snapshot    |
| Fri 17 | `routine_05_friday`      | Weekly P&L, win rate, R-multiple, tuning suggestions    |

Each routine writes a markdown report into `memory/` and pings
Slack/Discord. State is durable — re-running a routine on the same
day is idempotent for reads, append-only for the trade ledger.

---

## 6. Kill switches (operator-only, typed in operator channel)

- `HALT` — block new entries, hold open positions.
- `FLATTEN` — close all positions at market, then HALT.
- `RESUME` — undo HALT.
- `GO LIVE CONFIRMED` — required (with `memory/go-live.md` containing
  the same phrase) to flip from paper to live.

The bot also self-halts when:
- Alpaca reports `trading_blocked=True` on the account.
- Daily drawdown exceeds −5%.
- Any pre-trade GUARDRAILS check fails.

---

## 7. Pre-trade checklist (enforced in code, not optional)

1. `TRADING_MODE` is `dry_run` or `paper`. `live` requires §8.
2. `Alpaca account.trading_blocked` is False.
3. Open position count < 4.
4. Candidate's price is in $5–$500.
5. 10% of equity affords ≥ 1 share.
6. Bracket order has stop AND target attached.
7. Intent line written to `logs/intent-YYYYMMDD.log` **before** the
   API call.
8. Pre-trade Slack/Discord ping sent.

Implementation: `skills/guardrails.py:check_can_trade` +
`build_plan` + `log_intent`.

---

## 8. Path from paper to live

Live trading is gated. All four conditions must hold:

1. **20 consecutive paper trading days completed**, tracked in
   `memory/portfolio.md` `paper_days` counter.
2. **Cumulative paper P&L positive** at the end of the 20-day window.
3. **Routine 5 weekly review** shows positive expectancy in R for
   the active strategy registry.
4. **Operator action**:
   - Type `GO LIVE CONFIRMED` in the operator channel.
   - Create `memory/go-live.md` containing that exact phrase.
   - Generate a **separate** live API key/secret pair (never reuse paper).
   - Update `.env`:
     ```
     TRADING_MODE=live
     ALPACA_BASE_URL=https://api.alpaca.markets
     ALPACA_API_KEY=<new live key>
     ALPACA_API_SECRET=<new live secret>
     ```

For the **first 5 live trading days**, override sizing to 2% per
trade by setting `MAX_POSITION_PCT=0.02` in `.env`. Then back to
0.10 after 5 green days live.

---

## 9. Strategy admission (adding new strategies)

Strategy lock applies. New entry strategies are admitted only when:

1. Pure function `Signal | None` lives in `skills/strategies.py`.
2. Backtested via `scripts/backtest.py --strategy <name> --days 1000`
   on real Alpaca bars (paper-mode data).
3. Backtest result: **trades ≥ 30** AND **expectancy > 0R**.
4. Operator approves the strategy by name.
5. Strategy listed in CLAUDE.md "Active strategies" and GUARDRAILS.md §3.

Stop / target / sizing are NEVER strategy-specific. Universal exit.

---

## 10. Daily commands (operator side)

```bash
# Validate keys + connectivity (run after every key rotation)
python3 scripts/check_alpaca.py

# Pull broker state into portfolio.md (after manual UI edits or VPS rebuild)
python3 scripts/sync_portfolio.py

# Compare strategies on real bars (decide which to keep enabled)
python3 scripts/backtest.py --days 1000

# Manually trigger a routine (cron does this automatically)
python3 routines/routine_01_premarket.py

# Run the whole pipeline offline with synthetic data (smoke test)
TRADING_MODE=dry_run python3 routines/routine_01_premarket.py \
  && TRADING_MODE=dry_run python3 routines/routine_02_open.py \
  && TRADING_MODE=dry_run python3 routines/routine_03_midday.py \
  && TRADING_MODE=dry_run python3 routines/routine_04_eod.py
```

---

## 11. Reading the daily reports

| File                          | What it tells you                                       |
| ----------------------------- | ------------------------------------------------------- |
| `memory/premarket-YYYYMMDD.md`| What the bot saw at 07:00 — ranked candidates           |
| `memory/eod-YYYYMMDD.md`      | What actually happened today — wins, losses, carryover  |
| `memory/weekly-YYYYMMDD.md`   | Friday review — win rate, expectancy, tuning hints      |
| `memory/backtest-YYYYMMDD.md` | Strategy comparison from the most recent backtest       |
| `memory/trade-history.md`     | Permanent ledger — every closed trade, append-only      |
| `memory/portfolio.md`         | Current state — equity, BP, open positions, paper days  |
| `logs/intent-YYYYMMDD.log`    | Pre-API record of every order intent                    |

Treat `portfolio.md` as the local source of truth in dry_run, and
the broker (Alpaca) as truth in paper/live — `sync_portfolio.py`
reconciles.

---

## 12. Watchlist hygiene

- One ticker per line. Comments after `#` ignored.
- Default: ~25 large-cap, liquid US equities across sectors.
- Routine 5 flags repeat losers — operator decides whether to remove.
- Routine 5 flags repeat winners — operator decides whether to keep.
- Watchlist mutations are operator-only. Routines never auto-edit it.

---

## 13. What NOT to do

- ❌ Override the −4% / +8% bracket "just this once."
- ❌ Hold a position through earnings without explicit operator OK.
- ❌ Increase position size to recover a drawdown.
- ❌ Add a strategy that hasn't passed §9 admission.
- ❌ Run live without §8 satisfied.
- ❌ Commit `.env`, intent logs, or live portfolio state to git.
- ❌ Skip the pre-trade intent log to "save time" during volatility.

---

## 14. One-line summary

**4 strategies, 4 max positions, 10% sizing, 1:2 risk-reward,
paper-only until 20 green days, intent-logged before every order,
strategy lock enforced by code, kill switches always available.**
