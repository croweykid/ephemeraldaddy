# Bug & Efficiency Audit (2026-03-23)

This note captures concrete, code-level issues that can cause freezes, unnecessary work, or brittle behavior, plus low-risk fixes that preserve current UX.

## 1) Astrotheme import can block the UI thread for a long time

### Why this is risky
- `search_astrotheme_profile_url()` performs multiple synchronous HTTP requests (Astrotheme + DuckDuckGo + Bing).
- `_astrotheme_http_get()` uses a 20-second timeout for each request.
- The import button handler calls this directly from the main window event path.

In bad network conditions, users can experience long UI stalls.

### Evidence
- `urlopen(..., timeout=20)` in `_astrotheme_http_get()`.  
  (`ephemeraldaddy/gui/astrotheme_search.py`)
- Multi-source search in `_collect_astrotheme_search_candidates()` and `_collect_web_search_candidates()`.  
  (`ephemeraldaddy/gui/astrotheme_search.py`)
- Direct call on button action in `_on_import_astrotheme_from_search_panel()`.  
  (`ephemeraldaddy/gui/app.py`)

### Low-risk improvement
Move Astrotheme lookup+parse to a worker thread (Qt worker pattern already exists in the project). Keep the exact same UI behavior and outputs; only make the operation asynchronous with loading state + cancel support.

## 2) Swiss ephemeris readiness cache can become stale for newly requested bodies

### Why this is risky
`_SWE_DATA_READY` is a single global boolean. Once set `True` for one required body set, later calls with different required sets skip checks entirely.

That can produce subtle failures when a later feature requests a body whose data was never validated/downloaded.

### Evidence
- Early return when `_SWE_DATA_READY` is true.
- `_SWE_DATA_READY` is set based only on the current `required_bodies` argument.
- Different call sites pass different body sets (`planetary_longitude()` vs `planetary_positions()`).

All in `ephemeraldaddy/core/ephemeris.py`.

### Low-risk improvement
Replace `_SWE_DATA_READY: bool` with `_SWE_READY_BODIES: set[str]` and only skip checks when `required_bodies <= _SWE_READY_BODIES`.

## 3) Heavy astronomy data is loaded eagerly at import time

### Why this is inefficient
- `ts = load.timescale()` and `eph = load('de421.bsp')` run at module import.
- This cost is paid even when callers only need lightweight helpers or UI flows unrelated to position calculations.

### Evidence
Top-level initialization in `ephemeraldaddy/core/ephemeris.py`.

### Low-risk improvement
Use lazy initialization (`get_timescale()`, `get_ephemeris()`) so heavy resources load only when actually needed. Cache the initialized objects so runtime behavior remains unchanged after first access.

## 4) Gazetteer bootstrap path may do expensive work during interactive search

### Why this is risky
Location search invokes `resolve_search_sources()`, which can trigger `get_local_gazetteer()`; if DB is missing, it may build from bundled data or attempt download/build.

If this happens during a user-initiated search interaction, it can block unexpectedly.

### Evidence
- `search_locations()` calls `resolve_search_sources()` in `ephemeraldaddy/io/geocode.py`.
- `resolve_search_sources()` calls `get_local_gazetteer()` in `ephemeraldaddy/io/local_gazetteer.py`.
- `get_local_gazetteer()` can call `build_db()` or `_download_and_build()`.

### Low-risk improvement
Do one-time async warmup at app startup (or first geocode use) and return quickly with online fallback while local DB is building.

## 5) Download/extract step uses full-file in-memory copy

### Why this is inefficient
`target.write(source.read())` copies the full file in memory before write.

### Evidence
In `_download_and_build()` (`ephemeraldaddy/io/local_gazetteer.py`).

### Low-risk improvement
Use `shutil.copyfileobj(source, target, length=1024 * 1024)` (or similar chunking) to reduce peak memory with no functional change.

## 6) Exception handling hides root causes in hot paths

### Why this hurts debuggability/perf tuning
Several hot paths use broad `except Exception` and proceed silently or with generic fallback. This can mask real regressions and make slow/failing branches harder to identify.

### Evidence
- `planetary_longitude()` and `planetary_positions()` swallow broad exceptions around ephemeris calculations (`ephemeraldaddy/core/ephemeris.py`).
- `_get_chart_for_filter()` catches any exception and stores `None` in cache (`ephemeraldaddy/gui/app.py`).

### Low-risk improvement
Keep user-facing behavior unchanged, but add debug logging (guarded by env flag) so operators can detect repeated failures and optimize bottlenecks with real signals.

## Suggested implementation order (highest impact first)
1. Async Astrotheme import workflow.
2. Fix Swiss ephemeris readiness cache semantics.
3. Lazy-load Skyfield timescale/ephemeris.
4. Async gazetteer bootstrap + non-blocking fallback.
5. Stream zip extraction writes.
6. Add debug logging for swallowed exceptions.
