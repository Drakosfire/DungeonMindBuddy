---
pr_body_template: |
  ## Outcome
  The live-control server can explicitly confirm one exact active Threat publication proposal into one exact World Graph contribution and immutable revision, preserve durable commit intent and receipt across response loss or restart, recover ambiguous outcomes through exact immutable revision lookup, and verify the exact Threat/resource/binding result without repinning or recommitting a known publication.

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
  - Design base: `573698b00028949741786db3361fd1d14d5a8906`
  - Dispatch base: {{TODO exact immutable main SHA after c1+c2a merge and this handoff is re-anchored}}
  - Actual base/head: {{TODO}}
  - Actual changed paths: {{TODO}}
  - Deferred: Workbench confirmation UI, Hermes query/hydration, Threat projection surface, placement, combat, mechanics revision adoption, and generic object publication.

  ## Evidence produced
  {{TODO}}

  ## Gaps, waivers, and stop conditions
  {{TODO: none, or exact stop report}}
---

# HANDOFF — SBW09c2b proposal-bound Threat commit, recovery, and exact verification

**Created:** 2026-08-01  
**Status:** DESIGNED / BLOCKED — implementation dispatch is prohibited until SBW09c1 and SBW09c2a implementations merge and this handoff receives an exact current-main re-anchor amendment.  
**Canonical path:** `Docs/Plans/HANDOFF-sbw09c2b-threat-publication-commit-recovery.md`  
**Design base:** `573698b00028949741786db3361fd1d14d5a8906`  
**Dispatch base:** not yet assigned; it must be the immutable main SHA containing the post-c1/post-c2a re-anchor amendment.  
**Suggested implementation branch:** `feat/sbw09c2b-threat-publication-commit-recovery`

> This document freezes the intended commit/recovery boundary. It is not implementation authority until the dispatch gate in §12 is satisfied against the actual merged c1 proposal and c2a lookup contracts.

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

A graph-writing endpoint is not safe merely because `merge_contribution_to_revision` is atomic. The application must know whether it already dispatched the exact contribution, prevent proposal supersession while the outcome is unresolved, recover an immutable revision after response loss, and never report preview material as durable without checking the exact committed revision. Intent, the bounded merge attempt, immediate receipt persistence, recovery, and verification therefore share one invariant.

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

- Most likely race: proposal supersession occurs after confirmation begins but before commit intent becomes durable.
- Most dangerous retry bug: stale-parent handling blindly re-merges or records current head as the committed revision.
- Most dangerous refusal bug: a typed `published=false` result is misclassified as transport ambiguity and consumes the crash-recovery retry.
- Most dangerous receipt bug: publication succeeds, receipt persistence fails, and a later request treats the proposal as uncommitted.
- Required defense: one shared lifecycle lock, intent-before-write, deterministic-refusal terminality, c2a-before-retry, immutable verification, and no-retry semantics once a committed revision is known.
- Split trigger: actual c1 cannot expose a semantic shared lock/claim boundary without changing its durable proposal contract.

## §2 Authority and dependency map

| Concern | Authority |
|---|---|
| Source and expected parent | SBW09a merged PR `#462` |
| Threat identity decision | SBW09b merged PR `#467` |
| Exact reviewed effect | actual merged SBW09c1 implementation; currently only designed |
| Operation-to-revision recovery | actual merged SBW09c2a public Kernel lookup; currently only designed |
| Resource/binding identity | SBW08 merged PR `#457` |
| Proposal seal/verification | `graph_memory.extract_promote_proposal` |
| Contribution reconstruction | `resolve_merged_contribution_from_package` or actual merged c1 adapter |
| Graph commit | public `graph_memory.kernel.merge_contribution_to_revision` |
| Exact revision reads | public Graph Kernel revision/integrity/rebuild/projection APIs |
| Sequence | active Threat tracker and roadmap |

Read after the dispatch gate:

1. `AGENTS.md` and external-agent PR-loop rules.
2. active tracker, roadmap, publication re-anchor, and this amended handoff.
3. merged c1 models/service/routes/tests and handback.
4. merged c2a public function/export/tests and handback.
5. SBW09a/SBW09b owning services and tests.
6. SBW08 resource/binding models and tests.
7. proposal verification and contribution reconstruction owners.
8. public Kernel contribution, revision, rebuild, and projection APIs.
9. generic extract-promote confirmation only as precedent; do not copy current-head recovery shortcuts.

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
| Proposal supersession racing confirmation | either supersession wins before claim or commit claim wins; never both | shared lifecycle lock |
| Crash after intent, before/around merge | c2a zero; one exact retry only if attempt remains unresolved and parent unchanged | recovery state machine |
| Deterministic merge refusal | c2a reconciliation; zero match becomes terminal uncommitted; no retry | commit service |
| Crash after commit, before receipt | unique immutable match recovers; no merge | c2a + ledger |
| Head advances or rolls back after commit | recover exact immutable committed revision | c2a |
| Multiple matching revisions | integrity ambiguity; no first-win receipt | c2a caller policy |
| Lookup unavailable/corrupt | remain unresolved `committing`; no merge | recovery state machine |
| Verification fails after publication | persist committed-unverified; retry forbidden | verifier |
| Restart/read | exact record round-trips under lifecycle lock | ledger/GET |
| Corrupt commit ledger | fail closed; no repair/overwrite | parser/store |
| UI/Hermes/product projection | absent | successors |

## §4 Provisional implementation allowlist

This allowlist must be revalidated against actual c1/c2a merges.

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live_control_server/models/threat_publication_commit.py` | strict request, record, ledger, response models |
| Create | `apps/live_control_server/services/threat_publication_commit_store.py` | path-safe atomic ledger reads/writes; no independent lock |
| Create | `apps/live_control_server/services/threat_publication_commits.py` | claim, commit, recovery, verification orchestration |
| Create | `apps/live_control_server/routes/threat_publication_commits.py` | POST confirm and GET exact record |
| Modify | `apps/live_control_server/services/threat_publication_proposals.py` | shared lifecycle lock/claim seam; block supersession after claim |
| Modify | `apps/live_control_server/main.py` | route registration |
| Create | `tests/test_threat_publication_commit_models.py` | model/state/ledger invariants |
| Create | `tests/test_threat_publication_commits.py` | service, persistence, recovery, concurrency, verification |
| Create | `tests/test_threat_publication_commit_api.py` | route/status/result contracts |
| Modify | `tests/test_threat_publication_proposals.py` | supersession blocked after commit claim |

Bounded test-only discovery exception:

```text
Directory: tests/
Maximum additional paths: 2
Allowed: existing shared fixtures/helpers or route-registration test only
Rule: no additional production scope
Report: exact paths and why local fixtures were insufficient
```

Stop before implementation if actual names differ materially, c1 has no operation-scoped lifecycle lock, or c2a's merged signature/semantics differ. Amend rather than guess.

Production changes under `src/graph_memory/**`, SBW09a/SBW09b models/stores, ThreatDraft, accepted-mechanics persistence, DungeonMind, UI, corpus, placement, or combat are prohibited.

## §5 Exclusions and demolition

Excluded: proposal construction, identity selection, assertion subsets, parent/mechanics repinning, retries under a new operation/proposal, current-head receipt inference, first-match selection, UI confirmation, Hermes write/query/hydration, Threat projection UI, placement/combat, generic publication, supersession/retraction, and undo.

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
commit_id: UUID or bounded tcommit_<token>
sealed_proposal_digest: exact persisted c1 sealed_proposal_digest
expected_parent_revision_id: exact persisted c1/SBW09a parent
actor: nonblank bounded string
operator_note: optional bounded string
```

Route identity supplies `draft_id`, `operation_id`, and `proposal_id`. The canonical request digest includes every route identity and request field.

The request must not accept assertion IDs, world/campaign/root, identity/target IDs, resource/binding IDs, mechanics locators/bodies, `dry_run`, live-world permission, idempotency policy, or a replacement parent.

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
resolution_id
source_digest
resolution_request_digest
candidate_set_digest
expected_parent_revision_id
expected_contribution_id
accepted_assertion_ids
decision: create_new | connect_existing
threat_node_id
external_resource_node_id
binding_id
binding_edge_id
state: committing | uncommitted | ambiguous | committed_unverified | committed_verified
merge_attempt_count: 0..2
committed_revision_id: optional exact revision
recovered_via_operation_lookup: bool
verification_status: not_started | passed | degraded | failed
verification_codes: bounded ordered list
warnings: bounded ordered list
created_by
operator_note
created_at
updated_at
```

The exact effect fields are extracted from and validated against the durable c1 proposal and its sealed effect. They are never reconstructed from mutable draft, label, mechanics store, or current head.

State invariants:

- `committing`: no committed revision; attempt count is 1 or 2; outcome remains unresolved.
- `uncommitted`: no committed revision; deterministic refusal, unsafe retry, or exhausted recovery; terminal for this claim.
- `ambiguous`: no selected revision; multiple immutable matches or integrity ambiguity; terminal pending external repair.
- `committed_unverified`: committed revision required; merge retry prohibited.
- `committed_verified`: committed revision required; verification passed; merge retry prohibited.
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

There is no `.commit.lock`. The c1 operation-scoped `.proposal.lock` is the sole proposal/commit lifecycle lock. The commit store exposes dependency-neutral unlocked low-level reads/writes legal only while that semantic lock is held; it must not import the proposal service.

One operation has at most one commit record. A terminal uncommitted record is not cleared to reuse the proposal; a new parent requires a new SBW09a operation, resolution, and proposal.

### §6.4 Routes and results

```text
POST /api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/proposals/{proposal_id}/commits
GET  /api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/commits/{commit_id}
```

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

## §7 Shared proposal claim and lock

The actual c1 proposal service must expose a semantic context/helper equivalent to:

```python
with claim_threat_publication_proposal_lifecycle(
    repo_root, draft_id, operation_id
) as claim:
    ...
```

Names may follow c1 conventions; semantics may not:

1. acquire the exact operation-scoped c1 proposal lock;
2. permit active-proposal and commit-ledger loads under that lock;
3. permit c2b atomic commit-record writes;
4. require c1 supersession to inspect commit-record existence under the same lock;
5. refuse supersession once any commit record exists;
6. require GET and POST commit-record reads/writes under this same lock;
7. release only after the current state transition, Kernel call/recovery, immediate receipt persistence, and any attempted verification persistence complete or fail safely.

Lock order:

```text
proposal lifecycle lock
→ commit ledger unlocked read/write
→ SBW09b identity read
→ SBW09a publication refresh/read
→ exact graph read / Kernel world-write lock
```

No predecessor or Kernel path may call back into proposal/commit storage. No second application lock may reverse this order.

Supersession/confirmation race must be serializable:

- supersession wins lock first: c2b observes proposal inactive and writes no intent;
- c2b wins and persists any commit record: supersession is refused permanently;
- a superseded proposal never also owns a commit record.

If holding the lifecycle lock across the Kernel call is incompatible with actual c1, stop rather than introduce a check-then-act gap.

## §8 Exact commit and recovery algorithm

### §8.1 Replay before dependencies

Under the lifecycle lock, load the commit ledger before proposal, predecessor, or graph reads.

- exact `committed_verified`: return record;
- exact `committed_unverified`: verification only;
- exact `committing`: recovery first; never blindly merge;
- exact `uncommitted` or `ambiguous`: return terminal record;
- same ID with changed request: conflict; bytes unchanged;
- different ID when any record exists: busy/conflict.

### §8.2 New admission

1. Load exact c1 proposal; require it is active.
2. Require request sealed digest and parent equal persisted proposal.
3. Read exact SBW09b resolution; require active and all identities/digests equal proposal.
4. Refresh/read exact SBW09a operation; require ready and route/source/world/campaign/mechanics/parent equal proposal and resolution.
5. Require current head equals expected parent before intent. Mismatch writes no commit record and performs no merge.
6. Verify complete sealed proposal and reconstruct complete contribution with existing authority. File-source verification may be disabled only because SBW09a/SBW09b are the source authorities; package digest, principal, parent, effect, contribution meta, node map, and identity snapshot remain verified.
7. Whole proposal only. Reconstructed contribution ID, accepted IDs, Threat/resource/binding IDs, and parent equal c1 authority exactly.
8. Persist `committing`, `merge_attempt_count=1` before the Kernel call.

### §8.3 Kernel call

Call only:

```text
kernel.merge_contribution_to_revision(
  configured world root,
  world_id=exact proposal world,
  contribution=exact reconstructed contribution,
  expected_parent_revision_id=exact proposal parent,
)
```

No direct graph storage, generic HTTP confirm, mutable-source prepare, contribution supersession, or second merge framework.

A result with `published=true` and exact revision ID immediately persists `committed_unverified` before audits.

A typed deterministic `published=false` result is not a transport ambiguity. Reconcile once through c2a in case authority exists despite the return; if zero matches, persist `uncommitted` and do not retry.

### §8.4 Ambiguous outcome reconciliation

For a Kernel exception, missing result, missing revision ID, failed receipt persistence, or replayed `committing` record, call c2a with:

```text
world_id = exact proposal world
operation_id = proposal.expected_contribution_id
```

The key is the Graph contribution ID because Kernel publication records `operation_ids=[contribution.contribution_id]`. It is not the SBW09a operation ID.

| Lookup | Attempt classification | Additional checks | Result |
|---|---|---|---|
| one match | any unresolved path | exact world, parent, operation membership, contribution/effect | persist committed-unverified, recovered=true |
| multiple matches | any | none may be selected | persist ambiguous |
| zero matches | deterministic refusal | none | persist uncommitted; no retry |
| zero matches | unresolved committing, attempts=1, current head still original parent | exact same contribution only | persist attempts=2, make one retry |
| zero matches | unresolved committing and head changed | retry unsafe | persist uncommitted |
| zero matches | unresolved committing after second attempt | retry exhausted | persist uncommitted |
| lookup unavailable/corrupt | any unresolved path | outcome unknown | retain committing; return unavailable |

After the one permitted recovery retry, reconcile through c2a again before classification. No third attempt exists.

Head advance or rollback after commit cannot hide the immutable matching revision. Current head is never substituted for committed revision ID.

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

Verification consumes only the commit record, exact c1 proposal, reconstructed contribution, and exact committed revision.

Required checks:

1. c2a returns exactly one matching manifest and it is the recorded revision.
2. Manifest world, revision, parent, and operation membership are exact.
3. Exact revision payload loads through public integrity authority.
4. `contribution_source_payload_sha256[expected_contribution_id]` equals the public digest of the exact reconstructed contribution.
5. `contribution_replay_manifest` contains one active exact contribution/digest entry.
6. Every accepted assertion support record names the exact contribution ID.
7. Create-new contains the exact sealed Threat node and authored fields.
8. Connect-existing does not introduce or rewrite target Threat identity fields.
9. External-resource node equals exact strict `ExternalResourceV1`.
10. Binding edge equals exact ID/endpoints/predicate/binding ID/`ThreatStatblockBindingV1`.
11. No mechanics body, rules elements, rendered Markdown, or assets enter graph state.
12. Exact committed-revision rebuild reports equivalence.
13. Exact revision-pinned projection reports the same revision and exact Threat/resource/binding.

Current head is irrelevant after committed revision is known.

| Condition | State | Verification | Merge retry |
|---|---|---|---|
| all checks pass | committed_verified | passed | no |
| exact objects/support pass but rebuild or secondary audit is unavailable/degraded | committed_unverified | degraded | no |
| contribution/object/binding/digest/projection mismatch | committed_unverified | failed | no |
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
| contribution | reconstructed ID equal c1 expected ID | none |
| committed revision | Kernel result or unique c2a match | never current head |
| resource/binding | c1 sealed effect + SBW08 models | none |
| replay | commit ID + canonical request digest | none |

### Persistence/replay

| Event | Durable effect | Replay |
|---|---|---|
| admission fails before intent | none | caller fixes/new request |
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

Prohibited fallbacks: latest mechanics, current draft, latest resolution, labels/rank, current head as committed revision, first immutable match, new parent, new proposal/contribution ID, or direct storage scanning.

## §11 Required evidence

| Guarantee | Boundary | Command/evidence |
|---|---|---|
| strict models/state | commit models | `uv run pytest -q tests/test_threat_publication_commit_models.py` |
| claim/commit/recovery/verify | service | `uv run pytest -q tests/test_threat_publication_commits.py` |
| routes | API | `uv run pytest -q tests/test_threat_publication_commit_api.py` |
| proposal supersession blocked | c1 owner | focused c1 proposal tests |
| c1 regression | predecessor | actual merged c1 suites |
| c2a zero/one/many regression | Kernel owner | actual merged c2a suite |
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
7. Proposal supersession/confirmation race is serializable.
8. Crash after intent: zero lookup + unchanged parent permits exactly one retry.
9. Deterministic `published=false`: zero lookup persists uncommitted with zero retry.
10. Crash after graph commit: one lookup match recovers without merge.
11. Head advance and rollback do not hide committed revision.
12. Duplicate matches persist ambiguity; no first-win.
13. Lookup unavailable retains committing; no merge.
14. Exception or missing revision ID reconciles before retry.
15. Verification failure after commit remains committed-unverified.
16. Crash after committed-unverified verifies only on replay.
17. Ledger write failure before intent makes no graph call.
18. Receipt write failure after commit recovers after restart without duplicate merge.
19. Corrupt ledger fails closed.
20. Predecessor/mechanics/proposal bytes remain unchanged except commit-claim behavior.

Baseline-red commands require identical base/head comparison and explicit waiver. Do not claim repository-wide CI unless attached checks exist.

## §12 Dispatch gate and re-anchor amendment

Implementation must not begin from this design-only handoff. Dispatch requires:

- c1 implementation merged with exact SHA, actual models/fields/service/lock/routes/tests/handback reviewed;
- c2a implementation merged with exact SHA, actual public signature/export/plural semantics/tests reviewed;
- this file amended to replace provisional names/assumptions with actual contracts;
- §4 allowlist revalidated and narrowed;
- tracker/roadmap mark c1+c2a complete and c2b sole next publication implementation;
- amendment records immutable dispatch SHA and proves no lock-order/scope conflict;
- any required Kernel write/CAS, c1 durable-schema, or c2a semantic change is handled as a predecessor slice.

The amendment may tighten but not weaken exact identity, intent-before-write, deterministic-refusal terminality, immutable recovery, plural ambiguity, or committed-but-unverified guarantees.

## §13 Required implementation handback

Record exact base/head and ancestry; changed paths/diff; actual c1 lock seam and c2a signature; JSON examples; every §11 result/provenance; Kernel merge-call counts; unique recovery revision; zero/one/many plus head advance/rollback evidence; exact Threat/resource/binding verification; committed-unverified examples proving no retry; predecessor/proposal/mechanics before/after bytes; baseline waivers; out-of-scope paths; and confirmation UI/Hermes/projection/placement/combat remain false.

## §14 Acceptance rubric

- [ ] Actual c1/c2a contracts re-anchored before implementation.
- [ ] One active proposal owns at most one commit record.
- [ ] Supersession and confirmation share one serializable lifecycle lock.
- [ ] Intent is durable before Kernel call.
- [ ] Whole sealed proposal is verified; no subset exists.
- [ ] Deterministic refusal is never retried.
- [ ] At most two attempts exist: initial plus one unresolved zero-match recovery retry.
- [ ] Every ambiguous outcome checks c2a before retry.
- [ ] Unique recovery validates exact parent/contribution/effect.
- [ ] Multiple matches remain ambiguous.
- [ ] Current head is never substituted for committed revision.
- [ ] Known committed revision permanently prohibits merge retry.
- [ ] Committed-unverified is durable and truthfully exposed.
- [ ] Exact revision verifies digest/replay/support, Threat/resource/binding, rebuild, projection.
- [ ] No mechanics body enters graph state.
- [ ] Storage is path-safe, atomic, bounded, restart-safe, corruption-closed.
- [ ] No production path outside amended allowlist changes.
- [ ] UI/query/projection/placement/combat remain false.

## §15 Reviewer attack list

- Race proposal supersession between admission and intent.
- Count merge calls across replay, concurrency, refusal, exception, and crash seams.
- Search for current-head substitution, repinning, first match, `next(...)`, label lookup, or mutable draft reads.
- Verify c2a key is expected contribution ID, not SBW09a operation ID.
- Delete immediate receipt after synthetic publish and require restart recovery.
- Advance and roll back head before recovery.
- Seed duplicate operation IDs and ensure no revision is selected.
- Fail every atomic ledger save point.
- Return typed unpublished result and prove no recovery retry.
- Fail verification after publication and prove no merge retry.
- Inspect connect-existing for unintended Threat rewrites.
- Recursively scan graph/receipt payloads for mechanics bodies.
- Verify application code uses public Kernel APIs, not storage/contribution-store internals.

## §16 Stop conditions

Stop if actual c1 cannot expose a safe shared lifecycle lock; c1 lacks exact effect identity needed for verification; c2a cannot recover independent of head; recovery requires choosing among multiple matches; contribution reconstruction requires mutable state; safe commit requires Kernel write/CAS changes; exact verification requires storage-internal application imports; any committed outcome can become retryable; a production path outside amended allowlist is required; later UI/Hermes/placement/combat/generic publication enters scope; or an unwaived owning-boundary regression appears.
