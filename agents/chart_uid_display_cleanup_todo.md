# Chart UID Display Cleanup — TODO

## Governing identity rules

- `chart_uid` is the chart's durable internal identity.
  - Static, unique, and suitable for persistence, relationships, caches, imports/exports, and internal references.
  - It should not ordinarily be visible to users.
  - The sole intended user-visible UID surface is **Chart Data Output**, and only when explicitly enabled under **Settings > Dev Tools**.
- **Chart ID** is the short, user-facing rank/ordinal defined by the current sorting method in Database View's middle panel.
  - It is presentation state, not durable identity.
  - It is expected to change when the sort order changes.
  - Preserve it anywhere a compact user-facing chart reference is useful.
- **Local SQLite row ID** is a separate internal implementation/runtime handle.
  - Do not treat it as the user-facing Chart ID.
  - In new/touched code, prefer names such as `local_row_id` instead of ambiguous legacy `chart_id` naming when the value is actually a SQLite row key.

## Immediate patch scope

### 1. Reminds Me Of lookup UI

- [ ] Remove `or UID` wording from the chart lookup placeholder.
- [ ] Remove instructions that tell users they may enter a Chart UID.
- [ ] Remove Chart UID wording from the `Chart not found` warning/error copy.
- [ ] Preserve UID-backed lookup/resolution internally if the existing implementation relies on it.
- [ ] Do not expose the resolved UID in normal UI output.

### 2. Alternate Chart lookup UI

- [ ] Remove `or UID` wording from the chart lookup placeholder.
- [ ] Remove instructions that tell users they may enter a Chart UID.
- [ ] Remove Chart UID wording from the `Chart not found` warning/error copy.
- [ ] Preserve UID-backed lookup/resolution internally.
- [ ] Do not expose UID values in the user-facing surface.

### 3. Similar Charts plain-text export

- [ ] Stop emitting raw `chart_uid` values in the text export.
- [ ] Preserve normal user-facing chart names.
- [ ] Where a compact numeric reference is useful, use the current user-facing Chart ID rank rather than UID or SQLite row ID.
- [ ] Do not alter UID-backed internal matching, persistence, or action payloads merely to change export presentation.

### 4. Similar Charts Markdown export

- [ ] Remove the `Chart UID` column entirely.
- [ ] Keep useful user-facing columns such as chart name, similarity score, and current Chart ID rank where appropriate.
- [ ] Ensure no UID leaks into row labels, fallback strings, headings, or footnotes.

## Explicitly out of scope / do not regress

- [ ] Do **not** remove or replace internal `chart_uid` fields used for durable identity.
- [ ] Do **not** convert UID-backed persistence back to Chart IDs.
- [ ] Do **not** use user-facing Chart ID rank as a database key.
- [ ] Do **not** expose SQLite/local row IDs as Chart IDs.
- [ ] Do **not** remove the optional Dev Tools UID display from Chart Data Output.
- [ ] Do **not** introduce per-row UID ↔ local-row-ID database lookups in hot loops.

## Runtime/performance rule

Use the existing identity architecture consistently:

> SQLite converts UID ↔ local row ID at hydration and persistence boundaries.  
> RAM converts UID ↔ local row ID everywhere else.

Prefer in-memory mappings for hydrated charts, conceptually:

```python
_chart_uid_by_local_row_id: dict[int, str]
_local_row_id_by_chart_uid: dict[str, int]
_display_chart_id_by_chart_uid: dict[str, int]
```

The display-Chart-ID map should reflect the current Database View ordering and must be treated as presentation state only.

## Validation checklist

- [ ] Search ordinary user-facing UI strings for `UID`, `Chart UID`, and `chart_uid`; verify only the explicitly enabled Dev Tools Chart Data Output surface remains intentionally visible.
- [ ] Verify Reminds Me Of still resolves and saves relationships correctly after the copy cleanup.
- [ ] Verify Alternate Chart lookup still resolves correctly.
- [ ] Verify Similar Charts text export contains no raw UID.
- [ ] Verify Similar Charts Markdown export contains no UID column or values.
- [ ] Re-sort Database View and confirm displayed Chart IDs change with rank as intended.
- [ ] Confirm durable relationships/references remain stable after a re-sort because they are still UID-backed internally.
- [ ] Confirm no new per-chart database translation calls were introduced into Similar Charts/filter loops.

## Implementation note

`app.py` is very large. If the normal GitHub contents API cannot safely replace it in one operation, use a repository-level blob/tree/commit workflow or another safe patch mechanism. Do not overwrite or truncate the file merely to make a small UI-string edit.
