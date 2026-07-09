# Predictions Cache and Explainers Summary v2 | last updated 2026-07-09

## Scope

This document describes the current architectural goals and cache responsibilities for the Predictions feature in both:

- **Database View > Database Analytics > Predictions / Traits distribution**, and
- **Chart View > Predictions**, including Traits and D&D-ification sections.

The core design goal is that Predictions should use durable, UID-backed calculation data wherever possible. Rendered HTML is not a primary cache. In-memory objects are allowed only as transient conveniences inside one app session and must not become a second source of truth.

## Architectural principles

1. **UIDs are the durable identity boundary.**
   - Persisted prediction data should be associated with permanent chart UIDs, not legacy transient row IDs.
   - Row IDs may still be used internally by Database Analytics while traversing currently loaded rows, but persisted chart-facing prediction metadata should resolve back to UIDs.

2. **Persist calculations, not rendered views.**
   - The reusable assets are trait likelihoods, trait DB averages, norm signatures, chart signatures, D&D statblock payloads, and D&D alignment parts.
   - Chart View can render HTML from those assets on demand.
   - A rendered-HTML cache is intentionally not part of the durable Predictions architecture because it can drift from the actual metadata/cache state.

3. **Cached stale data should display, but stale status must be explicit.**
   - If prior data exists for a chart, Chart View should show it rather than forcing a manual Calculate first.
   - If chart birth data, trait definitions, or DB norms have changed enough to invalidate freshness, the old data may still be displayed with a Recalculate notice.
   - Fresh recalculation paths must not silently treat stale payloads as fresh.

4. **Database Analytics is the shared trait scoring engine.**
   - Traits in Chart View, Traits in Database Analytics, and D&D Alignment trait scoring should share the same trait likelihood/distribution cache path.
   - The shared path is `_collect_traits_distribution_analytics()` accessed from Chart View through `trait_likelihoods_with_distribution_cache()`.

5. **DB-level norms are separate from per-chart likelihoods.**
   - `.traits_distribution_likelihood_cache` stores reusable per-chart/per-analytical-profile trait likelihoods.
   - `.database_norms_cache` stores DB-level trait averages and norm signatures.
   - `chart_trait_metadata` stores per-chart/per-trait materialized assignments/deviations for immediate Chart View display.

## Cache and persistence layers

### 1. `.traits_distribution_likelihood_cache`

**Owner:** Database Analytics trait distribution code.

**Purpose:** Avoid rescoring every chart/trait combination when only a small number of charts or traits changed.

**Current structure:**

- Uses a compact profile-indexed format.
- Stores analytical profile keys once.
- Stores per-chart likelihood rows keyed by profile index and chart token.
- Preserves row-level staleness checks by chart token.
- Reuses profile likelihoods across trait renames/recolors when the analytical profile is unchanged.

**Primary code paths:**

- `_load_traits_distribution_likelihood_cache()`
- `_save_traits_distribution_likelihood_cache()`
- `_collect_traits_distribution_analytics()`

### 2. `.database_norms_cache`

**Owner:** Chart trait prediction helpers.

**Purpose:** Persist database-level trait averages and norm signatures so Chart View and Database Analytics do not need to recalculate the whole database norm baseline for every chart render.

**Design notes:**

- Cache keys are based on trait UID/analytical profile, not display-only fields.
- Display-only trait changes should not force DB norm rescoring.
- Norm freshness is based on the database norm state and the configured refresh threshold.
- Stale norm data can remain displayable until a forced/background refresh recomputes it.

**Primary code paths:**

- `_load_trait_norm_cache()`
- `_save_trait_norm_cache()`
- `_database_trait_averages()`
- `_database_norm_signature_for_traits()`

### 3. `chart_trait_metadata`

**Owner:** Core DB plus trait prediction helpers.

**Purpose:** Materialize per-chart/per-trait results for fast Chart View display.

**Stored concepts:**

- chart UID,
- trait UID,
- trait display name,
- direction (`above`, `below`, `neutral`),
- likelihood,
- DB average,
- deviation,
- trait signature,
- norm signature,
- chart signature,
- update timestamp.

**Design role:**

This is the first place Chart View Traits should look. If data exists, it should render immediately. If the signatures indicate the result is stale, it should still render with a Recalculate notice.

**Primary code paths:**

- `db.get_chart_trait_metadata(chart_uid)`
- `db.upsert_chart_trait_metadata(chart_uid, rows, ...)`
- `trait_metadata_for_chart(owner, chart, cached_only=True)`
- `trait_metadata_for_chart(owner, chart, cached_only=False)`

### 4. D&D prediction metadata

**Owner:** Core DB plus D&D prediction helpers.

**Purpose:** Persist D&D Statblock and Alignment data across app sessions.

**Stored concepts:**

- D&D statblock payloads,
- statblock cache fingerprints,
- norm token/count,
- norm chart UIDs,
- DB norm averages used for the statblock,
- cached timestamp,
- D&D alignment parts.

**Primary code paths:**

- `chart_dnd_prediction_metadata`
- `db.get_chart_dnd_prediction_metadata(chart_uid)`
- `db.upsert_chart_dnd_prediction_metadata(chart_uid, payload)`
- `_load_persisted_dnd_prediction_payload(chart)`
- `_persist_dnd_prediction_payload(chart, section, payload)`

## Chart View Traits order of operations

The intended Chart View Traits flow is:

1. Resolve the current chart and active trait set.
2. Call `trait_metadata_for_chart(owner, chart, cached_only=True)`.
3. If persisted metadata exists and is fresh, render it immediately.
4. If persisted metadata exists but is stale, render it immediately with a Recalculate notice.
5. If no persisted metadata exists, show the manual Calculate prompt.
6. When the user calculates/recalculates, call `trait_metadata_for_chart(owner, chart)`.
7. During calculation, use `trait_likelihoods_with_distribution_cache()` for missing chart/trait likelihoods.
8. Use `_database_trait_averages()` / `.database_norms_cache` for missing DB-level trait averages.
9. Persist the resulting rows to `chart_trait_metadata` using chart UID and trait UIDs.
10. Render the calculated results.

There should be no hidden rendered-HTML fallback that displays results when `chart_trait_metadata` is absent. If rendered results exist without materialized metadata, that indicates a consistency problem; the architecture should repair or expose that problem rather than mask it with a phantom cache.

## Database View > Database Analytics Traits/Predictions flow

Database Analytics is responsible for bulk trait distribution work and for warming the shared trait likelihood cache.

The intended Database Analytics flow is:

1. Build the active trait signature from active trait analytical profiles.
2. Build the selected/database chart ID set for the current analytics view.
3. Load `.traits_distribution_likelihood_cache` if not already loaded.
4. For each chart/trait profile:
   - reuse chart-level aggregate likelihoods if available,
   - otherwise reuse individual trait/profile likelihoods if chart tokens match,
   - otherwise score only the missing chart/trait profile combinations.
5. Save newly scored individual/profile likelihoods back to `.traits_distribution_likelihood_cache` as progress is made.
6. Persist complete per-chart trait metadata rows to `chart_trait_metadata` when a non-partial aggregate completes.
7. Use `.database_norms_cache` for DB-level averages and norm signatures where appropriate.

The key efficiency goal is incremental recomputation: adding/updating one chart or changing one trait profile should not force a full database-wide recalculation when existing profile/chart-token entries remain valid.

## D&D Alignment flow

D&D Alignment is trait-based, so it should share the trait cache architecture.

The intended D&D Alignment flow is:

1. Build D&D alignment trait items.
2. Compute chart likelihoods through `trait_likelihoods_with_distribution_cache()`.
3. Resolve DB averages through `_database_trait_averages()`.
4. Store/restore D&D alignment parts through D&D prediction metadata for display across sessions.
5. Allow stale display payloads when explicitly rendering cached/stale UI, but force fresh recomputation when recalculating metadata.

## D&D Statblock flow

D&D Statblock is not trait-profile likelihood scoring. It uses D&D stat predictors and DB-relative stat norm averages, so it should not be forced into `.traits_distribution_likelihood_cache` unless the statblock system is redesigned around trait-like analytical profiles.

The intended D&D Statblock flow is:

1. Build chart raw D&D stat predictor scores.
2. Resolve DB norm stat averages once for the norm cohort.
3. Pass those precomputed DB norm averages into `score_dnd_statblock()`.
4. Attach/store the DB norm averages with the statblock payload.
5. Use the same stored averages when explaining the displayed statblock in popouts.
6. Persist the statblock payload in D&D prediction metadata by chart UID.
7. Display stale statblocks when requested by UI display paths, but force fresh recomputation when recalculating.

## Explainers and math auditability

### D&D Statblock popouts

The Statblock popout should explain the actual displayed value, including:

- evidence subtotals,
- scorer-equivalent raw evidence,
- DB norm raw average,
- ratio against the D&D average anchor,
- clamp/round behavior,
- fallback normalization when DB norms are unavailable,
- cache timestamp / norm snapshot context where available.

If the displayed statblock came from a stale cache payload, the popout should explain the stale payload against the same stored DB norm averages that produced it, not against newly computed current norms.

### Traits

Trait explainers should distinguish:

- chart likelihood,
- DB average,
- deviation from DB average,
- above/below/neutral assignment,
- trait UID/profile identity,
- stale vs fresh metadata state.

## Freshness and invalidation model

### Chart changes

Trait and D&D caches that depend on birth data should consider the chart state/signature, including salient birth fields and `chart_uses_houses`. Rectified times should only influence calculations where the chart is explicitly configured to use them.

### Trait changes

Display-only trait changes such as renames or colors should not force rescoring analytical profiles.

Analytical trait profile changes should invalidate affected trait/profile calculations and downstream chart metadata for that trait.

### Database norm changes

Small database edits should not force a full norm rebuild unless they cross the configured database-norm refresh threshold. Stale norms may remain displayable, but recalculation paths should be explicit about whether they are using stale or fresh norms.

## Current design non-goals

1. **No durable rendered-HTML cache for Chart View Traits.**
   - Rendered HTML is downstream presentation, not source data.
   - Persisting it risks hiding metadata/cache inconsistencies.

2. **No silent fallback to a second Predictions architecture.**
   - If `chart_trait_metadata` should exist but does not, the UI should show Calculate or the code should repair/write metadata through the primary flow.

3. **No legacy chart-ID identity for persisted prediction records.**
   - Persisted prediction records should be UID-backed.

4. **No full-database recalculation for every minor edit.**
   - The cache architecture should preserve per-chart/per-profile work whenever chart tokens and analytical profiles still match.

## Verification checklist for future work

When changing Predictions code, confirm the following:

- Chart View Traits checks `chart_trait_metadata` before showing Calculate.
- Chart View Traits does not use a rendered-HTML cache as a source of truth.
- Recalculate routes through `trait_metadata_for_chart(owner, chart)`.
- Missing trait likelihoods route through `trait_likelihoods_with_distribution_cache()`.
- DB trait averages route through `.database_norms_cache` / `_database_trait_averages()`.
- New trait calculations write `trait_uid` rows to `chart_trait_metadata` for the chart UID.
- Database Analytics persists partial likelihood progress to `.traits_distribution_likelihood_cache` as it scores missing profile rows.
- Database Analytics writes materialized chart trait metadata after complete non-partial aggregate passes.
- D&D Alignment uses the shared trait likelihood/norm architecture.
- D&D Statblock reuses precomputed DB norm averages and stores the norm snapshot with the displayed payload.
- Stale UI states display old data with a Recalculate control rather than blocking the panel behind Calculate.

## Testing notes

Focused checks that are useful for this area:

```bash
python3 -m py_compile ephemeraldaddy/gui/features/charts/trait_predictions.py ephemeraldaddy/gui/features/charts/dnd_predictions.py ephemeraldaddy/analysis/dnd/dnd_stat_calculator.py ephemeraldaddy/analysis/dnd/dnd_class_axes_v2.py
```

```bash
PYTHONPATH=/workspace/ephemeraldaddy pytest -q tests/test_trait_predictions_cache.py tests/test_dnd_stat_normalization.py
```

In minimal containers, the pytest command may be blocked by missing GUI system libraries required by PySide6, such as `libGL.so.1`. In that case, source-level checks and `py_compile` still provide partial verification, but full regression coverage requires a GUI-capable test environment.
