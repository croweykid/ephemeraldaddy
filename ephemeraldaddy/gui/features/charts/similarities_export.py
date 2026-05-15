"""Pure export helpers for Database View Similarities Analysis."""

from __future__ import annotations

from collections import OrderedDict

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
}


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
    """Return the JSON bucket for a Similarities Analysis section and delta."""
    category = SIMILARITIES_JSON_SECTION_CATEGORIES.get(section_title)
    if category is None:
        return None
    if percent_difference < 0:
        return f"anti{category}"
    return category


def normalize_similarities_json_criterion(section_title: str, label: object) -> str | None:
    """Convert UI labels into criterion strings consumed by profile scoring."""
    text = str(label).strip()
    if not text:
        return None

    if section_title == "Houses in positions in common":
        if ": House " not in text:
            return None
        body, house_text = text.split(": House ", 1)
        house_num = house_text.strip()
        if not house_num.isdigit():
            return None
        return f"{body.strip()} in H{int(house_num)}"

    if section_title == "Signs in houses in common":
        if not text.startswith("House ") or ": " not in text:
            return None
        house_text, sign = text.split(": ", 1)
        house_num = house_text.replace("House ", "", 1).strip()
        if not house_num.isdigit():
            return None
        return f"{sign.strip()} in H{int(house_num)}"

    if section_title == "Top 3 Dominant Houses in common":
        if not text.startswith("House "):
            return None
        house_num = text.replace("House ", "", 1).strip()
        if not house_num.isdigit():
            return None
        return str(int(house_num))

    if section_title == "Gates in common":
        if not text.startswith("Gate "):
            return None
        gate_num = text.replace("Gate ", "", 1).strip()
        if not gate_num.isdigit():
            return None
        return str(int(gate_num))

    return text


def build_similarities_json_export_payload(
    selection_name: str,
    export_sections,
) -> OrderedDict:
    """Build profile-shaped JSON data for Similarities Analysis export sections.

    ``export_sections`` is the same data shape used by the CSV exporter: an
    iterable of ``(section_title, matches)`` entries whose matches contain
    label, selection count/total, database count/total, and matching names.
    """
    profile = empty_similarities_json_profile(selection_name)
    for section_title, matches in export_sections:
        if not matches:
            continue
        for (
            label,
            match_count,
            total_count,
            database_match_count,
            database_total_count,
            _matching_chart_names,
        ) in matches:
            selection_percent = (match_count / total_count) * 100 if total_count else 0.0
            database_percent = (
                (database_match_count / database_total_count) * 100
                if database_total_count
                else 0.0
            )
            percent_difference = selection_percent - database_percent
            if abs(percent_difference) <= 3.0:
                continue
            category = similarities_json_category_for_section(
                section_title,
                percent_difference,
            )
            if category is None:
                continue
            ratio = int(round(abs(percent_difference)))
            if ratio <= 0:
                continue
            criterion = normalize_similarities_json_criterion(section_title, label)
            if criterion is None:
                continue
            profile[category][criterion] = ratio
    return OrderedDict([(selection_name, profile)])


def similarities_json_payload_has_factors(payload: OrderedDict, selection_name: str) -> bool:
    """Return True when a Similarities Analysis JSON payload has exportable factors."""
    profile = payload.get(selection_name)
    if not isinstance(profile, dict):
        return False
    return any(bool(profile.get(key)) for key in SIMILARITIES_JSON_FACTOR_KEYS)
