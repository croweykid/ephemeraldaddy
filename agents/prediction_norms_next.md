# Prediction Norms: Decisions and Next Migrations

## Current source contract

- **Official** is the read-only catalog bundled with the application.
- **My Database** is a user-generated population snapshot in
  `~/.ephemeraldaddy/.prediction_norms_snapshot.json`.
- Population sources are alternatives, not overlays. A lookup reads exactly
  one of them.
- Recalculate DB Norms is the only operation allowed to scan the full database
  to replace **My Database**. Ordinary chart changes must never trigger that
  scan.
- While **Official** is selected, norms for user-created Traits live in the
  separate `~/.ephemeraldaddy/.prediction_norms_trait_extensions.json` store.
  This extension may add custom Trait rows only; it must not override other
  Official predictor sections.
- Norm generation and invalidation must remain UID-first and must preserve the
  `chart_uses_houses` distinction. Rectified times are not reliable-house data.

## Catalog schema work

Replace the transitional flat version-1 catalog with named predictor sections:

1. Traits
2. Enneagram
3. Fantasy RPG
4. Distinguishing Factors
5. HD Electrochemistry

Each section must carry its own:

- sample size;
- scoring/algorithm version;
- reliable-house and no-house sample counts;
- generation timestamp;
- complete provenance (source database/snapshot and generation method).

Trait rows must preserve author-supplied metadata, including `sample_sizes`
and the new `type` value (`theoretical` or `observed`). These fields describe
the author's model and must not be replaced with automated prose.

## Default Trait developer pipeline

Add an explicitly developer-only Settings > Developer Tools workflow that can:

1. compare the current bundled `default_traits` definitions with the Official
   catalog by stable Trait UID and analytical profile hash;
2. report added, removed, and analytically changed definitions without doing
   work merely because display text changed;
3. calculate only missing or analytically changed Trait baselines against the
   developer database;
4. stage and validate a new Official catalog for packaging; and
5. refuse to overwrite the installed Official file from consumer workflows.

The existing command-line bundling helper remains the final packaging gate
until that developer UI is implemented.

## Predictor migrations before removing remaining live paths

- Migrate Enneagram and Fantasy RPG away from legacy `norm_charts_provider`
  fallbacks into their static catalog sections.
- Migrate HD Electrochemistry's separate background norm system into its static
  catalog section.
- Add the Distinguishing Factors section and route it through the same explicit
  source selection.
- Only after each predictor has a complete, versioned static section should its
  live-cohort fallback be deleted. Do not disconnect a fallback while it is the
  only mechanism producing a genuinely database-relative result.
- Audit the applicable concerns in
  `agents/ephemeraldaddy_uid_migration_performance_diagnosis.md` before building
  new bulk loaders or caches. Do not reintroduce ID-first joins, repeated
  ID-to-UID translation, per-chart queries, or broad revision invalidation.

## Ranking follow-up

Keep ranking caches incremental through the durable chart change journal:
score only UIDs added or analytically edited since the cache high-water mark,
remove deleted UIDs, then re-sort the saved scores. Non-astral metadata changes
must not invalidate astrological rankings.
