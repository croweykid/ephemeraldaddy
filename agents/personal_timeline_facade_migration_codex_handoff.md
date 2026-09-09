# Personal Timeline Integration Cleanup — Codex Handoff

**Status:** The original compatibility-facade problem has now been corrected in PR #2243. This document describes the **remaining bounded architectural cleanup** that should happen later as part of the ongoing `app.py` refactor.  
**Primary prerequisite:** Start from updated `main` after PR #2243 (or its equivalent final changes) has merged. Re-read the current tree before editing; do not assume exact line numbers or filenames remain unchanged.  
**Primary architectural goal:** Finish making Personal Timeline a normal, explicitly owned Transit workflow without moving feature logic into `ephemeraldaddy/gui/app.py`. `app.py` should remain application/window orchestration only.

---

## 1. Read this first

Before changing code, read:

1. `AGENTS.md`
2. `agents/app_py_refactor_manifesto.md`
3. this handoff
4. the current versions of:
   - `ephemeraldaddy/gui/features/transits/personal_timeline.py`
   - `ephemeraldaddy/gui/features/transits/personal_timeline_core.py`
   - `ephemeraldaddy/gui/features/transits/personal_timeline_persistence.py`
   - `ephemeraldaddy/gui/features/transits/personal_timeline_sorting.py`
   - `ephemeraldaddy/gui/features/transits/personal_timeline_filters.py`
   - `ephemeraldaddy/gui/features/transits/personal_timeline_analysis.py`
   - `ephemeraldaddy/gui/features/transits/personal_timeline_results.py`
   - `ephemeraldaddy/gui/features/transits/cache.py`
   - `ephemeraldaddy/gui/window_chrome.py`
   - relevant Transit/app bootstrap code that exists at that time
   - `tests/test_personal_timeline*.py`
   - `.github/workflows/personal-timeline-tests.yml`

The `app.py` refactor manifesto is authoritative. Its relevant constraints are:

- `app.py` should ultimately be roughly 5,000–8,000 lines and should primarily orchestrate application/window lifecycles;
- workflow behavior belongs in explicit feature packages;
- runtime method injection and compatibility facades are transitional patterns only;
- shortening `app.py` is not itself success if ownership remains hidden;
- new controllers should not use an entire window as an arbitrary service locator;
- public chart identity should use stable `chart_uid`;
- extraction work must preserve performance, behavior, and shutdown correctness.

Do **not** use this task as permission to perform a broad unrelated `app.py` rewrite.

---

## 2. Historical problem and what PR #2243 now fixes

Earlier in PR #2243, `personal_timeline.py` temporarily acted as a compatibility facade over `personal_timeline_core.py`:

```python
install_personal_timeline_persistence(_core)
install_personal_timeline_sorting(_core)
sys.modules[__name__] = _core
```

That temporary arrangement existed because tests were monkeypatching generator internals through the historical `personal_timeline` module path and because cache/sorting behavior had initially been added as post-definition method installers.

Codex review correctly identified that this reintroduced two architectural problems:

1. feature behavior depended on import order and global class mutation;
2. the facade had an ambiguous lifetime/removal condition.

A later Codex review also identified a process-lifecycle problem with the async cache workers: parentless `QThread`s could still be running during application teardown.

### PR #2243 now changes this architecture

After the follow-up fixes, the intended state of #2243 is:

- `personal_timeline.py` is a **real public integration module**, not a `sys.modules` facade;
- there is no `sys.modules[__name__] = ...` substitution;
- persistence is not installed by assigning methods onto `PersonalTimelineWindowWidget`;
- sorting is not installed by assigning methods onto `PersonalTimelineWindowWidget`;
- the public `PersonalTimelineWindowWidget` explicitly subclasses the current core/base widget and directly owns cache/sort lifecycle integration;
- generator-internal tests import `personal_timeline_core` directly when they need to monkeypatch generator internals;
- `personal_timeline_persistence.py` exposes an explicit `PersonalTimelinePersistenceController` instead of an `install_*` function;
- cache read/reconstruction and write/serialization/flush/`fsync` remain off the GUI thread;
- cache QThreads are process-owned and coordinated with `QCoreApplication.aboutToQuit`;
- application shutdown waits for in-flight cache jobs to finish before Qt teardown can destroy a running thread;
- a late cache miss after the window closes still cannot launch a fresh ephemeris generation.

**Do not reintroduce the removed facade or installer architecture during later refactoring.**

---

## 3. Current ownership map after #2243

Verify this map against `main` before editing.

### `personal_timeline.py` — public integration owner

Expected responsibilities:

- public `PersonalTimelineWindowWidget`;
- explicit subclass/composition point for persistence and sorting;
- canonical `open_personal_timeline_for_window(...)` used by `window_chrome.py`;
- explicit exports of public Timeline model/generation names required by callers.

This is now a real module. It must not become another hidden facade later.

### `personal_timeline_core.py` — remaining transitional implementation bucket

Expected responsibilities still include too many things:

- timeline data classes;
- ephemeris generation;
- candidate transit construction;
- boundary refinement;
- date/death/timeline limits;
- selected-chart UID resolution;
- generation QThread worker;
- the current base `PersonalTimelineWindowWidget` implementation;
- filters/presentation glue;
- a legacy/core-level `open_personal_timeline_for_window(...)` that may now be redundant.

This file is the main remaining architectural cleanup target. The `_core` name is deliberately not the desired permanent owner.

### `personal_timeline_persistence.py` — cache lifecycle collaborator

Expected responsibilities:

- cache fingerprint configuration;
- cached-window reconstruction;
- asynchronous read/write worker types;
- process-owned cache job tracking;
- explicit application-shutdown draining;
- `PersonalTimelinePersistenceController`.

It must **not** mutate widget classes or depend on importing `personal_timeline.py` first.

### `personal_timeline_sorting.py` — pure-ish sorting policy/helper owner

Expected responsibilities:

- typed sort keys;
- ascending/descending toggle logic;
- sorting helper functions.

It must **not** install or replace widget methods at runtime.

### `cache.py`

Expected responsibilities:

- permanent Personal Timeline disk-cache schema/path;
- SHA-256 fingerprinting;
- JSON serialization/deserialization;
- atomic file replacement;
- `flush`/`fsync` behavior.

### `window_chrome.py`

Expected responsibility:

- a small lazy menu callback that imports the canonical Timeline opener;
- no Timeline calculation/cache/sorting logic.

### `app.py`

Expected responsibility for this workflow:

- ideally none beyond existing application-level orchestration;
- if a Transit bootstrap is eventually necessary, `app.py` may invoke it explicitly, but must not own its implementation.

---

## 4. Remaining end goal

The next Codex migration is **not** “remove the facade”—that should already be done by #2243.

The remaining goal is to eliminate the ambiguous `personal_timeline_core.py` bucket and leave clear workflow ownership.

A reasonable target structure is:

```text
ephemeraldaddy/gui/features/transits/
    personal_timeline.py                 # optional canonical public API/re-exports
    personal_timeline_generation.py      # models + ephemeris generation
    personal_timeline_window.py          # concrete Qt window + opener
    personal_timeline_persistence.py     # cache controller/workers/shutdown integration
    personal_timeline_sorting.py         # typed row sort policy
    personal_timeline_filters.py
    personal_timeline_analysis.py
    personal_timeline_results.py
    cache.py
```

Exact names may change if the Transit workflow has been reorganized by then. Preserve these ownership boundaries even if names differ.

### Generation owner

Should contain non-window logic such as:

- `TimelineTransitDefinition`;
- `PersonalTimelineWindow`;
- `_timeline_transiting_bodies` or its public replacement;
- candidate-definition construction;
- aspect-orb math;
- boundary refinement;
- death/timeline bounds;
- `generate_personal_timeline(...)`;
- generation constants.

It may depend on ephemeris/astrology code but should not construct `QMainWindow`s or inspect arbitrary GUI owners.

### Window owner

Should contain:

- `PersonalTimelineWindowWidget`;
- generation-worker orchestration if still Qt-specific;
- explicit persistence collaborator construction;
- explicit sorting/header wiring;
- filtering controls/presentation orchestration;
- `open_personal_timeline_for_window(...)`;
- selected-chart resolution if that remains a UI/window concern.

### Persistence owner

Keep cache I/O and shutdown semantics explicit. Do not move them into the window just to reduce module count.

---

## 5. Critical invariants that must survive the migration

These are not optional cleanup details. Any refactor that breaks one of these is incomplete.

### 5.1 Cache reads and writes stay off the GUI thread

The following work must never be moved back into a QWidget completion handler:

- reading the cache file;
- parsing potentially large JSON;
- reconstructing thousands of cached windows;
- serializing thousands of generated windows;
- writing the file;
- flushing;
- `fsync`;
- atomic replacement.

Only final decoded data/status and widget mutations should return to the GUI thread.

### 5.2 Application shutdown drains cache jobs

The #2243 fix adds process-level lifecycle coordination for active cache jobs.

Preserve these semantics:

1. every cache worker QThread is tracked independently of an individual Timeline window;
2. `QCoreApplication.aboutToQuit` has an explicit shutdown hook;
3. shutdown waits until active reads/writes finish;
4. no `QThread` may still be running when Qt/application teardown destroys it;
5. do not use `QThread.terminate()` or kill a thread during a cache write;
6. an atomic write must either finish normally or leave the previous cache intact.

If the app later gains a central appwide background-job coordinator, Personal Timeline cache jobs may migrate to it, but the above semantics must remain intact.

### 5.3 Closing a Timeline is not application shutdown

When an individual Timeline window closes:

- cancel/request interruption of the expensive ephemeris generation worker as currently appropriate;
- do not start generation after a late cache miss;
- a cache read/write already in flight may finish safely at process scope;
- closing one Timeline must not block or shut down unrelated cache jobs for another Timeline.

### 5.4 Cache fingerprint behavior remains stable

A cache hit is valid only when transit-relevant chart/generation inputs match.

Preserve invalidation for changes such as:

- birth datetime;
- location;
- natal positions;
- birth-time/rectification state that affects astronomy;
- death bounds;
- candidate bodies;
- aspect configuration/orbs;
- scan/boundary refinement configuration;
- explicit Timeline algorithm version.

Do not invalidate solely for unrelated metadata such as comments unless that metadata becomes calculation-relevant in the future.

### 5.5 UID is authoritative

Use stable `chart_uid` throughout Timeline public APIs and cache identity.

Do not introduce new Timeline APIs keyed by numeric SQLite IDs.

### 5.6 Sorting semantics remain typed

All seven visible columns remain sortable:

- Age — numeric;
- Transit — text;
- Scope — text;
- Chart relevance — text/semantic relevance representation;
- Start — datetime;
- End — datetime;
- Duration — numeric.

Repeated click on the same column reverses direction. Clicking another column starts ascending. Active sorting must continue to apply after filter rerenders.

---

## 6. Recommended Codex procedure

Perform this in a dedicated PR from current `main` after #2243 merges.

### Phase 0 — baseline

1. Confirm #2243 is merged.
2. Pull/re-read current `main`.
3. Read the manifesto and this handoff.
4. Run the current focused Personal Timeline test suite before editing.
5. Record the baseline count/results.
6. Confirm there are no existing unrelated failures.

### Phase 1 — inventory all Timeline imports and ownership

Search the whole repository for:

```text
personal_timeline
personal_timeline_core
PersonalTimelineWindowWidget
PersonalTimelinePersistenceController
open_personal_timeline_for_window
generate_personal_timeline
_ACTIVE_CACHE_JOBS
shutdown_personal_timeline_cache_jobs
personal_timeline_sorting
```

Classify every match as:

- production caller;
- test caller;
- documentation;
- compatibility residue;
- duplicate/obsolete owner.

Pay particular attention to:

- `window_chrome.py`;
- `app.py`;
- Chart Editor and Database View window owners;
- `tests/test_personal_timeline*.py`;
- packaging/import-time initialization;
- any new Transit bootstrap code added since this document was written.

### Phase 2 — add characterization tests before moving code

At minimum characterize:

1. Database View requires exactly one selected Chart UID.
2. Chart Editor resolves the current Chart UID correctly.
3. public `PersonalTimelineWindowWidget` is an explicit class, not a mutated alias.
4. importing Timeline modules in a different order does not change behavior.
5. cache lookup begins automatically when an integrated Timeline window opens.
6. cache hit renders without starting ephemeris generation.
7. cache miss starts generation exactly once.
8. successful generation schedules exactly one cache write.
9. failed/interrupted generation does not replace the last good cache.
10. read/parse/reconstruction runs off GUI thread.
11. write/serialize/flush/`fsync` runs off GUI thread.
12. close-during-cache-read does not launch generation afterward.
13. application shutdown waits for an in-flight cache read/write.
14. no running cache `QThread` remains after the shutdown coordinator returns.
15. sorting remains active through filter rerenders.

Characterization tests should describe behavior, not preserve obsolete implementation details.

### Phase 3 — extract generation/model logic

Create the generation owner first because it has the cleanest dependency direction.

Move, with minimal semantic changes:

- Timeline dataclasses;
- generation constants;
- candidate construction;
- ephemeris/aspect helper calculations;
- time/death bounds;
- `generate_personal_timeline(...)`.

Then update generator-focused tests to import that module directly.

Avoid changing astrology calculations in the same commit. Structural extraction should be behavior-preserving.

Suggested commit:

`Extract Personal Timeline generation model`

### Phase 4 — establish the canonical concrete window owner

Move the actual integrated window behavior into a clearly named window module.

The concrete class should explicitly show its dependencies, e.g. conceptually:

```python
class PersonalTimelineWindowWidget(...):
    def __init__(...):
        ...
        self._persistence = PersonalTimelinePersistenceController(...)
        self._configure_sorting()
        self._begin_cache_lookup_or_generation()
```

Do not replace that with:

```python
install_timeline_window_behaviors(SomeClass)
```

or with `MethodType`, `setattr`, `sys.modules`, import side effects, or a hidden registry whose only purpose is method injection.

Suggested commit:

`Make Personal Timeline window ownership explicit`

### Phase 5 — remove redundant core-level opener/window ownership

Once the canonical window owner works:

- move `open_personal_timeline_for_window(...)` to the window owner;
- update `window_chrome.py` to import only that canonical opener;
- migrate selected-chart UID resolution to the most appropriate explicit owner;
- remove any duplicate legacy opener from `personal_timeline_core.py`;
- delete the obsolete base/window implementation from `_core` once no caller uses it.

Do not retain two openers that instantiate different Timeline window classes.

### Phase 6 — delete `personal_timeline_core.py`

Only after all production/test imports have migrated:

1. search the repository again for `personal_timeline_core`;
2. require zero production/test imports;
3. remove the file;
4. update documentation/workflow path filters if needed;
5. run the focused suite and relevant broader GUI tests.

Do not rename `_core` to another vague bucket such as `personal_timeline_impl.py` and call the migration complete.

---

## 7. Specific guidance for `app.py`

The user expects this stage may be better suited to Codex because `app.py` is still large. That does **not** mean the Timeline implementation should be moved into `app.py`.

### What to inspect in `app.py`

Search for:

- Transit/Timeline startup hooks;
- window coordinator construction;
- `aboutToQuit` connections;
- Chart Editor/Database View window registration;
- any generic feature-bootstrap mechanism that has appeared since this handoff;
- any existing appwide background-worker/shutdown coordinator.

### Preferred outcome: no Timeline-specific feature blob in `app.py`

If `window_chrome.py` can lazily import the canonical opener and the persistence module can register its process-lifecycle requirement through an established explicit application service, `app.py` may need no Timeline-specific change.

### If `app.py` must participate

Keep its role narrow and obvious. Acceptable examples:

```python
transit_features = TransitFeatureCoordinator(...)
```

or:

```python
background_jobs.register_shutdown_participant(timeline_cache_jobs)
```

provided those objects live in feature/coordination modules and `app.py` merely wires dependencies.

Unacceptable outcomes include placing any of the following in `app.py`:

- Personal Timeline cache serialization;
- timeline ephemeris generation;
- Timeline table sorting;
- filter state logic;
- row construction;
- cache worker classes;
- direct global thread dictionaries;
- runtime replacement of Timeline widget methods.

### Do not duplicate shutdown ownership

PR #2243 currently gives Timeline cache jobs their own explicit `aboutToQuit` handling. If a later `app.py` refactor establishes a canonical appwide shutdown/background-job coordinator, migration to that owner should be **one-for-one**, not additive.

There must be one clear authority that guarantees all Timeline cache jobs are finished before Qt teardown. Do not leave both an old feature hook and a new appwide hook competing to wait/cleanup the same threads without a deliberate idempotent design.

---

## 8. Threading/shutdown acceptance criteria

Before completing the future refactor, test these cases explicitly:

### Quit during cache read

1. open a chart whose Timeline cache exists and is large enough that read/parse is in flight;
2. immediately quit the application;
3. application waits cleanly;
4. no `QThread: Destroyed while thread is still running` warning/crash;
5. no late GUI callback mutates a destroyed window.

### Quit during cache write

1. generate a Timeline;
2. trigger application exit while serialization/write/`fsync` is in flight;
3. application waits until the job ends;
4. no running QThread remains;
5. cache file is either the fully written new atomic version or the prior intact version—never a partially replaced file.

### Close Timeline but keep application running

1. open Timeline;
2. close it during cache read;
3. cache worker may finish;
4. no generation begins after close;
5. application remains responsive;
6. another Timeline can still operate normally.

### Multiple Timeline windows

1. open two Timeline windows for different UIDs;
2. allow concurrent read/write jobs;
3. close one window;
4. the other remains unaffected;
5. application shutdown drains all active process-owned jobs.

---

## 9. Tests and CI that must remain authoritative

At the time of #2243, focused CI includes:

```text
tests/test_personal_timeline.py
tests/test_personal_timeline_filters.py
tests/test_personal_timeline_analysis.py
tests/test_personal_timeline_cache.py
tests/test_personal_timeline_persistence.py
tests/test_personal_timeline_sorting.py
```

Keep `.github/workflows/personal-timeline-tests.yml` path triggers synchronized with any renamed/split modules.

If generation moves to `personal_timeline_generation.py`, the workflow must trigger on that path.

If the window owner becomes `personal_timeline_window.py`, it must trigger on that path.

Do not accidentally make the focused workflow stop running because `personal_timeline*.py` patterns no longer cover a new directory/package layout.

Run relevant broader GUI/window tests after the focused suite. Structural refactors often pass unit tests while breaking lazy menu imports, Qt ownership, or shutdown order.

---

## 10. Non-goals

Do not combine this future Codex cleanup with:

- new transit bodies;
- new astrology scoring rules;
- LoG importer feature expansion;
- row flagging/color UI;
- dominance Top-N settings;
- Results-statistics redesign;
- angle-axis canonicalization;
- birth-time confidence redesign;
- cache format redesign unless required by an actual bug;
- broad Database View refactoring;
- wholesale `app.py` decomposition.

Those are separate changes and make ownership regressions much harder to diagnose.

---

## 11. Suggested commit sequence

Prefer small reviewable commits such as:

1. `Add Personal Timeline ownership characterization tests`
2. `Extract Personal Timeline generation model`
3. `Move integrated Personal Timeline window to canonical owner`
4. `Route window chrome to canonical Timeline opener`
5. `Remove obsolete Personal Timeline core module`
6. `Update Timeline CI paths and architecture docs`

If appwide shutdown coordination has matured enough to absorb Timeline jobs, keep that as its own commit:

7. `Register Timeline cache jobs with appwide shutdown coordinator`

Do not mix calculation changes into these structural commits.

---

## 12. Definition of done

This deferred migration is complete when all of the following are true:

1. `personal_timeline_core.py` no longer exists, or has been reduced to a genuinely named/owned module rather than a generic implementation bucket.
2. There is one canonical concrete Personal Timeline window class.
3. There is one canonical opener used by `window_chrome.py`.
4. No Personal Timeline code uses `sys.modules` aliasing.
5. No Personal Timeline code installs/replaces widget methods at runtime.
6. Persistence is an explicit collaborator with a narrow API.
7. Sorting is explicit instance behavior/policy, not injected behavior.
8. Cache I/O/reconstruction/serialization remains off the GUI thread.
9. Cache jobs are guaranteed to finish before application/Qt teardown.
10. Closing a Timeline during cache lookup cannot trigger late generation.
11. Chart identity remains UID-based.
12. All focused Timeline tests pass.
13. Relevant broader GUI/window tests pass.
14. CI path triggers still cover every moved Timeline implementation file.
15. `app.py` has gained no new Timeline feature implementation; at most it contains narrow application-level wiring.
16. A future developer can determine Timeline ownership by reading imports/classes, without knowing historical facade or monkeypatch behavior.

### End-state principle

**Personal Timeline should be an ordinary Transit workflow with explicit generation, window, persistence, sorting, and lifecycle owners. `app.py` may coordinate the workflow, but must not be the workflow.**
