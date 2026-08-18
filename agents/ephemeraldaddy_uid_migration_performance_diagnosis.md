# EphemeralDaddy Chart_ID → UID Migration Performance Diagnosis

## Executive Summary

The UID migration itself is not the fundamental performance problem.

The likely regression is that several hot UI paths now repeatedly translate between stable `chart_uid` values and local SQLite integer row IDs by calling database helper functions. Before the migration, many of those paths used already-loaded integer IDs or direct Python dictionary lookups.

That turns operations that were formerly cheap in-memory lookups into repeated SQLite queries, sometimes once per chart during filtering, rendering, selection handling, or analytics refreshes.

The architectural goal of making `chart_uid` the authoritative identity is sound. The runtime lookup strategy is not.

The recommended design is:

- `chart_uid` remains the durable, authoritative application identity.
- Integer chart IDs remain ephemeral local SQLite row keys.
- The application keeps in-memory bidirectional UID ↔ local-row-ID indexes for already-hydrated charts.
- SQLite UID/ID translation is used only at true persistence/hydration boundaries or as a fallback.

---

## 1. Highest-Confidence Regression: Per-Chart UID Lookup in Database View Hot Paths

A major regression appears in Database View filtering and placeholder checks.

Before the migration, code could do a direct lookup such as:

```python
row = self._active_chart_rows_by_id.get(int(chart_id))
```

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

## 3. Selection State Now Reconstructs Integer IDs From UIDs

PR #2184 intentionally removed parallel cached integer selection state and retained only UID-owned selection state.

That is architecturally clean, but it causes unnecessary reconstruction work.

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

It is reasonable for UID state to be authoritative.

It is unnecessary for the application to deliberately forget the matching local row ID while the chart is already loaded.

### Confidence

**High.**

---

## 4. Database Analytics Cache Now Performs Extra ID ↔ UID Translation

The metrics migration changed internal snapshot storage from integer-ID keys to UID keys.

That change is reasonable.

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

The migration appears to have conflated two separate concepts:

1. **Authoritative identity**
2. **Runtime lookup representation**

`chart_uid` should absolutely be the authoritative identity for:

- cross-feature references
- persistent metadata
- relationships
- exports
- cache identity
- durable links
- user-visible references

But this does **not** imply that local SQLite row IDs must be discarded from memory.

A local integer row ID is still useful as an ephemeral runtime adapter.

The mistake is not using UIDs.

The mistake is repeatedly asking SQLite to translate values that were already known when the rows were hydrated.

---

# Recommended Architecture

Maintain UID authority while adding in-memory bidirectional indexes.

For example:

```python
# Authoritative identity
chart_uid: str

# Ephemeral runtime indexes
_chart_uid_by_local_row_id: dict[int, str]
_local_row_id_by_chart_uid: dict[str, int]
```

Build them when Database View rows are loaded:

```python
self._chart_uid_by_local_row_id = {}
self._local_row_id_by_chart_uid = {}

for row in self._chart_rows:
    local_id = int(row[0])
    uid = str(row[30] or "").strip().upper()

    if uid:
        self._chart_uid_by_local_row_id[local_id] = uid
        self._local_row_id_by_chart_uid[uid] = local_id
```

Then hot-path code should use these maps.

---

# Specific Changes Recommended

## `_chart_matches_filters()`

Avoid:

```python
chart_uid = get_chart_uid(chart_id)
```

Use the already-loaded row or in-memory map.

Example:

```python
chart_uid = self._chart_uid_by_local_row_id.get(int(chart_id))
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

---

## `_current_local_row_id()`

Preferred order:

1. `self._latest_chart.id`, if it belongs to `current_chart_uid`
2. in-memory UID → row-ID map
3. `get_chart_id_by_uid()` only as fallback

---

## Database Analytics

Do not repeatedly call:

```python
get_chart_uid_map(...)
```

inside cache iteration when the same UID mappings are already represented by hydrated Database View rows or cache metadata.

The cache should carry or reuse identity maps for its lifetime.

---

# Recommended Rule

The migration should follow this rule:

> SQLite converts UID ↔ local row ID at hydration and persistence boundaries.  
> RAM converts UID ↔ local row ID everywhere else.

This preserves the UID-first architecture while avoiding repeated database work during ordinary GUI operations.

---

# Priority Ranking

## 1. Per-row `get_chart_uid()` calls in Database View / filtering

**Confidence: Very high**

Most likely major regression.

---

## 2. Repeated `_current_local_row_id()` / UID → ID lookups

**Confidence: High**

Especially relevant to frequently called UI and autosave paths.

---

## 3. Selection UID → local-ID reconstruction

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

The migration's stated objective included reducing redundant SQLite lookups. The remaining hot-path UID/ID translations appear to work against that objective.

---

# Bottom Line

The UID migration should not be rolled back.

The correct fix is to separate:

- durable identity policy
- local runtime indexing

Keep UID as the single source of truth for chart identity.

Keep local integer IDs as cached, disposable runtime handles for SQLite-backed data that is already loaded.

The app should not query SQLite to rediscover an ID/UID pair it already knows.
