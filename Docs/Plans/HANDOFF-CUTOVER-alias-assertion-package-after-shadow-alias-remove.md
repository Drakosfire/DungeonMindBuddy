---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: CUTOVER — remaining alias assertion package after shadow-alias-remove
  - Flow: CUTOVER
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-CUTOVER-alias-assertion-package-after-shadow-alias-remove.md
  - Branch: cutover/alias-assertion-package-after-shadow-alias-remove

  ## Verification pointer
  - Implementation predecessor: PR #583 live/replay exit
  - PR #583 head: 2cacc7cbdf77977e86daf29ed2b9058f94d54e70
  - PR #583 merge: 299579bd3c3f78a9393ae3c97c57a1dfd6b155ed
  - Canonical input: rev:0c644e56b45bcaac709012206e3e41c2
  - Forensic predecessor: PR #577, closed unmerged at b31bbc32b98c170c44f75de3fa1e8e252e7d0555
  - Verification: exact §7 results from implementation handback

  This PR reconstructs a two-row alias assertion package. It does not mutate
  the World Graph and does not reopen the six retired merge-shadow aliases.
---

# HANDOFF — reconstruct remaining alias assertion package

**Created:** 2026-08-13  
**Status:** READY — do not dispatch until `HANDOFF-DOCUMENTS-cutover-exact-six-live-exit-state-sync.md` merges to `main`.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-CUTOVER-alias-assertion-package-after-shadow-alias-remove.md`  
**Conversation/workstream:** `CUTOVER — remaining alias assertion package after shadow-alias-remove`  
**Flow / owner:** `CUTOVER`  
**Direction:** DESIGN → CODE → REVIEW  
**Design base:** post-live Eldyrwild `rev:0c644e56b45bcaac709012206e3e41c2` recorded by the exact-six live-exit state sync  
**Suggested branch:** `cutover/alias-assertion-package-after-shadow-alias-remove`  
**PR title:** `CUTOVER: reconstruct remaining alias assertion package`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process:
> [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md).
>
> **Dispatch gate:** Before the first code change, fetch/re-anchor current
> `origin/main`, prove it is a descendant of the live-exit state-sync merge,
> prove this canonical handoff exists on that base, and prove the tracker names
> `cutover-alias-assertion-package-after-shadow-alias-remove` as `READY`. Record
> the exact dispatch-base SHA in the implementation handback.
>
> Reconstruct exactly two source-grounded aliases. Do not mutate the World
> Graph. Do not reopen the six retired merge-shadow aliases. Do not seal a
> one-row package. If a new generic Kernel capability is required, STOP.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Alias blocker element** | One current durable element classified `EVIDENCE_PROVENANCE` because a substantive Buddy alias cannot yet be expressed at DungeonMind assertion grain. |
| **Source assertion** | One revision-bound active Buddy `GraphContributionAssertion` whose semantic payload explicitly carries the alias claim. |
| **Alias adoption row** | One deterministic DungeonMind `AliasAssertion`-compatible value plus metadata, accompanied by Buddy source-lineage proof. |
| **Complete two-row package** | Both remaining blockers covered; `residual_count = 0`; no one-row seal. |

The flow identifier `CUTOVER` is the owner for this slice.

## §1 Mission and merge-ready invariant

**Mission:** Reconstruct exactly the two remaining source-grounded
`EVIDENCE_PROVENANCE` blockers as DungeonMind-compatible AliasAssertion rows
from current revision-bound Buddy authority, seal a complete two-row package,
and prove package-construction `EVIDENCE_PROVENANCE: 2 → 0` without mutating
the World Graph.

**Merge-ready invariant:** Against the exact post-#583 live Eldyrwild revision,
the same two `EVIDENCE_PROVENANCE` blocker elements are enumerated losslessly;
both are covered by deterministic AliasAssertion rows whose value, assertion
identity lineage, contribution identity, contribution source SHA, metadata, and
evidence are proven from revision-bound Buddy authority; `EVIDENCE_PROVENANCE`
clears 2→0; `ATTRIBUTE_ASSERTION` remains 0; `IDENTITY_HISTORY` remains 20;
`CONTRIBUTION_HISTORY` remains 5291; relationship inventories remain
`323 / 314 / 9 / 3` and `323 / 318 / 5 / 3`; canonical World Graph head, tree,
contribution authority, identity authority, and node aliases are unchanged.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern the PR? | **Yes.** Two reconstructable alias rows, one sealed package, no mutation. |
| Most likely failure | Sealing a one-row package, or treating PR #577 as current implementation ancestry. |
| Second likely failure | Inventing metadata/evidence instead of copying locked assertion/contribution/source lineage. |
| Third likely failure | Mutating the live world or reopening the six retired aliases. |
| Stop condition | Either alias fails reconstruction, a third EP blocker appears, or a Kernel change is required. |

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | `AGENTS.md`; tracker; continuity status; exact-six live-exit state sync |
| Canonical input | `rev:0c644e56b45bcaac709012206e3e41c2` / payload `0640d7ef8ce152ee4f656959e0e9a6c9c2fdf5ecc8bd721729b3019170d677f2` |
| Live parent (historical) | `rev:5a7c13ae45c49a65b402920499be72ed` |
| Implementation predecessor | PR #583; head `2cacc7cb…`; merge `299579bd…`; 3 review cycles; live/replay proven |
| Forensic predecessor | PR #577, closed unmerged at `b31bbc32b98c170c44f75de3fa1e8e252e7d0555` |
| Named successor | next normalized CUTOVER blocker after `EVIDENCE_PROVENANCE` 2→0, chosen from remasurement |
| What remains false | Five relationship STOPs; durable adoption; Case B; `CUTOVER_READY` |
| Runtime ownership | Isolated measurement only. No live World Graph mutation. |

### Forensic predecessor

PR #577 is evidence, not implementation ancestry.

It proved:

```text
2 source-grounded aliases were reconstructable
6 merge-shadow aliases were not package provenance
partial 8→N package must not be sealed
```

PR #577 is closed unmerged. The successor may use its algorithms and tests as
forensic reference, but it must **not** merge, reopen, extend, or wholesale
cherry-pick the old branch. The current input is the post-#583 live world
containing exactly two blockers, not the historical eight-blocker state.

## §3 Locked two aliases

```text
Captain
  blocker:
    node:node:captain-lysandra-ironveil:field:aliases
  target node:
    node:captain-lysandra-ironveil
  alias:
    Captain
  source assertion:
    assertion:2a63c5992970e366
  source contribution:
    contribution:a4231edb9a228963
  source payload SHA:
    2cf28604655f23e43846e389e5dce9920f98dfd670a0717ca3bf12e48703380c

Thrin Branchborn
  blocker:
    node:node:thrin-branchborn:field:aliases
  target node:
    node:thrin-branchborn
  alias:
    Thrin Branchborn
  source assertion:
    assertion:1275811e41cbb14c
  source contribution:
    contribution:a4231edb9a228963
  source payload SHA:
    2cf28604655f23e43846e389e5dce9920f98dfd670a0717ca3bf12e48703380c
```

Attempting to package any other alias, including the six retired merge-shadow
aliases, is a scope violation.

## §4 Files in scope — expected bounded lease

| Action | Path                                                                                                            |
| ------ | --------------------------------------------------------------------------------------------------------------- |
| Create | `apps/live_control_server/integrations/dungeonmind_kernel/alias_assertion_package_conformance_v1.py`            |
| Modify | `apps/live_control_server/integrations/dungeonmind_kernel/whole_world_conformance_v4.py`                        |
| Modify | `apps/live_control_server/integrations/dungeonmind_kernel/whole_world_conformance_v5.py`                        |
| Create | `apps/live_control_server/services/cutover_alias_assertion_package_after_shadow_alias_remove.py`                |
| Create | `scripts/build_cutover_alias_assertion_package_after_shadow_alias_remove.py`                                    |
| Create | `tests/test_alias_assertion_package_conformance_v1.py`                                                          |
| Create | `tests/test_cutover_alias_assertion_package_after_shadow_alias_remove.py`                                       |
| Create | `tests/fixtures/dungeonmind_kernel/eldyrwild_cutover_alias_assertion_package_after_shadow_alias_remove_v1.json` |

If current post-live architecture proves one of those historical #577 seams is
no longer required, remove it from the successor lease during pre-dispatch
design review rather than carrying dead machinery forward.

If a new generic Kernel capability is required:

```text
STOP
→ return to stewardship
```

**Bounded discovery exception:** None beyond the lease-trim rule above.

## §5 Explicitly out of scope

```text
src/graph_memory/**
canonical/live World Graph data
Captain / Thrin removal
the six retired merge-shadow aliases
five dual-sense relationship STOPs
DungeonMind Case B / durable adoption
CUTOVER_READY declaration
Docs/Sources/design-agent/**
Docs/Roadmaps/ROADMAP-campaign-supergraph.md
Docs/Design/ARCHITECTURE-campaign-supergraph.md
wholesale cherry-pick of the closed PR #577 branch
```

## §6 Implementation contract

```text
enumerate the exact two remaining EVIDENCE_PROVENANCE blockers
→ reconstruct both from revision-bound Buddy authority
→ preserve exact assertion IDs, contribution ID, and source SHA
→ validate both rows as current pinned DungeonMind alias assertion records
→ seal only when package_rows = 2, covered IDs = exact input set, residual_count = 0
→ prove EVIDENCE_PROVENANCE 2 → 0
→ prove canonical World Graph head/tree/aliases/identity/contributions unchanged
```

Do not invent metadata. Do not invent identity history. Do not traverse merge
history to manufacture alias provenance.

## §7 Evidence required to merge

The successor must prove:

```text
actual canonical input:
  rev:0c644e56b45bcaac709012206e3e41c2
  payload 0640d7ef8ce152ee4f656959e0e9a6c9c2fdf5ecc8bd721729b3019170d677f2

input blocker inventory:
  EVIDENCE_PROVENANCE = 2
  exact IDs = Captain + Thrin

package:
  package_rows = 2
  covered blocker IDs = exact input blocker set
  residual_count = 0
  passed = true

lineage:
  exact assertion IDs preserved
  exact contribution ID preserved
  exact contribution source SHA preserved
  active support lineage matches
  explicit evidence/source-artifact lineage matches

DungeonMind:
  both rows validate as current pinned DungeonMind alias assertion records
  no invented metadata
  no invented identity history

classification:
  EVIDENCE_PROVENANCE 2 → 0
  ATTRIBUTE_ASSERTION remains 0
  IDENTITY_HISTORY remains 20
  CONTRIBUTION_HISTORY remains 5291
  relationship inventories unchanged

mutation:
  canonical World Graph head unchanged
  graph tree unchanged
  contribution authority unchanged
  identity authority unchanged
  node aliases unchanged

other blockers:
  five relationship STOPs untouched
  durable-adoption boundary untouched
  CUTOVER disposition remains derived from remaining normalized blockers
```

Exact verification commands belong in the implementation handback. At minimum:

```bash
uv run pytest -q tests/test_alias_assertion_package_conformance_v1.py \
  tests/test_cutover_alias_assertion_package_after_shadow_alias_remove.py
uv run ruff check <leased Python paths>
git diff --check
git diff --name-only <dispatch-base>...HEAD
```

## §8 Required review handback

Record:

1. `Review Cycle <N>` and exact PR/branch/head SHA;
2. exact dispatch/base SHA actually used;
3. confirmation the canonical input is `rev:0c644e56…` / `0640d7ef…`;
4. actual changed paths versus §4, including any lease-trim;
5. package row count, covered IDs, residual_count, passed;
6. lineage proof for both aliases;
7. classification 2→0 with unchanged `ATTRIBUTE_ASSERTION` / `IDENTITY_HISTORY` / `CONTRIBUTION_HISTORY` / relationship inventories;
8. confirmation canonical World Graph head was not mutated;
9. confirmation the six retired aliases were not reopened;
10. confirmation Case B / `CUTOVER_READY` remain false.

## §9 Acceptance rubric

- [ ] Exactly one independently useful capability from §1 is delivered and proved by §7.
- [ ] Package has exactly two rows covering Captain and Thrin Branchborn.
- [ ] Residual count is 0; a one-row package is refused.
- [ ] Locked assertion/contribution/source lineage is preserved.
- [ ] `EVIDENCE_PROVENANCE` 2→0.
- [ ] Canonical World Graph is unchanged.
- [ ] Five relationship STOPs remain.
- [ ] No generic Kernel file is changed unless stewardship authorized a split.
- [ ] Actual changed paths stay inside the reviewed lease.

## Stop conditions

Stop and report instead of expanding when any of these appears:

- preflight drift against `rev:0c644e56b45bcaac709012206e3e41c2`;
- a third `EVIDENCE_PROVENANCE` blocker;
- either locked alias fails reconstruction;
- a required generic Kernel change;
- a worker proposes live World Graph mutation;
- a worker proposes reopening the six retired aliases;
- a worker proposes sealing a one-row package;
- a worker proposes Case B or `CUTOVER_READY`.

Report:

```text
Stop condition:
Invariant clause affected:
Why current mission cannot absorb it:
Required evidence now missing:
Affected paths/ownership layers:
Proposed successor or re-brief:
State-authority update needed:
```
