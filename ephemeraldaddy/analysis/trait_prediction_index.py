"""Shared trait prediction index primitives.

This module is intentionally GUI-free.  It owns the fast/read-through pieces that
Chart View, Database Analytics, and future prediction consumers can share:
compiled trait descriptors, chart-vector cache keys, baseline accumulator helpers,
a tiny worker queue, and a cached-result reader that combines chart-local
likelihood vectors with DB baseline vectors.
"""

from __future__ import annotations

import copy
import hashlib
import time
import json
import logging
import queue
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Hashable, Iterable, Mapping

from ephemeraldaddy.analysis.traits import calculate_trait_likelihoods, trait_possible_score
from ephemeraldaddy.analysis.trait_signatures import trait_definition_signature, chart_prediction_signature
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
    # Current labels for absent cells or mismatched chart/model inputs.
    stale_trait_names: frozenset[str] = field(default_factory=frozenset)

    @property
    def stale(self) -> bool:
        return bool(self.stale_chart_vector or self.stale_trait_definition or self.stale_db_baseline or self.stale_trait_names)


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
        self._likelihood_vectors: OrderedDict[tuple[str, str], float] = OrderedDict()
        self._chart_generations: dict[str, int] = {}
        self._trait_generations: dict[str, int] = {}
        self._listeners: set[Callable[..., Any]] = set()
        self.revision = 0
        self._baseline_accumulators: dict[tuple[str, str], BaselineAccumulator] = {}
        self._lock = threading.RLock()
        self._queue: queue.Queue[
            tuple[Hashable | None, Callable[..., Any], tuple[Any, ...], dict[str, Any]]
        ] = queue.Queue()
        self._queued_keys: set[Hashable] = set()
        self._worker: threading.Thread | None = None
        self._stop_event = threading.Event()

    def invalidate_chart(self, uid: str) -> None:
        with self._lock:
            self._chart_generations[uid] = self._chart_generations.get(uid, 0) + 1
            self.revision += 1

    def invalidate_trait(self, uid: str) -> None:
        with self._lock:
            self._trait_generations[uid] = self._trait_generations.get(uid, 0) + 1
            self.revision += 1

    def refresh_guard(self, chart_uids: Iterable[str], traits: list[dict[str, Any]]) -> Callable[[], bool]:
        with self._lock:
            chart_versions = {uid: self._chart_generations.get(uid, 0) for uid in chart_uids}
            trait_versions = {trait_uid_for_index_item(t): self._trait_generations.get(trait_uid_for_index_item(t), 0) for t in traits}
        database = str(db.DB_PATH)
        def obsolete() -> bool:
            with self._lock:
                return (str(db.DB_PATH) != database
                        or any(self._chart_generations.get(uid, 0) != version for uid, version in chart_versions.items())
                        or any(self._trait_generations.get(uid, 0) != version for uid, version in trait_versions.items()))
        return obsolete

    def subscribe(self, callback: Callable[..., Any]) -> Callable[[], None]:
        with self._lock:
            self._listeners.add(callback)
        def unsubscribe() -> None:
            with self._lock:
                self._listeners.discard(callback)
        return unsubscribe

    def _publish(self, chart_uids: Iterable[str], traits: list[dict[str, Any]]) -> None:
        with self._lock:
            self.revision += 1
            callbacks = tuple(self._listeners)
        for callback in callbacks:
            try:
                callback(frozenset(chart_uids), frozenset(trait_uid_for_index_item(t) for t in traits))
            except RuntimeError:
                # A Qt relay can be destroyed between copying and notification.
                with self._lock:
                    self._listeners.discard(callback)

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
                    profile_signature=trait_definition_signature(trait),
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
        self, chart: Any, traits: list[dict[str, Any]], *,
        chart_signature: str, trait_signature: str = "", definition_signatures: Mapping[str, str] | None = None,
    ) -> dict[str, float]:
        # Cache each analytical profile separately: a roster/label change cannot
        # invalidate another Trait. Names are applied only when assembling results.
        active = [t for t in traits if not t.get("archived", False) and t.get("name")]
        definitions = definition_signatures if definition_signatures is not None else {str(t["name"]): trait_definition_signature(t) for t in active}
        values = {}
        missing = []
        with self._lock:
            for trait in active:
                key = (chart_signature, definitions[str(trait["name"])])
                cached = self._likelihood_vectors.get(key)
                if cached is None:
                    missing.append(trait)
                else:
                    self._likelihood_vectors.move_to_end(key)
                    values[str(trait["name"])] = float(cached)
        if missing:
            compiled = self.compile_traits(missing, stable_json_hash([
                (trait_uid_for_index_item(t), t["name"], definitions[str(t["name"])]) for t in missing
            ]))
            features = self.chart_features(chart, chart_signature)
            possible = {t.name: t.possible_with_houses if features.uses_houses else t.possible_without_houses for t in compiled}
            scored = calculate_trait_likelihoods(chart, missing, possible_scores=possible)
            with self._lock:
                for trait in missing:
                    name = str(trait["name"])
                    if name in scored:
                        key = (chart_signature, definitions[str(trait["name"])])
                        self._likelihood_vectors[key] = float(scored[name])
                        values[name] = float(scored[name])
                while len(self._likelihood_vectors) > TRAIT_INDEX_MAX_LIKELIHOOD_VECTORS:
                    self._likelihood_vectors.popitem(last=False)
        return values

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
                with self._lock:
                    if self._queue.empty():
                        self._worker = None
                        return
                continue
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
        return self.results_for_uids([query.chart_uid], traits, chart_signatures={query.chart_uid: query.chart_signature}).get(query.chart_uid)

    def results_for_uids(
        self, chart_uids: Iterable[str], traits: list[dict[str, Any]], *,
        snapshot: Mapping[str, Any] | None = None,
        chart_signatures: Mapping[str, str] | None = None,
    ) -> dict[str, TraitPredictionResult]:
        """Read any available scores in bulk, using only the static norm source.

        Partial and older caches are readable. No chart hydration, scoring,
        factor explanations, or population generation occurs on this path.
        """
        from ephemeraldaddy.core.prediction_norms import trait_norm_values, prediction_norms_reference

        snapshot = snapshot if snapshot is not None else prediction_norms_reference()
        uids = tuple(dict.fromkeys(str(uid).strip().upper() for uid in chart_uids if str(uid).strip()))
        by_uid = {trait_uid_for_index_item(trait): trait for trait in traits}
        by_name = {str(trait.get("name", "")): trait for trait in traits}
        rows = db.get_trait_prediction_rows_by_uids(uids, by_uid, trait_names=by_name)
        signatures = {name: trait_definition_signature(trait) for name, trait in by_name.items()}
        averages_by_mode = {mode: trait_norm_values(traits, snapshot, include_houses=mode) for mode in (False, True)}
        results = {}
        for uid, entries in rows.items():
            scores = {}
            outdated_definitions = set()
            outdated_charts = set()
            times = []
            for row in entries:
                row_uid = str(row.get("trait_uid", ""))
                trait = by_uid.get(row_uid) if row_uid else by_name.get(str(row.get("trait_name", "")))
                if trait is None:
                    continue
                name = str(trait["name"])
                if name in scores:
                    continue
                scores[name] = float(row["likelihood"])
                if row.get("trait_signature") != signatures[name]:
                    outdated_definitions.add(name)
                current_chart = (chart_signatures or {}).get(uid)
                if current_chart:
                    chart_stale = row.get("chart_signature") != current_chart
                elif row.get("cached_astro_revision") is None:
                    # Pre-checkpoint caches need one worker verification only
                    # for charts that have actually had their astro inputs edited.
                    chart_stale = bool(row.get("latest_astro_edit_revision", 0))
                else:
                    chart_stale = row["cached_astro_revision"] != row["current_astro_revision"]
                if chart_stale:
                    outdated_charts.add(name)
                times.append(str(row.get("updated_at", "")))
            if scores:
                outdated_definitions.update(by_name.keys() - scores.keys())
                averages = averages_by_mode[bool(entries[0].get("uses_houses", True))]
                available = dict(averages)
                results[uid] = TraitPredictionResult(
                    scores, available, {name: value - available[name] for name, value in scores.items() if name in available},
                    stale_chart_vector=bool(outdated_charts), stale_trait_definition=bool(outdated_definitions),
                    stale_db_baseline=set(available) != set(by_name), updated_at=max(times, default=""),
                    stale_trait_names=frozenset(outdated_definitions | outdated_charts),
                )
        return results

    def persist_scores(
        self, chart: Any, traits: list[dict[str, Any]], scores: Mapping[str, float], *,
        snapshot: Mapping[str, Any] | None = None,
        definition_signatures: Mapping[str, str] | None = None,
        expected_astro_revision: int | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> bool:
        """Write one saved chart's cells, rejecting a changed astro revision."""
        from ephemeraldaddy.core.prediction_norms import trait_norm_values, trait_norm_signature, prediction_norms_reference

        snapshot = snapshot if snapshot is not None else prediction_norms_reference()
        uid = str(getattr(chart, "chart_uid", "") or "").strip().upper()
        if not uid:
            return False
        signature = chart_prediction_signature(chart)
        if expected_astro_revision is None:
            expected_astro_revision = db.chart_astro_revisions([uid]).get(uid)
            saved = db.load_chart_by_uid(uid) if expected_astro_revision is not None else None
            if saved is None or chart_prediction_signature(saved) != signature:
                return False
        averages = trait_norm_values(traits, snapshot, include_houses=bool(chart_uses_houses(chart)))
        definitions = definition_signatures if definition_signatures is not None else {str(t["name"]): trait_definition_signature(t) for t in traits}
        rows = [{"trait_uid": trait_uid_for_index_item(t), "trait_name": t["name"],
                 "trait_signature": definitions[str(t["name"])], "likelihood": float(scores[t["name"]])}
                for t in traits if t["name"] in scores]
        if should_cancel and should_cancel():
            return False
        if not db.upsert_chart_trait_likelihoods(
            uid, rows, chart_signature=signature, expected_astro_revision=expected_astro_revision,
        ):
            return False
        derived = []
        definitions = {t["name"]: t for t in traits}
        for row in rows:
            name = row["trait_name"]
            if name in averages:
                delta = row["likelihood"] - averages[name]
                derived.append({**row, "db_average": averages[name], "deviation": delta,
                                "direction": "above" if delta >= 5 else "below" if delta <= -5 else "neutral",
                                "norm_signature": trait_norm_signature(definitions[name], snapshot)})
        if derived:
            if should_cancel and should_cancel():
                return False
            return db.upsert_chart_trait_metadata(
                uid, derived, trait_signature="", norm_signature="", chart_signature=signature,
                expected_astro_revision=expected_astro_revision,
            )
        return True

    def score_chart(self, chart: Any, traits: list[dict[str, Any]], *, persist: bool = True) -> dict[str, float]:
        scores = self.chart_likelihoods(chart, traits, chart_signature=chart_prediction_signature(chart))
        if persist:
            self.persist_scores(chart, traits, scores)
        return scores

    def collect(self, chart_uids: Iterable[str], traits: list[dict[str, Any]], *,
                calculate_missing: bool = False, should_cancel: Callable[[], bool] | None = None,
                progress: Callable[[float], None] | None = None) -> dict[str, Any]:
        """Shared numeric collection for Analytics, Rankings and accuracy reviews.

        Cached reads hydrate no charts. Missing or input-mismatched cells
        are calculated only by workers; GUI callers queue them and show old values.
        Cohort totals describe that cohort, never its population reference.
        """
        uids = tuple(dict.fromkeys(str(uid).strip().upper() for uid in chart_uids if str(uid).strip()))
        active = [t for t in traits if not t.get("archived", False)]
        if calculate_missing:
            from ephemeraldaddy.analysis.trait_cache_migration import import_legacy_trait_cache
            import_legacy_trait_cache(active)
        cached = self.results_for_uids(uids, active)
        missing = {}
        for uid in uids:
            result = cached.get(uid)
            scores = result.likelihoods if result is not None else {}
            stale_names = result.stale_trait_names if result is not None else frozenset()
            needed = [t for t in active if t["name"] not in scores or t["name"] in stale_names]
            if needed:
                missing[uid] = needed
        groups = {}
        for uid, needed in missing.items():
            key = tuple((trait_uid_for_index_item(t), trait_definition_signature(t)) for t in needed)
            groups.setdefault(key, ([], needed))[0].append(uid)
        if calculate_missing:
            processed = 0
            for scoped_uids, needed in groups.values():
                if should_cancel and should_cancel():
                    break
                def group_progress(value: float) -> None:
                    if progress:
                        progress((processed + value * len(scoped_uids) / 100.) * 100. / max(1, len(missing)))
                self.refresh_uids(scoped_uids, needed, should_cancel=should_cancel, notify=False, progress=group_progress, reuse_matching_scores=True)
                processed += len(scoped_uids)
            cached = self.results_for_uids(uids, active)
            if missing:
                self._publish(missing, active)
        elif missing:
            # Existing worker queue owns scoring; no window crosses it.
            for scoped_uids, needed in groups.values():
                self.request_refresh(scoped_uids, needed, reuse_matching_scores=True)
        names = [str(t["name"]) for t in active]
        complete = {uid: result for uid, result in cached.items() if set(names) <= result.likelihoods.keys()}
        parsed = len(complete)
        if progress and (not should_cancel or not should_cancel()):
            progress(100.0 if parsed == len(uids) else parsed * 100.0 / max(1, len(uids)))
        return {"trait_names": names, "totals": {name: sum(r.likelihoods[name] / 100.0 for r in complete.values()) for name in names},
                "chart_count": parsed, "colors": {t["name"]: t.get("color", "#ffffff") for t in active},
                "partial": parsed != len(uids), "requested_chart_count": len(uids), "parsed_chart_count": parsed,
                "parsed_percent": parsed * 100.0 / len(uids) if uids else 100.0}

    def refresh_uids(
        self, chart_uids: Iterable[str], traits: list[dict[str, Any]], *,
        should_cancel: Callable[[], bool] | None = None,
        progress: Callable[[float], None] | None = None,
        notify: bool = True, chart_versions: Mapping[str, int] | None = None,
        reuse_matching_scores: bool = False,
    ) -> dict[str, TraitPredictionResult]:
        """Explicit worker-only refresh of the supplied chart/Trait intersection."""
        uids = tuple(dict.fromkeys(str(uid).strip().upper() for uid in chart_uids if str(uid).strip()))
        active = [trait for trait in traits if not trait.get("archived", False)]
        with self._lock:
            versions = dict(chart_versions) if chart_versions is not None else {uid: self._chart_generations.get(uid, 0) for uid in uids}
        from ephemeraldaddy.core.prediction_norms import prediction_norms_reference
        reference = prediction_norms_reference()
        definitions = {str(t["name"]): trait_definition_signature(t) for t in active}
        obsolete = self.refresh_guard([], active)
        completed = []
        for start in range(0, len(uids), 64):
            if obsolete() or (should_cancel and should_cancel()):
                break
            chunk = uids[start:start + 64]
            astro_revisions = db.chart_astro_revisions(chunk)
            charts = db.load_charts_by_uids(chunk)
            chart_signatures = {uid: chart_prediction_signature(chart) for uid, chart in charts.items()}
            cached = self.results_for_uids(charts, active, chart_signatures=chart_signatures) if reuse_matching_scores else {}
            for uid, chart in charts.items():
                if obsolete() or (should_cancel and should_cancel()):
                    break
                if getattr(chart, "is_placeholder", False) or self._chart_generations.get(uid, 0) != versions.get(uid, 0):
                    continue
                result = cached.get(uid)
                scores = {name: value for name, value in result.likelihoods.items() if name not in result.stale_trait_names} if result else {}
                needed = [trait for trait in active if trait["name"] not in scores]
                scores.update(self.chart_likelihoods(chart, needed, chart_signature=chart_signatures[uid], definition_signatures=definitions))
                if obsolete() or (should_cancel and should_cancel()):
                    break
                if self._chart_generations.get(uid, 0) != versions.get(uid, 0):
                    continue
                accepted = uid in astro_revisions and self.persist_scores(
                    chart, active, scores, snapshot=reference, definition_signatures=definitions,
                    expected_astro_revision=astro_revisions[uid],
                    should_cancel=lambda: obsolete() or bool(should_cancel and should_cancel()),
                )
                if not accepted:
                    continue
                completed.append(uid)
                if progress:
                    progress(len(completed) * 100.0 / max(1, len(uids)))
        if completed and notify:
            self._publish(completed, active)
        return self.results_for_uids(completed, active)

    def request_missing(self, chart_uids: Iterable[str], traits: list[dict[str, Any]]) -> None:
        """Schedule missing/input-mismatched cells; reuse fresh scores."""
        uids = tuple(sorted(set(chart_uids)))
        definitions = copy.deepcopy(traits)
        obsolete = self.refresh_guard([], definitions)
        if uids and definitions:
            self.enqueue(self.collect, uids, definitions, calculate_missing=True,
                         should_cancel=obsolete,
                         key=("missing", str(db.DB_PATH), uids, tuple((trait_uid_for_index_item(t), trait_definition_signature(t)) for t in definitions)))

    def request_refresh(
        self, chart_uids: Iterable[str], traits: list[dict[str, Any]], *,
        reuse_matching_scores: bool = False,
    ) -> None:
        uids = tuple(sorted(set(chart_uids)))
        definitions = copy.deepcopy(traits)
        with self._lock:
            chart_versions = {uid: self._chart_generations.get(uid, 0) for uid in uids}
            trait_versions = {trait_uid_for_index_item(t): self._trait_generations.get(trait_uid_for_index_item(t), 0) for t in definitions}
        # Trait edits supersede the whole requested column. A chart edit skips
        # just that chart, whose new request owns its replacement scores.
        cancelled = self.refresh_guard([], definitions)
        if uids and definitions:
            self.enqueue(self.refresh_uids, uids, definitions, should_cancel=cancelled, chart_versions=chart_versions, reuse_matching_scores=reuse_matching_scores,
                         key=(str(db.DB_PATH), "refresh", uids, tuple((trait_uid_for_index_item(t), trait_definition_signature(t)) for t in definitions), tuple(chart_versions.values()), tuple(trait_versions.values()), reuse_matching_scores))


_INDEX = TraitPredictionIndex()


def global_trait_prediction_index() -> TraitPredictionIndex:
    return _INDEX


def read_cached_trait_prediction(
    query: TraitPredictionQuery, traits: list[dict[str, Any]], *,
    baseline_averages: Mapping[str, float] | None = None,
) -> TraitPredictionResult | None:
    # Compatibility entry point. Delete when callers use results_for_uids.
    snapshot = None
    if baseline_averages is not None:
        snapshot = {"trait_baselines": {f"name:{name.casefold()}": {"db_average": value}
                                     for name, value in baseline_averages.items()}}
    return global_trait_prediction_index().results_for_uids(
        [query.chart_uid], traits, snapshot=snapshot,
        chart_signatures={query.chart_uid: query.chart_signature},
    ).get(query.chart_uid.upper())
