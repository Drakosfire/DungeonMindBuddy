---
title: Saved World Plan → Playable Run adoption
document_class: implementation_handoff
status: BLOCKED
created_at: "2026-10-04"
workstream: DEMO
design_authority: "../Design/DESIGN-world-plan-playable-adoption.md"
design_base: "Buddy main 0f42fec0812655bb37c87b6be9a7fe5741d7f25f"
pr_topology: serial
implementation_branch: not_assigned
implementation_pr: not_authorized
---

# HANDOFF — Start a Run from the exact saved World Plan

> This is durable design authority only. It is BLOCKED and holds no
> implementation write lease.

## Status and activation gate

**Status: BLOCKED — PRIME design review, product-sequence gate, and
implementation resource/path ownership are outstanding.**

This handoff was prepared against Buddy main
0f42fec0812655bb37c87b6be9a7fe5741d7f25f. Re-anchor against live main and
current open PRs before any implementation dispatch; the base above is a
design-time reference, not an implementation pin.

Implementation may be activated only after all of the following are true:

1. PRIME has reviewed and accepted the companion design's source identity,
   admission, revision, audience, and Runtime ownership decisions.
2. PRIME has re-anchored the Demo roadmap and confirmed the prerequisites and
   ordering for the saved-Plan card projection and shared World-conversation
   work. The current roadmap places same-content-to-Run after those steps; do
   not skip or silently resequence them.
3. APP-STATE confirms that a WorkObject's kind cannot change during its
   lifetime, so the existing Run-to-WorkObject identity preserves that the
   source was a Plan. If that invariant is false, stop for a versioned
   source-kind persistence design.
4. DEMO, SERVER, and APP-STATE agree on the exact API/service contract and
   individually owned paths. PRIME records the exact implementation path
   allowlist, path owners, active PR/lease conflicts, and completion sync set.
5. Runtime/test resources are named and isolated. No active operator or
   dogfood runtime is reused or restarted.

Until all gates are satisfied, do not create an implementation branch, PR,
schema migration, or runtime write.

## §1 Mission and merge-ready invariant

Deliver one explicit GM action that starts a new managed-World Play Run from
the selected World Plan's exact current committed WorkRevision, without
converting, cloning, or rewriting that Plan.

The Run must remain bound to the same World ID, WorkObject ID, WorkRevision ID,
revision number, and content SHA-256 accepted at creation. Its sealed manifest
must be derived from that exact immutable Markdown in the owning
application-state transaction. Future Plan edits create a new WorkRevision and
cannot change or retarget an already-created Run.

## §2 Current contract and owning boundaries

Read these authorities after re-anchoring:

1. **DESIGN-world-plan-playable-adoption.md**.
2. **ARCHITECTURE-playable-material-and-runtime.md**.
3. **ROADMAP-demo.md**, especially the delivery order and active DEMO handoffs.
4. The accepted World Plan/editor and World PlayRun V2 contracts.
5. The current APP-STATE Content and Play admission/identity contracts.

Current implementation evidence at design time:

- **get_committed_playable_revision** can resolve an exact World Plan revision.
- UI Start Run preflight rejects documents whose kind is not **runbook**.
- APP-STATE **admit_playable_revision** and
  **resolve_pinned_playable_revision** require **runbook**; both new-Run
  admission and existing-Run resume therefore need deliberate owner-reviewed
  widening.
- World Play Run persistence already records World, WorkObject ID, exact
  WorkRevision ID, revision number, and digest, and seals a manifest. Reuse
  this identity path if possible; do not create a parallel source store.

Owner boundaries:

- **DEMO** owns the GM Start Play affordance and mounted UI proof.
- **SERVER** owns typed World-scoped route/preflight integration and fail-closed
  error behavior.
- **APP-STATE** owns atomic source admission, immutable exact-revision
  resolution, Run persistence, and database-level evidence.
- **PRIME** owns activation, path/lease arbitration, cross-lane sequencing,
  and exact-head review.
- DungeonMind Graph remains untouched; this work does not publish or authorize
  Graph claims.

## §3 Observable contract and required evidence

The implementation PR must prove, at the owning boundaries:

| Sequence | Required result |
| --- | --- |
| Active World Plan, current committed revision, no divergent working copy, valid existing Playable markers | One explicit Start Play creates one World Run bound to the exact source identity and sealed manifest. |
| Save the Plan after Run creation | Plan gets a new WorkRevision; existing Run and manifest remain pinned to the old WorkRevision and bytes. |
| Start a second Run after the new save | The new Run can bind the new current revision without modifying the first Run. |
| Wrong World, Runbook passed where Plan was requested, Campaign-owned Plan, discarded Plan, dirty working copy, stale expected revision, wrong SHA | Fail closed; no Run, manifest, copy, or cross-World fallback is created. |
| Missing/unsupported/mixed/malformed markers, duplicate IDs, orphan/invalid edges, or no runnable Beat | Fail closed before partial Run creation; no inferred headings or auto-added markers. |
| Existing Run opened after Plan edit/discard | Reads its exact historical Plan revision; never substitutes the latest Plan. |
| Runtime choice and note mutation | Persists only to that Run; source Plan Markdown and WorkRevision remain byte-for-byte unchanged. |
| Plan includes Graph/source refs | No implicit Graph read, publication, or canon mutation. |

Required evidence includes:

- APP-STATE PostgreSQL transaction tests for exact Plan admission, owner/kind,
  current-revision and clean-working-copy fences, atomic Run+manifest creation,
  idempotent same-binding replay, conflict on changed binding, and exact pinned
  historical reads after later Plan saves.
- Server/API tests for explicit World scoping, stale/dirty/unsupported Plan
  failure behavior, and no fallback to Campaign or Runbook routes.
- Mounted UI tests proving selected Plan identity is retained through Start
  Play, source changes/World switches cannot retarget an in-flight attempt, and
  failures leave no false “started” state.
- A mounted Play/Plan owning-boundary test that proves Runtime notes/selections
  do not mutate the Plan.
- Fresh exact-head verification and an isolated end-to-end witness if required
  by PRIME at activation. A helper-only test is not evidence for persistence or
  mounted-flow claims.

## §4 Candidate implementation paths — not a write lease

These are reconnaissance candidates only. None is currently reserved by this
BLOCKED handoff. PRIME and the owning teams must re-check all active PRs and
explicitly authorize the final path set at activation.

**DEMO UI candidates**

- **apps/live-control-ui/src/playSurface/startRunAttempt.ts** and its focused
  test: allow an explicitly typed World Plan source while preserving exact
  current/nondivergent preflight.
- World Plan/Play navigation entry point and its mounted tests: provide the
  explicit Start Play action. **PlanSurfacePage.tsx** and the mounted
  **PlanSurfacePage.test.tsx** are not implicitly available; reconcile the
  former against #886's production Page/shell lease and the latter against the
  PRIME-assigned mounted-harness repair lane before allocating either path.
- Any necessary API wrapper/type files: inspect active leases first; do not
  assume **liveApi.ts** or shared types are free.

**SERVER route candidates**

- **apps/live_control_server/routes/play_runs.py**
- **apps/live_control_server/routes/workspace_documents.py**
- **apps/live_control_server/services/workspace_document_registry.py**
- **apps/live_control_server/services/play_run_registry.py**
- **apps/live_control_server/services/play_run_reference_manifest.py**

**APP-STATE transaction candidates**

- **src/application_state/content/playable_admission.py**
- **src/application_state/play/service.py**
- Owning Content/Play tests, including **tests/test_world_play_runs_v2.py**
  and focused exact-pin/admission tests

Do not add a database column, migration, alternate content copy, or new
source-kind receipt unless APP-STATE proves the identity invariant cannot be
met with current durable fields and PRIME re-reviews the changed contract.

The final ACTIVE handoff must replace this candidate inventory with an exact
exclusive write allowlist and explicitly name any transferred/shared paths.
The mounted harness repair owns **PlanSurfacePage.test.tsx** until its owner
closes or transfers that lease. #886 retains production Plan Page/shell paths
until its own accepted settlement or explicit handback. Do not rely on Git
conflicts to arbitrate either path.

## §5 PR topology and state-authority sync

**Topology: serial.** One implementation PR only. No stacked/successor PR is
authorized by this handoff. A separate repair or newly discovered capability
returns to PRIME for decomposition and a new BLOCKED handoff.

At activation, identify the mutable DEMO state authorities that need to record
completed predecessors. The implementation PR must carry that backward-looking
sync in its authorized lease, likely including **Docs/Roadmaps/ROADMAP-demo.md**
and this handoff, plus any current DEMO tracker/status authority found during
re-anchor. It must not claim this slice complete before its own merge or
invent its final merge SHA/review-cycle count.

## §6 Scope boundaries

Included:

- one explicit Start Play action from an existing saved World Plan;
- reuse of the same Plan WorkObject and exact immutable WorkRevision;
- fail-closed Plan-kind, World-owner, current/clean, digest, and supported
  structure admission;
- Run-local choices/selections and notes through existing Run ownership;
- exact historical read after later Plan edits.

Explicitly excluded:

- Plan-to-Runbook conversion, content copying, or second authored store;
- local-draft or stale-revision starts;
- automatic or silent Run rebase; Plan-backed rebase requires a separate
  reviewed contract;
- automatic playable marker generation or new grammar;
- player-facing projection/audience classification; first projection is
  GM-only;
- Graph reads/writes, evidence publication, DungeonMind API mutation, or
  Runtime-to-World canon promotion;
- new roll/outcome model, provider/model call, new credentials, or
  GenerationEngine changes;
- changes to GenerationEngine parity sequencing or any E5 write lease;
- changes to live operator UI 5202/API 8000, DOGFOOD 5203, or private corpus
  contents.

## §7 Runtime and resource ownership

**No runtime mutation is authorized while BLOCKED.**

For a future implementation lane:

- Use isolated mounted tests and the repository's disposable PostgreSQL
  application-state fixture. It creates a uniquely named test database from
  the configured test-admin DSN and drops it after the test; prove the DSN and
  target are the disposable fixture before any database write.
- Do not connect to, restart, reseed, or reconfigure the operator's live UI
  5202, API 8000, or DOGFOOD 5203.
- Any manual browser witness must use a separately assigned UI/API port pair
  and isolated test World/data, not private corpus content unless the operator
  explicitly directs that exact private fixture.
- Do not call model providers or expose credentials; no provider work is needed
  for this contract.

If the existing test fixture cannot isolate the required PostgreSQL state,
stop and return the exact resource gap to PRIME rather than borrowing a live
database.

## §8 Required review and stop conditions

Before merge, PRIME independently reviews one exact implementation head and
requires all of §3 evidence. Block and return to design if:

- WorkObject kind is not immutable or exact Plan source kind cannot be proven
  from durable identity;
- a WorkRevision is not retained/readable by exact ID after later edits;
- storage cannot atomically bind the Run and manifest to the Plan revision;
- Plan structure cannot be validated through the existing owning parser;
- serving the full pinned Plan would require a content copy or latest-pointer
  fallback;
- preserving Run/Plan separation requires a schema/public contract not reviewed
  here;
- implementation needs a path or runtime resource owned by another active lane
  and no explicit split/transfer is approved.

No acceptance claim may exceed the concrete tests and isolated operator
witness actually completed.
