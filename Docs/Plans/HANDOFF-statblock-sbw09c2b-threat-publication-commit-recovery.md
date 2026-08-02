---
pr_body_template: |
  ## Outcome
  Implement the exact backend publication transaction for one reviewed statblock-backed Threat proposal: durable intent before mutation, one exact-parent Kernel merge, immutable recovery, and revision-pinned verification without duplicate graph writes.

  ## Base
  `3d5e66b53b09112178dda99063fd9acade3fb087` — merge of PR `#474`.

  ## Invariant
  One exact active proposal has at most one durable commit record. Every uncertain outcome consults immutable revision authority before retry. At most two lifetime Kernel merge calls exist. A known committed revision is never retryable.

  ## Scope
  Only the production and test paths allowlisted in the checked-in handoff. No Kernel changes, UI, Hermes query, product projection, placement, combat, mechanics adoption, undo, or generic publication.

  ## Final delivery
  Do not commit or push incrementally. Complete implementation, tests, scope accounting, and the PR handback first. Then stage only approved paths, create one commit beginning with `statblock`, and push as the final repository mutation.
---

# statblock — HANDOFF: SBW09c2b proposal-bound commit, immutable recovery, and exact verification

**Created:** 2026-08-01  
**Status:** ACTIVE — dispatch exactly one implementation capability.  
**Canonical path:** `Docs/Plans/HANDOFF-statblock-sbw09c2b-threat-publication-commit-recovery.md`  
**Parent authority:** `Docs/Plans/HANDOFF-sbw09c2b-threat-publication-commit-recovery.md`, merged in PR `#474`  
**Required implementation base:** `3d5e66b53b09112178dda99063fd9acade3fb087`  
**Suggested implementation branch:** `feat/statblock-sbw09c2b-threat-publication-commit-recovery`  
**Required implementation PR title prefix:** `statblock`

> This dispatch handoff does not replace or weaken PR `#474`. It freezes the executable implementation slice, exact base, changed-path budget, proof obligations, and final delivery sequence. A conflict with the parent authority is a stop condition.

## §0 Capability decision

**Selected capability:** one proposal-bound backend publication transaction that durably distinguishes `committing`, `uncommitted`, `ambiguous`, `committed_unverified`, and `committed_verified`, with at most one initial merge and one governed recovery retry.

The included intent, mutation, recovery, receipt, and verification work shares one invariant: separating them would create a window where the application could duplicate a committed write or report a reviewed proposal as durable graph truth.

**Named successors:** Workbench confirmation UI; SBW10a query/hydration; SBW10b projection; placement; combat; mechanics adoption; retraction/undo; generic authored-object publication.

## §1 Mission and invariant

```text
The live-control server can explicitly confirm one exact active statblock-backed
Threat publication proposal into at most one exact immutable World Graph revision
and return a durable, recoverable, revision-pinned publication receipt.
```

```text
One exact active SBW09c1 proposal has at most one durable SBW09c2b commit record.
Intent is durable before mutation. Every uncertain outcome is reconciled through
immutable revision authority before retry. At most two lifetime Kernel merge calls
exist. Once an immutable committed revision is known, it is never retryable.
```

This is not one slice if implementation also requires UI, identity reselection, assertion subsets, mechanics mutation, parent repinning, Kernel write/CAS changes, Hermes query, projection, placement, combat, generic publication, retraction, or rebinding.

## §2 Authority and base

Read in order:

1. Repository rules: `AGENTS.md`, `.cursor/rules/external-agent-pr-loop.mdc`, `.cursor/skills/external-agent-pr-loop/SKILL.md`.
2. This dispatch handoff and the parent authority merged in PR `#474`.
3. Active Threat tracker and roadmap.
4. SBW09c1 merged PR `#478`: proposal model/service/routes/tests.
5. SBW09c2a merged PR `#476`: `kernel.find_world_graph_revisions_by_operation_id` and tests.
6. SBW09a `#462`, SBW09b `#467`, and SBW08 `#457` authorities.
7. Existing seal/reconstruction and public Kernel merge, integrity, digest, rebuild, and projection APIs.

Authority precedence:

```text
repository architecture and lifecycle decisions
→ active tracker and roadmap
→ parent authority from PR #474
→ this dispatch handoff
→ merged predecessor implementation and owning tests
→ other implementation
→ Project Sources and chat
```

The implementation branch must descend from:

```text
3d5e66b53b09112178dda99063fd9acade3fb087
```

Record that SHA in the implementation PR body before code changes. Do not silently adopt a newer base. Material drift is a stop condition.

## §3 Observable paths

| Path | Required behavior |
|---|---|
| Create-new confirmation | Intent → exact merge → receipt → pinned verification. |
| Connect-existing confirmation | Commit resource+binding only; no target Threat rewrite. |
| Committed-verified replay | Return before predecessor/graph reads; zero merges. |
| Committed-unverified replay | Verification only; zero merges. |
| Committing replay | c2a reconciliation first; never blind merge. |
| Same commit ID, changed request | Conflict; bytes unchanged. |
| Different commit ID after claim | Busy/conflict; no second ledger or merge. |
| Supersession races confirmation | Exactly one ordering wins under one lifecycle lock. |
| Inactive proposal/resolution/operation | No intent and no graph call. |
| SBW09a refresh finds drift | Only its exact `ready → stale` transition; no c2b intent. |
| Parent changed before intent | Parent mismatch; no record. |
| Crash after intent | Immutable lookup before any retry. |
| Typed `published=False` | Reconcile once; zero match becomes terminal uncommitted; no retry. |
| Exception/malformed result | Reconcile before retry/classification. |
| Commit succeeds, receipt save fails | Restart recovers exact revision; no duplicate merge. |
| Head advances or rolls back | Immutable match remains recoverable. |
| Multiple matches | Persist ambiguity; select none. |
| Integrity-valid contradictory match | Persist ambiguity; select none. |
| Graph authority cannot integrity-load | Retain committing; integrity failure/500; no merge. |
| Transient lookup failure | Retain committing; recovery pending/503; no merge. |
| Verification fails/degrades | Remain committed-unverified; no merge retry. |
| Missing GET | 404 with no directory or lock creation. |
| Corrupt commit ledger | Fail closed; never repair or overwrite. |

## §4 Exact changed-path allowlist

Production:

```text
CREATE apps/live_control_server/models/threat_publication_commit.py
CREATE apps/live_control_server/services/threat_publication_commit_store.py
CREATE apps/live_control_server/services/threat_publication_commits.py
CREATE apps/live_control_server/routes/threat_publication_commits.py
MODIFY apps/live_control_server/services/threat_publication_proposals.py
MODIFY apps/live_control_server/main.py
```

Tests:

```text
CREATE tests/test_threat_publication_commit_models.py
CREATE tests/test_threat_publication_commits.py
CREATE tests/test_threat_publication_commit_api.py
MODIFY tests/test_threat_publication_proposals.py
```

Bounded discovery exception:

```text
Directory: tests/
Maximum additional paths: 2
Kinds: existing shared fixture/helper or route-registration test only
Rule: include only when an owning-boundary sequence cannot be represented locally
Report: exact path, necessity, and why an allowlisted local fixture was insufficient
```

No production discovery exception exists.

## §5 Explicitly out of scope

- `src/graph_memory/**` changes.
- SBW09a/SBW09b schema or ledger changes.
- ThreatDraft or accepted-mechanics mutation.
- Changes to extract-promote seal/reconstruction code.
- DungeonMind generation/client work.
- UI confirmation controls.
- Hermes query/hydration or product projection.
- Placement, canvas, embed, or combat work.
- Generic publication, retraction, undo, or mechanics rebinding.

No prior Threat-specific commit path exists. Generic extract-promote confirmation remains an independent Graph Review consumer and is not deleted.

## §6 Request, record, and storage

Confirmation route:

```text
POST /api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/proposals/{proposal_id}/commits
```

Request schema `dmb_confirm_threat_publication_request_v1` contains only:

```text
commit_id
sealed_proposal_digest
expected_parent_revision_id
actor
operator_note
```

It cannot select resolution, assertions, identity, world/root, mechanics, resource/binding IDs, parent, retry policy, or dry-run behavior.

Durable record schema `dmb_threat_publication_commit_v1` binds:

```text
commit/request/proposal identities and digests
resolution/source/candidate-set identities
world_id, campaign_id, original parent
expected contribution ID and source-payload SHA256
exact accepted assertion IDs
create_new | connect_existing decision
Threat, selected-target, resource, binding, and edge identities
state and merge attempt count (1 | 2)
committed revision and recovery flag
verification status/codes/warnings
audit actor/note/timestamps
```

The record does not copy the sealed proposal or mechanics body. Contribution reconstruction uses `proposal.created_by`; record `created_by` is the c2b confirmer.

Storage:

```text
out/threat_publication_commits/<draft_id>/<operation_id>/ledger.json
```

One valid ledger contains exactly one record. Any record permanently claims the proposal, including terminal uncommitted or ambiguous. No empty ledger and no `.commit.lock`. Saves are atomic. Corrupt or contradictory authority fails closed and is never automatically repaired.

GET route:

```text
GET /api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/commits/{commit_id}
```

Committed-unverified is a success-shaped exact-revision receipt with `retry_allowed=false`.

## §7 Shared lifecycle lock

Expose the existing c1 operation-scoped `.proposal.lock` as the proposal/commit lifecycle lock. The commit store owns no lock and does not import the proposal service.

Lock order:

```text
lifecycle lock
→ proposal ledger unlocked read
→ commit ledger unlocked read/write
→ SBW09b resolution read
→ SBW09a refresh/read
→ public Kernel APIs
```

After any valid commit record exists:

- exact replay of the persisted c1 proposal remains available;
- no new proposal may be created or superseded;
- c1 uses existing `publication_proposal_busy` with an explicit claim message;
- a commit ledger without matching proposal authority is an integrity failure;
- c1 no-artifact fast paths require both proposal and commit ledgers absent.

Hold the lifecycle lock across admission, intent persistence, merge, immediate receipt persistence, and attempted verification persistence. A demonstrated lock-order cycle is a stop condition.

## §8 Admission and reconstruction

Under the lifecycle lock, load the commit ledger before proposal, predecessor, draft, or graph reads.

Existing states:

```text
committed_verified   → exact replay immediately; zero dependencies/merges
committed_unverified → verification only; zero merges
committing           → c2a reconciliation first
uncommitted          → terminal replay
ambiguous            → terminal replay
changed request or different commit ID → conflict/busy
```

When no record exists:

1. Load the route-named active proposal.
2. Require request digest and parent match c1.
3. Revalidate exact SBW09b resolution.
4. Refresh/read exact SBW09a operation; drift may only write its owned `ready → stale` transition.
5. Require operation remains ready and exact across world, campaign, source, mechanics locator, and parent.
6. Reconstruct the complete sealed proposal using `confirming_principal=proposal.created_by`, `assertion_ids=None`, `verify_source=False`.
7. Require exact proposal/version/digest, contribution ID, ordered assertion IDs, Threat/resource/binding effect, world, and parent.
8. Persist `kernel.compute_contribution_source_payload_sha256(contribution)`.
9. Require current head equals the original parent.
10. Atomically persist `state=committing`, `merge_attempt_count=1`.

Only then call the Kernel. Connect-existing must contain no Threat node or identity/attribute rewrite.

## §9 Mutation and commit points

Only allowed graph mutation:

```python
kernel.merge_contribution_to_revision(
    configured_world_graph_root,
    world_id=record.world_id,
    contribution=exact_reconstructed_contribution,
    expected_parent_revision_id=record.expected_parent_revision_id,
)
```

Commit points:

```text
intent: atomic committing record
actual graph commit: Kernel immutable revision publication
publication proof: atomic committed_unverified record with exact revision
verified completion: atomic committed_verified record
```

A direct `published=True` result is accepted only when world, original parent, revision, contribution ID, and assertion IDs are exact. Persist committed-unverified before broader audits.

Any exception, malformed/contradictory result, missing revision, or `published=False` enters reconciliation first.

## §10 Immutable recovery

Lookup by:

```text
world_id = record.world_id
operation_id = record.expected_contribution_id
```

Never use SBW09a operation ID, current head, first match, or contribution-store existence as publication proof.

| Lookup result | Durable transition | Merge |
|---|---|---|
| One integrity-valid exact parent/membership/digest/replay match | committed_unverified | none |
| Multiple matches | ambiguous | none |
| One integrity-valid but contradictory match | ambiguous | none |
| Revision/manifest cannot integrity-load | remain committing; integrity_failure/500 | none |
| Transient lookup failure | remain committing; recovery_pending/503 | none |
| Zero after typed published=False | uncommitted | none |
| Zero after uncertain attempt 1 + unchanged parent/authorities | persist attempt 2 | one exact retry |
| Zero after uncertain attempt 1 + drift | uncommitted | none |
| Zero after attempt 2 | uncommitted | none |

Mandatory distinction:

```text
integrity-unloadable graph authority
→ unresolved committing + 500

integrity-valid revision contradicting persisted proof
→ terminal ambiguous + 409
```

Before the single retry, all proposal, resolution, operation, parent, contribution ID, source digest, assertions, and effect IDs must reconstruct identically; attempt count 2 persists before the call. No third merge exists. Attempt 2 with unavailable/corrupt lookup remains committing but can never merge again.

## §11 Exact verification

Verify only the durable record, c1 proposal, exact reconstructed contribution, exact committed revision, and public Kernel outputs.

Required core proof:

- c2a returns exactly the recorded revision;
- manifest world/revision/parent/status/operation membership are exact;
- revision integrity-load succeeds;
- contribution source digest and replay entry are exact;
- every accepted assertion support record names the contribution;
- create-new materializes exact Threat/authored fields;
- connect-existing contains no Threat rewrite and target matches the persisted candidate snapshot;
- external statblock resource and `uses_statblock` binding are exact;
- no mechanics body, rules, rendered Markdown, assets, or recursive equivalent entered graph state.

Secondary audits:

- `rebuild_from_contributions(compare_revision_id=committed_revision, publish=False)` reports `rebuild_equivalent_to_pinned_revision`;
- projection uses exact world, campaign, committed revision pin, GM admissibility, and campaign scope.

Outcomes:

```text
all proof passes → committed_verified / passed
core passes, secondary unavailable/degraded → committed_unverified / degraded
core mismatch → committed_unverified / failed
post-commit dependency unavailable → committed_unverified / not_started or degraded
```

No verification outcome permits a merge retry.

## §12 Evidence

Focused commands:

```bash
uv run pytest -q tests/test_threat_publication_commit_models.py
uv run pytest -q tests/test_threat_publication_commits.py
uv run pytest -q tests/test_threat_publication_commit_api.py
uv run pytest -q tests/test_threat_publication_proposals.py
```

Regression evidence must include c1, c2a, SBW09a, SBW09b, SBW08, extract-promote, and focused Kernel merge/digest/rebuild/projection owners named in the parent authority.

Also run:

```bash
uv run ruff check <every touched Python path>
git diff --check
git diff --stat 3d5e66b53b09112178dda99063fd9acade3fb087...HEAD -- <all allowlisted paths>
git diff --name-only 3d5e66b53b09112178dda99063fd9acade3fb087...HEAD
```

Required adversarial coverage includes normal create/connect, replay/input conflicts, concurrent confirmation, supersession races, orphan authority, intent and receipt save failures, zero/one/many lookup, head advance/rollback, deterministic refusal, one bounded retry, transient lookup failure, integrity-unloadable graph authority, integrity-valid contradiction, verification failure/degradation, no mechanics copy, no connect-existing rewrite, predecessor-byte rules, corrupt ledger, and missing GET no-artifact behavior.

Every uncertain sequence must assert merge-call count:

```text
normal success: 1
terminal replay: 0
committed-unverified replay: 0
concurrent first confirmation: <=1 initial total
permitted recovery: <=2 lifetime
published response loss: 1 lifetime
published=False: 1 lifetime
multiple/contradictory/unavailable/corrupt lookup: 0 new
attempt_count=2 replay: 0 new
```

## §13 Implementation handback

Before final commit and push, the implementation PR body must contain:

- exact base/head and ancestry;
- actual changed paths and line counts;
- exact lock/helper names and c1 behavior changes;
- exact c2a signature used;
- request, state, record, and response examples;
- reconstruction principal proof;
- contribution/assertion/Threat/resource/binding extraction rules;
- every command/result with local, independent, CI, or manual provenance;
- merge-call accounting;
- zero/one/many, head advance, and rollback evidence;
- distinct evidence for transient failure, integrity-unloadable authority, and integrity-valid contradiction;
- direct/recovered committed-unverified examples and verification codes;
- predecessor-byte evidence for success/replay and refresh-drift paths;
- baseline failures and explicit waivers;
- paths outside scope or `none`;
- stop conditions or `none`;
- explicit statement that all named successors remain false.

## §14 Acceptance

Review accepts only when:

- branch descends from exact base;
- one operation has at most one record and any record claims the proposal;
- supersession and confirmation share the lifecycle lock;
- exact proposal replay remains available;
- request cannot redefine content/identity/mechanics/root/parent/retry;
- reconstruction uses `proposal.created_by`;
- complete proposal and exact contribution digest persist before merge;
- intent persists before every allowed Kernel call;
- at most two lifetime calls exist and deterministic refusal is never retried;
- every uncertain result reconciles before retry/classification;
- exact recovery requires integrity-valid revision, parent, membership, digest, and replay;
- integrity-unloadable authority stays unresolved/nonretrying;
- integrity-valid contradiction and multiple matches remain ambiguous;
- current head is never committed-revision proof;
- known committed revision is never retryable;
- committed-unverified is durable, success-shaped, and exact-revision pinned;
- verification proves contribution/support/Threat/resource/binding/rebuild/projection;
- connect-existing performs no Threat rewrite;
- no mechanics body enters graph state;
- storage is atomic, strict, path-safe, bounded, and corruption-closed;
- no production path outside the allowlist changes;
- successors remain false;
- final commit and push follow §16.

## §15 Stop conditions

Stop without committing or pushing if:

- branch/base ancestry is wrong or repository contracts materially drifted;
- c1 cannot safely expose its existing operation lock;
- supersession blocking requires a c1 schema change;
- reconstruction requires extract-promote changes;
- exact effect identity is insufficient;
- c2a is head-dependent or first-win;
- transient failure, integrity-unloadable authority, and integrity-valid contradiction cannot be distinguished;
- safe commit requires Kernel changes or direct storage imports;
- a known committed outcome can become retryable or a third attempt is needed;
- a production path outside §4 is required;
- UI, Hermes, projection, placement, combat, generic publication, adoption, or undo enters scope;
- required tests cannot be reproduced or remain failing without an explicit operator waiver.

## §16 Final delivery — commit and push last

Commit and push are the **final implementation actions**, not incremental checkpoints.

Required order:

1. Implement only §4.
2. Run all focused, regression, lint, diff, and scope checks.
3. Resolve failures or document exact base/head comparison and required waiver.
4. Complete the implementation PR handback.
5. Re-read the full diff against this handoff and the parent authority.
6. Run one final clean verification pass.
7. Inspect `git status --short` and changed-path accounting.
8. Stage only existing approved paths explicitly; never stage unrelated work.
9. Create one final commit whose message starts with `statblock`.
10. Push with upstream tracking.
11. Open or update the draft implementation PR whose title starts with `statblock`.
12. Return branch, commit SHA, PR URL, exact checks, and waivers.

Final command shape:

```bash
git status --short
git diff --check
git diff --name-only 3d5e66b53b09112178dda99063fd9acade3fb087...HEAD

git add <only existing approved §4 paths and approved test exceptions>
git commit -m "statblock: implement SBW09c2b commit recovery"
git push -u origin feat/statblock-sbw09c2b-threat-publication-commit-recovery
```

If any unapproved path, unresolved failure, missing waiver, or stop condition remains, do not stage, commit, or push. No essential constraint may exist only in chat or the PR description.
