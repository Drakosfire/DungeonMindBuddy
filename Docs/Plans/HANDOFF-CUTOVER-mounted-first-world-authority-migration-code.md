---
pr_body_template: |
  ## Handoff pointer
  - Workstream: CUTOVER / D.2C2 — mounted first-world authority migration
  - Flow: CUTOVER
  - Direction: CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-CUTOVER-mounted-first-world-authority-migration-code.md`
  - Frozen design authority: `Docs/Plans/HANDOFF-CUTOVER-mounted-first-world-authority-migration.md`
  - Exact implementation base: `f1eae2a3d27e430ee19e254d5b52fa556b2632ff`
  - Design PR #644 merge: `f1eae2a3d27e430ee19e254d5b52fa556b2632ff`
  - Accepted design head: `ded066cec49c3840c3b19c3e817ffa569a116f39`
  - Design review: Cycle 2 PASS-equivalent `5025378684`
  - DungeonMind provider: PR #46 merge `bf40e933bdedf3cf08bb23a07a135958bdb7cc6b`

  ## Mission
  Move the mounted first-world/bootstrap workflow from Buddy filesystem/Kernel graph authority onto DungeonMind's reviewed zero-parent initialization authority, preserving Buddy exact-run/source/review authority and exact retry semantics.

  ## Merge contract
  - native review eligibility + prepare use `WorldGraphInitializationAuthority.probe()`
  - native confirm creates/replays exactly one DungeonMind `D_0` with `parent_revision_id=None`
  - no synthetic/EMPTY/baseline parent; native `baselineRevisionId=null`
  - no Buddy World Graph files are opened/created on mounted native first-world review/prepare/confirm
  - exact `SourceArtifactV2 + SourceRevision` closure
  - accepted nodes map to `CREATED_NEW`; accepted edges map to neutral `None`
  - genesis semantic profile is the builtin worldbuilding descriptor
  - exact retry, lost-response restart, and two synchronized identical confirms recover to the same receipt/D_0
  - changed plan/source/contribution/actor/profile fails closed
  - explicit `buddy_files` compatibility remains until D.3
  - D.2A Threat and D.2B existing-world worldbuilding regressions remain green
  - D.2C predecessor state authorities are synchronized truthfully; D.3 remains false
---

# HANDOFF — CUTOVER D.2C2 CODE: mounted first-world authority migration

**Created:** 2026-08-25  
**Status:** ACTIVE — IMPLEMENTATION DISPATCH  
**Workstream / flow:** `CUTOVER`  
**Direction:** CODE → REVIEW  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Branch:** `cutover/mounted-first-world-authority-migration`  
**Exact implementation base:** `f1eae2a3d27e430ee19e254d5b52fa556b2632ff`  
**Frozen design authority:** [`HANDOFF-CUTOVER-mounted-first-world-authority-migration.md`](HANDOFF-CUTOVER-mounted-first-world-authority-migration.md)  
**Design PR #644 merge:** `f1eae2a3d27e430ee19e254d5b52fa556b2632ff`  
**Accepted design head:** `ded066cec49c3840c3b19c3e817ffa569a116f39`  
**Design review:** Cycle 2 PASS-equivalent `5025378684`  
**DungeonMind provider merge:** `bf40e933bdedf3cf08bb23a07a135958bdb7cc6b` — PR #46  
**DungeonMind accepted provider head:** `bc2800b1d09aa70cf33d92ea6b8fc4a786f4b999`  
**Provider review:** Cycle 3 PASS-equivalent `5024825675`  
**Successor:** D.3 Buddy graph-engine demolition  

> This file is the implementation dispatch wrapper. The merged #644 handoff is the semantic design authority. If this wrapper and the merged design conflict, stop and re-brief rather than choosing locally.

---

## 1. Mission and merge-ready invariant

Implement the last mounted Buddy World Graph writer migration:

```text
Buddy exact-run review + source/workspace admission
  → storage-neutral first-world reviewed plan
  → WorldGraphInitializationAuthority
  → DungeonMind ReviewedWorldInitializationCommandV1
  → DungeonMind atomic first-world initialization
  → D_0.parent_revision_id = None
```

Merge-ready invariant:

> **In `DUNGEONMIND_WORLD_GRAPH_AUTHORITY=dungeonmind`, mounted first-world review eligibility, prepare, confirm, exact retry, lost-response recovery, and concurrent identical confirm obtain graph initialization truth only through DungeonMind-backed initialization authority. They do not open, create, hydrate, replay, rebuild, or verify against Buddy filesystem World Graph state.**

Buddy still owns exact ExtractionRun, managed-world admission, workspace/source lineage, frozen evidence, operator dispositions, and product response. DungeonMind owns the pristine predicate, source/evidence admission into graph authority, graph materialization, D_0/head, command-hash idempotency, and reviewed-init receipt.

---

## 2. Re-anchor before code

Repository law: `AGENTS.md` at the exact base. Follow its re-anchor, isolated-lane, write-lease, review-cycle, and backward-looking state-sync rules.

At dispatch:

```text
Buddy main = f1eae2a3d27e430ee19e254d5b52fa556b2632ff
#644 design = merged
AS2 #643 = merged
AS3 = dispatched by handoff on main; declared lease is disjoint from this CUTOVER lease
DungeonMind Buddy pin = still c5d3688587b0f5d506e0f7d64f33eb0628bac896
required DungeonMind pin = bf40e933bdedf3cf08bb23a07a135958bdb7cc6b
```

Immediately before implementation, re-check:

1. `main` has not advanced to a conflicting APP-STATE implementation head.
2. no open PR/worktree has acquired `pyproject.toml`, `uv.lock`, or a D.2C2 server path;
3. the exact DungeonMind #46 merge remains the provider target;
4. `AGENTS.md` and the merged #644 handoff have not changed materially.

A new owner of a leased path is a stop/serialization decision, not a merge-conflict exercise.

---

## 3. Frozen design rules — do not redesign in CODE

### 3.1 Separate zero-parent authority

Add a narrow `WorldGraphInitializationAuthority`; do not make existing-parent `WorldGraphAuthority.publish()` accept `None`, `EMPTY`, sentinels, or synthetic parents.

### 3.2 Native eligibility is authority-backed

Both:

```text
exact-run review → first_world_publish_eligible
prepare_first_world(...)
```

must use `WorldGraphInitializationAuthority.probe()` in native mode.

After native `D_0` exists, review must report first-world ineligible even when the Buddy graph directory does not exist.

`classify_world_graph_state`, `world_paths.world_dir`, and `try_open_world_graph_head` may remain only behind explicit `buddy_files` compatibility.

### 3.3 One real genesis revision

Native initialization topology is:

```text
D_0.parent_revision_id = None
head = D_0
baselineRevisionId = null
committedRevisionId = D_0
```

Never persist an empty baseline revision or fabricate a baseline ID.

### 3.4 Exact first-world identity semantics

For the actual Buddy first-world producer:

```text
accepted node identity → IdentityOutcome.CREATED_NEW
accepted edge identity → None
```

Do not rewrite accepted edges to `CREATED_NEW`.

Bind-existing / existing identity semantics are forbidden in pristine first-world publication.

### 3.5 Genesis semantic profile

Pin the provider command to the same builtin worldbuilding descriptor already used by the native DungeonMind graph reader:

```text
load_builtin_v3_descriptor()
```

Construct its exact `SemanticProfileRef` from:

```text
profile_id
profile_revision
descriptor_sha256(descriptor)
```

The profile is adapter-owned and stable. It is not browser input and is not copied from a parent revision.

### 3.6 Stable command-hash inputs

Rebuild the provider command from server-owned sealed facts. Freeze:

```text
initialization_id            = deterministic from world_id + sealed plan identity
contribution.produced_at     = existing _FIXED_PRODUCED_AT = 1970-01-01T00:00:00Z
actor                        = live_control:graph_review_confirm
source artifact/revision time = preserved immutable Buddy source metadata
semantic_profile             = builtin descriptor ref above
```

Do not substitute request wall-clock values for any of these except the first-attempt `requested_initialized_at` described below.

### 3.7 Exact retry / restart / concurrent confirm

Initialization adapter logic:

```text
matching reviewed-init receipt exists
  → requested_initialized_at = receipt.initialized_at
  → rebuild complete command
  → D.2C1 exact replay or real conflict

different initialization_id receipt exists
  → already-initialized/conflict
  → NEVER borrow timestamp

no receipt exists
  → choose one UTC requested_initialized_at
  → call D.2C1
  → if idempotency conflict:
       re-read verified receipt
       if same initialization_id:
          rebuild complete command once with receipt.initialized_at
          call D.2C1 exactly once more
       else:
          preserve conflict
```

This single conflict-recovery retry is required for synchronized identical first confirms that both initially saw no receipt and chose different timestamps.

Any changed plan/source/contribution/actor/profile remains a conflict. Never translate a remaining digest conflict into success.

### 3.8 No Buddy initialization registry

Do not add:

- filesystem reviewed-init registry;
- APP-STATE initialization row;
- process-local HMAC checkpoint;
- browser-authoritative initialization timestamp;
- random initialization ID.

DungeonMind receipt is the durable replay authority.

---

## 4. Write lease

Expected production paths:

```text
pyproject.toml
uv.lock

apps/live_control_server/ports/world_graph_initialization.py
apps/live_control_server/ports/world_graph_initialization_access.py
apps/live_control_server/integrations/dungeonmind/world_graph_initialization_adapter.py
apps/live_control_server/integrations/buddy_files/world_graph_initialization_adapter.py
apps/live_control_server/services/first_world_graph_publication.py
apps/live_control_server/services/first_world_graph.py
apps/live_control_server/services/extract_promote.py
```

Bounded shared-mapper extraction only if genuinely required:

```text
apps/live_control_server/integrations/dungeonmind/world_graph_writes.py
apps/live_control_server/integrations/dungeonmind_kernel/eldyrwild_existing_world_adoption_bundle_v2.py
```

Owning tests may include existing or new CUTOVER/first-world tests. Prefer existing families; do not create parallel duplicate test suites merely to match names in this handoff.

Backward-looking CUTOVER state-sync lease:

```text
Docs/Plans/STEWARDS-ANCHOR-cutover.md
Docs/Plans/PR-TRACKER-campaign-supergraph.md
Docs/Roadmaps/ROADMAP-campaign-supergraph.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/PR-TRACKER-campaign-supergraph.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-campaign-supergraph.md
Docs/Design/STATUS-world-graph-continuity-spine.md   # only if its current claim is stale
Docs/Plans/HANDOFF-CUTOVER-reviewed-first-world-initialization.md
Docs/Plans/HANDOFF-CUTOVER-mounted-first-world-authority-migration.md
this dispatch handoff
```

Explicitly out of lease unless a concrete blocker forces re-brief:

```text
src/application_state/**
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/playSurface/**
apps/live_control_server/services/play_run_*.py
apps/live_control_server/services/workspace_document_registry.py
apps/live_control_server/services/tiptap_markdown_write.py
tests/conftest.py
Docker/compose/application-state DSNs
Threat semantics
existing-world worldbuilding semantics
broad graph_memory deletion / D.3
```

---

## 5. Implementation order

### Step 1 — exact DungeonMind repin

Change only the DungeonMind dependency pin from `c5d368...` to:

```text
bf40e933bdedf3cf08bb23a07a135958bdb7cc6b
```

Refresh `uv.lock`. No floating branch/tag/range.

### Step 2 — add initialization port + authority access

Define product-facing request/state/receipt/error contracts. Keep DungeonMind models, SQL repositories, DSNs, and graph payloads out of the product service layer.

Factory rules must match existing authority selection:

```text
production dungeonmind mode + production root → DungeonMind initialization adapter
explicit buddy_files / non-production root      → buddy_files adapter
```

No silent production fallback from DungeonMind to files.

### Step 3 — implement DungeonMind adapter

Adapter owns:

- probe through DungeonMind head + verified reviewed-init receipt;
- deterministic initialization ID;
- Buddy source → `SourceArtifactV2 + SourceRevision` mapping;
- Buddy contribution → `GraphContributionV2` mapping;
- builtin semantic-profile ref;
- reviewed-init repository/service construction;
- exact retry/lost-response/concurrent-conflict recovery;
- provider error → stable Buddy port error mapping;
- post-initialize receipt verification required by the product response.

Do not pass graph payload bytes into Buddy code. DungeonMind materializes D_0.

### Step 4 — make first-world planning storage-neutral

Remove the native first-world need for:

```text
build_empty_technical_baseline_store(...)
Kernel store queries
Buddy graph head/directory state
```

Pure validation is sufficient for a pristine plan:

- accepted node IDs unique;
- create-new only;
- accepted edge endpoints created by the same plan;
- relationship IDs/mappings valid;
- rejected facts remain review history.

Value models/pure mapping helpers may remain for D.3.

### Step 5 — move review eligibility and prepare

Native exact-run review and prepare both use the initialization port probe.

Prepare stays inert:

```text
0 graph revisions
0 heads
0 reviewed-init receipts
0 Buddy graph dirs
```

### Step 6 — move confirm orchestration

Extract mounted first-world orchestration to:

```text
apps/live_control_server/services/first_world_graph_publication.py
```

Keep `extract_promote.py` thin. Preserve exact-run rematerialization and all current source/workspace/evidence/decision digest checks before publication.

Then call only `WorldGraphInitializationAuthority.initialize(...)` for native graph authority.

Map native receipt honestly:

```text
initialized          → baseline None / committed D_0
exact replay         → already_initialized / same D_0 / baseline None
```

### Step 7 — explicit buddy_files compatibility

Retain legacy first-world filesystem/Kernel behavior only behind explicit compatibility selection. This is D.3 deletion debt, not a production fallback.

### Step 8 — evidence + state sync

Run all required owning-boundary evidence below. Only after executable behavior is proven, carry the backward-looking state sync in the same PR.

---

## 6. Backward-looking state sync

The implementation PR records already-completed predecessor truth:

```text
D.2B / Buddy #640
  merge = 6ef7aefa741a82f512f5918b460cbee1a427cae4
  accepted head = caa9d84e4431db1b90ea58dab2e74d270fbcffee
  review cycles = 3
  final PASS-equivalent = 5020798053

D.2C1 design / Buddy #642
  merge = d80c8688774602972e07593b83e3d8d09d4b0a7b
  accepted head = 0f9e07686dfd157bb35acbd10765bfe3de68166f
  review cycles = 2
  final PASS-equivalent = 5023757627

D.2C1 provider / DungeonMind #46
  merge = bf40e933bdedf3cf08bb23a07a135958bdb7cc6b
  accepted head = bc2800b1d09aa70cf33d92ea6b8fc4a786f4b999
  review cycles = 3
  final PASS-equivalent = 5024825675

D.2C2 design / Buddy #644
  merge = f1eae2a3d27e430ee19e254d5b52fa556b2632ff
  accepted head = ded066cec49c3840c3b19c3e817ffa569a116f39
  review cycles = 2
  final PASS-equivalent = 5025378684
```

For the in-flight implementation:

```text
D.2C2 implementation = ACTIVE / this PR
D.3 = false / blocked until D.2C2 implementation merges
```

Do not invent this PR's future merge SHA, final accepted head, or final review count.

---

## 7. Required acceptance evidence

### 7.1 Pin/import boundary

Prove exact DungeonMind merge in both `pyproject.toml` and `uv.lock`, and prove product services do not import DungeonMind PostgreSQL infrastructure.

### 7.2 Native review + prepare with Buddy graph absent

With Buddy graph storage physically absent:

1. exact-run review reports first-world eligible via initialization probe;
2. prepare succeeds for valid reviewed create-new facts;
3. prepare performs zero DungeonMind mutations;
4. no Buddy graph directory is created;
5. no filesystem/head/Kernel baseline helper is called;
6. after native confirm, exact-run review reports ineligible while the Buddy directory remains absent.

### 7.3 Real PostgreSQL `∅ → D_0`

Against disposable migrated DungeonMind PostgreSQL, prove after one confirm:

```text
1 world head = D_0
1 graph revision
D_0.parent_revision_id = None
1 reviewed-init receipt
1 reviewed contribution
exact required source artifact/revision rows
0 existing_world_adoptions row
0 Buddy World Graph files
```

### 7.4 Semantic mapping witness

Use a real first-world plan with at least:

```text
2 accepted nodes
1 accepted edge
1 rejected candidate
```

Prove:

```text
accepted nodes → CREATED_NEW
accepted edge  → None
rejected fact  → durable rejected review history, absent from D_0
receipt accepted_assertion_ids == materialized accepted set
semantic_profile == builtin descriptor ref
```

### 7.5 Source/evidence closure

Every D_0 evidence ref must resolve through exactly the `SourceArtifactV2` and `SourceRevision` submitted in the command and committed in the same provider transaction.

No invented artifact, extra source row, or current-source lookup.

### 7.6 Product topology

Native API response:

```text
outcome = initialized
baseline_revision_id = None
committed_revision_id = D_0
```

No synthetic revision exists.

### 7.7 Exact retry

Same sealed product plan again:

```text
outcome = already_initialized
same D_0
same durable receipt
same contribution
same command_sha256
1 total graph revision
1 total reviewed-init receipt
```

Exercise receipt-seeded `requested_initialized_at`; do not mock a constant clock as the only proof.

### 7.8 Lost response + restart

Inject failure after provider commit but before Buddy response. Recreate adapter/service instance and retry the same sealed request.

Expected: read receipt → reuse `initialized_at` → rebuild complete command → exact same D_0, no second initialization.

### 7.9 Two synchronized identical confirms

Both callers may initially observe no receipt and choose different timestamps.

Expected:

```text
one D_0
one reviewed-init receipt
one command_sha256
both callers succeed as initialized / already_initialized
```

The losing caller may execute exactly one conflict → receipt reread → rebuild → provider replay.

### 7.10 Changed retry

Change any sealed plan/source/contribution/actor/profile semantic input under the same deterministic initialization identity.

Expected: conflict; never old-receipt success.

### 7.11 Race/non-pristine

Prepare while probe sees no head, then introduce competing authoritative state/residue before confirm. DungeonMind transaction must fail closed. Buddy must not clean, repin, adopt, or create a second world.

### 7.12 Workspace/source drift

Advance or mutate source/workspace authority after prepare. Confirm must fail during Buddy rematerialization/lineage verification before provider publication.

### 7.13 buddy_files regression

Explicit file-mode/non-production selection still initializes through legacy storage until D.3. Do not test this as a silent production fallback.

### 7.14 Existing writer regressions

Re-run focused D.2A Threat and D.2B existing-world worldbuilding publication/recovery tests. First-world changes must not alter those state machines.

### 7.15 Static D.3 readiness gate

Mounted production first-world path has no imports/calls to:

```text
graph_memory.kernel.reviewed_world_initialization
graph_memory.kernel.world_initialization
Buddy world-supergraph head/storage authority
Buddy filesystem reviewed-init receipt authority
```

Remaining references must be explicit `buddy_files`, tests, migration/tooling, or D.3 deletion owners.

---

## 8. Suggested verification commands

Discover exact test filenames at implementation time; do not duplicate suites solely to match this spelling. At minimum run owning equivalents of:

```bash
uv run pytest tests/test_first_world_graph.py -q
uv run pytest tests/test_live_extract_promote_api.py -q
uv run pytest tests/test_cutover_dungeonmind_world_graph_authority.py -q
uv run pytest tests -q -k 'first_world and dungeonmind'

# Real PostgreSQL first-world integration cohort; required tests must not silently skip.
uv run pytest tests -q -m integration -k 'first_world and dungeonmind'

# Existing writer regressions
uv run pytest tests -q -k 'threat and dungeonmind'
uv run pytest tests -q -k 'worldbuilding and dungeonmind'

uv run ruff check .
git diff --check
```

If broad suite cost is reasonable, run the full non-live-LLM suite before handback. Record exact commands, pass/fail/skip counts, and PostgreSQL DSN isolation strategy without leaking credentials.

---

## 9. Stop / re-brief conditions

Stop rather than silently widening scope if:

1. real Buddy first-world facts cannot be expressed by DungeonMind #46 public contracts;
2. exact restart/concurrent replay cannot be reconstructed from verified DungeonMind receipt + server-owned sealed facts;
3. implementation needs a new Buddy initialization registry;
4. implementation needs caller-supplied graph bytes, a fake baseline, `EMPTY`, or ExistingWorldAdoption;
5. correctness requires changing DungeonMind #46 provider contract rather than consuming it;
6. APP-STATE or another active lane acquires a required D.2C2 path and the seam cannot be serialized cleanly;
7. UI/API contract must change beyond native `baselineRevisionId=null` already admitted by v1;
8. broad `graph_memory` demolition is required to make this slice work; that belongs to D.3;
9. D.2A/D.2B semantics must materially change to support first-world.

---

## 10. Nano-commit story

Prefer reviewable commits such as:

```text
1. repin DungeonMind + add initialization port/factory
2. add native + buddy_files initialization adapters and deterministic mapping
3. make first-world planning and review eligibility storage-neutral/native-probed
4. move mounted first-world prepare/confirm orchestration behind initialization authority
5. add real PostgreSQL retry/restart/concurrency/source-closure proofs
6. run D.2A/D.2B regressions + static D.3 readiness checks
7. carry atomic CUTOVER predecessor state sync
```

Do not mix D.3 deletion into the final commit.

---

## 11. Review handback contract

Return:

1. exact PR / branch / final head SHA;
2. exact implementation base and whether rebased during work;
3. cumulative changed-path set against this write lease;
4. nano-commit story;
5. exact DungeonMind pin in `pyproject.toml` and `uv.lock`;
6. initialization port/factory shape and authority-selection rule;
7. exact genesis semantic-profile ref construction;
8. source/contribution mapping explanation, including node vs edge identity;
9. native review/prepare Buddy-files-absent witness;
10. real PostgreSQL `∅ → D_0` witness;
11. exact retry witness;
12. lost-response/restart witness;
13. synchronized concurrent-confirm witness;
14. changed-command and non-pristine failure witnesses;
15. source/evidence closure proof;
16. explicit `buddy_files` compatibility proof;
17. D.2A/D.2B regression results;
18. static mounted-call-path D.3 readiness evidence;
19. ruff / diff-check / broader test results and skip counts;
20. state-authority sync showing #640/#642/#46/#644 completed, D.2C2 active, D.3 false;
21. stop conditions encountered or `none`.

Review begins only when executable implementation is present. This dispatch seed itself is not Review Cycle 1.
