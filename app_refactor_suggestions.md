# `ephemeraldaddy/gui/app.py` Refactor Suggestions (Revised)

This revision reflects your feedback:

- Keep **transit workflow out of scope for now**.
- Prioritize **dialog extraction** and **MainWindow controllers**.
- Clarify whether helper extraction belongs in `style.py`.

## Quick call on `style.py` vs `formatting.py`

Short answer: they should stay separate.

- `ephemeraldaddy/gui/style.py` currently contains **visual/theme constants** (QSS snippets, sizing constants, app settings, text constants).
- The `_format_*`, `_sign_*`, `_aspect_*`, and prevalence/weight helpers in `app.py` are mostly **data/label/domain formatting + metric calculations**, not appearance styling.

### Recommendation

- Keep `style.py` as the design-system surface for recurring UI aesthetics.
- Create a distinct helper module, but use a less confusing name than `formatting.py` if preferred:
  - `ephemeraldaddy/gui/features/charts/presentation.py` (recommended)
  - or `ephemeraldaddy/gui/features/charts/labels.py`

This avoids turning `style.py` into a mixed “theme + logic” bucket.

## Revised extraction priorities

### 1) Dialog-heavy features (do this now)

You asked whether to use one `dialogues.py` or three modules. Both are valid; here are the tradeoffs.

#### Option A: single module (`ephemeraldaddy/gui/features/dialogues.py`)

**Pros**
- Fastest to implement.
- One import surface while refactor is still moving.
- Good if dialogs share lots of utility code and are still evolving quickly.

**Cons**
- Can become another monolith if you keep adding dialogs.
- Feature ownership boundaries stay blurry.
- Merge conflicts increase as multiple features touch the same file.

#### Option B: one module per feature

- `ephemeraldaddy/gui/features/charts/dialogs.py`
- `ephemeraldaddy/gui/features/retcon/dialogs.py`
- `ephemeraldaddy/gui/features/familiarity/dialogs.py`

**Pros**
- Clear feature boundaries and ownership.
- Easier long-term navigation and review.
- Lower conflict risk with parallel work.

**Cons**
- Slightly more boilerplate and import wiring.
- More files up front.

#### Practical recommendation

Start with **Option A (single `dialogues.py`) now** for speed, but set a threshold:

- If file exceeds ~800 lines or >5 dialogs, split to feature-local modules.

That gives immediate progress without committing to another giant file.

### 2) MainWindow controllers (do this now)

Keep `MainWindow` as composition root and push behavior into controllers:

- `ChartAnalysisController`
- `ImportExportController`
- `ChartsLibraryController`

(Transit intentionally excluded for now.)

Suggested home: `ephemeraldaddy/gui/features/controllers/`.

## Migration mechanics (unchanged, still best path)

Use **extract + delegate + delete** in small batches:

1. Move implementation into module/controller.
2. Keep method names in `MainWindow`, delegate internally.
3. Run smoke checks.
4. Remove dead code once stable.

## Immediate implementation sequence

1. Extract `ManageChartsDialog`, `RetconEngineDialog`, and `FamiliarityCalculatorDialog` into a new single module: `ephemeraldaddy/gui/features/dialogues.py`.
2. Introduce `ChartAnalysisController`, move chart-analysis methods from `MainWindow` via delegation.
3. Introduce `ChartsLibraryController` for library CRUD wiring.
4. Introduce `ImportExportController` for CSV/import/export flows.
5. Move helper/label/metric functions into `ephemeraldaddy/gui/features/charts/presentation.py` (not `style.py`).

## Updated “done” targets

- `app.py` < 5,000 lines (first milestone).
- `MainWindow` < 60 methods (first milestone).
- Transit workflow remains in `app.py` until dedicated design pass is complete.
- No new business logic added to `style.py`.
