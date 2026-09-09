# Personal Timeline Facade Migration — Codex Handoff

**Status:** Deferred architectural cleanup after the current Personal Timeline cache/sorting work lands.  
**Primary prerequisite:** Do not begin this migration against an older Personal Timeline implementation. Start from updated `main` **after PR #2243 (or its equivalent final changes) has merged**, then inspect the current tree before editing.  
**Primary architectural goal:** Remove the transitional `personal_timeline.py` compatibility facade and its `sys.modules` alias without moving feature ownership back into `ephemeraldaddy/gui/app.py`. Personal Timeline should have an explicit, coherent owner under `ephemeraldaddy/gui/features/transits/`, and `app.py` should remain orchestration-only.

---

## 1. Read these before changing code

Read, in this order:

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
   - `tests/test_personal_timeline*.py`
   - `.github/workflows/personal-timeline-tests.yml`

The `app.py` refactor manifesto is authoritative. In particular:

- `app.py` is moving toward roughly 5,000–8,000 lines and should contain application/window orchestration, not feature implementations;
- new work belongs in workflow-first packages;
- runtime injection and compatibility facades are transitional mechanisms, not end states;
- a migration is not successful merely because it reduces line count;
- the change must improve ownership, performance, testability, and debuggability without breaking existing behavior.

Do **not** use this task as permission to perform a broad unrelated `app.py` refactor.

---

## 2. Why this task exists

The current Personal Timeline implementation temporarily uses a compatibility facade at:

`ephemeraldaddy/gui/features/transits/personal_timeline.py`

Its current shape is conceptually:

```python
from ephemeraldaddy.gui.features.transits import personal_timeline_core as _core
from ephemeraldaddy.gui.features.transits.personal_timeline_persistence import (
    install_personal_timeline_persistence,
)
from ephemeraldaddy.gui.features.transits.personal_timeline_sorting import (
    install_personal_timeline_sorting,
)

install_personal_timeline_persistence(_core)
install_personal_timeline_sorting(_core)

sys.modules[__name__] = _core
```

This arrangement solved a short-term compatibility problem while Personal Timeline was being split out and while tests still monkeypatched private generator helpers through the old module path.

It is **not** the desired permanent architecture.

The problems are:

1. Importing `personal_timeline` does more than import symbols: it mutates the implementation class at import time.
2. `sys.modules[__name__] = _core` means the apparent module identity and the actual implementation module are different.
3. Tests depend on that identity trick in order to monkeypatch private implementation globals.
4. Persistence and sorting currently install behavior by monkeypatching methods onto `PersonalTimelineWindowWidget`.
5. The public import path therefore hides initialization order and behavior ownership.
6. Future contributors can reasonably be confused about whether `personal_timeline.py`, `personal_timeline_core.py`, the installers, or `window_chrome.py` actually owns the feature.
7. This is exactly the kind of transitional indirection the `app.py` refactor manifesto says must eventually be removed once an explicit owner exists.

The goal is **not** to move this machinery into `app.py`. The size and existing responsibilities of `app.py` are reasons to keep the migration bounded and feature-owned.

---

## 3. Current ownership map to verify before editing

Do not assume these paths are unchanged by the time this task starts. Verify them first.

At the time this handoff was written, the responsibilities are approximately:

### `personal_timeline.py`

- transitional compatibility facade;
- installs persistence integration;
- installs sorting integration;
- replaces its own module identity with `personal_timeline_core` through `sys.modules`.

### `personal_timeline_core.py`

- `TimelineTransitDefinition`;
- `PersonalTimelineWindow`;
- timeline generation and boundary refinement;
- chart UID resolution;
- worker for expensive ephemeris generation;
- `PersonalTimelineWindowWidget`;
- filtering UI and result rendering;
- `open_personal_timeline_for_window(...)`.

This file is currently the de facto implementation owner despite the vague `_core` name.

### `personal_timeline_persistence.py`

- cache-generation fingerprint configuration;
- cached-window reconstruction;
- asynchronous cache read/write workers;
- off-GUI-thread permanent-cache I/O;
- runtime installation that wraps/replaces selected `PersonalTimelineWindowWidget` methods.

### `personal_timeline_sorting.py`

- typed sort keys;
- header-click sort state;
- runtime installation that wraps `__init__` and `_populate` on `PersonalTimelineWindowWidget`.

### `cache.py`

- permanent Personal Timeline disk-cache format and path;
- SHA-256 chart/generation fingerprinting;
- JSON read/write;
- atomic replace and `fsync` behavior.

### `window_chrome.py`

- lazy menu-level open hook for both Chart Editor and Database View;
- currently imports `open_personal_timeline_for_window` from the compatibility path.

### tests

At least `tests/test_personal_timeline.py` currently imports:

```python
from ephemeraldaddy.gui.features.transits import personal_timeline as timeline
```

and monkeypatches private implementation helpers through that alias. This is one of the reasons the `sys.modules` facade still exists.

---

## 4. Desired end state

The migration is complete only when all of the following are true.

### 4.1 No compatibility module identity trick

There must be no Personal Timeline code that does:

```python
sys.modules[__name__] = ...
```

and no equivalent import redirection trick.

### 4.2 No ambiguous `personal_timeline_core.py` owner

The final implementation should have names that describe responsibility rather than a generic `_core` bucket.

Preferred bounded end state under the existing `transits` workflow package:

```text
ephemeraldaddy/gui/features/transits/
    personal_timeline_generation.py
    personal_timeline_window.py
    personal_timeline_persistence.py
    personal_timeline_sorting.py
    personal_timeline_filters.py
    personal_timeline_analysis.py
    personal_timeline_results.py
    cache.py
```

Exact names may vary if the repository has already established a better convention by the time the task starts, but preserve the ownership split:

- **generation/model logic** must have an explicit owner;
- **window/UI orchestration** must have an explicit owner;
- **persistence** must remain a named dependency;
- **sorting** must remain a named responsibility;
- analysis/results/filter modules should not be churned unnecessarily.

Avoid generic new names such as `helpers.py`, `utils.py`, `manager.py`, or another `core.py` merely to make the rename easy.

### 4.3 Prefer removing runtime monkeypatch installers

The preferred architecture is that `PersonalTimelineWindowWidget` directly owns or composes its persistence and sorting behavior instead of having methods replaced after class definition.

In particular, the ideal final state does **not** require:

```python
install_personal_timeline_persistence(module)
install_personal_timeline_sorting(module)
```

at import time.

Prefer one of these explicit patterns:

1. **Direct methods on the window class** that call small functions/services from the persistence/sorting modules; or
2. **Small explicit collaborators** constructed by the window, e.g. a persistence coordinator and sort-state object with narrow responsibilities; or
3. Another repository-established typed pattern that makes initialization obvious and testable.

Do not replace one hidden runtime installer with another hidden runtime installer under a different filename.

### 4.4 `window_chrome.py` imports a canonical open function

The lazy menu hook should ultimately import from the actual owner, for example:

```python
from ephemeraldaddy.gui.features.transits.personal_timeline_window import (
    open_personal_timeline_for_window,
)
```

The exact destination may differ if a dedicated Transit feature registry exists by then.

What matters is that the import points to a real owner rather than a compatibility shim.

### 4.5 `app.py` stays orchestration-only

This task must **not** move Personal Timeline generation, cache handling, sorting, filtering, widget construction, or thread management into `app.py`.

If `app.py` needs any change at all, it should be a tiny explicit integration hook consistent with the manifesto.

A good final result may require **zero `app.py` changes** if `window_chrome.py` can continue to lazily open the feature from its canonical owner.

### 4.6 If a Transit feature bootstrap/registry is genuinely needed, it lives outside `app.py`

The compatibility-facade comment currently names an “explicit Transit-feature bootstrap/registry” as the deletion milestone.

Important interpretation:

- a registry is **not mandatory** if runtime installer behavior can be eliminated entirely;
- direct ownership is preferable to creating infrastructure merely to satisfy the word “registry.”

If there remains a legitimate one-time initialization need shared by Transit features, create a narrowly named owner under the Transit workflow, e.g.:

```text
ephemeraldaddy/gui/features/transits/bootstrap.py
```

or another repository-consistent name.

It should expose an explicit operation such as:

```python
def initialize_transit_features() -> None:
    ...
```

and be idempotent.

Do not put registry state into `app.py`; `app.py` may call it as orchestration if necessary, but should not own the implementation.

Do not create a registry if its only purpose would be to preserve the current runtime monkeypatch approach.

---

## 5. Required migration procedure

Perform this as a bounded architectural PR. Do not combine it with unrelated Personal Timeline features.

### Phase 0 — establish the correct base

1. Confirm PR #2243's final changes are already in `main`.
2. Start a new branch from updated `main`.
3. Confirm `main` is clean/current before editing.
4. Run the existing focused Personal Timeline tests before making changes.
5. Record the baseline result.

At the time of this handoff, the focused workflow runs:

```text
tests/test_personal_timeline.py
tests/test_personal_timeline_filters.py
tests/test_personal_timeline_analysis.py
tests/test_personal_timeline_cache.py
tests/test_personal_timeline_persistence.py
tests/test_personal_timeline_sorting.py
```

Update that list if current `main` has added more relevant tests.

### Phase 1 — inventory every facade caller

Before moving code, search the entire repository for:

```text
personal_timeline
personal_timeline_core
install_personal_timeline_persistence
install_personal_timeline_sorting
PersonalTimelineWindowWidget
open_personal_timeline_for_window
generate_personal_timeline
sys.modules
```

Classify each hit as:

- production caller;
- test caller;
- compatibility-only reference;
- documentation/comment;
- unrelated match.

Do not delete the facade until every production and test caller has an explicit replacement path.

Pay special attention to:

- `window_chrome.py`;
- all `tests/test_personal_timeline*.py` files;
- any imports that may have appeared in `app.py` since this handoff;
- packaging/entrypoint files;
- type-checking imports;
- hidden circular-import workarounds.

### Phase 2 — add characterization coverage before structural changes

The existing focused suite is necessary but not sufficient for an architectural move.

Add or strengthen characterization tests for these state transitions before deleting the compatibility layer:

1. Chart Editor menu opens Personal Timeline for the current chart UID.
2. Database View menu requires exactly one selected chart UID.
3. Personal Timeline can instantiate without relying on import order from a previous `personal_timeline` import.
4. Sorting is active on a newly created Personal Timeline window without a runtime facade import.
5. Permanent-cache lookup starts automatically on window creation.
6. Cache hit renders without launching ephemeris generation.
7. Cache miss launches generation once.
8. Cache write occurs after successful generation.
9. Cache read/write remains off the GUI thread.
10. Closing during an in-flight cache lookup does not later launch generation.
11. Repeated window creation does not double-connect sorting signals or double-install persistence behavior.
12. Existing filtering/results behavior remains available.

These tests should verify the new ownership model, not merely duplicate old implementation details.

### Phase 3 — separate generation/model ownership from window ownership

`personal_timeline_core.py` currently combines pure-ish generation logic with Qt window code. Use this migration to remove the ambiguous `_core` owner, but keep the extraction bounded.

Recommended split:

#### `personal_timeline_generation.py`

Move only logic that does not need a `QWidget`/`QMainWindow`, such as:

- `TimelineTransitDefinition`;
- `PersonalTimelineWindow`;
- candidate definition construction;
- aspect-orb calculation;
- active-window calculation;
- boundary refinement;
- date/death/timeline bounds;
- `generate_personal_timeline(...)`;
- constants genuinely owned by generation.

It may still depend on ephemeris functions and astrology constants. The point is to remove Qt/window ownership from this layer.

Tests that monkeypatch generator internals should import this module directly.

For example, replace:

```python
from ephemeraldaddy.gui.features.transits import personal_timeline as timeline
monkeypatch.setattr(timeline, "planetary_longitude", fake_longitude)
```

with a direct import of the generation owner.

Do not preserve the old monkeypatch path merely to avoid editing tests.

#### `personal_timeline_window.py`

Move/own:

- chart UID selection resolution used to open the feature;
- `_PersonalTimelineWorker` if it remains the best owner;
- `PersonalTimelineWindowWidget`;
- `open_personal_timeline_for_window(...)`;
- filter/widget/result presentation orchestration.

The window should import generation APIs explicitly.

### Phase 4 — remove persistence runtime method replacement

Current persistence integration wraps/replaces widget methods such as `_start_generation`, `_on_finished`, and `closeEvent` after the class already exists.

Replace this with explicit ownership.

Preferred procedure:

1. Keep the low-level disk cache in `cache.py` unchanged unless a real bug is found.
2. Keep cache worker types and cache reconstruction logic in `personal_timeline_persistence.py`.
3. Give the window an explicit persistence collaborator or explicit helper calls.
4. Make the startup sequence visible in the window code.

Target state should read conceptually like:

```python
class PersonalTimelineWindowWidget(QMainWindow):
    def __init__(...):
        ...
        self._timeline_cache = PersonalTimelinePersistence(...)
        self._start_cache_lookup()

    def _start_cache_lookup(self):
        ...

    def _on_cache_lookup_finished(self, result):
        if result.hit:
            self._render_cached_windows(result.windows)
        else:
            self._start_generation_worker()

    def _on_generation_finished(self, windows):
        self._render_generated_windows(windows)
        self._timeline_cache.write_async(windows)
```

That is illustrative, not a mandated class name.

Critical invariants to preserve from PR #2243:

- disk read and JSON parse must remain off the GUI thread;
- cached-window reconstruction must remain off the GUI thread if it can be large;
- serialization/write/flush/`fsync`/atomic replace must remain off the GUI thread;
- only UI mutation returns to the GUI thread;
- malformed cache is a miss, not a user-facing failure;
- interrupted/failed generation does not replace a previously good cache;
- close during lookup does not allow a late miss to start generation;
- background worker lifetime must remain safe if the window closes.

Do not regress any of these in the name of simplifying imports.

### Phase 5 — remove sorting runtime method replacement

Current sorting integration wraps `PersonalTimelineWindowWidget.__init__` and `_populate` after class definition.

Replace that with explicit window initialization and explicit sorting calls.

Preferred state:

- sort column/order state is initialized directly by the window;
- header click is connected directly during window construction;
- `_populate(...)` or its caller explicitly obtains sorted windows;
- typed keys remain in `personal_timeline_sorting.py` if that keeps the logic testable and isolated.

For example:

```python
self._sort_column = None
self._sort_order = Qt.AscendingOrder
self.tree.header().sectionClicked.connect(self._on_sort_header_clicked)
```

and:

```python
rows = sorted_timeline_windows(...)
self._populate_rows(rows)
```

Preserve:

- all seven sortable columns;
- numeric Age sorting;
- numeric Duration sorting;
- datetime Start/End sorting;
- stable tie-breaking;
- ascending/descending toggle;
- sort state surviving filter rerenders.

### Phase 6 — migrate callers to explicit owners

Update production callers after the new modules are working.

#### `window_chrome.py`

Change the lazy import away from the compatibility path.

The menu behavior must remain available in both:

- Chart Editor / Chart View;
- Database View.

Do not duplicate feature-opening logic in both menu paths.

#### tests

Update each test to import the module it actually tests:

- generation tests → generation owner;
- window/open-selection tests → window owner;
- persistence worker tests → persistence owner;
- sorting tests → sorting owner;
- analysis/filter tests stay with their current explicit modules.

Tests should stop depending on a magical shared module identity.

#### `app.py`

Only change if a real current caller exists or an explicit Transit bootstrap must be called there.

If no Personal Timeline import/integration currently lives in `app.py`, do **not** add one just because this handoff originated from the `app.py` refactor discussion.

The end goal is less feature responsibility in the monolith, not a ceremonial app-level registration layer.

### Phase 7 — delete the transitional facade

Only after callers and tests have migrated:

1. Delete `ephemeraldaddy/gui/features/transits/personal_timeline.py` if it is no longer the canonical implementation owner.
2. Delete `personal_timeline_core.py` after its responsibilities have moved to clearly named modules.
3. Remove all `sys.modules` aliasing associated with this feature.
4. Remove obsolete `install_personal_timeline_*` functions if runtime installation has been eliminated.
5. Search the repository again for stale imports/comments.
6. Update `.github/workflows/personal-timeline-tests.yml` path triggers if filenames have changed so the focused workflow still runs when the new modules change.

Do not leave a second “temporary” facade unless an unavoidable external compatibility requirement is discovered. If one truly must remain, document the external consumer and a concrete deletion condition; internal tests are not sufficient justification for preserving it.

---

## 6. Bootstrap/registry decision rule

Codex should make this decision explicitly rather than automatically introducing infrastructure.

### Prefer **no registry** when:

- persistence is directly composed by `PersonalTimelineWindowWidget`;
- sorting is directly initialized by the widget;
- `window_chrome.py` can lazily import the canonical open function;
- there is no other required one-time global Transit registration.

This is likely the cleanest end state.

### Introduce a Transit bootstrap only when:

- multiple Transit features genuinely share one-time registration;
- initialization order must be guaranteed before windows are constructed;
- the registration cannot reasonably be owned by the concrete feature itself.

If introduced:

- place it under `gui/features/transits/`;
- keep it tiny and idempotent;
- make dependencies explicit;
- do not let it become a generic service locator;
- do not move feature code into it;
- do not make it import every Transit module eagerly if that harms startup.

A bootstrap whose only job is to reproduce the current method-monkeypatch installers is **not an improvement**.

---

## 7. Performance requirements

This migration must preserve or improve user-perceived performance.

### Absolutely do not regress:

- expensive ephemeris generation remains on a worker thread;
- permanent-cache reads/parsing/reconstruction remain off the GUI thread;
- permanent-cache serialization/write/flush/`fsync` remain off the GUI thread;
- cache hits avoid running the expensive generator;
- filter and sort changes operate on already-generated windows rather than regenerating ephemerides;
- lazy menu opening should not make normal application startup import heavy Personal Timeline dependencies unnecessarily.

### Check startup/import cost

Because removing a lazy compatibility import can accidentally make imports eager, verify that the new architecture does not cause `app.py` startup to import all of Personal Timeline, Swiss Ephemeris work, or large Qt feature graphs before the user opens the feature.

Keep the menu-level import lazy unless the repository has adopted a measured feature-registration system with equivalent or better startup behavior.

---

## 8. Chart UID and data-integrity requirements

Preserve the current UID-first behavior.

- Public Personal Timeline selection/open APIs use `chart_uid`.
- Database View must still require exactly one selected UID.
- Chart Editor should use the authoritative current UID.
- Do not reintroduce numeric database IDs into new public interfaces.
- Permanent-cache keys remain chart-UID based.
- Cache fingerprints must still invalidate when transit-relevant chart inputs change.
- Unrelated notes/flavor metadata should not force timeline regeneration unless current calculation policy explicitly changes.

Do not use this migration to redesign the cache fingerprint unless a separately demonstrated correctness bug requires it.

---

## 9. Behavior that must not change

This is primarily an architecture migration. Preserve user-visible Personal Timeline behavior unless a regression fix is required.

At minimum preserve:

- broad candidate generation rather than a doctrine-driven “major transits only” list;
- Jupiter/Saturn/outer planets/nodes/Chiron/asteroids/Lilith candidate support as currently configured;
- major and minor aspects according to current configured aspect types;
- cohort/generational cycles retained and labeled rather than discarded;
- existing body-relevance metadata behavior;
- all current filter presets and filter semantics;
- Results popup integration;
- continuous transit-window date ranges and boundary refinement;
- current death-date capping behavior;
- permanent per-chart cache behavior;
- typed column sorting;
- Chart Editor and Database View menu access.

Do not use this PR to revise astrological research methodology, body/aspect taxonomy, or Results statistics.

---

## 10. Tests and regression gates

### Focused suite

The focused Personal Timeline suite must remain green.

Add tests for the new explicit architecture rather than only carrying old tests forward.

At minimum verify:

#### Import/ownership

- canonical generation module imports directly;
- canonical window module imports directly;
- importing the window creates a functioning widget without first importing an old facade;
- no test requires `sys.modules` aliasing;
- no double installation occurs after repeated imports/window creation.

#### Generation

- authoritative DB UID selection behavior;
- exactly-one-UID validation;
- Saturn-return definition coverage or equivalent existing characterization;
- continuous-window boundary refinement;
- known death-year bounds.

#### Cache

- fingerprint round trip/invalidation coverage;
- cache hit bypasses generation;
- miss launches generation once;
- malformed cache is handled as a miss;
- read/parsing/reconstruction off GUI thread;
- write/serialization/flush path off GUI thread;
- close-during-read guard;
- failed/interrupted generation does not overwrite good cache.

#### Sorting

- all visible columns retain typed sort keys;
- Age numeric ordering;
- Duration numeric ordering;
- Start/End datetime ordering;
- toggle direction;
- filter rerender preserves active sort.

#### Menu/open integration

Add a narrow smoke/characterization test if practical that proves both menu owners still reach the same canonical open path.

### CI path triggers

After file moves/renames, inspect `.github/workflows/personal-timeline-tests.yml`.

The workflow must trigger on the new module names. Do not accidentally make the focused suite stop running because the old wildcard no longer covers a new package/path.

### Final regression review

Before declaring the task complete:

1. reread the original requirement and this handoff;
2. inspect the final diff as if you did not write it;
3. trace the actual import/open flow from `window_chrome.py` to the window;
4. trace cache-hit, cache-miss, generation-complete, and close-during-cache state transitions;
5. search for stale `personal_timeline_core`, facade, and installer references;
6. verify `app.py` did not gain feature implementation logic;
7. run the focused suite on the final branch after reconciling current `main`.

Passing tests alone are not sufficient if the final import architecture still depends on hidden runtime mutation.

---

## 11. Non-goals

Do not expand this PR into any of the following unless required by a regression directly caused by the migration:

- wholesale `app.py` decomposition;
- Database View or Chart Editor class renames unrelated to Timeline opening;
- `AppwideWindowCoordinator` implementation;
- broad Transit View redesign;
- Personal Transit redesign;
- new astrology calculation methods;
- new Timeline filters;
- new Results statistics;
- Library of Ghosts feature expansion;
- settings redesign;
- permanent-cache schema redesign;
- general-purpose plugin/feature registry for the whole application;
- moving every `personal_timeline_*` file into a nested package merely for aesthetics.

A bounded flat-module cleanup under `gui/features/transits/` is preferable to a large package reorganization if it fully removes the facade and clarifies ownership.

---

## 12. Suggested commit sequence

Keep commits reviewable and behaviorally coherent.

Recommended sequence:

1. **Add Personal Timeline facade-migration characterization tests**
   - establish import/order/cache/sorting/open behavior before structural edits.

2. **Split Personal Timeline generation and window ownership**
   - create explicitly named generation/window modules;
   - move tests to direct owners;
   - keep temporary compatibility only during the intermediate commit if needed.

3. **Make Personal Timeline persistence explicit**
   - remove method-replacement installer;
   - preserve asynchronous cache semantics.

4. **Make Personal Timeline sorting explicit**
   - remove `__init__`/`_populate` runtime wrappers;
   - preserve typed sorting behavior.

5. **Remove Personal Timeline compatibility facade**
   - migrate `window_chrome` and remaining callers;
   - delete `personal_timeline.py` facade and `personal_timeline_core.py` if no longer needed;
   - remove stale installer/import comments.

6. **Update focused CI paths and reconcile current main**
   - final workflow/path cleanup only after filenames are settled.

If the change can be cleanly completed in fewer commits, that is fine. Do not squash unrelated architectural steps into one opaque rewrite merely to reduce commit count.

---

## 13. Definition of done

This task is complete when:

- `personal_timeline.py` is no longer a transitional facade;
- there is no Personal Timeline `sys.modules` alias;
- `personal_timeline_core.py` no longer serves as an ambiguously named implementation bucket;
- Personal Timeline generation has an explicit owner;
- Personal Timeline window/open behavior has an explicit owner;
- persistence is explicitly composed/owned rather than installed through runtime method replacement;
- sorting is explicitly initialized/owned rather than installed through runtime method replacement;
- `window_chrome.py` lazily opens the feature through the canonical owner;
- tests import the modules they actually test rather than relying on shared module identity;
- no Personal Timeline implementation logic has been moved into `app.py`;
- expensive generation and cache I/O remain off the GUI thread;
- cache-hit/miss/close semantics remain correct;
- all existing Personal Timeline user behavior is preserved;
- CI path triggers cover the new module layout;
- the focused Personal Timeline test suite passes on the final branch reconciled with current `main`;
- a repository-wide search shows no stale facade/import/installer dependency.

### Architectural end goal in one sentence

**Personal Timeline should behave like a normal, explicitly owned Transit workflow that `app.py`/window chrome can invoke, not like behavior that only exists because importing one module secretly rewrites another module/class at runtime.**

---

## 14. Suggested PR framing

Suggested PR title:

**Remove Personal Timeline compatibility facade**

Suggested PR summary:

> Replaces Personal Timeline's transitional `sys.modules` facade and import-time method installers with explicit generation/window/persistence/sorting ownership under `gui/features/transits/`, updates callers/tests to canonical modules, preserves lazy menu opening and all asynchronous cache behavior, and keeps `app.py` limited to orchestration.
