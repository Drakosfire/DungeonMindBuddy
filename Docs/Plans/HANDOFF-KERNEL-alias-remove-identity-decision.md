---
pr_body_template: |
  ## Handoff pointer
  - Conversation: KERNEL — replay-safe alias_remove identity decision
  - Flow / agent: KERNEL
  - Direction: DESIGN → CODE
  - Handoff: Docs/Plans/HANDOFF-KERNEL-alias-remove-identity-decision.md
  - PR / branch: kernel/alias-remove-identity-decision

  ## Verification pointer
  - Design predecessor: this handoff merged to main
  - Semantic predecessor: PR #576 / current main descendant of
    fda746b99a8a9830280bf1beac126a8221ddedfc
  - Forensic predecessor: PR #577 STOP (unmerged) — six identity-shadow aliases
  - Verification: exact §7 commands/results from the implementation handback

  The checked-in handoff, cumulative code diff, nano commits, and independently
  rerun verification are the review contract. The PR description is transport
  metadata only. Document sync is a separate operation.
---

# HANDOFF — make `alias_remove` identity decisions replay-safe

**Created:** 2026-08-13.
**Status:** DESIGN READY — **DO NOT DISPATCH implementation until this handoff is merged to `main`.**
**Canonical handoff path:** `Docs/Plans/HANDOFF-KERNEL-alias-remove-identity-decision.md`
**Conversation name:** `KERNEL — replay-safe alias_remove identity decision`
**Flow / agent:** `KERNEL`
**Handoff direction:** `DESIGN → CODE`
**Design agent:** DungeonBuddy design steward — 2026-08-13
**Code agent:** fresh KERNEL code agent using the same conversation name
**PR title:** `KERNEL: make alias_remove identity decisions replay-safe`
**Suggested branch:** `kernel/alias-remove-identity-decision`

> **Dispatch gate:** Before the first code change, record the exact `origin/main` SHA, prove it is a descendant of `fda746b99a8a9830280bf1beac126a8221ddedfc` (PR #576), and prove this canonical handoff exists on that base. If the tracker no longer names `kernel-alias-remove-identity-decision` as next, stop and return to design.
>
> This checked-in handoff is the complete implementation authority for the slice. Do not retire Eldyrwild aliases here. Do not change `merge_identity` union semantics. Do not invent contribution-assertion correction for aliases. Do not implement `alias_add`, rename, or general identity editing.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Identity/materialization decision** | A durable `IdentityDecisionRecord` that changes current identity surface (canonical node, aliases, redirects) without rewriting contribution/evidence/source bytes. Distinct from `GraphContributionAssertionCorrection`, which is contribution-assertion correction and currently edge-only. |
| **`alias_remove`** | Already-reserved `IdentityDecisionKind`. Today it can be recorded but is not applied. This slice fills that reserved capability. |
| **Current survivor aliases** | `UnionSupergraphNode.aliases` on the canonical living node. |
| **Derived alias index** | `store.aliases` lookup map. A key exists because a canonical label or an active alias currently materializes it. |
| **Merge-shadow alias** | A current survivor alias whose only owning path is `merge_identity()` unioning a merged-away node's label/aliases onto the survivor. It has no independent active current-node `node` or `alias` assertion. |
| **Independent semantic support** | An active `assertion_kind="alias"` whose subject is the current node and whose alias value matches, or an active `assertion_kind="node"` for that node whose `value.aliases` list contains the matching value. |
| **Historical merge authority** | The original merge `IdentityDecisionRecord`, including `merge_side_effects.aliases_added_to_target` and alias-map rewrites, plus redirects and merged-away node state. Unchanged by later `alias_remove`. |

The flow identifier `KERNEL` is the owner for this slice.

## Why this is the next capability

PR #577 reached the correct STOP: of eight `EVIDENCE_PROVENANCE` alias blockers, two are source-grounded current-node aliases and six are active only because identity-merge materialization carried historical labels forward. Direct cleanup of those six would be fake. Replay is:

```text
historical merge decision
→ merge_identity()
→ source label/aliases unioned onto survivor aliases
→ store.aliases rewritten
→ rebuild repeats the same side effect
```

`IdentityDecisionKind` already reserves `alias_remove`. `_apply_identity_decision()` currently falls through those records to append-only `record_identity_decision()`. There is no replay-applied mutation primitive. Contribution assertion correction is edge-only and is the wrong owner.

This is therefore a missing governed identity-materialization capability, not a six-object data-cleanup problem.

PR #577 remains open as forensic evidence. Do not merge it. Do not reuse its worktree or add implementation to it. After this design authority lands, close #577 unmerged.

## Agent flow and nano-commit contract

Use `KERNEL`. Keep the work in nano commits. A recommended story shape is:

1. `remove_identity_alias` mutating primitive + fail-closed validation;
2. replay wiring in `_apply_identity_decision` with deterministic ledger order;
3. exact-retry idempotency, inverse-order rejection, independent-support refusal, unmerge composition guard;
4. rebuild/replay equivalence proofs;
5. only if needed, one narrowly justified projection compatibility fix from the bounded-discovery exception.

Do not encode a PR number into the title, branch name, public identifiers, or design authority.

## Review and doc-sync contract

Review the cumulative diff and nano-commit sequence against this handoff. The implementation PR must not update the roadmap/tracker/handoff status as part of a code fix. After merge, document synchronization is a separate operation.

## §1 Mission and merge-ready invariant

**Mission:** Kernel callers can publish one governed `alias_remove` identity decision so that a currently materialized alias can be retired from current identity surface without rewriting merge history, contributions, evidence, or independent alias/node assertions.

**Merge-ready invariant:** Against one in-memory or published store, one exact `(subject_node_id, alias)` that is currently materialized and lacks independent semantic support is atomically removed from `node.aliases` and from the corresponding derived `store.aliases` mapping when that mapping exists solely because of that alias; a durable `decision_kind="alias_remove"` record is appended in ledger order; earlier merge decisions, redirects, merge side effects, contributions, evidence, and source artifacts remain byte/semantically unchanged; exact retry does not duplicate the decision or re-mutate; pinned contribution+identity replay reconstructs the same cleaned current state; `alias_remove` before the merge that would introduce the alias fails closed; independent semantic support fails closed; changing generic merge union behavior is a stop.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes**, if this slice is generic `alias_remove` only. Eldyrwild application, `alias_add`, and merge-union policy changes are separately useful and are split. |
| Most likely adversarial sequence | Replay re-runs `merge_identity()` and re-unions the alias, while `alias_remove` is recorded but not applied; or inverse ledger order silently tombstones a future merge. |
| Will §7 actually detect that failure? | **Yes.** Owning proofs rebuild from contributions + identity ledger and fingerprint `node.aliases` / `store.aliases`; inverse-order and independent-support cases must fail closed. |
| Easiest owning boundary to under-test | Replay: a live `remove_identity_alias` can look right while `_apply_identity_decision` still appends without mutating. |
| Fact that forces stop/split | If the only correct implementation changes generic `merge_identity` union semantics, requires a new decision kind, or cannot refuse independent semantic support without scanning DungeonMind. |

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | `Docs/Design/ARCHITECTURE-campaign-supergraph.md`; `Docs/Design/CONTRACT-graph-kernel-boundary.md`; `Docs/Plans/PR-TRACKER-campaign-supergraph.md` after this handoff merges |
| Base revision | Exact `origin/main` SHA after this handoff is merged; must be a descendant of `fda746b99a8a9830280bf1beac126a8221ddedfc` and contain this file |
| Predecessor contract | `IdentityDecisionKind` already includes `alias_remove`; `IdentityDecisionRecord.alias` already exists; `merge_identity` / `unmerge_identity` / `record_identity_decision`; `_apply_identity_decision` in `contribution_rebuild.py`; durable identity-decision ledger order via `identity_decision_index.all_decision_ids` |
| Exact input consumed | One `remove_identity_alias(...)` call naming exact `world_id`, `subject_node_id`, alias string, actor, and reason |
| Named successors | (1) `cutover-eldyrwild-identity-shadow-alias-remove` — apply exactly six Eldyrwild `alias_remove` decisions; (2) resume alias-assertion package for the remaining two source-grounded aliases (`Captain`, `Thrin Branchborn`) |
| What remains false | No Eldyrwild alias is retired; `EVIDENCE_PROVENANCE` remains 8; `alias_add` / rename / general identity editing remain unimplemented; merge-union policy is unchanged; alias-package fixture is not sealed |
| Explicit non-goals | Direct canonical graph JSON edits; deleting or rewriting merge records; contribution assertion correction for aliases; DungeonMind vocabulary; CUTOVER fixture reseal; tracker/status edits in the implementation PR |
| Branch / isolated checkout | `kernel/alias-remove-identity-decision` in a fresh worktree; do not reuse `/tmp/dmb-cutover-repin-v5` (PR #577) or `/tmp/dmb-cutover-shadow-aliases` |
| Parallel lanes / collision hotspots | PR #577 owns CUTOVER alias-package conformance paths and must not be extended. This slice owns Kernel identity decision/replay files listed in §4. Open product PRs (#578, #516, #510, #497) do not lease those Kernel paths. |
| Runtime/state ownership | Synthetic Kernel tests only. Do not mutate live Eldyrwild `out/` canonical graph. Do not share another worktree's `out/`. |
| State-authority sync set after merge | `Docs/Plans/PR-TRACKER-campaign-supergraph.md`; `Docs/Design/STATUS-world-graph-continuity-spine.md`; this handoff status; then dispatch the Eldyrwild six-alias successor |

Read authoritative inputs in order before changing code:

1. this handoff
2. `src/graph_memory/kernel/identity_models.py`
3. `src/graph_memory/kernel/identity_decisions.py`
4. `src/graph_memory/kernel/contribution_rebuild.py` (`_apply_identity_decision`, identity ledger apply loop)
5. `src/graph_memory/world_supergraph/identity_decision_store.py`
6. `src/graph_memory/kernel/contribution_merge.py` (`_apply_alias_assertion`, `_apply_node_assertion`)
7. `src/graph_memory/kernel/world_projection.py` (`_active_node_aliases`) — read for consumer behavior; edit only if the bounded-discovery gate is triggered
8. `tests/test_graph_kernel_identity_decisions.py`
9. `tests/test_graph_kernel_contribution_rebuild.py`

### Why this is not contribution correction

`GraphContributionAssertionCorrection` is typed for `assertion_kind="edge"`. Alias retirement here is not contradicting a source assertion. The six motivating aliases have no independent current-node assertion. Using contribution correction would invent a source-level lie.

The original merge remains historically true: "the merge added this alias." The later decision is separately true: "current identity materialization subsequently retired it."

### Why merge-union semantics must not change

`merge_identity()` currently unions source label + source aliases onto the survivor and rewrites `store.aliases`. That is the recorded merge side effect used by `unmerge_identity`. Changing that generic rule would retcon every historical merge, not just six Eldyrwild objects.

If implementation discovers that `alias_remove` cannot be made correct without changing merge union behavior, **STOP** and report the affected population and behavioral consequences. Do not "fix" merge to make these six examples cleaner.

### Forensic lineage (context only — not this PR's mutation set)

Measured on canonical Eldyrwild `rev:5a7c13ae45c49a65b402920499be72ed` after PR #576. Each of the six is a `merge_identity` side effect (`aliases_added_to_target`) with no independent active current-node `node`/`alias` assertion.

| Survivor node | Active alias to retire later | Keepers on the same CUTOVER inventory |
|---|---|---|
| `item_foot_of_statue` | `Enormous boulder` | |
| `loc:chilled_warehouse` | `the last warehouse` | |
| `loc:crooked-retort` | `Merchant’s Crossroads apothecary` | |
| `loc:the-council` | `Council headquarters` | |
| `loc:underground-entrance` | `A second underground entrance is discovered` | |
| `obj:session9:scroll_abyssal` | `A scroll written in a strange language is found` | |
| `node:captain-lysandra-ironveil` | — | keep `Captain` |
| `node:thrin-branchborn` | — | keep `Thrin Branchborn` |

Do not apply these six decisions in this PR. The successor owns that mutation after the primitive exists.

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| Call `remove_identity_alias` on a merge-shadow alias | No mutating API; `alias_remove` records are append-only | Remove exact alias from `node.aliases`; drop derived `store.aliases` key if solely owned by that alias; append `alias_remove` decision | Yes | `identity_decisions.py` |
| Replay via `_apply_identity_decision` | Falls through to `record_identity_decision` (no mutation) | Apply `remove_identity_alias` using the durable decision's subject/alias/actor/reason so `decision_id` matches | Yes | `contribution_rebuild.py` |
| Ledger order after merge | Merge re-unions alias on rebuild | `alias_remove` later in `all_decision_ids` retires it after merge; no special second cleanup pass | Yes | identity ledger apply loop |
| Inverse order: `alias_remove` before introducing merge | Undefined / would require tombstone | **Fail closed**; alias is not currently materialized | Yes | `remove_identity_alias` validation |
| Independent active `alias` or `node` assertion support | No check | **Fail closed**; do not retire source-grounded aliases | Yes | `remove_identity_alias` validation |
| Canonical label casefold-equals the alias | Label may also exist in `store.aliases` | **Fail closed**; this primitive does not rename or unlabel | Yes | validation |
| Exact retry after success | N/A | Same `decision_id`, no second append, aliases remain absent | Yes | `remove_identity_alias` |
| Merge decision / side effects / redirects | Would be tempting to rewrite | Byte/semantically unchanged | Yes | identity history |
| `unmerge_identity` of a merge whose added alias was later removed | Would restore `aliases_added_to_target`, undoing `alias_remove` | **Fail closed** in this slice; composition is a successor | Yes | `unmerge_identity` guard |
| `record_identity_decision` with `alias_remove` | Append-only footgun | Refuse; callers must use `remove_identity_alias` | Yes | `record_identity_decision` |
| `alias_add` | Reserved, unimplemented | Remain unimplemented; refuse if someone passes it to the new mutating path | Yes | non-goal |
| Projection `_active_node_aliases` merge-record union | Comment treats merge-inherited aliases as permanent | Current projection must not resurrect a subsequently retired alias; see bounded discovery | Yes | projection, only if gate trips |

### Ordered failure sequences

| Sequence | Required safe outcome | Owning proof |
|---|---|---|
| Merge source S into survivor T, adding alias A → `alias_remove` A on T | T.aliases lacks A; derived index key absent if solely from A; merge decision/side effects unchanged | §7 happy-path + history-intact proof |
| Same `remove_identity_alias` inputs after success | No second decision row; store fingerprint unchanged | §7 idempotency |
| `alias_remove` A, then merge that first introduces A | Remove fails closed because A is not currently on T | §7 inverse-order |
| Publish/replay contributions + merge + later `alias_remove` | Rebuilt `node.aliases` / `store.aliases` match the cleaned live store | §7 rebuild proof |
| Node assertion or alias assertion independently carries A → `alias_remove` A | Fail closed; A remains | §7 independent-support |
| `alias_remove` A after merge → `unmerge` that merge | Unmerge refuses; merge remains active; A stays retired | §7 unmerge composition |
| Tamper merge `aliases_added_to_target` to drop A instead of adding `alias_remove` | Out of scope / forbidden; tests must prove merge bytes unchanged | §7 history-intact |
| Attempt to change `merge_identity` so it no longer unions labels | Stop condition, not an implementation choice | steward report |

## §4 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| Modify | `src/graph_memory/kernel/identity_decisions.py` | Add `remove_identity_alias`; refuse append-only `alias_remove`/`alias_add` on `record_identity_decision`; guard `unmerge_identity` composition |
| Modify | `src/graph_memory/kernel/contribution_rebuild.py` | Replay `alias_remove` through `remove_identity_alias` in durable ledger order |
| Modify | `src/graph_memory/kernel/__init__.py` | Export `remove_identity_alias` from the legal Kernel boundary |
| Modify | `src/graph_memory/kernel/contracts.py` | Add `remove_identity_alias` to the implemented PR004 identity tuple |
| Modify | `Docs/Design/CONTRACT-graph-kernel-boundary.md` | Record the new exported identity operation; do not rewrite unrelated contract text |
| Modify | `tests/test_graph_kernel_identity_decisions.py` | Own mutating primitive, fail-closed, idempotency, independent-support, unmerge-guard proofs |
| Modify | `tests/test_graph_kernel_contribution_rebuild.py` | Own replay/rebuild equivalence and inverse-order-on-replay proofs |
| Modify | `tests/test_graph_kernel_boundaries.py` | Only if the Kernel export/boundary allowlist requires the new symbol |

**Bounded discovery exception:**

```text
Directory: src/graph_memory/kernel/world_projection.py
Maximum additional paths: 1
Allowed path kinds: existing `_active_node_aliases` / identity-survivor alias union only
Decision rule: only if a failing owning-boundary test proves that after a successful
alias_remove, project_world_graph still emits the removed alias solely because
merge-record union treats inherited aliases as permanent. The allowed fix is:
skip re-union of a merge-inherited alias that a later active alias_remove retired.
Any broader "aliases are no longer additive" policy, alias_add, or assertion
retraction redesign is a stop condition.
```

A required path outside this lease/exception is a stop report.

## §5 Explicitly out of scope / collision boundary

| Path, layer, or capability | Why this slice must not touch or claim it |
|---|---|
| Eldyrwild canonical graph / live `out/` / six alias_remove publications | Named successor `cutover-eldyrwild-identity-shadow-alias-remove` |
| `Captain` / `Thrin Branchborn` aliases | Source-grounded; remain current; later alias-package slice |
| `merge_identity` union rule | Generic identity-materialization policy change; stop rather than retcon |
| `alias_add`, rename, split/unmerge behavior except the composition guard | Not required to prove `alias_remove` |
| `GraphContributionAssertionCorrection` / edge correction | Wrong owner; edge-only |
| CUTOVER analyzers, alias-package service, successor fixtures | Diagnostic/package work; do not seal a partial package here |
| PR #577 branch / worktree / conformance edits | Forensic STOP; close unmerged after this authority lands |
| DungeonMind dependency/vocabulary | Buddy identity materialization, not adoption |
| Tracker / STATUS / Backlog in the implementation PR | Separate post-merge state-authority sync |
| UI / Graph Review identity-editing workflow | Product surface after the Kernel contract exists |

## §6 Implementation contract

```text
Input:
  UnionSupergraphStore
  world_id: str
  subject_node_id: exact current canonical node id
  alias: exact alias string to retire
  actor: non-blank
  reason: non-blank
  root: Path | None
    required when subject has assertion_support rows that must be resolved
    to prove or refute independent semantic support

Output:
  (updated store, IdentityDecisionRecord)
  decision_kind == "alias_remove"
  subject_node_id == requested node
  alias == requested alias
  merge_side_effects is None
  decision_id == compute_identity_decision_id(...)

Invariant:
  same as §1

Failure behavior:
  unknown node → fail closed
  merged_away / non-canonical subject → fail closed
  alias blank / whitespace-only → fail closed
  alias casefold-equals subject canonical label → fail closed
  alias not currently in subject.aliases (casefold match) → fail closed
    including inverse order before the introducing merge
  independent semantic support → fail closed
  unresolved assertion_support that might be independent support → fail closed
  unmerge of a merge whose aliases_added_to_target includes an alias later
    retired by active alias_remove on that survivor → fail closed
  record_identity_decision(kind=alias_remove|alias_add) → fail closed

Replay / idempotency:
  same input after success → return existing decision, no second append, no alias resurrection
  changed alias/subject/reason → distinct decision_id
  pinned rebuild → apply durable identity decisions in index/ledger order after contributions
  merge then alias_remove in that ledger order → cleaned current aliases
  alias_remove then introducing merge in that ledger order → rebuild fails closed

Trust boundary:
  Verifies: exact node id, exact alias string, current materialization,
            independent support absence, ledger order, decision identity
  Records/trusts without proving: the human judgment that the alias should
            not remain a current semantic alias
```

Public operation name must be `remove_identity_alias` and must be exported from `graph_memory.kernel`, parallel to `merge_identity`.

### Decision record shape

Reuse `IdentityDecisionRecord`. Do not add a new model.

```text
decision_kind = "alias_remove"
subject_node_id = survivor node id
target_node_id = None
alias = exact alias string being retired
affected_node_ids = [subject_node_id]
merge_side_effects = None
status = "active"
reversible = True   # reversal/unremove is a successor; do not implement alias_add here
```

Do not rewrite the earlier merge record. History continues to say the merge added the alias.

### Current-state mutation

On success, atomically:

1. Remove matching values from `subject.aliases` using the existing casefold helper pattern (`_remove_items`).
2. If `store.aliases[alias.casefold()] == subject_node_id` **and** the key is not still produced by the remaining canonical label or remaining aliases, delete that mapping.
3. If another remaining label/alias still casefolds to that key, keep the mapping.
4. Append the decision. Do not create/retract redirects. Do not touch merged-away nodes.

### Independent semantic support

Independent support exists when any of:

1. An active `assertion_kind="alias"` support for `subject_node_id` whose resolved alias value casefold-equals the target alias;
2. An active `assertion_kind="node"` support for `subject_node_id` whose resolved `value.aliases` contains a casefold-equal value.

Rules:

- Empty `assertion_support` for that object → treat as no independent support (identity-only materialization, including merge-shadow).
- Active node assertion that does **not** list the alias is not independent support for that alias.
- If support rows exist and assertion payloads cannot be resolved, fail closed.
- Do not import `world_projection` into `identity_decisions`. Resolve through existing Kernel contribution/support loaders.
- Do not traverse identity redirects to manufacture support for a merged-away node.

### Ordering

Replay must use existing durable identity-decision order (`identity_decision_index.all_decision_ids` / pinned store snapshot order). "After merge" emerges from that order. Do not add a post-merge cleanup pass.

Reject inverse order rather than creating tombstone/future-suppression semantics.

A later merge that re-introduces the same alias after an earlier `alias_remove` is a new merge. Historical `alias_remove` does not suppress it. A new retirement requires a distinct reason and therefore a distinct `decision_id`. Do not collapse those into one tombstone.

### Unmerge composition

`unmerge_identity` must refuse when:

```text
original merge is still the unmerge target
AND an active alias_remove exists
AND alias_remove.subject_node_id == merge.target_node_id
AND alias_remove.alias casefold-matches a value in
    merge.merge_side_effects.aliases_added_to_target
```

Do not implement unmerge-then-reapply-later-decisions in this slice.

### A. State / fallback matrix

| Observable path | Loading/init | Exact success | Ordinary miss | Integrity failure | Stale/superseded | Retry/replay |
|---|---|---|---|---|---|---|
| `remove_identity_alias` | require node in store | alias absent; decision appended | alias not present → fail | unresolved support → fail | merged_away subject → fail | exact retry no-op |
| rebuild apply loop | load ledger order | apply merge then remove | missing decision payload → existing rebuild failure | digest/integrity existing rules | skip decisions already on baseline snapshot | deterministic cleaned state |
| unmerge after remove | load original merge | **refuse** | unknown merge id → existing error | missing side_effects → existing error | already superseded merge → existing error | no partial unmerge |

No fallback from label search, redirect traversal, or DungeonMind alias vocabulary.

### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Exact node id | Must be current canonical subject | missing/merged_away → fail | No |
| Exact alias string | Casefold match against `node.aliases` | not present → fail (no tombstone) | No |
| Derived `store.aliases` key | Delete only if solely owned by the retired alias | remaining label/alias still maps → keep | No |
| Canonical label | Not removable by this primitive | casefold-equal → fail | No |
| Independent assertion | Exact resolved alias/node assertion values | unresolved → fail | No |
| Merge decision id | Untouched | must not be rewritten to encode the retirement | No |

### C. Persistence / replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay | Compatibility | Rollback |
|---|---|---|---|---|---|
| `alias_remove` decision | existing `IdentityDecisionRecord` JSON in store + identity-decision ledger | alias/subject/kind survive round trip; `decision_id` stable | exact retry no second row | old stores without `alias_remove` replay unchanged | do not implement `alias_add` reversal here |
| Rebuild | contribution ledger + identity ledger order | cleaned `node.aliases` / `store.aliases` match published cleaned store | deterministic | historical merge/unmerge tests still pass | unmerge composition deferred via fail-closed |
| Merge history | original merge JSON | `merge_side_effects` still lists the added alias | unchanged | required | not a rollback mechanism for `alias_remove` |

### D. Predecessor → consumer mapping

**Grounding source:** current Kernel identity models at the implementation base.

| Predecessor field/outcome | Real shape | Consumer behavior | Transformation | Proof |
|---|---|---|---|---|
| `IdentityDecisionKind` | includes `alias_remove` | new mutating path | no schema change | contract test |
| `IdentityDecisionRecord.alias` | `str \| None` | required non-blank for `alias_remove` | store exact string | unit test |
| `merge_side_effects.aliases_added_to_target` | list on merge records | historical fact only | never edited by remove | history-intact test |
| `_apply_identity_decision` default branch | append-only for unknown kinds | `alias_remove` becomes mutating | call `remove_identity_alias` | rebuild test |
| `_active_node_aliases` merge-record union | optional projection resurrection | must not undo `alias_remove` | bounded-discovery only | projection test if gate trips |

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Command or manual scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Merge-shadow alias retired from current aliases | Kernel identity | contract | synthetic merge adds A; `remove_identity_alias` A | A absent from `node.aliases`; merge record still lists A in side effects | merge JSON mutated or A remains |
| Derived index key removed only when solely owned | Kernel identity | contract | A is the only producer of `A.casefold()` | `store.aliases` lacks that key | deleting a key still produced by label/remaining alias |
| Shared casefold key retained | Kernel identity | adversarial | remaining alias/label still casefolds to same key | mapping remains, points at subject | accidental hijack/drop |
| Independent alias assertion refuses | Kernel identity | adversarial | active `assertion_kind=alias` for A | fail closed; A remains | retiring Captain-like source-grounded alias |
| Independent bundled node-assertion alias refuses | Kernel identity | adversarial | active node assertion `aliases` contains A | fail closed; A remains | treating survivor node existence as support for merge-shadow A |
| Inverse order fails closed | Kernel identity + rebuild | adversarial | `alias_remove` in ledger before introducing merge | live call and rebuild fail; no tombstone | remove succeeds and later merge is suppressed |
| Exact retry idempotent | Kernel identity | adversarial | call exact remove twice | one decision_id row; second call no-ops | duplicate decision or second mutation |
| Replay reconstructs cleaned state | contribution rebuild | contract | contributions + merge + later `alias_remove`; `rebuild_from_contributions` | rebuilt aliases/index match cleaned store | rebuild re-unions A |
| Merge/unmerge/redirect/contribution/evidence unchanged | Kernel identity | contract | fingerprint merge decision, redirects, contribution/evidence maps before/after remove | exact match except new `alias_remove` row and current alias surface | any history rewrite |
| Unmerge composition fails closed | Kernel identity | adversarial | merge → remove A → unmerge that merge | unmerge raises; A stays retired; merge remains active | unmerge restores A |
| `record_identity_decision(alias_remove)` refuses | Kernel identity | contract | append-only call | raises; no silent non-mutating record | footgun append-only `alias_remove` |
| Historical identity tests still pass | Kernel identity/rebuild | regression | existing identity + rebuild suites | no behavior change for merge/split/unmerge happy paths except the new unmerge guard | generic merge-union change |
| No Eldyrwild movement | live graph / CUTOVER | regression | do not publish Eldyrwild; focused CUTOVER tests still see EP=8 if run | canonical revision unchanged | this PR retires the six aliases or reseals alias-package |
| Kernel export exists | Kernel boundary | contract | `graph_memory.kernel.remove_identity_alias` importable | listed in `__all__` / contracts / kernel-boundary doc | private-only helper |

Exact verification commands:

```bash
uv sync --locked

uv run ruff check \
  src/graph_memory/kernel/identity_decisions.py \
  src/graph_memory/kernel/contribution_rebuild.py \
  src/graph_memory/kernel/__init__.py \
  src/graph_memory/kernel/contracts.py \
  tests/test_graph_kernel_identity_decisions.py \
  tests/test_graph_kernel_contribution_rebuild.py \
  tests/test_graph_kernel_boundaries.py

uv run pytest tests/test_graph_kernel_identity_decisions.py -q
uv run pytest tests/test_graph_kernel_contribution_rebuild.py -q
uv run pytest tests/test_graph_kernel_boundaries.py -q

git diff --check
git diff --stat <implementation-base>...HEAD -- \
  src/graph_memory/kernel/identity_decisions.py \
  src/graph_memory/kernel/contribution_rebuild.py \
  src/graph_memory/kernel/__init__.py \
  src/graph_memory/kernel/contracts.py \
  Docs/Design/CONTRACT-graph-kernel-boundary.md \
  tests/test_graph_kernel_identity_decisions.py \
  tests/test_graph_kernel_contribution_rebuild.py \
  tests/test_graph_kernel_boundaries.py
git diff --name-only <implementation-base>...HEAD
```

If the bounded projection exception is used, add `src/graph_memory/kernel/world_projection.py` and the exact failing proof that justified it to the handback.

### Minimal live / dogfood proof

`Not applicable — this is intentionally a synthetic Kernel capability slice. The first real-world proof is the named Eldyrwild six-alias successor. Mutating Eldyrwild here is a merge blocker, not extra confidence.`

### Baseline failure handling

For any required command already failing on the exact implementation base: rerun on base and head, report both, and do not call the gate green.

## §8 Required review handback

Record:

1. `Review Cycle <N>` and exact PR/branch/head SHA;
2. §1 mission/invariant disposition;
3. §7 required vs produced evidence + provenance;
4. nano-commit/fix story;
5. base/head and actual changed paths vs §4;
6. whether the projection bounded-discovery exception was used, and the failing proof if so;
7. paths outside §4 (`none` or stop report);
8. stop conditions and resolution;
9. named successors still false (six Eldyrwild removes; two-alias package);
10. proof that generic `merge_identity` union behavior is unchanged.

## §9 Acceptance rubric

- [ ] Exactly one independently useful capability from §1 is delivered and proved by §7.
- [ ] `alias_remove` is an identity/materialization decision, not contribution correction.
- [ ] Replay uses durable decision order; no special post-merge cleanup pass.
- [ ] Independent semantic support refuses removal.
- [ ] `node.aliases` and derived `store.aliases` update atomically.
- [ ] Earlier merge decisions/side effects/redirects are unchanged.
- [ ] Exact retry is idempotent.
- [ ] Inverse order fails closed; no tombstone semantics.
- [ ] Unmerge composition with a later `alias_remove` fails closed.
- [ ] `alias_add` / rename / Eldyrwild mutation / alias-package sealing remain unimplemented.
- [ ] Actual changed paths stay inside §4 / bounded discovery.
- [ ] Named successors remain unimplemented/unclaimed.

## Stop conditions

Stop and report instead of expanding when any of these appears:

- the only correct fix changes generic `merge_identity` label/alias union;
- a new mutation primitive/kind beyond filling reserved `alias_remove` is required;
- independent-support refusal cannot be implemented without DungeonMind or identity-redirect provenance invention;
- inverse-order semantics cannot be fail-closed without tombstones;
- Eldyrwild live mutation or CUTOVER fixture work is required to prove the primitive;
- projection compatibility requires a general aliases-are-not-additive redesign;
- required path outside §4 or another lane's write lease;
- PR #577 is reused as the implementation branch.

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

## Named CUTOVER sequence after this primitive

This slice does not move the Eldyrwild blocker ledger. After merge + state-authority sync, the intended sequence is:

```text
PR 577 diagnostic STOP (close unmerged once this authority is on main)
        ↓
this KERNEL primitive (generic replay-safe alias_remove)
        ↓
BUILD/CUTOVER: apply six exact Eldyrwild alias_remove decisions
        ↓
remeasure Eldyrwild
expected EVIDENCE_PROVENANCE 8 → 2
remaining: Captain + Thrin Branchborn
        ↓
resume alias-package construction
expected EVIDENCE_PROVENANCE 2 → 0
```

Treat `8 → 2` as an expected later observation, not permission to fake the count in this PR.
