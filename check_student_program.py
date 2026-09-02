"""
Watches the (now-live) ANS 2026 Winter Conference Student Program page
for a CONTENT change -- specifically, a change to the page's own
"Last modified" timestamp, which the site prints whenever this page's
body is edited. Right now the page says "Registration for the Student
Program will open soon!"; the next time an editor updates that page
(most likely to open registration), this timestamp will move, and this
script will email an alert.

Why watch "Last modified" instead of diffing the whole page: this page
shares a global header, nav, and footer with every ANS page, and those
contain rotating pieces (a "Latest News" snippet, magazine cover art,
etc.) that change ON THEIR OWN and would trigger constant false
positives if the entire page HTML were hashed. The per-page "Last
modified" line only moves when THIS page's own content is edited, so
it's a clean, low-noise signal.

First run after this script is installed: no baseline exists yet, so it
just records the current "Last modified" value and exits WITHOUT
emailing (this is the seeding run -- trigger it manually once after
deploying). Every run after that compares against the saved baseline
and emails the moment it changes.
"""

import os
import re
import json
from datetime import datetime, timezone

import requests

STATE_FILE = "state.json"
URL = "https://www.ans.org/meetings/wc2026/student/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

RECIPIENT_EMAIL = "rhirji3@gatech.edu"

LAST_MODIFIED_RE = re.compile(r"Last modified[^<\n]{0,60}", re.IGNORECASE)


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"content_baseline_last_modified": None, "content_change_notified": False}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def get_last_modified_string():
    resp = requests.get(URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    match = LAST_MODIFIED_RE.search(resp.text)
    if not match:
        return None
    return match.group(0).strip()


def send_email(old_value, new_value):
    import smtplib
    from email.mime.text import MIMEText

    gmail_address = os.environ["GMAIL_ADDRESS"]
    gmail_app_password = os.environ["GMAIL_APP_PASSWORD"]

    subject = "ANS Student Program page content changed"
    body = (
        f"The student program page's content changed as of "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.\n\n"
        f"Previous: {old_value}\n"
        f"Now:      {new_value}\n\n"
        f"URL: {URL}\n\n"
        f"This likely means registration has opened -- go check it."
    )

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = RECIPIENT_EMAIL

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, gmail_app_password)
        server.sendmail(gmail_address, [RECIPIENT_EMAIL], msg.as_string())


def main():
    state = load_state()

    if state.get("content_change_notified"):
        print("Already notified about a content change -- nothing to do.")
        return

    current = get_last_modified_string()
    if current is None:
        print("Could not find a 'Last modified' string on the page this run -- "
              "site markup may have changed. Skipping (will retry next run).")
        return

    baseline = state.get("content_baseline_last_modified")

    if baseline is None:
        state["content_baseline_last_modified"] = current
        save_state(state)
        print(f"Baseline captured: '{current}'. Will alert on the next change.")
        return

    if current != baseline:
        print(f"Change detected: '{baseline}' -> '{current}'")
        send_email(baseline, current)
        state["content_change_notified"] = True
        state["content_baseline_last_modified"] = current
        save_state(state)
        print("Email sent and state updated.")
    else:
        print(f"No change yet (still: '{current}')")


if __name__ == "__main__":
    main()
