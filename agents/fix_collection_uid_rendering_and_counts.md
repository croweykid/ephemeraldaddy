# Fix custom collection rendering after `chart_id` → `chart_UID` migration

## Problem statement

Custom collections currently behave as though they contain charts internally, but Database View can render them as empty.

Observed behavior:

1. Select several charts in Database View.
2. Open **Manage Collections** and click **New**.
3. Confirm creation from the selected charts.
4. Open the newly created collection.
5. Database View footer reports the correct collection size, but no chart rows are visible.
6. Return to **All** or **Public**, re-select the same charts, and choose **Add selected charts** for that collection.
7. The manager reports that the charts are already members.

This is strong evidence that collection persistence and membership are working. The charts are being lost later in the Database View display/filter path.

A related UX change is also required: Collection Manager should display custom collections as:

```text
Collection Name (17)
```

rather than only:

```text
Collection Name
```

The count should represent live/resolvable members where practical, not stale orphaned UIDs.

---

## Relevant existing architecture

Primary files:

- `ephemeraldaddy/gui/app.py`
- `ephemeraldaddy/gui/features/charts/collections.py`
- `ephemeraldaddy/gui/features/database_view/collections/collection_manager_panel.py`
- `tests/test_collections.py`
- `tests/test_database_view_selection_persistence_source.py`
- `tests/test_database_view_performance.py`

Important current behavior already confirmed:

- `CustomCollection` is UID-oriented.
- `chart_belongs_to_collection()` is UID-first and retains local integer ID fallback only for legacy compatibility.
- Creating a collection from selected charts stores chart UIDs.
- Adding selected charts to an existing collection also operates on UIDs.
- The Database View footer count is calculated after active-collection membership filtering.

Therefore, **do not rewrite collection persistence back around integer chart IDs**. That is not the defect.

---

## Likely root cause

The UID migration was only partially completed in the Database View render/filter pipeline.

The active-row caches were migrated from integer-ID keys:

```python
self._active_chart_rows_by_id
self._displayed_chart_rows_by_id
```

to UID keys:

```python
self._active_chart_rows_by_uid
self._displayed_chart_rows_by_uid
```

The active collection path also correctly filters rows and then records:

```python
self._active_collection_total_count = len(rows)
```

If that footer count is correct, the collection rows have already survived `_chart_in_active_collection(row)`.

However, `_chart_matches_filters()` still appears to accept a local `chart_id`, convert that ID back to a UID, and then use the UID to look up an already-available row:

```python
chart_row = self._active_chart_rows_by_uid.get(
    str(get_chart_uid(chart_id) or "").strip().upper()
)
```

That is an unnecessary and fragile ID → UID round trip inside a render path that already has both the row and normalized UID in hand.

Even if this is not the only stale-ID branch, it is the wrong contract and should be eliminated.

### Important diagnostic boundary

The defect must occur after:

```python
self._active_collection_total_count = len(rows)
```

and before the corresponding rows are inserted into the visible list, e.g. before/around:

```python
self.list_widget.addItem(item)
```

That is the section to inspect closely for any remaining assumptions that logical chart identity is an integer `chart_id`.

---

# Proposed patch

## 1. Make Database View filtering UID-native

### Preferred design

Do not make `_chart_matches_filters()` reconstruct a row from a local integer ID.

Instead, pass the row itself into the function.

Conceptually change this style:

```python
matches_filters = self._chart_matches_filters(chart_id, ...)
```

into:

```python
matches_filters = self._chart_matches_filters(row, ...)
```

and update the helper along these lines:

```python
def _chart_matches_filters(self, chart_row, ...):
    if not self._has_active_chart_filters():
        return True

    chart_uid = str(chart_row[30] or "").strip().upper()

    # Continue filter evaluation using chart_row directly.
    # If another cache needs a key, use chart_uid.
```

This is preferred because the render loop already has the authoritative row. It should not perform another database/cache identity lookup simply to recover the same row.

### Acceptable second-best design

If changing the helper to accept rows would create too much churn, change it to accept a UID:

```python
def _chart_matches_filters(self, chart_uid: str, ...):
    chart_uid = str(chart_uid or "").strip().upper()
    chart_row = self._active_chart_rows_by_uid.get(chart_uid)
    ...
```

Then call it with the UID already extracted from the row in `_populate_list()`.

Example:

```python
item_chart_uid = str(chart_uid or "").strip().upper()
matches_filters = self._chart_matches_filters(item_chart_uid, ...)
```

### Do not do this

Do not keep this pattern in the normal render/filter path:

```python
get_chart_uid(chart_id)
```

Local integer IDs should be converted/resolved only at explicit persistence/legacy boundaries. Once Database View has a normalized UID, that UID should remain the logical identity throughout selection, filtering, rendering, drag/drop, and collection membership.

---

## 2. Audit `_populate_list()` for all stale integer-ID assumptions

Within the portion of `_populate_list()` after active collection filtering, audit every branch that can skip a row.

The row should have a normalized UID established once:

```python
item_chart_uid = str(chart_uid or "").strip().upper()
```

From that point onward:

- `_active_chart_rows_by_uid` must be keyed by `item_chart_uid`.
- `_displayed_chart_rows_by_uid` must be keyed by `item_chart_uid`.
- Selection persistence must use UID.
- `Qt.UserRole` data used to identify a chart should use UID where the item represents chart identity.
- Filtering should consume `item_chart_uid` or the row directly.
- Any hidden/skip logic should not depend on successfully re-resolving `chart_id -> chart_UID`.

Integer row IDs may still exist as ordinary row metadata for database operations, but must not be the identity contract between UI stages.

### Temporary assertions/debug counters

During implementation, add temporary diagnostics or assertions around this boundary if needed:

```python
assert self._active_collection_total_count == len(self._active_chart_rows_by_uid)
```

For a failing collection, useful counters are:

```text
collection members:      8
active UID rows:         8
post-display filtering:  8
list items inserted:     8
```

If the first two are 8 and a later count becomes 0, inspect the exact skip branch responsible.

Do not leave noisy console logging in production unless it follows an existing debug logging convention.

---

## 3. Preserve legacy compatibility only at the boundary

`chart_belongs_to_collection()` currently has UID-first membership with integer-ID fallback. Preserve that unless there is a separate reason to remove it.

Desired semantics:

```python
if normalized_uid and normalized_uid in collection.chart_uids:
    return True

# Legacy compatibility only
if chart_id is not None and chart_id in collection.chart_ids:
    return True
```

The fallback is useful for reading old persisted state, but newly created/updated collections should continue to write UIDs.

Do not add new code that populates `chart_ids` for newly created collections merely to make the UI work.

---

## 4. Add member counts to Collection Manager labels

In `collection_manager_panel.py`, custom collection list items should display:

```python
f"{custom_collection.name} ({collection_count})"
```

while retaining stable collection identity independently from display text:

```python
item = QListWidgetItem(f"{custom_collection.name} ({collection_count})")
item.setData(Qt.UserRole, custom_collection.collection_id)
```

Any code that currently parses the visible item text to recover a collection name or collection ID should be changed to use `Qt.UserRole` or another explicit data role.

### Count semantics

Prefer a count of live/resolvable chart UIDs rather than simply:

```python
len(custom_collection.chart_uids)
```

because a collection can theoretically contain a UID whose chart has since been deleted.

If Collection Manager already has access to Database View's loaded UID map, use something equivalent to:

```python
live_chart_uids = set(self._local_row_id_by_chart_uid)
collection_count = len(custom_collection.chart_uids & live_chart_uids)
```

or derive the live UID set from the current loaded chart rows.

Important performance point: compute the live UID set **once per Collection Manager refresh**, then reuse it for every collection. Do not issue one database query per collection.

If the manager does not currently have an appropriate live UID set without introducing awkward coupling, `len(custom_collection.chart_uids)` is acceptable as an initial implementation, but document that it is persisted membership count rather than live chart count.

### Refresh behavior

Counts must update after:

- creating a collection from selected charts;
- adding selected charts;
- removing charts;
- deleting a chart if live-count semantics are implemented;
- deleting/renaming collections where the list is refreshed anyway.

---

# Tests to add

## A. Create → activate → visible rows regression test

This is the missing high-value regression test.

Pseudo-test:

```python
select_charts(A_UID, B_UID, C_UID)
create_collection_from_selection("Test")

collection = get_collection("Test")
assert collection.chart_uids == {A_UID, B_UID, C_UID}

activate_collection(collection.collection_id)
populate_list()

assert window._active_collection_total_count == 3
assert window.list_widget.count() == 3
```

The exact UI fixture may differ. The important assertion is that collection membership count and visible rendered item count agree when no other filters are active.

This test would have caught the current regression.

---

## B. UID survives local row-ID changes

A collection must remain valid if a chart's transient/local integer row ID changes while its UID remains the same.

Conceptually:

```python
original = row(id=12, uid=A_UID)
collection.chart_uids = {A_UID}

# Simulate reload/reimport/reindex with a different local id.
reloaded = row(id=104, uid=A_UID)

assert chart_belongs_to_collection(reloaded, collection)
assert collection_view_displays(reloaded)
```

This protects the entire reason for the UID migration.

---

## C. Existing-member add remains idempotent

```python
collection.chart_uids = {A_UID, B_UID}
add_selected_to_collection([A_UID, B_UID])

assert collection.chart_uids == {A_UID, B_UID}
assert rendered_members == 2
```

The current "already in collection" message is evidence that this storage behavior already works; retain it.

---

## D. UID normalization

Ensure comparisons are case-normalized consistently:

```python
collection.chart_uids = {A_UID.upper()}
row_uid = A_UID.lower()

assert chart_belongs_to_collection(...)
assert row_is_visible_in_collection(...)
```

If UIDs are canonicalized at persistence time, test that instead. The important point is that inconsistent casing must not make collection rows disappear.

---

## E. Collection Manager count labels

Add a test around the list refresh/population function:

```python
collection.chart_uids = {A_UID, B_UID, C_UID}
refresh_collection_list()

item = find_collection_item(collection.collection_id)
assert item.text() == "Test (3)"
assert item.data(Qt.UserRole) == collection.collection_id
```

Also verify that add/remove operations update the label after refresh.

If live/resolvable counts are implemented, include an orphan UID:

```python
collection.chart_uids = {A_UID, B_UID, MISSING_UID}
assert item.text() == "Test (2)"
```

---

# Existing tests that should continue to pass

Run at minimum:

```bash
pytest tests/test_collections.py
pytest tests/test_database_view_selection_persistence_source.py
pytest tests/test_database_view_performance.py
```

Also run any tests matching Database View, Collection Manager, and chart UID migration behavior.

If the repository has a practical standard full-suite command, run it before finalizing the PR.

---

# Acceptance criteria

The patch is complete when all of the following are true:

1. Create a collection from N selected charts.
2. Activate that collection.
3. Database View footer reports N charts.
4. N corresponding rows are visible when no other filters/search terms are active.
5. Selecting those same charts from All/Public and trying to add them again remains idempotent and does not create duplicates.
6. Database View filters still work inside custom collections.
7. Collection identity is UID-based through the display/filter pipeline; no normal rendering path performs an unnecessary `chart_id -> chart_UID` re-resolution.
8. Collection Manager displays `Name (N)` for each custom collection.
9. The visible count refreshes after collection membership changes.
10. Existing legacy collection compatibility remains intact.
11. Regression tests cover create → activate → render and UID persistence across local ID changes.

---

# Non-goals

Do not use this patch as an excuse to:

- redesign the full collection persistence format;
- remove all legacy `chart_id` support across the application;
- refactor unrelated portions of the very large `app.py`;
- change search/filter semantics;
- disable filters inside collections;
- add per-collection database queries merely to obtain counts.

Keep the PR narrow: repair the UID identity handoff in Database View, add collection counts, and add regression coverage.

---

# Suggested PR title

```text
Fix UID-based custom collection rendering and show member counts
```

## Suggested PR summary

```markdown
## Summary
- keep custom collection rendering UID-native through Database View filtering
- remove the stale local-ID → UID re-resolution from the row display path
- show collection member counts in Collection Manager
- add regressions for create → activate → render and UID persistence across local row-ID changes

## Why
Collection membership was already persisted correctly by UID: the footer reported the correct number of collection members and attempts to re-add them reported that they already existed. Rows were being lost later in Database View's post-membership render/filter pipeline after the UID migration.
```
