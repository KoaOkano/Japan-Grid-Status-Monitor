"""
Parse a denki-yoho CSV without assuming fixed column positions.

Strategy: scan every row for cells that look like a header for the hourly
usage-rate table (a cell containing "使用率" i.e. "usage rate"), then walk
the rows below it collecting (hour_label, usage_rate_pct) pairs until the
numbers stop making sense. This tolerates the column-order differences
between areas (e.g. Kansai) because we always locate columns by keyword,
never by fixed index.
"""

import csv
import io
import re
from dataclasses import dataclass


@dataclass
class ParseResult:
    latest_usage_rate_pct: float | None
    latest_hour_label: str | None
    tomorrow_peak_usage_rate_pct: float | None
    raw_header_row: list | None
    warning: str | None  # non-fatal notes about parsing confidence


def _to_float(cell: str) -> float | None:
    cell = cell.strip().replace("%", "").replace(",", "")
    if not cell:
        return None
    try:
        val = float(cell)
    except ValueError:
        return None
    # Normalize: some areas may express rate as 0.925 instead of 92.5
    if 0 < val <= 1.5:
        val *= 100
    return val


def parse_area_csv(text: str) -> ParseResult:
    rows = list(csv.reader(io.StringIO(text)))

    usage_rate_col = None
    header_row_idx = None
    header_row = None

    for i, row in enumerate(rows):
        for j, cell in enumerate(row):
            if "使用率" in cell:
                usage_rate_col = j
                header_row_idx = i
                header_row = row
                break
        if usage_rate_col is not None:
            break

    if usage_rate_col is None:
        return ParseResult(None, None, None, None,
                            warning="No '使用率' (usage rate) header found - "
                                    "format may have changed, needs manual check.")

    # First column is usually the hour/time label (e.g. "13時" or "13:00").
    time_col = 0

    latest_rate = None
    latest_label = None
    all_rates_seen = []

    for row in rows[header_row_idx + 1:]:
        if not row or len(row) <= usage_rate_col:
            continue
        rate = _to_float(row[usage_rate_col])
        if rate is None:
            continue
        label = row[time_col].strip() if len(row) > time_col else None
        all_rates_seen.append((label, rate))

    if all_rates_seen:
        latest_label, latest_rate = all_rates_seen[-1]

    # Best-effort: look for a "翌日" (tomorrow) section and grab a peak usage
    # rate near it, if present. This is intentionally loose - flagged as a
    # warning if not found rather than guessed at.
    tomorrow_peak = None
    tomorrow_warning = None
    for i, row in enumerate(rows):
        joined = "".join(row)
        if "翌日" in joined:
            # scan the next few rows for a usage-rate-like percentage
            for scan_row in rows[i:i + 6]:
                for cell in scan_row:
                    val = _to_float(cell)
                    if val is not None and 0 < val <= 100:
                        tomorrow_peak = val
                        break
                if tomorrow_peak is not None:
                    break
            break
    if tomorrow_peak is None:
        tomorrow_warning = "Could not confidently locate tomorrow's peak forecast."

    warning = tomorrow_warning if latest_rate is not None else \
        "Found usage-rate header but no numeric rows beneath it - check format."

    return ParseResult(
        latest_usage_rate_pct=latest_rate,
        latest_hour_label=latest_label,
        tomorrow_peak_usage_rate_pct=tomorrow_peak,
        raw_header_row=header_row,
        warning=warning,
    )
