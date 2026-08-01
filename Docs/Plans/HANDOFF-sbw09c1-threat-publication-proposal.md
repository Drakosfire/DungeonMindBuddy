---
pr_body_template: |
  ## Outcome
  The live-control server can turn one exact ready Threat publication operation plus one exact active create-new or connect-existing identity resolution into one durable, deterministic, no-write publication proposal that seals the exact World Graph effects for review.

  ## Merge-ready invariant
  One exact ready SBW09a operation plus one exact active non-refuse SBW09b resolution can produce and durably reload at most one exact deterministic proposal whose sealed accepted assertions represent only the intended Threat identity, authored create-new fields, external statblock resource, and exact immutable ThreatStatblockBinding against the operation's expected parent; changed inputs, stale or superseded authority, refusal, collisions, storage failure, and replay cannot mutate the World Graph or predecessor stores.

  ## Evidence required to merge
  | Guarantee | Owning boundary | Required evidence | Result |
  |---|---|---|---|
  | Exact SBW09a/SBW09b mapping | proposal service | real predecessor-model integration matrix | {{TODO}} |
  | Deterministic create-new/connect-existing effects | proposal builder | exact assertion snapshots and digest replay tests | {{TODO}} |
  | Existing sealed-proposal authority is reused honestly | proposal adapter | seal/verify/reconstruct round-trip test | {{TODO}} |
  | Proposal is durable and replay-safe | proposal ledger | save/reload, same replay, changed-input conflict, supersession tests | {{TODO}} |
  | Preparation is no-write | workflow boundary | graph/predecessor byte and head comparison on success/failure | {{TODO}} |
  | Stale/refused/superseded authority fails closed | service/API | ordered predecessor-drift and resolution-state tests | {{TODO}} |

  ## Scope and explicit deferrals
  - Design base: `35c3d34c6db44371cba81eb65883b2b76e011cad`
  - Dispatch base: {{TODO exact immutable main SHA after this handoff merges}}
  - Actual base/head: {{TODO}}
  - Actual changed paths: {{TODO}}
  - Paths outside §4: {{TODO: none or stop report}}
  - Deferred and still false: graph commit, publication receipt, ambiguous-commit recovery, post-commit verification, Workbench action, Hermes query/hydration, Threat projection, placement, and combat.

  ## Evidence produced
  ### Automated
  {{TODO}}

  ### Adversarial
  {{TODO}}

  ### Regression
  {{TODO}}

  ### Manual / dogfood
  Not applicable to product UI in this slice. Record one real API preparation using an existing accepted Threat operation if the local environment has valid data; do not build a new management surface for proof.

  ## Gaps, waivers, and stop conditions
  {{TODO: none, or exact missing evidence / waiver / split}}
---

# HANDOFF — SBW09c1 exact durable Threat publication proposal

**Created:** 2026-08-01  
**Status:** ACTIVE — dispatch exactly one no-write publication-proposal capability after this authority merges and the dispatcher records the immutable main SHA.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw09c1-threat-publication-proposal.md`  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Design base:** `35c3d34c6db44371cba81eb65883b2b76e011cad`  
**Implementation dispatch base:** the exact immutable `origin/main` merge SHA containing this handoff; record it in the implementation PR body before code changes.  
**Suggested branch:** `feat/sbw09c1-threat-publication-proposal`

> This handoff is complete implementation authority for SBW09c1 only. It does not authorize a World Graph write.
>
> The next slice, SBW09c2, owns proposal-bound confirmation, the single governed Kernel commit, durable receipt and ambiguous-outcome recovery, and exact committed-revision verification.

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Public/durable contract changed? | User/operator surface changed? | Failure model changed? | Independently testable/revertible? | Decision |
|---|---:|---:|---:|---:|---:|---|
| Construct exact Threat/resource/binding effects | Yes | No new graph schema | No | Pure validation | Yes | Include |
| Seal a proposal using existing proposal-bound governance semantics | Yes | New Threat adapter contract | API only | proposal drift/integrity | Yes | Include |
| Durably save/reload/replay one proposal | Yes | Yes — proposal ledger | API only | storage/replay/supersession | Yes | Include |
| Confirm and commit the proposal | Yes | Commit route/outcome | Yes | stale parent/atomic failure | Yes | Successor SBW09c2 |
| Persist exact commit receipt and recover ambiguous outcome | Yes | Yes — receipt/recovery owner | Yes | response loss/restart | Yes | Successor SBW09c2 |
| Verify exact committed revision | Yes | No graph schema; distinct outcome semantics | Yes | committed-but-unverified | Yes | Successor SBW09c2 |
| Workbench publication action | Yes | UI workflow | Yes | UI retry/reload | Yes | Successor after backend authority |
| Hermes query/hydration | Yes | Consumer contract | Yes | zero/one/many binding | Yes | SBW10a |
| Compact/full Threat projection | Yes | Presentation contract | Yes | unresolved/multiple binding | Yes | SBW10b |

**Selected capability:** exact durable no-write Threat publication proposal.

**Why included rows share one invariant:** exact effect construction, sealing, and durable reload are all necessary for one reviewable proposal to remain the same proposal across process boundaries. None changes campaign truth.

**Named successors:** `SBW09c2`, Workbench publication action, `SBW10a`, `SBW10b`, `MAGIC-D3`, placement, and combat.

## §1 Mission

The live-control server can turn one exact ready Threat publication operation plus one exact active create-new or connect-existing identity resolution into one durable, deterministic, no-write publication proposal that seals the exact World Graph effects for review.

**Invariant**

```text
One exact ready SBW09a operation plus one exact active non-refuse SBW09b
resolution can produce and durably reload at most one exact deterministic
proposal whose sealed accepted assertions represent only the intended Threat
identity, authored create-new fields, external statblock resource, and exact
immutable ThreatStatblockBinding against the operation's expected parent;
changed inputs, stale or superseded authority, refusal, collisions, storage
failure, and replay cannot mutate the World Graph or predecessor stores.
```

**Mission falsification test**

```text
This is not one slice if implementation must commit a graph revision, persist a
commit receipt, recover an ambiguous commit, verify a committed revision, add a
Workbench management surface, change Graph Kernel contribution semantics, or
introduce a new generic proposal framework.
```

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed path? | Yes. Every path either constructs, seals, persists, reloads, supersedes, or rejects the same exact no-write proposal. |
| Most likely adversarial failure? | A proposal is prepared from one resolution, then a reordered tag/role list or superseded identity decision is treated as the same active authority, allowing later confirmation of effects the GM did not review. |
| Does §7 detect it? | Yes. Canonical-order replay tests, changed-predecessor conflicts, supersession sequences, and exact sealed-effect assertions are owning-boundary requirements. |
| Easiest boundary to under-test? | No-write behavior. A helper-level proposal test does not prove that predecessor refresh, exact-parent inspection, ledger failure, and route errors leave graph and predecessor stores untouched. |
| What forces a stop/split? | Needing a new generic proposal schema, modifying Kernel merge behavior, adding a commit/receipt, or semantically faking extract-promote source fields rather than providing an explicit mapping. |

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Reports/REPORT-sbw09c-publication-reanchor-2026-08-01.md`; active Threat roadmap and tracker; grounded authored-object lifecycle decision |
| Repository rules | `AGENTS.md`; `.cursor/rules/external-agent-pr-loop.mdc`; `.cursor/skills/external-agent-pr-loop/SKILL.md` |
| Design base | `35c3d34c6db44371cba81eb65883b2b76e011cad` |
| Dispatch base | Exact immutable main SHA containing this handoff, recorded before implementation |
| Predecessor contracts | Merged SBW09a PR `#462`; merged SBW09b PR `#467`; merged SBW08 PR `#457`; current sealed extract-promote proposal code |
| Exact input consumed | Route IDs, one ready `ThreatPublicationOperationV1`, one active `ThreatPublicationIdentityResolutionV1`, exact expected-parent revision, exact accepted mechanics locator, and a typed prepare request |
| Named successor | `SBW09c2` proposal-bound commit + receipt/recovery + exact verification |
| What remains false | No graph mutation, publication receipt, published Threat, Hermes discovery, mechanics hydration, Threat projection, placement, or combat integration |
| Explicit non-goals | UI, DMS call, ThreatDraft mutation, mechanics mutation, graph contribution merge, generic proposal redesign, query, projection, placement, combat, images |

Read authoritative inputs in order:

1. `AGENTS.md` and external-agent PR-loop rules.
2. `Docs/Reports/REPORT-sbw09c-publication-reanchor-2026-08-01.md`.
3. `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md`.
4. `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`.
5. `Docs/Plans/HANDOFF-sbw09a-publication-operation-ledger.md` and merged models/services/routes.
6. `Docs/Plans/HANDOFF-sbw09b-threat-identity-resolution.md` and merged models/services/routes.
7. `Docs/Plans/HANDOFF-pr457-sbw08-statblock-binding-contract.md` and `src/graph_memory/union_supergraph/statblock_binding.py`.
8. `src/graph_memory/extract_promote_proposal.py`.
9. `src/graph_memory/extract_promote_ops.py` proposal reconstruction and confirmation logic, as precedent only; do not call commit.
10. `src/graph_memory/kernel/contributions.py` public contribution/assertion builders.
11. `src/graph_memory/kernel/contribution_merge.py` only to understand future commit compatibility and exact-parent collision behavior.
12. Current route registration and focused predecessor tests.

### Authority precedence

```text
repository rules
→ active lifecycle decision and synchronized Threat roadmap/tracker
→ this handoff and its reconciliation report
→ merged SBW09a and SBW09b durable authority
→ merged SBW08 exact binding contract
→ existing sealed proposal contract
→ current Kernel public contribution contracts
→ superseded bundled SBW09 plans
→ chat summaries
```

If current main changes predecessor models, sealed proposal shape, route ownership, or lock order before dispatch, stop and re-anchor rather than adapting silently.

## §3 Observable-path inventory

| Observable path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| Prepare from ready create-new resolution | No proposal contract | Build exact create-new effects, seal, save, and return review artifact | Yes | proposal service/ledger |
| Prepare from ready connect-existing resolution | No proposal contract | Build only exact resource + binding effects; do not rewrite existing Threat | Yes | proposal service/ledger |
| Prepare from refusal | No contract | Typed refusal; no proposal file/ledger mutation | Yes | proposal service |
| Prepare from stale/cancelled/superseded operation | No proposal contract | Existing SBW09a refresh may mark stale; reject; no proposal | Yes | predecessor integration |
| Prepare from superseded/historical resolution | No proposal contract | Reject; only exact active resolution is eligible | Yes | predecessor integration |
| Prepare after graph head advances | No proposal contract | SBW09a exact-parent refresh rejects; never repin | Yes | predecessor integration |
| Exact proposal replay | No contract | Same proposal ID + canonical exact request returns existing proposal before new graph work | Yes | proposal ledger |
| Proposal ID reused with changed request | No contract | Typed conflict; existing proposal unchanged | Yes | proposal ledger |
| Competing first proposals | No contract | One active proposal per operation; loser receives busy/conflict | Yes | proposal ledger |
| Explicit replacement | No contract | New ID names exact active predecessor; old/new supersession links update atomically | Yes | proposal ledger |
| Read after restart | No contract | Exact operation/resolution/digests/effect package/contribution identity reload | Yes | proposal ledger |
| Read historical proposal | No contract | Return immutable prepared or superseded record; do not silently revalidate or mutate | Yes | proposal read service |
| Corrupt proposal ledger | No contract | Fail closed; no auto-repair or opportunistic overwrite | Yes | store/parser |
| Exact-parent preflight | No proposal contract | Inspect immutable expected parent for typed target/resource/binding collisions without mutation | Yes | service + public Kernel read |
| Route response | No route | Stable typed result labels and exact HTTP mapping | Yes | API route |
| Downstream confirmation | Could reconstruct effects | SBW09c2 consumes the exact sealed package and revalidates operation/resolution/parent; no reconstruction from current draft | Yes | durable public contract |

A `No` in the invariant column is a split trigger. There are none.

## §4 Files in scope — allowlist

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live_control_server/models/threat_publication_proposal.py` | Strict request/proposal/ledger/response contracts, IDs, digests, bounds, and invariants |
| Create | `apps/live_control_server/services/threat_publication_proposals.py` | Exact predecessor validation, effect construction, sealed-proposal adapter, exact-parent preflight, lock/persistence/replay/supersession |
| Create | `apps/live_control_server/routes/threat_publication_proposals.py` | Prepare/read API and typed HTTP mapping |
| Modify | `apps/live_control_server/main.py` | Register the new router only |
| Create | `tests/test_threat_publication_proposal_models.py` | Strict model, digest, canonicalization, and corruption matrix |
| Create | `tests/test_threat_publication_proposals.py` | Service, persistence, replay, concurrency, no-write, exact effects, and adversarial sequences |
| Create | `tests/test_threat_publication_proposal_api.py` | Route/status/response contract proof |

### Bounded discovery exception

```text
Directory: tests/
Maximum additional paths: 2
Allowed path kinds: an existing focused shared fixture/helper file used by both SBW09a/SBW09b tests, or a route-registration regression test
Decision rule: add only when reuse avoids duplicating a real predecessor fixture and the path remains test-only
Required report: name the path, why a new local helper was insufficient, and confirm no production scope was added
```

Any change under `src/graph_memory/kernel/`, `src/graph_memory/union_supergraph/`, `src/graph_memory/extract_promote_*`, `apps/live-control-ui/`, `corpus/`, or accepted-mechanics/ThreatDraft stores is a stop condition. Reusing existing imports is permitted; modifying those owners is not.

## §5 Files and capabilities explicitly out of scope

| Path or capability | Why this slice must not touch or claim it |
|---|---|
| `src/graph_memory/kernel/contribution_merge.py` and world-graph write code | SBW09c2 owns commit and recovery; c1 is no-write |
| `src/graph_memory/extract_promote_proposal.py` | Existing sealed proposal must be adapted as-is; needing changes indicates a generic-contract predecessor slice |
| `src/graph_memory/extract_promote_ops.py` | Existing confirmation is precedent; c1 must not call its commit path |
| SBW09a/SBW09b model or ledger schema | Predecessor authority is immutable for this slice |
| ThreatDraft and accepted mechanics stores | Exact source is read through SBW09a snapshot only |
| Workbench/UI publication controls | New product workflow is independently useful and belongs after backend authority |
| Hermes query/hydration and projection | SBW10a/SBW10b |
| Placement/combat/media | Later roadmap phases |
| General object-publication framework | One Threat capability first; generalization requires evidence from a second object type |

### Demolition declaration

```text
Replaced path: none — no prior Threat publication proposal owner exists
Deleted in this PR: no
If no, retained reason: SBW09a/SBW09b and extract-promote remain authoritative predecessors
Named remaining consumer: existing extract-promote CLI/API continue unchanged
Required deletion owner: not applicable
```

## §6 Implementation contract and conditional matrices

### §6.0 Public contract

#### Prepare request

```text
schema: dmb_prepare_threat_publication_proposal_request_v1
proposal_id: caller-supplied UUID or tpub_<bounded token>
actor: nonblank bounded string
operator_note: optional bounded string
supersedes_proposal_id: optional exact current active proposal ID
```

Route identity supplies `draft_id`, `operation_id`, and `resolution_id`; the request must not duplicate them.

#### Durable proposal

```text
schema: dmb_threat_publication_proposal_v1
proposal_id
request_digest
draft_id
operation_id
resolution_id
source_digest
resolution_request_digest
candidate_set_digest
expected_parent_revision_id
decision: create_new | connect_existing
threat_node_id
sealed_proposal_schema: dmb_extract_promote_proposal_v1
sealed_proposal_version
sealed_proposal_id
sealed_proposal_digest
sealed_proposal: complete package
expected_contribution_id
accepted_assertion_ids
effect_summary
state: active | superseded
supersedes_proposal_id
superseded_by_proposal_id
created_by
operator_note
created_at
updated_at
```

The model must verify internal equality between top-level predecessor identities and the sealed package's world, parent, contribution metadata, identity snapshot, proposal ID/digest, assertion IDs, and expected contribution ID. Extra fields fail closed.

#### Ledger

```text
schema: dmb_threat_publication_proposal_ledger_v1
draft_id
operation_id
active_proposal_id
proposals: bounded append-only history
```

Storage:

```text
out/threat_publication_proposals/<draft_id>/<operation_id>/ledger.json
out/threat_publication_proposals/<draft_id>/<operation_id>/.proposal.lock
```

The service owns one atomic JSON replacement under one operation-scoped exclusive lock. It must enforce path containment and distinguish unavailable storage from corrupt/impossible state.

#### Response labels

At minimum:

```text
publication_proposal_ready
publication_proposal_superseded
publication_proposal_identity_refused
publication_proposal_operation_not_ready
publication_proposal_resolution_not_active
publication_proposal_predecessor_mismatch
publication_proposal_parent_mismatch
publication_proposal_typed_collision
publication_proposal_busy
publication_proposal_input_conflict
publication_proposal_history_full
publication_proposal_not_found
publication_proposal_graph_unavailable
publication_proposal_storage_unavailable
publication_proposal_integrity_failure
```

#### Routes

```text
POST /api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/identity-resolutions/{resolution_id}/proposals
GET  /api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/proposals/{proposal_id}
```

HTTP mapping:

| Outcome | Status |
|---|---:|
| newly prepared proposal | 201 |
| exact replay / read | 200 |
| not found | 404 |
| refusal, not-ready, superseded resolution, busy, input conflict, changed predecessor, parent mismatch, typed collision, history full | 409 |
| graph/storage unavailable | 503 |
| integrity failure | 500 |
| request validation | 422 |

### §6.1 Exact predecessor mapping

| Predecessor field/outcome | Real shape | Proposal behavior | Transformation/proof |
|---|---|---|---|
| `ThreatPublicationOperationV1.operation_id` | bounded UUID/op token | exact ledger and proposal identity | equality assertion |
| `operation.source_snapshot` | strict immutable snapshot | sole authored field source | no ThreatDraft read |
| `operation.source_digest` | `sha256:<64 hex>` | top-level source identity and sealed source revision | exact copy |
| `operation.expected_parent_revision_id` | nonblank revision ID | sole proposal parent | exact copy; no current-head substitution |
| `operation.state` | ready/stale/cancelled/superseded | only ready is eligible | refresh through SBW09a owner |
| `resolution.resolution_id` | UUID/tres token | exact identity decision | exact copy |
| `resolution.request_digest` | `sha256:<64 hex>` | proposal predecessor identity | exact copy |
| `resolution.candidate_set_digest` | `sha256:<64 hex>` | reviewed-candidate identity | exact copy |
| `resolution.state` | active/superseded | only active is eligible | read exact record |
| `resolution.decision=create_new` | `created_node_id`, no selected target | exact new Threat endpoint | exact deterministic ID |
| `resolution.decision=connect_existing` | full `selected_target` snapshot | exact existing Threat endpoint | exact node ID; no label/alias fallback |
| `resolution.decision=refuse` | no usable endpoint | typed refusal | no ledger write |
| accepted mechanics ref | provider/statblock/revision/contract/version/digest | external resource + primary binding | SBW08 helper/model construction |

### §6.2 Exact effect construction

All assertions use public `kernel.build_assertion`; the service never creates ad hoc assertion IDs.

All generated collections are canonicalized before assertion construction:

```text
intended_roles: trimmed, blank removed, exact duplicates removed, sorted
tags: trimmed, blank removed, exact duplicates removed, sorted
aliases: one exact source name for create_new v1
```

#### Create-new sealed effects

Ordered accepted assertions:

1. Threat node assertion.
2. Authored description attribute when nonblank.
3. Threat-kind attribute when nonblank.
4. One intended-role attribute per canonical role.
5. One tag attribute per canonical tag.
6. External statblock resource node assertion.
7. Exact `uses_statblock` binding edge assertion.

Threat node:

```text
assertion_kind: node
subject_node_id: resolution.created_node_id
label: source_snapshot.name
campaign_scope: source_snapshot.campaign_id
epistemic_kind: fact
visibility: gm
identity_resolution_outcome: created_new
value:
  kind: threat
  role: first canonical intended role, else threat_kind, else threat
  aliases: [source_snapshot.name]
  source_domains: [worldbuilding]
  canon_state: canonical
  approval_state: accepted
```

Attribute assertions use stable predicates `description`, `threat_kind`, `intended_role`, and `tag`; their semantic value is `{attribute: <predicate>, text: <exact value>, source_domains: [worldbuilding], canon_state: canonical, approval_state: accepted}` plus explicit provenance.

#### Connect-existing sealed effects

Ordered accepted assertions:

1. External statblock resource node assertion.
2. Exact `uses_statblock` binding edge assertion to `resolution.selected_target.node_id`.

Connect-existing must not add or update a Threat node assertion, alias, description, kind, role, tag, or unrelated relationship. The selected candidate snapshot is sealed as identity review evidence, not re-materialized as current graph truth.

#### External resource

Use `external_statblock_node_id` and strict `ExternalResourceV1` fields from SBW08. No revision or digest belongs on the logical resource node.

#### Binding

Use `compute_binding_id` and `edge_id_from_binding_id` from SBW08. Initial publication role is exactly `primary`, with `phase_key=null` and `variant_label=null`. The six accepted-mechanics locator fields are copied exactly. No latest/preferred policy exists.

#### Provenance

The proposal may use virtual source artifact locators because SBW09a/SBW09b are durable server-owned authority rather than corpus prose. They must be deterministic, non-absolute, and non-secret.

```text
operation authority artifact:
  threat-publication-operation:<operation_id>
  threat-publication://<world_id>/<campaign_id>/<draft_id>/<operation_id>

identity authority artifact:
  threat-publication-resolution:<resolution_id>
  threat-publication://<world_id>/<campaign_id>/<draft_id>/<operation_id>/resolution/<resolution_id>
```

Create-new Threat/attribute evidence uses `worldbuilding`; external resource/binding evidence uses `statblock`. Evidence and source-artifact IDs must be deterministic from operation, resolution, and effect kind. Provenance fields must not change assertion semantic identity.

### §6.3 Existing sealed proposal adapter

SBW09c1 must reuse `seal_promote_proposal` and `verify_promote_proposal`; it must not clone their digest rules.

Required explicit mapping:

```text
world_id                 <- operation.source_snapshot.world_id
parent_revision_id       <- operation.expected_parent_revision_id
source_revision_id       <- operation.source_digest
source_artifact_id       <- threat-publication-operation:<operation_id>
verified_source_uri      <- deterministic threat-publication:// URI
candidate_preview_id     <- resolution.resolution_id
candidate_schema         <- dmb_threat_publication_identity_resolution_v1
candidate_version        <- 1
contribution_meta.source_kind       <- identity_decision
contribution_meta.source_artifact_id <- same operation artifact
contribution_meta.source_revision_id <- operation.source_digest
contribution_meta.extraction_profile <- dmb_threat_publication_v1
contribution_meta.campaign_scope     <- operation.source_snapshot.campaign_id
contribution_meta.authored_by        <- resolution.actor
accepted_proposals        <- exact ordered effects above
rejected_assertions       <- []
unresolved_mentions       <- []
node_id_map               <- {draft:<draft_id>: <exact threat_node_id>}
identity_outcome_snapshot <- {resolution_id: create_new|connect_existing}
prepared_by               <- request.actor
```

The service then calls existing proposal verification and contribution reconstruction with mutable-source verification disabled because predecessor validation is owned by SBW09a/SBW09b, not by a corpus-file digest. The reconstructed contribution ID and accepted assertion IDs are persisted in the Threat proposal and must agree on reload.

If this mapping is rejected by current proposal validation, requires fake non-authority values, or requires changing `extract_promote_proposal.py`, stop and propose the smallest generic sealed-effect contract slice. Do not weaken validation.

### §6A State and fallback matrix

| Path | Loading/initializing | Exact success | Ordinary miss | Dependency unavailable | Integrity failure | Stale/superseded | Retry/replay |
|---|---|---|---|---|---|---|---|
| Prepare | acquire proposal lock, check replay before dependency reads | active durable proposal | predecessor/proposal not found typed | graph/store 503; no proposal | fail closed 500 | reject 409; never repin | exact replay returns existing |
| Read | acquire proposal lock, parse exact ledger | exact historical proposal | 404 | store 503 | fail closed 500 | return persisted state, no auto-refresh | safe repeated read |
| Replace | exact active proposal required | old/new links and active pointer atomically replaced | named predecessor missing | store 503 | fail closed | wrong active predecessor conflicts | exact new request replays |
| Refuse decision | predecessor validation only | typed refusal | n/a | predecessor errors mapped | fail closed | n/a | no proposal created |

No fallback source is permitted. There is no ThreatDraft fallback, current-head fallback, label fallback, alias fallback, or reconstructed accepted-mechanics fallback.

### §6B Identity matrix

| Situation | Matching rule | Ambiguity behavior | Fallback? | Persistence consequence |
|---|---|---|---|---|
| Draft/operation/resolution | exact route ID equality | mismatch fails | No | no proposal |
| Create-new Threat | exact persisted `created_node_id` | absent/mismatch fails | No | sealed exact ID |
| Connect-existing Threat | exact selected candidate node ID and snapshot | absent/mismatch fails | No | sealed exact target |
| Label/alias | display/review only | never resolves identity | No | not an endpoint authority |
| External resource | SBW08 deterministic provider/resource ID | mismatch fails | No | exact logical resource assertion |
| Binding | SBW08 deterministic full semantic identity | mismatch fails | No | exact edge assertion |
| Proposal | exact proposal ID + canonical request digest | changed request conflicts | No | immutable history |
| Supersession | exact current active proposal ID | wrong/missing predecessor conflicts | No | atomic bidirectional lineage |
| Deletion/rebinding | prohibited | n/a | No | no deletion/rebinding in c1 |

### §6C Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay behavior | Compatibility/migration | Rollback |
|---|---|---|---|---|---|
| Prepare | proposal ledger v1 | exact model/serialized equality and verified sealed digest | same ID+request returns same record | v1 only; unknown schema fails closed | no graph state to roll back |
| Changed request with same ID | no write | existing bytes unchanged | typed conflict | no coercion | n/a |
| New proposal while active exists | no write unless explicit supersession | active pointer preserved | busy/conflict | n/a | n/a |
| Explicit supersession | one atomic ledger replacement | old/new IDs and timestamps round-trip | exact replay deduplicated | v1 lineage only | historical predecessor retained |
| Process restart | reload ledger | exact proposal/effect/contribution IDs survive | no new graph/predecessor read on ordinary read | no auto-migration | operator can prepare a new explicitly superseding proposal |
| Corrupt ledger | none | fail closed | never overwrite | manual recovery only; no silent repair | restore known-good file outside this slice |

### §6D Lock-order matrix

Required order:

```text
proposal ledger lock
→ SBW09b identity ledger read
→ SBW09a publication ledger refresh/read
→ exact expected-parent World Graph revision read
```

The implementation may realize SBW09b's existing internal order (`identity → publication → projection`) through its public service. It must not acquire an identity/proposal lock while already holding a publication or graph lock, and no predecessor service may call back into the proposal owner.

Exact replay should be checked from the proposal ledger before predecessor or graph reads, mirroring SBW09a/SBW09b. A changed request with an existing proposal ID also conflicts before dependency reads.

### §6E Commit-point declaration

```text
World Graph commit point: not applicable — this slice never calls a graph write API.
Proposal durable write point: atomic ledger replacement after all predecessor,
sealed-effect, exact-parent, and internal verification succeeds.
Before proposal write: no new durable c1 state exists.
After proposal write: one immutable review proposal exists; campaign truth is unchanged.
Post-write response failure: exact replay by proposal_id recovers the existing proposal.
```

## §7 Verification ownership map and commands

| Guarantee | Owning boundary | Command/scenario | Expected evidence |
|---|---|---|---|
| Strict proposal/ledger invariants | models | `uv run pytest -q tests/test_threat_publication_proposal_models.py` | valid/invalid/corrupt model matrix passes |
| Exact predecessor mapping and effects | service | `uv run pytest -q tests/test_threat_publication_proposals.py` | create/connect assertion snapshots and IDs match authority |
| Durable replay/supersession/restart | ledger/service | same command | exact round-trip, conflict, busy, replacement, history bound |
| No graph/predecessor mutation | workflow failure injection | same command | graph head/revision bytes, ThreatDraft, accepted ref, SBW09a/SBW09b ledgers unchanged except permitted SBW09a stale refresh |
| Exact-parent collision preflight | service + public Kernel read | same command | typed mismatches reject, identical typed resource/binding remain deterministic |
| Route/status contract | API | `uv run pytest -q tests/test_threat_publication_proposal_api.py` | exact statuses/labels/bodies |
| SBW09a regression | predecessor | `uv run pytest -q tests/test_threat_publication_operations.py` or the current exact SBW09a focused test path discovered at dispatch | no regression |
| SBW09b regression | predecessor | `uv run pytest -q tests/test_threat_publication_identity.py` | no regression |
| SBW08 contract regression | graph contract | `uv run pytest -q tests/test_statblock_binding_graph_contract.py` | no ID/schema/no-mechanics regression |
| Existing sealed proposal regression | governance contract | run current focused `extract_promote_proposal` and atomic confirm tests discovered at dispatch | existing proposal/confirm behavior unchanged |
| Route registration/build | application | `uv run pytest -q tests/test_live_control_server.py` if present, otherwise the current main import/route smoke test | app imports and routes register |
| Diff hygiene | repository | `git diff --check` and `git diff --name-only <base>...HEAD` | no whitespace errors or unexpected paths |

The worker must discover and record the exact existing SBW09a and extract-promote test filenames before editing; a renamed test is not permission to omit the proof. If no owning-boundary predecessor test exists, add no production scope—report the test gap and use the bounded test-only discovery exception.

### Required ordered adversarial scenarios

1. Prepare create-new; save; restart; read; sealed package and reconstructed contribution ID are exact.
2. Prepare connect-existing; verify there is no Threat node or authored-field assertion in the effect.
3. Prepare refusal; verify no proposal directory/ledger appears.
4. Advance graph head after SBW09a operation; prepare rejects through predecessor freshness and never repins.
5. Supersede the identity resolution before preparation; prepare rejects.
6. Reorder identical roles/tags in mutable test input upstream of snapshot construction; proposal semantic effect remains canonical only when the persisted source snapshot is identical; changed snapshot digest never reuses the proposal.
7. Repeat exact request after response loss; same proposal returns without graph read or duplicate history.
8. Reuse proposal ID with changed actor/note/supersedes input; conflict and byte-identical ledger.
9. Race two first proposals; exactly one active proposal is durable.
10. Inject storage failure before atomic replace; no partial ledger and no graph/predecessor mutation.
11. Corrupt the ledger; read and prepare fail closed without overwrite.
12. Place an incompatible typed object at the deterministic external resource/binding identity in the exact parent; prepare rejects typed collision without mutation.

### Minimal live proof

```text
Existing surface used: none required; backend authority only.
Smallest scenario: when valid local accepted-mechanics and publication-operation data exists, call the prepare endpoint once, inspect the exact review package, restart the server, and read the same proposal.
Initial state: one ready SBW09a operation and active create/connect SBW09b resolution.
Action: prepare proposal, restart, read proposal.
Expected observation: exact proposal/contribution/effects return; World Graph head is unchanged.
Evidence captured: request/response IDs and before/after graph head only; no secrets or mechanics body.
```

Do not build a UI, management panel, search view, or commit control to satisfy this proof.

### Baseline failure protocol

For every required command already failing on the dispatch base, run the identical command on base and head, preserve exact output, and state whether the PR adds a failure. No failing gate may be called green without an explicit operator waiver.

## §8 Required implementation handback

The PR body or handback must include:

1. Exact dispatch base SHA containing this handoff.
2. Head SHA.
3. Actual changed paths and focused diff stat.
4. Every §7 command/scenario and exact result.
5. Evidence provenance: author-local, independently rerun, CI, or manual.
6. Exact create-new and connect-existing effect summaries and assertion IDs from tests.
7. Proof that no graph write API was called.
8. Before/after graph head and predecessor-store comparison for success/failure paths.
9. Baseline failures and explicit waivers; `none` when absent.
10. Paths outside §4; `none` or stop report.
11. Stop conditions and deviations; `none` when absent.
12. Confirmation that SBW09c2 and every later successor remain false.
13. Confirmation that the authoritative handoff was implemented without compression or omitted constraints.

## §9 Acceptance rubric

- [ ] Exactly one capability—exact durable no-write publication proposal—was delivered.
- [ ] One exact ready SBW09a operation and one exact active non-refuse SBW09b resolution are the only predecessor authority.
- [ ] Create-new seals the exact Threat identity/authored fields, resource, and binding; connect-existing seals only resource and binding.
- [ ] Refuse, stale operation, superseded resolution, mismatch, typed collision, unavailable dependency, and integrity failure produce no proposal or graph mutation.
- [ ] Proposal identity, request digest, predecessor digests, expected parent, sealed digest, contribution ID, assertion IDs, and supersession lineage round-trip exactly.
- [ ] Existing sealed proposal hashing/verification is reused without weakening or cloning its rules.
- [ ] No copied mechanics, latest fallback, display-name identity, current-head substitution, or ThreatDraft reconstruction exists.
- [ ] Exact replay is dependency-free and duplicate-safe; changed input conflicts.
- [ ] Persistence is atomic, bounded, path-safe, restart-safe, and fail-closed on corruption.
- [ ] Every guarantee is proved at its owning boundary, including ordered concurrency and no-write sequences.
- [ ] No unexpected production path changed.
- [ ] Baseline failures and evidence provenance are truthful.
- [ ] SBW09c2 graph commit/receipt/recovery/verification remains unimplemented and unclaimed.

## §10 Reviewer protocol and skeptical attack list

Review the invariant before individual files.

1. Compare actual diff with §1, §3, §4, and §5.
2. Inspect whether the service invented a second proposal digest or bypassed `verify_promote_proposal`.
3. Verify the extract-promote field mapping is semantically explicit, not placeholder theater.
4. Confirm connect-existing cannot alter the reviewed Threat's identity fields.
5. Confirm create-new uses only the persisted SBW09a source snapshot and exact SBW09b created ID.
6. Search recursively for copied mechanics keys in request, proposal, assertion, ledger, and response models.
7. Force graph head movement, resolution supersession, exact replay, changed replay, storage failure, and ledger corruption.
8. Confirm no graph write, contribution record, receipt, or current-head repin occurs.
9. Verify canonical ordering of roles/tags and deterministic assertion/contribution identities.
10. Verify lock order and ensure no callback into an earlier lock owner.
11. Confirm all route statuses are typed and no raw exception leaks internal paths.
12. Confirm SBW09c2 remains a real independently useful successor rather than being partly implemented under helper names.

A green helper test is insufficient when the workflow, persistence, or route boundary owns the guarantee.

## §11 Stop conditions

Stop and report instead of widening scope when:

- existing sealed proposal functions cannot represent the exact Threat effect without fake or semantically false fields;
- a new generic proposal schema or change to `extract_promote_proposal.py` is required;
- Graph Kernel contribution/merge behavior must change;
- safe proposal preparation requires a graph write or contribution-record write;
- exact-parent collision inspection is unavailable through current public reads;
- predecessor state can only be reconstructed from mutable ThreatDraft/current head;
- connect-existing would need to rewrite identity fields to be useful;
- a commit receipt, ambiguous-commit recovery, or exact post-commit verification is pulled into c1;
- a UI surface is required merely to prove backend authority;
- a path outside §4 or its bounded test exception is required;
- required owning-boundary tests are red on head beyond base or need an unapproved waiver.

Use this stop report:

```text
Stop condition:
Why SBW09c1 cannot absorb it:
Current owner/path inspected:
New public/durable contract discovered:
Affected observable paths:
Required path outside scope:
Smallest predecessor or successor slice:
Tracker/authority update needed:
Operator decision required:
```

## Final dispatch check

- [ ] This handoff is merged to main.
- [ ] Dispatcher recorded the exact immutable main SHA containing it.
- [ ] Implementation branch starts from that SHA.
- [ ] Current main still matches SBW09a/SBW09b/SBW08 and proposal-governance mappings.
- [ ] §4 paths are collision-checked against open PRs.
- [ ] Every §6 matrix is complete.
- [ ] Every §9 claim maps to §7 proof.
- [ ] No essential constraint exists only in chat.