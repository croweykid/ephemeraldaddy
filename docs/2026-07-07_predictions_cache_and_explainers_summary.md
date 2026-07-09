# Predictions Cache and Explainers Summary v2 | last updated 2026-07-09

## Scope

This document summarizes the requested Chart View Predictions-panel changes discussed in this conversation, especially the D&D-ification Statblock/Alignment behavior, statblock popout math explainers, persisted prediction caches, stale-cache UI, UID-only cache identity, and the related Traits-panel cached-rendering behavior. It also records the current architectural core shared by Database View > Database Analytics > Predictions/Traits distribution and Chart View > Predictions: durable calculation data should live in UID-backed metadata and shared calculation caches, while rendered HTML should remain downstream presentation rather than a durable cache.

## Original user goals

1. **Make the D&D Statblock popout math auditable.**
   - The Statblock popout already listed evidence subtotals.
   - The requested behavior was to add a divider and then show:
     - each subtotal again,
     - the subtotals added together,
     - the actual DB norm comparison,
     - when the DB norm/cache value was cached,
     - and the remaining math leading to the final displayed D&D stat.

2. **Never block previously loaded Predictions results behind a Calculate prompt.**
   - If any Predictions section has prior data for a chart, that data should display by default.
   - Even stale data should display first.
   - If stale, the UI should show a recalculation option at the top while keeping old results visible.

3. **Make D&D prediction caches survive app restarts.**
   - In-memory owner/chart-object caches were not enough.
   - D&D Statblock and Alignment payloads needed UID-backed persistence in app metadata/storage.

4. **Use UIDs only.**
   - Legacy chart ID fallbacks should be removed.
   - Charts missing UIDs should fail loudly in Terminal with the chart name and a clear message.

5. **Make stale-cache correctness explicit.**
   - Stale cached values may be acceptable for display, but fresh recalculation paths must not silently reuse stale data.
   - Statblock cache validation must include chart state, not just norm state, so edited charts are not treated as fresh when database norms have not changed.

6. **Use a visually consistent Recalculate control.**
   - The stale notice should use a button styled like the Predictions-panel `Calculate!` button, not a random rich-text link.

7. **Apply the cache-first principle beyond D&D Statblock.**
   - D&D Alignment should also restore and display cached results.
   - Traits should render available persisted metadata/results immediately and should not depend on a rendered-HTML cache as a source of truth.
   - Fast sections should not be unnecessarily bottlenecked by a manual Calculate/Recalculate flow.

## Programmatic changes made

### 1. D&D statblock evidence subtotals and math walkthrough

File: `ephemeraldaddy/gui/features/charts/dnd_predictions.py`

- `_build_dnd_stat_evidence_html()` was changed to return both rendered evidence HTML and a list of `(section_name, subtotal)` pairs.
- `_build_dnd_stat_math_html()` was added to render the math block below a divider.
- The math block now shows:
  - per-section subtotals,
  - displayed subtotal sum,
  - scorer-equivalent raw total after category balancing/count weighting,
  - DB norm raw average when available,
  - ratio math against the D&D average anchor,
  - clamp/round behavior,
  - fallback tanh normalization when DB norms are unavailable or zero,
  - and the final displayed stat value.
- `build_dnd_statblock_popout_info_html()` wires the evidence subtotal output into the math walkthrough.

Important implementation locations:

- `_build_dnd_stat_evidence_html()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`
- `_build_dnd_stat_math_html()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`
- `build_dnd_statblock_popout_info_html()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`

### 2. Use scorer-equivalent raw evidence for fallback math

File: `ephemeraldaddy/gui/features/charts/dnd_predictions.py`

A review concern identified that displayed evidence subtotals are not the same raw quantity normalized by `score_dnd_statblock()`.

To address that:

- `_build_dnd_stat_math_html()` calls `calculate_weighted_criteria_scores()` for the selected stat.
- Fallback normalization uses this scorer-equivalent raw total rather than the visible subtotal sum.
- The UI still shows the visible subtotal sum, but explains that the category-balanced scorer raw total is the value that is actually normalized.

Important implementation location:

- `_build_dnd_stat_math_html()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`

### 3. Store original DB norm averages with statblock cache payloads

File: `ephemeraldaddy/gui/features/charts/dnd_predictions.py`

A stale popout correctness concern was identified: stale statblock values could be explained against current DB norms.

To fix that:

- Statblock cache payloads now store:
  - `norm_token`,
  - `norm_count`,
  - `db_norm_averages`,
  - `key_fingerprint`,
  - `cached_at`,
  - and the statblock payload itself.
- Restored statblocks are given their original `_db_norm_averages`.
- `build_dnd_statblock_popout_info_html()` passes those stored norm averages into `_build_dnd_stat_math_html()`.
- The popout math therefore describes the same norm snapshot that produced the displayed statblock.

Important implementation locations:

- `DndPredictionPanelAdapter._score_statblock()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`
- `DndPredictionPanelAdapter.build_popout_info()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`
- `_build_dnd_stat_math_html()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`

### 4. Fix stale statblock popout HTML cache keys

File: `ephemeraldaddy/gui/features/charts/dnd_predictions.py`

A review concern identified that popout HTML was keyed against the current norm token, even when the statblock being displayed was stale.

To fix that:

- Statblock cache payloads include a `key_fingerprint` describing the payload that produced the displayed statblock.
- Statblock popout HTML cache keys now include that statblock payload fingerprint.
- This prevents stale popout HTML from being stored or reused as if it belonged to fresh/current norm data.

Important implementation location:

- `DndPredictionPanelAdapter.build_popout_info()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`

### 5. Persist D&D prediction metadata across app sessions

File: `ephemeraldaddy/core/db.py`

A major concern was that owner-level caches only lasted for the current app session.

To address this, a new persistent SQLite table was added:

- `chart_dnd_prediction_metadata`
  - `chart_uid TEXT PRIMARY KEY`
  - `payload TEXT NOT NULL DEFAULT '{}'`
  - `updated_at TEXT NOT NULL DEFAULT ''`

New DB helpers were added:

- `_create_dnd_prediction_metadata_table()`
- `upsert_chart_dnd_prediction_metadata(chart_uid, payload)`
- `get_chart_dnd_prediction_metadata(chart_uid)`

Schema initialization now calls `_create_dnd_prediction_metadata_table()` from `_ensure_schema()`.

Important implementation locations:

- `_create_dnd_prediction_metadata_table()` in `ephemeraldaddy/core/db.py`
- `upsert_chart_dnd_prediction_metadata()` in `ephemeraldaddy/core/db.py`
- `get_chart_dnd_prediction_metadata()` in `ephemeraldaddy/core/db.py`
- `_ensure_schema()` in `ephemeraldaddy/core/db.py`

### 6. Serialize and restore D&D statblock payloads safely

File: `ephemeraldaddy/gui/features/charts/dnd_predictions.py`

Because `DnDStatBlock` objects cannot be directly persisted as JSON, statblock serialization helpers were added:

- `_statblock_to_cache_dict()`
- `_statblock_from_cache_dict()`
- `_restore_statblock_cache_payload()`

These helpers convert statblock raw scores, displayed scores, and modifiers to/from JSON-safe dictionaries and restore a `DnDStatBlock` object when loading persisted metadata.

Important implementation locations:

- `_statblock_to_cache_dict()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`
- `_statblock_from_cache_dict()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`
- `_restore_statblock_cache_payload()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`

### 7. Persist and restore D&D Statblock and Alignment caches

File: `ephemeraldaddy/gui/features/charts/dnd_predictions.py`

D&D cache persistence/restoration helpers were added:

- `_load_persisted_dnd_prediction_payload(chart)`
- `_persist_dnd_prediction_payload(chart, section, payload)`
- `_owner_cache_bucket(owner, attr_name)`

Statblock behavior:

- `_restore_statblock_cache()` checks chart-local cache first, then owner cache, then persisted DB metadata.
- `_score_statblock()` persists freshly computed statblock payloads.

Alignment behavior:

- `_dnd_alignment_score_parts()` checks chart-local cache, then owner cache, then persisted DB metadata.
- Freshly computed alignment parts are persisted.

Important implementation locations:

- `_load_persisted_dnd_prediction_payload()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`
- `_persist_dnd_prediction_payload()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`
- `DndPredictionPanelAdapter._restore_statblock_cache()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`
- `DndPredictionPanelAdapter._score_statblock()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`
- `_dnd_alignment_score_parts()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`

### 8. Remove legacy chart ID cache fallback and fail loudly on missing UIDs

File: `ephemeraldaddy/gui/features/charts/dnd_predictions.py`

The UID migration concern was addressed by removing chart ID fallbacks from D&D prediction cache identity.

Current behavior:

- `_chart_prediction_cache_uid()` checks UID-style attributes only:
  - `uid`
  - `UID`
  - `chart_uid`
  - `permanent_uid`
- `_chart_prediction_cache_identity()` returns `uid:<uid>` only when a UID exists.
- Missing UIDs trigger `_log_missing_chart_uid()`.
- `_log_missing_chart_uid()` logs through the module logger and prints to stderr with the chart name and failed context.

Important implementation locations:

- `_chart_prediction_cache_uid()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`
- `_chart_prediction_cache_identity()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`
- `_log_missing_chart_uid()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`
- `DndPredictionPanelAdapter._norm_charts_cache_token()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`

### 9. Include chart state in statblock cache validation

File: `ephemeraldaddy/gui/features/charts/dnd_predictions.py`

A review concern identified that statblock cache keys initially included norm/stat-key data but not chart birth/place/house state.

To fix that:

- `_chart_state_cache_token(chart)` was added.
- It uses `owner._chart_analytics_cache_token(chart)` when available.
- If that app-level token is unavailable, it builds a UID-based chart-state payload including:
  - UID,
  - chart name,
  - local datetime,
  - birth place,
  - latitude,
  - longitude,
  - `birthtime_unknown`,
  - `retcon_time_used`,
  - `retcon_hour`,
  - `retcon_minute`,
  - and `chart_uses_houses`.
- `_statblock_cache_key(norm_charts, chart)` now includes this chart-state token.
- Recalculate with `allow_stale=False` therefore recomputes when the chart changes, even if the database norm token does not.

Important implementation locations:

- `DndPredictionPanelAdapter._chart_state_cache_token()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`
- `DndPredictionPanelAdapter._statblock_cache_key()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`
- `DndPredictionPanelAdapter._statblock_cache_is_stale()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`
- `DndPredictionPanelAdapter._score_statblock()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`

### 10. Display cached/stale D&D results by default and show a Recalculate button

File: `ephemeraldaddy/gui/features/charts/dnd_predictions.py`

D&D rendering was updated so cached results display by default when available.

Behavior:

- If statblock cache exists, the statblock chart renders.
- If that cache is stale, a stale notice is inserted at the top of the section.
- If alignment cache exists, the alignment chart renders.
- If alignment cache is stale, a stale notice is inserted at the top of that subsection.
- Only sections with no prior cache show the `No prior data. Calculate (can take awhile)?` prompt.

The stale notice now uses a real `QPushButton("Recalculate")` styled consistently with the existing `Calculate!` button.

Important implementation locations:

- `DndPredictionPanelAdapter._show_stale_recalculate_notice()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`
- `DndPredictionPanelAdapter.render()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`

### 11. Make alignment stale-cache behavior explicit

File: `ephemeraldaddy/gui/features/charts/dnd_predictions.py`

A concern was raised that alignment breakdown/debug paths might silently reuse stale values.

The final behavior makes this intentional and explicit:

- Display paths pass `allow_stale=True`.
- Fresh metadata refreshes pass `allow_stale=False`.

Important implementation locations:

- `_dnd_alignment_score_parts(..., allow_stale=...)` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`
- `dnd_alignment_deviations(..., allow_stale=...)` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`
- `build_dnd_alignment_breakdown_html()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`
- `build_dnd_alignment_debug_summary_html()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`
- `draw_dnd_alignment_grid()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`
- `DndPredictionPanelAdapter.cache_alignment_metadata()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`

### 12. Render Chart View Traits from persisted chart trait metadata first

File: `ephemeraldaddy/gui/features/charts/trait_predictions.py`

The broader Predictions-panel concern included Traits. The current design is intentionally metadata-first rather than rendered-HTML-cache-first.

Current behavior:

- `render_traits_predictions()` calls `trait_metadata_for_chart(owner, chart, cached_only=True)` before showing the manual Calculate prompt.
- If persisted `chart_trait_metadata` exists and is fresh, the Traits section renders it immediately.
- If persisted `chart_trait_metadata` exists but is stale, the Traits section still renders it immediately and prepends the stale/Recalculate notice.
- If no persisted metadata exists, the Traits section shows the manual `Calculate!` prompt.
- The rendered-HTML in-memory view cache path was removed so the panel does not silently display a phantom secondary cache when materialized metadata is missing.
- When the user calculates/recalculates, `trait_metadata_for_chart(owner, chart)` performs the calculation and persists rows back to `chart_trait_metadata` by chart UID and trait UID.

Important implementation locations:

- `render_traits_predictions()` in `ephemeraldaddy/gui/features/charts/trait_predictions.py`
- `trait_metadata_for_chart()` in `ephemeraldaddy/gui/features/charts/trait_predictions.py`
- `db.get_chart_trait_metadata()` in `ephemeraldaddy/core/db.py`
- `db.upsert_chart_trait_metadata()` in `ephemeraldaddy/core/db.py`

### 13. Shared Traits/Predictions cache architecture

Files:

- `ephemeraldaddy/gui/features/charts/database_analytics.py`
- `ephemeraldaddy/gui/features/charts/trait_predictions.py`
- `ephemeraldaddy/gui/features/charts/dnd_predictions.py`

The current Predictions architecture has three related but distinct trait-data layers:

1. **`.traits_distribution_likelihood_cache`**
   - Owned by Database Analytics.
   - Stores reusable per-chart/per-analytical-profile trait likelihoods.
   - Uses chart tokens and compact profile entries so small chart/trait edits can update incrementally instead of forcing a full database recalculation.
   - Shared by Database Analytics, Chart View Traits, and D&D Alignment via `_collect_traits_distribution_analytics()` / `trait_likelihoods_with_distribution_cache()`.

2. **`.database_norms_cache`**
   - Stores DB-level trait averages and norm signatures.
   - Used by `_database_trait_averages()` and `_database_norm_signature_for_traits()`.
   - Should be keyed by analytical trait profile/UID rather than display-only fields so renames/recolors do not force rescoring.

3. **`chart_trait_metadata`**
   - Stores materialized per-chart/per-trait results by chart UID and trait UID.
   - This is the first-read source for Chart View Traits.
   - Rows include likelihood, DB average, deviation, direction, trait signature, norm signature, and chart signature.
   - Fresh rows render immediately; stale rows render with a Recalculate notice; absent rows show Calculate.

Rendered HTML is not a durable Predictions cache. If rendered output exists but `chart_trait_metadata` does not, that is a consistency problem to repair or expose, not a reason to maintain a second fallback architecture.

Important implementation locations:

- `_collect_traits_distribution_analytics()` in `ephemeraldaddy/gui/features/charts/database_analytics.py`
- `_load_traits_distribution_likelihood_cache()` in `ephemeraldaddy/gui/features/charts/database_analytics.py`
- `_save_traits_distribution_likelihood_cache()` in `ephemeraldaddy/gui/features/charts/database_analytics.py`
- `trait_likelihoods_with_distribution_cache()` in `ephemeraldaddy/gui/features/charts/trait_predictions.py`
- `_database_trait_averages()` in `ephemeraldaddy/gui/features/charts/trait_predictions.py`
- `_database_norm_signature_for_traits()` in `ephemeraldaddy/gui/features/charts/trait_predictions.py`
- `trait_metadata_for_chart()` in `ephemeraldaddy/gui/features/charts/trait_predictions.py`
- `_dnd_alignment_score_parts()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`

### 14. D&D Statblock DB norm reuse is separate from trait likelihood caching

Files:

- `ephemeraldaddy/analysis/dnd/dnd_stat_calculator.py`
- `ephemeraldaddy/analysis/dnd/dnd_class_axes_v2.py`
- `ephemeraldaddy/gui/features/charts/dnd_predictions.py`

D&D Statblock scoring is not trait-profile likelihood scoring. It uses D&D stat predictors and DB-relative stat norm averages. Therefore, Statblock should not be forced into `.traits_distribution_likelihood_cache` unless the statblock system is redesigned around trait-like analytical profiles.

Current behavior:

- The GUI resolves DB norm stat averages once for the norm cohort.
- `score_dnd_statblock()` accepts precomputed `db_norm_averages` and uses them rather than recalculating the same norm cohort again.
- Cached statblock payloads store the DB norm averages that produced the displayed statblock.
- Popout explainers use the stored DB norm averages so stale statblocks are explained against the same norm snapshot that produced them.

Important implementation locations:

- `score_dnd_statblock()` in `ephemeraldaddy/analysis/dnd/dnd_stat_calculator.py`
- `score_dnd_statblock()` wrapper in `ephemeraldaddy/analysis/dnd/dnd_class_axes_v2.py`
- `DndPredictionPanelAdapter._score_statblock()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`
- `build_dnd_statblock_popout_info_html()` in `ephemeraldaddy/gui/features/charts/dnd_predictions.py`

## Known testing notes from the implementation cycle

The focused D&D stat normalization tests passed during development:

```bash
PYTHONPATH=/workspace/ephemeraldaddy pytest tests/test_dnd_stat_normalization.py -q
```

Python compilation checks were run on the modified files:

```bash
python3 -m py_compile ephemeraldaddy/core/db.py ephemeraldaddy/gui/features/charts/dnd_predictions.py ephemeraldaddy/gui/features/charts/trait_predictions.py
```

`git diff --check` also passed.

A broader source-layout test command continued to fail on existing unrelated source-layout assertions:

```bash
PYTHONPATH=/workspace/ephemeraldaddy pytest tests/test_chart_view_right_panel_layout_source.py tests/test_dnd_stat_normalization.py -q
```

The failing assertions referenced existing source expectations in:

- `tests/test_chart_view_right_panel_layout_source.py`
- `ephemeraldaddy/gui/app.py`
- `ephemeraldaddy/gui/features/charts/cv_right_panel_stack.py`
- `ephemeraldaddy/gui/features/controllers/chart_view_window.py`

Those failures were not introduced by the D&D cache/explainer work, but they remained present during the focused verification runs.

## Remaining caveats / follow-up ideas

1. **Automated tests for DB persistence should be added.**
   - The new `chart_dnd_prediction_metadata` table and statblock JSON round-trip helpers should have direct unit tests.

2. **GUI stale-notice behavior should be integration-tested.**
   - Especially the “cached results render first, Recalculate appears at top” behavior.

3. **UID-missing cases should be intentionally exercised.**
   - Now that ID fallback is removed, test coverage should verify the loud terminal message and absence of silent fallback behavior.

4. **Traits persistence/display behavior may need deeper UX testing.**
   - Traits now render materialized `chart_trait_metadata` immediately when possible. The long-term solution should continue strengthening that metadata/cache flow, not adding a durable rendered-HTML cache.

5. **Cache invalidation workflows should be audited around trait/profile edits.**
   - Display-only trait edits should not force rescoring. Analytical profile edits should invalidate affected profile likelihoods and downstream chart metadata for that trait.
