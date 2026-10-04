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

**Status: BLOCKED — PRIME accepted the design premise at reviewed PR #907 head
be84bf001a1f810524f913bbfd2507269afa8b2c. The updated PR head still needs final
review; product-sequence and implementation resource/path gates are
outstanding.**

This handoff was prepared against Buddy main
0f42fec0812655bb37c87b6be9a7fe5741d7f25f. Re-anchor against live main and
current open PRs before any implementation dispatch; the base above is a
design-time reference, not an implementation pin.

Implementation may be activated only after all of the following are true:

1. PRIME's acceptance of the companion design's source identity, admission,
   revision, audience, and Runtime ownership decisions is recorded at reviewed
   PR #907 head be84bf001a1f810524f913bbfd2507269afa8b2c. The current updated
   PR head must receive final review before this handoff can move from BLOCKED
   to ACTIVE. That review does not itself activate implementation.
2. PRIME has re-anchored the Demo roadmap and confirmed the prerequisites and
   ordering for the saved-Plan card projection and shared World-conversation
   work. The current roadmap places same-content-to-Run after those steps; do
   not skip or silently resequence them. Before the card projection is treated
   as a satisfied predecessor, its owner must prove:
   - The exact saved World Plan WorkRevision and digest are projection
     authority. Cards derive from the existing versioned Markdown markers;
     there is no parallel card store and no minted Playable identity for
     unmarked prose.
   - The initial projection is GM-only. Unsupported or malformed authored
     Markdown remains readable in the Plan authoring surface but is never
     silently admitted as playable structure.
   - Marker identity, links, and card/document order remain equivalent through
     one supported editor transaction, ordinary Save, and fresh reopen at the
     resulting exact committed revision and digest.
   These are card-projection predecessor proofs, not card implementation work
   or paths leased by this handoff.
3. Re-anchor current UI ownership before allocating any Plan/Play entry path.
   #906's mounted-harness repair lease is closed. Buddy PR #904 merged at
   fb1c48d622c9d8d404b1dddb5d5f618e03cc7ef0; its temporary
   UI-integration/mounted-test lease is in post-merge settlement. #886 retains
   production Plan Page/shell paths pending its own accepted settlement or
   explicit handback. Do not infer that a path is available merely because
   #904 merged; PRIME must re-check active PRs and resolve a nonoverlapping
   lease.
4. Preserve the APP-STATE-confirmed supported Content mutation invariant:
   WorkObject kind is fixed at creation, mutation guards check the locked kind,
   and supported update SQL does not write kind. The implementation must
   include or retain an owning regression for attempts to retag kind. This is
   an application contract, not a database-trigger guarantee; privileged
   direct SQL outside the supported API is not an activation blocker. If a new
   supported writer can retag kind, stop and review the smallest versioned
   source-kind receipt with APP-STATE before admitting that writer.
5. DEMO, SERVER, and APP-STATE agree on the exact API/service contract and
   individually owned paths. PRIME records the exact implementation path
   allowlist, path owners, active PR/lease conflicts, and completion sync set.
6. Runtime/test resources are named and isolated. No active operator or
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
- At the Buddy main 6feb3059b2da4d2ec29966ce9723f0effc70108f re-anchor,
  APP-STATE confirmed that supported Content
  mutations preserve WorkObject kind (locked-kind mutation guard, update SQL
  does not write kind, import assigns kind at creation). This is an API
  invariant, not a database trigger; unsupported privileged SQL is not a
  product mutation gate. Evidence is in
  **src/application_state/content/service.py**,
  **src/application_state/content/repository.py**,
  **src/application_state/content/import_plans.py**,
  **src/application_state/content/import_runbooks.py**, and the existing
  wrong-kind regression in
  **tests/application_state/test_runbook_work_object_postgres.py**.
- Content retains exact WorkRevisions. Existing-Run resolution can read the
  exact historical revision after edits or discard; a current Plan read still
  requires an active object. New-Run current/active/clean admission and
  existing-Run exact historical read are distinct paths.
- Server manifest derivation already recognizes v1 Scene-first and v2
  Beat-first structures. Preserve both forms' current parser/readiness
  behavior; the existing v2 nonzero-Beat readiness check must not silently
  become a blanket v2-only Plan filter. Relevant evidence is in
  **apps/live_control_server/services/play_run_reference_manifest.py**,
  **apps/live_control_server/services/play_run_registry.py**, and
  **tests/test_live_play_run_reference_manifest.py**.
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
| Retry the existing Run ID with the original binding after the Plan changes, becomes dirty, or is discarded | Return the same historical Run/manifest binding without current/clean re-admission or receipt rewrite. |
| New Run requested from the wrong World, a Runbook, Campaign-owned/discarded Plan, dirty working copy, stale expected revision, or wrong SHA | Fail closed; no Run, manifest, copy, or cross-World fallback is created. |
| Valid existing v1 Scene-first Plan structure | Preserve current parser and Run-readiness behavior; do not silently reject it for not being v2 Beat-first. |
| Missing/unsupported/mixed/malformed markers, duplicate IDs, orphan/invalid edges, or no runnable structure under the existing readiness rule | Fail closed before partial Run creation; no inferred headings or auto-added markers. |
| Existing Run opened after Plan edit/discard | Reads its exact historical Plan revision; never substitutes the latest Plan. |
| Runtime choice and note mutation | Persists only to that Run; source Plan Markdown and WorkRevision remain byte-for-byte unchanged. |
| Plan includes Graph/source refs | No implicit Graph read, publication, or canon mutation. |

Required evidence includes:

- APP-STATE PostgreSQL transaction tests for exact Plan admission, owner/kind,
  the supported API's no-retag invariant, current-revision and
  clean-working-copy fences for a new Run, atomic Run+manifest creation,
  same-binding replay after current Plan state changes without rewriting the
  original receipt, conflict on changed binding, and exact pinned historical
  reads after later Plan saves and discard.
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
#906's mounted-harness repair lease is closed. #904 merged at
fb1c48d622c9d8d404b1dddb5d5f618e03cc7ef0, placing its temporary mounted-test
lease in post-merge settlement; re-check the current owner of
**PlanSurfacePage.test.tsx** at activation. #886 retains production Plan
Page/shell paths pending its own accepted settlement or explicit handback.
Do not rely on Git conflicts to arbitrate either path.

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

- a supported Content writer can retag WorkObject kind, or exact Plan source
  kind cannot be proven from the stable WorkObject identity; privileged
  out-of-contract direct SQL alone is not a stop condition;
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
