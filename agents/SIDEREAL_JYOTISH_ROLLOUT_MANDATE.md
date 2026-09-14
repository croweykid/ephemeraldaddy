# EphemeralDaddy Sidereal / Jyotish Rollout Mandate

## Status

This document is the implementation mandate for adding a first-class Sidereal mode and Jyotish-style divisional-chart support to EphemeralDaddy.

The architecture decision is now settled:

1. EphemeralDaddy continues to have **one person/chart identity per `chart_uid`**.
2. Tropical D1 and Sidereal D1 are two astrology-data representations linked to that same `chart_uid`.
3. **Sidereal D1 is persisted** in a dedicated sidereal table in the **same database** as the rest of EphemeralDaddy.
4. D2/D3/D7/D9/D10/D12/etc. remain deterministic projections derived from Sidereal D1 and are generated on demand rather than persisted as independent chart records.
5. Shared person/editor data remains shared between Tropical and Sidereal Chart Editor views.
6. The current Predictions system is Tropical-specific and is **hidden in Sidereal mode** for this rollout.
7. A future Sidereal Predictions system may add sidereal predictors to Traits, but that is a separate feature tier and must not be inferred from the existence of Sidereal Chart Analytics.

The early calculation/Astro Twin proof of concept is still useful, but it is no longer a decision gate for whether Sidereal D1 should be persisted. Persisted Sidereal D1 is the target architecture. The POC exists to validate mathematics, performance, similarity behavior, and integration seams before the feature spreads through the GUI.

---

## 1. Canonical Product / Identity Model

The user-facing and engineering model is:

```text
                        Chart UID
                           |
             +-------------+-------------+
             |                           |
        Person Data                  Astrology Data
   observations/tags, notes,        /              \
   photos, biography, ABC,      Tropical D1       Sidereal D1
   Material Facts, metadata                           |
                                             divisional projections
                                          D2 D3 D7 D9 D10 D12...
```

### Important EphemeralDaddy terminology

Do **not** interpret `Traits` in generic English as ordinary descriptive person data.

In EphemeralDaddy, **Traits are part of the Predictions system**. They are predicted from astrological/metaphysical properties, currently including Tropical astrology plus Human Design and BaZi predictors. Purely observed/descriptive labels belong to tags/observations and related person-data systems.

Therefore:

- Observations/tags are shared person data.
- Predictions Traits are not shared neutral person data; they belong to the current Tropical prediction framework unless/until sidereal predictors are deliberately added.

### Mandatory identity invariant

There is still only one person/chart entity and one `chart_uid`.

Do **not** create:

```text
Alice Tropical    -> UID A
Alice Sidereal    -> UID B
Alice D9          -> UID C
```

The correct model is:

```text
Alice -> UID A
         |-- Tropical D1 astrology data
         |-- Sidereal D1 astrology data
         `-- on-demand D# projections
```

Sidereal mode changes the active astrology representation. It does not convert the person into another chart identity.

---

## 2. Persistence Architecture: Same Database, Separate Sidereal Table

Sidereal D1 must be stored in a **separate logical table/domain inside the existing EphemeralDaddy database**, keyed to the same `chart_uid` as the parent chart.

Do not create a second physical database file unless a later, independently justified storage requirement demands it.

A separate physical database would add unnecessary synchronization, backup, migration ordering, orphan cleanup, transaction, failure-recovery, and UID-integrity problems. A sibling table provides the needed isolation without splitting the persistence boundary.

Conceptual schema:

```text
charts / person data
--------------------------------
chart_uid  PRIMARY KEY
birth/source data
observations / notes / tags
ABC
Material Facts
photo references
biography / metadata
...

<tropical astrology storage>
--------------------------------
chart_uid  UNIQUE / FK
existing tropical ASTRO_DATA
...

sidereal_chart_data
--------------------------------
chart_uid  PRIMARY KEY or UNIQUE FK
ayanamsha
calculation_version
source_recalculation_token
positions
retrogrades
ascendant
mc
house_cusps
house_assignments
aspects, if persisted by the chosen existing data convention
nakshatras / padas, when implemented
other canonical Sidereal D1 calculated fields
```

Exact normalization and field layout must follow the current refactor's repository/data-access conventions rather than blindly copying this sketch.

### Sidereal D1 is persisted but still derived/rebuildable

Persisting Sidereal D1 is a performance/product decision, not a claim that the data is independently authored.

Sidereal D1 remains deterministically derived from:

- source birth data;
- the chosen ayanamsha;
- the calculation implementation/version;
- applicable birth-time/rectification state.

The stored row therefore needs enough provenance/invalidation data to determine when it is stale and regenerate it safely.

The sidereal table is the durable database-wide **snapshot layer** that future Sidereal Astro Twin, research, rankings, analytics, and Sidereal Trait-predictor work can query without recomputing ~3,000 charts for every operation.

---

## 3. What Is Persisted vs. Derived On Demand

### Persist

- one parent person/chart record per `chart_uid`;
- existing Tropical D1 astrology data according to current architecture;
- one Sidereal D1 data record per chart where calculation is possible;
- provenance/invalidation metadata for that Sidereal D1 record.

### Do not persist as independent chart entities

- D2 Hora;
- D3 Drekkana;
- D7 Saptamsha;
- D9 Navamsha;
- D10 Dashamsha;
- D12 Dwadashamsha;
- other vargas.

Divisional charts are mathematical projections of the stored sidereal longitudes and should be generated on demand.

Preferred flow:

```text
stored Sidereal D1
    |
    +-> request D9
    |      -> derive D9 positions
    |      -> derive only required analytics
    |      -> display
    |      -> optionally keep in bounded memory cache
    |
    `-> request D10
           -> derive D10 independently
```

Do not eagerly generate D2 through D60 simply because Sidereal D1 exists.

### No recursive chart explosion

A D9 must never become a new persisted parent capable of generating its own persisted child records.

The database remains roughly:

```text
~3,000 chart identities
~3,000 Tropical D1 astrology records
~3,000 Sidereal D1 astrology records
```

not:

```text
~3,000 x every supported D# as chart identities
```

---

## 4. Global Astrology Mode

Add/extend the global astrology setting under:

```text
Settings > Astrology
```

Conceptually:

```text
Zodiac / Astrology mode:
(*) Tropical
( ) Sidereal

Sidereal ayanamsha:
    Lahiri
```

Lahiri is the initial sidereal standard for this rollout. Architecture must not make future alternate ayanamshas impossible, but there is no requirement to expose multiple choices immediately.

### Mode semantics

Changing Tropical/Sidereal mode selects the active astrology-data context. It must **not** rewrite, convert, or destroy the other representation.

Think:

```text
Chart UID
   |
   `-> active astrology lens
          |-- Tropical D1
          `-- Sidereal D1
```

not:

```text
"convert this chart permanently to sidereal"
```

A shared facade/context boundary should expose the active coordinate-system data so UI and analysis code does not devolve into hundreds of scattered `if sidereal:` branches.

Conceptual API:

```python
get_active_astrology_context(chart_uid)
```

or an equivalent repository/service abstraction appropriate to the refactor.

---

## 5. Three Layers Must Remain Distinct

Do not collapse the following concepts into one flag.

### Layer A: Coordinate system

Examples:

- Tropical;
- Sidereal/Lahiri;
- future alternate ayanamshas.

### Layer B: Chart projection

Examples:

- D1 Rashi;
- D2 Hora;
- D3 Drekkana;
- D7 Saptamsha;
- D9 Navamsha;
- D10 Dashamsha;
- D12 Dwadashamsha.

### Layer C: Analysis / prediction framework

Examples:

- EphemeralDaddy's existing Chart Analytics applied to Tropical coordinates;
- EphemeralDaddy's existing Chart Analytics applied to Sidereal coordinates;
- current Tropical Predictions / Trait framework;
- future Sidereal Predictions / sidereal Trait predictors;
- future Jyotish-native drishti/yoga/dasha/etc. systems.

A Sidereal D1 chart can be analyzed with existing ED prevalence/dominance/aspect machinery where mechanically valid without claiming those algorithms are canonical Jyotish.

A D9 grand trine found by ED's Western aspect engine is not automatically Jyotish `drishti`. Western dignities are not automatically Jyotish dignity rules. Keep labels honest.

---

## 6. Chart Editor Mode Matrix

The Sidereal Chart Editor is not a stripped-down unrelated window. It is a **sidereal version of the same Chart Editor experience**, backed by the same `chart_uid`, with astrology-sensitive panels switched to sidereal data and non-astral person panels shared.

### Tropical mode

```text
Chart / positions        -> Tropical
Chart Analytics          -> Tropical
Predictions              -> Tropical
Observations             -> shared person data
ABC                      -> shared person data
Material Facts           -> shared person data
Time Sensitivity         -> Tropical calculations
Photo Gallery            -> shared person data
```

### Sidereal mode

```text
Chart / positions        -> Sidereal
Chart Analytics          -> Sidereal
Predictions              -> HIDDEN for now
Observations             -> SAME shared person data
ABC                      -> SAME shared person data
Material Facts           -> SAME shared person data
Time Sensitivity         -> Sidereal calculations
Photo Gallery            -> SAME shared person data
```

### Shared-panel invariant

Observations, ABC, Material Facts, Photo Gallery, and other designated non-astral person-level panels are **not duplicated** between Tropical and Sidereal views.

Edits from either view write to the same underlying parent record and must be visible from the other view.

For example:

```text
Edit Observation in Sidereal Chart Editor
        -> writes shared chart/person data for chart_uid
        -> Tropical Chart Editor sees the same edit

Add photo in Tropical Chart Editor
        -> writes shared Photo Gallery data for chart_uid
        -> Sidereal Chart Editor sees the same photo
```

Do not create `sidereal_notes`, `sidereal_photos`, `sidereal_material_facts`, etc.

### Astronomy-derived fields remain coordinate-specific

Positions, houses, angles, aspects, prevalence, dominance, and other coordinate-derived calculations must come from the active Tropical or Sidereal D1 context.

---

## 7. Predictions Are Tropical-Only in This Rollout

The entire existing Predictions section is based on the Tropical interpretation/predictor framework.

This includes EphemeralDaddy Traits. Traits are predicted using the existing predictor system, including Tropical astrological properties and currently integrated Human Design/BaZi properties. They must **not** be presented as if they are valid Sidereal predictions merely because Sidereal positions can be calculated.

Therefore the mandate is simple:

```text
Tropical mode:
    Predictions -> visible

Sidereal mode:
    Predictions -> hidden
```

Do not grey out the panel while silently showing Tropical output under a Sidereal chart. Do not opportunistically substitute Sidereal placements into the Tropical Predictions engine and call the result validated.

### Future Sidereal Predictions / Traits

A future project may add Sidereal predictor properties to the Trait system, conceptually:

```text
Trait
|-- Tropical predictors
|-- Human Design predictors
|-- BaZi predictors
`-- Sidereal predictors        <- future
```

The persisted `sidereal_chart_data` table is specifically useful for this possibility because database-wide Trait research can quickly query the Sidereal state of every chart without rebuilding every Sidereal chart for every training/comparison operation.

A future Sidereal Trait layer may use:

- Sidereal signs;
- Sidereal houses;
- Sidereal aspects;
- Sidereal dominance/analytics properties where intentionally defined;
- Nakshatras/padas;
- later Jyotish-native properties if deliberately implemented.

That future work must establish its own predictor semantics and validation. It is **not part of the initial Sidereal-mode rollout**.

### Tags/observations remain distinct

Observed tags, observations, notes, or other descriptive labels about a person remain shared outcome/person data. Do not create fake `tropical_funny` versus `sidereal_funny` observed labels merely to compare frameworks.

This separation is valuable for later empirical testing: the same observed outcomes can be tested against Tropical predictors and Sidereal predictors independently.

---

## 8. Chart Analytics Policy

Chart Analytics remains visible in both modes and must consume the active coordinate-system context.

```text
Tropical mode -> Tropical Chart Analytics
Sidereal mode -> Sidereal Chart Analytics
```

Mechanically suitable examples include:

- sign prevalence;
- element prevalence;
- modality prevalence;
- house prevalence;
- quadrant counts / percentages;
- aspect counts;
- aspect patterns;
- dominance where the current engine can be applied coherently;
- other position/house/aspect-derived analytics.

### Semantic rule

When ED's existing Western analytics are applied to Sidereal positions, label them as **EphemeralDaddy analytics on Sidereal coordinates**, not canonical Jyotish analytics.

Do not silently rename:

- ED aspects -> Jyotish drishti;
- ED patterns -> Jyotish yogas;
- ED dominance -> canonical Jyotish strength;
- Western dignity/dispositor rules -> Jyotish dignity rules.

A future explicit analysis-framework control may exist, but it is not required for the first Sidereal rollout.

---

## 9. Time Sensitivity Policy

Time Sensitivity is available in both Chart Editor modes, but it is coordinate-aware rather than shared static output.

The underlying source facts about birth-time certainty/uncertainty are shared. The astrological consequences must be recalculated using the active coordinate system.

```text
Tropical mode
    -> Tropical Ascendant/MC/houses/etc. sensitivity

Sidereal mode
    -> Sidereal Ascendant/MC/houses/etc. sensitivity
```

Do not display a Tropical Time Sensitivity result under Sidereal mode simply because the parent birth-time metadata is shared.

This same birth-time reliability policy must be respected when deriving divisional Ascendants/houses.

---

## 10. Sidereal D1 Calculation Contract

Sidereal D1 should be exposed through a clean calculated-data contract, not a second persisted `Chart` object with another identity.

Conceptual shape:

```python
@dataclass(frozen=True)
class SiderealChartData:
    chart_uid: str
    ayanamsha: str
    positions: Mapping[str, float]
    retrogrades: Mapping[str, bool]
    ascendant: float | None
    mc: float | None
    houses: Sequence[float] | None
    aspects: Sequence[Aspect]
    nakshatras: Mapping[str, object] | None
    source_recalculation_token: str
    calculation_version: int
```

Exact fields must fit current repository/domain contracts.

### Terminology

Sidereal D1 is astrology data, not descriptive metadata. Avoid calling it chart metadata in code if that conflicts with current ASTRO_DATA classification.

---

## 11. Recalculation and Invalidation

Persisted Sidereal D1 must regenerate when any source input capable of changing it becomes stale.

Use or extend EphemeralDaddy's canonical astrology-data recalculation token rather than creating unrelated invalidation logic.

Applicable invalidators include:

- birth date;
- birth time;
- timezone / UTC resolution;
- latitude / longitude;
- timed vs. untimed status;
- rectification-related source data;
- ayanamsha;
- sidereal calculation version;
- any future source option affecting sidereal geometry.

Changing shared non-astral data must **not** trigger sidereal recomputation:

- Observations;
- ABC content;
- Material Facts;
- photos;
- tags;
- biography;
- notes;
- unrelated UI settings.

### Stale-row behavior

A sidereal row whose `source_recalculation_token` no longer matches the parent chart's current calculation inputs is stale derived data and must be rebuilt before it is treated as authoritative.

Do not trust persisted Sidereal D1 indefinitely merely because a row exists.

---

## 12. Initial Ayanamsha Policy

The initial supported sidereal calculation uses **Lahiri**.

Do not implement sidereal positions by subtracting a hardcoded value such as "about 24 degrees."

Ayanamsha is date-sensitive and must be calculated using the astronomical layer/Swiss Ephemeris facilities or another validated mathematically equivalent implementation.

Architecture should permit later alternate ayanamshas without requiring wholesale rewrites.

Conceptual context object:

```python
@dataclass(frozen=True)
class ZodiacContext:
    zodiac: Literal["tropical", "sidereal"] = "tropical"
    ayanamsha: str | None = None
```

Avoid leaking raw `sidereal=True` booleans throughout unrelated GUI/business logic.

---

## 13. Swiss Ephemeris Safety

The current astronomy stack uses `pyswisseph` / Swiss Ephemeris.

Use Swiss Ephemeris sidereal calculation and sidereal-house facilities where appropriate rather than manually shifting values without validation.

### Global-state/concurrency caveat

Swiss Ephemeris `set_sid_mode` is global library state.

Before parallel calculations, worker-thread use, or multiple ayanamshas are permitted, verify that Sidereal mode cannot race or leak into Tropical calculations.

Acceptable approaches may include:

- a lock around stateful sidereal operations;
- a tightly scoped calculation facade that sets/consumes sidereal mode atomically;
- a validated projection implementation that avoids mutable global state where mathematically equivalent.

Tests must prove that opening/calculating Sidereal charts does not mutate subsequent Tropical results.

---

## 14. Sidereal Houses and Angles Must Match Sidereal Coordinates

Never combine Sidereal planets with Tropical cusps/angles and present the result as a coherent Sidereal chart.

For Sidereal D1:

- planets are Sidereal;
- Ascendant is Sidereal;
- MC is Sidereal;
- house cusps are Sidereal;
- house assignments use those Sidereal cusps;
- coordinate-derived Chart Analytics consume the same context.

This must have explicit regression fixtures.

---

## 15. Divisional Charts Derive From Stored Sidereal D1

D2/D3/D7/D9/D10/D12/etc. should consume the canonical stored Sidereal longitudes, not rerun full astronomy unnecessarily and not scrape a rendered D1 UI.

Conceptually:

```text
parent birth data
      |
      v
persisted Sidereal D1
      |
      +-> D2
      +-> D3
      +-> D7
      +-> D9
      +-> D10
      `-> D12
```

D1 is special because it is a database-wide application mode and future research/predictor substrate. The divisional charts are lightweight projections of it.

A small bounded memory cache for recently used D# projections is acceptable if profiling supports it.

Suggested cache identity:

```python
CacheKey(
    chart_uid,
    sidereal_source_recalculation_token,
    ayanamsha,
    division,
    varga_ruleset_version,
)
```

Do not duplicate Observations, ABC, Material Facts, Photo Gallery, biography, tags, Traits, or other person/prediction data into this cache.

---

## 16. Varga Mathematics Must Be Rule-Driven

Do not assume every divisional chart is correctly implemented by a generic formula such as:

```python
degree // (30 / N)
```

Segment size is only part of the problem. Sign-assignment rules vary by varga/tradition, and some divisions have special mappings.

Use an explicit rules registry, for example:

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

Each supported division requires:

- documented tradition/rule choice;
- deterministic tests;
- all relevant source signs;
- exact segment-boundary behavior;
- values immediately below/above boundaries;
- ruleset versioning where future tradition choices could alter results.

Do not ship a generic D# calculator known to be wrong for special cases.

---

## 17. Nakshatras and Padas

Nakshatra/pada support belongs adjacent to Sidereal D1 and should be easy to add once Sidereal longitude is authoritative.

Basic geometry:

```text
27 Nakshatras
360 / 27 = 13 degrees 20 minutes each
4 padas per Nakshatra
1 pada = 3 degrees 20 minutes
```

Nakshatra/pada data should live in the Sidereal astrology domain, not be bolted into the Tropical parser.

It can be deferred from the first visible UI if necessary, but the sidereal schema/module design must not make it painful later.

---

## 18. UI Entry Points

Users should be able to access Sidereal/Jyotish views through both:

### A. Chart-level controls

A `D[#]` / Sidereal/Jyotish button/control associated with the current chart.

### B. `window_chrome`

A menu path exposing Sidereal D1 and supported divisional charts.

Both entry paths must call the same underlying service/factory.

Conceptually:

```text
D1 / D9 / D10 control
or
window_chrome -> Sidereal / Jyotish -> D1 Rashi
                                    -> D9 Navamsha
                                    -> D10 Dashamsha
                                           |
                                           v
                            open_astrology_view(chart_uid, context)
```

Do not create separate calculation implementations for buttons and menus.

The global Settings > Astrology mode is distinct from explicitly opening a D# projection: the setting changes the default D1 astrology lens, while D# commands request a specific divisional projection.

---

## 19. Chart Editor / Context Contract

The existing Chart Editor shell should be shared rather than forked wholesale.

Coordinate-aware panels should consume a chart-like astrology context rather than assuming every context is the one persisted Tropical `Chart` object.

Conceptual protocol:

```python
class AstrologyChartContext(Protocol):
    chart_uid: str
    zodiac: str
    division: str
    positions: Mapping[str, float]
    houses: Sequence[float] | None
    aspects: Sequence[Aspect]
    retrogrades: Mapping[str, bool]
    use_birth_time_data: bool
```

Potential providers:

```text
TropicalD1Context
SiderealD1Context
VargaChartView
HypotheticalChartContext
```

This does **not** mean person-level panels become duplicated context data. They should continue to address the underlying `chart_uid` and shared person repositories.

### Coordinate editing

Sidereal D1 and D# positions are derived from parent birth data and must not be independently drag-edited into incoherence.

If EphemeralDaddy eventually offers an explicit "Create hypothetical from this view" action, that is a separate new chart workflow, not ordinary Sidereal editing.

---

## 20. Divisional-Chart Window Behavior

Divisional charts are nested alternate chart views, not persisted people.

They may reuse the Sidereal Chart Editor shell, but their astrology coordinates are read-only projections.

If shared person-level panels are displayed in a D# view, they must still point to the same parent `chart_uid` and must never become D#-specific copies.

The initial D# surface should prioritize:

- chart visualization;
- projected positions;
- valid angles/houses where methodology and birth-time quality support them;
- Chart Analytics where the chosen ED algorithms are mechanically meaningful;
- explicit Sidereal/Lahiri/D# labeling.

Current Tropical Predictions remain unavailable in D# views.

---

## 21. Birth-Time Quality and Untimed Charts

Divisional angles can be more birth-time-sensitive than ordinary D1 planetary placements.

For example, D9 divides each 30-degree sign into 3 degree 20 minute sections, so modest Ascendant movement near a boundary can change Navamsha Lagna.

Respect existing ED timing-quality rules.

Recommended behavior:

```text
Reliable known birth time
    -> Sidereal/D# planetary positions
    -> Sidereal/D# Ascendant when methodology supports it
    -> houses when methodology supports them

Unknown / unusable birth time
    -> planetary Sidereal/D# positions may remain available
    -> angles unavailable
    -> houses unavailable

Rectified / uncertain range
    -> do not present a fragile single D# Lagna as certain
```

The Time Sensitivity panel should make such instability inspectable rather than hiding it.

---

## 22. Performance Mandate

The main risk is not the arithmetic. It is accidentally making every Sidereal or D# request trigger the entire application graph.

Avoid:

```text
open D9
 -> construct another full persisted Chart
 -> duplicate person data
 -> calculate every analysis
 -> run Tropical Predictions
 -> update rankings
 -> update Trait indexes
 -> write database child record
 -> refresh unrelated windows
```

### Rule 1: Sidereal D1 is persisted once, refreshed only when stale

Normal use should read the stored Sidereal D1 row rather than recalculate it on every panel access.

### Rule 2: D# projections are lazy

Opening D9 calculates D9. It must not precompute D2-D8 or all traditional vargas.

### Rule 3: Analyses are lazy

Only derive analytics needed by visible panels or explicit research operations.

### Rule 4: Shared panels do not duplicate storage

Observations/ABC/Material Facts/Photo Gallery are read/written through their existing shared parent repositories.

### Rule 5: Derived views do not pollute person indexes

D9 etc. do not become extra rows in chart lists, normal database chart counts, relationship graphs, backups, person search, or ordinary rankings as separate people.

### Rule 6: Add query/index optimization only where measurement supports it

The Sidereal table should be queryable efficiently, but do not serialize an enormous precomputed "every possible Sidereal research property" blob merely because future research may use it.

Add derived/indexed research representations intentionally if profiling shows database-wide Sidereal queries need them.

---

## 23. Future Sidereal Trait / Research Architecture

Persisted Sidereal D1 enables a future predictor layer without another chart corpus.

Example research flow:

```text
Trait being modeled
    |
charts carrying relevant training/outcome labels
    |
join by chart_uid
    |
sidereal_chart_data
    |
search recurring Sidereal properties
```

The sidereal table itself is the snapshot of each chart's Sidereal state.

There is no need to persist another "Sidereal Trait chart" for each person merely to determine whether database charts match Sidereal properties.

If performance later requires a compact feature vector/index, derive it from `sidereal_chart_data` and version/invalidate it independently.

### Controlled framework comparison

Keeping shared observed person outcomes separate from astrology-specific predictors creates a useful testbed:

```text
same people
same observations/tags/outcomes
same chart_uid set

Tropical predictors  vs.  Sidereal predictors
```

This allows future research to test whether Sidereal properties add signal rather than changing the labels to fit the framework.

---

## 24. Astro Twin Experimental Program

The Astro Twin experiment remains a useful early research/validation surface.

Once Sidereal D1 records exist, comparisons can operate directly from persisted Sidereal vectors instead of recalculating all D1s every run.

Support at least these conceptual modes:

### A. Sidereal D1 -> Sidereal D1

Baseline Sidereal Astro Twin.

### B. D9 -> D9

Derive subject D9 and comparison D9s from stored Sidereal D1 records.

Question:

> Who has a Navamsha most structurally similar to this person's Navamsha?

### C. D9 -> Sidereal D1

Compare a subject's derived D9 against comparison charts' **Sidereal D1**, never Tropical D1.

Question:

> Whose ordinary Sidereal natal structure most resembles this person's Navamsha?

### Coordinate consistency

Do not compare:

```text
Alice D9 Sidereal
vs.
Bob Tropical D1
```

and treat the result as a clean same-coordinate comparison.

### Reuse current Astro Twin logic

Before implementation, inspect the production Astro Twin similarity metric, feature vector, filters, weights, and ranking behavior on the active branch. Do not reconstruct an assumed algorithm from memory.

If Astro Twin is tightly coupled to persisted Tropical `Chart` objects, refactor the comparison seam to accept an astrology context/vector rather than creating fake D# chart rows.

---

## 25. Astro Twin Statistical Controls

A ~3,000-chart database will always produce a nearest neighbor. A striking match is not evidence by itself.

D9 is also mathematically derived from D1 and therefore not independent of natal structure.

Recommended evaluation:

1. Choose a subject.
2. Calculate the best astrology-only D9->D1 or D9->D9 match before inspecting held-out outcomes.
3. Evaluate held-out person-level data after the match is fixed.
4. Compare with Tropical D1->D1 and Sidereal D1->D1 baselines.
5. Compare against random controls.
6. Compare against shuffled/permuted D9 assignments or another null model.
7. Repeat across enough subjects to avoid anecdotal cherry-picking.

Held-out evaluation may use appropriate existing person-level labels/metadata that were not consumed by the astrology similarity metric.

The POC is informative even though Sidereal D1 persistence is already mandated: it helps determine whether deeper varga product investment and Sidereal predictor research are worthwhile.

---

## 26. Export Rules

Exports must identify their astrology context.

Sidereal/divisional exports should be capable of recording:

- parent `chart_uid` / identity reference;
- Tropical vs. Sidereal;
- ayanamsha;
- division (`D1`, `D9`, etc.);
- analysis framework where relevant;
- calculation/ruleset version when required for reproducibility.

Do not export a D9 analytics result in a form indistinguishable from the parent's Tropical analytics.

Shared person data included in exports remains parent-chart data, not copied D# ownership.

---

## 27. Proposed Core Modules

Prefer isolated calculation/domain modules rather than scattering Sidereal branches through the GUI.

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

- zodiac/ayanamsha context;
- Lahiri D1 calculation;
- Sidereal angles/houses facade;
- Nakshatra/pada derivation;
- calculation provenance/token support;
- no GUI responsibilities.

### `vargas.py`

Responsibilities may include:

- explicit varga rule registry;
- pure longitude-to-varga transforms;
- division names/metadata;
- ruleset versioning;
- boundary-safe tests;
- no person-data writes;
- no GUI responsibilities.

### Persistence/repository layer

Use the existing refactor's repository/data-access pattern for:

- `sidereal_chart_data` reads/writes;
- stale-record detection;
- batch creation/backfill;
- parent deletion cleanup;
- migrations.

Do not make calculation modules directly own SQLite/DB writes if current architecture already separates those concerns.

---

## 28. Migration / Backfill Logistics

Because Sidereal D1 is now a persistent first-class data domain, production rollout requires a schema migration/backfill plan.

### Migration requirements

- create the Sidereal D1 table/domain;
- key each row by existing `chart_uid`;
- enforce one Sidereal D1 row per chart per supported persisted context (initially Lahiri);
- preserve parent deletion/integrity behavior;
- ensure backups include the Sidereal table;
- ensure restoring old databases can create/backfill the missing Sidereal table safely.

### Backfill requirements

Existing ~3,000 charts will need Sidereal D1 data.

Do not make application startup recalculate all charts synchronously every time.

Choose an explicit one-time/lazy migration strategy consistent with current ED migration conventions. Acceptable patterns include:

- one-time background/batched backfill with progress;
- migration-time batch generation if measured fast and safe;
- lazy per-chart generation plus a deliberate database-wide backfill command for research readiness.

Whatever strategy is selected must be resumable/idempotent enough that interruption does not corrupt parent charts or duplicate rows.

The Sidereal table should record calculation version/token so future algorithm updates can invalidate/backfill safely.

---

## 29. Refresh and State Isolation

Refresh logic must respect both the shared parent identity and separate astrology contexts.

Examples:

- editing birth data invalidates both affected Tropical derived data and the Sidereal D1 row;
- editing an Observation updates both open Chart Editor modes immediately/at normal shared-data refresh boundaries without recalculating astrology;
- adding/removing a Photo Gallery item is visible in both modes without recalculating Sidereal data;
- switching Tropical -> Sidereal swaps Chart Analytics and Time Sensitivity to Sidereal context;
- switching Sidereal -> Tropical restores Tropical context;
- Sidereal refresh must not overwrite Tropical ASTRO_DATA;
- D9 refresh must not write D9 as a new chart row;
- opening/closing a D# view must not change the database person count;
- a stale Sidereal row must be rebuilt before being used for analysis/research.

Prefer immutable calculated Sidereal/D# data objects where practical.

---

## 30. Relationship to Human Design and BaZi

Human Design and BaZi demonstrate that one person/chart record can support multiple metaphysical systems.

They do **not** justify flattening every future system into hundreds of fields on the parent `Chart` object.

Do not add:

```text
d2_positions
d3_positions
d9_positions
d10_positions
...
```

to every persisted parent chart.

Likewise, do not treat existing Tropical Traits as automatically Sidereal simply because Traits already accept HD/BaZi predictors.

A future Sidereal predictor family should be explicit and data-driven.

---

## 31. Relationship to Draconic Support

Draconic calculation is a useful precedent for alternate coordinate projections from canonical chart data.

Reuse the architectural lesson that transformed coordinates should have a clean projection boundary.

Do not force Sidereal/varga logic through Draconic code if the astronomy, houses, persistence, caching, or context requirements differ.

Sidereal D1 is more substantial than a purely transient projection because it is now a persisted application-wide coordinate representation and future research substrate.

---

## 32. POC / Rollout Phases

### Phase 0 — Inspection and contracts

Before broad code changes:

- inspect current `Chart`, ASTRO_DATA, repository, and migration ownership on `oh-lawdy-we-still-refactoring!`;
- inspect current ephemeris/house seams;
- inspect Chart Editor panel dependencies;
- inspect Settings > Astrology flow;
- inspect current Astro Twin implementation;
- locate code that assumes all astrology data is Tropical;
- locate code that assumes every chart-like object is a persisted person;
- document Swiss Ephemeris Sidereal global-state handling;
- select authoritative D9 test vectors/rule references.

### Phase 1 — Pure calculation POC

Implement/test production-quality primitives for:

- Lahiri Sidereal D1;
- Sidereal houses/angles where timed data is valid;
- D9 from Sidereal longitudes;
- calculation provenance/tokening;
- external-reference fixtures.

This phase may operate in memory while mathematics is being verified.

### Phase 2 — Persisted Sidereal D1

Implement:

- Sidereal table migration;
- `chart_uid` linkage;
- stale-row detection;
- write/read repository/service;
- initial backfill strategy;
- Lahiri context/version metadata.

This is the target architecture, not an optional optimization.

### Phase 3 — Sidereal Chart Editor mode

Wire the shared Chart Editor shell so Sidereal mode provides:

- Sidereal chart visualization/positions;
- Sidereal Chart Analytics;
- shared Observations;
- shared ABC;
- shared Material Facts;
- Sidereal Time Sensitivity;
- shared Photo Gallery;
- **no Predictions panel**.

Verify edits to shared panels propagate across both modes because they address the same `chart_uid`.

### Phase 4 — Global Settings mode

Expose/complete:

```text
Settings > Astrology > Tropical / Sidereal
```

and ensure coordinate-aware surfaces use the active context without mutating the other representation.

### Phase 5 — Astro Twin / research validation

Implement/reuse:

- Sidereal D1->D1;
- D9->D9;
- D9->Sidereal D1;
- baseline/random/shuffled controls;
- batch performance measurements.

### Phase 6 — Additional vargas

Add tested divisions one at a time, likely beginning with:

```text
D2
D3
D7
D10
D12
```

Do not bulk-enable every varga through an unvalidated generic mapper.

### Phase 7 — Future Sidereal Predictions, only if deliberately approved

Possible future work:

- Sidereal predictor properties for Traits;
- dedicated Sidereal Predictions UI;
- Sidereal research indexes/feature vectors;
- Nakshatra-based predictor support;
- explicit interaction with HD/BaZi predictor families.

This requires a separate design/validation decision.

### Phase 8 — Jyotish-native systems, only if warranted

Potential future systems include:

- drishti;
- yogas;
- dashas;
- Jyotish dignity/strength rules;
- varga dignity/strength;
- Shadbala;
- Ashtakavarga;
- functional benefic/malefic logic;
- other tradition-specific interpretation layers.

These are not prerequisites for Sidereal D1 or basic divisional-chart support.

---

## 33. Testing Mandate

### Sidereal astronomy tests

Verify against trusted external/reference charts for multiple dates and locations.

Test:

- dates far apart enough to exercise ayanamsha drift;
- sign-boundary cases;
- retrograde bodies;
- Ascendant/MC;
- house cusps;
- timed/untimed charts;
- timezone/UTC conversion behavior;
- Lahiri provenance/versioning.

### Varga tests

For every supported D#:

- all relevant source signs;
- every segment transition;
- exact boundary behavior;
- values immediately below/above boundaries;
- wraparound at 0/360;
- known reference examples;
- explicit floating-point tolerances.

### Persistence tests

Verify:

- one Sidereal row per intended `chart_uid`/context;
- parent deletion does not orphan corrupt data;
- birth-data changes invalidate stale Sidereal rows;
- shared-person edits do not invalidate Sidereal rows;
- migrations are idempotent/resumable as designed;
- backup/restore includes Sidereal data;
- old databases upgrade safely.

### Tropical regression tests

When Tropical mode is active, existing Tropical calculations and Predictions must remain equivalent to pre-feature behavior.

Opening/calculating Sidereal data must not leak Swiss Ephemeris state into later Tropical results.

### Chart Editor UI tests

Tropical mode must show:

- Tropical Chart Analytics;
- Tropical Predictions;
- Observations;
- ABC;
- Material Facts;
- Tropical Time Sensitivity;
- Photo Gallery.

Sidereal mode must show:

- Sidereal Chart Analytics;
- Observations;
- ABC;
- Material Facts;
- Sidereal Time Sensitivity;
- Photo Gallery;
- **no Predictions panel**.

Verify shared-panel edits from either mode are visible in the other mode.

Verify Sidereal Chart Analytics/Time Sensitivity never display stale Tropical results.

### Divisional UI tests

Verify:

- D# views identify Sidereal/Lahiri/division clearly;
- derived coordinates are not independently editable;
- untimed restrictions are honored;
- changing D# refreshes analytics to the new projection;
- D# views never create person rows/UIDs;
- shared panels, if displayed, still edit the parent `chart_uid`.

### Performance tests

Measure:

- single-chart Sidereal D1 calculation;
- single Sidereal D1 database read;
- initial ~3,000-chart backfill;
- D9 derivation;
- batch D9 derivation where research requires it;
- Sidereal Astro Twin runtime;
- memory footprint of batch research;
- Tropical/Sidereal mode-switch latency;
- Chart Editor open/refresh latency.

Use measurements before adding additional denormalized/indexed research storage.

---

## 34. Explicitly Rejected Approaches

Unless this mandate is deliberately revised, do **not**:

- create a second physical database merely for Sidereal data;
- create a second person/chart UID for Sidereal D1;
- create persisted chart entities for every varga;
- duplicate Observations between Tropical/Sidereal views;
- duplicate ABC data between Tropical/Sidereal views;
- duplicate Material Facts between Tropical/Sidereal views;
- duplicate Photo Gallery data between Tropical/Sidereal views;
- call observed tags "Traits" in implementation/design discussion;
- show the existing Tropical Predictions/Traits panel in Sidereal mode;
- silently feed Sidereal placements into Tropical Predictions and call it Sidereal prediction;
- treat current Tropical Trait predictors as coordinate-neutral;
- eagerly calculate all vargas for all charts at startup;
- hardcode a constant ayanamsha shift;
- mix Tropical houses/angles with Sidereal planets;
- assume every varga uses one generic mapping formula;
- label ED Western analytics as canonical Jyotish analytics;
- compare D9 Sidereal against Tropical D1 as a same-coordinate Astro Twin experiment;
- include D# projections in normal person counts/search/relationship graphs as extra people;
- allow D# coordinates to become independently editable;
- permit Swiss Ephemeris Sidereal global state to contaminate Tropical calculations;
- fork an entirely separate Chart Editor when shared shell/context routing is sufficient;
- block basic Sidereal support on implementing the full Jyotish tradition.

---

## 35. Decision Gates

### Gate A — Calculation correctness

Lahiri D1 and D9 must agree with trusted references before broad UI exposure.

### Gate B — Persistence/invalidation correctness

The Sidereal table must remain synchronized to source birth data through deterministic invalidation, without creating duplicate person identities.

### Gate C — UI/context isolation

Tropical and Sidereal Chart Editor modes must use the correct astrology context while sharing designated person panels safely.

### Gate D — Performance

Backfill, database reads, mode switching, D# derivation, and research workloads must be measured and acceptable at the current database scale.

### Gate E — Varga research signal

Astro Twin experiments should determine whether deeper divisional-chart investment produces stable structure beyond nearest-neighbor inevitability.

This gate affects deeper varga/research investment, **not** whether Sidereal D1 exists.

### Gate F — Sidereal Predictions methodology

No Sidereal Predictions panel is released until Sidereal-specific predictor semantics, Trait integration, training/query behavior, and validation are deliberately designed.

---

## 36. Definition of Initial Success

The initial rollout is successful when all of the following are true:

1. Every parent chart can own at most one current Lahiri Sidereal D1 record keyed to the same `chart_uid`.
2. Sidereal D1 is stored in the same database in a separate logical table/domain.
3. Existing Tropical D1 behavior remains unchanged.
4. Settings > Astrology can select Tropical or Sidereal without mutating the other representation.
5. Tropical Chart Editor shows Tropical Chart Analytics and Tropical Predictions.
6. Sidereal Chart Editor shows Sidereal Chart Analytics and hides Predictions.
7. Observations are shared across Tropical and Sidereal views.
8. ABC is shared across Tropical and Sidereal views.
9. Material Facts are shared across Tropical and Sidereal views.
10. Photo Gallery is shared across Tropical and Sidereal views.
11. Time Sensitivity uses the active Tropical/Sidereal coordinate context.
12. Edits in shared panels from either Chart Editor mode affect the same parent data and appear in both modes.
13. D9 can be generated from stored Sidereal D1 without creating another chart UID/row.
14. Supported D# views are read-only with respect to derived coordinates.
15. Birth-time/untimed behavior remains coherent.
16. Sidereal storage invalidates/rebuilds correctly when source birth data changes.
17. Astro Twin research can compare Sidereal D1/D1, D9/D9, and D9/Sidereal-D1 without duplicating person records.
18. Current Tropical Traits remain correctly understood as Predictions-system outputs/predictors rather than generic observed labels.
19. The architecture leaves a clean future path for Sidereal Trait predictors without requiring another duplicated chart corpus.
20. The code clearly distinguishes person data, coordinate system, chart division, analytics framework, and prediction framework.

---

## 37. Final Architectural Rule

The product metaphor is:

> One person has multiple astrological representations.

The persistence model is:

> One `chart_uid`, shared person data, one Tropical D1 astrology domain, one persisted Sidereal D1 astrology domain, and lazy divisional projections derived from Sidereal D1.

The Chart Editor rule is:

> Non-astral person panels are shared; coordinate-sensitive panels follow the active Tropical/Sidereal context; current Predictions remain Tropical-only.

The future-prediction rule is:

> Sidereal Predictions, if added, gain explicit Sidereal predictors rather than pretending the existing Tropical Trait model is coordinate-neutral.

Preserve those boundaries throughout implementation.