# EphemeralDaddy Chart_ID → UID Migration Performance Diagnosis

## Executive Summary

Below is an analysis of performance failure post-chart_ID-> UID migration. I reverted most of the changes, and that fixed the slowdown. But we learned a lesson, so I'm maintaining this document for future clarification, when we reattempt the migration:

----Analysis below is correct, except when it recommended against reverting. Reverting was the trick. It fixed it. We'll need to redo a fair bit of work, but so be it.

The UID migration itself is not the fundamental performance problem.

The likely regression is that several hot UI paths now repeatedly translate between stable `chart_uid` values and the SQLite `charts.id` primary key by calling database helper functions. Before the migration, many of those paths used already-loaded integers or direct Python dictionary lookups.

That turns operations that were formerly cheap in-memory lookups into repeated SQLite queries, sometimes once per chart during filtering, rendering, selection handling, or analytics refreshes.

The architectural goal of making `chart_uid` the authoritative durable identity is sound. The runtime lookup strategy is not.

## Critical clarification: EphemeralDaddy has only two chart-reference concepts

There are **two**, and only two, application-level chart references:

1. **`chart_uid` — internal durable identity.** A static, unique reference used internally for persistence, relationships, caches, cross-feature references, and durable links.
2. **Chart ID — user-facing current-sort rank.** A short, friendly ordinal indicating where a chart ranks under the Database View middle panel's current sorting method.

The SQLite column `charts.id` is **not a third chart identity**. It is simply the table's integer primary key and may remain useful as private database plumbing. It should not be promoted into application semantics, presented to users as Chart ID, or treated as another durable reference system.

Likewise, names such as `local_row_id`, `_current_local_row_id()`, `_local_row_ids_for_uids()`, and related terminology are migration-era implementation vocabulary for `charts.id`. They should be treated as transitional/legacy naming, not as evidence that EphemeralDaddy requires a third form of chart identity.

The recommended design is therefore:

- `chart_uid` remains the durable, authoritative internal application identity.
- UIDs should never normally be shown to users. The sole intended user-visible UID surface is Chart Data Output when the user has explicitly enabled UID display under **Settings > Dev Tools**.
- User-facing Chart IDs remain useful and should continue to represent the chart's current sort rank in Database View.
- `charts.id` may continue to exist as a private SQLite primary key for efficient database operations, joins, and already-hydrated row access.
- Any UID ↔ `charts.id` mapping needed for performance should remain an internal persistence/runtime optimization, not become a third application-level identity model.
- SQLite UID/primary-key translation should occur only at true persistence/hydration boundaries or as a fallback; already-known mappings should be reused in memory.
- New code should reserve `chart_id` for the actual user-facing Chart ID rank. Where direct access to `charts.id` is unavoidable in DB-layer code, name it in a way that makes its database-only role obvious, such as `sqlite_row_id` or `db_row_pk`. Do not proliferate `local_row_id` as a new application concept.

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

## SQLite `charts.id`

The database schema currently contains:

```sql
id        INTEGER PRIMARY KEY AUTOINCREMENT
chart_uid TEXT
```

`charts.id` is database plumbing. It is neither the durable chart identity nor the user-facing Chart ID rank.

It can remain because integer primary keys are cheap and useful for SQLite operations. Removing it is not required to achieve the intended two-reference model. The important rule is containment: code outside persistence/runtime plumbing should not begin treating `charts.id` as another form of chart identity.

Where migration-era code calls this value `chart_id`, that name is ambiguous legacy terminology. Where migration-era code calls it `local_row_id`, that name should likewise be understood as a transitional alias for `charts.id`, not as a new architectural identifier that needs to spread through the application.

The application should not build product behavior around a third `local_row_id` concept. If an already-hydrated row carries its SQLite primary key, that is simply cached database state.

---

## 1. Highest-Confidence Regression: Per-Chart UID Lookup in Database View Hot Paths

A major regression appears in Database View filtering and placeholder checks.

Before the migration, code could do a direct lookup such as:

```python
row = self._active_chart_rows_by_id.get(int(chart_id))
```

In this historical example, the variable named `chart_id` was actually functioning as the SQLite `charts.id` primary key. It should not be confused with the intended user-facing current-sort Chart ID.

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

## 2. `current_chart_id` Was Replaced With Repeated UID → SQLite Primary-Key Resolution

Commit `c6ed52983d...` removed retained `current_chart_id` controller state and introduced `_current_local_row_id()`.

That helper name should be read as migration-era terminology for recovering the SQLite `charts.id` primary key. It is **not** a third chart-reference concept that the application is intended to preserve.

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

The current `MainWindow._current_local_row_id()` appears to have been improved so that it first reuses the already-loaded chart's SQLite primary key:

```python
latest_chart = getattr(self, "_latest_chart", None)

if latest_uid == current_uid:
    sqlite_row_id = int(getattr(latest_chart, "id", 0) or 0)
    if sqlite_row_id > 0:
        return sqlite_row_id

return get_chart_id_by_uid(current_uid)
```

The source comment explicitly says this avoids another UID-to-ID query on every autosave or refresh check.

That is the correct performance direction. The architectural cleanup is to keep this behavior confined to DB/runtime plumbing rather than allow `local_row_id` to become a third identity model.

However, the equivalent Database View path still appears to use the simple database-query version.

### Confidence

**High.**

---

## 3. Selection State Now Reconstructs SQLite Primary Keys From UIDs

PR #2184 intentionally removed parallel cached integer selection state and retained only UID-owned selection state.

That is architecturally correct for durable selection identity, but it causes unnecessary reconstruction work when the corresponding hydrated database row already carries `charts.id`.

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

However, it still means Database View can query SQLite to rediscover `charts.id` values for charts that are already loaded into the UI.

The migration also changed `_populate_list()` so that it can call this conversion rather than reading retained integer state directly.

### Key distinction

It is reasonable for UID state to be authoritative for selection identity.

It is unnecessary for the application to deliberately forget an already-known SQLite row primary key while the chart is loaded.

Retaining that integer alongside a hydrated row does **not** create a third chart identity. It is just cached database state.

The user-facing Chart ID rank is separate presentation state and should be derived from the current Database View ordering.

### Confidence

**High.**

---

## 4. Database Analytics Cache Now Performs Extra SQLite-ID ↔ UID Translation

The metrics migration changed internal snapshot storage from integer `charts.id` keys to UID keys.

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

This is not necessarily catastrophic because these are batched queries, but it means a subsystem explicitly designed around caching is repeatedly consulting SQLite simply to translate database primary keys for records it has already hydrated.

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

The performance lesson should be generalized across Database View, filtering, analytics, and other hot paths: if the row is already hydrated, reuse what the row already knows.

This does **not** imply that a `local_row_id` application concept needs to be preserved or expanded.

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

The migration conflated different layers of the application:

1. **Durable internal chart identity** — `chart_uid`
2. **User-facing current-sort rank** — Chart ID
3. **Private database implementation state** — SQLite `charts.id`

Only the first two are application-level chart-reference concepts.

`chart_uid` should absolutely be authoritative for:

- cross-feature internal references
- persistent metadata
- relationships
- cache identity
- durable links
- stable import/export identity

It should **not** become normal user-facing copy. Except for the explicit Dev Tools opt-in in Chart Data Output, users should not be asked to read or work with UIDs.

User-facing Chart IDs should remain available because they communicate something useful that UIDs do not: where the chart currently ranks under the selected Database View sorting method.

SQLite `charts.id` may continue to exist and may be retained in hydrated row objects or private lookup structures when that avoids redundant database work. But this is an implementation optimization, not a third identity system.

The mistake is not using UIDs.

The mistake is repeatedly asking SQLite to translate values that were already known when rows were hydrated, while allowing ambiguous names such as `chart_id` and `local_row_id` to blur the boundary between product semantics and database plumbing.

---

# Recommended Architecture

## Application-level model: exactly two references

```python
# Durable internal identity
chart_uid: str

# User-facing presentation state derived from current Database View ordering
chart_id: int
```

Conceptually:

```text
chart_uid
    static
    unique
    internal
    durable

chart_id
    short
    user-facing
    current-sort rank
    intentionally changeable
```

There is no third `local_row_id` application identity.

## Persistence/runtime implementation detail

SQLite may continue to use:

```sql
charts.id INTEGER PRIMARY KEY AUTOINCREMENT
```

and already-hydrated rows may retain that integer so the application does not repeatedly query SQLite for information it already has.

If a persistence-layer map materially improves performance, it can exist privately, for example:

```python
# Persistence/runtime optimization only; not chart identity.
_uid_by_sqlite_row_id: dict[int, str]
_sqlite_row_id_by_uid: dict[str, int]
```

Such maps should be built at hydration boundaries and kept within the layer that needs them. Their existence does not imply that callers should start passing a third identifier throughout the GUI.

Build or derive the displayed Chart ID rank from the Database View's current sorted order:

```python
_display_chart_id_by_chart_uid = {
    uid: rank
    for rank, uid in enumerate(current_sorted_chart_uids, start=1)
}
```

The exact implementation may differ, but the semantic separation should remain explicit.

---

# Specific Changes Recommended

## `_chart_matches_filters()` and placeholder checks

Avoid per-call database translation such as:

```python
chart_uid = get_chart_uid(sqlite_row_id)
```

If the function is operating on an already-hydrated row, get the UID from that row or from a private in-memory persistence map.

The goal is not to introduce `local_row_id` more deeply. The goal is to stop querying SQLite for information already present in memory.

---

## `_selected_local_row_ids()` / `_local_row_ids_for_uids()`

These names should be considered migration-era transitional vocabulary.

Selection ownership should remain UID-based.

If a selected UID needs its underlying SQLite row for a database operation, first use already-hydrated row state or a private persistence map. Only use `get_chart_ids_by_uid()` for genuinely missing rows.

Do not use the displayed Chart ID rank as a persistence lookup key.

Longer term, helpers should be renamed or collapsed so they do not suggest that `local_row_id` is a third form of chart identity.

---

## `_current_local_row_id()`

This helper likewise represents a migration-era DB-access concern, not product semantics.

When a database operation genuinely requires `charts.id`, preferred order is:

1. reuse the already-loaded chart row's `id` if available
2. use a private hydrated UID ↔ SQLite-primary-key map if already available
3. query SQLite by UID only as a fallback

Do not surface this integer as Chart ID, and do not propagate it farther than necessary.

---

## Database Analytics

Do not repeatedly call:

```python
get_chart_uid_map(...)
```

inside cache iteration when the same UID mappings are already represented by hydrated Database View rows or cache metadata.

The cache should carry or reuse necessary DB plumbing internally for its lifetime.

Analytics output that displays a Chart ID should use the current Database View sort rank. It should not expose UID except through the explicit Dev Tools Chart Data Output setting, and it should not expose SQLite `charts.id` as though it were Chart ID.

---

## Similar Charts / Similarities

Similar Charts and Similarities should use UID for durable internal references and relationship identity.

When already-hydrated rows or chart objects are available, reuse them rather than repeatedly resolving UID ↔ `charts.id` through SQLite.

When presenting a chart to the user:

- show the chart's normal name/alias and, where a numeric identifier is useful, its current user-facing Chart ID rank
- do not display the UID
- do not display SQLite `charts.id` as Chart ID
- do not use the current Chart ID rank as a durable relationship key
- do not query SQLite repeatedly merely to recover a database primary key for a row already present in memory

This distinction is especially important during the current migration because older helpers named `*_chart_id` may actually refer to `charts.id`, while some newer helpers named `*_local_row_id` refer to exactly the same underlying database value. Such helpers should be audited by semantics, not renamed mechanically.

---

# Recommended Rules

The migration should follow these rules:

> EphemeralDaddy has two chart-reference concepts: UID and Chart ID.  
> UID is durable internal identity.  
> Chart ID is user-facing current-sort rank.  
> SQLite `charts.id` is private database plumbing, not a third chart identity.  
> `local_row_id` is transitional terminology for that plumbing, not an architectural target.  
> Reuse already-hydrated database state in RAM rather than repeatedly querying SQLite for UID ↔ primary-key translation.

And for display:

> Never show a chart UID in ordinary UI.  
> Only show UID in Chart Data Output when explicitly enabled under Settings > Dev Tools.  
> Use Chart ID when a compact user-facing numeric reference or current-sort rank is useful.  
> Never substitute SQLite `charts.id` for the user-facing Chart ID rank merely because both are integers.

This preserves the UID-first internal architecture, the intended user-facing Chart ID concept, and the performance advantages of already-hydrated database rows without inventing a third identifier model.

---

# Priority Ranking

## 1. Per-row `get_chart_uid()` calls in Database View / filtering

**Confidence: Very high**

Most likely major regression.

---

## 2. Repeated UID → SQLite-primary-key lookups

**Confidence: High**

Especially relevant to frequently called UI and autosave paths.

---

## 3. Selection UID → SQLite-primary-key reconstruction

**Confidence: High**

Batched, but still unnecessary repeated database work when rows are already hydrated.

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

Those historical commit names contain `row ID` terminology because that is how the migration was implemented at the time. They should not be read as defining a desired third application-level identifier.

The migration's stated objective included reducing redundant SQLite lookups. The remaining hot-path UID/`charts.id` translations appear to work against that objective.

---

# Bottom Line

The UID migration should not be rolled back, and Chart IDs should not be eliminated from the user experience.

EphemeralDaddy should have exactly two chart-reference concepts:

- **`chart_uid`** — static, unique, internal durable identity
- **Chart ID** — short, user-facing current-sort rank

SQLite `charts.id` may continue to exist because it is useful database plumbing. It should remain private implementation state and should not be elevated into a third chart identity.

`local_row_id` should therefore be treated as transitional migration terminology, not as an application concept that needs to be preserved or expanded.

Keep UID as the single source of truth for durable chart identity.

Keep Chart ID as the short, readable indicator of current Database View sort rank.

Keep SQLite primary-key handling contained to persistence/runtime code, reuse already-hydrated values when available, and do not query SQLite to rediscover information the application already has in memory.