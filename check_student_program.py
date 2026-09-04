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

IMPORTANT: the site has been observed rendering the SAME instant with
different timezone abbreviations across requests (e.g. "2:48pm EDT" vs
"11:48am MST" for the same edit -- both are 18:48 UTC). A raw string
compare would treat that as a false "change", so this script parses the
timestamp into an actual UTC instant and compares THAT, falling back to
a raw string compare only if parsing fails.

First run after this script is installed: no baseline exists yet, so it
just records the current "Last modified" value and exits WITHOUT
emailing (this is the seeding run -- trigger it manually once after
deploying). Every run after that compares against the saved baseline
and emails the moment it changes.
"""

import os
import re
import json
from datetime import datetime, timedelta, timezone

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

# Fixed-offset approximations -- fine for "is this the same moment right
# now", not meant as a general historical timezone database.
TZ_OFFSETS_HOURS = {
    "EST": -5, "EDT": -4,
    "CST": -6, "CDT": -5,
    "MST": -7, "MDT": -6,
    "PST": -8, "PDT": -7,
    "UTC": 0, "GMT": 0,
}

TIMESTAMP_RE = re.compile(
    r"([A-Za-z]+\s+\d{1,2},\s+\d{4}),\s+(\d{1,2}:\d{2}\s*(?:am|pm))\s+(\w+)",
    re.IGNORECASE,
)


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


def parse_last_modified(raw_string):
    """
    Try to turn a raw 'Last modified ...' string into an aware UTC-ish
    datetime so the SAME instant compares equal regardless of which
    timezone abbreviation the site happened to render it in. Returns
    None if the format doesn't match (caller falls back to a raw
    string compare in that case).
    """
    if not raw_string:
        return None
    match = TIMESTAMP_RE.search(raw_string)
    if not match:
        return None
    date_part, time_part, tz_abbr = match.groups()
    offset_hours = TZ_OFFSETS_HOURS.get(tz_abbr.upper())
    if offset_hours is None:
        return None
    try:
        naive = datetime.strptime(
            f"{date_part} {time_part.replace(' ', '').upper()}",
            "%B %d, %Y %I:%M%p",
        )
    except ValueError:
        return None
    return naive.replace(tzinfo=timezone(timedelta(hours=offset_hours)))


def is_same_moment(raw_a, raw_b):
    dt_a = parse_last_modified(raw_a)
    dt_b = parse_last_modified(raw_b)
    if dt_a is not None and dt_b is not None:
        return dt_a == dt_b
    # Couldn't confidently parse one or both -- fall back to exact text match.
    return raw_a == raw_b


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

    if not is_same_moment(baseline, current):
        print(f"Change detected: '{baseline}' -> '{current}'")
        send_email(baseline, current)
        state["content_change_notified"] = True
        state["content_baseline_last_modified"] = current
        save_state(state)
        print("Email sent and state updated.")
    else:
        print(f"No real change (same instant, text shown as: '{current}')")
        # Keep the baseline as whatever the site is showing right now so
        # future runs compare against the freshest rendering.
        if current != baseline:
            state["content_baseline_last_modified"] = current
            save_state(state)


if __name__ == "__main__":
    main()
