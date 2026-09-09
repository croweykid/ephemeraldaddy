# Personal Timeline Integration Cleanup — Codex Handoff

**Status:** Deferred architectural cleanup after PR #2243 lands.  
**Primary owner:** `ephemeraldaddy/gui/features/transits/`  
**Primary goal:** Finish decomposing the remaining `personal_timeline_core.py` implementation bucket into explicit generation/window owners without moving feature implementation into `app.py`, without reintroducing runtime class mutation, and without regressing cache/thread/timezone semantics.

---

## 1. Why this handoff exists

Personal Timeline was introduced quickly as an empirical transit-research workflow and then expanded with:

- broad filterable transit generation;
- Library of Ghosts event comparison;
- permanent per-chart caching;
- asynchronous cache I/O;
- sortable table headers;
- process-safe cache worker shutdown.

PR #2243 removed the worst transitional mechanisms that existed during the first extraction:

- no `sys.modules[__name__] = ...` module substitution;
- no import-time mutation of `PersonalTimelineWindowWidget`;
- no `install_personal_timeline_persistence(...)` method replacement;
- no `install_personal_timeline_sorting(...)` method replacement.

The remaining architectural debt is narrower: `personal_timeline_core.py` still combines generation/model logic and the base Qt window implementation. The next Codex task is to finish that ownership split safely.

This is a good Codex task because `app.py` is large and undergoing a staged refactor. The work requires broad caller inventory and careful integration review, but it must remain a bounded Transit-workflow migration rather than becoming another general `app.py` rewrite.

---

## 2. Read before editing

Read, in this order:

1. `AGENTS.md`
2. `agents/app_py_refactor_manifesto.md`
3. this handoff
4. current `main` versions of:
   - `ephemeraldaddy/gui/features/transits/personal_timeline.py`
   - `ephemeraldaddy/gui/features/transits/personal_timeline_core.py`
   - `ephemeraldaddy/gui/features/transits/personal_timeline_persistence.py`
   - `ephemeraldaddy/gui/features/transits/personal_timeline_sorting.py`
   - `ephemeraldaddy/gui/features/transits/personal_timeline_filters.py`
   - `ephemeraldaddy/gui/features/transits/personal_timeline_analysis.py`
   - `ephemeraldaddy/gui/features/transits/personal_timeline_results.py`
   - `ephemeraldaddy/gui/features/transits/cache.py`
   - `ephemeraldaddy/gui/window_chrome.py`
   - `tests/test_personal_timeline*.py`
   - `.github/workflows/personal-timeline-tests.yml`
5. inspect current `app.py` only for relevant Transit/window integration points; do not treat the whole file as migration scope.

The refactor manifesto is authoritative. In particular:

- `app.py` should converge toward application/window orchestration only;
- feature implementation belongs in workflow-first packages;
- compatibility aliases and runtime callback injection are transitional patterns, not destinations;
- line-count reduction by itself is not a successful refactor;
- preserve performance, behavior, UID integrity, threading safety, and existing tests.

---

## 3. Current architecture after PR #2243

Verify this against current `main` before editing because filenames may have moved.

### `personal_timeline.py`

This is now the real public integration module.

It owns:

- the public `PersonalTimelineWindowWidget` subclass;
- composition of `PersonalTimelinePersistenceController`;
- cache-hit/cache-miss lifecycle integration;
- sortable-header wiring;
- close guard preventing a late cache miss from launching generation;
- `open_personal_timeline_for_window(...)` used by window chrome;
- a small explicit public re-export surface for Timeline dataclasses/generation API.

Important: this module must remain an explicit owner. Do not convert it back into a facade that mutates or replaces another module at import time.

### `personal_timeline_core.py`

This is the remaining transitional implementation bucket.

It currently owns both:

1. generation/model behavior, including Timeline transit/window dataclasses, timeline bounds, broad candidate generation, boundary refinement, etc.; and
2. base Qt window behavior, including selection resolution, generation worker, filtering UI, population, results opening, and base close behavior.

This mixed ownership is the principal cleanup target.

### `personal_timeline_persistence.py`

Owns persistence infrastructure:

- `PersonalTimelinePersistenceController`;
- permanent-cache read/write workers;
- off-GUI-thread JSON parsing/reconstruction;
- off-GUI-thread serialization/write/flush/`fsync`/atomic replace;
- cache-window reconstruction;
- application-shutdown coordination for active cache jobs;
- restoration of cached window endpoints into the chart's timezone rule set.

It must not mutate the Timeline widget class globally.

### `personal_timeline_sorting.py`

Owns typed sorting logic only:

- sort keys;
- sort ordering;
- header-click state transitions.

It must not install methods onto a widget class.

### `cache.py`

Owns the permanent Timeline disk format and cache fingerprint.

The fingerprint includes transit-relevant chart data and **timezone identity**, not merely the birth instant's numeric UTC offset.

### `window_chrome.py`

Owns the lazy UI hook for opening Personal Timeline from the appropriate top-level window context.

It should call a canonical Timeline open function; it should not own Timeline implementation.

---

## 4. End-state architecture

The preferred bounded destination is:

```text
ephemeraldaddy/gui/features/transits/
    personal_timeline.py                # small public integration/export surface, if still useful
    personal_timeline_generation.py     # pure/non-Qt generation + data models
    personal_timeline_window.py         # Qt window + opener + generation worker orchestration
    personal_timeline_persistence.py    # explicit persistence collaborator/workers
    personal_timeline_sorting.py        # typed sorting helpers/state
    personal_timeline_filters.py
    personal_timeline_analysis.py
    personal_timeline_results.py
    cache.py
```

Exact filenames may differ if the Transit package has gained a stronger convention by then. Preserve these ownership boundaries regardless of spelling.

### Generation owner

Move non-widget logic out of `personal_timeline_core.py`, including where appropriate:

- `TimelineTransitDefinition`;
- `PersonalTimelineWindow`;
- Timeline-generation constants;
- broad candidate construction;
- aspect/orb calculations;
- ephemeris boundary helpers;
- death/timeline bounds;
- continuous-window detection;
- boundary refinement;
- `generate_personal_timeline(...)`.

This module should not import Qt widgets.

### Window owner

Own explicitly:

- authoritative Chart UID selection/open behavior;
- Timeline generation `QThread` worker if still needed;
- Timeline window construction;
- filter controls and filter-state orchestration;
- rendering/population;
- results-window opening;
- cache lifecycle coordination via an explicit persistence collaborator;
- sorting lifecycle via direct instance wiring or a small explicit sort-state collaborator;
- close behavior.

### `app.py`

The desired outcome is **not** to move Timeline code into `app.py`.

At most, `app.py` may contain a very small explicit startup/window-integration call if the current architecture genuinely requires it. Prefer zero `app.py` changes if `window_chrome.py` and the Transit package can own the integration cleanly.

Do not add:

- Timeline calculations;
- cache workers;
- Timeline widget methods;
- filter logic;
- sorting logic;
- Library of Ghosts analysis;
- Timeline persistent state

to `app.py`.

---

## 5. Non-negotiable behavioral invariants

The migration is not successful if any of these regress.

### 5.1 Broad empirical generation remains broad

Personal Timeline is a research tool, not a fixed doctrinal “major transits” report.

Preserve:

- broad candidate generation before display filtering;
- asteroids and Lilith unless explicitly filtered by the user;
- minor aspects unless explicitly filtered;
- outer-to-outer/cohort cycles, labeled rather than silently discarded;
- existing dominance relevance integration;
- filter rerenders without regenerating ephemerides.

Do not introduce a new hidden “traditional importance” filter during architectural cleanup.

### 5.2 Stable Chart UID remains authoritative

Use `chart_uid` for:

- public Timeline identity;
- cache identity;
- window routing;
- analysis linkage.

Do not introduce numeric SQLite row IDs into new Timeline public APIs.

### 5.3 Cache reads and writes remain off the GUI thread

For potentially large Timeline caches:

- file read occurs off GUI thread;
- JSON parse occurs off GUI thread;
- cached-window reconstruction occurs off GUI thread;
- serialization occurs off GUI thread;
- file write/flush/`fsync` occurs off GUI thread;
- atomic replacement occurs off GUI thread;
- only decoded results/status and UI mutation return to GUI thread.

Do not simplify the architecture by making cache I/O synchronous again.

### 5.4 Application shutdown drains cache workers

Cache jobs are process-lifetime work, not child-window-lifetime work.

Preserve all of these:

1. active cache worker threads remain strongly referenced until completion;
2. application shutdown waits for active cache jobs before Qt teardown returns;
3. do not allow `QThread: Destroyed while thread is still running`;
4. do not use `QThread.terminate()` during cache writes;
5. allow an atomic write to finish normally or leave the prior cache intact;
6. closing an individual Timeline window must not shut down unrelated cache jobs.

If EphemeralDaddy later gains an appwide background-job coordinator, Timeline cache workers may migrate to it only if these semantics remain intact.

### 5.5 Close-during-lookup behavior remains safe

If the user closes Personal Timeline while a cache lookup is in flight:

- the read may finish safely in the background;
- a late cache miss must **not** start a new ephemeris-generation worker;
- a late cache hit must not mutate a destroyed/closing window;
- closing one Timeline must not block unrelated Timeline windows.

### 5.6 Cache fingerprinting must include timezone rules

This is calculation correctness, not presentation metadata.

A named timezone is more than its UTC offset at birth. For example, two IANA zones may both be `-05:00` on the birth date while following different DST rules later. Those zones can generate different local Timeline endpoints over a lifetime.

Therefore preserve this invariant:

> Cache identity must distinguish named timezone rule sets, not merely the ISO birth datetime and its current numeric offset.

The current cache fingerprint records timezone identity (e.g. the IANA `ZoneInfo.key`) in addition to the ISO birth datetime.

A future refactor must not collapse this back to `birth_datetime.isoformat()` alone.

### 5.7 Cached endpoints must be restored into the chart timezone

Cache window `start`/`end` strings contain numeric offsets, but ISO 8601 does not preserve an IANA timezone rule set.

`datetime.fromisoformat(...)` therefore reconstructs fixed-offset `tzinfo` objects. If those are used directly, a window spanning a DST transition can have different arithmetic after cache reload than it had immediately after generation.

Example invariant:

```text
America/New_York
2026-03-07 12:00 -05:00
through
2026-03-09 12:00 -04:00
```

A freshly generated window using the shared `ZoneInfo("America/New_York")` has two local calendar days of Timeline duration semantics. Restoring the two ISO endpoints as independent fixed offsets changes subtraction to 47 elapsed hours.

Therefore:

1. parse cached endpoints as aware datetimes;
2. treat the persisted offset as the instant-disambiguation data;
3. convert each endpoint back into the selected chart's `dt.tzinfo` before constructing `PersonalTimelineWindow`;
4. reject offset-free cached endpoints as malformed;
5. keep both endpoints under the same chart timezone rule object for midpoint/duration semantics.

This matters to:

- `duration_days`;
- midpoint-based Age sorting;
- overlap/exposure calculations;
- randomized/background analysis;
- any future exact-hit/event alignment using Timeline window bounds.

Do not “normalize everything to fixed UTC offsets” unless the entire Timeline generation/analysis model is deliberately redesigned and all semantics/tests are updated together.

### 5.8 Existing caches may miss after timezone-fingerprint changes

That is acceptable and intentional.

Correct regeneration is preferable to reusing a cache whose timezone-rule identity was never represented in the fingerprint.

Do not add backward-compatibility code that guesses a named timezone from a numeric offset.

### 5.9 Cache invalidation remains selective

Transit-relevant changes must miss/regenerate, including:

- birth datetime;
- named timezone identity/rules;
- birth location where relevant;
- natal positions;
- birth-time/rectification state affecting astronomy;
- death bounds;
- candidate bodies;
- aspect/orb configuration;
- scan/boundary refinement configuration;
- explicit Timeline algorithm version.

Do not invalidate solely for unrelated metadata such as comments.

### 5.10 Sorting remains typed

All seven columns remain sortable:

- Age — numeric;
- Transit — text;
- Scope — text;
- Chart relevance — semantic/text representation;
- Start — datetime;
- End — datetime;
- Duration — numeric.

Repeated click on the same column reverses direction. Clicking a different column begins ascending. Sorting remains active after filter rerender.

### 5.11 Library of Ghosts analysis semantics remain intact

Preserve:

- schema validation;
- partial/fuzzy dates without false precision;
- peak → begin → end anchor preference;
- observed overlap vs background exposure;
- exact-hit proximity analysis;
- randomized expectation;
- current event-place metadata even when not yet consumed by location-sensitive transit calculations.

If event time is unknown, do not manufacture a clock time for exact short-duration matching.

---

## 6. Required Codex procedure

Perform this as a dedicated architectural PR from current `main` after #2243 is merged.

### Phase 0 — baseline

1. Confirm #2243 (or equivalent final implementation) is merged.
2. Re-read current `main`; do not work from this handoff's historical assumptions alone.
3. Run the focused Personal Timeline suite.
4. Record baseline pass count and runtime.
5. Confirm no unrelated failures before moving code.

### Phase 1 — inventory every caller

Search the repository for:

```text
personal_timeline
personal_timeline_core
PersonalTimelineWindowWidget
PersonalTimelinePersistenceController
open_personal_timeline_for_window
generate_personal_timeline
TimelineTransitDefinition
PersonalTimelineWindow
_ACTIVE_CACHE_JOBS
shutdown_personal_timeline_cache_jobs
personal_timeline_sorting
```

Classify each occurrence as:

- production caller;
- test caller;
- documentation;
- compatibility residue;
- duplicate/obsolete owner.

Pay particular attention to:

- `window_chrome.py`;
- `app.py`;
- Chart Editor and Database View window routing;
- `tests/test_personal_timeline*.py`;
- packaging/startup imports;
- any Transit bootstrap code added after this document.

### Phase 2 — strengthen characterization before moving code

Before extraction, retain/add tests for at least:

1. Database View requires exactly one selected Chart UID.
2. Chart Editor resolves the current Chart UID correctly.
3. public Timeline window is an explicit class, not an alias/mutated base.
4. import order does not determine whether persistence/sorting exists.
5. cache lookup begins on integrated window startup.
6. cache hit renders without launching generation.
7. cache miss starts generation exactly once.
8. successful generation schedules one cache write.
9. failed/interrupted generation does not replace a good cache.
10. read/parse/reconstruction executes off GUI thread.
11. write/serialize/flush/`fsync` executes off GUI thread.
12. close during cache read does not later launch generation.
13. application shutdown drains an in-flight cache worker.
14. no active cache QThread remains after shutdown coordination.
15. all seven sorting columns preserve typed behavior.
16. sort direction survives filter rerenders.
17. cached DST-crossing windows retain the chart's named timezone and same `duration_days`/midpoint semantics as freshly generated windows.
18. fingerprint differs for two named zones that share the same offset at birth but have different rule identities.

Tests should describe required behavior rather than preserve obsolete internal names.

### Phase 3 — extract generation/model logic

Create `personal_timeline_generation.py` (or repository-equivalent name) first.

Move generation/data logic with minimal semantic edits.

Update generator-focused tests to import the generation owner directly.

Do not combine this structural move with astrology-formula changes.

Suggested commit:

```text
Extract Personal Timeline generation model
```

### Phase 4 — establish explicit window owner

Move base Qt window behavior out of `personal_timeline_core.py` into `personal_timeline_window.py` or equivalent.

The window owner should import generation APIs explicitly rather than importing a generic `_core` module.

Keep the persistence controller as an explicit collaborator.

Keep sorting as direct instance behavior/helper calls.

Suggested commit:

```text
Move Personal Timeline window orchestration to explicit owner
```

### Phase 5 — retire `personal_timeline_core.py`

Only delete/retire the old core module after:

- every production import has moved;
- every test import has moved;
- no hidden circular-import workaround depends on it;
- public Timeline entry points remain stable or are intentionally migrated in the same PR.

Do not leave a permanent `personal_timeline_core.py` forwarding facade unless there is a genuine external/public compatibility requirement. Internal callers should migrate completely.

Suggested commit:

```text
Remove transitional Personal Timeline core module
```

### Phase 6 — inspect `app.py` integration

After the Transit package owns itself cleanly, inspect `app.py` for any remaining Timeline-specific behavior.

If there is none: make no `app.py` change.

If a tiny orchestration hook remains necessary:

- keep it narrow;
- use explicit function/class imports;
- do not make the whole window an implicit service locator;
- do not add runtime callback installation;
- do not move feature state into `app.py`.

### Phase 7 — CI and final review

Run the focused Timeline suite and inspect the final PR diff manually.

Also verify:

- branch is current with `main`;
- no duplicate classes/functions remain;
- no runtime class mutation was reintroduced;
- no synchronous cache I/O slipped into GUI callbacks;
- no cache-worker shutdown gap was introduced;
- timezone identity is still part of the fingerprint;
- cached endpoints are still converted to chart `tzinfo` before `PersonalTimelineWindow` construction;
- workflow path filters include any renamed/moved Timeline files.

---

## 7. Explicit non-goals for this migration

Do **not** combine the architecture cleanup with:

- new astrology scoring systems;
- new aspect taxonomies;
- dropping asteroids/minor aspects/cohort cycles;
- redesigning Library of Ghosts statistics;
- changing randomization methodology;
- changing the default Timeline lifespan;
- unrelated Settings refactors;
- broad Database View refactors;
- general `app.py` cleanup outside the exact integration boundary;
- replacing PySide6/Qt;
- redesigning cache file format unless required by a demonstrated bug.

If such work is discovered, document it separately.

---

## 8. Definition of done

The future Codex migration is complete when all are true:

- `personal_timeline_core.py` no longer acts as a mixed generation/window owner;
- generation logic has an explicit non-widget owner;
- Timeline Qt orchestration has an explicit window owner;
- the public Timeline import path is simple and understandable;
- no `sys.modules` tricks exist;
- no Timeline runtime class monkeypatch installers exist;
- persistence remains explicit composition;
- sorting remains explicit instance behavior/helper logic;
- `app.py` contains at most narrow orchestration, preferably none for this feature;
- stable Chart UID remains authoritative;
- broad research-candidate behavior is unchanged;
- cache read/write remains asynchronous;
- application exit safely drains active cache workers;
- cache fingerprint distinguishes named timezone rules;
- cached endpoints restore into chart timezone before duration/midpoint/analysis use;
- DST-crossing cache hit results are semantically equivalent to freshly generated windows;
- existing filtering, results, and Library of Ghosts analysis continue to work;
- focused CI passes;
- final branch is reconciled with `main`;
- the PR contains no unrelated architectural churn.

The end goal is straightforward: **Personal Timeline should be a normal, explicitly owned Transit workflow with transparent module boundaries, safe background persistence, stable timezone semantics, and minimal top-level application coupling.**
