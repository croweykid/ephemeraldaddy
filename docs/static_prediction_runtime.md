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
| Static norms source changes | Reclassify cached scores against that source |
| Explicit Recalculate DB Norms | Generate a new static reference, including Distinguishing Factors |

Raw scores and above/below/neutral metadata are written incrementally. Partial
updates preserve other Traits. Classification uses the selected static row,
never an Analytics cohort mean or the old live baseline table. Batch reads
restrict chart and Trait UIDs in SQL and require no chart hydration, scoring,
or factor explanation. Cold Search queues missing selected Traits separately;
unknown scores/norms are never treated as negative evidence.

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

Enneagram no longer loads live reference charts before its static reader.
Distinguishing Factors reads persisted metric payloads and caches their static
baselines; chart presentation and sort refresh run outside the GUI thread. Old
snapshots lacking this section report it unavailable until an explicit rebuild.
No replacement norms are manufactured during rendering.

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
6.96 ms**, with **4,000 SELECTs reduced to 4**. Both paths performed zero score
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
