# Codex Handoff: Astro Twin Settings + Ranking Actions

## Repository / Branch

- Repository: `croweykid/ephemeraldaddy`
- Continue work on the existing branch: `codex/tidy-astro-twin-settings-and-ranking-actions`
- The user will open an edit in this existing branch.
- **Do not merge this branch.**
- **Do not create a pull request unless separately instructed.**
- **Do not modify `main`.**
- Make the final implementation and commit on this branch only after verification passes.

## Where the Previous Attempt Stopped

The last GitHub Actions checkpoint was:

- Run: `33398377658`
- Job: `99508343894`
- Job name: `finish`
- Conclusion: **failure**

Step status from that run:

1. Checkout — passed
2. Apply candidate patch — passed
3. Repair generated assertion quoting — passed
4. Compile changed Python — passed
5. Run focused regressions — **failed**
6. Remove temporary workflows — skipped
7. Commit finalized feature — skipped

Important implications:

- The generated candidate application source **compiled successfully**.
- The generated regression test file also **compiled successfully**.
- Earlier failures caused by malformed quote escaping in generated test assertions had already been fixed by this point.
- The current blocker is therefore one or more **actual focused pytest failures**, not Python syntax.
- The final feature commit from that workflow **did not land**, because the commit step was skipped.
- Nothing was merged.
- Temporary rescue workflows still need to be removed before the final commit.

Do **not** guess which assertion failed. Your first task is to reproduce the focused test failure locally and inspect the exact result.

## Primary Files

The implementation is concentrated in:

- `ephemeraldaddy/gui/dev_tools.py`
- `ephemeraldaddy/gui/features/charts/similarities_algorithm_log.py`
- `tests/test_astro_twin_settings_layout_source.py`

The ranking formatter changes in `similarities_algorithm_log.py` appeared to already be present on the branch during the previous attempt. **Inspect the current branch source before editing it. Do not duplicate code that is already correct.**

## Temporary Rescue Workflows

Several temporary workflow files were created solely to get the candidate patch onto the branch and diagnose it:

- `.github/workflows/codex-astro-twin-settings-finalize.yml`
- `.github/workflows/codex-astro-twin-settings-diagnose.yml`
- `.github/workflows/codex-astro-twin-settings-finish.yml`
- `.github/workflows/codex-astro-twin-settings-finish2.yml`

An earlier file named `.github/workflows/codex-astro-twin-settings-patch.yml` was already deleted.

You may inspect the remaining temporary workflows as a reference for the intended candidate source changes, but **do not continue using CI workflows as patch machinery**. Edit the real source and tests directly.

Before the final commit, remove all remaining temporary `codex-astro-twin-settings-*.yml` workflow files. Do not alter unrelated workflows.

# Required Final Behavior

## 1. Astro Twin Settings Intro

The Settings section should lead with:

```python
QLabel("Choose how Astro Twins are defined:")
```

Remove or avoid these obsolete labels/captions:

```python
QLabel("Scoring Methods")
"Choose the metric by which Astro Twins are defined:"
QLabel("Match preference")
QLabel("Astro Twin Calculator")
```

The result should read as one coherent settings section rather than several redundant nested headings.

## 2. Move Demographic Matching Below the Custom Scoring Panel

The scoring choices and Custom configuration belong first.

After:

```python
algorithm_layout.addWidget(custom_fields_frame)
```

the layout should:

1. add some vertical spacing,
2. add a horizontal divider,
3. show the **Demographic Matching** section,
4. finish with the stretch after that section.

Expected divider:

```python
demographic_algorithm_divider = QFrame()
demographic_algorithm_divider.setFrameShape(QFrame.HLine)
demographic_algorithm_divider.setFrameShadow(QFrame.Sunken)
```

Expected header:

```python
demographic_match_header = QLabel("Demographic Matching")
demographic_match_header.setStyleSheet(subheader_style)
```

Radio options, in this exact order:

| Label | Stored mode |
|---|---|
| `Include everyone (default)` | `none` |
| `Match assigned sex` | `sex` |
| `Opposite assigned sex` | `opposite_sex` |
| `Match gender identity` | `gender` |
| `Opposite gender identity` | `opposite_gender` |

`none` should be checked by default.

Do not restore a separate `Match preference` heading.

## 3. Placement Weighting Mode Must Be Inline

The placement weighting `QComboBox` should contain:

```text
Chart-defined weights
Generic base weights
Hybrid (generic + dominant body bonuses)
```

with item data:

```text
chart_defined
generic
hybrid
```

Use `PLACEMENT_WEIGHTING_MODE_TOOLTIPS` for the explanatory text.

Each combo item should receive its tooltip through `Qt.ToolTipRole`, and the combo itself should update its tooltip whenever the selected index changes, so the current choice is explainable without an extra label.

The combo must sit **inline on the same row as the Placement criterion label**.

Conceptually:

```text
[checkbox]  Placement Ⓘ   [Chart-defined weights ▼]   [weight]
```

Do not use a separate:

```python
QLabel("Placement-weight mode")
```

The `Reset Weights to Default` button stays below the factor grid rather than being moved into the Placement row.

## 4. `SimilarityAlgorithmAccuracyBrowser`

`SimilarityAlgorithmAccuracyBrowser` should support an optional callback:

```python
on_use_row: Callable[[dict[str, object]], None] | None = None
```

It should keep:

```python
self._expanded_rows
self._rows
self._on_use_row
```

### Refresh behavior

`refresh_ranking()` should load:

```python
aggregate_similarity_algorithm_accuracy(include_v2=True)
```

and format it with:

```python
format_similarity_algorithm_accuracy_ranking_html(
    self._rows,
    expanded_rows=self._expanded_rows,
    highlight_color=CHART_DATA_HIGHLIGHT_COLOR,
    factor_weight_color=self._factor_weight_color,
)
```

### Factor weight color

Use the existing shared red-to-green scale rather than introducing a second color algorithm:

```python
more_readable_color_scale_rgb_for_range(
    float(weight),
    0.0,
    scale_max,
)
```

Protect against a zero maximum, e.g. by using `1.0` when necessary.

Return CSS such as:

```python
f"rgb({red}, {green}, {blue})"
```

### Link handling

`_toggle_algorithm_details(url)` must:

- parse the row index from `url.path()`,
- for scheme `use`, invoke the callback for a valid row,
- pass a copied row dict rather than the browser's internal object,
- for scheme `algorithm`, toggle expansion and refresh,
- ignore unsupported schemes,
- safely ignore malformed row indexes.

## 5. Ranking "Use this" Must Actually Restore the Algorithm

Create a mapping from logged algorithm mode to the Settings radio:

```text
default
generic_astro
comprehensive
all_or_nothing
big_3
custom
database_distinction
```

Implement something equivalent to:

```python
apply_accuracy_ranking_row(row: dict[str, object])
```

### Normal algorithms

For a recognized non-Custom mode, selecting **Use this** should select the corresponding Settings radio.

### All or Nothing

This case must restore more than just the radio.

If the snapshot includes:

```python
settings["all_or_nothing_component"]
```

restore the corresponding criterion in `all_or_nothing_criterion_combo` using its item data, then select the All-or-Nothing radio.

A ranking entry that represented one All-or-Nothing criterion must not silently turn into a different criterion when reused.

### Custom

For Custom ranking rows, only switch to Custom if the row contains enough detail to reconstruct the settings.

Require:

- `algorithm_snapshot` to be a dict,
- `details_available` not to be false,
- `selected_factors` to be a list.

If an older/legacy ranking entry lacks reconstructable Custom details, **do not change the active scoring mode and pretend restoration succeeded**.

When details are available:

1. Set `preset_state["applying"] = True`.
2. Reset all factor checkboxes to off.
3. Reset all factor weights to `0.0`.
4. Apply every valid factor entry's `enabled` and `weight`.
5. Restore the snapshot's `placement_weighting_mode` when present and recognized.
6. Clear preset identity/state because this configuration now came from a ranking record rather than a named preset:
   - `preset_state["name"] = None`
   - `preset_state["preset_in_use"] = False`
   - set the preset combo to `-1` while signals are blocked
   - hide the preset status label
7. In `finally`, set `preset_state["applying"] = False`.
8. Only then select the Custom radio.

Instantiate the ranking browser with:

```python
SimilarityAlgorithmAccuracyBrowser(
    on_use_row=apply_accuracy_ranking_row
)
```

## 6. Research / Accuracy Panel Layout

Below:

```python
QPushButton("Show 90-100% similarities")
```

add a horizontal divider:

```python
research_accuracy_divider = QFrame()
research_accuracy_divider.setFrameShape(QFrame.HLine)
```

Then place the algorithm ranking below it.

The ranking should consume the remaining vertical room:

```python
research_layout.addWidget(algorithm_accuracy_label, 1)
```

Do not leave:

```python
research_layout.addStretch(1)
```

below the ranking.

Also remove any browser cap such as:

```python
self.setMaximumHeight(360)
```

The collapsible ranking is supposed to use the available Settings panel space rather than being trapped in a short box.

## 7. Ranking Formatter

File: `ephemeraldaddy/gui/features/charts/similarities_algorithm_log.py`

Verify the formatter has these behaviors. They may already exist on the current branch.

### Use column

The table has a centered Use column:

```html
<th align="center">Use</th>
```

Each row has a link using the zero-based row index:

```html
href="use:{index - 1}"
```

### Custom factor details

Only **enabled** factors should be listed.

Build/filter an `enabled_factors` collection using the factor's `enabled` state, then iterate only that collection.

Use:

```python
bool(factor.get("enabled", False))
```

Each shown factor should be formatted like:

```python
f"{label}: {weight:g} (on)"
```

There should be no `(off)` factor entries.

For each enabled factor, obtain the display color through:

```python
factor_weight_color(weight, maximum_weight)
```

The maximum should be based on the relevant displayed factor weights so the shared scale can show relative strength meaningfully.

# Existing Behavior That Must Not Regress

The focused source-level tests also represent prior requirements. Preserve these unless an assertion itself is clearly stale relative to the specifications above.

- **Database Distinction** remains before **Custom**, with Custom the final scoring option.
- Database Distinction's explanation remains tooltip-only.
- The Custom subpanel retains its intended visual grouping.
- The preset-save button remains at the bottom of the Custom panel.
- The Custom factor grid keeps centered/renamed headers and compact columns.
- The currently selected scoring method uses `CHART_DATA_HIGHLIGHT_COLOR`.
- The Total completion display shows the green completion percentage at full completion.
- The Custom preset selector and preset-in-use state remain wired.
- Saving a loaded preset still offers the correct update-existing vs save-new choices.
- `Manage Presets` remains file-gated and positioned to the right of the preset selector.

Do not "fix" the new requirements by deleting these existing behaviors.

# Focused Regression Tests

The intended focused test file includes these tests:

```text
test_algorithm_caption_leads_and_demographic_matching_follows_custom_subpanel
test_demographic_matching_labels_order_and_no_tooltips
test_database_distinction_precedes_custom_as_final_scoring_option
test_database_distinction_explanation_is_tooltip_only
test_custom_subpanel_has_visual_cues_and_preset_button_at_bottom
test_custom_weight_grid_uses_centered_renamed_headers_and_compact_columns
test_placement_weight_mode_is_inline_with_placement_criterion_without_label
test_placement_weighting_modes_have_item_and_selected_tooltips
test_selected_scoring_method_uses_chart_data_highlight_color
test_total_only_shows_green_completion_percentage_at_one
test_custom_preset_selector_and_in_use_state_are_wired
test_saving_loaded_preset_offers_exact_update_or_new_choices
test_manage_presets_button_is_file_gated_and_right_of_selector
test_research_accuracy_ranking_fills_space_below_button_and_divider
test_research_use_this_applies_mode_custom_snapshot_and_all_or_nothing_criterion
test_research_weight_coloring_uses_shared_zero_based_red_green_scale
test_ranking_formatter_has_use_action_and_filters_disabled_factors
```

Two generated assertions previously had broken Python quote nesting. That was already diagnosed. If you encounter these checks, their outer string quotes need to allow the inner `"enabled"` / `"weight"` strings:

```python
assert 'calculator_checkboxes[key].setChecked(bool(factor.get("enabled", False)))' in SECTION
assert 'calculator_weights[key].setValue(float(factor.get("weight", 0.0)))' in SECTION
```

Do not reintroduce the malformed double-quoted versions.

# Required Work Sequence

## 1. Reproduce the current failure first

On the existing branch, run:

```bash
python -m pytest -q tests/test_astro_twin_settings_layout_source.py
```

Record the exact failing test(s) and assertion(s).

The previous handoff did not capture the final pytest output, so the failure must be regenerated rather than inferred.

## 2. Inspect the current source

Compare the actual branch files against the requirements above.

The temporary rescue workflows contain the previous candidate patch and can be consulted if useful, but the current source is authoritative.

Do not mechanically paste the workflow-generated candidate if the branch has changed around it.

## 3. Implement/fix the real files directly

Edit:

```text
ephemeraldaddy/gui/dev_tools.py
ephemeraldaddy/gui/features/charts/similarities_algorithm_log.py
tests/test_astro_twin_settings_layout_source.py
```

as required.

A test should only be changed when its expectation is wrong relative to the specified behavior. Do not modify tests merely to make a wrong implementation pass.

## 4. Compile all changed Python

Run:

```bash
python -m py_compile ephemeraldaddy/gui/dev_tools.py
python -m py_compile ephemeraldaddy/gui/features/charts/similarities_algorithm_log.py
python -m py_compile tests/test_astro_twin_settings_layout_source.py
```

All must pass.

## 5. Run the focused regression file

```bash
python -m pytest -q tests/test_astro_twin_settings_layout_source.py
```

All focused tests must pass.

## 6. Run nearby relevant tests

Search the test suite for tests covering:

- similarity algorithm logging,
- accuracy/ranking aggregation,
- algorithm snapshots,
- Custom presets,
- scoring method state,
- All-or-Nothing criterion restoration.

Run the relevant nearby test modules or a sensible broader subset.

Do not expand scope into unrelated failing areas of the application.

## 7. Check the diff

Run:

```bash
git diff --check
```

Then review the full diff for:

- accidental unrelated edits,
- duplicated UI construction,
- stale temporary workflow code,
- malformed layout ordering,
- snapshot restoration that silently loses settings.

## 8. Remove temporary rescue workflows

Delete all remaining files matching:

```text
.github/workflows/codex-astro-twin-settings-*.yml
```

These were scaffolding for the interrupted attempt and should not be part of the finished feature.

Do not remove unrelated workflows.

## 9. Re-run verification after cleanup

At minimum:

```bash
python -m pytest -q tests/test_astro_twin_settings_layout_source.py
git diff --check
```

If any source changed during cleanup/final correction, repeat the compile commands as well.

## 10. Commit, but do not merge

Once the implementation satisfies the requirements and verification passes:

- commit the completed changes to `codex/tidy-astro-twin-settings-and-ranking-actions`,
- do **not** merge,
- do **not** create a PR,
- do **not** modify `main`.

# Definition of Done

The task is complete only when all of the following are true:

- Settings begins with `Choose how Astro Twins are defined:`.
- Redundant old headings are gone.
- Demographic Matching sits below the Custom configuration with a divider.
- Placement weighting mode is inline with Placement.
- Placement weighting tooltips work per item and for the selected value.
- Research ranking fills its available panel height.
- Ranking has a functioning **Use this** action.
- Normal ranking rows restore the appropriate scoring radio.
- All-or-Nothing rows restore their criterion as well as their mode.
- Reconstructable Custom rows restore factor enabled states, weights, placement weighting mode, and clear named-preset state.
- Non-reconstructable legacy Custom rows do not falsely switch the Settings mode.
- Ranking factor details show enabled factors only.
- Factor strength colors use the shared zero-based red-to-green scale.
- Focused regression tests pass.
- Relevant nearby tests pass or any unrelated pre-existing failure is clearly identified.
- `git diff --check` passes.
- All temporary `codex-astro-twin-settings-*.yml` workflows are deleted.
- The final changes are committed only to the existing feature branch.

# Final Report Back to User

When finished, report:

1. The exact focused regression failure(s) you found at the start.
2. The files changed.
3. A concise description of the final UI/behavior changes.
4. Every verification command run and whether it passed.
5. Any remaining uncertainty or test limitation.
6. The final commit SHA.
7. Confirmation that the temporary rescue workflows were removed.
8. Confirmation that nothing was merged and `main` was not changed.
