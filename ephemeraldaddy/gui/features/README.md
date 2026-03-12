# GUI Feature Slices

This package holds the ongoing decomposition of `ephemeraldaddy/gui/app.py` into focused, feature-aligned modules.

## Ownership boundaries

- `controllers/`
  - Main-window orchestration and lifecycle coordination.
  - Should not contain business logic for astrology, scoring, or DB queries.
  - Should delegate to workers/helpers/adapters and keep methods small.

- `charts/`
  - Manage Charts view-specific widgets/delegates/dialog helpers.
  - Keep chart-list presentation and interactions local to this slice as extraction progresses.

- `import_export/`
  - Pure parsing/formatting helpers for CSV/import/export pathways.
  - Keep these modules Qt-free and side-effect-light to allow headless tests.

- `retcon/`
  - Retcon-related workers and feature-specific execution paths.
  - Workers should prefer dependency injection/lazy resolution for heavy dependencies.

- `coordination/`
  - Cross-feature communication primitives (in-process pub/sub/request patterns).
  - Avoid introducing this dependency unless a real cross-feature workflow needs it.

## Practical guidelines

- Prefer vertical-slice extraction: move one workflow at a time.
- Preserve behavior first; optimize only after parity is stable.
- Keep `app.py` call sites stable during migrations, then remove compatibility layers.
- Avoid import-time heavy initialization in feature modules when possible.
