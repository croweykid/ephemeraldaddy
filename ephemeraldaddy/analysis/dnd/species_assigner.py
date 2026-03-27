# species_assigner.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
import math

# You already have these in interpretations.py; import if available.
try:
    from ephemeraldaddy.core.interpretations import MODES, PLANET_ORDER, SIGN_ELEMENTS, SIGN_KEYWORDS
except Exception:
    SIGN_ELEMENTS = {
        "Aries": "Fire", "Leo": "Fire", "Sagittarius": "Fire",
        "Taurus": "Earth", "Virgo": "Earth", "Capricorn": "Earth",
        "Gemini": "Air", "Libra": "Air", "Aquarius": "Air",
        "Cancer": "Water", "Scorpio": "Water", "Pisces": "Water",
    }
    PLANET_ORDER = [
        "Sun", "Moon", "Mercury", "Venus", "Mars",
        "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
        "Chiron", "Ceres", "Pallas", "Juno", "Vesta",
        "Rahu", "Ketu", "Lilith", "Part of Fortune",
        "AS", "MC", "DS", "IC",
    ]
    MODES = {
        "cardinal": {"Aries", "Cancer", "Libra", "Capricorn"},
        "mutable": {"Gemini", "Virgo", "Sagittarius", "Pisces"},
        "fixed": {"Taurus", "Leo", "Scorpio", "Aquarius"},
    }
    SIGN_KEYWORDS = {}

#mute signs: water signs
#humane signs: gem, vir, lib, aqu
#bestial signs: tau, cap
#feral signs: leo, sag
#quadrupedian, or four-footed signs: ari, tau, leo, cap
#vernal: ari, tau, gem
#aestival: can, leo, vir
#autumnal: lib, sco, sag
#hyemal: cap, aqu, pis
#bicorporeal/dualistic: gem, sag, pis
#fruitful: can, sco, pis
#barren: gem, leo, vir



SIGN_CLASSICAL_TRAITS = ("mute", "humane", "bestial", "feral", "quadrupedian", "bicorporeal")
SIGN_SEASONS = ("vernal", "aestival", "autumnal", "hyemal")
SIGN_FERTILITY = ("fruitful", "barren")

# ----------------------------
# Public API
# ----------------------------

SPECIES_FAMILIES = [
    "Aasimar",
    "Birdfolk",
    "Canids",
    "Cosmids",
    "Cyborgs",
    "Cyclops",
    "Dragons",
    "Dwarf",
    "Elf",
    "Fey",
    "Genasi",
    "Spirits",  # renamed family label
    "Gnome",
    "Half-orcs",
    "Halfling",
    "Human",
    "Tabaxi",
    "Lizardfolk (Reptilians)",
    "Merfolk",
    "Minotaur",
    "Nymph",
    "Ogres",
    "Orcs",
    "Plasmoid",
    "Robots",
    "Rodentfolk",
    "Shapeshifter",
    "Skeleton",
    "Stone People (Golems)",
    "Succubi/Incubi",
    "Tiefling",
    "Triton",
    "Vampire",
    "Yuan-Ti (Serpentine)",
]


@dataclass(frozen=True)
class SpeciesPick:
    family: str
    subtype: str
    score: float
    runner_up: Optional[Tuple[str, str, float]]  # (family, subtype, score)
    top_three: List[Tuple[str, str, float]]
    evidence: List[str]


class SpeciesAssigner:
    """
    Drop-in assigner.

    You can feed it either:
      A) a parsed chart mapping with at least:
         chart["positions"][planet] = {"sign": "Aquarius", "house": 5, "lon": 305.62}
         chart["aspects"] = [{"p1":"Sun","p2":"Moon","aspect":"square","orb":2.1}, ...]

      B) OR a minimal chart with just longitudes:
         chart["positions"][planet] = {"lon": 305.62, "sign":"Aquarius"}  # house optional
         (aspects will be derived)

    If your app's structure differs, write a tiny adapter that produces this shape.
    """

    def __init__(
        self,
        *,
        orb_tight_deg: float = 3.0,
        orb_default_deg: float = 6.0,
        angular_window_deg: float = 3.0,
        angular_conj_deg: float = 2.0,
    ) -> None:
        self.orb_tight_deg = orb_tight_deg
        self.orb_default_deg = orb_default_deg
        self.angular_window_deg = angular_window_deg
        self.angular_conj_deg = angular_conj_deg

    def assign(self, chart: Any) -> SpeciesPick:
        positions = self._get_positions(chart)
        aspects = self._get_aspects(chart, positions)

        feats = self._extract_features(positions, aspects)
        scores, reasons = self._score_families(positions, aspects, feats)

        # Select top families
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        (fam1, fam1_score), (fam2, fam2_score) = ranked[0], ranked[1]
        fam3, fam3_score = ranked[2]

        # Subtype selection for top families
        sub1, ev1 = self._pick_subtype(fam1, positions, aspects, feats)
        sub2, _ev2 = self._pick_subtype(fam2, positions, aspects, feats)
        sub3, _ev3 = self._pick_subtype(fam3, positions, aspects, feats)

        # Evidence: combine family reasons + subtype evidence, keep it short & specific
        evidence = self._compact_evidence(reasons.get(fam1, []), ev1, positions, aspects, feats)

        return SpeciesPick(
            family=fam1,
            subtype=sub1,
            score=round(fam1_score, 3),
            runner_up=(fam2, sub2, round(fam2_score, 3)),
            top_three=[
                (fam1, sub1, round(fam1_score, 3)),
                (fam2, sub2, round(fam2_score, 3)),
                (fam3, sub3, round(fam3_score, 3)),
            ],
            evidence=evidence,
        )

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
    def _clamp01(x: float) -> float:
        if x <= 0.0:
            return 0.0
        if x >= 1.0:
            return 1.0
        return float(x)

    @staticmethod
    def _sigmoid(x: float) -> float:
        return 1.0 / (1.0 + math.exp(-x))


    def _get_positions(self, chart: Any) -> Dict[str, Dict[str, Any]]:
        # Native app.Chart shape uses object attributes; keep this fast-path first.
        if hasattr(chart, "positions") and isinstance(getattr(chart, "positions"), Mapping):
            return self._from_native_chart(chart)

        pos = chart.get("positions") or chart.get("planets") or {}
        if not isinstance(pos, Mapping):
            raise TypeError("chart['positions'] (or chart['planets']) must be a mapping")

        out: Dict[str, Dict[str, Any]] = {}
        for k, v in pos.items():
            if not isinstance(v, Mapping):
                continue
            planet = str(k)
            sign = v.get("sign")
            house = v.get("house")
            lon = self._first_non_none(
                v.get("lon"),
                v.get("longitude"),
                v.get("ecl_lon"),
                v.get("deg"),
            )

            if lon is None and sign is None:
                continue

            # normalize lon
            if lon is not None:
                lon = float(lon) % 360.0

            out[planet] = {
                "sign": str(sign) if sign else None,
                "house": int(house) if house is not None else None,
                "lon": lon,
            }

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

            out[str(body)] = {
                "sign": str(sign) if sign else None,
                "house": int(house) if house is not None else None,
                "lon": lon,
            }

        return out

    def _get_aspects(
        self,
        chart: Any,
        positions: Mapping[str, Mapping[str, Any]],
    ) -> List[Dict[str, Any]]:
        raw = chart.get("aspects") if isinstance(chart, Mapping) else getattr(chart, "aspects", None)
        if isinstance(raw, list) and raw:
            # normalize
            out = []
            for a in raw:
                if not isinstance(a, Mapping):
                    continue
                p1 = str(a.get("p1") or a.get("planet1") or a.get("from") or "")
                p2 = str(a.get("p2") or a.get("planet2") or a.get("to") or "")
                asp = str(a.get("aspect") or a.get("type") or "")
                orb = a.get("orb")
                if orb is None and a.get("delta") is not None:
                    orb = abs(float(a.get("delta")))
                if not p1 or not p2 or not asp:
                    continue
                out.append({"p1": p1, "p2": p2, "aspect": asp.lower(), "orb": float(orb) if orb is not None else None})
            return out

        # Derive major aspects if missing and we have longitudes
        return self._derive_aspects(positions)

    def _derive_aspects(self, positions: Mapping[str, Mapping[str, Any]]) -> List[Dict[str, Any]]:
        majors = [
            ("conjunction", 0.0),
            ("sextile", 60.0),
            ("square", 90.0),
            ("trine", 120.0),
            ("opposition", 180.0),
        ]

        planets = [p for p in positions.keys() if positions[p].get("lon") is not None]
        out: List[Dict[str, Any]] = []

        for i in range(len(planets)):
            for j in range(i + 1, len(planets)):
                p1, p2 = planets[i], planets[j]
                d = self._angle_delta(float(positions[p1]["lon"]), float(positions[p2]["lon"]))
                best = None
                for name, target in majors:
                    orb = abs(d - target)
                    if orb <= self.orb_default_deg:
                        if best is None or orb < best[1]:
                            best = (name, orb)
                if best:
                    out.append({"p1": p1, "p2": p2, "aspect": best[0], "orb": float(best[1])})

        return out

    # ----------------------------
    # Feature extraction
    # ----------------------------

    def _extract_features(
        self,
        positions: Mapping[str, Mapping[str, Any]],
        aspects: List[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        # Basic element balance, weighted by importance
        weights = {
            "Sun": 3.0, "Moon": 3.0, "AS": 3.0,
            "Mercury": 1.5, "Venus": 1.5, "Mars": 1.5,
            "Jupiter": 1.25, "Saturn": 1.25,
            "Uranus": 1.0, "Neptune": 1.0, "Pluto": 1.0,
            "MC": 1.5, "DS": 1.0, "IC": 1.0,
        }

        elem = {"Fire": 0.0, "Earth": 0.0, "Air": 0.0, "Water": 0.0}
        modal = {"cardinal": 0.0, "mutable": 0.0, "fixed": 0.0}
        sign_trait_balance = {trait: 0.0 for trait in SIGN_CLASSICAL_TRAITS}
        season_balance = {season: 0.0 for season in SIGN_SEASONS}
        fertility_balance = {fertility: 0.0 for fertility in SIGN_FERTILITY}
        gemini_weight = 0.0
        neptune_sign_weight = 0.0
        total_weight = 0.0
        for p, info in positions.items():
            sign = info.get("sign")
            if not sign or sign not in SIGN_ELEMENTS:
                continue
            w = weights.get(p, 0.5)
            elem[SIGN_ELEMENTS[sign]] += w
            total_weight += w
            if sign == "Gemini":
                gemini_weight += w
            if p == "Neptune":
                neptune_sign_weight += w
            for mode, signs in MODES.items():
                if sign in signs:
                    modal[mode] += w
                    break

            sign_meta = SIGN_KEYWORDS.get(str(sign).title(), {}) if isinstance(SIGN_KEYWORDS, Mapping) else {}
            for trait in SIGN_CLASSICAL_TRAITS:
                if sign_meta.get(trait) is True:
                    sign_trait_balance[trait] += w
            season = sign_meta.get("season")
            if season in season_balance:
                season_balance[str(season)] += w
            fertility = sign_meta.get("fertility")
            if fertility in fertility_balance:
                fertility_balance[str(fertility)] += w

        # Angular emphasis (only if angles have longitudes)
        angular_hits: List[str] = []
        for angle in ("AS", "MC", "DS", "IC"):
            if angle not in positions or positions[angle].get("lon") is None:
                continue
            ang_lon = float(positions[angle]["lon"])
            for p, info in positions.items():
                if p in ("AS", "MC", "DS", "IC"):
                    continue
                if info.get("lon") is None:
                    continue
                d = self._angle_delta(ang_lon, float(info["lon"]))
                if d <= self.angular_window_deg:
                    angular_hits.append(p)

        # Tight outer-planet binds to luminaries/AS
        tight_outer = self._tight_outer_binds(aspects, ("Sun", "Moon", "AS"))

        # House emphasis (if houses exist)
        house_counts: Dict[int, float] = {}
        for p, info in positions.items():
            h = info.get("house")
            if h is None:
                continue
            w = weights.get(p, 0.5)
            house_counts[h] = house_counts.get(h, 0.0) + w

        def conj_to_angle_strength(p: str, angle: str, max_orb: Optional[float] = None) -> float:
            orb = self.angular_conj_deg if max_orb is None else max_orb
            if positions.get(p, {}).get("lon") is None or positions.get(angle, {}).get("lon") is None:
                return 0.0
            d = self._angle_delta(float(positions[p]["lon"]), float(positions[angle]["lon"]))
            return self._clamp01(1.0 - (d / max(1e-6, orb)))

        def tight_hard_strength(p: str, q: str, max_orb: float = 2.0) -> float:
            hard = {"conjunction", "square", "opposition"}
            best: Optional[float] = None
            for a in aspects:
                p1, p2 = str(a.get("p1")), str(a.get("p2"))
                asp = str(a.get("aspect", "")).lower()
                orb = float(a.get("orb", 999.0)) if a.get("orb") is not None else 999.0
                if asp not in hard or orb > max_orb:
                    continue
                if (p1 == p and p2 == q) or (p1 == q and p2 == p):
                    best = orb if best is None else min(best, orb)
            if best is None:
                return 0.0
            return self._clamp01(1.0 - (best / max(1e-6, max_orb)))

        def is_conj_within(p: str, q: str, orb: float = 4.0) -> bool:
            if positions.get(p, {}).get("lon") is None or positions.get(q, {}).get("lon") is None:
                return False
            return self._angle_delta(float(positions[p]["lon"]), float(positions[q]["lon"])) <= orb

        sun_conj = max(conj_to_angle_strength("Sun", "AS"), conj_to_angle_strength("Sun", "MC"))
        sun_house = positions.get("Sun", {}).get("house")
        sun_angular_house = 1.0 if sun_house in (1, 10) else 0.0
        sun_angularity = max(sun_conj, sun_angular_house)

        sun_cluster_penalty = 0.0
        if is_conj_within("Sun", "Mercury", 5.0):
            sun_cluster_penalty += 0.35
        if is_conj_within("Sun", "Venus", 5.0):
            sun_cluster_penalty += 0.25
        sun_cluster_penalty = self._clamp01(sun_cluster_penalty)

        personal = ("Sun", "Moon", "AS", "Mercury", "Venus", "Mars")
        w_sum = 0.0
        w_sun = 0.0
        for body in personal:
            if body not in positions:
                continue
            info = positions[body]
            if info.get("sign") is None and info.get("lon") is None:
                continue
            w = weights.get(body, 0.5)
            w_sum += w
            if body == "Sun":
                w_sun += w
        solar_dominance_ratio = w_sun / max(1e-6, w_sum)
        # Approximate calibrated percentile mapping: p50~0.20, p90~0.30, p95~0.34
        solar_dominance_signal = self._clamp01((solar_dominance_ratio - 0.20) / 0.14)

        glm_signs = {"Gemini", "Libra", "Pisces"}
        glm_weight = 0.0
        glm_total = 0.0
        taurus_weight = 0.0
        taurus_total = 0.0
        for body in personal:
            sign = positions.get(body, {}).get("sign")
            if not sign:
                continue
            w = weights.get(body, 0.5)
            glm_total += w
            if sign in glm_signs:
                glm_weight += w
            taurus_total += w
            if sign == "Taurus":
                taurus_weight += w
        glm_signature = glm_weight / max(1e-6, glm_total)
        taurus_signature = taurus_weight / max(1e-6, taurus_total)

        identity_flux = max(
            tight_hard_strength("Uranus", "Moon", max_orb=2.0),
            tight_hard_strength("Uranus", "AS", max_orb=2.0),
            tight_hard_strength("Neptune", "Moon", max_orb=2.0),
            tight_hard_strength("Neptune", "AS", max_orb=2.0),
        )

        mutable_air_water_ratio = self._clamp01((modal.get("mutable", 0.0) / max(1e-6, sum(modal.values())) + ((elem["Air"] + elem["Water"]) / max(1e-6, sum(elem.values())))) / 2.0)

        jupiter_visibility = max(
            conj_to_angle_strength("Jupiter", "AS"),
            conj_to_angle_strength("Jupiter", "MC"),
            tight_hard_strength("Jupiter", "Sun", max_orb=2.0),
            tight_hard_strength("Jupiter", "MC", max_orb=2.0),
        )

        sign_trait_ratio = {
            k: (v / max(1e-6, total_weight))
            for k, v in sign_trait_balance.items()
        }
        season_ratio = {
            k: (v / max(1e-6, total_weight))
            for k, v in season_balance.items()
        }
        fertility_ratio = {
            k: (v / max(1e-6, total_weight))
            for k, v in fertility_balance.items()
        }

        return {
            "element_balance": elem,
            "modal_balance": modal,
            "sign_trait_ratio": sign_trait_ratio,
            "season_ratio": season_ratio,
            "fertility_ratio": fertility_ratio,
            "gemini_ratio": gemini_weight / max(1e-6, total_weight),
            "neptune_sign_ratio": neptune_sign_weight / max(1e-6, total_weight),
            "angular_hits": angular_hits,
            "tight_outer_to_big3": tight_outer,  # list of (outer, target, aspect, orb)
            "house_counts": house_counts,
            "sun_angularity": sun_angularity,
            "solar_dominance_ratio": solar_dominance_ratio,
            "solar_dominance_signal": solar_dominance_signal,
            "sun_cluster_penalty": sun_cluster_penalty,
            "glm_signature": glm_signature,
            "taurus_signature": taurus_signature,
            "identity_flux": identity_flux,
            "mutable_air_water_ratio": mutable_air_water_ratio,
            "jupiter_visibility": jupiter_visibility,
        }

    def _tight_outer_binds(
        self,
        aspects: List[Mapping[str, Any]],
        targets: Tuple[str, ...],
    ) -> List[Tuple[str, str, str, float]]:
        outers = {"Uranus", "Neptune", "Pluto"}
        hard = {"square", "opposition", "conjunction"}
        out: List[Tuple[str, str, str, float]] = []
        for a in aspects:
            p1, p2 = str(a.get("p1")), str(a.get("p2"))
            asp = str(a.get("aspect", "")).lower()
            orb = float(a.get("orb", 999.0)) if a.get("orb") is not None else 999.0
            if orb > self.orb_tight_deg:
                continue
            if asp not in hard:
                continue
            if p1 in outers and p2 in targets:
                out.append((p1, p2, asp, orb))
            elif p2 in outers and p1 in targets:
                out.append((p2, p1, asp, orb))
        return out

    # ----------------------------
    # Scoring
    # ----------------------------

    def _score_families(
        self,
        positions: Mapping[str, Mapping[str, Any]],
        aspects: List[Mapping[str, Any]],
        feats: Mapping[str, Any],
    ) -> Tuple[Dict[str, float], Dict[str, List[str]]]:
        """
        Families are named to match your list as closely as possible,
        except one family label avoids a banned term: we use "Spirits" for the incorporeal bucket.
        """
        scores: Dict[str, float] = {k: 0.0 for k in self._families()}
        reasons: Dict[str, List[str]] = {k: [] for k in self._families()}

        elem = feats["element_balance"]
        modal = feats.get("modal_balance", {"cardinal": 0.0, "mutable": 0.0, "fixed": 0.0})
        fire, earth, air, water = elem["Fire"], elem["Earth"], elem["Air"], elem["Water"]
        top_elem = max(elem.items(), key=lambda kv: kv[1])[0]
        big3 = self._big3(positions)
        total_elem = max(1e-6, sum(elem.values()))
        total_modal = max(1e-6, sum(modal.values()))
        mutable_ratio = modal.get("mutable", 0.0) / total_modal
        sign_trait_ratio = feats.get("sign_trait_ratio", {}) or {}
        season_ratio = feats.get("season_ratio", {}) or {}
        fertility_ratio = feats.get("fertility_ratio", {}) or {}

        hard = {"square", "opposition", "conjunction"}

        # Helpers for prominences
        def has_planet(p: str) -> bool:
            return p in positions and (positions[p].get("sign") or positions[p].get("lon") is not None)

        def sign_of(p: str) -> Optional[str]:
            if p not in positions:
                return None
            raw = positions[p].get("sign")
            return str(raw) if raw else None

        def angular_count(p: str) -> int:
            return feats["angular_hits"].count(p)

        def tight_aspects_between(p: str, q: str, kinds: Iterable[str]) -> List[Mapping[str, Any]]:
            out = []
            for a in aspects:
                p1, p2 = str(a.get("p1")), str(a.get("p2"))
                asp = str(a.get("aspect", "")).lower()
                orb = float(a.get("orb", 999.0)) if a.get("orb") is not None else 999.0
                if orb > self.orb_tight_deg:
                    continue
                if asp not in kinds:
                    continue
                if (p1 == p and p2 == q) or (p1 == q and p2 == p):
                    out.append(a)
            return out

        def planet_power(p: str) -> float:
            """How chart-defining a planet is (0..~2); avoids samey results from mere presence."""
            if not has_planet(p):
                return 0.0

            info = positions.get(p, {})
            power = 0.20
            power += 0.30 * min(2, angular_count(p))

            if info.get("house") in (1, 10):
                power += 0.20

            for t in ("Sun", "Moon", "AS"):
                if t == p:
                    continue
                power += 0.20 * len(tight_aspects_between(p, t, hard))

            if p in ("Sun", "Moon", "AS"):
                power += 0.25

            return min(2.0, power)

        def is_prominent(p: str, threshold: float = 0.70) -> bool:
            return planet_power(p) >= threshold

        # Quick “dominance” boosts
        sun_boost = 1.0 + 0.45 * planet_power("Sun")
        moon_boost = 1.0 + 0.45 * planet_power("Moon")
        venus_boost = 1.0 + 0.45 * planet_power("Venus")
        mars_boost = 1.0 + 0.45 * planet_power("Mars")
        jup_boost = 1.0 + 0.45 * planet_power("Jupiter")
        sat_boost = 1.0 + 0.45 * planet_power("Saturn")
        ura_boost = 1.0 + 0.45 * planet_power("Uranus")
        nep_boost = 1.0 + 0.45 * planet_power("Neptune")
        plu_boost = 1.0 + 0.45 * planet_power("Pluto")

        # A) Aasimar family (gated + capped)
        sun_ang = float(feats.get("sun_angularity", 0.0))
        sun_dom = float(feats.get("solar_dominance_signal", 0.0))
        sun_cluster_pen = float(feats.get("sun_cluster_penalty", 0.0))
        jup_vis = float(feats.get("jupiter_visibility", 0.0))

        aasimar_gate_hits = 0
        aasimar_gate_hits += 1 if sun_ang >= 0.75 else 0
        aasimar_gate_hits += 1 if sun_dom >= 0.72 else 0
        aasimar_gate_hits += 1 if jup_vis >= 0.40 else 0

        aasimar_angular = 0.0
        aasimar_aspect = 0.0
        aasimar_element = 0.0
        aasimar_house = 0.0

        if aasimar_gate_hits >= 2:
            aasimar_angular += 0.55 * sun_ang
            aasimar_aspect += 0.45 * sun_dom + 0.35 * jup_vis
            aasimar_aspect -= 0.35 * sun_cluster_pen
            reasons["Aasimar"].append("Solar command is angular/rare + supported by Jupiter.")
        else:
            aasimar_angular += 0.20 * sun_ang
            aasimar_aspect += 0.18 * jup_vis + 0.12 * sun_dom
            reasons["Aasimar"].append("Solar signature present but not extreme enough for primary typing.")

        aasimar_angular = self._clamp01(aasimar_angular / 0.60) * 0.60
        aasimar_aspect = self._clamp01(aasimar_aspect / 0.60) * 0.60
        aasimar_element = self._clamp01(aasimar_element / 0.40) * 0.40
        aasimar_house = self._clamp01(aasimar_house / 0.30) * 0.30

        aasimar_score = 0.10 + aasimar_angular + aasimar_aspect + aasimar_element + aasimar_house
        if aasimar_gate_hits >= 2:
            aasimar_score += 0.85 + 0.15 * min(3, aasimar_gate_hits)
        else:
            aasimar_score = min(aasimar_score, 0.50)

        scores["Aasimar"] += aasimar_score

        # B) Tiefling family
        # Mars/Pluto hard ties to big3 increase “infernal” style
        hard = {"square", "opposition", "conjunction"}
        if is_prominent("Mars"):
            scores["Tiefling"] += 0.9 * mars_boost
            reasons["Tiefling"].append("Mars emphasized (edge/drive).")
        if is_prominent("Pluto"):
            scores["Tiefling"] += 0.9 * plu_boost
            reasons["Tiefling"].append("Pluto emphasized (intensity/compulsion).")
        for t in ("Sun", "Moon", "AS"):
            if tight_aspects_between("Pluto", t, hard):
                scores["Tiefling"] += 1.0 * plu_boost
                reasons["Tiefling"].append(f"Pluto tightly bound to {t}.")
            if tight_aspects_between("Mars", t, hard):
                scores["Tiefling"] += 0.75 * mars_boost
                reasons["Tiefling"].append(f"Mars tightly bound to {t}.")
        if not is_prominent("Mars") and not is_prominent("Pluto"):
            scores["Tiefling"] -= 1.2

        # C) Fey family
        if is_prominent("Venus"):
            scores["Fey"] += 2.0 * venus_boost
            reasons["Fey"].append("Venus emphasized (aesthetic/social magnetism).")
        # Venus with Uranus/Neptune for “enchanted / weird”
        if tight_aspects_between("Venus", "Uranus", {"conjunction", "square", "opposition"}):
            scores["Fey"] += 1.0 * ura_boost
            reasons["Fey"].append("Venus tightly tied to Uranus (unconventional charm).")
        if tight_aspects_between("Venus", "Neptune", {"conjunction", "square", "opposition"}):
            scores["Fey"] += 1.0 * nep_boost
            reasons["Fey"].append("Venus tightly tied to Neptune (dreamy allure).")

        # D) Genasi family (elemental)
        # Score increases when one element dominates and the matching rulers are present.
        dom_ratio = (max(elem.values()) / max(1e-6, sum(elem.values())))
        scores["Genasi"] += 3.0 * max(0.0, dom_ratio - 0.28)  # needs real dominance
        reasons["Genasi"].append(f"Element dominance ratio ≈ {dom_ratio:.2f} (higher = more elemental-typed).")

        # E) Nymph family (element + Venus/Moon)
        scores["Nymph"] += (0.9 * venus_boost if is_prominent("Venus") else 0.0)
        scores["Nymph"] += (0.7 * moon_boost if is_prominent("Moon") else 0.0)
        # prefer clear element dominance too
        scores["Nymph"] += 1.2 * max(0.0, dom_ratio - 0.30)
        if tight_aspects_between("Venus", "Moon", {"conjunction", "trine", "sextile"}):
            scores["Nymph"] += 0.55
        scores["Nymph"] += 0.22 * self._clamp01((water - fire) / max(1e-6, sum(elem.values())))

        # F) Constructs / Cyborgs / Robots families (systems)
        tech_signals = 0
        # Saturn + Uranus + Mercury ties
        if is_prominent("Saturn"):
            tech_signals += 1
            scores["Cyborgs"] += 0.75 * sat_boost
            scores["Robots"] += 0.7 * sat_boost
            reasons["Cyborgs"].append("Saturn emphasized (systems/constraints).")
            reasons["Robots"].append("Saturn emphasized (structure/rigor).")
        if is_prominent("Uranus"):
            tech_signals += 1
            scores["Cyborgs"] += 0.8 * ura_boost
            scores["Robots"] += 0.75 * ura_boost
            reasons["Cyborgs"].append("Uranus emphasized (tech/novelty).")
            reasons["Robots"].append("Uranus emphasized (automation/novelty).")
        if is_prominent("Mercury"):
            tech_signals += 1
            scores["Cyborgs"] += 0.7
            scores["Robots"] += 0.7
            reasons["Cyborgs"].append("Mercury emphasized (cognition/throughput).")
            reasons["Robots"].append("Mercury emphasized (cognition/throughput).")
        if tight_aspects_between("Mercury", "Uranus", hard):
            tech_signals += 1
            scores["Cyborgs"] += 0.8 * ura_boost
            scores["Robots"] += 0.7 * ura_boost
            reasons["Cyborgs"].append("Mercury tightly tied to Uranus (nonstandard thinking).")
        if tight_aspects_between("Mercury", "Saturn", hard):
            tech_signals += 1
            scores["Cyborgs"] += 0.7 * sat_boost
            scores["Robots"] += 0.7 * sat_boost
            reasons["Robots"].append("Mercury tightly tied to Saturn (precise, rule-bound mind).")

        # Avoid over-typing on single generic signatures.
        if tech_signals <= 1:
            scores["Cyborgs"] -= 0.45
            scores["Robots"] -= 0.45
        elif tech_signals >= 3:
            scores["Cyborgs"] += 0.25
            scores["Robots"] += 0.25

        # G) Cosmids family (outer planets run the show)
        tight_outer = feats["tight_outer_to_big3"]
        if tight_outer:
            scores["Cosmids"] += 0.35 + 0.35 * len(tight_outer)
            if len(tight_outer) == 1:
                scores["Cosmids"] -= 0.4
            reasons["Cosmids"].append(f"Tight outer-planet binds to big-3: {len(tight_outer)}.")
        # add if air/water lean + outer planets
        scores["Cosmids"] += 0.35 * (air + water) / max(1e-6, fire + earth + air + water)

        bestial_ratio = float(sign_trait_ratio.get("bestial", 0.0))
        feral_ratio = float(sign_trait_ratio.get("feral", 0.0))
        quadrupedian_ratio = float(sign_trait_ratio.get("quadrupedian", 0.0))
        humane_ratio = float(sign_trait_ratio.get("humane", 0.0))
        bicorporeal_ratio = float(sign_trait_ratio.get("bicorporeal", 0.0))
        fruitful_ratio = float(fertility_ratio.get("fruitful", 0.0))
        mute_ratio = float(sign_trait_ratio.get("mute", 0.0))

        # H) Beastfolk buckets (Canids / Tabaxi / Rodentfolk / Yuan-Ti / Lizardfolk)
        # Canids: Moon+Mars+Saturn blend; pack/service houses if available
        if is_prominent("Moon") and is_prominent("Mars"):
            scores["Canids"] += 1.1 * moon_boost + 0.9 * mars_boost
            reasons["Canids"].append("Moon+Mars present (bond + drive).")
        if is_prominent("Saturn"):
            scores["Canids"] += 0.5 * sat_boost
        scores["Canids"] += 0.35 * self._clamp01((quadrupedian_ratio - 0.18) / 0.30)

        # Tabaxi: Mercury/Venus + fire/air
        if is_prominent("Mercury") and is_prominent("Venus"):
            scores["Tabaxi"] += 1.0 + 0.6 * (venus_boost - 1.0)
            reasons["Tabaxi"].append("Mercury+Venus present (quick social + aesthetic).")
        scores["Tabaxi"] += 0.7 * (fire + air) / total_elem
        scores["Tabaxi"] += 0.25 * self._clamp01((feral_ratio - 0.12) / 0.30)

        # Rodentfolk: Mercury dominance + air/earth; complexity
        if is_prominent("Mercury"):
            scores["Rodentfolk"] += 0.62
            reasons["Rodentfolk"].append("Mercury emphasized (resourceful cognition).")
        if sign_of("Mercury") in ("Gemini", "Virgo"):
            scores["Rodentfolk"] += 0.60
        if sign_of("Sun") in ("Gemini", "Virgo"):
            scores["Rodentfolk"] += 0.25
        scores["Rodentfolk"] += 0.28 * (air + earth) / max(1e-6, sum(elem.values()))
        scores["Rodentfolk"] += 0.18 * self._clamp01((humane_ratio + bicorporeal_ratio - 0.25) / 0.45)
        if sign_of("Mercury") in ("Gemini", "Virgo"):
            scores["Rodentfolk"] += 0.45
        if sign_of("Sun") in ("Gemini", "Virgo") or sign_of("AS") in ("Gemini", "Virgo"):
            scores["Rodentfolk"] += 0.25
        if is_prominent("Mercury") and sign_of("Mercury") in ("Gemini", "Virgo") and ((air + earth) / max(1e-6, sum(elem.values()))) >= 0.45:
            scores["Rodentfolk"] += 0.95
            reasons["Rodentfolk"].append("Mercury domicile/exaltation style with air-earth blend boosts rodent coding.")
        scores["Rodentfolk"] += 0.03 * len(aspects) / 10.0  # more aspect-web -> busier mind
        if not tight_aspects_between("Mercury", "Moon", hard) and not tight_aspects_between("Mercury", "AS", hard):
            scores["Rodentfolk"] -= 0.35

        # Lizardfolk: Saturn+Pluto + earth/fixed survival vibe
        if is_prominent("Saturn") and is_prominent("Pluto"):
            scores["Lizardfolk (Reptilians)"] += 1.4 * sat_boost + 1.2 * plu_boost
            reasons["Lizardfolk (Reptilians)"].append("Saturn+Pluto blend (cold pragmatism).")
        scores["Lizardfolk (Reptilians)"] += 0.7 * earth / max(1e-6, sum(elem.values()))
        scores["Lizardfolk (Reptilians)"] += 0.25 * self._clamp01((bestial_ratio - 0.12) / 0.28)

        # Yuan-Ti: Pluto/Neptune + survival + charisma (Venus optional)
        if is_prominent("Pluto") and is_prominent("Neptune"):
            scores["Yuan-Ti (Serpentine)"] += 1.6 * plu_boost + 1.2 * nep_boost
            reasons["Yuan-Ti (Serpentine)"].append("Pluto+Neptune blend (hypnotic depth).")
        elif is_prominent("Pluto"):
            scores["Yuan-Ti (Serpentine)"] += 0.5 * plu_boost
        if is_prominent("Venus"):
            scores["Yuan-Ti (Serpentine)"] += 0.25 * venus_boost
        scores["Yuan-Ti (Serpentine)"] += 0.35 * self._clamp01((mute_ratio - 0.10) / 0.25)
        if tight_aspects_between("Pluto", "Neptune", hard):
            scores["Yuan-Ti (Serpentine)"] += 0.9
        scorpio_personal = sum(1 for p in ("Sun", "Moon", "Mercury", "Venus", "AS") if sign_of(p) == "Scorpio")
        if scorpio_personal >= 2:
            scores["Yuan-Ti (Serpentine)"] += 0.18 * scorpio_personal

        # I) Mortals: Elf/Dwarf/Halfling/Human/Half-orcs/Orcs etc (baseline)
        # Human gets points for balance (low dominance ratio)
        scores["Human"] += 2.0 * max(0.0, 0.33 - abs(dom_ratio - 0.33))
        reasons["Human"].append("Element balance favors adaptability (not strongly dominated).")

        # Elf: air + Venus/Mercury refinement
        scores["Elf"] += 1.2 * (air / max(1e-6, sum(elem.values())))
        if is_prominent("Venus"):
            scores["Elf"] += 0.7 * venus_boost
        if is_prominent("Mercury"):
            scores["Elf"] += 0.6
        scores["Elf"] += 0.24 * self._clamp01((humane_ratio - 0.20) / 0.35)
        reasons["Elf"].append("Air emphasis + (Venus/Mercury) tends elf-ish.")

        # Dwarf: earth + Saturn
        scores["Dwarf"] += 1.0 * (earth / max(1e-6, sum(elem.values())))
        if is_prominent("Saturn"):
            scores["Dwarf"] += 0.7 * sat_boost
        taurus_signature = float(feats.get("taurus_signature", 0.0))
        if taurus_signature >= 0.25:
            scores["Dwarf"] += 0.35 * self._clamp01((taurus_signature - 0.25) / 0.45)
            reasons["Dwarf"].append("Taurus dominance strengthens dwarf coding (endurance/craft/material grounding).")
        hyemal_ratio = float(season_ratio.get("hyemal", 0.0))
        if bestial_ratio >= 0.16:
            scores["Dwarf"] += 0.18 * self._clamp01((bestial_ratio - 0.16) / 0.24)
            reasons["Dwarf"].append("Bestial sign coding (Taurus/Capricorn) reinforces dwarf survival archetype.")
        if quadrupedian_ratio >= 0.20:
            scores["Dwarf"] += 0.10 * self._clamp01((quadrupedian_ratio - 0.20) / 0.30)
        if hyemal_ratio >= 0.12:
            scores["Dwarf"] += 0.08 * self._clamp01((hyemal_ratio - 0.12) / 0.20)
        reasons["Dwarf"].append("Earth+Saturn tends dwarf-ish (structure/craft).")

        # Halfling: humane+fixed feel (with social nimbleness channels)
        scores["Halfling"] += 0.8 * ((air + water) / max(1e-6, sum(elem.values())))
        if is_prominent("Venus"):
            scores["Halfling"] += 0.5 * venus_boost
        if is_prominent("Mercury"):
            scores["Halfling"] += 0.5
        fixed_ratio = modal.get("fixed", 0.0) / total_modal
        scores["Halfling"] += 0.20 * self._clamp01((fixed_ratio - 0.30) / 0.35)
        scores["Halfling"] += 0.18 * self._clamp01((humane_ratio - 0.22) / 0.30)
        if sign_of("Moon") in ("Cancer", "Virgo") or sign_of("Venus") in ("Taurus", "Libra"):
            scores["Halfling"] += 0.25
        reasons["Halfling"].append("Humane+fixed + social planets tends halfling-ish.")

        # Half-orcs / Orcs: Mars + Saturn hard + fire/earth
        hard_ms = tight_aspects_between("Mars", "Saturn", hard)
        if hard_ms and (is_prominent("Mars") or is_prominent("Saturn")):
            scores["Half-orcs"] += 0.8 * mars_boost + 0.6 * sat_boost
            scores["Orcs"] += 0.7 * mars_boost + 0.5 * sat_boost
            reasons["Half-orcs"].append("Mars tightly tied to Saturn (hard-edged grit).")
            reasons["Orcs"].append("Mars tightly tied to Saturn (hard-edged grit).")
        scores["Half-orcs"] += 0.8 * (fire + earth) / max(1e-6, sum(elem.values()))
        if is_prominent("Mars"):
            scores["Half-orcs"] += 0.5 * mars_boost
        scores["Orcs"] += 0.72 * (fire + earth) / max(1e-6, sum(elem.values()))
        if is_prominent("Mars"):
            scores["Orcs"] += 0.35 * mars_boost
        if sign_of("Mars") in ("Aries", "Scorpio", "Capricorn"):
            scores["Orcs"] += 0.35
        if is_prominent("Mars") and is_prominent("Pluto"):
            scores["Orcs"] += 0.7 * mars_boost + 0.6 * plu_boost

        # J) Undead-style families (Vampire / Skeleton / Spirits)
        # Note: family label "Spirits" replaces a banned term.
        # Vampire: Venus + Pluto (+ Saturn restraint)
        if is_prominent("Venus") and is_prominent("Pluto"):
            scores["Vampire"] += 1.7 * venus_boost + 1.7 * plu_boost
            reasons["Vampire"].append("Venus+Pluto blend (desire + power).")
            if is_prominent("Saturn"):
                scores["Vampire"] += 0.6 * sat_boost
        elif is_prominent("Venus"):
            scores["Vampire"] += 0.45 * venus_boost
        elif is_prominent("Pluto"):
            scores["Vampire"] += 0.45 * plu_boost
        if tight_aspects_between("Venus", "Pluto", hard):
            scores["Vampire"] += 1.0
        if tight_aspects_between("Saturn", "Pluto", hard):
            scores["Vampire"] += 0.7
        scorpio_core = sum(1 for p in ("Sun", "Moon", "Venus", "Pluto", "AS") if sign_of(p) == "Scorpio")
        if scorpio_core >= 2:
            scores["Vampire"] += 0.25 * scorpio_core

        # Skeleton: Saturn + Mercury, low Venus/Moon emphasis (approximated)
        if is_prominent("Saturn") and is_prominent("Mercury"):
            scores["Skeleton"] += 1.6 * sat_boost + 1.2
            reasons["Skeleton"].append("Saturn+Mercury blend (austere intellect).")
        if is_prominent("Venus"):
            scores["Skeleton"] -= 0.3 * (venus_boost)  # polish reduces skeleton-typing
        if is_prominent("Moon"):
            scores["Skeleton"] -= 0.2 * (moon_boost)

        # Spirits: Neptune prominence + big 12th/8th if houses exist
        if is_prominent("Neptune"):
            scores["Spirits"] += 1.8 * nep_boost
            reasons["Spirits"].append("Neptune emphasized (porous boundaries).")
        # house weighting
        hc = feats["house_counts"]
        if hc:
            scores["Spirits"] += 0.9 * (hc.get(12, 0.0) + hc.get(8, 0.0)) / max(1e-6, sum(hc.values()))
            scores["Vampire"] += 0.7 * (hc.get(8, 0.0)) / max(1e-6, sum(hc.values()))

        # K) Birdfolk: air + Mercury + (Moon for owlin) + Uranus for kenku-ish weird
        scores["Birdfolk"] += 1.0 * (air / max(1e-6, sum(elem.values())))
        if is_prominent("Mercury"):
            scores["Birdfolk"] += 0.9
        if tight_aspects_between("Mercury", "Uranus", hard):
            scores["Birdfolk"] += 0.5 * ura_boost

        # L) Shapeshifter: Gemini/Libra/Pisces-coded + gated + capped
        glm = float(feats.get("glm_signature", 0.0))
        flux = float(feats.get("identity_flux", 0.0))
        mutable_air_water_ratio = float(feats.get("mutable_air_water_ratio", 0.0))
        glm_trait_support = self._clamp01((bicorporeal_ratio + humane_ratio + fruitful_ratio) / 0.90)

        shapeshifter_gate_hits = 0
        shapeshifter_gate_hits += 1 if glm >= 0.55 else 0
        shapeshifter_gate_hits += 1 if flux >= 0.50 else 0
        shapeshifter_gate_hits += 1 if mutable_air_water_ratio >= 0.62 else 0

        sh_angular = 0.0
        sh_aspect = 0.0
        sh_element = 0.0
        sh_house = 0.0

        if shapeshifter_gate_hits >= 2:
            sh_element += 0.55 * glm + 0.30 * mutable_air_water_ratio + 0.18 * glm_trait_support
            sh_aspect += 0.45 * flux
            reasons["Shapeshifter"].append("Gemini/Libra/Pisces signature + identity-flux markers.")
            if glm_trait_support >= 0.45:
                reasons["Shapeshifter"].append("Bicorporeal/humane/fruitful sign tags reinforce identity-morph coding.")
        else:
            sh_element += 0.20 * glm + 0.15 * mutable_air_water_ratio + 0.08 * glm_trait_support
            reasons["Shapeshifter"].append("Some flexibility markers, but not enough for primary typing.")

        sh_angular = self._clamp01(sh_angular / 0.60) * 0.60
        sh_aspect = self._clamp01(sh_aspect / 0.60) * 0.60
        sh_element = self._clamp01(sh_element / 0.40) * 0.40
        sh_house = self._clamp01(sh_house / 0.30) * 0.30

        shapeshifter_score = 0.08 + sh_angular + sh_aspect + sh_element + sh_house
        if shapeshifter_gate_hits < 2:
            shapeshifter_score = min(shapeshifter_score, 0.32)

        scores["Shapeshifter"] += shapeshifter_score

         # M) Additional families so every family has a path to rank #1.
        # Keep these moderate to avoid flattening all distinctions.
        # Cosmic/dragonic
        if is_prominent("Jupiter") and is_prominent("Pluto"):
            scores["Dragons"] += 1.4 * jup_boost + 1.0 * plu_boost
            reasons["Dragons"].append("Jupiter+Pluto prominence (mythic force).")
        elif is_prominent("Jupiter"):
            scores["Dragons"] += 0.55 * jup_boost
        elif is_prominent("Pluto"):
            scores["Dragons"] += 0.35 * plu_boost
        if tight_aspects_between("Jupiter", "Sun", hard) or tight_aspects_between("Jupiter", "Mars", hard):
            scores["Dragons"] += 0.7 * jup_boost
        scores["Dragons"] += 0.75 * (fire + earth) / max(1e-6, sum(elem.values()))

        # Smaller earth-intellect archetype
        if is_prominent("Mercury"):
            scores["Gnome"] += 0.9
        if is_prominent("Saturn"):
            scores["Gnome"] += 0.6 * sat_boost
        scores["Gnome"] += 0.7 * (earth + air) / max(1e-6, sum(elem.values()))

        # Brute-force archetypes
        if is_prominent("Mars") and is_prominent("Jupiter"):
            scores["Minotaur"] += 1.2 * mars_boost + 0.8 * jup_boost
            reasons["Minotaur"].append("Mars+Jupiter prominence (forceful momentum).")
        scores["Minotaur"] += 0.65 * (earth + fire) / max(1e-6, sum(elem.values()))

        if is_prominent("Mars") and is_prominent("Saturn"):
            scores["Ogres"] += 1.1 * mars_boost + 0.9 * sat_boost
            if top_elem == "Earth":
                scores["Ogres"] += 0.95
            reasons["Ogres"].append("Mars+Saturn prominence (raw endurance).")
        if tight_aspects_between("Mars", "Saturn", hard):
            scores["Ogres"] += 1.25
        elif is_prominent("Saturn"):
            scores["Ogres"] += 0.45 * sat_boost
        if is_prominent("Saturn") and top_elem == "Earth":
            scores["Ogres"] += 0.5
        scores["Ogres"] += 0.9 * earth / max(1e-6, sum(elem.values()))
        scores["Ogres"] += 0.22 * self._clamp01((modal.get("fixed", 0.0) / total_modal - 0.25) / 0.35)

        # Water/liminal archetypes
        if is_prominent("Neptune"):
            scores["Merfolk"] += 1.1 * nep_boost
        if is_prominent("Moon"):
            scores["Merfolk"] += 0.8 * moon_boost
        scores["Merfolk"] += 0.8 * water / max(1e-6, sum(elem.values()))

        if is_prominent("Neptune") and is_prominent("Mars"):
            scores["Triton"] += 1.0 * nep_boost + 0.7 * mars_boost
            reasons["Triton"].append("Neptune+Mars prominence (martial tides).")
        elif is_prominent("Neptune"):
            scores["Triton"] += 0.55 * nep_boost
        if tight_aspects_between("Neptune", "Moon", hard) or tight_aspects_between("Neptune", "Jupiter", hard):
            scores["Triton"] += 0.5 * nep_boost
        scores["Triton"] += 1.05 * water / max(1e-6, sum(elem.values()))

        # Synthetic/liminal body archetypes
        if is_prominent("Neptune") and is_prominent("Uranus"):
            scores["Plasmoid"] += 1.2 * nep_boost + 0.9 * ura_boost
            reasons["Plasmoid"].append("Neptune+Uranus prominence (fluid anomaly).")
        elif is_prominent("Neptune"):
            scores["Plasmoid"] += 0.5 * nep_boost
        if sign_of("Neptune") in ("Pisces", "Aquarius") and sign_of("Uranus") in ("Pisces", "Aquarius", "Gemini", "Libra"):
            scores["Plasmoid"] += 0.55
        scores["Plasmoid"] += 0.85 * (water + air) / max(1e-6, sum(elem.values()))

        # Lust/charm infernal archetype
        if is_prominent("Venus") and (is_prominent("Neptune") or is_prominent("Pluto")):
            scores["Succubi/Incubi"] += 1.4 * venus_boost + 0.8 * max(nep_boost, plu_boost)
            reasons["Succubi/Incubi"].append("Venus with Neptune/Pluto prominence (seductive intensity).")
        elif is_prominent("Venus") and top_elem in ("Water", "Air"):
            scores["Succubi/Incubi"] += 0.45 * venus_boost
        if tight_aspects_between("Venus", "Neptune", hard) or tight_aspects_between("Venus", "Pluto", hard):
            scores["Succubi/Incubi"] += 0.9

        # Stone bodies: earth + saturn + fixed pressure
        if is_prominent("Saturn") and (is_prominent("Mars") or is_prominent("Pluto")):
            scores["Stone People (Golems)"] += 1.0 * sat_boost + 0.6 * max(mars_boost, plu_boost)
        elif is_prominent("Saturn"):
            scores["Stone People (Golems)"] += 0.45 * sat_boost
        scores["Stone People (Golems)"] += 0.95 * earth / max(1e-6, sum(elem.values()))
        scores["Stone People (Golems)"] += 0.24 * self._clamp01((modal.get("fixed", 0.0) / total_modal - 0.24) / 0.35)

        # Single-eye titan style: solar + saturnine fixation
        if is_prominent("Sun") and is_prominent("Saturn"):
            scores["Cyclops"] += 1.1 * sun_boost + 0.9 * sat_boost
        scores["Cyclops"] += 0.55 * fire / max(1e-6, sum(elem.values()))

        # Distribution calibration to prevent perennial over-winners.
        # These are intentionally conservative multipliers.
        calibration = {
            "Aasimar": 1.08,
            "Tiefling": 0.74,
            "Human": 0.92,
            "Elf": 1.22,
            "Halfling": 1.30,
            "Birdfolk": 1.14,
            "Skeleton": 1.10,
            "Cosmids": 1.00,
            "Robots": 1.08,
            "Tabaxi": 1.08,
            "Dwarf": 0.94,
            "Rodentfolk": 1.18,
            "Nymph": 1.22,
            "Stone People (Golems)": 1.30,
            "Vampire": 1.18,
            "Lizardfolk (Reptilians)": 1.08,
            "Yuan-Ti (Serpentine)": 1.22,
            "Half-orcs": 1.20,
            "Orcs": 1.22,
            "Plasmoid": 1.24,
            "Merfolk": 1.10,
            "Minotaur": 1.10,
            "Ogres": 1.40,
            "Triton": 1.35,
            "Succubi/Incubi": 1.24,
            "Gnome": 1.00,
            "Dragons": 1.20,
            "Cyclops": 1.08,
        }
        for fam, mult in calibration.items():
            if fam in scores:
                scores[fam] *= mult

        # Clean up: clamp very low negatives
        for k in list(scores.keys()):
            scores[k] = float(max(-1.0, scores[k]))

        return scores, reasons

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
        elem = feats["element_balance"]
        top_elem = max(elem.items(), key=lambda kv: kv[1])[0]
        evidence: List[str] = []

        hard = {"square", "opposition", "conjunction"}

        def tight(p: str, q: str) -> bool:
            for a in aspects:
                p1, p2 = str(a.get("p1")), str(a.get("p2"))
                asp = str(a.get("aspect", "")).lower()
                orb = float(a.get("orb", 999.0)) if a.get("orb") is not None else 999.0
                if orb <= self.orb_tight_deg and asp in hard and ((p1 == p and p2 == q) or (p1 == q and p2 == p)):
                    return True
            return False

        # Aasimar subtypes
        if family == "Aasimar": #Angel
            protector = tight("Saturn", "Sun") or tight("Saturn", "Moon")
            scourge = (positions.get("Mars", {}).get("house") in (1, 10)) or tight("Mars", "Sun")
            fallen = tight("Pluto", "Sun") or tight("Pluto", "Moon") or tight("Saturn", "Sun")
            if fallen and not protector and (tight("Pluto", "Sun") or tight("Pluto", "Moon")):
                evidence.append("Subtype: Pluto tightly tied to luminary => Fallen lean.")
                return "Fallen", evidence
            if scourge:
                evidence.append("Subtype: Mars tied to identity/calling => Scourge lean.")
                return "Scourge", evidence
            evidence.append("Subtype: Saturn supports luminaries => Protector lean.")
            return "Protector", evidence

        if family == "Birdfolk":
            # crude but functional:
            # Owlin: Moon + Saturn / nocturnal houses; Kenku: Mercury-Uranus weird; Aarakocra: Sun/Jupiter/Air
            if tight("Mercury", "Uranus"):
                evidence.append("Subtype: Mercury–Uranus tight => Kenku lean.")
                return "Kenku", evidence
            if positions.get("Moon", {}).get("house") in (8, 12) or tight("Saturn", "Moon"):
                evidence.append("Subtype: Moon in 8/12 or Saturn–Moon => Owlin lean.")
                return "Owlin", evidence
            if top_elem == "Air" and (tight("Sun", "Jupiter") or positions.get("Jupiter", {}).get("house") in (9, 10, 11)):
                evidence.append("Subtype: Air + Sun/Jupiter => Aarakocra lean.")
                return "Aarakocra", evidence
            return "Other (non-owl, non-kenku, non-aarakocra)", evidence

        if family == "Canids":
            # Shepherd Dogs: Saturn + Moon + 6/10; Wolfkin: Moon+Mars + 8/12; Houndfolk: Jupiter+Moon mutable proxy; Gnolls: Mars+Uranus hard
            h_moon = positions.get("Moon", {}).get("house")
            if (positions.get("Saturn", {}).get("house") in (6, 10) or tight("Saturn", "Moon")) and (h_moon in (6, 10) or positions.get("Moon", {}).get("house") is not None):
                evidence.append("Subtype: Saturn/Moon duty pattern => Shepherd Dogs lean.")
                return "Shepherd Dogs", evidence
            if h_moon in (8, 12) and (tight("Mars", "Moon") or tight("Mars", "AS")):
                evidence.append("Subtype: Moon 8/12 + Mars tight => Wolfkin lean.")
                return "Wolfkin", evidence
            if tight("Mars", "Uranus"):
                evidence.append("Subtype: Mars–Uranus tight => Gnolls lean.")
                return "Gnolls", evidence
            if tight("Jupiter", "Moon") or positions.get("Jupiter", {}).get("house") in (3, 9):
                evidence.append("Subtype: Jupiter–Moon or roaming houses => Houndfolk lean.")
                return "Houndfolk", evidence
            return "Wolfkin", evidence

        if family == "Cosmids":
            # Starspawned: Uranus+Neptune to big3; Eclipsians: nodes tied to luminaries; Abysswalkers: Pluto+Neptune to big3; Chronomancers: Saturn+Uranus+Mercury tight; Cometkin: Jupiter+Uranus angular
            if tight("Mercury", "Saturn") and tight("Mercury", "Uranus"):
                evidence.append("Subtype: Mercury tightly tied to Saturn+Uranus => Chronomancers.")
                return "Chronomancers", evidence
            if (tight("Pluto", "Sun") or tight("Pluto", "Moon") or tight("Pluto", "AS")) and (tight("Neptune", "Sun") or tight("Neptune", "Moon") or tight("Neptune", "AS")):
                evidence.append("Subtype: Pluto+Neptune tightly tied to big3 => Abysswalkers.")
                return "Abysswalkers", evidence
            if (tight("Uranus", "Sun") or tight("Uranus", "Moon") or tight("Uranus", "AS")) and (tight("Neptune", "Sun") or tight("Neptune", "Moon") or tight("Neptune", "AS")):
                evidence.append("Subtype: Uranus+Neptune tightly tied to big3 => Starspawned.")
                return "Starspawned", evidence
            if positions.get("Uranus", {}).get("house") in (10, 11) and positions.get("Jupiter", {}).get("house") in (10, 11):
                evidence.append("Subtype: Uranus+Jupiter high/visible houses => Cometkin.")
                return "Cometkin", evidence
            # nodes
            if (tight("Rahu", "Sun") or tight("Ketu", "Sun") or tight("Rahu", "Moon") or tight("Ketu", "Moon")):
                evidence.append("Subtype: Nodes tightly tied to luminaries => Eclipsians.")
                return "Eclipsians", evidence
            return "Starspawned", evidence

        if family == "Cyborgs":
            # Light augmented / Combat-oriented / Advanced AI
            combat = tight("Mars", "Saturn") or tight("Mars", "Uranus")
            ai = tight("Mercury", "Uranus") and tight("Mercury", "Saturn")
            if ai:
                evidence.append("Subtype: Mercury tightly tied to Uranus+Saturn => Advanced AI.")
                return "Advanced AI", evidence
            if combat:
                evidence.append("Subtype: Mars tightly tied to Saturn/Uranus => Combat-Oriented.")
                return "Combat-Oriented", evidence
            return "Light Augmented", evidence

        if family == "Dwarf":
            # Hill / Mountain / Duergar / Mark of Warding
            taurus_signature = float(feats.get("taurus_signature", 0.0))
            if positions.get("Pluto", {}).get("house") in (8, 12) or tight("Pluto", "Saturn"):
                evidence.append("Subtype: Saturn+Pluto underworld signature => Duergar (Underdark).")
                return "Duergar (Underdark)", evidence
            if tight("Mercury", "Saturn"):
                evidence.append("Subtype: Mercury–Saturn defensive systems => Mark of Warding (Eberron).")
                return "Mark of Warding (Eberron)", evidence
            if positions.get("Mars", {}).get("sign") in ("Aries", "Capricorn", "Scorpio") or tight("Mars", "Saturn"):
                evidence.append("Subtype: Mars+Saturn grit => Mountain.")
                return "Mountain", evidence
            if taurus_signature >= 0.30 or positions.get("Moon", {}).get("sign") == "Taurus":
                evidence.append("Subtype: Taurus-heavy signature => Hill.")
                return "Hill", evidence
            return "Hill", evidence

        if family == "Elf":
            # High / Wood / Drow / Eladrin / Sea / Shadar-Kai / Avariel
            air = feats["element_balance"]["Air"]
            water = feats["element_balance"]["Water"]
            earth = feats["element_balance"]["Earth"]
            if tight("Pluto", "Venus") and (water > earth):
                evidence.append("Subtype: Venus–Pluto + water lean => Drow.")
                return "Drow (Dark Elf)", evidence
            if tight("Saturn", "Pluto") or positions.get("Saturn", {}).get("house") in (12,):
                evidence.append("Subtype: Saturn+Pluto / 12th signature => Shadar-Kai.")
                return "Shadar-Kai", evidence
            if water > air and (positions.get("Moon", {}).get("sign") in ("Cancer", "Pisces", "Scorpio") or positions.get("Neptune", {}).get("sign") in ("Pisces",)):
                evidence.append("Subtype: Water emphasis => Sea Elf.")
                return "Sea Elf", evidence
            if air >= water and (positions.get("Mercury", {}).get("sign") in ("Gemini", "Virgo", "Aquarius") or tight("Mercury", "Jupiter")):
                evidence.append("Subtype: Air + Mercury/Jupiter => High Elf.")
                return "High Elf", evidence
            if earth > air and positions.get("Moon", {}).get("sign") in ("Taurus", "Virgo", "Capricorn"):
                evidence.append("Subtype: Earth + Moon => Wood Elf.")
                return "Wood Elf", evidence
            if positions.get("Uranus", {}).get("house") in (1, 4, 7, 10) and positions.get("Moon", {}).get("house") in (1, 4, 7, 10):
                evidence.append("Subtype: angular Uranus+Moon => Eladrin (seasonal shifts).")
                return "Eladrin (Seasonal)", evidence
            if air > 0 and (tight("Sun", "Jupiter") or positions.get("Jupiter", {}).get("house") in (9, 10, 11)):
                evidence.append("Subtype: Air + Sun/Jupiter altitude vibe => Avariel.")
                return "Avariel", evidence
            return "High Elf", evidence

        if family == "Fey":
            # hobgoblins, firbolgs, leprechauns, trolls, giants, fairies, satyrs, fawns
            if tight("Venus", "Saturn"):
                evidence.append("Subtype: Venus–Saturn tight => Hobgoblins (strategic social discipline).")
                return "Hobgoblins", evidence
            if top_elem == "Air" and (tight("Venus", "Uranus") or tight("Mercury", "Uranus")):
                evidence.append("Subtype: Air + Uranian charm => Fairies.")
                return "Fairies", evidence
            if top_elem == "Earth" and (positions.get("Jupiter", {}).get("house") in (4, 6, 10) or tight("Jupiter", "Saturn")):
                evidence.append("Subtype: Earth + Jupiter/Saturn => Firbolgs.")
                return "Firbolgs", evidence
            if tight("Venus", "Jupiter") and positions.get("Venus", {}).get("house") in (5,):
                evidence.append("Subtype: Venus–Jupiter + 5th => satyrs/fawns.")
                return "Satyr/Fawn", evidence
            if tight("Mars", "Jupiter"):
                evidence.append("Subtype: Mars–Jupiter tight => Trolls/giants.")
                return "Trolls", evidence
            return "Leprechauns", evidence

        if family == "Genasi":
            # Air/Earth/Fire/Water + your extended set
            if top_elem == "Fire":
                if tight("Uranus", "Mars"):
                    return "Electric", evidence
                return "Fire", evidence
            if top_elem == "Air":
                if tight("Uranus", "Mars") or tight("Uranus", "Mercury"):
                    return "Electric", evidence
                return "Air", evidence
            if top_elem == "Earth":
                if feats["element_balance"]["Water"] > 0.9 * feats["element_balance"]["Earth"]:
                    return "Mud", evidence
                return "Earth", evidence
            if top_elem == "Water":
                if tight("Saturn", "Moon") or tight("Saturn", "Neptune"):
                    return "Ice", evidence
                return "Water", evidence
            # fallback
            return top_elem, evidence

        if family == "Halfling":
            # Lightfoot/Stout/Ghostwise/Marks
            if tight("Mercury", "Neptune") or tight("Moon", "Neptune"):
                return "Ghostwise", evidence
            if top_elem == "Earth":
                return "Stout", evidence
            if tight("Venus", "Jupiter"):
                return "Mark of Hospitality (Eberron)", evidence
            if tight("Venus", "Moon") and positions.get("Moon", {}).get("house") in (6,):
                return "Mark of Healing (Eberron)", evidence
            return "Lightfoot", evidence

        if family == "Human":
            if self._is_spiky(feats):
                return "Variant", evidence
            return "Standard", evidence

        if family == "Tabaxi":
            if tight("Venus", "Pluto") or (positions.get("Pluto", {}).get("house") in (1, 8) and positions.get("Venus", {}).get("house") in (1, 5, 7)):
                return "Pantherkin", evidence
            if positions.get("Sun", {}).get("sign") in ("Leo",) or positions.get("Mars", {}).get("sign") in ("Leo", "Aries"):
                return "Tigerfolk", evidence
            return "Other (non-panther, non-tiger, non-lion, non-cat)", evidence

        if family in {"Lizardfolk (Reptilians)", "Lizardfolk (Reptilian)"}:
            # Dinoboiz vs misc
            if tight("Mars", "Jupiter") or positions.get("Jupiter", {}).get("house") in (1, 10):
                return "Dinoboiz", evidence
            return "Other", evidence

        if family == "Robots":
            # Autognome vs misc constructs
            if tight("Mercury", "Saturn") and feats["element_balance"]["Earth"] > feats["element_balance"]["Water"]:
                return "Autognome", evidence
            return "Alternative Construct", evidence

        if family == "Rodentfolk":
            # Ratfolk/Squirrelfolk/Guineafolk
            if feats["element_balance"]["Air"] > feats["element_balance"]["Earth"]:
                return "Squirrelfolk", evidence
            if feats["element_balance"]["Earth"] >= feats["element_balance"]["Air"] and (positions.get("Saturn", {}).get("house") in (2, 6) or positions.get("Mercury", {}).get("house") in (2, 6)):
                return "Ratfolk", evidence
            return "Other (non-rat, non-squirrel)", evidence

        if family == "Shapeshifter":
            # Changelings / Doppelgangers / Lycanthropes
            glm_signature = float(feats.get("glm_signature", 0.0))
            if glm_signature >= 0.60:
                evidence.append("Subtype: strong Gemini/Libra/Pisces signature => Changelings.")
                return "Changelings", evidence
            mercury_angular = positions.get("Mercury", {}).get("house") in (1, 10)
            if tight("Pluto", "Mercury") and mercury_angular:
                evidence.append("Subtype: tight Pluto–Mercury with angular Mercury => Doppelgangers.")
                return "Doppelgangers", evidence
            hc = feats.get("house_counts", {}) or {}
            house_total = max(1e-6, sum(float(v) for v in hc.values()))
            liminal_emphasis = (float(hc.get(1, 0.0)) + float(hc.get(8, 0.0)) + float(hc.get(12, 0.0))) / house_total
            if tight("Mars", "Moon") and liminal_emphasis >= 0.33:
                evidence.append("Subtype: tight Mars–Moon plus 1/8/12 house emphasis => Lycanthropes.")
                return "Lycanthropes", evidence
            return "Changelings", evidence

        if family == "Skeleton":
            # Bone Warrior / Skeletal Mage / Lich
            if tight("Mercury", "Pluto") and tight("Mercury", "Saturn"):
                return "Lich", evidence
            if tight("Mercury", "Saturn"):
                return "Skeletal Mage", evidence
            return "Bone Warrior", evidence

        if family == "Spirits":
            # poltergeist/wraith/ghoul/vagrant spirit
            if tight("Uranus", "Neptune") or tight("Uranus", "Moon"):
                return "Poltergeist", evidence
            if tight("Saturn", "Neptune") or tight("Saturn", "Moon"):
                return "Wraith", evidence
            if tight("Mars", "Neptune"):
                return "Ghoul", evidence
            return "Vagrant Spirit", evidence

        if family == "Stone People (Golems)":
            # Stoneborn / Earth-Forged / Crystalborn
            if feats["element_balance"]["Earth"] > 0.40 * sum(feats["element_balance"].values()):
                if tight("Uranus", "Venus") or tight("Uranus", "Mercury"):
                    return "Crystalborn", evidence
                if tight("Saturn", "Mars"):
                    return "Earth-Forged Golems", evidence
            return "Stoneborn", evidence

        if family == "Succubi/Incubi":
            # Abyssal vs Dreamweaver
            if tight("Venus", "Neptune"):
                return "Dreamweaver Succubi", evidence
            return "Abyssal Succubi", evidence

        if family == "Tiefling":
            # Standard / Feral / Bloodline hints
            feral = tight("Mars", "Uranus") or positions.get("Mars", {}).get("house") in (1,)
            if feral:
                return "Feral", evidence
            # crude bloodline heuristics:
            if tight("Saturn", "Sun") or tight("Saturn", "Pluto"):
                return "Bloodlines (e.g., Asmodeus)", evidence
            if tight("Mars", "Sun") or positions.get("Mars", {}).get("house") in (10,):
                return "Bloodlines (e.g., Zariel)", evidence
            if tight("Saturn", "Neptune"):
                return "Bloodlines (e.g., Levistus)", evidence
            return "Standard", evidence

        if family == "Vampire":
            # True Vampire / Dhampir / Nosferatu
            if tight("Venus", "Pluto") and tight("Saturn", "Pluto"):
                return "True Vampire", evidence
            if tight("Saturn", "Pluto") and not positions.get("Venus", {}).get("sign"):
                return "Nosferatu", evidence
            return "Dhampir", evidence

        if family == "Yuan-Ti (Serpentine)":
            # Pureblood/Malison
            if tight("Pluto", "Neptune") and tight("Venus", "Pluto"):
                return "Pureblood", evidence
            return "Malison", evidence

        # Families with no subtype list in your reference
        if family in {"Cyclops", "Dragons", "Merfolk", "Minotaur", "Ogres", "Orcs", "Plasmoid", "Triton"}:
            return "", evidence

        # Generic fallback
        return "", evidence

    # ----------------------------
    # Evidence formatting helpers
    # ----------------------------

    def _compact_evidence(
        self,
        family_reasons: List[str],
        subtype_evidence: List[str],
        positions: Mapping[str, Mapping[str, Any]],
        aspects: List[Mapping[str, Any]],
        feats: Mapping[str, Any],
        limit: int = 6,
    ) -> List[str]:
        out: List[str] = []
        # include 1–2 hard facts about tight outer binds if present
        tob = feats.get("tight_outer_to_big3", [])
        if tob:
            # show up to 2
            for outer, target, asp, orb in tob[:2]:
                out.append(f"Tight: {outer} {asp} {target} (orb {orb:.2f}°).")

        # include a short element summary
        elem = feats["element_balance"]
        out.append("Elements (weighted): " + ", ".join(
            f"{k}={elem[k]:.1f}" for k in ("Fire", "Earth", "Air", "Water")
        ) + ".")

        # add reasons + subtype notes
        for s in family_reasons:
            if s not in out:
                out.append(s)
        for s in subtype_evidence:
            if s not in out:
                out.append(s)

        return out[:limit]

    # ----------------------------
    # Utility
    # ----------------------------

    def _families(self) -> List[str]:
        # Mirrors your list labels, with one renamed family ("Spirits") to avoid a banned term.
        return list(SPECIES_FAMILIES)

    def _big3(self, positions: Mapping[str, Mapping[str, Any]]) -> Dict[str, Optional[str]]:
        out: Dict[str, Optional[str]] = {}
        for k in ("Sun", "Moon", "AS"):
            out[k] = positions.get(k, {}).get("sign")
        return out

    def _is_spiky(self, feats: Mapping[str, Any]) -> bool:
        # “spiky” = many tight outer binds or extreme element dominance
        elem = feats["element_balance"]
        dom_ratio = max(elem.values()) / max(1e-6, sum(elem.values()))
        return bool(feats.get("tight_outer_to_big3")) or dom_ratio >= 0.40

    @staticmethod
    def _angle_delta(a: float, b: float) -> float:
        d = abs((a - b) % 360.0)
        return min(d, 360.0 - d)

    @staticmethod
    def _sign_for_longitude(lon: float) -> str:
        signs: Sequence[str] = (
            "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
            "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
        )
        idx = int((lon % 360.0) // 30.0)
        return signs[idx]

    @staticmethod
    def _house_for_longitude(houses: Any, lon: float) -> Optional[int]:
        if not isinstance(houses, (list, tuple)) or len(houses) < 12:
            return None
        lon = lon % 360.0
        cusps = [float(c) % 360.0 for c in houses[:12]]
        for idx in range(12):
            start = cusps[idx]
            end = cusps[(idx + 1) % 12]
            if end <= start:
                end += 360.0
            probe = lon
            if probe < start:
                probe += 360.0
            if start <= probe < end:
                return idx + 1
        return None


def assign_top_three_species(chart: Any) -> List[Tuple[str, str, float]]:
    """Convenience wrapper used by GUI and external callers."""
    return SpeciesAssigner().assign(chart).top_three

def assign_top_three_species_with_evidence(
    chart: Any,
) -> List[Tuple[str, str, float, List[str]]]:
    """Return top three species picks plus compact evidence for each."""
    assigner = SpeciesAssigner()
    positions = assigner._get_positions(chart)
    aspects = assigner._get_aspects(chart, positions)
    feats = assigner._extract_features(positions, aspects)
    scores, reasons = assigner._score_families(positions, aspects, feats)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)

    picks_with_evidence: List[Tuple[str, str, float, List[str]]] = []
    for family, score in ranked[:3]:
        subtype, subtype_evidence = assigner._pick_subtype(family, positions, aspects, feats)
        compact_evidence = assigner._compact_evidence(
            reasons.get(family, []),
            subtype_evidence,
            positions,
            aspects,
            feats,
        )
        picks_with_evidence.append((family, subtype, round(score, 3), compact_evidence))
    return picks_with_evidence


# # ----------------------------
# # Example usage
# # ----------------------------
# if __name__ == "__main__":
#     # Minimal example chart
#     chart = {
#         "positions": {
#             "Sun": {"sign": "Pisces", "lon": 335.30, "house": 4},
#             "Moon": {"sign": "Capricorn", "lon": 287.47, "house": 1},
#             "Mercury": {"sign": "Aquarius", "lon": 318.45, "house": 3},
#             "Venus": {"sign": "Aquarius", "lon": 305.62, "house": 3},
#             "Mars": {"sign": "Aries", "lon": 6.00, "house": 2},
#             "Jupiter": {"sign": "Virgo", "lon": 150.80, "house": 8},
#             "Saturn": {"sign": "Aries", "lon": 10.89, "house": 2},
#             "Uranus": {"sign": "Virgo", "lon": 178.56, "house": 9},
#             "Neptune": {"sign": "Scorpio", "lon": 236.97, "house": 10},
#             "Pluto": {"sign": "Virgo", "lon": 172.43, "house": 9},
#             "AS": {"sign": "Capricorn", "lon": 271.25, "house": 1},
#             "MC": {"sign": "Libra", "lon": 209.05, "house": 10},
#         }
#         # "aspects": [...]  # optional; will be derived if missing
#     }

#     pick = SpeciesAssigner().assign(chart)
#     print(pick)

# Master reference for species + subtype explainer text.
# Fill in each blank string with a user-facing explanation.
SPECIES_SUBVARIANT_EXPLAINER_TEMPLATE: Dict[str, str] = {
    "Aasimar": "Aasimar look like people who have been lit slightly better than the rest of us, as if the air around them has been quietly retouched. They tend to smell faintly of cold morning air, old linen, and the last inch of beeswax candle. Being near one can feel oddly clarifying, which is pleasant right up until they start speaking as though conscience were a public utility.",
    "Aasimar::Protector": "Protector aasimar have the unmistakable air of someone who would arrive on a hilltop at dawn for no practical reason and somehow make it seem justified. Their presence has the clean, thin quality of high altitude: bright, dry, and a little severe. They are reassuring in the way a well-built bridge is reassuring, which is lovely unless you were hoping for mischief.",
    "Aasimar::Scourge": "Scourge aasimar do not so much glow as overheat. Their beauty has the hard, white edge of metal left too long in a forge, and the room around them can feel one bad mood away from becoming a sermon. They are what happens when moral clarity decides that subtlety is for later.",
    "Aasimar::Fallen": "Fallen aasimar look like grace that missed a step and kept walking. There is usually something singed about them, not literally, but in the sense that their elegance has acquired corners, smoke, and a private grievance. They give off the feeling of cathedral stone after a storm: still grand, still cold, and no longer taking questions.",

    "Birdfolk": "Birdfolk are the general case for feathered humanoids: beaks, talons, wings, down, pinfeathers, head-cocks, and the distinct sense that they noticed three things behind you while you were still introducing yourself. They often smell of sun-warmed feathers, dust, rainwater, and whatever passes for grooming in a species that regards bathing as both practical and theatrical.",
    "Birdfolk::Kenku": "Kenku are compact, dark-feathered, bright-eyed little opportunists who move with the start-stop precision of creatures that have spent centuries surviving by noticing absolutely everything. Their voices often sound borrowed because, in a sense, they are. Being around one feels like standing in an alley behind a theatre and realizing the alley is smarter than the play.",
    "Birdfolk::Owlin": "Owlin tend to look soft until they turn their heads and remind you that softness and predation have never actually been enemies. They smell faintly of dry bark, old paper, dust, and night air through a half-open window. They experience the world as a series of quiet motions in darkness, which makes daylight society seem to them exactly as clumsy as it is.",
    "Birdfolk::Aarakocra": "Aarakocra have the rangy, weather-polished look of things built by cliff edges and wind shear rather than by towns. Their feathers often carry the smell of clean air, stone, and distant rain. They experience ground life the way sailors experience long meetings in basements: with patience, but not respect.",
    "Birdfolk::Other (non-owl, non-kenku, non-aarakocra)": "The rest of birdfolk run the full avian catalog: glossy, scruffy, shrill, stately, ridiculous, impeccable, and everything between. Some arrive all swan-neck elegance, some all gull-nerved audacity, some with the grave self-importance of a heron in shallow water. As a class, they are ornamental only until they open their beaks.",

    "Canids": "Canids are dog-, wolf-, jackal-, and hyena-flavored humanoids built around nose, ear, pack, pace, and the useful belief that the world usually means something if you sniff it long enough. They often smell of fur, leather, weather, woodsmoke, and the outer edge of the camp. They tend to experience a place socially first and aesthetically second, which frankly is how most places deserve to be experienced.",
    "Canids::Shepherd Dogs": "Shepherd-dog folk look like practical competence grew a coat and learned to stand upright. They have the alert, domestic, faintly managerial energy of a creature that has spent generations preventing disorder and being rewarded with more disorder. They notice open gates, fraying ropes, unattended children, and your bad plan before you do.",
    "Canids::Wolfkin": "Wolfkin are all rangy limbs, watchful eyes, winter breath, and the feeling that they would trust moonlight over municipal law. They smell of pine bark, cold fur, damp earth, and distance. They experience the world in terms of border, pursuit, silence, and hunger, which makes taverns feel to them like an odd and temporary truce.",
    "Canids::Gnolls": "Gnolls have the rough, powerful, slightly disreputable look of a laugh that got teeth involved. Their presence often brings with it the smell of hide, dust, old blood, sun-baked grass, and bad judgment. They experience appetite as a structural principle rather than a passing inconvenience, which is very dynamic of them and very tiresome for everyone else.",
    "Canids::Houndfolk": "Houndfolk are long-faced, keen-nosed, and built with the air of something designed to follow the one true line through a baffling world. They tend to carry scents the way scholars carry footnotes: obsessively, hierarchically, and with a grim sense of duty. To them, every room is a layered archive of where everyone has been and what they were too polite to mention.",

    "Cosmids": "Cosmids look as though some part of them was assembled using sky instead of ordinary childhood. Their skin, eyes, or manner often suggest moonlight, eclipses, starfields, deep water at midnight, or the sort of clock that makes you nervous. Being near one can feel mildly dislocating, like discovering the evening has become larger than advertised.",
    "Cosmids::Chronomancers": "Chronomancer cosmids often have a faintly delayed quality, as though their gestures arrive in several drafts and their attention is standing half a minute to one side of the present. They may smell of old books, iron filings, cold tea, and the air inside watchmakers' shops. They experience time less as a line and more as a crowded hallway.",
    "Cosmids::Abysswalkers": "Abysswalkers carry the cold vastness of unlit distances: not theatrical menace, just scale, quiet, and the unnerving suggestion that human concerns are very local weather. Their colors tend toward dark glass, deep blue, black, silver, and other shades found where sunlight has resigned. They make ordinary rooms feel like provisional shelters.",
    "Cosmids::Starspawned": "Starspawned beings have a polished, remote beauty, as though they were designed for admiration from far away and unfortunate clarity up close. There is often something glittering, crystalline, or over-precise about them, like frost on dark metal. They experience the world as pattern first, event second, which makes them good at prophecy-adjacent behavior and terrible at brunch.",
    "Cosmids::Cometkin": "Cometkin look fast even when standing still. Hair, eyes, clothing, aura, whatever they have always seems to imply motion, sparks, streaks, and the possibility of immediate departure. They smell of ozone, hot stone, and the first five seconds of a storm.",
    "Cosmids::Eclipsians": "Eclipsians are creatures of dimming and revelation: a face in shadow with a ring of light around it, a voice that seems nearer when it lowers, an atmosphere of thresholds. They experience the world in terms of appearance, disappearance, and timing, which makes them excellent at entrances and deeply unhelpful in committees.",

    "Cyborgs": "Cyborgs are part person, part engineered amendment, with flesh and mechanism forced into a truce that may or may not be elegant. They can smell of machine oil, warm copper, antiseptic, leather straps, rain on metal, or simply clean skin with one wrong note underneath. They experience the world through sensation plus calibration, which means they are rarely fully off-duty.",
    "Cyborgs::Advanced AI": "Advanced AI cyborgs often have the slightly overfinished quality of objects built after too much thought. Their gaze can be unsettling not because it is cold, but because it is busy in ways yours is not. They tend to parse rooms as data-rich negotiation zones, which is probably correct and still a dreadful way to attend a birthday dinner.",
    "Cyborgs::Combat-Oriented": "Combat cyborgs look reinforced in the manner of things designed after a lawsuit. Plates, braces, subdermal housings, hard edges, and a gait that suggests momentum has legal standing. They smell of oil, solvent, hot wiring, wool padding, and the practical side of fear.",
    "Cyborgs::Light Augmented": "Lightly augmented cyborgs are the subtle model: a lens where an eye ought to be ordinary, a joint that moves too smoothly, fingertips with improbable steadiness, hearing tuned half a notch beyond comfort. They are often most noticeable in silence, when nothing is happening and they are still detecting six things more than you.",

    "Cyclops": "Cyclopes are huge one-eyed humanoids whose central eye gives them an unnervingly direct presence, like being personally addressed by geology. They often smell of lanolin, stone dust, forge heat, wet earth, and old timber. The world comes to them in mass, distance, line, and impact; fine print is not their chosen art form.",

    "Dragons": "Dragons look the way a treasury, a thunderstorm, and an ego problem would look if forced to share a skeleton. Their scents vary wildly by kind—sulfur, cedar, river mud, snow, spice, hot coin, damp cave—but always feel expensive in one way or another. They experience place three-dimensionally and proprietorially: sky above, hoard below, everything else under review.",

    "Dwarf": "Dwarves are compact, broad, weather-resistant people who tend to look as though they were designed by someone suspicious of both waste and ornament. They often smell of clean wool, yeast, iron, soap, cedar chests, and last night's fire. They experience the world through weight, workmanship, temperature, and whether a thing was made properly, which is an excellent way to move through life if you don't mind being right all the time.",
    "Dwarf::Duergar (Underdark)": "Duergar have the pale, drawn, pressure-cooked look of people shaped by depth, stone, labor, and a chronic shortage of sunlight. They smell of metal filings, lamp smoke, stale air, and underground water. The surface world often strikes them as glaring, flimsy, and much too enthusiastic.",
    "Dwarf::Mark of Warding (Eberron)": "These dwarves tend to look groomed, guarded, and professionally difficult to steal from. Even their clothes often seem arranged with the logic of locks and ledgers. They experience the world as a series of vulnerabilities to be anticipated, priced, and quietly prevented.",
    "Dwarf::Mountain": "Mountain dwarves are the blockier, heavier, more fortress-like branch: thick wrists, deep chests, stride like a loaded cart that has no intention of tipping. They fit high cold places, strong doors, and dark ale with a sort of ancestral precision. One gets the sense they would survive the end of an age mainly by considering it overblown.",
    "Dwarf::Hill": "Hill dwarves are still sturdy, but in a warmer, rounder, more lived-in way, like a good farmhouse built on bedrock. They smell of root vegetables, grain, pipe leaf, beeswax, and cellars that keep excellent records. They experience land in seasons and yield, not conquest.",

    "Elf": "Elves tend to look too composed for ordinary biology, as if they were given more time in the drying rack. Their movements are usually economical, their clothes annoying in their effortless drape, and their senses tuned toward leaf-rustle, distant water, moonlight, and insult. They experience time with enough slack in it to make the rest of us seem like panicked shoppers.",
    "Elf::Drow (Dark Elf)": "Drow have the dark, polished beauty of things that evolved away from sun glare and into candlelight, fungus light, polished obsidian, and dangerous court manners. They often smell faintly of mineral water, incense, spider silk, oil, and enclosed stone. They experience space vertically, politically, and with no sentimental attachment to innocence.",
    "Elf::Shadar-Kai": "Shadar-Kai are severe, pale, dark-clad, and edged with the exhausted glamour of people who have spent too long standing near endings. Their beauty is spare rather than lush: chain, bone, ash, salt, black cloth, pale hands. They experience joy like a brief clear bell in winter air: real, sharp, and not to be wasted.",
    "Elf::Sea Elf": "Sea elves move with the smooth economy of swimmers even on land, which has the side effect of making everyone else look roughly assembled. They smell of salt, kelp, wet stone, shell, and cool currents. They experience the world in layers and pressure: surface glitter, middle drift, deep quiet.",
    "Elf::High Elf": "High elves have the curated look of people who were introduced to language, music, and passive disappointment at an impressionable age and never looked back. They tend to carry scents like parchment, herbs, polished wood, expensive soap, and garden air at dusk. They experience civilization aesthetically first and morally second, which explains rather a lot.",
    "Elf::Wood Elf": "Wood elves look sun-browned or leaf-shadowed, quick on the feet, and naturally dressed by bark, moss, leather, and very irritating good taste. They smell of resin, crushed leaves, clean fur, and rain caught in branches. The world comes to them as track, wind, rustle, and line of sight.",
    "Elf::Eladrin (Seasonal)": "Eladrin shift with the seasons, and it shows. Spring eladrin feel like wet earth and blossom air; summer like warm fruit and lightning far off; autumn like smoke, apples, and copper leaves; winter like frost on stone and a pause before speech. They experience mood as climate, which is poetic in theory and a public hazard in practice.",
    "Elf::Avariel": "Avariel are winged elves, all long bones, high shoulders, feathers, and the expensive look of creatures not intended for mud. They smell of cold air, feather dust, cliff grass, and sun on linen. On the ground they are patient, the way a hawk is patient on a glove.",

    "Fey": "Fey look, smell, and behave as though natural beauty were given opinions and then insufficient supervision. Flowers, bark, wet moss, honey, loam, dusk, mushrooms, cold streams, perfume that is half nectar and half warning: all of it belongs here. They experience the world as charged with meaning, and unfortunately so are teaspoons, promises, nicknames, and Tuesdays.",
    "Fey::Hobgoblins": "Fey hobgoblins have a martial tidiness to them: lacquered gear, measured posture, sharp eyes, and the air of people who keep banners folded correctly. They smell of oiled leather, campfire ash, cedar, and damp leaves. They experience community as a thing to be maintained deliberately, not wished into existence by flute music.",
    "Fey::Fairies": "Fairies are tiny, bright, quick, and entirely too comfortable with the fact that their size encourages underestimation. They often smell like nectar, crushed herbs, pollen, rain on petals, or whatever passes for confectionery in a flowerbed. They experience a room as a landscape, a table as a district, and your drink as an opportunity.",
    "Fey::Firbolgs": "Firbolgs are large, gentle, long-faced forest people with the kindly melancholy of old paths and weathered barns. They smell of moss, damp wool, bark, mushrooms, and soup that has been simmering for a respectable length of time. They experience speech as something to use when silence has had a fair chance.",
    "Fey::Satyr/Fawn": "Satyrs and fawns are goat-legged creatures of music, appetite, dancing, dust, wine, grass, and the ancient conviction that evening ought to go on longer. They smell of crushed thyme, sweat, cedar cups, spilled fruit, and hillside heat. They experience civilization as a useful source of cups and audiences.",
    "Fey::Trolls": "Fey-flavored trolls are less 'civilized giant' and more 'woodland problem with ancestry.' They tend to look damp, broad, rooty, licheny, and assembled by a marsh with strong feelings. They smell of peat, wet bark, pond water, mushrooms, and whatever was under the bridge before the bridge arrived.",
    "Fey::Leprechauns": "Leprechauns are small, neat, bright-eyed beings with the trim, polished appearance of people who could vanish into a hedge and come out with your ring, your purse, and a legal argument. They smell of clover, tobacco, old coins, rain on stone, and very expensive mischief. They experience rules the way musicians experience rhythm: as something to play with brilliantly."
}
