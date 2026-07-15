---
name: diagnose-ephemeraldaddy
description: Diagnose bugs, regressions, unexpected behavior, and architectural faults in the EphemeralDaddy Python desktop application. Use when investigating symptoms that may cross modules, signals, callbacks, shared state, window lifecycle, persistence, astrology or Human Design calculation layers, platform branches, packaging, or UI boundaries. Trace the root cause and report an evidence-backed diagnosis, but do not edit files or implement a fix unless the user explicitly follows up asking for implementation.
---

# Diagnose EphemeralDaddy

Trace behavior across the application until the causal chain is supported by code evidence. Treat the visible symptom as a starting location, not a presumed source.

Read `references/project-context.md` for stable project context. Prefer repository evidence over that reference whenever they differ.

## Establish the symptom

- Restate the observed behavior, expected behavior, trigger, platform, and affected window or feature from the user's evidence.
- Inspect the repository before asking questions. Ask only for information that cannot be recovered from code, logs, tests, or supplied artifacts and would materially change the diagnosis.
- Separate confirmed facts from working hypotheses.

## Trace the causal path

1. Locate the visible behavior and its immediate owner with `rg` or repository-native navigation.
2. Trace both callers and consumers. Follow imports, constructors, signal connections, callbacks, event handlers, timers, state mutation, persistence, and cleanup.
3. Identify the owner of each relevant state transition. Distinguish object creation, visibility, activation, destruction, caching, and persistence.
4. Check alternate entry points and platform-specific branches. A correct local function may receive stale or incorrectly transformed state upstream.
5. Compare the failing path with a nearby working path when one exists.
6. Inspect tests, recent diffs, comments, and configuration only when they can confirm or reject a concrete hypothesis.
7. Run focused, read-only diagnostics or tests when safe. Do not change source, configuration, generated files, dependencies, or persistent data.

Do not stop at the first plausible explanation. Confirm the path from initiating event to observed symptom and look for evidence that could falsify it.

## Diagnose across boundaries

Explicitly check relevant boundaries:

- UI widget to controller or service
- parent window to child window
- signal emission to connected slot
- calculation engine to presentation layer
- loaded data to normalized in-memory form
- saved state to restored state
- macOS behavior to Windows behavior
- source tree to packaged application

For lifecycle bugs, build a compact event sequence covering creation, show or hide, activation, close, cleanup, and recreation. For calculation bugs, trace the input value, every transformation, weighting or normalization step, and the final consumer.

## Report and stop

Lead with the most likely root cause and confidence level. Include:

- the causal chain;
- exact supporting files and symbols;
- why the symptom appears where it does;
- competing explanations considered and the evidence against them;
- the smallest conceptual repair boundary;
- focused verification that would distinguish any remaining uncertainty.

Use clickable absolute file links when available. Keep code excerpts short and diagnostic.

Do not patch, refactor, format, install dependencies, rewrite tests, or modify files during the diagnostic turn. If the user asks to fix the issue in a later message, implement the narrowest supported repair and verify it proportionately.

## Guard against common failures

- Do not assume the named or displayed widget owns the faulty state.
- Do not infer a cause from a single matching function name.
- Do not recommend broad refactoring before locating the causal chain.
- Do not silently reinterpret intentional astrology rules, JSON conventions, or window behavior as defects.
- Do not omit contradictory evidence.
- Do not turn a request to diagnose into authorization to edit.
