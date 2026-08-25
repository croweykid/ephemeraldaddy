"""Versioned schemas and distribution helpers for static prediction norms.

This module is intentionally GUI- and database-free. Runtime readers may keep
supporting the legacy v1 snapshot while predictor engines migrate one section at
a time to the v2 catalog.

The v2 design uses one catalog with independently versioned predictor sections.
That gives Official/My Database one atomic source-selection boundary without
forcing unrelated predictors to share one row schema or invalidation policy.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import statistics
from typing import Any, Iterable, Mapping, Sequence


PREDICTION_NORMS_CATALOG_VERSION = 2

PREDICTION_NORMS_SECTION_TRAITS = "traits"
PREDICTION_NORMS_SECTION_ENNEAGRAM = "enneagram"
PREDICTION_NORMS_SECTION_FANTASY_RPG = "fantasy_rpg"
PREDICTION_NORMS_SECTION_DISTINGUISHING_FACTORS = "distinguishing_factors"
PREDICTION_NORMS_SECTION_HD_ELECTROCHEMISTRY = "hd_electrochemistry"

PREDICTION_NORMS_SECTION_KEYS: tuple[str, ...] = (
    PREDICTION_NORMS_SECTION_TRAITS,
    PREDICTION_NORMS_SECTION_ENNEAGRAM,
    PREDICTION_NORMS_SECTION_FANTASY_RPG,
    PREDICTION_NORMS_SECTION_DISTINGUISHING_FACTORS,
    PREDICTION_NORMS_SECTION_HD_ELECTROCHEMISTRY,
)

TRAIT_NORM_SECTION_VERSION = 2
TRAIT_SCORE_BIN_SCALE = 10
TRAIT_SCORE_MIN = 0.0
TRAIT_SCORE_MAX = 100.0
TRAIT_SCORE_BIN_COUNT = int((TRAIT_SCORE_MAX - TRAIT_SCORE_MIN) * TRAIT_SCORE_BIN_SCALE) + 1

TRAIT_DISTRIBUTION_WITH_HOUSES = "with_houses"
TRAIT_DISTRIBUTION_WITHOUT_HOUSES = "without_houses"
TRAIT_DISTRIBUTION_KEYS: tuple[str, ...] = (
    TRAIT_DISTRIBUTION_WITH_HOUSES,
    TRAIT_DISTRIBUTION_WITHOUT_HOUSES,
)


def stable_payload_hash(value: Any) -> str:
    """Return a deterministic SHA-256 digest for JSON-like norm payloads."""
    try:
        payload = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    except TypeError:
        payload = repr(value)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _finite_float_values(values: Iterable[Any]) -> list[float]:
    cleaned: list[float] = []
    for raw_value in values:
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(value):
            cleaned.append(value)
    return cleaned


def _trait_score_bin(value: float) -> int:
    bounded = max(TRAIT_SCORE_MIN, min(TRAIT_SCORE_MAX, float(value)))
    index = int(round((bounded - TRAIT_SCORE_MIN) * TRAIT_SCORE_BIN_SCALE))
    return max(0, min(TRAIT_SCORE_BIN_COUNT - 1, index))


def summarize_trait_distribution(values: Iterable[Any]) -> dict[str, Any]:
    """Summarize 0-100 Trait scores with a tenth-point empirical histogram.

    Trait likelihoods are currently emitted to one decimal place, so a 1001-bin
    histogram retains the complete empirical score distribution while remaining
    compact enough to bundle for hundreds of Traits.
    """
    cleaned = _finite_float_values(values)
    if not cleaned:
        return {
            "sample_size": 0,
            "mean": 0.0,
            "stdev": 0.0,
            "median": 0.0,
            "minimum": 0.0,
            "maximum": 0.0,
            "histogram_tenths": [0] * TRAIT_SCORE_BIN_COUNT,
        }

    histogram = [0] * TRAIT_SCORE_BIN_COUNT
    for value in cleaned:
        histogram[_trait_score_bin(value)] += 1

    return {
        "sample_size": len(cleaned),
        "mean": statistics.fmean(cleaned),
        "stdev": statistics.pstdev(cleaned),
        "median": statistics.median(cleaned),
        "minimum": min(cleaned),
        "maximum": max(cleaned),
        "histogram_tenths": histogram,
    }


def _validated_trait_histogram(summary: Mapping[str, Any]) -> tuple[list[int], int] | None:
    raw_histogram = summary.get("histogram_tenths")
    if not isinstance(raw_histogram, Sequence) or isinstance(raw_histogram, (str, bytes)):
        return None
    if len(raw_histogram) != TRAIT_SCORE_BIN_COUNT:
        return None

    histogram: list[int] = []
    try:
        for raw_count in raw_histogram:
            count = int(raw_count)
            if count < 0:
                return None
            histogram.append(count)
        sample_size = int(summary.get("sample_size", 0) or 0)
    except (TypeError, ValueError):
        return None

    if sample_size < 0 or sum(histogram) != sample_size:
        return None
    return histogram, sample_size


def trait_empirical_percentile(score: float, summary: Mapping[str, Any]) -> float | None:
    """Return the midrank empirical percentile for one 0-100 Trait score."""
    validated = _validated_trait_histogram(summary)
    if validated is None:
        return None
    histogram, sample_size = validated
    if sample_size <= 0:
        return None

    index = _trait_score_bin(score)
    below = sum(histogram[:index])
    equal = histogram[index]
    percentile = 100.0 * (below + (equal * 0.5)) / float(sample_size)
    return max(0.0, min(100.0, percentile))


def trait_z_score(score: float, summary: Mapping[str, Any]) -> float | None:
    """Return the population-standardized Trait score, when spread is nonzero."""
    try:
        mean = float(summary.get("mean", 0.0))
        stdev = float(summary.get("stdev", 0.0))
        value = float(score)
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(item) for item in (mean, stdev, value)) or stdev <= 0:
        return None
    return (value - mean) / stdev


def trait_distribution_for_chart(
    trait_norm_row: Mapping[str, Any],
    *,
    uses_houses: bool,
) -> Mapping[str, Any] | None:
    """Return the statistically comparable Trait population for a target chart.

    ``with_houses`` is for charts with reliable house data. ``without_houses``
    is a reference population rescored with house-dependent criteria disabled.
    The latter must not merely be the subset of charts lacking birth times.
    """
    distributions = trait_norm_row.get("distributions")
    if not isinstance(distributions, Mapping):
        return None
    key = TRAIT_DISTRIBUTION_WITH_HOUSES if uses_houses else TRAIT_DISTRIBUTION_WITHOUT_HOUSES
    selected = distributions.get(key)
    return selected if isinstance(selected, Mapping) else None


def build_trait_norm_row(
    *,
    key: str,
    uid: str,
    name: str,
    profile_hash: str,
    source: str,
    with_houses_scores: Iterable[Any],
    without_houses_scores: Iterable[Any],
    model_kind: str = "",
    sample_sizes: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one self-contained v2 Trait norm row."""
    row = {
        "key": str(key),
        "uid": str(uid),
        "name": str(name),
        "profile_hash": str(profile_hash),
        "source": str(source),
        "model_kind": str(model_kind),
        "distributions": {
            TRAIT_DISTRIBUTION_WITH_HOUSES: summarize_trait_distribution(with_houses_scores),
            TRAIT_DISTRIBUTION_WITHOUT_HOUSES: summarize_trait_distribution(without_houses_scores),
        },
    }
    if isinstance(sample_sizes, Mapping):
        row["sample_sizes"] = {str(key): value for key, value in sample_sizes.items()}
    row["row_signature"] = stable_payload_hash(
        {
            "uid": row["uid"],
            "profile_hash": row["profile_hash"],
            "source": row["source"],
            "model_kind": row["model_kind"],
            "distributions": row["distributions"],
        }
    )
    return row


def empty_prediction_norms_catalog(
    *,
    source: str,
    snapshot_id: str = "",
    created_at: str = "",
    chart_count: int = 0,
    house_reliable_chart_count: int = 0,
    generator_version: str = "",
    provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return an empty v2 catalog with all current predictor namespaces."""
    root_provenance: dict[str, Any] = {
        "chart_count": max(0, int(chart_count)),
        "house_reliable_chart_count": max(0, int(house_reliable_chart_count)),
        "generator_version": str(generator_version),
    }
    if isinstance(provenance, Mapping):
        root_provenance.update({str(key): value for key, value in provenance.items()})

    return {
        "catalog_version": PREDICTION_NORMS_CATALOG_VERSION,
        "snapshot_id": str(snapshot_id),
        "source": str(source),
        "created_at": str(created_at),
        "provenance": root_provenance,
        "sections": {
            PREDICTION_NORMS_SECTION_TRAITS: {
                "version": TRAIT_NORM_SECTION_VERSION,
                "algorithm_version": "",
                "rows": {},
                "retired_trait_keys": [],
            },
            PREDICTION_NORMS_SECTION_ENNEAGRAM: {
                "version": 1,
                "algorithm_version": "",
                "rows": {},
            },
            PREDICTION_NORMS_SECTION_FANTASY_RPG: {
                "version": 1,
                "algorithm_version": "",
                "rows": {},
            },
            PREDICTION_NORMS_SECTION_DISTINGUISHING_FACTORS: {
                "version": 1,
                "algorithm_version": "",
                "rows": {},
            },
            PREDICTION_NORMS_SECTION_HD_ELECTROCHEMISTRY: {
                "version": 1,
                "algorithm_version": "",
                "rows": {},
            },
        },
    }


@dataclass(frozen=True, slots=True)
class PredictionNormsCatalogValidation:
    valid: bool
    errors: tuple[str, ...]


def validate_prediction_norms_catalog(payload: Mapping[str, Any] | None) -> PredictionNormsCatalogValidation:
    """Validate the structural contract without requiring every section to be complete."""
    errors: list[str] = []
    if not isinstance(payload, Mapping):
        return PredictionNormsCatalogValidation(False, ("catalog is not a mapping",))

    if payload.get("catalog_version") != PREDICTION_NORMS_CATALOG_VERSION:
        errors.append(
            f"catalog_version must be {PREDICTION_NORMS_CATALOG_VERSION}"
        )

    sections = payload.get("sections")
    if not isinstance(sections, Mapping):
        errors.append("sections must be a mapping")
        return PredictionNormsCatalogValidation(False, tuple(errors))

    for section_key in PREDICTION_NORMS_SECTION_KEYS:
        section = sections.get(section_key)
        if not isinstance(section, Mapping):
            errors.append(f"missing section: {section_key}")
            continue
        rows = section.get("rows")
        if not isinstance(rows, Mapping):
            errors.append(f"{section_key}.rows must be a mapping")

    return PredictionNormsCatalogValidation(not errors, tuple(errors))


def legacy_prediction_snapshot_to_catalog(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Adapt a v1 snapshot into the v2 namespace without inventing statistics.

    Legacy Trait rows retain only their existing mean as ``legacy_db_average``.
    They are intentionally not upgraded into distributions because the missing
    population spread cannot be reconstructed from a mean.
    """
    catalog = empty_prediction_norms_catalog(
        source=str(payload.get("source", "") or "legacy_v1"),
        snapshot_id=str(payload.get("snapshot_id", "") or ""),
        created_at=str(payload.get("created_at", "") or ""),
        chart_count=int(payload.get("chart_count", 0) or 0),
        provenance={
            "legacy_snapshot_version": payload.get("version"),
            "legacy_norm_signature": str(payload.get("norm_signature", "") or ""),
        },
    )

    sections = catalog["sections"]
    trait_section = sections[PREDICTION_NORMS_SECTION_TRAITS]
    legacy_rows = payload.get("trait_baselines")
    if isinstance(legacy_rows, Mapping):
        for raw_key, raw_row in legacy_rows.items():
            if not isinstance(raw_row, Mapping):
                continue
            row = dict(raw_row)
            if "db_average" in row:
                try:
                    row["legacy_db_average"] = float(row.pop("db_average"))
                except (TypeError, ValueError):
                    row.pop("db_average", None)
            row["legacy_v1"] = True
            trait_section["rows"][str(raw_key)] = row

    retired = payload.get("retired_trait_keys")
    if isinstance(retired, Sequence) and not isinstance(retired, (str, bytes)):
        trait_section["retired_trait_keys"] = [str(value) for value in retired]

    fantasy_rows: dict[str, Any] = {}
    dnd_alignment_keys = payload.get("dnd_alignment_trait_keys")
    if isinstance(dnd_alignment_keys, Sequence) and not isinstance(dnd_alignment_keys, (str, bytes)):
        fantasy_rows["alignment_trait_keys"] = [str(value) for value in dnd_alignment_keys]
    dnd_stat_averages = payload.get("dnd_stat_raw_averages")
    if isinstance(dnd_stat_averages, Mapping):
        fantasy_rows["stat_raw_averages"] = {
            str(key): float(value)
            for key, value in dnd_stat_averages.items()
            if isinstance(value, (int, float))
        }
    sections[PREDICTION_NORMS_SECTION_FANTASY_RPG]["rows"] = fantasy_rows
    return catalog
