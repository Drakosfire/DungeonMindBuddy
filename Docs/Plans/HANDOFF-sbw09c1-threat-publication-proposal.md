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
  | Deterministic create/connect effects | proposal builder | exact assertion snapshots and digest replay tests | {{TODO}} |
  | Existing sealed-proposal authority is reused honestly | proposal adapter | seal/verify/reconstruct round-trip test | {{TODO}} |
  | Proposal is durable and replay-safe | proposal ledger | save/reload, replay, conflict, supersession tests | {{TODO}} |
  | Preparation is no-write | workflow boundary | graph/predecessor byte and head comparison | {{TODO}} |

  ## Scope and explicit deferrals
  - Design base: `35c3d34c6db44371cba81eb65883b2b76e011cad`
  - Dispatch base: {{TODO exact immutable main SHA after this handoff merges}}
  - Actual base/head: {{TODO}}
  - Actual changed paths: {{TODO}}
  - Paths outside §4: {{TODO: none or stop report}}
  - Deferred and still false: graph commit, receipt/recovery, verification, Workbench action, Hermes query/hydration, Threat projection, placement, and combat.

  ## Evidence produced
  {{TODO}}

  ## Gaps, waivers, and stop conditions
  {{TODO: none, or exact missing evidence / waiver / split}}
---

# HANDOFF — SBW09c1 exact durable Threat publication proposal

**Created:** 2026-08-01  
**Status:** ACTIVE — dispatch one no-write publication-proposal capability only after this authority merges.  
**Canonical path:** `Docs/Plans/HANDOFF-sbw09c1-threat-publication-proposal.md`  
**Design base:** `35c3d34c6db44371cba81eb65883b2b76e011cad`  
**Dispatch base:** the exact immutable `origin/main` SHA containing this handoff, recorded in the implementation PR body before code changes.  
**Suggested branch:** `feat/sbw09c1-threat-publication-proposal`

> SBW09c1 never writes the World Graph. SBW09c2 owns confirmation, the single governed Kernel commit, durable receipt/ambiguous-outcome recovery, and exact committed-revision verification.

## §0 Capability decomposition

| Outcome | Independently useful? | Durable/public contract? | Decision |
|---|---:|---:|---|
| Build exact create/connect assertions | Yes | No new graph schema | Include |
| Seal and durably reload one review proposal | Yes | Yes — Threat proposal ledger/API | Include |
| Confirm and commit | Yes | Commit contract | SBW09c2 |
| Persist receipt/recover ambiguous commit | Yes | Yes — receipt owner | SBW09c2 |
| Verify exact committed revision | Yes | Outcome semantics | SBW09c2 |
| UI, Hermes, projection | Yes | Separate product/consumer contracts | Later successors |

**Selected capability:** exact durable no-write Threat publication proposal.

**Why one slice:** effect construction, sealing, persistence, reload, replay, and supersession all establish one reviewable proposal identity. None changes campaign truth.

## §1 Mission and invariant

The live-control server can turn one exact ready Threat publication operation plus one exact active create-new or connect-existing identity resolution into one durable, deterministic, no-write publication proposal that seals the exact World Graph effects for review.

```text
One exact ready SBW09a operation plus one exact active non-refuse SBW09b
resolution can produce and durably reload at most one exact deterministic
proposal whose sealed accepted assertions represent only the intended Threat
identity, authored create-new fields, external statblock resource, and exact
immutable ThreatStatblockBinding against the operation's expected parent;
changed inputs, stale or superseded authority, refusal, collisions, storage
failure, and replay cannot mutate the World Graph or predecessor stores.
```

This is not one slice if implementation must commit a revision, persist a commit receipt, recover an ambiguous commit, verify a committed revision, modify Graph Kernel contribution semantics, change the existing sealed-proposal schema, or add a product management surface.

### Pre-dispatch critique

- Most likely failure: a superseded identity resolution or changed ordered inputs reuse an old proposal authority.
- Required detection: canonicalized effect snapshots, predecessor digest equality, replay-before-dependency-read, explicit supersession, and exact sealed-package verification.
- Easiest guarantee to under-test: no-write behavior across predecessor refresh, exact-parent inspection, storage failure, and API errors.
- Split trigger: any need to change `extract_promote_proposal.py`, Graph Kernel merge behavior, or introduce receipt/recovery.

## §2 Authority and boundaries

| Field | Authority |
|---|---|
| Reconciliation | `Docs/Reports/REPORT-sbw09c-publication-reanchor-2026-08-01.md` |
| Roadmap/tracker | active Threat roadmap and tracker synchronized with PR `#467` |
| Source/parent | merged SBW09a PR `#462` models/services/routes |
| Threat identity | merged SBW09b PR `#467` models/services/routes |
| Resource/binding | merged SBW08 PR `#457`; `statblock_binding.py` |
| Proposal seal | `src/graph_memory/extract_promote_proposal.py` |
| Contribution reconstruction | no-write resolver in `src/graph_memory/extract_promote_ops.py` |
| Graph reads | public `graph_memory.kernel` revision-pinned read APIs |
| Named successor | SBW09c2 commit/receipt/recovery/verify |

Read in this order:

1. `AGENTS.md` and external-agent PR-loop rules.
2. reconciliation report, tracker, roadmap, this handoff.
3. SBW09a operation models/service/tests.
4. SBW09b identity models/service/tests.
5. SBW08 binding model/helpers/tests.
6. `extract_promote_proposal.py` and no-write reconstruction in `extract_promote_ops.py`.
7. Kernel public contribution/assertion builders and exact revision reads.
8. current route registration.

No mutable ThreatDraft read, DMS call, accepted-mechanics mutation, graph write, current-head fallback, label fallback, or copied mechanics is permitted.

## §3 Observable paths

| Path | Required behavior | Owner |
|---|---|---|
| Prepare create-new | exact new Threat/authored fields/resource/binding proposal | service/ledger |
| Prepare connect-existing | resource + binding only; no existing Threat rewrite | service/ledger |
| Prepare refuse | typed refusal; no proposal storage | service |
| Stale/cancelled/superseded operation | reject through SBW09a; no repin | predecessor integration |
| Historical/superseded resolution | reject; only exact active resolution | predecessor integration |
| Same proposal ID + same request | return existing before dependency reads | ledger |
| Same proposal ID + changed request | conflict; bytes unchanged | ledger |
| Competing first proposals | exactly one active proposal | lock/ledger |
| Explicit replacement | atomic old/new supersession lineage | ledger |
| Restart/read | exact proposal/package/contribution IDs round-trip | parser/store |
| Corrupt ledger | fail closed; never auto-repair | parser/store |
| Exact-parent preflight | inspect immutable parent for endpoint/resource/binding collisions; no write | service/public read |
| API | stable labels/statuses; no internal path leaks | route |
| SBW09c2 consumption | consume exact package and revalidate predecessors; never reconstruct from current draft | durable contract |

## §4 Files in scope

| Action | Path |
|---|---|
| Create | `apps/live_control_server/models/threat_publication_proposal.py` |
| Create | `apps/live_control_server/services/threat_publication_proposals.py` |
| Create | `apps/live_control_server/routes/threat_publication_proposals.py` |
| Modify | `apps/live_control_server/main.py` |
| Create | `tests/test_threat_publication_proposal_models.py` |
| Create | `tests/test_threat_publication_proposals.py` |
| Create | `tests/test_threat_publication_proposal_api.py` |

Bounded test-only discovery exception:

```text
Directory: tests/
Maximum additional paths: 2
Allowed: existing shared predecessor fixture/helper or route-registration test
Rule: test-only reuse; no production scope
Report: exact path and why a local helper was insufficient
```

Any production change under `src/graph_memory/`, SBW09a/SBW09b models or ledgers, ThreatDraft/accepted-mechanics stores, UI, or corpus is a stop condition.

## §5 Explicit exclusions and demolition

Excluded: graph merge/write code, receipt/recovery, post-commit verification, UI, Hermes, projection, placement, combat, media, generic object publication, and changes to existing sealed-proposal code.

```text
Replaced path: none
Deleted in this PR: no
Retained reason: SBW09a, SBW09b, SBW08, and extract-promote remain authoritative predecessors
Named remaining consumer: existing extract-promote CLI/API remain unchanged
Required deletion owner: not applicable
```

## §6 Implementation contract

### §6.1 Request, proposal, ledger

Prepare request:

```text
schema: dmb_prepare_threat_publication_proposal_request_v1
proposal_id: UUID or bounded tpub_<token>
actor: nonblank bounded string
operator_note: optional bounded string
supersedes_proposal_id: optional exact active proposal ID
```

Route identity supplies `draft_id`, `operation_id`, and `resolution_id`. The canonical request digest includes those route identities plus every request field.

Durable proposal:

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
sealed_proposal_id          # exactly equals proposal_id
sealed_proposal_digest
sealed_proposal_version
sealed_proposal             # complete dmb_extract_promote_proposal_v1 package
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

Ledger:

```text
schema: dmb_threat_publication_proposal_ledger_v1
draft_id
operation_id
active_proposal_id
proposals: bounded immutable history
```

Storage:

```text
out/threat_publication_proposals/<draft_id>/<operation_id>/ledger.json
out/threat_publication_proposals/<draft_id>/<operation_id>/.proposal.lock
```

One atomic JSON replacement under one operation-scoped exclusive lock. Extra fields, unknown schema/version, impossible lineage, duplicate IDs, active-pointer mismatch, and package/digest disagreement fail closed.

### §6.2 Predecessor rules

- Refresh/read the exact SBW09a operation through its owner. It must remain `ready` and route IDs, source digest, world/campaign, accepted mechanics, and expected parent must match the proposal inputs.
- Read the exact SBW09b resolution through its owner. It must remain `active`; draft/operation/source/parent must equal SBW09a.
- `refuse` returns `publication_proposal_identity_refused` and writes no proposal.
- `create_new` uses only `created_node_id`.
- `connect_existing` uses only `selected_target.node_id` and preserves the complete candidate snapshot as review evidence. Label/alias/rank never resolves identity.
- Exact replay and changed-request conflict are decided from the proposal ledger before predecessor or graph reads.

### §6.3 Canonical effect construction

Canonicalize persisted source collections before assertion construction:

```text
intended_roles: trim, remove blanks, exact-dedupe, sort
tags: trim, remove blanks, exact-dedupe, sort
aliases: [exact source name] for create_new v1
```

All assertions use public `kernel.build_assertion`; all resource/binding IDs and validation use SBW08 helpers/models.

#### Create-new ordered effects

1. Threat node.
2. `description` attribute when nonblank.
3. `threat_kind` attribute when nonblank.
4. one `intended_role` attribute per canonical role.
5. one `tag` attribute per canonical tag.
6. external statblock resource node.
7. exact primary `uses_statblock` edge.

Threat node:

```text
subject_node_id: resolution.created_node_id
label: source_snapshot.name
kind: threat
role: first canonical intended role, else threat_kind, else threat
aliases: [source_snapshot.name]
source_domains: [worldbuilding]
identity_resolution_outcome: created_new
campaign_scope: source_snapshot.campaign_id
visibility: gm
epistemic_kind: fact
```

Attributes use predicates `description`, `threat_kind`, `intended_role`, and `tag`, with exact text and `source_domains:[worldbuilding]`.

#### Connect-existing ordered effects

1. external statblock resource node.
2. exact primary `uses_statblock` edge to `resolution.selected_target.node_id`.

No Threat node, alias, description, kind, role, tag, or unrelated relationship assertion is allowed.

#### Resource and binding

- Resource uses `external_statblock_node_id` and strict `ExternalResourceV1`; it contains logical statblock identity/contract only.
- Binding uses `compute_binding_id` and `edge_id_from_binding_id` with the exact six-field accepted mechanics locator.
- Initial role is `primary`; `phase_key=null`; `variant_label=null`.
- The reused proposal verifier requires every accepted node assertion to carry a nonblank `identity_resolution_outcome`: use `created_new` for both create-new node assertions and `matched_existing` for the connect-existing external-resource node. Attribute and edge assertions carry the same operation outcome for audit consistency.
- Recursive mechanics-body keys such as `definition`, `rules_elements`, rendered Markdown, assets, and equivalents are forbidden.

### §6.4 Provenance

Use deterministic virtual, non-absolute, non-secret authority locators:

```text
threat-publication-operation:<operation_id>
threat-publication://<world>/<campaign>/<draft>/<operation>

threat-publication-resolution:<resolution_id>
threat-publication://<world>/<campaign>/<draft>/<operation>/resolution/<resolution>
```

Threat/authored-field evidence uses `worldbuilding`; resource/binding evidence uses `statblock`. Evidence/source IDs are deterministic from operation, resolution, and effect kind and remain provenance-only for assertion identity.

### §6.5 Existing sealed-proposal adapter

Reuse `seal_promote_proposal`, `verify_promote_proposal`, and the existing no-write contribution reconstruction. Do not clone digest rules.

```text
proposal_id               <- exact Threat proposal_id
world_id                  <- operation.source_snapshot.world_id
parent_revision_id        <- operation.expected_parent_revision_id
source_revision_id        <- operation.source_digest
source_artifact_id        <- threat-publication-operation:<operation_id>
verified_source_uri       <- deterministic threat-publication:// operation URI
candidate_preview_id      <- resolution.resolution_id
candidate_schema          <- dmb_threat_publication_identity_resolution_v1
candidate_version         <- 1
contribution_meta.source_kind        <- identity_decision
contribution_meta.source_artifact_id <- same operation artifact
contribution_meta.source_revision_id <- operation.source_digest
contribution_meta.extraction_profile <- dmb_threat_publication_v1
contribution_meta.campaign_scope     <- source campaign_id
contribution_meta.authored_by        <- resolution.actor
accepted_proposals         <- exact ordered effects
rejected_assertions        <- []
unresolved_mentions        <- []
```

Identity map must use the existing proposal validator's vocabulary, not the SBW09b command names:

```text
identity_key = publication:<resolution_id>
node_id_map = {identity_key: exact threat_node_id}
identity_outcome_snapshot = {
  identity_key: created_new       # create_new
  identity_key: matched_existing  # connect_existing
}
```

For create-new, the Threat node assertion carries `identity_resolution_outcome=created_new`, so `verify_promote_proposal` checks the snapshot and node map directly. The external-resource node also carries `created_new` to satisfy the verifier's nonblank-node-outcome rule. For connect-existing, there is deliberately no Threat node assertion; the external-resource node carries `matched_existing`, and the proposal model independently verifies the exact selected target and snapshot.

Mutable-source verification is disabled only because SBW09a/SBW09b are the source authorities rather than a corpus file. Package digest, principal, parent, accepted payload, contribution metadata, node map, and identity snapshot verification remain enabled.

If current functions reject this honest mapping, require fake values, or require changes to `extract_promote_proposal.py`, stop for a generic sealed-effect contract predecessor. Do not weaken validation.

### §6.6 Exact-parent preflight

Load the exact expected revision through the public Kernel integrity read. Verify without mutation:

- create-new Threat ID is absent;
- connect target exists, is projectable Threat identity, and agrees with the persisted candidate snapshot;
- external resource ID is absent or exactly the same typed resource;
- deterministic binding edge is absent or exactly the same typed binding;
- an incompatible typed/untyped collision rejects.

This is review-time preflight, not proof a later commit will succeed. SBW09c2 revalidates everything against the same parent.

### §6A State/fallback matrix

| Condition | Prepare | Durable outcome | Retry |
|---|---|---|---|
| ready op + active create/connect + exact parent | seal/save proposal | one active proposal | exact replay |
| refusal | typed reject | none | new identity resolution |
| stale/cancelled/superseded op | typed reject | none except permitted SBW09a stale transition | explicit SBW09a retry lineage |
| resolution missing/superseded | typed reject | none | new active resolution |
| head advanced | parent mismatch/not-ready | none; never repin | explicit SBW09a retry |
| changed request same proposal ID | conflict | existing bytes unchanged | new ID |
| active proposal exists | busy unless exact supersession | unchanged | explicit replacement |
| dependency unavailable | 503 typed failure | none | retry same exact input |
| typed collision/integrity failure | fail closed | none | operator resolves authority |
| storage failure before replace | typed failure | no partial proposal | retry same exact input |
| response lost after replace | unknown to caller | exact proposal exists | exact replay recovers |

No fallback source exists.

### §6B Identity matrix

| Identity | Rule | Fallback |
|---|---|---|
| operation/resolution/proposal | exact IDs and digests | none |
| create-new Threat | exact persisted `created_node_id` | none |
| connect target | exact persisted selected candidate node ID/snapshot | none |
| label/alias/rank | review only | prohibited |
| resource/binding/edge | SBW08 deterministic full identity | none |
| proposal replay | exact ID + canonical request digest | none |
| supersession | exact current active proposal ID | none |
| deletion/rebinding | prohibited in c1 | none |

### §6C Persistence/replay matrix

| Operation | Guarantee |
|---|---|
| prepare/save | atomic bounded ledger replacement after all validation |
| exact replay | same durable record; no dependency read or duplicate history |
| changed replay | conflict; existing bytes unchanged |
| explicit supersession | old/new bidirectional lineage and active pointer change atomically |
| restart/read | exact package/digest/contribution/assertion identities reload |
| corrupt ledger | fail closed; no auto-repair/overwrite |
| rollback | no graph truth changed; historical proposal retained and supersedable |

### §6D Lock order

```text
proposal ledger lock
→ SBW09b identity read
→ SBW09a publication refresh/read
→ exact expected-parent World Graph read
```

Respect SBW09b's internal `identity → publication → projection` order. No predecessor may call back into proposal storage, and no proposal/identity lock may be acquired while holding a publication or graph lock in reverse order.

### §6E Commit declaration

```text
World Graph commit point: none.
Proposal durable point: atomic ledger replacement after full validation.
After write: one review proposal exists; campaign truth is unchanged.
Response loss: exact replay recovers the proposal.
```

### §6F Result labels and routes

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

Routes:

```text
POST /api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/identity-resolutions/{resolution_id}/proposals
GET  /api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/proposals/{proposal_id}
```

HTTP: created `201`; replay/read `200`; not found `404`; state/conflict/collision `409`; unavailable `503`; integrity `500`; validation `422`.

## §7 Verification and commands

| Guarantee | Boundary | Command |
|---|---|---|
| strict model/digest/ledger rules | model | `uv run pytest -q tests/test_threat_publication_proposal_models.py` |
| create/connect effects, persistence, replay, concurrency, no-write | service/ledger | `uv run pytest -q tests/test_threat_publication_proposals.py` |
| route labels/statuses | API | `uv run pytest -q tests/test_threat_publication_proposal_api.py` |
| SBW09b regression | predecessor | `uv run pytest -q tests/test_threat_publication_identity.py` |
| SBW08 regression | graph contract | `uv run pytest -q tests/test_statblock_binding_graph_contract.py` |
| sealed proposal regression | proposal owner | `uv run pytest -q tests/test_extract_promote_proposal.py tests/test_extract_promote_ops_atomic.py` |
| SBW09a regression | predecessor | discover and run the exact focused SBW09a test path named by its merged handoff before editing; record path/result |
| hygiene/scope | repository | `git diff --check`; `git diff --name-only <base>...HEAD` |

Required adversarial sequences:

1. Create-new prepare → restart → exact read/reconstruction.
2. Connect-existing proposal contains no Threat node/authored-field assertions.
3. Refuse creates no proposal path.
4. Head advances → predecessor stale/not-ready → no proposal/repin.
5. Resolution superseded → reject.
6. Exact replay after response loss → same record before dependency reads.
7. Changed request same ID → conflict and byte-identical ledger.
8. Two first proposals race → one active result.
9. Storage failure before replace → no partial ledger or graph/predecessor mutation.
10. Corrupt ledger → fail closed without overwrite.
11. Incompatible resource/binding collision at exact parent → no proposal.
12. Before/after graph head, revision bytes, ThreatDraft, accepted ref, and SBW09a/SBW09b ledgers are unchanged on success/failure, except SBW09a's permitted monotonic stale refresh.

Minimal live proof may call the backend route with real local data, restart, and read the same proposal. Do not build UI to satisfy proof.

For any baseline-red command, compare identical base/head commands and require an explicit waiver; do not call it green.

## §8 Required handback

Record exact base/head, changed paths, diff stat, every command/result and provenance, exact create/connect effect summaries, proof no graph write API was called, before/after head/store comparison, baseline failures/waivers, paths outside scope, stop conditions, and confirmation that SBW09c2 and later successors remain false.

## §9 Acceptance rubric

- [ ] Exactly one no-write proposal capability delivered.
- [ ] Only exact SBW09a/SBW09b authority is consumed.
- [ ] Create-new and connect-existing effects follow §6 exactly.
- [ ] Refuse/stale/superseded/mismatch/collision/unavailable/integrity paths produce no graph mutation.
- [ ] Existing proposal seal/verification is reused with honest identity vocabulary.
- [ ] Proposal, predecessor, parent, package, contribution, assertion, and lineage identities round-trip exactly.
- [ ] Replay is dependency-free and duplicate-safe; changed input conflicts.
- [ ] Persistence is atomic, bounded, path-safe, restart-safe, and corruption-closed.
- [ ] No copied mechanics, latest fallback, label identity, current-head substitution, or mutable-draft reconstruction exists.
- [ ] All guarantees are proved at owning boundaries and no unexpected path changed.
- [ ] SBW09c2 commit/receipt/recovery/verification remains unimplemented and unclaimed.

## §10 Reviewer attack list

- Search for a cloned proposal digest or weakened verifier.
- Verify `created_new` / `matched_existing` mapping, not `create_new` / `connect_existing`, inside the existing proposal identity snapshot.
- Confirm every node assertion carries the required nonblank identity outcome.
- Confirm sealed proposal ID equals Threat proposal ID.
- Confirm connect-existing cannot rewrite the Threat.
- Recursively search proposal/ledger/response payloads for copied mechanics.
- Force stale parent, superseded resolution, exact replay, changed replay, race, storage failure, and corruption.
- Verify no graph write, contribution record, receipt, or current-head repin.
- Audit lock order and route error/path leakage.
- Confirm all successor behavior remains absent.

## §11 Stop conditions

Stop if honest reuse of the current sealed proposal is impossible; a generic proposal/schema change is required; Graph Kernel or SBW09a/SBW09b schemas must change; exact-parent preflight is unavailable through public reads; safe preparation requires a graph/contribution write; connect-existing requires identity rewrite; commit/receipt/verification or UI is pulled in; a production path outside §4 is required; or an unwaived head-only test failure appears.

```text
Stop condition:
Why SBW09c1 cannot absorb it:
Owner/path inspected:
New durable contract:
Affected paths:
Required predecessor/successor slice:
Authority update/operator decision:
```

## Final dispatch check

- [ ] Handoff merged to main.
- [ ] Exact containing-main SHA recorded.
- [ ] Implementation branch starts from that SHA.
- [ ] Current predecessor contracts still match.
- [ ] §4 collision check complete.
- [ ] Every rubric claim maps to §7 proof.
- [ ] No essential constraint exists only in chat.