# Japan Grid Status Monitor

Pings a Slack channel when Japan's regional power grid operators' real-time
usage-rate data crosses a "watch" (92%) or "alert" (97%) tier, plus a daily
18:00 JST digest across all 9 areas (Okinawa's operator is separate; this
covers the 9 mainland/interconnected areas + Okinawa = 10 operators total,
though Okinawa isn't interconnected to the mainland grid).

## Setup

1. **Create the repo** and push these files to it.
2. **Add your Slack webhook as a secret:**
   Repo → Settings → Secrets and variables → Actions → New repository secret
   - Name: `SLACK_WEBHOOK_URL`
   - Value: your `https://hooks.slack.com/services/...` URL
3. **Run calibration first, before trusting any alerts:**
   Repo → Actions → "Japan Grid Status Monitor" → Run workflow → mode: `calibrate`
   This posts one message to Slack showing exactly what usage rate (and hour)
   it found for each of the 10 areas, or a warning if it couldn't find one.
   Compare a couple of these numbers against the area's own public "denki
   yoho" page to sanity-check before relying on it.
4. Once calibration looks right, the schedule takes over automatically:
   - Every 30 min → tier-change check (only posts when an area crosses a
     threshold, not on every run)
   - Daily at 18:05 JST → full digest of all areas

## Known caveats (read before fully trusting this)

- These are **unofficial, undocumented CSV feeds** each utility happens to
  publish for their own public "denki yoho" pages - not a stable public API.
  Any operator can change their file format or URL without notice.
- Two URLs (**Chubu** and **Chugoku**) were not confirmed against a live
  fetch during setup (only referenced secondhand) - if calibration mode
  shows a fetch failure for either, check the operator's own page for the
  current CSV link and update `scripts/config.py`.
- The parser looks for a column labeled "使用率" (usage rate) rather than
  assuming a fixed position, to survive minor format differences - but if an
  operator overhauls their page entirely, calibration mode will surface that
  as a warning rather than silently reporting a wrong number.
- Kansai's feed has known quirks (reversed column order, forecast rather
  than actual usage rate) - already accounted for by the keyword-based
  parser, but worth double-checking in calibration mode.
- Thresholds (92% = watch, 97% = alert) approximate OCCTO's own public
  reserve-margin tiers, translated into usage-rate terms. Adjust
  `WATCH_THRESHOLD_PCT` / `ALERT_THRESHOLD_PCT` in `scripts/config.py` if
  you want it more or less sensitive.

## Moving from test to your work Slack

Just swap the `SLACK_WEBHOOK_URL` secret's value to your work workspace's
webhook - no code changes needed.
