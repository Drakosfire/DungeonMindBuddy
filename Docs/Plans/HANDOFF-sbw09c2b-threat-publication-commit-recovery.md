---
pr_body_template: |
  ## Outcome
  The live-control server can explicitly confirm one exact active Threat publication proposal into one exact World Graph contribution and immutable revision, preserve durable commit intent and receipt across response loss or restart, recover ambiguous outcomes through exact immutable revision lookup, and verify the exact Threat/resource/binding result without ever repinning or recommitting a known publication.

  ## Merge-ready invariant
  For one exact active SBW09c1 proposal, at most one durable commit record can claim it; the record binds the exact proposal digest, expected parent, contribution ID, accepted assertion set, Threat identity, external resource, and binding. The service persists intent before the single Kernel merge, persists committed-unverified authority immediately when publication is proven, resolves crashes through the SBW09c2a exact contribution-ID lookup before any retry, never selects the first of multiple matches, and never retries after a committed revision is known. Verification is pinned to that immutable revision, and verification failure remains committed-but-unverified rather than becoming a second write.

  ## Evidence required to merge
  | Guarantee | Owning boundary | Required evidence | Result |
  |---|---|---|---|
  | One proposal claim and one commit record | shared proposal lifecycle lock + commit ledger | concurrency and proposal-supersession race matrix | {{TODO}} |
  | Intent-before-write and exact single merge | commit service | injected crash/write/merge sequences | {{TODO}} |
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
| Add GM-facing confirmation UI | Yes | Product surface | SBW09c2c or successor after backend proof |
| Query/hydrate/project the published Threat | Yes | Consumer contracts | SBW10a/SBW10b |
| Generalize publication to every object type | Yes | Generic framework | Reject for this slice |

**Selected capability:** one proposal-bound, durable, recoverable backend commit path that truthfully distinguishes uncommitted, ambiguous, committed-unverified, and committed-verified outcomes.

### Why the included work is one invariant

A graph-writing endpoint is not safe merely because `merge_contribution_to_revision` is atomic. The application must know whether it already asked the Kernel to publish, must prevent the proposal from being superseded while that outcome is unresolved, must recover a revision when the process dies after head advance, and must never report preview material as durable without checking the exact committed revision. Intent, the single merge, immediate receipt persistence, recovery, and verification are therefore one publication invariant.

### Mission falsification test

This is not one slice if implementation also requires a Workbench UI, mechanics mutation, identity reselection, parent repinning, a generic graph editor, a second Graph Kernel, a new revision index beyond SBW09c2a, or changes to World Graph write/CAS semantics.

## §1 Mission and merge-ready invariant

```text
One exact active Threat publication proposal can be explicitly confirmed into
one exact immutable World Graph revision with a durable commit record that
survives response loss and restart, recovers an ambiguous outcome from immutable
revision authority, and verifies the exact Threat/resource/binding result at the
committed revision without a latest/current-head fallback or duplicate write.
```

```text
For one exact active SBW09c1 proposal, at most one durable commit record can claim
it; the record binds the exact proposal digest, expected parent, contribution ID,
accepted assertion set, Threat identity, external resource, and binding. Intent is
persisted before the single Kernel merge. Publication proof is persisted as
committed_unverified immediately when an exact immutable revision is known.
Recovery resolves the expected contribution ID through SBW09c2a before any retry,
multiple matches remain an integrity ambiguity, and no merge occurs after a
committed revision is known. Verification is pinned to that revision; degraded or
failed verification remains committed-but-unverified and never becomes a retry.
```

### Pre-dispatch critique

- Most likely race: proposal supersession occurs after confirmation begins but before the commit record becomes durable.
- Most dangerous retry bug: stale-parent handling blindly re-merges or records the current head as the committed revision.
- Most dangerous receipt bug: graph publication succeeds, receipt persistence fails, and a later request treats the proposal as uncommitted.
- Required defense: one shared proposal lifecycle lock, durable intent before merge, c2a lookup before retry, exact immutable verification, and terminal no-retry semantics once any committed revision is known.
- Split trigger: the actual c1 service cannot expose a semantic shared lock/claim boundary without changing its durable proposal schema or invalidating its replay rules.

## §2 Authority and dependency map

| Concern | Authority |
|---|---|
| Source and expected parent | SBW09a merged PR `#462` |
| Threat identity decision | SBW09b merged PR `#467` |
| Exact reviewed effect | actual merged SBW09c1 proposal implementation; currently only designed |
| Operation-to-revision recovery | actual merged SBW09c2a public Kernel lookup; currently only designed |
| Resource/binding identity | SBW08 merged PR `#457` |
| Proposal seal/verification | `graph_memory.extract_promote_proposal` |
| Contribution reconstruction | `resolve_merged_contribution_from_package` or its actual merged c1 adapter |
| Graph commit | public `graph_memory.kernel.merge_contribution_to_revision` |
| Exact revision reads | public Graph Kernel revision/integrity/projection APIs |
| Sequence | active Threat tracker and roadmap |

Read in order after the dispatch gate is satisfied:

1. `AGENTS.md` and external-agent PR-loop rules.
2. active Threat tracker, roadmap, publication re-anchor, this handoff amendment.
3. merged SBW09c1 models/service/routes/tests and handback.
4. merged SBW09c2a public function/export/tests and handback.
5. SBW09a/SBW09b owning services and tests.
6. SBW08 resource/binding models and tests.
7. `extract_promote_proposal.py` and contribution reconstruction helper.
8. public Kernel contribution, revision, rebuild, and projection APIs.
9. generic extract-promote confirm code only as precedent; do not copy current-head recovery shortcuts.

### Locked authority boundaries

- The exact active c1 proposal is complete content authority.
- The SBW09a operation remains source and expected-parent authority.
- The SBW09b resolution remains Threat identity authority.
- The commit request confirms; it does not select assertions, identity, parent, world root, or mechanics.
- The Kernel owns graph mutation and immutable revision publication.
- The application commit ledger owns durable intent, outcome, and verification status.
- SBW09c2a owns complete exact operation-ID-to-revision lookup.
- Current head is useful only for the pre-merge expected-parent check or deciding whether a zero-match recovery may make one exact retry. It is never proof of which revision committed this proposal.

## §3 Observable-path inventory

| Path | Required behavior | Owner |
|---|---|---|
| Confirm exact active proposal | persist intent, perform one exact merge, persist receipt, verify | commit service |
| Exact POST replay after success | return durable record before predecessor or graph reads | commit ledger |
| Exact POST replay after committed-unverified | re-run verification only; never merge | commit service |
| Same commit ID, changed request | conflict; bytes unchanged | ledger |
| Different commit ID for claimed proposal | busy/conflict; no second record | ledger |
| Proposal supersession racing confirmation | either supersession wins before claim or commit claim wins; never both | shared lifecycle lock |
| Crash after intent, before merge | recovery lookup zero; one exact retry only when original parent remains head | recovery state machine |
| Crash after graph commit, before receipt | unique immutable match recovers revision; no merge | c2a + ledger |
| Head advances after commit | recover exact earlier immutable revision | c2a |
| Head rolls back after commit | recover exact rolled-back-away revision | c2a |
| Multiple matching revisions | integrity ambiguity; no first-win receipt | c2a caller policy |
| Lookup unavailable/corrupt | remain unresolved `committing`; no merge | recovery state machine |
| Merge refuses before publication | persist `uncommitted`; proposal remains claimed | commit service |
| Publication proven, verification fails | persist `committed_unverified`; retry forbidden | verifier |
| Restart/read | exact commit record round-trips | ledger/GET |
| Corrupt commit ledger | fail closed; no repair/overwrite | parser/store |
| UI/Hermes/projection surface | absent | successors |

## §4 Files in scope — provisional allowlist

This allowlist must be revalidated against the actual c1/c2a merges before dispatch.

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live_control_server/models/threat_publication_commit.py` | strict request, commit-record, ledger, response models |
| Create | `apps/live_control_server/services/threat_publication_commit_store.py` | path-safe atomic commit-ledger reads/writes; no independent lock |
| Create | `apps/live_control_server/services/threat_publication_commits.py` | claim, commit, recovery, verification orchestration |
| Create | `apps/live_control_server/routes/threat_publication_commits.py` | POST confirm and GET exact record |
| Modify | `apps/live_control_server/services/threat_publication_proposals.py` | expose shared lifecycle lock/claim seam and reject supersession after commit claim |
| Modify | `apps/live_control_server/main.py` | register route |
| Create | `tests/test_threat_publication_commit_models.py` | strict model/state/ledger invariants |
| Create | `tests/test_threat_publication_commits.py` | service, persistence, recovery, concurrency, verification |
| Create | `tests/test_threat_publication_commit_api.py` | route/status/result contracts |
| Modify | `tests/test_threat_publication_proposals.py` | prove proposal supersession is blocked after commit claim |

Bounded test-only discovery exception:

```text
Directory: tests/
Maximum additional paths: 2
Allowed: existing shared fixtures/helpers or route-registration test only
Rule: no additional production scope
Report: exact paths and why local fixtures were insufficient
```

Stop before implementation if actual c1 names differ materially, c1 has no operation-scoped lifecycle lock, or c2a's merged signature/semantics differ from the design assumed here. Amend this handoff rather than guessing.

Production changes under `src/graph_memory/**`, SBW09a/SBW09b models/stores, ThreatDraft, accepted-mechanics persistence, DungeonMind, UI, corpus, placement, or combat are prohibited.

## §5 Explicit exclusions and demolition

Excluded:

- proposal construction or identity selection;
- assertion subset selection;
- parent or mechanics repinning;
- automatic retry under a new operation/proposal;
- current-head-as-receipt inference;
- first matching revision selection;
- UI confirmation flow;
- Hermes write tools or query/hydration;
- compact/full Threat projection UI;
- placement/combat;
- generic object publication framework;
- contribution supersession/retraction or undo.

```text
Replaced path: any Threat-specific use of current-head inference, generic stale-parent already-applied shortcuts, or proposal supersession after commit begins
Deleted in this PR: no
Retained reason: existing generic extract-promote confirmation remains an independent consumer and is not the Threat publication path
Named remaining consumer: Graph Review / generic extract-promote workflows
Required deletion owner: none in this slice; a later consolidation may reuse the stronger recovery primitive deliberately
```

## §6 Request, record, storage, and API contract

### §6.1 Confirmation request

```text
schema: dmb_confirm_threat_publication_request_v1
commit_id: UUID or bounded tcommit_<token>
proposal_digest: exact persisted c1 proposal digest
expected_parent_revision_id: exact persisted c1/SBW09a parent
actor: nonblank bounded string
operator_note: optional bounded string
```

Route identity supplies `draft_id`, `operation_id`, and `proposal_id`.

The request must not accept:

- assertion IDs or a selection;
- world/campaign/root;
- identity or target node IDs;
- resource/binding IDs;
- mechanics locators or bodies;
- `dry_run`, live-world permission, or idempotency policy;
- a replacement parent.

Canonical request digest includes every route identity and request field.

### §6.2 Durable commit record

```text
schema: dmb_threat_publication_commit_v1
commit_id
request_digest
draft_id
operation_id
proposal_id
proposal_digest
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

The exact effect identity fields must be copied from and validated against the c1 proposal—not reconstructed from current draft, label, mechanics store, or graph head.

State invariants:

- `committing`: no committed revision; merge attempt count is 1 or 2.
- `uncommitted`: no committed revision; terminal for this proposal claim.
- `ambiguous`: no selected committed revision; terminal until operator repair/reconciliation.
- `committed_unverified`: committed revision required; merge retry prohibited.
- `committed_verified`: committed revision required; verification passed; merge retry prohibited.
- Any record permanently claims the proposal. There is no record deletion or reset in v1.

### §6.3 Ledger and storage

```text
schema: dmb_threat_publication_commit_ledger_v1
draft_id
operation_id
commit: ThreatPublicationCommitV1 | null
```

Storage:

```text
out/threat_publication_commits/<draft_id>/<operation_id>/ledger.json
```

There is deliberately no `.commit.lock`. The c1 operation-scoped `.proposal.lock` is the sole lifecycle lock covering proposal activity and commit claim/outcome. The commit store exposes unlocked low-level reads/writes that are legal only while that semantic lifecycle lock is held.

One operation can have at most one commit record. A terminal `uncommitted` record is not cleared to reuse the proposal; the operator must create a new SBW09a operation, identity resolution, and proposal if publication should be attempted against a new parent.

### §6.4 Routes

```text
POST /api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/proposals/{proposal_id}/commits
GET  /api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/commits/{commit_id}
```

Minimum result labels:

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

HTTP mapping:

- first committed result: `201`, including committed-unverified;
- replay, recovery, GET, or verification-only replay: `200`;
- not found: `404`;
- uncommitted, stale, busy, changed input, or ambiguity: `409`;
- validation: `422`;
- unavailable dependency/storage: `503`;
- corrupt durable authority/integrity: `500`.

A committed-unverified outcome is a success-shaped receipt containing the exact committed revision and `retry_allowed=false`. It must not be collapsed into a generic 500 that invites a second commit.

## §7 Shared proposal claim and lock contract

### §7.1 One lifecycle lock

The actual c1 proposal service must expose a semantic context/helper equivalent to:

```python
with claim_threat_publication_proposal_lifecycle(
    repo_root, draft_id, operation_id
) as claim:
    ...
```

The helper name may follow actual c1 conventions, but these semantics are fixed:

1. acquire the exact operation-scoped c1 proposal lock;
2. allow loading the active proposal and commit ledger under that lock;
3. permit c2b to atomically create/update the commit record;
4. cause c1 proposal supersession to check the commit ledger under the same lock;
5. refuse proposal supersession once any commit record exists, regardless of state;
6. release only after the c2b state transition, Kernel call/recovery, immediate receipt persistence, and verification persistence complete or fail safely.

### §7.2 Lock order

```text
proposal lifecycle lock
→ commit ledger unlocked read/write
→ SBW09b identity read
→ SBW09a publication refresh/read
→ exact World Graph read / Kernel world-write lock
```

No SBW09a/SBW09b/Kernel code may call back into proposal or commit storage. No second application lock may be acquired in reverse order.

### §7.3 Proposal supersession race

The required result is serializable:

- supersession acquires the lock first and completes: c2b sees the requested proposal is no longer active and writes no intent;
- c2b acquires the lock first and persists any commit record: supersession is refused permanently;
- there is no state where a superseded proposal also owns a commit record.

If holding the proposal lifecycle lock across the Kernel call is incompatible with the actual c1 contract, stop. Do not replace it with a check-then-act window.

## §8 Exact commit and recovery algorithm

### §8.1 Replay before dependencies

Under the lifecycle lock, load the commit ledger before proposal, predecessor, or graph reads.

- same commit ID + exact request digest + `committed_verified`: return record;
- same commit ID + exact request digest + `committed_unverified`: run verification only, then return updated record;
- same commit ID + exact request digest + `committing`: enter recovery; never blindly merge;
- same commit ID + changed request: conflict; bytes unchanged;
- different commit ID when any record exists: busy/conflict; no second record.

### §8.2 New commit admission

For a new record:

1. Load the exact c1 proposal and require it is the active proposal for the operation.
2. Require request proposal digest and expected parent equal the persisted proposal.
3. Read the exact SBW09b resolution and require it remains active and identity/digests equal the proposal.
4. Refresh/read the exact SBW09a operation and require it remains `ready`; route IDs, source digest, world/campaign, mechanics locator, and expected parent must equal proposal and resolution.
5. Require current head equals the expected parent before the first attempt. A mismatch produces no commit record and no merge.
6. Verify the complete sealed proposal and reconstruct the complete contribution using existing authority. File-source verification may be disabled only because SBW09a/SBW09b are the mutable-source authorities; package digest, principal, parent, effect, contribution meta, node map, and identity snapshot remain verified.
7. Whole proposal only: no assertion subset. Reconstructed contribution ID, accepted assertion IDs, Threat/resource/binding IDs, and expected parent must exactly equal the c1 proposal fields.
8. Persist `committing`, `merge_attempt_count=1` before the Kernel call.

### §8.3 Kernel commit

Call exactly:

```text
kernel.merge_contribution_to_revision(
  exact configured world root,
  world_id=proposal world,
  contribution=exact reconstructed contribution,
  expected_parent_revision_id=proposal expected parent,
)
```

Do not call direct World Graph storage, generic HTTP confirm, mutable-source prepare, contribution supersession, or any second merge framework.

When the result proves publication and supplies a revision ID, immediately persist `committed_unverified` with that exact revision before running audits.

### §8.4 Ambiguous outcome reconciliation

Whenever the Kernel call raises, reports unpublished unexpectedly, omits a revision ID, or a replay finds `committing`, call the merged c2a public lookup with:

```text
world_id = exact proposal world
operation_id = proposal.expected_contribution_id
```

The lookup key is the Graph contribution ID because Kernel publication records `operation_ids=[contribution.contribution_id]`. It is not the SBW09a publication operation ID.

Interpretation:

| Lookup | Additional checks | Result |
|---|---|---|
| one match | exact world, parent, operation membership, contribution/effect verification | persist `committed_unverified`, recovered=true |
| multiple matches | none may be selected | persist `ambiguous`; fail closed |
| zero matches, current head still expected parent, attempts=1 | exact same contribution only | persist attempts=2, perform one retry |
| zero matches, head changed | publication not proven and retry unsafe | persist `uncommitted` |
| zero matches after second attempt | publication not proven | persist `uncommitted` |
| lookup unavailable/corrupt | outcome unresolved | retain `committing`; return unavailable |

After the one permitted recovery retry, reconcile through c2a again before classifying the result. No third merge is permitted.

Head advancement or rollback after a successful commit cannot hide the immutable matching revision. Current head must never be substituted for `committed_revision_id`.

### §8.5 Receipt persistence failure

Required injected sequence:

```text
intent persisted
→ Kernel publishes revision
→ committed_unverified save fails
→ response is unavailable/unknown
→ restart/replay sees committing
→ c2a finds one exact immutable revision
→ committed_unverified is persisted
→ verification runs
```

No second merge occurs.

## §9 Exact committed-revision verification

Verification consumes only the durable commit record, the exact c1 proposal, reconstructed contribution, and exact committed revision.

Required checks:

1. c2a returns exactly one matching manifest for the expected contribution ID, and it is the recorded committed revision.
2. Manifest world, revision, parent, and operation membership are exact.
3. Exact revision payload loads through public integrity authority.
4. `contribution_source_payload_sha256[expected_contribution_id]` equals the exact reconstructed contribution source digest.
5. `contribution_replay_manifest` contains one active entry for the exact contribution ID and digest.
6. Every accepted assertion ID has durable support naming the exact contribution ID.
7. Create-new contains the exact Threat node and authored fields sealed by c1.
8. Connect-existing does not introduce or rewrite the target Threat identity fields.
9. The external-resource node is the exact strict `ExternalResourceV1` sealed by c1.
10. The binding edge has the exact edge ID, endpoints, predicate, binding ID, and strict `ThreatStatblockBindingV1` sealed by c1.
11. No mechanics body, rules elements, rendered Markdown, or assets are copied into graph state.
12. `rebuild_from_contributions(... compare_revision_id=committed_revision_id, publish=False)` reports equivalence to the exact revision.
13. Exact revision-pinned projection reports the same revision and contains the exact Threat, external resource, and binding.

Current head is irrelevant once `committed_revision_id` exists.

Verification classification:

| Condition | Commit state | Verification status | Retry merge? |
|---|---|---|---|
| every required check passes | `committed_verified` | `passed` | no |
| exact objects/support are present but rebuild or secondary audit is unavailable/degraded | `committed_unverified` | `degraded` | no |
| contribution/object/binding/digest/projection identity mismatch | `committed_unverified` | `failed` | no |
| verification dependency temporarily unavailable | `committed_unverified` | `not_started` or `degraded` | no; later verification-only replay |

A later exact POST may re-run verification. It may never call merge after a committed revision exists.

## §10 State, fallback, identity, persistence, and commit matrices

### §10A State/fallback matrix

| Durable state | Meaning | POST behavior | Fallback |
|---|---|---|---|
| no record | proposal unclaimed | new admission | none |
| committing | intent exists, outcome unresolved | c2a reconciliation first | no blind merge |
| uncommitted | publication not proven; retry unsafe/exhausted | return terminal conflict | new operation/proposal |
| ambiguous | multiple immutable matches/integrity ambiguity | return terminal conflict | operator repair only |
| committed_unverified | exact revision known | verify only | no merge |
| committed_verified | exact revision verified | exact replay | none |

### §10B Identity matrix

| Identity | Authority | Fallback |
|---|---|---|
| source/parent | SBW09a operation snapshot | none |
| Threat target/new ID | SBW09b resolution | none |
| reviewed effect | c1 proposal + sealed package | none |
| contribution | exact reconstructed ID equal to c1 expected ID | none |
| committed revision | Kernel result or unique c2a match | never current head |
| resource/binding | exact c1 fields + SBW08 models | none |
| commit replay | commit ID + canonical request digest | none |

### §10C Persistence/replay matrix

| Event | Durable effect | Replay |
|---|---|---|
| admission fails before intent | none | caller fixes or creates new request |
| intent save succeeds | proposal permanently claimed | reconcile before merge |
| merge publishes | immutable revision exists | unique c2a match recovers |
| immediate receipt saves | committed revision durable in app ledger | verify only |
| verification saves | terminal/refreshable audit status | no merge |
| ledger corrupt | none further | fail closed; no overwrite |

### §10D Commit-point declaration

```text
Application intent point: atomic commit-ledger save in state=committing.
Graph commit point: Kernel publishes immutable revision and advances head.
Application publication proof point: atomic save in state=committed_unverified.
Verified completion point: atomic save in state=committed_verified.

After graph commit, no application failure may make the operation retryable.
```

### §10E No-fallback declaration

Prohibited fallbacks:

- latest accepted mechanics;
- current ThreatDraft;
- latest/current identity resolution;
- label, alias, or candidate rank;
- current graph head as committed revision;
- first matching immutable revision;
- a newly pinned parent;
- a second proposal or contribution ID;
- direct graph-file inspection from application code.

## §11 Verification ownership and required evidence

| Guarantee | Owning boundary | Required command/evidence |
|---|---|---|
| strict models and state invariants | commit models | `uv run pytest -q tests/test_threat_publication_commit_models.py` |
| claim/merge/recovery/verification | commit service | `uv run pytest -q tests/test_threat_publication_commits.py` |
| route labels/statuses | API | `uv run pytest -q tests/test_threat_publication_commit_api.py` |
| proposal cannot supersede after claim | c1 proposal owner | focused c1 proposal tests |
| c1 proposal regression | predecessor | actual merged c1 focused suites |
| c2a zero/one/many regression | Kernel lookup owner | actual merged c2a focused suite |
| SBW09a/SBW09b regression | predecessor | focused operation and identity suites |
| SBW08 exact binding regression | graph contract | `tests/test_statblock_binding_graph_contract.py` |
| sealed proposal/contribution regression | graph governance | current exact promote proposal/ops suites |
| Kernel merge/rebuild/projection regression | Kernel owners | current focused contribution merge/rebuild/projection suites |
| scope/hygiene | repository | `git diff --check`; exact base/head name-only diff |

Required adversarial sequences:

1. Create-new confirmation → committed-unverified save → exact verification → restart GET.
2. Connect-existing commit contains no Threat node rewrite.
3. Request cannot select a subset of assertions.
4. Exact terminal replay returns before predecessor and graph reads.
5. Changed same-ID replay conflicts with byte-identical ledger.
6. Concurrent first confirmations produce one record and at most one Kernel merge.
7. Proposal supersession/confirmation race is serializable under the shared lock.
8. Crash after intent, before merge: zero lookup + unchanged parent permits exactly one retry.
9. Crash after graph commit, before receipt: one lookup match recovers without merge.
10. Head advances after commit: earlier immutable revision still recovers.
11. Head rolls back after commit: rolled-back-away revision still recovers.
12. Duplicate matching revisions: persist ambiguity; never first-win.
13. Lookup unavailable/corrupt: retain `committing`; no merge.
14. Kernel reports unpublished or raises after publication: lookup proves or disproves commit.
15. Committed revision plus verification failure: committed-unverified, retry forbidden.
16. Crash after committed-unverified before verification: replay verifies only.
17. Commit-ledger write fails before intent: no graph call.
18. Receipt write fails after graph commit: restart recovery sequence succeeds without duplicate merge.
19. Corrupt commit ledger: fail closed without overwrite or graph call.
20. Success and every failure path leave ThreatDraft, accepted mechanics, SBW09a, SBW09b, and c1 proposal bytes unchanged except the c1 commit-claim behavior under its shared lock.

For every baseline-red command, run the identical command at base and head and record an explicit waiver. Do not claim repository-wide CI unless attached checks actually exist.

## §12 Dispatch gate and required re-anchor amendment

Implementation must not begin from this design-only handoff. Dispatch requires all of the following:

- SBW09c1 implementation is merged to main with exact merge SHA, actual models, proposal fields, service names, lock semantics, routes, tests, and handback reviewed.
- SBW09c2a implementation is merged to main with exact merge SHA, actual public function/export, plural zero/one/many semantics, and tests reviewed.
- This file is amended to replace every provisional c1/c2a name or assumption with actual merged contracts.
- The provisional allowlist in §4 is revalidated and narrowed against current main.
- The tracker and roadmap mark c1 and c2a complete and c2b as the sole next publication implementation.
- The amendment records the exact immutable dispatch-base SHA and proves the c1/c2a production paths do not create a lock-order or scope conflict.
- Any discovered need to change Graph Kernel write/CAS semantics, c1 durable proposal schema, or c2a plural lookup semantics is resolved as a predecessor slice rather than silently absorbed.

The amendment may tighten this design. It may not weaken exact identity, intent-before-write, immutable recovery, plural ambiguity, or committed-but-unverified guarantees.

## §13 Required implementation handback

Record:

- exact dispatch base/head and merge ancestry;
- actual changed paths/diff stat;
- actual c1 shared lock/claim seam and c2a signature;
- request/record/ledger JSON examples;
- every §11 command/result and provenance;
- count of Kernel merge calls in all replay/race/crash tests;
- exact unique recovery manifest and committed revision;
- zero/one/many recovery evidence, including head advance and rollback;
- exact Threat/resource/binding verification evidence;
- committed-unverified degraded/failed examples with merge retry proving absent;
- before/after bytes for predecessor/proposal/mechanics stores;
- baseline failures and waivers;
- paths outside the amended allowlist;
- confirmation that UI, Hermes query/hydration, Threat projection, placement, and combat remain false.

## §14 Acceptance rubric

- [ ] Actual merged c1 and c2a contracts were re-anchored before implementation.
- [ ] One exact active proposal can own at most one commit record.
- [ ] Proposal supersession and confirmation share one serializable lifecycle lock.
- [ ] Intent is durable before the first Kernel merge.
- [ ] Whole sealed proposal is reconstructed and verified; no assertion subset exists.
- [ ] At most two merge attempts occur: the initial attempt and one zero-match recovery retry.
- [ ] Every ambiguous outcome checks c2a before retry.
- [ ] Unique recovery validates exact parent, contribution, and effect before receipt.
- [ ] Multiple matches remain ambiguous; no first-win path exists.
- [ ] Current head is never recorded as committed revision merely because contribution state is visible there.
- [ ] Any known committed revision permanently prohibits merge retry.
- [ ] Committed-but-unverified is durable and truthfully exposed.
- [ ] Exact revision verifies contribution digest/replay/support, Threat/resource/binding, rebuild, and projection.
- [ ] No mechanics body enters graph state.
- [ ] Storage is path-safe, atomic, bounded, restart-safe, and corruption-closed.
- [ ] No production path outside the amended allowlist changed.
- [ ] Later UI/query/projection/placement/combat capabilities remain unimplemented.

## §15 Reviewer attack list

- Force a proposal supersession exactly between confirmation admission and intent persistence.
- Count Kernel merge calls across exact replay, concurrent requests, every exception, and every crash seam.
- Search for current-head substitution, parent repinning, first match, `next(...)`, label lookup, or mutable draft reads.
- Verify the c2a lookup key is the expected contribution ID, not SBW09a operation ID.
- Delete or corrupt the immediate receipt after a real synthetic publish and require restart recovery.
- Advance and roll back head before recovery.
- Seed two manifests with the same contribution operation ID and ensure no revision is selected.
- Fail every atomic commit-ledger save point.
- Make exact object verification fail after publication and confirm no merge retry.
- Inspect connect-existing revision for unintended Threat node/attribute rewrites.
- Recursively scan graph payloads and receipts for mechanics bodies.
- Verify no application import reaches into `world_supergraph.storage` or contribution-store internals when a public Kernel API owns the operation.

## §16 Stop conditions

Stop and report if:

- actual c1 cannot expose a safe shared lifecycle lock/claim seam;
- actual c1 proposal lacks exact contribution/assertion/effect identity required for verification;
- actual c2a cannot recover immutable revisions independent of head;
- complete recovery requires selecting one of multiple matches;
- contribution reconstruction requires mutable draft/mechanics/current-head data;
- safe commit requires changes to Kernel write/CAS semantics;
- exact verification requires application imports of storage internals rather than public Kernel APIs;
- any committed outcome cannot be persisted without becoming retryable;
- a production path outside the amended allowlist is required;
- UI, Hermes, placement, combat, or generic publication is pulled into scope;
- an unwaived owning-boundary regression appears.
