# Sun-Moon Hot Takes Plugin — Codex Completion Handoff

## Purpose

Finish the **Sun-Moon Hot Takes** plugin integration after the generic plugin-framework work is merged.

The user will provide/reference the pull request containing the framework changes. **Treat that PR and the current post-merge `main` branch as authoritative.** Do not assume the file contents or line numbers in this handoff are newer than the repository. Inspect the PR diff and current files first, then make surgical changes against the current code.

This task has two goals:

1. Finish wiring the new generic `chart_info` plugin hook into Chart Editor's **Chart Data Output → Chart Info** interaction.
2. Finish plugin upload/UI/test support so the new Python plugin and the existing Human Design supplement coexist without regressions or unnecessary performance cost.

Do **not** redesign the framework again unless current code proves a change is necessary. The generic framework was intentionally introduced so future plugins can use common lifecycle and hook semantics without teaching `app.py` about each plugin individually.

---

## User-facing behavior required

The source plugin is named exactly:

- filename: `sun-moon_hot-takes.py`
- display name: `Sun-Moon Hot Takes`
- companion data file: `sun_moon_hot_takes.json`

The reference/source copies currently live under `docs/`.

When the plugin is installed and enabled, clicking either the **Sun** or **Moon** position row in Chart Editor's **Chart Data Output** panel must append a supplement to the **bottom** of the existing native Chart Info interpretation for that clicked position.

The plugin must determine the lookup entry from the **currently open chart's Sun sign + Moon sign combination**, regardless of whether the user clicked the Sun row or Moon row.

Required rendering:

```text
[CHART_DATA_HIGHLIGHT_COLOR, bold] Sun-Moon Hot Takes:
[italic, only if average/avg is not null] <average text>

[only if best_case is not null] [bold] Best case: [normal] <best-case text>

[only if worst_case is not null] [bold] Worst case: [normal] <worst-case text>
```

Important details:

- Preserve the source hot-take strings **verbatim**. Do not rewrite, sanitize, spellcheck, normalize punctuation, or soften language.
- Null fields are omitted entirely, including their labels.
- Do not manufacture placeholder text for missing fields.
- The plugin supplement is appended after native Chart Info; it does not replace native Chart Info.
- Clicking Sun and Moon for the same chart should produce the same Sun/Moon-combination supplement beneath the respective native Sun/Moon interpretation.
- Clicking Mars, Venus, angles, nodes, etc. must not show the Sun-Moon Hot Takes block.
- Disabled/uninstalled plugin = native behavior only.

---

## Existing framework work to preserve

After the referenced PR is merged, inspect these files before changing anything:

- `ephemeraldaddy/analysis/plugins.py`
- `ephemeraldaddy/analysis/human_design_plugins.py`
- `ephemeraldaddy/gui/settings/modules/plugins.py`
- `docs/sun-moon_hot-takes.py`
- `docs/sun_moon_hot_takes.json`
- `ephemeraldaddy/gui/app.py`
- `tests/test_plugin_manager.py`

The framework introduced by the PR should include the following concepts. Preserve them unless the current merged code differs materially:

### Generic plugin registry

`ephemeraldaddy.analysis.plugins` owns generic lifecycle behavior rather than `human_design_plugins.py`.

The registry recognizes at least:

- `humdes_gates.json` → **Human Design Gates-Lines Supplement** → legacy JSON/data plugin
- `sun-moon_hot-takes.py` → **Sun-Moon Hot Takes** → Python plugin

### Python plugin manifest

The Sun-Moon source plugin declares a literal manifest similar to:

```python
PLUGIN_MANIFEST = {
    "api_version": 1,
    "name": "Sun-Moon Hot Takes",
    "hooks": ["chart_info"],
    "data_files": ["sun_moon_hot_takes.json"],
}
```

Manifest validation is performed through AST/literal parsing **without executing the plugin**. Executable plugin code is imported lazily only when an enabled plugin hook is actually dispatched.

### Generic Chart Info hook

The framework provides a dispatcher equivalent to:

```python
chart_info_plugin_paragraphs(context)
```

Each plugin returns declarative styled paragraphs/segments rather than receiving Qt widgets directly. A normalized segment can contain:

```python
{
    "text": "...",
    "bold": True,          # optional
    "italic": True,        # optional
    "color_role": "highlight",  # optional
}
```

This separation is intentional. **Do not give arbitrary plugins direct ownership of `QTextCursor`, `QPlainTextEdit`, or Chart Editor internals.** The application should render the normalized declarative result.

### Lazy/cached behavior

The generic Python-plugin modules are cached by plugin revision, and plugin lifecycle changes invalidate those caches. The Sun-Moon plugin independently caches its parsed JSON payload. The Human Design plugin's parsed payload was also moved toward revision-based caching.

Do not reintroduce per-click plugin discovery/import/JSON parsing.

---

# Implementation work remaining

## 1. Reconcile imports in `app.py`

The old application code imported generic plugin lifecycle functions from the Human Design-specific module. After the framework PR, change the imports so ownership is semantically correct.

Preferred shape, adjusted to current code style:

```python
from ephemeraldaddy.analysis.human_design_plugins import humdes_gate_line_supplement_lines
from ephemeraldaddy.analysis.plugins import (
    chart_info_plugin_paragraphs,
    install_plugin_file,
    installed_plugin_names,
    recognized_plugin_names,
)
```

If additional generic plugin functions are actually needed, import them from `ephemeraldaddy.analysis.plugins`, not `human_design_plugins.py`.

Do not remove the existing Human Design supplement integration.

---

## 2. Expand the Settings plugin-upload file filter

The existing upload dialog was designed when every plugin was JSON and currently uses a JSON-only filter similar to:

```python
"JSON files (*.json);;All files (*)"
```

Update it to permit recognized Python plugin files as well, for example:

```python
"Plugin files (*.json *.py);;JSON files (*.json);;Python files (*.py);;All files (*)"
```

Continue validating by **exact recognized filename**, not merely extension.

Required behavior:

- selecting `humdes_gates.json` still works
- selecting `sun-moon_hot-takes.py` works
- installing the Python plugin also installs its declared sibling `sun_moon_hot_takes.json`
- selecting an unrecognized `.py` or `.json` still produces the existing not-recognized path/message rather than silently executing/copying it
- plugin manager displays the human-readable display name where supported

Do not broaden this task into a public arbitrary-plugin marketplace or unrestricted plugin auto-discovery. The generic contract can support future registered plugins without changing the safety boundary now.

---

## 3. Add a generic Chart Info supplement renderer in `app.py`

Add a **small application-owned helper** that accepts normalized paragraphs from `chart_info_plugin_paragraphs()` and appends them to the current Chart Info document.

A reasonable conceptual signature is:

```python
def _append_chart_info_plugin_paragraphs(
    self,
    paragraphs: list[list[dict[str, Any]]],
) -> None:
    ...
```

Name can follow current conventions.

### Renderer requirements

The helper must:

1. No-op for no paragraphs.
2. Preserve the native Chart Info content already rendered.
3. Move a `QTextCursor` to the **end** of the Chart Info document.
4. Insert sensible separation before the first plugin block (normally a blank line; avoid accumulating absurd whitespace).
5. Render paragraph separation consistently, normally two newlines between logical paragraphs.
6. For each segment:
   - `bold=True` → `QFont.Bold`
   - `italic=True` → italic
   - `color_role == "highlight"` → **existing `CHART_DATA_HIGHLIGHT_COLOR` constant**
   - otherwise use normal Chart Info text formatting/color rather than inheriting bold/italic/highlight accidentally from the previous segment
7. Preserve embedded newlines in segment text.
8. Never interpret plugin strings as HTML. The declarative styles are the boundary.
9. Leave the Chart Info cursor/display in the normal expected state after appending.
10. Tolerate malformed/empty normalized output without crashing Chart Editor.

Use the existing `QTextCursor`, `QTextCharFormat`, `QFont`, and `QColor` conventions already present in Chart Info renderers such as decan/Human Design rendering. Do not introduce another rich-text abstraction unless one already exists after the merge.

### Multi-plugin separation

Review the generic dispatcher’s behavior for multiple plugins. The framework version may insert an empty paragraph as a separator between plugin outputs. If the normalizer strips empty segments but the dispatcher can still emit an empty paragraph, make the renderer handle it intentionally **or** clean the runtime representation so there is one consistent rule.

Do not leave a representation in which a nominal separator is silently impossible to render.

---

## 4. Dispatch the generic hook from the correct Chart Editor interaction seam

This is the most important part of the remaining work.

### Do NOT blindly dispatch at the end of `_show_position_info()`

`_show_position_info()` is reused from more than one UI context. Chart/popout/database flows can temporarily redirect `self.chart_info_output` and call shared renderers.

If the plugin simply reads `self._latest_chart` after every call to `_show_position_info()`, a position clicked in another chart/popout can receive the **wrong chart's** Sun/Moon interpretation.

That is a real data-context bug, not a hypothetical style concern.

### Scope required by the user

For this task, Sun-Moon Hot Takes is required specifically for:

> Chart Editor → Chart Data Output → click Sun or Moon position row → Chart Info

Do not opportunistically enable it in every popout until those call sites can provide their actual chart context.

### Preferred integration strategy

Use the existing centralized summary-click flow, likely `_handle_summary_info_click(...)`, and identify the **main Chart Info target** using the existing comparison similar to:

```python
targets_main_chart_info = target_info_widget is self.chart_info_output
```

When the click resolves to a **position** entry in the main Chart Data Output panel:

1. Run the existing native position renderer first.
2. Build a generic plugin context from the actual selected position and current chart.
3. Call `chart_info_plugin_paragraphs(context)`.
4. Append the returned paragraphs with the new generic renderer.
5. Return through the existing click-handling path.

Do not hardcode the Sun-Moon plugin name in this dispatch path. Dispatch the generic `chart_info` hook for position clicks and let each plugin decide whether the context applies.

### Context contract

At minimum pass plain serializable-ish values/mappings, e.g.:

```python
chart = self._latest_chart
chart_signs = chart.signs() if chart is not None and hasattr(chart, "signs") else {}

context = {
    "target": "position",
    "body": body,
    "sign": sign,
    "house_num": house_num,
    "chart_signs": dict(chart_signs),
}
```

If longitude, display label, house-enabled state, or other already-available primitive metadata can be included cheaply and cleanly, that is acceptable and may help future plugins. Do not pass the whole Qt window/widget or require plugin code to inspect application internals.

### Genericity rule

The app-level hook dispatcher should **not** contain logic like:

```python
if body in {"Sun", "Moon"}:
    run_sun_moon_plugin()
```

Instead:

```python
if this_is_a_main_chart_position_click:
    run_all_chart_info_plugins(context)
```

The Sun-Moon plugin itself already filters to Sun/Moon.

This is the main future-proofing requirement.

---

## 5. Confirm the Sun-Moon plugin itself against current reference JSON

Inspect `docs/sun-moon_hot-takes.py` and `docs/sun_moon_hot_takes.json` after merge.

The plugin should:

- require `context["target"] == "position"`
- return nothing unless clicked body is Sun or Moon
- require both Sun and Moon signs in `context["chart_signs"]`
- normalize sign keys case-insensitively
- look up:
  - `table[sun_sign][moon_sign]`
- map `average` (and optional compatibility fallback `avg`)
- map `best_case`
- map `worst_case`
- return declarative styled paragraphs
- cache its JSON file after first successful load
- fail closed (`[]`) rather than crash Chart Editor if the companion file is missing/invalid

### Verbatim-data requirement

Do **not** modify the descriptions in `sun_moon_hot_takes.json` as part of implementation or tests.

If a test needs fixture text, either:

- read a known entry from the reference file and compare exact strings, or
- copy the exact existing string into a fixture without editing it.

No content cleanup belongs in this task.

---

## 6. Preserve Human Design plugin behavior

The existing Human Design Gates-Lines Supplement is a regression boundary.

Verify all of the following after genericization:

- `humdes_gates.json` remains recognized
- existing install behavior remains functional
- existing enable/disable behavior remains functional
- gate/line supplement formatting is unchanged unless a current bug requires a narrowly justified fix
- existing fixing/exaltation/detriment trimming behavior remains intact
- the JSON is not reparsed on every gate click

Do not convert the Human Design data plugin into a Python plugin merely for symmetry. The framework is intentionally able to support legacy/data-only and Python hook plugins together.

---

# Test work required

## 7. Repair/update `tests/test_plugin_manager.py`

The pre-refactor test suite was coupled to `ephemeraldaddy.analysis.human_design_plugins` as if that module owned global plugin lifecycle state.

A test resembling this may now be stale:

```python
from ephemeraldaddy.analysis import human_design_plugins as plugins
monkeypatch.setattr(plugins, "PLUGIN_DIR", plugin_dir)
monkeypatch.setattr(plugins, "DISABLED_PLUGIN_DIR", disabled_dir)
plugins.set_plugin_enabled(...)
```

If lifecycle functions are compatibility imports/aliases into the new generic module, monkeypatching path globals on `human_design_plugins` will not necessarily alter the globals used by `analysis.plugins`.

**Preferred fix:** test generic lifecycle through `ephemeraldaddy.analysis.plugins` directly. Keep Human Design tests focused on Human Design-specific payload validation/formatting.

Do not deform production code solely to retain a test’s obsolete implementation coupling.

Update Settings assertions only where the UI genuinely changed. Avoid gratuitous UI changes.

---

## 8. Add generic plugin-runtime tests

Add or extend tests covering at least:

### Registry/lifecycle

- both recognized plugin filenames are present
- display names are correct
- install/enable/disable paths work
- disabling an enabled plugin prevents hook dispatch
- re-enabling makes it available again without application restart
- cache invalidation occurs on state/install changes

### Python manifest validation

- correct API version accepted
- unsupported API version rejected
- missing/empty hook list rejected
- missing required sibling data file rejected
- non-sibling/path-traversal `data_files` entries rejected
- manifest must be a literal dictionary
- validation does **not execute plugin code**
- an arbitrary unregistered `.py` file is rejected even if it has a syntactically valid manifest

### Failure isolation

- plugin import failure does not crash Chart Editor/runtime
- plugin `chart_info()` exception does not propagate into Chart Editor
- malformed hook return is ignored/normalized safely

---

## 9. Add Sun-Moon plugin unit tests

Test the plugin independently from Qt.

Required cases:

1. Non-position target → `[]`.
2. Position target for non-Sun/Moon body → `[]`.
3. Missing `chart_signs` → `[]`.
4. Missing Sun or Moon sign → `[]`.
5. Sign-key case normalization works.
6. A combination with average + best + worst renders all three in the right order.
7. Average null → no average paragraph/text.
8. Best null → no `Best case:` label.
9. Worst null → no `Worst case:` label.
10. Header segment is bold and `color_role == "highlight"`.
11. Average segment is italic.
12. Best/Worst labels are bold while their description segments are normal.
13. Source description strings match the JSON **exactly**.
14. Missing/invalid JSON produces no supplement rather than an exception.
15. JSON loading is cached rather than reopening/reparsing on every hook call.

If importing a hyphenated source filename directly is awkward, test it through the generic plugin loader or use `importlib.util.spec_from_file_location`, matching production behavior.

---

## 10. Add Chart Info integration/regression tests

Prefer a narrow helper/UI integration test over launching the entire application if existing fixtures permit it.

Cover:

### Main Chart Editor

- plugin installed/enabled + Sun row click:
  - native Sun interpretation remains
  - hot-take block is appended after it
- Moon row click:
  - native Moon interpretation remains
  - same chart-combination hot-take block is appended
- Mars/non-luminary position click:
  - native info remains
  - no Sun-Moon block
- plugin disabled/uninstalled:
  - native output is unchanged
- null properties do not leave orphan labels

### Formatting

Where Qt test infrastructure allows document-format inspection:

- `Sun-Moon Hot Takes:` has exact `CHART_DATA_HIGHLIGHT_COLOR`
- header is bold
- average is italic
- `Best case:` / `Worst case:` labels are bold
- body description text is not accidentally bold/italic due to format leakage

### Critical context regression

Add a regression test ensuring a position click routed to a non-main/popout Chart Info target does **not** append a Sun-Moon supplement based on unrelated `self._latest_chart` state.

This test is mandatory unless the implementation explicitly passes the actual popout chart context and intentionally supports popouts.

The safest current behavior is simply: generic plugin dispatch for this feature occurs only for the main Chart Data Output → main Chart Info path.

---

# Performance constraints

## 11. Keep the click path cheap

The framework was generalized specifically without eroding existing performance.

On ordinary Chart Info clicks, do not:

- rescan arbitrary directories
- reparse Python source manifests
- re-import enabled plugins
- reopen/reparse the Sun-Moon JSON on every click
- reopen/reparse Human Design JSON on every gate click
- instantiate Settings/plugin-manager UI

Expected hot path after warm-up:

1. obtain current plugin revision
2. use cached enabled plugin modules
3. invoke relevant `chart_info` handlers
4. Sun-Moon plugin performs dictionary lookup in already-cached JSON
5. render zero or a few paragraphs

No background thread/process is needed for this lookup.

---

# Companion-file lifecycle review

## 12. Deliberately decide how `data_files` behave on enable/disable

Inspect the merged generic runtime.

The initial framework version installs declared sibling data files into the plugin directory but may move only the `.py` file itself into `disabled/` when disabling.

That can be functionally acceptable because:

- an absent/disabled Python module cannot execute
- leaving inert JSON in the enabled plugin directory is cheap

But the behavior must be deliberate and tested.

Choose one consistent rule:

### Option A — preferred if minimal change

Only the registered primary plugin file controls enabled/disabled state. Companion data remains in the main plugin directory. Document/test this behavior.

### Option B — move plugin bundle together

Move the primary plugin plus all declared companion data atomically between enabled/disabled locations.

If choosing B, avoid partial moves and ensure enabling can determine the manifest/data list safely without executing disabled code.

Do **not** spend disproportionate effort on this if Option A is already reliable. Companion JSON lingering inertly is not a performance concern.

---

# Local plugin execution boundary

## 13. Do not broaden security scope in this PR

A `.py` plugin is executable local Python code. The intended boundary is:

- pre-install validation reads only a literal manifest via AST
- recognized filename is required
- companion files are validated before install
- plugin code executes only after installed/enabled and the relevant hook dispatch occurs
- plugin exceptions cannot bring down Chart Editor

Do not attempt to build a Python sandbox in this task. If stronger third-party-plugin isolation is desired later, that is a separate architectural project.

---

# Recommended work order

Codex should proceed in this order:

1. **Read the referenced PR diff and latest `main`.** Confirm what framework commits actually landed.
2. Inspect `analysis/plugins.py`, `human_design_plugins.py`, Settings plugin manager, the Sun-Moon plugin/data, current `app.py`, and plugin tests.
3. Run the existing targeted plugin tests **before editing** to capture current failures after merge.
4. Fix `app.py` imports to use generic plugin lifecycle/dispatch ownership.
5. Expand upload dialog filters to `.json` + `.py` while retaining exact-filename validation.
6. Implement the generic declarative Chart Info append renderer.
7. Integrate generic `chart_info` dispatch into the **main Chart Data Output position-click path**, after native rendering.
8. Explicitly prevent wrong-chart dispatch in popout/alternate Chart Info targets.
9. Repair stale plugin-manager tests caused by old Human Design module ownership.
10. Add generic plugin-runtime tests.
11. Add Sun-Moon plugin unit tests.
12. Add Chart Info integration/context-regression tests.
13. Run targeted plugin/Chart Info tests.
14. Run the broader test suite appropriate for the repository.
15. Perform the manual acceptance sequence below.
16. Review the final diff for accidental hot-take-data modifications and unrelated `app.py` churn.

Keep `app.py` edits surgical. Do not combine this task with unrelated refactoring simply because the file is large.

---

# Test commands

First inspect `pyproject.toml`, `pytest.ini`, CI workflow, or repository docs for the canonical environment and lint commands. Do not invent tooling that the repository does not use.

At minimum, run the existing plugin-manager test and all newly added plugin tests, e.g. conceptually:

```bash
pytest -q tests/test_plugin_manager.py
pytest -q tests/test_plugin_runtime.py tests/test_sun_moon_hot_takes_plugin.py
```

Use the actual filenames you create.

Also locate existing Chart Info / chart-summary interaction tests and run those targeted files.

Then run the broad suite if practical:

```bash
pytest -q tests/
```

If the full suite has unrelated existing failures, report them separately and distinguish pre-existing failures from task regressions.

Run whatever formatter/linter/type-check commands the repository itself specifies.

---

# Manual acceptance sequence

Perform all of these before considering the task complete:

1. Launch EphemeralDaddy normally.
2. Open Settings → Plugins.
3. Upload `docs/sun-moon_hot-takes.py` while `docs/sun_moon_hot_takes.json` is present beside it.
4. Confirm the plugin installs and Plugin Manager displays **Sun-Moon Hot Takes** as enabled.
5. Open a natal chart whose Sun/Moon combination has known reference text.
6. Click the **Sun** position row in Chart Data Output.
7. Confirm native Sun Chart Info renders first.
8. Confirm the Sun-Moon Hot Takes block is appended below it.
9. Verify exact styles:
   - header = `CHART_DATA_HIGHLIGHT_COLOR` + bold
   - average = italic
   - `Best case:` = bold label
   - `Worst case:` = bold label
10. Compare displayed descriptions to `docs/sun_moon_hot_takes.json` and confirm text is verbatim.
11. Click the **Moon** row and confirm the same Sun/Moon-combination supplement appears beneath Moon's native interpretation.
12. Click Mars and at least one other non-luminary position; confirm there is no Sun-Moon block.
13. Test a chart combination containing one or more null fields and verify omitted sections leave no orphan label.
14. Disable Sun-Moon Hot Takes in Plugin Manager.
15. Without restarting, click Sun/Moon again and confirm the supplement is absent.
16. Re-enable it and confirm the supplement returns without restart.
17. Verify **Human Design Gates-Lines Supplement** still installs/enables/disables and renders exactly as before.
18. Exercise at least one position-info popout/alternate Chart Info target and confirm it does not receive a Sun-Moon block derived from the wrong chart.

---

# Acceptance criteria

The task is complete only when all of the following are true:

- [ ] Generic plugin lifecycle APIs are consumed from the generic plugin module, not semantically owned by Human Design code.
- [ ] Existing `humdes_gates.json` behavior remains functional.
- [ ] Settings upload accepts recognized `.py` plugins as well as `.json` plugins.
- [ ] `sun-moon_hot-takes.py` installs with `sun_moon_hot_takes.json`.
- [ ] Enabled Python plugins are lazily loaded/cached rather than reparsed/reimported per click.
- [ ] Main Chart Data Output position clicks dispatch the generic `chart_info` hook.
- [ ] `app.py` contains no Sun-Moon-specific lookup logic.
- [ ] The app renderer maps declarative `highlight` to `CHART_DATA_HIGHLIGHT_COLOR`.
- [ ] Sun click shows the correct current chart Sun/Moon combination.
- [ ] Moon click shows the same correct current chart Sun/Moon combination.
- [ ] Non-Sun/Moon clicks do not show this plugin's supplement.
- [ ] Average/best/worst null handling matches requirements exactly.
- [ ] All hot-take description text remains verbatim.
- [ ] Disabling the plugin removes behavior without deleting/restarting the app.
- [ ] Re-enabling restores behavior without restart.
- [ ] Plugin exceptions do not crash Chart Editor.
- [ ] Popout/alternate-chart clicks cannot accidentally use unrelated `self._latest_chart` Sun/Moon signs.
- [ ] Existing plugin tests are updated for generic lifecycle ownership.
- [ ] New runtime, Sun-Moon, formatting, and context-regression tests pass.
- [ ] No unrelated `app.py` refactor/churn is included.

---

# Final report expected from Codex

When finished, report:

1. Exact files changed.
2. Where the Chart Info hook is dispatched and why that location avoids wrong-chart context.
3. How plugin output is rendered/styled.
4. How plugin caching/invalidation behaves.
5. Whether companion data files move on disable or remain inert in the main plugin directory, and why.
6. Exact targeted/full test commands run and results.
7. Manual acceptance results.
8. Any pre-existing failures or limitations that remain.

Do not report the feature complete if only the generic framework exists. **The feature is complete only when an installed/enabled Sun-Moon Hot Takes plugin visibly appends the correct current-chart interpretation to Chart Editor's Chart Info after Sun/Moon row clicks.**
