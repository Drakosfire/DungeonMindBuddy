# BUDDY — V9.A native canary qualification and process rollback

Status: ACTIVE. Owner/designer: Elderwyld vNext completion lane.
Authority: operator's active optimize-before-cutover/finish-vNext goal, including
implementation, review, merge and launch authorization. No PRIME coordination
required. V8 prerequisite is satisfied by Core #229 merge
f770098ad27b772e6351f2827a2b7bd6628705e8, reviewed final head6b3c52d and
all-green CI44442480375 attempt2. Core runtime remains4b6516e; that merge changes
only evidence/control documents. Read the canonical V8 acceptance artifact there.

Base/candidate: Buddy92cc639aa6da1f89a07de69693a82c7b7e293d59, fetched main at
activation. Branch: codex/v9-native-canary-qualification. Freeze this exact source
composition rather than chase subsequent main movement. Core dependency4b6516e
is unchanged; V8 qualified Buddy0a746752 is the semantic predecessor, not automatic
qualification of the later hosted/lore/combat/store changes or APP schema.

## Outcome and serial boundary

Can the selected native runtime start against a verified restore of current real
Elderwyld authority, preserve ordinary consumer semantics, and undergo a process
rollback without rewriting knowledge/history or disturbing another runtime?

One serial Buddy-owned qualification PR after V8. A separately bounded V9.B
activation follows only after this slice passes. V10 retirement and V11 deployed
baseline remain in the full objective. Do not substitute a successful canary for
actual cutover or claim this slice completes vNext.

Three repository paths only: this handoff;
Docs/Reports/V9-native-canary-qualification-v1.json;
Docs/Plans/HANDOFF-BUDDY-native-validated-command-adoption.md (truthful #4029 seal).
No route/DTO/auth/runtime implementation, schema authoring, dependency change,
provider/ingestion experiment, production DDL/backfill or serving switch. If a
runtime defect is found, rebrief and split its repair before acceptance.
Inspect relevant open PR leases before edits; new qualification paths are unique.

## Current discovery, not acceptance

- Port5202 is not listening. API8000/PID1002232 belongs to the separate dirty
  jev-freeze-dogfood checkout; it is outside this lease and is not a rollback target.
- Original operator checkout .env identifies Core at127.0.0.1:54330,
  database dungeonmind_cutover_live_restore_20261011, and separate APP state at
  127.0.0.1:54331/dungeonbuddy_application_state. Credentials stay private.
- Read-only discovery found native space elderwyld head
  rev:5293c1b237a0064bd16fffd080bfa6b1, different from the old V8 restored head.
  APP binding elderwyld→elderwyld is active/version3. Its validated-head field is
  historical binding metadata, not current-head authority.
- Core schema0021_native_source_withdrawal is behind required0022; only prior
  task-owned clones have0022/artifacts. Migration/backfill are explicit actions,
  never repairs performed by a read. Current native head/parent must be rechecked.
- Core/APP logical sizes observed1873402903/199449623 bytes. Projects has ample
  space, but logical size is not dump size or reclaimed bytes. No snapshot is
  yet created by this slice. Sources remain untouched.

## Operational lease and failure cases

Reuse the existing task root /home/drakosfire/Projects/.codex/v7-elderwyld-scope,
UUID48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8, writable verified before allocation.
New scratch/evidence stays in scratch/v9-buddy, caches in the existing task cache.
Use existing task PostgreSQL container codex-v8-live-head on32903 for uniquely
named Core/APP restores, never its retained V8 clone or unrelated databases.

Explicitly authorized operations for this slice: read-only source inventory;
consistent source Core/APP exports; restore into unique owned databases;
compatibility/lineage/binding/receipt/citation verification; migrate ONLY those
restores to accepted Core/Buddy schema; explicit derived artifact backfill there;
owned canary process startup/stop/restart/rollback on independently checked free
ports; provider-free consumer checks. No live source migration or history write.
APP/Core dumps are separate snapshots, not a cross-database atomic transaction;
record before/after head/binding and reject incoherent assumptions.

Reserve API18290/UI15202 only after confirming free. No use of8000 or5202 in
this qualification. Use loopback/local-operator configuration, exact source
attestation and explicit frontend proxy. No request traffic to other-lane API.
Preserve source/artifact locators and real restored managed binding; no fixture
binding substitution. Keep APP/Core databases distinct. Loading a restored real
binding is recovery proof, not direct live-serving proof.

No new worktree/environment is required initially: use the existing isolated
checkout sequentially. Before changing its Git source stop all owned processes
using it, commit/protect changes, then restart at an exact ref. Never change code
under a running process. Do not sync the shared venv. If a second immutable
checkout becomes necessary, obtain it through the managed worktree tool within
repository storage policy; do not allocate elsewhere as a fallback.

## Required evidence and verification

1. Record exact snapshot/dump hashes, versions, source/restore database identities,
   consistency boundaries and cleanup ownership. Preserve failures and unknowns.
2. Verify current head→genesis lineage, parent, revision/receipt/event consistency,
   domain/profile refs, real managed binding/version and source/citation identity.
   Never assume the old V8 head remains current; no old-name bridge.
3. Verify Core0022 and selected Buddy APP schema on restores; record additive
   migration/older-native compatibility. Backfill only explicit exact head/parent
   artifacts; verify ordinary-source/derived integrity and no authority mutation.
4. Qualify actual imported Core/Buddy file hashes, lock pin, frontend build/API
   mapping and full-app/lifespan startup. Installed package metadata alone is
   insufficient. Keep secrets out of logs and evidence.
5. Inventory intended managed projection, exact/complete object, neighborhood,
   evidence, source anchor, search and Plan subject-search selectors. Native writes
   have their own governed paths; one authority flag does not prove all routes.
6. Run owning native inspection/source/recap, publication/relationship, auth and
   affected newer consumer cohorts at exact source with existing disposable DB
   isolation. Qualify the final full SHA with the unmodified repo-owned hosted
   frontend verifier/canonical validator and normal lock. Later discovered-suite
   diagnostics apply if frontend implementation changes; none is authorized here.
7. Rehearse rollback using only owned processes/configuration and the same native
   authority/history. Establish a known-good native target first. Verify restart,
   loaded pins, head/binding, receipts/replay, fresh source authorization and exact
   citation reopening. No legacy fallback or restoring stale data over writes.
8. Independent cumulative review and normal automatic checks before merge. No
   baseline rerun or timing claim from diagnostic/profiled durations.

## Continuation and cleanup

V9.B must independently establish fresh live recovery readiness, selected-scope
write boundary, actual schema/artifact readiness, loaded serving composition and
mapping, then verify head/binding/receipts/citations after activation. This PR
cannot authorize a silent live DDL, APP upgrade or selector change by implication.
The operator's broader launch authority remains valid for that explicit next slice.

Retain unique refs, dumps, restore DBs, scripts/logs/receipts and canary resources
for qualification/activation review, owned by this lane. Record every created,
retained and removed path, owner/reason and cleanup follow-up. Do not blanket-clean
shared storage. No standing deletion permission: remove only specifically scoped
reproducible artifacts after active process/mount/connection, dirty/unique-data and
commit checks. Keep live sources, other-lane processes and prior V8 evidence intact.
Settle the actual #4029 merge in this PR; settle this slice after actual merge in
its dependent activation record, never by inventing a future merge identity.

## Pre-start clarification from independent boundary review

Before any canary process starts, establish these concrete gates:

- Snapshot receipt currently proves separate dump consistency and stable selected
  head/binding only. Source epoch/lifecycle and APP provisioning coherence need
  explicit restored/live comparison or a fresh appropriately bounded capture.
  Do not retrospectively claim unrecorded before-epoch checks.
- Inventory required file-backed artifact bodies, managed/source files and session
  dependencies. Copy and hash required authority or mount it explicitly read-only;
  identify unavailable locators. Never silently resolve mutable source-checkout
  paths as isolated canary authority.
- Pin an isolated dotenv root with explicit Core/APP restore DSNs, managed/artifact/
  session/world paths, frontend proxy and all intended native selectors. Inspect
  startup/background-write behavior; no source/other-lane defaults. Recheck free
  owned ports immediately before bind.
- Exact older native release rollback target is Buddy
  0a746752da32324256d83b018e884aa7cb8ad692 with Core4b6516e; forward target is
  frozen92cc639. Test BOTH against Core0022 and the forward APP0167 restore,
  without downgrading schema/data. Distinguish same-release restart from release
  rollback and record unsupported new APP payload kinds honestly. If backward
  compatibility is absent, rebrief a safe rollback target before activation;
  do not call a restart proof a release-rollback proof.

Snapshot capture completed in task scratch: Core947930229 bytes and APP102665777
bytes, hash-bound in current-authority-snapshot.json. Both source connections were
read-only; head/binding remained equal. APP source schema20261117_0160 is behind
selected candidate0167. These dumps are retained pending the additional coherence,
restore and file-authority checks above; no canary/rollback/activation success.
