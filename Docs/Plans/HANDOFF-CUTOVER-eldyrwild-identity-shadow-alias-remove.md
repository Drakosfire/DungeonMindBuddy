---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: CUTOVER — exact-six Eldyrwild identity-shadow alias_remove
  - Flow: CUTOVER
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-CUTOVER-eldyrwild-identity-shadow-alias-remove.md
  - Branch / PR: cutover/eldyrwild-identity-shadow-alias-remove

  ## Verification pointer
  - Semantic predecessor: PR #580, merged at 3a52d309a606608c9338147b78e0a2f708084042
  - Dispatch gate: merged HANDOFF-DOCUMENTS-cutover-alias-remove-state-sync.md / current main
  - Forensic predecessor: PR #577, closed unmerged at b31bbc32b98c170c44f75de3fa1e8e252e7d0555
  - Verification: exact §7 results from implementation handback

  The checked-in handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
  Merging the application package is not the same as completing the live Eldyrwild exit.
---

# HANDOFF — retire Eldyrwild identity-shadow aliases

**Created:** 2026-08-13  
**Status:** DONE / HISTORICAL — do not redispatch  
**Canonical handoff path:** `Docs/Plans/HANDOFF-CUTOVER-eldyrwild-identity-shadow-alias-remove.md`  
**Conversation/workstream:** `CUTOVER — exact-six Eldyrwild identity-shadow alias_remove`  
**Flow / owner:** `CUTOVER`  
**Direction:** DESIGN → CODE → REVIEW  
**Base revision:** `71d11169cc56880ed09f457ddd9a6069429d0b96`  
**Suggested branch:** `cutover/eldyrwild-identity-shadow-alias-remove`  
**PR title:** `CUTOVER: retire Eldyrwild identity-shadow aliases`

### Completion record

```text
DONE / HISTORICAL — do not redispatch.

PR: #583
implementation head: 2cacc7cbdf77977e86daf29ed2b9058f94d54e70
merge: 299579bd3c3f78a9393ae3c97c57a1dfd6b155ed
review cycles: 3

live parent: rev:5a7c13ae45c49a65b402920499be72ed
live parent payload: 2632870ef70638969503de788cfdec97acd490875deff3e2630ac91dc96fe974
live result: rev:0c644e56b45bcaac709012206e3e41c2
live result payload: 0640d7ef8ce152ee4f656959e0e9a6c9c2fdf5ecc8bd721729b3019170d677f2
six alias_remove decision IDs:
  identity-decision:cad289933720e2c5
  identity-decision:045e447237353ccc
  identity-decision:05b5668d773648bf
  identity-decision:ef5c3950517c705e
  identity-decision:33d03a555ff0bc61
  identity-decision:668e4292aa9c047f
live/replay: proven (rebuild_equivalent_to_pinned_revision + rebuild_equivalent_to_head)
retry: already_applied / no-op; head unchanged; no seventh decision
keepers: Captain and Thrin Branchborn remain with locked assertion/contribution/source lineage
relationships: canonical 323 / 314 / 9 / 3; migration 323 / 318 / 5 / 3
EVIDENCE_PROVENANCE: 8 → 2
ATTRIBUTE_ASSERTION: not currently authorized (merge-only proof 16/28 on the cleaned head; locked #575 policy is stale)
IDENTITY_HISTORY: 14 → 20
CONTRIBUTION_HISTORY: 5285 → 5291
remaining EVIDENCE_PROVENANCE:
  node:node:captain-lysandra-ironveil:field:aliases
  node:node:thrin-branchborn:field:aliases
CUTOVER_NOT_READY remains true

identity-lifecycle re-proof on the cleaned head reconstructs 16/28 merge-only
rows. The 12 unresolved fields are the six survivors' last_identity_decision_id
+ identity_state, because those pointers now name alias_remove. PR #575 required
explicit proof or STOP on a new identity-decision kind. Do not claim
ATTRIBUTE_ASSERTION = 0 as current authority from the locked #575 28-ID policy.
```

Successor: [`HANDOFF-CUTOVER-identity-lifecycle-through-alias-remove.md`](HANDOFF-CUTOVER-identity-lifecycle-through-alias-remove.md). Captain/Thrin packaging remains `BLOCKED`.

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md).
>
> **Dispatch gate:** Before the first code change, fetch/re-anchor current `origin/main`, prove it is a descendant of this state-sync merge, prove this canonical handoff exists on that base, and prove the tracker names `cutover-eldyrwild-identity-shadow-alias-remove` as `READY`. Record the exact dispatch-base SHA in the implementation handback.
>
> Use public `graph_memory.kernel.remove_identity_alias`. Do not change generic Kernel semantics. Do not remove `Captain` or `Thrin Branchborn`. Do not package all eight aliases. Do not classify the six as `SOURCE_MIGRATION_HISTORY`. Do not edit graph JSON directly. Merging this application package is not slice `DONE`; canonical live publication + replay proof are required.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Merge-shadow alias** | A current survivor alias whose only owning path is `merge_identity()` unioning a merged-away node's label/aliases onto the survivor. It has no independent active current-node `node` or `alias` assertion. |
| **Independent semantic support** | An active `assertion_kind="alias"` whose subject is the current node and whose alias value matches, or an active `assertion_kind="node"` for that node whose `value.aliases` list contains the matching value. |
| **Keeper** | A source-grounded current alias that must remain: `Captain` on `node:captain-lysandra-ironveil` and `Thrin Branchborn` on `node:thrin-branchborn`. |
| **Exact-six application** | Six governed `alias_remove` identity decisions against the current Eldyrwild parent. Not a generic Kernel change. |
| **Live exit** | Post-merge canonical publication with expected-parent CAS, followed by full contribution + identity replay that reconstructs the cleaned head. |

The flow identifier `CUTOVER` is the owner for this slice.

## §1 Mission and merge-ready invariant

**Mission:** Apply exactly six governed `alias_remove` identity decisions to the current Eldyrwild world so that merge-shadow aliases cease to be current identity truth while all merge history, redirects, source authority, evidence, independently supported aliases, and replay semantics remain intact.

**Merge-ready invariant:** One coherent package that:

1. operates on the actual current Eldyrwild parent;
2. removes exactly six named current aliases through public `remove_identity_alias`;
3. preserves original merge decisions and merge side effects;
4. preserves redirects and merged-away identities;
5. preserves contributions, evidence, and source artifacts;
6. refuses any independently supported alias;
7. preserves `Captain` and `Thrin Branchborn`;
8. reconstructs the cleaned state through full contribution + identity replay;
9. exact-retries as already applied / no-op;
10. leaves relationship inventories unchanged;
11. does not claim `DONE` until the canonical live exit is proven after merge.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed path? | **Yes.** Isolated-clone apply, replay, retry, keeper preservation, and later live exit are the same six retirements against the same parent. |
| Most likely adversarial sequence | Apply five of six, or also retire a keeper, then treat a clone-green as live `DONE`. |
| Will §7 detect that failure? | **Yes.** Exact target/keeper scans, clone proofs, and the explicit live-exit gate refuse partial or keeper-touching packages. |
| Easiest owning boundary to under-test | Live parent CAS + full replay. Helper tests can pass while the canonical world is untouched or reconstructed incorrectly. |
| Fact that forces stop/split | Preflight drift against the actual current head, independent support for any of the six, a required generic Kernel change, or an unplanned durable representation. |

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | `AGENTS.md`; `Docs/Plans/PR-TRACKER-campaign-supergraph.md`; `Docs/Design/STATUS-world-graph-continuity-spine.md`; PR #580 Kernel primitive |
| Base revision | Re-anchor to the merged state-sync descendant of `71d11169cc56880ed09f457ddd9a6069429d0b96` before first code change |
| Predecessor contract | PR #580 — public replay-safe `remove_identity_alias`; head `5d4d43f01bc99729f6d6e577ec33553d9b5249b4`; merge `3a52d309a606608c9338147b78e0a2f708084042`; 2 review cycles |
| Branch / isolated checkout | `cutover/eldyrwild-identity-shadow-alias-remove` |
| Exact input consumed | Current Eldyrwild canonical parent `rev:5a7c13ae45c49a65b402920499be72ed` / payload `2632870ef70638969503de788cfdec97acd490875deff3e2630ac91dc96fe974` unless preflight proves a newer actual current head |
| Named successor | `cutover-alias-assertion-package-after-shadow-alias-remove` — Captain + Thrin package only after live/replay `EVIDENCE_PROVENANCE` 8→2 |
| What remains false | No Eldyrwild alias is retired until live exit; `EVIDENCE_PROVENANCE` is still 8 in current state; Captain/Thrin are not packaged; five relationship STOPs remain; DungeonMind adoption remains blocked |
| Explicit non-goals | Generic Kernel semantics; `alias_add`; unmerge composition; all-eight packaging; direct JSON cleanup; relationship cleanup; Case B |
| Parallel lanes / collision hotspots | `Docs/Sources/design-agent/**` is independent and non-authoritative. Do not edit Kernel files. |
| Runtime/state ownership | Isolated temp clone for merge-ready proof. Canonical live world is a post-merge explicit apply with `--allow-live-world` and expected-parent CAS. Do not symlink another worktree's `out/`. |
| State-authority sync set after merge | Tracker, continuity status, this handoff completion, Backlog pair — only after canonical live/replay exit |

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| Six merge-shadow aliases on survivors | Current identity truth via merge union | Retired through public `remove_identity_alias` | Yes | application service |
| Captain / Thrin Branchborn | Independently source-supported | Unchanged; attempting removal is a test failure | Yes | keeper proof |
| Original merge records | Historical `aliases_added_to_target` | Semantically/byte-equivalent historical fields | Yes | identity ledger |
| Redirects / merged-away nodes | Active historical identity | Remain active / merged-away | Yes | identity ledger |
| Contribution / evidence / source | Unchanged by #580 | Unchanged by this slice | Yes | clone + live proof |
| Isolated clone apply | Not implemented | Six retirements + replay reconstruct cleaned head | Yes | tests + script |
| Exact retry | N/A | Already applied / no-op | Yes | apply script |
| Canonical live apply | Forbidden until post-merge | Expected-parent CAS after re-anchor + complete preflight | Yes | live apply |
| `EVIDENCE_PROVENANCE` | 8 | Expected 8→2 only after proven live/replay exit | Yes | live remeasure |

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| Preflight finds drift vs actual current head | `STOP` → remeasure → return to stewardship; never repair until green | preflight |
| Any of the six has independent support | Refuse; do not retire | support refusal |
| Attempt to remove Captain or Thrin | Test failure and scope violation | keeper proof |
| Inverse/partial package (five of six) | Fail closed; do not publish | exact-six scan |
| Clone green treated as live DONE | Slice remains incomplete until live exit | live-exit gate |
| Generic Kernel file appears in the diff | Stop / split; Kernel is predecessor, not this lease | path review |

## §4 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live_control_server/services/eldyrwild_identity_shadow_alias_remove.py` | Bounded application package: preflight, six `remove_identity_alias` calls, keeper guards, expected-parent CAS |
| Create | `scripts/apply_eldyrwild_identity_shadow_alias_remove.py` | Operator status/apply CLI; live apply requires `--allow-live-world` |
| Create | `tests/test_eldyrwild_identity_shadow_alias_remove.py` | Isolated-clone apply, replay, retry, keeper, exact-six, and refusal proofs |

**Bounded discovery exception:** None.

If the current governed real-world publication seam proves that one additional persisted policy/artifact path is structurally required, that is a stop/re-design signal. Do not silently invent a new durable representation. No generic Kernel file belongs in this lease.

## §5 Explicitly out of scope / collision boundary

| Path | Why this slice must not touch or claim it |
|---|---|
| `src/graph_memory/**` | Generic Kernel semantics are already merged at PR #580. |
| `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` | Stable phase-level authority. |
| `Docs/Design/ARCHITECTURE-campaign-supergraph.md` | Architecture did not change. |
| `Docs/Plans/HANDOFF-KERNEL-alias-remove-identity-decision.md` | Historical completed Kernel authority. |
| `Docs/Plans/HANDOFF-CUTOVER-alias-assertion-package-after-575.md` | SUPERSEDED forensic handoff. |
| `Docs/Sources/design-agent/**` | Non-authoritative export mirror. |
| `Captain` / `Thrin Branchborn` removal | Keepers; later two-alias package only. |
| Five dual-sense relationship STOPs | Separate migration decisions. |
| DungeonMind adoption seam / Case B | Still blocked. |
| Direct graph JSON cleanup | Unauthorized; would not survive replay. |
| Reclassifying the six as `SOURCE_MIGRATION_HISTORY` | Explicit STOP. |

## §6 Implementation contract

### Exact six targets

| Survivor | Remove exact alias | Merged-away source | Introducing merge decision | Derived store key |
|---|---|---|---|---|
| `item_foot_of_statue` | `Enormous boulder` | `item_enormous_boulder` | `identity-decision:622b690ffe07c2c6` | `enormous boulder` |
| `loc:chilled_warehouse` | `the last warehouse` | `loc:last_warehouse` | `identity-decision:1ff8bf27a0b1921c` | `the last warehouse` |
| `loc:crooked-retort` | `Merchant’s Crossroads apothecary` | `organization:merchant-s-crossroads-apothecary` | `identity-decision:adab1e19800e24d7` | `merchant’s crossroads apothecary` |
| `loc:the-council` | `Council headquarters` | `item:session11:council-headquarters` | `identity-decision:3a8965f409e85911` | `council headquarters` |
| `loc:underground-entrance` | `A second underground entrance is discovered` | `mystery:session9:second_underground_entrance` | `identity-decision:c7f1cab745c8a1d2` | `a second underground entrance is discovered` |
| `obj:session9:scroll_abyssal` | `A scroll written in a strange language is found` | `mystery:session9:scroll_in_strange_language` | `identity-decision:ac8e5efc25de3804` | `a scroll written in a strange language is found` |

### Exact keepers

Attempting to remove either is a test failure and scope violation.

```text
node:captain-lysandra-ironveil
alias: Captain
source assertion: assertion:2a63c5992970e366
source contribution: contribution:a4231edb9a228963
source SHA: 2cf28604655f23e43846e389e5dce9920f98dfd670a0717ca3bf12e48703380c

node:thrin-branchborn
alias: Thrin Branchborn
source assertion: assertion:1275811e41cbb14c
source contribution: contribution:a4231edb9a228963
source SHA: 2cf28604655f23e43846e389e5dce9920f98dfd670a0717ca3bf12e48703380c
```

### Preflight — fail closed

Before package construction or any live write, prove against the **actual current world head**:

1. all six survivor IDs exist and are current canonical identities;
2. each exact alias is currently materialized on its survivor;
3. each introducing merge decision exists;
4. each merged-away source redirects as expected;
5. no active current `node` or `alias` assertion independently supports any of the six aliases;
6. Captain and Thrin Branchborn retain independent active support;
7. no prior active `alias_remove` already retired any of the six;
8. the operation's expected parent is the actual current head.

Any drift is:

```text
STOP
→ remeasure
→ return to stewardship
```

Never “repair until green.”

### Implementation model

```text
build bounded application package
→ prove on isolated temp clone
→ review every distinct head
→ merge
→ re-anchor current live world
→ rerun complete preflight
→ explicit live apply with expected-parent CAS
→ replay from durable contribution + identity authority
→ verify exact live exit
→ retry proof
→ state-authority sync
```

Public call shape:

```text
remove_identity_alias(
  store,
  world_id=...,
  subject_node_id=<survivor>,
  alias=<exact alias string>,
  actor=...,
  reason=...,
)
```

Use a distinct inspectable reason per retirement. Do not change `merge_identity` union semantics. Do not call `record_identity_decision(kind=alias_remove)`.

### Expected live exit

Expected, but never forced:

```text
EVIDENCE_PROVENANCE: 8 → 2

remaining:
  Captain
  Thrin Branchborn
```

The live proof must additionally establish:

- six and only six aliases retired;
- their alias-index entries disappear only when no surviving legitimate surface produces them;
- original merge records remain semantically/byte-equivalent in historical fields;
- redirects remain active;
- merged-away nodes remain historical/merged-away;
- contribution/evidence/source authority unchanged;
- full replay reconstructs the cleaned head;
- exact retry is no-op/already-applied;
- relationship inventories unchanged.

### Failure behavior

```text
unknown survivor → fail closed
alias not currently materialized → fail closed
canonical-label collision → fail closed
independent semantic support → fail closed
unresolved/divergent active support copies → fail closed
keeper listed as a removal target → fail closed
expected parent mismatch → fail closed
inverse ledger order → fail closed
```

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Command or manual scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Exact six targets present once | successor handoff + tests | contract | deterministic content + apply inventory | all six survivors/aliases/decision ids; no extras | missing/extra target |
| Keepers protected | tests | adversarial | attempt Captain/Thrin removal | refuse; aliases remain | either keeper retired |
| Isolated clone apply | service/tests | owning-boundary | temp clone of current parent | six retired; merges/redirects/sources intact | live mutation in the implementation PR |
| Full replay reconstructs cleaned head | rebuild/tests | replay | contribution + identity rebuild | cleaned aliases; historical merge fields unchanged | replay resurrects a retired alias |
| Exact retry no-op | apply script/tests | idempotency | second apply same parent/reasons | already_applied / no second decision | second retirement row |
| Relationship inventories unchanged | clone proof | regression | canonical `323 / 314 / 9 / 3` | unchanged | any inventory delta |
| No generic Kernel files | git diff | lease | `git diff --name-only <base>...HEAD` | only §4 paths | any `src/graph_memory/**` |
| Live exit not claimed early | tracker/status after merge | process | no current `EVIDENCE_PROVENANCE = 2` until live proof | current remains 8 until live apply | fake 8→2 in the implementation PR |

Exact verification commands for the **implementation** PR (not this documentation PR):

```bash
uv run pytest -q tests/test_eldyrwild_identity_shadow_alias_remove.py
uv run ruff check \
  apps/live_control_server/services/eldyrwild_identity_shadow_alias_remove.py \
  scripts/apply_eldyrwild_identity_shadow_alias_remove.py \
  tests/test_eldyrwild_identity_shadow_alias_remove.py
git diff --check
git diff --name-only <dispatch-base>...HEAD
```

Expected changed-path set:

```text
apps/live_control_server/services/eldyrwild_identity_shadow_alias_remove.py
scripts/apply_eldyrwild_identity_shadow_alias_remove.py
tests/test_eldyrwild_identity_shadow_alias_remove.py
```

### Minimal live / dogfood proof

Required **after merge**, not as a substitute for isolated-clone merge-ready proof:

```text
Existing surface: canonical Eldyrwild world
Smallest realistic scenario: explicit apply with expected-parent CAS after complete preflight
Expected observation: EVIDENCE_PROVENANCE: 8 → 2; remaining Captain and Thrin Branchborn
Evidence captured: apply receipt, replay reconstruction, retry already_applied, relationship inventories unchanged
```

### Baseline failure handling

Not applicable to this documentation PR. The implementation PR must not treat current `EVIDENCE_PROVENANCE = 8` as a failure to repair; that count is the truthful pre-live baseline.

## §8 Required review handback

Record:

1. `Review Cycle <N>` and exact PR/branch/head SHA;
2. exact dispatch/base SHA actually used;
3. confirmation PR #580 remains the Kernel predecessor;
4. actual changed paths versus §4;
5. preflight result against the actual current world head;
6. isolated-clone apply, replay, retry, keeper, and exact-six proofs;
7. confirmation `EVIDENCE_PROVENANCE` is still 8 until live exit;
8. confirmation Captain and Thrin were not removed;
9. confirmation no generic Kernel file changed;
10. named successor (Captain/Thrin package) still unimplemented;
11. explicit statement that live exit remains false until post-merge publication.

## §9 Acceptance rubric

- [ ] Exactly one independently useful capability from §1 is delivered and proved by §7.
- [ ] Exactly six named merge-shadow aliases are retired through public `remove_identity_alias`.
- [ ] Original merge decisions, redirects, merged-away identities, contributions, evidence, and source artifacts remain intact.
- [ ] `Captain` and `Thrin Branchborn` remain independently supported.
- [ ] Full contribution + identity replay reconstructs the cleaned head.
- [ ] Exact retry is already applied / no-op.
- [ ] Relationship inventories are unchanged.
- [ ] Generic Kernel semantics were not modified.
- [ ] Actual changed paths stay inside §4.
- [ ] Slice is not marked `DONE` until canonical live publication + replay prove `EVIDENCE_PROVENANCE: 8 → 2`.

## Stop conditions

Stop and report instead of expanding when any of these appears:

- preflight drift against the actual current head;
- independent support for any of the six aliases;
- a required generic Kernel change;
- an unplanned durable/public representation;
- a worker proposes direct graph JSON cleanup;
- a worker proposes removing Captain or Thrin;
- a worker proposes packaging all eight aliases;
- a worker proposes reclassifying the six as `SOURCE_MIGRATION_HISTORY`;
- a worker proposes relationship cleanup or Case B adoption work;
- required path outside §4.

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
