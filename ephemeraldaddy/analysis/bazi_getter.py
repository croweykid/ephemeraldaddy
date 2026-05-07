from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Any, Mapping

from lunar_python import Solar

UNKNOWN_BAZI_VALUE = "Unknown"

BAZI_BRANCH_TO_SIGN = {
    "子": "Rat",
    "丑": "Ox",
    "寅": "Tiger",
    "卯": "Rabbit",
    "辰": "Dragon",
    "巳": "Snake",
    "午": "Horse",
    "未": "Goat",
    "申": "Monkey",
    "酉": "Rooster",
    "戌": "Dog",
    "亥": "Pig",
}
BAZI_SIGN_ALIASES = {
    "rat": "Rat",
    "ox": "Ox",
    "tiger": "Tiger",
    "rabbit": "Rabbit",
    "dragon": "Dragon",
    "snake": "Snake",
    "horse": "Horse",
    "goat": "Goat",
    "sheep": "Goat",
    "ram": "Goat",
    "monkey": "Monkey",
    "rooster": "Rooster",
    "chicken": "Rooster",
    "dog": "Dog",
    "pig": "Pig",
    "boar": "Pig",
}


@dataclass(frozen=True)
class BaziChartData:
    lunar_date_str: str
    zodiac_animal: str
    year_pillar: str
    month_pillar: str
    day_pillar: str
    hour_pillar: str
    heavenly_stems: dict[str, str]
    earthly_branches: dict[str, str]
    five_elements_summary: dict[str, Any]
    ten_gods_summary: dict[str, str]


def build_bazi_chart_data(dt_local: datetime, *, include_hour: bool = True) -> BaziChartData:
    """Generate BaZi data using local civil birth date/time."""
    solar = Solar.fromYmdHms(
        dt_local.year,
        dt_local.month,
        dt_local.day,
        dt_local.hour,
        dt_local.minute,
        dt_local.second,
    )
    lunar = solar.getLunar()
    ec = lunar.getEightChar()

    bazi_data = BaziChartData(
        lunar_date_str=lunar.toString(),
        zodiac_animal=lunar.getYearShengXiao(),
        year_pillar=ec.getYear(),
        month_pillar=ec.getMonth(),
        day_pillar=ec.getDay(),
        hour_pillar=ec.getTime(),
        heavenly_stems={
            "year": ec.getYearGan(),
            "month": ec.getMonthGan(),
            "day": ec.getDayGan(),
            "hour": ec.getTimeGan(),
        },
        earthly_branches={
            "year": ec.getYearZhi(),
            "month": ec.getMonthZhi(),
            "day": ec.getDayZhi(),
            "hour": ec.getTimeZhi(),
        },
        five_elements_summary={
            "year": ec.getYearWuXing(),
            "month": ec.getMonthWuXing(),
            "day": ec.getDayWuXing(),
            "hour": ec.getTimeWuXing(),
            "na_yin": {
                "year": ec.getYearNaYin(),
                "month": ec.getMonthNaYin(),
                "day": ec.getDayNaYin(),
                "hour": ec.getTimeNaYin(),
            },
        },
        ten_gods_summary={
            "year": ec.getYearShiShenGan(),
            "month": ec.getMonthShiShenGan(),
            "hour": ec.getTimeShiShenGan(),
            "day_branch_main": ec.getDayShiShenZhi(),
        },
    )
    if include_hour:
        return bazi_data

    heavenly_stems = dict(bazi_data.heavenly_stems)
    heavenly_stems["hour"] = UNKNOWN_BAZI_VALUE

    earthly_branches = dict(bazi_data.earthly_branches)
    earthly_branches["hour"] = UNKNOWN_BAZI_VALUE

    na_yin = dict(bazi_data.five_elements_summary.get("na_yin", {}))
    na_yin["hour"] = UNKNOWN_BAZI_VALUE

    five_elements_summary = dict(bazi_data.five_elements_summary)
    five_elements_summary["hour"] = UNKNOWN_BAZI_VALUE
    five_elements_summary["na_yin"] = na_yin

    ten_gods_summary = dict(bazi_data.ten_gods_summary)
    ten_gods_summary["hour"] = UNKNOWN_BAZI_VALUE

    return BaziChartData(
        lunar_date_str=bazi_data.lunar_date_str,
        zodiac_animal=bazi_data.zodiac_animal,
        year_pillar=bazi_data.year_pillar,
        month_pillar=bazi_data.month_pillar,
        day_pillar=bazi_data.day_pillar,
        hour_pillar=UNKNOWN_BAZI_VALUE,
        heavenly_stems=heavenly_stems,
        earthly_branches=earthly_branches,
        five_elements_summary=five_elements_summary,
        ten_gods_summary=ten_gods_summary,
    )


def _normalized_bazi_token_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().casefold()).strip("_")


def normalize_bazi_sign_value(value: Any) -> str:
    text = str(value).strip()
    if not text or text == UNKNOWN_BAZI_VALUE:
        return ""
    for char in text:
        sign = BAZI_BRANCH_TO_SIGN.get(char)
        if sign:
            return sign
    parenthetical = re.search(r"\(([^()]+)\)", text)
    if parenthetical:
        text = parenthetical.group(1).strip()
    key = _normalized_bazi_token_key(text)
    return BAZI_SIGN_ALIASES.get(key, text.title())


def bazi_include_hour_for_chart(chart: Any) -> bool:
    from ephemeraldaddy.core.chart import chart_uses_houses

    return chart_uses_houses(chart)


def effective_bazi_datetime_and_hour_policy(chart: Any) -> tuple[datetime | None, bool]:
    dt_local = getattr(chart, "dt_local", None)
    chart_dt = getattr(chart, "dt", None)
    if dt_local is None and isinstance(chart_dt, datetime):
        dt_local = (
            chart_dt.astimezone(chart_dt.tzinfo).replace(tzinfo=None)
            if chart_dt.tzinfo is not None
            else chart_dt
        )
    include_hour = bazi_include_hour_for_chart(chart)
    if not isinstance(dt_local, datetime):
        return None, include_hour
    if include_hour and bool(getattr(chart, "retcon_time_used", False)):
        retcon_hour = getattr(chart, "retcon_hour", None)
        retcon_minute = getattr(chart, "retcon_minute", None)
        if retcon_hour is not None and retcon_minute is not None:
            try:
                dt_local = dt_local.replace(
                    hour=int(retcon_hour),
                    minute=int(retcon_minute),
                    second=0,
                    microsecond=0,
                )
            except Exception:
                pass
    return dt_local, include_hour


def bazi_sign_weights_from_pillars(chart: Any, *, include_hour: bool) -> dict[str, float]:
    weights: dict[str, float] = {}
    pillar_attrs = ["bazi_year_pillar", "bazi_month_pillar", "bazi_day_pillar"]
    if include_hour:
        pillar_attrs.append("bazi_hour_pillar")
    for attr_name in pillar_attrs:
        sign = normalize_bazi_sign_value(getattr(chart, attr_name, ""))
        if sign:
            weights[sign] = weights.get(sign, 0.0) + 1.0
    return weights


def bazi_sign_weights_from_data(bazi_data: BaziChartData) -> dict[str, float]:
    weights: dict[str, float] = {}
    for branch in getattr(bazi_data, "earthly_branches", {}).values():
        sign = normalize_bazi_sign_value(branch)
        if sign:
            weights[sign] = weights.get(sign, 0.0) + 1.0
    return weights


def bazi_sign_weights_from_chart(chart: Any) -> dict[str, float]:
    dt_local, include_hour = effective_bazi_datetime_and_hour_policy(chart)
    pillar_weights = bazi_sign_weights_from_pillars(chart, include_hour=include_hour)
    if pillar_weights:
        return pillar_weights
    for attr_name in ("bazi_sign_weights", "bazi_branch_weights", "dominant_bazi_sign_weights"):
        raw_weights = getattr(chart, attr_name, None)
        if not isinstance(raw_weights, Mapping) or not raw_weights:
            continue
        weights: dict[str, float] = {}
        for raw_sign, raw_weight in raw_weights.items():
            sign = normalize_bazi_sign_value(raw_sign)
            if not sign:
                continue
            try:
                weight = float(raw_weight)
            except (TypeError, ValueError):
                weight = 0.0
            weights[sign] = weights.get(sign, 0.0) + weight
        if weights:
            return weights
    if dt_local is None:
        return {}
    return bazi_sign_weights_from_data(build_bazi_chart_data(dt_local, include_hour=include_hour))