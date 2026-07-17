"""Fetch a CSV from a utility's URL, trying multiple encodings."""

import datetime as dt
import zoneinfo

import requests

JST = zoneinfo.ZoneInfo("Asia/Tokyo")


def build_url(area) -> str:
    if area.date_format is None:
        return area.url_template
    today_jst = dt.datetime.now(JST).strftime(area.date_format)
    return area.url_template.format(date=today_jst)


def fetch_area_csv(area, timeout=15) -> tuple[str | None, str | None]:
    """
    Returns (text, error). Exactly one will be None.
    """
    url = build_url(area)
    try:
        resp = requests.get(url, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (grid-status-monitor; personal use)"
        })
        resp.raise_for_status()
    except requests.RequestException as e:
        return None, f"HTTP error fetching {url}: {e}"

    raw = resp.content
    for enc in area.encoding_candidates:
        try:
            return raw.decode(enc), None
        except UnicodeDecodeError:
            continue
    return None, f"Could not decode {url} with any of {area.encoding_candidates}"
