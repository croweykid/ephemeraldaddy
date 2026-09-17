# EphemeralDaddy Batch Tagging Performance and Roster-State Patch Plan

## Status

- Target repository: `croweykid/ephemeraldaddy`
- Baseline: current `main` after PR #2303
- Scope: Database View → Batch Editor → Tags
- Primary code paths:
  - `ephemeraldaddy/gui/app.py`
  - `ephemeraldaddy/gui/dbv_search_panel.py`
  - `ephemeraldaddy/core/db.py`
- Purpose: implementation plan only; no source changes are included in this document

## Problem statement

Applying a tag through Batch Editor can take far longer than the underlying database update warrants. When the operation causes the Database View roster to refresh, the middle panel can return to the top or another unexpected viewport position instead of remaining where the user was working.

These symptoms have related causes:

1. The tag database writer is narrow, but the post-save UI path can perform broad work.
2. Active tag filters can turn a one-field metadata edit into a complete database hydration and roster rebuild.
3. Adding a previously unknown tag can rebuild the entire Search-panel tag tree.
4. An expanded Database Analytics tag section can be recalculated synchronously.
5. The roster rebuild preserves selected IDs but does not preserve the roster's current item or viewport anchor.

## Confirmed current behavior

### The database write is not the main problem

`add_tag_to_charts_by_uid()` already:

- uses stable chart UIDs;
- reads only the selected rows;
- updates only the `tags` column;
- uses one SQLite transaction;
- avoids complete chart recalculation and derived-cache persistence.

The database layer should remain narrow. A bulk-SQL rewrite may be considered later if profiling shows the selected-row loop matters for very large selections, but it is not the first repair target.

### The expensive post-save chain

The current add-tag route is approximately:

```text
_on_batch_tags_apply()
  → add_tag_to_charts_by_uid()
  → patch selected cached Chart objects
  → _finalize_batch_tag_updates()
      → refresh_tag_catalog_for_added_tags()
      → _update_batch_tag_state()
      → optional tag-distribution render
      → optional Property Manager refresh
      → when tag filters are active:
          _refresh_filters_after_batch_edit()
            → deferred _refresh_charts()
              → list_charts()
              → rebuild identity indexes and collection counts
              → refresh several unrelated selectors
              → _populate_list()
                → clear the roster
                → sort and refilter every row
                → hydrate chart data when required by row decorations
                → recreate every visible QListWidgetItem
```

`refresh_metrics=False` prevents the broad analytics refresh in this filtered-tag path, but it does not make `_refresh_charts()` lightweight. The roster and several adjacent data structures are still rebuilt.

### Why the roster jumps

`_populate_list()` preserves persistent selection by UID/local row ID, but it does not capture or restore:

- `list_widget.currentItem()` by chart UID;
- the UID of the top visible roster item;
- the top item's pixel offset within the viewport;
- the vertical scrollbar value as a fallback.

The method clears the `QListWidget` and constructs new items. Selection is reapplied during reconstruction, but the viewport is left to Qt. With multiple selected rows or no surviving current item, the resulting location can look arbitrary.

## Required user-visible behavior

After applying or removing a tag:

1. The save should complete promptly for ordinary selections.
2. The selected charts should remain selected when they still match the active filters.
3. The current row should remain current when it still exists.
4. The same chart should remain at the top of the visible roster, at approximately the same pixel offset.
5. If the top-visible chart disappears because the tag change legitimately changes filter membership, the viewport should anchor to the nearest surviving neighboring row.
6. If there are no active tag filters, the roster should not be rebuilt at all.
7. Tag completers, the Batch Editor tag summary, visible tag filters, expanded tag analytics, and any open Property Manager must eventually reflect the saved state.
8. Tag-only changes must not trigger astrological recalculation, broad prediction invalidation, or unrelated Database Analytics work.

## Proposed repair

### Phase 1: introduce a roster-view snapshot

Add a small UID-based state object outside `app.py` if practical, following the repository's extraction direction. A suitable home is `ephemeraldaddy/gui/features/database_view/chart_list.py` or a new sibling module dedicated to roster state.

Suggested data:

```python
@dataclass(frozen=True)
class ChartRosterViewState:
    selected_uids: tuple[str, ...]
    current_uid: str | None
    top_visible_uid: str | None
    top_visible_offset: int
    scrollbar_value: int
```

Capture rules:

- Obtain chart identity from the existing item UID roles, never from visible text or display position.
- Record persistent selection, not only currently visible selection.
- Use `list_widget.itemAt(QPoint(0, 0))` or the first intersecting item as the viewport anchor.
- Record the anchor item's `visualItemRect(item).top()` so restoration does not gradually drift.
- Retain the raw scrollbar value only as a fallback.

Restore rules, after item reconstruction and layout completion:

1. Restore selection by UID.
2. Restore `currentItem` by `current_uid` without discarding multi-selection.
3. Find `top_visible_uid`; position it at the captured offset.
4. If that UID no longer exists, use the nearest surviving UID based on the pre-refresh ordered UID list.
5. If no UID anchor survives, restore the bounded scrollbar value.
6. Queue one `QTimer.singleShot(0, ...)` restoration if Qt has not finalized item geometry yet. Avoid repeated timers.

This snapshot/restore utility should be usable by other unavoidable roster rebuilds, but the initial patch should wire it only into the batch-tag/filter path and any narrowly shared helper required for testing.

### Phase 2: stop using `_refresh_charts()` for tag-filter maintenance

Tag edits already know:

- which chart UIDs changed;
- which local row IDs correspond to them;
- the new tag value or removed tag value;
- whether any tag-search filter is active.

Use that information instead of rereading the entire database.

Add a targeted method with a name such as:

```python
def _refresh_roster_after_tag_change(
    self,
    changed_uids: set[str],
    *,
    added_tags: Sequence[str] = (),
    removed_tags: Sequence[str] = (),
) -> None:
    ...
```

Responsibilities:

1. Patch the tag field in the corresponding `_chart_rows` tuples. The tags field is already part of the lightweight `list_charts()` projection.
2. Keep `_active_chart_rows_by_uid` and `_displayed_chart_rows_by_uid` consistent for changed rows.
3. Update cached `Chart.tags` when a cached chart exists; do not load a complete Chart merely to patch tags.
4. If no tag-related filter is active, stop after cache/UI synchronization. Do not rebuild the roster.
5. If tag filters are active, reevaluate only the changed rows against the current filter state.

For each changed UID under active filters, there are three cases:

| Before | After | Required roster action |
| --- | --- | --- |
| visible | visible | update the existing row only if its displayed content depends on tags; otherwise leave it in place |
| visible | hidden | remove that one item |
| hidden | visible | insert that one item at its correctly sorted position |

If targeted insertion is too risky for the first patch, a scoped `_populate_list()` remains acceptable provided it operates on the already-patched `_chart_rows`, skips `list_charts()` and unrelated refreshes, and wraps the rebuild in the roster-view snapshot. The important boundary is: do not call the general `_refresh_charts()` hydration pipeline for a tag-only edit.

### Phase 3: separate tag-catalog updates from full tag-tree reconstruction

`refresh_tag_catalog_for_added_tags()` currently merges the new tag efficiently at the data level, but `refresh_search_tags_list()` can rebuild the entire tree when its signature changes.

Add an incremental insertion path for one or a small number of new tags:

- insert a new uncategorized tag in case-insensitive sorted order;
- create missing category parents for hierarchical tags;
- preserve existing checkbox objects and their modes;
- preserve category expansion state;
- preserve the Search tag tree viewport;
- update `_dbv_search_tag_tree_signature` after insertion;
- fall back to the established complete rebuild only when the tree is missing, corrupt, or structurally incompatible.

If the Search tags tree is collapsed, update `_known_chart_tags` and completer models immediately but defer tree widget creation until the user expands it.

### Phase 4: keep analytics refresh field-scoped and deferred

The expanded tag-distribution section is the only Database Analytics section whose displayed data necessarily changes after a tag edit.

- Invalidate only `tag_distribution`.
- If it is visible and expanded, schedule its refresh after the roster/UI state has settled rather than rendering it inside the save callback.
- Coalesce repeated tag edits into one pending refresh.
- Do not refresh similarity calculations, Traits, Rankings, astrological prevalence, or prediction norms.
- Keep the existing collapsed/hidden check.

### Phase 5: constrain Property Manager synchronization

If a Property Manager is open to Tags, its usage counts should refresh. An open manager displaying an unrelated metadata field should not be rebuilt.

Prefer a field-aware call such as:

```python
coordinator.refresh_open_widgets(changed_fields={"tags"})
```

The coordinator can then refresh only live dialogs whose current field is affected. This is secondary to the roster repair but belongs in the same performance audit.

## Suggested implementation order

1. Add roster-view snapshot and restoration helpers with unit tests.
2. Capture and restore roster state around the existing filtered-tag rebuild. This fixes the disruptive jump first.
3. Patch `_chart_rows` tag values in place after successful writes.
4. replace the filtered-tag call to `_refresh_filters_after_batch_edit()` with a tag-specific roster refresh that does not call `_refresh_charts()`.
5. Make new-tag tree insertion incremental or lazy.
6. Defer and coalesce the tag-distribution render.
7. Make Property Manager refresh field-aware if profiling shows meaningful cost.
8. Remove batch-tag debug plumbing only in a separate cleanup change, after the repaired path is stable.

## Regression coverage

### Database writer tests

Retain the existing assertions that tag add/remove:

- use UID-native writers;
- update only `charts.tags`;
- do not call `update_chart()`;
- do not calculate dominant weights;
- preserve one-transaction behavior across SQLite parameter chunks.

Add a behavioral test proving that mixed selections return only UIDs whose serialized tags actually changed.

### No-filter fast-path tests

Given selected charts and no active tag filter:

- applying an existing tag must not call `_refresh_charts()`;
- applying a new tag must not call `_refresh_charts()`;
- removing a tag must not call `_refresh_charts()`;
- `_chart_rows`, `_chart_cache`, tag completers, and the Batch Editor summary must reflect the change;
- unrelated analytics refresh methods must not run.

### Active-filter tests

Cover required, optional, excluded, and `untagged` modes:

- a changed visible row remains visible;
- a changed visible row is removed when it no longer matches;
- a previously hidden row is inserted when it begins matching;
- unchanged rows are not reconstructed on the targeted path;
- persistent hidden selections remain intact;
- sorting remains correct after insertion.

### Roster-state tests

Use a real or sufficiently faithful `QListWidget` test:

- scroll to the middle of a roster;
- select multiple nonadjacent charts;
- set a current item distinct from the top-visible item;
- trigger the necessary tag-filter update;
- process the Qt event queue;
- assert selection UIDs, current UID, top-visible UID, and approximate pixel offset.

Also test:

- the top-visible UID being removed;
- the current UID being removed;
- filtering to an empty roster;
- descending sorts;
- changing membership near the beginning and end of the list;
- several rapid tag applications before a deferred refresh runs.

### Tag-tree tests

- Adding one new tag does not clear and recreate existing tree widgets.
- Existing filter modes and logic buttons survive insertion.
- Hierarchical tags create or reuse the correct parent path.
- Expansion and scroll state survive insertion.
- A collapsed tree performs no widget construction until opened.

### Analytics tests

- Only `tag_distribution` is invalidated by a tag edit.
- A collapsed tag section does not render.
- Several rapid changes coalesce into one visible-section refresh.
- Similarities, Traits, Rankings, and prediction norms are untouched.

## Instrumentation and verification

Keep the existing `[batch-tagging-debug]` timestamps during implementation and add temporary phase timings around:

- database write;
- cache/row patch;
- tag catalog update;
- tag tree update;
- filtered roster update;
- tag-distribution refresh;
- total Apply-to-idle time.

Test with:

- one selected chart;
- 10, 100, and 900 selected charts;
- an existing tag and a new tag;
- Search tags collapsed and expanded;
- no active filter, required tag, excluded tag, and `untagged` filter;
- Database Analytics tags collapsed and expanded;
- default row decorations enabled and disabled;
- macOS and Windows.

The critical observation is whether time scales with the number of changed rows rather than the total database size.

## Acceptance criteria

The patch is ready when all of the following are true:

- With no active tag filter, Batch Editor tag add/remove performs no full roster rebuild and no `list_charts()` reread.
- With active tag filters, only changed rows are reevaluated, or a scoped roster repaint uses existing rows without general database hydration.
- The selected UIDs remain stable except where the filter legitimately removes them from visible selection.
- The current UID and top-visible UID remain stable whenever they survive.
- When the viewport anchor disappears, the nearest surviving row becomes the anchor rather than the roster jumping to the top.
- Adding a new tag does not synchronously rebuild a collapsed Search tag tree.
- Tag-only edits refresh no unrelated analytics or astrological calculations.
- Existing Batch Editor, Search, Collection, hidden-chart, and UID-selection tests pass.
- New behavioral tests cover performance-boundary calls and viewport preservation.

## Non-goals

- Do not refactor the entire Database View refresh architecture in this patch.
- Do not change tag syntax, normalization, category semantics, or filter logic.
- Do not replace UID identity with local row IDs.
- Do not alter chart calculation or cache-validity rules.
- Do not broadly move code out of `app.py` beyond the small reusable roster-state helper or narrowly targeted tag-refresh helper.
- Do not suppress necessary UI synchronization; make it incremental, deferred, or field-scoped.

## Recommended patch shape

Prefer two reviewable commits:

1. **Preserve Database roster state during scoped rebuilds**
   - snapshot/restore helper;
   - Batch Editor integration;
   - viewport and selection regression tests.

2. **Make Batch Editor tag refresh incremental**
   - `_chart_rows` tag patching;
   - targeted filtered-row reevaluation;
   - incremental/lazy tag-tree update;
   - deferred tag-distribution refresh;
   - performance-boundary regression tests.

This split makes the visible-state fix independently reviewable while keeping the performance work focused on tag-only dependencies.
