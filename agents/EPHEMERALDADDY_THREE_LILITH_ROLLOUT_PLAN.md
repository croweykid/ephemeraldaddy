# EphemeralDaddy Three-Lilith Canonicalization & Full-App Rollout Plan

**Repository:** `croweykid/ephemeraldaddy`  
**Foundation branch:** `feature/three-lilith-foundation`  
**Foundation commits already present:**
- `c2023a677c7a90186ebe7399eca56016705fca56` — add canonical Lilith identity compatibility contract
- `7cc623df9ef71f9f1b7bd99459a21c77fdcf3c74` — test permanent legacy Lilith semantic aliases

**Codex instruction:** `main` advanced after the foundation branch was created. At handoff time, `feature/three-lilith-foundation` is 2 commits ahead and 4 commits behind current `main`. Prefer creating the rollout branch from current `main` and cherry-picking the two foundation commits above (or rebase the foundation branch first). Do not partially activate the new semantic alias layer while the runtime still emits only the old single `Lilith` body. The alias integration and three-body ephemeris output must land atomically.

---

## 1. Mission

Replace EphemeralDaddy's current **single, mode-switched Lilith slot** with **three simultaneously calculated, permanently distinct canonical bodies** throughout the entire application:

1. `Mean Lilith`
2. `Osculating Lilith`
3. `Natural Lilith`

The finished application must compute, store, reload, draw, interpret, aspect, score, compare, analyze, transit, export, import, cache, and generate norms for all three as separate bodies.

There must no longer be a runtime choice where "Lilith" means one calculation today and another calculation tomorrow.

### Definition of done

A newly calculated chart must contain all three canonical keys in every relevant derived-data structure. No newly generated position, retrograde, aspect endpoint, research feature, or export may use plain `"Lilith"` as the body identity.

Legacy **semantic references** to `"Lilith"` and `"True Lilith"` must continue to work and must mean `Osculating Lilith`.

Legacy **stored coordinates** named `"Lilith"` must **not** be trusted as Osculating coordinates. They must be discarded as ambiguous and recalculated from the chart's astronomical inputs, generating all three canonical Lilith positions.

---

## 2. Canonical identity contract — immutable

Use the foundation module already committed:

`ephemeraldaddy/core/body_identity.py`

Canonical constants:

```python
MEAN_LILITH = "Mean Lilith"
OSCULATING_LILITH = "Osculating Lilith"
NATURAL_LILITH = "Natural Lilith"

CANONICAL_LILITH_BODIES = frozenset({
    MEAN_LILITH,
    OSCULATING_LILITH,
    NATURAL_LILITH,
})
```

### Permanent semantic aliases

These are product decisions, not transitional heuristics:

```text
"Lilith"      -> "Osculating Lilith"
"True Lilith" -> "Osculating Lilith"
```

Case-insensitive forms should normalize identically.

Also normalize semantically explicit historical forms when found during the repo audit, for example:

```text
"Lilith (true)"        -> "Osculating Lilith"
"Lilith (osculating)"  -> "Osculating Lilith"
"Lilith (mean)"        -> "Mean Lilith"
```

Only add aliases whose semantics are explicit.

### Do NOT globally alias `"Black Moon Lilith"`

The phrase `"Black Moon Lilith"` is historically ambiguous and the current application has used it as a display name produced by a calculation mode. Do not assign it globally to Mean, Osculating, or Natural without provenance.

If a serialized semantic object contains `"Black Moon Lilith"` plus metadata that explicitly identifies its calculation method, migrate it from that provenance. Otherwise preserve/flag it as ambiguous rather than guessing.

### Semantic identity is not coordinate provenance

This distinction is mandatory:

- A **Trait criterion** saying `"Lilith in H7"` is a semantic reference. It means `Osculating Lilith`.
- A **stored chart position** such as `positions["Lilith"] = 214.22` is an old derived coordinate. It does **not** prove which Lilith algorithm produced `214.22`.

Never implement migration by mechanically renaming:

```python
positions["Lilith"] -> positions["Osculating Lilith"]
```

That can silently turn a Mean coordinate into an Osculating identity.

Old ambiguous Lilith coordinates must be recalculated.

---

## 3. Swiss Ephemeris mappings — fixed technical contract

Use three distinct Swiss Ephemeris body IDs:

| EphemeralDaddy canonical name | Swiss Ephemeris definition | Swiss ID |
|---|---|---:|
| `Mean Lilith` | Mean lunar apogee | `SE_MEAN_APOG` / `MEAN_APOG` | 12 |
| `Osculating Lilith` | Osculating lunar apogee, historically "True Lilith" | `SE_OSCU_APOG` / `OSCU_APOG` | 13 |
| `Natural Lilith` | Interpolated lunar apogee, also called Natural Apogee | `SE_INTP_APOG` / `INTP_APOG` | 21 |

Primary reference: Swiss Ephemeris programming interface and Astrodienst's Lilith/apogee documentation.

Useful authoritative references:
- https://www.astro.com/swisseph/swephprg.htm
- https://www.astro.com/swisseph/swisseph.htm
- https://www.astro.com/swisseph/hyplistn.htm

### Critical rule: no cross-method fallback

The current one-body implementation can fall back from the requested "True" apogee to the Mean apogee if the preferred Swiss alias is unavailable. That behavior becomes invalid once the three calculations are separate identities.

After this refactor:

- If `Osculating Lilith` cannot be calculated, **do not substitute Mean Lilith**.
- If `Natural Lilith` cannot be calculated, **do not substitute Mean or Osculating Lilith**.
- If `Mean Lilith` cannot be calculated, **do not substitute another method**.

Return `None`, an explicit unavailable result, or raise/report through the application's normal calculation-availability mechanism. Log which exact canonical body could not be calculated.

Three names that sometimes contain the same fallback longitude are worse than one missing value because the application would treat fabricated duplicates as independent research variables.

---

## 4. Current architecture that must be retired

At the time this plan was written, `ephemeraldaddy/core/ephemeris.py` uses a single runtime slot:

- `LILITH_CALCULATION_MEAN = "mean"`
- `LILITH_CALCULATION_TRUE = "true"`
- process-global `_LILITH_CALCULATION_MODE`
- `set_lilith_calculation_mode(...)`
- `get_lilith_calculation_mode()`
- `get_lilith_display_name(...)`
- a helper that chooses Mean vs Osculating Swiss IDs
- `planetary_positions()` emits only `results["Lilith"]`
- `planetary_retrogrades()` emits only `"Lilith"`

`ephemeraldaddy/core/interpretations.py` currently also has single-body assumptions including:

- `BLACK_MOON_LILITH = {"Lilith"}`
- one `NATAL_WEIGHT["Lilith"]`
- one `BODY_SIGN_DURATION_DAYS["Lilith"]`
- one `PLANET_ORDER` entry
- one glyph/color entry
- one `PLANET_KEYWORDS["Lilith"]`
- one Lilith body-definition entry
- a special-case `"Lilith (mean)" -> "Lilith"` duration normalization

`ephemeraldaddy/analysis/weighted_chart_predictor.py` currently contains a local duplicate alias table that normalizes both:

```python
"true lilith" -> "Lilith"
"lilith"      -> "Lilith"
```

`ephemeraldaddy/analysis/traits.py` contains actual existing Trait criteria using `"True Lilith"`.

`ephemeraldaddy/core/chart_data_fields.py` currently treats `lilith_calculation_mode` as an ASTRO_DATA input.

All of those assumptions must be removed or converted.

---

## 5. Required repo-wide discovery pass before editing

Do not assume the files named in this plan are exhaustive. `app.py` is large and several research/export paths have historically carried their own local body lists.

Run a literal search first and keep the result list as an implementation checklist:

```bash
rg -n \
  '"Lilith"|'\''Lilith'\''|True\ Lilith|Black\ Moon\ Lilith|Lilith\ \(mean\)|Lilith\ \(true\)|Lilith\ \(osculating\)|lilith_calculation_mode|LILITH_CALCULATION|_LILITH_|BLACK_MOON_LILITH|SE_MEAN_APOG|SE_OSCU_APOG|INTP_APOG|PLANET_ORDER|BODY_ALIASES|⚸' \
  ephemeraldaddy tests
```

Then do a second structural pass for places likely to contain implicit allowlists or body-order assumptions:

```bash
rg -n \
  'planetary_positions|planetary_retrogrades|positions|retrogrades|find_aspects|compute_aspects|NATAL_WEIGHT|POSITION_WEIGHTS|TRANSIT_WEIGHT|NATAL_BODY_LOUDNESS|BODY_SIGN_DURATION_DAYS|PLANET_GLYPHS|required.*bod|body.*list|body.*order|export|serializer|deserialize|dropdown|combo|selector|filter|norm|similarit|analytics|cache|signature|schema_version' \
  ephemeraldaddy tests
```

Do not stop after updating every literal `"Lilith"` occurrence. Audit generic loops that may silently filter through a fixed body allowlist.

---

## 6. Core ephemeris refactor

### 6.1 Replace calculation mode with canonical ID mapping

Refactor the single mode helper into something conceptually equivalent to:

```python
LILITH_SWISS_ID_CANDIDATES = {
    MEAN_LILITH: (
        "SE_MEAN_APOG",
        "MEAN_APOG",
        "MEAN_APOGEE",
    ),
    OSCULATING_LILITH: (
        "SE_OSCU_APOG",
        "OSCU_APOG",
        "OSCU_APOGEE",
    ),
    NATURAL_LILITH: (
        "SE_INTP_APOG",
        "INTP_APOG",
        "INTP_APOGEE",
    ),
}
```

The exact aliases should match what the installed `pyswisseph` build actually exposes. Test them explicitly.

### 6.2 `planetary_longitude()`

It must accept all three canonical names directly.

Semantic aliases may be normalized at a **semantic API boundary**, but the low-level coordinate routine should prefer canonical identities and should never return a different algorithm as fallback.

Examples:

```text
planetary_longitude(dt, "Mean Lilith")
planetary_longitude(dt, "Osculating Lilith")
planetary_longitude(dt, "Natural Lilith")
```

All three must resolve to their own Swiss body ID.

### 6.3 `planetary_positions()`

Always attempt all three calculations.

New output:

```python
{
    ...
    "Mean Lilith": ...,
    "Osculating Lilith": ...,
    "Natural Lilith": ...,
}
```

Do not emit:

```python
"Lilith"
"True Lilith"
"Black Moon Lilith"
```

as position keys for newly calculated charts.

### 6.4 `planetary_retrogrades()` and speed

Calculate each body independently from its own Swiss ID and instantaneous longitude speed.

New output must contain separate booleans/records:

```python
"Mean Lilith"
"Osculating Lilith"
"Natural Lilith"
```

If the application exposes raw speed anywhere, it must likewise keep all three separate.

### 6.5 Availability checks

Replace a single `lilith_mode_available()` concept with canonical-body availability, such as:

```python
lilith_body_available(MEAN_LILITH)
lilith_body_available(OSCULATING_LILITH)
lilith_body_available(NATURAL_LILITH)
```

Availability of one is not availability of another.

### 6.6 Ephemeris preparation

Audit any "required bodies" preload lists and Swiss data readiness checks. The three apogees generally do not need asteroid orbital files, but the application must not accidentally exclude them because only one old Lilith slot was expected.

### 6.7 Range behavior

The app's supported natal/transit date range should be tested against all three methods. If a method becomes unavailable at a supported date boundary, surface that as a specific unsupported calculation instead of cross-falling back.

---

## 7. Retire the global Lilith calculation setting

The application should no longer ask the user to choose one Lilith calculation. All three are first-class bodies and should always be computed.

### Settings work

Find every UI/control/help string for:

- Mean Lilith
- True Lilith
- Lilith calculation
- osculating/oscillating wording
- `lilith_calculation_mode`

Remove or replace the selector that controls chart calculation.

If explanatory Settings text is retained, it should explain that EphemeralDaddy now tracks three lunar-apogee calculations independently.

Use the canonical spelling **Osculating Lilith**.

### Persisted preference compatibility

Existing preference values such as:

```text
lilith_calculation_mode = mean
lilith_calculation_mode = true
```

may still be read long enough to prevent old settings files from failing to load, but they must no longer control calculation output.

They can be:

- ignored after migration,
- retained temporarily as legacy metadata/provenance,
- later removed by a settings-schema cleanup.

### `chart_data_fields.py`

`lilith_calculation_mode` should ultimately stop being an `ASTRO_DATA_INPUT_FIELD`, because it no longer changes the astronomical result set.

Do this only after the compatibility/migration loader can tolerate old persisted values.

### Calculation signatures

Any cache or derived-data signature that historically incorporated `lilith_calculation_mode` must be replaced with a **body/calculation schema version** indicating the new three-Lilith model.

---

## 8. Central body registry sweep

The goal is three independent identities everywhere, not one family-level "Lilith" value.

Where possible, consolidate duplicated lists into central constants rather than adding three strings to twenty unrelated local arrays.

### Required registries to audit

At minimum:

- `PLANET_ORDER`
- `NATAL_WEIGHT`
- `POSITION_WEIGHTS`
- `BLACK_MOON_LILITH` or its replacement
- slow/minor/transit body sets
- `TRANSIT_WEIGHT`
- `NATAL_BODY_LOUDNESS`
- `BODY_SIGN_DURATION_DAYS`
- glyph dictionaries
- color dictionaries
- body labels
- chart drawing order
- selectable-body arrays
- required-body arrays
- tooltip registries
- research-factor registries
- aspect endpoint filters
- interpretation/body metadata registries
- serializers/export order
- import validators
- any "known bodies" validation set

### Replace the family set

Prefer a canonical name such as:

```python
LILITH_BODIES = CANONICAL_LILITH_BODIES
```

If `BLACK_MOON_LILITH` must remain temporarily for API compatibility, make it refer to the canonical three-body set, not `{"Lilith"}`.

### Ordering

Keep the three contiguous everywhere a deterministic order is needed:

```text
Mean Lilith
Osculating Lilith
Natural Lilith
```

unless an existing UI has a stronger semantic reason for another order.

---

## 9. Weighting contract

Treat the three Liliths exactly as three separate body identities.

There is **no family cap**, no shared pool, and no aggregation back into a single Lilith score.

Create three independent entries anywhere body weighting applies, for example:

```python
NATAL_WEIGHT = {
    ...
    "Mean Lilith": <explicit value>,
    "Osculating Lilith": <explicit value>,
    "Natural Lilith": <explicit value>,
}
```

The values are independently configurable. They may be numerically equal if that is the chosen configuration, but they are never the same variable.

For backward continuity, the old single Lilith value must not be accidentally applied as a combined family score.

Audit separately:

- natal dominance weight
- aspect-pair body weight
- transit priority weight, if Lilith transits participate
- natal-body loudness, if used in transit priority
- any Similarities-specific factor weight
- any analytics/prediction weighting

Do not silently default new canonical bodies to generic body weight `1` because a lookup was missed.

---

## 10. Semantic alias integration

The foundation module already defines:

```python
canonicalize_semantic_body_name(...)
```

Make it the single source of truth for legacy Lilith identity references.

### `interpretations.normalize_body_name()`

Integrate:

1. angle alias normalization (`ASC -> AS`, etc.)
2. canonical semantic body normalization
3. any other existing canonical aliases

Do not create a second Lilith alias table in this module.

### `weighted_chart_predictor.py`

Delete the local collapsing behavior:

```python
"true lilith": "Lilith"
"lilith": "Lilith"
```

and route semantic body normalization through the central helper.

Existing Traits containing `"True Lilith"` must then target `Osculating Lilith`.

Existing Traits containing plain `"Lilith"` must also target `Osculating Lilith`.

### Compound criterion parsing

Audit parsers for strings such as:

```text
Lilith in H7
True Lilith in Scorpio
Sun square Lilith
Ceres square True Lilith
Part of Fortune trine True Lilith
```

The parser must normalize the body token/endpoint, not just compare the raw entire string.

Examples after normalization:

```text
Lilith in H7                 -> Osculating Lilith in H7
True Lilith in H10           -> Osculating Lilith in H10
Ceres square True Lilith     -> Ceres square Osculating Lilith
Sun square Lilith            -> Sun square Osculating Lilith
```

### Trait storage

It is acceptable for a legacy user-authored Trait JSON file to retain the old wording on disk until that Trait is rewritten/saved, provided runtime scoring canonicalizes it correctly.

If Traits are rewritten during migration, write canonical body names.

Do not rewrite coordinate data using this semantic alias function.

---

## 11. Interpretations and descriptions

Create physically separate dictionary keys immediately.

### `PLANET_KEYWORDS`

Required:

```python
PLANET_KEYWORDS["Mean Lilith"] = ...
PLANET_KEYWORDS["Osculating Lilith"] = ...
PLANET_KEYWORDS["Natural Lilith"] = ...
```

If differentiated interpretation copy is not ready yet, the initial values may be textually identical to the old Lilith interpretation, but they must be separate entries.

Avoid making all three keys reference one mutable dictionary object.

### Other interpretation registries

Audit and split any current single Lilith entry in:

- body definition/metadata dictionaries
- dominance descriptions
- body keyword maps
- sign-placement prose maps
- aspect prose helpers
- tooltip/help copy
- body category descriptions
- chart summary generators

This is an architectural split first. Interpretation language can diverge later without another identity refactor.

---

## 12. Display identity vs persisted identity

### Canonical persisted/exported names

Always:

```text
Mean Lilith
Osculating Lilith
Natural Lilith
```

### UI display glyphs

Use:

| Canonical body | UI display |
|---|---|
| `Mean Lilith` | `🌝⚸` |
| `Osculating Lilith` | `🌚⚸` |
| `Natural Lilith` | `🌗⚸` |

The emoji combination is a presentation alias only.

Do not use `🌝⚸`, `🌚⚸`, or `🌗⚸` as:

- dictionary keys in chart data
- DB column/body names
- cache identities
- Trait criterion identities
- CSV field identities
- JSON body keys
- API keys

A display helper can map canonical identity to decorative label.

---

## 13. Chart model and calculation pipeline

`Chart.__init__()` currently derives positions, retrogrades, aspects, dominance-related data, etc. from generic dictionaries. Preserve that adaptive design where it works, but verify every downstream filter.

### New-chart invariant

After `planetary_positions()`:

```python
assert "Mean Lilith" in chart.positions
assert "Osculating Lilith" in chart.positions
assert "Natural Lilith" in chart.positions
assert "Lilith" not in chart.positions
```

Equivalent invariant for `retrogrades`.

### Aspects

`find_aspects(chart.positions)` must treat the three as distinct endpoints.

A target body may legitimately have three separate aspects, one from each Lilith.

Do not deduplicate:

```text
Mean Lilith square Sun
Osculating Lilith square Sun
Natural Lilith square Sun
```

merely because their names belong to one conceptual family.

### Dominance

All three must participate according to their independent configured weights.

Audit both:

- sign/element/mode/house dominance
- dominant-planet/body output

If the algorithm assumes body names are unique keys, that is fine. If it has allowlists, update them.

### Body Dynamics

Any Enabling / Antagonizing / Escalating body-role analysis must preserve the three endpoints independently.

### Time-specific recalculation

Any routine that regenerates positions because of retcon/rectification/midpoint/time edits must regenerate all three automatically.

---

## 14. Natal, synastry, composite, and transit audit

The three-body split must be valid in every astrological context.

Audit:

- Natal chart aspects
- Chart wheel
- Synastry
- Composite calculations
- Personal Transits / Daily Vibe
- Personal Transits / Life Forecast
- Global Transits
- Personal Timeline / future transit systems
- any progression/return/cycle feature if present

### Transit category sets

The existing Personal Transit logic references the Lilith category set. Expand it to all three canonical bodies under the intended Lilith transit policy.

If all three are eligible, they must remain three separate transit bodies.

Likewise, all three can be natal targets where Lilith is allowed as a natal endpoint.

### Interaction with aspect deduplication

Structural axis deduplication (`AS/DS`, `MC/IC`, `Rahu/Ketu`) must **not** generalize to the three Lilith bodies.

The three Liliths are not complementary axis aliases. They are separate calculations.

### Separate transit-fix branch

There is separate work on:

`fix/personal-transit-eligibility-axis-timezone`

When integrating both initiatives, rebase/cherry-pick carefully so the Personal Transit body-category changes from this rollout do not undo the Jupiter/Saturn/Chiron/axis/timezone fixes on that branch.

---

## 15. `app.py` / GUI audit

Do not refactor the whole `app.py` merely because it is large. Use the repo-wide search results to make targeted edits and push logic into shared helpers where possible.

Audit every display/interaction surface that may assume one Lilith:

- Chart Data Output
- Chart View text
- Chart Editor
- body selectors/dropdowns
- aspect filters
- sort controls
- interpretation panes
- dominance displays
- Personal Transit popout
- Global Transit output
- Synastry output
- Similarities Analysis UI
- Database Analytics UI
- Settings
- Database Norms Snapshot action
- import/export dialogs
- copy-to-clipboard text
- tooltips
- legends
- chart/body search
- any body enable/disable preferences

The UI should show all three canonical bodies unless a feature has a deliberate, documented body subset.

---

## 16. Chart wheel / drawing

Audit the drawing pipeline independently from text output.

Required:

- three bodies available in drawing order
- three distinct glyph/display-label mappings
- three independent longitudes
- no body-name alias collapsing before plotting
- collision/stacking logic can distinguish all three even when longitudes are close
- hover/tooltip text names the correct canonical body
- aspect-line code preserves exact endpoint identity

Because the three apogees can cluster or diverge, label-placement code must be tested with:
- near-identical longitudes
- moderate separation
- wide separation

No coordinate should be nudged in the underlying chart model to solve a display collision.

---

## 17. Persistence and backward compatibility — highest-risk section

This migration must distinguish **old derived data** from **old semantic references**.

### 17.1 New derived-data schema version

Introduce a body/astronomy schema marker, for example:

```text
THREE_LILITH_BODY_SCHEMA_VERSION = 1
```

or fold it into an existing derived-data/calculation signature.

The marker must make a one-Lilith chart/cache distinguishable from a three-Lilith chart/cache without inspecting arbitrary values.

### 17.2 Loading a current chart

If a stored chart has:

```text
Mean Lilith
Osculating Lilith
Natural Lilith
```

and its derived-data signature/schema is current, load normally.

### 17.3 Loading a legacy chart with plain `"Lilith"`

If any legacy derived structure contains ambiguous old Lilith data:

```python
positions["Lilith"]
retrogrades["Lilith"]
aspects involving "Lilith"
dominance values derived from the old body set
body-dynamics roles derived from the old body set
```

do **not** rename those values.

Instead:

1. preserve the chart's source/birth metadata
2. reconstruct the effective calculation datetime using the same retcon/rectification policy as normal chart calculation
3. recalculate `positions`
4. recalculate `retrogrades`
5. recalculate aspects
6. recalculate dominance-derived fields
7. recalculate Body Dynamics / any body-dependent derived fields
8. refresh derived signatures
9. persist canonical data only after successful recalculation

### 17.4 Old `lilith_calculation_mode` metadata

If an old chart says the old mode was `mean` or `true`, that is useful diagnostic provenance but does not change the migration action.

Still regenerate **all three**.

This avoids maintaining two classes of migrated chart.

### 17.5 Old `"True Lilith"` coordinate keys

If any stored derived-coordinate format used `"True Lilith"` explicitly, the label provides stronger provenance, but the preferred migration remains to regenerate all three from source astronomical inputs so every chart enters the same current schema.

### 17.6 Missing astronomical inputs

Some old/imported records may not have enough reliable data to regenerate positions.

Do not invent three Liliths.

Define an explicit failure state:

- mark derived astronomy stale / migration incomplete
- exclude that chart's ambiguous Lilith value from three-Lilith research/norm generation
- preserve source record
- surface a count/diagnostic in the migration or Norm Snapshot result
- provide a route for manual chart-data repair if the UI has one

Do not publish a norm snapshot that silently mixes migrated and ambiguous one-Lilith data.

### 17.7 Idempotence

Running migration twice must not alter already-canonical charts or produce duplicate work beyond ordinary safe recalculation.

### 17.8 Transactionality / backup

For batch DB migration:

- create/verify a backup first
- migrate in a transaction or recoverable batches
- do not delete legacy derived data until canonical replacement has calculated successfully
- log counts: scanned / already current / migrated / skipped / failed

### 17.9 Cache invalidation

Invalidate or version-bump every cache whose value can depend on body identity:

- calculated chart cache
- aspect cache
- dominance cache
- Similarities cache
- Trait-score cache
- Trait ranking cache where underlying scores change
- Database Analytics cache
- prediction/norm cache
- transit cache if persisted
- export-derived cache if any

Do not let a cache entry calculated under the one-Lilith body universe satisfy a request under the three-Lilith universe.

---

## 18. Database schema / `db.py`

Audit the very large DB module by targeted search rather than wholesale editing.

Find:

- positions persistence
- retrograde persistence
- aspect persistence
- derived-data signatures
- chart hydration
- chart save/update
- JSON payload columns
- migration/version tables
- batch recalculation commands
- Database Norm Snapshot source loading
- Trait caches
- research caches

If positions are stored as JSON, schema migration may be mostly payload-level.

If any Lilith values are normalized into dedicated columns/tables, add canonical identities/columns instead of overloading the old one.

### New-save invariant

After successful migration or calculation, newly persisted derived data must not write plain `"Lilith"`.

Legacy source metadata may retain an old settings/provenance field if intentionally preserved, but raw astronomical outputs must be canonical.

---

## 19. Manual Database Norms Snapshot in Settings — mandatory integration

This is part of the feature, not a later cleanup.

The manual **Database Norms Snapshot** action in Settings must guarantee that its reference population is using the three-Lilith calculation schema before it computes/publishes norms.

### Required snapshot sequence

1. Resolve the eligible source-chart population.
2. Check each chart's derived-data/body-schema version.
3. Recalculate/migrate any eligible legacy chart with ambiguous one-Lilith derived data.
4. Explicitly identify charts that cannot be regenerated because required source astronomical inputs are missing.
5. Build all norm/research source values only from charts that satisfy the current body schema.
6. Calculate Mean, Osculating, and Natural Lilith as distinct factors wherever the norm system consumes body/position/aspect evidence.
7. Build the new snapshot in temporary memory/file/table space.
8. Validate snapshot structure, chart counts, schema signature, and section signatures.
9. Only then atomically publish/swap it as the active snapshot.
10. Report migrated / already-current / skipped / failed counts to the user.

### Snapshot provenance

Add body-schema information to snapshot provenance, for example:

```json
{
  "body_schema_version": 1,
  "canonical_lilith_bodies": [
    "Mean Lilith",
    "Osculating Lilith",
    "Natural Lilith"
  ]
}
```

The exact shape can follow existing provenance conventions.

### Mixed-schema rejection

Snapshot publication must fail validation if the source population contains a mix of:
- current three-Lilith derived data
- ambiguous one-Lilith derived data being treated as current

Skipping explicitly invalid/unrecoverable charts with a reported reason is preferable to silently mixing them.

### Norm versioning

Audit:
- `analysis/prediction_norms_catalog.py`
- `analysis/prediction_norms_generator.py`
- default/bundled norm snapshots
- any Settings-side snapshot builder in `app.py` or another GUI module

The current catalog is already versioned and carries provenance. Use that machinery rather than creating a parallel Lilith-only version system.

If Trait norms can change because legacy `"Lilith"` / `"True Lilith"` criteria now explicitly bind to Osculating while the chart also contains Mean/Natural, regenerate the affected norms.

---

## 20. Traits and prediction scoring

This is a backward-compatibility hotspot because the repository already contains Traits using `"True Lilith"`.

### Existing Trait behavior after rollout

These must continue to score:

```text
True Lilith in H7
True Lilith in H10
Ceres square True Lilith
Part of Fortune trine True Lilith
Moon sextile True Lilith
```

They now target `Osculating Lilith`.

Likewise any plain `"Lilith"` criterion targets `Osculating Lilith`.

### New Trait authoring

Trait editors/selectors should offer the three canonical names independently:

```text
Mean Lilith
Osculating Lilith
Natural Lilith
```

Do not offer plain `"Lilith"` as a new canonical factor.

### Scoring parser

Ensure normalization is applied consistently to:

- `bodies`
- `antibodies`
- `positions`
- `antipositions`
- `aspects`
- `antiaspects`
- any direct criterion lookup

A parser that fixes `"True Lilith"` only in body criteria but misses aspect strings is incomplete.

### Trait cache invalidation

The canonicalization changes the meaning/key lookup of existing criteria and the chart body universe changes. Bump/invalidate relevant possible-score and actual-score caches as required.

---

## 21. Similarities Analysis

Mean, Osculating, and Natural Lilith are three separate variables.

Required behavior:

- all three positions can participate
- all three aspects can participate
- all three body/dominance values can participate if that analysis uses them
- labels are canonical in data/export
- UI may decorate labels with the designated glyphs
- no `"Lilith family"` roll-up
- no alias normalization that turns the three canonical names into one identity
- old trait/semantic plain `"Lilith"` still maps only to Osculating

### Regression cases

Construct a fixture where:

```text
Mean Lilith       -> one sign/aspect result
Osculating Lilith -> a different sign/aspect result
Natural Lilith    -> a third result
```

Assert that Similarities produces three independently addressable features.

Also construct a case where all three happen to make the same aspect type to one body. Assert all three survive as separate body-specific observations.

### Existing structural dedupe

Keep existing angle/node structural deduplication behavior, but do not treat the Lilith trio as redundant.

---

## 22. Database Analytics

Audit the feature-generator and UI selector paths separately.

Required:

- Mean Lilith is independently queryable
- Osculating Lilith is independently queryable
- Natural Lilith is independently queryable
- sign distribution per body is independent
- house distribution per body is independent where houses apply
- aspect statistics preserve endpoint identity
- filters/dropdowns list all three
- CSV/JSON analytics exports use canonical names
- cached analytics from the old one-body schema are invalidated

Do not add a default combined "Lilith" statistic. A future aggregate could be a separate feature, but it is not part of this migration.

---

## 23. Exports

Do not assume generic chart serialization automatically guarantees all exporters are correct.

Audit each exporter for:
- body allowlists
- ordering arrays
- display-name substitutions
- body category filters
- aspect endpoint filters
- hard-coded columns
- CSV header generation
- JSON schema validation
- plain-text chart-data formatting

### Export contract

Machine-readable export identities are:

```text
Mean Lilith
Osculating Lilith
Natural Lilith
```

Never export the decorative emoji as the body identity.

### Required exporter regression test

Create a chart fixture with all three values and assert the exported result contains all three canonical names and contains no plain `"Lilith"` output field.

---

## 24. Imports

Imports require type-sensitive compatibility.

### Importing a full chart with astronomical source data

If an imported chart contains:
- datetime
- location / coordinates
- enough source metadata to calculate the chart
- an old ambiguous `Lilith` derived coordinate

ignore/reject the old derived Lilith coordinate and recalculate all three.

### Importing a coordinate-only chart

If the file contains only a historical `"Lilith"` longitude and lacks provenance/source data, do not reinterpret it as Osculating.

Preserve/flag ambiguity or omit it from canonical calculations.

### Importing a Trait or semantic criteria file

Plain `"Lilith"` and `"True Lilith"` are semantic references and therefore normalize to `Osculating Lilith`.

This is intentionally different from coordinate migration.

### Round-trip test

A newly exported three-Lilith chart imported back into the application must preserve all three identities exactly.

---

## 25. Duration sorting

The current code has one approximate Lilith sign-duration entry.

Replace it with three explicit keys.

Do not retain a normalization step that changes `"Lilith (mean)"` into plain `"Lilith"`.

If duration sorting is only a UI approximation, document the chosen approximate values. If the three methods need different practical duration behavior, encode that separately.

The important invariant is that missing duration metadata for one canonical Lilith must not cause it to fall to an unrelated generic body default silently.

---

## 26. Research/statistical implications

The three bodies are independent dimensions in the application's research machinery.

This means:
- a Trait can reference one without referencing the others
- Similarities can report one without collapsing the others
- Database Analytics can compare their distributions
- norms can encode features involving each independently
- a chart's dominance calculation can include each according to its own body weight

No family cap or normalization should be introduced merely because all three describe lunar apogee calculations.

If a statistical model later needs collinearity handling, that is a model-specific concern and not an identity-layer reason to merge them.

---

## 27. Calculation and schema signatures

This rollout changes the body universe, so the change must be visible to stale-data detection.

Add a stable signature component, e.g.:

```text
body_schema = three_lilith_v1
```

Use it anywhere a derived result can otherwise appear current even though it was generated before this rollout.

Consider:
- `derived_birth_data_signature`
- chart calculation cache keys
- database recalculation checks
- norms snapshot provenance/signature
- Trait score cache signatures
- Similarities cache keys
- analytics cache keys

Do not rely only on the absence/presence of `"Lilith"` because some old records may omit Lilith entirely.

---

## 28. Tests — required matrix

Do not merge this rollout based only on UI inspection.

### 28.1 Foundation identity tests

Already added in `tests/test_body_identity.py`:

- `Lilith -> Osculating Lilith`
- `True Lilith -> Osculating Lilith`
- case-insensitive aliases
- three canonical names remain distinct
- `"Black Moon Lilith"` is not guessed
- unknown names pass through

Keep these tests.

### 28.2 Swiss ID tests

Assert each canonical body resolves to the expected Swiss constant/ID:

```text
Mean        -> 12
Osculating -> 13
Natural     -> 21
```

If testing aliases rather than numeric constants, still assert they map to three different Swiss IDs.

### 28.3 Direct numeric cross-check

For a fixed timezone-aware UTC timestamp:

1. calculate each Lilith through EphemeralDaddy
2. independently call `swe.calc_ut()` with each expected body ID
3. compare longitude within the normal numerical tolerance

This catches an accidental method swap.

### 28.4 No-fallback test

Simulate one canonical Swiss identifier being unavailable.

Assert that body becomes unavailable; assert it does not equal another Lilith because of fallback substitution.

### 28.5 Position output

Assert:
- exactly three canonical Lilith keys
- no plain `"Lilith"` key
- no `"True Lilith"` key
- no `"Black Moon Lilith"` key

### 28.6 Retrograde/speed output

Same identity assertions plus independent expected speed/retrograde results.

### 28.7 Registry tests

Assert each canonical Lilith is present independently in every required body registry and order list.

Assert no registry canonicalizes one canonical name to another.

### 28.8 Weight tests

Assert lookups for all three use their intended explicit entries rather than generic fallback weights.

### 28.9 Aspect tests

Create positions where all three form known aspects.

Assert aspect endpoints preserve exact canonical body name.

Assert three same-type aspects to one target are not deduplicated.

### 28.10 Trait compatibility tests

Use criteria containing:
- plain `Lilith`
- `True Lilith`
- canonical `Osculating Lilith`

Assert all three semantic references target the same Osculating chart value.

Use explicit `Mean Lilith` and `Natural Lilith` criteria and assert they target their own values.

### 28.11 Legacy chart migration test

Fixture:
- valid datetime/location
- `positions["Lilith"]`
- `retrogrades["Lilith"]`
- aspects involving `"Lilith"`
- old `lilith_calculation_mode`

Load/migrate it.

Assert:
- old derived Lilith coordinate was not simply copied
- all three canonical positions are recalculated
- all three retrograde entries exist
- aspects regenerated from current positions
- no plain Lilith endpoint survives in new derived data
- schema signature updated

### 28.12 Migration idempotence

Migrate the canonical result again.

Assert no destructive or duplicative change.

### 28.13 Unrecoverable legacy chart test

Fixture lacks required astronomical source inputs.

Assert:
- ambiguous old coordinate is not relabeled Osculating
- migration reports/marks the chart as incomplete
- norm generation does not treat it as canonical data

### 28.14 Save/load round trip

Create a new chart, save, reload.

Assert all three survive in:
- positions
- retrogrades
- aspects
- any persisted derived metrics that expose body identities

### 28.15 Similarities tests

Assert all three are separate variables and all three may appear in results/export.

### 28.16 Database Analytics tests

Assert selectors/features/stats can distinguish all three.

### 28.17 Norm Snapshot tests

Assert:
- old one-Lilith source charts are migrated before scoring
- unrecoverable charts are reported/skipped
- snapshot provenance carries current body schema
- all relevant features use canonical identities
- publication rejects a mixed-schema source
- rebuilding twice is stable

### 28.18 Export tests

Explicitly test every supported export format that contains body data.

Do not infer exporter correctness from `Chart.as_dict()`.

### 28.19 Import tests

Test:
- current canonical chart
- legacy chart with source data
- ambiguous coordinate-only legacy chart
- legacy Trait file

### 28.20 UI tests / smoke tests

Verify:
- all three labels visible where expected
- no duplicate decorative labels
- Settings no longer changes which Lilith is calculated
- chart wheel can display all three
- hover identifies correct canonical body
- body selectors contain all three

### 28.21 Platform tests

Run the relevant suite on macOS and Windows because EphemeralDaddy ships to both.

---

## 29. Suggested deterministic test timestamp

Use a fixed timezone-aware UTC datetime rather than `now()`.

For example:

```python
datetime.datetime(2026, 9, 10, 13, 26, tzinfo=datetime.timezone.utc)
```

This corresponds to the Personal Transit comparison work that exposed the current Lilith-method mismatch, but the three-body unit test should compare directly against Swiss Ephemeris IDs rather than hard-coding values copied from an external website.

Location is not required for the geocentric Lilith body longitude itself, though a full chart fixture may use a stable location for house/aspect integration testing.

---

## 30. Runtime invariants and diagnostics

Add development/test assertions or validation helpers for:

### Canonical new chart

```text
Mean Lilith present
Osculating Lilith present
Natural Lilith present
plain Lilith absent
```

when all three calculations are available.

### No identity substitution

If a method cannot calculate, it must be missing/unavailable rather than filled with another method's coordinate.

### Canonical aspect endpoints

No newly calculated aspect endpoint should be plain `"Lilith"`.

### Canonical exports

No new machine-readable export should use plain `"Lilith"` as a body identity.

### Norm safety

A norm snapshot should expose its body schema version and refuse to masquerade as current if generated from stale one-Lilith data.

### Migration logging

Log only operational/chart IDs needed for diagnostics, not unnecessary personal chart metadata.

Suggested counts:

```text
charts_scanned
charts_already_current
charts_recalculated
charts_skipped_missing_inputs
charts_failed
```

---

## 31. Do-not-do guardrails

Do **not**:

1. globally search/replace `"Lilith"` with `"Osculating Lilith"`
2. rename an old stored coordinate and call that a migration
3. retain one process-global Lilith calculation mode as a hidden source of truth
4. fall back from one Lilith algorithm to another
5. persist emoji UI aliases as body identities
6. collapse the three canonical names inside semantic normalization
7. add a shared "Lilith family weight" or family cap
8. assume all exporters are adaptive without testing them
9. assume Similarities and Analytics are adaptive without testing them
10. keep a local Trait alias table after `core/body_identity.py` becomes authoritative
11. infer generic `"Black Moon Lilith"` without provenance
12. publish Database Norms from mixed old/new body schemas
13. silently include unrecoverable ambiguous coordinates in research
14. share one mutable interpretation dictionary among all three canonical keys
15. silently drop Natural Lilith because one binding constant name differs; resolve supported aliases and test
16. make display collision fixes by modifying astronomical longitudes
17. merge a partial state where chart calculation emits three bodies but scoring/research still treats only one

---

## 32. Recommended implementation sequence

Keep commits small enough to review, but do not ship the application in an internally inconsistent partial state.

### Phase A — Foundation — already committed

- `core/body_identity.py`
- identity tests
- permanent semantic decisions

### Phase B — Ephemeris triad

- three Swiss ID mappings
- positions
- longitude
- retrogrades/speed
- availability
- eliminate cross-method fallback
- ephemeris unit tests

### Phase C — Core body registries

- PLANET_ORDER
- category sets
- weights
- durations
- glyphs/colors
- body metadata
- interpretations
- semantic normalization integration

At the end of this phase, the core engine should understand the three identities everywhere.

### Phase D — Chart calculation and Settings

- chart creation/recalculation
- aspects
- dominance
- Body Dynamics
- retire active Lilith mode setting
- calculation/body schema signature

### Phase E — Persistence migration

- loader/hydration
- DB recalculation
- stale-data detection
- cache invalidation
- backup/transaction behavior
- migration tests

Do this before research/norm code is allowed to consume the new schema.

### Phase F — Traits / research / norms

- weighted predictor alias integration
- existing Trait compatibility
- Similarities
- Database Analytics
- Database Norms Snapshot
- norm provenance/versioning
- research cache invalidation

### Phase G — Exports/imports

- every format
- canonical body names
- old chart import rules
- old Trait import rules
- round-trip tests

### Phase H — GUI / `app.py` / chart wheel

- three display labels
- three selectors
- three wheel bodies
- tooltips
- Settings cleanup
- targeted `app.py` hard-coded lists

### Phase I — full regression

- all new tests
- existing astronomy/chart suite
- trait/norm/research suite
- export/import suite
- macOS
- Windows
- manual smoke test with an old database backup

Only after this should obsolete one-body compatibility code be deleted.

---

## 33. Suggested Codex commit breakdown

A reviewable sequence could be:

1. `Integrate canonical Lilith identities and compute all three apogees`
2. `Split Lilith body registries, weights, and interpretations`
3. `Remove runtime Lilith mode from chart calculation and settings`
4. `Migrate legacy Lilith derived chart data to three-body schema`
5. `Update Trait aliases, Similarities, Analytics, and Database Norms`
6. `Update imports and exports for three canonical Lilith bodies`
7. `Update chart UI, wheel, selectors, and tooltips`
8. `Add three-Lilith regression matrix and remove obsolete mode code`

If one commit becomes huge because of `app.py`, split UI-only work further. Do not split the core identity/ephemeris change into a state where the app maps legacy semantic `"Lilith"` to `Osculating Lilith` but does not yet emit `Osculating Lilith`.

---

## 34. Specific current files Codex should inspect

Confirmed direct targets:

```text
ephemeraldaddy/core/body_identity.py              # foundation, already added
ephemeraldaddy/core/ephemeris.py                  # one-body mode currently lives here
ephemeraldaddy/core/interpretations.py            # registries/weights/order/glyphs/keywords
ephemeraldaddy/core/chart.py                      # position/retrograde/aspect generation and serialization
ephemeraldaddy/core/chart_data_fields.py          # lilith_calculation_mode currently ASTRO input
ephemeraldaddy/core/db.py                         # persistence/migrations/cache/norm source paths
ephemeraldaddy/core/composite.py                  # transit/synastry body category behavior
ephemeraldaddy/analysis/weighted_chart_predictor.py # duplicated Lilith semantic aliases
ephemeraldaddy/analysis/traits.py                 # existing True Lilith criteria
ephemeraldaddy/analysis/prediction_norms_generator.py
ephemeraldaddy/analysis/prediction_norms_catalog.py
tests/test_body_identity.py                       # foundation tests, already added
```

Likely targets to locate by search:

```text
ephemeraldaddy/gui/app.py
ephemeraldaddy/gui/features/**
ephemeraldaddy/graphics/**
ephemeraldaddy/io/**
export/import modules
Similarities Analysis implementation
Database Analytics implementation
Settings / Database Norms Snapshot implementation
chart-wheel label/glyph code
trait editor / criterion selector code
```

This list is not permission to stop searching after these files are changed.

---

## 35. Manual acceptance checklist

Before opening the final PR, verify all of the following on a clean new chart and on a migrated old chart:

- [ ] `Mean Lilith` is calculated
- [ ] `Osculating Lilith` is calculated
- [ ] `Natural Lilith` is calculated
- [ ] all three use different Swiss body definitions
- [ ] no cross-method fallback exists
- [ ] new `positions` contains no plain `"Lilith"`
- [ ] new `retrogrades` contains no plain `"Lilith"`
- [ ] new aspect endpoints preserve the three canonical names
- [ ] all three have explicit independent registry entries
- [ ] all three have explicit weighting entries wherever applicable
- [ ] all three have separate interpretation keys
- [ ] legacy semantic `"Lilith"` resolves to Osculating
- [ ] legacy semantic `"True Lilith"` resolves to Osculating
- [ ] generic `"Black Moon Lilith"` is not guessed without provenance
- [ ] old stored `positions["Lilith"]` is recalculated rather than renamed
- [ ] old retrogrades/aspects are regenerated
- [ ] derived dominance/body-dynamics data is regenerated where stale
- [ ] old chart migration is idempotent
- [ ] unrecoverable old charts are reported, not fabricated
- [ ] Settings no longer selects which Lilith calculation exists
- [ ] old settings files still load safely
- [ ] body/calculation schema version invalidates old caches
- [ ] Chart Data Output shows all three
- [ ] chart wheel shows all three
- [ ] tooltips distinguish all three
- [ ] body selectors expose all three
- [ ] Personal Transits preserve all three when eligible
- [ ] Global Transits preserve all three when eligible
- [ ] natal/synastry/composite aspects preserve all three
- [ ] Similarities Analysis treats all three separately
- [ ] Similarities export treats all three separately
- [ ] Database Analytics treats all three separately
- [ ] Database Analytics exports use canonical names
- [ ] Database Norms Snapshot migrates/recalculates source charts first
- [ ] Database Norms Snapshot records body-schema provenance
- [ ] Database Norms Snapshot cannot publish mixed-schema data
- [ ] Trait `"Lilith"` criteria still work and now bind Osculating
- [ ] Trait `"True Lilith"` criteria still work and now bind Osculating
- [ ] new Traits can explicitly target Mean/Osculating/Natural
- [ ] JSON export includes all three canonical names
- [ ] CSV/text exports include all three where relevant
- [ ] current export/import round trip preserves all three
- [ ] legacy chart import uses recalculation when possible
- [ ] ambiguous coordinate-only import is not falsely relabeled
- [ ] no machine-readable output uses the decorative emoji as an identity
- [ ] full automated suite passes
- [ ] macOS smoke test passes
- [ ] Windows smoke test passes
- [ ] an old database backup can open and migrate without destructive loss

---

## 36. Final architectural invariant

After this rollout, **"Lilith" is not a calculated body in EphemeralDaddy.**

It is only a permanent **legacy semantic alias** for `Osculating Lilith`.

The actual calculated body universe contains:

```text
Mean Lilith
Osculating Lilith
Natural Lilith
```

Each has:
- its own Swiss calculation
- its own stored coordinate
- its own speed/retrograde state
- its own aspects
- its own registry identity
- its own weights
- its own interpretation key
- its own research dimension
- its own export identity
- its own UI presentation

That invariant is what prevents this problem from returning in another subsystem later.
