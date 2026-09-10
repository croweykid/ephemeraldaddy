# Three-Lilith Rollout — One-Time Database Migration Addendum

**Status:** Normative amendment to `agents/EPHEMERALDADDY_THREE_LILITH_ROLLOUT_PLAN.md`.

**Precedence:** Where this file conflicts with the rollout plan's existing migration, Database Norms Snapshot, testing, implementation-sequence, or acceptance-checklist language, **this addendum controls**. In particular, it supersedes any wording that could be read as requiring Database Norms Snapshot, application startup, chart loading, or another ordinary feature to recalculate the entire database.

## Hard requirement: database-wide recalculation happens once, manually

The conversion of legacy one-Lilith chart data into the new three-Lilith schema is a **one-time, explicitly user-triggered database migration**. It is not a recurring recalculation policy and must not become routine application behavior.

The full-database migration must **never** run automatically from application startup/bootstrap, database open, Settings open, Chart View open, chart-list refresh, ordinary chart load/save, Similarities Analysis, Database Analytics, Personal or Global Transits, Personal Timeline, Database Norms Snapshot generation, a schema/version check, or any other normal feature invocation.

Normal creation/editing/import of an **individual chart** may calculate that chart directly into the current three-Lilith schema as part of that chart's normal calculation lifecycle. If an individually opened legacy chart must be refreshed for correctness, that refresh must be limited to that chart. It must never fan out into a database-wide recalculation.

Merely discovering that the database-wide migration has not been completed may update a status indicator. **Detection must never start the migration.**

## Manual location and UI

Add the migration under:

```text
Settings > Developer Tools
```

Suggested states:

```text
Three-Lilith database migration: Not run
[Migrate Database to Three-Lilith Schema…]
```

```text
Three-Lilith database migration: Incomplete
[Resume Three-Lilith Migration…]
```

```text
Three-Lilith database migration: Complete
```

After successful completion, do not leave an easy accidental button that blindly recalculates the whole database again. If a developer-only rerun option is retained, label it explicitly as a rerun, require confirmation, and skip already-current charts unless the user deliberately selects a separate force-recalculate operation.

## Persistent migration state

Keep per-chart schema state and database-wide migration state separate.

Per-chart state identifies whether one chart's derived astronomy data is current. This enables resumability and idempotence.

Database-wide state records that the one-time migration version has completed, conceptually equivalent to:

```text
three_lilith_db_migration_version = 1
```

Use existing database metadata/migration infrastructure where available rather than introducing a parallel versioning mechanism.

A startup status check, if needed, must be cheap: read the persistent migration/version marker and continue. **Do not scan, hydrate, deserialize, or recalculate thousands of chart rows on startup merely to determine migration status.**

Once the migration succeeds, future launches should perform no three-Lilith database-wide recalculation.

## Accurate progress bar is mandatory

The database-wide migration must use EphemeralDaddy's existing boilerplate progress-bar/progress-dialog mechanism. Locate and reuse the established component/helper in-tree rather than inventing a second progress framework.

Use a determinate progress bar whenever chart counts are knowable. An indeterminate spinner is not acceptable for a multi-thousand-chart migration.

Search for the existing implementation with something similar to:

```bash
rg -n 'QProgress|ProgressDialog|progress_bar|progress bar|setRange\(|setMaximum\(|setValue\(|progress.*signal|cancel.*progress' ephemeraldaddy tests
```

If several helpers exist, prefer the one already used for long-running database/batch work.

### Phase 1 — preflight

Obtain the database chart-row count cheaply first, using the repository's normal count query/path. Then inspect migration/schema state.

Show real progress, for example:

```text
Checking charts for migration…
1,842 / 2,973
```

At the end of preflight, freeze the set and count of charts that actually require migration.

### Phase 2 — recalculate and persist

Reset/reconfigure the determinate progress bar to the exact number of charts requiring migration.

Show real counters, for example:

```text
Migrating charts…
731 / 2,614
Already current: 359
Skipped: 4
Failed: 1
```

The primary progress counter advances **only when a chart reaches a terminal outcome in the current run**: successfully recalculated and durably persisted, explicitly skipped for a recorded reason, or failed and recorded. Do not advance merely because work was queued or started.

Do not mutate the denominator opportunistically during Phase 2. If the work set changes because of a meaningful concurrency problem, stop/reconcile rather than displaying misleading progress.

The bar represents completed chart records, not a fabricated ETA. An ETA is unnecessary unless the existing boilerplate already computes one from real completed work.

The progress UI must remain responsive. Use the established worker/progress mechanism when safe. Do not block the Qt event loop for thousands of calculations. Respect database and ephemeris thread-affinity constraints rather than moving unsafe objects to another thread solely to obtain responsiveness.

## Cancellation, interruption, and resume

If the existing progress boilerplate supports cancellation, wire it up.

On cancel:

- finish or roll back the current chart at a safe transaction boundary
- stop further chart processing
- preserve charts already migrated successfully
- do not set the database-level completion marker
- leave status as `Incomplete`
- require another explicit Developer Tools action to resume

A crash or forced quit must have equivalent recoverability. Do not wrap the entire multi-thousand-chart migration in one giant transaction.

On explicit resume, preflight again and skip charts already at the current per-chart schema version. Successfully migrated charts must not incur another expensive recalculation.

## Completion semantics

Set the database-level completion marker only after successful chart data is durably persisted, dependent cache/signature invalidation is complete, post-migration validation succeeds, and migration bookkeeping commits.

The chart-processing bar may reach 100% once every planned chart has reached a terminal outcome, but the final dialog must not say **Complete** until validation/bookkeeping succeeds.

Cancellation, blocking failures, or uncommitted work must never produce a false completed migration marker.

Show a final summary using actual counters:

```text
Charts scanned:          N
Already current:         N
Successfully migrated:   N
Skipped / unrecoverable: N
Failed:                  N
```

If cancelled, report that explicitly and show how much remains.

## Database Norms Snapshot must not become a migration entry point

The rollout plan previously described the manual Database Norms Snapshot as recalculating/migrating legacy source charts before scoring. **That behavior is superseded by this addendum.**

Database Norms Snapshot is a repeatable analytical operation. The three-Lilith database conversion is a one-time migration. Keep them separate.

Required Norm Snapshot behavior:

1. Read the persistent three-Lilith migration/body-schema status through the cheapest available metadata path.
2. If migration has not completed, stop before norm scoring.
3. Direct the user to `Settings > Developer Tools > Migrate Database to Three-Lilith Schema…`.
4. Do not start, resume, or inline the bulk migration from Norm Snapshot.
5. Once migration status is current, build norms from current canonical chart data.
6. Validate that stale/ambiguous one-Lilith rows are not being treated as current.
7. If such rows unexpectedly exist despite a completed marker, fail safely and report the inconsistency rather than automatically repairing the whole database.
8. Preserve body-schema provenance in the generated snapshot.

Conceptually:

```text
Developer Tools migration = one-time database transformation
Database Norms Snapshot   = analytical snapshot of an already-current database
```

## Required tests

The rollout must include regression tests proving all of the following:

- normal startup does not invoke the database-wide migration
- opening the database does not invoke it
- opening Settings does not invoke it
- opening Chart View does not invoke it
- Similarities Analysis does not invoke it
- Database Analytics does not invoke it
- transit generation does not invoke it
- Database Norms Snapshot does not invoke or resume it
- a migration-version/status check does not invoke it
- only the explicit Developer Tools migration action starts the database-wide work
- a completed migration marker prevents automatic future reruns
- a new chart is created directly under the current three-Lilith schema
- migration reruns/resumes skip already-current charts
- cancellation leaves the database migration state incomplete
- resume preserves and skips previously successful charts
- failures cannot falsely set the completion marker
- preflight uses a real chart-count denominator
- migration uses the frozen count of charts requiring work
- progress advances only for real terminal per-chart outcomes
- migrated/skipped/failed counters match actual outcomes
- final summary counts reconcile with the preflight work set
- Norm Snapshot blocks and directs the user to Developer Tools when migration is incomplete
- Norm Snapshot rejects unexpected mixed-schema data rather than launching bulk recalculation

## Do-not-do rules added by this amendment

Do **not** implement the three-Lilith migration as an automatic startup migration. Do not implement a `for chart in all_charts: recalculate(chart)` check on every launch. Do not put bulk recalculation inside ordinary chart hydration. Do not make research features opportunistically repair the database. Do not make Database Norms Snapshot silently perform migration. Do not use an endless spinner when an accurate denominator is available. Do not increment progress when work is merely queued. Do not mark migration complete after cancellation or blocking failure. Do not recalculate already-current charts on ordinary resume/rerun.

## Acceptance requirements added by this amendment

Before the three-Lilith rollout is considered complete, manually verify that the migration is reachable only from `Settings > Developer Tools`; normal startup remains fast and never launches it; the completion state survives restart; interrupted migration resumes only when explicitly requested; already-current charts are skipped; the existing progress dialog displays accurate determinate preflight and migration counts; the UI remains responsive; cancellation is safe; final counters reconcile; and Database Norms Snapshot refuses to perform the migration itself.
