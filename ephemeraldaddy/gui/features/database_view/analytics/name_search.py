"""Pure name-token extraction and aggregation for Database Analytics."""

from __future__ import annotations

import json
import math
import os
import statistics
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal

NameMetric = Literal["frequency", "mean_alignment", "median_alignment", "mode_alignment"]

# Relationship words and conversational alias detritus are deliberately excluded.
# Internal apostrophes and hyphens remain part of a token; only surrounding
# punctuation is removed.
DEFAULT_NAME_STOPWORDS = frozenset(
    {
        "a", "alias", "also", "an", "and", "aunt", "boyfriend", "brother",
        "child", "cousin", "dad", "daddy", "daughter", "ex", "father", "friend",
        "girlfriend", "grandfather", "grandma", "grandmother", "grandpa", "husband",
        "known", "mom", "mommy", "mother", "my", "née", "nephew", "niece", "or",
        "partner", "roommate", "sister", "son", "spouse", "the", "uncle", "wife",
    }
)
NAME_SUPPRESSIONS_PATH_ENV = "EPHEMERALDADDY_NAME_SUPPRESSIONS_PATH"
NAME_SUPPRESSIONS_FILENAME = "name_suppressions.json"


def resolve_name_suppressions_path(path: str | os.PathLike[str] | None = None) -> Path:
    """Return the user-writable file holding manually suppressed name tokens."""
    if path is not None:
        return Path(path).expanduser()
    env_path = os.environ.get(NAME_SUPPRESSIONS_PATH_ENV)
    if env_path:
        return Path(env_path).expanduser()
    return Path.home() / ".ephemeraldaddy" / NAME_SUPPRESSIONS_FILENAME


def load_name_suppressions(
    path: str | os.PathLike[str] | None = None,
) -> frozenset[str]:
    """Load normalized user suppressions, tolerating absent or damaged files."""
    try:
        payload = json.loads(resolve_name_suppressions_path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return frozenset()
    values = payload.get("suppressed_names", []) if isinstance(payload, dict) else []
    if not isinstance(values, list):
        return frozenset()
    return frozenset(
        str(value).strip().casefold() for value in values if str(value).strip()
    )


def suppress_name_tokens(
    names: Iterable[str],
    path: str | os.PathLike[str] | None = None,
) -> int:
    """Persist name tokens as suppressed and return the number newly added."""
    destination = resolve_name_suppressions_path(path)
    existing = set(load_name_suppressions(destination))
    requested = {str(name).strip().casefold() for name in names if str(name).strip()}
    updated = existing | requested
    added = len(updated - existing)
    if not added:
        return 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(f"{destination.suffix}.tmp")
    temporary.write_text(
        json.dumps(
            {"schema_version": 1, "suppressed_names": sorted(updated)},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
    return added


@dataclass(frozen=True)
class NameStatistic:
    """One name token's chart membership and optional Alignment summary."""

    name: str
    chart_uids: tuple[str, ...]
    frequency: int
    alignment_count: int
    mean_alignment: float | None
    median_alignment: float | None
    mode_alignment: tuple[float, ...]

    def value_for(self, metric: NameMetric) -> float | None:
        if metric == "frequency":
            return float(self.frequency)
        if metric == "mean_alignment":
            return self.mean_alignment
        if metric == "median_alignment":
            return self.median_alignment
        if metric == "mode_alignment":
            return self.mode_alignment[0] if len(self.mode_alignment) == 1 else None
        raise ValueError(f"Unsupported name metric: {metric}")


def _strip_surrounding_punctuation(token: str) -> str:
    start = 0
    end = len(token)
    while start < end and unicodedata.category(token[start]).startswith(("P", "S")):
        start += 1
    while end > start and unicodedata.category(token[end - 1]).startswith(("P", "S")):
        end -= 1
    return token[start:end]


def extract_name_tokens(
    name: object,
    alias: object,
    *,
    stopwords: Iterable[str] = DEFAULT_NAME_STOPWORDS,
) -> tuple[str, ...]:
    """Return unique, whitespace-delimited name tokens in encounter order."""
    blocked = {str(word).strip().casefold() for word in stopwords if str(word).strip()}
    tokens: list[str] = []
    seen: set[str] = set()
    for field in (name, alias):
        for raw_token in str(field or "").split():
            token = _strip_surrounding_punctuation(raw_token).strip()
            key = token.casefold()
            if not token or key in blocked or key in seen:
                continue
            seen.add(key)
            tokens.append(token)
    return tuple(tokens)


def chart_has_name_token(
    chart: Any,
    token: str,
    *,
    stopwords: Iterable[str] | None = None,
) -> bool:
    """Return whether a chart's name or alias contains an exact name token."""
    effective_stopwords = (
        DEFAULT_NAME_STOPWORDS | load_name_suppressions()
        if stopwords is None
        else frozenset(stopwords)
    )
    target = str(token or "").strip().casefold()
    if not target:
        return False
    return target in {
        name_token.casefold()
        for name_token in extract_name_tokens(
            getattr(chart, "name", ""),
            getattr(chart, "alias", ""),
            stopwords=effective_stopwords,
        )
    }


def _alignment_value(chart: Any) -> float | None:
    value = getattr(chart, "alignment_score", None)
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def analyze_names(
    charts: Iterable[Any],
    *,
    minimum_frequency: int = 4,
    stopwords: Iterable[str] | None = None,
) -> list[NameStatistic]:
    """Aggregate tokens by distinct chart UID, retaining canonical spelling."""
    if minimum_frequency < 1:
        raise ValueError("minimum_frequency must be at least 1")
    effective_stopwords = (
        DEFAULT_NAME_STOPWORDS | load_name_suppressions()
        if stopwords is None
        else frozenset(stopwords)
    )
    display_by_key: dict[str, str] = {}
    uids_by_key: dict[str, set[str]] = {}
    alignments_by_key: dict[str, list[float]] = {}
    for chart in charts:
        chart_uid = str(getattr(chart, "chart_uid", "") or "").strip().upper()
        if not chart_uid:
            continue
        alignment = _alignment_value(chart)
        for token in extract_name_tokens(
            getattr(chart, "name", ""),
            getattr(chart, "alias", ""),
            stopwords=effective_stopwords,
        ):
            key = token.casefold()
            members = uids_by_key.setdefault(key, set())
            if chart_uid in members:
                continue
            display_by_key.setdefault(key, token)
            members.add(chart_uid)
            if alignment is not None:
                alignments_by_key.setdefault(key, []).append(alignment)

    results: list[NameStatistic] = []
    for key, chart_uids in uids_by_key.items():
        if len(chart_uids) < minimum_frequency:
            continue
        values = alignments_by_key.get(key, [])
        modes = tuple(float(value) for value in statistics.multimode(values)) if values else ()
        results.append(
            NameStatistic(
                name=display_by_key[key],
                chart_uids=tuple(sorted(chart_uids)),
                frequency=len(chart_uids),
                alignment_count=len(values),
                mean_alignment=statistics.fmean(values) if values else None,
                median_alignment=float(statistics.median(values)) if values else None,
                mode_alignment=modes,
            )
        )
    return sorted(results, key=lambda item: (-item.frequency, item.name.casefold()))
