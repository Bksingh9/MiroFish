# Deal Memory — Project Memory

**Read this file first at the start of every session.**

## Identity

- **Business name:** Deal Memory
- **Niche:** AI operations layer for M&A advisors, business brokers, and PE associates
- **Operator email:** `dealmemory.ops@gmail.com` (placeholder — register at accounts.google.com, then replace this string everywhere via grep)
- **Build branch:** `claude/ai-automation-agency-nLjRP`
- **Repo location:** `/home/user/MiroFish/agency/`

## Why this product wins

Deal advisors run 5–30 concurrent deals. Each deal generates hundreds of emails, dozens of docs, and weeks of phone calls. The work that loses deals is invisible: a counterparty going quiet for 6 days, an LOI redline never logged, an IC memo waiting on data the analyst forgot to pull.

We build a per-deal RAG memory system that ingests their email/Drive/calendar/call transcripts and surfaces:
- Auto-generated IC memos and weekly deal status reports
- "Quiet counterparty" alerts when momentum is fading
- Auto-indexed data rooms (LOI, NDA, IM, CIM, financials)
- Searchable deal memory across the firm's full deal history

**Defensible because:** the moat compounds — every deal closed becomes training data for the next one. After 6 months, leaving us means losing the institutional memory of every deal touched.

## Pricing

- **Setup:** $1,500 (one-time)
- **Retainer:** $800–$2,000/mo per advisor (volume tiers)
- **Target:** 5 paying advisors by day 90 → $5K–$10K MRR

## Hard rules

1. **Build first, explain second.** Working code beats a roadmap.
2. **Sub-agents for parallel work.** Spawn them when blocked instead of asking.
3. **Every deliverable ships with:** working code + README + 5-min demo script + pricing justification.
4. **Never write manual code outside this repo.** Claude Code only.
5. **Context discipline.** Summarize completed phases at end of every work session — don't let context bloat slow us down.
6. **Use Anthropic SDK with `claude-opus-4-7` + adaptive thinking + prompt caching.** Never `budget_tokens`. Never `temperature`/`top_p`/`top_k` (removed on Opus 4.7).

## Tech stack (locked)

| Layer | Choice |
|---|---|
| Brain / orchestration | Anthropic SDK (Python) — `claude-opus-4-7`, adaptive thinking, prompt caching |
| Build tool | Claude Code (this) |
| Email | Gmail API via OAuth 2.0 |
| "Database" | Google Sheets (no ClickUp — operator preference) |
| Calendar | Google Calendar API |
| Docs / data room | Google Drive API |
| Hosting | Hostinger VPS + cron (deferred until v1 client lands) |
| Notifications | Email-to-self for now; Slack webhook when first client onboards |

## Repo layout

```
agency/
├── CLAUDE.md                      # ← this file
├── README.md                      # operator's manual
├── .env.example                   # credentials template
├── requirements.txt               # Python deps
├── skills/
│   └── morning_briefing/          # daily 8am briefing
├── templates/
│   ├── leads_sheet_schema.md      # Google Sheet structure
│   └── outreach/                  # cold outreach templates
└── config/                        # OAuth tokens, runtime configs
```

## Next-action queue (update as we go)

- [x] Scaffold repo, CLAUDE.md, README, .env, requirements
- [x] Morning Briefing skill (Gmail + Sheets summary via Opus 4.7)
- [x] Lead tracking sheet schema
- [x] First outreach template — M&A advisor touch 1
- [ ] Operator registers `dealmemory.ops@gmail.com` and runs OAuth flow
- [ ] Cold outreach templates touch 2 + touch 3
- [ ] Lead Scraper skill (LinkedIn Sales Navigator export → Sheet)
- [ ] Onboarding skill — 12-question intake → scope doc
- [ ] Deal Memory v0 — single-deal RAG ingestor (the core product)
- [ ] Weekly Deal Status Report skill
- [ ] Quiet-Counterparty Alert skill
- [ ] First 3 paying advisors

## Decision log

- **2026-05-02** — Picked M&A advisors over local services (higher ACV, longer stickiness, smallest competitive surface). User explicitly chose Option B from the three candidates.
- **2026-05-02** — Skipping ClickUp; using Google Sheets as task/lead DB. Reduces onboarding friction for clients.
- **2026-05-02** — Locked `claude-opus-4-7` with adaptive thinking. Effort `high` for briefings, `xhigh` for IC memo generation when we build it.
