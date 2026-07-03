# Birth Time and Birth Place Calculation Protocol

This document records the working protocol for converting a user's birth date, birth time, and birth place into the datetimes and coordinates used by EphemeralDaddy's chart calculations. It exists because earlier approaches produced confusing or site-mismatched results; the current protocol matches the behavior expected by major astrology sites because it treats the entered time as **local civil birth time at the resolved birthplace**, then lets standard timezone and ephemeris libraries do the UTC conversion.

## Executive summary

1. **Birth place is resolved first.** A place string is geocoded to latitude/longitude, preferring the local GeoNames gazetteer and falling back to Nominatim only when allowed.
2. **Timezone comes from the coordinates.** For normal chart creation, the app does not ask the user to manually choose an offset. It infers an IANA timezone from the resolved latitude/longitude with `timezonefinder`, then wraps that name in `zoneinfo.ZoneInfo`.
3. **The entered birth time is local wall time.** A naive `datetime` such as `1990-04-12 08:30` means “8:30 AM at the birthplace,” not UTC and not the computer's current timezone.
4. **The chart stores an aware datetime.** `Chart` attaches the inferred or explicit timezone and keeps `chart.dt` timezone-aware.
5. **Planet and house calculations convert to UTC internally.** Swiss Ephemeris and Skyfield receive the correct instant after `chart.dt` is converted from local time to UTC.
6. **Unknown birth time is factual uncertainty.** The UI uses noon as the neutral date-preserving placeholder, but time-specific chart facts are disabled unless the chart has a known birth time or the user explicitly enables rectified time.
7. **Rectified time is a hypothesis, not a fact.** If enabled, it can be used for time-dependent calculations, but the chart still knows the original birth time was unknown.

## Birth place protocol

### 1. Normalize a human-readable place into coordinates

The canonical user input is a human-readable birthplace, e.g. `Alexandria, Egypt`, `Chicago, IL, USA`, or another city/region/country string. The app resolves that string through `geocode_location()`.

Resolution order:

1. `local_geocode_location(query)` searches the local gazetteer.
2. If the local gazetteer has a match, its `(latitude, longitude, label)` is used immediately.
3. If the local gazetteer has no match and gazetteer-only mode is not enabled, the app falls back to online Nominatim geocoding.
4. If the place cannot be resolved, the GUI asks whether to abandon the location and use the hard fallback `lat=0.0`, `lon=0.0`, `UTC`.

The local gazetteer is intentionally first because it is fast, offline-friendly, deterministic, and backed by GeoNames city data. The search ranks by population and label, so precise place strings are preferred; ambiguous strings should be made more specific by adding region/country.

### 2. Coordinates are the authoritative location data

Once a place has been geocoded, the coordinates become the canonical location used by calculations:

- latitude is positive north and negative south;
- longitude is positive east and negative west;
- the formatted place label may be saved back into the UI/database for clarity;
- if saved coordinates already exist for a chart, those coordinates may be reused instead of re-geocoding the text label.

Do not derive coordinates from a timezone name. A timezone is too broad for house cusps and angles; the app needs the actual latitude/longitude of the birthplace.

## Birth timezone protocol

### 1. Infer timezone from latitude/longitude

For normal chart creation, `Chart` receives a naive local datetime plus latitude/longitude and no timezone override. It calls `localize_naive_datetime()`, which in turn calls `timezone_from_latlon()`.

`timezone_from_latlon()`:

1. validates latitude and longitude ranges;
2. asks `timezonefinder.TimezoneFinder.timezone_at(lat=..., lng=...)` for an IANA timezone name;
3. if that fails near borders/coastlines, tries `certain_timezone_at(...)`;
4. returns `ZoneInfo(name)` and `inferred_ok=True` when successful;
5. returns `ZoneInfo("UTC")` and `inferred_ok=False` when inference fails.

When inference fails, `chart.used_utc_fallback` is set so the UI/database can warn that the chart did not receive a reliable local timezone.

### 2. Use real timezone rules, not fixed offsets

The correct timezone is an IANA zone such as `America/New_York`, not a hand-entered `-05:00` offset. IANA zones contain historical daylight-saving and legal timezone changes, which are required for old charts, DST transitions, and locations whose offsets changed over time.

The current implementation attaches `ZoneInfo` directly to the local civil datetime. That is the intended behavior for the app's astrology-site parity: preserve the birth clock time as entered for the birthplace, then let downstream calculations convert that local aware datetime to UTC.

## Birth time protocol

### 1. Known birth time

For a known birth time:

1. The UI builds a naive `datetime` from the selected date and time.
2. The place is resolved to coordinates.
3. `Chart(name, dt_local, lat, lon, tz=None)` is created.
4. `Chart` infers the timezone from coordinates and attaches it to the naive local datetime.
5. Planet positions, retrogrades, Placidus houses, Ascendant, Midheaven, Descendant, IC, Part of Fortune, and aspects are calculated from that aware datetime.

This means `08:30 in Chicago` is treated as Chicago local time on that date, including the correct historical timezone/DST behavior supplied by `ZoneInfo("America/Chicago")` after coordinate-based inference.

### 2. Unknown birth time

For an unknown birth time, the app uses **12:00 local/noon** as a neutral placeholder so date-based planetary positions can still be calculated without systematically biasing them toward the previous or next day.

However, noon fallback is not treated as a real birth time. The chart is marked with `birthtime_unknown=True`, and `chart_uses_houses(chart)` resolves to false unless rectified time is enabled. When birth time data is not allowed, the app sanitizes time-specific metadata by removing:

- Placidus and Porphyry houses;
- Ascendant, Midheaven, Descendant, and IC;
- aspects involving those angles.

This is the key distinction: **noon may be used to preserve a date for non-time-specific positions, but houses and angles must not be treated as factual for unknown-time charts.**

### 3. Rectified time

If a chart has unknown birth time but the user enables rectified time, `retcon_time_used=True` and the stored `retcon_hour`/`retcon_minute` are allowed to drive time-specific calculations. The effective datetime is the chart date with the rectified hour/minute substituted.

Rectified time should always be documented and understood as provisional. It can support exploratory features, but algorithms that require facts rather than hypotheses should continue checking `birthtime_unknown`, `retcon_time_used`, and especially `chart_uses_houses(chart)` before using houses or angles.

## Calculation pipeline

### Planetary positions

`Chart` calculates planetary positions from the aware local datetime. The ephemeris layer converts to the instant required by the underlying astronomy libraries. This keeps the public app protocol simple: callers supply local birthplace time, not UTC.

### Placidus houses and angles

Placidus houses and primary angles are calculated with Swiss Ephemeris:

1. `recompute_time_specific_metadata()` gets the effective chart datetime.
2. It calls `placidus_houses_and_axes(dt_effective, lat, lon)`.
3. The house code converts `dt_effective` to UTC.
4. It computes Julian day UT with Swiss Ephemeris.
5. It calls `swe.houses(jd_ut, lat, lon, b"P")` for Placidus cusps and Asc/MC.
6. The app derives DS and IC as the opposite points of AS and MC.

This is the major reason the current results align with official astrology sites: Swiss Ephemeris receives the correct UTC instant and the actual birthplace coordinates.

### Sidereal time / Porphyry comparison data

The app also keeps Porphyry house data for internal comparison/fallback contexts. Local sidereal time is computed from the aware datetime converted to UTC plus geographic longitude. Placidus from Swiss Ephemeris remains the authoritative house system for natal chart output.

## Import and fallback behavior

### Native database rows

Native rows store `datetime_iso`, `tz_name`, `lat`, `lon`, and `used_utc_fallback`. On load, the stored aware datetime and coordinates are used to reconstruct the chart. If stored metadata says UTC fallback was used, that warning remains attached to the chart.

### Pattern / legacy imports

Some import formats provide a `birthtimezone` rather than a birthplace. In that legacy path, the app may infer a rough place string from the timezone's final segment and geocode that. This is a compatibility path, not the preferred protocol. Preferred data should include the actual birthplace and/or coordinates.

If an import row is missing date, time, timezone, or place data badly enough that the app cannot resolve a real local chart context, it uses `12:00 UTC` at `(0.0, 0.0)` and marks `used_utc_fallback` so the row is visibly lower confidence.

## Do / don't checklist

### Do

- Do treat user-entered birth time as local civil time at the birthplace.
- Do geocode the birthplace before inferring timezone.
- Do infer an IANA timezone from coordinates.
- Do keep `chart.dt` timezone-aware.
- Do let Swiss Ephemeris/Skyfield convert to UTC internally.
- Do use `chart_uses_houses(chart)` before relying on houses, angles, Part of Fortune, or angle aspects.
- Do preserve `birthtime_unknown=True` even when rectified time is enabled.
- Do warn when `used_utc_fallback=True`.

### Don't

- Do not treat entered birth time as UTC.
- Do not use the user's current computer timezone for a birth chart.
- Do not use a fixed offset when an IANA timezone can be inferred.
- Do not derive house cusps from timezone alone; use latitude and longitude.
- Do not treat noon fallback as a factual birth time.
- Do not use rectified time silently in algorithms that are meant to be factual only.
- Do not rely on legacy `ID` references when documenting chart records; use UID terminology.

## Quick examples

### Known time

Input:

- date: `1990-04-12`
- time: `08:30`
- place: `Chicago, IL, USA`

Protocol:

1. Geocode Chicago to latitude/longitude.
2. Infer `America/Chicago` from those coordinates.
3. Store `1990-04-12 08:30` with `America/Chicago` timezone rules.
4. Convert to UTC only inside ephemeris/house calculations.
5. Houses and angles are allowed because the birth time is known.

### Unknown time

Input:

- date: `1990-04-12`
- time: unknown
- place: `Chicago, IL, USA`

Protocol:

1. Geocode Chicago to latitude/longitude.
2. Infer `America/Chicago`.
3. Use `1990-04-12 12:00` local as the placeholder calculation time.
4. Mark `birthtime_unknown=True`.
5. Remove houses/angles unless rectified time is enabled.
6. Show conditional unknown-sign indicators when relevant.

### Unknown time with rectified time

Input:

- date: `1990-04-12`
- time: unknown
- rectified time: `08:30`
- place: `Chicago, IL, USA`

Protocol:

1. Keep factual unknown-time status.
2. Use `08:30` as the effective exploratory time for house/angle calculations.
3. Continue labeling the chart as rectified/provisional where appropriate.

## Source-of-truth code map

- Birthplace geocoding: `ephemeraldaddy/io/geocode.py`
- Local GeoNames gazetteer: `ephemeraldaddy/io/local_gazetteer.py`
- Timezone inference and local datetime localization: `ephemeraldaddy/core/timeutils.py`
- Chart construction, unknown-time policy, rectified-time policy: `ephemeraldaddy/core/chart.py`
- Swiss Ephemeris Placidus house calculation: `ephemeraldaddy/core/houses.py`
- Chart View form behavior for known/unknown/rectified times: `ephemeraldaddy/gui/app.py`
- CSV/pattern import compatibility behavior: `ephemeraldaddy/gui/features/import_export/`
