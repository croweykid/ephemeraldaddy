# Chart View save-integrity regressions

## What this test file is

`tests/test_chart_view_save_integrity_regression_source.py` is a **static source-contract test**.
It opens these production files as text:

- `ephemeraldaddy/gui/app.py`
- `ephemeraldaddy/core/db.py`
- `ephemeraldaddy/gui/features/charts/cv_right_panel_stack.py`

It then extracts selected functions and checks that critical calls and guards are
still present and in the required order. It is a fast tripwire for refactors; it
does not click through the application.

For example, the first test finds `on_update_chart()` and
`update_chart_lightweight_metadata()`. It verifies that a non-recalculating save
uses the lightweight update and that the lightweight SQL statement does not write
calculated positions or houses. Other tests verify the timer routing, the
recalculation-precedence guard, Material Facts save ordering, leave-prompt
deferral, and the Anagrams scheduling condition.

## What a passing result means

A pass means the inspected implementation still has these structural guarantees:

| Area | Contract checked automatically |
| --- | --- |
| Alias/tag/note/score saves | The save path can use `update_chart_lightweight_metadata()` rather than the full `update_chart()` path. |
| Rapid subjective edits | Sentiments, relationship types, and scores feed one 2-second debounced subjective-save timer. |
| Calculation edits | Birth time, rectified time, and rectification range queue the timing preview and mark the metadata autosave as requiring recalculation. |
| Mixed edits | A subjective timer firing while recalculation is pending defers to the recalculating metadata timer and does not clear the dirty flag. |
| Material Facts | Material Facts are written before the save path clears the dirty state. |
| Leaving Chart View | Timed saves defer while the Save/Discard/Cancel prompt is open, and the Save action remains wired to the formal save path. |
| Subjective Notes tab | Anagrams are scheduled only for the ABC panel, not merely because Subjective Notes became active. |

## What it does **not** prove

These tests do not instantiate `QApplication`, operate real widgets, wait for Qt
timers, measure save duration, compare a before/after ephemeris payload, or close
and reopen a chart from a real database. They therefore do not by themselves
prove that:

- a save is perceptibly quick on a user's machine;
- the final value from a burst of actual Qt signals wins;
- every edited value survives a real close/reopen cycle;
- a platform-specific close event flushes or prompts correctly; or
- calculated positions numerically match newly entered birth data.

Those are end-to-end GUI observations and should be checked with the manual
procedure below until a controlled Qt/database integration harness exists. A
passing static suite should be described as “the save-path contracts are intact,”
not as proof that the complete user workflow was executed.

## Running the automated checks

From the repository root:

```bash
PYTHONPATH=. pytest -q tests/test_chart_view_save_integrity_regression_source.py
```

To include the older, related save-path checks:

```bash
PYTHONPATH=. pytest -q \
  tests/test_chart_view_save_integrity_regression_source.py \
  tests/test_chart_view_metadata_only_save_source.py \
  tests/test_retcon_lucygoosey_autosave.py
```

Each dot in pytest's compact output is one passing test. A failure shows the
contract that disappeared and the source fragment that no longer matched. First
determine whether production behavior regressed or whether a safe refactor made
the textual assertion stale; do not change an assertion merely to make it green.

## Manual GUI regression procedure

Use a disposable copy of the database and one saved chart with a known birth
time. Record the chart's UID and a baseline export or screenshot of its calculated
positions before starting.

1. **Lightweight fields:** Change only an alias, tag, note, or score and save.
   Confirm the save completes promptly. Reopen the same UID and verify the field
   persisted and the recorded calculated positions did not change.
2. **Debounce:** Rapidly change several subjective fields, stop editing for more
   than two seconds, then leave and reopen the same UID. Verify the last value of
   every field persisted and that no repeated full-calculation/loading sequence
   appeared.
3. **Calculation inputs:** Change birth time, place, rectified-time state, and
   rectification range one at a time. After each save, reopen the UID and verify a
   full recalculation occurred and the calculated output matches the new input.
4. **Timer race:** Change one birth/calculation field and immediately toggle a
   sentiment before either debounce interval expires. Wait, reopen the UID, and
   verify both edits persisted. Confirm analytics that depend on birth data were
   invalidated/refreshed.
5. **Material Facts:** Edit Material Facts, then make a subjective edit that
   triggers autosave. Leave and reopen the UID. Verify the Material Facts remain
   present; do not infer they were saved merely from the dirty indicator.
6. **Pending save while leaving:** Make a subjective edit and immediately switch
   charts or close Chart View. Verify the pending change is either flushed or a
   Save/Discard/Cancel prompt is shown. Reopen the original UID and confirm there
   was no silent loss.
7. **Anagrams isolation:** Open Subjective Notes without visiting or expanding the
   ABC/Anagrams UI. Confirm no Anagrams calculation, loading state, or rendered
   output is scheduled solely by activating Subjective Notes.

Record the application build/commit, operating system, database copy, chart UID,
before/after values, position comparison, observed loading indicators, and result
for every step. That record is the evidence for the end-to-end portion of the
regression run.
