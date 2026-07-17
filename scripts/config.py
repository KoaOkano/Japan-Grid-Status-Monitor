"""
Configuration for Japan's 10 regional grid operators' real-time "denki yoho"
(電力予報 / power forecast) CSV feeds.

Each operator publishes updated supply/demand CSVs roughly every 5 minutes.
Formats are NOT officially documented and differ slightly area to area, so
scripts/parse.py uses keyword-based column detection rather than fixed
column positions.

Sources verified July 2026. If Anthropic or an operator changes a URL, only
this file should need updating.
"""

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class Area:
    id: str                    # short id used in state.json / Slack messages
    name_jp: str
    name_en: str
    url_template: str          # may contain {date} for date-stamped filenames
    date_format: Optional[str] # strftime format for {date}, or None if static URL
    encoding_candidates: tuple  # encodings to try in order
    notes: str = ""            # known quirks, for humans reading this file


AREAS = [
    Area(
        id="hokkaido",
        name_jp="北海道",
        name_en="Hokkaido",
        url_template="http://denkiyoho.hepco.co.jp/area/data/juyo_01_{date}.csv",
        date_format="%Y%m%d",
        encoding_candidates=("cp932", "utf-8-sig", "utf-8"),
    ),
    Area(
        id="tohoku",
        name_jp="東北",
        name_en="Tohoku",
        url_template="https://setsuden.nw.tohoku-epco.co.jp/common/demand/juyo_02_{date}.csv",
        date_format="%Y%m%d",
        encoding_candidates=("cp932", "utf-8-sig", "utf-8"),
        notes="Has an extra wind-power 5-min column other areas lack.",
    ),
    Area(
        id="tokyo",
        name_jp="東京",
        name_en="Tokyo",
        url_template="https://www.tepco.co.jp/forecast/html/images/juyo-d1-j.csv",
        date_format=None,
        encoding_candidates=("cp932", "utf-8-sig", "utf-8"),
        notes="Static filename, always today's data. Has solar-share % column.",
    ),
    Area(
        id="chubu",
        name_jp="中部",
        name_en="Chubu",
        url_template="https://powergrid.chuden.co.jp/denki_yoho_content_data/juyo_cepco003.csv",
        date_format=None,
        encoding_candidates=("cp932", "utf-8-sig", "utf-8"),
    ),
    Area(
        id="hokuriku",
        name_jp="北陸",
        name_en="Hokuriku",
        url_template="https://www.rikuden.co.jp/nw/denki-yoho/csv/juyo_05_{date}.csv",
        date_format="%Y%m%d",
        encoding_candidates=("cp932", "utf-8-sig", "utf-8"),
    ),
    Area(
        id="kansai",
        name_jp="関西",
        name_en="Kansai",
        url_template="https://www.kansai-td.co.jp/yamasou/juyo1_kansai.csv",
        date_format=None,
        encoding_candidates=("cp932", "utf-8-sig", "utf-8"),
        notes=(
            "Column ORDER is reversed vs other areas (hourly block comes after "
            "max-usage block), usage-rate column is FORECAST not actual, and it "
            "has extra forecast/actual temperature columns other areas lack."
        ),
    ),
    Area(
        id="chugoku",
        name_jp="中国",
        name_en="Chugoku",
        url_template="https://www.energia.co.jp/nw/jukyuu/sys/juyo_07_{date}.csv",
        date_format="%Y%m%d",
        encoding_candidates=("cp932", "utf-8-sig", "utf-8"),
        notes="URL path not fully confirmed - Energia's csv.html page structure may differ, verify.",
    ),
    Area(
        id="shikoku",
        name_jp="四国",
        name_en="Shikoku",
        url_template="https://www.yonden.co.jp/nw/denkiyoho/juyo_shikoku.csv",
        date_format=None,
        encoding_candidates=("cp932", "utf-8-sig", "utf-8"),
    ),
    Area(
        id="kyushu",
        name_jp="九州",
        name_en="Kyushu",
        url_template="https://www.kyuden.co.jp/td_power_usages/csv/juyo-hourly-{date}.csv",
        date_format="%Y%m%d",
        encoding_candidates=("cp932", "utf-8-sig", "utf-8"),
    ),
    Area(
        id="okinawa",
        name_jp="沖縄",
        name_en="Okinawa",
        url_template="https://www.okiden.co.jp/denki2/juyo_10_{date}.csv",
        date_format="%Y%m%d",
        encoding_candidates=("cp932", "utf-8-sig", "utf-8"),
    ),
]

# Threshold tiers, expressed as usage rate (demand / supply capacity * 100).
# These roughly mirror the tiers Japan's grid coordinator (OCCTO) uses for its
# public reserve-margin warnings (reserve margin = 100 - usage rate):
#   reserve >= 8%  -> normal   (usage rate <= 92%)
#   reserve 3-8%   -> watch    (usage rate 92-97%)
#   reserve < 3%   -> alert    (usage rate > 97%)
WATCH_THRESHOLD_PCT = 92.0
ALERT_THRESHOLD_PCT = 97.0
