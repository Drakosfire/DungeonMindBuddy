---
pr_body_template: |
  ## Handoff pointer
  - Conversation: CON-READY
  - Flow / agent: INGEST
  - Direction: DESIGN → CODE
  - Handoff: `Docs/Plans/HANDOFF-INGEST-first-world-graph-from-reviewed-source.md`
  - Branch: `agent/con-ready-first-world-graph-initialization`

  ## Verification pointer
  - Base: `0a6a1ab5ab0aab197ea16059ec20cd61dea16100`
  - Merged predecessor: PR #565 (`BUILD: read imported sources as rich documents`)
  - Verification: see §8 and the latest numbered review handback

  The checked-in handoff, cumulative diff, nano commits, numbered review
  handback, and independently rerun verification are the review contract. The PR
  description is transport metadata only.
---

# HANDOFF — INGEST: First World Graph from Reviewed Source

**Created:** 2026-08-12.
**Status:** ACTIVE — dispatch exactly one implementation capability.
**Conversation / workstream:** `CON-READY`
**Flow / agent:** `INGEST`
**Handoff direction:** `DESIGN → CODE`
**Canonical handoff path:** `Docs/Plans/HANDOFF-INGEST-first-world-graph-from-reviewed-source.md`
**Implementation branch:** `agent/con-ready-first-world-graph-initialization`
**PR title:** `INGEST: initialize a new world's graph from reviewed source`
**Base:** `main` at `0a6a1ab5ab0aab197ea16059ec20cd61dea16100`
**Merged predecessor:** PR #565 — `BUILD: read imported sources as rich documents`
**Roadmap slice:** `CR02A` — first reviewed source → durable World Graph
**Primary CON-READY behavior:** advances `CR-U3 — Get a useful semantic index`
**Secondary behavior:** first bounded piece of `CR-U4 — Inspect and correct what DungeonBuddy understood`
**Named immediate successor:** `CR02B — existing-world review/correction + duplicate binding`
**Following successor:** `CR02C — graph object → exact source passage navigation`

> **Dispatch rule:** This checked-in handoff is authoritative once present on the implementation branch. It does not need to merge to `main` before INGEST starts.
>
> **PR-body rule:** The PR description is transport metadata only. It is never merge authority and cannot substitute for the handoff, cumulative diff, nano-commit story, review handback, or verification.
>
> **Review-count rule:** The first formal review on this PR is `Review Cycle 1`; every later formal review increments exactly once regardless of PASS or CHANGES REQUESTED. Fix commits, handbacks, comments, or reruns do not increment the count until a formal review occurs.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Managed world** | A world admitted by PR #564's server-owned `world_containers.json` registry, with exact `world_id=W` and source root `corpus/<W>-markdown`. |
| **First-world publish** | The one transition from a managed world with no World Graph to a durable World Graph initialized from a human-reviewed, source-backed contribution. |
| **Exact Build run** | A canonical `ExtractionRun` created from one committed workspace-document revision and one immutable `SourceArtifact`, not a legacy/latest graph-ingest selector. |
| **Source world** | `SourceArtifact.world_id` resolved server-side from the exact workspace-document lineage. It is the only acceptable target-world authority for this capability. |
| **Review decision** | Explicit GM choice for one candidate: keep/create or reject for objects, keep/accept or reject for relationships. This slice does not imply full editing. |
| **Initialization plan** | A sealed, deterministic description of the exact run, source, decisions, materialized contribution digest, and intended target world before the irreversible graph publication. |
| **Reviewed initialization receipt** | Durable proof that a particular exact run + reviewed decision set initialized W. It is not the legacy checked-in-bundle bootstrap receipt and must not fabricate Git/bundle provenance. |
| **Generic promote** | The older `extract-promote/prepare|confirm` path for already-promotable recap/canon runs. Worldbuilding remains outside that generic path in this PR. |
| **Worldbuilding write-plan v1** | Existing BLD-10 prepare/confirm machinery for a worldbuilding candidate against an already-existing head. It is useful precedent but is not sufficient for an absent world because it requires an existing parent revision and currently hardcodes Eldyrwild. |
| **Capability** | A coherent behavior someone can use, depend on, test, or revert. |
| **Owning boundary** | The layer where a guarantee becomes true and therefore must be proved. |
| **Invariant** | The single property every changed layer and observable path establishes or protects. |
| **Stop condition** | A discovered fact that invalidates the slice boundary or requires a contract reconciliation before implementation expands. |

---

# §0 Pickup and operating rules

Before implementation:

1. Read `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`.
2. Read `Docs/Roadmaps/ROADMAP-con-ready.md`.
3. Read the three merged CR01 handoffs:
   - `Docs/Plans/HANDOFF-CON-READY-build-lossless-markdown-import.md`
   - `Docs/Plans/HANDOFF-BUILD-create-new-world-from-build.md`
   - `Docs/Plans/HANDOFF-BUILD-rich-source-reader.md`
4. Read exact Build extraction lineage:
   - `apps/live-control-ui/src/buildSurface/useBuildExtraction.ts`
   - `apps/live_control_server/routes/graph_preview.py`
   - `apps/live_control_server/services/source_artifact_registry.py`
   - `apps/live_control_server/services/promotable_ingest_run.py`
5. Read the current review/publish authority:
   - `apps/live_control_server/models/extract_promote.py`
   - `apps/live_control_server/services/extract_promote.py`
   - `src/graph_memory/worldbuilding_write_plan.py`
   - `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx`
   - `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewExactRunProjection.tsx`
   - `apps/live-control-ui/src/api/extractPromoteApi.ts`
6. Read the generic Kernel initialization implementation before inventing another transaction:
   - `src/graph_memory/kernel/world_initialization.py`
   - `src/graph_memory/kernel/world_initialization_models.py`
   - `src/graph_memory/world_supergraph/paths.py`
7. Reconcile against current `main` and open PRs before coding. There was no open CON-READY collision at dispatch. If a newer branch now owns generic first-world graph publication, stop rather than create a second initialization authority.

The governing product question is:

> **If I ignored every architecture name and watched the GM after importing a new one-shot world, can they turn the first extracted source into that world's durable semantic memory without touching a terminal or accidentally writing into Eldyrwild?**

For this PR the answer must become:

> **Yes. In Graph Review the GM can keep or reject the first source's extracted objects/relationships, explicitly create the new world's World Graph, and receive a durable receipt for exactly those selected source-backed changes.**

Do not turn this into every form of graph correction, object editing, source navigation, or generic campaign creation.

---

# §1 Mission and merge-ready invariant

## 1.1 Current user-visible failure

CR01 now gets a GM surprisingly far:

```text
Build
→ New world: The Glass Orchard
→ Import exact Markdown source
→ Read it comfortably
→ Extract
→ exact reviewable ExtractionRun
→ Open in Graph Review
```

Then the product stops being CON-READY.

The repository already preserves the correct world identity through the source layer:

```text
WorkspaceDocument
  world_id = W
  campaign_id = W        # world-level Build source convention from PR #564
        ↓
SourceArtifact
  world_id = W
  campaign_id = W
  workspace_document_id = D
  workspace_document_revision = R
  content_sha256 = H
```

But the promotion adapter drops `world_id`, and the extract-promote service substitutes:

```py
DEFAULT_WORLD_ID = "eldyrwild"
```

The generic worldbuilding path is also deliberately inspect-only, while the explicit BLD-10 write-plan path requires an already-existing World Graph parent revision.

So a newly-created world can produce valid source-backed extraction evidence but cannot become its own first durable World Graph through the product.

That is the first CR02 blocker.

## 1.2 Mission

> **As a GM who created a new managed world and extracted its first committed source, I can review the extracted objects and relationships, reject obvious junk, and explicitly initialize that same world's World Graph from exactly the changes I kept.**

## 1.3 One independently useful outcome after this PR

A convention one-shot can go from pasted Markdown to a durable semantic graph without pre-existing graph setup:

```text
The Glass Orchard source
→ Extract
→ Review Hesta / Apothecary / faction / threat / relationships
→ uncheck/reject one bad candidate
→ Create World Graph
→ durable graph under world_id = the-glass-orchard
```

The created graph contains only the reviewed accepted contribution and its source/evidence support. Eldyrwild is not involved.

## 1.4 Merge-ready invariant

> **For one canonical reviewable worldbuilding ExtractionRun whose exact SourceArtifact and workspace-document lineage identify a managed world W with no existing World Graph, Graph Review derives W only from server-resolved lineage, presents an explicit keep/reject review of that exact run, seals the GM's non-empty decision set, and on confirm atomically initializes W from exactly the resulting source-backed contribution. Retry after an ambiguous result is idempotent for that same plan; a foreign, unmanaged, already-initialized, unreadable, stale, or identity-mismatched world fails closed. No client-supplied world/path, DEFAULT_WORLD_ID fallback, fake campaign/session, fabricated Git/bundle attestation, static campaign map mutation, source rewrite, or graph mutation outside W is permitted.**

Every implementation decision and test should be reducible to this invariant.

## 1.5 What becomes true

After merge, for a **new managed world with no graph**:

- an exact worldbuilding run knows its actual source world W through server lineage;
- Graph Review can distinguish `first publish available` from ordinary inspect-only state;
- the GM can explicitly keep/reject first-source object and relationship candidates;
- relationship selection cannot survive rejected endpoints;
- confirm creates an empty technical baseline + reviewed contribution as one atomic initialization transaction;
- the resulting graph carries the source artifact/evidence support from the extraction;
- retry cannot create another graph or duplicate the first contribution;
- a durable reviewed-initialization receipt explains why this graph exists.

## 1.6 What remains deliberately false afterward

Do **not** claim full CR02 completion.

Still false / successor work:

- merging a second worldbuilding source into an already-initialized world through this new product path;
- `bind_existing` / duplicate reconciliation in the new-world workflow;
- rename extracted object before publication;
- manually add a missing object;
- edit relationship endpoints/type/label;
- merge duplicate graph objects;
- rich graph-object → exact source passage navigation (`CR-U5`);
- Hermes source follow-through (`CR03`);
- statblock/mechanics enrichment (`CR04`);
- Playable Layer behavior (`CR05`);
- local source asset ingestion/serving;
- campaign lifecycle inside W.

Those are not excuses to weaken first-world identity or evidence integrity.

## 1.7 Pre-dispatch critique

| Question | Answer |
|---|---|
| Is this just architecture work? | **No.** The GM gets a new explicit action they cannot perform today: create the first graph for a world they just imported. |
| Why not wire the existing generic promote sheet? | Worldbuilding is intentionally inspect-only there; generic promote also assumes an existing head and legacy default world. Re-enabling it would violate prior authority boundaries. |
| Why not just create an empty graph at world creation? | Because PR #564 deliberately made world creation source-root only. Empty graph bootstrap without reviewed knowledge is not independently useful and creates partial-state problems. The first reviewed publish is the correct commit point. |
| Why not generalize the old Eldyrwild bootstrap service? | It is a certified checked-in-bundle activation path with fixed Eldyrwild attestation. Interactive GM review has different provenance and must not fabricate bundle/Git approval. |
| Why not solve all CR-U4 now? | First-world publication needs only create/reject/accept decisions. Existing-world binding, rename/add/edit are a coherent next capability and would materially widen this PR. |
| What is the most likely catastrophic bug? | A Glass Orchard run initializes or prepares against Eldyrwild because `DEFAULT_WORLD_ID` or campaign label remains an implicit target. Every owning test must adversarially use W != `eldyrwild`. |
| What is the second most likely bug? | A failed/ambiguous confirm leaves an empty production W graph, then retry is blocked or duplicates the contribution. Initialization must stage and promote atomically. |
| What fact would force a stop? | If the Kernel cannot represent a world-level/no-session technical baseline without fabricating a user-visible session, or if atomic initialization would require reusing the legacy bundle attestation with fake values. Stop and reconcile the generic initialization contract instead. |

---

# §2 Ground truth from the current repository

This section is not aspirational; implementation must start from these facts.

## 2.1 Build extraction is already exact enough

Do not rebuild extraction.

`useBuildExtraction()` already launches only from a committed-clean document envelope and sends:

```text
document_id
expected_revision
expected_content_sha256
profile_id = worldbuilding_shepherds_flock_v0
profile_version = 0.1
```

The server creates a SourceArtifact from the exact committed workspace revision and produces an exact canonical ExtractionRun. The Build handoff to `/ingest` carries exact:

```text
extractionRunId
sourceArtifactId
documentId
revision
```

No `latest` substitution is allowed.

## 2.2 SourceArtifact already has the correct world

Current creation logic does:

```text
artifact_world_id = record.world_id if record.world_id else record.campaign_id
```

For PR #564-managed worlds, the workspace document explicitly has:

```text
world_id = W
campaign_id = W
```

Therefore the authoritative first-world lineage is already present before this PR.

## 2.3 The adapter currently loses W

`PromotableIngestRun` does not currently carry `world_id`.

The canonical ExtractionRun adapter resolves the SourceArtifact but returns campaign/session only. This PR must preserve the exact source world at that seam.

## 2.4 Extract-promote currently hardcodes Eldyrwild

`src/graph_memory/extract_promote_ops.py` defines:

```py
DEFAULT_WORLD_ID = "eldyrwild"
```

The live service currently passes `DEFAULT_WORLD_ID` to generic prepare and BLD-10 worldbuilding write-plan prepare/confirm contexts.

This default remains valid only for explicitly legacy paths that genuinely lack a world identity. It must not be consulted for a canonical Build ExtractionRun with exact SourceArtifact world lineage.

## 2.5 Generic worldbuilding promote is deliberately inspect-only

The exact-run review package can show source prose and assertion evidence for worldbuilding, but generic `/extract-promote/prepare` rejects BLD-08 worldbuilding publication.

Preserve this boundary.

This PR creates a **separate first-world reviewed publication capability**; it does not silently make worldbuilding eligible for the recap/canon generic-promote path.

## 2.6 Existing BLD-10 machinery is useful precedent, not a drop-in solution

The existing worldbuilding write plan already knows explicit decisions:

Objects:
- `create_new`
- `bind_existing`
- `reject`
- `defer`

Relationships:
- `accept`
- `reject`
- `defer`

And its confirm path can merge a materialized reviewed contribution into an existing head.

But it currently:

- requires `expected_parent_revision_id`;
- verifies/open-merges against `DEFAULT_WORLD_ID`;
- therefore cannot initialize an absent W;
- has no current product UI using it.

Reuse semantic mapping/materialization helpers where they are actually generic. Do not force a fake parent revision into this first-world capability.

## 2.7 The Kernel already proves the right atomic pattern

`kernel.initialize_world_from_contributions()` already demonstrates the required transaction pattern:

```text
staging root
→ empty technical baseline
→ ordered contribution merge
→ rebuild/integrity/evidence support proof
→ initialization receipt
→ atomic os.rename into production under world-init lock
```

This PR should factor/reuse that transaction pattern.

Do **not** implement:

```text
mkdir production W
→ publish empty head
→ later merge contribution
```

That creates a recoverable-but-bad partial state the existing Kernel carefully avoids.

## 2.8 The legacy bootstrap approval attestation is not truthful for this path

`WorldInitializationApprovalAttestation` currently uses bundle-oriented fields:

```text
bundle_id
bundle_digest
approved_bundle_merge_sha
```

The Eldyrwild bootstrap service uses those fields for a checked-in certified bundle.

A GM clicking `Create World Graph` is not approving a Git-merged bundle.

**Never populate `approved_bundle_merge_sha` with a sentinel, source digest, current code SHA, empty string, or invented value just to reuse the old receipt model.**

The reviewed-source initializer must have truthful review/run/source/decision attestation of its own, or a genuinely generic additive authority contract that leaves old receipts valid byte-for-byte.

---

# §3 Observable paths and adversarial sequences

## 3.1 Observable-path inventory

| Path | Current behavior | Required behavior | Owning boundary |
|---|---|---|---|
| New managed W → first source → Extract → Graph Review | exact source/evidence visible; worldbuilding marked inspect-only | exact review identifies W and offers `Create World Graph` | run resolver + review package + UI |
| First-world review | no publication decisions wired | explicit keep/reject for objects and relationships | first-world review UI |
| Reject one object | n/a | object excluded from contribution; dependent relationships excluded/disabled | UI decision builder + server validator |
| Reject one relationship | n/a | relationship excluded, endpoint objects may remain | plan builder |
| Confirm non-empty review | world_not_initialized / Eldyrwild assumption | atomically creates W baseline + contribution | reviewed initializer |
| Confirm with zero accepted assertions | n/a | fail closed; do not create empty W graph | prepare/confirm |
| Lost confirm response | n/a | retry exact same sealed plan returns same initialized result/no duplicate | receipt + audit |
| Retry after different process initialized W | n/a | fail closed unless exact matching reviewed-init receipt proves same plan | initializer |
| W missing managed-world registry record | source lineage may still name W | no first-world publish; no filesystem adoption | managed-world admission |
| unmanaged `out/.../worlds/W` already exists | no valid new-world state | fail closed; never overwrite/adopt | initializer |
| world graph exists/readable | this slice is not existing-world merge | first-publish unavailable; direct user to later existing-world workflow | review capability state |
| world graph exists/unreadable | could be mistaken for absent | fail closed as damaged/unreadable, never initialize over it | status classifier |
| SourceArtifact W != candidate/run campaign scope | currently world not checked | fail closed before review publication | run resolver/plan verifier |
| SourceArtifact says W but workspace D now points elsewhere | immutable source should prevent this | exact lineage verification fails closed | first-world admission |
| W == `the-glass-orchard`, Eldyrwild exists | default can leak | only W may be inspected/mutated | every backend owning test |
| Browser sends `worldId=eldyrwild` or a path | no such input should exist | request rejected/ignored by strict model; browser cannot choose target | API model |
| Sessionless world source | current run session empty/null | initialize without inventing `session-1` or another user-visible session | initializer/store/projection tests |
| Page navigation while confirm in flight | possible stale adoption | terminal receipt remains bound to exact run/W; no foreign-page state mutation | UI generation/frozen binding |
| Hard reload after success | no first graph today | world remains initialized and same first contribution is present | durable receipt + graph store |

## 3.2 Required first-world decision model

This PR intentionally exposes only decisions that make sense when W has no existing graph.

For an object candidate:

```text
Keep   → create_new
Ignore → reject
```

For a relationship candidate:

```text
Keep   → accept
Ignore → reject
```

Do not expose `bind_existing` in first-world mode: there is no W graph to bind against.

Do not expose `defer` unless the UI gives it a distinct understandable meaning. `Ignore` must not secretly mean defer.

### Relationship dependency rule

A kept relationship is valid only when both endpoint object candidates are also kept/materialized by this plan.

Preferred behavior:

- rejecting an endpoint automatically turns dependent relationships off and visually explains why;
- re-enabling a relationship may re-enable its endpoints only if that behavior is explicit and tested;
- server independently rejects impossible decision sets even if the UI misbehaves.

Never create dangling first-world edges.

## 3.3 Defaults

For a valid first-world extraction:

- evidence-backed object candidates may default to `Keep`;
- evidence-backed relationship candidates may default to `Keep` only when both endpoints are kept;
- zero-candidate or zero-kept plans are not confirmable;
- unsupported/invalid-evidence candidates are not silently defaulted into the contribution.

The GM must see what is going to be created before the irreversible action.

---

# §4 Target architecture and contracts

## 4.1 Canonical lineage

The target world chain is:

```text
WorkspaceDocument D@R
  world_id = W
  campaign_id = W
  committed bytes digest = H
        ↓ server creates
SourceArtifact A
  world_id = W
  campaign_id = W
  workspace_document_id = D
  workspace_document_revision = R
  content_sha256 = H
        ↓ canonical ExtractionRun registry
ExtractionRun X
  source_artifact_id = A
        ↓ server-owned resolver
FirstWorldReviewContext
  run_id = X
  world_id = W
  source_artifact_id = A
  source_revision_id = sha256:H
  document_id = D
  document_revision = R
  campaign_scope = W
  session_scope = null
        ↓ explicit GM decisions
FirstWorldInitializationPlan P
  world_id = W
  exact run/source identity
  decision_digest
  contribution payload digest
        ↓ confirm
World Graph W
```

The browser supplies only:

```text
runId
decisions
```

The browser never supplies:

```text
worldId
world root/path
SourceArtifact path
candidate graph path
parent revision
baseline revision
contribution id/digest
workspace target path
```

## 4.2 `PromotableIngestRun` world identity

Add an exact world identity to the canonical run resolver.

Recommended shape:

```py
@dataclass(frozen=True)
class PromotableIngestRun:
    ...
    world_id: str | None
```

Rules:

1. Canonical Build ExtractionRun:
   - load SourceArtifact;
   - require its `world_id` for first-world eligibility;
   - preserve it exactly.
2. Cross-check exact workspace lineage before first publish:
   - SourceArtifact `workspace_document_id` exists;
   - workspace record is active `worldbuilding_source`;
   - its explicit `world_id == SourceArtifact.world_id`;
   - its revision/digest agree with the immutable SourceArtifact lineage.
3. Legacy graph-ingest/recap path may keep `world_id=None` and legacy default behavior outside this capability.
4. Never derive a canonical Build run's world from current UI campaign selection or `DEFAULT_WORLD_ID`.

## 4.3 Managed-world admission

First-world publication is allowed only when W is a managed world from PR #564.

Server must resolve:

```py
get_world_container(repo_root(), W)
```

and verify at least:

```text
record.world_id == W
record.source_root_relpath == corpus/<W>-markdown
source root exists
workspace source belongs to W
```

Do not create or repair the managed world registry here.

Do not adopt an arbitrary `corpus/<W>-markdown` directory merely because it exists.

## 4.4 First-world graph-state classifier

The review package needs a server-owned classification for the exact run's W.

Recommended additive fields on the exact-run review response, or an equivalent nested capability object:

```text
worldId: W
worldState: "uninitialized" | "initialized" | "unreadable" | "unmanaged"
firstWorldPublishEligible: true | false
firstWorldPublishReason: string | null
```

Rules:

- `uninitialized`: no production world graph exists at W and the world is managed;
- `initialized`: a valid readable W head exists;
- `unreadable`: W storage exists but cannot be opened/validated as an initialized graph;
- `unmanaged`: SourceArtifact names W but no matching managed world record exists.

Only `uninitialized` + exact canonical worldbuilding run + valid evidence package is eligible.

Do not collapse `unreadable` into `uninitialized`.

The existing `promotable=false` field for generic worldbuilding promote may remain false. First-world publish is a separate explicit capability, not a reversal of BLD-07.

## 4.5 Product API contract

Implement an additive first-world prepare/confirm API rather than weakening generic promote.

Recommended route shape:

```text
POST /api/live/extract-promote/worldbuilding/first-world/prepare
POST /api/live/extract-promote/worldbuilding/first-world/confirm
```

Exact naming may vary if the owning route conventions demand it, but the capability must remain visibly separate from generic recap promote and existing-head BLD-10.

### Prepare request

```json
{
  "schema": "dmb_first_world_graph_prepare_request_v1",
  "runId": "<exact run>",
  "decisions": [
    {"assertionId":"npc_hesta", "decision":"create_new"},
    {"assertionId":"loc_apothecary", "decision":"create_new"},
    {"assertionId":"edge_hesta_runs_shop", "decision":"accept"},
    {"assertionId":"junk_candidate", "decision":"reject"}
  ]
}
```

No world or parent fields.

### Prepare response

Recommended authority fields:

```text
schema = dmb_first_world_graph_plan_v1
planId
planDigest
decisionDigest
worldId = W
runId
sourceArtifactId
sourceRevisionId
workspaceDocumentId
workspaceDocumentRevision
campaignScope
sessionScope = null
acceptedAssertionIds
rejectedAssertionIds
contributionId
contributionPayloadSha256
reviewedEffect / sealed contribution material needed for confirm
summary
confirmable = true|false
diagnostics
```

Do not put filesystem paths into browser authority.

### Confirm request

```json
{
  "schema": "dmb_first_world_graph_confirm_request_v1",
  "plan": { ...exact prepare response... }
}
```

### Confirm receipt

Recommended user/authority fields:

```text
schema = dmb_first_world_graph_confirm_v1
outcome = initialized | already_initialized | published_audit_degraded
worldId = W
planId
planDigest
decisionDigest
sourceArtifactId
sourceRevisionId
contributionId
baselineRevisionId
committedRevisionId
appliedAssertionCount
acceptedAssertionIds
rejectedAssertionIds
auditStatus
warnings
```

`already_initialized` is allowed only when the durable reviewed-initialization receipt proves this exact plan/contribution is already the initialization authority.

## 4.6 Prepare authority

Prepare must re-resolve all durable authority from `runId`.

Ordered prepare:

```text
runId
→ canonical ExtractionRun
→ exact SourceArtifact
→ exact workspace-document lineage
→ W
→ managed-world registry W
→ classify W graph state
→ load exact candidate + frozen source-span index
→ re-run existing candidate/evidence/profile validation
→ validate explicit decisions are complete/coherent
→ materialize one deterministic source_extraction contribution for W
→ digest contribution
→ seal first-world plan
```

No production graph mutation in prepare.

### Candidate identity

Use existing BLD-08 semantic mapping and contribution construction wherever those functions do not require an existing graph.

Do not add a second worldbuilding candidate grammar.

### Complete decision set

The plan must make every candidate's disposition explicit or derive it by one documented closed rule. Preferred contract: require exactly one decision per candidate assertion ID and reject duplicates/unknown/missing IDs.

This prevents a later parser/profile change from silently changing what “default selected” meant at confirm time.

## 4.7 First-world initialization transaction

This is the core backend capability.

Create an additive generic reviewed-initialization primitive, preferably under Kernel, that reuses/factors the proven staging transaction in `world_initialization.py`.

Conceptually:

```text
initialize_reviewed_world(
    world_id=W,
    campaign_id=W,
    source/run/decision authority,
    contribution=C,
)
```

Required steps:

```text
acquire/coordinate world-init publication lock
→ prove W absent
→ build staging world
→ publish structurally valid empty technical baseline
→ merge exactly C
→ verify contribution ledger + evidence support + rebuild equivalence + world integrity
→ write reviewed-initialization receipt inside staging authority
→ atomically rename staged W into production
→ after rename, never turn success into a pre-commit error
```

### Reuse, do not copy

If current private helpers in `world_initialization.py` need factoring, factor them into a shared internal transaction primitive used by both:

- legacy certified-bundle initialization; and
- reviewed-source initialization.

Do not maintain two subtly different implementations of staging, integrity verification, and atomic promotion.

## 4.8 Truthful reviewed initialization authority

Do not reuse legacy `WorldInitializationApprovalAttestation` with fake values.

Add a separate reviewed-source receipt/authority model, e.g.:

```text
dmb_reviewed_world_initialization_receipt_v1

world_id
campaign_id
run_id
source_artifact_id
source_revision_id
workspace_document_id
workspace_document_revision
plan_id
plan_digest
decision_digest
contribution_id
contribution_payload_sha256
baseline_revision_id
initial_head_revision_id
actor
created_at
```

A compact nested reviewed-attestation object is also acceptable.

The authority digest stamped on the technical baseline should bind the above semantic approval inputs, not a fabricated Git concept.

### Backward compatibility

Existing Eldyrwild `dmb_world_initialization_receipt_v1` files and their plan/attestation digests must continue to parse and compare exactly as before.

Do not add a defaulted field to the old strict attestation model if serializing it would change old plan/attestation digests.

If a shared generic model cannot be added without changing persisted legacy digests, keep the new reviewed receipt additive and separate.

## 4.9 No fake session

The first Build world source is world-level and normally has no session.

Do not invent:

```text
session-1
session-0
first-session
```

merely because the current union-supergraph technical baseline has a string `focus_session_id` field.

The initializer must preserve the semantic truth:

```text
session scope = none
```

If the current storage model already treats `focus_session_id=""` as technical “no focus”, prove that through validation/projection tests and keep it non-user-visible.

If it cannot safely represent no session, **STOP CONDITION:** reconcile the generic world-level graph storage contract before publication. Do not smuggle a fake playable session into W.

## 4.10 Confirmation and race semantics

Confirm must re-resolve the exact run/source/world again. The response-carried plan is evidence to verify, not authority to choose W.

Before the irreversible commit:

```text
resolved run == plan.runId
SourceArtifact == plan source identity/digest
workspace lineage == plan document identity/revision
managed world == W
candidate/profile/evidence still verify
materialized contribution digest == sealed plan digest
W graph state == uninitialized
```

Then initialize atomically.

### Race: W appears before confirm

If W appears between prepare and confirm:

1. load reviewed initialization receipt if present;
2. if it proves the exact same `planDigest` + contribution digest and current head descends from that initialized head, return `already_initialized`;
3. otherwise return 409 (`world_already_initialized` / `stale_world_state`) and do not mutate.

Do not reinterpret a first-world plan as a normal merge after a race.

### Lost response retry

If the first confirm committed and the network response was lost:

- exact retry must resolve to `already_initialized` or equivalent terminal receipt;
- no second baseline;
- no duplicate contribution;
- no second initialization receipt;
- no mutation of another world.

## 4.11 Post-commit audit

After atomic rename, a best-effort audit may fail without converting a committed graph into an “it definitely failed” response.

Use the same philosophical rule as existing confirm code:

```text
before publication proven → error is safe
publication proven → terminal receipt, possibly audit degraded
```

The receipt must identify the immutable initial committed revision, not simply whatever later head happens to exist.

## 4.12 UI: exact first-world review

Add a game-facing review control inside the existing exact-run Graph Review path.

Recommended component:

```text
GraphReviewFirstWorldPublishSheet
```

Do not reuse `GraphReviewExtractPromoteSheet` if that requires pretending worldbuilding is generic campaign-memory promotion.

GM-facing copy should be about the current world:

```text
Review what DungeonBuddy found

✓ Hesta — person
✓ Hesta's Apothecary — location
✓ Hesta runs Hesta's Apothecary — relationship
☐ “Old Ferryman” — person

[ Create World Graph with 3 changes ]
```

Avoid:

- `proposal_digest`
- `parent revision`
- `MDAST`
- `candidate graph`
- `campaign memory`
- `bootstrap`

as primary UI language.

Those may remain in test/debug attributes if necessary.

### Source evidence

The exact-run review already has source prose + assertion evidence. Preserve that. The GM should be able to understand why an object/relationship was extracted without opening debug JSON.

This PR does not need to implement the full #565 source-reader navigation link yet; CR02C owns graph→source follow-through.

## 4.13 UI terminal receipt

On success, show something like:

```text
World Graph created
3 source-backed changes added to The Glass Orchard.
```

The sheet may list accepted objects/relationships from the sealed plan/receipt.

Do not claim an object is persisted unless the terminal receipt proves it.

If post-confirm committed graph reload is already possible without static campaign-map changes, reload it. If current Graph Review live-state infrastructure cannot represent this sessionless dynamic W, do not widen the PR into a whole new graph browser. Preserve the terminal receipt and make the next action truthful.

**Minimum product acceptance for this slice:** the GM can complete the review and create W's durable graph entirely in DungeonBuddy, with a clear terminal result. CR02B/C can improve browsing/correction/navigation.

---

# §5 State, identity, and failure matrices

## 5.1 World-state matrix

| Source/run | Managed W? | Graph W | First-world UI | Prepare | Confirm |
|---|---:|---|---|---|---|
| canonical worldbuilding | yes | absent | enabled | allowed | initialize |
| canonical worldbuilding | yes | valid existing | disabled, “World Graph already exists” | reject | reject first-world path |
| canonical worldbuilding | yes | unreadable/corrupt | disabled error | reject | reject |
| canonical worldbuilding | no | absent | disabled unmanaged | reject | reject |
| canonical worldbuilding | no | existing | disabled unmanaged | reject | reject |
| legacy recap run | n/a | any | not shown | generic existing behavior | generic existing behavior |
| legacy graph-ingest worldbuilding artifact | ambiguous | any | not shown unless exact managed-world lineage can be proven | reject first-world | reject |
| canonical Build run with missing world lineage | no authority | any | disabled identity error | reject | reject |

## 5.2 Decision matrix

| Candidate kind | UI Keep | UI Ignore | Invalid in this slice |
|---|---|---|---|
| object/node | `create_new` | `reject` | `bind_existing`, ambiguous defer |
| relationship/edge | `accept` | `reject` | accept if endpoint rejected/missing |

## 5.3 Identity matrix

| Identity | Authority | Client selectable? | Fallback? |
|---|---|---:|---:|
| target world W | SourceArtifact + exact workspace lineage | No | No DEFAULT for canonical Build run |
| managed-world membership | `world_containers.json` | No | No filesystem adoption |
| source bytes | immutable SourceArtifact digest/URI | No | No current workspace text fallback |
| candidate graph | exact ExtractionRun component | No | No latest |
| source span index | exact run-pinned component | No | No registry-current re-derive |
| decision set | explicit GM review | Yes | no hidden confirm defaults |
| contribution | server materialized from sealed plan | No | no browser contribution payload authority |
| graph root | configured server world root | No | no path input |
| existing parent | none for first-world | No | no fake parent |
| session scope | exact run/source = none | No | no invented session |

## 5.4 Failure/retry matrix

| Failure point | Durable W graph? | Retry behavior |
|---|---:|---|
| review package load | no | exact run reload |
| decision validation | no | fix review decisions |
| prepare verification | no | rerun exact prepare |
| staging baseline publish | no production W | safe retry after staging cleanup |
| staging contribution merge | no production W | safe retry after staging cleanup |
| staging integrity proof | no production W | safe retry after staging cleanup |
| atomic rename not reached | no | safe retry |
| rename succeeds, response fails | yes | exact plan retry returns already_initialized after receipt/audit proof |
| foreign W appears before rename | foreign/existing W | fail closed; never overwrite |
| post-commit audit degraded | yes | terminal degraded receipt; never “retry to maybe publish again” |

---

# §6 Files in scope — strict allowlist

Every production change must be listed here or reconciled under the bounded discovery exception before review acceptance.

## 6.1 Server lineage + API

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live_control_server/services/promotable_ingest_run.py` | Preserve exact SourceArtifact `world_id` on canonical Build runs; keep legacy behavior explicit. |
| Modify | `apps/live_control_server/models/extract_promote.py` | Add strict first-world review/prepare/confirm models and additive review-package world capability fields. |
| Modify | `apps/live_control_server/services/extract_promote.py` | Resolve first-world eligibility, build/verify sealed first-world plan, call atomic reviewed initializer, classify retries. |
| Modify | `apps/live_control_server/routes/extract_promote.py` | Expose additive first-world prepare/confirm routes. |
| Read-only expected | `apps/live_control_server/services/world_container_registry.py` | Managed-world admission authority; should not need mutation. |
| Read-only expected | `apps/live_control_server/services/source_artifact_registry.py` | Exact source-world/workspace lineage authority; should not need mutation. |

## 6.2 Kernel initialization

| Action | Path | Purpose |
|---|---|---|
| Create or modify | `src/graph_memory/kernel/reviewed_world_initialization.py` | Reviewed-source initialization authority/receipt + idempotent inspect/confirm semantics. Prefer a new module to avoid polluting legacy bundle policy. |
| Modify as needed | `src/graph_memory/kernel/world_initialization.py` | Factor shared atomic staging/promotion primitive so reviewed init and legacy init do not duplicate transaction logic. Legacy behavior/digests unchanged. |
| Modify as needed | `src/graph_memory/kernel/__init__.py` | Export the reviewed initializer if Kernel conventions require it. |
| Modify as needed | `src/graph_memory/world_supergraph/paths.py` | Add a safe reviewed-initialization receipt path if receipt is stored inside W. |
| Modify (reconciled) | `src/graph_memory/union_supergraph/validate.py` | Allow `focus_session_id=""` as technical no-focus for sessionless / world-level stores. See §10.1. |

## 6.3 Frontend product path

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/api/types.ts` | First-world review/plan/receipt types; exact-run world capability fields. |
| Modify | `apps/live-control-ui/src/api/extractPromoteApi.ts` | First-world prepare/confirm client calls. |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx` | Route eligible exact worldbuilding run to first-world review capability without generic promote. |
| Create | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewFirstWorldPublishSheet.tsx` | Keep/reject review + explicit Create World Graph action + terminal receipt. |
| Create | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewFirstWorldPublishSheet.test.tsx` | Own decision/dependency/confirm/retry/product-copy proofs. |
| Modify as needed | owning Graph Review stylesheet currently used by workbench | Minimal styling only; use existing tokens/layout. |

## 6.4 Backend tests

| Action | Path | Purpose |
|---|---|---|
| Modify | `tests/test_promotable_ingest_run.py` | Exact Build run preserves SourceArtifact W; legacy path remains explicit. |
| Modify | `tests/test_live_extract_promote_api.py` | API first-world prepare/confirm identity, unmanaged/existing/unreadable/foreign world failures, retries. |
| Create | `tests/test_reviewed_world_initialization.py` | Atomic staging, integrity, receipt, idempotency, race, failure cleanup, no fake legacy attestation. |
| Modify as needed | `tests/test_worldbuilding_write_plan.py` | Only if shared semantic-mapping helpers are factored/reused; existing BLD-10 behavior must remain green. |
| Modify (reconciled) | `tests/test_graph_memory_union_supergraph.py` | Prove structural store validation accepts sessionless `focus_session_id=""`. |

## 6.5 Handoff

| Action | Path | Purpose |
|---|---|---|
| Current handoff | `Docs/Plans/HANDOFF-INGEST-first-world-graph-from-reviewed-source.md` | Implementation/review authority. |

## 6.6 Expected unchanged authorities

These should remain unchanged unless a stop-condition reconciliation explicitly names why:

- `apps/live_control_server/routes/graph_preview.py` — extraction launch already correct;
- `apps/live_control_server/services/source_artifact_registry.py` — exact W already preserved;
- `apps/live_control_server/services/world_container_registry.py` — read for admission, do not widen ownership;
- `apps/live-control-ui/src/buildSurface/useBuildExtraction.ts` — extraction launch already exact;
- `apps/live-control-ui/src/buildSurface/BuildIngestToolbar.tsx` — handoff already exact;
- `src/graph_memory/extraction/worldbuilding_extraction_profile.py` — extraction ontology/profile is not this PR;
- `src/graph_memory/union_supergraph/model.py` unless the no-session stop condition genuinely requires a storage reconciliation;
- `apps/live_control_server/services/world_graph_bootstrap.py` — fixed Eldyrwild certified-bundle activation must stay fixed;
- static campaign maps / `WORLD_ID_BY_CAMPAIGN`;
- #565 Markdown reader and source writer;
- Hermes tooling;
- Playable Layer;
- statblock/resource publication.

## 6.7 Bounded discovery exception

```text
Directories:
  apps/live_control_server/services/
  apps/live-control-ui/src/planSurface/graphReviewWorkbench/
  src/graph_memory/kernel/
  tests/

Maximum additional paths: 4
Allowed kinds:
  - one tiny pure first-world plan/decision helper
  - one owning frontend integration test if the workbench has a different canonical test file
  - one kernel receipt/model helper
  - one test fixture/helper

Decision rule:
  path must establish/prove the same §1 first-world initialization invariant.
  It may not add existing-world merge, full correction UX, source navigation,
  campaign lifecycle, or another graph mutation authority.
```

If more than four additional paths are genuinely required, reconcile this handoff before review rather than silently consuming them.

---

# §7 Explicitly out of scope

Do not implement or claim:

- generic re-enabling of worldbuilding through `/extract-promote/prepare`;
- second-source merge into an initialized W;
- existing-world `bind_existing` review;
- rename extracted candidate;
- create missing graph object by hand;
- relationship editing;
- object merge/redirect UI;
- graph deletion/reset/reinitialize;
- automatic graph initialization when a world is created;
- automatic graph initialization when extraction finishes;
- graph initialization with zero accepted assertions;
- campaign creation inside W;
- static campaign-map mutation;
- local asset serving;
- source upload beyond existing paste import;
- new extraction kinds/profile ontology;
- object→source navigation;
- Hermes changes;
- Plan/Play surface changes;
- statblock generation/publication;
- legacy Eldyrwild bootstrap redesign;
- migration of existing Eldyrwild initialization receipts;
- fabricated or placeholder approval attestation;
- arbitrary filesystem world creation/adoption.

If one of these appears necessary merely to initialize W from the first reviewed source, return a stop report instead of expanding silently.

---

# §8 Evidence required to merge

Every material invariant clause is merge-blocking unless explicitly waived by the operator.

## 8.1 Evidence ledger

| Guarantee | Owning boundary | Required proof |
|---|---|---|
| Exact Build run preserves SourceArtifact W | run resolver | canonical run test with W=`the-glass-orchard`, campaign W, source lineage exact |
| No canonical Build fallback to Eldyrwild | run resolver/service | adversarial test with live Eldyrwild head + absent Glass Orchard head; target remains Glass Orchard |
| Managed-world gate | service | missing registry W fails before staging; unmanaged corpus directory is not adopted |
| Existing W is not first-published | service | readable existing head returns ineligible/409, unchanged head |
| Unreadable W is not treated absent | service | malformed world storage returns unreadable/block, no replacement |
| Exact workspace lineage is rechecked | service | SourceArtifact/workspace W or revision mismatch fails closed |
| Frozen source/evidence stays exact | existing review verifier + first prepare | tampered candidate/span/source digest blocks plan |
| Decisions are explicit/complete | plan builder | missing, duplicate, unknown candidate decision rejected |
| Relationship endpoints required | plan builder/UI | reject endpoint → edge cannot remain accepted |
| Zero accepted changes cannot initialize | prepare/confirm | no production W world directory/head |
| Prepare is inert | service | no graph/receipt mutation after successful prepare |
| Plan binds exact decisions + contribution digest | plan verifier | mutate decision/effect/digest → confirm rejects before publication |
| No fake bundle/Git attestation | reviewed initializer | reviewed receipt fields are run/source/decision authority; old bundle model untouched |
| Atomic initialization | Kernel | inject failure after baseline/merge/integrity in staging → production W absent |
| Production W appears only after verified staging | Kernel | successful confirm produces baseline + initial contribution + valid head/ledger |
| Evidence support survives initialization | Kernel | initialized graph integrity report has no unsupported accepted assertions |
| Rebuild equivalent | Kernel | rebuild from contributions equals initial head |
| Lost-response retry idempotent | confirm | same plan after commit → already_initialized, same contribution/head lineage, no duplicate |
| Foreign initialization race blocked | confirm | different W receipt/head appearing between prepare/confirm → 409, no merge reinterpretation |
| No mutation outside W | integration | Eldyrwild head/digest identical before/after Glass Orchard confirm |
| No source mutation | integration | source bytes/digest unchanged after review/confirm |
| No world-container mutation | integration | managed record/root unchanged after graph initialize |
| Sessionless stays semantically sessionless | Kernel/projection | no invented `session-*`; any technical empty focus never surfaces as playable session |
| UI only offers first publish when eligible | component/workbench | managed+absent exact run shows CTA; initialized/unmanaged/unreadable does not |
| UI keep/reject maps exactly | component | object/edge decisions match displayed state; no hidden defaults at submit |
| UI terminal receipt survives confirm ambiguity semantics | component | terminal success is never overwritten by refresh error; unknown result retries exact plan, not re-prepare with changed choices |
| Generic recap promote unchanged | regression | existing generic promote tests green |
| Existing BLD-10 existing-head confirm unchanged | regression | relevant worldbuilding write-plan tests green |
| Legacy Eldyrwild bootstrap unchanged | regression | initialization/bootstrap focused tests green |
| Frontend type/build | UI | `pnpm exec tsc -b && pnpm build` green |
| Diff/scope hygiene | repo | strict path list + `git diff --check` |

## 8.2 Required backend focused run

At minimum, from repo root, run the exact owning tests after implementation:

```bash
pytest -q \
  tests/test_promotable_ingest_run.py \
  tests/test_live_extract_promote_api.py \
  tests/test_reviewed_world_initialization.py \
  tests/test_worldbuilding_write_plan.py
```

Also include the smallest existing Kernel/legacy bootstrap tests that cover any factored `world_initialization.py` code. Discover and record exact filenames rather than guessing them away.

If factoring the transaction touches generic contribution merge/rebuild primitives, add their owning focused tests.

## 8.3 Required frontend focused run

From `apps/live-control-ui`:

```bash
pnpm exec vitest run \
  src/planSurface/graphReviewWorkbench/GraphReviewFirstWorldPublishSheet.test.tsx \
  <owning GraphReview exact-run/workbench tests> \
  src/api/<extract-promote owning test if present>
pnpm exec tsc -b
pnpm build
```

Record exact current filenames in the handback.

Do not omit the existing exact-run handoff tests if GraphReviewWorkbench composition changes.

## 8.4 Base failure protocol

For any required command already failing on base `0a6a1ab5ab0aab197ea16059ec20cd61dea16100`:

1. run/cite the same command or exact failing subset on base and HEAD;
2. state whether HEAD adds/removes/preserves failures;
3. do not call a non-green gate green;
4. request a fresh operator waiver for this PR if the failing row remains an acceptance gate;
5. waivers from #562/#564/#565 do not transfer.

## 8.5 Required live dogfood — Glass Orchard first graph

Use the actual CR01 world/source path, not a backend-only fixture.

Suggested material:

- World: `The Glass Orchard` (`the-glass-orchard`)
- Source: the Hesta / convention one-shot material already used in CR01 dogfood, or a similarly real one-shot source
- Include at least:
  - one named NPC/person;
  - one location;
  - one group/threat if available;
  - at least two source-backed relationships;
  - one deliberately rejectable/noisy candidate.

### Required GM journey

1. Start with a managed world W that has **no** World Graph.
2. In Build, open the committed rich source from PR #565.
3. Click `Extract`.
4. Open the exact run in Graph Review.
5. Confirm Graph Review visibly identifies the material as the first graph for **The Glass Orchard**, not Eldyrwild/campaign-debug metadata.
6. Inspect several objects/relationships with source evidence.
7. Reject at least one candidate.
8. Confirm any dependent relationship is also disabled/rejected when required.
9. Click the explicit create action.
10. Record the terminal receipt/outcome and committed revision.
11. Verify in-product result clearly says the World Graph was created for The Glass Orchard with the reviewed count.
12. Hard reload the review/source flow; confirm the world is now classified initialized and the first-publish CTA is no longer offered.
13. Confirm exact retry/reconciliation does not create another graph/contribution.
14. Restart live-control; confirm W remains initialized.
15. Confirm the source document is byte-identical to before publication.
16. Confirm the managed world registry record is unchanged.
17. Confirm Eldyrwild's head is unchanged.
18. Confirm no campaign/session was invented for the world-level source.

### Capture

Record:

```text
world_id W
workspace document D + revision
digest H
SourceArtifact A
ExtractionRun X
plan id/digest
decision digest
accepted/rejected candidate IDs
contribution ID + payload digest
baseline revision
initial committed revision
reviewed initialization receipt path/id
Eldyrwild head before/after
W state after restart
```

Screenshots of review + terminal receipt are strongly preferred because this is a GM-visible product milestone.

## 8.6 Adversarial live proof — no default-world leak

With Eldyrwild graph present and healthy:

```text
prepare/confirm Glass Orchard first graph
```

Must prove:

```text
Glass Orchard created/advanced
Eldyrwild head unchanged
no Eldyrwild contribution from this source
```

This is merge-blocking. It directly tests the defect motivating the slice.

---

# §9 Suggested nano-commit story

Implementation may discover slightly different file grouping, but keep each commit one proof story.

Recommended sequence:

1. `DOMAIN: preserve exact source world through promotable run`
   - `PromotableIngestRun.world_id`
   - canonical SourceArtifact/workspace cross-check
   - tests proving W != Eldyrwild

2. `KERNEL: atomically initialize reviewed world from one contribution`
   - reviewed authority/receipt
   - shared staging transaction refactor if needed
   - failure cleanup/idempotency tests
   - old bootstrap digest behavior unchanged

3. `API: prepare and confirm first-world reviewed graph`
   - exact run → managed W classifier
   - strict decisions → sealed plan
   - confirm/retry/race semantics
   - API tests

4. `UI: review first-world objects and relationships`
   - exact-run eligibility
   - keep/reject + dependency behavior
   - Create World Graph + terminal receipt
   - component/workbench tests

5. `DOGFOOD: prove Glass Orchard first graph`
   - checked-in handoff reconciliation/backlog notes only if repo convention requires
   - no generated dogfood artifacts need commit unless they are already expected by project convention

Avoid one giant “implement first-world graph” commit.

---

# §10 Stop conditions and required reconciliations

Stop and report before widening if any of these are true:

1. **No-session storage is not truthful.** A World Graph cannot be initialized without inventing a user-visible fake session. Reconcile the generic graph focus model first.
2. **Atomic transaction cannot be reused.** The only available route would duplicate the staging/rename/integrity algorithm from `world_initialization.py`. Refactor a shared primitive rather than copy it.
3. **Reviewed authority would require fake legacy attestation.** Do not put dummy/fake values in `approved_bundle_merge_sha` or equivalent.
4. **First-world candidate mapping secretly requires an existing graph.** If `create_new` materialization cannot be performed without head-based identity gating, isolate the minimal head-free worldbuilding mapper or return a design reconciliation. Do not create a production empty head just to run prepare against it.
5. **Graph Review cannot distinguish exact-run W from static campaign context.** Add a bounded exact-run world capability; do not mutate the global campaign map.
6. **Current source artifact lacks explicit managed-world lineage.** Do not infer from title/path/current UI. This source is not eligible for first-world publication.
7. **A newer branch owns this capability.** Stop rather than fork authority.

Any reconciliation must state:

- discovered fact;
- why the current invariant cannot be satisfied;
- smallest contract change;
- files/evidence added;
- what remains out of scope.

## 10.1 Reconciliation — sessionless `focus_session_id=""` (RC1)

**Discovered fact:** Empty technical baseline stores for world-level sources must use `focus_session_id=""`. Prior UnionSupergraph *store* validation treated empty string as missing (`bool("")` is false), so reviewed world initialization could not pass structural validation without inventing a fake `session-*` focus.

**Why the prior invariant could not be satisfied:** Handoff §4.9 forbids inventing a user-visible session for a world-level first source. Legacy Eldyrwild bootstrap uses a real focus session; first-world Glass Orchard has none. Keeping `bool(focus_session_id)` would force a fake session or block publication.

**Smallest contract change:** In `validate_union_supergraph_store_payload` only, require `isinstance(focus_session_id, str)` (including `""`). Do **not** relax representative-fixture acceptance (`validate_union_supergraph_fixture`), which still expects a non-empty focus match for Eldyrwild-shaped fixtures. Projection already treats falsy focus as “no session focus.”

**Files / evidence:**
- `src/graph_memory/union_supergraph/validate.py` — store-payload string check;
- `tests/test_graph_memory_union_supergraph.py` — empty baseline / `""` store-payload proof;
- `tests/test_reviewed_world_initialization.py` — sessionless receipt + store `focus_session_id==""`.

**Out of scope:** Changing `union_supergraph/model.py` field types; inventing a new focus enum; making empty focus pass representative-fixture acceptance; teaching product UI to display a playable “session” for `""`.

---

# §11 Required review handback

Every formal review begins with exactly one:

```text
Review Cycle N — PASS
```

or

```text
Review Cycle N — CHANGES REQUESTED
```

The handback must include:

1. Exact PR URL, branch, and head SHA.
2. Base `0a6a1ab5ab0aab197ea16059ec20cd61dea16100` or a deliberately reconciled replacement base.
3. §1 Mission and merge-ready invariant copied exactly.
4. Finding ledger from all prior cycles with open/closed status.
5. Nano-commit list and proof story.
6. Actual changed paths and whether every path is §6/declared bounded exception.
7. Backend/frontend commands and exact results.
8. Base/head comparison for any failure.
9. Dogfood result with Glass Orchard identifiers.
10. Adversarial no-default-world-leak result.
11. Operator waivers; `none` if none.
12. Stop conditions encountered/resolution; `none` if none.
13. Confirmation target W is derived from exact SourceArtifact/workspace lineage, never client/default campaign context.
14. Confirmation source bytes, workspace registry, and world-container registry are unchanged by graph publication.
15. Confirmation existing generic recap promote remains unchanged.
16. Confirmation legacy Eldyrwild bootstrap receipts/digests remain valid unchanged.
17. Confirmation no fake session was created.
18. Confirmation reviewed initialization authority contains no fabricated Git/bundle attestation.
19. Confirmation initialization is atomic and exact retry is idempotent.
20. Explicit statement of what CR-U4/U5 still remain false.

## Review posture

Review the user-visible outcome before admiring the transaction machinery.

Ask first:

> **Could a GM import a brand-new one-shot world, review its first extraction, and safely create that world's semantic memory without knowing anything about Eldyrwild, graph roots, bootstrap scripts, or revision IDs?**

A technically elegant answer that still requires manual world-graph setup is a failure.

---

# §12 Successor boundary

Do not automatically dispatch successors until this PR is dogfooded.

If first-world publication works, the next critical-path question becomes:

> **Can the GM cheaply correct the second extraction against what is already known?**

That is `CR02B`, expected to own:

- existing-world worldbuilding prepare/confirm through exact W;
- `bind_existing` / duplicate handling;
- reject/defer semantics;
- rename candidate before create;
- add missing object;
- relationship correction;
- no automatic graph rewrite before explicit confirm.

Then `CR02C` owns:

> **From a graph object, can the GM open the exact original source near the relevant passage?**

That should reuse PR #565's rich source reader plus existing SourceArtifact/span provenance rather than building another document reader.

The steward should re-evaluate after dogfood: if the first initialized graph is already unusable because extraction quality is poor, CR02B moves immediately ahead of navigation. If the graph is good enough but provenance navigation is the bigger friction, CR02C may come first.
