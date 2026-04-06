# Competing Code Paths / Redundancy Audit (2026-04-06)

## Scope
- Repository-wide static read-through focused on Python modules, launch paths, and duplicate-versioned components.

## Findings

1. **Two active GUI launch paths with different startup behavior**
   - `pyproject.toml` installs `ephemeraldaddy = ephemeraldaddy.gui.bootstrap:main`.
   - README still recommends `python -m ephemeraldaddy.gui.app`.
   - `bootstrap.py` intentionally shows a loading widget before importing the heavy GUI module; direct `gui.app` execution imports that heavy module first.
   - Impact: cold-start UX and perceived responsiveness can differ by launch method.

2. **Legacy monolith remains alongside current GUI app path**
   - `ephemeraldaddy/legacy/app_with_old_settings_menu.py` remains as a full alternate app implementation.
   - Current startup path uses `ephemeraldaddy/gui/app.py`.
   - Impact: maintenance ambiguity (bugfixes applied to one path can be missed in the other), accidental user/dev launches into outdated behavior, larger review surface.

3. **D&D classifiers exist in multiple generations (`v1`, `v2`, `v2_subclasses`)**
   - `species_assigner.py` and `dnd_class_axes.py` coexist with `species_assigner_v2.py` and `dnd_class_axes_v2.py`/`dnd_class_axes_v2_subclasses.py`.
   - Current GUI imports point to `v2` modules.
   - Impact: drifting rule sets and inconsistent output if different code paths import different generations; extra cognitive load while debugging results.

4. **Chartwheel generator has multiple compatibility entry wrappers**
   - There is a top-level compatibility launcher (`graphics/chartwheel_generator.py`), a package entry (`graphics/chartwheel_generator/__main__.py`), and an extra `graphics/chartwheel_generator/py.py` that duplicates the `__main__` behavior.
   - All redirect into `_chartwheel_generator_impl.py`.
   - Impact: mostly low-risk, but adds confusion about canonical invocation and creates additional files that can diverge accidentally.

5. **Human Design derivation logic appears in two behavioral paths**
   - `DatabaseAnalyticsChartsMixin._extract_human_design_profile()` derives/caches gates/lines/channels from chart positions.
   - `MainWindow` separately computes HD gates/channels/type with `_chart_human_design_gates/_channels/_type`.
   - Impact: subtle mismatches are possible if one path changes (sorting/filtering/caching semantics) and the other does not, which can produce inconsistent filter behavior vs analytics output.

6. **Geocoding path has local+online branches gated by env flags**
   - `geocode_location()` attempts local gazetteer first, then online fallback unless strict offline env flag is enabled.
   - `search_locations()` combines source resolution and optional online lookup.
   - Impact: behavior can vary significantly by runtime flags/environment; this is intentional, but without clear runtime observability it can look like nondeterministic search quality to users.

## Practical risk ranking
- **Higher risk:** #2 (legacy full app), #3 (versioned D&D logic), #5 (split Human Design derivation behavior).
- **Medium risk:** #1 (launch path divergence), #6 (environment-gated search behavior).
- **Lower risk:** #4 (chartwheel wrappers).

## Suggested cleanup order
1. Choose and document one canonical GUI launch command (and keep fallback explicitly marked as legacy).
2. Hard-deprecate or remove `legacy/app_with_old_settings_menu.py` from active workflows.
3. Consolidate D&D logic to one generation and move old modules behind explicit `legacy` namespace or delete.
4. Consolidate Human Design derivation into one shared helper used by both analytics and filter paths.
5. Keep one chartwheel entry wrapper + one package `__main__`, remove duplicate `py.py`.
6. Add lightweight runtime diagnostics indicating whether geocoding result came from local or online source.
