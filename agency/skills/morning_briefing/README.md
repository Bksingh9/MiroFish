# Morning Briefing Skill

Daily 8am briefing pulled from Gmail + the operations Google Sheet, synthesized by Claude Opus 4.7.

## What it does

Reads:
- Last 24h of Gmail inbox (subjects, senders, snippets — never message bodies, keeps tokens cheap)
- "Today" tab of the ops sheet (today's tasks)
- "Pipeline" tab of the ops sheet (active leads + outreach status)

Synthesizes into 4 sections:
1. **INBOX — TOP 3** with suggested actions
2. **TODAY** — top 3 tasks
3. **PIPELINE** — overdue follow-ups flagged
4. **THE ONE THING** — the single sharpest recommendation for the day

## Why Opus 4.7 + adaptive thinking

The briefing requires triage judgment (which email actually matters, which lead is actually overdue, what's the single sharpest move). That's the kind of multi-step reasoning where adaptive thinking earns its keep. Effort `high` is the floor for intelligence-sensitive work — we'd waste tokens at `low`.

## Why prompt caching

The persona block is ~2K tokens of stable instructions. With `cache_control: ephemeral` on it, every run after the first reads from cache (≈10× cheaper). Daily runs will hit a fresh cache because the 5-min TTL expires overnight, but within a working session (e.g. running the briefing twice while debugging) the cache hits.

To upgrade to 1-hour TTL when running multiple times per day, change `cache_control` to `{"type": "ephemeral", "ttl": "1h"}` — but it costs 2× to write, so stick with the default unless you're batching runs.

## Running

```bash
cd agency
source .venv/bin/activate
python skills/morning_briefing/morning_briefing.py
```

First run launches a browser for Google OAuth. The token persists at `config/google_token.json`.

## Costs

Per run, with a typical inbox (~20 emails) and pipeline (~30 leads):
- Input: ~3K tokens (mostly the JSON payload)
- Output: ~600 tokens
- Cost: ~$0.03/run on Opus 4.7 = **~$0.90/month** if run daily

When we hand this to a paying client at $200/mo as part of Product 1 (Smart Inbox), margin is enormous.

## Cron deployment (later)

Once we have a paying client and the prompt is stable, ship to a Hostinger VPS:

```cron
0 8 * * * cd /opt/dealmemory/agency && /opt/dealmemory/agency/.venv/bin/python skills/morning_briefing/morning_briefing.py >> /var/log/dealmemory/briefing.log 2>&1
```

For now, run manually each morning. Tightens the prompt before we automate.

## Extending

Send the briefing somewhere instead of just printing:

- **Email-to-self:** add a `gmail.send` scope and post via the Gmail API.
- **Slack:** set `SLACK_WEBHOOK_URL` in `.env` and POST the text payload.
- **Telegram:** add a bot, POST to `https://api.telegram.org/bot<TOKEN>/sendMessage`.

Don't add all three speculatively — pick one when we need it.
