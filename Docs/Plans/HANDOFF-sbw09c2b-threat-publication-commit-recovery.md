---
pr_body_template: |
  ## Outcome
  The live-control server can explicitly confirm one exact active Threat publication proposal into at most one exact immutable World Graph revision, persist durable intent before mutation, recover an uncertain outcome from immutable revision authority, and return an exact verified or truthfully committed-unverified receipt without repinning or duplicating the graph write.

  ## Merge-ready invariant
  One exact active SBW09c1 proposal may be claimed by at most one durable SBW09c2b commit record. The record binds the proposal identity and digest, exact reconstructed contribution and source digest, expected parent, accepted assertion set, Threat identity, external resource, and immutable statblock binding. Intent is persisted before the Kernel call. Uncertain outcomes consult the SBW09c2a plural immutable-revision lookup before any retry. A known committed revision permanently forbids another merge. Verification is pinned to that immutable revision, and any verification failure remains committed-unverified rather than becoming retryable.

  ## Evidence required to merge
  | Guarantee | Owning boundary | Required evidence | Result |
  |---|---|---|---|
  | One proposal claim and at most one commit record | shared proposal lifecycle lock + commit store | confirmation/supersession/concurrent-confirm race matrix | {{TODO}} |
  | Intent before mutation and bounded attempts | commit service | injected intent-save, Kernel result, exception, and receipt-save sequences | {{TODO}} |
  | Honest immutable recovery | c2a integration | zero/one/many matches, head advance, rollback, and lookup failure | {{TODO}} |
  | Exact revision verification | verifier | manifest, contribution digest, replay manifest, support, Threat/resource/binding, rebuild, and projection matrix | {{TODO}} |
  | Committed-but-unverified honesty | record state machine + routes | failed/degraded verification and replay-with-zero-merge tests | {{TODO}} |

  ## Scope and explicit deferrals
  - Re-anchor base: `36def9e102c3e58f0ad00cd8ad7a4fbfe15de594`
  - SBW09c1 authority: PR `#478`, merge `c15420e6bc6bc9eca83933bf9982b233ff0fc3a7`
  - SBW09c2a authority: PR `#476`, merge `c6e867ed9ac04e4e92d87c4fcd1bbddef88f681a`
  - Implementation base: {{TODO exact immutable main SHA containing this re-anchored handoff}}
  - Actual base/head: {{TODO}}
  - Actual changed paths: {{TODO exact allowlist accounting}}
  - Deferred and still false: Workbench confirmation UI, Hermes query/hydration, Threat projection product card, placement, combat, mechanics revision adoption, undo/retraction, and generic object publication.

  ## Evidence produced
  {{TODO exact commands, results, provenance, merge-call counts, and baseline waivers}}

  ## Gaps, waivers, and stop conditions
  {{TODO: none, or exact stop report}}
---

# HANDOFF — SBW09c2b proposal-bound Threat commit, immutable recovery, and exact verification

**Created:** 2026-08-01  
**Status:** ACTIVE AUTHORITY CANDIDATE — replace the provisional handoff in draft PR `#474`, merge the re-anchor into main, then dispatch exactly one implementation capability from the resulting immutable merge SHA.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw09c2b-threat-publication-commit-recovery.md`  
**Re-anchor base:** `36def9e102c3e58f0ad00cd8ad7a4fbfe15de594`  
**Implementation base:** the exact immutable main SHA containing this handoff after the authority PR merges; record it before implementation begins.  
**Suggested implementation branch:** `feat/sbw09c2b-threat-publication-commit-recovery`

> This text supersedes the provisional design in draft PR `#474`. SBW09c1 and SBW09c2a are now merged. The implementation agent must consume their actual contracts described below rather than the earlier assumptions.

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Public/durable contract changed? | User or operator surface changed? | Failure model changed? | Independently testable or revertible? | Decision |
|---|---:|---:|---:|---:|---:|---|
| Claim one exact reviewed proposal | No | Yes | No | Yes | No | Include with commit safety |
| Persist intent before graph mutation | No | Yes | No | Yes | No | Include with recovery |
| Perform one exact-parent Kernel merge | Yes | Uses existing Kernel contract | Backend API only | Yes | No | Include |
| Recover uncertain response/process outcomes | Yes | Yes | Backend API only | Yes | No | Include |
| Verify the exact immutable Threat/resource/binding result | Yes | Yes | Backend API only | Yes | No | Include |
| Add GM-facing confirmation controls | Yes | Yes | Yes | Yes | Yes | Named successor |
| Query and hydrate the published Threat | Yes | Yes | Yes | Yes | Yes | SBW10a successor |
| Build the Threat projection card | Yes | Yes | Yes | Yes | Yes | SBW10b successor |
| Generalize publication to arbitrary object types | Yes | Yes | Yes | Yes | Yes | Reject from this slice |
| Add undo, retraction, or mechanics rebinding | Yes | Yes | Yes | Yes | Yes | Later successors |

**Selected capability:** one proposal-bound backend publication transaction that durably distinguishes uncommitted, unresolved, ambiguous, committed-unverified, and committed-verified outcomes while permitting at most one initial merge plus one tightly bounded recovery retry.

**Why the included rows share one invariant:** intent, graph mutation, recovery, and verification cannot be separated without creating a period where the application may duplicate a committed write or misreport a preview as durable truth. They are one at-most-once publication capability.

**Named successors:** Workbench confirmation UI; SBW10a query/hydration; SBW10b product projection; AOW03/AOW04 placement; COMBAT01/SBW15 live combat; mechanics revision adoption; retraction/undo; generic authored-object publication.

## §1 Mission and invariant

### Mission

```text
The live-control server can explicitly confirm one exact active Threat publication
proposal into at most one exact immutable World Graph revision and return a durable,
recoverable, revision-pinned publication receipt.
```

### Invariant

```text
For one exact active SBW09c1 proposal, at most one durable commit record may claim
it and at most one known World Graph publication may result. The record binds the
exact proposal, contribution, expected parent, Threat/resource/binding effect, and
immutable revision. Intent is durable before mutation. Every uncertain outcome is
reconciled through SBW09c2a before any retry. A known committed revision can never
become retryable, and verification is always pinned to that immutable revision.
```

### Mission falsification test

This is not one slice if implementation must also deliver a confirmation UI, identity reselection, mechanics mutation, parent repinning, generic publication, Graph Kernel write/CAS changes, placement, combat, or query/projection product work.

## §2 Re-anchor findings, authority, and boundaries

### §2.1 Current repository authority

| Concern | Actual authority |
|---|---|
| Current re-anchor base | `36def9e102c3e58f0ad00cd8ad7a4fbfe15de594` |
| Exact source and expected parent | SBW09a, merged PR `#462` |
| Exact Threat identity decision | SBW09b, merged PR `#467` |
| Exact reviewed no-write effect | SBW09c1, merged PR `#478`; merge `c15420e6bc6bc9eca83933bf9982b233ff0fc3a7` |
| Immutable operation→revision recovery | SBW09c2a, merged PR `#476`; merge `c6e867ed9ac04e4e92d87c4fcd1bbddef88f681a` |
| Resource/binding contract | SBW08, merged PR `#457` |
| Proposal seal verification | `graph_memory.extract_promote_proposal.verify_promote_proposal` |
| Exact contribution reconstruction | `graph_memory.extract_promote_ops.resolve_merged_contribution_from_package` |
| Graph mutation | `graph_memory.kernel.merge_contribution_to_revision` |
| Immutable lookup | `graph_memory.kernel.find_world_graph_revisions_by_operation_id` |
| Exact revision integrity | `graph_memory.kernel.load_world_graph_revision_with_integrity` |
| Pinned rebuild audit | `graph_memory.kernel.rebuild_from_contributions(compare_revision_id=..., publish=False)` |
| Revision-pinned projection | `graph_memory.kernel.project_world_graph` with `WorldGraphProjectionRequest.revision_pin` |
| Sequence authority | active Threat tracker and roadmap, amended with this handoff authority |

### §2.2 Actual SBW09c1 contract

The merged proposal authority stores:

```text
ThreatPublicationProposalV1
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
  sealed_proposal_id == proposal_id
  sealed_proposal_digest: sha256:<64 hex>
  sealed_proposal_version
  sealed_proposal
  expected_contribution_id
  accepted_assertion_ids
  effect_summary:
    decision
    threat_node_id
    external_resource_node_id
    binding_edge_id
    accepted_assertion_count
    authored_field_assertion_count
  state: active | superseded
  created_by
  ...
```

Proposal storage and lock:

```text
out/threat_publication_proposals/<draft_id>/<operation_id>/ledger.json
out/threat_publication_proposals/<draft_id>/<operation_id>/.proposal.lock
```

The merged service currently owns the private operation lock `_proposal_lock`, unlocked proposal-ledger helpers, and ledger-absent no-artifact fast paths. This slice must expose a semantic shared lifecycle seam and preserve c1 behavior.

The c1 response envelope permits `resolution_id=null` only when a GET/storage failure has no honest resolution identity. Persisted proposals always carry an exact non-null `resolution_id`.

### §2.3 Actual SBW09c2a contract

```python
kernel.find_world_graph_revisions_by_operation_id(
    root: Path,
    world_id: str,
    operation_id: str,
) -> tuple[WorldGraphRevision, ...]
```

Required caller assumptions:

- the result is plural zero/one/many and ordered by `(created_at, revision_id)`;
- every enumerated immutable manifest is inspected once from one revision-ID snapshot;
- current head, ancestry, head advance, and rollback do not filter matches;
- manifest `world_id` and `revision_id` are bound to their storage identities and mismatch fails closed;
- missing, malformed, corrupt, or unreadable authority propagates failure;
- the call performs no durable writes;
- c2b may never choose the first match.

### §2.4 Actual Kernel merge behavior that governs recovery

```python
kernel.merge_contribution_to_revision(
    root: Path,
    *,
    world_id: str,
    contribution: GraphContribution,
    expected_parent_revision_id: str | None,
) -> ContributionMergeResult
```

Important current behavior:

- expected-parent admission occurs before the Kernel's idempotent-noop check;
- successful publication writes `operation_ids=[contribution.contribution_id]` into the immutable revision manifest;
- `published=False` is a typed deterministic result, not proof that no immutable revision exists until c2a reconciliation completes;
- exceptions may occur before or after durable graph effects and therefore require c2a reconciliation;
- the contribution ledger may be written before revision publication, so application recovery must use immutable revision authority rather than contribution-record existence;
- current head is never sufficient proof of which revision contains this publication.

### §2.5 Exact reconstruction principal

The c1 sealed package was prepared and verified with `proposal.created_by`. The c2b confirmation request's `actor` is the commit confirmer and may differ.

Therefore c2b must reconstruct the exact contribution using:

```text
confirming_principal = proposal.created_by
```

It must not use the c2b request actor as the package principal. The request actor is recorded only as commit audit identity.

### §2.6 Authority precedence

```text
1. Repository architecture and lifecycle decisions
2. Active Threat tracker and roadmap after this re-anchor merges
3. This checked-in handoff
4. Merged c1/c2a implementation and owning-boundary tests
5. Other repository implementation and tests
6. Project Sources, attached documents, and chat summaries
```

Read in order before changing code:

1. `AGENTS.md`, `.cursor/rules/external-agent-pr-loop.mdc`, and the external-agent PR-loop skill.
2. Active Threat tracker, roadmap, publication re-anchor report, and this handoff.
3. Merged c1 models/service/routes/tests and PR `#478` review history.
4. Merged c2a function/export/tests and PR `#476` review history.
5. SBW09a/SBW09b models, services, and tests.
6. SBW08 binding helpers/models/tests.
7. `extract_promote_proposal.py` and `resolve_merged_contribution_from_package`.
8. Public Kernel merge, revision, integrity, rebuild, and projection APIs.
9. Generic extract-promote confirmation only as precedent; do not copy current-head or idempotent-noop shortcuts.

### §2.7 Locked boundaries

- The exact active c1 proposal is complete content authority.
- SBW09a remains source and expected-parent authority at new admission and before the one allowed zero-match retry.
- SBW09b remains Threat identity authority at new admission and before the one allowed zero-match retry.
- The confirmation request confirms; it cannot select assertions, identity, parent, world root, mechanics, resource, or binding.
- The Kernel alone owns graph mutation and immutable revision publication.
- The c2b commit record owns application intent, outcome, recovery status, and verification status.
- c2a alone owns complete operation-ID lookup over immutable revisions.
- Current head is used only for pre-intent parent admission and deciding whether a zero-match unresolved attempt may retry once. It is never committed-revision proof.
- If the implementation base moves and any actual contract above changes materially, stop and re-anchor rather than guessing.

## §3 Observable-path inventory

| Observable path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| Confirm active create-new proposal | No commit path | Intent → exact merge → receipt → pinned verification | Yes | commit service |
| Confirm active connect-existing proposal | No commit path | Resource+binding commit only; no Threat identity rewrite | Yes | commit service/verifier |
| Exact successful replay | Proposal only | Return durable terminal record before predecessor/graph reads | Yes | commit ledger/service |
| Committed-unverified replay | No receipt | Verification only; zero merge calls | Yes | commit service |
| Same commit ID, changed request | No contract | Conflict; bytes unchanged | Yes | commit ledger |
| Different commit ID for claimed operation | No contract | Busy/conflict; no second record or merge | Yes | commit ledger |
| Proposal supersession races confirmation | No shared claim | Exactly one wins under one lifecycle lock | Yes | shared lifecycle lock |
| Refused/superseded proposal | Proposal state only | No intent and no graph call | Yes | admission |
| Stale/cancelled operation | Proposal may preexist | No intent and no graph call | Yes | predecessor admission |
| Superseded/missing resolution | Proposal may preexist | No intent and no graph call | Yes | predecessor admission |
| Parent changed before intent | No commit path | Parent mismatch; no commit record | Yes | admission |
| Crash after intent before/around merge | No recovery | c2a first; one conditional exact retry maximum | Yes | recovery state machine |
| Deterministic `published=False` | No receipt | Reconcile once; zero match → terminal uncommitted; no retry | Yes | commit service |
| Exception/malformed Kernel result | No receipt | c2a before any retry/classification | Yes | recovery state machine |
| Commit succeeds, receipt save fails | No recovery | Restart finds exact immutable revision; no second merge | Yes | c2a + commit store |
| Head advances after commit | No recovery | Exact immutable revision still recovered | Yes | c2a |
| Head rolls back after commit | No recovery | Exact immutable revision still recovered | Yes | c2a |
| Multiple matching revisions | No policy | Persist ambiguity; never first-win | Yes | recovery state machine |
| Lookup unavailable/corrupt | No policy | Remain committing; no merge | Yes | recovery state machine |
| Verification unavailable/degraded | No receipt | Persist committed-unverified; no merge retry | Yes | verifier/store |
| Verification mismatch | No receipt | Persist committed-unverified/failed; no merge retry | Yes | verifier/store |
| Restart GET | No commit endpoint | Exact record round-trip | Yes | store/route |
| Missing commit GET | No endpoint | Typed 404 with no storage creation | Yes | route/store |
| Corrupt commit ledger | No ledger | Fail closed; no repair or overwrite | Yes | parser/store |
| UI/Hermes/projection card/placement/combat | Absent | Remain absent | Yes | successors |

## §4 Files in scope — exact allowlist

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live_control_server/models/threat_publication_commit.py` | strict request, commit record, ledger, response, state/result contracts |
| Create | `apps/live_control_server/services/threat_publication_commit_store.py` | path-safe atomic commit-ledger storage; no independent lock |
| Create | `apps/live_control_server/services/threat_publication_commits.py` | admission, intent, merge, recovery, receipt, and verification orchestration |
| Create | `apps/live_control_server/routes/threat_publication_commits.py` | POST confirmation and GET exact record |
| Modify | `apps/live_control_server/services/threat_publication_proposals.py` | expose shared lifecycle lock/helpers; detect commit claim; block supersession; preserve honest fast paths |
| Modify | `apps/live_control_server/main.py` | mount c2b routes only |
| Create | `tests/test_threat_publication_commit_models.py` | strict model and state invariants |
| Create | `tests/test_threat_publication_commits.py` | service, store, concurrency, crash, recovery, and verification sequences |
| Create | `tests/test_threat_publication_commit_api.py` | route/status/result/no-artifact contracts |
| Modify | `tests/test_threat_publication_proposals.py` | proposal replay/supersession/orphan-authority behavior after commit claim |

**Bounded discovery exception**

```text
Directory: tests/
Maximum additional paths: 2
Allowed path kinds: existing shared fixture/helper or route-registration test only
Decision rule: include only when reproducing an owning-boundary sequence cannot be done locally without duplicating an existing fixture contract
Required report: exact path, reason, and why a local fixture was insufficient
```

No production discovery exception exists. If another production path is required, stop and report it.

## §5 Explicitly out of scope

| Path, layer, or capability | Why excluded |
|---|---|
| `src/graph_memory/**` changes | c2b must consume the merged public Kernel; any required Kernel change is a predecessor slice |
| SBW09a/SBW09b models or ledgers | source and identity authority are frozen predecessors |
| ThreatDraft or accepted-mechanics stores | the c1 proposal is complete content authority |
| `extract_promote_proposal.py` / `extract_promote_ops.py` changes | reuse existing seal/reconstruction semantics; modification is a stop condition |
| DungeonMind provider/client | mechanics generation is not publication |
| UI code | confirmation UI is a successor after backend proof |
| Hermes/query/hydration | SBW10a |
| Product Threat projection | SBW10b |
| Placement/canvas/embed | SBW11, SBW12, AOW03, AOW04 |
| Combat persistence/runtime | COMBAT01, SBW15 |
| Generic authored-object publication | requires a separate generalization proof |
| Undo/retraction/superseding a committed publication | separate lifecycle contract |
| Mechanics revision adoption/rebinding | later explicit governed operation |

Nearby work is not authorization.

**Demolition declaration**

```text
Replaced path: no prior Threat-specific commit path exists
Deleted in this PR: no
Retained reason: generic extract-promote confirmation remains an independent consumer
Named remaining consumer: Graph Review / generic extract-promote workflows
Required deletion owner: none; later consolidation requires its own reviewed capability
```

## §6 Public and durable contract

### §6.1 Commit identity and confirmation request

Commit IDs accept canonical UUIDs or:

```text
tcommit_<1..128 safe token characters>
```

Request:

```text
schema: dmb_confirm_threat_publication_request_v1
commit_id: UUID or bounded tcommit_<token>
sealed_proposal_digest: exact persisted c1 value including sha256: prefix
expected_parent_revision_id: exact persisted c1 parent
actor: nonblank bounded commit confirmer
operator_note: optional bounded string
```

Route identity supplies `draft_id`, `operation_id`, and `proposal_id`.

Canonical request digest includes:

```text
draft_id
operation_id
proposal_id
commit_id
sealed_proposal_digest
expected_parent_revision_id
actor
operator_note
```

The request must not accept:

- `resolution_id`
- `assertion_ids` or assertion subset
- `world_id`, `campaign_id`, or `world_root`
- Threat/target/resource/binding IDs
- mechanics locator or mechanics body
- new/replacement parent
- `dry_run`
- `allow_live_world`
- idempotency policy
- retry policy

### §6.2 Durable commit record

```text
schema: dmb_threat_publication_commit_v1
commit_id
request_digest

draft_id
operation_id
proposal_id
proposal_request_digest
sealed_proposal_digest
sealed_proposal_version

resolution_id
source_digest
resolution_request_digest
candidate_set_digest
world_id
campaign_id
expected_parent_revision_id

expected_contribution_id
expected_contribution_source_payload_sha256   # raw lowercase 64-hex Kernel digest
accepted_assertion_ids                        # exact ordered c1 list

decision: create_new | connect_existing
threat_node_id
selected_target: ThreatIdentityCandidateV1 | null
external_resource_node_id
binding_id
binding_edge_id

state: committing | uncommitted | ambiguous | committed_unverified | committed_verified
merge_attempt_count: 1 | 2
committed_revision_id: string | null
recovered_via_operation_lookup: bool
verification_status: not_started | passed | degraded | failed
verification_codes: bounded ordered unique list
warnings: bounded ordered unique list

created_by                            # c2b request actor, not proposal principal
operator_note
created_at
updated_at
```

The record is constructed only after:

- exact proposal verification and contribution reconstruction;
- exact c1/c2a/predecessor checks;
- exact effect extraction;
- contribution source digest computation;
- current-head parent admission.

The record never copies the sealed proposal or mechanics body. It binds the c1 authority by IDs and digests.

Record invariants:

- route IDs and proposal IDs are exact and path-safe;
- `proposal_request_digest == proposal.request_digest`;
- `sealed_proposal_digest == proposal.sealed_proposal_digest`;
- `expected_contribution_id == proposal.expected_contribution_id`;
- `accepted_assertion_ids == proposal.accepted_assertion_ids` in exact order;
- `external_resource_node_id == proposal.effect_summary.external_resource_node_id`;
- `binding_edge_id == proposal.effect_summary.binding_edge_id`;
- decision, `threat_node_id`, counts, and effect shape agree with the reconstructed contribution;
- create-new requires `selected_target=null`;
- connect-existing requires the exact persisted `ThreatIdentityCandidateV1` snapshot from the active resolution;
- `committing`, `uncommitted`, and `ambiguous` require `committed_revision_id=null`;
- `committed_unverified` and `committed_verified` require a nonblank exact revision ID;
- `committed_verified` requires `verification_status=passed`;
- `committed_unverified` permits `not_started`, `degraded`, or `failed` only;
- noncommitted states require `verification_status=not_started`;
- `recovered_via_operation_lookup=true` requires a committed revision;
- no state transition can reduce `merge_attempt_count` or remove a known committed revision;
- no record can transition from committed to any noncommitted state.

### §6.3 Commit ledger and storage

Ledger:

```text
schema: dmb_threat_publication_commit_ledger_v1
draft_id
operation_id
commit: ThreatPublicationCommitV1
```

Storage:

```text
out/threat_publication_commits/<draft_id>/<operation_id>/ledger.json
```

There is no empty persisted ledger and no `.commit.lock`.

Rules:

- file absence means no commit claim;
- any valid ledger contains exactly one commit record;
- one operation has at most one commit record in v1;
- the record permanently claims its proposal and operation, including terminal uncommitted or ambiguous states;
- a new parent requires a new SBW09a operation, resolution, and proposal;
- save uses one atomic JSON replacement;
- schema, route identities, request digest, state invariants, bounds, unknown fields, and malformed JSON fail closed;
- corrupt storage is never repaired or overwritten automatically;
- a failed atomic replacement must leave prior valid bytes intact.

### §6.4 Response envelope

```text
schema: dmb_threat_publication_commit_response_v1
draft_id
operation_id
proposal_id: string | null
commit_id
result_label
commit: ThreatPublicationCommitV1 | null
retry_allowed: bool
message: string | null
```

`retry_allowed` means only that the service may still make its one internally governed zero-match recovery retry on a future exact replay. It never authorizes a caller-selected second contribution, parent, proposal, or merge policy.

Minimum result labels:

```text
publication_commit_verified
publication_commit_committed_unverified
publication_commit_recovery_pending
publication_commit_uncommitted
publication_commit_outcome_ambiguous
publication_commit_proposal_not_active
publication_commit_operation_not_ready
publication_commit_resolution_not_active
publication_commit_predecessor_mismatch
publication_commit_parent_mismatch
publication_commit_busy
publication_commit_input_conflict
publication_commit_not_found
publication_commit_graph_unavailable
publication_commit_storage_unavailable
publication_commit_integrity_failure
```

### §6.5 Routes and HTTP mapping

```text
POST /api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/proposals/{proposal_id}/commits
GET  /api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/commits/{commit_id}
```

| Outcome | HTTP |
|---|---|
| first request reaches `committed_verified` | `201` |
| first request reaches `committed_unverified` | `201` |
| exact replay/recovery/GET of committed state | `200` |
| recovery pending due unavailable/corrupt lookup dependency | `503` |
| missing GET | `404` |
| uncommitted, ambiguous, inactive, stale, busy, parent mismatch, changed input | `409` |
| request validation | `422` |
| graph/storage dependency unavailable before truth can be established | `503` |
| corrupt durable authority or integrity contradiction | `500` |

Committed-unverified is a success-shaped receipt with exact revision ID and `retry_allowed=false`. It is never a generic error that invites another commit.

GET for a never-created commit must not create the commit directory, proposal directory, or lock file.

## §7 Shared lifecycle lock and c1 integration

### §7.1 Required semantic seam

Modify the merged c1 service to expose these exact semantics; names may vary only if the implementation handback maps them explicitly:

```python
@contextmanager
def threat_publication_lifecycle_lock(
    root: Path,
    draft_id: str,
    operation_id: str,
) -> Iterator[None]: ...


def load_threat_publication_proposal_ledger_unlocked(...) -> ThreatPublicationProposalLedgerV1 | None: ...


def find_threat_publication_proposal(
    ledger: ThreatPublicationProposalLedgerV1,
    proposal_id: str,
) -> ThreatPublicationProposalV1 | None: ...
```

The semantic lock must use the existing c1 lock path:

```text
out/threat_publication_proposals/<draft_id>/<operation_id>/.proposal.lock
```

The commit store exposes dependency-neutral helpers equivalent to:

```python
def threat_publication_commit_ledger_exists(...) -> bool: ...
def load_threat_publication_commit_ledger_unlocked(...) -> ThreatPublicationCommitLedgerV1 | None: ...
def save_threat_publication_commit_ledger_unlocked(...) -> None: ...
```

The commit store must not import the proposal service and must not acquire a lock.

### §7.2 Lock order

```text
Threat publication lifecycle lock
→ proposal ledger unlocked read
→ commit ledger unlocked read/write
→ SBW09b identity read
→ SBW09a publication refresh/read
→ public Kernel head/revision/merge/rebuild/projection APIs
```

No predecessor or Kernel path may call back into proposal or commit storage. No second application lock may reverse this order.

### §7.3 Proposal behavior after commit authority exists

Within c1 `prepare_threat_publication_proposal`:

- exact replay of an already persisted proposal ID remains unchanged and occurs before new-proposal admission;
- once any valid commit record exists, no different proposal may be created and no active proposal may be superseded;
- refusal should return `publication_proposal_busy` with an explicit commit-claim message rather than inventing a new c1 result label;
- a commit ledger without the matching proposal ledger/proposal is an integrity failure;
- proposal and commit route identities must agree;
- a terminal uncommitted commit record still blocks c1 supersession; v1 recovery is a new operation, not proposal reuse.

### §7.4 Honest no-artifact fast paths

The c1 ledger-absent fast paths added in PR `#478` remain valid only when both authorities are absent:

```text
proposal ledger absent AND commit ledger absent
```

If a commit ledger exists, c1 prepare/read must enter the shared lifecycle lock and load both authorities. It must not return a no-proposal/refusal fast path that hides an orphaned or corrupt commit claim.

### §7.5 Serializable supersession/confirmation race

- supersession wins the lifecycle lock and persists first → c2b observes the named proposal is not active and writes no intent;
- c2b wins and persists any commit record → c1 supersession is refused permanently;
- a superseded proposal can never also own a commit record;
- concurrent first confirmations can produce at most one durable record and at most one initial Kernel merge call.

Holding this lifecycle lock across the Kernel call, immediate receipt persistence, and attempted verification persistence is authorized for this one operation-scoped backend capability. If that creates a demonstrated lock-order cycle, stop rather than weaken serializability.

## §8 Exact admission and contribution reconstruction

### §8.1 Replay before dependencies

Under the lifecycle lock, load the commit ledger before proposal, predecessor, or graph reads.

| Existing record | Exact same commit ID + request digest | Changed request or different commit ID |
|---|---|---|
| `committed_verified` | return immediately; zero dependency reads; zero merge calls | conflict/busy |
| `committed_unverified` | verification only; zero merge calls | conflict/busy |
| `committing` | c2a reconciliation first; never blind merge | conflict/busy |
| `uncommitted` | return terminal record | conflict/busy |
| `ambiguous` | return terminal record | conflict/busy |

### §8.2 New admission sequence

When no commit record exists:

1. Load the exact proposal ledger and exact route-named proposal under the lifecycle lock.
2. Require proposal `state=active` and ledger `active_proposal_id == proposal_id`.
3. Require request sealed digest and parent equal persisted proposal values.
4. Read the exact SBW09b resolution named by `proposal.resolution_id`.
5. Require the resolution remains active, publishable, and exact across draft, operation, source digest, resolution request digest, candidate-set digest, expected parent, decision, Threat ID, and selected-target snapshot.
6. Refresh/read the exact SBW09a operation.
7. Require operation remains `publication_ready` and exact across draft, operation, world, campaign, source digest, accepted mechanics locator, and expected parent.
8. Verify and reconstruct the complete sealed package using:

```python
verified, contribution = resolve_merged_contribution_from_package(
    review_package=proposal.sealed_proposal,
    confirming_principal=proposal.created_by,
    world_id_hint=operation.source_snapshot.world_id,
    root=configured_world_graph_root,
    expected_parent_revision_id=proposal.expected_parent_revision_id,
    assertion_ids=None,
    verify_source=False,
)
```

9. Require the verified package principal, proposal ID/digest/version, world, parent, and complete effect equal c1 authority.
10. Require reconstructed `contribution.contribution_id == proposal.expected_contribution_id`.
11. Require exact ordered accepted assertion IDs equal `proposal.accepted_assertion_ids`; no subset exists.
12. Compute `kernel.compute_contribution_source_payload_sha256(contribution)` and persist it in the record.
13. Derive and validate exact Threat, selected-target snapshot, external-resource node, binding edge, and binding ID from the proposal plus reconstructed contribution. Do not use labels or graph search to resolve identity.
14. Open current world head and require it equals the exact proposal parent.
15. Construct the strict record with `state=committing`, `merge_attempt_count=1`, and persist it atomically.

Only after the intent save succeeds may the Kernel merge be called.

Admission failure before step 15 writes no commit record and makes no graph call.

### §8.3 Whole-proposal rule

There is no accepted assertion selection in c2b. The contribution is the complete c1 sealed effect.

Create-new expected effect:

```text
Threat node
optional description attribute
optional threat_kind attribute
zero or more intended_role attributes
zero or more tag attributes
external statblock resource node
primary uses_statblock binding edge
```

Connect-existing expected effect:

```text
external statblock resource node
primary uses_statblock binding edge
```

Connect-existing must contain no Threat node assertion and no Threat label, alias, description, kind, role, tag, or other identity rewrite.

## §9 Kernel call, result classification, and durable commit points

### §9.1 Only allowed graph mutation

```python
result = kernel.merge_contribution_to_revision(
    configured_world_graph_root,
    world_id=record.world_id,
    contribution=exact_reconstructed_contribution,
    expected_parent_revision_id=record.expected_parent_revision_id,
)
```

No direct graph storage, generic HTTP confirmation, mutable-source prepare, contribution supersession, second graph framework, or caller-supplied world root is permitted.

### §9.2 Commit points

```text
Application intent point:
  atomic commit ledger save with state=committing and merge_attempt_count=1 or 2

Graph commit point:
  Kernel immutable revision publication/head advance

Application publication proof:
  atomic commit ledger save with state=committed_unverified and exact revision ID

Verified completion:
  atomic commit ledger save with state=committed_verified
```

After graph commit, no application failure may make another merge permissible.

### §9.3 Direct result classification

A direct `published=True` result is usable as immediate publication proof only when all are exact:

```text
result.world_id == record.world_id
result.parent_revision_id == record.expected_parent_revision_id
result.revision_id is nonblank
result.contribution_ids == [record.expected_contribution_id]
result.accepted_assertion_ids == record.accepted_assertion_ids
```

When exact, persist `committed_unverified` immediately before rebuild/projection or other audits.

Any malformed, missing, contradictory, or exception result is an uncertain outcome and must enter c2a reconciliation.

A typed `published=False` result is deterministic refusal, but c2a must still be consulted once before terminal classification in case immutable authority exists despite response-level refusal.

## §10 Immutable recovery algorithm

### §10.1 Recovery lookup key

```text
world_id = record.world_id
operation_id = record.expected_contribution_id
```

The lookup key is the Graph contribution ID because the Kernel publishes:

```text
operation_ids=[contribution.contribution_id]
```

It is never the SBW09a publication operation ID.

### §10.2 Reconciliation entry points

Reconcile before any retry when:

- replay loads `state=committing`;
- the Kernel raises;
- the Kernel result is missing/malformed/contradictory;
- `published=True` lacks an exact revision ID;
- `published=False` is returned;
- immediate committed-unverified persistence fails after a known or possible graph commit.

### §10.3 Unique-match publication proof

One c2a match becomes a recovery candidate only after all core checks pass:

- manifest world and revision identities are exact;
- `manifest.parent_revision_id == record.expected_parent_revision_id`;
- `record.expected_contribution_id` appears exactly in manifest `operation_ids`;
- the exact revision loads through `kernel.load_world_graph_revision_with_integrity`;
- revision `contribution_source_payload_sha256[expected_contribution_id]` equals the record's persisted contribution source digest;
- revision `contribution_replay_manifest` contains exactly one active entry for the expected contribution with the same digest.

After these checks, persist `committed_unverified`, set the exact revision ID, set `recovered_via_operation_lookup=true`, and begin full verification. Do not call merge.

A unique match that fails core publication-proof checks is an integrity ambiguity. Persist `ambiguous`; do not select it as the committed revision and do not retry.

### §10.4 Zero/one/many policy

| Lookup result | Prior event | Additional conditions | Durable transition | Merge action |
|---|---|---|---|---|
| one exact core-verified match | any unresolved path | none | `committed_unverified` | none |
| multiple matches | any unresolved path | none may be selected | `ambiguous` | none |
| zero matches | deterministic `published=False` | none | `uncommitted` | none |
| zero matches | unresolved attempt 1 | original parent still head; exact proposal/resolution/operation remain valid; contribution re-reconstructs identically | persist `committing` attempt 2 | one exact retry |
| zero matches | unresolved attempt 1 | parent changed or any authority mismatch | `uncommitted` | none |
| zero matches | unresolved attempt 2 | none | `uncommitted` | none |
| lookup unavailable/corrupt | any unresolved path | outcome remains unknown | remain `committing` | none |

### §10.5 One permitted recovery retry

Before the one retry:

1. c2a returned zero;
2. record is `committing` with `merge_attempt_count=1`;
3. current head still equals the original parent;
4. the exact proposal remains active and claimed by this record;
5. exact SBW09b resolution remains active and identical;
6. exact SBW09a operation remains ready and identical;
7. complete contribution re-reconstruction yields the same contribution ID, source digest, assertion IDs, and effect IDs;
8. persist `merge_attempt_count=2` before the second Kernel call.

After the second call, reconcile through c2a again before terminal classification. No third merge call exists.

If c2a is unavailable after attempt 2, retain `committing` with attempt count 2. Future replays may reconcile, but may never merge again.

### §10.6 Required receipt-save failure sequence

```text
intent persisted
→ Kernel publishes exact revision
→ committed-unverified save fails atomically, leaving prior committing bytes intact
→ response is unavailable/unknown
→ restart/replay loads committing
→ c2a finds one exact core-verified revision
→ committed-unverified persists
→ full verification runs
```

Merge-call count for this sequence is exactly one.

Head advance or rollback after commit cannot hide the immutable matching revision. Current head is never substituted for committed revision identity.

## §11 Exact committed-revision verification

Verification consumes only:

```text
durable commit record
exact c1 proposal
exact reconstructed contribution
exact committed revision and public Kernel outputs
```

It does not consume mutable ThreatDraft or current mechanics content.

### §11.1 Core verification — required for passed

1. c2a returns exactly one match for the expected contribution and it is the recorded revision.
2. Manifest world, revision, parent, status, and operation membership are exact.
3. Exact revision payload loads through `load_world_graph_revision_with_integrity`.
4. Revision contribution source digest equals the record and the reconstructed contribution.
5. Revision replay manifest contains one active exact contribution/digest entry.
6. Every expected accepted assertion ID has a support record with:
   - `support_state=supported`;
   - expected contribution in `active_contribution_ids`;
   - exact per-contribution evidence/source-artifact lineage where present.
7. Reconstructed contribution contains exactly the c1 accepted assertion IDs and no additional accepted assertion.
8. Create-new materializes the exact Threat node core and every authored field assertion.
9. Connect-existing contribution contains no Threat identity/attribute rewrite and the committed target node still matches the persisted selected-target snapshot.
10. External-resource node has exact deterministic ID, canonical label/aliases, kind `external_resource`, role `statblock`, source domain `manual_seed`, and strict `ExternalResourceV1` payload.
11. Binding edge has exact edge ID, endpoints, predicate `uses_statblock`, outbound direction, binding ID, and strict `ThreatStatblockBindingV1` payload.
12. Exact contribution/resource/binding payloads contain no copied mechanics body, rules elements, rendered Markdown, assets, or equivalent recursive content.

A core mismatch sets `verification_status=failed`, persists `committed_unverified`, records stable codes, and never permits another merge.

### §11.2 Secondary audits

Pinned rebuild:

```python
kernel.rebuild_from_contributions(
    configured_world_graph_root,
    world_id=record.world_id,
    compare_revision_id=record.committed_revision_id,
    publish=False,
)
```

Require diagnostic:

```text
rebuild_equivalent_to_pinned_revision
```

Revision-pinned projection:

```text
WorldGraphProjectionRequest
  world_id = record.world_id
  campaign_id = record.campaign_id
  revision_pin = record.committed_revision_id
  admissibility = gm
  scope_mode = campaign
  query_text = exact Threat label or node identity as appropriate
```

Require:

- snapshot revision equals the committed revision;
- exact Threat/resource/binding are represented consistently with the core checks;
- projection never silently binds newer mechanics.

If core checks pass but rebuild or projection is unavailable/degraded, persist:

```text
state=committed_unverified
verification_status=degraded
```

A later exact replay may rerun verification only. It may not merge.

### §11.3 Verification result matrix

| Condition | State | Verification | Merge retry |
|---|---|---|---|
| all core checks and secondary audits pass | `committed_verified` | `passed` | no |
| core checks pass; rebuild/projection unavailable or degraded | `committed_unverified` | `degraded` | no |
| core digest/support/object/binding mismatch | `committed_unverified` | `failed` | no |
| proposal or verification dependency unavailable after commit | `committed_unverified` | `not_started`/`degraded` | no |

## §12 State, identity, persistence, and fallback matrices

### §12.1 State/fallback matrix

| State | Meaning | POST behavior | GET behavior | Merge fallback |
|---|---|---|---|---|
| no record | proposal unclaimed | new admission | `404` | none |
| committing, attempt 1 | outcome unresolved; one retry may remain | c2a first | return pending record | one conditional retry only after zero match + full revalidation |
| committing, attempt 2 | outcome unresolved; no retry remains | c2a only | return pending record | none |
| uncommitted | deterministic refusal/unsafe retry/exhausted zero-match | terminal conflict | return record | new operation/proposal required |
| ambiguous | duplicate match or integrity contradiction | terminal conflict | return record | operator repair only |
| committed_unverified | immutable revision known | verification only | return receipt | none |
| committed_verified | exact verified publication | exact replay before dependencies | return receipt | none |

### §12.2 Identity matrix

| Identity | Authority | Persisted binding | Fallback |
|---|---|---|---|
| source and expected parent | SBW09a + c1 proposal | source digest + parent | none |
| Threat new/target identity | SBW09b + c1 proposal | threat ID + selected-target snapshot when connect | none |
| reviewed effect | c1 sealed package | proposal IDs/digests + assertion/effect IDs | none |
| contribution | exact reconstruction | contribution ID + source digest | none |
| committed revision | exact Kernel result or one core-verified c2a match | revision ID | never current head |
| resource/binding | c1 effect + SBW08 strict models | node/edge/binding IDs | none |
| commit replay | commit ID + canonical request digest | one record | none |

### §12.3 Persistence/replay matrix

| Event | Durable effect | Replay |
|---|---|---|
| admission fails before intent | none | caller fixes authority or creates new operation |
| intent saves | proposal permanently claimed | c2a before merge |
| graph publishes | immutable revision exists | c2a can recover by contribution ID |
| direct/recovered receipt saves | exact committed revision in app ledger | verification only |
| verification saves | verified/degraded/failed audit state | no merge |
| ledger save fails before intent | no record | no graph call |
| receipt save fails after commit | prior committing bytes remain | c2a recovery |
| ledger corrupt | no further mutation | fail closed |

### §12.4 Failure classification matrix

| Failure | Before/after intent | Durable state | HTTP/result | Retry policy |
|---|---|---|---|---|
| proposal/resolution/operation inactive | before | none | `409` typed predecessor result | no merge |
| parent mismatch before intent | before | none | `409` parent mismatch | new operation |
| intent storage unavailable | before graph call | none | `503` storage unavailable | safe exact request retry |
| Kernel typed refusal + zero lookup | after | `uncommitted` | `409` uncommitted | no merge retry |
| Kernel exception + zero lookup + unchanged parent | after attempt 1 | `committing` attempt 2 before retry | pending/continue | one retry |
| Kernel exception + lookup unavailable | after | `committing` | `503` recovery pending | replay later; no immediate merge |
| one exact recovered revision | after | `committed_unverified` | `200`/`201` committed receipt | verify only |
| multiple revisions | after | `ambiguous` | `409` ambiguous | no merge |
| verification dependency unavailable | after commit | `committed_unverified` | success-shaped receipt | verify later only |
| verification mismatch | after commit | `committed_unverified` failed | success-shaped receipt with failure codes | no merge |

### §12.5 Prohibited fallbacks

- latest mechanics
- current ThreatDraft
- latest identity resolution
- label/alias/rank identity selection
- current head as committed revision
- first immutable revision match
- new parent under the same record
- new proposal or contribution ID during recovery
- caller-selected assertion subset
- caller-selected world root
- contribution-store existence as publication proof
- direct World Graph storage scanning

## §13 Required evidence

### §13.1 Focused commands

```bash
uv run pytest -q tests/test_threat_publication_commit_models.py
uv run pytest -q tests/test_threat_publication_commits.py
uv run pytest -q tests/test_threat_publication_commit_api.py
uv run pytest -q tests/test_threat_publication_proposals.py
```

Regression bundle must include the actual merged owners:

- `tests/test_threat_publication_proposal_models.py`
- `tests/test_threat_publication_proposals.py`
- `tests/test_threat_publication_proposal_api.py`
- `tests/test_graph_kernel_operation_revision_lookup.py`
- `tests/test_threat_publication_operations.py`
- `tests/test_threat_publication_routes.py`
- `tests/test_threat_publication_identity.py`
- identity route tests if separate
- `tests/test_statblock_binding_graph_contract.py`
- `tests/test_extract_promote_proposal.py`
- `tests/test_extract_promote_ops_atomic.py`
- focused Kernel merge/source-authority/rebuild/world-projection suites

Also:

```bash
uv run ruff check <every touched Python path>
git diff --check
git diff --name-only <implementation-base>...HEAD
```

No repository-wide CI claim is permitted without attached checks. Baseline-red suites require exact base/head reproduction and explicit waiver.

### §13.2 Required adversarial sequences

1. Create-new commit → intent → one merge → immediate receipt → exact verification → restart GET.
2. Connect-existing commit produces resource+binding only and preserves exact target snapshot.
3. Request schema rejects assertion selection, world/root, identity, mechanics, and replacement parent fields.
4. Contribution reconstruction uses `proposal.created_by`; a different commit actor does not alter contribution ID.
5. Exact committed-verified replay returns before proposal/predecessor/graph reads.
6. Committed-unverified replay calls verification only and makes zero merge calls.
7. Same commit ID with changed request conflicts and leaves bytes unchanged.
8. Different commit ID after any claim returns busy/conflict.
9. Concurrent first confirmations yield one record and at most one initial merge.
10. Proposal supersession/confirmation race is serializable in both orderings.
11. c1 exact proposal replay still works after commit claim.
12. c1 new proposal/supersession is blocked after any commit record, including uncommitted.
13. Proposal ledger absent + commit ledger present fails integrity instead of taking the c1 no-artifact fast path.
14. Missing commit GET creates no directories or lock files.
15. Ledger write failure before intent makes zero graph calls.
16. Crash after intent, before Kernel call: zero lookup + unchanged parent permits exactly one retry.
17. Zero lookup retry is blocked when proposal, resolution, operation, contribution, or parent no longer matches.
18. Typed `published=False` + zero lookup persists uncommitted and performs no recovery retry.
19. Kernel exception/malformed result always invokes c2a before retry.
20. Crash after graph commit, before receipt: one match recovers with zero additional merge calls.
21. Receipt replacement failure leaves prior committing bytes intact and restart recovers.
22. Head advance after commit does not hide recovery.
23. Head rollback after commit does not hide recovery.
24. Multiple matches persist ambiguity and select none.
25. Unique match with wrong parent, digest, replay entry, or effect becomes ambiguity/integrity failure; no retry.
26. Lookup unavailable retains committing and makes no merge.
27. Attempt 2 plus zero lookup becomes terminal uncommitted; no third merge.
28. Attempt 2 plus lookup unavailable remains committing but never merges again.
29. Verification failure after commit remains committed-unverified and cannot merge.
30. Core verification pass + rebuild/projection unavailable becomes degraded, not failed/uncommitted.
31. Every accepted assertion support record names the exact contribution.
32. Create-new exact node/authored fields/resource/binding verified at immutable revision.
33. Connect-existing has no target Threat rewrite.
34. Recursive scan proves no mechanics body/rules/rendered Markdown/assets entered the contribution or exact committed resource/binding.
35. Predecessor, c1 proposal, ThreatDraft, and accepted-mechanics bytes remain unchanged except the intentional c1 commit-claim behavior.
36. Corrupt commit ledger fails closed and is not repaired.

### §13.3 Merge-call accounting

Every service test involving uncertainty must assert Kernel merge-call count explicitly.

```text
normal success: 1
exact terminal replay: 0
committed-unverified verification replay: 0
concurrent first confirmation across both callers: <=1 initial call total
intent crash + permitted recovery retry: exactly 1 later retry, <=2 lifetime calls
published response loss + recovery: 1 lifetime call
published=false deterministic refusal: 1 lifetime call
multiple matches: 0 new calls
lookup unavailable: 0 new calls
attempt_count=2 replay: 0 new calls
```

## §14 Required implementation handback

The implementation handback must record:

- exact implementation base/head and ancestry;
- exact changed paths and line counts;
- exact shared lifecycle lock/helper names;
- exact c1 fast-path and supersession changes;
- exact c2a signature used;
- JSON examples for request, every durable state, and response;
- contribution reconstruction principal and proof that commit actor cannot alter contribution ID;
- source digest, accepted assertion, Threat/resource/binding extraction rules;
- every §13 command and result with provenance;
- merge-call counts for every crash/replay sequence;
- zero/one/many lookup evidence including head advance and rollback;
- direct and recovered committed-unverified examples;
- exact verification results and stable codes;
- before/after bytes for proposal, predecessor, ThreatDraft, accepted mechanics, and graph head/revision where relevant;
- baseline failures and exact waivers;
- out-of-scope path accounting;
- explicit statement that UI, Hermes, product projection, placement, combat, mechanics adoption, undo, and generic publication remain false.

## §15 Acceptance rubric

- [ ] Implementation base is the immutable main SHA containing this re-anchored handoff.
- [ ] Actual c1 and c2a contracts are used without private storage scanning.
- [ ] One operation has at most one durable commit record.
- [ ] Any commit record permanently claims the exact proposal.
- [ ] Proposal supersession and confirmation share one serializable lifecycle lock.
- [ ] c1 no-artifact fast paths require both proposal and commit authority to be absent.
- [ ] Exact c1 proposal replay remains available after claim.
- [ ] Confirmation request cannot select content, identity, mechanics, root, or parent.
- [ ] Contribution reconstruction uses `proposal.created_by`, not the commit actor.
- [ ] Whole sealed proposal is verified; no assertion subset exists.
- [ ] Exact contribution ID and lifecycle-neutral source digest are persisted before merge.
- [ ] Intent is durable before the first and optional second Kernel call.
- [ ] At most two lifetime merge attempts exist: initial plus one zero-match recovery retry.
- [ ] Deterministic refusal is never retried.
- [ ] Every uncertain outcome checks c2a before retry or terminal classification.
- [ ] Unique recovery requires exact parent, integrity load, contribution digest, and replay entry.
- [ ] Multiple matches remain ambiguous.
- [ ] Current head is never substituted for committed revision.
- [ ] Known committed revision permanently prohibits merge retry.
- [ ] Committed-unverified is durable, success-shaped, and truthfully exposed.
- [ ] Exact revision verifies contribution/support, Threat/resource/binding, rebuild, and projection.
- [ ] Connect-existing performs no Threat identity rewrite.
- [ ] No mechanics body enters graph state.
- [ ] Storage is strict, path-safe, atomic, bounded, restart-safe, and corruption-closed.
- [ ] Missing GET and terminal pre-intent paths create no storage artifacts.
- [ ] No production path outside §4 changes.
- [ ] UI/query/product projection/placement/combat remain false.

## §16 Reviewer attack list

- Race proposal supersession between active-proposal read and intent save.
- Race two first confirmations with different commit IDs.
- Replay with same commit ID but changed actor, note, digest, or parent.
- Confirm using a different actor than `proposal.created_by`; prove contribution ID is unchanged because reconstruction uses the sealed principal.
- Seed a commit ledger while deleting the proposal ledger; attack c1 fast paths.
- Count merge calls across every replay, refusal, exception, and receipt-save seam.
- Search for current-head substitution, repinning, first-match selection, `next(...)`, label lookup, mutable draft reads, or contribution-record publication inference.
- Verify the c2a lookup key is `expected_contribution_id`, never SBW09a `operation_id`.
- Return `published=True` with inconsistent IDs and require reconciliation.
- Return `published=False` after synthetic immutable publication and require c2a recovery rather than terminal refusal.
- Delete immediate receipt after synthetic publish and require restart recovery.
- Advance and roll back head before recovery.
- Seed duplicate operation IDs and ensure no revision is selected.
- Seed one matching manifest with wrong parent or payload digest and ensure it is not accepted.
- Fail every atomic commit-ledger replacement point.
- Fail verification after publication and prove no merge retry.
- Inspect connect-existing accepted assertions and committed target fields for rewrites.
- Recursively scan the exact contribution/resource/binding for mechanics bodies.
- Verify application code imports only public Kernel APIs, not world-supergraph storage or contribution-store internals.
- Verify rebuild runs with `publish=False` and exact `compare_revision_id`.
- Verify pinned projection uses the committed revision, not current head.

## §17 Stop conditions

Stop and report before widening scope if:

- the authority PR containing this handoff is not merged or the implementation base differs;
- c1 cannot expose the existing operation-scoped lock as a safe shared lifecycle seam;
- blocking c1 supersession requires changing the durable c1 proposal schema rather than reading the c2b claim under the shared lock;
- exact contribution reconstruction cannot use `proposal.created_by` without changing extract-promote code;
- c1 lacks enough exact effect identity to derive and persist contribution/resource/binding proof;
- c2a cannot recover independently of current head or returns nonplural/first-win semantics;
- safe commit requires a Kernel write/CAS change;
- exact recovery requires direct graph-storage or contribution-store imports from application code;
- one unique revision cannot be proven against the persisted contribution source digest;
- any known committed outcome can become merge-retryable;
- a third merge attempt becomes necessary;
- a production path outside §4 is required;
- UI, Hermes, product projection, placement, combat, generic publication, mechanics adoption, or undo enters scope;
- an owning-boundary regression cannot be reproduced identically at the implementation base.

## §18 Authority PR companion updates

The documentation authority PR that checks in this handoff must also update the active tracker and roadmap so they state current truth:

```text
SBW09c1  MERGED #478
SBW09c2a MERGED #476
SBW09c2b ACTIVE / NEXT PUBLICATION IMPLEMENTATION
```

It must remove language claiming c1/c2a are active or unimplemented, retain MAGIC-D3 as blocked on c2b + SBW10a + SBW10b, record the exact authority merge SHA after merge, and keep later query/projection/placement/combat gates unchanged.

The authority PR is documentation only. It does not claim runtime behavior or green CI. Implementation begins only after that authority is on main.
