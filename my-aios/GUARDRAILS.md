# GUARDRAILS.md — Hard Limits

> These rules are non-negotiable. Any code that would violate them must
> refuse to execute and emit a Slack/Discord alert instead.

---

## 1. Account Mode

- Default: **PAPER ACCOUNT ONLY**.
- Live trading is forbidden until BOTH conditions are met:
  - 20+ consecutive trading days on paper with positive cumulative P&L,
    OR explicit signed-off transition note in `memory/go-live.md`.
  - Operator has typed the exact phrase `GO LIVE CONFIRMED` in chat.

## 2. Position Limits

| Limit                       | Value          |
| --------------------------- | -------------- |
| Max concurrent positions    | 4              |
| Max position size           | 10% of equity  |
| Max single-day new entries  | 4              |
| Max daily loss (kill switch)| 5% of equity   |
| Max weekly loss             | 10% of equity  |

If any cap is breached → halt entries, flatten if daily-loss kill
switch trips, alert operator.

## 3. Strategy Lock

- **Entry**: any strategy registered in `skills/strategies.py:STRATEGIES`.
  Operator approves additions. Each strategy must be a pure function
  returning `Signal | None` and must include backtest results showing
  positive expectancy on at least 6 months of bars before being added.
  Currently sanctioned strategies:
  1. `mean_reversion`  — RSI(14)<35 AND close > SMA(50)
  2. `trend_pullback`  — close>SMA(200), SMA(50)>SMA(200), close near SMA(20), RSI 40-55
  3. `breakout`        — new 20-day high, close>SMA(50), RSI 55-80
  4. `macd_cross`      — MACD bullish cross, close>SMA(200), positive histogram
- **Exit (universal)**: `−4%` hard stop / `+8%` take profit. No
  discretionary widening of stops. Trailing stop optional only after
  +4%. Same exit applies to every strategy.
- **Universe**: US equities, average daily volume > 500k shares,
  price between $5 and $500, no penny stocks, no leveraged ETFs.
- No options. No crypto. No FX. No shorting. No margin > 1.0x.

## 4. Money-touching Actions

Before any of the following the bot MUST:

1. Re-read this file.
2. Verify dry-run flag in `.env` (`TRADING_MODE=paper|dry_run|live`).
3. Log the intent to `logs/intent-YYYYMMDD.log` BEFORE the API call.
4. Send a pre-trade Slack/Discord ping.

Money-touching actions: place order, cancel order, modify stop,
liquidate, withdraw, transfer.

## 5. API Keys & Secrets

- Never commit `.env`, key files, or anything matching `*secret*`.
- `.gitignore` MUST include `.env`, `logs/`, `memory/portfolio-live.md`.
- Keys live on the VPS only. Never echo them in logs or notifications.

## 6. Failure Modes

| Failure                          | Action                                    |
| -------------------------------- | ----------------------------------------- |
| Alpaca API down                  | Skip cycle, alert, retry next cron        |
| Data feed stale > 15 min         | No new entries this cycle                 |
| Conflicting signal (long + stop) | Cancel both, alert, manual review         |
| Bot crashes mid-order            | Persist intent, reconcile on next start   |
| Operator types `HALT` in chat    | Cancel all open orders, do not enter new  |

## 7. Override Phrases

Only the operator can use these. Bot must verify the message comes
from the operator's authenticated channel.

- `HALT` — stop all new entries, hold existing positions.
- `FLATTEN` — close all positions at market, then HALT.
- `GO LIVE CONFIRMED` — flip from paper → live (only if §1 satisfied).
- `RESUME` — undo HALT.

## 8. What the Bot Will NEVER Do

- Trade outside US equities.
- Take a position larger than 10% of equity.
- Hold more than 4 positions.
- Move a stop further from price than its initial −4%.
- Place an order without a stop attached.
- Skip the GUARDRAILS check to "make up time."
- Edit this file without operator confirmation in chat.
