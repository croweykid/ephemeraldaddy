# Single-source-of-truth redundancy audit (2026-07-25)

## Scope and method

This is a static audit of production Python. It compares AST-normalized function bodies, repeated
module constants, import paths, and same-class method names. Tests, notes, and generated package
metadata were excluded from recommendations. A matching name alone is not treated as proof of a
problem; the findings below were checked at their definitions and call sites.

## Highest-priority findings

### 1. Database Analytics defines the same methods twice in one class

`DatabaseAnalyticsChartsMixin` contains two copies each of
`_enneagram_type_for_database_label`, `_show_database_analytics_popout`, `_on_pick`,
`_show_info_for_pick_target`, and `_on_click`. The second definitions silently replace the first
ones when Python creates the class. The paired bodies are AST-identical, so today this is dead code
rather than a behavioral fork, but edits to the first copy would have no effect.

**Canonicalization:** retain one copy of each method in `database_analytics.py` and add a source test
that rejects duplicate method names within a class.

### 2. Search-option constants already have a shared module, but `app.py` redeclares them

`gui/widgets/search_controls.py` is explicitly the shared constants module and defines generation,
sentiment, relationship, gender, and guessed-gender options. `gui/app.py` independently rebuilds
those same values instead of importing them. This is a concrete drift risk because the Search Panel
also consumes the shared module.

**Canonicalization:** make `search_controls.py` authoritative; import its constants into `app.py`
and remove the local definitions. Keep UI-only aliases such as `SEARCH_GENDER_BLANK_ALIASES` local
unless another consumer needs them.

### 3. `style.py` assigns global style constants more than once

`CHART_DATA_HIGHLIGHT_COLOR` is assigned twice to the same value. More importantly,
`RELATIVE_YEAR_COLORS` is first defined with past and future buckets, then reassigned later without
`"year before last"` and `"last year"`. Because both assignments are in one module, only the later
mapping is observable after import. This makes the earlier mapping misleading dead configuration.

**Canonicalization:** define each token once in its relevant app-wide style section. Before merging
the relative-year mappings, verify whether past-year colors should be supported or deliberately
removed, then preserve that decision in one mapping and a focused test.

### 4. Large helper blocks are duplicated between `ManageChartsDialog` and `MainWindow`

AST-identical methods occur in both classes, including `_sanitize_export_token`,
`_calculate_pair_dissimilarity_from_selection`, `_update_location_completers`,
`_update_enneagram_predictor_total_label`, `_normalize_aspect_type`, `_extract_aspect_weight`,
`_collect_aspect_type_counts`, `_draw_popout_aspect_distribution_chart`, and
`_build_popout_left_panel`. Several related helpers are duplicated as well. The two classes are
therefore maintaining the same export, similarity, analytics-popout, and completer behavior in the
40,000-line central GUI module.

**Canonicalization:** move pure helpers to focused modules first (export filename formatting,
aspect aggregation, and similarity selection). Put stateful shared GUI behavior in a narrowly
scoped mixin/controller outside `app.py`; do not create another broad base class.

### 5. D&D class scoring has parallel, substantially duplicated implementations

`dnd_class_axes.py`, `dnd_class_axes_v2.py`, and `dnd_class_axes_v2_subclasses.py` repeat the same
axis constants and feature-extraction helpers. The two v2 files additionally have identical class
family scoring and assignment bodies. Current production GUI imports consistently select
`dnd_class_axes_v2.py`, while the subclass variant remains a parallel rule set rather than importing
the shared v2 engine.

**Canonicalization:** extract common axes, chart feature extraction, normalization, and family
scoring into an unversioned internal engine. Keep version/subclass modules as thin policy/data
adapters. Mark the original module as legacy or remove it after checking external API compatibility.

## Medium-priority findings

### 6. Human Design reference data exists in competing modules

`AWARENESS_STREAMS` appears in both `core/interpretations.py` and
`analysis/human_design_reference.py`. `HD_CIRCUIT_GROUPS` appears in both
`analysis/human_design_reference.py` and `analysis/hd_circuits_reference.py`. Channel topology is
also represented as a tuple in `core/hd.py` and as metadata-rich records in
`human_design_reference.py`. The latter representation difference can be useful, but topology
should be derived from the metadata-rich source rather than hand-maintained twice.

**Canonicalization:** make `human_design_reference.py` authoritative for descriptive records and
have computation modules derive compact tuples/lookups from it. Re-export compatibility names only
where required to avoid broad import churn.

### 7. Human Design chart derivation has separate analytics and search paths

Database Analytics derives a six-part profile through `_extract_human_design_profile`, while
`MainWindow` separately implements `_chart_human_design_gates`,
`_chart_human_design_channels`, and `_chart_human_design_type` for filtering. This can make search
and analytics disagree after fixes to gate calculation, caching, unknown birth time, or rectified
birth time handling.

**Canonicalization:** create one analysis-layer profile function returning a typed result and make
both paths consume it. Its cache signature must include birth data/place, effective-time policy,
and `chart_uses_houses`; factual calculations must not silently adopt rectified times.

### 8. Basic astrology calculations are repeated across analysis and presentation

`sign_for_longitude` exists in `analysis/body_dynamics_reworked.py`,
`analysis/weighted_chart_predictor.py`, and `gui/features/charts/presentation.py`. Body-dynamics
ruler/weight/house/aspect-orb helpers are also duplicated between
`analysis/body_dynamics_reworked.py` and `gui/features/charts/metrics.py`.

**Canonicalization:** put longitude normalization, sign/house lookup, aspect distance, and body
weight rules in small core analysis modules. Presentation code should only format results. Add
boundary tests for 0/360 degrees, cusps, missing houses, and `chart_uses_houses=False` before
switching consumers.

### 9. Startup animation rendering is copied into the subprocess module

`gui/startup.py` and `gui/startup_animation_process.py` duplicate star creation, wave advancement,
particle drawing, polygon-point helpers, and `paintEvent`. A visual fix can consequently land in
only one startup mode.

**Canonicalization:** extract the widget/renderer to a dependency-light module that both startup
entry paths import. Keep process launch and lifecycle handling separate.

## Lower-priority cleanup

- `gui/app.py` and `gui/dbv_search_panel.py` separately define the same settings keys for hidden and
  placeholder-chart filters. Put application setting keys in one constants module.
- `analysis/weighted_chart_predictor.py` and `gui/features/charts/enneagram_predictions.py` duplicate
  body aliases, canonical factor names/lookups, and house/gate parsing. The GUI should import the
  predictor's public normalization API.
- `gui/features/charts/dnd_predictions.py` and `enneagram_predictions.py` duplicate cache UID/signature
  checks and no-data rendering. Separate shared prediction cache validation from chart-specific UI.
- Chartwheel invocation still has a top-level wrapper, package `__main__.py`, and `py.py`. Keep one
  compatibility wrapper and the standard package entry point, and remove the ambiguously named copy
  after verifying packaging references.

## Recommended sequence

1. Delete same-class shadowed methods and duplicate assignments; add AST/source regression tests.
2. Import the existing Search constants into `app.py`.
3. Extract pure duplicated helpers from the two large GUI classes.
4. Consolidate Human Design derivation/reference data with birth-time-policy tests.
5. Build shared D&D and astrology calculation kernels, retaining thin compatibility adapters.
6. Consolidate startup rendering and low-risk cache/settings helpers.

This order removes silent shadowing first, then uses small import-only migrations before touching
calculation engines whose output compatibility requires broader tests.
