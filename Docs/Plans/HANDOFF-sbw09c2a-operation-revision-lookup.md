---
pr_body_template: |
  ## Outcome
  The public Graph Kernel can resolve one exact operation ID to zero, one, or many immutable World Graph revisions across the complete revision store, independent of the current head, without mutating graph state or choosing a first match.

  ## Merge-ready invariant
  For one exact `(world_id, operation_id)` lookup, every complete immutable revision manifest in one enumeration snapshot is inspected exactly once and every exact operation-ID membership match is returned in deterministic order; missing matches remain explicit, multiple matches remain ambiguous, corrupt or unreadable authority fails closed, current-head movement or rollback cannot hide an existing match, and the lookup performs no graph, head, contribution, manifest, or index mutation.

  ## Evidence required to merge
  | Guarantee | Owning boundary | Required evidence | Result |
  |---|---|---|---|
  | Complete immutable revision enumeration | storage-to-Kernel read boundary | baseline/head-advanced/rolled-back fixtures | {{TODO}} |
  | Exact zero/one/many semantics | public Kernel facade | no-match, unique-match, duplicate-operation tests | {{TODO}} |
  | No first-win or head-only fallback | public contract | ambiguity and rollback sequences | {{TODO}} |
  | Fail-closed integrity | manifest parser | corrupt/missing manifest tests | {{TODO}} |
  | Read-only behavior | storage boundary | before/after filesystem snapshot | {{TODO}} |

  ## Scope and explicit deferrals
  - Design base: `d101341bbffeb07627097de2dbcfe84930e01ce2`
  - Dispatch base: {{TODO exact immutable main SHA containing this handoff}}
  - Actual base/head: {{TODO}}
  - Actual changed paths: {{TODO}}
  - Deferred: Threat proposal commit, durable commit intent/receipt, confirmation API, exact Threat/resource/binding verification, UI, Hermes, projection, placement, and combat.

  ## Evidence produced
  {{TODO}}

  ## Gaps, waivers, and stop conditions
  {{TODO: none or exact stop report}}
---

# HANDOFF — SBW09c2a exact operation-to-revision lookup

**Created:** 2026-08-01  
**Status:** ACTIVE READ-ONLY PREREQUISITE — safe to implement in parallel with SBW09c1 after this handoff merges.  
**Canonical path:** `Docs/Plans/HANDOFF-sbw09c2a-operation-revision-lookup.md`  
**Design base:** `d101341bbffeb07627097de2dbcfe84930e01ce2`  
**Dispatch base:** exact immutable `origin/main` SHA containing this handoff, recorded before implementation.  
**Suggested branch:** `feat/sbw09c2a-operation-revision-lookup`

> This slice does not commit a Threat publication. It closes the public read-contract gap required for honest response-loss and restart recovery in SBW09c2b.

## §0 Capability decomposition

| Candidate outcome | Independently useful? | Public/durable contract changed? | Decision |
|---|---:|---:|---|
| Resolve exact operation ID across all immutable revision manifests | Yes | Public Kernel read contract | Include in SBW09c2a |
| Interpret zero/one/many matches without first-win fallback | Yes | Public result semantics | Include in SBW09c2a |
| Confirm a Threat proposal | Yes | Application write contract | SBW09c2b |
| Persist commit intent/receipt and recover a crash | Yes | Application durable contract | SBW09c2b |
| Verify exact Threat/resource/binding at the committed revision | Yes | Threat publication outcome contract | SBW09c2b |
| Modify World Graph write/CAS semantics | No need discovered | Kernel write contract | Reject |

**Selected capability:** a complete, deterministic, read-only public Kernel lookup from exact operation ID to immutable revision manifests.

### Why this split is required

Existing synchronous confirmation can report the revision returned by `merge_contribution_to_revision`, but no durable Threat commit receipt exists. If the process dies after the Kernel advances the head and before the application stores its receipt, a safe retry cannot depend on current head:

- another publication may advance the head;
- the head may be rolled back;
- `merge_contribution_to_revision` checks the original expected parent before its idempotent-noop path;
- the committed immutable revision still records the exact contribution/operation ID in `WorldGraphRevision.operation_ids`.

The storage package already owns `list_revision_ids` and exact typed manifest loading. The public Kernel facade exposes lookup only by already-known revision ID. Application code must not reach through that boundary into `world_supergraph.storage` or scan directories itself.

## §1 Mission and merge-ready invariant

```text
Given one exact world ID and operation ID, the public Graph Kernel returns every
immutable published revision whose manifest contains that exact operation ID,
regardless of current head position, without mutating durable state or silently
selecting one match.
```

```text
For one exact (world_id, operation_id) lookup, every complete immutable revision
manifest in one enumeration snapshot is inspected exactly once and every exact
operation-ID membership match is returned in deterministic order; missing
matches remain explicit, multiple matches remain ambiguous, corrupt or unreadable
authority fails closed, current-head movement or rollback cannot hide an existing
match, and the lookup performs no graph, head, contribution, manifest, or index
mutation.
```

**Mission falsification test:** this is not one slice if implementation adds a graph write, contribution merge, Threat-specific model, application receipt store, confirmation route, background index, watcher, migration, or current-head-only shortcut.

### Pre-dispatch critique

- Most likely failure: return the first directory or current-head ancestry match and silently hide duplicate operation IDs.
- Most dangerous recovery error: report `not_found` after head rollback even though the immutable committed revision still exists.
- Required proof: complete revision-store enumeration, exact membership, deterministic zero/one/many results, and before/after filesystem equality.
- Split trigger: needing a durable secondary operation index or changing revision/write semantics.

## §2 Context, authority, and boundaries

| Concern | Authority |
|---|---|
| Revision metadata | `WorldGraphRevision.operation_ids` in `src/graph_memory/world_supergraph/model.py` |
| Immutable revision enumeration | existing `list_revision_ids` in `src/graph_memory/world_supergraph/storage.py` |
| Manifest loading/integrity | existing `load_world_graph_revision_manifest` |
| Public boundary | `src/graph_memory/kernel/world_graph.py` and `src/graph_memory/kernel/__init__.py` |
| Motivation | Threat tracker/roadmap, SBW09c1 handoff, and SBW09c publication re-anchor |
| Named successor | SBW09c2b proposal-bound commit, durable receipt/recovery, exact verification |

Read in order:

1. `AGENTS.md` and external-agent PR-loop rules.
2. Threat tracker, roadmap, SBW09c1 handoff, and re-anchor report.
3. `src/graph_memory/world_supergraph/model.py`.
4. `src/graph_memory/world_supergraph/storage.py`.
5. `src/graph_memory/kernel/world_graph.py`.
6. `src/graph_memory/kernel/__init__.py`.
7. World Graph storage and Kernel facade tests.
8. `merge_contribution_to_revision` and `confirm_extract_promote` only to preserve recovery motivation; do not change them.

### Locked boundaries

- Revision manifests remain immutable source authority.
- Current head is not a complete publication-history index.
- Exact operation identity is case-sensitive full-string equality; no prefix, slug, normalization, or label matching.
- The result is plural; callers own zero/one/many policy.
- Application code must not import `world_supergraph.storage` for this lookup after merge.
- This slice adds no index, cache, receipt, or write.

## §3 Observable-path inventory

| Path | Current behavior | Required behavior | Owner |
|---|---|---|---|
| No revisions | internal enumeration only | return empty tuple | public Kernel facade |
| Revisions, no match | no public operation lookup | explicit empty result | public Kernel facade |
| One exact match | caller must know revision ID | return exact typed manifest | public Kernel facade |
| Match behind newer head | no public path | still return earlier revision | complete scan |
| Match on rolled-back-away revision | head chain hides it | still return immutable revision | complete scan |
| Same operation ID in multiple manifests | no contract | return every match; never first-win | result semantics |
| Similar/prefix/case-varied ID | no contract | no match unless exact equality | matcher |
| Enumerated manifest missing | internal loader raises | fail closed; no partial success | manifest loader |
| Enumerated manifest malformed | typed validation raises | fail closed; no partial success | typed parser |
| Concurrent completed revision | no contract | fixed enumeration snapshot; next call may see new revision | enumeration function |
| Read-only check | no public path | no bytes/mtimes/head/index changes | storage boundary |

## §4 Files in scope — allowlist

| Action | Path | Purpose |
|---|---|---|
| Modify | `src/graph_memory/kernel/world_graph.py` | add public plural operation lookup using existing storage enumeration and manifest reads |
| Modify | `src/graph_memory/kernel/__init__.py` | export the public function |
| Create | `tests/test_graph_kernel_operation_revision_lookup.py` | zero/one/many, rollback, head advance, integrity, concurrency, and read-only proof |

### Bounded discovery exception

```text
Directory: tests/
Maximum additional paths: 1
Allowed: existing World Graph fixture/helper only
Rule: test-only reuse; no production scope
Report: exact path and reason
```

Any change to `world_supergraph/storage.py`, revision models, revision IDs, publish/CAS behavior, contribution merge, application services, or UI is a stop condition unless current-main reconnaissance proves the existing `list_revision_ids` or manifest API is absent or unusable. Stop and report rather than widening silently.

## §5 Explicit exclusions and demolition

Excluded:

- Threat proposal/commit models;
- application receipt or commit-intent storage;
- graph publication or retry;
- operation-ID uniqueness enforcement;
- background index/cache;
- head ancestry lookup;
- rollback behavior changes;
- contribution ledger repair;
- UI, Hermes, projection, placement, and combat.

```text
Replaced path: future application/internal revision-directory scanning for operation recovery
Deleted in this PR: no — no production application path exists yet
Retained reason: existing storage enumeration and manifest readers remain internal implementation
Named remaining consumer: World Graph storage tests and Kernel facade
Required deletion owner: SBW09c2b must use this public function rather than internal storage
```

## §6 Implementation contract and matrices

### §6.1 Public function

Add one public Kernel function with explicit plural semantics:

```python
def find_world_graph_revisions_by_operation_id(
    root: Path,
    world_id: str,
    operation_id: str,
) -> tuple[WorldGraphRevision, ...]:
    ...
```

Naming may change only if current Kernel conventions require it; plural zero/one/many semantics may not.

Required behavior:

1. Validate `world_id` through existing storage/path authority.
2. Reject blank or whitespace-only `operation_id` with `ValueError`.
3. Snapshot revision IDs once using existing `list_revision_ids`.
4. Load every enumerated manifest through `load_world_graph_revision_manifest`.
5. Include a manifest only when `operation_id in manifest.operation_ids` by exact string equality.
6. Return immutable typed manifests sorted by `(created_at, revision_id)`.
7. Return an empty tuple when no complete revisions exist or none match.
8. Propagate typed not-found, permission, JSON, Pydantic, or integrity errors for an enumerated manifest; never skip it and return partial success.
9. Perform no graph payload read unless existing manifest validation requires it.
10. Perform no write, repair, index update, head requirement, or current-head filtering.

### §6.2 Concurrency semantics

The lookup snapshots revision IDs once at call start. A revision completed after enumeration may appear on the next call; it is not partially included in the current call. Every ID in the snapshot must either produce one valid typed manifest or fail the whole lookup.

Publication writes a complete revision directory before advancing head. The lookup therefore does not use head as a completeness gate. If an enumerated directory is incomplete, fail closed rather than treating it as absent.

### §6.3 Caller policy

The function does not decide publication outcome:

```text
0 matches → not observed
1 match   → unique immutable publication candidate
>1        → ambiguous integrity condition; caller must fail closed
```

SBW09c2b must additionally verify exact contribution identity, parent, accepted assertions, Threat/resource/binding objects, and a revision-pinned projection before persisting a recovered receipt.

### §6A State/fallback matrix

| Condition | Result | Fallback |
|---|---|---|
| no revision directory | empty tuple | none |
| exact unique match | one typed manifest | none |
| match behind newer head | one typed manifest | no head fallback needed |
| head rolled back away | immutable match still returned | none |
| duplicate operation IDs | multiple typed manifests | caller fails closed |
| malformed/missing enumerated manifest | exception | no partial list |
| blank operation ID | `ValueError` | none |
| unreadable root | propagated error | none |

### §6B Identity matrix

| Identity | Rule |
|---|---|
| world | exact safe `world_id` |
| operation | exact case-sensitive full string |
| revision | typed manifest `revision_id` |
| ordering | `created_at`, then `revision_id` |
| uniqueness | not assumed or enforced by lookup |

### §6C Persistence/replay matrix

| Operation | Durable effect | Replay |
|---|---|---|
| lookup | none | same immutable snapshot yields same ordered result |
| concurrent publish after enumeration | none | next lookup may include it |
| corrupt manifest | none | repeat fails until repaired externally |
| rollback | head changed elsewhere | lookup still scans all immutable revisions |

### §6D Commit-point declaration

```text
Commit point: none.
Durable writes: none.
World Graph head read: unnecessary.
World Graph head write: prohibited.
```

## §7 Verification ownership map and commands

| Guarantee | Boundary | Command/scenario |
|---|---|---|
| Public import and strict input | Kernel facade | `uv run pytest -q tests/test_graph_kernel_operation_revision_lookup.py` |
| Zero/one/many exact results | Kernel facade | same command |
| Newer head does not hide prior match | immutable revision store | same command |
| Rollback does not hide prior match | immutable revision store | same command |
| Duplicate operation ID remains plural | public contract | same command |
| Malformed/missing manifest fails closed | manifest parser | same command |
| Concurrent completed revision is next-call visible only | enumeration snapshot | same command |
| No mutation | filesystem snapshot | same command |
| Existing World Graph regression | owning suites | `uv run pytest -q tests/test_world_supergraph_storage.py tests/test_graph_kernel_boundary.py tests/test_graph_kernel_contributions.py` or exact current equivalents discovered before editing |
| Hygiene/scope | repository | `git diff --check`; `git diff --name-only <base>...HEAD` |

Required adversarial sequences:

1. Publish baseline and a contribution revision; advance head again; lookup still returns the earlier contribution revision.
2. Roll head back to baseline; lookup still returns the immutable later revision.
3. Publish two synthetic revisions with the same operation ID through the lower-level World Graph publish API; lookup returns two manifests in deterministic order.
4. Create an incomplete enumerated revision directory or remove its manifest; lookup fails closed rather than returning other matches.
5. Fix the enumeration snapshot, complete another revision concurrently, and prove it appears only on the next call.
6. Snapshot every file under the world root before/after lookup; contents and head are byte-identical.

Baseline-red commands require identical base/head comparison and an explicit waiver. No green claim may hide absent CI or skipped tests.

## §8 Required implementation handback

Record exact dispatch base/head, changed paths/diff stat, public signature/export, every §7 result and provenance, zero/one/many examples, rollback/head-advance/concurrency evidence, before/after no-write evidence, baseline failures/waivers, paths outside §4, and confirmation that SBW09c2b and all application/UI behavior remain false.

## §9 Acceptance rubric

- [ ] One read-only public Kernel capability was delivered.
- [ ] Every immutable revision ID in one enumeration snapshot is inspected exactly once.
- [ ] Exact operation-ID equality is the only match rule.
- [ ] Zero, one, and many matches are explicit; no first-win path exists.
- [ ] Current-head advance and rollback cannot hide an immutable match.
- [ ] Corrupt or incomplete enumerated authority fails closed without partial success.
- [ ] Result order is deterministic.
- [ ] No graph payload, head, contribution, manifest, index, cache, or application state is mutated.
- [ ] Application code is not added and internal storage is not exposed directly.
- [ ] Existing Kernel/storage tests remain green or truthfully baseline-waived.
- [ ] SBW09c2b commit/receipt/recovery/verification remains unimplemented.

## §10 Reviewer attack list

- Search for current-head or parent-chain filtering.
- Search for `next(...)`, first match, uniqueness assertion, or silent duplicate collapse.
- Verify exact case-sensitive membership, not substring/prefix/normalized matching.
- Corrupt one enumerated manifest and confirm no partial result returns.
- Roll back head and confirm the detached immutable revision is still found.
- Verify one enumeration snapshot; no changing-directory loop until a preferred answer appears.
- Check export through `graph_memory.kernel`.
- Compare world-root bytes and mtimes before/after.
- Reject new indexes, caches, write locks, application imports, or graph changes.

## §11 Stop conditions

Stop and report if:

- `list_revision_ids` or manifest loading is not safely reusable from the Kernel facade;
- complete lookup requires changing revision storage or write semantics;
- a durable operation index is required;
- concurrent publication cannot be given snapshot semantics without a write lock or storage redesign;
- revisions do not reliably retain operation IDs;
- a path outside §4 is required beyond the bounded test exception;
- required owning-boundary tests are head-only red without waiver.

```text
Stop condition:
Why SBW09c2a cannot absorb it:
Owner/path inspected:
Missing or conflicting contract:
Required broader slice:
Tracker/roadmap change:
Operator decision:
```

## Final dispatch check

- [ ] Handoff merged to main.
- [ ] Exact containing-main SHA recorded.
- [ ] Implementation branch begins at that SHA.
- [ ] SBW09c1 branch does not modify the allowlisted Kernel paths.
- [ ] Current storage still has immutable `operation_ids`, `list_revision_ids`, and typed manifest loading.
- [ ] Every rubric claim maps to §7 proof.
- [ ] No essential constraint exists only in chat.