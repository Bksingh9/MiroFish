"""Morning Briefing — Deal Memory operator's daily 8am briefing.

Reads:
  - Last 24h of Gmail (unread + recent threads)
  - "Today" sheet (today's priorities)
  - "Pipeline" sheet (active outreach status)

Synthesizes via Claude Opus 4.7 (adaptive thinking) into a tight briefing.

Run manually each morning until first paying client lands; then deploy as
8am cron on Hostinger VPS. See agency/README.md.
"""

from __future__ import annotations

import base64
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import anthropic
import gspread
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]

MODEL = "claude-opus-4-7"

BRIEFING_PERSONA = """You are the Chief of Staff for Deal Memory — an AI operations layer for M&A advisors, business brokers, and PE associates.

Your operator runs the agency solo. They need a 90-second briefing every morning that surfaces what to act on, hides what doesn't matter, and tells them the one thing they should do first.

Format the briefing as plain text with these sections, in this order, no markdown headers:

INBOX — TOP 3
For each: 1-line summary + sender + suggested action (REPLY / DELEGATE / IGNORE / SCHEDULE). Skip noise (newsletters, receipts, GitHub notifications) entirely.

TODAY
Bullet the top 3 tasks from the Today sheet. If a task is blocked, say what's blocking it.

PIPELINE
For each lead with Outreach Status in {contacted, follow-up-due, proposal-sent, negotiating}: name + niche + last touch date + next move. If a follow-up is overdue, mark it OVERDUE.

THE ONE THING
Single sharpest recommendation: what should the operator do FIRST today, and why. One sentence. Be opinionated.

Tone: direct, calm, surgical. No fluff, no preamble, no validation. Skip "Good morning!" and similar. Lead with the data.
"""


# ---------- Google auth ----------

def get_google_creds() -> Credentials:
    token_path = REPO_ROOT / os.environ.get("GOOGLE_TOKEN_PATH", "config/google_token.json")
    client_path = REPO_ROOT / os.environ.get("GOOGLE_OAUTH_CLIENT_PATH", "config/google_oauth_client.json")
    creds: Credentials | None = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), GOOGLE_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not client_path.exists():
                sys.exit(
                    f"Missing OAuth client at {client_path}.\n"
                    "Download it from Google Cloud Console (Credentials → OAuth client → Desktop app)."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(client_path), GOOGLE_SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json())
    return creds


# ---------- Gmail ----------

def fetch_recent_emails(creds: Credentials, hours: int = 24) -> list[dict]:
    """Pull recent inbox messages. Returns lightweight dicts: subject, from, snippet, date."""
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    after = int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp())
    query = f"in:inbox after:{after}"
    resp = service.users().messages().list(userId="me", q=query, maxResults=30).execute()
    out: list[dict] = []
    for ref in resp.get("messages", []):
        msg = service.users().messages().get(
            userId="me", id=ref["id"], format="metadata",
            metadataHeaders=["From", "Subject", "Date"],
        ).execute()
        headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
        out.append({
            "from": headers.get("From", ""),
            "subject": headers.get("Subject", "(no subject)"),
            "date": headers.get("Date", ""),
            "snippet": msg.get("snippet", ""),
            "unread": "UNREAD" in msg.get("labelIds", []),
        })
    return out


# ---------- Sheets ----------

def fetch_sheet_tab(creds: Credentials, sheet_id: str, tab: str) -> list[dict]:
    """Read a tab as list-of-dicts using the first row as headers. Empty list if tab missing."""
    gc = gspread.authorize(creds)
    try:
        ws = gc.open_by_key(sheet_id).worksheet(tab)
    except (gspread.WorksheetNotFound, gspread.SpreadsheetNotFound):
        return []
    return ws.get_all_records()


# ---------- Claude ----------

def build_user_payload(emails: list[dict], today: list[dict], pipeline: list[dict]) -> str:
    today_iso = datetime.now().strftime("%A, %B %d, %Y")
    return (
        f"Date: {today_iso}\n\n"
        f"=== RAW INBOX (last 24h, {len(emails)} messages) ===\n"
        f"{json.dumps(emails, indent=2, default=str)}\n\n"
        f"=== TODAY SHEET ({len(today)} rows) ===\n"
        f"{json.dumps(today, indent=2, default=str)}\n\n"
        f"=== PIPELINE SHEET ({len(pipeline)} rows) ===\n"
        f"{json.dumps(pipeline, indent=2, default=str)}\n"
    )


def generate_briefing(client: anthropic.Anthropic, payload: str) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=[
            {
                "type": "text",
                "text": BRIEFING_PERSONA,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": payload}],
    )
    text_parts = [b.text for b in response.content if b.type == "text"]
    usage = response.usage
    cache_note = (
        f"[cache: {usage.cache_read_input_tokens} read, "
        f"{usage.cache_creation_input_tokens} written, "
        f"{usage.input_tokens} fresh]"
    )
    return "\n".join(text_parts) + f"\n\n— {cache_note}"


# ---------- main ----------

def main() -> int:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY missing in .env")
    sheet_id = os.environ.get("OPS_SHEET_ID")
    if not sheet_id:
        sys.exit("OPS_SHEET_ID missing in .env — see templates/leads_sheet_schema.md")

    creds = get_google_creds()
    emails = fetch_recent_emails(creds)
    today = fetch_sheet_tab(creds, sheet_id, "Today")
    pipeline = fetch_sheet_tab(creds, sheet_id, "Pipeline")

    client = anthropic.Anthropic(api_key=api_key)
    payload = build_user_payload(emails, today, pipeline)
    briefing = generate_briefing(client, payload)

    header = f"=== Deal Memory — Morning Briefing — {datetime.now().strftime('%Y-%m-%d %H:%M')} ==="
    print(header)
    print(briefing)
    return 0


if __name__ == "__main__":
    sys.exit(main())
