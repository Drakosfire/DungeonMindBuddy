# Existing plain-page identity Save retention

Status: ACTIVE. Alan explicitly authorized this bounded stacked continuation on
November 20, 2026. The updated goal also grants merge and benchmark authority;
independent review and repository verification gates still apply. Deployment,
migration allocation, serving pins and competing lanes remain outside scope.

## Outcome, stack and lease

Preserve an existing wrapper-free all-block PagePresentation through ordinary
frontend draft persistence and Save. Do not enroll a sidecar-free page, expose
another Save owner or enable agent dispatch.

Parent: PR #4243, reviewed head `6da4b530aa2fdefc41ca281b4a3fb6e05d827eeb`,
merged as `08d23da86a079121b7b31812e93db1857df17864` after independent cycle-1 PASS.
Branch: `codex/contextual-layout-save-retention` in
`/home/drakosfire/Projects/.codex/bf5b/DungeonMindBuddy`.
Merge order: #4243, then this successor. The successor was rebased onto the
parent's actual merged result; verify and review its corrected integrated head.

Expected exclusive write lease: this handoff and these four frontend files:
`tiptap/pageComposer/presentation.ts`, its `presentation.test.ts`,
`workspaceDocument/useWorkspaceDocumentAuthoring.ts`, and its
`useWorkspaceDocumentAuthoring.presentation.test.tsx`, under
`apps/live-control-ui/src/`. Current filename audit checked 62 returned open PRs
and found no overlaps. No Plan owner, BuildSurfaceShell, backend, schema,
lockfile, shared runtime, real data or provider changes.
The consuming lease also includes truthful predecessor settlement in
`HANDOFF-LAYOUT-plain-page-save-safety.md` now that its actual merge is known.

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

## Independent review cycle 1 — enrollment transition HOLD

Independent review passed #4243 at its exact reviewed head and held this PR at
`e40de90b65dd4f8f63602456bd7e340c676c2fdb` for one P2 finding: a committed
identity-only page could lose its local retention signal when wrapped and then
unwrapped/undone before Save. Ordinary Save then sent null and was refused.

The correction derives plain retention from the committed snapshot as well as
the current local sidecar. It validates the latest sidecar against its own latest
source, so text edits while wrapped do not require a stale snapshot digest.
Receipt checks use that same committed-enrollment basis. Legacy plain pages and
intentional unwrap of a committed visual page keep their existing behavior.
Two parameterized owning-hook regressions exercise wrap/unwrapping with and
without text edits while wrapped, a later plain edit, Save and cold reopen.
Fresh focused/exact-source evidence and independent cycle-2 review are required.

Correction diagnostics passed all 82 focused cases and the application TypeScript
check. Results are retained in `focused-enrollment.json` and
`enrollment-typecheck.log` under the existing retention evidence task. These are
diagnostics, not a substitute for the corrected integrated exact-head verifiers.

Further independent inspection identified an old-client dirty draft with a
matching enrolled base digest but null/missing local sidecar and reparsed JSON
without IDs. Committed retention must refuse that state before projection can
allocate replacement IDs. Both draft and Save enter projection when the committed
base is enrolled, even if the local sidecar field is absent. Two seeded null/
undefined compatibility controls require no prepare/commit and unchanged raw
draft/base identities. Recovery remains explicit; no silent ID reconstruction.
This correction supersedes source `417f2459` for final qualification. Its running
isolated exact-source verification is historical evidence only, not the final
corrected-head pass. Fresh exact-source verification and cycle-2 review remain
required after this old-client guard.
