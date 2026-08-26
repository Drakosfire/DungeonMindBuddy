---
pr_body_template: |
  ## Handoff pointer
  - Workstream: CUTOVER / D.2C2 — mounted first-world authority migration
  - Flow: CUTOVER
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-CUTOVER-mounted-first-world-authority-migration.md`
  - Implementation repository: `Drakosfire/DungeonMindBuddy`
  - Provider prerequisite: DungeonMind PR #46, merged `bf40e933bdedf3cf08bb23a07a135958bdb7cc6b`

  ## Outcome
  Move the mounted Buddy first-world prepare → confirm workflow off Buddy's
  filesystem World Graph runtime and onto DungeonMind's reviewed first-world
  initialization authority. In `dungeonmind` authority mode, eligibility,
  initialization, exact retry/recovery, and D_0 verification must not open,
  hydrate, mutate, replay, rebuild, or verify against Buddy World Graph files.

  ## Locked rules
  - one real DungeonMind genesis revision: `D_0.parent_revision_id is None`
  - no fake/EMPTY parent and no persisted empty baseline revision
  - keep zero-parent initialization separate from existing-parent `WorldGraphAuthority.publish()`
  - native product receipt reports `baselineRevisionId = null`; never fabricate one
  - exact retry rebuilds the complete DungeonMind command and lets D.2C1 compare `command_sha256`
  - no hidden Buddy receipt/initialization registry
  - D.2B Threat/worldbuilding publication semantics must not change
  - D.3 remains false until this slice is accepted

  ## Required proof
  - exact DungeonMind repin to #46 merge
  - native prepare succeeds with Buddy graph storage physically absent and performs zero graph mutation
  - native confirm creates one real `D_0`, one head, one reviewed-init receipt, and no Buddy graph files
  - accepted first-world node identity maps to `created_new`; accepted edge maps to DungeonMind-neutral `None`
  - source/evidence closure persists through exact `SourceArtifactV2 + SourceRevision`
 - exact-run review eligibility uses the initialization probe, not Buddy graph-directory absence
 - genesis `semantic_profile` is the builtin worldbuilding descriptor already used by the native reader
 - exact retry returns the same D_0 with zero second initialization
 - lost-response/retry returns the same durable receipt/D_0
 - two synchronized identical confirms yield one D_0 / one receipt and success for both callers
 - changed sealed plan/source/contribution fails closed; no hidden re-prepare/repin
 - native response uses `baselineRevisionId = null`, `committedRevisionId = D_0`
 - explicit `buddy_files` mode remains supported until D.3
 - D.2A Threat + D.2B existing-world worldbuilding regression cohorts stay green
 - mounted native first-world call graph contains no Buddy filesystem World Graph runtime imports
---

# HANDOFF — CUTOVER D.2C2: mounted first-world authority migration

**Created:** 2026-08-25  
**Status:** CYCLE 1 REPAIR — awaiting Review Cycle 2  
**Workstream / flow:** `CUTOVER`  
**Direction:** DESIGN → CODE → REVIEW  
**Implementation repository:** `Drakosfire/DungeonMindBuddy`  
**Buddy design base:** `d80c8688774602972e07593b83e3d8d09d4b0a7b` — merge of Buddy PR #642  
**Current Buddy `main` (re-anchor before CODE):** `2de68441dd2b0adaf934526236d2c8983f9a7e9e` — AS2 #643 merged; AS3 dispatched, lease disjoint from D.2C2 CUTOVER paths  
**Cycle 1 reviews (same head `a9e1d713`; not Cycle 2):** REQUEST-CHANGES-equivalent `5025040987`; addendum `5025096047`  
**DungeonMind provider pin to consume:** `bf40e933bdedf3cf08bb23a07a135958bdb7cc6b` — merge of DungeonMind PR #46  
**DungeonMind accepted provider head:** `bc2800b1d09aa70cf33d92ea6b8fc4a786f4b999`  
**DungeonMind provider review:** Cycle 3 PASS-equivalent `5024825675`  
**Buddy D.2C1 design merge:** PR #642 merge `d80c8688774602972e07593b83e3d8d09d4b0a7b`; accepted design head `0f9e07686dfd157bb35acbd10765bfe3de68166f`; Cycle 2 PASS-equivalent `5023757627`  
**Buddy D.2B merge:** PR #640 merge `6ef7aefa741a82f512f5918b460cbee1a427cae4`; accepted head `caa9d84e4431db1b90ea58dab2e74d270fbcffee`; 3 review cycles  
**Suggested implementation branch:** `cutover/mounted-first-world-authority-migration`  
**Suggested implementation PR:** `CUTOVER: move first-world initialization behind DungeonMind authority`  
**Successor:** D.3 Buddy graph-engine demolition

> **Dispatch ruling:** D.2C1 is complete. DungeonMind now owns a real reviewed
> zero-parent initialization transaction. D.2C2 consumes that provider from the
> mounted Buddy product path. This is the last mounted product World Graph writer
> migration before D.3 demolition.

---

## 1. Mission and merge-ready invariant

Move the current first-world path:

```text
Buddy exact-run review
  → Buddy first-world plan
  → Buddy Kernel empty technical baseline
  → Buddy filesystem graph-state classification
  → Buddy Kernel reviewed-world initialization
  → Buddy baseline revision → Buddy initial head
```

onto:

```text
Buddy exact-run review + product/source admission
  → storage-neutral first-world plan
  → WorldGraphInitializationAuthority
  → DungeonMind ReviewedWorldInitializationCommandV1
  → DungeonMind atomic reviewed initialization
  → D_0.parent_revision_id = None
```

The merge-ready invariant is:

> **When `DUNGEONMIND_WORLD_GRAPH_AUTHORITY=dungeonmind`, mounted first-world
> eligibility, prepare, and confirm obtain World Graph initialization state and
> durable graph authority only through the reviewed-initialization authority
> boundary; confirm publishes or exactly replays one DungeonMind `D_0` without
> opening, creating, hydrating, mutating, replaying, rebuilding, or verifying
> against Buddy's filesystem World Graph.**

Buddy still owns the exact-run, source document, workspace lineage, reviewed
operator decisions, and product response. DungeonMind owns whether the target is
actually pristine, the first graph materialization, source/evidence admission
inside graph authority, D_0/head, idempotency, and the durable initialization
receipt.

---

## 2. Re-anchor truth

### 2.1 DungeonMind provider prerequisite is merged

DungeonMind `main` is:

```text
bf40e933bdedf3cf08bb23a07a135958bdb7cc6b
```

That merge contains the accepted PR #46 head:

```text
bc2800b1d09aa70cf33d92ea6b8fc4a786f4b999
```

D.2C1 now provides:

```python
initialize_reviewed_world(
    command: ReviewedWorldInitializationCommandV1,
    *,
    initialization_repository: ReviewedWorldInitializationRepository,
    graph_reader: GraphSnapshotReader,
) -> ReviewedWorldInitializationReceiptV1
```

and PostgreSQL `PostgresReviewedWorldInitializationRepository`.

Provider invariants already proved there and **not to be reimplemented in
Buddy**:

- real genesis revision with `parent_revision_id=None`;
- graph bytes materialized inside DungeonMind from reviewed facts;
- exact `SourceArtifactV2 + SourceRevision` closure;
- atomic source + contribution + graph revision/head + receipt commit;
- receipt-first exact retry and lost-response recovery;
- same initialization id + changed command digest is conflict;
- different initialization id on an initialized world is conflict;
- reciprocal exclusion with existing-world adoption;
- historical initialization receipt remains valid after later descendants.

### 2.2 Buddy is still pinned to the pre-provider DungeonMind revision

`pyproject.toml` currently pins:

```text
c5d3688587b0f5d506e0f7d64f33eb0628bac896
```

D.2C2 owns the exact repin to `bf40e933...` and corresponding `uv.lock` refresh.
Do not widen DungeonMind versions or move to a floating branch/tag.

### 2.3 Mounted first-world authority is still legacy Buddy runtime

Current production first-world code still does all of the following:

- `first_world_graph.classify_world_graph_state(...)` opens Buddy world dirs,
  heads, and revisions;
- `materialize_first_world_plan(...)` constructs a Kernel empty technical
  baseline solely to perform create-new checks;
- `extract_promote.confirm_first_world(...)` builds the legacy Kernel
  `ReviewedWorldInitializationPlan`;
- confirm calls `graph_memory.kernel.reviewed_world_initialization.initialize_reviewed_world(...)`;
- the product receipt can name a persisted Buddy `baseline_revision_id`.

This is exactly the D.2C2 deletion/migration surface.

---

## 3. Locked design decisions

### 3.1 Zero-parent initialization gets a separate authority port

Do **not** overload existing-parent publication:

```python
WorldGraphAuthority.publish(
    WorldGraphPublishRequest(expected_parent_revision_id=...)
)
```

with `None`, `"EMPTY"`, a sentinel, or an optional expected parent.

Existing-parent publication and zero-parent initialization are different state
machines. Add a narrow sibling port, preferred naming:

```text
apps/live_control_server/ports/world_graph_initialization.py
apps/live_control_server/ports/world_graph_initialization_access.py
```

Conceptual interface:

```python
class WorldGraphInitializationAuthority(Protocol):
    def probe(self, world_id: str) -> WorldGraphInitializationState: ...
    def initialize(
        self,
        request: WorldGraphInitializationRequest,
    ) -> WorldGraphInitializationReceipt: ...
```

The product-facing request contains Buddy/product values, not PostgreSQL
repositories or DungeonMind infrastructure objects.

Preferred request facts:

```text
world_id
campaign_id
initialization_id
source_plan_schema
source_plan_id
source_plan_sha256
actor
source_artifact              # server-resolved Buddy source value
source_revision_token        # exact Buddy/source token from the run
source_uri                   # exact sealed source URI
reviewed_contribution        # rebuilt Buddy contribution value
```

Preferred receipt facts:

```text
world_id
initialization_id
published_revision_id
reviewed_contribution_id
reviewed_contribution_sha256
accepted_assertion_ids
outcome = initialized | already_initialized
```

The port does not expose a SQL connection, repository bundle, DungeonMind model,
or graph payload.

`semantic_profile` is **not** a product-request field. The native adapter pins it
per §3.6b. Do not copy it from a parent revision; first-world has none.

### 3.2 State probe is advisory; DungeonMind's transaction remains pristine authority

Native exact-run review eligibility and native prepare must answer whether
first-world publication is plausibly available **without** reading Buddy graph
files. After native genesis there is deliberately no Buddy graph directory;
filesystem-absent is therefore not a proxy for uninitialized.

`resolve_first_world_capability` and prepare admission both call
`WorldGraphInitializationAuthority.probe()`. Confine
`classify_world_graph_state`, `world_paths.world_dir`, and
`try_open_world_graph_head` to the named `buddy_files` adapter.

The DungeonMind adapter may probe:

- current DungeonMind head;
- the durable reviewed-initialization receipt.

A coherent head means `initialized`. A verified reviewed-init receipt is also
`initialized`. Contradictory receipt/revision state is an integrity failure.
After a successful native confirm, exact-run review must report
`first_world_publish_eligible=false` even when the Buddy World Graph directory
is physically absent.

**No head is not permission to duplicate D.2C1's entire pristine SQL predicate.**
There may be unexpected source/contribution residue that the lightweight probe
does not see. Prepare may report an uninitialized candidate; confirm's D.2C1
transaction is the final authority and must fail `non_pristine_target` if any
forbidden durable residue exists.

This is deliberate TOCTOU-safe layering:

```text
prepare probe says "candidate is uninitialized"
        ↓
confirm rebuilds exact command
        ↓
DungeonMind locks W and proves pristine atomically
```

### 3.3 Keep Buddy source/workspace admission in Buddy

These remain product/application authority and should not be pushed into
DungeonMind:

- managed-world container admission;
- `SourceArtifact ↔ workspace document` identity/revision checks;
- exact committed Markdown digest checks;
- exact ExtractionRun and candidate/evidence admission;
- operator first-world dispositions.

`cross_check_workspace_lineage(...)` remains useful. What leaves the mounted
native path is **filesystem World Graph state**, not Buddy's source/document
model.

### 3.4 Remove Kernel runtime from first-world planning, but do not over-delete value models

Current `materialize_first_world_plan(...)` creates
`build_empty_technical_baseline_store(...)` only so create-new ID checks have an
empty store to query.

For a first world there is no existing object authority to inspect. Replace
that runtime dependency with pure plan validation:

- accepted nodes must be unique create-new candidate IDs;
- bind-existing is forbidden;
- accepted edge endpoints must be nodes created by the same initial plan;
- duplicate relationship IDs / invalid mappings fail closed;
- rejected facts remain review history.

It is acceptable for D.2C2 to keep existing Buddy candidate/contribution **value
models and pure mapping functions**. D.3 owns broad graph-engine deletion. The
D.2C2 mounted call path must not depend on Kernel/world-supergraph storage or an
in-memory Kernel store to establish authority.

### 3.5 Reuse the established Buddy → DungeonMind semantic mapping

Do not invent a second contribution dialect for first-world.

Use the same bounded mapping conventions already exercised by D.1/D.2A/D.2B
and the adoption producer:

- deterministic Buddy source `(artifact_id, revision token)` → DungeonMind
  `SourceRevision` identity;
- Buddy worldbuilding accepted node `created_new` →
  `IdentityOutcome.CREATED_NEW`;
- Buddy accepted edge `accepted_by_operator` → DungeonMind-neutral
  `identity_resolution_outcome=None`;
- rejected review facts stay rejected history;
- mechanics/statblock bindings remain outside World Graph first-world facts.

The accepted PR #46 provider was explicitly repaired to accept neutral first-world
edges. **Do not rewrite an edge to `CREATED_NEW` just to satisfy a model.**

If a reusable source/contribution mapper currently lives as a private helper in
the adoption producer or `world_graph_writes.py`, extract only the bounded pure
helper needed here. Do not invoke adoption semantics, build an adoption bundle,
or refactor the whole migration stack.

### 3.6 DungeonMind command source closure must be deterministic

Native adapter constructs exactly one `SourceArtifactV2` and the required
`SourceRevision` from server-resolved source authority.

Rules:

- use the committed Buddy SourceArtifact record and exact workspace lineage;
- preserve stable source timestamps/metadata already on that record; do not
  substitute `now()` into source records;
- derive the DungeonMind source revision ID with the same deterministic mapping
  already used by existing publication/adoption paths;
- set the artifact's `current_revision_id` to that exact DungeonMind revision;
- source revision belongs to that artifact and binds the committed content
  digest/locator;
- source/evidence refs on the mapped contribution must close through exactly
 those command records.

D.2C1 rejects invented/unreferenced rows. Buddy must not work around that guard.

### 3.6b Genesis semantic_profile is the builtin worldbuilding descriptor

D.2C1 requires `semantic_profile` on the initialization command and hashes it
into `command_sha256`. Existing-parent publication copies that ref from the
parent revision payload. First-world has no parent.

The native adapter pins genesis to the **same builtin worldbuilding descriptor**
already used by the native DungeonMind reader:

```text
apps/live_control_server/integrations/dungeonmind/world_graph_writes.py
  _build_graph_reader() → StaticSemanticProfileRegistry([load_builtin_v3_descriptor()])
```

Rules:

- adapter-owned; not a browser/product-request field;
- stable across first attempt, exact retry, lost-response, and concurrent confirm;
- do not look up "current head" profile, invent a second descriptor, or substitute
  `now()` metadata into the profile ref.

If that predecessor helper is extracted, keep the pin identical. Changing the
descriptor is a command-hash change and is therefore a conflict, not a silent
upgrade.

### 3.7 Stable initialization id is deterministic; no Buddy receipt registry

Derive a bounded stable initialization id from sealed product identity, for
example:

```text
initialization_id =
  "dmb:first-world:" + sha256(canonical({world_id, plan_id})).hexdigest()
```

Equivalent deterministic naming is acceptable if tests freeze it.

Do not generate a random id on confirm and do not add a Buddy filesystem/APP-STATE
initialization registry. Exact retry of the same plan must derive the same id.
A distinct plan for an already initialized world remains a provider conflict.

### 3.8 Retry timestamp comes from durable DungeonMind receipt when one exists

This is a critical D.2C2 rule.

D.2C1's `command_sha256` binds **every semantic command field**, including
`requested_initialized_at`. Therefore confirm must not blindly call
`datetime.now()` on every retry and expect provider replay to succeed.

Do **not** add a browser-authoritative timestamp, a new plan schema, a Buddy
initialization registry, or weaken D.2C1's digest. Do not use source-artifact
time as a fake initialization-request time.

Frozen non-timestamp command-hash inputs (reconstruct from sealed server-owned
facts, never from wall clock or the HTTP caller):

```text
contribution.produced_at     = existing _FIXED_PRODUCED_AT ("1970-01-01T00:00:00Z")
actor                        = live_control:graph_review_confirm
source artifact/revision times = immutable Buddy SourceArtifact record
semantic_profile             = §3.6b builtin worldbuilding descriptor
```

A verified receipt for **W** whose `initialization_id` is **not** the derived id
must never donate `initialized_at`. That is already-initialized / conflict, not
reconstruction.

Native adapter receipt-aware initialize:

```text
initialize(request)
  → probe verified reviewed-init receipt for W

  if matching initialization_id receipt exists:
      requested_initialized_at = receipt.initialized_at
      rebuild the COMPLETE command from current server-resolved plan/source facts
      call D.2C1 initialize_reviewed_world(...)
      provider command_sha256 equality decides replay vs conflict

  if receipt exists with a different initialization_id:
      fail already-initialized / conflict
      do not reuse that receipt's initialized_at

  if no receipt exists:
      requested_initialized_at = one UTC timestamp for this attempt
      call D.2C1 initialize_reviewed_world(...)
      if provider reports idempotency conflict:
          re-read the verified reviewed-init receipt for W
          if receipt.initialization_id != requested initialization_id:
              preserve already-initialized / conflict
          else:
              rebuild the COMPLETE current server-owned command
                  using receipt.initialized_at
              call D.2C1 exactly once more
              identical remaining fields → digest matches → exact replay
              any changed plan/source/contribution/actor/profile field → conflict
```

The idempotency-conflict recovery exists because two identical confirms can both
observe no receipt, choose `T1` and `T2`, then DungeonMind commits `T1`. The
second request reaches the world lock with the same `initialization_id` but a
different `command_sha256` solely because of `T2`. Rebuilding once with
`receipt.initialized_at` makes the second caller exact-replay instead of a
timestamp-only conflict.

D.2C1 stores:

```text
receipt.initialized_at = command.requested_initialized_at
```

so the durable receipt contains exactly the timestamp needed to reconstruct the
original command after a lost response, process restart, or concurrent first
confirm.

This gives restart-safe and concurrent-exact replay **without**:

- a new HMAC plan schema;
- a process-local prepare secret;
- a hidden Buddy plan/receipt registry;
- trusting a client-supplied timestamp.

If any rebuilt source/contribution/plan/actor/profile field differs, the
provider's stored `command_sha256` comparison fails closed. That is the intended
behavior. Do not convert a remaining provider conflict into
`already_initialized` success.

### 3.9 Product plan schema can remain v1

Because retry timestamp is recovered from DungeonMind authority rather than
carried by the browser, D.2C2 does not need to widen `FirstWorldGraphPlan` solely
for idempotency.

Keep `dmb_first_world_graph_plan_v1` unless implementation discovers a real
contract gap. Do not add a schema revision for architecture aesthetics.

This also keeps the APP-STATE UI/type lease disjoint (`baselineRevisionId` is
already optional). AS2 #643 is merged; AS3 is dispatched on a disjoint lease.
Re-anchor implementation to current `main` before CODE.

### 3.10 Native product receipt must tell the truth about genesis topology

DungeonMind D_0 has no persisted baseline parent. For native mode:

```text
baseline_revision_id = None
committed_revision_id = D_0
```

The existing server response already models `baseline_revision_id` as optional,
so this slice may preserve `dmb_first_world_graph_confirm_v1` while changing the
native value to null.

Never manufacture a baseline revision ID and never publish an empty revision for
compatibility.

Explicit `buddy_files` mode may continue returning its legacy baseline revision
until D.3 removes that adapter/runtime.

### 3.11 Extract first-world orchestration out of the monolithic service

D.2B already established the useful pattern:

```text
extract_promote.py
  → worldbuilding_graph_publication.py
```

D.2C2 should do the same for first-world, preferred new module:

```text
apps/live_control_server/services/first_world_graph_publication.py
```

It should own mounted first-world prepare/confirm orchestration and authority
error mapping. `extract_promote.py` should become a thin delegator for
`prepare_first_world` / `confirm_first_world`.

Do not refactor unrelated extract-promote behavior.

---

## 4. Native adapter boundary

Preferred implementation files:

```text
apps/live_control_server/integrations/dungeonmind/world_graph_initialization_adapter.py
apps/live_control_server/integrations/buddy_files/world_graph_initialization_adapter.py
```

### 4.1 DungeonMind adapter

The DungeonMind adapter may import:

- `ReviewedWorldInitializationCommandV1`;
- `initialize_reviewed_world`;
- `PostgresRepositoryBundle` / reviewed-init repository;
- pinned semantic profile/v6 graph reader using the §3.6b builtin descriptor;
- the bounded mapping helpers needed to construct source records and
  `GraphContributionV2`.

The product service must not.

The adapter must map provider failures into stable Buddy port failures, including
at least:

```text
authority_unavailable
integrity_failure
already_initialized / idempotency_conflict
inexpressible
initialization_failed
```

Do not leak raw psycopg exceptions, DSNs, or provider repository records.

### 4.2 Buddy-files adapter

The named non-production adapter may wrap the existing legacy first-world Kernel
initializer and filesystem classification until D.3.

Its existence is compatibility debt, not alternate production authority.
Keep the selection rule identical to the current authority factory:

```text
production dungeonmind mode + production root → DungeonMind adapter
explicit non-production root / buddy_files / quiesced → Buddy-files adapter
```

D.3 owns deletion of this adapter and the legacy reviewed-world initializer.

---

## 5. Prepare path and review eligibility

Native prepare remains inert. Native exact-run review eligibility uses the same
probe; it does not call `classify_world_graph_state`.

Required order:

```text
resolve exact ExtractionRun
→ validate worldbuilding profile/sessionlessness
→ validate frozen source/evidence
→ admit managed Buddy world
→ prove SourceArtifact ↔ workspace lineage
→ probe WorldGraphInitializationAuthority
→ require no authoritative DungeonMind head / coherent uninitialized state
→ pure materialize first-world reviewed plan
→ return sealed product plan
```

`resolve_first_world_capability` (wired into exact-run review as
`first_world_publish_eligible`) follows the same probe gate. Do not keep a
parallel filesystem classify on the native path.

Prepare must create:

```text
0 DungeonMind graph revisions
0 DungeonMind heads
0 reviewed-init receipts
0 Buddy World Graph directories
```

Remove the current filesystem race check:

```python
world_paths.world_dir(world_graph_root(), world_id).exists()
```

from the mounted native path. DungeonMind's confirm transaction owns the race.
Filesystem classification remains legal only behind `buddy_files`.

---

## 6. Confirm path

Confirm must continue to treat the response-carried product plan as evidence,
not authority.

Required order:

```text
resolve exact run again
→ revalidate exact source / frozen evidence
→ re-prove managed world + workspace lineage
→ rebuild dispositions from sealed decision snapshot
→ pure rematerialize first-world plan
→ compare plan_id / plan_digest / decision_digest
→ compare accepted/rejected IDs, contribution ID/digest, reviewed effect, summary
→ derive deterministic initialization_id
→ WorldGraphInitializationAuthority.initialize(exact rebuilt request)
→ map provider receipt into product receipt
```

There is no pre-confirm Buddy filesystem graph-state classification in native
mode. A competing writer or unexpected durable residue is resolved by the
DungeonMind world lock/pristine predicate.

### Exact retry

Exact retry repeats the same rebuild. Native adapter finds the durable receipt,
uses its `initialized_at` to reconstruct the original provider command, and lets
D.2C1 verify the full command digest.

Concurrent first confirms that both miss the receipt follow §3.8: the loser of
the world lock recovers from idempotency conflict by rebuilding once with
`receipt.initialized_at`. Product result is success for both, not a
timestamp-only 409.

Expected product result:

```text
outcome = already_initialized
committed_revision_id = exact prior D_0
baseline_revision_id = None
zero second DungeonMind revision
zero second initialization receipt
```

### Changed/stale retry

If the same deterministic initialization id is presented with changed source,
contribution, actor, or plan semantics, D.2C1 command digest comparison must
fail closed. Do not silently repin to today's source or return an old receipt as
success.

---

## 7. Write lease

Implementation may create/modify:

```text
pyproject.toml
uv.lock

apps/live_control_server/ports/world_graph_initialization.py                  # new
apps/live_control_server/ports/world_graph_initialization_access.py           # new
apps/live_control_server/integrations/dungeonmind/world_graph_initialization_adapter.py  # new
apps/live_control_server/integrations/buddy_files/world_graph_initialization_adapter.py  # new
apps/live_control_server/services/first_world_graph_publication.py             # new
apps/live_control_server/services/first_world_graph.py
apps/live_control_server/services/extract_promote.py

# only if a bounded shared mapping extraction is required:
apps/live_control_server/integrations/dungeonmind/world_graph_writes.py
apps/live_control_server/integrations/dungeonmind_kernel/eldyrwild_existing_world_adoption_bundle_v2.py

# owning CUTOVER tests / new tests
 tests/test_first_world_graph.py
 tests/test_live_extract_promote_api.py
 tests/test_cutover_dungeonmind_world_graph_authority.py
 tests/test_cutover_*first_world*.py
```

Use actual repository test filenames discovered during implementation; do not
create duplicate test families merely to match this spelling.

Backward-looking atomic state sync in the implementation PR may modify:

```text
Docs/Plans/STEWARDS-ANCHOR-cutover.md
Docs/Plans/PR-TRACKER-campaign-supergraph.md
Docs/Roadmaps/ROADMAP-campaign-supergraph.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/PR-TRACKER-campaign-supergraph.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-campaign-supergraph.md
Docs/Design/STATUS-world-graph-continuity-spine.md   # only if its owning claims are stale
Docs/Plans/HANDOFF-CUTOVER-reviewed-first-world-initialization.md
this handoff
```

### Explicitly out of lease

Do not modify in D.2C2 unless a new concrete blocker requires re-brief:

```text
src/application_state/**
APP-STATE migrations/services
Play/Runbook persistence or runtime
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/playSurface/**
apps/live_control_server/services/play_run_*.py
apps/live_control_server/services/workspace_document_registry.py
apps/live_control_server/services/tiptap_markdown_write.py
tests/conftest.py
Docker / compose / application-state DSNs
Threat product workflow semantics
existing-world worldbuilding plan semantics
D.3 broad graph_memory deletion
```

Current APP-STATE AS2 PR #643 is merged. AS3 is dispatched; its lease remains
disjoint from the D.2C2 CUTOVER paths named above. Re-check the exact
accepted/merged AS3 lease before implementation begins and re-anchor to Buddy
`main` `2de68441dd2b0adaf934526236d2c8983f9a7e9e` (or its successor).

---

## 8. Backward-looking state sync owned by this implementation PR

Do not make a bookkeeping-only PR first. D.2C2 implementation carries the now
knowable predecessor facts atomically.

Record at minimum:

### D.2B

```text
PR #640: DONE
merge: 6ef7aefa741a82f512f5918b460cbee1a427cae4
accepted head: caa9d84e4431db1b90ea58dab2e74d270fbcffee
review cycles: 3
```

### D.2C1 design/provider

```text
Buddy design PR #642: DONE
merge: d80c8688774602972e07593b83e3d8d09d4b0a7b
accepted design head: 0f9e07686dfd157bb35acbd10765bfe3de68166f
final design review: 5023757627

DungeonMind implementation PR #46: DONE
merge: bf40e933bdedf3cf08bb23a07a135958bdb7cc6b
accepted implementation head: bc2800b1d09aa70cf33d92ea6b8fc4a786f4b999
final provider review: Cycle 3 PASS-equivalent 5024825675
```

### D.2C2

Mark active during implementation and DONE only after its own accepted head is
merged. D.3 remains blocked/false until then.

---

## 9. Required acceptance evidence

### 9.1 Pin and import boundary

Prove:

- `pyproject.toml` pins exact DungeonMind merge `bf40e933...`;
- `uv.lock` resolves that exact revision;
- no production Buddy product service imports DungeonMind PostgreSQL types;
- no product service receives a DSN/repository bundle.

### 9.2 Native prepare with Buddy graph absent

Run the mounted first-world review/prepare path with the configured Buddy World
Graph directory physically absent.

Prove:

- exact-run review reports first-world eligibility from `WorldGraphInitializationAuthority.probe()`, not Buddy graph-directory/head existence;
- after native confirm, exact-run review reports ineligible even though the Buddy World Graph directory remains absent;
- managed-world + workspace/source lineage still work;
- prepare is confirmable for a valid reviewed create-new plan;
- zero DungeonMind mutations occur;
- no Buddy graph directory is created;
- no call to `try_open_world_graph_head`, `world_paths.world_dir`, Kernel graph
  loading, or `build_empty_technical_baseline_store` occurs on this path.

### 9.3 Real PostgreSQL `∅ → D_0`

Against disposable migrated PostgreSQL:

```text
before:
  no head
  no graph revisions
  no reviewed-init receipt
  no source/contribution rows for W

after confirm:
  one head = D_0
  one graph revision D_0
  D_0.parent_revision_id = None
  one reviewed-init receipt
  exact source artifact/revision
  one reviewed contribution
  zero existing-world adoption rows
```

Buddy graph storage remains physically absent throughout.

### 9.4 Exact semantic mapping witness

Use a real first-world plan containing at least:

```text
2 accepted create-new nodes
1 accepted edge between them
1 rejected candidate
```

Prove provider command/materialization sees:

```text
accepted nodes → IdentityOutcome.CREATED_NEW
accepted edge  → identity_resolution_outcome=None
rejected fact  → durable rejected history, not D_0 fact
```

Prove receipt accepted assertion IDs equal the materialized accepted set.

Prove the provider command's `semantic_profile` is the §3.6b builtin
worldbuilding descriptor (`load_builtin_v3_descriptor()`), not a parent-copied
or invented ref.

### 9.5 Source/evidence closure

Prove every D_0 evidence ref resolves through the exact `SourceArtifactV2` and
`SourceRevision` persisted in the same provider command/transaction.

No invented artifact id, no unrelated current source lookup, no duplicate extra
source row.

### 9.6 Product receipt topology

Native response must prove:

```text
outcome = initialized
baseline_revision_id = None
committed_revision_id = D_0
```

No synthetic empty revision exists in PostgreSQL.

### 9.7 Exact retry

Call the mounted confirm endpoint again with the exact same sealed product plan.
Prove:

```text
outcome = already_initialized
same D_0
same reviewed-init receipt
same reviewed contribution
same command_sha256
1 total graph revision
1 total receipt
```

This proof must exercise receipt-seeded `requested_initialized_at`, not a mocked
constant clock.

### 9.7b Concurrent identical confirms

Two synchronized callers confirm the same sealed plan against an uninitialized
world (both may observe no receipt and choose distinct UTC timestamps).

Prove:

```text
one D_0
one reviewed-init receipt
one command_sha256
both callers succeed (initialized / already_initialized)
neither caller receives a timestamp-only idempotency conflict as the product result
```

The second caller may take the §3.8 conflict → re-read receipt → rebuild with
`receipt.initialized_at` → second D.2C1 call path. A third caller that changes
plan/source/contribution/actor/profile must still conflict.

### 9.8 Lost-response / restart-safe reconstruction

At the owning boundary, inject a response-loss condition after the provider
commit, then rebuild the exact Buddy request in a fresh adapter/service instance.

Prove the adapter obtains the durable receipt, reuses
`receipt.initialized_at`, rebuilds the complete provider command, and receives
the exact same D_0 with no second initialization.

A changed rebuilt command must conflict rather than recover.

### 9.9 Race / non-pristine refusal

Prepare while probe sees no head, then introduce an authoritative competing
state before confirm (head or forbidden durable residue). Confirm must fail
closed through DungeonMind's pristine transaction. No hidden Buddy repin,
cleanup, or second world is permitted.

### 9.10 Source/workspace drift

After prepare, mutate/advance the Buddy workspace/source authority so the exact
lineage no longer matches the sealed plan. Confirm must fail before publication.

### 9.11 Explicit file-mode regression

With an explicit test/non-production Buddy root, prove the named `buddy_files`
initializer still works with legacy storage until D.3. This is not a production
fallback test.

### 9.12 Existing writer regressions

Re-run focused D.2A + D.2B cohorts proving:

- Threat exact-parent publication/recovery unchanged;
- existing-world worldbuilding prepare binding, sealed identity, publication,
  recovery, and evidence verification unchanged.

Do not widen first-world semantics through those paths.

### 9.13 D.3 readiness static gate

At accepted D.2C2 head, mounted production first-world code must no longer import
or call:

```text
graph_memory.kernel.reviewed_world_initialization
graph_memory.kernel.world_initialization
world_supergraph storage/head APIs for first-world authority
Buddy filesystem first-world receipts
classify_world_graph_state / try_open_world_graph_head / world_paths.world_dir
  on the native eligibility/prepare/confirm path
```

Remaining occurrences must be confined to explicitly named `buddy_files`, tests,
legacy migration/tooling, or other D.3 deletion owners.

---

## 10. Error mapping

Keep stable product-level failures. Exact names may reuse existing API codes,
but semantic distinctions must survive:

```text
DungeonMind unavailable          → 503 authority_unavailable
verified authority contradiction → 409 publication_integrity_failure / world_unreadable
world already initialized        → 409 world_already_initialized
same init id, changed command     → 409 idempotency/integrity conflict
provider cannot express facts    → 409 dungeonmind_inexpressible
provider transaction failure     → 5xx first_world_initialization_failed
workspace/source drift           → existing 409 workspace/plan verification failure
```

Do not convert a **remaining** provider integrity/idempotency conflict (changed
plan/source/contribution/actor/profile, or mismatched initialization id) into
`already_initialized` success.

A first-attempt timestamp-only conflict on the **same** initialization id is not
a product failure: the adapter must apply the §3.8 re-read/`initialized_at`
rebuild and call D.2C1 once more. After that recovery, identical semantics are
`already_initialized`; real differences remain conflict.

---

## 11. Stop / re-brief conditions

Stop and return to design rather than silently expanding scope if any of these
are required:

1. DungeonMind #46 cannot consume the real Buddy first-world source/contribution
   shape without changing its public reviewed-init contract.
2. Exact restart or concurrent-confirm retry cannot be reconstructed from the
   verified provider receipt plus current server-owned sealed plan/source facts.
3. D.2C2 would require persisting a new Buddy initialization/receipt registry.
4. The only path forward requires a fake expected parent or ExistingWorldAdoption.
5. AS3 or a later APP-STATE successor takes ownership of a file D.2C2 genuinely
   must mutate and the collision cannot be removed by sequencing/rebase.
6. Correct native behavior requires broad deletion of graph_memory beyond the
   mounted first-world writer; that belongs to D.3.
7. Product compatibility requires fabricating a baseline revision instead of
   returning `null`.
8. Concurrent identical confirms cannot be made exact-replay-safe without a new
   plan schema, HMAC timestamp, or Buddy initialization registry.

---

## 12. Completion truth

D.2C2 is DONE only when all of this is true:

```text
Mounted graph readers                  → DungeonMind native
Exact-run Graph Review writes          → DungeonMind native D.1
Threat publication                     → WorldGraphAuthority → DungeonMind
Existing-world worldbuilding           → WorldGraphAuthority → DungeonMind
First-world/bootstrap                  → WorldGraphInitializationAuthority → DungeonMind
Buddy product/runtime non-graph state  → Buddy-owned stores/services
```

and:

```text
mounted Buddy World Graph writers = 0
```

At that point D.3 is no longer a migration project. It is demolition of
explicitly dead Buddy graph-engine adapters/runtime plus whatever narrow test or
tooling accommodations remain.

Do **not** perform D.3 in this PR.
