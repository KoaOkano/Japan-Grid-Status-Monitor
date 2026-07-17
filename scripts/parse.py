"""
Parse a denki-yoho CSV without assuming fixed column positions.

Strategy: find every row that looks like a header for a "使用率" (usage rate)
table, then walk the rows below each one collecting values until the block
ends (blank row, column count changes, or an implausible value). This
tolerates per-area column-order differences (e.g. Kansai) because columns
are always located by keyword, never fixed index - and it naturally handles
files that contain multiple stacked tables (today's hourly block, a 5-minute
block, tomorrow's forecast block, etc.) because each table gets its own
scoped read.
"""

import csv
import io
from dataclasses import dataclass


@dataclass
class ParseResult:
    latest_usage_rate_pct: float | None
    tomorrow_peak_usage_rate_pct: float | None
    warning: str | None  # non-fatal notes about parsing confidence


def _to_float(cell: str) -> float | None:
    cell = cell.strip().replace("%", "").replace(",", "")
    if not cell:
        return None
    try:
        val = float(cell)
    except ValueError:
        return None
    if 0 < val <= 1.5:  # some areas may express rate as 0.925 instead of 92.5
        val *= 100
    return val


def _find_usage_rate_headers(rows):
    """Returns list of (row_idx, column_idx, header_row) for every row
    containing a '使用率' cell - there may be several (today, tomorrow,
    day-after-tomorrow, weekly...)."""
    found = []
    for i, row in enumerate(rows):
        for j, cell in enumerate(row):
            if "使用率" in cell:
                found.append((i, j, row))
                break
    return found


def _extract_block_rates(rows, header_row_idx, usage_rate_col, header_width):
    """Scoped read of one usage-rate table: stops at a blank row, a row whose
    width doesn't match the header (signals a different table started), or a
    value outside 0-100 (signals we've drifted into an unrelated table)."""
    rates = []
    for row in rows[header_row_idx + 1:]:
        if not row or all(c.strip() == "" for c in row):
            break
        if len(row) != header_width:
            break
        if len(row) <= usage_rate_col:
            break
        rate = _to_float(row[usage_rate_col])
        if rate is None:
            continue
        if not (0 <= rate <= 100):
            break
        rates.append(rate)
    return rates


def parse_area_csv(text: str) -> ParseResult:
    rows = list(csv.reader(io.StringIO(text)))
    headers = _find_usage_rate_headers(rows)

    if not headers:
        return ParseResult(None, None,
                            warning="No '使用率' (usage rate) header found - "
                                    "format may have changed, needs manual check.")

    # First usage-rate table in the file is today's hourly block.
    today_idx, today_col, today_header = headers[0]
    today_rates = _extract_block_rates(rows, today_idx, today_col, len(today_header))
    latest_rate = today_rates[-1] if today_rates else None

    # Tomorrow's block: the first usage-rate header that appears after a row
    # mentioning "翌日" (tomorrow). Reuses the same scoped-block logic, then
    # takes the max as the forecast peak.
    tomorrow_peak = None
    tomorrow_marker_idx = None
    for i, row in enumerate(rows):
        if "翌日" in "".join(row):
            tomorrow_marker_idx = i
            break

    if tomorrow_marker_idx is not None:
        for h_idx, h_col, h_row in headers:
            if h_idx > tomorrow_marker_idx:
                block_rates = _extract_block_rates(rows, h_idx, h_col, len(h_row))
                if block_rates:
                    tomorrow_peak = max(block_rates)
                break

    warning = None
    if latest_rate is None:
        warning = "Found usage-rate header but no numeric rows beneath it - check format."
    elif tomorrow_peak is None:
        warning = "Could not locate tomorrow's forecast block."

    return ParseResult(
        latest_usage_rate_pct=latest_rate,
        tomorrow_peak_usage_rate_pct=tomorrow_peak,
        warning=warning,
    )
