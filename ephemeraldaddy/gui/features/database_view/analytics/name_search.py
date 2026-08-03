"""Pure name-token extraction and aggregation for Database Analytics."""

from __future__ import annotations

import math
import statistics
import unicodedata
from dataclasses import dataclass
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
    stopwords: Iterable[str] = DEFAULT_NAME_STOPWORDS,
) -> list[NameStatistic]:
    """Aggregate tokens by distinct chart UID, retaining canonical spelling."""
    if minimum_frequency < 1:
        raise ValueError("minimum_frequency must be at least 1")
    display_by_key: dict[str, str] = {}
    uids_by_key: dict[str, set[str]] = {}
    alignments_by_key: dict[str, list[float]] = {}
    for chart in charts:
        chart_uid = str(getattr(chart, "chart_uid", "") or "").strip().upper()
        if not chart_uid:
            continue
        alignment = _alignment_value(chart)
        for token in extract_name_tokens(
            getattr(chart, "name", ""), getattr(chart, "alias", ""), stopwords=stopwords
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
