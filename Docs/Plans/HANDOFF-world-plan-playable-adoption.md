---
title: Saved World Plan → Playable Run adoption
document_class: implementation_handoff
status: BLOCKED
created_at: "2026-10-04"
workstream: DEMO
design_authority: "../Design/DESIGN-world-plan-playable-adoption.md"
design_base: "Buddy main 6507fd4a2ec00b5b9f6f9ee1ec2d7600e0b75121"
pr_topology: serial
implementation_branch: not_assigned
implementation_pr: not_authorized
---

# HANDOFF — Start and reopen a Run from the exact saved World Plan

> This is durable contract authority only. It remains BLOCKED and grants no
> implementation or runtime write lease.

## Status and activation gate

**Status: BLOCKED — PRIME accepted the design at PR #907 head
7d44c33cc6e240bd711b6e202bc4042ea52ea9b7, merged at
d8e861661716d2fa8c1fb1e3e56ef08268d32da8. Buddy main is re-anchored at
6507fd4a2ec00b5b9f6f9ee1ec2d7600e0b75121, including merged PR #925. PRIME
confirmed the next functional slice is saved World Plan → exact pinned Run →
read-only reopen. The remaining gates are the exact disposable test-resource
pin and PRIME publishing ACTIVE with the final allowlist.**

APP-STATE confirmed the #907 request/replay contract on main 6507: no
migration or schema addition; the existing create_world_play_run arguments
remain World ID, Run ID, Plan WorkObject ID, expected current revision number
and digest. The service resolves and stores the WorkRevision ID atomically.
Historical Run aggregate reads resolve the stored source pin. APP-STATE also
confirmed the Plan-backed rebase guard must run before the same-target early
return. SERVER confirmed the existing World V2 route and response are
sufficient and provided the manifest-integrity requirements below.

PRIME confirmed these sequencing and path dispositions:

- PR #927 stays a separate queued Plan↔Play conversation lane. It is not a
  predecessor for this slice.
- PR #914's visual review hold is not a global product gate. PRIME transfers
  the existing native Run projection files listed in §4 to this slice before
  activation; #914 does not need to merge first.
- PR #917 remains prototype evidence, not a product predecessor. DOGFOOD
  withdrew its production reservation; PRIME transfers the production Plan
  Page and mounted test paths listed in §4 to this slice. #917 does not need to
  merge first.
- PRs #886 and #904 are merged and their leases are closed. Their historical
  handoffs are not current reservations.

Implementation may be activated only after all of the following are true:

1. PRIME pins the exact §4 allowlist and one serial owner sequence:
   APP-STATE → SERVER → DEMO. The transfers from #914 and #917 remain
   exclusive to this slice while active.
2. PRIME pins the test-resource identity: use only the disposable,
   per-test database fixture configured by DMB_APPLICATION_STATE_TEST_DATABASE_URL
   and TestClient. Prove the fixture creates a unique database for each test
   and never targets operator or DOGFOOD state.
3. PRIME changes this handoff to ACTIVE with the exact implementation branch,
   verified fixture configuration and PR topology. Until then, do not start
   product implementation, runtime services, provider work, or
   operator-database changes.

## §1 Mission and invariant

Provide one explicit GM action to start a new managed-World Play Run from the
selected saved World Plan's exact current committed WorkRevision, then reopen
that Run using the same immutable source revision.

The source identity is the selected World ID, existing Plan WorkObject ID,
exact WorkRevision ID, revision number and content SHA-256. WorkObject kind
remains plan. The Run has its own Run ID and Run revision. Its sealed reference
manifest is derived atomically from the same exact Plan WorkRevision. Starting
or reopening must not convert, clone, retag, or rewrite the Plan.

A later Plan Save creates a new WorkRevision and never retargets an existing
Run. Opening an old Run reads its retained revision even if the Plan is later
edited, dirty, or discarded. A separate new Run may bind the newer current
revision.

## §2 Current contract and owning boundaries

Read these authorities at activation:

1. **DESIGN-world-plan-playable-adoption.md**.
2. **ARCHITECTURE-playable-material-and-runtime.md**.
3. **Docs/Roadmaps/ROADMAP-demo.md**, including its active entries.
4. The accepted World Plan/editor and World PlayRun V2 contracts.
5. Current APP-STATE Content and Play admission, replay, read, and rebase
   implementations.

Re-anchored source findings:

- The existing World V2 create/replay request already carries
  playable_artifact_id, expected_playable_revision and
  expected_playable_content_sha256. Its response carries
  playable_work_revision_id. SERVER reports no need to edit routes, workspace
  document registry, API types or schema for this slice.
- The exact current Plan revision can be read through the existing generic
  committed-revision boundary. DEMO must verify the returned World, WorkObject,
  WorkRevision ID, revision number and digest against the selected Plan or Run.
- APP-STATE confirms new-Run admission requires the active World-owned Plan,
  exact current committed revision and a clean working-copy boundary.
  Same-binding replay of an existing Run precedes current/clean re-admission.
  Existing Run read resolves its stored historical WorkRevision after Plan
  edit or discard.
- APP-STATE currently rejects kind plan in admit_playable_revision and
  resolve_pinned_playable_revision. Its new-Run path must widen only the
  intended World V2 boundary while preserving Campaign V1 and Runbook behavior.
- APP-STATE must reject Plan-backed rebase before any same-target no-op return.
  Starting a separate Run from a newer Plan revision remains allowed.
- PlaySurfacePage currently loads every World Run through the Runbook-specific
  exact-revision read, checks that the current Runbook remains active/current,
  and offers Runbook rebase when a newer revision appears. That behavior must
  remain for Runbook Runs. A Plan-backed Run instead resolves its exact
  historical Plan revision and reopens read-only without a rebase prompt,
  latest-revision fallback, or Plan-active requirement.
- The current native Run projection rejects a World revision whose kind is
  plan. PRIME has transferred that projection seam and its focused owning test
  from #914 to this slice. Extend the existing seam; do not add a parallel
  parser/projection or cast a Plan record to Runbook.
- SERVER's ensure_v2_native_ready currently reads a Runbook kind, and its v2
  sealed-structure comparison converts edge collections to sets. The Run
  contract must admit a Plan source and reject duplicate persisted edge tuples
  before READY or Play context.
- Existing World V2 persistence already records World, WorkObject ID,
  WorkRevision ID, revision number and digest and seals the manifest. Reuse
  that identity path.

APP-STATE owns atomic source admission, replay, historical resolution,
Run persistence and database evidence. SERVER owns World V2 preflight,
manifest validation/READY and route-boundary evidence. DEMO owns Start Play,
Plan/Play navigation and mounted product evidence. PRIME owns activation,
path arbitration, cross-owner order and independent exact-head review. No
DungeonMind Graph read, publication or canon write is included.

## §3 Observable contract and required evidence

The one implementation PR must prove these behaviors at their owning
boundaries:

| Sequence | Required result |
| --- | --- |
| Active World Plan, current committed revision, clean working-copy boundary, valid admitted Playable structure | Explicit Start Play creates one World Run and sealed manifest atomically from the selected Plan revision. |
| Start response | World, WorkObject ID, WorkRevision ID, revision number and digest agree with the exact Plan revision used for admission. |
| Plan Save after Run creation | The Plan receives a new WorkRevision; the existing Run and manifest remain pinned to the earlier ID, revision number and bytes. |
| Reopen after Plan edit, dirty working copy or discard | Play reads the Run's exact historical Plan revision and manifest. It does not require the Plan to remain active/current, show rebase_required, call Run rebase/progress mutation, or follow the Plan's latest pointer. |
| Same-binding replay for an existing Run ID after Plan changes | Return the stored Run and manifest without current/clean re-admission or receipt rewrite. A changed binding conflicts. |
| Start a second Run after a later Plan Save | The second Run can bind the new current revision; the first Run remains unchanged. |
| Wrong World, Runbook/Campaign source, discarded or dirty Plan, stale revision, wrong SHA, or invalid structure on new Run | Fail closed before Run/manifest creation. No fallback, inferred marker, partial Run, or content copy is created. |
| Existing valid v1 Scene-first and v2 Beat-first structures | Preserve their current parser and readiness behavior. Do not impose a new grammar or reject valid v1 solely for not being v2. |
| Missing, mixed, malformed, duplicate-ID, orphan-edge, invalid-edge, or non-runnable structure | Fail closed under the existing admission/readiness rules. Do not infer headings or insert markers. |
| Editor Save and fresh Plan reopen before Start | The same World and Plan WorkObject reopen at the exact committed WorkRevision ID, revision number and digest. Authored marker identity, links and document order remain intact. Start sends that exact current revision number and digest. |
| Successful read-only Run reopen | No Plan content/WorkRevision, sealed manifest, Run revision/progress or Graph mutation occurs. The existing active-Run focus pointer may be set after verified load; failed, foreign or corrupt loads must not update it or display READY. |
| Plan contains Graph/source references | No implicit Graph read, publication, or canon mutation occurs. |

### Persisted v2 manifest integrity

Read-only review at Buddy main
271e15177b5675c686b32f6ea1cfcd6fa25735a6 found that
PlayRunReferenceManifestV2._validate_membership does not require unique edge
tuples and compare_v2_sealed_structure converts edge collections to sets. A
duplicate otherwise-valid persisted tuple can therefore disappear in
comparison.

Before READY or Play context, reject every duplicate persisted
(option_id, effect, target_kind, target_id) tuple and compare the preserved
multiplicities against derivation from the exact pinned WorkRevision. Do not
rebuild or rewrite a corrupt manifest, Run, source revision or progress. Prove
this through stored-manifest corruption at the owning PostgreSQL and
World-V2/Play boundary; a helper-only test is insufficient.

### Required owner evidence

- APP-STATE PostgreSQL: Plan-kind and World-owner admission; current/clean
  fences for a new Run; atomic Run+manifest creation; supported no-retag
  invariant; exact WorkRevision retention; same-binding replay after source
  change/discard without receipt rewrite; conflict on changed binding; and
  Plan-backed rebase rejection before the same-target return.
- SERVER: explicit World-scoped new-Run preflight and failure mapping; no
  Run/manifest on invalid new admission; stored duplicate-edge corruption
  rejected before READY/Play context; exact GET/read of the Run and sealed
  manifest remains bound to the stored revision.
- DEMO mounted path: selected Plan identity persists through Start; dirty,
  stale, source-switch, World-switch and late-response cases cannot retarget an
  attempt or show false success. Save/reopen the source before Start and prove
  exact WorkRevision identity, digest, marker identity, links and order.
  After Plan edit/discard, reopen the existing Run against its original pinned
  source; preserve Runbook behavior and do not call Plan rebase.
- Verify that opening the Run leaves the Plan bytes, Run revision/progress and
  sealed manifest unchanged. The existing active-Run focus pointer may update
  only after successful verified load.
- Re-run the exact cumulative base-to-head diff and all assigned owner suites.
  A helper test cannot substitute for transaction, READY/Play-context, or
  mounted product evidence.

## §4 Proposed exclusive write sets — BLOCKED, not an active lease

The following exact path sets are proposed for PRIME activation from Buddy
main 6507fd4a2ec00b5b9f6f9ee1ec2d7600e0b75121. They are not writable until
PRIME publishes the ACTIVE handoff. The single PR is serial and the owner sets
are disjoint.

**APP-STATE**

- src/application_state/content/playable_admission.py
- src/application_state/play/service.py
- tests/application_state/test_play_runtime_world_runs_postgres.py

Rebase rejection and the current/clean/replay distinctions belong in the
existing World Runs PostgreSQL test path. No additional APP-STATE test path is
leased. If another test file proves necessary, stop and get a single-owner path
transfer before editing it.

**SERVER**

- apps/live_control_server/services/play_run_reference_manifest.py
- apps/live_control_server/services/play_run_registry.py
- tests/test_play_run_reference_manifest.py
- tests/test_world_play_runs_v2.py

Test persisted duplicate-edge corruption at the SERVER-owned manifest and
World V2/Play boundary. If an additional test under tests/application_state is
needed to prove READY behavior, SERVER must document the concrete boundary gap
and obtain an explicit single-owner path transfer before editing it. Do not
double-lease or silently expand the APP-STATE set.

**DEMO**

- apps/live-control-ui/src/playSurface/startRunAttempt.ts
- apps/live-control-ui/src/playSurface/startRunAttempt.test.ts
- apps/live-control-ui/src/playSurface/StartRunPanel.tsx
- apps/live-control-ui/src/playSurface/StartRunPanel.test.tsx
- apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx
- apps/live-control-ui/src/playSurface/PlaySurfacePage.test.tsx
- apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx
- apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx
- apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.ts
- apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.test.ts

PRIME transfers the production projection and owning-test paths from #914 to
this slice, effective before activation. Freeze those paths on the #914 branch;
retain its evidence and reconcile/rebase after this slice changes production.
The visual review hold remains on #914 and does not block this slice.

PRIME transfers PlanSurfacePage.tsx and PlanSurfacePage.test.tsx from the #917
prototype reservation to this production slice. Freeze those paths on the
prototype branch and reconcile them later. #917 remains prototype evidence,
not a production predecessor. Do not read, update, or restart its runtime as
part of this handoff.

No routes, workspace registry, public API type, shared API wrapper, schema,
migration, dependency, Graph, Agent conversation, native corpus, provider, or
operator-runtime path is included. The current World V2 request/response is
sufficient unless an owner demonstrates a concrete missing fact and PRIME
reviews a changed contract before edits.

## §5 Topology and state-authority sync

**Topology: serial, one cross-owner implementation PR.** APP-STATE contributes
first, SERVER second, DEMO last. Each owner writes only its §4 paths; later
contributors consume the prior exact commits and do not edit earlier-owner
paths without an explicit transfer. No parallel or stacked implementation PR
is authorized. If a new capability or public contract is needed, preserve the
work and return to PRIME for a split/revised handoff.

The eventual implementation PR's authorized documentation sync set is:

- Docs/Roadmaps/ROADMAP-demo.md: record #925 Graph code integration as merged,
  keep any remaining live Graph/provider acceptance distinct, and update the
  next action and this slice's completion only after its real evidence.
- This handoff: record its exact implementation head, review/merge evidence and
  released owner/path/resource leases after completion.
- Docs/Plans/HANDOFF-DEMO-world-owned-play-runs.md: make only the verified
  #820 C2 completion correction. The current ROADMAP-demo ledger records PR
  #820 merged at bfa741261e715eadb48d873f87fccc1764417da8 with the independent
  mounted Play/Start Run witness; correct the stale C2 ACTIVE header without
  redesigning C1/C2 semantics.

Do not pre-mark the in-flight slice complete, invent its merge SHA or review
count, or create a separate status-only PR.

## §6 Scope boundaries

Included:

- One explicit Start Play action for an existing saved World Plan.
- Reuse of the same Plan WorkObject and exact immutable WorkRevision.
- Fail-closed kind, World-owner, current/clean, revision, digest and structure
  admission for a new Run.
- Read-only reopen of the historical pinned Plan revision after later Plan
  edits or discard.
- Existing Runbook starts and rebase behavior remain unchanged.
- Source Save/reopen proof before Start and exact read-only reopened source.

Excluded:

- Plan-to-Runbook conversion, content copying, second authored store, or
  source-kind receipt.
- Draft/stale-revision starts, inferred playable markers, or new grammar.
- Plan-backed Run rebase. APP-STATE rejects it even when the requested target
  matches the stored Plan pin; a newer Plan may start a separate Run.
- New Run choices, notes, rolls, selected results, combat outcomes or any
  additional durable Run actions. Existing Run behavior and source separation
  must remain unchanged.
- Player-facing audience classification; the first projection is GM-only.
- Graph reads/writes, evidence publication, DungeonMind mutation, or
  Runtime-to-World canon promotion.
- Provider/model calls, new credentials, private corpus changes, Generation
  Engine changes, or any E5 write lease.
- Operator UI/API/database, DOGFOOD runtime, prototype runtime, or changes to
  ports 5202, 8000 or 5203.

## §7 Runtime and resource ownership

**No runtime or operator-database mutation is authorized while BLOCKED.**

At activation, use only the disposable per-test database fixture configured by
DMB_APPLICATION_STATE_TEST_DATABASE_URL with TestClient. Prove that the fixture
creates a unique database for each test before the first database write.
Record the fixture identity and cleanup behavior in the ACTIVE handoff. Do not
start a manual product server or use an operator/DOGFOOD endpoint for this
contract.

Do not connect to, restart, reseed or reconfigure operator UI 5202, API 8000,
DOGFOOD 5203, the prototype backend or any operator/shared database. Do not
call providers, use private corpus content, or expose credentials. A manual
browser witness is outside this contract unless PRIME separately assigns an
isolated synthetic environment.

If the assigned fixture cannot prove database isolation, stop and return the
exact resource gap to PRIME. Never borrow the operator or DOGFOOD runtime.

## §8 Required review and stop conditions

PRIME independently reviews one exact implementation head and the cumulative
base-to-head diff. Block and return to design if:

- A supported Content writer can retag WorkObject kind or the exact Plan source
  cannot be proven from stable WorkObject identity. Privileged out-of-contract
  direct SQL alone is not a product mutation blocker.
- The exact WorkRevision is not retained/readable after later Plan edits or
  discard, or the Run/manifest cannot be atomically bound to it.
- A Plan-backed rebase can pass, including an identical-target replay.
- Plan structure cannot be validated by the existing owning parser while
  preserving v1 and v2 readiness behavior.
- Duplicate persisted v2 manifest edges disappear during comparison or reach
  READY/Play context.
- Reopen requires a content copy, latest-pointer fallback, Plan-active check,
  Run rebase, or mutation of the sealed manifest or Run progress.
- A new schema/public API contract, additional path or runtime resource proves
  necessary. Preserve evidence and return the exact expansion to PRIME.
- The slice adds any Run action or Graph behavior outside §6.

No acceptance claim may exceed the concrete tests, isolated resource and
operator-facing evidence actually completed.
