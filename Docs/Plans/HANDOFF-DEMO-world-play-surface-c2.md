# HANDOFF — DEMO: migrate World Play UI to typed V2

**Status:** COMPLETE — Buddy PR #820 merged at
`bfa741261e715eadb48d873f87fccc1764417da8` after exact-head PRIME review
**Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`
**Repository:** `Drakosfire/DungeonMindBuddy`
**Base:** Buddy `main@f34cc2a32b2abc9a4548d0750f911e154c39b54c` (C1 #810 plus model-policy PR #819)
**Branch / checkout:** `codex/demo-world-play-c2` / `/home/drakosfire/.codex/worktrees/demo-world-play-c2/DungeonMindBuddy`
**Topology:** Serial; one C2 implementation PR, with PRIME owning review and merge.
**PR title:** `DEMO: migrate World Play Run and Runbook UI to V2`

PRIME explicitly authorized C2 from current merged main after the C1 owner-boundary witness passed. The current remote default branch was refreshed to the exact base above after Buddy PR #819 merged. #819 changed model policy, Hermes Agent code/tests and its own handoff; none overlap this C2 write set. The current open Buddy PR inventory (#798, #781, #760–#761, and #763–#765) also has no paths overlapping this lease. This handoff is the exclusive expected-path lease. If the implementation needs another path, contract, repository, dependency, migration, or runtime/state change, stop before editing and return to PRIME for transfer or split.

## Capability and boundary

Migrate the managed-World Play UI's Runbook selection/creation, Start Run, open/resume, runtime progress, exact Runbook projection, and same-World rebase to the already accepted typed World V2 routes from C1. Pass the verified managed `world_id` explicitly to each V2 operation. Never map it to `campaign_id`, infer World ownership from matching strings, or retry through campaign V1. Preserve existing campaign Play V1 behavior.

The global active-Run pointer remains a selection hint. For a managed World, validate the pointed ID with World V2 detail before resuming; a failed or foreign detail leaves the chooser available with an actionable error. A Runbook and Run response must retain its V2 schema discriminator and exact `world_id`; the Run remains pinned to its exact artifact, committed revision, WorkRevision ID, content SHA, and independent `run_revision`.

ARCHITECTURE's current C2 ruling keeps the shared V1 Agent publisher/provider request contract untouched. Play Agent conversation and generic Agent Run resolution remain unavailable in this slice. The current Play publisher must not represent a World ID as a Campaign or publish a World V2 Run as if it were a V1 Run. Do not add a context resolver or Agent turn. C1's specialized read-only World Run context route has no eligible current Play consumer without that resolver, so this slice defers it. No graph query/write or World mutation is allowed.

## Exclusive write lease

Only these paths may be edited:

~~~text
Docs/Plans/HANDOFF-DEMO-world-play-surface-c2.md
Docs/Plans/HANDOFF-DEMO-world-play-surface-v2.md
Docs/Plans/HANDOFF-DEMO-world-owned-play-runs.md
Docs/Roadmaps/ROADMAP-demo.md
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/api/liveApi.test.ts
apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx
apps/live-control-ui/src/playSurface/PlaySurfacePage.test.tsx
apps/live-control-ui/src/playSurface/StartRunPanel.tsx
apps/live-control-ui/src/playSurface/StartRunPanel.test.tsx
apps/live-control-ui/src/playSurface/blankRunbook.ts
apps/live-control-ui/src/playSurface/blankRunbook.test.ts
apps/live-control-ui/src/playSurface/startRunAttempt.ts
apps/live-control-ui/src/playSurface/startRunAttempt.test.ts
apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.ts
apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.test.ts
apps/live-control-ui/src/playSurface/runbook/RunbookTableDeck.tsx
apps/live-control-ui/src/playSurface/runbook/RunbookTableDeck.test.tsx
apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.tsx
apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.test.tsx
~~~

The doc edits settle the merged C1 predecessor and activate C2; they do not pre-claim C2 completion. No backend, database, migration, dependency/lockfile, shared Agent context, provider, corpus, product runtime, or other repository path is leased. No product server or database is to be started or modified for this UI lane. Verification uses mocked API/state and mounted UI tests.

## Acceptance and failure cases

- Add discriminated client types and World API wrappers for C1 World Runbook list/create/read/snapshot/current-or-exact committed revision/TipTap prepare+commit, and World PlayRun list/detail/create/replay/progress/rebase/reference-manifest operations. Every call requires an explicit World ID and uses the documented V2 route/query/body; verify returned discriminator and owner before admitting records.
- In a managed World, list and label only World-owned Runbooks/Runs. Create a blank Runbook through the World V2 create and TipTap routes, then start a World V2 Run from the exact current committed revision and SHA. Manifest sealing, uncertain-create reconciliation and explicit retry retain the same intended Run UUID and World binding.
- Open a URL Run only through World V2 detail, then verify its World, exact Runbook pin, sealed manifest and revision before rendering. World owner mismatch, campaign ID equality, an unbound legacy V1 Run, invalid V2 discriminator, malformed UUID, damaged/mismatched pin, or unreadable manifest fail closed with a visible error.
- On managed-World resume, treat the global active pointer only as a hint and validate it with the selected World V2 detail route. Missing, malformed, stale, campaign-owned, or foreign pointers never auto-resume through V1; keep the World chooser and actionable status.
- Save progress through V2 with `expected_run_revision`; reconcile only by reading that exact World V2 Run. Rebase only after an explicit action against a verified current committed Runbook revision/SHA from the same World. A V2 rebase error leaves the prior admitted Run/progress intact and reports the error; never switch scopes or retry through V1.
- Any World list/get/create/progress/rebase/manifest/context failure leaves the prior selected document/Run state intact where one exists and presents an actionable unavailable/error state. No V1 fallback, ID translation, fabricated context, silent retry, or different-scope Run creation.
- Keep the campaign-backed list/start/open/resume/progress behavior on its existing V1 API and prove compatibility controls, including an actual Campaign ID equal to a World ID.
- Do not expose Play Agent conversation or generic current-Agent-Run resolution. Do not alter shared Agent publisher/provider schemas. The focused diff contains no graph access or writes.

Owning-boundary evidence is the mounted Play route and Start Run flow with mocked API/state, including World-only create/list/open/resume/progress/rebase and the campaign V1 control. Unit tests alone do not replace the mounted route evidence. Cover cross-World URLs, matching Campaign strings, unbound legacy Runs, malformed/damaged records, interrupted create/seal retry, V2 route failures, progress CAS reconciliation, same-World exact-pin rebase, and route cancellation/selection changes.

## Verification and handback

Run the focused API and Play test files named in the lease, UI typecheck (record inherited failures against this exact base), and `git diff --check`. Compare the exact cumulative `f34cc2a32b2abc9a4548d0750f911e154c39b54c..HEAD` diff against this path list; inspect campaign V1 compatibility, World V2 route arguments, error-state behavior, and the no-World-as-Campaign invariant. Commit intended changes, push the assigned branch, open or update one PR titled above, and hand its exact head plus test results and unresolved limitations to PRIME. Do not merge.

### Initial pre-PR verification — 2026-09-30

The eight focused UI/API suites in this lease passed 218 tests, including mounted
managed-World list/select/resume, Start Run, blank Runbook creation, exact-pin
rebase failure, World progress CAS reconciliation, V1 Campaign controls, and
late route-response cancellation. The late-response route suite was rerun alone
(6/6) with no React test warnings. `git diff --check` passed. UI typecheck reports
only the existing unrelated `ThreatPublicationPanel.tsx(553,77): Cannot find
namespace 'JSX'` diagnostic on this exact base; no C2 path is named. No product
server, database, provider, or corpus was started or modified. C2 remains ACTIVE
until PRIME reviews and merges the assigned PR; this evidence is not merge or
product acceptance.

### PRIME review correction — 2026-10-01

PRIME's first review held PR #820 at head
`f57b5d7f2f3b282d34b85f129f48e72ddbe3a153` for late World A completion races
after switching to World B. The finding covered Runbook list refresh, Start Run
create/seal completion, blank Runbook create/selection, and explicit Play Run
rebase after route/World change. A cancelled effect alone was insufficient
because list state was written inside its awaited helper and the other callers
continued into state adoption or navigation after their await.

The correction fences list requests by scope and request generation, Start Run
completion by current World and selected Runbook, and blank-create UI writes by
World generation. A backend-created World A Runbook remains under World A and
can be found again after returning to that World; a completed World A Run is
sealed under World A but cannot navigate from the current World B selection.
Play rebase captures the exact route/World and request generation; it still
validates the server receipt and performs exact-World reconciliation, but a
stale result cannot load or replace the newly selected route.

Five mounted deferred A→B regressions cover the late list, Start Run, blank
Runbook, successful rebase, and rebase-response-loss exact reconciliation. The
eight leased UI/API suites now pass 223 tests. The UI typecheck still reports
only the inherited unrelated
`ThreatPublicationPanel.tsx(553,77): Cannot find namespace 'JSX'` diagnostic.
`git diff --check` passes. No server, database, provider, or corpus was used.
The first correction was awaiting PRIME's re-review at this point; C2 remains
ACTIVE. Neither that correction nor its tests claim merge or operator
acceptance.

### PRIME second re-review — same-World selection ABA, 2026-10-01

At PR #820 head `2429543d733a0c031341d81d3f8ce427205eff10`, PRIME's mounted
probe selected Runbook A, started a Run, selected B, returned to A, and then
resolved the original A create and manifest. The document-ID-only completion
check allowed navigation from that abandoned action because A was selected
again. The same ABA could let a deferred blank-Runbook completion replace the
current selection.

The correction tracks a selection generation separately from World/route
scope, advances it on actual Runbook selection changes and scope resets, and
captures it for Start Run and blank-create actions. A stale completion cannot
adopt Run state or selection or navigate; an exact World write already issued
still completes and remains discoverable/reconcilable. Code commit
`269973feca4761ddfffab1c7a3843b7392168e5c` contains the fence and two
mounted deferred A→B→A regressions.

All eight focused C2 UI/API suites passed 225 tests, including two deferred
same-World A→B→A mounted regressions and five prior World A→B regressions.
Cumulative and working diff checks passed. UI typecheck retains only the
inherited unrelated `ThreatPublicationPanel.tsx(553,77): Cannot find namespace
'JSX'` error. No server, database, provider, or corpus was used. PRIME passed
the exact head `0edeba0e231db57c451e4892bda867cd5e556f46`; its independent
mounted Play/Start Run tests passed 32/32. Buddy PR #820 merged at
`bfa741261e715eadb48d873f87fccc1764417da8`. The C2 write lease is ended.
This does not claim J1/J2, connected-demo, visual, or operator acceptance.

## Predecessor settlement

C1 Buddy PR #810 merged at `9aa82aacca3d27849b3fba83dcfc6577097b9b7d` from reviewed head `da2aa5c5dbe70d7ce49d90ecee2eb2274fae155e`; the C1 tested code head was `561513a8a2ca2099380e4f891ec1012f37e1f21d`. Its fresh seven-suite PostgreSQL owner witness passed 242 tests with 11 existing Pydantic `schema` shadow warnings in 106.39 seconds. C1 supplied the typed World-owned Runbook and World PlayRun V2 routes this UI slice consumes. PR #820 consumed these C1 routes and is now merged; the exact C2 completion evidence and lease settlement are recorded above. Do not infer J1/J2 or operator acceptance from this bounded slice.

The separate saved managed-World Plan Agent continuity witness is **PASS** per PRIME's later report after a clean attributable direct recall challenge. C2 does not independently rerun or expand that witness.
