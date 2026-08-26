"""Authoritative separation between calculation data, metadata, and chart status.

``ASTRO_DATA`` contains chart inputs and derived outputs belonging to astronomical,
astrological, Human Design, or BaZi calculation. Only changes to
``ASTRO_DATA_INPUT_FIELDS`` may trigger those calculations.

``NONASTRAL_DATA`` is descriptive/user metadata and must never trigger
astrology-derived calculations, Trait score invalidation, Trait ranking updates,
or Trait-panel refreshes.

``CHART_INFO_STATUS`` contains chart state that controls whether/how a chart is
eligible for UI result populations. Status changes may alter membership in a
ranking or result set, but do not make the chart's astrology or Trait scores
numerically stale.
"""

from __future__ import annotations

import logging
from typing import Any, TypedDict


logger = logging.getLogger(__name__)

ASTRO_DATA_CATEGORY = "astro_data"
NONASTRAL_DATA_CATEGORY = "nonastral_data"
CHART_INFO_STATUS_CATEGORY = "chart_info_status"


class NonastralPatch(TypedDict, total=False):
    """Typed payload accepted by the general non-astro persistence path.

    The historical name is retained for compatibility. Some fields below are
    now semantically ``CHART_INFO_STATUS`` rather than ``NONASTRAL_DATA``; both
    categories are safe for narrow persistence because neither permits
    astrology recalculation.
    """

    name: str
    alias: str | None
    from_whence: str | None
    gender: str | None
    sentiments: list[str]
    relationship_types: list[str]
    tags: list[str]
    reminds_me_of: str
    comments: str
    emoji_portrait: str
    enneagram_type: list[str]
    tritype: list[int]
    mbti: list[str]
    quotes: list[str]
    rectification_notes: str
    biography: str
    chart_data_source: str
    alternate_chart_uid: str | None
    positive_sentiment_intensity: int | None
    negative_sentiment_intensity: int | None
    familiarity: int | None
    alignment_score: int | None
    sexiness_score: int
    matched_expectations: int
    familiarity_factors: list[str]
    age_when_first_met: int
    year_first_encountered: int | None
    current_relationship: bool
    last_encounter: int | None
    data_rating: str
    social_score: int
    chart_type: str
    source: str
    is_placeholder: bool
    is_deceased: bool
    profile_pic: str | None


ASTRO_DATA_INPUT_FIELDS = frozenset(
    {
        "datetime_iso",
        "dt",
        "dt_local",
        "birth_place",
        "tz_name",
        "lat",
        "lon",
        "used_utc_fallback",
        "birth_month",
        "birth_day",
        "birth_year",
        "birthtime_unknown",
        "retcon_time_used",
        "retcon_hour",
        "retcon_minute",
        "rectification_range_used",
        "rectification_range_start_minute",
        "rectification_range_end_minute",
        "chart_uses_houses",
        "use_birth_time_data",
        "death_month",
        "death_day",
        "death_year",
        "deathtime_unknown",
        "death_hour",
        "death_minute",
        "death_place",
        "lilith_calculation_mode",
    }
)

ASTRO_DATA_DERIVED_FIELDS = frozenset(
    {
        "positions",
        "retrogrades",
        "houses",
        "housesPo",
        "aspects",
        "signs_unknown",
        "unknown_signs",
        "dominant_sign_weights",
        "dominant_planet_weights",
        "dominant_nakshatra_weights",
        "dominant_element_weights",
        "dominant_mode",
        "modal_distribution",
        "body_dynamics_roles",
        "human_design_gates",
        "human_design_lines",
        "human_design_channels",
        "human_design_defined_centers",
        "human_design_type",
        "human_design_authority",
        "bazi_year_pillar",
        "bazi_month_pillar",
        "bazi_day_pillar",
        "bazi_hour_pillar",
        "bazi_year_element",
        "bazi_month_element",
        "bazi_day_element",
        "bazi_hour_element",
        "derived_birth_data_signature",
        "derived_positions",
        "derived_retrogrades",
        "derived_houses",
        "derived_houses_po",
        "derived_aspects",
        "enneagram_type_weights",
        "dominant_enneagram_type",
        "top_three_enneagram_types",
        "weirdness_score",
        "weirdness_formula_version",
        "weirdness_norm_signature",
    }
)

ASTRO_DATA = ASTRO_DATA_INPUT_FIELDS | ASTRO_DATA_DERIVED_FIELDS

# Result-population / UI eligibility state. ``chart_type`` and ``source`` are
# included because hypothetical status is currently encoded through chart type;
# ``is_hidden``/``is_hypothetical`` are accepted synthetic event names even
# where they are not persisted as literal chart-table columns.
CHART_INFO_STATUS = frozenset(
    {
        "chart_type",
        "source",
        "is_placeholder",
        "is_hidden",
        "is_hypothetical",
    }
)

NONASTRAL_DATA = frozenset(
    {
        "chart_uid",
        "id",
        "name",
        "alias",
        "from_whence",
        "gender",
        "sentiments",
        "relationship_types",
        "tags",
        "reminds_me_of",
        "comments",
        "emoji_portrait",
        "enneagram_type",
        "tritype",
        "mbti",
        "quotes",
        "rectification_notes",
        "biography",
        "chart_data_source",
        "alternate_chart_uid",
        "positive_sentiment_intensity",
        "negative_sentiment_intensity",
        "familiarity",
        "alignment_score",
        "sexiness_score",
        "matched_expectations",
        "familiarity_factors",
        "age_when_first_met",
        "year_first_encountered",
        "current_relationship",
        "last_encounter",
        "data_rating",
        "social_score",
        "is_deceased",
        "traits",
        "traits_above_average",
        "traits_below_average",
        "trait_likelihoods",
        "predicted_traits_above_avg",
        "predicted_traits_below_avg",
        "predicted_trait_deviations",
        "profile_pic",
        "created_at",
        "is_current",
    }
)

if ASTRO_DATA & NONASTRAL_DATA:
    raise RuntimeError("Chart fields cannot be both ASTRO_DATA and NONASTRAL_DATA")
if ASTRO_DATA & CHART_INFO_STATUS:
    raise RuntimeError("Chart fields cannot be both ASTRO_DATA and CHART_INFO_STATUS")
if NONASTRAL_DATA & CHART_INFO_STATUS:
    raise RuntimeError("Chart fields cannot be both NONASTRAL_DATA and CHART_INFO_STATUS")

# Both categories are non-astro persistence fields. This union exists so legacy
# narrow-write APIs can remain safe while call sites migrate away from treating
# chart status as ordinary descriptive metadata.
NONASTRO_DATA = NONASTRAL_DATA | CHART_INFO_STATUS


def chart_data_category(field: str) -> str | None:
    """Return the authoritative semantic category for a chart field/event name."""
    normalized = str(field or "")
    if normalized in ASTRO_DATA:
        return ASTRO_DATA_CATEGORY
    if normalized in CHART_INFO_STATUS:
        return CHART_INFO_STATUS_CATEGORY
    if normalized in NONASTRAL_DATA:
        return NONASTRAL_DATA_CATEGORY
    return None


def is_astro_data_input(field: str) -> bool:
    """Return whether changing ``field`` is allowed to trigger recalculation."""
    return str(field) in ASTRO_DATA_INPUT_FIELDS


def require_nonastro_data_fields(fields: str | set[str] | frozenset[str]) -> None:
    """Reject a narrow persistence write unless every field is non-astro data."""
    requested = {fields} if isinstance(fields, str) else set(fields)
    invalid = requested - NONASTRO_DATA
    if invalid:
        invalid_text = ", ".join(sorted(invalid))
        logger.error(
            "Refusing a narrow non-astro save for unclassified or ASTRO_DATA "
            "field(s): %s. Classify new persisted fields in chart_data_fields.py; "
            "route ASTRO_DATA inputs through the Chart View calculation path, or "
            "classify descriptive metadata/status appropriately.",
            invalid_text,
        )
        raise ValueError(
            "Narrow non-astro update received unclassified/ASTRO_DATA fields: "
            + invalid_text
        )


def require_nonastral_data_fields(fields: str | set[str] | frozenset[str]) -> None:
    """Compatibility alias for the historical narrow non-astro write validator.

    Despite the legacy function name, chart-info-status fields are intentionally
    accepted here. Narrow persistence of status is safe; status must simply be
    dispatched as membership/UI invalidation rather than Trait score invalidation.
    """
    require_nonastro_data_fields(fields)


def astro_data_recalculation_token(
    chart: Any | None,
    *,
    birth_place: str | None = None,
    chart_uses_houses_value: bool | None = None,
) -> tuple[Any, ...]:
    """Return the canonical token for the ASTRO_DATA inputs of a chart."""
    if chart is None:
        return ()
    dt_value = getattr(chart, "dt", None)
    retcon_hour = getattr(chart, "retcon_hour", None)
    retcon_minute = getattr(chart, "retcon_minute", None)
    return (
        dt_value.isoformat() if dt_value is not None else None,
        (
            birth_place
            if birth_place is not None
            else getattr(chart, "birth_place", None) or ""
        ),
        round(float(getattr(chart, "lat", 0.0) or 0.0), 6),
        round(float(getattr(chart, "lon", 0.0) or 0.0), 6),
        bool(getattr(chart, "birthtime_unknown", False)),
        bool(getattr(chart, "retcon_time_used", False)),
        (
            (int(retcon_hour), int(retcon_minute))
            if retcon_hour is not None and retcon_minute is not None
            else None
        ),
        (
            bool(getattr(chart, "rectification_range_used", False)),
            getattr(chart, "rectification_range_start_minute", None),
            getattr(chart, "rectification_range_end_minute", None),
        ),
        bool(
            chart_uses_houses_value
            if chart_uses_houses_value is not None
            else getattr(chart, "use_birth_time_data", False)
        ),
    )
