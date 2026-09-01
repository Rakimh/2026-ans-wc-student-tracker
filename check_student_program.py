"""
Checks whether the ANS 2026 Winter Conference & Expo Student Program page
has gone live, and emails an alert the first time it's detected.

Detection strategy (two independent checks, either one triggers an alert):
  1. Direct hit: GET the guessed URL (wc2026/student/) and see if it 200s.
  2. Nav-link scan: GET the conference homepage and look for any link whose
     href or text contains "student" — this catches ANS linking the page
     from a slightly different slug than we guessed.

State is persisted in state.json (committed back to the repo by the GitHub
Actions workflow) so we only send one email, not one every 15 minutes.
"""

import os
import json
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

STATE_FILE = "state.json"

CANDIDATE_URL = "https://www.ans.org/meetings/wc2026/student/"
CONFERENCE_HOME = "https://www.ans.org/meetings/wc2026/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

RECIPIENT_EMAIL = "rhirji3@gatech.edu"


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"notified": False, "found_url": None}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def check_direct_url():
    try:
        resp = requests.get(CANDIDATE_URL, headers=HEADERS, timeout=20, allow_redirects=True)
        if resp.status_code == 200:
            return resp.url
    except requests.RequestException as e:
        print(f"Direct URL check failed: {e}")
    return None


def check_homepage_for_student_link():
    try:
        resp = requests.get(CONFERENCE_HOME, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            print(f"Homepage returned status {resp.status_code}")
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True).lower()
            if "student" in href.lower() or "student" in text:
                if href.startswith("/"):
                    href = "https://www.ans.org" + href
                return href
    except requests.RequestException as e:
        print(f"Homepage check failed: {e}")
    return None


def send_email(found_url):
    import smtplib
    from email.mime.text import MIMEText

    gmail_address = os.environ["GMAIL_ADDRESS"]
    gmail_app_password = os.environ["GMAIL_APP_PASSWORD"]

    subject = "🚨 ANS 2026 Winter Conference Student Program is LIVE"
    body = (
        f"The student program page appears to be live as of "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.\n\n"
        f"URL: {found_url}\n\n"
        f"Go sign up now — no formal announcement is made, so this may not "
        f"stay quiet for long."
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

    if state.get("notified"):
        print("Already notified previously — nothing to do. "
              "(Reset state.json's 'notified' field to false to re-arm.)")
        return

    found_url = check_direct_url() or check_homepage_for_student_link()

    if found_url:
        print(f"Student program page detected: {found_url}")
        send_email(found_url)
        state["notified"] = True
        state["found_url"] = found_url
        save_state(state)
        print("Email sent and state updated.")
    else:
        print(f"Not live yet, checked at "
              f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")


if __name__ == "__main__":
    main()
