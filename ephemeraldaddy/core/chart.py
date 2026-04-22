# ephemeraldaddy/core/chart.py
from .ephemeris import planetary_positions, planetary_retrogrades, local_sidereal_time_deg
from .houses import placidus_houses_and_axes, porphyry_houses
from .aspects import find_aspects
from .timeutils import localize_naive_datetime
from .interpretations import MODES, PLANET_ORDER
import datetime

ANGLE_BODIES = frozenset({"AS", "MC", "DS", "IC"})


def resolve_use_birth_time_data(chart) -> bool:
    return not bool(getattr(chart, "birthtime_unknown", False)) or bool(
        getattr(chart, "retcon_time_used", False)
    )


def sync_use_birth_time_data(chart) -> bool:
    resolved = resolve_use_birth_time_data(chart)
    try:
        chart.use_birth_time_data = resolved
    except Exception:
        pass
    return resolved


def chart_uses_houses(chart) -> bool:
    return sync_use_birth_time_data(chart)


def _effective_chart_datetime(chart) -> datetime.datetime | None:
    dt = getattr(chart, "dt", None)
    if not isinstance(dt, datetime.datetime):
        return None
    if chart_uses_houses(chart) and bool(getattr(chart, "retcon_time_used", False)):
        retcon_hour = getattr(chart, "retcon_hour", None)
        retcon_minute = getattr(chart, "retcon_minute", None)
        if retcon_hour is not None and retcon_minute is not None:
            try:
                return dt.replace(
                    hour=int(retcon_hour),
                    minute=int(retcon_minute),
                    second=0,
                    microsecond=0,
                )
            except Exception:
                return dt
    return dt


def sanitize_time_specific_metadata(chart) -> None:
    chart.houses = []
    chart.housesPo = []
    positions = getattr(chart, "positions", None) or {}
    for angle in ANGLE_BODIES:
        positions.pop(angle, None)
    chart.positions = positions
    aspects = getattr(chart, "aspects", None) or []
    chart.aspects = [
        aspect
        for aspect in aspects
        if str(aspect.get("p1", "")).strip() not in ANGLE_BODIES
        and str(aspect.get("p2", "")).strip() not in ANGLE_BODIES
    ]


def recompute_time_specific_metadata(chart) -> None:
    dt_effective = _effective_chart_datetime(chart)
    if dt_effective is None:
        sanitize_time_specific_metadata(chart)
        return
    lat = getattr(chart, "lat", None)
    lon = getattr(chart, "lon", None)
    if lat is None or lon is None:
        sanitize_time_specific_metadata(chart)
        return

    lst_deg = local_sidereal_time_deg(dt_effective, lon)
    chart.housesPo = porphyry_houses(lst_deg, lat)
    chart.houses, placidus_angles = placidus_houses_and_axes(dt_effective, lat, lon)

    positions = getattr(chart, "positions", None) or {}
    for angle in ANGLE_BODIES:
        positions.pop(angle, None)
    positions.update(placidus_angles)
    asc = positions.get("AS")
    mc = positions.get("MC")
    if asc is not None:
        positions["DS"] = (asc + 180.0) % 360.0
    if mc is not None:
        positions["IC"] = (mc + 180.0) % 360.0
    chart.positions = positions
    chart.aspects = find_aspects(chart.positions)


def apply_time_specific_metadata_policy(chart) -> None:
    use_birth_time_data = sync_use_birth_time_data(chart)
    if use_birth_time_data:
        recompute_time_specific_metadata(chart)
    else:
        sanitize_time_specific_metadata(chart)


class Chart:
    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)
        if name in {"birthtime_unknown", "retcon_time_used"}:
            object.__setattr__(self, "use_birth_time_data", resolve_use_birth_time_data(self))

    def __init__(
        self,
        name,
        dt_local,
        lat,
        lon,
        tz=None,
        alias: str | None = None,
        from_whence: str | None = None,
    ):
        """
        name: label for the chart
        dt_local: datetime in local civil time (may be naive)
        lat, lon: birth location coordinates (float)
        tz: optional explicit tzinfo (ZoneInfo or similar). If provided, overrides inference.
        """
        self.birth_place = None
        self.sentiments = []
        self.relationship_types = []
        self.tags = []
        self.comments = ""
        self.rectification_notes = ""
        self.biography = ""
        self.chart_data_source = ""
        self.positive_sentiment_intensity = 1
        self.negative_sentiment_intensity = 1
        self.familiarity = 1
        self.alignment_score = None
        self.matched_expectations = 0
        self.familiarity_factors = []
        self.dominant_sign_weights = {}
        self.dominant_planet_weights = {}
        self.dominant_nakshatra_weights = {}
        self.dominant_element_weights = {}
        self.dominant_mode = None
        self.human_design_gates = []
        self.human_design_lines = []
        self.human_design_channels = []
        self.bazi_year_pillar = ""
        self.bazi_month_pillar = ""
        self.bazi_day_pillar = ""
        self.bazi_hour_pillar = ""
        self.bazi_year_element = ""
        self.bazi_month_element = ""
        self.bazi_day_element = ""
        self.bazi_hour_element = ""
        self.age_when_first_met = 0
        self.year_first_encountered = None
        self.data_rating = "blank"
        self.chart_type = "personal"
        self.name = name
        self.alias = alias
        self.from_whence = from_whence
        self.gender = None
        self.lat = lat
        self.lon = lon
        self.birthtime_unknown = False
        self.signs_unknown = False
        self.unknown_signs = []
        self.dt_local = dt_local
        self.retcon_time_used = False
        self.retcon_hour = None
        self.retcon_minute = None
        self.use_birth_time_data = True
        self.is_deceased = False
        self._explicit_tz = tz
        self.used_utc_fallback = False  # will be set if tz inference falls back to UTC
        # # Now self.dt is guaranteed tz-aware:
        # self.positions = planetary_positions(self.dt, lat, lon)
        # # TRUE Placidus via Swiss Ephemeris
        # self.houses = placidus_houses(self.dt, lat, lon)
        # self.aspects = find_aspects(self.positions)

        if dt_local.tzinfo is not None:
            # already tz-aware, trust caller
            self.dt = dt_local
        elif tz is not None:
            # tz provided explicitly
            self.dt = dt_local.replace(tzinfo=tz)
        else:
            # infer timezone from lat/lon (may fall back to UTC)
            dt_aware, inferred_ok = localize_naive_datetime(dt_local, lat, lon)
            self.dt = dt_aware
            self.used_utc_fallback = not inferred_ok

        # Now self.dt is guaranteed tz-aware:
        self.positions = planetary_positions(self.dt, lat, lon)
        self.retrogrades = planetary_retrogrades(self.dt)

        # real RAMC/LST in degrees, based on this chart’s datetime and longitude
        self.housesPo = []
        self.houses = []
        self.aspects = []
        recompute_time_specific_metadata(self)
        self._add_part_of_fortune()
        self.aspects = find_aspects(self.positions)
        self.modal_distribution = self._modal_distribution()

    def as_dict(self):
        return {
            "name": self.name,
            "alias": self.alias,
            "from_whence": self.from_whence,
            "gender": self.gender,
            "datetime": str(self.dt),
            "lat": self.lat,
            "lon": self.lon,
            "sentiments": self.sentiments,
            "relationship_types": self.relationship_types,
            "tags": self.tags,
            "comments": self.comments,
            "rectification_notes": self.rectification_notes,
            "biography": self.biography,
            "chart_data_source": self.chart_data_source,
            "chart_type": self.chart_type,
            "source": self.chart_type,
            "positive_sentiment_intensity": self.positive_sentiment_intensity,
            "negative_sentiment_intensity": self.negative_sentiment_intensity,
            "familiarity": self.familiarity,
            "alignment_score": self.alignment_score,
            "matched_expectations": self.matched_expectations,
            "familiarity_factors": self.familiarity_factors,
            "human_design_gates": self.human_design_gates,
            "human_design_lines": self.human_design_lines,
            "human_design_channels": self.human_design_channels,
            "bazi_year_pillar": self.bazi_year_pillar,
            "bazi_month_pillar": self.bazi_month_pillar,
            "bazi_day_pillar": self.bazi_day_pillar,
            "bazi_hour_pillar": self.bazi_hour_pillar,
            "bazi_year_element": self.bazi_year_element,
            "bazi_month_element": self.bazi_month_element,
            "bazi_day_element": self.bazi_day_element,
            "bazi_hour_element": self.bazi_hour_element,
            "dominant_sign_weights": self.dominant_sign_weights,
            "dominant_planet_weights": self.dominant_planet_weights,
            "dominant_nakshatra_weights": self.dominant_nakshatra_weights,
            "dominant_element_weights": self.dominant_element_weights,
            "dominant_mode": self.dominant_mode,
            "age_when_first_met": self.age_when_first_met,
            "year_first_encountered": self.year_first_encountered,
            "data_rating": self.data_rating,
            "positions": self.positions,
            "retrogrades": self.retrogrades,
            "houses": self.houses,
            "aspects": self.aspects,
            "modal_distribution": self.modal_distribution,
            "used_utc_fallback": self.used_utc_fallback,
            "use_birth_time_data": bool(getattr(self, "use_birth_time_data", chart_uses_houses(self))),
            "signs_unknown": bool(getattr(self, "signs_unknown", False)),
            "unknown_signs": list(getattr(self, "unknown_signs", []) or []),
        }


    @property
    def sentiment_confidence(self):
        """Backwards-compatible alias for renamed `familiarity` metric."""
        return self.familiarity

    @sentiment_confidence.setter
    def sentiment_confidence(self, value):
        self.familiarity = value

    @property
    def source(self):
        """Backwards-compatible alias for older code paths using `source`."""
        return self.chart_type

    @source.setter
    def source(self, value):
        self.chart_type = value

    @property
    def social_score(self) -> int:
        familiarity = int(getattr(self, "familiarity", 1) or 1)
        positive = int(getattr(self, "positive_sentiment_intensity", 1) or 1)
        negative = int(getattr(self, "negative_sentiment_intensity", 1) or 1)
        return (positive * familiarity) - (negative * familiarity)

    def _modal_distribution(self) -> dict[str, float]:
        mode_counts = {"cardinal": 0.0, "mutable": 0.0, "fixed": 0.0}
        for body, lon in self.positions.items():
            if body in {"AS", "MC", "DS", "IC"}:
                continue
            if lon is None:
                continue
            sign_index = int((float(lon) % 360.0) // 30)
            sign = (
                "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
            )[sign_index]
            for mode, signs in MODES.items():
                if sign in signs:
                    mode_counts[mode] += 1.0
                    break
        total = max(1.0, sum(mode_counts.values()))
        return {mode: count / total for mode, count in mode_counts.items()}

    def _add_part_of_fortune(self) -> None:
        asc = self.positions.get("AS")
        sun = self.positions.get("Sun")
        moon = self.positions.get("Moon")
        if asc is None or sun is None or moon is None:
            return

        is_day_chart = False
        if self.houses and isinstance(self.houses, (list, tuple)) and len(self.houses) >= 12:
            house_index = self._house_index(sun, self.houses)
            if house_index is not None:
                is_day_chart = 7 <= (house_index + 1) <= 12

        if is_day_chart:
            pof = (asc + moon - sun) % 360.0
        else:
            pof = (asc + sun - moon) % 360.0

        self.positions["Part of Fortune"] = pof

    @staticmethod
    def _house_index(lon: float, cusps: list[float]) -> int | None:
        lon = lon % 360.0
        for i in range(12):
            start = cusps[i] % 360.0
            end = cusps[(i + 1) % 12] % 360.0
            if end <= start:
                end += 360.0
            lon_cmp = lon
            if lon_cmp < start:
                lon_cmp += 360.0
            if start <= lon_cmp < end:
                return i
        return None


def _sign_for_longitude(lon: float) -> str:
    signs = (
        "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
    )
    return signs[int((float(lon) % 360.0) // 30)]


def compute_unknown_sign_positions(chart: Chart) -> list[str]:
    """
    Return body names whose sign differs between 00:00 and 23:59 local time.
    """
    # Conditional indicators for unknown birth time are based on factual
    # unknown-time status; they should not be disabled by rectified time usage.
    if (
        not bool(getattr(chart, "birthtime_unknown", False))
        or getattr(getattr(chart, "dt", None), "tzinfo", None) is None
    ):
        return []
    base_date = chart.dt.date()
    tzinfo = chart.dt.tzinfo
    midnight = datetime.datetime(base_date.year, base_date.month, base_date.day, 0, 0, tzinfo=tzinfo)
    pre_midnight = datetime.datetime(base_date.year, base_date.month, base_date.day, 23, 59, tzinfo=tzinfo)
    positions_midnight = planetary_positions(midnight, chart.lat, chart.lon)
    positions_pre_midnight = planetary_positions(pre_midnight, chart.lat, chart.lon)
    ordered_names = [body for body in PLANET_ORDER if body in positions_midnight and body in positions_pre_midnight]
    extras = sorted(
        set(positions_midnight).intersection(positions_pre_midnight).difference(ordered_names)
    )
    ordered_names.extend(extras)
    unknown_positions: list[str] = []
    for body in ordered_names:
        if _sign_for_longitude(positions_midnight[body]) != _sign_for_longitude(positions_pre_midnight[body]):
            unknown_positions.append(body)
    return unknown_positions


def apply_unknown_sign_metadata(chart: Chart) -> None:
    unknown_positions = compute_unknown_sign_positions(chart)
    chart.unknown_signs = unknown_positions
    chart.signs_unknown = bool(unknown_positions)
