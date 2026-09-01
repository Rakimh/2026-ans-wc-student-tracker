# ANS 2026 Winter Conference Student Program Tracker

Checks every 15 minutes whether the ANS 2026 Winter Conference Student
Program page has gone live, and emails rhirji3@gatech.edu the moment it's
detected. Runs for free on GitHub Actions — no server needed.

## What it checks

1. Direct hit on the guessed URL: `https://www.ans.org/meetings/wc2026/student/`
2. A scan of `https://www.ans.org/meetings/wc2026/` for any link that
   mentions "student" — this catches it even if ANS uses a slightly
   different URL than the one guessed above.

## One-time setup

1. **Create a GitHub repo** and push these files to it (root of the repo).

2. **Get a Gmail App Password** (needed because Gmail blocks plain
   password login for scripts):
   - Turn on 2-Step Verification on the Gmail account you want to send
     from, if it isn't already on: https://myaccount.google.com/security
   - Go to https://myaccount.google.com/apppasswords
   - Create an app password named something like "ans-tracker"
   - Copy the 16-character password it gives you

3. **Add two repo secrets** (repo → Settings → Secrets and variables →
   Actions → New repository secret):
   - `GMAIL_ADDRESS` — the Gmail address you're sending from
   - `GMAIL_APP_PASSWORD` — the app password from step 2

4. **Push.** The workflow (`.github/workflows/check.yml`) will start
   running automatically every 15 minutes.

5. **Test it immediately** instead of waiting: go to the repo's Actions
   tab → "Check ANS Winter 2026 Student Program" → "Run workflow". Check
   the run log — it should print "Not live yet" (or send you a real email
   if the page has already gone live).

## After it fires

Once the page is detected, it emails you once and sets `notified: true`
in `state.json` so it won't spam you every 15 minutes afterward. If you
ever want to re-arm it (e.g. testing, or a false trigger), edit
`state.json` back to `{"notified": false, "found_url": null}` and push.

## Notes / limitations

- The exact student-program URL for 2026 hasn't been confirmed since ANS
  doesn't announce it — this tracker is built on the wc2025 → wc2026
  naming pattern, which has held for both the 2025 winter and 2026 annual
  conferences. If ANS breaks pattern entirely, the nav-link scan (check
  #2) is the backstop.
- 15-minute polling is intentionally not more aggressive, to stay
  respectful to ANS's site — you can tighten the cron in
  `.github/workflows/check.yml` if you want.
- GitHub Actions free tier is far more than enough for this (a few
  seconds every 15 minutes).
