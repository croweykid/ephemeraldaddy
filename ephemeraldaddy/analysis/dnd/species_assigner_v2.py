
from __future__ import annotations

# Merge your existing SPECIES_SUBVARIANT_EXPLAINER_TEMPLATE into this file if you want the descriptions co-located.

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
import math

from ephemeraldaddy.analysis.dnd.dnd_definitions import FAMILY_SUBTYPES, SPECIES_FAMILIES

from ephemeraldaddy.core.interpretations import (
    ASPECT_ANGLE_DEGREES,
    ASPECT_ORB_ALLOWANCES,
    ASPECT_SCORE_WEIGHTS,
    ASPECT_TYPES,
    MODES,
    NATAL_BODY_LOUDNESS,
    SIGN_ELEMENTS,
    SIGN_KEYWORDS,
)

SIGN_CLASSICAL_TRAITS = ("mute", "humane", "bestial", "feral", "quadrupedian", "bicorporeal")
SIGN_SEASONS = ("vernal", "aestival", "autumnal", "hyemal")
SIGN_FERTILITY = ("fruitful", "barren")
_BODY_WEIGHT_SCALE = max(float(v) for v in NATAL_BODY_LOUDNESS.values()) if NATAL_BODY_LOUDNESS else 1.0
BODY_WEIGHTS: Dict[str, float] = {body: float(weight) / _BODY_WEIGHT_SCALE for body, weight in NATAL_BODY_LOUDNESS.items()}

DERIVED_ASPECTS: Sequence[Tuple[str, float, float]] = tuple(
    (name, float(ASPECT_ANGLE_DEGREES[name]), float(ASPECT_ORB_ALLOWANCES[name]))
    for name in ASPECT_SCORE_WEIGHTS
    if name in ASPECT_ANGLE_DEGREES and name in ASPECT_ORB_ALLOWANCES
)

HARD_ASPECTS = set(ASPECT_TYPES["stress/friction"]["aspects"]) | {"conjunction"}
SOFT_ASPECTS = set(ASPECT_TYPES["chill vibes"]["aspects"])
ALL_MAJOR_ASPECTS = HARD_ASPECTS | SOFT_ASPECTS | {"quincunx"}

SPECIES_DISTRIBUTION_CALIBRATION: Dict[str, float] = {
    # Frequently over-selected broad buckets.
    "Human": 0.84,
    "Halfling": 0.92,
    "Dwarf": 0.94,
    "Orcs": 0.94,
    "Half-orcs": 0.95,
    # Under-selected families reported in production data.
    "Shapeshifter": 1.38,
    "Triton": 1.30,
    "Rodentfolk": 1.30,
    "Elf": 1.24,
}


@dataclass(frozen=True)
class SpeciesPick:
    family: str
    subtype: str
    score: float
    runner_up: Optional[Tuple[str, str, float]]
    top_three: List[Tuple[str, str, float]]
    evidence: List[str]


@dataclass
class ScoreCard:
    score: float = 0.0
    reasons: List[str] = None

    def __post_init__(self) -> None:
        if self.reasons is None:
            self.reasons = []

    def add(self, amount: float, reason: Optional[str] = None) -> None:
        self.score += amount
        if reason:
            self.reasons.append(reason)


class SpeciesAssigner:
    """
    Reworked classifier.

    Design:
    1) normalize chart input,
    2) extract stable symbolic features once,
    3) score families from the same feature space,
    4) choose subtype inside the winning family.

    No end-of-function score multipliers.
    No duplicate billing of the same planetary signal within one family.
    """

    def __init__(
        self,
        *,
        tight_orb_deg: float = 3.0,
        default_orb_deg: float = 6.0,
        angle_window_deg: float = 4.0,
        angle_conj_deg: float = 3.0,
    ) -> None:
        self.tight_orb_deg = tight_orb_deg
        self.default_orb_deg = default_orb_deg
        self.angle_window_deg = angle_window_deg
        self.angle_conj_deg = angle_conj_deg

    # ----------------------------
    # Public API
    # ----------------------------

    def assign(self, chart: Any) -> SpeciesPick:
        positions = self._get_positions(chart)
        aspects = self._get_aspects(chart, positions)
        feats = self._extract_features(positions, aspects)
        scores = self._score_families(positions, aspects, feats)

        ranked = self._rank_families(scores)
        ranked = self._apply_human_fallback_policy(ranked)
        top = ranked[:3]
        (fam1, card1) = top[0]
        subtype1, subtype_ev1 = self._pick_subtype(fam1, positions, aspects, feats)

        runner_up = None
        if len(top) > 1:
            fam2, card2 = top[1]
            subtype2, _ = self._pick_subtype(fam2, positions, aspects, feats)
            runner_up = (fam2, subtype2, round(card2.score, 3))

        top_three: List[Tuple[str, str, float]] = []
        for fam, card in top:
            subtype, _ = self._pick_subtype(fam, positions, aspects, feats)
            top_three.append((fam, subtype, round(card.score, 3)))

        evidence = self._compact_evidence(card1.reasons, subtype_ev1, feats)

        return SpeciesPick(
            family=fam1,
            subtype=subtype1,
            score=round(card1.score, 3),
            runner_up=runner_up,
            top_three=top_three,
            evidence=evidence,
        )

    @staticmethod
    def _rank_families(scores: Mapping[str, ScoreCard]) -> List[Tuple[str, ScoreCard]]:
        """
        Rank *all* species families by score (best first).

        We explicitly iterate `SPECIES_FAMILIES` so ranking always considers the
        full option set, not just whichever score entries happen to be present.
        """
        ranked: List[Tuple[str, ScoreCard]] = []
        for family in SPECIES_FAMILIES:
            card = scores.get(family, ScoreCard())
            try:
                numeric_score = float(card.score)
            except (TypeError, ValueError):
                numeric_score = float("-inf")
            if math.isnan(numeric_score):
                numeric_score = float("-inf")
            ranked.append((family, ScoreCard(score=numeric_score, reasons=list(card.reasons or []))))
        ranked.sort(key=lambda kv: kv[1].score, reverse=True)
        return ranked

    @staticmethod
    def _apply_human_fallback_policy(
        ranked: List[Tuple[str, ScoreCard]],
        *,
        minimum_non_human_score: float = 1.05,
        minimum_margin_over_human: float = -0.20,
    ) -> List[Tuple[str, ScoreCard]]:
        """
        Keep Human as a true fallback.

        Policy:
        - if Human is already not first, keep ranking unchanged;
        - if Human is first but a non-Human score is still plausible, promote the
          strongest non-Human to the top;
        - only keep Human first when everything else is weak/noisy.
        """
        if not ranked:
            return ranked

        top_family, top_card = ranked[0]
        if top_family != "Human":
            return ranked

        human_score = float(top_card.score)
        best_non_human_idx: Optional[int] = None
        best_non_human_score = float("-inf")
        for idx, (family, card) in enumerate(ranked):
            if family == "Human":
                continue
            score = float(card.score)
            if score > best_non_human_score:
                best_non_human_score = score
                best_non_human_idx = idx

        if best_non_human_idx is None:
            return ranked

        non_human_is_plausible = (
            best_non_human_score >= minimum_non_human_score
            and (best_non_human_score - human_score) >= minimum_margin_over_human
        )
        if not non_human_is_plausible:
            return ranked

        adjusted = list(ranked)
        adjusted[0], adjusted[best_non_human_idx] = adjusted[best_non_human_idx], adjusted[0]
        return adjusted

    # ----------------------------
    # Data ingestion
    # ----------------------------

    @staticmethod
    def _first_non_none(*values: Any) -> Any:
        for value in values:
            if value is not None:
                return value
        return None

    @staticmethod
    def _clamp01(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(high, float(value)))

    @staticmethod
    def _safe_ratio(numerator: float, denominator: float) -> float:
        return float(numerator) / max(1e-9, float(denominator))

    def _get_positions(self, chart: Any) -> Dict[str, Dict[str, Any]]:
        if hasattr(chart, "positions") and isinstance(getattr(chart, "positions"), Mapping):
            return self._from_native_chart(chart)

        pos = chart.get("positions") or chart.get("planets") or {}
        if not isinstance(pos, Mapping):
            raise TypeError("chart['positions'] (or chart['planets']) must be a mapping")

        out: Dict[str, Dict[str, Any]] = {}
        for body, raw in pos.items():
            if not isinstance(raw, Mapping):
                continue

            lon = self._first_non_none(
                raw.get("lon"),
                raw.get("longitude"),
                raw.get("ecl_lon"),
                raw.get("deg"),
            )
            sign = raw.get("sign")
            house = raw.get("house")

            lon_value: Optional[float] = None
            if lon is not None:
                lon_value = float(lon) % 360.0

            sign_value = str(sign) if sign else None
            house_value = int(house) if house is not None else None

            if lon_value is None and sign_value is None:
                continue

            if sign_value is None and lon_value is not None:
                sign_value = self._sign_for_longitude(lon_value)

            out[str(body)] = {"lon": lon_value, "sign": sign_value, "house": house_value}
        return out

    def _from_native_chart(self, chart: Any) -> Dict[str, Dict[str, Any]]:
        raw_positions = getattr(chart, "positions", {}) or {}
        houses = getattr(chart, "houses", None)
        out: Dict[str, Dict[str, Any]] = {}

        for body, raw in raw_positions.items():
            lon: Optional[float] = None
            sign: Optional[str] = None
            house: Optional[int] = None

            if isinstance(raw, Mapping):
                lon = self._first_non_none(
                    raw.get("lon"),
                    raw.get("longitude"),
                    raw.get("ecl_lon"),
                    raw.get("deg"),
                )
                sign = raw.get("sign")
                house = raw.get("house")
            else:
                try:
                    lon = float(raw)
                except (TypeError, ValueError):
                    lon = None

            if lon is not None:
                lon = lon % 360.0
                if sign is None:
                    sign = self._sign_for_longitude(lon)
                if house is None:
                    house = self._house_for_longitude(houses, lon)

            if lon is None and sign is None:
                continue

            out[str(body)] = {
                "lon": lon,
                "sign": str(sign) if sign else None,
                "house": int(house) if house is not None else None,
            }

        return out

    def _get_aspects(
        self,
        chart: Any,
        positions: Mapping[str, Mapping[str, Any]],
    ) -> List[Dict[str, Any]]:
        raw = chart.get("aspects") if isinstance(chart, Mapping) else getattr(chart, "aspects", None)
        if isinstance(raw, list) and raw:
            normalized: List[Dict[str, Any]] = []
            for item in raw:
                if not isinstance(item, Mapping):
                    continue
                p1 = str(item.get("p1") or item.get("planet1") or item.get("from") or "")
                p2 = str(item.get("p2") or item.get("planet2") or item.get("to") or "")
                aspect = str(item.get("aspect") or item.get("type") or "").lower().strip()
                orb = item.get("orb")
                if orb is None and item.get("delta") is not None:
                    orb = abs(float(item.get("delta")))
                if not p1 or not p2 or not aspect:
                    continue
                normalized.append({
                    "p1": p1,
                    "p2": p2,
                    "aspect": self._normalize_aspect_name(aspect),
                    "orb": float(orb) if orb is not None else None,
                })
            if normalized:
                return normalized
        return self._derive_aspects(positions)

    def _derive_aspects(self, positions: Mapping[str, Mapping[str, Any]]) -> List[Dict[str, Any]]:
        bodies = [body for body, info in positions.items() if info.get("lon") is not None]
        out: List[Dict[str, Any]] = []

        for i in range(len(bodies)):
            for j in range(i + 1, len(bodies)):
                p1 = bodies[i]
                p2 = bodies[j]
                lon1 = float(positions[p1]["lon"])
                lon2 = float(positions[p2]["lon"])
                delta = self._angle_delta(lon1, lon2)

                best_name: Optional[str] = None
                best_orb: Optional[float] = None
                best_limit: float = 999.0

                for name, target, limit in DERIVED_ASPECTS:
                    orb = abs(delta - target)
                    if orb <= min(limit, self.default_orb_deg):
                        if best_orb is None or orb < best_orb:
                            best_name = name
                            best_orb = orb
                            best_limit = limit

                if best_name is not None and best_orb is not None:
                    out.append({"p1": p1, "p2": p2, "aspect": best_name, "orb": float(best_orb)})

        return out

    # ----------------------------
    # Feature extraction
    # ----------------------------

    def _extract_features(
        self,
        positions: Mapping[str, Mapping[str, Any]],
        aspects: List[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        element_totals = {"Fire": 0.0, "Earth": 0.0, "Air": 0.0, "Water": 0.0}
        mode_totals = {"cardinal": 0.0, "fixed": 0.0, "mutable": 0.0}
        sign_totals = {sign: 0.0 for sign in SIGN_ELEMENTS}
        trait_totals = {trait: 0.0 for trait in SIGN_CLASSICAL_TRAITS}
        season_totals = {season: 0.0 for season in SIGN_SEASONS}
        fertility_totals = {fertility: 0.0 for fertility in SIGN_FERTILITY}
        house_totals: Dict[int, float] = {}

        total_weight = 0.0
        for body, info in positions.items():
            sign = info.get("sign")
            if not sign or sign not in SIGN_ELEMENTS:
                continue
            weight = BODY_WEIGHTS.get(body, 0.5)
            total_weight += weight

            element_totals[SIGN_ELEMENTS[sign]] += weight
            sign_totals[sign] += weight

            for mode, signs in MODES.items():
                if sign in signs:
                    mode_totals[mode] += weight
                    break

            trait_meta = SIGN_KEYWORDS.get(str(sign).title(), {})
            for trait in SIGN_CLASSICAL_TRAITS:
                if trait_meta.get(trait) is True:
                    trait_totals[trait] += weight
            season = trait_meta.get("season")
            if season in season_totals:
                season_totals[str(season)] += weight
            fertility = trait_meta.get("fertility")
            if fertility in fertility_totals:
                fertility_totals[str(fertility)] += weight

            house = info.get("house")
            if house is not None:
                house_totals[int(house)] = house_totals.get(int(house), 0.0) + weight

        element_ratios = {k: self._safe_ratio(v, total_weight) for k, v in element_totals.items()}
        mode_ratios = {k: self._safe_ratio(v, total_weight) for k, v in mode_totals.items()}
        sign_ratios = {k: self._safe_ratio(v, total_weight) for k, v in sign_totals.items()}
        trait_ratios = {k: self._safe_ratio(v, total_weight) for k, v in trait_totals.items()}
        season_ratios = {k: self._safe_ratio(v, total_weight) for k, v in season_totals.items()}
        fertility_ratios = {k: self._safe_ratio(v, total_weight) for k, v in fertility_totals.items()}
        house_ratios = {k: self._safe_ratio(v, total_weight) for k, v in house_totals.items()}

        prominence = {body: self._planet_prominence(body, positions, aspects) for body in positions}

        personal_bodies = ("Sun", "Moon", "AS", "Mercury", "Venus", "Mars")
        personal_signals = {
            body: positions.get(body, {}).get("sign")
            for body in personal_bodies
            if body in positions
        }

        dominant_element = max(element_ratios.items(), key=lambda kv: kv[1])[0]
        dominant_ratio = max(element_ratios.values()) if element_ratios else 0.0
        balance_score = 1.0 - max(0.0, dominant_ratio - 0.25) / 0.25
        balance_score = self._clamp01(balance_score)
        taurus_stellium_count = sum(
            1
            for body, info in positions.items()
            if body in BODY_WEIGHTS and info.get("sign") == "Taurus"
        )
        taurus_dominance_weight = self._clamp01(
            0.65 * float(sign_ratios.get("Taurus", 0.0))
            + 0.35 * self._clamp01(max(0.0, taurus_stellium_count - 2) / 4.0)
        )

        tight_outer_to_identity = []
        for outer in ("Uranus", "Neptune", "Pluto"):
            for target in ("Sun", "Moon", "AS"):
                strength = self._aspect_strength(outer, target, aspects, ALL_MAJOR_ASPECTS, max_orb=self.tight_orb_deg)
                if strength > 0.0:
                    tight_outer_to_identity.append((outer, target, strength))

        spikiness = self._clamp01(
            0.45 * dominant_ratio
            + 0.20 * max(prominence.get("Uranus", 0.0), prominence.get("Neptune", 0.0), prominence.get("Pluto", 0.0))
            + 0.25 * self._clamp01(len(tight_outer_to_identity) / 4.0)
            + 0.10 * self._clamp01(sum(1 for value in prominence.values() if value >= 0.75) / 5.0)
        )

        return {
            "element_totals": element_totals,
            "element_ratios": element_ratios,
            "mode_ratios": mode_ratios,
            "sign_ratios": sign_ratios,
            "trait_ratios": trait_ratios,
            "season_ratios": season_ratios,
            "fertility_ratios": fertility_ratios,
            "house_ratios": house_ratios,
            "prominence": prominence,
            "dominant_element": dominant_element,
            "dominant_ratio": dominant_ratio,
            "balance_score": balance_score,
            "spikiness": spikiness,
            "taurus_stellium_count": taurus_stellium_count,
            "taurus_dominance_weight": taurus_dominance_weight,
            "tight_outer_to_identity": tight_outer_to_identity,
            "aspect_count": len(aspects),
            "personal_signals": personal_signals,
            "positions": positions,
        }

    def _planet_prominence(
        self,
        body: str,
        positions: Mapping[str, Mapping[str, Any]],
        aspects: List[Mapping[str, Any]],
    ) -> float:
        if body not in positions:
            return 0.0

        info = positions[body]
        if info.get("sign") is None and info.get("lon") is None:
            return 0.0

        score = 0.15
        house = info.get("house")
        if house in (1, 10):
            score += 0.30
        elif house in (4, 7):
            score += 0.22

        for angle in ("AS", "MC", "DS", "IC"):
            if positions.get(angle, {}).get("lon") is None or info.get("lon") is None:
                continue
            delta = self._angle_delta(float(info["lon"]), float(positions[angle]["lon"]))
            if delta <= self.angle_window_deg:
                closeness = 1.0 - (delta / max(1e-9, self.angle_window_deg))
                score += 0.25 * closeness

        if body not in {"Sun", "Moon", "AS"}:
            identity_tie = max(
                self._aspect_strength(body, "Sun", aspects, ALL_MAJOR_ASPECTS, max_orb=self.tight_orb_deg),
                self._aspect_strength(body, "Moon", aspects, ALL_MAJOR_ASPECTS, max_orb=self.tight_orb_deg),
                self._aspect_strength(body, "AS", aspects, ALL_MAJOR_ASPECTS, max_orb=self.tight_orb_deg),
            )
            score += 0.22 * identity_tie

        if body in {"Sun", "Moon", "AS"}:
            score += 0.15

        return self._clamp01(score)

    # ----------------------------
    # Scoring
    # ----------------------------

    def _score_families(
        self,
        positions: Mapping[str, Mapping[str, Any]],
        aspects: List[Mapping[str, Any]],
        feats: Mapping[str, Any],
    ) -> Dict[str, ScoreCard]:
        cards: Dict[str, ScoreCard] = {family: ScoreCard() for family in SPECIES_FAMILIES}

        er = feats["element_ratios"]
        mr = feats["mode_ratios"]
        sr = feats["sign_ratios"]
        tr = feats["trait_ratios"]
        hr = feats["house_ratios"]
        prom = feats["prominence"]
        balance = float(feats["balance_score"])
        spikiness = float(feats["spikiness"])
        dominant_ratio = float(feats["dominant_ratio"])
        taurus_stellium_count = int(feats.get("taurus_stellium_count", 0))
        taurus_dominance_weight = float(feats.get("taurus_dominance_weight", 0.0))

        def ratio_signs(*signs: str) -> float:
            return sum(float(sr.get(sign, 0.0)) for sign in signs)

        def ratio_houses(*houses: int) -> float:
            return sum(float(hr.get(h, 0.0)) for h in houses)

        def p(body: str) -> float:
            return float(prom.get(body, 0.0))

        def link(a: str, b: str, kinds: Optional[Iterable[str]] = None, max_orb: Optional[float] = None) -> float:
            return self._aspect_strength(a, b, aspects, set(kinds) if kinds is not None else ALL_MAJOR_ASPECTS, max_orb=max_orb)

        # Shared signatures
        air_bird_signature = 0.45 * float(sr.get("Gemini", 0.0)) + 0.35 * float(sr.get("Aquarius", 0.0)) + 0.20 * float(sr.get("Libra", 0.0))
        rodent_sign_signature = (
            0.32 * float(sr.get("Virgo", 0.0))
            + 0.24 * float(sr.get("Capricorn", 0.0))
            + 0.22 * float(sr.get("Scorpio", 0.0))
            + 0.22 * float(sr.get("Taurus", 0.0))
        )
        serpent_sign_signature = 0.55 * float(sr.get("Scorpio", 0.0)) + 0.25 * float(sr.get("Pisces", 0.0)) + 0.20 * float(sr.get("Capricorn", 0.0))
        feline_sign_signature = 0.45 * float(sr.get("Leo", 0.0)) + 0.25 * float(sr.get("Libra", 0.0)) + 0.30 * float(sr.get("Scorpio", 0.0))
        dwarf_sign_signature = 0.52 * float(sr.get("Taurus", 0.0)) + 0.48 * float(sr.get("Capricorn", 0.0))
        canid_sign_signature = 0.34 * float(sr.get("Aries", 0.0)) + 0.22 * float(sr.get("Cancer", 0.0)) + 0.22 * float(sr.get("Scorpio", 0.0)) + 0.22 * float(sr.get("Capricorn", 0.0))
        elf_sign_signature = 0.34 * float(sr.get("Libra", 0.0)) + 0.28 * float(sr.get("Aquarius", 0.0)) + 0.20 * float(sr.get("Gemini", 0.0)) + 0.18 * float(sr.get("Pisces", 0.0))
        shape_sign_signature = 0.38 * float(sr.get("Gemini", 0.0)) + 0.32 * float(sr.get("Pisces", 0.0)) + 0.18 * float(sr.get("Libra", 0.0)) + 0.12 * float(sr.get("Aquarius", 0.0))

        # Aasimar
        cards["Aasimar"].add(0.95 * p("Sun"), "Sun prominence lifts Aasimar.")
        cards["Aasimar"].add(0.55 * p("Jupiter"), "Jupiter supports exalted scale.")
        cards["Aasimar"].add(0.35 * (er["Fire"] + er["Air"]), "Fire/Air tilt helps the celestial register.")
        cards["Aasimar"].add(0.25 * ratio_houses(9, 10, 11), "High-visibility houses reinforce it.")
        cards["Aasimar"].add(0.35 * link("Sun", "Jupiter", ALL_MAJOR_ASPECTS), "Sun-Jupiter contact tightens the fit.")
        cards["Aasimar"].add(-0.25 * max(p("Pluto"), link("Sun", "Pluto", HARD_ASPECTS)), "Heavy Plutonian weight muddies it.")

        # Birdfolk
        cards["Birdfolk"].add(1.45 * er["Air"], "Birdfolk is Air-first.")
        cards["Birdfolk"].add(1.15 * air_bird_signature, "Gemini/Aquarius/Libra avian signature.")
        cards["Birdfolk"].add(0.42 * p("Mercury"), "Mercury sharpens movement and avian alertness.")
        cards["Birdfolk"].add(0.28 * p("Uranus"), "Uranus adds altitude and oddness.")
        cards["Birdfolk"].add(0.22 * ratio_houses(3, 9, 11), "Movement, observation, and open-sky houses help.")

        # Canids
        cards["Canids"].add(0.75 * p("Moon"), "Moon gives bonding and pack signal.")
        cards["Canids"].add(0.65 * p("Mars"), "Mars gives pace and pursuit.")
        cards["Canids"].add(0.40 * p("Saturn"), "Saturn helps the working-dog end of the range.")
        cards["Canids"].add(0.45 * (er["Earth"] + er["Water"]), "Earth/Water grounds the family.")
        cards["Canids"].add(0.60 * canid_sign_signature, "Aries/Cancer/Scorpio/Capricorn supports the canid field.")
        cards["Canids"].add(0.25 * ratio_houses(4, 6, 8), "Domestic and survival houses reinforce it.")

        # Cosmids
        cards["Cosmids"].add(0.50 * (p("Uranus") + p("Neptune") + p("Pluto")), "Outer-planet emphasis helps Cosmids.")
        cards["Cosmids"].add(0.55 * (er["Air"] + er["Water"]), "Air/Water helps the unearthly register.")
        cards["Cosmids"].add(0.40 * ratio_houses(8, 11, 12), "Liminal houses reinforce it.")
        cards["Cosmids"].add(0.18 * self._clamp01(len(feats["tight_outer_to_identity"]) / 3.0), "Outer planets tied to identity intensify it.")

        # Cyborgs
        cards["Cyborgs"].add(0.72 * p("Mercury"), "Mercury handles throughput and interface.")
        cards["Cyborgs"].add(0.70 * p("Saturn"), "Saturn gives engineered structure.")
        cards["Cyborgs"].add(0.70 * p("Uranus"), "Uranus gives augmentation and novel hardware.")
        cards["Cyborgs"].add(0.28 * (er["Air"] + er["Earth"]), "Air/Earth supports the engineered body.")
        cards["Cyborgs"].add(0.32 * link("Mercury", "Uranus", ALL_MAJOR_ASPECTS), "Mercury-Uranus link supports synthetic cognition.")
        cards["Cyborgs"].add(0.28 * link("Mars", "Uranus", ALL_MAJOR_ASPECTS), "Mars-Uranus helps the weaponized end.")
        cards["Cyborgs"].add(0.18 * ratio_houses(3, 6, 10, 11), "Systems houses reinforce the fit.")

        # Cyclops
        cards["Cyclops"].add(0.72 * p("Sun"), "Cyclops needs solar centrality.")
        cards["Cyclops"].add(0.55 * p("Saturn"), "Saturn adds blunt singularity.")
        cards["Cyclops"].add(0.30 * p("Jupiter"), "Jupiter adds scale.")
        cards["Cyclops"].add(0.35 * (er["Fire"] + er["Earth"]), "Fire/Earth supports the giant-body feel.")
        cards["Cyclops"].add(0.22 * ratio_houses(1, 10), "Identity and visibility houses help.")

        # Dragons
        cards["Dragons"].add(0.65 * p("Jupiter"), "Jupiter gives scale and grandeur.")
        cards["Dragons"].add(0.45 * p("Sun"), "Solar force helps.")
        cards["Dragons"].add(0.42 * p("Pluto"), "Pluto adds hoard-level intensity.")
        cards["Dragons"].add(0.68 * (er["Fire"] + er["Earth"]), "Fire/Earth is the dragon spine.")
        cards["Dragons"].add(0.28 * mr["fixed"], "Fixed emphasis stabilizes dragonness.")
        cards["Dragons"].add(0.22 * link("Jupiter", "Sun", ALL_MAJOR_ASPECTS), "Sun-Jupiter bond helps.")

        # Dwarf
        cards["Dwarf"].add(1.10 * er["Earth"], "Earth anchors Dwarf.")
        cards["Dwarf"].add(0.85 * p("Saturn"), "Saturn gives craft, endurance, and load-bearing temperament.")
        cards["Dwarf"].add(0.65 * dwarf_sign_signature, "Taurus/Capricorn is the main sign lane.")
        cards["Dwarf"].add(0.25 * ratio_houses(2, 4, 6, 10), "Material and work houses reinforce it.")
        cards["Dwarf"].add(0.18 * tr["bestial"], "Bestial classical coding supports the earthy stock.")
        if taurus_stellium_count >= 3:
            stellium_bonus = 1.20 * taurus_dominance_weight
            cards["Dwarf"].add(
                stellium_bonus,
                f"Taurus stellium ({taurus_stellium_count} placements) boosts Dwarf by Taurus-dominance weight.",
            )

        # Elf
        cards["Elf"].add(0.88 * er["Air"], "Air is the main Elven atmosphere.")
        cards["Elf"].add(0.52 * p("Venus"), "Venus helps grace and finish.")
        cards["Elf"].add(0.42 * p("Mercury"), "Mercury helps finesse and speed.")
        cards["Elf"].add(0.62 * elf_sign_signature, "Libra/Aquarius/Gemini/Pisces is the main Elven sign lane.")
        cards["Elf"].add(0.25 * ratio_houses(3, 5, 9, 11), "Social and cultivated houses help.")
        cards["Elf"].add(0.26 * max(link("Venus", "Mercury", ALL_MAJOR_ASPECTS), link("Venus", "Jupiter", ALL_MAJOR_ASPECTS)), "Refined social/intellectual contacts reinforce Elf.")

        # Fey
        cards["Fey"].add(0.78 * p("Venus"), "Venus is the main Fey driver.")
        cards["Fey"].add(0.42 * p("Neptune"), "Neptune adds enchantment.")
        cards["Fey"].add(0.35 * p("Uranus"), "Uranus adds caprice and strangeness.")
        cards["Fey"].add(0.36 * (er["Air"] + er["Water"]), "Air/Water suits the Fey register.")
        cards["Fey"].add(0.28 * ratio_houses(5, 7, 11), "Pleasure and social houses reinforce it.")
        cards["Fey"].add(0.26 * max(link("Venus", "Neptune", ALL_MAJOR_ASPECTS), link("Venus", "Uranus", ALL_MAJOR_ASPECTS)), "Venus tied to Neptune/Uranus helps.")

        # Genasi
        cards["Genasi"].add(1.25 * self._clamp01((dominant_ratio - 0.31) / 0.24), "Genasi needs real elemental dominance.")
        cards["Genasi"].add(0.20 * max(p("Mars"), p("Moon"), p("Saturn"), p("Uranus")), "A strong elemental ruler helps.")
        cards["Genasi"].add(0.15 * ratio_houses(1, 4, 8), "Embodied element and strong atmospheres help.")

        # Spirits
        cards["Spirits"].add(1.05 * p("Neptune"), "Neptune is the main Spirits driver.")
        cards["Spirits"].add(0.45 * er["Water"], "Water helps diffusion and permeability.")
        cards["Spirits"].add(0.28 * er["Air"], "Air helps disembodiment.")
        cards["Spirits"].add(0.62 * ratio_houses(8, 12), "The 8th/12th axis reinforces it.")
        cards["Spirits"].add(0.22 * link("Moon", "Neptune", ALL_MAJOR_ASPECTS), "Moon-Neptune contact helps.")
        cards["Spirits"].add(-0.20 * er["Earth"], "Heavy Earth resists it.")

        # Gnome
        cards["Gnome"].add(0.85 * p("Mercury"), "Mercury is the main Gnome engine.")
        cards["Gnome"].add(0.45 * p("Uranus"), "Uranus adds invention.")
        cards["Gnome"].add(0.25 * p("Saturn"), "Saturn adds tinkering discipline.")
        cards["Gnome"].add(0.40 * (er["Earth"] + er["Air"]), "Air/Earth supports craft intelligence.")
        cards["Gnome"].add(0.24 * ratio_signs("Virgo", "Gemini", "Aquarius"), "Virgo/Gemini/Aquarius sharpens the fit.")

        # Half-orcs
        cards["Half-orcs"].add(0.82 * p("Mars"), "Mars is central here.")
        cards["Half-orcs"].add(0.48 * p("Saturn"), "Saturn adds grit.")
        cards["Half-orcs"].add(0.32 * p("Jupiter"), "Jupiter adds scale.")
        cards["Half-orcs"].add(0.56 * (er["Fire"] + er["Earth"]), "Fire/Earth supports the chassis.")
        cards["Half-orcs"].add(0.28 * balance, "Half-orcs tolerate more social integration than Orcs.")
        cards["Half-orcs"].add(0.22 * link("Mars", "Saturn", HARD_ASPECTS), "Mars-Saturn contact helps.")

        # Halfling
        cards["Halfling"].add(0.52 * p("Moon"), "Moon helps domestic scale.")
        cards["Halfling"].add(0.45 * p("Venus"), "Venus supports ease and sociability.")
        cards["Halfling"].add(0.38 * p("Mercury"), "Mercury supports nimble practicality.")
        cards["Halfling"].add(0.32 * (er["Earth"] + er["Air"]), "Earth/Air keeps it small, tidy, and quick.")
        cards["Halfling"].add(0.26 * ratio_houses(2, 4, 5, 6), "Home, food, habit, and local life reinforce it.")
        cards["Halfling"].add(0.20 * tr["humane"], "Humane sign coding helps.")

        # Human
        cards["Human"].add(1.10 * balance, "Humans score from broad balance.")
        cards["Human"].add(0.42 * (1.0 - spikiness), "Low symbolic extremity supports Human.")
        cards["Human"].add(0.20 * self._clamp01(1.0 - dominant_ratio), "Lack of elemental overcommitment helps.")

        # Tabaxi
        cards["Tabaxi"].add(0.68 * p("Mercury"), "Mercury gives feline quickness.")
        cards["Tabaxi"].add(0.55 * p("Venus"), "Venus adds social polish and allure.")
        cards["Tabaxi"].add(0.60 * (er["Fire"] + er["Air"]), "Fire/Air helps the agile cat lane.")
        cards["Tabaxi"].add(0.62 * feline_sign_signature, "Leo/Libra/Scorpio is the main feline sign lane.")
        cards["Tabaxi"].add(0.20 * ratio_houses(1, 5, 7), "Performance and social houses reinforce it.")

        # Lizardfolk
        cards["Lizardfolk (Reptilians)"].add(0.82 * p("Saturn"), "Saturn gives cold pragmatism.")
        cards["Lizardfolk (Reptilians)"].add(0.58 * p("Pluto"), "Pluto adds survival intensity.")
        cards["Lizardfolk (Reptilians)"].add(0.72 * er["Earth"], "Earth is the main element lane.")
        cards["Lizardfolk (Reptilians)"].add(0.32 * mr["fixed"], "Fixed emphasis = thick skin and arguably also sun basking - stationary for ectothermic homeostasis.")
        cards["Lizardfolk (Reptilians)"].add(0.26 * ratio_signs("Capricorn", "Scorpio", "Taurus"), "Capricorn/Scorpio/Taurus supports it.")
        cards["Lizardfolk (Reptilians)"].add(0.18 * ratio_houses(2, 6, 8, 10), "Survival and work houses reinforce it.")

        # Merfolk
        cards["Merfolk"].add(1.05 * er["Water"], "Water is the main Merfolk lane.")
        cards["Merfolk"].add(0.62 * p("Moon"), "Moon supports tide and body memory.")
        cards["Merfolk"].add(0.58 * p("Neptune"), "Neptune supports the sea register.")
        cards["Merfolk"].add(0.26 * p("Venus"), "Venus softens the aquatic presentation.")
        cards["Merfolk"].add(0.25 * ratio_houses(4, 8, 12), "Submerged houses reinforce it.")

        # Minotaur
        cards["Minotaur"].add(0.88 * p("Mars"), "Mars is primary.")
        cards["Minotaur"].add(0.52 * p("Jupiter"), "Jupiter adds size and momentum.")
        cards["Minotaur"].add(0.62 * (er["Fire"] + er["Earth"]), "Fire/Earth is the main chassis.")
        cards["Minotaur"].add(0.34 * mr["fixed"], "Fixed emphasis helps the head-down drive.")
        cards["Minotaur"].add(0.22 * ratio_signs("Taurus", "Aries", "Sagittarius"), "Taurus/Aries/Sagittarius supports it.")

        # Nymph
        cards["Nymph"].add(0.88 * p("Venus"), "Venus is central.")
        cards["Nymph"].add(0.50 * p("Moon"), "Moon adds organic softness.")
        cards["Nymph"].add(0.45 * (er["Water"] + er["Earth"]), "Water/Earth supports the nature-body lane.")
        cards["Nymph"].add(0.22 * link("Venus", "Moon", ALL_MAJOR_ASPECTS), "Venus-Moon contact helps.")
        cards["Nymph"].add(0.22 * ratio_houses(4, 5, 7, 12), "Natural and intimate houses reinforce it.")

        # Ogres
        cards["Ogres"].add(0.95 * p("Mars"), "Mars supplies force.")
        cards["Ogres"].add(0.82 * p("Saturn"), "Saturn supplies bulk and endurance.")
        cards["Ogres"].add(0.88 * er["Earth"], "Earth is the main Ogre lane.")
        cards["Ogres"].add(0.28 * mr["fixed"], "Fixed emphasis helps.")
        cards["Ogres"].add(-0.18 * er["Air"], "Heavy Air works against Ogre typing.")

        # Orcs
        cards["Orcs"].add(0.98 * p("Mars"), "Mars is central.")
        cards["Orcs"].add(0.54 * p("Pluto"), "Pluto intensifies it.")
        cards["Orcs"].add(0.35 * p("Jupiter"), "Jupiter adds scale and appetite.")
        cards["Orcs"].add(0.66 * (er["Fire"] + er["Earth"]), "Fire/Earth is the Orc backbone.")
        cards["Orcs"].add(0.28 * ratio_signs("Aries", "Scorpio", "Sagittarius"), "Aries/Scorpio/Sagittarius supports it.")
        cards["Orcs"].add(-0.14 * balance, "Too much balance pushes it away from Orc.")

        # Plasmoid
        cards["Plasmoid"].add(0.72 * p("Neptune"), "Neptune gives fluidity.")
        cards["Plasmoid"].add(0.62 * p("Uranus"), "Uranus gives weird embodiment.")
        cards["Plasmoid"].add(0.68 * (er["Water"] + er["Air"]), "Water/Air is the main lane.")
        cards["Plasmoid"].add(0.32 * mr["mutable"], "Mutable emphasis helps.")
        cards["Plasmoid"].add(0.22 * link("Neptune", "Uranus", ALL_MAJOR_ASPECTS), "Neptune-Uranus contact helps.")

        # Robots
        cards["Robots"].add(0.88 * p("Saturn"), "Saturn is the primary Robots signal.")
        cards["Robots"].add(0.72 * p("Mercury"), "Mercury adds instruction and cognition.")
        cards["Robots"].add(0.32 * p("Uranus"), "Uranus supports the construct edge.")
        cards["Robots"].add(0.52 * (er["Earth"] + er["Air"]), "Air/Earth supports constructed life.")
        cards["Robots"].add(0.28 * ratio_houses(3, 6, 10), "Procedure-heavy houses reinforce it.")
        cards["Robots"].add(-0.20 * max(p("Moon"), p("Neptune")), "High Moon/Neptune softens Robots.")

        # Rodentfolk
        cards["Rodentfolk"].add(0.82 * er["Earth"], "Rodentfolk needs an Earth floor.")
        cards["Rodentfolk"].add(0.62 * p("Mercury"), "Mercury adds quick sorting and vigilance.")
        cards["Rodentfolk"].add(0.68 * rodent_sign_signature, "Virgo/Capricorn/Scorpio/Taurus is the main rodent lane.")
        cards["Rodentfolk"].add(0.22 * er["Air"], "A little Air helps the twitchy end.")
        cards["Rodentfolk"].add(0.32 * ratio_houses(2, 6, 8, 12), "Storage, work, understructure, and hiding places reinforce it.")
        cards["Rodentfolk"].add(0.16 * link("Mercury", "Moon", ALL_MAJOR_ASPECTS), "Mercury-Moon contact helps reactive intelligence.")
        cards["Rodentfolk"].add(0.24 * p("Mercury") * self._clamp01((er["Air"] + er["Earth"] - 0.38) / 0.32), "Mercury + practical elemental blend boosts Rodentfolk even outside heavy Earth charts.")

        # Shapeshifter
        cards["Shapeshifter"].add(0.80 * mr["mutable"], "Mutable emphasis is central.")
        cards["Shapeshifter"].add(0.58 * shape_sign_signature, "Gemini/Pisces/Libra/Aquarius supports fluid identity.")
        cards["Shapeshifter"].add(0.42 * max(p("Mercury"), p("Neptune"), p("Uranus"), p("Pluto")), "Labile or uncanny planets help.")
        cards["Shapeshifter"].add(0.34 * ratio_houses(1, 8, 12), "Identity and liminal houses reinforce it.")
        cards["Shapeshifter"].add(0.24 * max(link("Mercury", "Neptune", ALL_MAJOR_ASPECTS), link("Mercury", "Pluto", ALL_MAJOR_ASPECTS), link("Moon", "Uranus", ALL_MAJOR_ASPECTS)), "Identity-fluid contacts help.")
        cards["Shapeshifter"].add(0.30 * self._clamp01((mr["mutable"] - 0.30) / 0.32), "Very high mutable concentration strongly favors Shapeshifter.")
        cards["Shapeshifter"].add(0.20 * self._clamp01((ratio_signs("Gemini", "Pisces") - 0.22) / 0.22), "Gemini/Pisces dominance materially increases Shapeshifter fit.")

        # Skeleton
        cards["Skeleton"].add(0.90 * p("Saturn"), "Saturn is primary.")
        cards["Skeleton"].add(0.66 * p("Mercury"), "Mercury supports the dry intellectual version.")
        cards["Skeleton"].add(0.34 * p("Pluto"), "Pluto supports undead persistence.")
        cards["Skeleton"].add(0.38 * (er["Earth"] + er["Air"]), "Dry Earth/Air supports it.")
        cards["Skeleton"].add(0.26 * ratio_houses(8, 10, 12), "Death and austerity houses help.")
        cards["Skeleton"].add(-0.25 * max(p("Venus"), p("Moon")), "Strong softness works against Skeleton.")

        # Stone People
        cards["Stone People (Golems)"].add(1.00 * er["Earth"], "Earth is primary.")
        cards["Stone People (Golems)"].add(0.82 * p("Saturn"), "Saturn gives mass and structure.")
        cards["Stone People (Golems)"].add(0.34 * max(p("Mars"), p("Pluto")), "A second hard planet helps the animated mass.")
        cards["Stone People (Golems)"].add(0.32 * mr["fixed"], "Fixed emphasis supports it.")
        cards["Stone People (Golems)"].add(0.28 * ratio_houses(2, 4, 10), "Material houses reinforce it.")

        # Succubi/Incubi
        cards["Succubi/Incubi"].add(0.92 * p("Venus"), "Venus is primary.")
        cards["Succubi/Incubi"].add(0.52 * max(p("Neptune"), p("Pluto")), "Neptune/Pluto adds seduction and danger.")
        cards["Succubi/Incubi"].add(0.38 * (er["Air"] + er["Water"]), "Air/Water suits the social-erotic field.")
        cards["Succubi/Incubi"].add(0.24 * ratio_houses(5, 7, 8), "Pleasure, relational, and taboo houses reinforce it.")
        cards["Succubi/Incubi"].add(0.30 * max(link("Venus", "Neptune", ALL_MAJOR_ASPECTS), link("Venus", "Pluto", ALL_MAJOR_ASPECTS)), "Venus tied to Neptune/Pluto helps.")

        # Tiefling
        cards["Tiefling"].add(0.74 * p("Mars"), "Mars drives the infernal edge.")
        cards["Tiefling"].add(0.72 * p("Pluto"), "Pluto deepens it.")
        cards["Tiefling"].add(0.40 * p("Saturn"), "Saturn hardens it.")
        cards["Tiefling"].add(0.42 * (er["Fire"] + er["Earth"]), "Fire/Earth supports the body plan.")
        cards["Tiefling"].add(0.22 * ratio_signs("Aries", "Scorpio", "Capricorn"), "Aries/Scorpio/Capricorn supports it.")
        cards["Tiefling"].add(0.26 * max(link("Mars", "Pluto", ALL_MAJOR_ASPECTS), link("Mars", "Saturn", ALL_MAJOR_ASPECTS), link("Pluto", "Sun", ALL_MAJOR_ASPECTS)), "Hard infernal contacts help.")

        # Triton
        cards["Triton"].add(0.86 * er["Water"], "Water is primary.")
        cards["Triton"].add(0.54 * p("Neptune"), "Neptune gives the marine register.")
        cards["Triton"].add(0.46 * p("Mars"), "Mars adds martial authority.")
        cards["Triton"].add(0.32 * p("Jupiter"), "Jupiter adds nobility and breadth.")
        cards["Triton"].add(0.24 * ratio_houses(9, 10, 11), "High public houses fit the sentinel role.")
        cards["Triton"].add(0.22 * self._clamp01((er["Water"] - 0.30) / 0.30), "Strong Water saturation pushes from generic aquatic into Triton.")
        cards["Triton"].add(0.16 * self._clamp01((max(p("Neptune"), p("Jupiter")) - 0.28) / 0.30), "Neptune/Jupiter authority supports Triton even when Mars is quieter.")

        # Vampire
        cards["Vampire"].add(0.86 * p("Venus"), "Venus is primary.")
        cards["Vampire"].add(0.82 * p("Pluto"), "Pluto is equally central.")
        cards["Vampire"].add(0.38 * p("Saturn"), "Saturn adds restraint and preservation.")
        cards["Vampire"].add(0.52 * ratio_signs("Scorpio", "Libra", "Capricorn"), "Scorpio/Libra/Capricorn supports the register.")
        cards["Vampire"].add(0.32 * ratio_houses(8, 12), "The 8th/12th axis supports it.")
        cards["Vampire"].add(0.32 * max(link("Venus", "Pluto", ALL_MAJOR_ASPECTS), link("Saturn", "Pluto", ALL_MAJOR_ASPECTS)), "Tight Venus-Pluto or Saturn-Pluto contact helps.")

        # Yuan-Ti
        cards["Yuan-Ti (Serpentine)"].add(0.86 * p("Pluto"), "Pluto is primary.")
        cards["Yuan-Ti (Serpentine)"].add(0.48 * p("Neptune"), "Neptune adds glamour and venomous blur.")
        cards["Yuan-Ti (Serpentine)"].add(0.44 * (er["Water"] + er["Earth"]), "Water/Earth suits the serpent body.")
        cards["Yuan-Ti (Serpentine)"].add(0.70 * serpent_sign_signature, "Scorpio/Pisces/Capricorn is the main serpent lane.")
        cards["Yuan-Ti (Serpentine)"].add(0.30 * ratio_houses(8, 12), "Liminal houses reinforce it.")
        cards["Yuan-Ti (Serpentine)"].add(0.24 * max(link("Pluto", "Neptune", ALL_MAJOR_ASPECTS), link("Venus", "Pluto", ALL_MAJOR_ASPECTS)), "Hypnotic contacts help.")

        # Mild floor so empty scorecards do not go negative or vanish completely.
        for family, card in cards.items():
            card.score = max(0.0, card.score)
            card.score *= float(SPECIES_DISTRIBUTION_CALIBRATION.get(family, 1.0))

        return cards

    # ----------------------------
    # Subtype picking
    # ----------------------------

    def _pick_subtype(
        self,
        family: str,
        positions: Mapping[str, Mapping[str, Any]],
        aspects: List[Mapping[str, Any]],
        feats: Mapping[str, Any],
    ) -> Tuple[str, List[str]]:
        er = feats["element_ratios"]
        sr = feats["sign_ratios"]
        hr = feats["house_ratios"]
        prom = feats["prominence"]
        evidence: List[str] = []

        def sign_of(body: str) -> Optional[str]:
            raw = positions.get(body, {}).get("sign")
            return str(raw) if raw else None

        def house_of(body: str) -> Optional[int]:
            value = positions.get(body, {}).get("house")
            return int(value) if value is not None else None

        def link(a: str, b: str, kinds: Optional[Iterable[str]] = None, max_orb: Optional[float] = None) -> float:
            return self._aspect_strength(a, b, aspects, set(kinds) if kinds is not None else ALL_MAJOR_ASPECTS, max_orb=max_orb)

        def strong_link(a: str, b: str, kinds: Optional[Iterable[str]] = None) -> bool:
            return link(a, b, kinds, self.tight_orb_deg) >= 0.30

        if family == "Aasimar":
            if max(link("Pluto", "Sun", HARD_ASPECTS), link("Pluto", "Moon", HARD_ASPECTS), link("Saturn", "Sun", HARD_ASPECTS)) >= 0.35:
                evidence.append("Pluto/Saturn cuts across the solar axis.")
                return "Fallen", evidence
            if max(link("Mars", "Sun", HARD_ASPECTS), link("Mars", "AS", HARD_ASPECTS), prom.get("Mars", 0.0)) >= 0.60:
                evidence.append("Mars pushes the celestial type toward punitive heat.")
                return "Scourge", evidence
            evidence.append("Solar-Jovian type stays upright and protective.")
            return "Protector", evidence

        if family == "Birdfolk":
            gem = float(sr.get("Gemini", 0.0))
            aqu = float(sr.get("Aquarius", 0.0))
            lib = float(sr.get("Libra", 0.0))
            if gem >= lib and gem >= aqu and (prom.get("Mercury", 0.0) >= 0.45 or strong_link("Mercury", "Uranus")):
                evidence.append("Gemini plus Mercury/Uranus lands in the corvid lane.")
                return "Kenku", evidence
            if aqu >= gem and aqu >= lib and (prom.get("Moon", 0.0) >= 0.40 or prom.get("Saturn", 0.0) >= 0.40 or house_of("Moon") in (8, 12)):
                evidence.append("Aquarius with nocturnal or observing markers lands in the owl lane.")
                return "Owlin", evidence
            if er["Air"] >= 0.33 and max(prom.get("Sun", 0.0), prom.get("Jupiter", 0.0), float(hr.get(9, 0.0)), float(hr.get(10, 0.0))) >= 0.34:
                evidence.append("Air plus altitude and daylight markers lands in the sky-hunter lane.")
                return "Aarakocra", evidence
            evidence.append("Avian family is clear, but without a narrow subtype lock.")
            return "Other (non-owl, non-kenku, non-aarakocra)", evidence

        if family == "Canids":
            if max(prom.get("Saturn", 0.0), float(hr.get(6, 0.0)), float(hr.get(10, 0.0))) >= 0.40 and prom.get("Moon", 0.0) >= 0.35:
                evidence.append("Duty-and-pack markers favor the shepherd lane.")
                return "Shepherd Dogs", evidence
            if max(float(sr.get("Scorpio", 0.0)), float(hr.get(8, 0.0)), float(hr.get(12, 0.0))) >= 0.20 and max(link("Mars", "Moon", HARD_ASPECTS), link("Mars", "AS", HARD_ASPECTS)) >= 0.25:
                evidence.append("Lunar survival plus Mars gives the wolf lane.")
                return "Wolfkin", evidence
            if max(link("Mars", "Uranus", HARD_ASPECTS), link("Mars", "Pluto", HARD_ASPECTS)) >= 0.28:
                evidence.append("Volatile Mars pushes it into the gnoll lane.")
                return "Gnolls", evidence
            evidence.append("The nose-and-trail version fits best.")
            return "Houndfolk", evidence

        if family == "Cosmids":
            if strong_link("Mercury", "Saturn") and strong_link("Mercury", "Uranus"):
                evidence.append("Mercury tied to Saturn and Uranus selects the time-engine subtype.")
                return "Chronomancers", evidence
            if max(link("Pluto", "Sun"), link("Pluto", "Moon"), link("Pluto", "AS")) >= 0.30 and max(link("Neptune", "Sun"), link("Neptune", "Moon"), link("Neptune", "AS")) >= 0.30:
                evidence.append("Pluto and Neptune both stain identity.")
                return "Abysswalkers", evidence
            if max(link("Uranus", "Sun"), link("Uranus", "Moon"), link("Uranus", "AS")) >= 0.30 and max(link("Neptune", "Sun"), link("Neptune", "Moon"), link("Neptune", "AS")) >= 0.25:
                evidence.append("Uranus plus Neptune on identity selects the starborn lane.")
                return "Starspawned", evidence
            if max(prom.get("Jupiter", 0.0), float(hr.get(10, 0.0)), float(hr.get(11, 0.0))) >= 0.40 and prom.get("Uranus", 0.0) >= 0.35:
                evidence.append("Jupiter-Uranus visibility selects the streaking subtype.")
                return "Cometkin", evidence
            evidence.append("Nodes or threshold logic nudge it toward eclipse coding.")
            return "Eclipsians", evidence

        if family == "Cyborgs":
            if prom.get("Mercury", 0.0) >= 0.45 and strong_link("Mercury", "Saturn") and strong_link("Mercury", "Uranus"):
                evidence.append("Mercury fused to Saturn and Uranus selects the machine-mind subtype.")
                return "Advanced AI", evidence
            if max(link("Mars", "Uranus"), link("Mars", "Saturn")) >= 0.30:
                evidence.append("Mars plugged into metal or voltage selects the combat chassis.")
                return "Combat-Oriented", evidence
            evidence.append("The augmentations are real but not total.")
            return "Light Augmented", evidence

        if family == "Dwarf":
            if max(float(hr.get(8, 0.0)), float(hr.get(12, 0.0)), link("Saturn", "Pluto")) >= 0.28:
                evidence.append("Underground and pressure markers select the deep subtype.")
                return "Duergar (Underdark)", evidence
            if strong_link("Mercury", "Saturn") and max(float(hr.get(2, 0.0)), float(hr.get(8, 0.0))) >= 0.18:
                evidence.append("Mercury-Saturn with security houses selects the warding subtype.")
                return "Mark of Warding (Eberron)", evidence
            if max(prom.get("Mars", 0.0), link("Mars", "Saturn")) >= 0.40:
                evidence.append("Mars plus Saturn pushes it toward the mountain lane.")
                return "Mountain", evidence
            evidence.append("The softer, steadier earthy branch fits best.")
            return "Hill", evidence

        if family == "Elf":
            if max(link("Venus", "Pluto"), float(sr.get("Scorpio", 0.0))) >= 0.26 and er["Water"] >= 0.22:
                evidence.append("Water and underworld polish select the dark branch.")
                return "Drow (Dark Elf)", evidence
            if max(link("Saturn", "Pluto"), float(hr.get(12, 0.0))) >= 0.28:
                evidence.append("Saturn-Pluto or 12th-house severity selects the dim austere branch.")
                return "Shadar-Kai", evidence
            if er["Water"] > er["Air"] and max(float(sr.get("Pisces", 0.0)), float(sr.get("Cancer", 0.0)), prom.get("Neptune", 0.0)) >= 0.22:
                evidence.append("Water-over-air selects the maritime branch.")
                return "Sea Elf", evidence
            if er["Air"] >= 0.28 and max(prom.get("Mercury", 0.0), prom.get("Jupiter", 0.0), float(hr.get(9, 0.0))) >= 0.34:
                evidence.append("Air with cultivated intellect selects the high branch.")
                return "High Elf", evidence
            if er["Earth"] >= 0.26 and max(float(sr.get("Virgo", 0.0)), float(sr.get("Taurus", 0.0)), float(hr.get(4, 0.0))) >= 0.18:
                evidence.append("Earth and woodland markers select the forest branch.")
                return "Wood Elf", evidence
            if max(prom.get("Uranus", 0.0), prom.get("Moon", 0.0)) >= 0.40 and feats["mode_ratios"].get("cardinal", 0.0) >= 0.18:
                evidence.append("Mood shift and bright angularity select the seasonal branch.")
                return "Eladrin (Seasonal)", evidence
            if er["Air"] >= 0.30 and max(prom.get("Sun", 0.0), prom.get("Jupiter", 0.0), float(hr.get(10, 0.0))) >= 0.40:
                evidence.append("Air and height select the winged branch.")
                return "Avariel", evidence
            evidence.append("The civilized airy branch remains the default.")
            return "High Elf", evidence

        if family == "Fey":
            if strong_link("Venus", "Saturn"):
                evidence.append("Venus disciplined by Saturn selects the martial-court subtype.")
                return "Hobgoblins", evidence
            if er["Air"] >= 0.30 and max(link("Venus", "Uranus"), link("Mercury", "Uranus")) >= 0.25:
                evidence.append("Tiny Air plus Uranian flicker selects the fairy lane.")
                return "Fairies", evidence
            if er["Earth"] >= 0.28 and max(prom.get("Jupiter", 0.0), link("Jupiter", "Saturn")) >= 0.30:
                evidence.append("Earth plus large benevolent Jupiter selects the firbolg lane.")
                return "Firbolgs", evidence
            if max(link("Venus", "Jupiter"), float(hr.get(5, 0.0))) >= 0.28:
                evidence.append("Pleasure and feast markers select the revel subtype.")
                return "Satyr/Fawn", evidence
            if max(link("Mars", "Jupiter"), prom.get("Mars", 0.0)) >= 0.35 and er["Earth"] >= 0.25:
                evidence.append("Big rough Earth and Mars-Jupiter selects the troll lane.")
                return "Trolls", evidence
            evidence.append("The neat trickster subtype fits the remaining Fey mix.")
            return "Leprechauns", evidence

        if family == "Genasi":
            dominant = feats["dominant_element"]
            if dominant == "Fire":
                if max(link("Uranus", "Mars"), link("Uranus", "Mercury")) >= 0.28:
                    evidence.append("Fire dominated by current and spark selects Electric.")
                    return "Electric", evidence
                return "Fire", evidence
            if dominant == "Air":
                if max(link("Uranus", "Mars"), link("Uranus", "Mercury")) >= 0.24:
                    evidence.append("Air crackles into Electric.")
                    return "Electric", evidence
                return "Air", evidence
            if dominant == "Earth":
                if er["Water"] >= 0.26:
                    evidence.append("Earth with enough Water becomes Mud.")
                    return "Mud", evidence
                return "Earth", evidence
            if dominant == "Water":
                if max(link("Saturn", "Moon"), link("Saturn", "Neptune")) >= 0.25:
                    evidence.append("Water held rigid by Saturn becomes Ice.")
                    return "Ice", evidence
                return "Water", evidence
            return dominant, evidence

        if family == "Spirits":
            if max(link("Uranus", "Neptune"), link("Uranus", "Moon")) >= 0.28:
                evidence.append("Erratic impact and displaced feeling selects the disruptive subtype.")
                return "Poltergeist", evidence
            if max(link("Saturn", "Neptune"), link("Saturn", "Moon"), float(hr.get(12, 0.0))) >= 0.28:
                evidence.append("Saturn on the porous axis selects the bleak subtype.")
                return "Wraith", evidence
            if max(link("Mars", "Neptune"), link("Mars", "Pluto")) >= 0.26:
                evidence.append("Ravenous or bodily corruption selects the ghoul lane.")
                return "Ghoul", evidence
            evidence.append("No single deforming tendency dominates.")
            return "Vagrant Spirit", evidence

        if family == "Halfling":
            if max(link("Mercury", "Neptune"), link("Moon", "Neptune")) >= 0.24:
                evidence.append("Quietly porous mind selects the inward subtype.")
                return "Ghostwise", evidence
            if er["Earth"] >= 0.28:
                evidence.append("Earthier and tougher selects Stout.")
                return "Stout", evidence
            if max(link("Venus", "Jupiter"), float(hr.get(4, 0.0)), float(hr.get(5, 0.0))) >= 0.28:
                evidence.append("Domestic welcome and abundance selects the hospitality mark.")
                return "Mark of Hospitality (Eberron)", evidence
            if max(link("Venus", "Moon"), float(hr.get(6, 0.0))) >= 0.28:
                evidence.append("Caretaking softness selects the healing mark.")
                return "Mark of Healing (Eberron)", evidence
            evidence.append("Quick social localism selects Lightfoot.")
            return "Lightfoot", evidence

        if family == "Human":
            if feats["spikiness"] >= 0.42:
                evidence.append("Still broadly human, but with a sharper skew.")
                return "Variant", evidence
            evidence.append("Balanced and low-spike chart lands in Standard.")
            return "Standard", evidence

        if family == "Tabaxi":
            if max(link("Venus", "Pluto"), float(sr.get("Scorpio", 0.0))) >= 0.28:
                evidence.append("Dark glamour selects Pantherkin.")
                return "Pantherkin", evidence
            if max(float(sr.get("Leo", 0.0)), prom.get("Mars", 0.0), prom.get("Sun", 0.0)) >= 0.30:
                evidence.append("Solar or martial striping selects Tigerfolk.")
                return "Tigerfolk", evidence
            evidence.append("Feline family is clear, but without a narrow cat branch.")
            return "Other (non-panther, non-tiger, non-lion, non-cat)", evidence

        if family == "Lizardfolk (Reptilians)":
            if max(link("Mars", "Jupiter"), prom.get("Jupiter", 0.0), float(hr.get(10, 0.0))) >= 0.32:
                evidence.append("Big prehistoric momentum selects Dinoboiz.")
                return "Dinoboiz", evidence
            evidence.append("Reptilian family is clear without the dinosaur tilt.")
            return "Other", evidence

        if family == "Robots":
            if strong_link("Mercury", "Saturn") and er["Earth"] >= er["Water"]:
                evidence.append("Mercury-Saturn with neat terrestrial engineering selects Autognome.")
                return "Autognome", evidence
            evidence.append("Construct logic wins without the gnomey finish.")
            return "Alternative Construct", evidence

        if family == "Rodentfolk":
            if er["Air"] > er["Earth"] and max(float(sr.get("Gemini", 0.0)), prom.get("Mercury", 0.0)) >= 0.24:
                evidence.append("The quicker, lighter arboreal lane selects Squirrelfolk.")
                return "Squirrelfolk", evidence
            if er["Earth"] >= er["Air"] and max(float(sr.get("Scorpio", 0.0)), float(sr.get("Capricorn", 0.0)), float(hr.get(6, 0.0)), float(hr.get(8, 0.0)), float(hr.get(12, 0.0))) >= 0.20:
                evidence.append("Earth plus understructure and survival selects Ratfolk.")
                return "Ratfolk", evidence
            evidence.append("Rodent family is clear, but without a narrow subtype lock.")
            return "Other (non-rat, non-squirrel)", evidence

        if family == "Shapeshifter":
            if max(float(sr.get("Gemini", 0.0)), float(sr.get("Pisces", 0.0)), link("Mercury", "Neptune")) >= 0.30:
                evidence.append("Socially fluid mutable coding selects Changelings.")
                return "Changelings", evidence
            if strong_link("Mercury", "Pluto") and max(prom.get("Mercury", 0.0), float(hr.get(1, 0.0))) >= 0.28:
                evidence.append("Mercury under Plutonian pressure selects Doppelgangers.")
                return "Doppelgangers", evidence
            if max(link("Mars", "Moon"), float(hr.get(1, 0.0)) + float(hr.get(8, 0.0)) + float(hr.get(12, 0.0))) >= 0.28:
                evidence.append("Body-instinct conflict selects Lycanthropes.")
                return "Lycanthropes", evidence
            evidence.append("Fluid identity remains social rather than predatory.")
            return "Changelings", evidence

        if family == "Skeleton":
            if strong_link("Mercury", "Pluto") and strong_link("Mercury", "Saturn"):
                evidence.append("Mercury bound to Saturn and Pluto selects the death-scholar.")
                return "Lich", evidence
            if strong_link("Mercury", "Saturn"):
                evidence.append("Dry learned Saturn-Mercury selects the caster subtype.")
                return "Skeletal Mage", evidence
            evidence.append("The simple martial frame remains.")
            return "Bone Warrior", evidence

        if family == "Stone People (Golems)":
            if er["Earth"] >= 0.34 and max(link("Uranus", "Venus"), link("Uranus", "Mercury")) >= 0.24:
                evidence.append("Stone plus luminous or precise Uranus selects Crystalborn.")
                return "Crystalborn", evidence
            if strong_link("Saturn", "Mars"):
                evidence.append("Saturn-Mars pressure selects the forged subtype.")
                return "Earth-Forged Golems", evidence
            evidence.append("Plain living mass remains the default.")
            return "Stoneborn", evidence

        if family == "Succubi/Incubi":
            if strong_link("Venus", "Neptune"):
                evidence.append("Venus drowned in Neptune selects Dreamweaver.")
                return "Dreamweaver Succubi", evidence
            evidence.append("The more direct infernal seduction subtype fits better.")
            return "Abyssal Succubi", evidence

        if family == "Tiefling":
            if max(link("Mars", "Uranus"), prom.get("Mars", 0.0), float(hr.get(1, 0.0))) >= 0.34:
                evidence.append("Unruly Mars pushes it feral.")
                return "Feral", evidence
            if max(link("Saturn", "Sun"), link("Saturn", "Pluto")) >= 0.28:
                evidence.append("Saturnine infernal authority selects the Asmodeus-ish lane.")
                return "Bloodlines (e.g., Asmodeus)", evidence
            if max(link("Mars", "Sun"), float(hr.get(10, 0.0))) >= 0.28:
                evidence.append("Martial visibility selects the Zariel-ish lane.")
                return "Bloodlines (e.g., Zariel)", evidence
            if max(link("Saturn", "Neptune"), float(sr.get("Capricorn", 0.0))) >= 0.24:
                evidence.append("Cold infernal reserve selects the Levistus-ish lane.")
                return "Bloodlines (e.g., Levistus)", evidence
            evidence.append("Infernal family is clear without a hard bloodline lock.")
            return "Standard", evidence

        if family == "Vampire":
            if strong_link("Venus", "Pluto") and strong_link("Saturn", "Pluto"):
                evidence.append("Venus-Pluto and Saturn-Pluto select the full aristocratic form.")
                return "True Vampire", evidence
            if strong_link("Saturn", "Pluto") and prom.get("Venus", 0.0) < 0.35:
                evidence.append("Dry Saturn-Pluto without strong Venus selects Nosferatu.")
                return "Nosferatu", evidence
            evidence.append("The partial blooded compromise remains.")
            return "Dhampir", evidence

        if family == "Yuan-Ti (Serpentine)":
            if strong_link("Pluto", "Neptune") and strong_link("Venus", "Pluto"):
                evidence.append("Smooth hypnotic venom selects Pureblood.")
                return "Pureblood", evidence
            evidence.append("The more visibly serpentine branch fits better.")
            return "Malison", evidence

        if family in {"Cyclops", "Dragons", "Merfolk", "Minotaur", "Nymph", "Ogres", "Orcs", "Plasmoid", "Triton", "Gnome"}:
            return "", evidence

        return "", evidence

    # ----------------------------
    # Evidence formatting
    # ----------------------------

    def _compact_evidence(self, family_reasons: List[str], subtype_evidence: List[str], feats: Mapping[str, Any], limit: int = 6) -> List[str]:
        out: List[str] = []
        er = feats["element_ratios"]
        out.append(
            "Elements: " + ", ".join(f"{k}={er[k]:.2f}" for k in ("Fire", "Earth", "Air", "Water")) + "."
        )
        for text in family_reasons:
            if text not in out:
                out.append(text)
        for text in subtype_evidence:
            if text not in out:
                out.append(text)
        return out[:limit]

    # ----------------------------
    # Utilities
    # ----------------------------

    def _aspect_strength(
        self,
        body_a: str,
        body_b: str,
        aspects: Sequence[Mapping[str, Any]],
        kinds: Iterable[str],
        *,
        max_orb: Optional[float] = None,
    ) -> float:
        allowed = {self._normalize_aspect_name(str(kind).lower()) for kind in kinds}
        limit = self.tight_orb_deg if max_orb is None else float(max_orb)
        best = 0.0

        for item in aspects:
            p1 = str(item.get("p1"))
            p2 = str(item.get("p2"))
            aspect = self._normalize_aspect_name(str(item.get("aspect", "")).lower())
            if aspect not in allowed:
                continue
            if not ((p1 == body_a and p2 == body_b) or (p1 == body_b and p2 == body_a)):
                continue

            orb = item.get("orb")
            if orb is None:
                continue
            orb_value = float(orb)
            if orb_value > limit:
                continue

            strength = 1.0 - (orb_value / max(1e-9, limit))
            if strength > best:
                best = strength

        return self._clamp01(best)

    @staticmethod
    def _normalize_aspect_name(name: str) -> str:
        lookup = {
            "opp": "opposition",
            "opposition": "opposition",
            "conj": "conjunction",
            "conjunction": "conjunction",
            "square": "square",
            "sq": "square",
            "trine": "trine",
            "tri": "trine",
            "sextile": "sextile",
            "sext": "sextile",
            "inconj": "quincunx",
            "quincunx": "quincunx",
            "quintile": "quintile",
            "biquintile": "biquintile",
            "semisquare": "semisquare",
            "semi-square": "semisquare",
            "sesquiquadrate": "sesquiquadrate",
            "semi-sextile": "semisextile",
            "semisextile": "semisextile",
        }
        return lookup.get(name.strip().lower(), name.strip().lower())

    @staticmethod
    def _angle_delta(a: float, b: float) -> float:
        delta = abs((a - b) % 360.0)
        return min(delta, 360.0 - delta)

    @staticmethod
    def _sign_for_longitude(lon: float) -> str:
        signs = (
            "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
            "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
        )
        return signs[int((lon % 360.0) // 30.0)]

    @staticmethod
    def _house_for_longitude(houses: Any, lon: float) -> Optional[int]:
        if not isinstance(houses, (list, tuple)) or len(houses) < 12:
            return None

        cusps = [float(c) % 360.0 for c in houses[:12]]
        probe = lon % 360.0
        for idx in range(12):
            start = cusps[idx]
            end = cusps[(idx + 1) % 12]
            if end <= start:
                end += 360.0
            test = probe
            if test < start:
                test += 360.0
            if start <= test < end:
                return idx + 1
        return None


def assign_top_three_species(chart: Any) -> List[Tuple[str, str, float]]:
    return SpeciesAssigner().assign(chart).top_three


def assign_top_three_species_with_evidence(chart: Any) -> List[Tuple[str, str, float, List[str]]]:
    assigner = SpeciesAssigner()
    positions = assigner._get_positions(chart)
    aspects = assigner._get_aspects(chart, positions)
    feats = assigner._extract_features(positions, aspects)
    scores = assigner._score_families(positions, aspects, feats)
    ranked = assigner._rank_families(scores)

    out: List[Tuple[str, str, float, List[str]]] = []
    for family, card in ranked[:3]:
        subtype, subtype_evidence = assigner._pick_subtype(family, positions, aspects, feats)
        evidence = assigner._compact_evidence(card.reasons, subtype_evidence, feats)
        out.append((family, subtype, round(card.score, 3), evidence))
    return out
