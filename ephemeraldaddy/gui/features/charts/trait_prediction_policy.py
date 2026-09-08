"""Optional provenance and gender policies for Chart View Trait Predictions.

These policies stay outside the generic astrology scorer and outside ``app.py``.
They are both opt-in and backward-compatible with Trait files that predate
``chartUIDs`` and ``genderDistribution``.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import ModuleType
from typing import Any

from ephemeraldaddy.analysis.traits import calculate_trait_scores, trait_possible_score
from ephemeraldaddy.core import db
from ephemeraldaddy.core.chart import chart_uses_houses
from ephemeraldaddy.gui.features.charts.similarities.cohort_metadata import chart_uid_is_ascribed
from ephemeraldaddy.gui.settings.core import (
    load_predictions_exclude_ascribed_trait_charts,
    load_predictions_use_trait_gender_distribution,
)

TRAIT_PREDICTION_POLICY_VERSION = 1


def _owner_settings(owner: Any) -> Any | None:
    for attr_name in ("settings", "_settings"):
        settings = getattr(owner, attr_name, None)
        if settings is not None and callable(getattr(settings, "value", None)):
            return settings
    return None


def predictions_exclude_ascribed_enabled(owner: Any) -> bool:
    explicit = getattr(owner, "_predictions_exclude_ascribed_trait_charts", None)
    if explicit is not None:
        return bool(explicit)
    settings = _owner_settings(owner)
    return (
        load_predictions_exclude_ascribed_trait_charts(settings, fallback=False)
        if settings is not None
        else False
    )


def predictions_use_gender_distribution_enabled(owner: Any) -> bool:
    explicit = getattr(owner, "_predictions_use_trait_gender_distribution", None)
    if explicit is not None:
        return bool(explicit)
    settings = _owner_settings(owner)
    return (
        load_predictions_use_trait_gender_distribution(settings, fallback=False)
        if settings is not None
        else False
    )


def _trait_profile(trait: Mapping[str, Any]) -> Mapping[str, Any]:
    profile = trait.get("profile")
    return profile if isinstance(profile, Mapping) else trait


def _normalize_gender(value: Any) -> str:
    return " ".join(str(value or "").split()).casefold()


def _matching_key(mapping: Mapping[Any, Any], normalized_label: str) -> Any | None:
    for key in mapping:
        if _normalize_gender(key) == normalized_label:
            return key
    return None


def gender_evidence_points(profile: Mapping[str, Any], gender: Any) -> float | None:
    """Return significant sample-minus-database gender prevalence in percentage points."""
    normalized_gender = _normalize_gender(gender)
    if not normalized_gender:
        return None
    distribution = profile.get("genderDistribution")
    if not isinstance(distribution, Mapping) or not bool(distribution.get("statisticallySignificant", False)):
        return None
    percentages = distribution.get("percentages")
    database_percentages = distribution.get("databasePercentages")
    if not isinstance(percentages, Mapping) or not isinstance(database_percentages, Mapping):
        return None
    sample_key = _matching_key(percentages, normalized_gender)
    database_key = _matching_key(database_percentages, normalized_gender)
    if sample_key is None or database_key is None:
        return None

    category_significant = False
    significance = distribution.get("significance")
    if isinstance(significance, Mapping):
        significance_key = _matching_key(significance, normalized_gender)
        detail = significance.get(significance_key) if significance_key is not None else None
        if isinstance(detail, Mapping):
            category_significant = bool(detail.get("significant", False))
    if not category_significant:
        categories = distribution.get("significantCategories")
        if isinstance(categories, (list, tuple, set, frozenset)):
            category_significant = any(
                _normalize_gender(value) == normalized_gender for value in categories
            )
    if not category_significant:
        return None
    try:
        return float(percentages[sample_key]) - float(database_percentages[database_key])
    except (TypeError, ValueError):
        return None


def likelihood_from_evidence(
    raw_score: float,
    possible_score: float,
    *,
    gender_delta: float | None = None,
) -> float:
    """Normalize signed evidence, adding gender to numerator and denominator when present."""
    raw = float(raw_score)
    possible = max(float(possible_score), 1.0)
    if gender_delta is not None:
        delta = float(gender_delta)
        raw += delta
        possible += abs(delta)
    normalized = max(-1.0, min(1.0, raw / possible))
    return round(50.0 + (normalized * 50.0), 1)


def calculate_trait_likelihoods_with_gender(
    chart: Any,
    traits: list[dict[str, Any]],
) -> dict[str, float]:
    """Score Traits with statistically significant recorded-gender evidence."""
    active_traits = [trait for trait in traits if not bool(trait.get("archived", False))]
    if chart is None or not active_traits:
        return {}
    raw_scores = calculate_trait_scores(chart, active_traits)
    include_houses = chart_uses_houses(chart)
    chart_gender = getattr(chart, "gender", None)
    likelihoods: dict[str, float] = {}
    for trait in active_traits:
        name = str(trait.get("name", "") or "").strip()
        if not name:
            continue
        profile = _trait_profile(trait)
        likelihoods[name] = likelihood_from_evidence(
            float(raw_scores.get(name, 0.0)),
            trait_possible_score(profile, include_houses=include_houses),
            gender_delta=gender_evidence_points(profile, chart_gender),
        )
    return likelihoods


def _gender_traits_for_chart(chart: Any, traits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gender = getattr(chart, "gender", None)
    if not _normalize_gender(gender):
        return []
    return [
        trait
        for trait in traits
        if gender_evidence_points(_trait_profile(trait), gender) is not None
    ]


def _canonical_chart_uid(chart: Any) -> str:
    return str(getattr(chart, "chart_uid", "") or "").strip().upper()


def ascribed_trait_names_for_chart(chart: Any, traits: list[dict[str, Any]]) -> set[str]:
    """Return Traits whose exported training/ascription cohort contains this UID."""
    chart_uid = _canonical_chart_uid(chart)
    if not chart_uid:
        return set()
    return {
        name
        for trait in traits
        if (name := str(trait.get("name", "") or "").strip())
        and chart_uid_is_ascribed(_trait_profile(trait), chart_uid)
    }


def filter_ascribed_prediction_metadata(
    chart: Any,
    traits: list[dict[str, Any]],
    metadata: Mapping[str, Any],
    *,
    enabled: bool,
) -> dict[str, Any]:
    """Filter ascribed Traits from a display copy, never from persisted analytics."""
    result = dict(metadata)
    if not enabled:
        return result
    excluded = ascribed_trait_names_for_chart(chart, traits)
    if not excluded:
        return result
    for key in ("likelihoods", "database_averages", "deviations"):
        value = result.get(key)
        if isinstance(value, Mapping):
            result[key] = {
                name: item for name, item in value.items() if str(name) not in excluded
            }
    for key in ("above", "below"):
        value = result.get(key)
        if isinstance(value, set):
            result[key] = {name for name in value if str(name) not in excluded}
        elif isinstance(value, (list, tuple)):
            result[key] = [name for name in value if str(name) not in excluded]
    for key in ("stale_trait_names", "unavailable_traits"):
        value = result.get(key)
        if isinstance(value, (list, tuple, set)):
            result[key] = [name for name in value if str(name) not in excluded]
    result["excluded_ascribed_traits"] = sorted(excluded)
    return result


def _gender_profile_payload(traits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for trait in traits:
        distribution = _trait_profile(trait).get("genderDistribution")
        if isinstance(distribution, Mapping) and bool(distribution.get("statisticallySignificant", False)):
            payload.append(
                {
                    "uid": str(trait.get("uid") or trait.get("trait_uid") or "").strip(),
                    "name": str(trait.get("name", "") or "").strip(),
                    "genderDistribution": distribution,
                }
            )
    return payload


def _database_gender_tokens(core: ModuleType, owner: Any) -> tuple[tuple[str, str], ...]:
    try:
        rows = core._database_chart_rows(owner)
    except Exception:
        rows = []
    tokens: set[tuple[str, str]] = set()
    for row in rows:
        try:
            uid = str(row[30] or "").strip().upper() if len(row) > 30 else ""
            gender = _normalize_gender(row[3] if len(row) > 3 else None)
        except (TypeError, IndexError):
            continue
        if uid:
            tokens.add((uid, gender))
    return tuple(sorted(tokens))


def _database_policy_signature(core: ModuleType, owner: Any) -> str:
    try:
        base_norm = core._database_norm_signature_from_state(core._database_norm_state(owner))
    except Exception:
        base_norm = repr(core._database_cache_revision(owner))
    return core._stable_json_hash(
        {
            "baseNorm": base_norm,
            "genderTokens": _database_gender_tokens(core, owner),
        }
    )


def _gender_metadata_cache_key(
    core: ModuleType,
    owner: Any,
    chart: Any,
    traits: list[dict[str, Any]],
) -> str:
    return core._stable_json_hash(
        {
            "policyVersion": TRAIT_PREDICTION_POLICY_VERSION,
            "chartUID": _canonical_chart_uid(chart),
            "chartSignature": core._chart_trait_metadata_signature(chart),
            "chartGender": _normalize_gender(getattr(chart, "gender", None)),
            "traitGenderProfiles": _gender_profile_payload(traits),
            "databasePolicySignature": _database_policy_signature(core, owner),
        }
    )


def _gender_database_averages(
    core: ModuleType,
    owner: Any,
    traits: list[dict[str, Any]],
) -> dict[str, float]:
    """Average gender-aware Traits across persisted charts with recorded gender."""
    if not traits:
        return {}
    cache_key = core._stable_json_hash(
        {
            "policyVersion": TRAIT_PREDICTION_POLICY_VERSION,
            "traits": _gender_profile_payload(traits),
            "databasePolicySignature": _database_policy_signature(core, owner),
        }
    )
    cache = getattr(owner, "_trait_gender_database_averages_cache", None)
    if not isinstance(cache, dict):
        cache = {}
        try:
            owner._trait_gender_database_averages_cache = cache
        except Exception:
            pass
    cached = cache.get(cache_key)
    if isinstance(cached, dict):
        return dict(cached)

    chart_uids = tuple(core._database_chart_uids(owner))
    if not chart_uids:
        return {}
    try:
        charts_by_uid = db.load_charts_by_uids(chart_uids)
    except Exception:
        return {}
    is_placeholder = getattr(owner, "_is_placeholder_chart", None)
    totals = {
        str(trait.get("name", "") or "").strip(): 0.0
        for trait in traits
        if str(trait.get("name", "") or "").strip()
    }
    chart_count = 0
    for raw_uid in chart_uids:
        uid = str(raw_uid or "").strip().upper()
        chart = charts_by_uid.get(uid)
        if chart is None or not _normalize_gender(getattr(chart, "gender", None)):
            continue
        if callable(is_placeholder) and is_placeholder(chart):
            continue
        try:
            likelihoods = calculate_trait_likelihoods_with_gender(chart, traits)
        except Exception:
            continue
        chart_count += 1
        for name in totals:
            totals[name] += float(likelihoods.get(name, 0.0))
    if not chart_count:
        return {}
    averages = {name: total / float(chart_count) for name, total in totals.items()}
    if len(cache) >= 8:
        cache.pop(next(iter(cache)), None)
    cache[cache_key] = dict(averages)
    return averages


def _trait_uids_by_name(core: ModuleType, traits: list[dict[str, Any]]) -> dict[str, str]:
    return {
        name: core._trait_uid_for_item(trait)
        for trait in traits
        if (name := str(trait.get("name", "") or "").strip())
    }


def install_trait_prediction_policy(core: ModuleType) -> None:
    """Install policy wrappers into the preserved Trait Predictions implementation."""
    if bool(getattr(core, "_ephemeraldaddy_trait_prediction_policy_installed", False)):
        return
    original_metadata = core.trait_metadata_for_chart
    original_apply = core._apply_traits_prediction_metadata
    original_cache_key = core._trait_predictions_cache_key

    def policy_metadata_for_chart(
        owner: Any,
        chart: Any,
        *,
        cached_only: bool = False,
        traits: list[dict[str, Any]] | None = None,
        trait_signature: str | None = None,
        legacy_trait_signature: str | None = None,
        norm_signature: str | None = None,
        chart_signature: str | None = None,
    ) -> dict[str, Any] | None:
        resolved_traits = traits if traits is not None else core.list_traits(active_only=True)
        placeholder = getattr(owner, "_is_placeholder_chart", lambda _chart: False)
        if (
            chart is None
            or placeholder(chart)
            or not predictions_use_gender_distribution_enabled(owner)
            or not _normalize_gender(getattr(chart, "gender", None))
        ):
            return original_metadata(
                owner,
                chart,
                cached_only=cached_only,
                traits=resolved_traits,
                trait_signature=trait_signature,
                legacy_trait_signature=legacy_trait_signature,
                norm_signature=norm_signature,
                chart_signature=chart_signature,
            )

        gender_traits = _gender_traits_for_chart(chart, resolved_traits)
        if not gender_traits:
            return original_metadata(
                owner,
                chart,
                cached_only=cached_only,
                traits=resolved_traits,
                trait_signature=trait_signature,
                legacy_trait_signature=legacy_trait_signature,
                norm_signature=norm_signature,
                chart_signature=chart_signature,
            )

        policy_key = _gender_metadata_cache_key(core, owner, chart, resolved_traits)
        cached = getattr(chart, "_trait_gender_prediction_metadata_cache", None)
        if isinstance(cached, dict) and cached.get("signature") == policy_key:
            metadata = cached.get("metadata")
            if isinstance(metadata, dict):
                return dict(metadata)
        if cached_only:
            # The static snapshot is astrology-only. Treat it as unavailable for
            # gender-aware rendering rather than silently showing stale semantics.
            return None

        base_metadata = original_metadata(
            owner,
            chart,
            cached_only=False,
            traits=resolved_traits,
            trait_signature=trait_signature,
            legacy_trait_signature=legacy_trait_signature,
            norm_signature=norm_signature,
            chart_signature=chart_signature,
        )
        if not isinstance(base_metadata, dict):
            return base_metadata

        adjusted_likelihoods = calculate_trait_likelihoods_with_gender(chart, gender_traits)
        adjusted_averages = _gender_database_averages(core, owner, gender_traits)
        applied_names = set(adjusted_likelihoods) & set(adjusted_averages)
        if not applied_names:
            return base_metadata

        likelihoods = dict(base_metadata.get("likelihoods", {}) or {})
        database_averages = dict(base_metadata.get("database_averages", {}) or {})
        for name in applied_names:
            likelihoods[name] = adjusted_likelihoods[name]
            database_averages[name] = adjusted_averages[name]
        metadata = core._metadata_from_vectors(
            likelihoods=likelihoods,
            database_averages=database_averages,
            updated_at=str(base_metadata.get("updated_at", "") or ""),
        )
        for key in ("unavailable_traits", "unavailable_trait_reason"):
            if key in base_metadata:
                metadata[key] = base_metadata[key]
        metadata["gender_criterion_traits"] = sorted(applied_names)
        try:
            chart._trait_gender_prediction_metadata_cache = {
                "signature": policy_key,
                "metadata": dict(metadata),
            }
            core._apply_trait_metadata_to_chart(
                chart,
                metadata,
                _trait_uids_by_name(core, resolved_traits),
                ("gender-policy", policy_key),
            )
        except Exception:
            pass
        return metadata

    def policy_apply_metadata(
        owner: Any,
        traits: list[dict[str, Any]],
        metadata: dict[str, Any],
        *,
        prefix_html: str = "",
    ) -> None:
        filtered = filter_ascribed_prediction_metadata(
            getattr(owner, "_traits_prediction_chart", None),
            traits,
            metadata,
            enabled=predictions_exclude_ascribed_enabled(owner),
        )
        original_apply(owner, traits, filtered, prefix_html=prefix_html)

    def policy_cache_key(
        owner: Any,
        chart: Any | None,
        traits: list[dict[str, Any]],
        *,
        trait_signature: str | None = None,
        trait_display_signature: str | None = None,
        norm_signature: str | None = None,
        chart_signature: str | None = None,
    ) -> str | None:
        base_key = original_cache_key(
            owner,
            chart,
            traits,
            trait_signature=trait_signature,
            trait_display_signature=trait_display_signature,
            norm_signature=norm_signature,
            chart_signature=chart_signature,
        )
        if base_key is None:
            return None
        use_gender = predictions_use_gender_distribution_enabled(owner)
        return core._stable_json_hash(
            {
                "base": base_key,
                "policyVersion": TRAIT_PREDICTION_POLICY_VERSION,
                "excludeAscribed": predictions_exclude_ascribed_enabled(owner),
                "useGenderDistribution": use_gender,
                "chartGender": _normalize_gender(getattr(chart, "gender", None)) if use_gender else "",
                "genderProfiles": _gender_profile_payload(traits) if use_gender else [],
            }
        )

    core.trait_metadata_for_chart = policy_metadata_for_chart
    core._apply_traits_prediction_metadata = policy_apply_metadata
    core._trait_predictions_cache_key = policy_cache_key
    core._ephemeraldaddy_trait_prediction_policy_installed = True
