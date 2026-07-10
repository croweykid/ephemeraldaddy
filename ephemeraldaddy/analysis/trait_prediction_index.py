"""Shared trait prediction index primitives.

This module is intentionally GUI-free.  It owns the fast/read-through pieces that
Chart View, Database Analytics, and future prediction consumers can share:
compiled trait descriptors, chart-vector cache keys, baseline accumulator helpers,
a tiny worker queue, and a cached-result reader that combines chart-local
likelihood vectors with DB baseline vectors.
"""

from __future__ import annotations

import hashlib
import json
import logging
import queue
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Hashable, Iterable, Mapping

from ephemeraldaddy.analysis.traits import calculate_trait_likelihoods, trait_possible_score
from ephemeraldaddy.core import db
from ephemeraldaddy.core.chart import chart_uses_houses

logger = logging.getLogger(__name__)

TRAIT_INDEX_VERSION = 1
TRAIT_INDEX_MAX_COMPILED_SIGNATURES = 128
TRAIT_INDEX_MAX_CHART_VECTORS = 10_000
TRAIT_INDEX_MAX_LIKELIHOOD_VECTORS = 25_000


def stable_json_hash(value: Any) -> str:
    try:
        payload = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    except TypeError:
        payload = repr(value)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def trait_uid_for_index_item(trait: Mapping[str, Any]) -> str:
    return str(trait.get("uid") or trait.get("trait_uid") or "").strip()


@dataclass(frozen=True)
class CompiledTraitProfile:
    """Scoring-relevant trait profile data compiled once per trait signature."""

    uid: str
    name: str
    profile_signature: str
    profile: Mapping[str, Any]
    possible_with_houses: float
    possible_without_houses: float


@dataclass(frozen=True)
class ChartFeatureVector:
    """Stable chart feature token used by the index cache.

    Full feature extraction can grow here over time.  Phase 3 starts by making
    the chart signature explicit and caching chart-local likelihood vectors
    behind it, so expensive scorers do not need to rediscover identity/state.
    """

    chart_signature: str
    uses_houses: bool
    feature_signature: str


@dataclass(frozen=True)
class TraitPredictionQuery:
    chart_uid: str
    chart_signature: str
    trait_signature: str
    norm_signature: str


@dataclass
class TraitPredictionResult:
    likelihoods: dict[str, float]
    database_averages: dict[str, float]
    deviations: dict[str, float]
    stale_chart_vector: bool = False
    stale_trait_definition: bool = False
    stale_db_baseline: bool = False
    updated_at: str = ""

    @property
    def stale(self) -> bool:
        return bool(self.stale_chart_vector or self.stale_trait_definition or self.stale_db_baseline)


@dataclass
class BaselineAccumulator:
    """Incremental baseline accumulator for one norm/trait-set generation."""

    norm_signature: str
    trait_signature: str
    sums: dict[str, float] = field(default_factory=dict)
    chart_count: int = 0

    def add_chart(self, likelihoods: Mapping[str, float]) -> None:
        self.chart_count += 1
        for trait_key, value in likelihoods.items():
            self.sums[str(trait_key)] = self.sums.get(str(trait_key), 0.0) + float(value)

    def remove_chart(self, likelihoods: Mapping[str, float]) -> None:
        if self.chart_count > 0:
            self.chart_count -= 1
        for trait_key, value in likelihoods.items():
            self.sums[str(trait_key)] = self.sums.get(str(trait_key), 0.0) - float(value)

    def averages(self) -> dict[str, float]:
        if self.chart_count <= 0:
            return {}
        return {name: total / float(self.chart_count) for name, total in self.sums.items()}


class TraitPredictionIndex:
    """In-process trait prediction index and background queue."""

    def __init__(self) -> None:
        self._compiled_traits: OrderedDict[str, tuple[CompiledTraitProfile, ...]] = OrderedDict()
        self._chart_vectors: OrderedDict[str, ChartFeatureVector] = OrderedDict()
        self._likelihood_vectors: OrderedDict[tuple[str, str], dict[str, float]] = OrderedDict()
        self._baseline_accumulators: dict[tuple[str, str], BaselineAccumulator] = {}
        self._lock = threading.RLock()
        self._queue: queue.Queue[
            tuple[Hashable | None, Callable[..., Any], tuple[Any, ...], dict[str, Any]]
        ] = queue.Queue()
        self._queued_keys: set[Hashable] = set()
        self._worker: threading.Thread | None = None
        self._stop_event = threading.Event()

    def compile_traits(self, traits: Iterable[Mapping[str, Any]], trait_signature: str) -> tuple[CompiledTraitProfile, ...]:
        with self._lock:
            cached = self._compiled_traits.get(trait_signature)
            if cached is not None:
                self._compiled_traits.move_to_end(trait_signature)
                return cached
        compiled: list[CompiledTraitProfile] = []
        for trait in traits:
            name = str(trait.get("name", "")).strip()
            if not name or bool(trait.get("archived", False)):
                continue
            profile = trait.get("profile", {}) if isinstance(trait.get("profile", {}), Mapping) else {}
            compiled.append(
                CompiledTraitProfile(
                    uid=trait_uid_for_index_item(trait),
                    name=name,
                    profile_signature=stable_json_hash(profile),
                    profile=profile,
                    possible_with_houses=trait_possible_score(profile, include_houses=True),
                    possible_without_houses=trait_possible_score(profile, include_houses=False),
                )
            )
        result = tuple(compiled)
        with self._lock:
            self._compiled_traits[trait_signature] = result
            self._compiled_traits.move_to_end(trait_signature)
            while len(self._compiled_traits) > TRAIT_INDEX_MAX_COMPILED_SIGNATURES:
                self._compiled_traits.popitem(last=False)
        return result

    def chart_features(self, chart: Any, chart_signature: str) -> ChartFeatureVector:
        with self._lock:
            cached = self._chart_vectors.get(chart_signature)
            if cached is not None:
                self._chart_vectors.move_to_end(chart_signature)
                return cached
        try:
            uses_houses = bool(chart_uses_houses(chart))
        except Exception:
            uses_houses = bool(getattr(chart, "use_birth_time_data", False))
        vector = ChartFeatureVector(
            chart_signature=chart_signature,
            uses_houses=uses_houses,
            feature_signature=stable_json_hash({"chart_signature": chart_signature, "uses_houses": uses_houses}),
        )
        with self._lock:
            self._chart_vectors[chart_signature] = vector
            self._chart_vectors.move_to_end(chart_signature)
            while len(self._chart_vectors) > TRAIT_INDEX_MAX_CHART_VECTORS:
                self._chart_vectors.popitem(last=False)
        return vector

    def chart_likelihoods(
        self,
        chart: Any,
        traits: list[dict[str, Any]],
        *,
        chart_signature: str,
        trait_signature: str,
    ) -> dict[str, float]:
        cache_key = (chart_signature, trait_signature)
        with self._lock:
            cached = self._likelihood_vectors.get(cache_key)
            if cached is not None:
                self._likelihood_vectors.move_to_end(cache_key)
                return dict(cached)
        compiled = self.compile_traits(traits, trait_signature)
        features = self.chart_features(chart, chart_signature)
        possible_scores = {
            item.name: item.possible_with_houses if features.uses_houses else item.possible_without_houses
            for item in compiled
        }
        likelihoods = calculate_trait_likelihoods(chart, traits, possible_scores=possible_scores)
        with self._lock:
            self._likelihood_vectors[cache_key] = dict(likelihoods)
            self._likelihood_vectors.move_to_end(cache_key)
            while len(self._likelihood_vectors) > TRAIT_INDEX_MAX_LIKELIHOOD_VECTORS:
                self._likelihood_vectors.popitem(last=False)
        return likelihoods

    def update_baseline_accumulator(
        self,
        *,
        norm_signature: str,
        trait_signature: str,
        chart_likelihoods: Iterable[Mapping[str, float]],
    ) -> BaselineAccumulator:
        key = (norm_signature, trait_signature)
        accumulator = BaselineAccumulator(norm_signature=norm_signature, trait_signature=trait_signature)
        for likelihoods in chart_likelihoods:
            accumulator.add_chart(likelihoods)
        with self._lock:
            self._baseline_accumulators[key] = accumulator
        return accumulator

    def enqueue(
        self,
        fn: Callable[..., Any],
        *args: Any,
        key: Hashable | None = None,
        **kwargs: Any,
    ) -> None:
        with self._lock:
            if key is not None and key in self._queued_keys:
                return
            if key is not None:
                self._queued_keys.add(key)
            self._queue.put((key, fn, args, kwargs))
        self.start_worker()

    def warm_chart_likelihoods_async(
        self,
        chart: Any,
        traits: list[dict[str, Any]],
        *,
        chart_signature: str,
        trait_signature: str,
    ) -> None:
        self.enqueue(
            self.chart_likelihoods,
            chart,
            traits,
            key=("chart_likelihoods", chart_signature, trait_signature),
            chart_signature=chart_signature,
            trait_signature=trait_signature,
        )

    def start_worker(self) -> None:
        with self._lock:
            if self._worker is not None and self._worker.is_alive():
                return
            self._stop_event.clear()
            self._worker = threading.Thread(target=self._run_queue, name="trait-prediction-index", daemon=True)
            self._worker.start()

    def stop_worker(self) -> None:
        self._stop_event.set()

    def _run_queue(self) -> None:
        while not self._stop_event.is_set():
            try:
                key, fn, args, kwargs = self._queue.get(timeout=0.25)
            except queue.Empty:
                return
            try:
                fn(*args, **kwargs)
            except Exception:
                logger.exception("Trait prediction index worker job failed.")
            finally:
                if key is not None:
                    with self._lock:
                        self._queued_keys.discard(key)
                self._queue.task_done()

    def read_cached(self, query: TraitPredictionQuery, traits: list[dict[str, Any]]) -> TraitPredictionResult | None:
        with self._lock:
            accumulator = self._baseline_accumulators.get((query.norm_signature, query.trait_signature))
            accumulator_averages = accumulator.averages() if accumulator is not None else None
        return read_cached_trait_prediction(query, traits, baseline_averages=accumulator_averages)


_INDEX = TraitPredictionIndex()


def global_trait_prediction_index() -> TraitPredictionIndex:
    return _INDEX


def read_cached_trait_prediction(
    query: TraitPredictionQuery,
    traits: list[dict[str, Any]],
    *,
    baseline_averages: Mapping[str, float] | None = None,
) -> TraitPredictionResult | None:
    """Fast read API that combines persisted chart vectors and baseline vectors."""
    traits_by_name = {str(trait.get("name", "")).strip(): trait for trait in traits if str(trait.get("name", "")).strip()}
    if not traits_by_name:
        return None
    trait_uids_by_name = {name: trait_uid_for_index_item(trait) for name, trait in traits_by_name.items()}
    names_by_uid = {uid: name for name, uid in trait_uids_by_name.items() if uid}
    active_names = set(traits_by_name)

    chart_rows = db.get_chart_trait_likelihoods(query.chart_uid)
    if baseline_averages is None:
        baseline_rows = db.get_trait_baseline_snapshot(
            norm_signature=query.norm_signature,
            trait_signature=query.trait_signature,
        )
    else:
        baseline_rows = [
            {"trait_name": name, "trait_uid": trait_uids_by_name.get(name, ""), "db_average": average}
            for name, average in baseline_averages.items()
        ]

    fresh_chart: dict[str, float] = {}
    stale_chart: dict[str, float] = {}
    stale_trait: dict[str, float] = {}
    for row in chart_rows:
        row_uid = str(row.get("trait_uid", "") or "").strip()
        name = names_by_uid.get(row_uid) if row_uid else str(row.get("trait_name", "")).strip()
        if name not in active_names:
            continue
        row_trait_signature = str(row.get("trait_signature", "") or "")
        row_chart_signature = str(row.get("chart_signature", "") or "")
        likelihood = float(row.get("likelihood", 0.0))
        if row_trait_signature == query.trait_signature and row_chart_signature == query.chart_signature:
            fresh_chart[name] = likelihood
        elif row_trait_signature == query.trait_signature:
            stale_chart[name] = likelihood
        else:
            stale_trait[name] = likelihood

    baselines: dict[str, float] = {}
    for row in baseline_rows:
        row_uid = str(row.get("trait_uid", "") or "").strip()
        name = names_by_uid.get(row_uid) if row_uid else str(row.get("trait_name", "")).strip()
        if name in active_names:
            baselines[name] = float(row.get("db_average", 0.0))

    stale_db_baseline = set(baselines) != active_names
    likelihoods: dict[str, float]
    stale_chart_vector = False
    stale_trait_definition = False
    if set(fresh_chart) == active_names:
        likelihoods = fresh_chart
    elif set(stale_chart) == active_names:
        likelihoods = stale_chart
        stale_chart_vector = True
    elif set(stale_trait) == active_names:
        likelihoods = stale_trait
        stale_trait_definition = True
    else:
        return None
    if not baselines:
        return None
    deviations = {name: float(likelihoods[name]) - float(baselines[name]) for name in likelihoods if name in baselines}
    updated_at = ""
    row_times = [str(row.get("updated_at", "") or "") for row in [*chart_rows, *baseline_rows]]
    if row_times:
        updated_at = max(row_times)
    return TraitPredictionResult(
        likelihoods=likelihoods,
        database_averages=baselines,
        deviations=deviations,
        stale_chart_vector=stale_chart_vector,
        stale_trait_definition=stale_trait_definition,
        stale_db_baseline=stale_db_baseline,
        updated_at=updated_at,
    )
