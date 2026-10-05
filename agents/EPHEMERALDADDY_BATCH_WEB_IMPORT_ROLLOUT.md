# EphemeralDaddy Batch Web Import — Codex Rollout Handoff

**Target branch:** `oh-lawdy-we-still-refactoring!`  
**Repository:** `croweykid/ephemeraldaddy`  
**Status:** Implementation handoff  
**Primary feature owner:** `ephemeraldaddy/gui/features/import_export/`  
**Network/data owner:** `ephemeraldaddy/io/web_profile/`  
**Database owner:** `ephemeraldaddy/core/db.py`  
**Menu entry:** Database View → Charts → **Batch Import**, immediately below **Delete chart(s)**  
**Primary constraint:** Implement the batch workflow without adding substantive feature logic to `gui/app.py`.

---

## 1. Goal

Add a **Batch Import** workflow for creating public-figure natal charts from a list of names.

The workflow must:

1. accept a pasted list of names and a CSV file;
2. look up each person in the background, trying **Astrotheme first** and **Wikipedia second**;
3. return the lookup results in a separate editable dark-theme window;
4. let the user repair names, dates, times, birth places, biographies, and other imported values before anything is saved;
5. validate birth places against EphemeralDaddy's existing geocoding path;
6. allow only complete, parseable rows to be selected for import;
7. save selected rows directly to the database without opening Chart Editor for each chart;
8. refresh Database View as charts are added without changing the current/open chart;
9. export unresolved or failed rows to CSV;
10. mark charts created by this automated workflow with a permanent `auto_generated = TRUE` provenance property;
11. provide a Database Search filter for auditing `auto_generated` charts later.

The purpose is not simply faster entry. The workflow must make automated records **easy to identify and audit** so an incorrect external lookup cannot silently blend into manually verified database records.

---

## 2. Read before editing

Read these files before implementation:

1. `AGENTS.md`
2. `agents/REFACTOR_MANIFESTO.md`
3. this handoff
4. current branch versions of:
   - `ephemeraldaddy/gui/window_chrome.py`
   - `ephemeraldaddy/gui/style.py`
   - `ephemeraldaddy/gui/astrotheme_search.py`
   - `ephemeraldaddy/gui/wikipedia_search.py`
   - `ephemeraldaddy/gui/wikipedia_blurb_getter.py`
   - `ephemeraldaddy/gui/features/chart_editor/wikipedia_biography.py`
   - `ephemeraldaddy/gui/features/import_export/builders.py`
   - `ephemeraldaddy/gui/features/import_export/web_profile_controller.py`
   - `ephemeraldaddy/gui/dbv_search_panel.py`
   - `ephemeraldaddy/io/geocode.py`
   - `ephemeraldaddy/core/db.py`
   - `docs/birth_time_and_place_protocol.md`
   - the current Astrotheme/Wikipedia import path in `ephemeraldaddy/gui/app.py`
   - the current Database View `_refresh_charts(...)` path in `app.py`
   - current QThread worker examples under `gui/features/`
5. relevant tests:
   - `tests/test_astrotheme_error_classification.py`
   - `tests/test_wikipedia_search_birth_data.py`
   - `tests/test_wikipedia_blurb_getter.py`
   - `tests/test_window_chrome_settings_source.py`
   - database migration tests
   - Database View filter/source tests

`AGENTS.md` currently refers to an older manifesto filename. On this branch, the active refactor document is `agents/REFACTOR_MANIFESTO.md`.

---

## 3. Existing code that must be reused

Do not create a parallel implementation of functionality the application already owns.

### 3.1 Astrotheme

`ephemeraldaddy/gui/astrotheme_search.py` already contains:

- `search_astrotheme_profile_url(...)`
- `parse_astrotheme_profile(...)`
- `AstrothemeNetworkError`
- `AstrothemeProfileNotFoundError`
- `AstrothemeProfileFormatError`

A parsed Astrotheme profile already supplies:

```text
name
birth_year
birth_month
birth_day
birth_hour
birth_minute
time_unknown
birth_place
data_rating
biography
profile_url
```

Reuse this parser behavior.

### 3.2 Wikipedia/Wikidata

`ephemeraldaddy/gui/wikipedia_search.py` already contains:

- `resolve_wikipedia_page_options(...)`
- `parse_wikipedia_available_birth_data(...)`
- `parse_wikipedia_birth_data(...)`

`resolve_wikipedia_page_options(...)` already distinguishes:

```text
single
multiple
not_found
```

`parse_wikipedia_available_birth_data(...)` already prefers article infobox data and falls back to Wikidata.

`ephemeraldaddy/gui/wikipedia_blurb_getter.py` already contains:

- `fetch_wikipedia_blurb(...)`
- `populate_wikipedia_biography(...)`
- `unique_title_matching_birth_date(...)`
- the Wikipedia ambiguity/not-found exception types.

`ephemeraldaddy/gui/features/chart_editor/wikipedia_biography.py` already contains useful non-UI logic for disambiguating candidate pages by factual birth date.

### 3.3 Birth-place search and geocoding

`ephemeraldaddy/io/geocode.py` already contains:

- `search_locations(query, limit=...)`
- `geocode_location(query)`
- `LocationLookupError`

Chart Editor's existing place-search behavior in `app.py` currently:

1. calls `search_locations(query, limit=7)`;
2. shows the candidate labels;
3. stores the selected label and coordinates;
4. later reuses those coordinates instead of geocoding the same value again.

The Batch Import window must follow the same user-visible semantics.

### 3.4 Chart date/time protocol

`docs/birth_time_and_place_protocol.md` is authoritative.

In particular:

- entered birth time is local civil time at the birthplace;
- the birthplace is resolved to coordinates before timezone inference;
- a known time remains a real local time;
- an unknown time uses local noon as a computational placeholder;
- unknown time remains `birthtime_unknown=True`;
- unknown-time charts must not gain factual house/angle status merely because noon was used internally.

Do not use the generic CSV import's `(0, 0) UTC` fallback for this feature. A batch row whose birth place cannot be validated is **not importable yet**.

### 3.5 Persistence

`ephemeraldaddy/core/db.py::save_chart(...)` is the canonical chart insertion path.

Do not bypass it with a feature-specific raw `INSERT`.

### 3.6 Database View refresh

The existing Database View `_refresh_charts(...)` path already accepts `changed_uids`.

New feature-facing APIs must use **Chart UID**, not numeric SQLite chart IDs. Numeric IDs may remain inside persistence-boundary code where the existing database implementation requires them.

---

## 4. Required user flow

### 4.1 Opening the feature

In `ephemeraldaddy/gui/window_chrome.py`, Database View's Charts menu currently contains:

```text
New chart
Edit chart
Delete chart(s)
Current Transits
...
```

Add:

```text
New chart
Edit chart
Delete chart(s)
Batch Import
Current Transits
...
```

The exact label is:

**Batch Import**

It must appear directly below **Delete chart(s)**.

The action opens a **new separate window**. It must not replace Database View and must not force Chart Editor open.

Use a lazy feature import/open function comparable in spirit to the existing Personal Timeline opener. `window_chrome.py` should own only the menu hook, not Batch Import implementation.

### 4.2 Initial input

The Batch Import window should support both:

#### A. Pasted names

A multiline input where one nonblank line = one requested person.

Preserve input order.

Do not silently deduplicate repeated names. The same name may intentionally appear more than once with different metadata when supplied through CSV.

#### B. CSV

Provide a `Load CSV` action.

Required logical column:

```text
name
```

Recognize column names case-insensitively.

If present, preserve these input columns:

```text
alias
from
tags
notes
```

Map them to the existing chart model as:

| CSV | Chart persistence |
| --- | --- |
| `alias` | `chart.alias` |
| `from` | `chart.from_whence` |
| `tags` | `chart.tags` |
| `notes` | `chart.comments` |

Use existing tag parsing/deduplication semantics. Do not invent a new tag serialization format.

A CSV may also contain resolved fields from a prior failures export; when practical, accept these for round-trip repair:

```text
birth_date
birth_time
birth_place
bio
sources
error
```

The minimum contract remains `name`.

### 4.3 Start lookup

Provide an explicit action such as **Look Up Names**.

The remote lookup must run off the GUI thread.

The window stays responsive while rows are being populated.

Progress should be visible at minimum as:

```text
Searching 7 / 42 — Person Name
```

Rows may populate as each lookup finishes; the user does not have to wait for the entire list before inspecting completed rows.

---

## 5. External lookup behavior

Create one canonical non-Qt lookup path rather than placing remote-provider logic in the Batch Import window.

The refactor manifesto already defines the intended ownership:

```text
ephemeraldaddy/io/web_profile/
    models.py
    lookup_service.py
    import_service.py
    astrotheme.py
    wikipedia.py
```

Use this feature to move toward that boundary.

### 5.1 Migration strategy

The existing Astrotheme/Wikipedia modules are already largely non-Qt even though they currently live under `gui/`.

Preferred bounded implementation:

1. establish `ephemeraldaddy/io/web_profile/`;
2. move or wrap the provider logic there;
3. keep thin compatibility imports at the old module paths if existing callers still require them;
4. do not make a lower-level `io/` module import `gui/`;
5. do not broaden this task into unrelated importer refactoring.

If moving all provider code safely would make this change too broad, the acceptable transitional alternative is:

- add the new canonical service/model boundary;
- let that service call narrowly extracted provider functions;
- leave documented compatibility wrappers behind;
- do not duplicate parsing logic.

### 5.2 Lookup order

For each requested name:

#### Stage 1 — Astrotheme

Try Astrotheme first.

If a profile is found and parsed:

- preserve Astrotheme's resolved name;
- preserve complete birth date;
- preserve known birth time if supplied;
- otherwise mark time unknown;
- preserve birthplace;
- preserve Rodden/data rating;
- preserve Astrotheme profile URL;
- preserve Astrotheme biography if supplied.

Then attempt Wikipedia for biography/source enrichment.

Astrotheme remains the preferred birth-data source when it supplied usable data.

#### Stage 2 — Wikipedia fallback

If Astrotheme:

- has no matching profile;
- returns unsupported profile markup; or
- is temporarily unavailable for this row,

try Wikipedia instead.

A provider outage must not end the entire batch.

Wikipedia fallback may supply:

- resolved article title/name;
- any available birth-date components;
- birthplace;
- Wikipedia URL;
- introductory biography text.

Wikipedia does not supply a factual birth time through the current EphemeralDaddy path. Therefore:

```text
birth_time = unknown
birthtime_unknown = TRUE
```

and chart construction uses local noon only after the place is validated.

### 5.3 Wikipedia ambiguity rules

Never silently choose among multiple plausible Wikipedia people.

If Astrotheme has already supplied a complete factual birth date, it is permissible to test the candidate Wikipedia pages' birth dates and automatically accept a Wikipedia page only when **exactly one** candidate matches that date. Reuse `unique_title_matching_birth_date(...)` semantics.

Otherwise, if Wikipedia returns multiple pages for the same name:

- keep the row;
- preserve the requested name;
- leave unresolved fields editable;
- put the candidate titles into the row's diagnostic state;
- flag the row with a blocking ambiguity error;
- do not select it for import automatically.

Example error:

```text
Multiple Wikipedia entries found: Alex Smith; Alex Smith (writer); Alex Smith (musician)
```

The user can manually repair the row.

### 5.4 Not found

If neither provider can resolve a person:

- keep the row in the table;
- preserve any CSV metadata;
- set a readable error;
- do not delete the row.

### 5.5 Biography failure is not necessarily a blocking failure

A valid name + valid birth date + validated birthplace is enough to construct a chart.

If birth data are valid but biography retrieval fails:

- preserve a warning in Errors;
- allow selection/import;
- leave biography blank or retain Astrotheme biography if available.

Distinguish **blocking validation errors** from **nonblocking provider warnings** in the row model.

---

## 6. Remote request pacing and service etiquette

The purpose of pacing is to reduce unnecessary load and comply with provider policy. Do not implement behavior intended to disguise automated traffic.

### 6.1 General rules

Use:

- one sequential lookup worker;
- no parallel requests to the same external provider;
- a descriptive, stable User-Agent;
- cancellable waits;
- caching of repeated requests where appropriate;
- explicit 429/503 handling and `Retry-After` support where supplied.

Do **not** implement:

- User-Agent rotation;
- proxy rotation;
- challenge bypasses;
- hidden retry storms;
- parallel fan-out across names.

### 6.2 Wikipedia/Wikimedia

Current Wikimedia guidance requires a meaningful User-Agent with contact information, recommends no more than three concurrent requests, and requires clients to honor `Retry-After` on 429 responses.

This workflow should be more conservative than that:

- one request at a time;
- descriptive User-Agent;
- provider-level pacing;
- backoff on 429/503.

Reference:

`https://www.mediawiki.org/wiki/Wikimedia_APIs/Rate_limits`

Also see:

`https://www.mediawiki.org/wiki/Wikimedia_APIs/Access_policy`

### 6.3 Birth-place geocoding / public Nominatim

The current online geocoder uses Nominatim through geopy when online search is enabled.

The public Nominatim policy currently sets an absolute maximum of one request per second and requires caching for permitted smaller bulk operations.

Reference:

`https://operations.osmfoundation.org/policies/nominatim/`

Therefore:

- try EphemeralDaddy's local gazetteer first;
- cache place lookups for the duration of the Batch Import session;
- normalize cache keys;
- perform online fallback sequentially;
- never send more than one public Nominatim request per second;
- do not repeat the same query when a cached result exists.

If this feature later becomes a high-volume or routinely repeated workflow, public Nominatim must be replaced/configured with an appropriate hosted or self-hosted provider rather than increasing request rate.

### 6.4 Jitter implementation

A small randomized delay may be added to the normal minimum interval so all clients do not send requests at mechanically identical boundaries.

Put pacing behind a dedicated non-Qt object, for example:

```text
RequestPacer
ProviderRateGate
```

Requirements:

- monotonic-clock based;
- cancellable;
- provider-specific minimum interval;
- optional bounded jitter;
- honors an externally supplied `Retry-After`;
- testable with injected clock/wait functions.

Do not use an unconditional `time.sleep(...)` that makes cancellation wait for the entire delay. Prefer an interruptible event wait.

Important: pace **provider HTTP calls**, not merely one delay between people. Existing Astrotheme discovery can make multiple HTTP requests while resolving a single name.

---

## 7. Proposed Batch Import package

Keep the GUI implementation outside `app.py`.

A reasonable destination is:

```text
ephemeraldaddy/gui/features/import_export/batch_web_import/
    __init__.py
    models.py
    csv_io.py
    workers.py
    table_model.py
    delegates.py
    controller.py
    window.py
```

Exact file splitting may vary if the current package has a stronger convention by implementation time, but preserve the ownership boundaries below.

### `models.py`

Toolkit-neutral row/state models where possible.

Suggested conceptual types:

```text
BatchImportSeed
BatchLookupResult
BatchImportRow
BatchImportError
ValidatedPlace
```

### `csv_io.py`

Own:

- input-header normalization;
- loading name rows;
- optional metadata mapping;
- failures CSV serialization.

No Qt.

### `workers.py`

Own QObject/QThread-compatible workers for:

- remote name lookup;
- Validate All geocoding;
- optionally serial import/chart creation if chart construction is expensive enough to warrant a worker.

No widget access.

### `table_model.py`

Own the editable `QAbstractTableModel`.

### `delegates.py`

Own specialized editors/rendering:

- Include checkbox/checkmark;
- birth-place editor + Search action;
- multiline biography editor if used;
- invalid-field appearance.

### `controller.py`

Own the workflow:

- load seeds;
- start/cancel lookup;
- apply worker results;
- row validation;
- start/cancel place validation;
- import selected;
- failure collection;
- Database View refresh callback.

Do not pass an entire Database View window and then probe arbitrary attributes.

### `window.py`

Own visual construction and dialogs only.

Expose narrow signals/callbacks to the controller.

---

## 8. Batch Import result table

Use a real table model (`QTableView` + `QAbstractTableModel`) rather than constructing hundreds of nested row widgets.

The primary visible columns are:

```text
Include
Name
Birth Date
Birth Time
Birth Place
Sources
Bio Blurb
Errors
```

### 8.1 Editable columns

At minimum these must be editable:

- Name
- Birth Date
- Birth Time
- Birth Place
- Bio Blurb

Sources and Errors are normally read-only diagnostic/provenance fields.

Optional CSV metadata (`alias`, `from`, `tags`, `notes`) must remain stored in the row model even if not all of them are shown as wide main-table columns.

Recommended UX: provide a compact expandable/detail editor or additional columns for these values if space permits. Do not discard them.

### 8.2 Birth date

Display canonical date as:

```text
YYYY-MM-DD
```

Validation must use a real calendar parser such as `datetime.date(...)`.

An impossible date such as `2020-02-31` is invalid even if it matches the text pattern.

### 8.3 Birth time

Accept either:

```text
HH:MM
```

or an explicit unknown/blank state.

Blank/unknown is **valid**.

It means:

```text
birthtime_unknown = TRUE
calculation time = 12:00 local
```

Do not treat noon as a known birth time.

### 8.4 Birth place

The text value and validated coordinates are separate row state.

Changing birthplace text must immediately invalidate any previously stored coordinates for that row until the edited text is validated again.

Do not keep old coordinates attached to newly edited place text.

### 8.5 Errors

Errors should be readable and actionable.

Examples:

```text
No Astrotheme profile or Wikipedia article found.
Multiple Wikipedia entries found: ...
Birth date is invalid.
Birth place has not been validated.
Birth place could not be resolved.
Chart save failed: ...
```

A row may carry more than one issue.

---

## 9. Per-row birth-place Search action

Each Birth Place editor must provide a **Search** action next to the place field.

Behavior must match Chart Editor's existing place search:

1. read current field text;
2. call `search_locations(query, limit=7)`;
3. if candidates exist, show a GUI-thread selection dialog;
4. when selected:
   - replace the place field with the selected display label;
   - store the candidate latitude;
   - store the candidate longitude;
   - mark the location validated;
   - clear the corresponding blocking location error;
5. if the user edits the field afterward, invalidate those stored coordinates.

If the candidate lookup itself may invoke the online geocoder, do not run that network request on the GUI thread. The worker returns candidates; the actual selection dialog remains on the GUI thread.

---

## 10. `Validate All` at the Birth Place header

At the top of the **Birth Place** column, add a visible **Validate all** action.

The requested placement is part of the column header area rather than a remote toolbar.

Implementation options:

1. custom `QHeaderView` that paints/hosts the action for the Birth Place section; or
2. a small header control aligned directly above that column if a hosted child button proves substantially more robust across platforms.

Do not place it at the bottom of the window or in an unrelated toolbar.

### 10.1 Validate All behavior

When clicked:

1. collect rows with nonblank birth-place text;
2. deduplicate normalized place strings for lookup;
3. resolve them off the GUI thread;
4. reuse session cache;
5. apply success/failure back on the GUI thread.

For each success:

- save lat/lon;
- save resolved label separately;
- set `place_valid=True`;
- clear location validation errors.

For each failure:

- clear lat/lon;
- set `place_valid=False`;
- visually flag the Birth Place cell;
- add a readable error.

Do not silently substitute `(0, 0)`.

### 10.2 Visual state

Use shared `style.py` colors/tokens.

Recommended semantics:

- success/selected: `COLOR_ACCENT_SUCCESS`;
- failure: `COLOR_ACCENT_DANGER`;
- warning: `COLOR_ACCENT_WARNING`;
- ordinary surfaces: existing dark background tokens.

If a new selected-row background or invalid-cell background is needed, define the color/token in `ephemeraldaddy/gui/style.py`. Do not scatter literal color values through the new feature.

---

## 11. Include checkbox behavior

The leftmost column is **Include**.

### 11.1 Eligibility

A row may be selected only if all of these are true:

- name is nonblank;
- birth date is a valid real calendar date;
- birth place is nonblank;
- birth place has validated coordinates.

Known birth time is **not** required.

Biography is **not** required.

### 11.2 Invalid selection attempt

Keep the checkbox interactive so the user can attempt selection and receive feedback.

If selection is attempted while a blocking field is missing/invalid, show exactly:

```text
Please correct the [missing info] field before selecting
```

Substitute the field label, for example:

```text
Please correct the birth date field before selecting
Please correct the birth place field before selecting
Please correct the name field before selecting
```

If multiple fields are invalid, identify the first blocking field in deterministic UI order:

```text
name
birth date
birth place
```

The checkbox must remain unchecked.

### 11.3 Valid selected row

When selected:

- render a green checkmark;
- change the row background to the Batch Import selected-row highlight;
- keep values editable.

If a selected row is edited so it becomes invalid:

- automatically clear its selected state;
- remove selected-row highlighting;
- retain the edited value;
- show the invalid-field appearance.

Do not allow a stale green selection to survive invalid edits.

### 11.4 Green check rendering

Qt's native checkbox appearance is platform dependent.

If necessary, use a delegate to render the checked state with `COLOR_ACCENT_SUCCESS` while retaining keyboard and mouse CheckState behavior.

---

## 12. Styling requirements

The Batch Import window must conform to the existing dark app style.

Use:

- `APPWIDE_DARK_THEME_STYLESHEET`;
- the established `COLOR_*` tokens;
- existing appwide button cursor/tone helpers;
- existing input/background/border tokens.

The current style owner is:

`ephemeraldaddy/gui/style.py`

Do not hardcode a separate independent theme in `window.py`.

If the table needs a feature-specific stylesheet, compose it from shared style tokens in `style.py`.

No light default table surface should appear during initialization, empty state, editing, selection, or header rendering.

---

## 13. Threading architecture

No external lookup, remote geocoding, or substantial multi-row chart construction may block the GUI event loop.

Follow the existing QObject → QThread patterns in the repository.

### 13.1 Worker rules

Use:

- `QObject`
- `Signal`
- `Slot`
- `QThread`
- interruption/cancellation checks
- strong references to active worker/thread objects until completion.

Do not:

- touch Qt widgets from the worker;
- call `QApplication.processEvents()` as a substitute for actual background work;
- call `QThread.terminate()`;
- allow a worker result from an old run to overwrite a newly loaded/restarted batch.

### 13.2 Run/generation identity

Give each lookup/validation run a generation or request token.

Every emitted row result should contain that token.

The controller ignores stale results whose token no longer matches the active run.

### 13.3 Cancellation

Closing the Batch Import window while work is active should:

1. request cancellation/interruption;
2. stop scheduling additional provider calls;
3. let an in-flight request return naturally;
4. drain/finish the thread safely;
5. then release worker/thread references.

Do not destroy a running QThread.

### 13.4 Sequential lookup

One batch worker should process names sequentially.

Do not create one QThread per person.

This makes provider pacing, cancellation, diagnostics, and ordering substantially easier to reason about.

---

## 14. Lookup row model

Suggested toolkit-neutral row structure:

```python
@dataclass
class BatchImportRow:
    input_index: int
    requested_name: str

    name: str
    alias: str
    from_whence: str
    tags: list[str]
    comments: str

    birth_year: int | None
    birth_month: int | None
    birth_day: int | None
    birth_hour: int | None
    birth_minute: int | None
    birthtime_unknown: bool

    birth_place: str
    validated_place_label: str
    lat: float | None
    lon: float | None
    place_valid: bool

    biography: str
    data_rating: str

    astrotheme_url: str
    wikipedia_url: str

    provider_warnings: list[str]
    blocking_errors: list[str]
    wikipedia_options: list[str]

    selected: bool
    lookup_status: str
```

Exact names may differ, but keep:

- raw requested identity;
- resolved/editable data;
- provenance;
- validation state;
- selection state;
- errors

as separate concepts.

Do not infer place validation merely from a nonblank string.

---

## 15. Source/provenance handling

The visible Sources column should identify which provider supplied useful data.

Examples:

```text
Astrotheme
Astrotheme + Wikipedia
Wikipedia
```

Store URLs in row state.

For persisted charts, `chart.chart_data_source` should retain the source URL(s), not merely the provider names.

A simple stable representation is acceptable, for example newline-separated provenance:

```text
Astrotheme: https://...
Wikipedia: https://...
```

Do not overwrite an Astrotheme birth source merely because Wikipedia supplied the biography.

---

## 16. Direct chart construction for the batch path

The current single-person Astrotheme importer drives Chart Editor fields and then calls Chart Editor's build path. That behavior is not appropriate for a batch.

Create a non-Qt `WebProfileImportService` or equivalent pure chart-construction service that applies the same rules without editing widgets.

For each selected validated row:

1. create a local naive datetime from date +:
   - factual time if known; or
   - `12:00` if time unknown;
2. use the row's already validated coordinates;
3. construct `Chart(...)` and allow normal timezone inference from coordinates;
4. attach metadata;
5. calculate the same derived dominance data required by the existing web importer;
6. save with `save_chart(...)`.

Set at minimum:

```text
chart.name
chart.alias
chart.from_whence
chart.tags
chart.comments
chart.birth_place
chart.birthtime_unknown
chart.biography
chart.chart_data_source
chart.data_rating
chart.relationship_types = ["public figure"]
chart.chart_type/source = public database source
chart.is_placeholder = FALSE
chart.auto_generated = TRUE
```

Do not duplicate dominant-sign / dominant-planet / dominant-nakshatra formulas. Call the existing calculation path.

The service should return a typed success result containing `chart_uid` and a typed failure result containing a readable error.

---

## 17. Database schema: `auto_generated`

Add a permanent chart property:

```text
auto_generated
```

Storage type:

```sql
INTEGER NOT NULL DEFAULT 0
```

Logical meaning:

```text
0 = FALSE
1 = TRUE
```

### 17.1 Meaning

`auto_generated` records **creation provenance**, not current verification status.

Once a chart has `auto_generated = TRUE`, later manually opening/editing/verifying it does not turn the value false.

This flag is intended specifically for charts created by this **automated web Batch Import workflow**.

Do not automatically mark the existing ordinary CSV Type 1 or Pattern imports true merely because they happen to process multiple rows. Those pathways ingest user-supplied structured birth data; this flag is for the new external-lookup generation workflow unless a later product decision broadens the definition.

### 17.2 Schema migration

Current branch schema version is `22`.

Bump to:

```text
SCHEMA_VERSION = 23
```

Update `_create_charts_table(...)` with:

```sql
auto_generated INTEGER NOT NULL DEFAULT 0
```

Update `_migrate_charts_columns(...)`:

```sql
ALTER TABLE charts
ADD COLUMN auto_generated INTEGER NOT NULL DEFAULT 0
```

when missing.

Add the v23 migration step in `_ensure_schema(...)`.

Because the default is `0`, every preexisting chart becomes schema-compliant as `FALSE`.

Retain the existing self-healing behavior for databases whose reported schema version and actual columns disagree.

### 17.3 `save_chart(...)`

Add an explicit keyword, for example:

```python
auto_generated: bool | None = None
```

Resolution order:

1. explicit argument when supplied;
2. otherwise `chart.auto_generated` if present;
3. otherwise false.

All existing callers therefore remain false by default.

The Batch Import path explicitly supplies true.

### 17.4 Loading

Update every chart reconstruction path so:

```text
chart.auto_generated
```

always exists.

This includes:

- normal charts;
- placeholder shells;
- compatibility projections for older schemas if any remain relevant.

Default false when absent.

### 17.5 Export/backup provenance

Treat `auto_generated` as structural/provenance data.

Add it to the appropriate database-export locked property set so a custom-property database export cannot silently reset it to false when the user excludes arbitrary metadata properties.

Full backup/restore and database append must preserve the column whenever it exists.

An older source database without the column naturally imports rows as false.

### 17.6 No Batch Editor toggle

Do not add `auto_generated` as an ordinary editable Batch Editor property.

The user audits it through filtering; it is not intended to be subjective metadata.

---

## 18. Database View lightweight row projection

Database Search should be able to filter this property without hydrating every full Chart object.

`list_charts()` currently has historical tuple positions relied on throughout Database View.

Therefore:

**append `auto_generated` to the end of the lightweight row projection. Do not insert it into the middle.**

Preserve all existing positional indices.

Then extend Database View's normalized row representation by appending the boolean at its end.

Do not shift the established indices for:

- name;
- alias;
- chart type;
- placeholder;
- birth date;
- tags;
- UID;
- weirdness metadata.

Add tests guarding this.

---

## 19. Database Search filter

Add an **Auto-generated** filter to Database View Search.

Use the existing `QuadStateSlider` convention:

```text
empty  = no criterion
true   = auto_generated only
false  = exclude auto_generated
```

The logical filter belongs near the existing Chart Type / data-completeness controls because it describes chart provenance/status rather than astrology.

### Required integration

Update:

- Search panel construction;
- `has_active_chart_filters(...)`;
- `_chart_matches_filters(...)`;
- clear/reset paths;
- any search-state snapshot/persistence path if those controls are persisted.

Use the lightweight row's appended `auto_generated` field. Do not hydrate the chart solely to answer this predicate.

Label:

**Auto-generated**

---

## 20. Import Selected & Export CSV of Failures

The bottom primary action must be labeled exactly:

**Import Selected & Export CSV of Failures**

### 20.1 Preflight

When clicked:

1. revalidate every selected row in memory;
2. clear any stale selections that no longer pass;
3. if no valid rows remain selected, show an explanatory message and do not write to the database.

### 20.2 Backup

Before the first database write:

- run `backup_database()` once;
- if backup fails, abort the import.

Do not create one backup per row.

### 20.3 Save

Process selected rows serially.

For each successful save:

- obtain the generated `chart_uid`;
- emit the UID to the GUI controller;
- mark the row imported/successful;
- do not set it as the current chart.

For each failed save:

- leave the row in the table;
- mark it failed;
- store the exception summary in Errors;
- include it in failures CSV.

### 20.4 Explicitly forbidden side effects

The Batch Import path must **not** call any of the single-profile import side effects that exist only to open the result in Chart Editor.

Do not:

- call `set_current_chart_by_uid(...)`;
- call Chart Editor `_set_current_chart_uid(...)`;
- fill Chart Editor input widgets;
- change Chart Editor's loaded birth-place coordinates;
- set Chart Editor's latest chart;
- schedule the imported chart for drawing;
- show/switch to Chart Editor;
- hide Database View.

The active/current chart should remain whatever it was before the batch operation.

---

## 21. Database View update behavior during import

The requested user experience is that newly imported charts appear in Database View's middle panel as they are added.

Use Chart UID at the feature boundary.

### 21.1 Per-chart update

After a row saves, the GUI thread may request a lightweight Database View update for that UID.

Do not trigger a complete analytics recalculation for every inserted chart.

Use the existing targeted `_refresh_charts(... changed_uids=...)` semantics or introduce a narrow Database View callback that delegates to them.

A possible controller dependency is conceptually:

```python
class BatchImportDatabaseSink(Protocol):
    def chart_added(self, chart_uid: str) -> None: ...
    def batch_finished(self, chart_uids: set[str]) -> None: ...
```

The implementation can decide the exact refresh flags.

### 21.2 Final consolidated refresh

At batch completion:

- perform one consolidated refresh for all imported UIDs;
- refresh tag completion once if imported tags changed the tag universe;
- schedule only the analytics/cache invalidation actually needed.

Do not call `force_full_analysis_refresh=True` once per chart.

### 21.3 Existing filters

Do not clear the user's Database View filters.

If an imported chart does not satisfy the current filter, it may legitimately not be visible.

The completion message may state that active filters can hide newly imported charts.

---

## 22. Failures CSV

The final action combines import + failure export.

Define “failure” carefully.

Include:

1. unresolved input rows with blocking lookup/validation errors; and
2. selected/preflight-valid rows whose chart construction/save failed.

Do not automatically classify a fully valid row that the user deliberately left unchecked as a failure.

### Suggested columns

```text
name
alias
from
tags
notes
birth_date
birth_time
birth_place
sources
bio
error
wikipedia_options
status
```

Preserve the user's manually edited values.

Use standard CSV quoting through Python's `csv` module.

If there are no failures, do not create a meaningless empty failures file. Report:

```text
All selected rows imported; no failures CSV was needed.
```

If failures exist, show a save-file dialog on the GUI thread after the import pass, with a sensible default filename such as:

```text
ephemeraldaddy_batch_import_failures_YYYY-MM-DD.csv
```

If the user cancels the save dialog, imported charts remain imported. Do not roll back valid database writes merely because the optional failure-file destination was canceled.

---

## 23. Row status semantics

Use explicit row states rather than deriving everything from cell text.

Suggested values:

```text
pending
searching_astrotheme
searching_wikipedia
lookup_complete
needs_manual_review
validating_place
ready
selected
importing
imported
failed
```

The exact enum names may vary.

Do not overload the Errors string as the only source of truth.

---

## 24. Duplicate handling

The current single-person web import asks for duplicate confirmation interactively.

A per-row modal duplicate dialog is not suitable for a large background batch.

Before writing, use the existing duplicate-detection logic through a non-Qt service if available.

Preferred behavior:

- flag likely duplicates in the table as a nonblocking or blocking review state before import;
- do not silently replace an existing chart;
- allow the user to leave a suspected duplicate unchecked.

Do not introduce a new duplicate algorithm as part of this task if the existing one can be called behind a narrow helper.

If extracting the existing duplicate check would make the first implementation disproportionately broad, record duplicate preflight as a bounded follow-up and make `save_chart(...)` remain insert-only. Do not silently update/overwrite an existing chart.

---

## 25. Error handling

Network/provider failures are row-level unless the application itself cannot continue safely.

Examples:

### Row-level

- Astrotheme profile missing;
- Astrotheme markup unsupported;
- Wikipedia missing;
- Wikipedia ambiguous;
- biography unavailable;
- one place fails validation;
- one chart fails to construct/save.

### Batch-level

- database backup cannot be created;
- database unavailable/corrupt;
- worker infrastructure cannot start;
- source CSV cannot be parsed at all.

One failed person must not discard successful results for other people.

---

## 26. Logging

Use structured, non-sensitive logs with a per-batch request ID and per-row index.

Useful events:

```text
batch lookup started
provider lookup started
provider result
provider warning/error
place validation result
selection rejected
chart save started
chart save completed with UID
chart save failed
batch canceled
batch completed
failure CSV saved
```

Do not log entire biography text.

Do not log private CSV notes unless needed for an explicitly handled diagnostic; names and public source URLs are sufficient for ordinary lookup logs.

---

## 27. Tests

Add focused behavioral tests. Do not rely only on source-string tests.

### 27.1 Lookup service

Test:

- Astrotheme success wins for birth data;
- Wikipedia biography enriches Astrotheme result;
- Astrotheme not-found falls back to Wikipedia;
- Astrotheme format error falls back;
- Astrotheme network failure on one row does not end the batch;
- Wikipedia single result;
- Wikipedia not found;
- Wikipedia multiple result becomes manual-review error;
- Wikipedia multiple candidates + exactly one factual date match resolves automatically;
- zero matching dates remains ambiguous;
- two matching dates remains ambiguous;
- biography failure is nonblocking when birth data remain valid.

Mock provider functions. Do not hit live sites in tests.

### 27.2 Request pacing

Test with injected clock/wait functions:

- minimum interval enforced;
- jitter remains within configured bounds;
- cancellation interrupts wait;
- `Retry-After` overrides normal interval when longer;
- one provider's pacing state does not corrupt another provider's state.

### 27.3 CSV

Test:

- pasted-name parsing;
- case-insensitive `name` header;
- `alias`, `from`, `tags`, `notes` retained;
- input order retained;
- repeated names retained;
- failures export is valid CSV;
- manual edits appear in failures export;
- valid unchecked rows are not classified as failures;
- prior failures CSV can be reloaded where supported.

### 27.4 Row validation

Test:

- blank name rejected;
- impossible calendar date rejected;
- unknown birth time is valid;
- blank birthplace rejected;
- unvalidated birthplace rejected;
- validated birthplace allows selection;
- editing validated place text invalidates coordinates;
- selected row automatically deselects if made invalid;
- rejected selection reports the requested warning text.

### 27.5 Validate All

Test:

- duplicate place strings are geocoded once per session cache;
- local lookup success;
- online failure marks only affected rows;
- failures retain visible error state;
- cancellation prevents remaining lookups;
- no `(0, 0)` fallback.

### 27.6 Schema migration

Add migration coverage for v23:

- v22 database upgrades to v23;
- preexisting rows read `auto_generated = 0`;
- `_create_charts_table` includes the column;
- self-healing migration adds the column even if `user_version` is already high;
- explicit `save_chart(... auto_generated=True)` persists true;
- ordinary `save_chart(...)` persists false;
- chart loading exposes boolean `chart.auto_generated`;
- custom database export preserves provenance;
- backup/restore preserves provenance.

### 27.7 Database View row compatibility

Test that appending `auto_generated` to `list_charts()` does not shift the historical tuple fields.

Test the normalized lightweight Database View row index explicitly.

### 27.8 Search filter

Test `Auto-generated`:

- empty mode matches both;
- true mode matches only true;
- false mode excludes true;
- clearing filters resets it;
- predicate uses lightweight row data without requiring full chart hydration.

### 27.9 Window chrome

Add a focused source/behavior test asserting:

```text
Delete chart(s)
Batch Import
Current Transits
```

in that order in Database View's Charts menu.

### 27.10 Import integration

With providers/geocoder/database mocked:

- selected valid rows save;
- unselected valid rows do not save;
- invalid rows do not save;
- `auto_generated` true only on this path;
- tags/from/notes/alias persist;
- unknown time persists correctly;
- `chart_data_source` preserves provenance;
- batch import does not call `set_current_chart_by_uid`;
- batch import does not render/open Chart Editor;
- Database View receives newly saved Chart UIDs;
- one save failure does not stop later rows;
- failures list contains the failed row.

---

## 28. Manual verification

Before declaring complete:

1. launch on macOS and Windows if available;
2. open Database View;
3. verify Charts menu order;
4. open Batch Import;
5. verify every surface is dark-themed;
6. paste 3–5 names including:
   - an Astrotheme hit with birth time;
   - a Wikipedia fallback;
   - a deliberately ambiguous common name;
   - a nonexistent name;
7. verify UI remains responsive during lookup;
8. edit a date to an impossible date and confirm selection is refused;
9. repair the date;
10. edit a birthplace and confirm old validation is cleared;
11. use its Search button;
12. run Validate all;
13. confirm failed places are visually obvious;
14. select valid rows;
15. import;
16. confirm Database View remains the foreground/default work area;
17. confirm no imported chart opens in Chart Editor;
18. confirm the previous current chart remains current;
19. confirm rows appear in Database View when current filters permit them;
20. enable Search → Auto-generated=true and confirm the batch-created charts appear;
21. switch Auto-generated=false and confirm they are excluded;
22. reopen one imported chart manually and verify birth-time semantics;
23. verify alias/from/tags/notes from CSV;
24. verify the failure CSV contains unresolved/failed rows and current manual edits;
25. close the Batch Import window while a lookup is active and verify clean worker shutdown.

---

## 29. Performance requirements

This workflow is intentionally a background task.

Measure at least:

- Batch Import window open time;
- GUI-thread blocking during active lookup;
- average remote request interval;
- Validate All geocoder request count versus number of unique place strings;
- Database View refresh count for an N-row import;
- number of full analysis refreshes.

Acceptance target:

- no network call on GUI thread;
- no online geocode call on GUI thread;
- no full Database View analysis refresh per imported row;
- duplicate location strings reuse cache;
- the UI remains interactive during provider delays.

---

## 30. Implementation phases

Keep commits/review slices bounded.

### Phase 1 — Data/service foundation

- establish web-profile models;
- establish canonical lookup service;
- add provider pacing/backoff;
- add pure import/chart construction service;
- add service tests.

No new GUI yet.

### Phase 2 — Database provenance

- add schema v23;
- add `auto_generated`;
- update `save_chart`;
- update load/projection/defaults/export behavior;
- add migration/persistence tests.

### Phase 3 — Database Search audit filter

- append `auto_generated` to lightweight chart rows;
- add Search `Auto-generated` QuadStateSlider;
- update active-filter/matching/reset paths;
- add tests.

### Phase 4 — Batch Import window

- models/table;
- paste + CSV input;
- lookup worker;
- editable result cells;
- per-place Search;
- Validate all;
- selection validation;
- styling;
- cancellation/lifecycle.

### Phase 5 — Save + failures export

- one pre-import backup;
- direct chart construction;
- direct `save_chart(... auto_generated=True)`;
- UID callbacks to Database View;
- failures CSV;
- no Chart Editor side effects.

### Phase 6 — Window chrome integration

- add **Batch Import** directly below **Delete chart(s)**;
- use lazy feature opener;
- add menu-order regression test.

### Phase 7 — Final regression review

- run focused test suite;
- compile changed Python modules;
- manually inspect the final diff;
- trace every new callback;
- verify no new public chart-ID API;
- verify no remote call runs on GUI thread;
- verify no new substantive implementation landed in `app.py`;
- verify current single-person Astrotheme/Wikipedia import still works.

---

## 31. `app.py` scope limit

This branch is actively extracting workflow code from `app.py`.

For this feature:

### Allowed

A small adapter may be added to legacy Database View code if it is currently the only place that can provide:

- a narrow “chart added” refresh callback;
- a narrow opener callback;
- existing calculation dependency injection.

### Not allowed

Do not put these in `app.py`:

- Batch Import window construction;
- table model;
- CSV parsing;
- web lookup loop;
- request pacing;
- geocoder worker;
- row validation;
- failures export;
- schema logic;
- selection rules;
- source-resolution logic.

If a legacy method must be called, wrap it behind a narrow typed callback or Protocol and leave the implementation in the feature package.

---

## 32. Acceptance criteria

The feature is complete only when all of the following are true.

### Menu/window

- [ ] Database View → Charts has **Batch Import** directly below **Delete chart(s)**.
- [ ] It opens a separate window.
- [ ] The window uses appwide dark-theme/style tokens.
- [ ] Database View remains usable while lookups run.

### Input/lookup

- [ ] Pasted names work.
- [ ] CSV names work.
- [ ] CSV `tags`, `from`, `notes`, `alias` survive import.
- [ ] Astrotheme is tried first.
- [ ] Wikipedia is the fallback.
- [ ] Multiple Wikipedia candidates are never silently guessed.
- [ ] Results appear incrementally.
- [ ] Lookup runs off the GUI thread.
- [ ] Provider requests are single-threaded and paced.
- [ ] 429/503 backoff is supported where applicable.

### Table/editing

- [ ] Name/date/time/place/bio are editable.
- [ ] Every place field has a Search action.
- [ ] Birth Place header has **Validate all**.
- [ ] Invalid places are visually flagged.
- [ ] Invalid dates are visually flagged.
- [ ] Unknown birth time is valid.
- [ ] Editing a validated place invalidates its old coordinates.

### Selection

- [ ] Include checkbox refuses incomplete/unparseable rows.
- [ ] Warning text follows `Please correct the [missing info] field before selecting`.
- [ ] Valid checked rows show a green checkmark.
- [ ] Selected rows use the designated highlighted row background.
- [ ] A selected row auto-deselects if edited into invalid state.

### Import

- [ ] Button label is exactly **Import Selected & Export CSV of Failures**.
- [ ] One database backup occurs before writes.
- [ ] Valid selected charts save directly.
- [ ] Imported charts do not open in Chart Editor.
- [ ] Current chart does not change.
- [ ] Database View receives new Chart UIDs and refreshes efficiently.
- [ ] One failed save does not end the remainder of the batch.
- [ ] Failures CSV preserves manual edits and optional metadata.

### Provenance

- [ ] Schema version is 23.
- [ ] `auto_generated` is NOT NULL and defaults to false.
- [ ] All preexisting charts become false.
- [ ] Ordinary chart creation remains false.
- [ ] This automated Batch Import path saves true.
- [ ] Loaded Chart objects always expose `auto_generated`.
- [ ] Provenance survives backup/export/restore.
- [ ] Search has an **Auto-generated** tri-state audit filter.
- [ ] `auto_generated` is not casually editable as subjective Batch Editor metadata.

### Architecture

- [ ] New feature logic lives outside `app.py`.
- [ ] Provider/network logic has no Qt dependency.
- [ ] Qt widgets are mutated only on the GUI thread.
- [ ] New workflow interfaces use Chart UID.
- [ ] Worker shutdown is clean and cancellable.
- [ ] Existing single-profile Astrotheme/Wikipedia import remains functional.
- [ ] Focused regression tests pass.

---

## 33. Final review instruction

Before completing the implementation, reread this handoff and the original product requirement and review the final diff as if authored by someone else.

Specifically inspect for these common failure modes:

- an invalid row can still be selected;
- a place edit retains old coordinates;
- Wikipedia ambiguity is silently resolved;
- unknown time gets stored as factual noon;
- a provider error ends the entire batch;
- imported charts accidentally become current;
- Chart Editor opens once per imported chart;
- Database View performs a full expensive refresh per row;
- `auto_generated` is missing from a chart-loading path;
- the v23 migration fails to mark legacy rows false;
- custom database export strips `auto_generated`;
- a historical `list_charts()` tuple index shifted;
- online geocoding is called in parallel or faster than policy permits;
- a background worker touches widgets;
- closing the window destroys an active QThread;
- the new UI contains ad-hoc styling instead of `style.py` ownership.

Passing tests is necessary but not sufficient. Trace the actual state transitions from input → provider result → manual edit → place validation → selection → chart construction → save → UID refresh → failures export.
