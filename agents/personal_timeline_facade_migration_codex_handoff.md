# Personal Timeline Integration Cleanup — Codex Handoff

**Status:** Deferred architectural cleanup after PR #2243 lands.  
**Primary owner:** `ephemeraldaddy/gui/features/transits/`  
**Primary goal:** Finish decomposing the remaining `personal_timeline_core.py` implementation bucket into explicit generation/window owners without moving feature implementation into `app.py`, without reintroducing runtime class mutation, and without regressing cache/thread/timezone semantics.
