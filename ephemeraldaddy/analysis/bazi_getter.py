from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from lunar_python import Solar


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


def build_bazi_chart_data(dt_local: datetime) -> BaziChartData:
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

    return BaziChartData(
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
