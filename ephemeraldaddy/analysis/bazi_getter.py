from lunar_python import Solar

@dataclass
class BaziChartData:
    lunar_date_str: str
    zodiac_animal: str
    year_pillar: str
    month_pillar: str
    day_pillar: str
    hour_pillar: str
    heavenly_stems: dict
    earthly_branches: dict
    five_elements_summary: dict
    ten_gods_summary: dict

solar = Solar.fromYmdHms(1990, 12, 31, 6, 30, 0)
lunar = solar.getLunar()
ec = lunar.getEightChar()

data = {
    "year_pillar": ec.getYear(),
    "month_pillar": ec.getMonth(),
    "day_pillar": ec.getDay(),
    "hour_pillar": ec.getTime(),
    "year_zodiac": lunar.getYearShengXiao(),
    "day_gan": ec.getDayGan(),
    "day_zhi": ec.getDayZhi(),
}
print(data)