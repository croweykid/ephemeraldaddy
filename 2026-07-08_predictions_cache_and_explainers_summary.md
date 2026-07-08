# Predictions Cache and Explainers Summary v2 | last updated 2026-07-08 12:09:26 UTC

## Purpose

This document summarizes the Predictions-panel and Database Analytics cache work discussed on 2026-07-08, including what was wrong, what changed, and what still matters architecturally. The central goal is to make Predictions and related Database Analytics sections feel immediate, explainable, and reliable without repeatedly rescoring the entire database.

## Original problem

Chart View Traits felt dramatically slower than Enneagram predictions even though both ultimately use the same weighted criteria scoring engine. The investigation found that Traits was not merely scoring the current chart. It was also comparing the chart against database-wide Trait averages, and cold/stale norm paths could trigger broad Database Analytics collection or direct database-wide scoring.

The user clarified that this was not acceptable as an interactive Chart View behavior. DB norms should be persisted, stale-but-usable, and refreshed in the background or by explicit user action rather than rebuilt synchronously whenever a chart view needs them.

## Design principles agreed during discussion

### 1. Stale-but-usable cache values are acceptable

The app should prefer showing cached norms immediately, even if those norms are stale. Stale cache data is not automatically a crisis. The intended model is:

- fresh cache: use it normally;
- stale cache: still use it, but mark/log that it may be out of date;
- missing cache: compute only what is required, ideally in a background or explicit refresh path.

The user compared this to having a few spiders in the house: a few stale values are acceptable if they keep the app responsive, but they should not grow into an uncontrolled infestation where nothing ever refreshes.

### 2. DB norm freshness should be appwide

Database norm freshness should not be reinvented inside each panel. The app should use one policy for:

- current database chart count;
- saved snapshot chart count;
- changed/new/deleted chart UID count;
- 10% freshness threshold;
- stale-but-usable vs missing cache behavior.

### 3. Background/incremental refresh should replace full synchronous rescans

When charts are added, changed, or deleted, the app should prefer incremental refresh:

- queue changed chart UIDs;
- recompute affected chart payloads;
- recompute affected trait payloads only when analytical trait definitions change;
- continue serving old cache values until replacement values are committed.

### 4. Display edits should not invalidate analytical cache data

Trait name, color, description, and other display-only metadata should not force rescoring. Only changes to analytical/scoring factors should invalidate cached score payloads.

### 5. Chart View Predictions should be lightweight

Chart View should load Predictions immediately from cached values. If norms are stale, it should indicate that rather than blocking. Explicit recalculation should write back to the shared persistent norm cache so the effort benefits the rest of the app.

### 6. Debug logging should be clear and toggleable

Terminal debug logging for Predictions should be controlled in Settings > Dev Tools. When enabled, logs should make cache behavior explainable: section starts, cache keys, hits/misses, stale hits, queued background work, writes, recalculations, completion, and failures.

## Changes made across the PR sequence

### Shared database norms freshness module

A new helper module was added:

- `ephemeraldaddy/gui/features/charts/database_norms_cache.py`

It centralizes:

- appwide DB norms cache filename;
- 10% stale threshold constant;
- `DatabaseNormsFreshness` summary state;
- changed UID detection;
- database norm freshness calculation;
- analytical mapping signature cleanup for trait/profile-like payloads.

This was added to prevent each caller from inventing its own stale/fresh policy.

### Database Metrics persistent cache behavior

Database Metrics persistent-cache loading was changed so row-token differences no longer automatically reject the entire cache. Instead, the app now:

- loads the persisted cache when version/config are valid;
- computes current vs saved chart UID token changes;
- records the changed UID count and threshold;
- marks the cache stale when needed;
- queues changed current chart IDs for refresh;
- treats stale caches as refresh-needed on panel show;
- clears stale flags after full or incremental cache refresh.

A bug noted by the Codex editor was fixed: if the only difference was deleted charts, `_database_metrics_lucy_goosey_ids` could stay empty because deleted UIDs have no current chart ID. Database Metrics refresh-needed logic now checks the stale-cache flag too, so deleted charts do not linger in totals indefinitely.

### Trait DB norm cache behavior

Trait DB norm lookups now distinguish normal read behavior from explicit refresh behavior.

Normal Chart View usage:

- stale cached trait averages remain usable;
- stale values avoid blocking Chart View;
- debug logging notes stale norm use when Predictions debug logging is enabled.

Explicit warming/recalculation:

- `_database_trait_averages(..., force_refresh_stale=True)` treats stale cached traits as missing;
- `warm_trait_database_norms()` uses that forced-refresh path;
- refreshed values are persisted back to the norm cache.

This preserves the intended efficiency while preventing stale fully-cached trait norms from living forever when a refresh is requested.

### Trait analytical signatures

Trait scoring cache identity now strips display-only metadata. The shared analytical signature helper excludes fields such as:

- name;
- color;
- description;
- motivation;
- quotes;
- archived state;
- samples;
- optionally UID fields when needed.

This prevents name/color-only edits from invalidating analytical cache payloads.

### Database Analytics Trait Rankings cache reuse

Traits Distribution / Trait Rankings now uses analytical profile keys and an individual per-profile likelihood cache. This means cached scores can be reused after a trait rename or color change instead of rescoring chart+trait pairs unnecessarily.

The persisted cache still carries display data where useful for rendering, but score reuse is keyed by analytical profile when possible.

### Chart View Trait Predictions render flow

The Chart View Traits render path was changed so a cache miss does not synchronously compute metadata before showing anything. Instead:

- cached view data renders immediately when available;
- otherwise a loading/refresh message appears;
- Trait metadata and DB norm work is deferred to the existing background worker.

This reduces the chance that opening or switching to Chart View blocks on broad trait norm work.

### Database View Traits Distribution loading popup

The modal/progress loading bar for Database Analytics Traits Distribution was removed. This addressed the user-observed issue where changing chart selection while Trait Rankings was open caused a “Loading trait predictions…” loading bar, even when the section should repaint from cached values.

Traits Distribution now calls its render method directly from the Database Analytics refresh path without creating that modal progress UI.

### Predictions debug logging

A Dev Tools setting label was clarified from thread-only language to step-level Predictions debug logging. Debug helpers were added in relevant Predictions/Database Analytics modules to log cache and worker activity when enabled.

The goal is to make the terminal explain what is happening without forcing debug noise during normal use.

## Architectural status after these changes

### Improved

- Stale DB metrics caches remain usable instead of being thrown away.
- Deleted charts now cause stale Database Metrics caches to refresh.
- Trait DB norms can be stale for normal reads but refresh when explicitly warmed.
- Trait name/color edits do not force analytical rescoring.
- Trait Rankings can reuse profile-level cached likelihoods.
- Chart View Traits no longer tries to synchronously build metadata on a view-cache miss.
- Database View Traits Ranking selection changes no longer show the modal “Loading trait predictions…” progress bar.
- Cache freshness logic is more centralized than before.

### Still worth watching

The codebase still has multiple historical layers around Predictions, Database Analytics, background preload, and cache warming. The newest changes reduce redundant work and centralize freshness policy, but a future cleanup pass could still simplify:

- Predictions warmup orchestration;
- Database Analytics background preload sequencing;
- naming around “prediction norms,” “database metrics,” and “traits distribution” caches;
- explainability/logging consistency across every Predictions section;
- a single user-facing “DB norms may be out of date” status message pattern.

### Practical expectation

With these changes, the app should increasingly behave like this:

1. Load cached Predictions and Database Analytics data immediately when possible.
2. Use stale cache values when fresh values are not ready.
3. Refresh stale data in explicit or deferred paths.
4. Avoid full-database rescoring on routine chart selection changes.
5. Avoid modal progress UI unless the user explicitly initiates expensive work.

## Test/check coverage added or updated

Source and regression tests were added or updated for:

- stale Database Metrics persistent cache loading;
- stale-cache refresh-needed detection;
- absence of modal loading UI in Traits Distribution refresh;
- stale Trait norm reuse for normal reads;
- forced stale Trait norm recomputation;
- trait rename/color cache reuse;
- analytical signature behavior;
- Dev Tools Predictions debug label/source expectations.

Some direct tests that import `PySide6.QtWidgets` could not be executed in the current container because `libGL.so.1` is missing. Syntax checks and source-level tests were run successfully where possible.
