# EphemeralDaddy Sidereal / Jyotish Rollout Mandate

## Status

This document is the implementation mandate for adding sidereal astrology and Jyotish-style divisional-chart support to EphemeralDaddy.

It is intentionally conservative about persistence and intentionally permissive about experimentation. The objective is to determine whether sidereal and divisional-chart features are useful enough to deserve first-class product treatment **without** multiplying the database into thousands of redundant chart records or contaminating established tropical behavior.

The implementation should proceed in phases. The first phase is a proof of concept built from production-quality primitives, not a disposable spike.

---

## 1. Core Product Model

EphemeralDaddy continues to have **one persisted person/chart entity per chart UID**.

Sidereal D1 and divisional charts are alternate calculated views of that same parent chart. They may feel like nested charts in the UI, but they are **not independent people, independent database charts, or independent UIDs**.

Conceptually:

```text
Persisted Chart / Person
    |
    |-- Tropical chart
    |-- Human Design
    |-- BaZi
    `-- Sidereal / Jyotish projection layer
         |-- D1 Rashi
         |-- D2 Hora
         |-- D3 Drekkana
         |-- D7 Saptamsha
         |-- D9 Navamsha
         |-- D10 Dashamsha
         |-- D12 Dwadashamsha
         `-- additional supported vargas
```

The UI may present these as child or nested chart views. Internally, there is still only one chart identity.

### Mandatory invariant

Do **not** create permanent rows or chart UIDs for D1, D2, D3, D9, D10, etc.

Do **not** allow derived charts to recursively spawn persisted derived charts.

The storage model must remain approximately:

```text
~3,000 persisted charts
```

not:

```text
~3,000 x number_of_vargas persisted charts
```

The latter is only multiplicative rather than mathematically exponential, but it is still unnecessary database growth and would infect ranking, export, backup, refresh, UID, relationship, trait, image, and migration behavior throughout the application.

---

## 2. Three Layers Must Remain Distinct

The implementation must keep the following concepts separate.

### Layer A: Coordinate system

Examples:

- tropical
- sidereal / Lahiri
- future alternate ayanamshas

### Layer B: Chart projection

Examples:

- D1 Rashi
- D2 Hora
- D3 Drekkana
- D9 Navamsha
- D10 Dashamsha
- etc.

### Layer C: Analysis framework

Examples:

- EphemeralDaddy's existing Western analytics
- Jyotish-specific analysis added later

These are not synonyms.

A sidereal D1 chart can be analyzed using EphemeralDaddy's existing dominance/aspect/prevalence machinery, but that does **not** make those calculations canonical Jyotish analytics.

Likewise, a D9 chart can be displayed using ED's standard chart presentation and analyzed with ED's Western aspect engine, but a Western grand trine in D9 is not the same concept as Jyotish drishti.

UI labels and exports must make the distinction visible whenever ambiguity is possible.

Recommended future display metadata:

```text
Coordinate system: Sidereal
Ayanamsha: Lahiri
Division: D9 Navamsha
Analysis framework: EphemeralDaddy
```

---

## 3. Sidereal D1 Is the Foundation, Not a Second Persisted Chart

The sidereal D1 should be treated as a deterministic projection derived from the parent's birth data and configured ayanamsha.

A convenient API may expose it as something like:

```python
chart.sidereal
```

but this should represent derived astro data, not a new persisted `Chart` instance.

Suggested shape:

```python
@dataclass(frozen=True)
class SiderealChartData:
    parent_uid: str
    ayanamsha: str
    positions: Mapping[str, float]
    retrogrades: Mapping[str, bool]
    ascendant: float | None
    mc: float | None
    houses: Sequence[float] | None
    nakshatras: Mapping[str, object] | None
    calculation_token: str
```

Exact fields may differ according to the refactor's current data contracts.

### Important terminology

Do not casually call sidereal D1 "metadata" in implementation code if that conflicts with EphemeralDaddy's existing classification of metadata versus derived ASTRO_DATA.

Sidereal coordinates are calculated astrology data.

---

## 4. D1 May Be Cached; Varga Charts Should Be Generated On Demand

It is acceptable to retain/cache a compact sidereal D1 projection for a parent chart if profiling demonstrates a benefit.

It is **not** acceptable to persist full independent D2/D3/D9/etc. chart objects for every database record.

Preferred behavior:

```text
birth data
   -> sidereal D1 projection
       -> D9 requested
           -> derive D9
           -> render / analyze
           -> retain only in bounded memory cache if useful
```

A divisional chart is a deterministic mathematical transformation of sidereal longitudes. It does not require a new ephemeris calculation for each varga.

The varga layer should consume the sidereal longitudes used for D1, not scrape or reverse-engineer data from a rendered D1 window.

### Suggested cache key

```python
CacheKey(
    parent_uid,
    astro_data_recalculation_token,
    ayanamsha,
    division,
    varga_ruleset_version,
)
```

A cache value should contain compact calculated positions and other deterministic derived fields, not a duplicate biography, traits, notes, photo gallery, widgets, database relationship state, or persisted `Chart` entity.

A bounded in-memory LRU cache is appropriate if repeated switching such as:

```text
D1 -> D9 -> D10 -> D9
```

otherwise causes needless recalculation.

---

## 5. Recalculation / Invalidation Rules

Sidereal and divisional data must invalidate whenever source birth data that affects astrology calculations changes.

Use or extend the existing canonical astro-data recalculation token rather than inventing unrelated invalidation logic.

At minimum, derived data must become stale when applicable inputs change, including:

- birth date
- birth time
- timezone / UTC resolution
- latitude / longitude
- timed versus untimed chart status
- rectification-related source data
- configured ayanamsha
- varga ruleset version

Changing subjective metadata, notes, images, or unrelated presentation settings must not trigger sidereal/varga recomputation.

---

## 6. Initial Ayanamsha Policy

The proof of concept uses **Lahiri**.

Do not implement sidereal astrology by hardcoding a fixed subtraction such as "about 24 degrees."

The ayanamsha is date-sensitive and must come from the astronomical calculation layer / Swiss Ephemeris support.

Architecture should allow future selectable ayanamshas without forcing the first UI to expose them.

Recommended configuration object:

```python
@dataclass(frozen=True)
class ZodiacContext:
    zodiac: Literal["tropical", "sidereal"] = "tropical"
    ayanamsha: str | None = None
```

Avoid scattering ad hoc `sidereal=True` booleans through unrelated call sites.

---

## 7. Swiss Ephemeris Safety

The current ephemeris stack uses `pyswisseph` / Swiss Ephemeris.

Swiss Ephemeris exposes sidereal calculation modes and sidereal house calculation support. Use those facilities rather than manually shifting every value unless a deliberately chosen projection strategy proves safer.

### Concurrency caveat

`set_sid_mode` is library/global state.

Before allowing concurrent calculations with multiple ayanamshas or worker threads, explicitly determine whether the current calculation model can race on sidereal mode.

Acceptable solutions may include:

- a lock around stateful Swiss Ephemeris sidereal operations;
- a tightly scoped calculation facade that sets and consumes sidereal mode atomically;
- or a validated projection approach that avoids mutable global state where mathematically equivalent.

Do not assume this problem away.

The proof of concept may use one Lahiri mode, but the production architecture must not quietly become unsafe when later parallelism or multiple ayanamshas are added.

---

## 8. Sidereal Houses and Angles Must Match the Coordinate System

Never mix sidereal planets with tropical house cusps/angles and present the result as a coherent sidereal chart.

For sidereal D1:

- planets are sidereal;
- Ascendant / MC must be sidereal;
- house cusps must be sidereal;
- any house assignments shown in analytics must use the same coordinate system.

This must be tested explicitly.

---

## 9. Varga Mathematics Must Be Rule-Driven

Divisional charts are not all implemented correctly by a naive generic formula such as:

```python
degree // (30 / N)
```

Segment boundaries are only part of the problem. Sign assignment rules differ by varga and tradition; some vargas have special mappings.

Use an explicit dispatch/rule layer.

Example:

```python
VARGA_RULES = {
    "D1": rashi,
    "D2": hora,
    "D3": drekkana,
    "D7": saptamsha,
    "D9": navamsha,
    "D10": dashamsha,
    "D12": dwadashamsha,
    "D30": trimsamsha,
}
```

Each supported division must have:

- documented rule/tradition;
- deterministic tests at boundaries;
- tests for all twelve source signs where relevant;
- exact behavior at 0 degrees and segment boundaries;
- a versioned ruleset if future tradition choices may alter results.

Do not ship a generic varga calculator that is known to be wrong for special cases.

---

## 10. Nakshatras and Padas

Once sidereal longitude exists, Nakshatra support is inexpensive and should be architecturally adjacent to the sidereal layer.

Basic geometry:

```text
27 Nakshatras
360 / 27 = 13 degrees 20 minutes each
4 padas per Nakshatra
1 pada = 3 degrees 20 minutes
```

Nakshatra/pada derivation belongs to the sidereal coordinate layer rather than a tropical chart parser.

It may be deferred from the first visible POC if necessary, but the module structure should not make it difficult to add.

---

## 11. UI Entry Points

Users should ultimately be able to open sidereal/divisional charts through both of the following paths.

### A. Chart-level button

A `D[#]` / Jyotish button or control accessible from the chart UI.

### B. `window_chrome` navigation

A corresponding menu path for opening the same views.

Both routes must resolve to the same underlying command/factory. Do not create separate sidereal calculation implementations for menu versus button launches.

Conceptually:

```text
D1 button
or
window_chrome -> Jyotish -> D1 Rashi
                      -> D9 Navamsha
                      -> D10 Dashamsha
                            |
                            v
              open_sidereal_chart(parent_uid, division)
```

The initial POC only needs D1 and D9 unless implementation testing suggests D1 alone is necessary first.

---

## 12. Sidereal Chart Window

The sidereal/divisional chart opens in a **read-only sidereal version of the Chart Editor window**.

Reuse the existing Chart Editor shell and presentation components where feasible rather than forking an unrelated second editor.

The window is chart-like, but it is not editing a persisted child chart.

### Included

- chart wheel / chart visualization
- sidereal/divisional positions
- houses and angles where valid
- aspects where the selected analysis mode uses them
- Chart Analytics
- Predictions where explicitly supported by the rollout phase

### Excluded

- Material Facts
- Subjective Notes / Observations
- Photo Gallery
- any controls that imply the D1/D9/etc. view owns separate person metadata
- any direct editing that could make the derived chart inconsistent with its parent birth data

### Read-only invariant

Derived astronomical/astrological positions in a D1/D9/etc. window are read-only.

A user must not be able to drag or directly edit "D9 Mars" independently of the parent chart, because the D9 value is determined by the source birth data.

A possible later feature may explicitly offer:

```text
Create hypothetical chart from this view
```

That would create a separate intentionally editable hypothetical chart. It is **not** part of the initial rollout.

---

## 13. Chart-Like Interface / Context Contract

Existing panels should gradually depend on a chart-data interface or protocol rather than requiring a fully persisted `Chart` entity.

Suggested conceptual protocol:

```python
class ChartContext(Protocol):
    positions: Mapping[str, float]
    houses: Sequence[float] | None
    aspects: Sequence[Aspect]
    retrogrades: Mapping[str, bool]
    use_birth_time_data: bool
```

Likely consumers may then accept:

```text
Chart
HypotheticalChart
SiderealD1View
VargaChartView
```

without pretending all of them have persistence, notes, traits, photos, relationships, or identities of their own.

Do not force the entire existing `Chart` class to become the backing object for every derived projection if a lightweight context object suffices.

---

## 14. Chart Analytics Policy

The sidereal Chart Editor **will** include Chart Analytics.

For the POC, existing analytics may be wired to the sidereal/varga positions where mechanically valid.

Examples that are straightforward to recompute against an alternate chart context include:

- sign prevalence
- element prevalence
- modality prevalence
- house prevalence
- quadrant counts / percentages
- aspect counts
- aspect patterns
- other position/aspect-based analytics that do not depend on person metadata

### Critical semantic rule

Existing EphemeralDaddy calculations remain **EphemeralDaddy / Western-style analytics applied to sidereal coordinates** unless and until a Jyotish-specific implementation exists.

For example, existing dominance calculations may be useful and experimentally interesting on a sidereal chart, but they must not be relabeled as canonical Jyotish dominance.

Likewise:

- ED aspects are not automatically Jyotish drishti;
- ED aspect patterns are not automatically Jyotish yogas;
- Western dignity/dispositor logic is not automatically a Jyotish dignity system.

Where ambiguity exists, surface the analysis framework in the UI and export metadata.

A later evolution may offer:

```text
Analysis framework:
(*) EphemeralDaddy
( ) Jyotish
```

but the initial feature does not need a complete second analysis engine.

---

## 15. Predictions Policy

Predictions are the area requiring the strongest rollout gate.

### D1 sidereal

D1 sidereal Predictions are mechanically plausible because natal and transit coordinates can both be calculated consistently in the sidereal system.

Many pure planet-to-planet angular separations remain invariant under a uniform zodiac offset, while the following can change materially:

- sign
- sign ruler / dispositor
- house
- house ruler
- ingress timing / sign context
- Nakshatra
- other sign- or house-dependent interpretation

Therefore D1 Predictions may be enabled after explicit validation that all participating inputs use the same coordinate system and no tropical-only assumptions leak into the presentation or interpretation.

### Divisional-chart predictions

Do **not** automatically point the existing Predictions engine at D9/D10/etc. and declare the result valid.

Questions such as whether to:

```text
natal D9
vs.
transiting planets transformed into D9
```

are astrological-framework decisions, not simple wiring tasks.

Initial mandate:

```text
D1 sidereal: Predictions eligible after validation
D9+ vargas: Predictions disabled or clearly experimental until methodology is deliberately chosen
```

Do not block the entire sidereal/varga POC on solving a complete Jyotish predictive system.

---

## 16. Birth-Time Quality and Untimed Charts

Birth-time uncertainty matters more strongly for divisional angles/houses than for ordinary D1 planetary placements.

D9 divides each 30-degree sign into 3 degree 20 minute sections. Small Ascendant movement can therefore change the Navamsha Lagna near a boundary.

Respect EphemeralDaddy's existing birth-time reliability rules.

Recommended behavior:

```text
Reliable known birth time
    -> planetary varga positions
    -> divisional Ascendant
    -> divisional houses where methodology supports them

Unknown / unusable birth time
    -> planetary varga positions may still be available
    -> divisional Ascendant unavailable
    -> divisional houses unavailable

Rectified / uncertain range
    -> do not present a single fragile divisional Ascendant as certain
```

Any UI suppression rules already used by tropical Chart Analytics for untimed charts should be reused or generalized, not reimplemented independently.

---

## 17. Performance Mandate

The varga arithmetic itself is cheap.

The main performance risk is accidentally triggering every downstream subsystem whenever a derived view is opened.

Avoid chains such as:

```text
calculate D9
 -> construct full persisted Chart
 -> calculate all aspects
 -> calculate dominance
 -> calculate all patterns
 -> calculate all interpretations
 -> run predictions
 -> update rankings/indexes
 -> write database
 -> refresh unrelated UI
```

Instead:

### Rule 1: Coordinates are lazy

Opening D9 calculates D9.

Opening D10 calculates D10.

Opening D9 must not eagerly construct D2 through D8.

### Rule 2: Analyses are independently lazy

Only calculate analytics needed by visible panels or explicit research operations.

### Rule 3: Persistence is minimal

No child-chart database row is required merely to display a varga.

### Rule 4: No ranking/index pollution

Derived views must not automatically appear in ordinary database chart counts, Rankings, search results, chart pickers, trait indexes, relationship graphs, or backup manifests as if they were people.

### Rule 5: Measure before caching broadly

A compact D1 cache is allowed, but do not precompute every chart's every varga merely because it is possible.

---

## 18. Export Rules

Any export initiated from a sidereal/divisional view must identify its coordinate context.

At minimum, exported chart or analytics data should be capable of distinguishing:

- parent chart UID / identity reference
- sidereal versus tropical
- ayanamsha
- division (`D1`, `D9`, etc.)
- analysis framework when relevant
- calculation / ruleset version when required for reproducibility

Do not export a D9 analytics table in a format indistinguishable from the parent tropical chart's analytics.

Existing export/share behavior should otherwise be reused where possible.

---

## 19. Proposed Core Modules

Prefer isolated pure calculation modules over adding dozens of sidereal/varga branches to the monolithic GUI layer.

Suggested organization:

```text
ephemeraldaddy/core/
    ephemeris.py
    houses.py
    draconic.py
    sidereal.py
    vargas.py
```

### `sidereal.py`

Responsibilities may include:

- zodiac/ayanamsha context
- Lahiri D1 projection
- sidereal angles/houses facade
- Nakshatra/pada derivation
- calculation token / cache-key support
- no GUI responsibilities

### `vargas.py`

Responsibilities may include:

- explicit supported varga rule registry
- pure longitude-to-varga transformations
- named division metadata
- ruleset versioning
- boundary-safe tests
- no database writes
- no GUI responsibilities

Keep both modules usable by research code without instantiating windows.

---

## 20. Proof of Concept Must Come Before Broad Rollout

The first implementation should answer three questions:

1. Are the sidereal and D9 calculations correct?
2. What is the actual performance cost over the current ~3,000-chart database?
3. Does divisional-chart matching produce anything empirically interesting enough to justify first-class UI and further Jyotish work?

### POC deliverables

Implement production-quality primitives for:

```text
Lahiri sidereal D1
D9 Navamsha
```

Then provide a lightweight read-only sidereal chart view capable of opening at least:

```text
D1
D9
```

and an isolated research harness for Astro Twin experiments.

No database migration is required for the POC.

No precomputation of all vargas is required.

No complete Jyotish interpretation engine is required.

No complete Jyotish prediction engine is required.

---

## 21. Astro Twin Experiment

The Astro Twin system is the preferred early validation surface because EphemeralDaddy already has a large enough chart database to test whether divisional similarity is producing nontrivial structure.

The POC should support at least three experiment modes.

### A. D1 -> D1

Baseline comparison using sidereal D1 against sidereal D1.

### B. D9 -> D9

Compare a subject's Navamsha against every comparison chart's Navamsha.

Interpretation question:

> Who has a Navamsha most structurally similar to this person's Navamsha?

### C. D9 -> D1

Compare a subject's Navamsha against comparison charts' **sidereal D1**, not their stored tropical D1.

Interpretation question:

> Whose ordinary sidereal natal structure most resembles this person's Navamsha?

This is likely the stranger and potentially more informative experiment.

### Coordinate consistency is mandatory

Do not compare:

```text
Alice D9 sidereal
vs.
Bob tropical D1
```

and treat the result as meaningful. The ayanamsha offset would contaminate the comparison metric.

Correct concept:

```text
~3,000 persisted parent charts
    -> derive ~3,000 Lahiri D1 vectors in memory
    -> derive subject D9
    -> run nearest-neighbor comparison
    -> retain only results / discard temporary vectors as appropriate
```

No new persisted chart rows are necessary.

---

## 22. Astro Twin Statistical Controls

A database of ~3,000 charts will always produce a nearest neighbor. A striking nearest neighbor alone is not evidence that the D9 experiment has explanatory validity.

Also, D9 is mathematically derived from D1; it is not statistically independent of the natal chart.

Therefore the experimental evaluation must include controls.

### Recommended validation sequence

1. Select a subject.
2. Calculate the best astrology-only D9 -> D1 or D9 -> D9 match without inspecting subjective outcome data.
3. After the match is fixed, evaluate held-out non-astrological information where available.
4. Compare against the subject's ordinary D1 -> D1 Astro Twin.
5. Compare against random controls.
6. Compare against shuffled/permuted D9 assignments or another suitable null model.
7. Repeat across enough subjects to determine whether any observed relationship survives anecdotal selection.

Potential held-out dimensions may include existing database information such as:

- traits
- MBTI
- Enneagram
- sentiments / subjective assessments
- similarity observations
- relationship patterns
- other non-astrological labels already available to research tooling

The astrology similarity metric must not directly consume the same held-out labels used to evaluate whether the match is interesting.

### Success criterion

The experiment becomes evidence for deeper rollout only if D9-derived matching consistently outperforms reasonable controls or reveals stable, interpretable structure across a meaningful sample—not because one celebrity pair looks compelling.

---

## 23. POC Should Reuse Current Astro Twin Logic, Not Guess It

Before implementing research comparison, inspect the current Astro Twin code path on the active branch and identify its actual similarity metric, filters, feature vector, weighting, and ranking behavior.

Do not recreate an assumed "Astro Twin" algorithm from memory or documentation if production code differs.

The D1/D9 experimental modes should reuse or explicitly adapt the current similarity machinery so that baseline comparisons remain interpretable.

If the existing Astro Twin code is tightly coupled to persisted `Chart` objects, refactor the comparison boundary toward a lightweight chart-context/vector input rather than persisting derived charts merely to satisfy the current API.

---

## 24. Rollout Phases

### Phase 0 — Inspection and contracts

Before code changes:

- locate current ephemeris and house calculation seams;
- inspect current Chart / ASTRO_DATA ownership after the ongoing refactor;
- inspect current Astro Twin implementation;
- inspect current Chart Editor panel dependencies;
- identify any code that assumes every chart-like object has a UID/database row;
- document Swiss Ephemeris sidereal state/concurrency handling;
- choose authoritative D9 rule references and expected test vectors.

No UI work should precede this inspection if it would force incorrect data contracts.

### Phase 1 — Pure calculation POC

Implement:

- `ZodiacContext` or equivalent;
- Lahiri sidereal planetary positions;
- sidereal angles/houses where birth time is valid;
- D9 calculation from sidereal longitudes;
- unit tests and known external comparison fixtures;
- in-memory batch derivation for research.

No database schema migration.

### Phase 2 — Astro Twin validation

Implement research-only or developer-facing modes:

- sidereal D1 -> D1;
- D9 -> D9;
- D9 -> sidereal D1;
- baseline / random / shuffled controls;
- timing measurements over the existing database.

Use results to decide whether broad divisional-chart UX is justified.

### Phase 3 — Read-only Sidereal Chart window

If Phase 1 calculations are verified, add the read-only chart view.

Initially expose:

- D1
- D9
- standard chart visualization
- valid positions/houses/aspects
- Chart Analytics wired to the derived chart context
- explicit Sidereal / Lahiri / D# labeling

Exclude person-editing panels.

### Phase 4 — D1 Predictions validation

Only after coordinate plumbing is proven:

- wire D1 sidereal natal data to compatible Predictions calculations;
- ensure sidereal transit context is consistent;
- audit sign-, ruler-, house-, ingress-, and interpretation-dependent logic;
- label output clearly.

D9+ Predictions remain gated.

### Phase 5 — Additional vargas

Add divisions individually through tested explicit rules.

Likely candidates:

```text
D2
D3
D7
D10
D12
```

Do not bulk-enable every traditional varga merely because a generic function can emit numbers.

### Phase 6 — Jyotish-native analysis, only if warranted

Potential future systems include:

- drishti
- yogas
- dashas
- Jyotish dignity systems
- varga strength/dignity analysis
- Shadbala
- Ashtakavarga
- functional benefic/malefic logic
- other tradition-specific interpretation layers

These are a separate project tier and must not be smuggled into the basic sidereal-coordinate rollout.

---

## 25. Testing Mandate

### Sidereal calculation tests

Verify against trusted external/reference calculations for multiple dates, locations, and planets.

Test:

- dates far apart in time so ayanamsha drift is exercised;
- sign-boundary cases;
- retrograde bodies;
- Ascendant / MC;
- house cusps;
- timed and untimed charts;
- timezone/UTC conversion behavior.

### Varga tests

For every supported varga:

- all source signs as applicable;
- every segment transition;
- exact boundary behavior;
- values immediately below and above boundaries;
- wraparound near 0 / 360 degrees;
- known published/reference examples.

Floating-point comparisons must have explicit tolerances and must not cause random segment flips near mathematically exact boundaries.

### Regression tests

Tropical calculations must remain byte-for-byte or tolerance-equivalent to pre-feature behavior where the feature is not selected.

Opening a sidereal chart must not mutate global tropical calculation state.

Opening D9 must not alter the parent chart's persisted positions.

Closing a sidereal window must not write a new chart row.

Database chart counts must remain unchanged after browsing derived charts.

### UI tests

Verify:

- both entry points open the same derived mode;
- correct parent identity is displayed;
- Material Facts is absent;
- Subjective Notes/Observations is absent;
- Photo Gallery is absent;
- edit controls cannot mutate derived coordinates;
- untimed charts suppress invalid angles/houses;
- D1/D9 labels and Lahiri context remain visible;
- analytics refresh against the derived context rather than stale tropical data;
- switching divisions does not leak the previous division's analytics.

### Performance tests

Measure at least:

- single-chart D1 generation;
- single-chart D9 generation;
- batch sidereal D1 for the full current database;
- batch D9 for the full current database where needed for research;
- Astro Twin comparison runtime;
- memory footprint before/after batch research;
- UI open/switch latency.

Use measurements to determine whether any persistence/cache beyond lightweight D1 data is justified.

---

## 26. Refresh and State Isolation

Sidereal/divisional refresh behavior must be scoped to the active derived view.

Examples:

- editing the parent birth data should invalidate the open derived chart and refresh it;
- switching D9 -> D1 should refresh analytics using D1 context;
- a tropical Chart Editor refresh must not accidentally consume cached D9 data;
- a D9 analytics refresh must not overwrite the parent tropical chart's persisted analytics;
- closing the derived window must not trigger an unnecessary database save of calculated child state.

Prefer immutable derived-data objects where practical.

---

## 27. Relationship to Existing Human Design and BaZi Support

Human Design and BaZi demonstrate that EphemeralDaddy can expose multiple metaphysical systems from one person/chart record.

They are **not**, by themselves, proof that the current flat `Chart` object is the correct place to store every field of every future system.

Do not extend the current pattern by adding fields such as:

```text
d2_positions
d3_positions
d9_positions
d10_positions
...
```

to every persisted `Chart`.

The sidereal/varga rollout should improve system boundaries rather than make the parent chart object an ever-larger warehouse.

---

## 28. Relationship to Draconic Support

Draconic calculation is an existing conceptual precedent for alternate coordinate projections derived from canonical chart data.

Reuse lessons from its separation of canonical positions versus transformed positions where appropriate.

However, do not force sidereal/varga behavior through draconic code if the underlying astronomy, houses, caching, or context requirements differ.

The reusable idea is the **projection boundary**, not necessarily the exact implementation.

---

## 29. What Must Not Happen

The following approaches are explicitly rejected unless this mandate is deliberately revised.

### Do not:

- create one database `Chart` row per varga;
- assign new chart UIDs to D1/D9/etc.;
- copy Material Facts, Notes, Photo Gallery, traits, relationships, or biography into derived views;
- eagerly calculate every varga for every stored chart at startup;
- persist huge nested derived structures without profiling evidence;
- mix tropical houses with sidereal planets;
- hardcode a constant ayanamsha subtraction;
- assume all vargas use the same generic mapping rule;
- silently label Western analytics as Jyotish analytics;
- silently enable D9 Predictions without choosing a methodology;
- compare D9 sidereal against tropical D1 in Astro Twin research;
- include derived charts in ordinary database rankings/search/chart counts as people;
- allow read-only derived positions to become independently editable;
- let Swiss Ephemeris sidereal global state leak across unrelated calculations;
- fork a second complete Chart Editor implementation when a shared chart-context shell will suffice;
- block the POC on implementing the entire Jyotish tradition.

---

## 30. Decision Gates

### Gate A — Calculation correctness

Do trusted reference charts agree for Lahiri D1 and D9?

If not, stop and fix mathematics before UX work expands.

### Gate B — Performance

Can the current database derive research vectors at acceptable runtime/memory cost without persistence explosion?

If not, optimize/calculate lazily before schema expansion.

### Gate C — Astro Twin signal

Do D9-derived matches show repeatable structure beyond nearest-neighbor inevitability and reasonable null controls?

If no, sidereal D1 may still be worthwhile, but broad varga product investment should be reconsidered.

### Gate D — UI stability

Can the existing Chart Editor accept a chart-like derived context without regressions to tropical editing and refresh behavior?

If not, improve the context boundary rather than persisting fake child charts to work around the UI.

### Gate E — Predictive methodology

D1 Predictions may proceed after consistent sidereal plumbing is validated.

D9+ Predictions require an explicit methodological decision before release.

---

## 31. Definition of Initial Success

The initial Sidereal/Jyotish rollout is successful when all of the following are true:

1. Existing tropical charts remain unchanged.
2. A parent chart can produce a verified Lahiri D1 view without a new persisted chart record.
3. The same parent can produce a verified D9 view on demand.
4. D1/D9 can open in a read-only Chart Editor-derived window.
5. The derived window omits person-specific editing panels.
6. Chart Analytics reads the active derived positions/houses/aspects correctly.
7. Untimed-chart restrictions remain coherent.
8. The database chart count does not increase from browsing sidereal/varga charts.
9. Astro Twin research can compare D1/D1, D9/D9, and D9/sidereal-D1 without persisting thousands of alternate charts.
10. Batch performance over the current database is measured and acceptable.
11. The code clearly distinguishes coordinate system, chart division, and analysis framework.
12. Future vargas and future Jyotish-native analytics can be added without restructuring the database identity model again.

---

## 32. Implementation Philosophy

The user-facing metaphor is:

> a person's sidereal/divisional charts are nested alternate versions of the same chart.

The engineering model is:

> one persisted person/chart entity plus deterministic, lazy, read-only calculated projections.

Preserve that distinction throughout the rollout.

The first experiment should be small enough to abandon if it proves uninteresting, but architected well enough that success does not require throwing it away and rebuilding the feature from scratch.
