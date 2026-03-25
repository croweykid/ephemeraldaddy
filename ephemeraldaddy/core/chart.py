# ephemeraldaddy/core/chart.py
from .ephemeris import planetary_positions, planetary_retrogrades, local_sidereal_time_deg
from .houses import placidus_houses_and_axes, porphyry_houses
from .aspects import find_aspects
from .timeutils import localize_naive_datetime
from .interpretations import MODES

class Chart:
    def __init__(self, name, dt_local, lat, lon, tz=None, alias: str | None = None):
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
        self.chart_data_source = ""
        self.positive_sentiment_intensity = 1
        self.negative_sentiment_intensity = 1
        self.familiarity = 1
        self.alignment_score = None
        self.familiarity_factors = []
        self.age_when_first_met = 0
        self.year_first_encountered = None
        self.chart_type = "personal"
        self.name = name
        self.alias = alias
        self.gender = None
        self.lat = lat
        self.lon = lon
        self.birthtime_unknown = False
        self.dt_local = dt_local
        self.retcon_time_used = False
        self.retcon_hour = None
        self.retcon_minute = None
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
        lst_deg = local_sidereal_time_deg(self.dt, lon)
        self.housesPo = porphyry_houses(lst_deg, lat) #porphyry house definitions
        self.houses, placidus_angles = placidus_houses_and_axes(self.dt, lat, lon)
        self.positions.update(placidus_angles)
        asc = self.positions.get("AS")
        mc = self.positions.get("MC")
        if asc is not None:
            self.positions["DS"] = (asc + 180.0) % 360.0
        if mc is not None:
            self.positions["IC"] = (mc + 180.0) % 360.0

        self._add_part_of_fortune()
        self.aspects = find_aspects(self.positions)
        self.modal_distribution = self._modal_distribution()

    def as_dict(self):
        return {
            "name": self.name,
            "alias": self.alias,
            "gender": self.gender,
            "datetime": str(self.dt),
            "lat": self.lat,
            "lon": self.lon,
            "sentiments": self.sentiments,
            "relationship_types": self.relationship_types,
            "tags": self.tags,
            "comments": self.comments,
            "chart_data_source": self.chart_data_source,
            "chart_type": self.chart_type,
            "source": self.chart_type,
            "positive_sentiment_intensity": self.positive_sentiment_intensity,
            "negative_sentiment_intensity": self.negative_sentiment_intensity,
            "familiarity": self.familiarity,
            "alignment_score": self.alignment_score,
            "familiarity_factors": self.familiarity_factors,
            "age_when_first_met": self.age_when_first_met,
            "year_first_encountered": self.year_first_encountered,
            "positions": self.positions,
            "retrogrades": self.retrogrades,
            "houses": self.houses,
            "aspects": self.aspects,
            "modal_distribution": self.modal_distribution,
            "used_utc_fallback": self.used_utc_fallback,
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
