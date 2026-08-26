# Traits Change Invalidation Policy

## Purpose

This document defines the authoritative invalidation and refresh rules for EphemeralDaddy's Traits subsystem and Trait-related Ranking UI.

The governing principle is simple:

> A change must invalidate only the smallest unit of data that actually became stale.

A generic "database changed" event is **not** sufficient justification to recompute Traits, rebuild Trait rankings, or refresh Trait UI. The system already distinguishes astrological calculation data from descriptive metadata; that distinction must be carried all the way through persistence, database change logging, cache invalidation, ranking maintenance, and UI refresh.

The database change log should be treated as the primary invalidation backbone, not as a specialized optimization used only by selected caches.

---

## 1. Authoritative change categories

Chart data must be classified into three distinct categories, plus Trait-definition events as a separate domain.

### 1.1 `astro_data`

`astro_data` contains chart inputs and derived values that are relevant to astrology-derived systems.

Examples include birth date/time/location, calculated positions, houses, aspects, dominant-sign weights, Human Design calculations, BaZi calculations, and other chart-derived astrological data.

Rules:

- Changes to `astro_data` may invalidate astrological calculations.
- If `astro_data` changes for Chart X, only Chart X becomes numerically stale.
- Trait scores derived from Chart X may therefore need recalculation for Chart X.
- No other chart's Trait score becomes stale merely because Chart X changed.
- Existing Trait rankings should be incrementally updated by removing/repositioning Chart X, not rebuilt from scratch.

### 1.2 `nonastral_data`

`nonastral_data` contains descriptive, subjective, organizational, or user-entered metadata that does not participate in astrology-derived calculations.

Examples include:

- tags
- notes/comments
- biography
- sentiments
- relationship types
- reminders/associations
- aliases
- descriptive metadata
- other ordinary subjective chart metadata

Rules:

- `nonastral_data` must never invalidate Trait scores.
- `nonastral_data` must never cause Trait rankings to be recomputed or reordered.
- `nonastral_data` must never refresh Trait panels merely because a chart/database row was reloaded.
- Consumers that actually depend on the changed field may refresh themselves narrowly.
- A tag edit is a tag-system event, not a Traits event.

### 1.3 `chart_info_status`

`chart_info_status` contains chart-state fields whose purpose is to determine whether/how a chart participates in UI result populations.

Initial canonical members should include at least:

```python
CHART_INFO_STATUS = frozenset({
    "is_placeholder",
    "is_hypothetical",
    "is_hidden",
})
```

Additional fields should only be added if their meaning is fundamentally "include/exclude or specially classify this chart in result populations," rather than astrological calculation or descriptive metadata.

Rules:

- `chart_info_status` affects membership/presentation, not Trait mathematics.
- Changing status must not recalculate the chart's Trait scores.
- Changing status may add/remove/reinclude the chart in Trait result sets.
- If a chart becomes excluded, remove its existing cached ranking entries.
- If a chart becomes included again, reuse valid cached Trait scores and insert the chart into the appropriate ranking positions.
- If its `astro_data` changed independently while excluded, only then should the affected Trait scores be recomputed before reinsertion.

### 1.4 `trait_data`

Trait definitions are not chart metadata and should be treated as their own change domain.

Trait events include:

- definition/model change
- rename
- archive
- unarchive
- delete
- add

These events have different consequences and must not be collapsed into a single "Traits dirty" flag.

---

## 2. Core invalidation vocabulary

Do not use a single catch-all concept such as `_rankings_data_dirty = True` to represent all ranking changes.

The system must distinguish at least the following operations.

### 2.1 Score invalidation

A numerical Trait score is stale and must be recalculated.

Examples:

- Chart X's `astro_data` changed.
- Trait T's scoring definition/model changed.

### 2.2 Membership invalidation

A chart should enter or leave a result population, but its underlying Trait score is not necessarily stale.

Examples:

- Chart X becomes hidden.
- Chart X becomes unhidden.
- Chart X changes placeholder/hypothetical status.
- Chart X is added or deleted.

### 2.3 Ordering mutation

A known ranking entry changed value and must move within an already-valid ordered ranking.

Example:

- Chart X's recalculated score for Trait T changes from 0.42 to 0.81.
- Remove X's old ranking entry and insert X at the correct new position.
- Do **not** recalculate A, B, C, D, or any other chart merely because their displayed ordinal positions shift around X.

### 2.4 Definition invalidation

The scoring model for a specific Trait changed.

Example:

- Trait T's definition or astrological model is edited.
- Trait T becomes stale for all eligible charts.
- Other Traits remain valid.

### 2.5 Presentation invalidation

Labels or visible availability changed without changing the underlying numerical model.

Examples:

- Trait renamed.
- Trait archived/unarchived.

These operations should update presentation and identifiers as required without unnecessary numerical rescoring.

---

## 3. Authoritative Traits change matrix

| Change | Recalculate Trait scores? | Ranking operation | Refresh Trait UI? |
| --- | --- | --- | --- |
| Tag rename/add/delete/category move | **No** | **None** | **No** |
| Notes/biography/sentiment/etc. | **No** | **None** | **No** |
| Astro data changes on Chart X | **Chart X only** | **Reposition X only in affected rankings** | **Yes** |
| New chart added | **New chart only** | **Insert new chart into applicable rankings** | **Yes** |
| Chart deleted | **No scoring** | **Remove deleted UID from rankings** | **Yes** |
| Chart X becomes hidden/excluded | **No** | **Remove X from applicable ranking populations** | **Yes** |
| Chart X becomes visible/included | **No, if cached score remains valid** | **Insert X using cached scores** | **Yes** |
| Placeholder/hypothetical status changes | **No** | **Update X's ranking membership only** | **Yes** |
| Trait T definition/model changes | **Trait T only, for eligible charts** | **Update Trait T ranking only** | **Yes** |
| Trait T added | **Trait T only, for eligible charts** | **Build Trait T ranking only** | **Yes** |
| Trait T renamed | **No numerical rescore** | **Preserve ordering; rename/migrate identity as required** | **Yes** |
| Trait T archived/unarchived | **No numerical rescore** | **Change visible availability/membership only** | **Yes** |
| Trait T deleted | **No rescore of other Traits** | **Remove Trait T ranking/cache entries** | **Yes** |

---

## 4. Critical distinction: "rerank" does not mean "recalculate everybody"

When Chart X's `astro_data` changes, Chart X may move within every Trait ranking whose score depends on that changed astrology.

That does **not** make the other charts stale.

Example before recalculation:

```text
1  A  8.2
2  B  7.9
3  X  7.4
4  C  7.1
5  D  6.8
```

After recalculating X only:

```text
1  X  8.4
2  A  8.2
3  B  7.9
4  C  7.1
5  D  6.8
```

The correct operation is conceptually:

```python
for trait_id in affected_traits:
    new_score = calculate_trait_score(chart_x, trait_id)

    ranking = trait_rankings[trait_id]
    ranking.remove(chart_x.uid)
    ranking.insert_sorted(chart_x.uid, new_score)
```

A/B/C/D may receive different displayed ordinal numbers because X crossed them. Their underlying scores were not recalculated, their cache entries were not invalidated, and their astrological data was not re-read merely to reconstruct the list.

This distinction must remain explicit in code and naming.

Prefer terms such as:

- `recalculate_trait_score(...)`
- `reposition_chart_in_trait_ranking(...)`
- `insert_chart_into_trait_ranking(...)`
- `remove_chart_from_trait_ranking(...)`

Avoid using a broad verb such as `rerank` when it conceals whether the implementation is rescoring every member or merely maintaining an ordered result structure.

---

## 5. Required event model

Chart-change events should preserve category and field granularity instead of collapsing into "database refreshed."

Conceptually:

```python
ChartChange(
    chart_uid="...",
    category="astro_data" | "nonastral_data" | "chart_info_status",
    changed_fields={...},
)
```

Trait events should be separate:

```python
TraitChange(
    trait_id="...",
    change_type=(
        "added"
        | "definition_changed"
        | "renamed"
        | "archived"
        | "unarchived"
        | "deleted"
    ),
)
```

The concrete schema may differ, but downstream consumers must have enough information to identify:

1. which chart(s) changed;
2. which field category changed;
3. which fields changed;
4. whether chart membership changed;
5. which Trait changed, if any;
6. what kind of Trait change occurred.

A boolean such as `database_changed=True` is insufficient.

---

## 6. Required dispatch behavior

Conceptually, chart events should be dispatched as follows:

```python
match change.category:
    case "astro_data":
        recalculate_astrology_for_chart(change.chart_uid)
        recalculate_trait_scores_for_chart(change.chart_uid)
        reposition_chart_in_affected_trait_rankings(change.chart_uid)
        refresh_visible_trait_ui_for_affected_results()

    case "chart_info_status":
        update_chart_population_membership(change.chart_uid)
        update_trait_ranking_membership(change.chart_uid)
        refresh_visible_trait_ui_for_affected_results()

    case "nonastral_data":
        refresh_only_actual_consumers_of(change.changed_fields)
        # No Trait invalidation.
        # No Trait ranking mutation.
        # No Trait UI refresh.
```

Trait events should be dispatched independently:

```python
match trait_change.change_type:
    case "added":
        calculate_only_new_trait_for_eligible_charts(trait_change.trait_id)
        build_only_that_trait_ranking(trait_change.trait_id)

    case "definition_changed":
        invalidate_only_trait(trait_change.trait_id)
        recalculate_only_trait_for_eligible_charts(trait_change.trait_id)
        refresh_only_that_trait_ranking(trait_change.trait_id)

    case "renamed":
        migrate_or_update_trait_identity(trait_change.trait_id)
        refresh_trait_labels_only(trait_change.trait_id)

    case "archived" | "unarchived":
        update_trait_visibility(trait_change.trait_id)

    case "deleted":
        remove_trait_cache_entries(trait_change.trait_id)
        remove_trait_ranking(trait_change.trait_id)
```

---

## 7. Database change log requirements

The existing database change journal should be deployed broadly enough that consumers can stop guessing what changed based on which UI method happened to call `_refresh_charts()`.

The journal should support incremental work at the smallest useful scope.

### For `astro_data`

Record enough information to identify affected chart UID(s). Trait consumers can then invalidate/recalculate only those charts.

### For `nonastral_data`

Record the change for consumers that care about the relevant metadata, but Traits should explicitly ignore the event.

Example:

```text
chart_uid = X
category = nonastral_data
changed_fields = {tags}
```

Expected Trait consequence:

```text
NONE
```

### For `chart_info_status`

Record enough information to determine whether the chart's eligibility changed.

Example:

```text
chart_uid = X
category = chart_info_status
changed_fields = {is_hidden}
old_value = false
new_value = true
```

Expected Trait consequence:

```text
remove X from applicable result populations
preserve X's numerical Trait cache
```

### For added/deleted charts

Treat chart membership itself as an explicit event.

- Added chart: calculate only the new chart's required Trait scores and insert it.
- Deleted chart: remove its ranking/cache membership; do not rescore survivors.

---

## 8. Ranking data structures should support incremental maintenance

Trait rankings should be maintainable as ordered collections rather than ephemeral products that must be rebuilt after every mutation.

Required operations should include the conceptual equivalents of:

```python
insert(chart_uid, score)
remove(chart_uid)
update_score(chart_uid, score)   # remove + sorted insert is acceptable
contains(chart_uid)
score_for(chart_uid)
```

The implementation may use sorted arrays, indexed lists, trees, bisect-based insertion, cached database ordering, or another suitable structure. The architectural requirement is that a single changed chart can be updated without recomputing unaffected chart scores.

If a displayed top-N list is used, implementation must still correctly handle a changed chart crossing into or out of the visible boundary.

Example:

- UI shows top 20.
- X was rank 36 and changes to rank 8.
- Insert X at rank 8 and displace the previous rank-20 entry from the visible set.
- Do not rescore ranks 1-35 or 37+.

---

## 9. Trait cache validity rules

Trait cache validity should be determined per chart and per Trait wherever practical.

A useful conceptual key is:

```text
(chart_uid, trait_id, astro_revision, trait_definition_revision)
```

The exact persisted structure can vary, but it should make these facts expressible:

- Chart X's astrology changed; X's cached Trait results are stale.
- Chart Y did not change; Y's cache remains valid.
- Trait T changed definition; T's cached scores are stale across eligible charts.
- Trait U did not change; U's cache remains valid.
- A tag changed; no Trait cache key became stale.
- X became hidden; X's cached scores remain numerically valid even if excluded from current results.

Do not delete or regenerate valid cache data merely because it is temporarily not displayed.

---

## 10. UI refresh rules

A data reload and an analytical invalidation are separate concepts.

Database View may need to refresh rows after a metadata operation. That does not grant the row-refresh function authority to mark analytical systems dirty.

In particular:

```python
_refresh_charts(...)
```

must not implicitly mean:

```python
_rankings_data_dirty = True
_refresh_visible_rankings_sections()
```

unless the caller/event explicitly establishes that ranking-relevant data changed.

The UI should refresh Trait surfaces only when one of the following occurs:

- an affected chart's Trait score was recalculated;
- ranking membership changed;
- an affected chart was repositioned;
- a Trait definition/presentation event requires it;
- the user explicitly requests a refresh/recalculation.

A tag edit is none of these.

---

## 11. Current known failure mode: Property Manager Tags

The current failure illustrates the architectural issue:

```text
Tags Manager edit
    -> Property Manager requests broad chart refresh
    -> _refresh_charts() treats general row refresh as Rankings invalidation
    -> entire Rankings panel is marked dirty
    -> visible Trait Ranking section refreshes/reloads
```

This is invalid behavior.

The correct chain is:

```text
Tags Manager edit
    -> persist tags as nonastral_data
    -> record nonastral_data/tags change
    -> refresh tag-dependent UI and database-row presentation as needed
    -> Traits subsystem ignores event
```

No Trait cache invalidation, scoring, ranking mutation, or Trait panel refresh should occur.

---

## 12. Explicit anti-patterns

Do not introduce or preserve any of the following patterns.

### 12.1 Global Rankings dirty flag as the primary invalidation model

Bad:

```python
self._rankings_data_dirty = True
```

when the only known fact is that some database data changed.

Why it is wrong:

- loses category information;
- loses affected UID information;
- loses affected Trait information;
- turns metadata edits into analytical work;
- makes incremental cache architecture ineffective;
- encourages full-section rebuilding.

### 12.2 Recomputing all charts because one chart changed

Bad:

```python
for chart in all_charts:
    recompute_traits(chart)
```

when only Chart X's `astro_data` changed.

Correct:

```python
recompute_traits(chart_x)
reposition_chart_x()
```

### 12.3 Recomputing all Traits because one Trait changed

Bad:

```python
recompute_every_trait_for_every_chart()
```

when Trait T's definition changed.

Correct:

```python
recompute_trait_t_for_eligible_charts()
```

### 12.4 Discarding valid scores on status changes

Bad:

```python
if chart.is_hidden:
    delete_trait_cache(chart.uid)
```

Correct:

```python
if chart.is_hidden:
    remove_chart_from_visible_rankings(chart.uid)
    preserve_valid_trait_cache(chart.uid)
```

### 12.5 Treating UI refresh as cache invalidation

Repainting or reloading a widget does not imply that underlying analytical data became stale.

---

## 13. Migration checklist

### Data classification

- [ ] Introduce canonical `CHART_INFO_STATUS` classification.
- [ ] Move `is_placeholder`, `is_hypothetical`, and `is_hidden` into that category wherever currently classified otherwise.
- [ ] Audit fields whose semantic purpose is result-population eligibility and classify deliberately.
- [ ] Preserve `tags` and ordinary subjective/descriptive metadata as `NONASTRAL_DATA`.

### Change journal

- [ ] Ensure change-log entries preserve chart UID.
- [ ] Ensure change-log entries preserve category: `astro_data`, `nonastral_data`, or `chart_info_status`.
- [ ] Preserve specific changed fields where useful.
- [ ] Ensure chart add/delete are represented as explicit membership events.
- [ ] Ensure Traits can consume only relevant journal events and ignore the rest.

### Trait invalidation

- [ ] Replace broad Trait invalidation after database refresh with UID-scoped invalidation.
- [ ] Recalculate only changed chart(s) for `astro_data` events.
- [ ] Recalculate only changed Trait(s) for definition/model events.
- [ ] Do not invalidate Trait scores for `chart_info_status` changes.
- [ ] Do not invalidate Trait scores for `nonastral_data` changes.

### Ranking maintenance

- [ ] Add/standardize incremental insert/remove/reposition operations.
- [ ] Astro edit on X: reposition X only.
- [ ] Add chart X: calculate X only, then insert X.
- [ ] Delete X: remove X only.
- [ ] Hide/exclude X: remove X only, preserve scores.
- [ ] Unhide/reinclude X: insert X using valid cached scores.
- [ ] Trait T definition edit: rebuild/update T ranking only.
- [ ] Trait T rename/archive/delete: perform only the semantically required operation.

### GUI refresh plumbing

- [ ] Stop `_refresh_charts()` from unconditionally invalidating Rankings.
- [ ] Remove implicit connection between general database row reloads and Trait refresh.
- [ ] Make Property Manager propagate actual change category/fields instead of a generic "refresh required" signal.
- [ ] Ensure Tags Manager only refreshes tag-dependent consumers.
- [ ] Ensure Trait Ranking refresh is driven by Trait-relevant invalidation events.

---

## 14. Validation checklist

### Tag/nonastral edits

- [ ] Rename a tag while Trait Rankings are expanded: no Trait scoring call occurs.
- [ ] Add/remove a tag from one or many charts: no Trait scoring call occurs.
- [ ] Move a tag between categories: no Trait ranking mutation occurs.
- [ ] Edit notes/biography/sentiment: no Trait cache invalidation occurs.
- [ ] Verify relevant database rows/tag UI still refresh correctly.

### Single-chart astro edits

- [ ] Edit Chart X birth data.
- [ ] Confirm only X's required astrological calculations are recomputed.
- [ ] Confirm only X's Trait scores are recalculated.
- [ ] Confirm X is repositioned correctly in affected Trait rankings.
- [ ] Confirm all other chart Trait score cache records remain untouched.
- [ ] Confirm ordinal labels for charts crossed by X update without rescoring those charts.

### Status changes

- [ ] Hide Chart X: X disappears from applicable Trait results without numerical rescoring.
- [ ] Unhide Chart X: X returns using valid cached scores.
- [ ] Toggle placeholder/hypothetical status: only result membership changes.
- [ ] Change X's `astro_data` while excluded, then reinclude it: X is recalculated only if its cached score revision is stale.

### Chart add/delete

- [ ] Add Chart X: calculate only X and insert it into rankings.
- [ ] Delete Chart X: remove X without rescoring survivors.

### Trait edits

- [ ] Change Trait T definition: recalculate T only across eligible charts.
- [ ] Add Trait T: calculate T only.
- [ ] Rename Trait T: no numerical rescore.
- [ ] Archive/unarchive Trait T: no numerical rescore.
- [ ] Delete Trait T: remove T data without touching other Traits.

### Performance/instrumentation

- [ ] Add temporary counters/logging around Trait scoring during migration tests.
- [ ] Verify a tag edit results in **zero** Trait score computations.
- [ ] Verify one-chart astro edit results in exactly the expected number of computations for that chart, not database-size-dependent work.
- [ ] Verify one-Trait definition edit scales with eligible chart count for that Trait only, not `chart_count × all_traits`.

---

## 15. Governing invariant

When deciding whether to invalidate Traits, ask two questions in order:

1. **Did an input to the Trait mathematics change?**
2. **If yes, exactly which chart(s) and/or Trait(s) became stale?**

If the answer to the first question is no, Traits should do nothing.

If the answer is yes, invalidate only the identified stale units.

The desired architecture is therefore:

```text
ASTRO_DATA CHANGE
    -> recalculate affected chart(s) only
    -> reposition affected chart(s) only

TRAIT_DATA CHANGE
    -> operate on affected Trait(s) only

CHART_INFO_STATUS CHANGE
    -> update result-set membership only
    -> preserve valid numerical scores

NONASTRAL_DATA CHANGE
    -> zero Trait consequences
```

Any code path that turns a tag edit, note edit, or generic database reload into a Traits-wide dirty state violates this policy and should be treated as an invalidation bug.