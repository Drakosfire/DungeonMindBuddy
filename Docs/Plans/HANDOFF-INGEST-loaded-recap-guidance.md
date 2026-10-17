# HANDOFF — INGEST loaded-recap guidance

**Created:** 2026-10-16.
**Status:** ACTIVE — PRIME explicitly authorizes this bounded UX repair under the operator’s Ingest-first goal.
**Base:** fetched `origin/main@4bd38f74e5f51e5032261718eab052f64edbb5ae`.
**Branch:** `codex/ingest-loaded-recap-guidance`.
**PR title:** `INGEST: clarify saved recap navigation status`.
**Topology:** parallel-independent from open PR #1244. This slice changes only Ingest UI copy and its owning test; #1244 owns server-side candidate-reference packaging/recovery and is not a dependency. No overlapping paths.

## Mission

When the GM opens a previously processed recap, the Ingest navigation status must describe the loaded reader state. It must not tell the GM to choose Process to build a graph-enriched recap while that recap is already open in the graph-enriched reader. Keep Process guidance for a new or editable recap where processing is the actual next action.

## Evidence and invariant

The normal `Load processed recap` UI path performs read-only `inspect_status`, switches the route to `view=recap`, and opens the graph-enriched reader. The current reader can show a working local projection with inline node references while explicitly stating that canonical recap and World memory are unchanged. The navigation status currently falls through to `Choose Process to build the enriched recap and graph context.` when no graph candidate is attached.

> **Invariant:** navigation guidance reflects the current user-visible state and available next action. A loaded read-only recap is described as being viewed; it is not instructed to run Process again. Copy must not imply that a local projection has been admitted to the World Graph.

## Exact write set

- `Docs/Plans/HANDOFF-INGEST-loaded-recap-guidance.md`
- `apps/live-control-ui/src/modules/IngestionModule.tsx`
- `apps/live-control-ui/src/modules/IngestionModule.test.tsx`

No API, extraction, persistence, schema, provider, corpus, graph-admission, shared navigation, or runtime-service changes. Do not edit the historical #1256/#1259 handoffs.

## Acceptance

- When an exact saved recap is loaded and its graph-enriched reader is visible, the navigation status reports that saved recap/session is being viewed. It does not say to choose Process.
- Loading/opening/error states remain truthful; in-progress processing guidance keeps precedence over the reader status.
- Empty/new recap guidance still tells the GM to write or paste a recap and choose Process.
- Candidate-ready guidance still points to Graph Review and distinguishes candidate state from World admission.
- Add a focused regression test for the loaded saved recap and retain/assert the new-recap Process guidance.
- Verify in the IngestionModule UI suite, typecheck/build where available, and `git diff --check` against the cumulative base-to-head diff.
- Do not run Process, Graph Review mutations, admission, publication, or persistence writes. Keep 5202 and operator tabs untouched; no runtime restart.

## Implementation and verification evidence

The navigation status now follows the reader state: it says the saved recap is opening while the projection loads, names the viewed session once projection is present, and directs the operator to the reader's error when opening fails. Active ingest/preview work keeps status precedence. The copy names the reader state only; it makes no claim that the projection or its candidates were admitted to World memory. A saved recap in reader mode no longer falls through to the Process instruction. The editable/new-source path still preserves its title guard and Process guidance.

- `npm test -- src/modules/IngestionModule.test.tsx`: passed, 41 tests. Coverage asserts the loaded Session 10 reader status and checks that an editable recap returns to Process guidance after a valid title; the existing normalized-source test also continues to require Process guidance.
- `git diff --check`: passed.
- `npm run typecheck` and `npm run build`: both stop on existing errors in unchanged `src/planSurface/components/WorldPlanAgentAnswer.tsx` (TS2532 at line 47, TS18048 at line 49, TS2339 at line 50). The typecheck failure prevents Vite build from running.
- Full UI suite (before the final assertion-only test extension): 308 files passed, 23 failed; 4,041 tests passed, 130 failed, 1 skipped. Failures include Plan/Graph Review suites expecting controls whose backing surface is now retired. The Ingest module suite passed independently; no green full-suite claim is made.
- No Process, Graph Review mutation, admission, publication, persistence write, or 5202 operation was performed.

## Review and completion

One reviewable UI-only PR on this branch. PRIME retains merge authority. Record exact head SHA and verification evidence in the PR description. The scope ends when truthful navigation status is proven at the UI test boundary and the PR is ready for independent review.
