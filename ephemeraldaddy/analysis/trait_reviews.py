"""Subjective Trait review metadata, independent of analytical definitions."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

TRAIT_REVIEW_FIELDS = frozenset({"chart_accuracy_rankings", "perceived_accuracy", "astro_analysis"})
ACCURACY_LABELS = ("useless", "pretty inaccurate", "mixed results", "mostly accurate", "very accurate")


def without_trait_reviews(profile: Mapping[str, Any]) -> dict[str, Any]:
    """Keep existing profile fingerprints stable when only a review changes."""
    return {key: value for key, value in profile.items() if key not in TRAIT_REVIEW_FIELDS}


def normalize_accuracy_rankings(entries: Any) -> list[dict[str, Any]]:
    """Retain the saved cohort's order, using permanent chart UIDs only."""
    if not isinstance(entries, (list, tuple)):
        return []
    result = []
    seen = set()
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        uid = str(entry.get("chart_uid") or "").strip().upper()
        if not uid or uid in seen:
            continue
        value = entry.get("value")
        if type(value) is not int or not 1 <= value <= 5:
            value = None
        result.append({"chart_uid": uid, "value": value, "name": str(entry.get("name") or "")})
        seen.add(uid)
    return result


def accuracy_rating_summary(
    entries: Sequence[Mapping[str, Any]],
    *,
    excluded_chart_uids: Iterable[object] = (),
) -> tuple[float | None, int, int]:
    """Return (mean, rated count, eligible count) for the same review cohort.

    Exclusions use permanent chart UIDs, not names or transient database IDs.
    Empty ratings never contribute to the mean, and no eligible ratings
    produces None rather than a misleading zero.
    """
    excluded = {
        normalized
        for uid in excluded_chart_uids
        if (normalized := str(uid or "").strip().upper())
    }
    eligible = [
        row for row in normalize_accuracy_rankings(entries)
        if row["chart_uid"] not in excluded
    ]
    values = [row["value"] for row in eligible if row["value"] is not None]
    average = sum(values) / len(values) if values else None
    return average, len(values), len(eligible)


def perceived_accuracy(entries: Sequence[Mapping[str, Any]]) -> float | None:
    return accuracy_rating_summary(entries)[0]


def trait_review_fields(profile: Mapping[str, Any]) -> dict[str, Any]:
    entries = normalize_accuracy_rankings(profile.get("chart_accuracy_rankings"))
    return {
        "chart_accuracy_rankings": entries,
        "perceived_accuracy": perceived_accuracy(entries),
        "astro_analysis": str(profile.get("astro_analysis") or ""),
    }


def _reviews_path() -> Path:
    from ephemeraldaddy.analysis.traits import TRAIT_DIR

    return TRAIT_DIR.parent / ".trait_reviews.json"


def load_bundled_trait_reviews() -> dict[str, Any]:
    """Read local annotations without ever writing the packaged default catalog."""
    path = _reviews_path()
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Trait reviews must contain a mapping keyed by Trait UID.")
    return payload


def save_trait_review(trait: Mapping[str, Any], **updates: Any) -> None:
    """Merge only review fields into the current Trait, preserving other edits."""
    if not updates or set(updates) - TRAIT_REVIEW_FIELDS:
        raise ValueError("Only Trait review metadata can be saved here.")
    if "chart_accuracy_rankings" in updates:
        updates["chart_accuracy_rankings"] = normalize_accuracy_rankings(updates["chart_accuracy_rankings"])
        updates["perceived_accuracy"] = perceived_accuracy(updates["chart_accuracy_rankings"])
    elif "perceived_accuracy" in updates:
        raise ValueError("Perceived accuracy must be derived from chart ratings.")
    if "astro_analysis" in updates:
        updates["astro_analysis"] = str(updates["astro_analysis"])

    from ephemeraldaddy.analysis.traits import _rewrite_single_trait

    if not trait.get("bundled", False):
        _rewrite_single_trait(trait["path"], updates)
        return
    uid = str(trait.get("uid") or trait.get("trait_uid") or "").strip()
    if not uid:
        raise ValueError("A permanent Trait UID is required to save a review.")
    payload = load_bundled_trait_reviews()
    fields = trait_review_fields(payload.get(uid, {}))
    fields.update(updates)
    payload[uid] = fields
    destination = _reviews_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Replace atomically so an interrupted save cannot truncate other reviews.
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=destination.parent, delete=False) as handle:
            temporary_path = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary_path, destination)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
