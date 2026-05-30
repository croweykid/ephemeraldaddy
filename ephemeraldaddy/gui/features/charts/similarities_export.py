"""Pure export helpers for Database View Similarities Analysis."""

from __future__ import annotations

import json
import re
from collections import OrderedDict
from collections.abc import Mapping

from ephemeraldaddy.core.interpretations import PLANET_ORDER, ZODIAC_NAMES
from ephemeraldaddy.gui.features.charts.similarities_db_norm import (
    SIMILARITY_DELTA_SIGNIFICANCE_STANDARD_ERRORS,
    similarity_deviation_z_score,
)

SIMILARITIES_JSON_FACTOR_KEYS: tuple[str, ...] = (
    "signs",
    "antisigns",
    "houses",
    "antihouses",
    "bodies",
    "antibodies",
    "nakshatras",
    "antinakshatras",
    "positions",
    "antipositions",
    "aspects",
    "antiaspects",
    "gates",
    "antigates",
    "channels",
    "antichannels",
    "centers",
    "anticenters",
    "profiles",
    "antiprofiles",
    "authorities",
    "antiauthorities",
    "bazisigns",
    "antibazisigns",
)

SIMILARITIES_JSON_SECTION_CATEGORIES: dict[str, str] = {
    "Signs in positions in common": "positions",
    "Houses in positions in common": "positions",
    "Signs in houses in common": "positions",
    "Top 3 Dominant Signs in common": "signs",
    "Top 3 Dominant Bodies in common": "bodies",
    "Top 3 Dominant Houses in common": "houses",
    "Dominant nakshatras in common": "nakshatras",
    "Aspects in common": "aspects",
    "Gates in common": "gates",
    "Channels in common": "channels",
    "Defined Centers in common": "centers",
    "Authorities in common": "authorities",
    "Profiles in common": "profiles",
    "BaZi signs in common": "bazisigns",
    "Signs in positions in contrast": "antipositions",
    "Houses in positions in contrast": "antipositions",
    "Signs in houses in contrast": "antipositions",
    "Top 3 Dominant Signs in contrast": "antisigns",
    "Top 3 Dominant Bodies in contrast": "antibodies",
    "Top 3 Dominant Houses in contrast": "antihouses",
    "Dominant nakshatras in contrast": "antinakshatras",
    "Aspects in contrast": "antiaspects",
    "Gates in contrast": "antigates",
    "Channels in contrast": "antichannels",
    "Defined Centers in contrast": "anticenters",
    "Authorities in contrast": "antiauthorities",
    "Profiles in contrast": "antiprofiles",
    "BaZi signs in contrast": "antibazisigns",
}


DISSIMILARITIES_JSON_OWNER_LABELS: dict[str, str] = {
    "chart_1": "chart 1 unique factors",
    "chart_2": "chart 2 unique factors",
}
DISSIMILARITIES_JSON_ANTI_TO_UNIQUE_CATEGORIES: dict[str, str] = {
    "antisigns": "signs",
    "antihouses": "houses",
    "antibodies": "bodies",
    "antinakshatras": "nakshatras",
    "antipositions": "positions",
    "antiaspects": "aspects",
    "antigates": "gates",
    "antichannels": "channels",
    "anticenters": "centers",
    "antiprofiles": "profiles",
    "antiauthorities": "authorities",
    "antibazisigns": "bazisigns",
}

SIMILARITIES_JSON_PRIMARY_POSITION_BODIES: tuple[str, ...] = (
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
    "Chiron",
    "Ceres",
    "Pallas",
    "Juno",
    "Vesta",
    "Lilith",
    "Rahu",
    "Ketu",
    "Part of Fortune",
)
SIMILARITIES_JSON_PRIMARY_POSITION_BODY_SET = set(SIMILARITIES_JSON_PRIMARY_POSITION_BODIES)
SIMILARITIES_JSON_POSITION_BODY_ORDER: tuple[str, ...] = (
    *SIMILARITIES_JSON_PRIMARY_POSITION_BODIES,
    *(body for body in PLANET_ORDER if body not in SIMILARITIES_JSON_PRIMARY_POSITION_BODY_SET),
    *ZODIAC_NAMES,
)
SIMILARITIES_JSON_POSITION_BODY_INDEX = {
    body: index for index, body in enumerate(SIMILARITIES_JSON_POSITION_BODY_ORDER)
}
SIMILARITIES_MIN_PERCENT_DIFFERENCE = 3.0
SIMILARITIES_EXCLUDED_BODIES_PATTERN = re.compile(r"\b(Ketu|DS|IC)\b")


def similarities_label_has_excluded_bodies(label: object) -> bool:
    """Return True when a label includes a mirrored factor that should be omitted."""
    text = str(label or "")
    if not text:
        return False
    return bool(SIMILARITIES_EXCLUDED_BODIES_PATTERN.search(text))


def similarities_match_clears_delta_threshold(
    match_count: int,
    total_count: int,
    database_match_count: int,
    database_total_count: int,
    *,
    threshold: float = SIMILARITIES_MIN_PERCENT_DIFFERENCE,
) -> bool:
    """Return True when selection-vs-database percent delta is at least threshold."""
    selection_percent = ((match_count / total_count) * 100.0) if total_count else 0.0
    database_percent = (
        ((database_match_count / database_total_count) * 100.0)
        if database_total_count
        else 0.0
    )
    return abs(selection_percent - database_percent) >= threshold


def empty_similarities_json_profile(selection_name: str) -> OrderedDict:
    """Build the skeleton profile used by Similarities Analysis JSON exports."""
    profile = OrderedDict([("name", selection_name)])
    for key in SIMILARITIES_JSON_FACTOR_KEYS:
        profile[key] = OrderedDict()
    profile["color"] = "#cc99ff"
    profile["motivation"] = ""
    profile["description"] = ""
    profile["quotes"] = OrderedDict()
    return profile


def similarities_json_category_for_section(
    section_title: str,
    percent_difference: float,
) -> str | None:
    """Return the JSON bucket for a Similarities Analysis section.

    Similarities exports keep both over- and under-represented factors in the
    positive factor category. Under-represented factors carry a negative weight,
    leaving ``anti*`` buckets available for manually curated antithetical traits.
    """
    _ = percent_difference
    return SIMILARITIES_JSON_SECTION_CATEGORIES.get(section_title)


def normalize_similarities_json_criterion(
    section_title: str,
    label: object,
) -> str | int | tuple[int, int] | None:
    """Convert UI labels into criterion strings consumed by profile scoring."""
    text = str(label).strip()
    if not text:
        return None

    if section_title in {"Houses in positions in common", "Houses in positions in contrast"}:
        if ": House " not in text:
            return None
        body, house_text = text.split(": House ", 1)
        house_num = house_text.strip()
        if not house_num.isdigit():
            return None
        return f"{body.strip()} in H{int(house_num)}"

    if section_title in {"Signs in houses in common", "Signs in houses in contrast"}:
        if not text.startswith("House ") or ": " not in text:
            return None
        house_text, sign = text.split(": ", 1)
        house_num = house_text.replace("House ", "", 1).strip()
        if not house_num.isdigit():
            return None
        return f"{sign.strip()} in H{int(house_num)}"

    if section_title in {"Top 3 Dominant Houses in common", "Top 3 Dominant Houses in contrast"}:
        if not text.startswith("House "):
            return None
        house_num = text.replace("House ", "", 1).strip()
        if not house_num.isdigit():
            return None
        return str(int(house_num))

    if section_title in {"Gates in common", "Gates in contrast"}:
        if not text.startswith("Gate "):
            return None
        gate_num = text.replace("Gate ", "", 1).strip()
        if not gate_num.isdigit():
            return None
        return int(gate_num)

    if section_title in {"Channels in common", "Channels in contrast"}:
        normalized = _normalize_channel_criterion(text)
        if normalized is None:
            return None
        return normalized

    return text


def _normalize_channel_criterion(text: str) -> tuple[int, int] | None:
    """Convert a channel label into a canonical two-gate tuple."""
    match = re.fullmatch(r"\s*(\d{1,2})\s*[-/,]\s*(\d{1,2})\s*", text)
    if not match:
        return None
    gate_a, gate_b = (int(value) for value in match.groups())
    if not (1 <= gate_a <= 64 and 1 <= gate_b <= 64 and gate_a != gate_b):
        return None
    return (min(gate_a, gate_b), max(gate_a, gate_b))


def similarity_delta_exceeds_export_standard_deviation_tier(
    selection_percent: float,
    database_percent: float,
    total_count: int,
) -> bool:
    """Return True when a factor lies beyond the second standard-error tier."""
    percent_difference = selection_percent - database_percent
    if percent_difference == 0.0:
        return False
    z_score = similarity_deviation_z_score(selection_percent, database_percent, total_count)
    if z_score is not None:
        return abs(z_score) > SIMILARITY_DELTA_SIGNIFICANCE_STANDARD_ERRORS
    return database_percent in {0.0, 100.0}


def _split_position_criterion(criterion: str) -> tuple[str, str]:
    body, separator, placement = criterion.partition(" in ")
    if not separator:
        return criterion, ""
    return body, placement


def _placement_sort_key(placement: str) -> tuple[int, int | str]:
    if placement.startswith("H") and placement[1:].isdigit():
        return (1, int(placement[1:]))
    zodiac_index = {sign: index for index, sign in enumerate(ZODIAC_NAMES)}.get(placement)
    if zodiac_index is not None:
        return (0, zodiac_index)
    return (2, placement.casefold())


def _position_sort_key(item: tuple[str, int]) -> tuple[int, str, tuple[int, int | str], str]:
    criterion, _weight = item
    body, placement = _split_position_criterion(criterion)
    body_index = SIMILARITIES_JSON_POSITION_BODY_INDEX.get(body)
    return (
        body_index if body_index is not None else len(SIMILARITIES_JSON_POSITION_BODY_ORDER),
        body.casefold(),
        _placement_sort_key(placement),
        criterion.casefold(),
    )


def sort_similarities_json_positions(profile: OrderedDict) -> None:
    """Sort exported position factors by body/planet order for readability."""
    positions = profile.get("positions")
    if isinstance(positions, OrderedDict):
        profile["positions"] = OrderedDict(sorted(positions.items(), key=_position_sort_key))


def _similarities_json_match_owner(match: tuple[object, ...]) -> str:
    return str(match[6]) if len(match) > 6 else ""


def _has_dissimilarity_json_owner(export_sections) -> bool:
    return any(
        str(section_title).endswith(" in contrast")
        and any(_similarities_json_match_owner(tuple(match)) in DISSIMILARITIES_JSON_OWNER_LABELS for match in matches)
        for section_title, matches in export_sections
    )


def _add_similarity_json_match_to_profile(
    profile: OrderedDict,
    section_title: str,
    match: tuple[object, ...],
    *,
    use_unique_factor_categories: bool = False,
    require_database_significance: bool = True,
) -> None:
    """Add one export factor, optionally gating cohort exports by DB significance.

    Multi-chart similarity exports use a database standard-error gate to avoid
    treating small cohort fluctuations as reusable profile factors. Two-chart
    dissimilarity exports are descriptive owner-unique contrasts (n=2), so their
    JSON bundle intentionally preserves every chart-unique factor and only uses
    the database percentage to set the exported weight.
    """
    if len(match) < 6:
        return
    label, match_count, total_count, database_match_count, database_total_count, _matching_chart_names = match[:6]
    match_count = int(match_count)
    total_count = int(total_count)
    database_match_count = int(database_match_count)
    database_total_count = int(database_total_count)
    selection_percent = (match_count / total_count) * 100 if total_count else 0.0
    database_percent = (
        (database_match_count / database_total_count) * 100
        if database_total_count
        else 0.0
    )
    percent_difference = selection_percent - database_percent
    if require_database_significance and not similarity_delta_exceeds_export_standard_deviation_tier(
        selection_percent,
        database_percent,
        total_count,
    ):
        return
    category = similarities_json_category_for_section(
        section_title,
        percent_difference,
    )
    if category is None:
        return
    if use_unique_factor_categories:
        category = DISSIMILARITIES_JSON_ANTI_TO_UNIQUE_CATEGORIES.get(category, category)
    ratio = int(round(percent_difference))
    if ratio == 0:
        return
    criterion = normalize_similarities_json_criterion(section_title, label)
    if criterion is None:
        return
    profile[category][criterion] = ratio


def build_similarities_json_export_payload(
    selection_name: str,
    export_sections,
) -> OrderedDict:
    """Build profile-shaped JSON data for Similarities Analysis export sections.

    ``export_sections`` is the same data shape used by the CSV exporter: an
    iterable of ``(section_title, matches)`` entries whose matches contain
    label, selection count/total, database count/total, matching names, and
    optionally a dissimilarity owner key (``chart_1`` or ``chart_2``).
    """
    if _has_dissimilarity_json_owner(export_sections):
        bundle = OrderedDict([("name", selection_name)])
        for owner_key in ("chart_1", "chart_2"):
            bundle[DISSIMILARITIES_JSON_OWNER_LABELS[owner_key]] = empty_similarities_json_profile(
                DISSIMILARITIES_JSON_OWNER_LABELS[owner_key]
            )
        for section_title, matches in export_sections:
            if not matches:
                continue
            for raw_match in matches:
                match = tuple(raw_match)
                owner_label = DISSIMILARITIES_JSON_OWNER_LABELS.get(_similarities_json_match_owner(match))
                if owner_label is None:
                    continue
                _add_similarity_json_match_to_profile(
                    bundle[owner_label],
                    section_title,
                    match,
                    use_unique_factor_categories=True,
                    require_database_significance=False,
                )
        for owner_label in DISSIMILARITIES_JSON_OWNER_LABELS.values():
            sort_similarities_json_positions(bundle[owner_label])
        return OrderedDict([(selection_name, bundle)])

    profile = empty_similarities_json_profile(selection_name)
    for section_title, matches in export_sections:
        if not matches:
            continue
        for raw_match in matches:
            _add_similarity_json_match_to_profile(profile, section_title, tuple(raw_match))
    sort_similarities_json_positions(profile)
    return OrderedDict([(selection_name, profile)])


def _format_similarities_export_key(key: object) -> str:
    if isinstance(key, int):
        return str(key)
    if isinstance(key, tuple) and len(key) == 2:
        gate_a, gate_b = key
        return f"({gate_a}, {gate_b})"
    return json.dumps(str(key), ensure_ascii=False)


def _format_similarities_export_value(value: object, *, indent: int = 0) -> str:
    if isinstance(value, Mapping):
        if not value:
            return "{}"
        next_indent = indent + 4
        lines = ["{"]
        for key, child in value.items():
            formatted_key = _format_similarities_export_key(key)
            formatted_child = _format_similarities_export_value(child, indent=next_indent)
            lines.append(f"{' ' * next_indent}{formatted_key}: {formatted_child},")
        lines.append(f"{' ' * indent}}}")
        return "\n".join(lines)
    if isinstance(value, tuple):
        tuple_items = ", ".join(
            _format_similarities_export_value(item, indent=indent) for item in value
        )
        return f"({tuple_items})"
    return json.dumps(value, ensure_ascii=False)


def format_similarities_json_export_payload(payload: OrderedDict) -> str:
    """Format Similarities Analysis exports as profile-compatible Python literals.

    The consuming profile definitions use integer gate keys and tuple channel
    keys. Standard JSON cannot represent those key types, so this formatter keeps
    the historical JSON-style double-quoted strings while preserving numeric and
    tuple keys for direct profile reuse.
    """
    return f"{_format_similarities_export_value(payload, indent=0)}\n"


def _similarities_json_profile_has_factors(profile: Mapping) -> bool:
    return any(bool(profile.get(key)) for key in SIMILARITIES_JSON_FACTOR_KEYS)


def similarities_json_payload_has_factors(payload: OrderedDict, selection_name: str) -> bool:
    """Return True when a Similarities Analysis JSON payload has exportable factors."""
    profile = payload.get(selection_name)
    if not isinstance(profile, dict):
        return False
    if _similarities_json_profile_has_factors(profile):
        return True
    return any(
        isinstance(profile.get(owner_label), Mapping)
        and _similarities_json_profile_has_factors(profile[owner_label])
        for owner_label in DISSIMILARITIES_JSON_OWNER_LABELS.values()
    )
