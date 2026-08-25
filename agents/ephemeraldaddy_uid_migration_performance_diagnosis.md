# EphemeralDaddy Chart_ID → UID Migration Performance Diagnosis

## Executive Summary

The UID migration itself is not the fundamental performance problem.

The likely regression is that several hot UI paths now repeatedly translate between stable `chart_uid` values and local SQLite integer row IDs by calling database helper functions. Before the migration, many of those paths used already-loaded integer IDs or direct Python dictionary lookups.

That turns operations that were formerly cheap in-memory lookups into repeated SQLite queries, sometimes once per chart during filtering, rendering, selection handling, or analytics refreshes.

The architectural goal of making `chart_uid` the authoritative durable identity is sound. The runtime lookup strategy is not.

There are three distinct concepts that must not be conflated:

1. **`chart_uid` — internal durable identity.** A static, unique reference used internally for persistence, relationships, caches, cross-feature references, and durable links. It is not ordinary user-facing information.
2. **Chart ID — user-facing sort rank.** A short, friendly ordinal indicating where a chart ranks under the Database View middle panel's current sorting method. It is presentation state, not durable identity.
3. **Local SQLite row ID — runtime/persistence handle.** An implementation-level integer used to address the local database efficiently. It may be retained in RAM as a disposable runtime handle, but it must not be treated as durable chart identity or confused with the user-facing Chart ID rank.

The recommended design is:

- `chart_uid` remains the durable, authoritative internal application identity.
- UIDs should never normally be shown to users. The sole intended user-visible UID surface is Chart Data Output when the user has explicitly enabled UID display under **Settings > Dev Tools**.
- User-facing Chart IDs remain useful and should continue to represent the chart's current sort rank in Database View.
- Local SQLite row IDs remain available as ephemeral runtime/persistence handles.
- The application keeps in-memory bidirectional UID ↔ local-row-ID indexes for already-hydrated charts.
- SQLite UID/row-ID translation is used only at true persistence/hydration boundaries or as a fallback.
- New code should name implementation-level integers `local_row_id` (or equivalent), not `chart_id`, when they are not the user-facing sort rank.

---

# Identity and Display Contract

This contract is part of the migration requirements, not an optional UI preference.

## `chart_uid`

`chart_uid` exists so a chart can be referenced uniquely and stably regardless of sorting, filtering, database row movement, import/export order, or UI state.

It should be used for:

- persistent metadata
- cross-feature references
- relationships between charts
- cache identity
- durable links
- imports/exports where a stable internal identity is required
- internal selection/state ownership where stability matters

It should **not** be used as normal display text. Long UIDs are implementation information and should remain hidden from users unless they explicitly opt into UID display in **Settings > Dev Tools > Chart Data Output**.

## User-facing Chart ID

Chart ID has a separate and legitimate purpose: it is the compact, human-readable rank of a chart under the Database View middle panel's current sorting method.

Therefore Chart ID:

- is user-facing
- is intentionally short and readable
- may change when the Database View sorting method changes
- is useful for quickly understanding a chart's current position/rank
- must not be used as durable identity
- must not be persisted as a cross-feature reference that is expected to survive resorting/reordering

A changing Chart ID is not an identity failure; changing with sort order is its intended semantics.

## Local SQLite row ID

A local SQLite integer row key is neither the durable chart identity nor the user-facing sort rank. It is an implementation handle.

It is useful because it is cheap to retain and efficient for local database access. The migration should not force the application to discard it from RAM and repeatedly ask SQLite to recover it from a UID.

Where older code calls a local SQLite row key `chart_id`, that name is ambiguous and should be treated as legacy terminology. New or touched code should distinguish `local_row_id` from the user-facing Chart ID rank.

---

## 1. Highest-Confidence Regression: Per-Chart UID Lookup in Database View Hot Paths

A major regression appears in Database View filtering and placeholder checks.

Before the migration, code could do a direct lookup such as:

```python
row = self._active_chart_rows_by_id.get(int(chart_id))
```

In this historical example, `chart_id` is functioning as a local row key; it should not be confused with the user-facing current-sort Chart ID described above.

During the UID migration, this became effectively:

```python
row = self._active_chart_rows_by_uid.get(
    str(get_chart_uid(chart_id) or "").strip().upper()
)
```

This occurs in code such as:

- `_is_placeholder_local_row_id()`
- `_is_similarities_placeholder_local_row_id()`
- `_chart_matches_filters()`

The important problem is that `get_chart_uid(chart_id)` is not merely string conversion.

It delegates to:

```python
def get_chart_uid(chart_id):
    return get_chart_uid_map([int(chart_id)]).get(int(chart_id))
```

`get_chart_uid_map()` opens and queries SQLite.

So an operation that previously looked like:

```text
10,000 charts
→ 10,000 Python dictionary lookups
```

can now resemble:

```text
10,000 charts
→ 10,000 get_chart_uid()
→ 10,000 single-element UID map calls
→ repeated SQLite connection/query work
→ 10,000 Python dictionary lookups
```

Even with an index on `charts(chart_uid)`, repeatedly crossing the Python ↔ SQLite boundary is much more expensive than reading an already-known value from memory.

### Confidence

**Very high.**

This is the strongest candidate for appwide slowdown after the migration.

---

## 2. `current_chart_id` Was Replaced With Repeated UID → ID Resolution

Commit `c6ed52983d...` removed retained `current_chart_id` controller state and introduced `_current_local_row_id()`.

The naming change toward `local_row_id` is important because the integer being recovered here is an internal database handle, not the user-facing current-sort Chart ID.

In some classes, it initially became:

```python
def _current_local_row_id(self) -> int | None:
    return get_chart_id_by_uid(self.current_chart_uid)
```

Many former uses of:

```python
self.current_chart_id
```

were then replaced with:

```python
self._current_local_row_id()
```

This affects paths such as:

- autosave eligibility
- metadata operations
- Similar Charts
- Chart View actions
- UI-state updates
- chart-existence checks
- alternate-chart handling

`get_chart_id_by_uid()` performs a SQLite query:

```python
SELECT id FROM charts WHERE chart_uid = ?
```

So code that used to read a Python attribute can now hit SQLite repeatedly.

### Partial Repair Already Exists

The current `MainWindow._current_local_row_id()` appears to have been improved so that it first reuses the already-loaded chart's local row ID:

```python
latest_chart = getattr(self, "_latest_chart", None)

if latest_uid == current_uid:
    local_row_id = int(getattr(latest_chart, "id", 0) or 0)
    if local_row_id > 0:
        return local_row_id

return get_chart_id_by_uid(current_uid)
```

The source comment explicitly says this avoids another UID-to-ID query on every autosave or refresh check.

That is the correct direction.

However, the equivalent Database View path still appears to use the simple database-query version.

### Confidence

**High.**

---

## 3. Selection State Now Reconstructs Local Row IDs From UIDs

PR #2184 intentionally removed parallel cached integer selection state and retained only UID-owned selection state.

That is architecturally clean for durable selection identity, but it causes unnecessary reconstruction work when the corresponding local row handles are already known.

The newer flow includes:

```python
def _selected_local_row_ids(...):
    return self._local_row_ids_for_uids(self._selected_chart_uid_order)
```

and:

```python
def _local_row_ids_for_uids(...):
    ...
    ids_by_uid = get_chart_ids_by_uid(ordered_uids)
```

`get_chart_ids_by_uid()` is sensibly batched, so this is much better than an N+1 query.

However, it still means Database View can query SQLite to rediscover local row IDs for charts that are already loaded into the UI.

The migration also changed `_populate_list()` so that it can call this conversion rather than reading retained integer-selection state directly.

### Key distinction

It is reasonable for UID state to be authoritative for selection identity.

It is unnecessary for the application to deliberately forget the matching local row ID while the chart is already loaded.

The user-facing Chart ID rank is a separate presentation value and should be derived from the current Database View ordering rather than substituted for either UID or local row ID.

### Confidence

**High.**

---

## 4. Database Analytics Cache Now Performs Extra Local-Row-ID ↔ UID Translation

The metrics migration changed internal snapshot storage from integer local-row-ID keys to UID keys.

That change is reasonable because cache identity should survive reordering and local database details.

However, the current refresh/iteration logic performs repeated translation calls such as:

```python
active_uid_by_id = get_chart_uid_map(active_ids)
```

then later:

```python
cached_uid_by_id = get_chart_uid_map(set(cache["chart_ids"]))
```

then:

```python
changed_ids_by_uid = get_chart_ids_by_uid(changed_uids)
```

and iteration helpers perform another:

```python
uid_by_id = get_chart_uid_map(ids)
```

This is not necessarily catastrophic because these are batched queries, but it means a subsystem explicitly designed around caching is repeatedly consulting SQLite simply to translate identities of records it has already hydrated.

That weakens the performance benefit of the cache.

### Confidence

**Moderate to high.**

---

## 5. Trait Rankings Already Hit the Same N+1 Problem

A later Aug. 14 migration commit contains a revealing comment:

```python
# Prefer the already-hydrated Database View rows. Falling back to one
# batched database lookup keeps numeric row IDs confined to this
# persistence adapter and avoids an N+1 UID resolution path.
```

Trait Rankings was then changed to reuse already-hydrated Database View identity information and only query SQLite for missing UIDs.

This is important because it confirms that the UID migration already generated this exact performance class in at least one subsystem.

The fix applied there should be generalized across Database View, filtering, analytics, and other hot paths.

---

## 6. Some Slowdown Is Probably Temporary Cache Invalidation

During the migration:

```python
DATABASE_METRICS_PERSISTENT_CACHE_VERSION = 2
```

was bumped to:

```python
DATABASE_METRICS_PERSISTENT_CACHE_VERSION = 3
```

That invalidates old persistent metrics caches and forces rebuilds.

Traits/Predictions also showed signs of cache churn after UID migration, including missing persisted metadata and stale norm caches.

This can explain slower first loads immediately after migration.

It does **not** adequately explain persistent appwide slowness after caches should have warmed.

### Confidence

**Moderate, but mainly transient.**

---

# Root Cause

The migration appears to have conflated three separate concepts:

1. **Durable internal identity** — `chart_uid`
2. **User-facing current-sort rank** — Chart ID
3. **Runtime/persistence lookup representation** — local SQLite row ID

`chart_uid` should absolutely be authoritative for:

- cross-feature internal references
- persistent metadata
- relationships
- cache identity
- durable links
- stable import/export identity

It should **not** become normal user-facing copy. Except for the explicit Dev Tools opt-in in Chart Data Output, users should not be asked to read or work with UIDs.

User-facing Chart IDs should remain available because they communicate something useful that UIDs do not: where the chart currently ranks under the selected Database View sorting method.

A local SQLite row ID is still useful as an ephemeral runtime adapter. It should be retained in memory when already known, but should not be confused with either the durable UID or the displayed Chart ID rank.

The mistake is not using UIDs.

The mistake is repeatedly asking SQLite to translate values that were already known when the rows were hydrated, while also allowing terminology to blur UID identity, displayed Chart ID rank, and local database row handles.

---

# Recommended Architecture

Maintain UID authority while preserving both display-rank semantics and efficient runtime handles.

For example:

```python
# Durable internal identity
chart_uid: str

# Ephemeral runtime indexes for hydrated rows
_chart_uid_by_local_row_id: dict[int, str]
_local_row_id_by_chart_uid: dict[str, int]

# User-facing presentation state derived from current Database View ordering
_display_chart_id_by_chart_uid: dict[str, int]
```

Build the runtime UID ↔ local-row-ID maps when Database View rows are loaded:

```python
self._chart_uid_by_local_row_id = {}
self._local_row_id_by_chart_uid = {}

for row in self._chart_rows:
    local_row_id = int(row[0])
    uid = str(row[30] or "").strip().upper()

    if uid:
        self._chart_uid_by_local_row_id[local_row_id] = uid
        self._local_row_id_by_chart_uid[uid] = local_row_id
```

Build or derive the displayed Chart ID rank from the Database View's current sorted order rather than from durable identity:

```python
self._display_chart_id_by_chart_uid = {
    uid: rank
    for rank, uid in enumerate(current_sorted_chart_uids, start=1)
}
```

The exact implementation may differ, but the semantic separation should remain explicit.

Then hot-path code should use the RAM maps.

---

# Specific Changes Recommended

## `_chart_matches_filters()`

Avoid:

```python
chart_uid = get_chart_uid(local_row_id)
```

Use the already-loaded row or in-memory map.

Example:

```python
chart_uid = self._chart_uid_by_local_row_id.get(int(local_row_id))
row = self._active_chart_rows_by_uid.get(chart_uid or "")
```

---

## `_is_placeholder_local_row_id()`

Avoid per-call database translation.

Use:

```python
chart_uid = self._chart_uid_by_local_row_id.get(int(local_row_id))
row = self._active_chart_rows_by_uid.get(chart_uid or "")
```

---

## `_is_similarities_placeholder_local_row_id()`

Same fix as above.

---

## `_selected_local_row_ids()`

Resolve from:

```python
self._local_row_id_by_chart_uid
```

instead of SQLite whenever possible.

Only use `get_chart_ids_by_uid()` for UIDs missing from the hydrated map.

Do not use the displayed Chart ID rank as a persistence lookup key.

---

## `_current_local_row_id()`

Preferred order:

1. `self._latest_chart.id`, if it belongs to `current_chart_uid`
2. in-memory UID → local-row-ID map
3. `get_chart_id_by_uid()` only as fallback

Again, this local row ID is not the displayed Chart ID rank.

---

## Database Analytics

Do not repeatedly call:

```python
get_chart_uid_map(...)
```

inside cache iteration when the same UID mappings are already represented by hydrated Database View rows or cache metadata.

The cache should carry or reuse identity maps for its lifetime.

Analytics output that displays a Chart ID should use the current Database View sort rank, not expose the underlying UID and not casually expose the local SQLite row key.

---

## Similar Charts / Similarities

Similar Charts and Similarities should use UID for durable internal references and relationship identity, while using hydrated in-memory UID ↔ local-row-ID maps for runtime access.

When presenting a chart to the user:

- show the chart's normal name/alias and, where a numeric identifier is useful, its current user-facing Chart ID rank
- do not display the UID
- do not use the current Chart ID rank as a durable relationship key
- do not query SQLite repeatedly merely to translate UID ↔ local row ID inside scoring, filtering, rendering, or refresh loops

This distinction is especially important during the current migration because older helpers named `*_chart_id` may refer to local database row keys rather than the intended user-facing current-sort Chart ID. Such helpers should be audited by semantics, not renamed mechanically.

---

# Recommended Rules

The migration should follow these rules:

> UID is durable internal identity.  
> Chart ID is user-facing current-sort rank.  
> Local row ID is an internal runtime/persistence handle.  
> SQLite converts UID ↔ local row ID at hydration and persistence boundaries.  
> RAM converts UID ↔ local row ID everywhere else.

And for display:

> Never show a chart UID in ordinary UI.  
> Only show UID in Chart Data Output when explicitly enabled under Settings > Dev Tools.  
> Use Chart ID when a compact user-facing numeric reference or current-sort rank is useful.

This preserves the UID-first internal architecture, the useful user-facing Chart ID concept, and the performance advantages of already-hydrated local database handles.

---

# Priority Ranking

## 1. Per-row `get_chart_uid()` calls in Database View / filtering

**Confidence: Very high**

Most likely major regression.

---

## 2. Repeated `_current_local_row_id()` / UID → local-row-ID lookups

**Confidence: High**

Especially relevant to frequently called UI and autosave paths.

---

## 3. Selection UID → local-row-ID reconstruction

**Confidence: High**

Batched, but still unnecessary repeated database work.

---

## 4. Database Analytics identity translation inside cached workflows

**Confidence: Moderate to high**

Likely contributes to heavier analytics refreshes.

---

## 5. Cache-version and signature invalidation

**Confidence: Moderate**

Explains some first-load slowness, but probably not ongoing appwide degradation.

---

# Relevant Migration History

Important commits/PRs examined during diagnosis include:

- PR #2184 — **Use chart UIDs as authoritative chart identity; resolve local row IDs only at persistence boundary**
- `c7ac037a710b...` — merge of PR #2184
- `c6ed52983d...` — **Preserve UID deletion refreshes and cached row IDs**
- `fa0e69cd8f...` — **Migrate metrics and row cache state to UIDs**
- `35c4ed363d...` — **Migrate duplicate and trait ranking state to UIDs**
- `70efa812a1...` — **Fix Database View UID row caching**
- `c33001b4c5...` — **Finish UID migration for trait prediction caches**

The migration's stated objective included reducing redundant SQLite lookups. The remaining hot-path UID/local-row-ID translations appear to work against that objective.

---

# Bottom Line

The UID migration should not be rolled back, and Chart IDs should not be eliminated from the user experience.

The correct fix is to separate:

- durable internal identity (`chart_uid`)
- user-facing current-sort rank (Chart ID)
- local runtime/persistence indexing (local SQLite row ID)

Keep UID as the single source of truth for durable chart identity.

Keep Chart ID as the short, readable indicator of current Database View sort rank.

Keep local integer row IDs as cached, disposable runtime handles for SQLite-backed data that is already loaded.

Do not expose UIDs unless the user explicitly enables them in Dev Tools, and do not query SQLite to rediscover a UID/local-row-ID pair the application already knows.
