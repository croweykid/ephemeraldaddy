"""Pure text models for Chart Information keyword drill-downs."""

from __future__ import annotations

from dataclasses import dataclass
import math

from ephemeraldaddy.core.decans import ZODIAC_DECANS
from ephemeraldaddy.core.house_definitions import HOUSE_DEFINITIONS
from ephemeraldaddy.core.interpretations import (
    ASPECT_KEYWORDS,
    GRECOROMAN_ELEMENTS,
    MODE_KEYWORDS,
    MODES,
    PLANET_DETRIMENT,
    PLANET_EXALTATION,
    PLANET_FALL,
    PLANET_KEYWORDS,
    PLANET_RULERSHIP,
    PLANETARY_JOYS,
)
from ephemeraldaddy.gui.features.chart_information.token_formatting import (
    ordinal_house_header,
)


@dataclass(frozen=True, slots=True)
class DecanInformationModel:
    """Resolved, display-ready data for one zodiac decan."""

    sign_name: str
    decan_number: int
    ordinal_label: str
    subsign_ruler: str
    description: str
    keywords: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ModeKeywordModel:
    """Normalized mode label and its semantic keyword collections."""

    key: str
    label: str
    keywords: tuple[str, ...]
    signs: tuple[str, ...]

    @property
    def has_reference_data(self) -> bool:
        return self.key in {"cardinal", "mutable", "fixed"} and bool(
            self.keywords or self.signs
        )


def build_decan_information(
    sign_name: str, longitude: object | None
) -> DecanInformationModel | None:
    """Resolve decan reference data without depending on a Chart Editor window."""
    try:
        longitude_value = float(longitude) if longitude is not None else None
    except (TypeError, ValueError):
        longitude_value = None
    if longitude_value is None or not math.isfinite(longitude_value):
        return None

    sign_key = str(sign_name or "").strip().title()
    decan_number = min(3, max(1, int((longitude_value % 30.0) // 10.0) + 1))
    selected_decan = next(
        (
            entry
            for entry in ZODIAC_DECANS.get(sign_key, [])
            if int(entry.get("decan", 0)) == decan_number
        ),
        {},
    )
    return DecanInformationModel(
        sign_name=sign_key,
        decan_number=decan_number,
        ordinal_label=("1st", "2nd", "3rd")[decan_number - 1],
        subsign_ruler=str(selected_decan.get("subsign_ruler", "")).strip() or "Unknown",
        description=str(selected_decan.get("description", "")).strip(),
        keywords=tuple(
            str(keyword).strip()
            for keyword in selected_decan.get("keywords", [])
            if str(keyword).strip()
        ),
    )


def build_mode_keyword_model(mode: str) -> ModeKeywordModel:
    """Normalize one astrological mode into immutable presentation data."""
    mode_key = str(mode or "").strip().lower()
    return ModeKeywordModel(
        key=mode_key,
        label=mode_key.title() if mode_key else "Mode",
        keywords=tuple(
            sorted(
                str(keyword).strip()
                for keyword in MODE_KEYWORDS.get(mode_key, set())
                if str(keyword).strip()
            )
        ),
        signs=tuple(
            sorted(
                str(sign).strip()
                for sign in MODES.get(mode_key, set())
                if str(sign).strip()
            )
        ),
    )


def build_element_definition_lines(element: str) -> list[str]:
    """Build reusable plain-text lines for a classical element definition."""
    element_key = str(element or "").strip().lower()
    data = GRECOROMAN_ELEMENTS.get(element_key, {})
    element_label = str(data.get("name") or element or "Element").strip().title()
    if not data:
        return [element_label, "", "No element definition data available."]

    lines = [element_label]
    greek = str(data.get("greek", "")).strip()
    if greek:
        lines.append(f"Greek: {greek}")
    qualities = [str(item).strip() for item in data.get("qualities", []) if str(item).strip()]
    if qualities:
        lines.append(f"Qualities: {', '.join(qualities)}")
    signs = [str(item).strip() for item in data.get("signs", []) if str(item).strip()]
    if signs:
        lines.append(f"Signs: {', '.join(signs)}")
    for label, key in (
        ("Polarity", "polarity"),
        ("Temperament", "temperament"),
        ("Core function", "core_function"),
        ("Basic function", "basic_function"),
        ("Core meaning", "core_meaning"),
        ("Use", "use"),
        ("Object", "object"),
        ("Suit", "suit"),
        ("Suit function", "suit_function"),
        ("Suit style", "suit_style"),
        ("Basic style", "basic_style"),
    ):
        value = str(data.get(key, "")).strip()
        if value:
            lines.append(f"{label}: {value}")
    for label, key in (
        ("Strengths", "strengths"),
        ("Challenges", "challenges"),
        ("Distortions", "distortions"),
        ("Needs", "needs"),
        ("Fears", "fears"),
        ("Verbs", "verbs"),
    ):
        items = [str(item).strip() for item in data.get(key, []) if str(item).strip()]
        if items:
            lines.extend(["", f"{label}:", *(f"• {item}" for item in items)])
    return lines


def build_planet_keyword_text(
    body: str,
    *,
    display_body: str,
    sign_name: str = "",
    house_number: int | None = None,
    chart_uses_houses: bool = False,
) -> str:
    """Build planet keyword copy from already-resolved chart context.

    ``chart_uses_houses`` is deliberately explicit: callers must not infer a
    planetary joy from unreliable unknown or unaccepted rectified birth time.
    """
    body_name = str(body or "").strip()
    label = str(display_body or "").strip() or body_name
    verbs = PLANET_KEYWORDS.get(body_name, {}).get("verbs", [])
    clean_verbs = [str(item).strip() for item in verbs if str(item).strip()]
    if not clean_verbs:
        return f"{label}\n\nNo verb keywords available."

    resolved_sign = str(sign_name or "").strip().title()
    status_line = ""
    exaltation = PLANET_EXALTATION.get(body_name, {})
    fall = PLANET_FALL.get(body_name, {})
    if (
        resolved_sign
        and exaltation
        and resolved_sign == str(exaltation.get("sign", "")).strip().title()
    ):
        status_line = f"Exalted in {resolved_sign}."
    elif resolved_sign and resolved_sign in PLANET_RULERSHIP.get(body_name, set()):
        status_line = f"Ruler of {resolved_sign}."
    elif resolved_sign and resolved_sign in PLANET_DETRIMENT.get(body_name, set()):
        status_line = f"Detriment in {resolved_sign}."
    elif (
        resolved_sign
        and fall
        and resolved_sign == str(fall.get("sign", "")).strip().title()
    ):
        status_line = f"Fall in {resolved_sign}."
    elif chart_uses_houses:
        joy_houses = PLANETARY_JOYS.get(body_name, set())
        if isinstance(joy_houses, int):
            joy_houses = {joy_houses}
        if house_number in joy_houses:
            status_line = f"With joy in house {house_number}."

    lines = [f"• {keyword}" for keyword in clean_verbs]
    if status_line:
        return "\n".join([label, status_line, "", *lines])
    return "\n".join([label, "", *lines])


def build_aspect_keyword_text(aspect_type: str) -> str:
    """Build the plain-text keyword drill-down for an aspect type."""
    aspect_label = str(aspect_type or "").strip()
    aspect_key = aspect_label.replace(" ", "_").lower()
    keywords = ASPECT_KEYWORDS.get(aspect_key, [])
    clean_keywords = [str(item).strip() for item in keywords if str(item).strip()]
    header = f"{aspect_label or 'Aspect'} keywords"
    if not clean_keywords:
        return f"{header}\n\nNo keyword data available."
    return "\n".join([header, "", *(f"• {keyword}" for keyword in clean_keywords)])


def build_house_keyword_text(house_number: int, *, joy_body: str = "") -> str:
    """Build the plain-text keyword drill-down for an astrological house."""
    keywords = HOUSE_DEFINITIONS.get(house_number, {}).get("core_domains", [])
    clean_keywords = [str(item).strip() for item in keywords if str(item).strip()]
    header = ordinal_house_header(house_number)
    clean_joy_body = str(joy_body or "").strip()
    if clean_joy_body:
        header = f"{header} (planetary joy in {clean_joy_body})"
    if not clean_keywords:
        return f"{header}\n\nNo house keywords available."
    return "\n".join([header, "", *(f"• {keyword}" for keyword in clean_keywords)])
