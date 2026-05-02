# Deal Memory — Operator Manual

AI operations layer for M&A advisors, business brokers, and PE associates.

## What's in this repo

| Path | What it does |
|---|---|
| `CLAUDE.md` | Project memory — Claude reads this first |
| `skills/morning_briefing/` | 8am daily briefing — Gmail + leads sheet → AI summary |
| `templates/leads_sheet_schema.md` | Exact Google Sheet structure to set up |
| `templates/outreach/` | Cold outreach templates for M&A advisors |
| `.env.example` | Credentials you must fill in |
| `requirements.txt` | Python deps |

## First-time setup (15 minutes)

### 1. Register the ops Gmail account

Go to https://accounts.google.com → create `dealmemory.ops@gmail.com` (or your preferred handle).
Then grep-replace it across the repo:

```bash
grep -rl "dealmemory.ops@gmail.com" agency/ | xargs sed -i 's/dealmemory.ops@gmail.com/YOUR_EMAIL/g'
```

### 2. Enable APIs and create OAuth credentials

In Google Cloud Console (https://console.cloud.google.com):

1. New project: "Deal Memory"
2. Enable **Gmail API**, **Google Sheets API**, **Google Drive API**, **Google Calendar API**
3. APIs & Services → Credentials → Create OAuth client ID → **Desktop app**
4. Download the JSON. Save it to `agency/config/google_oauth_client.json`

### 3. Get an Anthropic API key

Go to https://console.anthropic.com → API Keys → create one.

### 4. Set up `.env`

```bash
cp agency/.env.example agency/.env
# fill in ANTHROPIC_API_KEY and OPERATOR_EMAIL
```

### 5. Install deps

```bash
cd agency
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 6. Create the Google Sheet

Open `templates/leads_sheet_schema.md` and copy the column structure into a new Google Sheet titled **"Deal Memory — Operations"**. Share it with `dealmemory.ops@gmail.com` (full edit access). Copy the sheet ID from the URL into `.env` as `OPS_SHEET_ID`.

### 7. First run — authenticate

```bash
python skills/morning_briefing/morning_briefing.py
```

The first run opens a browser for Google OAuth. Approve. The token saves to `config/google_token.json` for future runs.

## Daily use

```bash
python skills/morning_briefing/morning_briefing.py
```

Outputs a briefing covering:
- Top 3 inbox priorities (with suggested replies)
- Today's tasks from the "Today" sheet
- Pipeline status — leads needing follow-up
- One sharp recommendation for the day

## Production deployment (after first paying client)

We'll set up a Hostinger VPS with cron at 8am. Until then, run it manually each morning over coffee — feedback loop tightens the prompt before we automate.

```cron
0 8 * * * cd /opt/dealmemory/agency && /opt/dealmemory/agency/.venv/bin/python skills/morning_briefing/morning_briefing.py
```

## Building new skills

1. Add a folder under `skills/<skill_name>/`
2. Update `CLAUDE.md` next-action queue
3. Use `claude-opus-4-7` with `thinking: {"type": "adaptive"}` and prompt caching on stable system prompts
4. Never use `budget_tokens` (deprecated/removed); never use `temperature`/`top_p`/`top_k` (removed on Opus 4.7)

## Outreach playbook

Cold outreach lives in `templates/outreach/`. Run the 3-touch sequence over 10 days:

| Day | Template | Goal |
|---|---|---|
| 1 | `ma_advisors_touch1.md` | Open a value-led conversation |
| 4 | `ma_advisors_touch2.md` | Follow up with case study |
| 10 | `ma_advisors_touch3.md` | Open-loop close |

Track each prospect in the leads sheet — set `Outreach Status` and `Follow-up Date` on every send.
