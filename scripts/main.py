"""
Entry point. Usage:

    python main.py --mode calibrate   # one-off: post raw findings per area to Slack
    python main.py --mode alert       # check thresholds, ping only on tier change
    python main.py --mode digest      # once-daily summary of all 9 areas

See ../README.md for setup instructions.
"""

import argparse
import datetime as dt
import zoneinfo

from config import AREAS, WATCH_THRESHOLD_PCT, ALERT_THRESHOLD_PCT
from fetch import fetch_area_csv
from parse import parse_area_csv
from notify import post_to_slack
from state import load_state, save_state

JST = zoneinfo.ZoneInfo("Asia/Tokyo")


def tier_for(rate_pct: float | None) -> str:
    if rate_pct is None:
        return "unknown"
    if rate_pct >= ALERT_THRESHOLD_PCT:
        return "alert"
    if rate_pct >= WATCH_THRESHOLD_PCT:
        return "watch"
    return "normal"


TIER_EMOJI = {"normal": "🟢", "watch": "🟡", "alert": "🔴", "unknown": "⚪"}


def run_calibrate():
    """Fetch + parse every area, post a diagnostic summary. Does not touch state."""
    now_label = f"{dt.datetime.now(JST):%Y-%m-%d %H:%M} JST"
    lines = [f"*Grid monitor calibration check* ({now_label})"]
    for area in AREAS:
        text, err = fetch_area_csv(area)
        if err:
            lines.append(f"❌ *{area.name_en}*: fetch failed - {err}")
            continue
        result = parse_area_csv(text)
        if result.latest_usage_rate_pct is None:
            lines.append(f"⚠️ *{area.name_en}*: parsed but no usage rate found - {result.warning}")
        else:
            tomorrow = (f"{result.tomorrow_peak_usage_rate_pct:.1f}%"
                        if result.tomorrow_peak_usage_rate_pct is not None else "n/a")
            note = f" | {result.warning}" if result.warning else ""
            lines.append(
                f"✅ *{area.name_en}*: {result.latest_usage_rate_pct:.1f}% "
                f"(as of {now_label}) | tomorrow peak: {tomorrow}{note}"
            )
    post_to_slack("\n".join(lines))


def run_alert():
    """Check each area's tier; ping only when a tier boundary is crossed."""
    state = load_state()
    now_label = f"{dt.datetime.now(JST):%Y-%m-%d %H:%M} JST"

    for area in AREAS:
        area_state = state.get(area.id, {})
        text, err = fetch_area_csv(area)

        if err:
            # Throttle fetch-failure pings to once per day per area.
            last_fail_date = area_state.get("last_fail_notified_date")
            today_str = dt.datetime.now(JST).strftime("%Y-%m-%d")
            if last_fail_date != today_str:
                post_to_slack(f"⚠️ *{area.name_en}* grid data fetch failed ({now_label}): {err}")
                area_state["last_fail_notified_date"] = today_str
                state[area.id] = area_state
            continue

        result = parse_area_csv(text)
        new_tier = tier_for(result.latest_usage_rate_pct)
        old_tier = area_state.get("tier")

        if new_tier != old_tier and new_tier != "unknown":
            emoji = TIER_EMOJI[new_tier]
            rate_str = f"{result.latest_usage_rate_pct:.1f}%" if result.latest_usage_rate_pct else "n/a"
            post_to_slack(
                f"{emoji} *{area.name_en}* usage rate {rate_str} "
                f"({old_tier or 'unknown'} → {new_tier}) as of {now_label}"
            )

        area_state["tier"] = new_tier
        area_state["last_rate_pct"] = result.latest_usage_rate_pct
        area_state["last_checked"] = now_label
        state[area.id] = area_state

    save_state(state)


def run_digest():
    """Once-daily summary across all 9 areas."""
    lines = [f"*Japan grid daily digest* - {dt.datetime.now(JST):%Y-%m-%d} 18:00 JST"]
    for area in AREAS:
        text, err = fetch_area_csv(area)
        if err:
            lines.append(f"❌ *{area.name_en}*: unavailable")
            continue
        result = parse_area_csv(text)
        current = f"{result.latest_usage_rate_pct:.1f}%" if result.latest_usage_rate_pct else "n/a"
        tomorrow = f"{result.tomorrow_peak_usage_rate_pct:.1f}%" if result.tomorrow_peak_usage_rate_pct else "n/a"
        tier = tier_for(result.latest_usage_rate_pct)
        lines.append(f"{TIER_EMOJI[tier]} *{area.name_en}*: now {current} | tomorrow peak (est) {tomorrow}")
    post_to_slack("\n".join(lines))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["calibrate", "alert", "digest"], required=True)
    args = parser.parse_args()

    if args.mode == "calibrate":
        run_calibrate()
    elif args.mode == "alert":
        run_alert()
    elif args.mode == "digest":
        run_digest()
