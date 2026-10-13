# Selected Graph object: reviewed observations

Status: ACTIVE under PRIME. This is one Buddy UI slice on `codex/dogfood-reviewed-node-observations`, based on Buddy `origin/main` at `47bc0235c6095543ba343fc90f02e8ea4ed4abbe`. The independent design decision is `/tmp/mirathorn-source-readable-nodes-decision-20261012.md` (SHA256 `11bc41555afad72c99236c9156d68c8f40dbab63e998236a301785022898667a`). This lane uses the isolated `dogfood-reviewed-observations` worktree and does not touch the running UI or native Graph database.

## Bounded outcome

Selecting a Graph object shows reviewed source observations even when its authored summary is empty. Each observation retains its own source and temporal context. The UI does not collapse differing accounts into a canonical summary or authored property. Coverage gaps are visible without making raw IDs the default reading experience. Long observations can be expanded. Existing evidence-reading gates remain unchanged.

## Exclusive write lease

- `apps/live-control-ui/src/api/types.ts`
- `apps/live-control-ui/src/graphReference/ResolvedGraphObjectProjection.tsx`
- `apps/live-control-ui/src/graphReference/ResolvedGraphObjectProjection.test.tsx`
- `apps/live-control-ui/src/graphReference/ReviewedSourceObservations.tsx`
- `apps/live-control-ui/src/graphReference/ReviewedSourceObservations.css`
- This handoff

The selected-object consumer uses the server's serialized `WorldGraphObjectReviewedSourceObservation` fields, `reviewedSourceObservations`, `coverageGapCodes`, and `coverageMissingIds`. No server, corpus, or retained write is in this slice. The PR is for independent PRIME review; merge and rollout are separate decisions.

## Verification boundary

The mounted selected-object test covers a null summary, two differing observations, source and session labels, and absence of a fabricated source opener. A second test covers long-text expansion, partial completeness, and coverage gaps. Run focused Vitest, UI typecheck, and cumulative base-to-head review before opening the PR. This is UI contract evidence, not a full-World or operator acceptance claim.
