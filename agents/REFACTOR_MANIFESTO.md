# `app.py` Refactor Manifesto and Migration Plan

**Status:** Approved architectural direction
**Last implementation audit:** 2026-09-11 (`4e4c1fa`/`a97a5d1`)
**Scope:** `ephemeraldaddy/gui/app.py` and the workflows currently coupled to it  
**Audience:** Codex agents and human contributors  
**Primary constraint:** Preserve every existing feature while measurably improving responsiveness, throughput, troubleshooting, and future development speed.

- `app.py` should be no more than 5,000–8,000 lines and should serve as
  application/window orchestration only. The intended high-level feature
  separation remains:

```text
features/
    chart_editor/
    import_export/
    database/
    search/
    transit/
    human_design/
    research/
    settings/
```

This compact tree is a durable structural goal: it names the major capability
areas that should no longer live in `app.py`. Section 3 refines it into the
canonical workflow-first package architecture used for concrete moves. Where
the names differ, use section 3's more precise destination names (for example,
`database_view/` and `transits/`) without losing any capability area listed
above. Some areas may ultimately be subpackages of a workflow rather than
direct children of `features/`.

## 0. Current implementation status (audited 2026-09-11)

This is a point-in-time implementation ledger, not a replacement for the
normative direction below. Update this section when a phase exit gate changes;
do not infer completion merely because a destination directory exists.

### Executive assessment

The refactor is **directionally aligned but not on track against the phased
exit gates**. Useful bounded extractions have continued, especially under
`chart_editor`, `database_view`, `transits`, and `settings`, but the prerequisite
and ownership milestones have not been completed in order. Twelve initial
bounded moves are now complete: `SegmentedTimeEdit`, `ChartListWidget`,
similarity-calculator settings persistence, saved-chart change classification,
Database View logical-selection state, the first pure Chart Information
keyword, token, decan, and mode model family, Chart Editor save-result/time
reliability lifecycle state, single-chart Markdown rendering and export
coordination, aspect and position sentence models, and toolkit-neutral decan and
mode documents have canonical owners and focused regression coverage. `app.py`
is still 39,012 lines with 1,059
four-space-indented methods, and it still defines both legacy
top-level window classes. The 5,000–8,000-line composition-root goal therefore
remains distant.

| Phase | Status | Audited evidence / remaining exit condition |
| --- | --- | --- |
| 0 — baselines and safeguards | **Partial** | Performance instrumentation and focused Database View/Chart Editor performance tests exist, as do many source-characterization tests. There is still no complete, reproducible baseline suite covering every workflow named by the exit gate, nor one maintained routing/lifecycle inventory. |
| 1 — UID migration | **Advanced, not complete** | Important selection, hidden-chart, refresh, duplicate, ranking, and worker state is UID-owned and guarded by source tests. Numeric row IDs and ID-shaped workflow APIs remain throughout `app.py`, including chart-picking, composite-chart, export, similarities, and tool-routing paths. Persistence-boundary conversion is not yet consistently narrow. |
| 2 — top-level windows | **Not started at the class boundary** | `ManageChartsDialog` and `MainWindow` remain defined in `app.py`; neither canonical window class nor `AppwideWindowCoordinator` exists. Tests still parse the legacy class names, so renaming requires a coordinated characterization-test update rather than an alias-only claim of completion. |
| 3 — explicit interfaces | **Not complete** | Sentiment tally behavior is still borrowed at class level, and `install_chart_view_right_panel_callbacks` still attaches `MethodType` methods at runtime. Some newer controllers use narrow callbacks, showing the intended pattern, but the phase exit gate is unmet. |
| 4 — core workflows | **Early/partial** | `ChartEditSession` and callback-based `ChartEditorController` and `ChartMarkdownExportController` boundaries exist and are used incrementally. The session now owns normalized identity, authoritative-versus-draft values, dirty fields, field-specific recalculation reasons, explicit birth-time/rectification/house-availability context, the latest typed save result, and accumulated save/prediction-flush state, but it does not yet own the full lifecycle promised in section 6.1. The pure `ChartRecalculationPolicy` owns saved-chart change classification behind temporary window delegates, but the coordinator is not implemented. `DatabaseSelectionModel` and `DatabaseSelectionController` own ordered logical UID selection, the navigation anchor, filtered-view merging, reconciliation, and one-step deselection restoration; Qt item mapping and persistence-boundary conversion remain in the window adapter. The canonical Database Search query/evaluator/controller and non-Qt web-profile service modules do not yet exist. |
| 5 — legacy package replacement | **Partial extraction, no retirement** | Correct workflow packages are growing; `SegmentedTimeEdit`, `ChartListWidget`, similarity-settings persistence, and single-chart Markdown rendering now live under `chart_editor`, `database_view`, `similarities`, and `import_export`, respectively. The appwide `chart_information` package now owns initial pure keyword/token/decan/mode, colorized aspect/position-sentence, and toolkit-neutral rich-text document models plus narrow presenters, but substantial Chart Information rendering remains in `app.py`. `gui/features/charts` still contains 80 Python modules and both generic controller staging modules remain. |
| 6 — settings | **Partial** | `gui/settings/core.py` and `gui/settings/modules` now exist, but legacy settings implementations remain under `gui/` and `gui/features/settings`; additions should use the canonical home while touched legacy code is migrated deliberately. |
| 7 — composition root | **Not started as an exit gate** | Imports and bounded helpers have moved out, but both primary windows and substantial workflow logic remain in `app.py`; it is not yet independently testable as a small composition root. |

### What is safe to change or remove now

- **Safe documentation cleanup:** keep this ledger current and replace stale
  counts/evidence. Preserve the high-level structural goals above; section 3
  supplies their concrete package mapping rather than superseding them.
  Historical provenance in section 8 should remain until the two
  workarounds it explains are actually retired; afterward it can move to Git
  history or an implementation note.
- **Safe code removal only after caller proof:** delete a compatibility alias,
  borrowed method, runtime installer group, or legacy-ID adapter only in the
  same bounded change that migrates all callers and updates its characterization
  tests. The current audit does **not** establish any of those artifacts as
  dead code.
- **Safe forward work:** finish one UID-first workflow slice, then implement its
  canonical owner behind a narrow interface. The lowest-risk next structural
  slices are the Database Selection model/controller and completing
  `ChartEditSession`, because both already have UID/state characterization
  coverage to build on.
- **Do not remove yet:** the legacy window classes, `MethodType` callback
  installer, sentiment tally borrowing, `gui/features/charts`, or generic
  controller modules. Each still has live callers or source tests and requires
  staged replacement, not deletion.
- **Do not weaken the gates:** the apparent out-of-order progress is not a
  reason to drop UID, performance, unknown/rectified-time,
  `chart_uses_houses`, stale-worker, or behavioral regression requirements.

### Audit method

The status above was established from the checked-out tree, not inferred from
directory names: line/method counts of `gui/app.py`, exact class and callback
references, existence checks for each canonical target module, package module
counts, focused test inventory, and recent file history. Re-run those checks
when updating the date or claiming a phase transition.

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

## 15. Immediate plan of attack

**Recorded:** 2026-09-10 23:17:30 UTC

**Purpose:** Turn the long-term phases above into a rational, low-regression
execution order for the next sequence of bounded changes.

### Current scale and planning principle

At the time this plan was recorded, `ephemeraldaddy/gui/app.py` was 39,847
lines. `ManageChartsDialog` accounted for roughly 22,900 lines and `MainWindow`
for roughly 14,500 lines. The largest-looking blocks are not automatically the
safest first moves: the sentiment tally, Database Search filter evaluator,
window constructors, rendering queue, and top-level window classes combine
state, presentation, calculation, caching, and refresh behavior.

Do not prioritize a migration by the number of lines it removes. Prioritize
work that establishes explicit ownership, typed inputs/results, focused tests,
and a deletion path for legacy coupling. The immediate sequence is:

1. establish repeatable baselines and a caller/ownership inventory;
2. extract genuinely stateless leaf code and small reusable widgets;
3. move pure calculations currently implemented as window methods;
4. finish the UID-first Database View selection path and introduce its
   model/controller;
5. complete `ChartEditSession` and extract `ChartRecalculationPolicy`;
6. establish reusable Chart Information ownership;
7. replace runtime callback injection and borrowed methods one workflow at a
   time;
8. separate and canonically rename the top-level windows only after their state
   boundaries are real;
9. migrate the large Search, Analytics, Similarities, and sentiment workflows
   after their state and refresh contracts are explicit; and
10. reduce `app.py` to composition/bootstrap last.

### Immediate low-risk extraction queue

#### A. Module-level stateless helpers

Move coherent function families directly to their workflow owners, never to a
generic `helpers.py` or `utils.py`:

- birth/date field validation and conversion to `chart_editor`;
- Lilith calculation-method normalization to its calculation/settings owner;
- similarity calculator settings loading/saving to `similarities`;
- prediction defaults to `predictions`; and
- Wikipedia lookup preferences to the Web Profile or Chart Editor biography
  workflow.

Each move must inventory callers first, add or retain focused tests, preserve
startup import order, and ensure the destination does not import `app.py`.

#### B. Standalone widgets and narrow Qt primitives

Move one class at a time, with its constructor callers and behavior tests:

- `SegmentedTimeEdit` to `features/chart_editor/`;
- `ChartListWidget` to `features/database_view/`, near the future list adapter;
- `_GlobalCloseShortcutFilter` to `features/windowing/`;
- `_PlanetDynamicsWorker` to its analytics/rendering workflow;
- `ResizablePixmapLabel` to its photo-gallery or presentation owner; and
- `_ComboItemColorDelegate` to the concrete workflow that uses it, unless a
  caller audit proves that it is genuinely appwide.

Do not collect unrelated widgets in a new generic staging module. Confirm that
tests do not depend on importing their old definitions from `app.py`, and check
for import cycles and cold-import regressions with every move.

#### C. Bootstrap and platform helpers

Extract small, coherent clusters for application identity, packaged-font
registration, Qt application construction, global shortcuts, screen geometry,
input scaling, icons, debug logging, and dependency-check state. Prefer
specific modules under `features/windowing/`, such as
`application_bootstrap.py` and `application_identity.py`.

Preserve the existing startup order exactly while doing this work. Avoid any
move that initializes Qt, Matplotlib, fonts, the database, or platform-specific
APIs earlier than before, and measure cold-import/startup effects.

#### D. Pure or effectively static window methods

Extract functions that do not depend on mutable window state before attempting
their surrounding UI workflows. Initial candidates include:

- analysis export-row construction;
- Database Analytics cache encoding/decoding and population-norm calculations;
- chart birth-year, aspect, body, and row normalization helpers;
- Chart Editor export Markdown construction;
- aspect line-segment construction;
- metadata-change and database-refresh impact classification; and
- analytics/cache signatures.

Use a tested pure function or typed policy object in the canonical destination.
When numerous callers make an immediate cutover unsafe, leave a temporary
one-line delegate, document its deletion condition, migrate all callers, and
then remove it. Do not replace window methods with mixins that retain the same
hidden window dependencies.

#### E. Finish existing extraction seams

Prefer completing an existing boundary over creating another overlapping one.
Inspect thin adapters around `ChartEditorController`, `ChartEditSession`,
Database close/import progress, Transit controllers, related-chart choices,
Web Profile import, and existing import/export builders. Keep pure work in the
service/model, progress and cancellation in a narrow GUI controller, and the
window limited to signal wiring and rendering.

### First high-value architectural work

#### 1. UID-first Database Selection

Complete one remaining Database View selection/navigation UID slice at a time.
Inventory and classify every related `chart_id`, `current_chart_id`,
`selected_ids`, ID-keyed cache, signal, navigation anchor, export path, and
refresh request as persistence-only, transitional, or erroneous.

Once the selection/navigation path no longer maintains durable parallel row-ID
state, introduce `DatabaseSelectionModel` and `DatabaseSelectionController` in
`features/database_view/selection.py`. They own ordered chart UIDs, anchor UID,
visible-versus-logical selection, and restoration after filters or refreshes.
A narrow view adapter alone translates Qt items/indexes and persistence row IDs.

This precedes broad Database View window extraction because selection is shared
by filters, collections, batch editing, exporting, duplicate checks, hiding,
analytics, and Chart Editor navigation.

#### 2. Complete `ChartEditSession`

Make `ChartEditSession` the authoritative owner of one create/edit lifecycle:

- active chart UID;
- authoritative loaded values versus current draft;
- dirty-field classification;
- save/discard state;
- rectified-time value, enablement, and reliability metadata;
- `chart_uses_houses` availability;
- recalculation impact; and
- the save result/change set emitted downstream.

Move state transitions before moving widget construction. The Chart Editor
should read explicit values from its widgets, submit them through a controller,
and render session results; it should not retain a parallel authoritative
session in arbitrary window attributes.

#### 3. Pure recalculation policy, then GUI coordination

First create and test `core/chart_recalculation_policy.py`. It must distinguish
authoritative birth facts, rectified-time hypotheses and enablement,
`chart_uses_houses`, derived astronomical data, tags, subjective metadata, and
presentation-only/flavor metadata. Preserve the optimization that lightweight
metadata edits do not trigger astronomical recalculation or broad analytics
refreshes.

Only after the pure policy is stable should
`features/coordination/recalculation_coordinator.py` translate its typed impact
into targeted recalculation, cache invalidation, Search/Analytics/Predictions
updates, and rendering. Test unknown-time, rectified-time, and no-houses cases
explicitly.

#### 4. Reusable Chart Information

Extract pure information models/builders and token/color formatting first, then
give `ChartInformationPresenter` a narrow `ChartInformationPanel` interface.
Convert one click source or entity family at a time: signs, bodies/positions,
houses, nakshatras, aspects, and Human Design entities.

Keep `ChartEditorInfoTabs` limited to the Chart Editor lower-left tab container;
it must not own the appwide presenter. Preserve appwide color coding and the
graph-popout contract that clicks update the associated Chart Information
panel.

### Explicitly deferred high-risk moves

Do **not** begin with the following wholesale moves:

- `_update_sentiment_tally`: first separate inputs, pure aggregation, norm/cache
  lookup, view-model construction, and the two window-specific presenters;
- `_chart_matches_filters`: first characterize each filter, introduce immutable
  `DatabaseSearchQuery`, translate widgets once, and extract predicate families
  into a non-Qt evaluator with representative benchmarks;
- either giant window `__init__`: allow constructors to shrink as leaf widgets,
  models, sessions, controllers, and factories gain explicit ownership;
- the complete `ManageChartsDialog` or `MainWindow` classes: moving or renaming
  them before state extraction only creates correctly named giant classes;
- Settings as one project: migrate a section when it is touched without making
  Settings reorganization block UID/session work; or
- the asynchronous render queue as a wholesale move: first characterize render
  order, generation invalidation, stale-result rejection, hidden-tab deferral,
  overlay lifecycle, timing preview, cache cleanliness, and cancellation.

Pure subcalculations within these areas may still migrate early when their
inputs and outputs can be made explicit and tested independently.

### Initial bounded change sequence

Subject to caller audits and existing coverage, use this as the first concrete
queue of PR-sized changes:

1. **Complete:** Extract `SegmentedTimeEdit` with focused widget tests.
2. **Complete:** Extract `ChartListWidget` with keyboard, double-click, drag, and open-feedback
   behavior tests.
3. **Complete:** Move pure similarity-settings functions to `similarities`.
4. Move metadata-change classification into a tested
   `ChartRecalculationPolicy` foundation.
5. Convert one remaining Database View selection/navigation ID slice to UID.
6. Introduce the UID-only `DatabaseSelectionModel` after that slice is clean.
7. Expand `ChartEditSession` to own authoritative-versus-draft state and dirty
   classification.
8. Move one Chart Information builder family behind typed models.
9. Replace one coherent runtime callback-injection group with an explicit
   controller and narrow Protocol/callback bundle.
10. Repeat by workflow, measuring behavior and deleting each compatibility
    facade when its caller count reaches zero.

The exact order of the first three leaf moves may change if a caller/import
audit reveals unexpected coupling. UID Selection, `ChartEditSession`, and
recalculation policy remain the first architectural unlocks.

### Backlog and review discipline

Label each candidate as one of:

1. **Leaf move** — no window state changes.
2. **Pure extraction** — typed calculation/formatting inputs and outputs.
3. **State extraction** — introduces or completes a model/session/controller.
4. **Ownership migration** — reroutes live UI behavior and removes a legacy
   path.

Before every significant slice, record:

- canonical workflow owner and current callers;
- window attributes read and written;
- signals, timers, workers, and cancellation/staleness tokens;
- database access and transaction boundaries;
- chart identity form and any row-ID conversion;
- cache keys and invalidation/refresh consumers;
- unknown-time, rectified-time, and `chart_uses_houses` behavior;
- existing correctness and source-characterization coverage;
- relevant before/after performance measurement; and
- every compatibility shim plus its objective deletion condition.

Review the final diff as a new reviewer would: trace affected callers and state
transitions, verify the underlying ownership problem was improved rather than
merely relocated, and do not treat passing tests or a reduced line count as
sufficient proof of success.
