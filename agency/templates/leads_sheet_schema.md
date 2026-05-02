# Operations Sheet — Schema

Create one Google Sheet titled **"Deal Memory — Operations"**, share with the operator email, then paste the sheet ID into `.env` as `OPS_SHEET_ID`.

It needs **5 tabs**, set up exactly as below. Header row goes in row 1; data starts row 2. The morning briefing reads the `Today` and `Pipeline` tabs by name — don't rename them.

---

## Tab 1: `Today`

What needs to happen today, in priority order. Wipe and rebuild every morning (or every Sunday for the week).

| Column | Type | Example |
|---|---|---|
| Priority | int (1=highest) | 1 |
| Task | text | Send proposal to Patel & Associates |
| Status | enum (`open`, `in-progress`, `blocked`, `done`) | open |
| Blocker | text (if Status=blocked) | Waiting on financials from client |
| ETA | date | 2026-05-02 |
| Notes | text | Use the IM template, customize for healthcare vertical |

---

## Tab 2: `Pipeline`

Every lead we're actively working. The morning briefing watches `Outreach Status` and `Follow-up Date`.

| Column | Type | Example |
|---|---|---|
| Name | text | Sarah Chen |
| Firm | text | Chen Capital Partners |
| Title | text | Managing Director |
| Niche | enum (`ma-advisor`, `business-broker`, `pe-associate`, `other`) | ma-advisor |
| Email | text | sarah@chencapital.com |
| LinkedIn | url | https://linkedin.com/in/sarahchen |
| Source | text | LinkedIn Sales Nav export 2026-05-01 |
| Pain Hypothesis | text | Runs 12 deals concurrent; loses momentum on stale ones |
| Outreach Status | enum (`new`, `contacted`, `follow-up-due`, `proposal-sent`, `negotiating`, `closed-won`, `closed-lost`, `dead`) | contacted |
| Last Touch Date | date | 2026-05-01 |
| Follow-up Date | date | 2026-05-05 |
| Touch Count | int | 1 |
| Notes | text | Replied with curiosity — book demo |

---

## Tab 3: `Clients`

Live clients we're delivering for. Update monthly.

| Column | Type | Example |
|---|---|---|
| Client Name | text | Patel & Associates |
| Primary Contact | text | Raj Patel |
| Email | text | raj@patelma.com |
| Product Tier | enum (`smart-inbox`, `weekly-report`, `aios`, `deal-memory`) | deal-memory |
| Setup Fee | number | 1500 |
| MRR | number | 1200 |
| Start Date | date | 2026-05-15 |
| Health Score | int 1-10 | 9 |
| Last Check-in | date | 2026-05-29 |
| Hours Saved/Week | int | 8 |
| Renewal Risk | enum (`low`, `med`, `high`) | low |
| Notes | text | Loves the quiet-counterparty alerts |

---

## Tab 4: `Revenue`

Monthly snapshot. Add one row per month.

| Column | Type | Example |
|---|---|---|
| Month | text (YYYY-MM) | 2026-05 |
| MRR Start | number | 0 |
| MRR End | number | 1200 |
| Setup Fees Collected | number | 1500 |
| New Clients | int | 1 |
| Churned Clients | int | 0 |
| Pipeline Value | number | 8500 |
| Notes | text | First client signed |

---

## Tab 5: `Skill Library`

Index of every skill we've built — for our own discoverability and to show prospects.

| Column | Type | Example |
|---|---|---|
| Skill Name | text | Morning Briefing |
| Path | text | skills/morning_briefing/ |
| Status | enum (`live`, `wip`, `idea`) | live |
| Used By | text (comma-sep) | self, Patel & Associates |
| Last Updated | date | 2026-05-02 |
| Description | text | 8am briefing — Gmail + sheet → AI summary |

---

## Quickstart fill

After creating the sheet, paste these starter rows so the morning briefing has data to chew on day 1:

**Today** row 2:
```
1 | Register dealmemory.ops@gmail.com and run OAuth flow | open | | 2026-05-02 | Blocks every other skill
```

**Pipeline** rows 2–4 (mock data — replace with real prospects):
```
Sarah Chen | Chen Capital Partners | Managing Director | ma-advisor | sarah@chencapital.com | https://linkedin.com/in/sarahchen | LinkedIn — manual | Runs 12 deals concurrent | new | | 2026-05-03 | 0 |
Marcus Webb | Webb M&A | Senior Broker | business-broker | marcus@webbma.com | https://linkedin.com/in/marcuswebb | Reddit r/business | Solo broker, drowning in IM grunt work | new | | 2026-05-04 | 0 |
Priya Shah | Cascade PE | Associate | pe-associate | priya@cascadepe.com | https://linkedin.com/in/priyashah | LinkedIn Sales Nav | 8 active deals, missed 2 close dates last quarter | new | | 2026-05-05 | 0 |
```
