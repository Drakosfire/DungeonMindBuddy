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

Use this prompt to start the execution stewardship turn:

```text
Execute the two independent implementation blockers for SBW09c2b in
Drakosfire/DungeonMindBuddy.

Current verified main is
573698b00028949741786db3361fd1d14d5a8906.

SBW09c1 implementation branch:
  feat/sbw09c1-threat-publication-proposal
  exact authority anchor:
  a4c00c3c4865781fe80015d1cf7442da626c3f6d

SBW09c2a implementation branch:
  feat/sbw09c2a-operation-revision-lookup
  exact authority anchor:
  573698b00028949741786db3361fd1d14d5a8906

Both branches currently contain zero implementation commits. Implement them as
separate PRs with separate worktrees and separate review evidence. The canonical
checked-in implementation handoffs are complete authority; do not compress,
reinterpret, or combine them.

SBW09c1 must deliver the exact durable no-write Threat publication proposal.
SBW09c2a must deliver the read-only public Graph Kernel operation-to-revision
lookup. Their production allowlists do not overlap. If implementation discovers
that they must overlap, stop both lanes and report the contract collision.

Do not implement SBW09c2b. Keep draft PR #474 open and blocked. After c1 and c2a
merge, amend #474 against the actual merged proposal model/service/lock contract
and the actual public lookup signature, tests, and merge SHAs.
```

## §1 Stewardship mission and invariant

### Mission

Implement and merge SBW09c1 and SBW09c2a as two independently reviewable capabilities so that the exact Threat publication proposal contract and the exact immutable-revision recovery lookup both exist before SBW09c2b is re-anchored.

### Stewardship invariant

```text
The c1 and c2a implementations remain isolated, each proves only its canonical
handoff invariant, neither imports the other's unfinished branch, and no c2b
commit/receipt/recovery behavior begins until both merge and PR #474 is amended
against their actual public contracts.
```

### What this handoff is

This is a coordination and execution handoff for two already-designed implementation slices. It does not replace either canonical implementation handoff:

- [`HANDOFF-sbw09c1-threat-publication-proposal.md`](HANDOFF-sbw09c1-threat-publication-proposal.md)
- [`HANDOFF-sbw09c2a-operation-revision-lookup.md`](HANDOFF-sbw09c2a-operation-revision-lookup.md)

When this jumpstart and a canonical implementation handoff disagree, the canonical implementation handoff wins unless current repository truth proves it stale. A material stale-contract finding is a stop condition, not permission to improvise.

## §2 Current verified truth

### Repository and branch state

| Item | Verified state |
|---|---|
| Current `main` | `573698b00028949741786db3361fd1d14d5a8906` |
| SBW09c1 authority | PR `#471`, merge `a4c00c3c4865781fe80015d1cf7442da626c3f6d` |
| SBW09c1 branch | `feat/sbw09c1-threat-publication-proposal` exactly equals `a4c00c3...`; zero implementation commits |
| SBW09c2a authority | PR `#473`, merge `573698b00028949741786db3361fd1d14d5a8906` |
| SBW09c2a branch | `feat/sbw09c2a-operation-revision-lookup` exactly equals `573698b...`; zero implementation commits |
| SBW09c2b design | draft PR `#474`; design-only, blocked, not implementation authority |
| Latest Threat implementation | SBW09b, merged PR `#467` |

### Capability boundary

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
  → commit intent / one governed merge / receipt / recovery / verification
  → remains false and blocked
```

### What remains false after only one blocker merges

If only c1 merges, there is still no safe immutable-history recovery lookup.

If only c2a merges, there is still no exact durable reviewed Threat publication proposal to commit.

Neither merge authorizes:

- World Graph publication from the Threat workflow;
- a commit intent or receipt ledger;
- proposal confirmation;
- crash recovery;
- committed-revision verification;
- Workbench publication UI;
- Hermes query/hydration;
- Threat projection, placement, or combat.

## §3 Authority precedence and required reading

Use authority in this order:

```text
1. AGENTS.md and external-agent PR-loop rules
2. merged architecture / lifecycle decisions
3. active Threat roadmap and tracker
4. the lane's canonical checked-in implementation handoff
5. merged predecessor code and owning-boundary tests
6. this execution jumpstart
7. PR descriptions, attached files, and chat summaries
```

Every worker must read:

1. `AGENTS.md`.
2. `.cursor/rules/external-agent-pr-loop.mdc`.
3. `.cursor/skills/external-agent-pr-loop/SKILL.md`.
4. `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md`.
5. `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`.
6. the lane's canonical handoff in full.
7. every predecessor and test named by that handoff.

The worker must not rewrite the handoff before implementation. Findings belong in the implementation PR handback or a stop report.

## §4 Execution topology

### Two independent worktrees or agents

Preferred topology:

```text
Steward
├── Lane A: SBW09c1 proposal implementation
│   └── feat/sbw09c1-threat-publication-proposal
└── Lane B: SBW09c2a Kernel lookup implementation
    └── feat/sbw09c2a-operation-revision-lookup
```

Use separate worktrees, environments, branches, commits, PRs, and review evidence. Do not stack one blocker on the other.

Suggested local setup:

```bash
git fetch origin --prune

git worktree add ../dmb-sbw09c1 \
  origin/feat/sbw09c1-threat-publication-proposal

git worktree add ../dmb-sbw09c2a \
  origin/feat/sbw09c2a-operation-revision-lookup
```

Before editing, each worktree must prove its exact anchor:

```bash
git rev-parse HEAD

git status --short
```

Expected:

```text
c1:  a4c00c3c4865781fe80015d1cf7442da626c3f6d
c2a: 573698b00028949741786db3361fd1d14d5a8906
```

### Current-main drift check

The c1 branch intentionally predates the c2a docs merge. Before c1 edits:

```bash
git fetch origin
git merge-base --is-ancestor \
  a4c00c3c4865781fe80015d1cf7442da626c3f6d \
  origin/main

git diff --name-only \
  a4c00c3c4865781fe80015d1cf7442da626c3f6d...origin/main
```

The worker must inspect every intervening path. Documentation-only or unrelated Surface work does not invalidate c1. Any intervening change to c1 predecessors, proposal-governance owners, route registration, or its allowlisted paths requires a stop report and exact re-anchor before coding.

The c2a branch already equals the verified current main anchor. Repeat the ancestry check immediately before editing in case main moved.

### No branch borrowing

Do not cherry-pick or merge:

- draft PR `#474`;
- the sibling blocker branch;
- historical or superseded SBW09 branches;
- generic graph-review recovery experiments;
- unreviewed local changes.

Each implementation PR must remain understandable from its own canonical handoff and merged predecessors.

## §5 Lane A — SBW09c1 exact durable no-write proposal

### §5.1 Mission

```text
The live-control server can turn one exact ready SBW09a publication operation
plus one exact active create-new or connect-existing SBW09b resolution into one
durable, deterministic, no-write publication proposal that seals the exact
World Graph effects for review.
```

### §5.2 Branch and authority

```text
Branch:
  feat/sbw09c1-threat-publication-proposal

Implementation anchor:
  a4c00c3c4865781fe80015d1cf7442da626c3f6d

Canonical handoff:
  Docs/Plans/HANDOFF-sbw09c1-threat-publication-proposal.md
```

### §5.3 Exact production allowlist

| Action | Path |
|---|---|
| Create | `apps/live_control_server/models/threat_publication_proposal.py` |
| Create | `apps/live_control_server/services/threat_publication_proposals.py` |
| Create | `apps/live_control_server/routes/threat_publication_proposals.py` |
| Modify | `apps/live_control_server/main.py` |
| Create | `tests/test_threat_publication_proposal_models.py` |
| Create | `tests/test_threat_publication_proposals.py` |
| Create | `tests/test_threat_publication_proposal_api.py` |

The canonical bounded exception permits at most two additional test-only paths for an existing fixture/helper or route-registration test. Record each path and why a local helper was insufficient.

Any production change under `src/graph_memory/**`, SBW09a/SBW09b models or ledgers, ThreatDraft/accepted mechanics, DungeonMind, UI, or corpus is a stop condition.

### §5.4 Required implementation truths

The worker must preserve all canonical c1 rules, including:

- exact replay and changed-request conflict are decided from the proposal ledger before predecessor or graph reads;
- proposal storage is one atomic replacement under the operation-scoped proposal lock;
- only the exact ready SBW09a operation and exact active SBW09b resolution are consumed;
- `refuse` creates no proposal;
- create-new seals the Threat node, authored fields, external resource, and exact primary binding;
- connect-existing seals only the external resource and exact binding and cannot rewrite the existing Threat;
- labels, aliases, ranking, mutable search, or current head never replace exact identity;
- the external resource and binding use SBW08 deterministic identities and contain no copied mechanics;
- proposal ID exactly equals sealed proposal ID;
- existing proposal vocabulary is `created_new` / `matched_existing`;
- every accepted node assertion has the required nonblank identity outcome;
- `seal_promote_proposal`, `verify_promote_proposal`, and existing no-write contribution reconstruction are reused rather than cloned;
- exact-parent preflight reads the operation's immutable parent and performs no graph write;
- current-head substitution and parent repinning are forbidden;
- no confirmation, commit, receipt, recovery, or post-commit verification is implemented.

### §5.5 Critical state paths

The implementation PR must prove at least:

| Condition | Required result |
|---|---|
| ready operation + active create-new | one exact active proposal |
| ready operation + active connect-existing | resource + binding only |
| refuse | typed refusal; no proposal path |
| stale/cancelled/superseded operation | typed rejection; no proposal |
| missing/superseded resolution | typed rejection; no proposal |
| exact replay after response loss | same durable proposal before dependency reads |
| same proposal ID + changed request | conflict; existing bytes unchanged |
| competing first proposals | exactly one active proposal |
| explicit replacement | atomic old/new supersession lineage |
| parent moved or typed collision | no proposal and no graph mutation |
| storage failure | no partial proposal |
| corrupt ledger | fail closed; no auto-repair |
| restart/read | exact package, contribution, assertion, and lineage identities reload |

### §5.6 Required verification

Run the exact commands from the canonical handoff. At minimum:

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

Discover and run the exact focused SBW09a test paths named by the merged SBW09a handoff before editing. Also run scoped Ruff/compile checks used by the neighboring services and:

```bash
git diff --check
git diff --name-only <implementation-base>...HEAD
```

For baseline-red commands, run the identical command at base and head and record the comparison. Do not convert absent CI or skipped tests into a green claim.

### §5.7 PR and handback

Suggested title:

```text
feat(sbw09c1): add exact durable Threat publication proposals
```

The PR body must use the handoff's `pr_body_template` and include:

- exact base and head;
- exact changed paths and any bounded test exception;
- create-new and connect-existing effect summaries;
- proof the graph head, revisions, predecessor ledgers, ThreatDraft, and accepted mechanics are unchanged except permitted SBW09a monotonic stale refresh;
- exact replay, conflict, race, restart, corruption, and storage-failure evidence;
- proposal seal/reconstruction evidence;
- author-local tests versus visible CI;
- explicit statement that c2b and all later product behavior remain false.

### §5.8 Lane A stop conditions

Stop and report if:

- current main changed any material c1 predecessor or allowlisted path;
- honest proposal reuse requires changing `extract_promote_proposal.py`;
- the existing verifier requires fake identity values or weakened validation;
- exact-parent preflight is unavailable through public reads;
- safe preparation requires a graph or contribution write;
- connect-existing requires rewriting Threat identity or authored fields;
- any production path outside the canonical allowlist is required;
- commit, receipt, recovery, verification, or UI work is being pulled in;
- a lock-order cycle appears between proposal, identity, publication, or graph owners.

The stop report must name the exact owner/path inspected, the violated invariant, the smallest predecessor slice required, and what remains unchanged.

## §6 Lane B — SBW09c2a operation-to-revision lookup

### §6.1 Mission

```text
The public Graph Kernel can resolve one exact operation ID to zero, one, or many
immutable World Graph revision manifests across the complete revision store,
independent of current head, without mutating graph state or choosing a first
match.
```

### §6.2 Branch and authority

```text
Branch:
  feat/sbw09c2a-operation-revision-lookup

Implementation anchor:
  573698b00028949741786db3361fd1d14d5a8906

Canonical handoff:
  Docs/Plans/HANDOFF-sbw09c2a-operation-revision-lookup.md
```

### §6.3 Exact production allowlist

| Action | Path |
|---|---|
| Modify | `src/graph_memory/kernel/world_graph.py` |
| Modify | `src/graph_memory/kernel/__init__.py` |
| Create | `tests/test_graph_kernel_operation_revision_lookup.py` |

The canonical bounded exception permits one additional test-only fixture/helper path.

Any change to `world_supergraph/storage.py`, revision models, revision identity, publish/CAS behavior, contribution merge, application services, or UI is a stop condition.

### §6.4 Required public contract

The exact function name may follow current Kernel conventions, but the canonical plural semantics are fixed:

```python
def find_world_graph_revisions_by_operation_id(
    root: Path,
    world_id: str,
    operation_id: str,
) -> tuple[WorldGraphRevision, ...]:
    ...
```

Required behavior:

1. validate `world_id` through existing path/storage authority;
2. reject blank or whitespace-only operation IDs;
3. snapshot revision IDs exactly once using the existing internal enumeration owner;
4. load every enumerated manifest through the typed manifest loader;
5. match exact case-sensitive full-string membership in `manifest.operation_ids`;
6. return every match sorted deterministically by `(created_at, revision_id)`;
7. return an empty tuple for no revisions or no matches;
8. propagate missing, malformed, unreadable, permission, JSON, validation, or integrity errors for any enumerated manifest;
9. never return partial success after an enumerated manifest fails;
10. perform no graph payload, head, contribution, manifest, index, cache, receipt, or application write;
11. perform no current-head or ancestry filtering;
12. never assert uniqueness or choose the first match.

The result contract is deliberately plural:

```text
0 matches → no immutable publication observed
1 match   → one immutable candidate for caller verification
>1        → ambiguity owned by the caller; lookup does not resolve it
```

### §6.5 Critical state paths

The implementation PR must prove at least:

| Condition | Required result |
|---|---|
| no revisions | empty tuple |
| revisions without exact ID | empty tuple |
| one exact match | one exact typed manifest |
| similar prefix/case-varied ID | no match |
| matching revision behind newer head | match still returned |
| matching revision rolled back away from head | match still returned |
| same operation ID in multiple manifests | all matches in deterministic order |
| enumerated manifest missing or malformed | whole lookup fails closed |
| revision completes after enumeration snapshot | absent this call; visible next call |
| before/after world-root snapshot | byte- and head-identical |

### §6.6 Required verification

Run the exact commands from the canonical handoff. At minimum:

```bash
uv run pytest -q tests/test_graph_kernel_operation_revision_lookup.py

uv run pytest -q \
  tests/test_world_supergraph_storage.py \
  tests/test_graph_kernel_boundary.py \
  tests/test_graph_kernel_contributions.py
```

If current test filenames differ, discover the exact owning equivalents before editing and record the substitution. Also run scoped Ruff/compile checks and:

```bash
git diff --check
git diff --name-only <implementation-base>...HEAD
```

Required adversarial proof includes:

- head advance cannot hide an earlier match;
- rollback cannot hide an immutable match;
- duplicate operation IDs remain plural;
- incomplete authority fails closed without a partial list;
- one fixed enumeration snapshot defines one call;
- no bytes, mtimes, head, indexes, or manifests change.

### §6.7 PR and handback

Suggested title:

```text
feat(graph): add exact operation-to-revision lookup
```

The PR body must use the handoff's `pr_body_template` and include:

- exact base and head;
- actual public signature/export;
- exact changed paths and any bounded test exception;
- zero/one/many examples;
- head-advance and rollback proof;
- corruption/incomplete-manifest behavior;
- before/after no-write evidence;
- author-local tests versus visible CI;
- explicit statement that c1, c2b, confirmation, receipts, UI, and product publication remain false.

### §6.8 Lane B stop conditions

Stop and report if:

- current main changed the declared storage or Kernel facade assumptions;
- the existing revision enumeration or typed manifest loader is absent or unusable;
- implementation requires changing `world_supergraph/storage.py` or revision models;
- safe lookup requires a durable secondary index, cache, watcher, or migration;
- the implementation can only inspect current head or its ancestry;
- operation identity requires normalization, prefix matching, or first-win selection;
- any application or Threat-specific code is required;
- a production path outside the canonical allowlist is required.

## §7 Coordination contract between lanes

### §7.1 Paths must remain disjoint

Expected production intersection:

```text
none
```

Expected test intersection:

```text
none, except shared existing regression suites executed but not modified
```

If c1 requests a production change in:

```text
src/graph_memory/kernel/world_graph.py
src/graph_memory/kernel/__init__.py
```

or c2a requests an application change under:

```text
apps/live_control_server/**
```

stop both lanes. The decomposition has changed and PR `#474` cannot be trusted without a new reconciliation.

### §7.2 No implementation dependency

c1 must not import the new c2a lookup.

c2a must not import c1 proposal models or services.

The first legitimate consumer relationship is c2b after both merge.

### §7.3 Cross-review questions

After each lane reaches review-ready state, the steward asks:

For c1:

- Did any graph write or receipt behavior enter the proposal path?
- Did connect-existing rewrite the Threat?
- Did proposal replay perform dependency reads?
- Did the implementation clone or weaken the existing proposal verifier?
- Did any mechanics body enter graph/proposal payloads?

For c2a:

- Is the function truly plural?
- Does it scan one complete immutable revision snapshot rather than head ancestry?
- Can duplicate IDs be silently collapsed?
- Can one bad manifest be skipped?
- Did any read create an index, cache, directory, or mtime change?

For both:

- Are actual changed paths within the lane's canonical allowlist?
- Are failures proved at owning boundaries rather than only mocked helpers?
- Are baseline and CI claims honest?
- Do all named successors remain false?

## §8 Merge and revalidation protocol

### §8.1 PR independence

Open two PRs against `main`. Do not stack either PR on the other.

Each PR must be mergeable and reviewable independently. The second PR to merge must update from current `main` or otherwise prove its base drift contains no material collision and rerun all focused and regression evidence at its final head.

### §8.2 Preferred review order

Preferred order is:

```text
1. SBW09c2a — narrow three-path read-only Kernel contract
2. SBW09c1 — larger stateful application proposal contract
```

This is a review preference, not a dependency. Either may merge first if its review is complete and the sibling remains path-disjoint.

### §8.3 Final-head evidence

Before merge, each lane must:

1. fetch current `main`;
2. inspect base drift;
3. resolve any documentation-only merge conflict without altering the canonical invariant;
4. rerun focused tests and owning regressions at the exact final head;
5. record the final head SHA and evidence provenance in the PR;
6. verify no uncommitted or unrelated work is present;
7. merge through the repository's normal review process.

No worker may claim visible CI if the repository exposes no workflow run or status context.

### §8.4 Handback ledger

The steward records:

| Field | SBW09c1 | SBW09c2a |
|---|---|---|
| PR number | TBD | TBD |
| implementation base | `a4c00c3...` | `573698b...` |
| final head | TBD | TBD |
| merge SHA | TBD | TBD |
| actual changed paths | TBD | TBD |
| focused tests | TBD | TBD |
| regression tests | TBD | TBD |
| visible CI | TBD | TBD |
| waivers/baseline failures | TBD | TBD |
| stop conditions encountered | TBD | TBD |

## §9 Mandatory PR #474 re-anchor after both merges

Draft PR `#474` is not implementation authority. Do not mark it ready or merge it unchanged merely because both blockers landed.

After both implementation PRs merge, update the `docs/sbw09c2b-threat-publication-commit-handoff` branch from current main and amend:

### §9.1 Actual c1 contract map

Record exact:

- proposal model names and schemas;
- proposal request digest field and sealed proposal digest field;
- proposal ledger path and lifecycle states;
- service read/prepare/supersession functions;
- route paths and response labels;
- proposal lock helper or internal seam;
- whether the operation-scoped lock can safely become the shared c2b lifecycle lock;
- reconstruction helper and expected contribution identity;
- effect summary fields for Threat, external resource, binding, and accepted assertion IDs;
- c1 tests that prove proposal claim/supersession behavior.

### §9.2 Actual c2a contract map

Record exact:

- public function name and signature;
- exported module path;
- result type and deterministic order;
- input validation;
- zero/one/many semantics;
- error propagation behavior;
- exact regression and adversarial tests;
- whether c2b should search by `expected_contribution_id` exactly as designed.

### §9.3 Revalidate c2b's provisional allowlist

Every c2b production and test path must be checked against actual c1/c2a names. Replace provisional paths, models, result labels, lock assumptions, and test filenames. Remove anything no longer required; do not widen silently.

### §9.4 Re-run c2b decomposition

Confirm that one backend slice can still own:

```text
proposal claim
→ durable intent
→ one Kernel merge
→ ambiguous-outcome recovery
→ immediate committed-unverified receipt
→ exact immutable verification
```

Split again if actual c1/c2a contracts reveal a separately useful durable claim protocol, a missing public verification primitive, or a lock boundary that cannot safely span proposal supersession and commit intent.

### §9.5 Exact dispatch gate

PR `#474` may become ready only when it contains:

- both blocker merge SHAs;
- current main SHA;
- actual predecessor mapping;
- corrected allowlist;
- exact lock order;
- exact recovery lookup call;
- exact test owners;
- a fresh skeptical review;
- an explicit statement that no c2b code exists yet.

After the amended handoff merges, create or reset the c2b implementation branch exactly at that merge SHA. Do not implement c2b from the current draft branch.

## §10 Skeptical review protocol

The steward performs one review pass per implementation PR and one cross-lane review after both are complete.

### Lane review verdict

Use:

```text
APPROVE
APPROVE WITH DOCUMENTED BASELINE WAIVER
REQUEST CHANGES
STOP — HANDOFF INVALIDATED
```

The author cannot self-approve through GitHub. A self-review may be posted as `COMMENT` with the explicit verdict and supporting evidence.

### Cross-lane review

After both final heads exist but before the second merge, compare their changed paths and public imports. Reject:

- overlapping production ownership;
- c1 importing c2a before c2b;
- c2a importing application code;
- duplicated revision lookup logic in c1;
- application scanning of graph storage internals;
- c2a uniqueness or first-win policy;
- hidden receipt or commit behavior in c1;
- any code copied from draft PR `#474`.

## §11 Whole-cycle stop conditions

Stop execution and write one reconciliation report if:

- current main no longer descends from the declared anchors;
- an open or merged PR changed c1/c2a predecessors or allowlisted paths materially;
- either lane requires the sibling lane's unfinished code;
- the production allowlists overlap;
- c1 cannot reuse sealed proposal governance honestly;
- c2a cannot expose the lookup without storage/model changes;
- a baseline failure prevents owning-boundary proof and cannot be isolated;
- proposal preparation requires graph mutation;
- revision lookup requires head/current-state inference;
- implementation begins to include c2b, UI, Hermes, projection, placement, or combat;
- exact branch provenance cannot be reconstructed;
- the final PR diff includes unrelated user or agent changes.

A reconciliation report must state:

```text
observed repository fact
which canonical handoff assumption it invalidates
exact paths and SHAs inspected
smallest design/predecessor repair required
which lane remains safe to continue, if any
what behavior remains unchanged
```

## §12 Stewardship completion checklist

This execution cycle is complete only when:

- [ ] c1 branch provenance is verified at `a4c00c3...`.
- [ ] c2a branch provenance is verified at `573698b...`.
- [ ] current-main drift is inspected before edits.
- [ ] c1 is implemented strictly within its canonical allowlist.
- [ ] c2a is implemented strictly within its canonical allowlist.
- [ ] each lane has its own PR, evidence, skeptical review, and final-head verification.
- [ ] no production path overlaps across the two PRs.
- [ ] both PRs merge with exact merge SHAs recorded.
- [ ] draft PR `#474` remains blocked during implementation.
- [ ] PR `#474` is amended against actual c1/c2a contracts after both merges.
- [ ] the amended c2b handoff receives fresh review before merge.
- [ ] no c2b implementation begins before its amended authority merges.

## §13 Required final handback

Return one concise handback containing:

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

The final handback must distinguish author-local tests, independently rerun tests, visible CI, and operator dogfood. No evidence category may substitute for another.
