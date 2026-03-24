from __future__ import annotations

from dataclasses import dataclass
import statistics
from typing import Protocol

from ephemeraldaddy.analysis.get_astro_twin import chart_similarity_score
from ephemeraldaddy.core.chart import Chart

SIMILARITY_NORMS_SETTINGS_GROUP = "similarity_norms"
DEFAULT_SIMILARITY_THRESHOLDS: tuple[float, float, float, float] = (20.0, 40.0, 60.0, 80.0)


class _SettingsLike(Protocol):
    def value(self, key: str, default: object | None = None) -> object: ...
    def setValue(self, key: str, value: object) -> None: ...


@dataclass(frozen=True)
class SimilarityThresholds:
    q20: float
    q40: float
    q60: float
    q80: float

    @classmethod
    def defaults(cls) -> "SimilarityThresholds":
        return cls(*DEFAULT_SIMILARITY_THRESHOLDS)

    def normalized(self) -> "SimilarityThresholds":
        ordered = sorted(
            [
                max(0.0, min(100.0, float(self.q20))),
                max(0.0, min(100.0, float(self.q40))),
                max(0.0, min(100.0, float(self.q60))),
                max(0.0, min(100.0, float(self.q80))),
            ]
        )
        return SimilarityThresholds(*ordered)


@dataclass(frozen=True)
class SimilarityBand:
    key: str
    label: str
    color: str


@dataclass(frozen=True)
class SimilarityCalibrationResult:
    minimum: float
    maximum: float
    average: float
    median: float
    mode_values: tuple[float, ...]
    mode_count: int
    pair_count: int
    thresholds: SimilarityThresholds


BAND_MOST_SIMILAR = SimilarityBand("most_similar", "most similar", "#26a69a")
BAND_SOMEWHAT_SIMILAR = SimilarityBand("somewhat_similar", "somewhat similar", "#9ccc65")
BAND_AVERAGE = SimilarityBand("average_similarity", "average similarity", "#fdd835")
BAND_SOMEWHAT_DISSIMILAR = SimilarityBand("somewhat_dissimilar", "somewhat dissimilar", "#fb8c00")
BAND_MOST_DISSIMILAR = SimilarityBand("most_dissimilar", "most dissimilar", "#e53935")


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    sorted_values = sorted(float(value) for value in values)
    p = max(0.0, min(100.0, float(percentile_value)))
    position = (len(sorted_values) - 1) * (p / 100.0)
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    if lower_index == upper_index:
        return sorted_values[lower_index]
    lower = sorted_values[lower_index]
    upper = sorted_values[upper_index]
    return lower + ((upper - lower) * (position - lower_index))


def classify_similarity(similarity_percent: float, thresholds: SimilarityThresholds) -> SimilarityBand:
    normalized = thresholds.normalized()
    value = float(similarity_percent)
    if value <= normalized.q20:
        return BAND_MOST_DISSIMILAR
    if value <= normalized.q40:
        return BAND_SOMEWHAT_DISSIMILAR
    if value <= normalized.q60:
        return BAND_AVERAGE
    if value <= normalized.q80:
        return BAND_SOMEWHAT_SIMILAR
    return BAND_MOST_SIMILAR


def compute_similarity_calibration(charts: list[Chart]) -> SimilarityCalibrationResult | None:
    if len(charts) < 2:
        return None
    similarity_values: list[float] = []
    for left_index, left_chart in enumerate(charts):
        for right_chart in charts[left_index + 1 :]:
            score, _placement, _aspect, _distribution = chart_similarity_score(left_chart, right_chart)
            similarity_values.append(round(score * 100.0, 1))
    if not similarity_values:
        return None

    counts = statistics.multimode(similarity_values)
    if counts:
        mode_count = max(similarity_values.count(value) for value in counts)
        mode_values = tuple(sorted(float(value) for value in counts))
    else:
        mode_count = 0
        mode_values = ()

    thresholds = SimilarityThresholds(
        q20=percentile(similarity_values, 20.0),
        q40=percentile(similarity_values, 40.0),
        q60=percentile(similarity_values, 60.0),
        q80=percentile(similarity_values, 80.0),
    ).normalized()
    return SimilarityCalibrationResult(
        minimum=min(similarity_values),
        maximum=max(similarity_values),
        average=statistics.fmean(similarity_values),
        median=statistics.median(similarity_values),
        mode_values=mode_values,
        mode_count=mode_count,
        pair_count=len(similarity_values),
        thresholds=thresholds,
    )


def load_similarity_thresholds(settings: _SettingsLike) -> SimilarityThresholds:
    defaults = SimilarityThresholds.defaults()
    thresholds = SimilarityThresholds(
        q20=float(settings.value(f"{SIMILARITY_NORMS_SETTINGS_GROUP}/q20", defaults.q20)),
        q40=float(settings.value(f"{SIMILARITY_NORMS_SETTINGS_GROUP}/q40", defaults.q40)),
        q60=float(settings.value(f"{SIMILARITY_NORMS_SETTINGS_GROUP}/q60", defaults.q60)),
        q80=float(settings.value(f"{SIMILARITY_NORMS_SETTINGS_GROUP}/q80", defaults.q80)),
    )
    return thresholds.normalized()


def save_similarity_thresholds(settings: _SettingsLike, thresholds: SimilarityThresholds) -> SimilarityThresholds:
    normalized = thresholds.normalized()
    settings.setValue(f"{SIMILARITY_NORMS_SETTINGS_GROUP}/q20", round(normalized.q20, 1))
    settings.setValue(f"{SIMILARITY_NORMS_SETTINGS_GROUP}/q40", round(normalized.q40, 1))
    settings.setValue(f"{SIMILARITY_NORMS_SETTINGS_GROUP}/q60", round(normalized.q60, 1))
    settings.setValue(f"{SIMILARITY_NORMS_SETTINGS_GROUP}/q80", round(normalized.q80, 1))
    return normalized


def save_similarity_calibration(settings: _SettingsLike, result: SimilarityCalibrationResult) -> SimilarityThresholds:
    normalized = save_similarity_thresholds(settings, result.thresholds)
    settings.setValue(f"{SIMILARITY_NORMS_SETTINGS_GROUP}/min", round(result.minimum, 1))
    settings.setValue(f"{SIMILARITY_NORMS_SETTINGS_GROUP}/max", round(result.maximum, 1))
    settings.setValue(f"{SIMILARITY_NORMS_SETTINGS_GROUP}/average", round(result.average, 1))
    settings.setValue(f"{SIMILARITY_NORMS_SETTINGS_GROUP}/median", round(result.median, 1))
    settings.setValue(
        f"{SIMILARITY_NORMS_SETTINGS_GROUP}/mode",
        ", ".join(f"{value:.1f}" for value in result.mode_values),
    )
    settings.setValue(f"{SIMILARITY_NORMS_SETTINGS_GROUP}/pair_count", int(result.pair_count))
    return normalized
