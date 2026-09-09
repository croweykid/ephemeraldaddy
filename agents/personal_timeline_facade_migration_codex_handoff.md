# Personal Timeline Integration Cleanup — Codex Handoff

**Status:** Deferred architectural cleanup after PR #2243 lands.  
**Primary owner:** `ephemeraldaddy/gui/features/transits/`  
**Primary goal:** Finish decomposing the remaining `personal_timeline_core.py` implementation bucket into explicit generation/window owners without moving feature implementation into `app.py`, without reintroducing runtime class mutation, and without regressing cache/thread/timezone semantics.

---

## Timezone/cache correctness added after Codex review

The current implementation must preserve **named timezone rule sets**, not only numeric UTC offsets. ISO cache endpoints parsed by `datetime.fromisoformat()` produce fixed-offset tzinfo objects, so cached endpoints must be converted back into the selected chart's `dt.tzinfo` before constructing `PersonalTimelineWindow`.

This is a non-negotiable calculation invariant because DST-crossing windows otherwise change duration/midpoint semantics after cache reload and can affect Age sorting, overlap/exposure, and randomized/background analysis.

The cache fingerprint must also include timezone identity (for example `ZoneInfo.key`). Two zones that share the same offset at birth can follow different DST rules later and must not reuse the same lifetime Timeline cache.

Future migration tests must retain both cases:

1. a DST-crossing cached window remains semantically equivalent to the freshly generated window after restoration into the chart timezone;
2. two named zones with the same birth-date offset but different rule identities produce different fingerprints.

Do not guess a named timezone from a numeric offset and do not normalize cached windows to unrelated fixed-offset tzinfo objects.

---

## Required architectural end state

1. `personal_timeline_core.py` is decomposed into explicit generation/model and Qt window owners.
2. `personal_timeline.py` remains a normal public integration surface, not a `sys.modules` facade.
3. No import-time class mutation or runtime widget method replacement is reintroduced.
4. Persistence remains explicit composition through `PersonalTimelinePersistenceController` or an equivalent typed collaborator.
5. Cache read/parse/reconstruction and write/serialize/flush/`fsync`/atomic replacement stay off the GUI thread.
6. Application shutdown continues to drain process-owned cache workers before Qt teardown.
7. Closing a Timeline during cache lookup cannot allow a late miss to start generation or a late hit to mutate a closing/destroyed window.
8. Stable `chart_uid` remains the authoritative identity.
9. Broad empirical candidate generation, filtering semantics, sorting, and Library of Ghosts analysis remain unchanged.
10. `app.py` remains orchestration-only; prefer zero Timeline implementation in `app.py`.

---

## Codex procedure

Start from current `main` only after #2243 (or its final equivalent) is merged. Read `AGENTS.md`, `agents/app_py_refactor_manifesto.md`, the current Timeline modules, `window_chrome.py`, focused Timeline tests, and workflow file before editing.

Inventory all callers of `personal_timeline`, `personal_timeline_core`, `PersonalTimelineWindowWidget`, `PersonalTimelinePersistenceController`, `open_personal_timeline_for_window`, `generate_personal_timeline`, `TimelineTransitDefinition`, `PersonalTimelineWindow`, cache-job shutdown functions, and sorting helpers.

Before structural changes, preserve or add characterization tests for:

- Chart Editor and Database View UID resolution;
- cache hit vs miss lifecycle;
- no import-order dependency;
- no core-class mutation;
- cache work off the GUI thread;
- close-during-lookup behavior;
- application shutdown draining active cache workers;
- all seven typed sortable columns;
- DST-crossing timezone restoration;
- named-zone fingerprint distinction.

Then, in bounded commits:

1. extract non-Qt Timeline generation/data-model logic to `personal_timeline_generation.py` or equivalent;
2. move Qt window/orchestration behavior to `personal_timeline_window.py` or equivalent;
3. update production and test callers to the explicit owners;
4. retire `personal_timeline_core.py` only after every internal caller has migrated;
5. inspect `app.py` only for a genuinely necessary narrow integration hook; do not move feature implementation there;
6. run the focused suite, reconcile current `main`, and manually review the final diff for duplicate owners, runtime mutation, synchronous I/O, shutdown gaps, and timezone regressions.

The migration is complete only when Personal Timeline is a normal, explicitly owned Transit workflow with transparent module boundaries, safe background persistence, stable timezone semantics, no compatibility alias tricks, and minimal top-level application coupling.
