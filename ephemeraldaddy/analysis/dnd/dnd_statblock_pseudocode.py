STATBLOCK_DEFINITIONS = {
	"STR" : "force output, pressure, direct physical assertion, ability to impose self on resistance",
	"DEX" : "precision, timing, agility, coordination, fine motor control, tactical slipperiness",
	"CON" : "endurance, recovery, stress tolerance, bodily continuity, staying power",
	"INT" : "system mastery, patterning, abstraction, technical reasoning, learned complexity",
	"WIS" : "instinct + judgment + attunement, reading the field correctly, ecological or moral sense",
	"CHA" : "social gravity, expressive force, visible selfhood, ability to impose will through presence",
}

from dataclasses import dataclass
from typing import Mapping, Dict, Any
import math

@dataclass(frozen=True)
class DnDStatBlock:
    strength_raw: float
    dexterity_raw: float
    constitution_raw: float
    intelligence_raw: float
    wisdom_raw: float
    charisma_raw: float

    strength: int
    dexterity: int
    constitution: int
    intelligence: int
    wisdom: int
    charisma: int

    modifiers: Mapping[str, int]

    def score_dnd_stats(chart: Any) -> DnDStatBlock:
    scorer = ClassAxisScorer()
    features = scorer.extract_features(chart)
    axis_scores = scorer.score_axes(features)
    return score_dnd_stats_from_features(axis_scores, features)

def score_dnd_stats_from_features(
    axis_scores: Mapping[str, float],
    features: AxisFeatureSet,
) -> DnDStatBlock:
    validate_axis_scores(axis_scores)
    ...

    def score_dnd_stats_from_features(
    axis_scores: Mapping[str, float],
    features: AxisFeatureSet,
    *,
    stat_floor: int = 8,
    stat_ceiling: int = 18,
) -> DnDStatBlock:
    validate_axis_scores(axis_scores)

    p = features.planet_prominence
    e = features.element_balance
    m = features.mode_balance
    h = features.house_emphasis
    a = features.aspect_signals

    raw: Dict[str, float] = {}

    # STR: force, directness, physical imposition
    raw["strength"] = _clamp01(
        0.40 * axis_scores["frontline_courage"]
        + 0.22 * axis_scores["instinct"]
        + 0.14 * axis_scores["discipline"]
        + 0.08 * p.get("Mars", 0.0)
        + 0.06 * p.get("Sun", 0.0)
        + 0.05 * h.get("self", 0.0)
        + 0.05 * ((e.get("Fire", 0.0) + e.get("Earth", 0.0)) / 2.0)
    )

    # DEX: timing, finesse, hand-brain coordination, tactical slipperiness
    raw["dexterity"] = _clamp01(
        0.32 * axis_scores["stealth_indirection"]
        + 0.20 * axis_scores["control_planning"]
        + 0.16 * axis_scores["risk_appetite"]
        + 0.10 * p.get("Mercury", 0.0)
        + 0.08 * p.get("Uranus", 0.0)
        + 0.07 * e.get("Air", 0.0)
        + 0.07 * m.get("mutable", 0.0)
    )

    # CON: stamina, durability, recovery, resistance
    raw["constitution"] = _clamp01(
        0.28 * axis_scores["discipline"]
        + 0.20 * axis_scores["instinct"]
        + 0.16 * axis_scores["mercy_restoration"]
        + 0.12 * p.get("Saturn", 0.0)
        + 0.08 * p.get("Moon", 0.0)
        + 0.08 * e.get("Earth", 0.0)
        + 0.08 * m.get("fixed", 0.0)
    )

    # INT: learning, abstraction, engineering, codification
    raw["intelligence"] = _clamp01(
        0.36 * axis_scores["study"]
        + 0.20 * axis_scores["technical_inventiveness"]
        + 0.16 * axis_scores["control_planning"]
        + 0.12 * p.get("Mercury", 0.0)
        + 0.08 * p.get("Saturn", 0.0)
        + 0.08 * h.get("craft", 0.0)
    )

    # WIS: instinct + judgment + attunement + moral/ecological reading
    raw["wisdom"] = _clamp01(
        0.28 * axis_scores["faith"]
        + 0.24 * axis_scores["nature_attunement"]
        + 0.18 * axis_scores["instinct"]
        + 0.12 * axis_scores["mercy_restoration"]
        + 0.08 * p.get("Moon", 0.0)
        + 0.05 * p.get("Jupiter", 0.0)
        + 0.05 * ((h.get("wild", 0.0) + h.get("meaning", 0.0)) / 2.0)
    )

    # CHA: presence, expression, will made visible
    raw["charisma"] = _clamp01(
        0.32 * axis_scores["social_leadership"]
        + 0.24 * axis_scores["performance"]
        + 0.18 * axis_scores["innate_power"]
        + 0.10 * p.get("Sun", 0.0)
        + 0.08 * p.get("Venus", 0.0)
        + 0.08 * h.get("social", 0.0)
    )

    raw = _rebalance_stat_profile(raw)
    ints = {k: _to_dnd_stat(v, stat_floor, stat_ceiling) for k, v in raw.items()}
    mods = {k: math.floor((value - 10) / 2) for k, value in ints.items()}

    return DnDStatBlock(
        strength_raw=raw["strength"],
        dexterity_raw=raw["dexterity"],
        constitution_raw=raw["constitution"],
        intelligence_raw=raw["intelligence"],
        wisdom_raw=raw["wisdom"],
        charisma_raw=raw["charisma"],
        strength=ints["strength"],
        dexterity=ints["dexterity"],
        constitution=ints["constitution"],
        intelligence=ints["intelligence"],
        wisdom=ints["wisdom"],
        charisma=ints["charisma"],
        modifiers=mods,
    )

    def _to_dnd_stat(raw_score: float, floor: int = 8, ceiling: int = 18) -> int:
    raw_score = _clamp01(raw_score)
    return int(round(floor + raw_score * (ceiling - floor)))

def _rebalance_stat_profile(raw: Mapping[str, float]) -> Dict[str, float]:
    # optional compression so celebrity charts don't all become 16/16/15/15/14/14
    values = {k: _clamp01(v) for k, v in raw.items()}
    mean = sum(values.values()) / max(1, len(values))
    compressed: Dict[str, float] = {}
    for key, value in values.items():
        # pull slightly toward center while preserving rank order
        compressed[key] = _clamp01(0.65 * value + 0.35 * mean)
    return compressed

#So the pipeline should become: chart -> AxisFeatureSet -> axis_scores -> DnDStatBlock -> class_family/class/subclass

#Why these mappings make sense inside your current file

# Your current extractor already divides raw chart material into exactly the buckets you need:

# planet_prominence
# element_balance
# mode_balance
# house_emphasis
# aspect_signals

# And your current axis layer already makes the following semantic distinctions:

# frontline_courage = direct conflict exposure
# stealth_indirection = angle/timing/concealment
# control_planning = board-shaping and sequencing
# mercy_restoration = healing and stabilization
# social_leadership = visible social gravity
# study, technical_inventiveness, faith, nature_attunement, innate_power = power-source logic rather than costume logic

# 1. Do not let one axis own one stat
# Bad:
# INT = study
# CHA = performance
# WIS = faith
# STR = frontline_courage

# 2. Use a playable stat range
# For a PC-facing system, I would use 5–20, not 3–18.
# Reason: 3–18 is flavorful for monsters and peasants; 8–18 is better for “this is a notable character” databases. Otherwise celebrities will produce either insulting stat blocks or cartoonishly jagged ones.

# 3. Keep raw and integer versions
# You want:
# strength_raw for downstream scoring
# strength for display
# modifier for D&D-style output

# That prevents rounding from wrecking class logic.

# 4. How class sorting should use the stat block afterward
# This is the important caveat: do not make classes depend only on stats.

# Use stats as a second layer, something like:

# class families / classes still score mostly from axis_scores
# stats provide bonus/malus nudges and human-readable summary
# subclasses can use stats more directly where appropriate

# Example logic:

# Barbarian likes high STR/CON, but still needs instinct and frontline_courage
# Rogue likes DEX, but still needs stealth_indirection and control_planning
# Wizard likes INT, but still needs study and control_planning
# Cleric likes WIS/CHA depending on domain flavor, but still needs faith and often mercy_restoration
# Paladin wants CHA and STR/CON pressure, but still needs faith, discipline, and frontline_courage

#CONCLUSION:
# Do this in order:
# add DnDStatBlock
# add score_dnd_stats_from_features(axis_scores, features)
# add score_dnd_stats(chart)
# display stat block in UI
# then update class scoring so stats are modifiers, not a new monarchy