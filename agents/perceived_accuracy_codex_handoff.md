# Perceived Accuracy Feedback — Codex Handoff

**Status:** Persistence foundation completed; GUI/settings integration remains  
**Intended next step:** Merge the current persistence PR, then implement the work below in a **new PR from updated `main`**.  
**Primary architectural constraint:** Do not solve this by expanding `ephemeraldaddy/gui/app.py` with another feature blob.

## 1. Read this first

Before changing code, read:

- `agents/app_py_refactor_manifesto.md`
- `ephemeraldaddy/core/perceived_accuracy.py`

Follow the workflow-first ownership rules in the manifesto. In particular, new perceived-accuracy UI behavior should have an explicit owner and a narrow interface. Keep `app.py` changes to minimal integration hooks where legacy structure makes them unavoidable.

Do **not** undertake a broad `app.py` refactor in this PR. Extract only the bounded seams needed to implement this feature safely.

## 2. What the current PR already provides

The current PR adds `ephemeraldaddy/core/perceived_accuracy.py`. Treat it as the persistence API to reuse, not something to replace casually.

Current behavior:

- Ratings are subjective chart-scoped metadata stored separately from the astronomical chart payload.
- Ratings are keyed by stable `chart_uid`.
- The persistence root is `perceived_accuracy`.
- There are deliberately separate namespaces:
  - `modules`
  - `properties`
- A rating record contains:
  - `value`: actual JSON/Python boolean
  - `version`: positive integer
  - `rated_at`: UTC timestamp
- `get_perceived_accuracy_value(...)` returns `True`, `False`, or `None`.
- `toggle_perceived_accuracy(...)` implements the required three-state behavior.
- Clicking the already-selected value removes that target entry completely.
- If the final rating for a chart is cleared, the chart's perceived-accuracy metadata row is deleted.

Conceptual payload:

```json
{
  "perceived_accuracy": {
    "modules": {
      "dnd_species": {
        "value": true,
        "version": 1,
        "rated_at": "2026-08-31T12:04:22Z"
      }
    },
    "properties": {
      "moon_sign:aries": {
        "value": false,
        "version": 1,
        "rated_at": "2026-08-31T12:10:00Z"
      }
    }
  }
}
```

### Required toggle semantics

| Current state | Click | Result |
| --- | --- | --- |
| unrated | 👍 | `True` |
| unrated | 👎 | `False` |
| 👍 | 👍 | unrated; delete entry |
| 👎 | 👎 | unrated; delete entry |
| 👍 | 👎 | `False`; replace record/update timestamp |
| 👎 | 👍 | `True`; replace record/update timestamp |

**Important:** "unrated" means absence of a stored target record. Do not introduce `value: null`, `cleared_at`, tombstones, rating history, or other retained clear-state data.

## 3. Goal of the next PR

Complete the user-facing perceived-accuracy controls in three places:

1. Chart Editor collapsible module headers.
2. Chart Information presentation for the currently displayed property/interpretation.
3. Settings > Display Preferences > a new **User Feedback** section.

The feature is deliberately low-friction: two thumbs and three states. Do not add comment dialogs, reason prompts, confidence sliders, confirmation dialogs, or analytics UI in this PR.

## 4. Architecture: keep this out of the monolith

First locate the actual current owners of:

- Chart Editor collapsible headers;
- the reusable Chart Information presenter/panel and the Chart Editor info-tabs host;
- Display Preferences construction and persistence;
- the existing Astro Twin perceived-accuracy setting;
- the active chart UID exposed to Chart Editor/Chart Information.

Do not guess ownership from old names. The manifesto establishes the preferred terminology:

- `ChartEditorWindow` for the individual-chart editor;
- `ChartInformationPresenter` / `ChartInformationPanel` for reusable Chart Information behavior;
- `ChartEditorInfoTabs` for the Chart Editor tab host.

Legacy names may still exist. Search first, then make the smallest safe integration.

### Shared thumbs control

Implement the 👍/👎 behavior once and reuse it.

Preferred shape:

- a small dedicated widget/controller with two `QToolButton`-style controls;
- a narrow target model or explicit arguments containing:
  - `chart_uid`
  - scope (`modules` or `properties`)
  - stable target key
  - version
- one method to refresh selected/unselected state from persistence;
- one action path that calls `toggle_perceived_accuracy(...)` and immediately reflects its returned `True` / `False` / `None` state;
- a clean way to retarget the control when Chart Information changes to a different property;
- visibility controlled by the global Display Preferences flag.

If the repository has an established shared-widget location, use it. Otherwise prefer a narrowly named perceived-accuracy feature module/package over generic `helpers`, `utils`, or dumping the implementation into `app.py`.

Do not make a controller accept an entire top-level window merely to reach arbitrary attributes. Use explicit values/callbacks or a small Protocol/view interface where appropriate.

## 5. Chart Editor module-header controls

Add 👍 and 👎 to the **right side of every applicable collapsible Chart Editor module header**.

Requirements:

- The controls must not interfere with expanding/collapsing the header.
- Use scope `modules`.
- Every module must have a stable semantic key independent of its visible label.
- Do not derive persistence keys from translated/display text.
- Existing saved rating state must be rendered whenever a chart is opened/refreshed.
- Switching charts must retarget/reload the buttons correctly.
- Clicking the selected thumb again must visibly return both buttons to the unrated state after persistence removes the entry.
- The controls must disappear when the global User Feedback display setting is off.

Centralize this at the common collapsible-header construction layer if one exists. Do not hand-wire dozens of copies unless the current architecture genuinely has no common seam; if that is the case, make a bounded reusable seam as part of this PR rather than duplicating logic throughout `app.py`.

### Module version

`toggle_perceived_accuracy(...)` accepts an integer `version` and currently defaults to `PERCEIVED_ACCURACY_VERSION`.

For this PR:

- use an existing interpretation/module revision if the module already exposes one;
- otherwise use the current perceived-accuracy version constant rather than inventing an elaborate version registry;
- keep the call site structured so a module-specific revision can be supplied later.

## 6. Chart Information property controls

Add 👍/👎 controls to the **upper-right corner of the Chart Information panel/presentation**.

The rating applies to **the specific property or interpretation currently being displayed**, not to "Chart Info" as one whole module.

Requirements:

- Use scope `properties`.
- When the displayed property changes, retarget the control and load that property's rating immediately.
- Two different displayed properties must never share a rating accidentally.
- The target key must describe semantic identity, not the rendered prose or visible title.
- Examples of acceptable key shapes, depending on the existing presenter model:
  - `moon_sign:aries`
  - `mars_house:7`
  - `aspect:sun_square_saturn`
  - `human_design_gate:34`
  - `human_design_profile:4_6`
- Those examples are guidance, **not a required universal grammar**. Inspect the presenter's actual entity/property model and choose deterministic stable IDs that survive copy edits.
- If a presentation genuinely cannot be assigned a stable semantic target, leave thumbs unavailable for that presentation rather than using a brittle text-derived key.

### Layout requirement

The thumbs occupy a reserved block at the upper right. **Text must wrap within the remaining width and must never render underneath/behind the buttons.**

It is acceptable and expected for the Chart Information heading/text to wrap earlier when it encounters the thumb block.

Prefer a real Qt layout solution (for example, an expanding text/presentation column plus a fixed-width controls column/row) over overlay coordinates or magic padding. Verify behavior at narrow panel widths.

The controls must also honor the global User Feedback display setting.

## 7. Settings > Display Preferences > User Feedback

At the bottom of **Settings > Display Preferences**, add a section titled:

**User Feedback**

It must contain these two checkboxes in this order:

1. **Show 👍/👎 for ranking perceived accuracy**
2. **Show perceived accuracy inputs for astro twins**

### Global thumbs preference

The first checkbox controls visibility of the new thumbs controls in:

- Chart Editor module headers;
- Chart Information property presentations.

Use the repository's existing settings key/persistence conventions. The UI should update consistently with other Display Preferences; if existing preferences apply live, this should apply live too. If the established pattern requires reopen/refresh, follow that pattern and test it.

### Move the existing Astro Twin setting

There is already an Astro Twin Calculator preference currently labeled approximately:

**Show perceived accuracy inputs**

Move that existing setting into the new **User Feedback** section and rename only its visible label to:

**Show perceived accuracy inputs for astro twins**

Critical requirements:

- Preserve the existing persisted settings key if at all practical.
- Do not silently reset users' existing preference merely because its UI location/label changed.
- Do not duplicate the setting in both sections.
- Do not make it functionally dependent on the new global thumbs setting unless existing behavior requires that. They are grouped together in the UI, but they are separate preferences.

## 8. Stable identity rules

This feature is useful only if ratings remain attached to the same semantic thing over time.

### Chart identity

Use `chart_uid`. Do not create new public APIs based on numeric database IDs.

### Module keys

Use stable internal identifiers for Chart Editor modules. A title rename must not orphan old votes.

### Property keys

Use stable semantic identifiers for the actual interpretation shown. A prose rewrite must not create a new key by accident.

Keep module and property targets in their existing separate persistence namespaces. Do not flatten them into one keyspace.

## 9. State/refresh behavior to verify explicitly

The same reusable control must behave correctly through all of these transitions:

- open an unrated chart;
- rate a module 👍;
- change 👍 to 👎;
- click 👎 again to clear it;
- switch to another chart;
- switch back and see persisted state;
- change Chart Information from property A to property B;
- rate B without changing A;
- return to A and see A's independent state;
- hide controls through Display Preferences;
- show them again and recover the persisted visual state.

Avoid stale-button state caused by widget reuse.

## 10. Tests / acceptance criteria

Add focused tests at the narrowest useful layer. At minimum cover:

### Persistence integration

- `True`, `False`, and unrated are visually mapped correctly.
- Clicking the already-selected thumb calls the persistence toggle and ends in `None`/unrated.
- Switching thumbs replaces the value.
- Existing charts with no perceived-accuracy row continue to behave normally.
- Separate `modules` and `properties` namespaces prevent collisions for identical string keys.

### Chart Editor

- Module header control uses the correct stable module key and active `chart_uid`.
- Chart changes reload rating state rather than carrying previous button state forward.
- Header expand/collapse remains usable when clicking outside the thumb controls.
- Thumb clicks do not accidentally toggle collapse unless explicitly intended.

### Chart Information

- Changing displayed property retargets the control.
- Ratings do not bleed between two property IDs.
- A property with no stable ID does not persist under display text.
- Text/heading does not render beneath the buttons at narrow widths.

### Settings

- Global thumbs setting hides/shows both Chart Editor and Chart Information controls.
- The Astro Twin preference is shown in User Feedback under its new label.
- Its pre-existing settings key/value still loads after the UI move.
- It is not duplicated in the old Astro Twin Calculator section.

### Regression pass

Run the relevant existing GUI/settings tests plus targeted perceived-accuracy tests. If GUI tests are difficult because of the current monolith, test the extracted widget/controller directly and add only the smallest integration characterization tests needed around legacy code.

## 11. Non-goals for this PR

Do not add any of the following unless required to fix a regression caused by this feature:

- aggregate accuracy dashboards;
- percentages, confidence intervals, or rankings;
- evaluator identity/multi-user support;
- reason/comment fields for 👎;
- clear history;
- automatic invalidation when birth data changes;
- export/import redesign;
- a wholesale `app.py` decomposition;
- broad settings architecture migration;
- a new rating database schema when the existing core API suffices.

Those can be separate PRs after basic data collection has real usage.

## 12. Implementation order

Recommended sequence for the new PR:

1. Rebase/start from updated `main` after the persistence PR merges.
2. Read `agents/app_py_refactor_manifesto.md` and inspect current owners before editing.
3. Locate the existing Astro Twin setting and record its persisted key before moving anything.
4. Add the new Display Preferences > User Feedback section and global visibility preference.
5. Build/test one reusable perceived-accuracy thumbs control around `ephemeraldaddy.core.perceived_accuracy`.
6. Integrate it into the common Chart Editor collapsible-header seam.
7. Integrate it into Chart Information with stable property retargeting and reserved layout space.
8. Wire live/settings refresh behavior using existing application patterns.
9. Add focused tests and run the relevant regression suite.
10. Review the diff specifically for new `app.py` feature logic; move any nontrivial new behavior to an explicit owner before opening the PR.

## 13. Definition of done

The PR is complete when a user can enable the global feedback preference, open any chart, independently rate applicable Chart Editor modules and individual Chart Information properties, switch/clear ratings with the required three-state behavior, close/reopen or switch charts without losing state, and disable the controls from Display Preferences — while the existing Astro Twin preference has merely moved/been relabeled and `app.py` has not acquired another substantial feature implementation.

Suggested PR title:

**Complete perceived accuracy feedback UI**
