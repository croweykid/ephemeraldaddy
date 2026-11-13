# Shared static Predictions runtime

Runtime population references belong to `core/prediction_norms.py`. It selects
Official or My Database, memoizes documents by path/mtime/size, supports v1 and
v2 namespaces, and exposes a borrowed read-only reference for numerical work.
The copying loader remains available to explicit snapshot editors/generators.
HD Electrochemistry retains its separate live-database norms behavior.

`analysis/trait_prediction_index.py` governs numerical Trait access for Chart
View, Rankings, Analytics, accuracy reviews, Search, and Fantasy RPG alignment.
It reuses the existing scorer, effective birth-time context, SQLite caches, and
background queue. GUI read views may retain labels, filters, or rendered data;
they no longer determine whether numerical scores need recalculation.

| Event | Work |
| --- | --- |
| Trait model saved / anti-trait appended | Queue only that Trait across eligible chart UIDs |
| Trait renamed | Apply current label through its permanent UID; no rescore |
| Trait archived | Remove from active roster; preserve cached numerical values |
| Trait deleted | Purge only its UID from raw/derived caches |
| Chart astro inputs saved | Consume the existing durable journal and refresh only that chart's Traits/alignment |
| Tags, aliases, notes, cohort changes | Reuse numerical scores |
| Chart roster / placeholder changes | Refresh Rankings and Search membership views; reuse saved scores and queue only missing cells |
| Static norms source changes | Reclassify cached scores against that source |
| Explicit Recalculate DB Norms | Generate a new static reference, including Distinguishing Factors |

Raw scores and above/below/neutral metadata are written incrementally. Partial
updates preserve other Traits. Classification uses the selected static row,
never an Analytics cohort mean or the old live baseline table. Batch reads
restrict chart and Trait UIDs in SQL and require no chart hydration, scoring,
or factor explanation. Search queues missing or input-mismatched selected
Trait cells separately, retaining older scores while replacements calculate.
This also repairs Traits edited while archived after they become active again;
availability or label changes alone leave valid numerical cells untouched.
Unknown scores/norms are never treated as negative evidence.

Each cached cell records the chart's durable astro journal revision. Batch reads
compare this checkpoint without loading charts, so an interrupted refresh remains
discoverable after restart, including partially refreshed chart/Trait sets. Older
caches without checkpoints are verified in the worker for previously edited
charts; matching signatures reuse their scores. Writes check the captured astro
revision under the SQLite write lock before replacing either raw or derived
rows. A new birth save cannot make an obsolete calculation appear current.
Rankings starts its collector for stale cells even when all scores are present,
and keeps the available rows visible during refresh. Committed legacy imports
publish only newly inserted cells; Analytics receives completion through the
shared Qt relay and repaints the current ranking without polling.
Analytics' snapshot-backed rankings also queue missing/stale cells for only the
current chart scope and selected Trait. Their scoped relay is installed before
the cache read, independently of legacy import, and skips unrelated completions.

Trait analytical identities exclude labels, colors, descriptions, sample
provenance, accuracy reviews, and astro analysis. Existing static rows remain
usable by UID even when their legacy full-profile hash differs. This deliberately
accepts stale references rather than silently regenerating a population baseline.
V2 distributions retain their separate recorded/exact-rectified and unknown-time
house policies. No distribution spread is invented for v1 means.

Numerical/factor-evidence work lives in `analysis/`, not `app.py`. Qt job and
presentation boundaries live in `gui/features/predictions/`; Database View's
Weirdness sort has its own small controller. Jobs use value snapshots and reject
obsolete completion tokens. The alignment controller is owned by the window,
so recreating a rendering adapter cannot resurrect the previous chart.

Accepted one-chart Trait metadata also stays on the live chart, so unsaved
charts and birth-data drafts survive subsequent renders without writing scores
to SQLite. The analysis reader checks this view before persisted scores, using
the chart's astro signature, Trait definitions/labels, and per-Trait static norm
references. Worker delivery validates the captured key against the live chart.
This presentation cache preserves factor evidence; it does not own scoring or
population norms. The optional gender overlay shares the base key and stays in
its own display cache.

Enneagram no longer loads live reference charts before its static reader.
Distinguishing Factors reads persisted metric payloads and caches their static
baselines; chart presentation and sort refresh run outside the GUI thread. Old
snapshots lacking this section report it unavailable until an explicit rebuild.
No replacement norms are manufactured during rendering.
Both chart presentation and Weirdness sorting guard persistence with the saved
chart's astro revision, so a birth save wins over an older calculation.
Accepted sort results update the score and freshness columns together in raw
Database View rows. Normalization therefore retains their current status when
collections change. Row adaptation lives beside the sort controller and
preserves the older provenance-only row shape.

## Compatibility boundaries

The old Traits/Analytics methods and Distinguishing Factors import path are
thin facades. Remove them when their remaining window/render callers move to
the canonical workflow packages. The old Analytics JSON cache is imported only
into missing SQLite cells; journal-changed charts are skipped. The application
never writes that parallel numerical cache again. The former baseline accumulator
is retained for compatibility with external callers, with no production runtime
callers or role in classification.

The optional recorded-gender setting remains a Chart View display overlay. It
uses the same static reference and never builds a second live population or
replaces the common astrology-only cached scores.

## Validation and measurements

The focused suite covers partial writes, mixed/partial legacy caches, cached
Search/Rankings, model/astro invalidation, canceled/superseded work, v2 house
modes, static document reuse, and GUI-free engine imports. Real offscreen Qt
checks cover first accuracy results, ratings/markers, GUI delivery/responsiveness,
previous-chart rejection, recreated alignment adapters, and close/reopen behavior.

Synthetic benchmark: 500 charts, 30 stored Traits, one requested Trait, three
runs per checkout. On this environment the median fell from **1,366.8 ms to
8.88 ms**, including durable astro-revision checks, with **4,000 SELECTs reduced
to 4**. Both paths performed zero score
calculations. These are cache-read measurements, not full application startup
or a benchmark against the user's database.

Reproduce against this branch or an older checkout:

```sh
python tools/benchmark_trait_cache_reads.py --checkout /path/to/checkout --charts 500
```

The benchmark creates and removes its own synthetic database. The broader
legacy regression selection had 32 failures before this work; the same 32 test
names still fail, with no additional failures. They include assertions tied to
old facade source locations and pre-existing cache fixture/import behavior.
