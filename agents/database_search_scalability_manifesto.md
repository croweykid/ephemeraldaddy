# Database Search and Analytics Scalability Manifesto

**Status:** Proposed staged implementation plan  
**Scope:** Database View search, filtering, list hydration, analytics, Similar
Charts, and the persistence projections that support those workflows  
**Primary constraint:** Preserve research accuracy and every existing filter
while making common queries interactive on substantially larger databases.

## 1. Purpose

Search and population analytics are central product capabilities. Their
performance must not depend on constructing every chart, decoding every
serialized field, or creating a Qt item for every database row.

The `app.py` refactor described in `agents/app_py_refactor_manifesto.md` is an
essential prerequisite because it establishes UID-first identity, explicit
workflow ownership, typed query boundaries, and targeted invalidation. Moving
existing loops into new modules is not, by itself, a performance improvement.
The scalable result also requires:

1. immutable query values independent of Qt;
2. an explicit query plan that reduces candidates before expensive work;
3. indexed SQL predicates and selected normalized search projections;
4. dependency-aware, incremental projection and cache maintenance;
5. paged or virtualized result presentation;
6. candidate retrieval before exact similarity scoring;
7. cancellable, revision-aware background jobs; and
8. reproducible correctness and performance gates.

This document defines how to introduce those capabilities without a flag-day
rewrite.

## 2. Relationship to the `app.py` manifesto

This proposal extends, rather than replaces, the approved architecture:

- Chart identity is `chart_uid` in queries, results, events, caches, selections,
  and workers. Numeric row IDs remain local to SQLite adapters.
- Search code moves toward
  `gui/features/database_view/search/`, not the legacy
  `gui/features/charts/` staging package.
- `DatabaseSearchQuery` is the canonical immutable input value.
- Search evaluators do not inspect Qt widgets or accept an entire window.
- `ChartRecalculationPolicy` and `RecalculationCoordinator` determine which
  projections, caches, panels, and analytics are affected by a change.
- Unknown time, rectified time, factual reliability, and
  `chart_uses_houses` remain explicit correctness inputs.

The two plans may proceed in bounded parallel slices, but scalable search must
not create a second identity system, a competing recalculation policy, or a new
window-as-service-locator.

## 3. Problem statement

The current wide chart record is effective for saving and loading one complete
chart. It is less effective for indexed membership queries across serialized
collections such as tags, sentiments, gates, channels, or traits. When those
criteria are evaluated in Python, approximate search cost is:

```text
T_search = O(number_of_candidate_charts × active_predicate_cost)
```

If all records are candidates, adding charts makes every complex search more
expensive. Constructing full chart objects and Qt items compounds the cost.

Naive all-pairs comparison has a still worse shape:

```text
T_pairwise = O(number_of_charts² × exact_feature_cost)
```

SQLite storage capacity is therefore not the practical limit. Candidate
selection, deserialization, derived calculations, similarity scoring, and GUI
materialization will become limiting first.

## 4. Goals and non-goals

### Goals

- Preserve every current filter and combination semantics.
- Keep common searches interactive as the database grows.
- Avoid loading complete chart objects unless a predicate needs them.
- Avoid recalculation during search when persisted derived data is valid.
- Make query cost, SQL count, rows loaded, and cache behavior observable.
- Preserve stable UID selection and ordering across filtering and paging.
- Support incremental analytics after a small number of chart changes.
- Make stale search and analytics results impossible to apply.
- Provide a measured basis for supported database-size claims.

### Non-goals

- Do not replace SQLite merely because the current query layer is inefficient.
- Do not normalize every field in the chart document.
- Do not change astrological, Human Design, BaZi, prediction, or similarity
  semantics in the name of speed.
- Do not silently treat unknown, rectified, or fallback times as factual.
- Do not add approximate similarity retrieval without preserving an exact and
  explainable final scoring stage.
- Do not move slow synchronous loops into a worker and call that algorithmic
  optimization.
- Do not perform a flag-day Search Panel rewrite.

## 5. Target architecture

```text
Search Panel / saved query
        |
        v
DatabaseSearchQuery (immutable, normalized once)
        |
        v
DatabaseSearchPlanner
        |
        +-- indexed scalar SQL predicates
        +-- indexed projection-table predicates
        +-- cheap persisted/in-memory predicates
        +-- expensive derived predicates
        |
        v
ordered candidate chart UIDs + total/count metadata
        |
        +-- paged Database View row model
        +-- exact analytics evaluator
        +-- similarity candidate retrieval and ranking
```

The persistence layer owns SQL and row conversion. The query layer owns query
semantics and planning. Presentation owns widgets and UID-to-view-index mapping.
No layer should infer query state from another layer's mutable widgets.

## 6. Canonical query model

`DatabaseSearchQuery` is a frozen, typed value object. The exact fields will be
derived from an inventory of the existing Search Panel, but its shape should
follow these rules:

```python
@dataclass(frozen=True, slots=True)
class DatabaseSearchQuery:
    text: str | None
    chart_types: frozenset[str]
    tags: frozenset[str]
    relationship_types: frozenset[str]
    sentiments: frozenset[str]
    human_design_types: frozenset[str]
    human_design_gates: frozenset[int]
    birth_date_range: DateRange | None
    require_known_birth_time: bool
    require_houses: bool
    allow_rectified_time: bool
```

This is illustrative, not permission to omit existing filters.

### Query rules

- Normalize case, whitespace, aliases, dates, enum labels, and empty values
  once when constructing the query.
- Represent inclusion, exclusion, any/all, and unknown-value semantics
  explicitly rather than encoding them in widget state.
- Include time-reliability and house-availability policy whenever a predicate
  depends on them.
- Make queries hashable so caches can use a query signature plus database
  revision.
- Version serialized saved queries so future schema changes can migrate them.
- Keep display labels out of the evaluator; use canonical internal values.

### Pros

- Reproducible searches and straightforward unit tests.
- No repeated widget reads or normalization inside chart loops.
- Enables saved searches, query diagnostics, and deterministic caching.
- Creates a stable boundary for SQL pushdown.

### Cons

- The complete value object will be substantial.
- Legacy filter semantics must be inventoried carefully.
- This boundary enables optimization but does not provide speed by itself.

## 7. Query planning and predicate tiers

`DatabaseSearchPlanner` compiles a query into active predicates and evaluates
them in the cheapest safe order.

### Tier 1: indexed scalar SQL

Use SQL for selective scalar criteria already represented as columns, such as:

- chart UID and chart type;
- created, birth, and death date ranges;
- known-time, rectification, and house-availability flags;
- exact scalar personality or Human Design values where stored canonically;
- other frequently searched scalar categories justified by measurements.

Add conventional indexes only for observed query patterns. Every index adds
write and storage cost, so an index must have a benchmark and an expected query
shape.

### Tier 2: indexed projection membership

Use normalized projection tables for frequently filtered many-valued data.
These tables reduce the candidate UID set through indexed joins or `EXISTS`
clauses before Python sees a record.

### Tier 3: cheap persisted evaluation

Some low-frequency or structurally complex fields may remain serialized. Load
only the columns needed by active predicates and evaluate inexpensive,
persisted values for the SQL survivors. Do not construct full chart objects.

### Tier 4: expensive exact evaluation

Run prediction, similarity, or recalculation-sensitive predicates last and only
for surviving UIDs. Prefer valid persisted results keyed by complete dependency
signatures. If exact evaluation requires calculation, make that cost explicit
in query diagnostics and execute it outside the UI thread.

### Planner output

The plan should expose, at least in development diagnostics:

- active predicate tiers and order;
- SQL statement count and elapsed time;
- candidate count after each tier;
- chart objects constructed;
- cache hits and misses;
- expensive calculations requested;
- total elapsed and UI-thread blocking time.

### Pros

- Most expensive work applies to a small survivor set.
- Query behavior becomes observable and optimizable.
- Simple searches remain simple rather than entering the full evaluator.

### Cons

- SQL and Python implementations need equivalence tests.
- A sophisticated cost optimizer is unnecessary initially and could obscure
  behavior. Start with deterministic tiers and measured ordering.

## 8. Hybrid normalized search projections

Retain the wide chart row as the authoritative chart document. Add indexed
projection tables only for high-value many-to-many search and aggregation
dimensions. Candidate tables include:

```sql
chart_tags(chart_uid, normalized_tag)
chart_relationship_types(chart_uid, relationship_type)
chart_sentiments(chart_uid, sentiment)
chart_traits(chart_uid, trait, state, confidence)
chart_hd_gates(chart_uid, gate)
chart_hd_channels(chart_uid, channel)
chart_hd_centers(chart_uid, center)
collection_members(collection_uid, chart_uid)
```

Each table should normally provide:

- a foreign key or validated UID reference;
- a composite uniqueness constraint beginning with `chart_uid`;
- a reverse index beginning with the queried value;
- canonical normalized values;
- transactional replacement for one chart's projection values.

Example:

```sql
PRIMARY KEY (chart_uid, normalized_tag)
CREATE INDEX chart_tags_by_tag
    ON chart_tags(normalized_tag, chart_uid)
```

### Projection ownership

- The authoritative save path is the only normal writer.
- Projection updates occur in the same transaction as the authoritative data
  when feasible.
- Serialized legacy values are not an independent writable source of truth.
- A schema/projection version identifies whether a chart needs rebuilding.
- Startup must not perform an unbounded rebuild without progress and
  cancellation. Use resumable batches.
- Backup, restore, integrity checks, and import/export tests cover projections.

### Rollout order

Choose tables using measured frequency and cost. A likely order is:

1. tags and collections;
2. relationship types and sentiments;
3. traits;
4. Human Design gates, channels, and centers;
5. additional dimensions only when benchmarks demonstrate value.

### Pros

- Fast indexed membership filtering and database-side counts.
- Eliminates repeated parsing for common analytics.
- Preserves fast complete-chart loading from the existing document row.

### Cons

- More complex writes and migrations.
- Projection drift is possible without one transactional writer and audits.
- Over-normalization would increase complexity without useful speed gains.

## 9. Dependency-aware maintenance and invalidation

Projection and cache updates must be driven by typed changes rather than a
global refresh. The recalculation policy should distinguish at least:

```text
BirthIdentityChange
EffectiveTimePolicyChange
HouseAvailabilityChange
DerivedAstrologyChange
TagsChange
RelationshipsChange
SubjectiveTraitsChange
CollectionsChange
BiographyOrNotesChange
DisplayOnlyChange
```

Examples:

- Biography edits do not rebuild astrology or HD projections.
- Tag edits update tag projections and tag analytics only.
- Birth-data edits invalidate derived fields whose dependency signature
  changed.
- House-dependent projections are absent or marked unavailable when
  `chart_uses_houses` is false.
- Rectified time is included only in workflows whose explicit policy permits
  it; factual analytics must not silently use it.
- Calculation-version changes invalidate only projections depending on that
  version.

### Cache keys

Every result cache must include all inputs that can change its answer:

- chart UID or ordered UID set;
- query or algorithm version;
- authoritative birth-data signature;
- rectified-time-use policy;
- `chart_uses_houses` where relevant;
- relevant tags or subjective-data revision;
- settings signature;
- database/projection revision.

### Pros

- Lightweight edits stay lightweight.
- Small changes produce incremental analytics updates.
- Correctness rules become testable and consistent.

### Cons

- Missing a dependency can cause stale results.
- Initial implementations should invalidate conservatively until coverage is
  strong.

## 10. Database View paging and virtualization

Search speed and render speed are separate. The UI must not create one Qt
widget item per matching chart.

Introduce a UID-oriented `QAbstractItemModel` or equivalent narrow view model
that supports:

- SQL-side filter and sort;
- result count independent of loaded rows;
- incremental/page loading;
- a lightweight display-row projection;
- UID-based stable selection independent of loaded pages;
- UID-to-visible-index mapping only in the view adapter;
- full chart loading only on open or explicit analytical demand;
- cancellation when the query changes;
- restoration of selection and scroll position where meaningful.

The model must preserve logical multi-selection across pages and filters.
Selection ownership belongs in `DatabaseSelectionModel`, not in materialized
Qt items.

### Pros

- Memory and Qt-object count track the visible window rather than all results.
- Large result sets can remain responsive.
- SQL sorting avoids expensive full-list Python rearrangement.

### Cons

- Drag/drop, batch selection, and collection behavior require careful
  characterization.
- Existing code may assume every matching chart has a live list item.
- This migration should follow UID-owned selection state.

## 11. Similarity scalability

Similarity should be separated into candidate retrieval and exact ranking.

### Candidate retrieval

Before exact scoring:

- remove hidden, placeholder, hypothetical, or otherwise ineligible UIDs;
- enforce time reliability and house requirements;
- use inexpensive indexed or precomputed coarse features;
- optionally retrieve a configurable candidate limit;
- record why candidates were excluded.

Begin with transparent SQLite predicates and precomputed buckets. Add an
approximate nearest-neighbor dependency only if benchmarks justify its
packaging and operational cost.

### Exact ranking

- Preserve the existing authoritative scoring algorithm.
- Score only retrieved candidates.
- Cache by source UID, candidate UID, algorithm version, settings signature,
  and both charts' dependency signatures.
- Invalidate only pairs involving a changed UID.
- Keep exclusions and results UID-keyed.
- Return score components so results remain explainable.

### Database-wide pair analysis

Do not rebuild an entire pair matrix after one chart changes. Update or remove
only pairs containing changed/deleted UIDs. For very large databases, require
an explicit bulk-analysis job with progress, cancellation, and a durable
revision marker.

### Pros

- Avoids unnecessary exact comparisons.
- Retains explainable final scores.
- Incremental pair invalidation makes ordinary edits inexpensive.

### Cons

- Overly aggressive candidate filters can hide valid matches.
- Candidate recall must be benchmarked against exhaustive results.
- Persisted pair caches consume storage and need versioned invalidation.

## 12. Background work and stale-result safety

After algorithmic reduction, genuinely expensive work should run outside the
Qt UI thread. Every job carries:

- request ID;
- immutable query or settings value;
- database/projection revision;
- source and candidate UIDs;
- cancellation token;
- progress information;
- result dependency signature.

The UI applies a result only when its request and revision remain current.
Database connections are created and configured for their worker thread; Qt
widgets are created and mutated only on the UI thread.

Threads suit I/O and SQLite waiting. CPU-bound work should prefer vectorized
NumPy operations or, when measurements justify it, processes with explicit
serialization and shutdown behavior.

### Pros

- Prevents frozen windows and stale-result races.
- Supports progress and cancellation for large jobs.

### Cons

- Background execution does not reduce total work by itself.
- Thread/process lifecycle, database connections, and packaging become more
  complex.

## 13. SQLite access policy

Establish one measured connection policy before adding concurrency:

- `PRAGMA foreign_keys = ON`;
- a documented `busy_timeout`;
- explicit transaction scopes;
- consistent row factories;
- read-only analytical connections where useful;
- query timing and row-count instrumentation in development;
- WAL mode only after concurrency, durability, backup, and restore tests show
  a benefit;
- no arbitrary SQL in widgets or GUI controllers.

WAL is not a default cure. It adds `-wal` and `-shm` lifecycle considerations,
and it does not fix long write transactions or inefficient queries.

## 14. Correctness requirements

Every new query and projection path must preserve:

- UID identity across imports, deletes, and restores;
- unknown birth-time behavior;
- explicit rectified-time policy;
- `chart_uses_houses` gating for house-sensitive features;
- separation of factual and provisional data;
- placeholder/hypothetical exclusion rules;
- stable filter inclusion/exclusion and any/all semantics;
- deterministic result ordering with a UID tie-breaker;
- deletion tombstones and projection cleanup;
- no user-visible numeric row identity.

For each migrated filter, run the old and new evaluator against representative
fixtures and compare UID result sets and ordering before deleting the old path.
Differences require an explicit correctness decision, not silent acceptance.

## 15. Performance benchmark plan

Create privacy-safe deterministic databases at approximately:

- 100 charts for correctness and fast CI;
- 1,000 charts for ordinary personal use;
- 10,000 charts for serious research use;
- 100,000 lightweight records for architecture stress tests.

Include realistic distributions of unknown times, rectified times,
house-disabled charts, tags, collections, traits, HD values, prediction cache
states, and hidden/non-aggregable records.

Measure:

- cold startup and first Database View hydration;
- empty/default query;
- indexed name/date/scalar query;
- tag/collection membership query;
- multifactor query with persisted derived values;
- expensive prediction-dependent query;
- query cancellation and replacement;
- first page and subsequent page rendering;
- Database Analytics full and one-chart incremental refresh;
- Similar Charts exhaustive baseline, candidate recall, and exact ranking;
- import/backfill throughput;
- authoritative versus subjective save latency;
- SQL count, rows decoded, chart objects constructed, UI blocking, and peak
  memory.

Report medians and a tail percentile such as p95. CI thresholds need tolerance
for noisy hosts, but large regressions must fail a performance gate.

Do not publish supported chart-count claims until these measurements exist.

## 16. Staged implementation plan

### Stage 0 — Characterize and instrument

- Inventory every Search Panel filter and exact semantics.
- Identify current SQL, deserialization, chart construction, calculation, and
  Qt-render costs.
- Add deterministic benchmark fixtures and query instrumentation.
- Record exhaustive Similar Charts results for recall comparison.

**Exit gate:** correctness fixtures and baseline measurements exist for simple,
complex, and similarity queries.

**Trade-off:** This produces little immediate UI change, but prevents optimizing
the wrong layer or changing research results unnoticed.

### Stage 1 — Establish the typed query boundary

- Add `DatabaseSearchQuery` in the approved workflow package.
- Translate Search Panel widgets to the query once per request.
- Extract pure normalization and predicate semantics.
- Keep the existing evaluator temporarily behind the new boundary.

**Exit gate:** the existing search result set can be reproduced without the
evaluator reading Qt widgets.

**Trade-off:** Architecture improves before latency does; the temporary façade
must have a documented deletion condition.

### Stage 2 — Push scalar predicates into SQLite

- Add a narrow persistence query API returning ordered UIDs and required
  lightweight columns.
- Push date, flags, types, and measured high-value scalar criteria into SQL.
- Batch-load only data required by remaining predicates.
- Add indexes justified by query plans and benchmarks.

**Exit gate:** simple queries avoid full chart-object construction and are
measurably faster without semantic differences.

**Trade-off:** SQL/Python equivalence tests add work, but provide the first
substantial algorithmic reduction.

### Stage 3 — Add high-value projections

- Introduce tags and collection projections first.
- Add resumable, versioned backfill with progress.
- Maintain projections transactionally on save/import/delete/restore.
- Compare projection-backed and legacy result sets.
- Add relationships, sentiments, traits, and HD dimensions only in measured
  order of value.

**Exit gate:** selected membership queries execute through indexed projections,
projection integrity is auditable, and old databases migrate safely.

**Trade-off:** Schema and writes become more complex; limiting normalization to
proven hot dimensions controls that cost.

### Stage 4 — Incremental invalidation and analytics

- Connect typed chart change sets to projection updates.
- Make analytics snapshots UID-keyed and revisioned.
- Recompute only affected sections and UIDs.
- Ensure deletions remove projections and cached contributions.

**Exit gate:** lightweight edits do not trigger broad recalculation or full
analytics refresh, and one-chart changes produce correct incremental totals.

**Trade-off:** Dependency mistakes risk stale data, so retain a diagnostic full
rebuild and comparison command.

### Stage 5 — Virtualize Database View

- Introduce the paged UID row model and narrow Qt adapter.
- Preserve logical selection through pages and filters.
- Move sorting and pagination to the query boundary.
- Remove assumptions that all matches have materialized Qt items.

**Exit gate:** first render and memory use are bounded by page/window size, and
selection/batch/collection regressions pass.

**Trade-off:** This is a visible GUI-infrastructure migration and needs focused
interaction tests and screenshots if behavior changes perceptibly.

### Stage 6 — Optimize Similar Charts

- Separate candidate retrieval from exact ranking.
- Add versioned, dependency-complete pair caching.
- Add incremental invalidation for changed/deleted UIDs.
- Benchmark candidate recall against exhaustive scoring.
- Add explicit bulk-analysis mode for database-wide pair work.

**Exit gate:** candidate mode meets an agreed recall target, exact scores remain
identical, and ordinary edits do not rebuild unaffected pairs.

**Trade-off:** Candidate retrieval is faster but adds recall risk; exact
exhaustive mode remains the validation oracle.

### Stage 7 — Cancellable background execution

- Move remaining expensive evaluation, analytics, and similarity jobs off the
  UI thread.
- Add request/revision tokens, progress, cancellation, and shutdown handling.
- Prevent stale results from updating a newer query or selection.

**Exit gate:** benchmark workloads remain interactive, cancellation is prompt,
and stale-result tests pass.

**Trade-off:** Concurrency adds lifecycle complexity and must follow work
reduction rather than conceal avoidable work.

### Stage 8 — Remove compatibility paths and enforce budgets

- Delete widget-reading and full-scan compatibility evaluators after parity.
- Remove temporary serialized-field membership paths once projection backfill
  and integrity repair are reliable.
- Add source gates for UID-only public interfaces and no SQL in widgets.
- Enforce representative correctness and performance budgets in CI.

**Exit gate:** one authoritative query path remains, documented performance
budgets pass, and projection repair/rebuild tooling is available.

## 17. Migration and rollback safety

- Use additive schema migrations before switching readers.
- Backfill in bounded transactions with a durable progress marker.
- Keep old readers available only until parity and integrity gates pass.
- Do not dual-write indefinitely; document the release/version that removes
  each compatibility path.
- Validate counts and sampled values after backfill.
- Provide a safe projection rebuild because projections are derived data.
- Never delete authoritative serialized/source data merely to save space during
  the first rollout.
- Test backup and restore both before and after projection schema introduction.
- On projection corruption, prefer rebuilding derived projections from
  authoritative chart data rather than attempting speculative repair.

## 18. Testing matrix

### Query semantics

- Every filter alone.
- Representative any/all/exclusion combinations.
- Empty, missing, malformed legacy, and Unicode values.
- Stable ordering and UID tie-breaking.
- Saved-query version migration.

### Time and factual integrity

- Known time.
- Unknown time.
- Rectified time allowed and forbidden.
- Import fallback time/location.
- `chart_uses_houses` true and false.
- House-sensitive queries never include unavailable facts.

### Projection integrity

- Create, edit, delete, import, restore, and bulk edit.
- Transaction rollback.
- Interrupted and resumed backfill.
- Projection version upgrade.
- Full rebuild equals incremental state.

### UI behavior

- Selection survives filters, paging, refresh, and deletion where appropriate.
- Batch operations address logical UID selections, not only visible rows.
- Rapid query changes cannot apply stale results.
- Cancellation and close are safe.
- Result counts and empty states remain accurate.

### Similarity

- Exact score parity.
- Hidden/non-aggregable exclusion.
- Cache hit, invalidation, and algorithm-version change.
- Candidate recall against exhaustive fixtures.
- No stale worker result crosses source UID or settings revision.

## 19. Pros and cons of the complete proposal

### Benefits

- Search work becomes proportional to a reduced candidate set rather than the
  entire database for most queries.
- SQLite performs the indexed set operations it is designed to handle.
- Full chart construction and expensive calculations become exceptional.
- Database View memory and render cost stop tracking total result count.
- Incremental projections and analytics keep ordinary edits inexpensive.
- Similarity retains exact, explainable scores while reducing comparisons.
- Typed boundaries make future filters safer to add and easier to benchmark.
- UID identity and time-reliability rules improve correctness as well as speed.

### Costs and risks

- More schema objects, migrations, and transactional maintenance.
- A staged period with compatibility evaluators and parity tests.
- Paging requires nontrivial Database View interaction changes.
- Invalidation bugs can create stale projections or caches.
- Similarity candidate reduction introduces recall considerations.
- Background jobs add cancellation, shutdown, and database-connection concerns.
- Benchmarks and large fixtures require ongoing maintenance.

These costs are preferable to a backend replacement or rewrite because each
stage produces a testable improvement, preserves authoritative chart data, and
can be rolled out independently.

## 20. Definition of success

The undertaking is complete when:

- Search Panel state is represented by immutable `DatabaseSearchQuery` values;
- evaluators do not inspect Qt widgets;
- common scalar and membership predicates execute through indexed SQLite
  paths;
- only surviving candidates enter persisted/Python or expensive evaluation;
- chart objects are constructed only when required;
- Database View presentation is paged or virtualized and UID-selected;
- analytics update incrementally from typed changes;
- Similar Charts uses candidate retrieval plus exact, explainable ranking;
- all background results are cancellation- and revision-safe;
- unknown, rectified, fallback-time, and `chart_uses_houses` rules are identical
  across search and analytics;
- projection rebuild, migration, backup, and restore paths are tested;
- 1k, 10k, and stress-scale benchmark results are recorded;
- supported database-size and latency claims are based on measurements; and
- temporary full-scan and dual-read compatibility paths are removed.

## 21. Per-change checklist

Before merging a search or analytics scalability slice:

1. Identify the canonical workflow owner and applicable manifesto phase.
2. State the authoritative data source and any derived projections.
3. Confirm all public chart identity is UID-based.
4. Document time reliability and `chart_uses_houses` behavior.
5. Record the old evaluator's result set for representative fixtures.
6. Measure baseline SQL count, rows loaded, chart objects created, elapsed time,
   UI blocking, and memory relevant to the slice.
7. Implement the smallest independently testable change.
8. Compare old and new UID result sets and ordering.
9. Test create/edit/delete/import/restore effects on derived state.
10. Verify cancellation and stale-result behavior if workers are involved.
11. Record before/after measurements without overstating conclusions.
12. Name every compatibility path and its deletion gate.