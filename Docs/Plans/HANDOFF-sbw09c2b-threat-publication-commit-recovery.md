---
pr_body_template: |
  ## Outcome
  The live-control server can explicitly confirm one exact active Threat publication proposal into one exact World Graph contribution and immutable revision, preserve durable commit intent and receipt across response loss or restart, recover ambiguous outcomes through exact immutable revision authority, and verify the exact Threat/resource/binding result without repinning or recommitting a known publication.

  ## Merge-ready invariant
  For one exact active SBW09c1 proposal, at most one durable commit record can claim it; the record binds the exact proposal request digest, sealed proposal digest, expected parent, contribution ID, accepted assertion set, Threat identity, external resource, and binding. Intent is persisted before the Kernel merge. Committed-unverified authority is persisted immediately when publication is proven. An unresolved attempt is reconciled through the SBW09c2a exact contribution-ID lookup before any retry; deterministic refusals are never retried; multiple matches remain ambiguous; and no merge occurs after a committed revision is known. Verification is pinned to that immutable revision, and verification failure remains committed-but-unverified rather than becoming a second write.

  ## Evidence required to merge
  | Guarantee | Owning boundary | Required evidence | Result |
  |---|---|---|---|
  | One proposal claim and one commit record | shared proposal lifecycle lock + commit ledger | concurrency and proposal-supersession race matrix | {{TODO}} |
  | Intent-before-write and bounded merge attempts | commit service | injected crash/write/refusal/exception sequences | {{TODO}} |
  | Honest ambiguous-outcome recovery | c2a lookup integration | zero/one/many, head-advance, and rollback sequences | {{TODO}} |
  | Exact committed-revision verification | verifier | contribution/support/object/binding/rebuild/projection matrix | {{TODO}} |
  | Committed-but-unverified honesty | receipt state machine | degraded/failed verification and replay tests | {{TODO}} |

  ## Scope and explicit deferrals
  - Required implementation base: {{EXACT_DISPATCH_SHA — the immutable origin/main SHA recorded by the post-merge authority sync of the PR merging this handoff}}
  - Actual base/head: {{TODO}}
  - Actual changed paths: {{TODO}}
  - Deferred: Workbench confirmation UI, Hermes query/hydration, Threat projection surface, placement, combat, mechanics revision adoption, and generic object publication.

  ## Evidence produced
  {{TODO}}

  ## Gaps, waivers, and stop conditions
  {{TODO: none, or exact stop report}}
---

# HANDOFF — SBW09c2b proposal-bound Threat commit, recovery, and exact verification

**Created:** 2026-08-01 (design-only draft, draft PR `#474`)
**Re-anchored:** 2026-08-01 against merged SBW09c1 + SBW09c2a implementation contracts
**Status:** RE-ANCHORED IMPLEMENTATION AUTHORITY — dispatch is prohibited until this amendment merges and a post-merge authority sync records the immutable `origin/main` dispatch SHA in this header.
**Canonical path:** `Docs/Plans/HANDOFF-sbw09c2b-threat-publication-commit-recovery.md`
**Re-anchor base:** `9d7acea97b257a87f636efdf18d206381fba5938` — current `origin/main` tip (PR `#481` merge; doc-only SIH-01 commits sit atop `c15420e6bc6bc9eca83933bf9982b233ff0fc3a7`, the PR `#478` merge containing PR `#476` at `c6e867ed`)
**Dispatch base:** not yet assigned. It must be the immutable `origin/main` SHA produced by merging this amendment, recorded here by post-merge authority sync. Dispatching from any earlier SHA is prohibited.
**Suggested implementation branch:** `feat/sbw09c2b-threat-publication-commit-recovery`

> This document is now the sole SBW09c2b implementation authority. Every provisional name from the design-only draft has been replaced with the actual merged SBW09c1 and SBW09c2a contracts. §12 records the amendment. Implementation must follow this file, not the pre-merge draft.

## §0 Capability decomposition

| Candidate outcome | Independently useful? | Durable/public contract changed? | Decision |
|---|---:|---:|---|
| Claim one exact active proposal for publication | No, inseparable from commit safety | Proposal lifecycle + commit authority | Include |
| Persist exact commit intent before graph mutation | No, inseparable from recovery | New application-owned durable record | Include |
| Perform one exact-parent Kernel merge | Yes | Existing Kernel write contract | Include |
| Recover response loss or process death | Yes | Commit state/retry contract | Include |
| Verify exact immutable Threat/resource/binding result | Yes | Publication outcome semantics | Include |
| Add GM-facing confirmation UI | Yes | Product surface | Named successor after backend proof |
| Query/hydrate/project the published Threat | Yes | Consumer contracts | SBW10a/SBW10b |
| Generalize publication to every object type | Yes | Generic framework | Reject |

**Selected capability:** one proposal-bound, durable, recoverable backend commit path that truthfully distinguishes uncommitted, ambiguous, committed-unverified, and committed-verified outcomes.

A graph-writing endpoint is not safe merely because `merge_contribution_to_revision` publishes atomically. The application must know whether it already dispatched the exact contribution, prevent proposal supersession while the outcome is unresolved, recover an immutable revision after response loss, and never report preview material as durable without checking the exact committed revision. Intent, the bounded merge attempt, immediate receipt persistence, recovery, and verification therefore share one invariant.

**Mission falsification:** this is not one slice if implementation also requires UI, mechanics mutation, identity reselection, parent repinning, a generic graph editor, a second Graph Kernel, a new revision index beyond c2a, or World Graph write/CAS changes.

## §1 Mission and invariant

```text
One exact active Threat publication proposal can be explicitly confirmed into
one exact immutable World Graph revision with a durable commit record that
survives response loss and restart, recovers an ambiguous outcome from immutable
revision authority, and verifies the exact Threat/resource/binding result at the
committed revision without a latest/current-head fallback or duplicate write.
```

```text
For one exact active SBW09c1 proposal, at most one durable commit record can claim
it. The record binds the exact proposal request digest, sealed proposal digest,
expected parent, contribution ID, accepted assertion set, Threat identity,
external resource, and binding. Intent is persisted before the Kernel merge.
Publication proof is persisted as committed_unverified immediately when an exact
immutable revision is known. An unresolved attempt checks c2a before any retry;
deterministic refusals are terminal, multiple matches remain ambiguous, and no
merge occurs after a committed revision is known. Verification is pinned to that
revision; degraded or failed verification remains committed-but-unverified.
```

### Pre-dispatch critique

- Most likely race: proposal supersession occurs after confirmation begins but before commit intent becomes durable. Closed by the actual c1 lock seam in §7 — c1 already serializes all proposal mutations under one operation-scoped file lock and holds it across every dependency and graph read.
- Most dangerous retry bug: stale-parent handling blindly re-merges or records current head as the committed revision. The merged Kernel raises `ValueError("stale parent ...")`; §8.3 classifies it as a deterministic refusal and forbids retry because the head has provably moved.
- Most dangerous refusal bug: a typed `published=false` result is misclassified as transport ambiguity and consumes the crash-recovery retry — or is misclassified as "nothing published" when the merged Kernel also returns it for the idempotent already-applied no-op. §8.3 reconciles every `published=false` through c2a exactly once and never retries a deterministic refusal.
- Most dangerous receipt bug: publication succeeds, receipt persistence fails, and a later request treats the proposal as uncommitted. §8.5 makes restart recovery through c2a the required sequence.
- Required defense: one shared lifecycle lock, intent-before-write, deterministic-refusal terminality, c2a-before-retry, immutable verification, and no-retry semantics once a committed revision is known.

## §2 Authority and dependency map — re-anchored to merged code

| Concern | Authority |
|---|---|
| Source and expected parent | SBW09a merged PR `#462` |
| Threat identity decision | SBW09b merged PR `#467` |
| Exact reviewed effect (proposal) | SBW09c1 merged PR `#478` (merge `c15420e6`, head `f0e85b4e`) |
| Operation-to-revision recovery | SBW09c2a merged PR `#476` (merge `c6e867ed`, head `bf3aba87`) |
| Resource/binding identity | SBW08 merged PR `#457` |
| Proposal seal/verification | `graph_memory.extract_promote_proposal.seal_promote_proposal` / `verify_promote_proposal` |
| Contribution reconstruction | `graph_memory.extract_promote_ops.resolve_merged_contribution_from_package` |
| Graph commit | public `graph_memory.kernel.merge_contribution_to_revision` |
| Exact revision reads | public `graph_memory.kernel.load_world_graph_revision_with_integrity`, `open_world_graph_head`, `rebuild_from_contributions`, `project_world_graph` |
| Sequence | active Threat tracker and roadmap |

### Merged SBW09c1 contract consumed here (PR `#478`)

Models — `apps/live_control_server/models/threat_publication_proposal.py`:

- `ThreatPublicationProposalV1` (`schema: dmb_threat_publication_proposal_v1`): `proposal_id`, `request_digest`, `draft_id`, `operation_id`, `resolution_id`, `source_digest`, `resolution_request_digest`, `candidate_set_digest`, `expected_parent_revision_id`, `decision`, `threat_node_id`, `sealed_proposal_id` (must equal `proposal_id`), `sealed_proposal_digest` (`sha256:<hex>` of the sealed package `proposal_digest`), `sealed_proposal_version`, `sealed_proposal` (complete sealed package), `expected_contribution_id`, `accepted_assertion_ids` (unique), `effect_summary`, `state` (`active|superseded`), `supersedes_proposal_id`, `superseded_by_proposal_id`, `created_by`, `operator_note`, `created_at`, `updated_at`.
- `ThreatPublicationEffectSummaryV1`: `decision`, `threat_node_id`, `external_resource_node_id`, `binding_edge_id`, `accepted_assertion_count`, `authored_field_assertion_count`. There is no top-level `binding_id` on the proposal; §6.2 pins where c2b obtains it.
- `ThreatPublicationProposalLedgerV1` (`schema: dmb_threat_publication_proposal_ledger_v1`): single active pointer, bidirectional supersession links, full-lineage acyclicity, per-proposal `request_digest` recomputation on load; `MAX_PROPOSALS_PER_OPERATION = 16`.
- `PrepareThreatPublicationProposalRequestV1` and `prepare_request_digest(draft_id, operation_id, resolution_id, request)` — canonical `_canonical_json_digest` over every route identity plus every request field.
- `ThreatPublicationProposalResponseV1`: `resolution_id: str | None`. GET not-found and storage-error paths return `resolution_id=null` rather than a sentinel identity; success returns the persisted resolution ID. c2b responses follow the same no-sentinel rule (§6.4).
- `validate_proposal_id`: UUID or `tpub_[A-Za-z0-9][A-Za-z0-9_.-]{0,127}`.

Service — `apps/live_control_server/services/threat_publication_proposals.py`:

- Storage: `out/threat_publication_proposals/<draft_id>/<operation_id>/ledger.json` under `proposal_root(repo_root())`, with path-escape rejection in `_operation_directory` and atomic whole-ledger replace via `write_json`.
- `_proposal_lock(root, draft_id, operation_id)`: the operation-scoped exclusive file lock (`.proposal.lock`). It is held across ledger load, replay comparison, SBW09b identity read, SBW09a publication refresh, exact-parent integrity-attested store load, preflight, seal, expected-contribution reconstruction, and ledger save.
- Pre-lock fast paths guarantee zero storage artifacts (no directory, no lock file) for terminal no-write outcomes: missing ledger with `supersedes_proposal_id` set, inactive/missing/refused resolution, and GET misses.
- Replay: exact `request_digest` match returns the persisted proposal before predecessor or graph reads; same `proposal_id` with a changed request returns `publication_proposal_input_conflict`; an active proposal without `supersedes_proposal_id` returns `publication_proposal_busy`; history bound returns `publication_proposal_history_full`.
- Expected contribution identity: computed once at prepare through `resolve_merged_contribution_from_package(review_package=package, confirming_principal=<prepare actor>, world_id_hint=<snapshot world>, root=<graph root>, expected_parent_revision_id=<operation parent>, assertion_ids=None, verify_source=False)` and persisted as `expected_contribution_id`.

Routes — `apps/live_control_server/routes/threat_publication_proposals.py`:

```text
POST /api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/identity-resolutions/{resolution_id}/proposals
GET  /api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/proposals/{proposal_id}
```

HTTP mapping: `201` first ready creation; `200` success/replay/superseded reads; `404` not-found; `409` typed conflicts; `503` graph/storage unavailable; `500` integrity failure; `422` route validation.

### Merged SBW09c2a contract consumed here (PR `#476`)

Public Kernel facade — `graph_memory.kernel.find_world_graph_revisions_by_operation_id`:

```python
def find_world_graph_revisions_by_operation_id(
    root: Path,
    world_id: str,
    operation_id: str,
) -> tuple[WorldGraphRevision, ...]:
```

- Returns every immutable revision manifest whose `operation_ids` contain `operation_id`, across the complete revision store in one enumeration snapshot, independent of current head. Performs no durable writes.
- Plural zero/one/many semantics; results ordered by `(created_at, revision_id)`. Ordering is deterministic evidence order only — it is never a selection rule.
- Errors: `ValueError` for blank/whitespace `operation_id`; `world_paths.assert_safe_world_id` validation for `world_id`; `WorldGraphIntegrityError` when a loaded manifest's embedded `world_id` or `revision_id` disagrees with the store path it was loaded from (manifest identity hardening merged in the PR `#476` review fix); storage parse/validation failures propagate as typed `WorldGraphError` family failures. Callers must treat any lookup error as "outcome unknown", never as "zero matches".
- Regression owner: `tests/test_graph_kernel_operation_revision_lookup.py`.

### Merged Kernel write contract consumed here

`graph_memory.kernel.merge_contribution_to_revision(root, *, world_id, contribution, expected_parent_revision_id) -> ContributionMergeResult` (`src/graph_memory/kernel/contribution_merge.py`):

- Publishes exactly one immutable revision with `operation_ids=[to_store.contribution_id]`. The manifest key is therefore the **Graph contribution ID**, not the SBW09a publication operation ID. Recovery through c2a must use the proposal's `expected_contribution_id`.
- Result taxonomy is pinned in §8.3; the design-only draft's assumption that `published=false` always means "nothing was published" is corrected there.
- `WorldGraphRevision` manifest fields: `world_id`, `revision_id`, `parent_revision_id`, `created_at`, `operation_ids`, `graph_schema`, `graph_payload_sha256`, `graph_payload_path`, `status="published"`.

### Exact-revision verification seams consumed here

- `kernel.load_world_graph_revision_with_integrity(root, world_id, revision_id) -> UnionSupergraphStore` — verifies on-disk manifest, graph payload hash, graph schema, and recomputed content-addressed revision ID.
- `UnionSupergraphStore.contribution_source_payload_sha256: dict[str, str]` — revision-bound lifecycle-neutral contribution digests.
- `UnionSupergraphStore.contribution_replay_manifest: list[ContributionReplayManifestEntry]` — `{contribution_id, status, source_payload_sha256}` membership frozen at publish time.
- `UnionSupergraphStore.assertion_support` — durable support records naming introducing contribution IDs.
- `kernel.compute_contribution_source_payload_sha256(contribution)` — public digest of the lifecycle-neutral source payload.
- `kernel.rebuild_from_contributions(root, *, world_id, publish=False, compare_revision_id=<committed>)` — pinned rebuild audit; equivalence is reported by the `rebuild_equivalent_to_pinned_revision` diagnostic.
- `kernel.project_world_graph(root, WorldGraphProjectionRequest(..., revision_pin=<committed>))` — request models imported from `graph_memory.projection.world_projection`, the same public seam merged SBW09b uses; `projection.snapshot.revision_id` must equal the committed revision.

### Read after the dispatch gate

1. `AGENTS.md` and external-agent PR-loop rules.
2. Active tracker, roadmap, and this amended handoff.
3. Merged c1 models/service/routes/tests and handback (PR `#478`).
4. Merged c2a public function/export/tests and handback (PR `#476`).
5. SBW09a/SBW09b owning services and tests.
6. SBW08 resource/binding models and tests (`graph_memory.union_supergraph.statblock_binding`).
7. `extract_promote_proposal.py` / `extract_promote_ops.py` verification and reconstruction owners.
8. Public Kernel contribution, revision, rebuild, and projection APIs.
9. Generic extract-promote confirmation only as precedent; do not copy current-head recovery shortcuts.

### Locked boundaries

- The exact active c1 proposal is complete content authority.
- SBW09a remains source and expected-parent authority.
- SBW09b remains Threat identity authority.
- The confirmation request confirms; it does not select assertions, identity, parent, world root, or mechanics.
- The Kernel owns graph mutation and immutable revision publication.
- The application commit ledger owns durable intent, outcome, and verification status.
- c2a owns complete exact operation-ID-to-revision lookup.
- Current head is used only for pre-merge parent admission or deciding whether an unresolved zero-match attempt may make one exact recovery retry. It is never proof of which revision committed the proposal.

## §3 Observable-path inventory

| Path | Required behavior | Owner |
|---|---|---|
| Confirm exact active proposal | persist intent, dispatch exact merge, persist receipt, verify | commit service |
| Exact replay after success | return durable record before predecessor/graph reads | commit ledger |
| Replay after committed-unverified | verification only; never merge | commit service |
| Same commit ID, changed request | conflict; bytes unchanged | ledger |
| Different commit ID for claimed proposal | busy/conflict; no second record | ledger |
| Proposal supersession racing confirmation | either supersession wins before claim or commit claim wins; never both | shared lifecycle lock (§7) |
| Crash after intent, before/around merge | c2a zero; one exact retry only if attempt remains unresolved and parent unchanged | recovery state machine |
| Deterministic merge refusal | c2a reconciliation; zero match becomes terminal uncommitted; no retry | commit service |
| Kernel idempotent already-applied no-op | c2a reconciliation; unique match becomes committed-unverified, never uncommitted | commit service |
| Crash after commit, before receipt | unique immutable match recovers; no merge | c2a + ledger |
| Head advances or rolls back after commit | recover exact immutable committed revision | c2a |
| Multiple matching revisions | integrity ambiguity; no first-win receipt | c2a caller policy |
| Lookup unavailable/corrupt | remain unresolved `committing`; no merge | recovery state machine |
| Verification fails after publication | persist committed-unverified; retry forbidden | verifier |
| Restart/read | exact record round-trips under lifecycle lock | ledger/GET |
| Corrupt commit ledger | fail closed; no repair/overwrite | parser/store |
| UI/Hermes/product projection | absent | successors |

## §4 Implementation allowlist — revalidated against merged c1/c2a

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live_control_server/models/threat_publication_commit.py` | strict request, record, ledger, response models |
| Create | `apps/live_control_server/services/threat_publication_commit_store.py` | path-safe atomic ledger reads/writes; dependency-neutral; no independent lock; must not import the proposal service |
| Create | `apps/live_control_server/services/threat_publication_commits.py` | claim, commit, recovery, verification orchestration |
| Create | `apps/live_control_server/routes/threat_publication_commits.py` | POST confirm and GET exact record |
| Modify | `apps/live_control_server/services/threat_publication_proposals.py` | expose the existing `_proposal_lock` through a public alias (§7); refuse supersession once a commit record exists |
| Modify | `apps/live_control_server/models/threat_publication_proposal.py` | add `publication_proposal_commit_claimed` to `ThreatPublicationProposalResultLabel`; no other model change |
| Modify | `apps/live_control_server/routes/threat_publication_proposals.py` | map `publication_proposal_commit_claimed` to `409`; no other route change |
| Modify | `apps/live_control_server/main.py` | commit router registration |
| Create | `tests/test_threat_publication_commit_models.py` | model/state/ledger invariants |
| Create | `tests/test_threat_publication_commits.py` | service, persistence, recovery, concurrency, verification |
| Create | `tests/test_threat_publication_commit_api.py` | route/status/result contracts |
| Modify | `tests/test_threat_publication_proposals.py` | supersession blocked after commit claim; zero-artifact preservation |
| Modify | `tests/test_threat_publication_proposal_models.py` | new label acceptance only |
| Modify | `tests/test_threat_publication_proposal_api.py` | `409` mapping for the new label |

Bounded test-only discovery exception:

```text
Directory: tests/
Maximum additional paths: 2
Allowed: existing shared fixtures/helpers or route-registration test only
Rule: no additional production scope
Report: exact paths and why local fixtures were insufficient
```

The merged c1 durable schemas (`dmb_threat_publication_proposal_v1`, `dmb_threat_publication_proposal_ledger_v1`, request/response envelopes), storage layout, replay semantics, pre-lock no-artifact fast paths, and result labels are frozen. The only permitted c1 changes are the three rows above. Any further c1 semantic need is a stop condition (§16), not an in-PR fix.

Production changes under `src/graph_memory/**`, SBW09a/SBW09b models/stores, ThreatDraft, accepted-mechanics persistence, DungeonMind, UI, corpus, placement, or combat are prohibited. The merged Kernel write, c2a lookup, integrity read, rebuild, and projection contracts are sufficient as-is; no Kernel change is needed or allowed.

## §5 Exclusions and demolition

Excluded: proposal construction, identity selection, assertion subsets, parent/mechanics repinning, retries under a new operation/proposal, current-head receipt inference, first-match selection, UI confirmation, Hermes write/query/hydration, Threat projection UI, placement/combat, generic publication, supersession/retraction of a committed contribution, and undo.

```text
Replaced path: any Threat-specific current-head inference, generic stale-parent already-applied shortcut, or proposal supersession after commit begins
Deleted in this PR: no
Retained reason: generic extract-promote confirmation remains an independent consumer
Named remaining consumer: Graph Review / generic extract-promote workflows
Required deletion owner: none; later consolidation may deliberately reuse the stronger recovery primitive
```

## §6 Request, record, storage, and API

### §6.1 Confirmation request

```text
schema: dmb_confirm_threat_publication_request_v1
commit_id: UUID or bounded tcommit_<token> (same validation pattern as c1 validate_proposal_id)
sealed_proposal_digest: exact persisted c1 sealed_proposal_digest (sha256:<64 hex>)
expected_parent_revision_id: exact persisted c1/SBW09a parent
actor: nonblank bounded string (same _MAX_ACTOR bound as c1)
operator_note: optional bounded string (same _MAX_NOTE bound as c1)
```

Route identity supplies `draft_id`, `operation_id`, and `proposal_id`. The canonical request digest uses the c1 `_canonical_json_digest` convention over every route identity plus every request field, mirroring `prepare_request_digest`.

The request must not accept assertion IDs, world/campaign/root, identity/target IDs, resource/binding IDs, mechanics locators/bodies, `dry_run`, live-world permission, idempotency policy, or a replacement parent.

`actor` is passed to `verify_promote_proposal` as `confirming_principal` and recorded as the commit's `created_by`. The merged verification requires a nonblank principal but does not bind it to the sealed `prepared_by`; contribution identity is unaffected by who confirms because `authored_by` comes from the sealed `contribution_meta.authored_by` (c1 persists the SBW09b resolution actor there). Requiring the confirm actor to equal the prepare actor is therefore not an identity control and is not imposed.

### §6.2 Durable commit record

```text
schema: dmb_threat_publication_commit_v1
commit_id
request_digest
draft_id
operation_id
proposal_id
proposal_request_digest        <- proposal.request_digest
sealed_proposal_digest         <- proposal.sealed_proposal_digest
resolution_id                  <- proposal.resolution_id
world_id                       <- sealed package world_id (recovery key; amendment §12)
source_digest                  <- proposal.source_digest
resolution_request_digest      <- proposal.resolution_request_digest
candidate_set_digest           <- proposal.candidate_set_digest
expected_parent_revision_id    <- proposal.expected_parent_revision_id
expected_contribution_id       <- proposal.expected_contribution_id
accepted_assertion_ids         <- proposal.accepted_assertion_ids (order preserved)
decision: create_new | connect_existing
threat_node_id                 <- proposal.threat_node_id
external_resource_node_id      <- proposal.effect_summary.external_resource_node_id
binding_id                     <- sealed package binding edge value.threat_statblock_binding.binding_id
binding_edge_id                <- proposal.effect_summary.binding_edge_id
state: committing | uncommitted | ambiguous | committed_unverified | committed_verified
merge_attempt_count: 1..2
committed_revision_id: exact revision | null
recovered_via_operation_lookup: bool
verification_status: not_started | passed | degraded | failed
verification_codes: bounded ordered list
warnings: bounded ordered list
created_by
operator_note
created_at
updated_at
```

Every effect field is extracted from and validated against the durable c1 proposal and its sealed package. They are never reconstructed from mutable draft, label, mechanics store, or current head.

`binding_id` derivation is pinned because the merged proposal model carries only `effect_summary.binding_edge_id`: read the binding edge assertion inside `sealed_proposal` (`value.threat_statblock_binding.binding_id`), then cross-check it against `compute_binding_id(...)` from the SBW09a snapshot's `accepted_mechanics_ref` plus the proposal `threat_node_id`, and require `edge_id_from_binding_id(binding_id) == effect_summary.binding_edge_id`. Any disagreement fails closed as commit-ledger integrity failure.

State invariants:

- `committing`: `committed_revision_id` is null; attempt count is 1 or 2; outcome remains unresolved.
- `uncommitted`: `committed_revision_id` is null; deterministic refusal, unsafe retry, or exhausted recovery; terminal for this claim.
- `ambiguous`: `committed_revision_id` is null; multiple immutable matches or integrity ambiguity; terminal pending external repair.
- `committed_unverified`: `committed_revision_id` is required; merge retry prohibited.
- `committed_verified`: `committed_revision_id` is required; verification passed; merge retry prohibited.
- A persisted record always has `merge_attempt_count >= 1`; the first durable state is `committing` with count 1.
- Any record permanently claims the proposal. No delete/reset exists in v1.

### §6.3 Ledger and storage

```text
schema: dmb_threat_publication_commit_ledger_v1
draft_id
operation_id
commit: ThreatPublicationCommitV1 | null
```

```text
out/threat_publication_commits/<draft_id>/<operation_id>/ledger.json
```

The commit store mirrors c1 storage discipline: path-safe identity components with escape rejection, atomic whole-file replace, schema marker validation, model validation on every load, and typed `unavailable`/`integrity` storage errors. Malformed JSON, wrong schema, or invariant failure is an integrity failure, never a repair.

There is no `.commit.lock`. The c1 operation-scoped `.proposal.lock` is the sole proposal/commit lifecycle lock (§7). The commit store exposes dependency-neutral unlocked low-level reads/writes legal only while that semantic lock is held; it must not import the proposal service. The allowed import direction is exactly:

```text
threat_publication_proposals.py  ->  threat_publication_commit_store.py (unlocked read only)
threat_publication_commits.py    ->  threat_publication_commit_store.py
threat_publication_commits.py    ->  threat_publication_proposals.py (public lock alias + read paths)
threat_publication_commit_store.py -> (no proposal/commit service imports)
```

One operation has at most one commit record. A terminal uncommitted record is not cleared to reuse the proposal; a new parent requires a new SBW09a operation, resolution, and proposal.

### §6.4 Routes and results

```text
POST /api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/proposals/{proposal_id}/commits
GET  /api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/commits/{commit_id}
```

Response envelope `dmb_threat_publication_commit_response_v1`:

```text
draft_id
operation_id
proposal_id: str | null   # route-known on POST; record-known on GET success; null on GET miss
commit_id: str            # always known (request commit_id on POST; route commit_id on GET)
result_label
commit: ThreatPublicationCommitV1 | null
retry_allowed: bool       # true only for an unresolved committing record whose latest
                          # reconciliation was unavailable and merge_attempt_count == 1
message: str | null
```

Following the merged c1 precedent (`resolution_id: str | None` on GET failure paths), failure responses never invent sentinel identities. Fields that cannot be known are `null`; there is no all-zero UUID anywhere.

Minimum labels:

```text
publication_commit_verified
publication_commit_committed_unverified
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

HTTP:

- first committed result: `201`, including committed-unverified;
- replay, recovery, GET, or verification-only replay: `200`;
- not found: `404`;
- uncommitted, stale, busy, changed input, or ambiguity: `409`;
- validation: `422`;
- unavailable dependency/storage: `503`;
- corrupt durable authority/integrity: `500`.

Committed-unverified is a success-shaped receipt with exact committed revision and `retry_allowed=false`, never a generic error that invites a second commit.

The c1 side of the claim boundary adds one label to the merged c1 contract (§7): `publication_proposal_commit_claimed`, mapped to `409` in the c1 proposal routes. No other c1 label, route, or mapping changes.

## §7 Shared proposal claim and lock — the actual merged seam

Merged c1 owns the only operation-scoped proposal lifecycle lock:

```text
apps/live_control_server/services/threat_publication_proposals.py
_proposal_lock(root, draft_id, operation_id)
  -> mkdir out/threat_publication_proposals/<draft_id>/<operation_id> (if absent)
  -> flock exclusive on .proposal.lock
```

c1 already holds this lock across every proposal mutation and across all of its dependency and graph reads (SBW09b identity read, SBW09a refresh, integrity-attested exact-parent store load, preflight, seal, expected-contribution reconstruction). Holding the same lock across the c2b Kernel merge is therefore consistent with merged behavior — it widens no lock-order dimension that c1 does not already occupy.

The exact seam for this slice:

1. **Public alias.** `threat_publication_proposals.py` exposes the existing lock under a public name (`proposal_lifecycle_lock`) with identical semantics — same path, same exclusive flock, same directory creation. The private name remains for internal callers. No second lock, no reimplementation, no path duplication.
2. **Commit-claim gate inside c1 supersession.** In `prepare_threat_publication_proposal`, under the lock, when `request.supersedes_proposal_id is not None`, the service reads the commit ledger through the commit store's dependency-neutral unlocked read before mutating the proposal ledger. If any commit record exists for the operation, the outcome is `publication_proposal_commit_claimed` (`409`); proposal bytes remain unchanged. This is the only c1 behavior change.
3. **c2b acquires the same lock.** Every commit POST and GET path runs inside `proposal_lifecycle_lock(root, draft_id, operation_id)`, loads the commit ledger first (replay before dependencies), then the c1 proposal ledger.
4. **No-artifact invariant preserved.** c1's merged pre-lock fast paths leave zero storage artifacts on terminal no-write outcomes; c2b must match: if the c1 proposal ledger file is absent, POST confirm returns `publication_commit_proposal_not_active` (`409`) before entering the lock and writes nothing; GET on an absent commit ledger returns `publication_commit_not_found` (`404`) before entering the lock and writes nothing. A legitimate claim is only possible when the c1 ledger exists, which means the operation directory and `.proposal.lock` already exist — the commit flow introduces no new artifact on any path.

Lock order (actual, frozen):

```text
proposal lifecycle lock (.proposal.lock)
→ commit ledger unlocked read/write
→ c1 proposal ledger unlocked read
→ SBW09b identity read (acquires the SBW09b identity lock internally)
→ SBW09a publication refresh/read (acquires the SBW09a publication lock internally)
→ exact graph read / Kernel world-write CAS (Kernel-internal)
```

No predecessor or Kernel path may call back into proposal/commit storage. No second application lock may reverse this order. The Kernel never imports application storage, so no cycle exists.

Supersession/confirmation race is serializable:

- supersession wins the lock first: either no commit record exists yet (supersession proceeds; the later confirm then observes the proposal inactive and writes no intent) or one exists (supersession is refused with `publication_proposal_commit_claimed`);
- c2b wins the lock first and persists any commit record: supersession is refused permanently;
- therefore a superseded proposal never also owns a commit record, and a claimed proposal is never superseded.

If this seam cannot be implemented without changing c1's durable proposal schemas or adding a second lock, stop (§16) — do not introduce a check-then-act gap.

## §8 Exact commit and recovery algorithm

### §8.1 Replay before dependencies

Under the lifecycle lock, load the commit ledger before proposal, predecessor, or graph reads.

- exact `committed_verified`: return record;
- exact `committed_unverified`: verification only;
- exact `committing`: recovery first (§8.4); never blindly merge;
- exact `uncommitted` or `ambiguous`: return terminal record;
- same commit ID with changed request digest: conflict; bytes unchanged;
- different commit ID when any record exists: busy/conflict.

### §8.2 New admission

1. Load the exact c1 proposal from the c1 ledger; require it exists and is the ledger's active proposal.
2. Require request `sealed_proposal_digest` and `expected_parent_revision_id` equal the persisted proposal.
3. Read the exact SBW09b resolution; require active and every shared identity/digest equal to the proposal (`resolution_id`, `source_digest`, `expected_parent_revision_id`; `resolution.request_digest == proposal.resolution_request_digest`; `resolution.candidate_set_digest == proposal.candidate_set_digest`).
4. Refresh/read the exact SBW09a operation; require `ready` and route/source/world/campaign/mechanics/parent equal to the proposal and resolution.
5. Read current head with `kernel.open_world_graph_head(graph_root, world_id)`; require it equals `expected_parent_revision_id` before intent. Mismatch writes no commit record and performs no merge (`publication_commit_parent_mismatch`, `409`).
6. Verify the complete sealed proposal and reconstruct the complete contribution with the exact merged calls:

```text
verify_promote_proposal(
    proposal.sealed_proposal,
    confirming_principal=request.actor,
    expected_parent_revision_id=proposal.expected_parent_revision_id,
)
resolve_merged_contribution_from_package(
    review_package=proposal.sealed_proposal,
    confirming_principal=request.actor,
    world_id_hint=<sealed package world_id>,
    root=graph_root,
    expected_parent_revision_id=proposal.expected_parent_revision_id,
    assertion_ids=None,
    verify_source=False,   # SBW09a/SBW09b are the source authorities; package digest,
                           # principal, parent, effect, contribution meta, node map,
                           # and identity snapshot remain verified
)
```

7. Whole proposal only. Require the reconstructed `contribution.contribution_id == proposal.expected_contribution_id`, its accepted assertion IDs equal `proposal.accepted_assertion_ids` (exact set), and Threat/resource/binding IDs equal §6.2 authority exactly. Any disagreement fails closed before intent.
8. Persist `committing`, `merge_attempt_count=1` before the Kernel call.

### §8.3 Kernel call and exact result taxonomy

Call only:

```text
kernel.merge_contribution_to_revision(
    graph_root,
    world_id=<exact proposal world>,
    contribution=<exact reconstructed contribution>,
    expected_parent_revision_id=<exact proposal parent>,
)
```

No direct graph storage, generic HTTP confirm, mutable-source prepare, contribution supersession, or second merge framework.

The merged Kernel's actual outcomes classify as follows — this table replaces the design-only draft's simpler published/unpublished split:

| Merged Kernel outcome | Signature | c2b classification |
|---|---|---|
| success | `published=true`, `revision_id=R` | persist `committed_unverified` with R immediately, before any audit |
| deterministic refusal, nothing published | `published=false`, `revision_id=null` (e.g. migration-required or validation-failure results; the Kernel has marked its contribution record `failed`) | reconcile once through c2a; zero matches ⇒ persist `uncommitted`; never retry |
| idempotent already-applied no-op | `published=false`, `revision_id=<parent>` plus `idempotent_noop:contribution_already_applied` in `diagnostics` | the exact contribution is already active and applied on head; reconcile through c2a; unique match ⇒ persist `committed_unverified` with `recovered_via_operation_lookup=true`; zero matches ⇒ authority disagreement, persist `ambiguous` (never `uncommitted`) |
| stale parent | `ValueError("stale parent ...")` (raised pre-write by the expected-parent check, or post-CAS-loss with the Kernel's contribution record marked `failed`) | deterministic refusal: reconcile once through c2a; zero matches ⇒ persist `uncommitted`; unique match ⇒ persist `committed_unverified` (a peer published the exact contribution); retry forbidden — the head has provably moved |
| no world head | `WorldGraphNotFoundError` | dependency failure before intent classification: reconcile through c2a; zero matches ⇒ `uncommitted`; treat storage errors per unavailable row |
| transport/process ambiguity | any other exception, missing result, `published=true` with missing `revision_id`, or failed receipt persistence | §8.4 ambiguous-outcome reconciliation |

A result with `published=true` and exact revision ID immediately persists `committed_unverified` before audits. No `published=false` result is ever persisted as `uncommitted` without exactly one c2a reconciliation, because the idempotent no-op proves `published=false` can coexist with a committed immutable revision.

### §8.4 Ambiguous outcome reconciliation

For a Kernel exception, missing result, missing revision ID, failed receipt persistence, or replayed `committing` record, call the merged c2a lookup with:

```text
kernel.find_world_graph_revisions_by_operation_id(
    graph_root,
    world_id=<commit record world_id>,
    operation_id=<commit record expected_contribution_id>,
)
```

The key is the Graph contribution ID because merged Kernel publication records `operation_ids=[to_store.contribution_id]` (`contribution_merge.py`). It is not the SBW09a operation ID, not the c1 proposal ID, and not the c2b commit ID.

| Lookup | Attempt classification | Additional checks | Result |
|---|---|---|---|
| one match | any unresolved path | exact `world_id`, `parent_revision_id == expected_parent_revision_id`, `operation_ids` membership, contribution/effect verification (§9 checks 4–10 against the matched revision) | persist `committed_unverified`, `recovered_via_operation_lookup=true` |
| multiple matches | any | none may be selected; deterministic `(created_at, revision_id)` order is evidence order, never a winner | persist `ambiguous` |
| zero matches | deterministic refusal (§8.3) | none | persist `uncommitted`; no retry |
| zero matches | unresolved `committing`, `merge_attempt_count=1`, current head still equals expected parent | exact same contribution and same expected parent only | persist `merge_attempt_count=2`, make one exact retry |
| zero matches | unresolved `committing` and head changed | retry unsafe | persist `uncommitted` |
| zero matches | unresolved `committing` after second attempt | retry exhausted | persist `uncommitted` |
| `WorldGraphIntegrityError` (manifest world/revision identity mismatch), storage parse/validation failure, or unavailable lookup | any unresolved path | outcome unknown; a corrupt or unreadable store is not "zero matches" | retain `committing`; return unavailable (`503`) |

After the one permitted recovery retry, reconcile through c2a again before classification. No third attempt exists.

Head advance or rollback after commit cannot hide the immutable matching revision — c2a scans the complete store in one enumeration snapshot independent of head. Current head is never substituted for the committed revision ID.

### §8.5 Required receipt-write failure sequence

```text
intent persisted
→ Kernel publishes
→ committed-unverified save fails
→ response unavailable/unknown
→ restart/replay sees committing
→ c2a finds one immutable revision
→ committed-unverified persists
→ verification runs
```

No second merge occurs.

## §9 Exact committed-revision verification

Verification consumes only the commit record, the exact c1 proposal, the reconstructed contribution, and the exact committed revision. Current head is irrelevant once the committed revision is known.

Required checks, pinned to merged public APIs:

1. `find_world_graph_revisions_by_operation_id` returns exactly one matching manifest and its `revision_id` equals the recorded committed revision.
2. That manifest's `world_id`, `revision_id`, `parent_revision_id == expected_parent_revision_id`, and `operation_ids` membership of `expected_contribution_id` are exact; `status == "published"`.
3. The exact revision payload loads through `kernel.load_world_graph_revision_with_integrity` (manifest, payload hash, schema, and content-addressed revision ID all attested).
4. `store.contribution_source_payload_sha256[expected_contribution_id]` equals `kernel.compute_contribution_source_payload_sha256(reconstructed_contribution)`.
5. `store.contribution_replay_manifest` contains exactly one entry for `expected_contribution_id` with `status == "active"` and `source_payload_sha256` equal to the same digest.
6. Every accepted assertion ID has a durable `assertion_support` record naming `expected_contribution_id`. The Kernel rekeys non-canonical assertion IDs at merge and reports `assertion_identity_rekeyed:<old>-><new>` in diagnostics; c1 builds assertions through `kernel.build_assertion` canonical identity, so any rekey entry for this contribution is a verification failure, not a remap.
7. `create_new`: the committed store contains the exact sealed Threat node (`node_id`, `kind=threat`, role, label, aliases, `source_domains`) plus every sealed authored-field attribute with exact values.
8. `connect_existing`: the target Threat node at the committed revision is byte-identical to its exact expected-parent form — no introduced or rewritten identity fields.
9. The external-resource node equals the exact strict `ExternalResourceV1` payload and the full node envelope (`node_id`, `kind=external_resource`, `role=statblock`, label, aliases, `source_domains`) — the same envelope semantics merged c1 preflight enforces.
10. The binding edge equals exact `edge_id`, endpoints, `predicate="uses_statblock"`, `binding_id`, and strict `ThreatStatblockBindingV1` payload.
11. No mechanics body, rules elements, rendered Markdown, or assets enter graph state — recursively scan the committed nodes/edges and the receipt payloads.
12. `kernel.rebuild_from_contributions(graph_root, world_id=..., publish=False, compare_revision_id=<committed>)` reports the `rebuild_equivalent_to_pinned_revision` diagnostic.
13. `kernel.project_world_graph(graph_root, WorldGraphProjectionRequest(world_id, campaign_id, focus=kind:"none", admissibility="gm", revision_pin=<committed>))` reports `projection.snapshot.revision_id == committed` and the exact Threat/resource/binding objects.

| Condition | State | Verification | Merge retry |
|---|---|---|---|
| all checks pass | committed_verified | passed | no |
| exact objects/support pass but rebuild or projection audit is unavailable/degraded | committed_unverified | degraded | no |
| contribution/object/binding/digest/projection mismatch (including any assertion rekey) | committed_unverified | failed | no |
| verification dependency unavailable | committed_unverified | not_started/degraded | no; later verification-only replay |

## §10 Matrices and commit points

### State/fallback

| State | Meaning | POST behavior | Fallback |
|---|---|---|---|
| no record | proposal unclaimed | new admission | none |
| committing | outcome unresolved | c2a reconciliation first | one conditional retry maximum |
| uncommitted | deterministic refusal/unsafe/exhausted | terminal conflict | new operation/proposal |
| ambiguous | multiple matches/integrity ambiguity | terminal conflict | operator repair |
| committed_unverified | revision known | verify only | no merge |
| committed_verified | revision verified | exact replay | none |

### Identity

| Identity | Authority | Fallback |
|---|---|---|
| source/parent | SBW09a snapshot | none |
| Threat target/new ID | SBW09b resolution | none |
| reviewed effect | c1 proposal + sealed package | none |
| contribution | reconstructed ID equal c1 `expected_contribution_id` | none |
| committed revision | Kernel result or unique c2a match | never current head |
| resource/binding | c1 sealed effect + SBW08 models | none |
| replay | commit ID + canonical request digest | none |

### Persistence/replay

| Event | Durable effect | Replay |
|---|---|---|
| admission fails before intent | none (and no storage artifacts, §7) | caller fixes/new request |
| intent saves | proposal permanently claimed | reconcile before merge |
| merge publishes | immutable revision exists | c2a recovers |
| receipt saves | exact committed revision in app ledger | verify only |
| verification saves | terminal/refreshable audit status | no merge |
| ledger corrupt | no further mutation | fail closed |

### Commit points

```text
Application intent point: atomic state=committing save.
Graph commit point: Kernel immutable revision publish/head advance.
Application publication proof: atomic state=committed_unverified save.
Verified completion: atomic state=committed_verified save.

After graph commit, no application failure may make the operation retryable.
```

Prohibited fallbacks: latest mechanics, current draft, latest resolution, labels/rank, current head as committed revision, first immutable match, new parent, new proposal/contribution ID, direct storage scanning, or treating `published=false` as proof that nothing committed without the §8.3 c2a reconciliation.

## §11 Required evidence

| Guarantee | Boundary | Command/evidence |
|---|---|---|
| strict models/state | commit models | `uv run pytest -q tests/test_threat_publication_commit_models.py` |
| claim/commit/recovery/verify | service | `uv run pytest -q tests/test_threat_publication_commits.py` |
| routes | API | `uv run pytest -q tests/test_threat_publication_commit_api.py` |
| proposal supersession blocked | c1 owner | `uv run pytest -q tests/test_threat_publication_proposals.py tests/test_threat_publication_proposal_models.py tests/test_threat_publication_proposal_api.py` |
| c1 regression | predecessor | full merged c1 suite (188-test bundle from PR `#478`) |
| c2a zero/one/many regression | Kernel owner | `uv run pytest -q tests/test_graph_kernel_operation_revision_lookup.py` |
| SBW09a/SBW09b regression | predecessors | focused operation/identity suites |
| SBW08 binding regression | graph contract | `tests/test_statblock_binding_graph_contract.py` |
| sealed proposal/contribution | governance | current promote proposal/ops suites |
| Kernel merge/rebuild/projection | Kernel | current focused suites |
| scope/hygiene | repository | `git diff --check`; exact name-only diff |

Required adversarial sequences:

1. Create-new commit → receipt → exact verification → restart GET.
2. Connect-existing commit has no Threat identity rewrite.
3. Request cannot select assertions.
4. Exact terminal replay returns before dependencies.
5. Changed replay conflicts with byte-identical ledger.
6. Concurrent first confirmations yield one record and at most one merge.
7. Proposal supersession/confirmation race is serializable: supersession-first wins and confirm refuses pre-intent; claim-first wins and supersession returns `publication_proposal_commit_claimed`.
8. Crash after intent: zero lookup + unchanged parent permits exactly one retry.
9. Deterministic `published=false` (`revision_id=null`): zero lookup persists uncommitted with zero retry.
10. Idempotent no-op (`published=false`, `revision_id=<parent>`, `idempotent_noop:*` diagnostic): unique lookup match persists committed-unverified, never uncommitted.
11. Stale-parent `ValueError`: zero lookup persists uncommitted; no retry even though attempts remain.
12. Crash after graph commit: one lookup match recovers without merge.
13. Head advance and rollback do not hide committed revision.
14. Duplicate matches persist ambiguity; no first-win even though c2a ordering is deterministic.
15. Lookup unavailable/corrupt (including `WorldGraphIntegrityError` from manifest identity mismatch) retains committing; no merge, no uncommitted.
16. Exception or missing revision ID reconciles before retry.
17. Verification failure after commit remains committed-unverified.
18. Assertion-rekey diagnostic from the Kernel fails verification instead of remapping.
19. Crash after committed-unverified verifies only on replay.
20. Ledger write failure before intent makes no graph call.
21. Receipt write failure after commit recovers after restart without duplicate merge.
22. Corrupt ledger fails closed.
23. Pre-lock terminal paths (missing c1 ledger on POST, missing commit ledger on GET) create zero commit/proposal storage artifacts.
24. Predecessor/mechanics/proposal bytes remain unchanged except the §7 commit-claim gate.

Baseline-red commands require identical base/head comparison and explicit waiver. Do not claim repository-wide CI unless attached checks exist. The four pre-existing main-line failures documented in `Backlog.md` (projection/boundary baselines) are not c2b-caused; they require the same base/head proof if cited.

## §12 Re-anchor amendment record and dispatch gate

This amendment replaces the design-only draft (draft PR `#474`, pre-merge head `0ffa7fca`) with the actual merged contracts. Material corrections, each a tightening or a factual pin — none weakens exact identity, intent-before-write, deterministic-refusal terminality, immutable recovery, plural ambiguity, or committed-but-unverified guarantees:

| # | Design-only assumption | Re-anchored actual |
|---|---|---|
| 1 | "actual merged SBW09c1/c2a; currently only designed" | c1 merged PR `#478` (`c15420e6`, head `f0e85b4e`); c2a merged PR `#476` (`c6e867ed`, head `bf3aba87`); §2 names the exact models, functions, routes, labels, and storage |
| 2 | Hypothetical `claim_threat_publication_proposal_lifecycle` helper | Actual merged `_proposal_lock` exposed through a public alias with unchanged semantics; the supersession commit-claim gate lands inside `prepare_threat_publication_proposal` under that lock (§7) |
| 3 | Provisional allowlist touched only the c1 service | Revalidated allowlist adds `models/threat_publication_proposal.py` and `routes/threat_publication_proposals.py` for exactly one new label (`publication_proposal_commit_claimed` → `409`), plus the owning c1 test files |
| 4 | "A typed `published=false` result is not a transport ambiguity" (implied: nothing published) | §8.3 taxonomy corrects this: the merged Kernel also returns `published=false` with `revision_id=<parent>` for the idempotent already-applied no-op, and raises `ValueError("stale parent ...")` rather than returning a typed refusal; every `published=false` reconciles through c2a exactly once before any `uncommitted` persistence |
| 5 | c2a signature provisional ("naming may change") | Exact merged signature `find_world_graph_revisions_by_operation_id(root, world_id, operation_id) -> tuple[WorldGraphRevision, ...]`; `(created_at, revision_id)` evidence ordering; `ValueError` on blank operation ID; `WorldGraphIntegrityError` on manifest world/revision identity mismatch (the merged hardening); lookup errors are never "zero matches" |
| 6 | Recovery key justified by design | Confirmed in merged code: publish records `operation_ids=[to_store.contribution_id]` in `contribution_merge.py`; the c2a key is the proposal's `expected_contribution_id` |
| 7 | Commit record had no `world_id` | `world_id` added (from the sealed package) so a post-restart record is self-sufficient for the c2a recovery call |
| 8 | `binding_id` source unspecified | Pinned: sealed package binding edge value, cross-checked against `compute_binding_id` and `edge_id_from_binding_id == effect_summary.binding_edge_id` (§6.2) |
| 9 | `merge_attempt_count: 0..2` | Tightened to `1..2`: the first durable state is always `committing` with count 1 |
| 10 | Response envelope unspecified | §6.4 envelope with the merged c1 no-sentinel precedent: unknown identities are `null` (c1 returns `resolution_id=null` on GET failure paths), never all-zero UUIDs; `retry_allowed` is explicit |
| 11 | Verification calls described generically | §9 pins the exact merged calls: `load_world_graph_revision_with_integrity`, `compute_contribution_source_payload_sha256`, `contribution_replay_manifest`, `assertion_support`, `rebuild_from_contributions(compare_revision_id=...)` + `rebuild_equivalent_to_pinned_revision`, `project_world_graph(revision_pin=...)` with the SBW09b request-model import seam; Kernel assertion rekeying is a verification failure, not a remap |

Dispatch gate — all must hold before implementation begins:

- [x] c1 implementation merged with exact SHA; actual models/fields/service/lock/routes/tests reviewed (PR `#478`).
- [x] c2a implementation merged with exact SHA; actual public signature/export/plural semantics/tests reviewed (PR `#476`).
- [x] This file amended to replace provisional names/assumptions with actual contracts.
- [x] §4 allowlist revalidated and narrowed against merged code.
- [x] Tracker/roadmap mark c1+c2a complete and c2b sole next publication implementation (this PR).
- [ ] This amendment merges; post-merge authority sync records the immutable `origin/main` dispatch SHA in this header.
- [ ] One implementation PR dispatches from that exact SHA on `feat/sbw09c2b-threat-publication-commit-recovery`.

Any required Kernel write/CAS, c1 durable-schema, or c2a semantic change discovered during implementation is a stop (§16) and becomes a predecessor slice — it is not fixed inside the c2b PR.

## §13 Required implementation handback

Record exact base/head and ancestry; changed paths/diff; the actual c1 lock alias and supersession gate diff; the c2a signature used; JSON examples of request/record/response; every §11 result and provenance; Kernel merge-call counts per scenario (must be 0 or 1 per path, 2 only for the sanctioned recovery retry); unique recovery revision; zero/one/many plus head advance/rollback evidence; idempotent no-op and stale-parent classification evidence; exact Threat/resource/binding verification; committed-unverified examples proving no retry; predecessor/proposal/mechanics before/after bytes; the §7 no-artifact matrix; baseline waivers; out-of-scope paths; and confirmation UI/Hermes/projection/placement/combat remain false.

## §14 Acceptance rubric

- [ ] Re-anchored authority merged and dispatch SHA recorded before implementation.
- [ ] One active proposal owns at most one commit record.
- [ ] Supersession and confirmation share the actual c1 lifecycle lock; supersession after any commit record returns `publication_proposal_commit_claimed`.
- [ ] Intent is durable before the Kernel call.
- [ ] Whole sealed proposal is verified; reconstructed contribution ID equals `expected_contribution_id`; no subset exists.
- [ ] Deterministic refusal is never retried; stale-parent `ValueError` is a deterministic refusal.
- [ ] Idempotent no-op is never persisted as uncommitted without a c2a reconciliation.
- [ ] At most two attempts exist: initial plus one unresolved zero-match recovery retry.
- [ ] Every ambiguous outcome checks c2a before retry; lookup errors are never treated as zero matches.
- [ ] Unique recovery validates exact parent/contribution/effect.
- [ ] Multiple matches remain ambiguous despite deterministic result ordering.
- [ ] Current head is never substituted for committed revision.
- [ ] Known committed revision permanently prohibits merge retry.
- [ ] Committed-unverified is durable and truthfully exposed with `retry_allowed=false`.
- [ ] Exact revision verifies digest/replay-manifest/support, Threat/resource/binding, rebuild, projection.
- [ ] No mechanics body enters graph state.
- [ ] Responses carry no sentinel identities; unknown fields are `null`.
- [ ] Storage is path-safe, atomic, bounded, restart-safe, corruption-closed; terminal pre-lock paths create zero artifacts.
- [ ] No production path outside the amended allowlist changes.
- [ ] UI/query/projection/placement/combat remain false.

## §15 Reviewer attack list

- Race proposal supersession between admission and intent, in both directions.
- Count merge calls across replay, concurrency, refusal, exception, and crash seams.
- Search for current-head substitution, repinning, first match, `next(...)`, label lookup, or mutable draft reads.
- Verify the c2a key is `expected_contribution_id`, not the SBW09a operation ID, proposal ID, or commit ID.
- Prove `published=false` with `revision_id` set (idempotent no-op) reconciles through c2a and never persists uncommitted on a unique match.
- Prove stale-parent `ValueError` never consumes the recovery retry.
- Delete the immediate receipt after synthetic publish and require restart recovery.
- Advance and roll back head before recovery.
- Seed duplicate operation IDs and ensure no revision is selected despite deterministic ordering.
- Fail every atomic ledger save point.
- Corrupt a manifest's embedded world/revision identity and prove the lookup surfaces `WorldGraphIntegrityError`, retaining `committing`.
- Return typed unpublished results in every §8.3 class and prove classification.
- Inject an assertion-rekey diagnostic and prove verification fails rather than remaps.
- Fail verification after publication and prove no merge retry.
- Inspect connect-existing for unintended Threat rewrites.
- Recursively scan graph/receipt payloads for mechanics bodies.
- Verify application code uses public Kernel APIs and the SBW09b projection request-model seam, not storage/contribution-store internals.
- Verify GET failure responses carry `proposal_id=null` and no sentinel UUIDs.
- Verify pre-lock terminal paths leave no new directories or lock files.

## §16 Stop conditions

Stop if: the public lock alias or supersession gate cannot be added without changing c1 durable schemas; c1 lacks exact effect identity needed for verification; c2a cannot recover independent of head; recovery requires choosing among multiple matches; contribution reconstruction requires mutable state; safe commit requires Kernel write/CAS changes; exact verification requires storage-internal application imports; any committed outcome can become retryable; a production path outside the amended allowlist is required; later UI/Hermes/placement/combat/generic publication enters scope; or an unwaived owning-boundary regression appears.
