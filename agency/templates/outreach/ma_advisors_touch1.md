# Touch 1 — M&A Advisors / Business Brokers / PE Associates

**When to send:** Day 1 of the sequence.
**Goal:** Open a conversation. Not a pitch. No demo ask, no calendar link.
**Word count target:** Under 120 words.

---

## Subject line options (A/B test)

- `quick one — the deal that went quiet`
- `something about your {{Firm}} workflow`
- `{{FirstName}} — most advisors lose this one`

(Pick one per niche. Don't rotate per send — let one win on reply rate.)

---

## Body

```
Hi {{FirstName}},

Saw you're running point on deals at {{Firm}} — congrats on the {{recent_deal_or_post}}.

Quick observation, not a pitch: most M&A advisors I talk to don't lose deals
on price. They lose them on momentum — a counterparty going quiet for 8 days,
a redline that never made it into the data room, an IC memo waiting on a
financial pull the analyst forgot about.

We built a system that watches every deal email + Drive doc and flags the
specific deals where momentum is dying — before the seller pulls the plug.
One advisor saved a $14M transaction last month from a 9-day quiet period
nobody noticed.

Worth 15 minutes to see if it's relevant to how {{Firm}} works? Happy to
just send a 90-second demo if a call's overkill.

— {{OperatorFirstName}}
Deal Memory
```

---

## Variables to fill in

| Token | Source | Example |
|---|---|---|
| `{{FirstName}}` | Pipeline sheet, Name column | Sarah |
| `{{Firm}}` | Pipeline sheet, Firm column | Chen Capital Partners |
| `{{recent_deal_or_post}}` | Their LinkedIn last 30 days | Series B announcement at TechCo |
| `{{OperatorFirstName}}` | You | (your first name) |

---

## Why this works

- **Pattern-interrupt opening:** "not a pitch" disarms — they expect a pitch
- **Specific pain:** "8 days," "9-day quiet period," "$14M" — numbers make it real
- **No fake personalization:** the `{{recent_deal_or_post}}` line must be researched, not generated. If you can't find one, swap to: "Saw you've been doing M&A in {{vertical}} — congrats on the run."
- **Low-friction CTA:** offers an out (90-second demo) so people who hate calls can still engage
- **No calendar link:** Calendly links cut reply rates ~30% on first-touch cold outreach

---

## After-send checklist

In the leads sheet `Pipeline` tab:
- Set `Outreach Status` → `contacted`
- Set `Last Touch Date` → today
- Set `Follow-up Date` → today + 3 days
- Increment `Touch Count` to 1
- Note any reply or LinkedIn signal in `Notes`
