# HANDOFF — INGEST recap route consistency

**Created:** 2026-10-17.
**Status:** ACTIVE — PRIME explicitly dispatches this follow-on under the operator’s Ingest-first goal.
**Base:** fetched `origin/main@168938813fd4b15ff00277142cce51dc50696b97` after #1298 merged.
**Branch:** `codex/ingest-recap-route-consistency`.
**PR title:** `INGEST: make saved recap route intent consistent`.
**Topology:** serial successor to merged #1298; parallel-independent of open #1244 (server candidate-evidence packaging), #1235 (Graph Review source-observation UI), and #1144 (candidate-kind validation). Their current changed-file lists do not overlap this lane.

## Mission

Make direct saved-recap URLs and picker-loaded recaps behave consistently without hiding or discarding an operator’s unsaved draft. Establish the expected read-versus-edit behavior from current code and prove it in the owning UI tests before making the smallest necessary fix.

## Current-code evidence and invariant

- `?campaign=<id>&session=session-N&view=recap` is explicit reader intent. It restores the exact recap and opens the graph-enriched reader.
- A direct saved-recap URL without `view=recap` currently hydrates the exact session. If a current normalized source is proven and no non-empty matching draft is restored, the component automatically enters the reader and its restore path canonicalizes the URL to `view=recap`.
- A matching non-empty local draft suppresses automatic reader entry. This preserves editable operator text and must not be overridden merely to force the reader.
- The prior dogfood observation reported a different direct-link view from picker navigation. Reproduce both the no-draft and matching-draft cases at the UI boundary. If the draft-preservation path is the distinction, make that path clear and offer an explicit way to open the saved reader while retaining the draft.

> **Invariant:** view intent follows verified saved-source state and explicit draft intent. Read-only projection never overwrites, clears, or obscures an unsaved draft without a visible, reversible operator action. Do not imply that a local projection or candidate was admitted to World memory.

## Exact write set

- `Docs/Plans/HANDOFF-INGEST-recap-route-consistency.md`
- `Docs/Plans/HANDOFF-INGEST-loaded-recap-guidance.md` (settle merged #1298 predecessor)
- `apps/live-control-ui/src/modules/IngestionModule.tsx`
- `apps/live-control-ui/src/modules/IngestionModule.test.tsx`

No other files. No API, extraction, persistence, schema, provider, corpus, Graph-admission, shared-navigation, or runtime-service changes. Do not change Build or historical settled handoffs other than the named #1298 predecessor.

## Acceptance

- Test a direct exact-session URL without `view=recap` and no matching draft; it must reach the same graph-enriched reader as picker loading and canonicalize the URL without adding a history step.
- Test a matching unsaved draft; it remains editable, its text is preserved, and the operator has a clear non-destructive route to the saved recap reader if the prior inconsistency is explained by draft preservation.
- Preserve unrelated query parameters and exact campaign/session binding.
- Keep source and Graph-admission claims truthful.
- If current behavior is intentional and no user-visible ambiguity reproduces, choose the next concrete Ingest usability defect within the same two UI files and document why it fits this handoff; do not manufacture a route fix.
- Verify with the focused IngestionModule UI suite, package typecheck/build where available, and `git diff --check`.
- No provider calls, Process, Graph Review mutation, admission, publication, persistence write, or 5202 change/restart.

## Review and completion

One reviewable PR on this branch. PRIME retains merge authority. Record the exact base/head and test evidence in the PR description. The PR is complete when the direct-route behavior is proven and any reproduced ambiguity is corrected without losing unsaved text, or when a replacement in-scope defect is proven and fixed.
