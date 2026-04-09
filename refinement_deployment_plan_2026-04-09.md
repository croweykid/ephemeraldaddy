# Refinement & Reliability Deployment Plan (2026-04-09)

This document captures concrete inefficiency/bug risk hotspots and a phased hardening plan that preserves current behavior while reducing freezes and maintenance risk.

## Highest-risk hotspots (behavioral risk + performance risk)

1. **Blocking network operations on the GUI thread (Astrotheme import)**
   - `_on_import_astrotheme_from_search_panel()` calls `search_astrotheme_profile_url()` and `parse_astrotheme_profile()` synchronously.
   - `search_astrotheme_profile_url()` can execute many HTTP calls (`astrotheme`, `duckduckgo`, `bing`) with 20s timeout each.
   - Risk: long UI stalls / “app frozen” perception.

2. **Expensive gazetteer bootstrap can happen in user-initiated location search path**
   - `search_locations()` calls `resolve_search_sources()`.
   - `resolve_search_sources()` calls `get_local_gazetteer()`, which may build/download DB if absent.
   - Risk: first-time search action can block for a long time; remote download/build can look like hang.

3. **Cache can pin transient load failures indefinitely in main chart filter path**
   - `_get_chart_for_filter()` caches `None` when `load_chart()` raises.
   - Risk: transient error becomes sticky; chart appears permanently missing until cache invalidation.

4. **Large single-method responsibilities amplify regression risk**
   - `_update_sentiment_tally()` has broad responsibility (selection, DB cache refresh, analytics collection, section state/UI updates).
   - The method’s size and branching makes safe edits difficult.

5. **Overly broad exception swallowing in hot paths**
   - Multiple broad `except Exception` paths suppress detail or continue silently.
   - Risk: hard-to-diagnose regressions, latent data errors, and performance blind spots.

## Sloppiest code areas (most likely to create accidental regressions)

1. **`MainWindow` construction and panel-build methods with mixed concerns**
   - UI creation, data wiring, side effects, and application state updates are interleaved.

2. **Transit popout worker orchestration closure cluster**
   - Worker lifecycle, caching, UI text rendering, and click metadata are deeply interwoven in one method.
   - Hard to reason about shutdown guarantees and race behavior.

3. **Formatting/domain/helper logic embedded across UI event methods**
   - Similar computations are repeated in nearby analysis paths.

## Deployment sequence (low-risk, behavior-preserving)

### Phase 0 — Safety rails first (no behavior change)
1. Add structured debug logging around every broad `except Exception` in the top 5 busiest flows:
   - filter refresh,
   - chart load/cache,
   - Astrotheme import,
   - transit worker callbacks,
   - geocode search.
2. Introduce a `debug_id` correlation token per user action to trace multi-step operations.
3. Add a tiny “UI latency logger” utility to record handlers exceeding 150ms.

### Phase 1 — Remove visible freezes
1. Move Astrotheme import lookup+parse into a worker thread.
2. Keep identical dialogs/messages, but add:
   - progress/cancel,
   - stale-result guard (ignore worker result if panel state changed).
3. Prewarm gazetteer asynchronously at startup (best effort), while preserving current fallback behavior.

### Phase 2 — Correctness hardening
1. Change chart cache semantics from `chart | None` to a richer status object:
   - success cache with TTL,
   - failure cache with short retry window,
   - explicit error class.
2. Ensure transient failures do not become permanent `None` entries.
3. Add explicit invalidation on DB restore/import/update paths.

### Phase 3 — Complexity reduction by seam extraction (without changing outcomes)
1. Split `_update_sentiment_tally()` by *responsibility seams* only:
   - snapshot collection,
   - analytics collection,
   - metric section projection,
   - widget application.
2. Keep a single orchestrator method with unchanged signature and call order.
3. Add snapshot-based unit tests that compare old vs new outputs from the same fixture chart sets.

### Phase 4 — Transit popout stability cleanup
1. Extract worker lifecycle into a dedicated coordinator class:
   - spawn,
   - cancel,
   - shutdown barrier,
   - bounded queue scheduling.
2. Keep current UI text format + cache keys unchanged to preserve behavior.
3. Add deterministic tests for:
   - close-while-running,
   - repeated open/close,
   - cancellation race with completion.

### Phase 5 — Legibility + maintainability pass
1. Replace repeated literal fallback dicts with typed defaults/helpers.
2. Normalize helper naming and narrow local scopes for nested closures.
3. Introduce small immutable dataclasses for intermediate analysis payloads.

## Error-prevention strategy during extraction (specific safeguards)

- **Extract + delegate + verify** only:
  1) move code,
  2) call moved code from old entry point,
  3) compare outputs,
  4) remove duplicate.
- Use **golden output snapshots** for textual summaries and sorted list outputs.
- Preserve event ordering with explicit tests around QTimer/QThread boundaries.
- Add “canary assertions” for invariants:
  - selection IDs stability,
  - cache key determinism,
  - sentinel defaults shape.
- Keep one toggle/env flag to fallback to legacy path for one release if needed.

## Success metrics

- 95th percentile interactive action latency reduced for:
  - Astrotheme import start-to-feedback,
  - first location search,
  - filter refresh on large datasets.
- Zero change in deterministic chart outputs for regression fixture set.
- Reduced uncategorized broad exception count in critical paths.
