---
pr_body_template: |
  ## Handoff pointer
  - Workstream: CUTOVER / D.2C2 provenance producer repair
  - Flow: CUTOVER
  - Direction: CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-CUTOVER-first-world-provenance-producer.md`
  - Suggested branch: `cutover/first-world-provenance-producer`
  - Suggested PR title: `CUTOVER: correct first-world provenance producer`

  ## Verification pointer
  - Exact base: record the re-anchored Buddy `main` SHA in the PR body
  - DungeonMind target pin: `5ca5d688612349034f8ca490d465af166d883e6e`
  - Accepted provider head: `de966092e81f778be90c827e73b3776620640b8f`
  - DungeonMind #47 review: Cycle 2 PASS-equivalent `5037371759`
  - Parked consumer: Buddy #651; do not resume it in this PR
  - Verification: HANDOFF §7

  The checked-in handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. The PR description is transport metadata.
---

# HANDOFF — CUTOVER: correct first-world provenance producer

**Created:** 2026-08-26  
**Status:** READY FOR DISPATCH after exact-current-main re-anchor  
**Canonical handoff path:** `Docs/Plans/HANDOFF-CUTOVER-first-world-provenance-producer.md`  
**Workstream:** `CUTOVER / D.2C2 first-world provenance compatibility`  
**Flow / owner:** `CUTOVER`  
**Direction:** CODE → REVIEW  
**Suggested branch:** `cutover/first-world-provenance-producer`  
**Suggested PR title:** `CUTOVER: correct first-world provenance producer`  

> **Observed Buddy design/dispatch base:**  
> `d721cba261c35fd1d77566df6c03be614a26f510` — current DungeonMindBuddy
> `main` when this handoff was authored. This commit is the disjoint
> `AGENT-INTERACTION: design advanced Agent trace inspector` design commit.
>
> **Required provider pin / merged authority:**  
> DungeonMind PR #47 merge
> `5ca5d688612349034f8ca490d465af166d883e6e`.
>
> **Accepted DungeonMind implementation head:**  
> `de966092e81f778be90c827e73b3776620640b8f`.
>
> **DungeonMind #47 formal review:**  
> Review Cycle 2 PASS-equivalent `5037371759`.
>
> **Accepted Buddy design predecessor:**  
> PR #653 merge `5ad992090c2e85d38784c888e4b870f5672bce8e`;
> accepted design head `289201c9c60ec75c3acca998722be1a7d0600c43`;
> Review Cycle 4 PASS-equivalent `5036593867`.
>
> **Parked consumer:**  
> Buddy PR #651 `CUTOVER: native genesis read/write continuity`.
> Its formally reviewed Cycle 3 head is
> `cf453078a5c1950ec5f23a5d5b99001ee9e456db`,
> review `5035980646`. The branch currently also contains the unreviewed
> parking/state commit `3a60610dc78b710aa0aea6af817da00b0bfb563e`.
> #651 remains parked until this PR merges.
>
> Re-anchor immediately before branch creation. If Buddy `main` no longer equals
> `d721cba261c35fd1d77566df6c03be614a26f510`, inspect every intervening
> commit and every open PR lease. Disjoint Agent/Play work is a normal re-anchor.
> Any overlap with the production/test/state paths leased below is a STOP and
> re-brief.

---

# 0. Why this slice exists

D.2C2 first-world initialization already publishes a legitimate immutable
DungeonMind genesis revision:

```text
reviewed first-world plan
        ↓
Buddy first-world initialization adapter
        ↓
DungeonMind reviewed-world initialization
        ↓
D_0
parent = None
reviewed-init receipt exists
head = D_0
```

Buddy PR #645 made that path production-native, but its first-world contribution
mapping used an empty parent-evidence view. When the shared contribution mapper
could not resolve a graph evidence record, it used its fallback:

```text
source_domain = SourceDomain.OTHER
```

The mapped `SourceArtifactV2` for the same source is correctly:

```text
source_domain     = WORLDBUILDING
source_domain_key = "worldbuilding"
```

DungeonMind native projection correctly rejects that mismatch.

PR #653 designed a closed historical compatibility rule. DungeonMind #47 now
implements it:

- immutable historical `D_0` bytes stay unchanged;
- only the named #645 first-world producer family receives compatibility;
- compatibility is content-bound and worldbuilding-only;
- ordinary provenance mismatch remains fail-closed;
- corrected retries can match historical receipts through one shared
  current-hash + historical-OTHER-normalized replay identity at application
  preflight, application recovery, PostgreSQL under-lock replay, and in-memory
  under-lock replay.

This Buddy slice consumes that provider capability and stops producing the defect.

---

# 1. Mission and merge-ready invariant

## 1.1 Mission

> **Buddy first-world initialization emits evidence whose `source_domain`
> matches the command-owned worldbuilding `SourceArtifact`, pins the merged
> DungeonMind #47 compatibility provider, and remains exact-replay-compatible
> with historical #645 receipts without rewriting stored graph revisions,
> changing shared adoption semantics, or resuming D.2C3.**

## 1.2 Merge-ready invariant

A merge-ready head must prove all of the following together:

```text
NEW WORLD
Buddy first-world command
  → command SourceArtifact = WORLDBUILDING
  → command EvidenceRef.source_domain = WORLDBUILDING
  → exactly one zero-parent DungeonMind D_0
  → stored D_0 evidence domain/key = worldbuilding/worldbuilding
  → ordinary DungeonMind native projection admits the first-world facts
  → exact retry returns already_initialized
  → receipt command_sha256 and D_0 stay unchanged

HISTORICAL #645 WORLD
historical stored command / D_0 used OTHER
  → immutable D_0 remains OTHER
  → corrected Buddy command uses WORLDBUILDING
  → corrected command preserves the historical exported evidence_ref_id
  → DungeonMind #47 OTHER-normalized replay digest equals the stored
    historical command_sha256
  → Buddy adapter returns already_initialized
  → one receipt, one D_0, no rewrite
  → DungeonMind compatibility projects the historical D_0 facts

PRODUCTION READ CONSTRUCTION
Buddy pinned to DungeonMind #47
  → WorldGraphProjectionService receives
    bundle.reviewed_world_initializations
  → no Buddy compatibility hint
  → no graph-payload rewrite
```

The producer correction and provider pin are one capability. Do not split them:

```text
producer correction without #47 pin
→ historical same-ID retry conflicts

#47 pin without producer correction
→ Buddy keeps manufacturing malformed provenance
```

---

# 2. Authority and predecessor chain

Read these from the checked-out repositories before editing. Current checked-in
repository authority beats this handoff if they conflict.

## 2.1 DungeonMindBuddy authority

Read in order:

1. `AGENTS.md`
2. `Docs/Design/ARCHITECTURE-campaign-supergraph.md`
3. `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`
4. `Docs/Plans/PR-TRACKER-campaign-supergraph.md`
5. `Docs/Design/STATUS-world-graph-continuity-spine.md`
6. `Docs/Plans/STEWARDS-ANCHOR-cutover.md`
7. `Docs/Plans/HANDOFF-CUTOVER-first-world-provenance-compatibility.md`
8. `Docs/Plans/HANDOFF-CUTOVER-native-genesis-read-write-continuity-code.md`
   - read-only in this slice except to understand the parked consumer
9. `apps/live_control_server/integrations/dungeonmind/world_graph_initialization_adapter.py`
10. `apps/live_control_server/integrations/dungeonmind/world_graph_reads.py`
11. `apps/live_control_server/integrations/dungeonmind_kernel/eldyrwild_existing_world_adoption_bundle_v2.py`
12. `tests/test_cutover_dungeonmind_first_world_initialization.py`

## 2.2 Merged DungeonMind provider authority

Pin and inspect exact merge:

```text
DungeonMind PR #47 merge:
5ca5d688612349034f8ca490d465af166d883e6e

accepted head:
de966092e81f778be90c827e73b3776620640b8f

review:
Cycle 2 PASS-equivalent 5037371759

ADR:
ADR-0023-reviewed-first-world-provenance-compatibility.md
```

Relevant provider seams:

- `src/dungeonmind/application/reviewed_world_initialization.py`
- `src/dungeonmind/application/world_graph_projection.py`
- `src/dungeonmind/application/graph_scope.py`

The Buddy implementation must consume #47 as-is. Do not change DungeonMind in
this PR.

## 2.3 Exact historical producer family

The compatibility applies only to the already-frozen family:

```text
source_plan_schema == "dmb_first_world_graph_plan_v1"

initialization_id matches:
^dmb:first-world:[0-9a-f]{64}$

actor == "live_control:graph_review_confirm"
```

Do not broaden this family.

---

# 3. Critical implementation constraint: preserve historical evidence identity

This is the highest-risk detail in the slice.

## 3.1 Current Buddy exported evidence identity

The shared adoption mapper creates contribution evidence IDs as:

```text
<raw_buddy_evidence_ref_id>:dmv1:<sha256(canonical v1 evidence binding)>
```

and its binding digest includes:

```text
schema_version
source_artifact_id
source_revision_id
source_domain
evidence_role
can_open_source
can_highlight_span
locator
uri
```

Therefore `source_domain` affects `evidence_ref_id`.

Historical #645 first-world mapping did this:

```text
draft.source_domain = OTHER
        ↓
exported_contribution_evidence_ref_id(raw_id, draft)
        ↓
historical evidence_ref_id = ID_OTHER
        ↓
command stored with:
  evidence_ref_id = ID_OTHER
  source_domain   = OTHER
```

## 3.2 Why the naive producer fix is wrong

Do **not** merely change the shared fallback to construct the draft with
`WORLDBUILDING` before deriving the exported ID:

```text
draft.source_domain = WORLDBUILDING
        ↓
exported ID = ID_WORLDBUILDING
```

DungeonMind #47 reconstructs the historical command hash by changing only:

```text
EvidenceRef.source_domain
WORLDBUILDING → OTHER
```

It intentionally leaves every other command field unchanged.

If Buddy changes the evidence ID as well:

```text
corrected:
  id = ID_WORLDBUILDING
  domain = WORLDBUILDING

#47 historical normalization:
  id = ID_WORLDBUILDING
  domain = OTHER

actual #645 historical:
  id = ID_OTHER
  domain = OTHER
```

then:

```text
hash(normalized corrected command) != historical receipt.command_sha256
```

and the historical retry contract fails.

## 3.3 Frozen Buddy producer rule

For the named first-world producer only:

1. Use the existing shared mapping path to obtain the same historical exported
   evidence identity that #645 would have produced.
2. Resolve each mapped evidence ref's `source_artifact_id` against the
   **command-owned mapped `SourceArtifactV2` set**.
3. Require that the artifact exists uniquely.
4. Require the artifact domain/key to be the expected first-world worldbuilding
   provenance:
   - `source_domain == SourceDomain.WORLDBUILDING`
   - `source_domain_key == "worldbuilding"`
5. Copy the evidence ref and change **only**
   `EvidenceRef.source_domain` to the artifact's `source_domain`.
6. **Do not recompute or replace `evidence_ref_id`.**
7. Do not invent `source_domain_key` on v1 `EvidenceRef`; the command contract
   does not have that field.
8. Return the corrected command contribution.

Conceptually:

```python
historical_ref = shared_mapping_result.evidence_ref
artifact = artifacts_by_id[historical_ref.source_artifact_id]

corrected_ref = historical_ref.model_copy(
    update={"source_domain": artifact.source_domain}
)

assert corrected_ref.evidence_ref_id == historical_ref.evidence_ref_id
```

This is a **versioned historical identity-preservation rule for this producer
family**, not a new generic exported-evidence identity algorithm.

The purpose of the `:dmv1:` ID remains intact for its original collision problem:
the source artifact/revision and other binding fields remain identity-bearing.
This slice does not change the shared adoption producer or its identity helper.

## 3.4 Required cryptographic owning proof

Before calling the implementation complete, a test must prove:

```text
historical_command = exact #645-shaped command
corrected_command  = new Buddy-produced command

for every corrected first-world evidence ref:
  corrected.source_domain == WORLDBUILDING
  corrected.evidence_ref_id == corresponding_historical.evidence_ref_id

reviewed_world_initialization_command_sha256(corrected)
  != reviewed_world_initialization_command_sha256(historical)

reviewed_world_initialization_replay_identity(corrected)
  .historical_other_normalized_sha256
  == reviewed_world_initialization_command_sha256(historical)
```

This proof is mandatory. Broad integration success is not a substitute.

If this equality cannot be achieved without modifying DungeonMind #47, **STOP
and re-brief**. Do not invent another Buddy-side replay comparison.

---

# 4. Write lease

This lease is exclusive for this slice.

## 4.1 Primary production lease

### A. First-world producer

`apps/live_control_server/integrations/dungeonmind/world_graph_initialization_adapter.py`

Allowed changes:

- add the first-world-only post-mapping provenance correction;
- build/validate a command artifact map;
- preserve the historical exported evidence IDs;
- fail closed on missing/ambiguous/non-worldbuilding command source authority;
- keep `_map_sources`, command semantics, receipt behavior, timestamps, and
  initialization identity otherwise unchanged.

Do not add a generic read-time compatibility shim.

### B. DungeonMind provider pin

`pyproject.toml`

Change only the DungeonMind exact git pin:

```text
bf40e933bdedf3cf08bb23a07a135958bdb7cc6b
→
5ca5d688612349034f8ca490d465af166d883e6e
```

Update the comment to identify PR #47 / reviewed-init provenance compatibility.

`uv.lock`

Regenerate only what is required by the exact DungeonMind pin change. Unrelated
dependency churn is a review blocker unless separately justified.

### C. Required projection constructor consumption

`apps/live_control_server/integrations/dungeonmind/world_graph_reads.py`

This path is currently part of parked #651's historical lease.

**Explicit temporary lease transfer for this PR:**

The producer+pin lane may change only the construction of
`WorldGraphProjectionService` required by DungeonMind #47:

```python
WorldGraphProjectionService(
    world_graph=bundle.world_graph,
    sources=bundle.sources,
    graph_reader=...,
    reviewed_world_initializations=bundle.reviewed_world_initializations,
    ...
)
```

No binder behavior, revision translation, native read semantics, projection
adaptation, retrieval semantics, or #651 acceptance logic may change here.

After this PR merges, #651 rebases and inherits this constructor wiring.

## 4.2 Test lease

Primary:

`tests/test_cutover_dungeonmind_first_world_initialization.py`

Allowed:

- update exact provider pin assertion;
- add producer-domain/identity/replay-hash unit proofs;
- add/extend real-PostgreSQL fresh-world proof;
- add historical #645-world correction replay proof;
- directly use DungeonMind projection to prove producer output is natively
  admissible;
- retain exact retry/lost-response/concurrency/conflict proofs.

Conditional constructor fallout only:

`tests/test_cutover_direct_dungeonmind_world_graph_reads.py`

This path is also part of parked #651's historical lease.

Temporary transfer is allowed **only** for tests/fixtures that must supply
`reviewed_world_initializations` after the provider constructor becomes required.

Do not alter D.2C3 binder/read behavior or acceptance semantics.

Explicitly **not leased**:

`tests/test_cutover_native_genesis_continuity.py`

That remains #651's owning proof and stays parked.

### Shared adoption regression

`tests/test_eldyrwild_existing_world_adoption_bundle_v2.py`

Read first. Prefer **no changes**. If the implementation changes this file or
the shared adoption producer, STOP unless the need is purely a focused regression
fixture that does not change adoption semantics.

## 4.3 Backward-looking CUTOVER state sync

Current `main` is materially stale about already-completed predecessor facts.
Per `AGENTS.md`, this implementation PR carries the backward-looking sync.

These paths are also in parked #651's historical docs lease. Because #651 is
blocked on this predecessor, they are explicitly transferred to this slice for
the bounded state sync:

- `Docs/Plans/PR-TRACKER-campaign-supergraph.md`
- `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`
- `Docs/Design/STATUS-world-graph-continuity-spine.md`
- `Docs/Plans/STEWARDS-ANCHOR-cutover.md`
- `Docs/Sources/design-agent/ACTIVE_AUTHORITY/PR-TRACKER-campaign-supergraph.md`
- `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-campaign-supergraph.md`
- `Docs/Plans/HANDOFF-CUTOVER-first-world-provenance-compatibility.md`

The sync must record only facts already true before this implementation merges:

```text
#653 provenance DESIGN
  DONE
  merge = 5ad992090c2e85d38784c888e4b870f5672bce8e
  accepted head = 289201c9c60ec75c3acca998722be1a7d0600c43
  Review Cycle 4 PASS-equivalent = 5036593867

DungeonMind #47 provenance CODE
  DONE
  merge/main = 5ca5d688612349034f8ca490d465af166d883e6e
  accepted head = de966092e81f778be90c827e73b3776620640b8f
  Review Cycle 2 PASS-equivalent = 5037371759

Buddy producer+pin
  DOING / this PR
  NOT DONE
  no invented merge SHA
  no invented final review count

#651 D.2C3
  DOING / PARKED ON THIS PRODUCER PREDECESSOR
  formal reviewed head = cf453078a5c1950ec5f23a5d5b99001ee9e456db
  Cycle 3 review = 5035980646
  branch parking head may be noted as 3a60610dc78b710aa0aea6af817da00b0bfb563e
  frozen admitted D_0 rubric remains unchanged

D.2C4
  BLOCKED on D.2C3

D.3A
  BLOCKED on D.2C4

D.3B
  BLOCKED on D.3A

D.3
  NOT DONE
```

At this PR head the dependency pin may truthfully say `5ca5d688...` because that
is part of the implementation diff. Do not claim the producer capability itself
is merged/DONE.

The canonical tracker/roadmap and their ACTIVE_AUTHORITY mirrors must be
byte-identical after the sync.

## 4.4 Handoff file

This file itself:

`Docs/Plans/HANDOFF-CUTOVER-first-world-provenance-producer.md`

## 4.5 Explicitly out of scope

Do not edit:

- `apps/live_control_server/integrations/dungeonmind/world_graph_authority_adapter.py`
- `apps/live_control_server/integrations/dungeonmind/world_graph_writes.py`
- `tests/test_cutover_native_genesis_continuity.py`
- `Docs/Plans/HANDOFF-CUTOVER-native-genesis-read-write-continuity-code.md`
- `Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md`

Do not:

- resume/rebase/merge #651;
- implement D.2C4;
- implement D.3A or D.3B;
- rewrite `graph_payload.evidence_refs` on reads;
- add a Buddy compatibility hint to DungeonMind;
- mutate historical `D_0`;
- update historical receipt hashes;
- publish a corrective `D_1` as a compatibility substitute;
- broaden `OTHER` acceptance;
- change the shared Eldyrwild adoption fallback;
- change existing-world adoption semantics;
- add a new DungeonMind contract;
- add a database migration;
- change first-world API/transport schemas;
- add another authority selector/fallback;
- touch Agent/Play/UI work.

---

# 5. Implementation plan

## Step 0 — Re-anchor and collision check

Before editing:

```bash
git fetch origin
git switch main
git pull --ff-only
git rev-parse HEAD
git status --short
```

Record the exact base SHA in the handback and PR body.

Inspect:

- all open Buddy PRs;
- their changed paths / leases;
- current `pyproject.toml` DungeonMind pin;
- current DungeonMind `main`.

At handoff authoring time:

```text
Buddy main = d721cba261c35fd1d77566df6c03be614a26f510
DungeonMind main = 5ca5d688612349034f8ca490d465af166d883e6e
open Buddy implementation PR = #651 only
```

The `d721cba2...` advance from the prior re-anchor is AGENT-INTERACTION design
and disjoint from this lease.

Create:

```bash
git switch -c cutover/first-world-provenance-producer
```

Any new overlap is a STOP.

## Step 1 — Pin DungeonMind #47 and consume its required projection dependency

Update:

```text
pyproject.toml
uv.lock
```

to exact provider merge:

```text
5ca5d688612349034f8ca490d465af166d883e6e
```

Then minimally update `WorldGraphProjectionService(...)` construction in
`world_graph_reads.py` with:

```text
reviewed_world_initializations=bundle.reviewed_world_initializations
```

Run the direct-read constructor cohort immediately. Do not continue with a
workaround that makes the new dependency optional in Buddy.

## Step 2 — Characterize historical vs corrected first-world commands

Before or alongside the producer change, add a focused test helper that can build:

```text
C_old = exact #645-shaped first-world command
C_new = corrected first-world command
```

The helper must preserve:

- same initialization ID;
- same requested initialization timestamp;
- same plan/source/profile/contribution semantics;
- same exported evidence IDs;
- domain-only correction on eligible first-world evidence refs.

Prove the §3.4 cryptographic equality.

Do not call a command “historical” merely because its graph payload says OTHER;
prove the command hash shape that #47 actually matches.

## Step 3 — Correct first-world contribution provenance only

In `world_graph_initialization_adapter.py`:

1. map artifacts/revisions as today;
2. map contribution using the existing shared mapper;
3. build an exact artifact map from the command-owned mapped artifacts;
4. for every first-world mapped assertion evidence ref:
   - locate its command-owned artifact;
   - require worldbuilding domain/key;
   - preserve `evidence_ref_id`;
   - copy only `source_domain=artifact.source_domain`;
5. return the corrected contribution;
6. build the normal `ReviewedWorldInitializationCommandV1`.

Prefer a small, obviously first-world-specific helper such as:

```text
_align_first_world_command_evidence_domains(...)
```

or equivalent.

The helper must not be reused by read paths.

### Required behavior

Fresh command:

```text
artifact.source_domain = WORLDBUILDING
ref.source_domain      = WORLDBUILDING
ref.evidence_ref_id    = historical #645-compatible exported ID
```

Historical normalized command:

```text
#47:
ref.source_domain      = OTHER
ref.evidence_ref_id    = same historical ID

→ exact historical command hash
```

## Step 4 — Prove fresh first-world PostgreSQL behavior

Use the existing real-PostgreSQL fixture in
`tests/test_cutover_dungeonmind_first_world_initialization.py`.

From an empty target:

```text
prepare
→ confirm
→ exactly one reviewed-init receipt
→ exactly one zero-parent D_0
→ zero adoption receipts
```

Assert command/source provenance:

- one mapped `SourceArtifactV2` for the first-world source;
- artifact `source_domain == WORLDBUILDING`;
- artifact `source_domain_key == "worldbuilding"`;
- every applicable contribution `EvidenceRef.source_domain == WORLDBUILDING`;
- exported evidence IDs retain the expected historical identity derivation.

Assert stored graph provenance:

- `D_0` evidence `source_domain == "worldbuilding"`;
- `D_0` evidence `source_domain_key == "worldbuilding"`;
- raw `D_0` contains `obj_session22_vial`;
- raw `D_0` contains `mystery_puddles`;
- rejected fixture node remains absent.

Then directly instantiate/use the **pinned DungeonMind**
`WorldGraphProjectionService` over the same repository bundle and prove the
fresh `D_0` admits:

```text
obj_session22_vial
mystery_puddles
```

This direct provider proof is allowed in this slice because it proves the
producer output is valid. Do **not** claim the full Buddy mounted D.2C3
projection/search/get-object capability.

Exact retry through the normal Buddy confirm path must return:

```text
outcome = already_initialized
same D_0
same receipt
same command_sha256
one revision
one receipt
```

## Step 5 — Prove historical #645 replay through the Buddy adapter

Required real-PostgreSQL witness:

1. Prepare a normal sealed first-world request.
2. Construct the exact historical #645 command:
   - same first-world mapping;
   - same historical exported evidence IDs;
   - evidence domains `OTHER`;
   - exact timestamp that will be retained on retry.
3. Seed DungeonMind through the reviewed-init provider with that historical
   command.
4. Verify durable state:
   - one receipt;
   - one zero-parent `D_0`;
   - raw `D_0` evidence remains `OTHER` / `"other"`;
   - receipt stores the historical command hash.
5. Call the normal Buddy
   `DungeonMindWorldGraphInitializationAdapter.initialize(request)`.
6. Buddy observes the receipt and reuses `existing.initialized_at`.
7. Buddy builds the corrected command.
8. DungeonMind #47 replay identity must recognize it.

Assert:

```text
Buddy outcome = already_initialized
published_revision_id unchanged
receipt command_sha256 unchanged
one graph revision
one reviewed-init receipt
zero adoption receipts
```

Also assert explicitly:

```text
reviewed_world_initialization_replay_identity(corrected)
  .historical_other_normalized_sha256
==
stored_receipt.command_sha256
```

Finally, directly prove pinned DungeonMind native projection admits the
historical `D_0` facts while raw revision bytes still say `OTHER`.

This is the cross-repository compatibility witness that closes the detour.

## Step 6 — Regression the old producer safety behavior

Keep existing first-world guarantees green:

- lost-response retry;
- synchronized same-request confirms;
- changed command still conflicts;
- receipt-without-head remains integrity;
- non-pristine target without receipt remains fail-closed;
- workspace/source-plan drift remains fail-closed;
- no Buddy graph directory is created on the native path;
- product services still do not import DungeonMind PostgreSQL infrastructure.

## Step 7 — Regression shared adoption semantics

The shared mapper remains a dependency but not an edit target.

Run:

```bash
uv run pytest tests/test_eldyrwild_existing_world_adoption_bundle_v2.py -q
```

The sealed adoption output/identity behavior must remain unchanged.

If the implementation needs to change
`eldyrwild_existing_world_adoption_bundle_v2.py` to accomplish the first-world
producer fix, STOP and re-brief rather than silently altering adoption authority.

## Step 8 — Backward-looking state sync

Update the §4.3 authority set together.

Required current sequence after the sync:

```text
#653 provenance DESIGN                         DONE
DungeonMind #47 provenance compatibility CODE DONE
Buddy first-world provenance producer+pin     DOING / this PR
#651 D.2C3                                    DOING / PARKED ON this PR
D.2C4                                         BLOCKED
D.3A                                          BLOCKED
D.3B                                          BLOCKED
D.3                                           NOT DONE
```

The current repository anchor becomes the exact base/head appropriate to each
document; do not rewrite historical design/dispatch SHAs as newer merge SHAs.

Check mirrors:

```bash
cmp Docs/Plans/PR-TRACKER-campaign-supergraph.md \
    Docs/Sources/design-agent/ACTIVE_AUTHORITY/PR-TRACKER-campaign-supergraph.md

cmp Docs/Roadmaps/ROADMAP-campaign-supergraph.md \
    Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-campaign-supergraph.md
```

## Step 9 — Full handback

Open a draft PR and return the §9 handback. Do not merge.

---

# 6. Invariants and failure semantics

## 6.1 Source authority, not Buddy string guessing

The corrected evidence domain comes from the mapped command-owned
`SourceArtifactV2`.

Do not:

```text
Buddy raw string "worldbuilding"
→ blindly set enum
```

Do:

```text
mapped SourceArtifactV2
→ exact artifact identity
→ exact source_domain/source_domain_key
→ first-world eligibility check
→ copy artifact.source_domain onto v1 EvidenceRef
```

If source closure is missing, duplicated, or disagrees with the expected
worldbuilding first-world path, fail `inexpressible`/integrity through the
existing port semantics. Do not guess.

## 6.2 Evidence ID is deliberately stable across this correction

For this producer family:

```text
historical ID = corrected ID
historical domain = OTHER
corrected domain = WORLDBUILDING
```

That is deliberate historical replay compatibility.

Do not alter the general `exported_contribution_evidence_ref_id` contract and do
not claim the shared adoption producer now ignores domain.

## 6.3 No read-side normalization

Forbidden:

```text
stored D_0
→ Buddy changes graph evidence in memory
→ DungeonMind projection
```

Required:

```text
stored D_0
→ exact DungeonMind projection
→ #47 provider-owned compatibility when historical
```

Fresh worlds should require no compatibility at all because they are born with
matching provenance.

## 6.4 Existing-world adoption remains unchanged

Eldyrwild adoption has no reviewed-init receipt and receives no genesis
compatibility.

This PR must not alter:

- adoption bundle bytes;
- existing-world receipt semantics;
- Buddy-A → D_A revision bridge;
- contribution evidence collision repair;
- source mapping;
- D.2A/D.2B governed write semantics.

## 6.5 D.2C3 remains false

This PR proves producer validity and provider compatibility.

It does **not** prove the full #651 merge contract:

```text
Buddy shared DirectAuthorityBinding
fresh D_0 mounted projection
Buddy search
Buddy exact-object retrieval
WorldGraphAuthority mutation context
D_0 → D_1 governed child
D_1 mounted native read
Eldyrwild binder regression
```

Those remain #651.

---

# 7. Acceptance gates

## 7.1 Exact pin gate

Repository files must reference exactly:

```text
5ca5d688612349034f8ca490d465af166d883e6e
```

for the DungeonMind dependency.

The old runtime pin:

```text
bf40e933bdedf3cf08bb23a07a135958bdb7cc6b
```

must not remain as the active `pyproject.toml` / `uv.lock` dependency.
Historical documentation may still mention it as history.

No unrelated package upgrade/churn.

## 7.2 Focused first-world cohort

Required:

```bash
uv run pytest tests/test_cutover_dungeonmind_first_world_initialization.py -q
```

Expected:

```text
PASS
required PostgreSQL witnesses EXECUTED
zero required skips
```

This cohort must include the fresh-world and historical-world witnesses in §5.

## 7.3 Direct read constructor regression

Because the provider constructor changed:

```bash
uv run pytest tests/test_cutover_direct_dungeonmind_world_graph_reads.py -q
```

Changes to this test file, if needed, are fixture/constructor consumption only.

## 7.4 Shared adoption regression

```bash
uv run pytest tests/test_eldyrwild_existing_world_adoption_bundle_v2.py -q
```

Expected: PASS, no semantic output drift.

## 7.5 D.2A / D.2B regression

Run the focused existing Threat and worldbuilding DungeonMind governed-write
cohorts discovered from current repository test inventory.

Record exact commands and outcomes in the handback.

Expected:

```text
PASS
no provider-pin regression
```

Do not expand their production scope.

## 7.6 Static gates

At minimum:

```bash
uv run ruff check \
  apps/live_control_server/integrations/dungeonmind/world_graph_initialization_adapter.py \
  apps/live_control_server/integrations/dungeonmind/world_graph_reads.py \
  tests/test_cutover_dungeonmind_first_world_initialization.py \
  tests/test_cutover_direct_dungeonmind_world_graph_reads.py

git diff --check
```

Run the repository's current applicable type/static/full test gates if present
and record them exactly.

## 7.7 Required proof ledger

### New-world producer

- [ ] exact DungeonMind pin is `5ca5d688...`;
- [ ] `WorldGraphProjectionService` receives `bundle.reviewed_world_initializations`;
- [ ] fresh command SourceArtifact is worldbuilding/worldbuilding;
- [ ] fresh command EvidenceRef domain is WORLDBUILDING;
- [ ] corrected evidence ID equals historical #645 evidence ID;
- [ ] corrected command hash differs from historical command hash;
- [ ] #47 historical normalized digest equals historical command hash;
- [ ] exactly one D0, parent None;
- [ ] exactly one reviewed-init receipt;
- [ ] zero adoption receipt;
- [ ] fresh stored D0 evidence domain/key is worldbuilding/worldbuilding;
- [ ] fresh provider projection admits `obj_session22_vial`;
- [ ] fresh provider projection admits `mystery_puddles`;
- [ ] exact Buddy retry returns already_initialized;
- [ ] exact retry preserves command_sha256/D0/receipt count.

### Historical #645 compatibility

- [ ] historical command is actually OTHER-shaped and uses historical evidence IDs;
- [ ] historical receipt stores exact historical command hash;
- [ ] historical raw D0 still stores OTHER/other;
- [ ] corrected Buddy command uses WORLDBUILDING;
- [ ] corrected Buddy command preserves historical evidence IDs;
- [ ] corrected replay identity's historical digest equals stored receipt hash;
- [ ] Buddy adapter returns already_initialized;
- [ ] one receipt / one D0 / zero adoption after retry;
- [ ] stored command_sha256 unchanged;
- [ ] raw historical D0 unchanged;
- [ ] pinned DungeonMind projection admits historical first-world facts.

### Fail-closed/regression

- [ ] changed command still conflicts;
- [ ] missing/ambiguous source artifact cannot be domain-corrected by guessing;
- [ ] non-worldbuilding first-world fallback cannot silently receive compatibility treatment;
- [ ] receipt-without-head remains integrity failure;
- [ ] non-pristine target without receipt remains fail-closed;
- [ ] lost-response/recovery remains stable;
- [ ] synchronized confirms remain stable;
- [ ] no Buddy graph directory created on native first-world path;
- [ ] Eldyrwild adoption bundle regression unchanged;
- [ ] D.2A/D.2B regressions green;
- [ ] no read-side graph rewrite exists.

### State authority

- [ ] #653 recorded DONE with exact merge/review;
- [ ] DungeonMind #47 recorded DONE with exact merge/review;
- [ ] this producer slice recorded DOING, not DONE;
- [ ] #651 remains DOING/PARKED;
- [ ] D.2C4/D.3A/D.3B remain false/blocked;
- [ ] no current-PR merge SHA invented;
- [ ] tracker mirror byte-identical;
- [ ] roadmap mirror byte-identical.

---

# 8. Stop conditions

STOP and report rather than expanding the PR if any of these occur:

1. Current Buddy `main` moved through any leased production/test/state path.
2. Another active PR/worktree owns a required path and no explicit transfer is
   available.
3. DungeonMind `main` no longer has #47 merge
   `5ca5d688612349034f8ca490d465af166d883e6e` as the provider authority
   expected by this handoff, or a later provider change materially alters replay.
4. The corrected first-world command cannot preserve the historical
   `evidence_ref_id` while changing only `source_domain`.
5. `reviewed_world_initialization_replay_identity(corrected)
   .historical_other_normalized_sha256` does not equal the actual historical
   #645 command hash.
6. Fixing #5 would require modifying DungeonMind #47.
7. The producer fix requires a Buddy read-side graph-payload rewrite.
8. The producer fix requires changing the shared Eldyrwild adoption fallback or
   exported evidence identity algorithm.
9. Existing-world adoption bytes/semantics change.
10. More than the exact constructor dependency in `world_graph_reads.py` needs
    to change.
11. `world_graph_authority_adapter.py` or `world_graph_writes.py` becomes
    necessary.
12. `tests/test_cutover_native_genesis_continuity.py` becomes necessary.
13. A new public API/transport contract is required.
14. A database migration is required.
15. The pin update forces unrelated dependency upgrades that cannot be cleanly
    separated.
16. Any required real-PostgreSQL witness skips or cannot run.
17. The implementation would need to weaken ordinary provenance mismatch
    rejection.
18. The implementation would need to change `D_0`, receipt
    `command_sha256`, or published revision identity.
19. State-authority sync cannot be made coherent without claiming this in-flight
    PR is already DONE.
20. Current checked-in authority contradicts the accepted #653 / DungeonMind
    #47 design.

A STOP is a successful handback. Do not solve a new architecture problem inside
this PR.

---

# 9. Handback contract

Return all of the following.

## 9.1 Repository identity

```text
repo: Drakosfire/DungeonMindBuddy
branch: cutover/first-world-provenance-producer
base SHA:
head SHA:
PR number:
PR state:
DungeonMind pin:
```

Do not invent a merge SHA. Do not merge unless explicitly instructed.

## 9.2 Cumulative diff inventory

List every changed path classified as:

```text
PRODUCTION
DEPENDENCY
TEST
STATE AUTHORITY
HANDOFF
TEMPORARY #651 LEASE TRANSFER
```

Any path outside §4 requires a one-line justification and should normally have
triggered a STOP first.

## 9.3 Nano-commit story

Prefer a reviewable sequence similar to:

```text
1. CUTOVER: pin DungeonMind provenance compatibility provider
2. CUTOVER: correct first-world evidence domain without changing historical identity
3. CUTOVER: prove fresh and historical first-world provenance in postgres
4. CUTOVER: sync completed provenance predecessors and park D.2C3
```

Equivalent smaller commits are fine.

Avoid one opaque everything-at-once commit.

## 9.4 Decisions ledger

Record any implementation choice not mechanically dictated by this handoff:

```text
question:
evidence:
decision:
rejected alternatives:
consequences:
reversal path:
```

In particular, explicitly record how the implementation preserves historical
evidence identity while correcting command provenance.

## 9.5 Verification ledger

Record exact commands and exact results for:

- first-world focused cohort;
- direct-read constructor cohort;
- Eldyrwild adoption regression;
- D.2A/D.2B regressions;
- static/lint gates;
- any broader/full suite run;
- canonical/mirror `cmp`;
- required PostgreSQL witness.

Required skips are blockers.

## 9.6 What remains false

The handback must state exactly:

```text
Buddy #651 is NOT resumed by this PR.
D.2C3 is NOT DONE.
D.2C4 is NOT dispatched.
D.3A is NOT dispatched.
D.3B is NOT dispatched.
D.3 is NOT DONE.
No historical D_0 was rewritten.
No historical receipt command_sha256 was rewritten.
No Buddy read-side provenance normalization was added.
No generic OTHER provenance waiver was added.
Eldyrwild adoption semantics were not changed.
```

## 9.7 Named successor

Only after this PR merges and its exact merge SHA is known:

```text
RE-ANCHOR Buddy #651
branch:
  cutover/native-genesis-read-write-continuity

required action:
  rebase/re-anchor onto then-current Buddy main
  inherit DungeonMind pin 5ca5d688...
  inherit reviewed-init projection constructor wiring
  restore the admitted fresh-D0 native witness
  preserve two-genesis binder semantics
  restore Buddy mounted:
    projection
    search
    exact-object retrieval
    WorldGraphAuthority mutation context
    D0 → one legal D1
    D1 native read
    retry/recovery
    Eldyrwild adoption regression

formal review:
  next distinct resumed head = Review Cycle 4
```

Do not dispatch D.2C4 until #651 merges.

---

# 10. Reviewer checklist

The reviewer should reject the PR if it merely makes tests green by changing
identity/replay semantics.

Review in this order:

1. exact base/head and current main;
2. changed-path lease;
3. exact DungeonMind pin;
4. cumulative diff, not last commit;
5. first-world producer command construction;
6. evidence ID/domain relationship;
7. cryptographic historical replay proof;
8. real PostgreSQL fresh-world witness;
9. real PostgreSQL historical-world witness;
10. direct provider projection on fresh and historical D0;
11. shared adoption regression;
12. constructor-only change in `world_graph_reads.py`;
13. state-authority sync and mirror equality;
14. what-remains-false ledger.

### Immediate REQUEST-CHANGES conditions

- evidence ID is recomputed from the corrected worldbuilding domain;
- historical retry is only mocked rather than run against real PostgreSQL;
- old receipt hash is rewritten;
- historical D0 is mutated or replaced;
- Buddy rewrites graph evidence before projection;
- shared adoption fallback changes;
- full #651 read/retrieval work appears in this PR;
- provider constructor is made optional to avoid wiring the receipt repository;
- state docs mark this PR or D.2C3 DONE before merge;
- required PostgreSQL proof skips.

---

# 11. Intended sequence after this slice

```text
#653 provenance compatibility DESIGN            DONE
        ↓
DungeonMind #47 compatibility CODE              DONE
        ↓
THIS PR
Buddy correct producer + pin #47                READY → DOING → REVIEW
        ↓
merge
        ↓
#651 re-anchor / D.2C3 Review Cycle 4
native genesis projection + retrieval + D1       PARKED → RESUME
        ↓
merge
        ↓
D.2C4 manual Graph Review authoring continuity
        ↓
D.3A mounted legacy graph-engine excision
        ↓
D.3B physical legacy package deletion
        ↓
FULL DEMOLITION
```
