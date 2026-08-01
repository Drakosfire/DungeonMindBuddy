> Status: ACTIVE EXECUTION STEWARDSHIP HANDOFF
> Use for: Executing, reviewing, and merging the two independent implementation PRs that block SBW09c2b: SBW09c1 and SBW09c2a.
> Do not use for: Combining both implementations into one PR, implementing SBW09c2b early, adding publication UI, or redesigning the canonical c1/c2a handoffs.
> Canonical repo path: `Docs/Plans/JUMPSTART-execute-sbw09c1-sbw09c2a.md`
> Prepared: 2026-08-01
> Repository: `Drakosfire/DungeonMindBuddy`
> Verified main anchor: `573698b00028949741786db3361fd1d14d5a8906` — merged PR `#473`
> Completion condition: SBW09c1 and SBW09c2a are independently reviewed and merged, then draft PR `#474` is re-anchored against both actual contracts.

# JUMPSTART — Execute SBW09c1 and SBW09c2a

## §0 Pickup prompt

```text
Execute the two independent implementation blockers for SBW09c2b in
Drakosfire/DungeonMindBuddy.

Current verified main:
  573698b00028949741786db3361fd1d14d5a8906

SBW09c1 branch and authority anchor:
  feat/sbw09c1-threat-publication-proposal
  a4c00c3c4865781fe80015d1cf7442da626c3f6d

SBW09c2a branch and authority anchor:
  feat/sbw09c2a-operation-revision-lookup
  573698b00028949741786db3361fd1d14d5a8906

Both branches currently contain zero implementation commits. Use separate
worktrees, separate PRs, and separate review evidence. The canonical c1 and c2a
handoffs are the implementation authority; do not compress, reinterpret, stack,
or combine them.

Do not implement SBW09c2b. Keep draft PR #474 blocked. After c1 and c2a merge,
amend #474 against the actual merged proposal model/service/lock contract and
the actual public lookup signature, tests, and merge SHAs.
```

## §1 Mission and invariant

**Mission**

Implement and merge SBW09c1 and SBW09c2a as two independently reviewable capabilities so the exact durable Threat proposal contract and the exact immutable-revision recovery lookup both exist before SBW09c2b is re-anchored.

**Invariant**

```text
The c1 and c2a implementations remain isolated, each proves only its canonical
handoff invariant, neither consumes unfinished sibling code, and no c2b
commit/receipt/recovery behavior begins until both merge and PR #474 is amended
against their actual public contracts.
```

This coordination handoff does not replace:

- [`HANDOFF-sbw09c1-threat-publication-proposal.md`](HANDOFF-sbw09c1-threat-publication-proposal.md)
- [`HANDOFF-sbw09c2a-operation-revision-lookup.md`](HANDOFF-sbw09c2a-operation-revision-lookup.md)

The canonical lane handoff wins if this document differs. A material mismatch with current code is a stop condition, not permission to improvise.

## §2 Current verified truth

| Item | Verified state |
|---|---|
| Current `main` | `573698b00028949741786db3361fd1d14d5a8906` |
| SBW09c1 authority | PR `#471`, merge `a4c00c3c4865781fe80015d1cf7442da626c3f6d` |
| SBW09c1 branch | exactly equals `a4c00c3...`; zero implementation commits |
| SBW09c2a authority | PR `#473`, merge `573698b00028949741786db3361fd1d14d5a8906` |
| SBW09c2a branch | exactly equals `573698b...`; zero implementation commits |
| SBW09c2b design | draft PR `#474`; design-only and blocked |
| Latest Threat implementation | SBW09b, merged PR `#467` |

```text
SBW09c1
  exact operation + exact active identity decision
  → deterministic sealed Threat/resource/binding proposal
  → durable reload/replay/supersession
  → no graph mutation

SBW09c2a
  exact world_id + exact operation_id
  → every immutable revision manifest containing that ID
  → zero / one / many deterministic results
  → no graph mutation

SBW09c2b
  exact proposal + exact recovery lookup
  → commit intent / governed merge / receipt / recovery / verification
  → remains false and blocked
```

Neither blocker authorizes graph publication, commit receipts, confirmation, crash recovery, committed-revision verification, UI, Hermes hydration, projection, placement, or combat.

## §3 Authority and required reading

Authority precedence:

```text
1. AGENTS.md and external-agent PR-loop rules
2. merged architecture and lifecycle decisions
3. active Threat roadmap and tracker
4. the lane's canonical checked-in implementation handoff
5. merged predecessor code and owning-boundary tests
6. this execution jumpstart
7. PR descriptions, attachments, and chat summaries
```

Every worker reads, in full:

1. `AGENTS.md`
2. `.cursor/rules/external-agent-pr-loop.mdc`
3. `.cursor/skills/external-agent-pr-loop/SKILL.md`
4. `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md`
5. `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`
6. the lane's canonical handoff
7. every predecessor and owning test named by that handoff

Do not rewrite the canonical handoff before implementation. Record findings in the implementation PR handback or a stop report.

## §4 Execution topology and branch safety

Use two independent agents or two independent worktrees:

```text
Steward
├── Lane A — feat/sbw09c1-threat-publication-proposal
└── Lane B — feat/sbw09c2a-operation-revision-lookup
```

Create local tracking branches before adding worktrees. Do **not** pass `origin/<branch>` directly as the worktree target; that creates a detached worktree.

```bash
git fetch origin --prune

# Run only when the local tracking branches do not already exist.
git branch --track \
  feat/sbw09c1-threat-publication-proposal \
  origin/feat/sbw09c1-threat-publication-proposal

git branch --track \
  feat/sbw09c2a-operation-revision-lookup \
  origin/feat/sbw09c2a-operation-revision-lookup

git worktree add \
  ../dmb-sbw09c1 \
  feat/sbw09c1-threat-publication-proposal

git worktree add \
  ../dmb-sbw09c2a \
  feat/sbw09c2a-operation-revision-lookup
```

When a local branch already exists, verify its upstream and use it; do not hide branch-creation failures with `|| true`.

Before editing in each worktree:

```bash
git rev-parse HEAD
git branch --show-current
git status --short
git rev-parse --abbrev-ref --symbolic-full-name @{upstream}
```

Expected anchors:

```text
c1:  a4c00c3c4865781fe80015d1cf7442da626c3f6d
c2a: 573698b00028949741786db3361fd1d14d5a8906
```

The c1 branch predates the c2a docs merge. Before c1 edits:

```bash
git fetch origin
git merge-base --is-ancestor \
  a4c00c3c4865781fe80015d1cf7442da626c3f6d \
  origin/main

git diff --name-only \
  a4c00c3c4865781fe80015d1cf7442da626c3f6d...origin/main
```

Inspect every intervening path. Documentation-only or unrelated Surface changes do not invalidate c1. Any change to c1 predecessors, proposal-governance owners, route registration, or c1 allowlisted paths requires a stop report and exact re-anchor before coding.

Repeat ancestry and drift checks for c2a immediately before editing in case `main` moved.

Do not cherry-pick or merge draft PR `#474`, the sibling blocker, superseded SBW09 branches, generic graph-review recovery experiments, or unrelated local work.

## §5 Lane A — SBW09c1 exact durable no-write proposal

### Mission and authority

```text
The live-control server can turn one exact ready SBW09a operation plus one exact
active create-new or connect-existing SBW09b resolution into one durable,
deterministic, no-write publication proposal that seals the exact World Graph
effects for review.
```

```text
Branch: feat/sbw09c1-threat-publication-proposal
Base:   a4c00c3c4865781fe80015d1cf7442da626c3f6d
Handoff: Docs/Plans/HANDOFF-sbw09c1-threat-publication-proposal.md
```

### Exact allowlist

| Action | Path |
|---|---|
| Create | `apps/live_control_server/models/threat_publication_proposal.py` |
| Create | `apps/live_control_server/services/threat_publication_proposals.py` |
| Create | `apps/live_control_server/routes/threat_publication_proposals.py` |
| Modify | `apps/live_control_server/main.py` |
| Create | `tests/test_threat_publication_proposal_models.py` |
| Create | `tests/test_threat_publication_proposals.py` |
| Create | `tests/test_threat_publication_proposal_api.py` |

Canonical bounded exception: at most two additional test-only fixture/helper or route-registration paths, each reported explicitly.

Any production change under `src/graph_memory/**`, SBW09a/SBW09b models or ledgers, ThreatDraft/accepted mechanics, DungeonMind, UI, or corpus is a stop condition.

### Non-negotiable behavior

- Exact replay and changed-request conflict are decided from the proposal ledger before dependency reads.
- Proposal storage is atomic under one operation-scoped proposal lock.
- Only the exact ready SBW09a operation and exact active SBW09b resolution are consumed.
- `refuse` creates no proposal.
- Create-new seals the Threat node, authored fields, external resource, and exact primary binding.
- Connect-existing seals only resource and binding; it cannot rewrite the existing Threat.
- Labels, aliases, rank, current search, and current head never replace exact identity.
- Resource and binding use SBW08 deterministic identities and contain no copied mechanics.
- Threat proposal ID exactly equals sealed proposal ID.
- Existing proposal vocabulary is `created_new` / `matched_existing`.
- Every accepted node assertion has the required nonblank identity outcome.
- Reuse `seal_promote_proposal`, `verify_promote_proposal`, and existing no-write reconstruction; do not clone them.
- Exact-parent preflight reads the immutable expected parent and performs no graph write.
- No confirmation, commit, receipt, recovery, or post-commit verification enters c1.

### Required state proof

| Condition | Required result |
|---|---|
| ready + create-new | one exact active proposal |
| ready + connect-existing | resource and binding only |
| refuse | typed refusal; no proposal path |
| stale/cancelled/superseded operation | typed rejection; no proposal |
| missing/superseded resolution | typed rejection; no proposal |
| exact replay after response loss | same record before dependency reads |
| changed request under same proposal ID | conflict; bytes unchanged |
| competing first proposals | exactly one active proposal |
| explicit replacement | atomic bidirectional supersession lineage |
| moved parent or typed collision | no proposal and no graph mutation |
| storage failure | no partial proposal |
| corrupt ledger | fail closed; no auto-repair |
| restart/read | exact package, contribution, assertion, and lineage identities |

### Required verification

Run the canonical handoff commands, including at minimum:

```bash
uv run pytest -q tests/test_threat_publication_proposal_models.py
uv run pytest -q tests/test_threat_publication_proposals.py
uv run pytest -q tests/test_threat_publication_proposal_api.py
uv run pytest -q tests/test_threat_publication_identity.py
uv run pytest -q tests/test_statblock_binding_graph_contract.py
uv run pytest -q \
  tests/test_extract_promote_proposal.py \
  tests/test_extract_promote_ops_atomic.py
```

Discover and run the exact focused SBW09a tests named by its merged handoff. Run scoped Ruff/compile checks used by neighboring services, plus:

```bash
git diff --check
git diff --name-only a4c00c3c4865781fe80015d1cf7442da626c3f6d...HEAD
```

Baseline-red commands require identical base/head comparison and an explicit waiver. Absent CI is not green CI.

### PR handback

Suggested title:

```text
feat(sbw09c1): add exact durable Threat publication proposals
```

Use the canonical handoff's PR-body template. Record exact base/head, changed paths, bounded exceptions, create/connect effect summaries, replay/race/restart/corruption evidence, proposal seal/reconstruction evidence, no-write comparison, evidence provenance, and confirmation that c2b remains false.

### Stop conditions

Stop if current main changed c1 authority materially; honest reuse requires changing `extract_promote_proposal.py`; the verifier requires fake values or weakened validation; exact-parent preflight is unavailable through public reads; preparation requires a graph write; connect-existing rewrites identity; a production path outside the allowlist is required; c2b/UI work is pulled in; or lock order cycles.

## §6 Lane B — SBW09c2a operation-to-revision lookup

### Mission and authority

```text
The public Graph Kernel can resolve one exact operation ID to zero, one, or many
immutable World Graph revision manifests across the complete revision store,
independent of current head, without mutating graph state or choosing a first
match.
```

```text
Branch: feat/sbw09c2a-operation-revision-lookup
Base:   573698b00028949741786db3361fd1d14d5a8906
Handoff: Docs/Plans/HANDOFF-sbw09c2a-operation-revision-lookup.md
```

### Exact allowlist

| Action | Path |
|---|---|
| Modify | `src/graph_memory/kernel/world_graph.py` |
| Modify | `src/graph_memory/kernel/__init__.py` |
| Create | `tests/test_graph_kernel_operation_revision_lookup.py` |

Canonical bounded exception: one additional test-only fixture/helper path.

Any change to `world_supergraph/storage.py`, revision models or identity, publish/CAS behavior, contribution merge, application services, or UI is a stop condition.

### Public contract

The exact name may follow current Kernel convention, but plural semantics are fixed:

```python
def find_world_graph_revisions_by_operation_id(
    root: Path,
    world_id: str,
    operation_id: str,
) -> tuple[WorldGraphRevision, ...]:
    ...
```

Required behavior:

1. Validate `world_id` through existing authority.
2. Reject blank or whitespace-only operation IDs.
3. Snapshot revision IDs exactly once.
4. Load every enumerated manifest through the typed loader.
5. Match exact case-sensitive full-string membership in `manifest.operation_ids`.
6. Return every match ordered by `(created_at, revision_id)`.
7. Return empty tuple for no revisions or no matches.
8. Propagate any missing, malformed, unreadable, permission, JSON, validation, or integrity failure for an enumerated manifest.
9. Never return partial success after one enumerated manifest fails.
10. Perform no graph payload, head, contribution, manifest, index, cache, receipt, or application write.
11. Perform no current-head or ancestry filtering.
12. Never assert uniqueness or select a first match.

```text
0 matches → no immutable publication observed
1 match   → one immutable candidate for caller verification
>1        → caller-owned ambiguity; lookup does not resolve it
```

### Required state proof

| Condition | Required result |
|---|---|
| no revisions or no exact ID | empty tuple |
| one exact match | exact typed manifest |
| prefix/case variation | no match |
| matching revision behind newer head | still returned |
| matching revision rolled back away | still returned |
| duplicate operation ID | all matches in deterministic order |
| enumerated manifest missing/malformed | entire lookup fails closed |
| revision completes after enumeration | visible only on the next call |
| before/after world-root snapshot | bytes, mtimes, and head unchanged |

### Required verification

Run the canonical handoff commands, including at minimum:

```bash
uv run pytest -q tests/test_graph_kernel_operation_revision_lookup.py
uv run pytest -q \
  tests/test_world_supergraph_storage.py \
  tests/test_graph_kernel_boundary.py \
  tests/test_graph_kernel_contributions.py
```

If owning test names differ, discover and record the exact substitutes before editing. Run scoped Ruff/compile checks plus:

```bash
git diff --check
git diff --name-only 573698b00028949741786db3361fd1d14d5a8906...HEAD
```

Prove head advance, rollback, duplicate IDs, incomplete authority, one enumeration snapshot, and no mutation. Baseline-red and CI claims follow the same truth rules as c1.

### PR handback

Suggested title:

```text
feat(graph): add exact operation-to-revision lookup
```

Use the canonical handoff's PR-body template. Record actual signature/export, exact paths, zero/one/many examples, head-advance/rollback evidence, fail-closed integrity, no-write proof, evidence provenance, and confirmation that c1/c2b and product publication remain false.

### Stop conditions

Stop if current main changed the storage/Kernel assumptions; enumeration or typed manifest loading is absent or unusable; storage/model changes are required; safe lookup requires an index/cache/watcher/migration; only current head or ancestry can be inspected; matching needs normalization or first-win policy; application code is required; or any production path outside the allowlist is needed.

## §7 Cross-lane coordination contract

Expected production path intersection: **none**.

Expected test-file intersection: **none**, except shared regression suites may be executed but not modified.

Stop both lanes if c1 requests changes to:

```text
src/graph_memory/kernel/world_graph.py
src/graph_memory/kernel/__init__.py
```

or c2a requests application changes under:

```text
apps/live_control_server/**
```

c1 must not import c2a. c2a must not import c1. Their first legitimate consumer relationship is c2b after both merge.

Cross-review must reject overlapping ownership, duplicated revision lookup in c1, application scans of graph-storage internals, uniqueness/first-win policy in c2a, hidden commit/receipt behavior in c1, or code copied from draft PR `#474`.

## §8 Merge and evidence protocol

Open two PRs against `main`; do not stack them.

Preferred review order:

```text
1. SBW09c2a — narrow three-path read-only Kernel contract
2. SBW09c1 — larger stateful application proposal contract
```

Either may merge first if independently complete. The second PR to merge must inspect current-main drift and rerun focused/regression evidence at its exact final head.

Before each merge:

1. fetch current `main`;
2. inspect drift and conflicts;
3. resolve documentation-only conflict without altering the invariant;
4. rerun focused and owning regression evidence;
5. record final head SHA and evidence provenance;
6. verify no unrelated or uncommitted work;
7. complete skeptical review through the normal repository process.

No PR may claim visible CI when no workflow run or status context exists.

Record:

| Field | SBW09c1 | SBW09c2a |
|---|---|---|
| PR number | TBD | TBD |
| implementation base | `a4c00c3...` | `573698b...` |
| final head | TBD | TBD |
| merge SHA | TBD | TBD |
| actual changed paths | TBD | TBD |
| focused evidence | TBD | TBD |
| regression evidence | TBD | TBD |
| visible CI | TBD | TBD |
| waivers/baseline failures | TBD | TBD |
| stop conditions | TBD | TBD |

## §9 Mandatory PR #474 re-anchor

Draft PR `#474` is not implementation authority. Do not mark it ready or merge it unchanged after the blockers land.

After both merge, update `docs/sbw09c2b-threat-publication-commit-handoff` from current main and replace provisional assumptions with actual contracts.

Capture from c1:

- exact proposal model/schema and digest fields;
- ledger path, lifecycle states, read/prepare/supersession functions;
- routes and result labels;
- exact operation-scoped lock helper/seam;
- whether that lock can safely own the c2b claim boundary;
- reconstruction helper and expected contribution identity;
- exact Threat/resource/binding/assertion effect fields;
- proposal claim/supersession tests.

Capture from c2a:

- exact public function name, signature, and export;
- result type and deterministic ordering;
- input validation and error propagation;
- zero/one/many behavior;
- exact adversarial/regression tests;
- confirmation that c2b recovery searches by `expected_contribution_id`.

Revalidate c2b's provisional allowlist, lock order, result labels, recovery algorithm, and test owners. Re-run the c2b decomposition; split again if actual contracts expose a separate claim protocol, missing public verification primitive, or unsafe lock boundary.

PR `#474` may become ready only when it contains both blocker merge SHAs, current-main SHA, actual predecessor mapping, corrected allowlist, exact lock order, exact lookup call, exact test owners, fresh skeptical review, and an explicit statement that c2b code does not yet exist.

After that amended handoff merges, create or reset the c2b implementation branch exactly at the handoff merge SHA. Never implement c2b from the present draft branch.

## §10 Review verdicts and whole-cycle stop conditions

Use one of:

```text
APPROVE
APPROVE WITH DOCUMENTED BASELINE WAIVER
REQUEST CHANGES
STOP — HANDOFF INVALIDATED
```

A self-review may be posted only as `COMMENT` with its explicit verdict; the author cannot self-approve.

Stop the whole cycle and write a reconciliation report if:

- current main no longer descends from the anchors;
- another PR materially changed predecessors or allowlisted paths;
- either lane requires unfinished sibling code;
- production allowlists overlap;
- c1 cannot reuse sealed proposal governance honestly;
- c2a cannot expose lookup without storage/model changes;
- owning-boundary proof is blocked by an unresolved baseline failure;
- preparation requires graph mutation;
- lookup requires current-state inference;
- c2b/UI/Hermes/projection/placement/combat enters either blocker;
- branch provenance cannot be reconstructed;
- unrelated changes enter a final diff.

The stop report states the observed fact, invalidated assumption, exact paths/SHAs, smallest repair, which lane remains safe, and what remains unchanged.

## §11 Completion checklist and final handback

The cycle is complete only when:

- [ ] both branch anchors and upstreams are verified;
- [ ] current-main drift is inspected before edits;
- [ ] c1 and c2a remain inside their separate allowlists;
- [ ] each has its own PR, evidence, review, and final-head verification;
- [ ] production paths do not overlap;
- [ ] both merge SHAs are recorded;
- [ ] PR `#474` remains blocked during implementation;
- [ ] PR `#474` is amended against actual merged contracts;
- [ ] the amended c2b handoff is freshly reviewed and merged;
- [ ] c2b implementation starts only from that merge SHA.

Return:

```text
SBW09c1
  PR:
  base:
  final head:
  merge SHA:
  changed paths:
  focused evidence:
  regression evidence:
  CI provenance:
  waivers:

SBW09c2a
  PR:
  base:
  final head:
  merge SHA:
  changed paths:
  focused evidence:
  regression evidence:
  CI provenance:
  waivers:

Cross-lane review
  path overlap:
  public contract collision:
  unresolved stop conditions:

SBW09c2b re-anchor
  PR #474 amended head:
  current-main anchor:
  c1 actual contract captured:
  c2a actual contract captured:
  provisional assumptions removed:
  fresh review verdict:
  implementation dispatch SHA:
```

Distinguish author-local tests, independently rerun tests, visible CI, and operator dogfood. No evidence category substitutes for another.
