---
title: Saved World Plan → Playable Run adoption
document_class: implementation_handoff
status: ACTIVE
created_at: "2026-10-04"
activated_at: "2026-10-06"
workstream: DEMO
design_authority: "../Design/DESIGN-world-plan-playable-adoption.md"
design_base: "Buddy main 04bd667d7f57a3c7b8b35f49d20a15562811a45f"
pr_topology: serial
implementation_base: "08e8cbe1207b74b0e15c6f95070899c5cc7c69fd"
implementation_branch: codex/demo-plan-run-activation-contract
implementation_pr: "https://github.com/Drakosfire/DungeonMindBuddy/pull/931"
app_state_commit: "6eae57016aa03ebac4e3135928a90eab4295fc7a"
server_commit: "96a75cf48e83e8f3cf49e2cc0d235476a3820209"
demo_code_commit: "ef2bf4054e065a98d0d0bf3253fa891be35383ac"
---

# HANDOFF — Start and reopen a Run from the exact saved World Plan

> This ACTIVE handoff pins the serial owner sequence, exact write lease,
> implementation PR, and isolated test resource described below.

## Status and activation record

**Status: ACTIVE — PRIME explicitly activated the #931 DEMO stage and
authorized reconciling this handoff on the same branch and PR.** The accepted
design is PR #907 head 7d44c33cc6e240bd711b6e202bc4042ea52ea9b7, merged at
d8e861661716d2fa8c1fb1e3e56ef08268d32da8. At activation, Buddy main was
`04bd667d7f57a3c7b8b35f49d20a15562811a45f`. After SERVER PR #935 merged,
current main advanced to `08e8cbe1207b74b0e15c6f95070899c5cc7c69fd`, and #931
was re-anchored there before final review. This serial PR is
[DEMO: pin Plan-to-Run activation contract](https://github.com/Drakosfire/DungeonMindBuddy/pull/931)
on `codex/demo-plan-run-activation-contract`. Its rebased owner commits are
APP-STATE `6eae57016aa03ebac4e3135928a90eab4295fc7a` followed by SERVER
`96a75cf48e83e8f3cf49e2cc0d235476a3820209`, then DEMO
`ef2bf4054e065a98d0d0bf3253fa891be35383ac`. The activation pin was published
at `f00859c0a7bf1b9c907b0ba7472cce14787ade80` before DEMO product edits. The
rebased ten UI file blobs are identical to pre-rebase code commit
`655edf9615dc3514b54755b4ac24562023cf1164`, which PRIME is independently
reviewing. The APP-STATE and SERVER owner code/test blobs also match their
pre-rebase commits `f644dfc61dc2531eac6a77416cf4c49dcbf51258` and
`7375b52b1b59353b605c56f22ec6d79999b576a8`; no conflict resolution changed
those files. The handoff remains ACTIVE while PRIME's final cumulative-head
review and the PR merge are pending; the write lease has not been released.

The accepted request/replay contract needs no migration or schema addition.
The existing create_world_play_run arguments remain World ID, Run ID, Plan
WorkObject ID, expected current revision number and digest. APP-STATE resolves
and stores the WorkRevision ID atomically and reads historical Run aggregates
from the stored source pin. Its Plan-backed rebase guard runs before the
same-target early return. SERVER confirms the existing World V2 route and
response are sufficient and owns the manifest-integrity requirements below.

PRIME confirmed these sequencing and path dispositions:

- PR #927 stays a separate queued Plan↔Play conversation lane. It is not a
  predecessor for this slice.
- PR #914's visual review hold is not a global product gate. PRIME transferred
  the native Run projection files listed in §4 to this slice; freeze those
  paths on #914 while this lease is active.
- PR #917 remains prototype evidence, not a product predecessor. DOGFOOD
  withdrew its production reservation; PRIME transferred the production Plan
  Page and mounted test paths listed in §4 to this slice. Freeze those paths
  on #917 while this lease is active.
- PRs #886 and #904 are merged and their leases are closed. Their historical
  handoffs are not current reservations.
- PRIME transferred only the assigned Plan→Run roadmap entries from #914 to
  #931. Freeze those entries on #914 while this lease is active.

Activation record:

1. **Authority and topology:** PRIME authorized the exact §4 path lease and
   the serial APP-STATE → SERVER → DEMO sequence on the existing #931 branch
   and PR. The #914 projection and roadmap entries and #917 Plan Page paths
   are exclusive to this slice until released or transferred.
2. **Current base and owner sequence:** remote `main` is
   `08e8cbe1207b74b0e15c6f95070899c5cc7c69fd` after #935 merged. PR #931 was
   re-anchored on this main, retaining APP-STATE → SERVER → DEMO order. The
   refreshed #935 paths are SERVER-only; the file inventories show no overlap
   between #935 and the leased #931 paths.
3. **Test resource:** use only PRIME's pinned disposable PostgreSQL 16
   container `8d01d8b8c07ab6712e522bcba62e975df10d98185f6302c9f708b417d5a8b508`,
   with its inspected loopback mapping and per-test fixture recorded in §7.
   The live mapping is `127.0.0.1:32768 → 5432`; PRIME confirmed that this
   supersedes the earlier `32782` note. `pg_isready` succeeds. DEMO ran the
   assigned PostgreSQL fixtures: APP-STATE passed 11/11 and SERVER passed
   31/31; a read-only post-run catalog check found no remaining test databases.
   Full test and UI verification details are recorded in §7.

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
- **Preimplementation finding, now addressed by pinned APP-STATE commit
  `6eae57016aa03ebac4e3135928a90eab4295fc7a`:** the original admission path
  rejected kind plan in admit_playable_revision and
  resolve_pinned_playable_revision. The contribution now admits World-owned
  Plans only on the World V2 path, preserves Campaign V1 Runbook-only behavior,
  and rejects Plan-backed rebase before the same-target retry.
- APP-STATE must reject Plan-backed rebase before any same-target no-op return.
  Starting a separate Run from a newer Plan revision remains allowed.
- **Preimplementation finding, now addressed by DEMO code commit
  `ef2bf4054e065a98d0d0bf3253fa891be35383ac`:** PlaySurfacePage loaded every
  World Run through the Runbook-specific exact-revision read, checked that the
  current Runbook remained active/current, and offered Runbook rebase when a
  newer revision appeared. That behavior remains for Runbook Runs. A Plan-backed
  Run now resolves its exact historical Plan revision and reopens read-only
  without a rebase prompt, latest-revision fallback, or Plan-active requirement.
- **Preimplementation finding, now addressed by the same DEMO code commit:**
  the native Run projection rejected a World revision whose kind was `plan`.
  The existing projection seam now allows an exact historical Plan revision
  for World V2 Play while preserving Campaign V1 Runbook-only behavior. PRIME
  transferred this seam and its focused owning test from #914; no parallel
  parser/projection or Runbook cast was added.
- **Preimplementation finding, now addressed by pinned SERVER commit
  `96a75cf48e83e8f3cf49e2cc0d235476a3820209`:** ensure_v2_native_ready read a
  Runbook kind and the v2 sealed-structure comparison converted edge
  collections to sets. The contribution admits the intended World Plan source
  and rejects duplicate persisted edge tuples before READY or Play context.
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

## §4 Exclusive write sets — ACTIVE lease

These exact path sets are PRIME's active, exclusive write lease for PR #931,
branch `codex/demo-plan-run-activation-contract`, re-anchored on Buddy main
`08e8cbe1207b74b0e15c6f95070899c5cc7c69fd` after #935. The single PR is serial and the
owner sets are disjoint. APP-STATE and SERVER have contributed their listed
paths in order; DEMO owns the final ten product paths below.

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

PRIME transferred the production projection and owning-test paths from #914
to this slice. Freeze those paths on the #914 branch; retain its evidence and
reconcile/rebase after this slice changes production. The visual review hold
remains on #914 and does not block this slice.

PRIME transferred PlanSurfacePage.tsx and PlanSurfacePage.test.tsx from the
#917 prototype reservation to this production slice. Freeze those paths on the
prototype branch and reconcile them later. #917 remains prototype evidence,
not a production predecessor. Do not read, update, or restart its runtime as
part of this handoff.

No routes, workspace registry, public API type, shared API wrapper, schema,
migration, dependency, Graph, Agent conversation, native corpus, provider, or
operator-runtime path is included. The current World V2 request/response is
sufficient unless an owner demonstrates a concrete missing fact and PRIME
reviews a changed contract before edits.

## §5 Topology and state-authority sync

**Topology: serial, one cross-owner implementation PR, #931.** The pinned
branch is `codex/demo-plan-run-activation-contract`, based on
`08e8cbe1207b74b0e15c6f95070899c5cc7c69fd`. Owner commits are APP-STATE
`6eae57016aa03ebac4e3135928a90eab4295fc7a`, SERVER
`96a75cf48e83e8f3cf49e2cc0d235476a3820209`, then DEMO
`ef2bf4054e065a98d0d0bf3253fa891be35383ac`. Each owner writes only
its §4 paths; later contributors consume the prior exact commits and do not
edit earlier-owner paths without an explicit transfer. No parallel or stacked
implementation PR is authorized. If a new capability or public contract is
needed, preserve the work and return to PRIME for a split or revised handoff.

PRIME also authorized this same PR's documentation sync set:

- `Docs/Roadmaps/ROADMAP-demo.md`: update only the assigned Plan→Run entries
  transferred from #914. Record the #925 Graph code integration merge and
  keep remaining live Graph/provider acceptance distinct when updating the
  next action. Mark this slice complete only after its actual evidence.
- This handoff: record the exact implementation head, review and merge
  evidence, and release owner/path/resource leases only after completion.
- `Docs/Plans/HANDOFF-DEMO-world-owned-play-runs.md`: make only the verified
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

**No operator, provider, or shared-runtime mutation is authorized.** Do not
start a manual product server or use an operator/DOGFOOD endpoint for this
contract.

The assigned test resource is PRIME's disposable PostgreSQL 16 container
`8d01d8b8c07ab6712e522bcba62e975df10d98185f6302c9f708b417d5a8b508`. On
2026-10-06, `docker inspect` verified it was running, had tmpfs
`/var/lib/postgresql/data` with `size=1g`, no mounts, and only the loopback
mapping `127.0.0.1:32768 → 5432`; `pg_isready` succeeded. PRIME confirmed
that port `32768` is authoritative for this exact container, superseding the
earlier `32782` note. `docker ps` found no published container on `32782`.
Configure `DMB_APPLICATION_STATE_TEST_DATABASE_URL` to
use database `postgres` on `127.0.0.1:32768` with the container's disposable
fixture credentials from local configuration; do not store or echo those
credentials here.

Use that variable with the repository's disposable per-test fixture and
TestClient. The fixture source in `tests/application_state/conftest.py`
confirms each test generates a unique
`dungeonbuddy_app_state_test_{uuid}` database, applies migrations to it, then
clears the fixture DSN, terminates its connections, and drops it in `finally`.
Do not use the fixture's default admin endpoint or any other database.

**DEMO verification checkpoint (2026-10-06):** the assigned mounted UI suites
passed 148/148 tests. APP-STATE's PostgreSQL owner suite passed 11/11, and
SERVER's World V2/manifest suites passed 31/31 with 11 existing Pydantic
`schema`-shadow warnings. Those database runs used the exact pinned DungeonMind
source commit `7c69e447f6d4acc963ac09c6fb9cb48cc1c5b9cc` from a temporary source
archive because the installed test package was stale; no dependency or lockfile
was changed. The post-run catalog check found no test databases. The cumulative
`git diff --check` passed. UI typecheck retains the inherited unrelated
`ThreatPublicationPanel.tsx(553,77): Cannot find namespace 'JSX'` diagnostic;
the affected file is outside this lease and has no changed-file diagnostics.
PRIME's independent exact-head review and PR merge remain pending.

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
