# Existing plain-page identity Save retention

Status: ACTIVE. Alan explicitly authorized this bounded stacked continuation on
November 20, 2026. The updated goal also grants merge and benchmark authority;
independent review and repository verification gates still apply. Deployment,
migration allocation, serving pins and competing lanes remain outside scope.

## Outcome, stack and lease

Preserve an existing wrapper-free all-block PagePresentation through ordinary
frontend draft persistence and Save. Do not enroll a sidecar-free page, expose
another Save owner or enable agent dispatch.

Parent: PR #4243, exact head `6da4b530aa2fdefc41ca281b4a3fb6e05d827eeb`.
Branch: `codex/contextual-layout-save-retention` in
`/home/drakosfire/Projects/.codex/bf5b/DungeonMindBuddy`.
Merge order: #4243, then this successor after rebasing onto its merged result
and verifying the integrated exact head. The predecessor is open and unreviewed;
do not record it as merged or complete.

Expected exclusive write lease: this handoff and these four frontend files:
`tiptap/pageComposer/presentation.ts`, its `presentation.test.ts`,
`workspaceDocument/useWorkspaceDocumentAuthoring.ts`, and its
`useWorkspaceDocumentAuthoring.presentation.test.tsx`, under
`apps/live-control-ui/src/`. Current filename audit checked 62 returned open PRs
and found no overlaps. No Plan owner, BuildSurfaceShell, backend, schema,
lockfile, shared runtime, real data or provider changes.

## Failure critique and validation

The current wrapper-free projection returns null even after loading a valid
identity-only sidecar. Both local draft projection and actual Save must retain
it. Visual unwrap must still emit null; legacy plain pages must remain
unenrolled. Recompute source spans/digest for edits, retain existing block IDs,
and avoid assigning a new block an existing block's ID. Reject duplicate IDs
instead of silently normalizing enrolled identity. Preserve interrupted drafts,
newer edits during Save, stale/conflict recovery and saved-receipt verification.

Use mapper tests and the mounted authoring hook for draft/reopen and both Save
phases. These mocks are frontend-owner evidence, not native PostgreSQL proof;
the parent carries actual persistence evidence. Then typecheck and exact-SHA
hosted verifier plus a meaningful full-discovered diagnostic, respecting the
global resource lock and Projects evidence filesystem. Inspect cumulative
parent-to-head diff, commit, push and publish the assigned stacked PR.
Independent exact-head review remains pending; no ordinary-chat or release claim.

## Implementation checkpoint

The mapper takes an optional existing presentation and validates its binding to
the prior Markdown before retaining all-block presentation. Draft persistence and
Save supply their existing local sidecar. Existing IDs are reserved before new
allocation; duplicate/invalid present IDs refuse in this retention mode. No
existing sidecar means no new enrollment, and visual unwrap keeps its null path.

Working-tree diagnostics: all 79 mapper/authoring presentation tests passed,
including three added cases, and the application TypeScript check passed. The
hook witness exercises actual frontend draft/Save ownership with mocked server
transport, then clears browser storage before a fresh server-snapshot reopen.
It is not a native database or model witness. Source whitespace checks pass.
Evidence: `/home/drakosfire/Projects/.codex/buddy-check.A0jV7T/retention/`;
`focused.json`, `focused.log`, `typecheck.log` and the task-owned test config.
The initial diagnostic startup failed on a shared dependency cache write; the
successful run used task-owned configuration/caches and the global lock.
Exact-commit hosted/discovered verification and independent review are pending.

## Receipt correction

Author-side inspection found that agreement between a stripped receipt and a
stripped refreshed snapshot could acknowledge identity loss. For an existing
identity-only sidecar, compare the returned fingerprint to the submitted
projection before advancing the local base or marking the draft clean. A
mismatch enters conflict and retains the draft. The new owning-hook regression
requires this refusal and unchanged local base/IDs. The earlier queued verifier
was explicitly cancelled while still awaiting the resource lock; it is not
passing evidence. Verify the corrected full commit, not the earlier head.
