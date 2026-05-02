"""Slack/Discord webhook notifier. Falls back to stdout if no webhook set."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


def notify(title: str, body: str) -> None:
    msg = f"*{title}*\n{body}"
    slack = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    discord = os.getenv("DISCORD_WEBHOOK_URL", "").strip()

    payload: dict[str, str]
    url: str
    if slack:
        url, payload = slack, {"text": msg}
    elif discord:
        url, payload = discord, {"content": msg}
    else:
        print(f"[notify:stub] {title}\n{body}", flush=True)
        return

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
    except urllib.error.URLError as e:
        print(f"[notify:error] {e}; falling back to stdout", flush=True)
        print(f"[notify:stub] {title}\n{body}", flush=True)
