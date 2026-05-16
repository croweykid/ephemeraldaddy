"""Statistical-significance helpers for database analytics charts."""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
import random
import statistics
from collections.abc import Callable, Sequence
from typing import Any

SIGNIFICANCE_CORRECTION_NONE = "none"
SIGNIFICANCE_CORRECTION_BH = "benjamini_hochberg"
SIGNIFICANCE_CORRECTION_BONFERRONI = "bonferroni"
SIGNIFICANCE_CORRECTION_DEFAULT = SIGNIFICANCE_CORRECTION_BH
SIGNIFICANCE_CORRECTION_SETTINGS_KEY = "data_visualization/significance_correction"

SIGNIFICANCE_CORRECTION_LABELS: dict[str, str] = {
    SIGNIFICANCE_CORRECTION_NONE: "None",
    SIGNIFICANCE_CORRECTION_BH: "Benjamini-Hochberg FDR",
    SIGNIFICANCE_CORRECTION_BONFERRONI: "Bonferroni strict",
}


@dataclass(frozen=True)
class SignificanceResult:
    """Per-label proportion test result for selection-vs-database analytics."""

    standard_error: float | None
    z_score: float | None
    p_value: float | None
    adjusted_p_value: float | None
    correction: str
    band: str
    model: str

    @property
    def is_significant(self) -> bool:
        return self.adjusted_p_value is not None and self.adjusted_p_value < 0.05


@dataclass(frozen=True)
class BootstrapResult:
    """Empirical null distribution summary for weighted/non-binomial metrics."""

    observed: float
    mean: float
    standard_deviation: float
    z_score: float | None
    p_value: float | None
    iterations: int
    model: str = "bootstrap/permutation"


def normalize_significance_correction(value: object) -> str:
    normalized = str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")
    aliases = {
        "": SIGNIFICANCE_CORRECTION_DEFAULT,
        "default": SIGNIFICANCE_CORRECTION_DEFAULT,
        "none": SIGNIFICANCE_CORRECTION_NONE,
        "no_correction": SIGNIFICANCE_CORRECTION_NONE,
        "benjamini": SIGNIFICANCE_CORRECTION_BH,
        "benjamini_hochberg": SIGNIFICANCE_CORRECTION_BH,
        "benjamini_hochberg_fdr": SIGNIFICANCE_CORRECTION_BH,
        "fdr": SIGNIFICANCE_CORRECTION_BH,
        "bh": SIGNIFICANCE_CORRECTION_BH,
        "bonferroni": SIGNIFICANCE_CORRECTION_BONFERRONI,
        "bonferroni_strict": SIGNIFICANCE_CORRECTION_BONFERRONI,
    }
    return aliases.get(normalized, SIGNIFICANCE_CORRECTION_DEFAULT)


def load_significance_correction(settings: Any) -> str:
    if settings is None:
        return SIGNIFICANCE_CORRECTION_DEFAULT
    return normalize_significance_correction(
        settings.value(SIGNIFICANCE_CORRECTION_SETTINGS_KEY, SIGNIFICANCE_CORRECTION_DEFAULT)
    )


def save_significance_correction(settings: Any, correction: object) -> str:
    normalized = normalize_significance_correction(correction)
    if settings is not None:
        settings.setValue(SIGNIFICANCE_CORRECTION_SETTINGS_KEY, normalized)
    return normalized


def two_tailed_normal_p_value(z_score: float | None) -> float | None:
    if z_score is None or not math.isfinite(float(z_score)):
        return None
    return math.erfc(abs(float(z_score)) / math.sqrt(2.0))


def significance_band(z_score: float | None, adjusted_p_value: float | None = None) -> str:
    if z_score is None or not math.isfinite(float(z_score)):
        return "n/a"
    magnitude = abs(float(z_score))
    if adjusted_p_value is not None and adjusted_p_value < 0.001:
        return "extreme"
    if magnitude >= 3.0:
        return "extreme"
    if adjusted_p_value is not None and adjusted_p_value < 0.01:
        return "strong"
    if magnitude >= 2.58:
        return "strong"
    if adjusted_p_value is not None and adjusted_p_value < 0.05:
        return "significant"
    if magnitude >= 1.96:
        return "significant"
    if magnitude >= 1.0:
        return "weak signal"
    return "noise range"


def _adjust_p_values(p_values: Sequence[float | None], correction: str) -> list[float | None]:
    normalized = normalize_significance_correction(correction)
    adjusted: list[float | None] = [None] * len(p_values)
    indexed = [(index, float(value)) for index, value in enumerate(p_values) if value is not None and math.isfinite(float(value))]
    m = len(indexed)
    if m == 0:
        return adjusted
    if normalized == SIGNIFICANCE_CORRECTION_NONE:
        for index, value in indexed:
            adjusted[index] = max(0.0, min(1.0, value))
        return adjusted
    if normalized == SIGNIFICANCE_CORRECTION_BONFERRONI:
        for index, value in indexed:
            adjusted[index] = max(0.0, min(1.0, value * m))
        return adjusted

    # Benjamini-Hochberg adjusted p-values, made monotonic from largest to smallest p.
    sorted_pairs = sorted(indexed, key=lambda item: item[1])
    running_min = 1.0
    for rank_from_end, (index, value) in enumerate(reversed(sorted_pairs), start=1):
        rank = m - rank_from_end + 1
        bh_value = min(1.0, value * m / rank)
        running_min = min(running_min, bh_value)
        adjusted[index] = running_min
    return adjusted


def proportion_standard_error(database_probability: float, selection_total: float, database_total: float | None = None) -> float | None:
    p = max(0.0, min(1.0, float(database_probability)))
    n = float(selection_total)
    if n <= 0:
        return None
    variance = p * (1.0 - p) / n
    if database_total is not None:
        population = float(database_total)
        if population > 1 and 0 < n < population:
            variance *= max(0.0, (population - n) / (population - 1.0))
    if variance <= 0.0:
        return 0.0
    return math.sqrt(variance)


def compute_proportion_significance_results(
    *,
    selection_counts: Sequence[float | int],
    database_counts: Sequence[float | int],
    loaded_charts: int | float,
    correction: str = SIGNIFICANCE_CORRECTION_DEFAULT,
    selection_total: float | None = None,
    database_total: float | None = None,
) -> list[SignificanceResult]:
    """Compare selected category proportions against database proportions.

    This is the statistically preferred model for categorical Database View charts.
    """

    normalized_correction = normalize_significance_correction(correction)
    resolved_selection_total = (
        float(selection_total)
        if selection_total is not None
        else float(sum(max(0.0, float(value)) for value in selection_counts))
    )
    resolved_database_total = (
        float(database_total)
        if database_total is not None
        else float(sum(max(0.0, float(value)) for value in database_counts))
    )
    has_selection = (
        float(loaded_charts or 0) > 0
        and resolved_selection_total > 0.0
        and resolved_database_total > 0.0
    )
    provisional: list[SignificanceResult] = []
    p_values: list[float | None] = []
    for selection_count, database_count in zip(selection_counts, database_counts):
        if not has_selection:
            result = SignificanceResult(
                standard_error=None,
                z_score=None,
                p_value=None,
                adjusted_p_value=None,
                correction=normalized_correction,
                band="n/a",
                model="category proportion z-test",
            )
            provisional.append(result)
            p_values.append(None)
            continue
        p_database = max(0.0, float(database_count)) / resolved_database_total
        p_selection = max(0.0, float(selection_count)) / resolved_selection_total
        standard_error = proportion_standard_error(
            p_database,
            resolved_selection_total,
            resolved_database_total,
        )
        if standard_error is None or standard_error <= 0.0:
            z_score = 0.0 if abs(p_selection - p_database) <= 1e-12 else None
        else:
            z_score = (p_selection - p_database) / standard_error
        p_value = two_tailed_normal_p_value(z_score)
        provisional.append(
            SignificanceResult(
                standard_error=standard_error,
                z_score=z_score,
                p_value=p_value,
                adjusted_p_value=None,
                correction=normalized_correction,
                band="n/a",
                model="category proportion z-test",
            )
        )
        p_values.append(p_value)

    adjusted_values = _adjust_p_values(p_values, normalized_correction)
    return [
        replace(
            result,
            adjusted_p_value=adjusted_values[index],
            band=significance_band(result.z_score, adjusted_values[index]),
        )
        for index, result in enumerate(provisional)
    ]


def typical_standard_error(results: Sequence[SignificanceResult]) -> float | None:
    values = [float(result.standard_error) for result in results if result.standard_error is not None and result.standard_error > 0]
    if not values:
        return None
    return math.sqrt(sum(value * value for value in values) / len(values))


def draw_standard_deviation_guides(
    ax: Any,
    sigma: float | None,
    *,
    max_sigma: int = 2,
    color: str = "#ff4d4d",
    label_prefix: str = "σ",
) -> None:
    """Draw shared dashed red significance/noise guides on signed delta charts."""

    if sigma is None or not math.isfinite(float(sigma)) or float(sigma) <= 0.0:
        return
    axis_min, axis_max = ax.get_xlim()
    limit = max(abs(float(axis_min)), abs(float(axis_max)))
    if limit <= 0:
        return
    sigma_value = abs(float(sigma))
    for multiplier in range(1, max(1, int(max_sigma)) + 1):
        guide = sigma_value * multiplier
        if guide <= 0 or guide >= limit:
            continue
        alpha = 0.78 if multiplier == 1 else 0.48
        linewidth = 1.1 if multiplier == 1 else 0.9
        for signed_guide in (-guide, guide):
            ax.axvline(
                signed_guide,
                color=color,
                linestyle=(0, (4, 3)),
                linewidth=linewidth,
                alpha=alpha,
                zorder=1.2,
            )
        ax.text(
            guide,
            0.995,
            f"+{multiplier}{label_prefix}",
            color=color,
            fontsize=6.5,
            alpha=alpha,
            ha="center",
            va="top",
            transform=ax.get_xaxis_transform(),
        )
        ax.text(
            -guide,
            0.995,
            f"-{multiplier}{label_prefix}",
            color=color,
            fontsize=6.5,
            alpha=alpha,
            ha="center",
            va="top",
            transform=ax.get_xaxis_transform(),
        )


def bootstrap_metric_significance(
    *,
    population: Sequence[Any],
    selected_size: int,
    observed: float,
    metric: Callable[[Sequence[Any]], float],
    iterations: int = 1000,
    seed: int | None = None,
) -> BootstrapResult | None:
    """Bootstrap/permutation support for weighted metrics that are not category counts."""

    population_values = list(population)
    n = int(selected_size)
    if n <= 0 or len(population_values) < n or iterations <= 0:
        return None
    rng = random.Random(seed)
    simulated: list[float] = []
    for _index in range(int(iterations)):
        sample = rng.sample(population_values, n) if n <= len(population_values) else population_values
        simulated.append(float(metric(sample)))
    if not simulated:
        return None
    mean = statistics.fmean(simulated)
    standard_deviation = statistics.stdev(simulated) if len(simulated) > 1 else 0.0
    z_score = ((float(observed) - mean) / standard_deviation) if standard_deviation > 0 else None
    tail_count = sum(1 for value in simulated if abs(value - mean) >= abs(float(observed) - mean))
    p_value = (tail_count + 1.0) / (len(simulated) + 1.0)
    return BootstrapResult(
        observed=float(observed),
        mean=mean,
        standard_deviation=standard_deviation,
        z_score=z_score,
        p_value=p_value,
        iterations=len(simulated),
    )
