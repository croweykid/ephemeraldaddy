# `app.py` Refactor Manifesto and Migration Plan

**Status:** Approved architectural direction  
**Scope:** `ephemeraldaddy/gui/app.py` and the workflows currently coupled to it  
**Audience:** Codex agents and human contributors  
**Primary constraint:** Preserve every existing feature while measurably improving responsiveness, throughput, troubleshooting, and future development speed.

## 1. Mission

The `app.py` refactor is not a line-count exercise. Its primary purpose is to
deliver a significant user-experience upgrade through better speed and
efficiency while making regressions easier to isolate and future features safer
to develop.

Every migration must advance all of these goals:

1. **User-perceived performance:** reduce startup cost, unnecessary database
   work, redundant chart calculations, synchronous UI-thread work, broad cache
   invalidation, and needless panel rerenders.
2. **Correctness:** preserve all current features and enforce the application's
   birth-time, rectified-time, `chart_uses_houses`, and UID integrity rules.
3. **Explicit ownership:** a developer should be able to identify which window,
   workflow, controller, model, or service owns a behavior without tracing
   arbitrary attributes across giant Qt objects.
4. **Troubleshootability:** failures should have narrow causal paths, typed
   boundaries, observable state transitions, and focused tests.
5. **Safe feature development:** new behavior should be added to a coherent
   workflow package instead of expanding `app.py` or depending on an entire
   window as a service locator.

Do not accept an extraction merely because it shortens `app.py`. An extraction
that keeps hidden window dependencies, increases import cost, duplicates work,
or adds indirection without ownership is not progress.

## 2. Canonical terminology

Use these names in all new code, documentation, and migration plans:

| Concept | Canonical name | Notes |
| --- | --- | --- |
| Default application mode and its top-level window | `DatabaseViewWindow` | Replaces the misleading `ManageChartsDialog` class name. |
| Individual-chart create/edit mode and its top-level window | `ChartEditorWindow` | Replaces the generic legacy `MainWindow` class name. User-facing mode copy may still say **Chart View** where appropriate during terminology migration. |
| Stateful individual-chart editing unit | `ChartEditSession` | Do not rename it `ChartEditingSession` or `ChartViewSession`. |
| Appwide top-level window routing and lifetime owner | `AppwideWindowCoordinator` | Do not use `MainWindow`, `ApplicationWindowCoordinator`, or another generic “main” abstraction. |
| Change-driven recalculation/refresh orchestrator | `RecalculationCoordinator` | It applies the pure `ChartRecalculationPolicy`. |
| Pure recalculation-impact policy | `ChartRecalculationPolicy` | It must encode authoritative-field and house-availability rules without Qt dependencies. |
| External website profile discovery/import | `WebProfileLookupService` and/or `WebProfileImportService` | Never use `Profile`, `ProfileLookup`, or `ProfileService` in isolation. Python modules use `web_profile_*`. |
| Database View query value object | `DatabaseSearchQuery` | Accuracy and evaluation efficiency are first-class requirements. |

### Prohibited ambiguous names

Do not introduce new modules, classes, or controllers named only:

- `MainWindow` or `main_window`;
- `ChartManager` for Database View;
- `ChartView` when the implementation specifically belongs to Chart Editor;
- `ProfileService` or `ProfileLookup` without the `WebProfile` qualifier;
- generic `helpers`, `utils`, `manager`, or `service` modules when a workflow
  name is available.

Legacy occurrences should be migrated deliberately, not mechanically. First
determine whether each occurrence refers to Database View, Chart Editor, or a
smaller workflow inside one of them.

## 3. Target package architecture

The long-term target is workflow-first organization. Use the following
structure for new extractions rather than perpetuating
`gui/features/controllers` or `gui/features/charts`:

```text
ephemeraldaddy/gui/features/
    chart_editor/
    database_view/
        analytics/
        collections/
        search/
        batch_editor/
    similarities/
    predictions/
    popouts/
    import_export/
    transits/
    windowing/
```

`ephemeraldaddy/gui/features/charts/` is a legacy staging area, not an approved
destination. It must be abolished safely over time. Do not spend effort
reorganizing or polishing that package as an end state. When a contained module
is actively migrated, place it directly in its correct workflow package and
update its imports and tests in the same bounded change.

### Option B is the destination

Prefer establishing the correct workflow package immediately when a bounded
migration can be performed and tested safely. A temporary compatibility import
or façade is acceptable when required to prevent a flag-day rewrite, but:

- it must be documented as transitional;
- it must not become the new owner of behavior;
- it must not create duplicate state or duplicate computation;
- it must have a clear deletion condition.

## 4. Chart identity prerequisite: finish UID migration first

The `chart_id` to `chart_uid` migration precedes selection-controller and broad
window extraction work. Do not bake legacy numeric IDs into new public APIs,
models, events, caches, or controller state.

### UID rules

1. Public workflow interfaces identify charts by `chart_uid`.
2. Selection order, navigation anchors, window routing, events, cache keys, and
   refresh requests use UIDs.
3. Numeric database row IDs may exist only at the persistence boundary where
   SQLite operations genuinely require them.
4. Boundary conversion should be local, explicit, and preferably batched.
5. Do not retain parallel UID and numeric-ID state across a controller merely
   for convenience.
6. Never expose a numeric ID to users as chart identity.
7. New names use `uid`, `chart_uid`, `chart_uids`, or `*_by_uid`; do not use a
   bare `id` when it means chart identity.

### UID migration audit before structural extraction

- Inventory all remaining `chart_id`, `current_chart_id`, `selected_ids`,
  ID-keyed caches, ID-based signals, and ID-bearing export paths.
- Classify each occurrence as persistence-only, transitional, or erroneous.
- Convert in small workflow slices with focused tests.
- Add source checks that prevent legacy identifiers from entering each newly
  migrated public interface.
- Complete the Database View selection/navigation UID path before introducing
  `DatabaseSelectionModel` or `DatabaseSelectionController`.

## 5. Window separation: first visible structural milestone

Separate the two top-level classes now known as `ManageChartsDialog` and
`MainWindow` into explicitly named `DatabaseViewWindow` and
`ChartEditorWindow`.

This is the first naming and ownership milestone, but it must not be executed as
one enormous copy-and-rename patch. Use an incremental strangler approach:

1. Establish destination modules/packages and characterization tests.
2. Rename one class at a time with temporary compatibility aliases only where
   necessary.
3. Update constructors, imports, type annotations, diagnostics, and tests to the
   canonical name.
4. Preserve behavior and startup ordering.
5. Delete compatibility aliases after all internal consumers have migrated.
6. Continue moving workflow behavior out of each window until the window owns
   presentation and explicit coordination only.

Do not reinterpret “default window” as “main window.” Database View is the
default application hub; that fact does not justify a generic `MainWindow`
abstraction.

## 6. Approved workflow boundaries

### 6.1 `ChartEditSession`

Target:

```text
ephemeraldaddy/gui/features/chart_editor/session.py
ephemeraldaddy/gui/features/chart_editor/controller.py
```

`ChartEditSession` owns the lifecycle and state of creating or editing one
chart, including:

- the active chart UID;
- authoritative loaded values versus the current draft;
- dirty-field classification;
- save/discard state;
- whether a change requires recalculation;
- rectified-time choice and reliability metadata;
- `chart_uses_houses` availability;
- save results and the change set emitted to downstream coordination.

It must not own widgets or accept the entire `ChartEditorWindow`. The
`ChartEditorWindow` supplies a typed view adapter or explicit values, and a
controller maps user actions to the session.

### 6.2 Database selection

After UID migration, introduce:

```text
ephemeraldaddy/gui/features/database_view/selection.py
```

with `DatabaseSelectionModel` and `DatabaseSelectionController`. They own
ordered UID selection, anchor UID, visible-versus-logical selection, and filter
restoration. Qt index/list-item mapping belongs in a narrow view adapter.

### 6.3 Web profile lookup and import

Separate provider/network/parser behavior from Qt orchestration:

```text
ephemeraldaddy/io/web_profile/
    models.py
    lookup_service.py
    import_service.py
    astrotheme.py
    wikipedia.py

ephemeraldaddy/gui/features/import_export/
    web_profile_controller.py
```

- `WebProfileLookupService` searches and resolves external candidates.
- `WebProfileImportService` normalizes an accepted candidate into an import
  request/result suitable for chart creation.
- Provider adapters handle site-specific parsing and errors.
- The GUI controller handles progress, cancellation, choices, and messages.
- Network services do not manipulate windows or Qt widgets.

### 6.4 `DatabaseSearchQuery`

The complete staged performance, persistence-projection, virtualization, and
similarity plan for this workflow is defined in
`agents/database_search_scalability_manifesto.md`. This section establishes the
architectural boundary; the dedicated manifesto defines how that boundary must
produce measured database-scale improvements.

Target:

```text
ephemeraldaddy/gui/features/database_view/search/
    query.py
    evaluator.py
    controller.py
    panel.py
    tag_filters.py
```

`DatabaseSearchQuery` is an immutable typed value object. The panel translates
widgets to/from the query. `DatabaseSearchEvaluator` evaluates charts without
reading Qt widgets.

Performance and accuracy requirements:

- normalize query values once, not once per chart;
- precompute active predicates and short-circuit inexpensive exclusions first;
- avoid repeated database access and prediction recalculation inside per-chart
  loops;
- batch-load required data;
- use UID-keyed caches with explicit revision/signature invalidation;
- preserve stable selection and ordering across query changes;
- benchmark representative large databases before and after migration;
- test every filter independently and in representative combinations.

### 6.5 `AppwideWindowCoordinator`

Target:

```text
ephemeraldaddy/gui/features/windowing/appwide_window_coordinator.py
```

It owns top-level Database View/Chart Editor creation, routing, show/hide/raise,
close decisions, application exit, and placement restoration. It does not own
feature popouts, chart calculations, or panel internals.

### 6.6 Settings groundwork

Do not use the term `Store`. Do not invent repositories organized around
arbitrary controller boundaries.

The intended structure is:

```text
ephemeraldaddy/gui/settings/
    core.py
    settings_keys.py
    settings_widgets.py
    modules/
        dev_tools.py
        property_manager.py
        traits.py
```

- `core.py` is the shared settings adapter/hub and repository of common settings
  constants or conversion behavior.
- Modules are organized according to actual Settings panel tag/section names.
- Migrate the current `gui/dev_tools.py`, `gui/property_manager.py`, and
  `gui/features/settings/traits.py` deliberately when settings work enters
  scope.
- The initial `app.py` undertaking should lay compatible groundwork, not turn
  settings reorganization into a blocking side project.

### 6.7 Recalculation

Targets:

```text
ephemeraldaddy/core/chart_recalculation_policy.py
ephemeraldaddy/gui/features/coordination/recalculation_coordinator.py
```

`ChartRecalculationPolicy` is pure and determines impact from typed changed
fields. `RecalculationCoordinator` applies that impact through explicit
dependencies.

The policy must distinguish at least:

- authoritative birth date/place/time changes;
- rectified-time values and whether use of rectified time is enabled;
- `chart_uses_houses` changes;
- derived astronomical data;
- tags;
- subjective notes/metrics;
- flavor metadata that does not affect calculation;
- changes that affect search, analytics, predictions, or presentation only.

The coordinator should invalidate and refresh only affected outputs. It must
avoid global database analytics refreshes and full chart recalculation for
lightweight edits.

## 7. Explicit interfaces: no window-as-service-locator

New controllers and services must not accept an entire window and then use
arbitrary `getattr`, `hasattr`, or `setattr` calls.

Use `typing.Protocol` for view and dependency boundaries when a concrete class
would create undesirable coupling. Example shape:

```python
from typing import Protocol

class ChartEditorView(Protocol):
    def read_chart_draft(self) -> "ChartDraft": ...
    def render_chart(self, result: "ChartRenderResult") -> None: ...
    def show_save_error(self, message: str) -> None: ...
```

Protocol requirements:

- keep each protocol small and workflow-specific;
- expose operations, not widget attributes;
- do not create one appwide mega-protocol;
- pass typed callbacks only when a protocol would be needlessly heavy;
- validate interface behavior through focused contract tests.

## 8. Correct the current ownership workarounds

### 8.1 Sentiment tally method borrowing

`MainWindow._update_sentiment_tally =
ManageChartsDialog._update_sentiment_tally` is not a change from the last 48
hours. Local history traces it to merged PR #1923 on 2026-07-17, “Skip Database
metrics refresh for lightweight Chart View edits.” It was already present in
the repository snapshot introduced by that merge. Later UID and batch-tag
commits touched nearby history but did not introduce the borrowing.

Therefore, do not treat it as a newly missing service from the recent callback
extraction. Diagnose the tally method's inputs and consumers, then replace the
borrowed method with an explicitly owned sentiment metrics calculation/service
and window-specific presenters. Preserve the lightweight-edit performance
optimization that PR #1923 was intended to provide.

### 8.2 Runtime callback injection

The `install_chart_view_right_panel_callbacks` pattern *is* recent. Local
history traces it to commit `fa7879d` on 2026-07-30, merged in PR #2054,
“Refactor chart right panel callbacks out of app.” It moved methods out of
`app.py` and reattached them dynamically with `MethodType`.

The legacy `MainWindow` name explains why the destination and owner were easy
to describe incorrectly, but renaming alone does not solve runtime injection.
The installed methods still rely on undeclared `ChartEditorWindow` attributes.

Repair it incrementally:

1. Canonically identify the owner as `ChartEditorWindow`.
2. Group callbacks by actual workflow rather than one “right panel” installer.
3. Introduce small Protocol-based view interfaces and explicit controller
   instances.
4. Connect signals to controller methods or typed callback bundles.
5. Delete `MethodType` installation once each callback group has an explicit
   owner.

### 8.3 Existing controllers with whole-window owners

Some controllers were deliberately introduced as an intermediate mitigation
for ambiguous `MainWindow` ownership. Do not discard useful extracted behavior
or attempt a foundation rewrite. Convert one controller at a time:

1. identify whether it belongs to Database View, Chart Editor, or appwide
   windowing;
2. move its internal state off the window;
3. replace the whole-window owner with explicit widgets, callbacks, services,
   or a small Protocol;
4. move it to the canonical workflow package;
5. preserve the old call path through a temporary façade only if required;
6. remove the façade after callers and tests migrate.

## 9. Chart information naming and ownership

“Chart Info panel” and “Chart Info!” are different concepts and must no longer
be distinguished only by punctuation.

Use:

- **`ChartInformationPresenter` / `chart_information`** for the reusable,
  appwide functionality that renders information for a clicked sign, body,
  position, nakshatra, house, aspect, Human Design gate/center/type/profile/
  channel/authority, or other chart entity. This is the successor concept to
  the broadly reused “Chart Info!” module.
- **`ChartEditorInfoTabs` / `chart_editor/info_tabs.py`** for Chart Editor's
  lower-left tabbed container containing Chart Info, Bio, Notes,
  Rectification, and Source.
- **`ChartInformationPanel`** for a single reusable panel instance in popouts
  and other windows.

The reusable presenter belongs above `chart_editor`, for example:

```text
ephemeraldaddy/gui/features/chart_information/
    models.py
    presenter.py
    panel.py
    token_formatting.py
```

The Chart Editor tabs may compose `ChartInformationPanel`, but must not become
the owner of appwide chart-information behavior.

All Chart Information presentations retain the appwide color-coding rules and
the graph-popout interaction contract defined in `AGENTS.md`.

## 10. Performance engineering requirements

Every substantial migration PR must establish a baseline and compare the new
path. Choose measurements relevant to the workflow, such as:

- cold import time for modules touched;
- application startup milestones;
- Database View first hydration;
- search latency for empty, simple, and complex queries;
- single-chart and multi-chart selection latency;
- Chart Editor open/load/render time;
- lightweight metadata save latency;
- recalculation-triggering save latency;
- database query count and rows loaded;
- number of recalculation, cache invalidation, and panel refresh calls;
- UI-thread blocking duration;
- peak memory or cache size for large-database workflows.

Rules:

1. Do not claim a speed improvement without a reproducible measurement.
2. Prefer instrumentation around workflow boundaries rather than ad hoc print
   statements.
3. Keep network latency separate from parsing/import/UI timings.
4. Do not trade accuracy for speed; optimize data access, reuse, batching,
   invalidation, and scheduling first.
5. Keep expensive CPU/database/network work off the Qt UI thread when safe.
6. Qt widgets must be created and mutated on the UI thread.
7. Worker results require cancellation/staleness tokens so an older result
   cannot overwrite a newer selection or chart session.
8. Cache keys must include every dependency that changes the result, including
   UID, authoritative birth information, rectified-time-use state, and
   `chart_uses_houses` where relevant.
9. Prefer targeted refresh events over global “refresh everything” calls.

## 11. Regression and migration gates

Each migration slice must pass gates appropriate to its risk.

### Required static gates

- compile all changed Python modules;
- run focused tests for the migrated workflow;
- run source tests that enforce intended ownership/naming where useful;
- confirm no new public `chart_id` API was introduced;
- confirm no new import from a lower-level service back into `gui/app.py` as a
  service locator;
- confirm no new callback installation through `MethodType`;
- inspect import cycles and startup import cost.

### Required behavioral gates

- preserve Database View as the default mode;
- preserve Chart Editor create, edit, save, discard, and return behavior;
- preserve selection through filters and refreshes;
- preserve unknown birth-time and rectified-time semantics;
- verify house-dependent output is unavailable when `chart_uses_houses` is
  false;
- verify lightweight metadata saves do not trigger astronomical recalculation;
- verify authoritative birth changes do trigger the required derived refresh;
- verify relevant Analytics, Search, Batch Editor, Collections, Predictions,
  and popouts receive correct targeted updates;
- verify close/reopen and window placement behavior;
- verify stale worker results cannot update the wrong chart/window.

### Visual gates

If a migration perceptibly changes a runnable UI, take screenshots of the
affected window/panel. Structural-only changes should not generate visual churn.

### Commit discipline

- Keep each commit bounded to one workflow or compatibility step.
- Do not combine large moves with unrelated formatting or feature changes.
- Prefer move-first, behavior-second commits only when tests can verify both
  states independently.
- Record baseline and after measurements in the PR body for performance work.
- State compatibility shims and their deletion condition explicitly.

## 12. Phased action plan

### Phase 0 — Baselines and safeguards

- Add reproducible performance benchmarks for startup, Database View hydration,
  Database Search, Chart Editor load/save, and targeted recalculation.
- Identify high-value characterization tests for the two current window classes.
- Inventory remaining chart-ID paths and dynamic owner dependencies.
- Record current feature routing and window lifecycle sequences.

**Exit gate:** performance baselines and regression coverage exist before major
movement.

### Phase 1 — Complete chart UID migration

- Convert remaining public workflow state, events, selection, navigation,
  caches, and refresh requests to UID.
- Confine numeric IDs to persistence adapters.
- Add guard tests for UID-only new interfaces.

**Exit gate:** Database View selection/navigation and Chart Editor routing can
operate through UID-first APIs without durable parallel ID state.

### Phase 2 — Name and separate the top-level windows

- Introduce `DatabaseViewWindow` and `ChartEditorWindow` in explicit workflow
  packages/modules.
- Update diagnostics and routes so no code guesses ownership from `MainWindow`.
- Retain short-lived compatibility aliases only where necessary.
- Begin `AppwideWindowCoordinator` around the existing top-level lifecycle.

**Exit gate:** all internal code refers to the canonical window names; generic
`MainWindow` no longer owns routing semantics.

### Phase 3 — Replace implicit interfaces

- Replace sentiment tally class-level method borrowing.
- Replace runtime right-panel callback injection.
- Add small Protocol-based view boundaries.
- Remove controller state stored arbitrarily on window objects.

**Exit gate:** no class-level behavior borrowing between the two windows and no
`MethodType` callback installer for Chart Editor workflows.

### Phase 4 — Extract core workflows

- Implement `ChartEditSession`.
- Implement `DatabaseSelectionModel` and controller.
- Implement `ChartRecalculationPolicy` and `RecalculationCoordinator`.
- Implement Web Profile lookup/import services and Qt controller.
- Implement `DatabaseSearchQuery`, evaluator, controller, and panel boundary.

**Exit gate:** each workflow has typed inputs/results, focused tests, and
measured performance equal to or better than baseline.

### Phase 5 — Replace legacy package structure

- Migrate modules out of `gui/features/charts` into approved workflow packages.
- Split the legacy `chart_view_window.py` by workflow.
- Establish appwide `chart_information` separately from Chart Editor's
  `ChartEditorInfoTabs`.
- Relocate misleading `main_window.py` contents by actual ownership, then
  delete it.

**Exit gate:** `gui/features/charts`, generic `main_window`, and generic
`chart_view_window` structures are gone.

### Phase 6 — Settings groundwork and follow-through

- Establish `gui/settings/core.py` and the tag-aligned `gui/settings/modules`
  structure.
- Migrate settings code when touched, without blocking higher-impact workflow
  work.
- Keep settings keys and common widgets at the parent settings package level.

**Exit gate:** settings additions have one predictable, tag-aligned home and do
not return to `app.py`.

### Phase 7 — Reduce `app.py` to composition and bootstrap

- Leave application startup, dependency construction, and explicit top-level
  coordination in `app.py`.
- Remove workflow implementations, reusable widgets, parsing, persistence
  policies, and feature-specific refresh logic.
- Re-measure all performance baselines and run the broad regression suite.

**Exit gate:** `app.py` is a readable composition root; both primary windows and
their workflows can be tested without importing the entire application module.

## 13. Per-session checklist for Codex

Before changing `app.py` or a migrating GUI workflow:

1. Read this document and the applicable `AGENTS.md` files.
2. State which canonical workflow owns the requested behavior.
3. Check whether chart UID migration blocks the intended extraction.
4. Trace existing callers, state, database access, timers, workers, and refresh
   consumers before editing.
5. Establish or identify a correctness and performance baseline.
6. Choose the smallest migration slice that advances the target architecture.
7. Use explicit typed values, Protocols, or callback bundles; never pass the
   whole window merely for convenience.
8. Preserve `chart_uses_houses`, unknown-time, and rectified-time integrity.
9. Run focused and relevant broad regression tests.
10. Measure the result and report both functional and performance effects.
11. Document any temporary compatibility layer and its deletion condition.
12. Do not opportunistically reorganize unrelated code.

## 14. Definition of success

The undertaking succeeds when:

- Database View and Chart Editor have explicit names and ownership;
- the application is faster in measured user workflows;
- lightweight changes trigger lightweight work;
- UID is the durable identity across application workflows;
- major workflows can be tested without constructing giant windows;
- controllers and services expose typed, narrow interfaces;
- stale asynchronous results cannot corrupt current UI state;
- `gui/features/charts`, `main_window`, and generic Chart Editor callback
  injection have been safely retired;
- Chart Information has a reusable appwide owner distinct from Chart Editor's
  tabbed info area;
- `app.py` is a composition root rather than the implementation of the whole
  application;
- no existing feature has been undercut in pursuit of structural cleanliness.

Architecture is serving the user only when it produces a faster, more reliable,
and easier-to-evolve application. That is the standard by which every refactor
step must be judged.
