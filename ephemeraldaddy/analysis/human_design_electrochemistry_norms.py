"""Persistent, database-wide norms for Human Design electrochemistry scores."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Iterable, Sequence

from ephemeraldaddy.analysis.human_design_synastry import (
    HD_ELECTROCHEMISTRY_MAX_SCORE,
    HumanDesignSynastryCandidate,
)
from ephemeraldaddy.core.human_design_system import (
    defined_centers_from_active_gates,
    defined_channels_from_active_gates,
)

HD_ELECTROCHEMISTRY_NORMS_CACHE_VERSION = 1
HD_ELECTROCHEMISTRY_NORMS_STALE_RATIO = 0.15
HD_ELECTROCHEMISTRY_NORMS_CACHE_FILENAME = ".hd_electrochemistry_norms_cache.json"


@dataclass(frozen=True, slots=True)
class HumanDesignElectrochemistryNorms:
    """Compact score distribution for all unordered chart pairs in a snapshot."""

    population_fingerprint: str
    chart_tokens: tuple[tuple[str, str], ...]
    histogram: tuple[int, ...]
    sample_size: int
    median: float
    percentile_thresholds: tuple[tuple[int, int], ...]

    def percentile_for_score(self, score: int) -> float:
        """Return the inclusive empirical percentile of a score in the snapshot."""
        if self.sample_size <= 0:
            return 0.0
        bounded_score = max(0, min(HD_ELECTROCHEMISTRY_MAX_SCORE, int(score)))
        return 100.0 * sum(self.histogram[: bounded_score + 1]) / self.sample_size


@dataclass(frozen=True, slots=True)
class HumanDesignElectrochemistryNormsFreshness:
    added_or_changed_uid_count: int
    refresh_threshold: int

    @property
    def requires_refresh(self) -> bool:
        return self.added_or_changed_uid_count >= self.refresh_threshold


def electrochemistry_chart_tokens(
    candidates: Iterable[HumanDesignSynastryCandidate],
) -> tuple[tuple[str, str], ...]:
    """Build UID-first tokens containing only score/reliability dependencies."""
    tokens = []
    for candidate in candidates:
        uid = str(candidate.chart_uid or "").strip().upper()
        if not uid or not 1 <= len(candidate.gates) <= 26:
            continue
        dependency = json.dumps(
            {
                "gates": sorted(candidate.gates),
                "uses_houses": bool(candidate.uses_houses),
                "astro_data_signature": str(candidate.astro_data_signature or ""),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        tokens.append((uid, sha256(dependency.encode("utf-8")).hexdigest()))
    return tuple(sorted(tokens))


def electrochemistry_population_fingerprint(chart_tokens: Sequence[tuple[str, str]]) -> str:
    encoded = json.dumps(list(chart_tokens), separators=(",", ":"), ensure_ascii=True)
    return sha256(encoded.encode("utf-8")).hexdigest()


def electrochemistry_norms_refresh_threshold(chart_count: int) -> int:
    """Refresh after at least 15% of the saved population is added or changed."""
    return max(1, math.ceil(max(0, int(chart_count)) * HD_ELECTROCHEMISTRY_NORMS_STALE_RATIO))


def electrochemistry_norms_freshness(
    saved_tokens: Sequence[tuple[str, str]],
    current_tokens: Sequence[tuple[str, str]],
) -> HumanDesignElectrochemistryNormsFreshness:
    """Ignore deletions; count only new charts and changed HD dependencies."""
    saved = dict(saved_tokens)
    current = dict(current_tokens)
    added_or_changed = sum(saved.get(uid) != token for uid, token in current.items())
    return HumanDesignElectrochemistryNormsFreshness(
        added_or_changed_uid_count=added_or_changed,
        refresh_threshold=electrochemistry_norms_refresh_threshold(len(saved) or len(current)),
    )


def _score_at_percentile(histogram: Sequence[int], sample_size: int, percentile: int) -> int:
    target_rank = max(1, math.ceil(sample_size * percentile / 100.0))
    cumulative = 0
    for score, count in enumerate(histogram):
        cumulative += count
        if cumulative >= target_rank:
            return score
    return HD_ELECTROCHEMISTRY_MAX_SCORE


def _histogram_median(histogram: Sequence[int], sample_size: int) -> float:
    if sample_size <= 0:
        return 0.0
    lower_rank = (sample_size + 1) // 2
    upper_rank = (sample_size + 2) // 2
    cumulative = 0
    lower_score: int | None = None
    for score, count in enumerate(histogram):
        cumulative += count
        if cumulative >= lower_rank and lower_score is None:
            lower_score = score
        if cumulative >= upper_rank:
            return ((lower_score if lower_score is not None else score) + score) / 2.0
    return 0.0


def calculate_human_design_electrochemistry_norms(
    candidates: Sequence[HumanDesignSynastryCandidate],
) -> HumanDesignElectrochemistryNorms:
    """Calculate a compact histogram over unique unordered candidate pairs."""
    eligible = [
        candidate
        for candidate in candidates
        if str(candidate.chart_uid or "").strip() and 1 <= len(candidate.gates) <= 26
    ]
    prepared = [
        (
            candidate.gates,
            {
                tuple(sorted((gate_a, gate_b)))
                for gate_a, gate_b, _center_a, _center_b in defined_channels_from_active_gates(
                    candidate.gates
                )
            },
        )
        for candidate in eligible
    ]
    histogram = [0] * (HD_ELECTROCHEMISTRY_MAX_SCORE + 1)
    sample_size = 0
    for left_index, (left_gates, left_channels) in enumerate(prepared):
        for right_index in range(left_index + 1, len(prepared)):
            right_gates, right_channels = prepared[right_index]
            combined_gates = left_gates | right_gates
            combined_channels = {
                tuple(sorted((gate_a, gate_b)))
                for gate_a, gate_b, _center_a, _center_b in defined_channels_from_active_gates(
                    combined_gates
                )
            }
            completed_channels = len(combined_channels - left_channels - right_channels)
            defined_centers = len(defined_centers_from_active_gates(combined_gates))
            score = completed_channels + defined_centers
            histogram[score] += 1
            sample_size += 1
    tokens = electrochemistry_chart_tokens(eligible)
    thresholds = tuple(
        (percentile, _score_at_percentile(histogram, sample_size, percentile))
        for percentile in (50, 75, 90, 95)
    ) if sample_size else ()
    return HumanDesignElectrochemistryNorms(
        population_fingerprint=electrochemistry_population_fingerprint(tokens),
        chart_tokens=tokens,
        histogram=tuple(histogram),
        sample_size=sample_size,
        median=_histogram_median(histogram, sample_size),
        percentile_thresholds=thresholds,
    )


def save_human_design_electrochemistry_norms(
    path: Path,
    norms: HumanDesignElectrochemistryNorms,
) -> None:
    """Atomically persist a compact norms snapshot."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": HD_ELECTROCHEMISTRY_NORMS_CACHE_VERSION,
        "population_fingerprint": norms.population_fingerprint,
        "chart_tokens": norms.chart_tokens,
        "histogram": norms.histogram,
        "sample_size": norms.sample_size,
        "median": norms.median,
        "percentile_thresholds": norms.percentile_thresholds,
    }
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    temporary_path.replace(path)


def load_human_design_electrochemistry_norms(
    path: Path,
) -> HumanDesignElectrochemistryNorms | None:
    """Load a valid compact norms snapshot, returning ``None`` on corruption."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        histogram = tuple(int(value) for value in payload["histogram"])
        if (
            payload.get("version") != HD_ELECTROCHEMISTRY_NORMS_CACHE_VERSION
            or len(histogram) != HD_ELECTROCHEMISTRY_MAX_SCORE + 1
            or sum(histogram) != int(payload["sample_size"])
        ):
            return None
        chart_tokens = tuple((str(uid), str(token)) for uid, token in payload["chart_tokens"])
        if str(payload["population_fingerprint"]) != electrochemistry_population_fingerprint(
            chart_tokens
        ):
            return None
        return HumanDesignElectrochemistryNorms(
            population_fingerprint=str(payload["population_fingerprint"]),
            chart_tokens=chart_tokens,
            histogram=histogram,
            sample_size=int(payload["sample_size"]),
            median=float(payload["median"]),
            percentile_thresholds=tuple(
                (int(percentile), int(score))
                for percentile, score in payload["percentile_thresholds"]
            ),
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None
