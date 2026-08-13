---
pr_body_template: |
  ## Handoff pointer
  - Conversation: CUTOVER — alias assertion adoption package after PR 575
  - Flow / agent: CUTOVER
  - Direction: DESIGN → CODE
  - Handoff: Docs/Plans/HANDOFF-CUTOVER-alias-assertion-package-after-575.md
  - PR / branch: cutover/alias-assertion-package-after-575

  ## Verification pointer
  - Semantic predecessor: DungeonMindBuddy PR #575 merge d32c244e8505b2d35d1aa536f6ef6cc097d735ce
  - DungeonMind pin: be76acc997c5fbcb8ceaa090969ec051afa6051d
  - Predecessor fixture: tests/fixtures/dungeonmind_kernel/eldyrwild_cutover_identity_lifecycle_history_after_571_v1.json
  - Predecessor fixture SHA-256: 1a2cd8f9c47b223d4623fccbe1c988dd8d3eb1c8796078a32a32720f51ef000b
  - Verification: exact §7 commands/results from the implementation handback

  The checked-in handoff, cumulative code diff, nano commits, and independently
  rerun verification are the review contract. The PR description is transport
  metadata only. Post-merge state-authority sync is a separate guarded operation.
---

# HANDOFF — CUTOVER reconstruct alias assertion adoption package after PR #575

**Created:** 2026-08-12.  
**Status:** DESIGN READY — **DO NOT DISPATCH until the post-PR #575 atomic state-authority sync is complete.**  
**Canonical handoff path:** `Docs/Plans/HANDOFF-CUTOVER-alias-assertion-package-after-575.md`  
**Conversation name:** `CUTOVER — alias assertion adoption package after PR 575`  
**Flow / agent:** `CUTOVER`  
**Handoff direction:** `DESIGN → CODE`  
**Design agent:** `ChatGPT stewardship / GPT-5.6 Sol`  
**Code agent:** `external implementation agent`  
**PR title:** `CUTOVER: reconstruct alias assertion adoption package`  
**Suggested branch:** `cutover/alias-assertion-package-after-575`

> **Steward anchor:** Build one deterministic, non-publishing Buddy adoption-package projection in which every currently blocking substantive alias is admitted as a DungeonMind-compatible alias assertion **only when its exact current value, assertion identity lineage, assertion metadata, and evidence provenance are losslessly reconstructable from revision-bound Buddy authority.**
>
> Do not fix aliases by editing graph truth. Do not invent evidence. Do not turn canonical labels or derivable lookup-index keys into authored alias claims. Do not traverse identity history to manufacture alias provenance. Do not start existing-world adoption.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Alias blocker element** | One current durable element classified `EVIDENCE_PROVENANCE` because a substantive Buddy alias cannot yet be expressed at DungeonMind assertion grain. |
| **Substantive node alias** | A nonblank `node.aliases` value that is not case-insensitively equal to the node's canonical `label`. |
| **Derivable alias-index key** | A `store.aliases` key already derivable from the canonical label or a substantive `node.aliases` value for its target node. It is lookup materialization, not an independent authored claim. |
| **Source assertion** | One revision-bound active Buddy `GraphContributionAssertion` whose semantic payload explicitly carries the alias claim. |
| **Direct alias assertion** | A Buddy `assertion_kind="alias"` whose subject is the current target node and whose alias value is exact. |
| **Bundled node alias** | An alias string explicitly present in the semantic `aliases` list of a Buddy `assertion_kind="node"` for the current target node. |
| **Alias adoption row** | One deterministic DungeonMind `AliasAssertionV4Record`-compatible value plus `KnowledgeAssertionMetadataV1`, accompanied by Buddy source-lineage proof. |
| **Covered blocker element** | An alias blocker element for which every substantive current alias represented by that durable element is completely reconstructed with no unsupported active source claim. |
| **Residual alias** | A current alias that cannot be reconstructed without guessing, hidden inheritance, identity replay, or source-authority drift. A residual is a STOP in this PR. |
| **Predecessor policy** | PR #575's explicit identity-lifecycle source-history policy. It remains required so the post-575 baseline is measured exactly. |

The flow identifier `CUTOVER` is the active repository/workstream owner for this slice.

---

## §1 Mission and merge-ready invariant

**Mission**

```text
CUTOVER can build a deterministic DungeonMind-compatible alias assertion package
for the exact post-PR575 Buddy alias blockers so that substantive current aliases
cross the repository boundary with source-grounded assertion metadata and evidence,
without mutating Buddy truth or inventing provenance.
```

**Merge-ready invariant**

```text
Against the exact PR575 successor world and DungeonMind PR30 contracts, the same
eight EVIDENCE_PROVENANCE blocker elements are first enumerated losslessly; every
one is then covered by one or more deterministic AliasAssertionV4Record-compatible
rows whose value, source assertion lineage, metadata, and evidence are proven from
revision-bound Buddy authority; legacy/default PR575 analysis remains byte-stable;
only those exact eight blocker elements change classification; EVIDENCE_PROVENANCE
clears 8→0; every unrelated blocker, relationship inventory, identity/contribution
history count, canonical graph byte, source authority, and predecessor fixture
remains unchanged; any alias requiring guessed evidence, ambiguous metadata,
identity-history traversal, or stale/mutated contribution authority fails closed
instead of being packaged.
```

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes.** Every path is a read-only reconstruction of current alias semantics into the existing DungeonMind alias-assertion contract. |
| What adversarial sequence is most likely to falsify it? | A materialized alias matches historical text, but the contribution ledger was mutated after publication or the only provenance belongs to a merged-away identity; a naive adapter reuses that evidence and falsely calls the alias package lossless. |
| Would the proposed §7 evidence detect that failure? | **Yes.** Revision-bound contribution digest checks, support-lineage equality, current-node subject checks, evidence resolvability, exact blocker-set sealing, and adversarial identity-derived/digest-drift tests must all fail closed. |
| Which owning boundary is easiest to under-test? | The source-lineage → DungeonMind metadata adapter. Helper tests alone are insufficient; the successor service must build and verify the exact real-world package. |
| What fact would force this slice to stop or split? | Any one of the exact eight blocker elements cannot be covered without inventing a display alias/evidence ref/metadata value, traversing merged-away identity history, or changing DungeonMind. **Do not seal a partial 8→N package in this PR; stop with the exact residual proof.** |

### Dispatch gate before implementation

PR #575 is merged, but at handoff creation current `main` still has mutable sequencing documents that describe the PR #575 slice as active/DOING.

Before the code agent starts, complete one guarded post-#575 state-authority sync:

```text
PR #575 merge:
d32c244e8505b2d35d1aa536f6ef6cc097d735ce

required sync intent:
- mark PR #575 / cutover-identity-lifecycle-history-after-571 DONE
- record cumulative review cycles = 3
- record merge d32c244e...
- make this alias-assertion package the next bounded CUTOVER slice
- update the current-state guide to the post-575 anchor
- preserve Backlog's already-correct READY EVIDENCE_PROVENANCE item unless its claim actually changed
```

Expected mutable authorities to inspect in that guarded sync:

```text
Docs/Plans/HANDOFF-cutover-identity-lifecycle-history-after-571.md
Docs/Plans/PR-TRACKER-campaign-supergraph.md
Docs/Design/STATUS-world-graph-continuity-spine.md
Backlog.md
Backlog-DONE.md
```

Only files whose current-state claim actually changed should be edited.

The implementation branch must then start from the exact checked-in handoff/state-sync descendant. If any product/kernel code lands between `d32c244e...` and dispatch, re-anchor instead of assuming semantic equivalence.

---

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` CUTOVER dispatch ladder; `Docs/Design/ARCHITECTURE-campaign-supergraph.md`; PR #575 successor ledger |
| Repository rules | `AGENTS.md`; `.cursor/skills/external-agent-pr-loop/SKILL.md`; re-anchor, isolated lane, write lease, review every distinct head, atomic state sync |
| Semantic base revision | `d32c244e8505b2d35d1aa536f6ef6cc097d735ce` — PR #575 merge |
| Dispatch base | Exact post-#575 state-sync / checked-in-handoff descendant of `d32c244e...`; record exact SHA in handback |
| Predecessor contract | PR #575 successor fixture `eldyrwild_cutover_identity_lifecycle_history_after_571_v1.json`, SHA `1a2cd8f9c47b223d4623fccbe1c988dd8d3eb1c8796078a32a32720f51ef000b` |
| DungeonMind semantic pin | `be76acc997c5fbcb8ceaa090969ec051afa6051d` (PR #30) |
| DungeonMind graph contract | `dm_union_graph_v5`; v5 reuses v4 alias assertion record semantics |
| DungeonMind alias record | `AliasAssertionV4Record(value, assertion_metadata)` |
| DungeonMind assertion metadata | `KnowledgeAssertionMetadataV1` — assertion ID, campaign scope, visibility, epistemic kind, canon state, nonempty evidence refs, session refs, explicit temporal scope |
| Canonical Buddy revision | `rev:5a7c13ae45c49a65b402920499be72ed` |
| Canonical graph payload SHA | `2632870ef70638969503de788cfdec97acd490875deff3e2630ac91dc96fe974` |
| #566 projection authority | `eldyrwild-relationship-node-kind-source-repair-v1`, manifest SHA `96cc26fc6e99448e8fba5cd6982070c1e29bb058f2b1e8a4ac291f8a0a083247` |
| Exact input consumed | Canonical Buddy store + exact #566 four-kind in-memory projection + PR #575 predecessor fixture + revision-bound contribution/support/evidence authority |
| Current package blocker | `EVIDENCE_PROVENANCE = 8`, Buddy-owned, `adoption_package_construction` |
| Named successor | The refreshed ledger decides. Five cross-repository dual-sense relationship STOPs are expected to remain; governed existing-world adoption remains later. |
| What remains false | No DungeonMind existing-world adoption transaction; no Postgres adoption; no Buddy read/write authority switch; no identity-history replay; no relationship decision |
| Explicit non-goals | Graph mutation, source correction, alias cleanup, identity merge replay, new DungeonMind alias schema, broad provenance repair, relationship cleanup, Case B adoption, authority promotion |

### Authoritative inputs — read in order

1. `AGENTS.md`
2. `Docs/Plans/PR-TRACKER-campaign-supergraph.md`
3. `Docs/Design/STATUS-world-graph-continuity-spine.md`
4. `Docs/Plans/HANDOFF-cutover-identity-lifecycle-history-after-571.md`
5. `tests/fixtures/dungeonmind_kernel/eldyrwild_cutover_identity_lifecycle_history_after_571_v1.json`
6. `apps/live_control_server/services/cutover_identity_lifecycle_history_after_571.py`
7. `apps/live_control_server/integrations/dungeonmind_kernel/whole_world_conformance_v4.py`
8. `apps/live_control_server/integrations/dungeonmind_kernel/whole_world_conformance_v5.py`
9. `src/graph_memory/evidence/assertion_support.py`
10. `src/graph_memory/kernel/contribution_models.py`
11. `src/graph_memory/kernel/contributions.py`
12. `src/graph_memory/world_supergraph/contribution_store.py`
13. `src/graph_memory/union_supergraph/model.py`
14. Pinned DungeonMind `src/dungeonmind/application/graph_snapshot_v4.py`
15. Pinned DungeonMind `src/dungeonmind/application/graph_snapshot_v5.py`
16. Pinned DungeonMind `src/dungeonmind/contracts/knowledge_assertion.py`
17. Existing alias conformance tests under `tests/test_dungeonmind_whole_world_conformance_v3.py`
18. Existing contribution/support integrity tests

### Exact predecessor facts

PR #575 established:

```text
ATTRIBUTE_ASSERTION = 0

EVIDENCE_PROVENANCE = 8
  blocking_stage = adoption_package_construction
  responsible_repo = DungeonMindBuddy

CONTRIBUTION_HISTORY = 5285
  blocking_stage = durable_adoption

IDENTITY_HISTORY = 14
  blocking_stage = durable_adoption

migration RELATIONSHIP_PREDICATE = 5
  blocking_stage = adoption_package_construction
  ownership_scope = cross_repository

DURABLE_ADOPTION_BOUNDARY = 1
POSTGRES_ADOPTION = 1

CUTOVER_NOT_READY
```

Known representative `EVIDENCE_PROVENANCE` examples from the compact predecessor ledger are:

```text
node:item_foot_of_statue:field:aliases
node:loc:chilled_warehouse:field:aliases
node:loc:crooked-retort:field:aliases
node:loc:the-council:field:aliases
node:loc:underground-entrance:field:aliases
```

**These are examples, not the complete authority.**

The implementation must enumerate and seal **all exact eight** blocker element IDs from the full classified-element inventory. Do not guess the other three from names, source prose, or search results.

### Current alias semantics already settled by the analyzer

Current Buddy conformance rules already distinguish:

```text
node.aliases empty
→ BUDDY_OPERATIONAL_ONLY

node.aliases contains only canonical-label duplicate(s)
→ BUDDY_OPERATIONAL_ONLY

substantive node.aliases
→ EVIDENCE_PROVENANCE
  because current node field lacks assertion-grain alias evidence

store.aliases entry derivable from canonical label or node.aliases
→ BUDDY_OPERATIONAL_ONLY

non-derivable store.aliases entry
→ EVIDENCE_PROVENANCE
```

Preserve those semantics.

The next PR is not allowed to convert operational lookup material into authored DungeonMind alias assertions merely to make the counter green.

---

## §3 Observable-path and adversarial-sequence inventory

| Path | Current behavior | Required behavior | Same invariant as §1? | Owning boundary |
|---|---|---|---:|---|
| Predecessor PR #575 reproduction | Exact fixture verifies; EP count = 8 | Byte-identical predecessor reproduction before successor work | Yes | CUTOVER successor service |
| Full blocker enumeration | Compact fixture exposes only representative examples | Capture exact all-eight `EVIDENCE_PROVENANCE` classified element IDs losslessly | Yes | Whole-world analyzer + successor service |
| Canonical-label alias | Operational lookup material | Remains operational-only; never enters alias package | Yes | Alias package proof |
| Derivable `store.aliases` key | Operational lookup index | Remains operational-only; never enters alias package | Yes | Alias package proof |
| Substantive node alias | EP blocker at node field grain | Reconstruct every current substantive alias from exact revision-bound source assertion(s) and produce DM alias row(s) | Yes | Alias package proof |
| Non-derivable store alias | EP blocker | Package only if exact human alias value and current-node source assertion lineage are directly recoverable | Yes | Alias package proof |
| Explicit Buddy alias assertion | Already assertion-grain in contribution history | Preserve exact semantic alias source and provenance; map to DM metadata | Yes | Source-lineage adapter |
| Alias bundled in Buddy node assertion | Coarse node assertion carries alias + evidence | Split deterministically into alias assertion row while preserving exact source assertion/evidence lineage | Yes | Source-lineage adapter |
| Multiple active source assertions for same alias text | Buddy may have multiple supports | Preserve distinct source assertions; DungeonMind permits duplicate alias text as distinct assertions | Yes | Alias package proof |
| Missing/dangling evidence | Cannot produce DM metadata safely | Residual / STOP; never synthesize evidence | Yes | Proof validator |
| Mutated contribution ledger after publication | Mutable file may disagree with revision-bound digest/support | Fail closed; do not trust mutable payload | Yes | Revision-bound source check |
| Alias only attributable through merged-away identity | Requires identity-history reasoning | STOP; do not traverse redirect/merge history in this slice | Yes | Alias proof boundary |
| #566 four-kind projection | Changes only four kinds | Alias proof and package rows remain byte/semantic identical | Yes | Successor service |
| Successor fixture replay | New non-publishing package/report | Deterministic byte-for-byte reproduction | Yes | Build/verify service |

### Ordered failure sequences

| Sequence | Required safe outcome | Owning proof |
|---|---|---|
| Materialized alias → find contribution → contribution digest differs from revision-bound seal | Refuse package row; stop with source-authority drift | §7 source-digest adversarial test |
| Alias → active support → evidence set in mutable assertion differs from `per_contribution_evidence_ref_ids` | Refuse; do not reuse aggregate support | §7 provenance-lineage adversarial test |
| Alias → source candidate exists only on merged-away node → active redirect points to survivor | Refuse this PR; report `identity_derived_alias_requires_identity_replay` | §7 identity-boundary test |
| Alias text appears in two active assertions with different metadata/evidence | Emit two distinct assertion rows; never first-win/collapse | §7 duplicate-text/multi-assertion test |
| Node aliases include label plus one substantive alias | Ignore label duplicate; package only substantive alias | §7 canonical-label regression |
| `store.aliases` key already derives from packaged/current node alias | Keep operational-only; do not emit second assertion | §7 lookup-index regression |
| Non-derivable alias key exists but no exact human alias string is source-grounded | STOP; normalized key is not promoted into invented display text | §7 non-derivable-key adversarial test |
| All eight appear covered, but one package row fails DungeonMind `AliasAssertionV4Record` / metadata validation | STOP; EP remains unresolved | §7 pinned-DM contract validation |
| Canonical package passes, #566 projection changes alias package bytes | STOP; kind-only projection leaked into alias semantics | §7 canonical/projection equality |
| Package clears EP but selector returns Case B while five relationship package blockers remain | STOP; stage-driven dispatch regression | §7 recommendation test |

---

## §4 Files in scope (allowlist)

The implementation PR is expected to modify only these paths.

| Action | Path | Purpose: how this establishes or proves §1 |
|---|---|---|
| Create | `apps/live_control_server/integrations/dungeonmind_kernel/alias_assertion_package_conformance_v1.py` | Exact alias blocker/source-lineage reconstruction and DungeonMind alias-record validation |
| Modify | `apps/live_control_server/integrations/dungeonmind_kernel/whole_world_conformance_v4.py` | Add explicit, proof-gated alias-package classification policy while preserving legacy/default behavior |
| Modify | `apps/live_control_server/integrations/dungeonmind_kernel/whole_world_conformance_v5.py` | Pass the explicit alias-package policy through the current v5 target seam without changing its default |
| Create | `apps/live_control_server/services/cutover_alias_assertion_package_after_575.py` | Verify PR #575 predecessor, build canonical + #566 successor measurement, seal exact blocker/classification delta and no-mutation proof |
| Create | `scripts/build_cutover_alias_assertion_package_after_575.py` | Thin build/status/verify CLI for deterministic fixture |
| Create | `tests/test_alias_assertion_package_conformance_v1.py` | Focused source-lineage, metadata, ambiguity, and fail-closed proofs |
| Create | `tests/test_cutover_alias_assertion_package_after_575.py` | Exact real-world predecessor/successor acceptance, blocker delta, fixture, no-mutation, recommendation |
| Create | `tests/fixtures/dungeonmind_kernel/eldyrwild_cutover_alias_assertion_package_after_575_v1.json` | Deterministic successor evidence artifact; SHA established by implementation, not this handoff |

**Bounded discovery exception**

```text
Directory:
tests/

Maximum additional paths:
2

Allowed path kinds:
Existing focused conformance / contribution-integrity test files only.

Decision rule for including one:
Only when a pre-existing owning-boundary regression belongs in the existing test
file and cannot be proven more directly by the two new focused suites.

Not permitted:
new product tests, UI tests, relationship tests, broad snapshot churn.
```

### Handoff check-in is not implementation scope

This handoff itself must be checked in before dispatch as repository authority. It is not an excuse for the implementation worker to rewrite or “simplify” it.

Post-merge tracker/status/backlog updates are a separate atomic state-authority sync, not implementation scope.

---

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why this slice must not touch or claim it |
|---|---|
| `pyproject.toml` | DungeonMind pin and dependencies are unchanged |
| `uv.lock` | No dependency change |
| `src/graph_memory/kernel/contribution_merge.py` | Source authority is read, not rewritten |
| `src/graph_memory/kernel/contributions.py` | Existing assertion/provenance identity is authority; no mutation needed |
| `src/graph_memory/kernel/contribution_models.py` | Do not redesign Buddy assertion contract |
| `src/graph_memory/evidence/assertion_support.py` | Existing support ledger is evidence, not a target |
| `src/graph_memory/kernel/identity_decisions.py` | Identity replay is separate durable-adoption work |
| `src/graph_memory/kernel/identity.py` | No identity rewrite/rebind |
| `graph_data/approved_graph_corrections/eldyrwild/**` | No source correction |
| Canonical World Graph files under runtime data | Analysis is non-publishing |
| `tests/fixtures/dungeonmind_kernel/eldyrwild_cutover_identity_lifecycle_history_after_571_v1.json` | PR #575 predecessor fixture is immutable |
| `tests/fixtures/dungeonmind_kernel/eldyrwild_cutover_repin_after_dm30_v1.json` | PR #571 fixture remains immutable |
| `tests/fixtures/dungeonmind_kernel/eldyrwild_cutover_reanchor_after_566_v1.json` | PR #568 fixture remains immutable |
| #566 repair manifest | Relationship kind projection authority is immutable |
| `Drakosfire/DungeonMind` | Pinned kernel already admits alias assertions; no sibling-repo change |
| Relationship mapping/adjudication code | Five dual-sense STOPs remain a separate cross-repository decision |
| DungeonMind adoption service / repository | Case B is still forbidden while package-construction blockers remain |
| Postgres adoption | Later durable-adoption proof |
| Buddy read/write routing | No authority switch |
| Alias cleanup/dedupe/rename | This PR translates existing truth; it does not improve content |
| Evidence fabrication or synthetic source spans | Explicitly forbidden |
| Traversal of merged-away identity to justify alias claims | Would couple this slice to identity-history replay |
| `Docs/Plans/PR-TRACKER-campaign-supergraph.md` in implementation PR | State sync happens after merge, separately |
| `Docs/Design/STATUS-world-graph-continuity-spine.md` in implementation PR | Same |
| `Backlog.md` / `Backlog-DONE.md` in implementation PR | Same |

If one of these must change to make the package work, stop and report the newly discovered contract gap.

---

## §6 Implementation contract and conditional matrices

### Input

```text
Buddy:
  exact canonical Eldyrwild revision
  exact canonical graph payload SHA
  exact #566 four-kind migration projection
  PR #575 predecessor fixture
  PR #575 identity-lifecycle source-history proof/policy
  current nodes + store.aliases
  assertion_support
  contribution_replay_manifest
  contribution_source_payload_sha256
  exact contribution ledger records
  evidence
  source_artifacts
  identity merge/redirect records only for boundary detection, never provenance traversal

DungeonMind:
  exact PR #30 pin be76acc...
  dm_union_graph_v5
  AliasAssertionV4Record
  KnowledgeAssertionMetadataV1
  v2 evidence/source-artifact contracts
```

### Output

A deterministic report, recommended schema:

```text
dmb_cutover_alias_assertion_package_after_575_v1
```

containing at least:

```text
predecessor
exact_evidence_provenance_blocker_ids
alias_inventory
package_rows
covered_blocker_element_ids
residuals
canonical_view
migration_projection
classification_delta
blocker_delta
relationship_invariants
adoption_seam
mutation_proof
cutover_disposition
next_slice_recommendation
```

A recommended proof schema:

```text
dmb_alias_assertion_package_conformance_v1
```

### Recommended package-row shape

Names may follow local conventions, but semantics are normative:

```python
class AliasAssertionPackageRowV1(BaseModel):
    blocker_element_id: str
    target_node_id: str
    alias_value: str

    source_form: Literal[
        "explicit_alias_assertion",
        "bundled_node_alias",
    ]

    buddy_source_assertion_id: str
    buddy_source_contribution_id: str
    buddy_source_payload_sha256: str

    source_evidence_ref_ids: list[str]
    source_artifact_ids: list[str]

    dungeonmind_assertion_id: str
    dungeonmind_alias_record: dict[str, Any]

    metadata_derivation: dict[str, str]
    reconstructable: bool
    rationale: str
```

### Recommended residual shape

```python
class AliasPackageResidualV1(BaseModel):
    blocker_element_id: str
    target_node_id: str | None
    alias_value: str | None
    alias_key: str | None
    reason_code: str
    source_candidate_ids: list[str]
    diagnostics: list[str]
```

### Invariant

Same as §1.

### Failure behavior

```text
predecessor fixture drift
→ refuse

EVIDENCE_PROVENANCE count != 8 at pinned source
→ refuse / re-anchor

exact blocker set cannot be enumerated
→ refuse

alias not source-grounded
→ residual + STOP

contribution digest drift
→ residual + STOP

support lineage drift
→ residual + STOP

missing/dangling evidence
→ residual + STOP

metadata cannot be mapped without guessing
→ residual + STOP

only identity-merge lineage explains alias
→ residual + STOP

DungeonMind alias record validation failure
→ residual + STOP

any residual after exact-eight analysis
→ DO NOT seal the successor fixture in this PR
→ return exact residual proof for steward redesign

all eight covered
→ apply explicit alias-package policy in memory
→ remeasure canonical + #566 projection
→ require EVIDENCE_PROVENANCE 8→0
```

### Replay / idempotency

```text
same exact source + same exact contract pins
→ byte-identical package rows, report, and fixture

changed contribution ledger with same revision-bound digest expectation
→ fail closed when ledger bytes no longer hash to the bound digest

changed canonical revision / payload / predecessor fixture / DM pin
→ stale-input refusal

retry after interrupted fixture build
→ existing identical bytes accepted; differing bytes refuse overwrite
```

### Trust boundary

```text
Verifies:
- exact current blocker set
- current materialized alias values
- exact revision-bound active contribution membership
- contribution source-payload digest
- exact assertion-support lineage
- exact source assertion semantic inclusion of alias
- evidence nonemptiness and resolvability
- deterministic metadata translation
- DungeonMind alias-record model validity
- package coverage of every blocker
- no source mutation

Records or trusts without proving:
- truth of source prose itself
- whether a human should prefer one alias over another
- future DungeonMind adoption transaction correctness
- relationship dual-sense decisions
```

### Source assertion discovery contract

For every current alias requiring packaging, search only revision-bound active Buddy authority.

#### Direct source form A — explicit alias assertion

A candidate is admissible only when:

```text
assertion.acceptance_state == "accepted"
assertion.assertion_kind == "alias"
assertion.subject_node_id == current target node_id
exact alias string is recoverable from assertion.value["alias"] and/or assertion.label
if both are present, they agree after only whitespace trimming
assertion's contribution is revision-bound active
support record is supported and names that contribution
support graph_object_id is the current target node (or null only if current repo semantics explicitly permit and exact subject still agrees)
```

Do not casefold two differing source strings into one authored value.

#### Direct source form B — bundled node alias

A candidate is admissible only when:

```text
assertion.acceptance_state == "accepted"
assertion.assertion_kind == "node"
assertion.subject_node_id == current target node_id
semantic_assertion_value(assertion.value)["aliases"] contains the exact current alias string
assertion's contribution is revision-bound active
support record is supported and names that contribution
```

The source node assertion's evidence supports the semantic payload that explicitly contains the alias. It may therefore be split into a DungeonMind alias assertion without inventing a source.

#### Forbidden source form — identity-derived alias

If a current alias is explainable only because:

```text
identity_merge_records.aliases_unioned
merged-away node label/alias
identity redirect traversal
```

and there is no admissible direct source assertion for the **current target node**, do not manufacture an alias assertion in this PR.

Report:

```text
reason_code = identity_derived_alias_requires_identity_replay
```

This protects the separation established by PR #575: identity history remains a distinct durable-adoption obligation.

### Revision-bound contribution proof

For every package row:

1. Find the source contribution ID in the exact revision replay manifest.
2. Require `status == active`.
3. Require the manifest/source-digest seal to match the exact mutable ledger contribution via `compute_contribution_source_payload_sha256`.
4. Find the exact accepted source assertion by ID.
5. Parse the current `DurableAssertionSupport`.
6. Require `support_state == supported`.
7. Require the contribution ID in `active_contribution_ids`.
8. Require the contribution's exact evidence IDs from `explicit_assertion_evidence_ref_ids(assertion)` to equal the support ledger's `per_contribution_evidence_ref_ids[contribution_id]`.
9. Require corresponding source-artifact lineage to agree with `per_contribution_source_artifact_ids`.
10. Require every referenced evidence ID and source artifact to exist in the exact store.

Do not use aggregate support evidence when per-contribution lineage exists.

Do not repair mutable ledgers.

### DungeonMind assertion ID contract

DungeonMind requires one graph-global opaque stable assertion ID per independent assertion.

Use:

```text
explicit Buddy alias assertion
→ preserve the exact Buddy alias assertion_id
  after proving it is unique within the package/source assertion inventory

alias split from a Buddy node assertion
→ derive a deterministic child ID from:
   world_id
   current target node_id
   source Buddy node assertion_id
   exact alias value
   literal assertion family "alias"
```

Recommended output form:

```text
assertion:cutover-alias:<sha256(canonical-json-input)[:24]>
```

The exact helper and canonical JSON input must be unit-tested and frozen by the new fixture.

Do not use array position.

Do not use current time.

Do not use contribution iteration order.

Do not reuse the parent node assertion ID for a split alias.

If the derived ID collides with any other planned package assertion ID carrying a different semantic claim, fail closed.

### DungeonMind metadata mapping

Each package row must validate as `AliasAssertionV4Record`.

Use source-specific metadata where Buddy actually preserves it.

Explicit precedence:

```text
campaign_scope
  → source GraphContributionAssertion.campaign_scope
  → null remains explicit world-universal; do not replace null with current campaign

visibility
  → source assertion visibility when non-null
  → otherwise exact current node.state.visibility only when it is a recognized DM Visibility
  → otherwise STOP

epistemic_kind
  → source assertion epistemic_kind when non-null
  → otherwise exact current node.state.epistemic_kind only when it is a recognized DM EpistemicKindV2
  → otherwise STOP

canon_state
  → source semantic assertion value["canon_state"] when present and recognized
  → otherwise exact current node.state.canon_state when recognized
  → otherwise STOP

evidence_ref_ids
  → exact per-source-assertion evidence lineage
  → nonempty required

session_refs
  → sorted unique real-world session IDs explicitly present on referenced evidence
  → may also include an explicit legacy source-session stamp when it is the same real-world provenance concept
  → never infer fictional time from session_refs

temporal_scope
  → no temporal scope or source-session-only observation means DM "unknown"
  → never upgrade unknown to world_timeless
  → explicit fictional-time semantics require an exact already-governed DungeonMind FictionalTimeAnchorRef mapping
  → if such mapping is not already available from current contracts, STOP rather than invent one
```

If source-specific visibility/epistemic/canon metadata conflicts with the proposed current-node fallback, preserve the source-specific value **only if doing so remains consistent with current Buddy semantics and the same alias source assertion**. If the conflict reveals two authorities rather than a representable per-assertion distinction, STOP.

The proof row must record where every metadata field came from. No hidden fallback.

### A. State and fallback matrix

| Observable path | Loading / initializing | Exact success | Ordinary miss | Dependency unavailable | Integrity / contract failure | Stale / superseded | Retry / replay |
|---|---|---|---|---|---|---|---|
| Predecessor verify | Verify exact SHA and bytes | Continue | N/A | Fail closed | Fail closed | Re-anchor | Safe |
| Exact blocker inventory | Full classified capture | Exactly 8 IDs | N/A | Fail closed | Fail closed | Re-anchor | Deterministic |
| Alias source search | Read revision-bound support + contributions | One or more admissible source assertions | Residual/STOP | Residual/STOP | Residual/STOP | Residual/STOP | Deterministic |
| DM record validation | Pinned PR30 models | Valid row | N/A | Fail closed | Residual/STOP | Re-anchor | Deterministic |
| Successor remeasurement | Explicit package policy | EP 8→0 | N/A | Fail closed | Fail closed | Re-anchor | Deterministic |
| Fixture build | Compose exact report | Write/verify exact bytes | Existing same bytes accepted | Fail closed | Differing existing bytes refused | Re-anchor | Idempotent |

No fallback source other than the explicit metadata precedence above is permitted.

### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Current target node ID | Exact durable Buddy node ID | Missing target = STOP | No |
| Explicit alias source subject | Must equal current target node ID | Different/merged-away subject = STOP | No |
| Alias value | Exact trimmed source string must equal current substantive alias | Casefold-only agreement is insufficient to rewrite display text | No |
| Canonical label duplicate | Operational-only | Never package | No |
| Derivable alias-index key | Operational-only | Never package a duplicate claim | No |
| Non-derivable alias-index key | Requires exact source-grounded human alias value | Key-only source = STOP | No |
| Merged-away identity | Do not traverse to justify alias | Report identity-derived residual | No |
| Duplicate alias text from distinct active source assertions | Preserve as distinct assertions | No first-win | No collapse |
| Assertion ID | Explicit alias keeps source ID; bundled-node alias gets deterministic child ID | Collision with differing semantic claim = STOP | No |

### C. Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate / replay behavior | Compatibility / migration | Rollback / reversion |
|---|---|---|---|---|---|
| PR #575 predecessor | Locked JSON fixture SHA `1a2cd8f9...` | Byte-stable | Verify only | Immutable predecessor | N/A |
| Alias package proof | New deterministic JSON section | Same source → same rows/order/IDs | Exact duplicate input → same bytes | Diagnostic only; no graph migration | Delete successor fixture/code if reverted |
| Successor fixture | New checked-in JSON fixture | Independent reproduce = identical bytes | Existing identical accepted; differing refused | Pins exact PR575 world + DM PR30 contracts | Git revert |
| World Graph | **No write** | Before/after digests identical | N/A | No migration | N/A |
| Contribution/evidence ledgers | **No write** | Before/after digests identical | N/A | No repair | N/A |

### D. Predecessor-to-consumer mapping

**Grounding sources:**

```text
Buddy:
GraphContributionAssertion
DurableAssertionSupport
UnionSupergraphNode
UnionSupergraphEvidence
UnionSupergraphSourceArtifact
PR #575 exact classified inventory

DungeonMind:
AliasAssertionV4Record
KnowledgeAssertionMetadataV1
dm_union_graph_v5 evidence ledger
```

| Predecessor field / outcome | Real shape and optionality | Consumer field / behavior | Transformation | Proof fixture/test |
|---|---|---|---|---|
| `node.aliases[]` substantive value | string | `AliasAssertionV4Record.value` | Exact trimmed value only | real-world package fixture |
| explicit alias `assertion_id` | nonblank deterministic string | `assertion_metadata.assertion_id` | Preserve exact | ID regression |
| bundled node assertion ID + alias | node assertion ID + exact string | alias assertion ID | Deterministic child ID | ID determinism test |
| `assertion.campaign_scope` | string or null | `campaign_scope` | Exact | metadata mapping test |
| `assertion.visibility` | optional string | `visibility` | Source value; explicit current-node adapter only if absent | metadata test |
| `assertion.epistemic_kind` | optional string | `epistemic_kind` | Source value; explicit current-node adapter only if absent | metadata test |
| source `value.canon_state` / node state | optional string | `canon_state` | Explicit precedence above | metadata test |
| per-contribution evidence refs | list[str] | `evidence_ref_ids` | Exact, nonempty | provenance-lineage test |
| evidence `session_id` | optional string | `session_refs[]` | Sorted unique real-world refs | session-vs-time test |
| absent / source-session-only temporal scope | null / provenance-only session | `temporal_scope.kind=unknown` | Explicit semantic adapter | temporal test |
| substantive alias blocker element | durable element ID | classification | Only proof-covered exact ID → `REPRESENTABLE_BY_EXPLICIT_ADAPTER` | classification delta |
| canonical label / derivable alias index | lookup material | no DM alias row | Remain `BUDDY_OPERATIONAL_ONLY` | regression |

---

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Command or manual scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Post-575 source is exact | successor service | contract | predecessor verifier | fixture SHA `1a2cd8f9...`, verified true | any drift |
| Full EP inventory is lossless | whole-world analyzer | contract | exact classified capture | exactly 8 unique blocker IDs, all persisted in successor fixture | count/set mismatch |
| Operational aliases stay out | alias proof | regression | focused alias classifier tests | label-only + derivable index emit no package rows | any invented assertion |
| Direct alias assertion reconstruction | alias proof | contract | focused source fixture | exact source assertion/evidence/metadata preserved | guessed field |
| Bundled node alias split | alias proof | contract | focused node assertion fixture | deterministic child ID + exact source evidence | parent ID reuse / source loss |
| Multiple same-text source assertions are not collapsed | alias proof | adversarial | two active assertions, differing evidence/metadata | two DM-valid rows | first-win/collapse |
| Mutable contribution drift is detected | alias proof | adversarial | alter ledger provenance without changing expected revision seal | fail closed | package accepted |
| Per-contribution support drift is detected | alias proof | adversarial | support provenance != assertion provenance | fail closed | aggregate evidence reused |
| Missing evidence fails | alias proof | adversarial | dangling/empty evidence | residual/STOP | synthetic evidence |
| Identity-derived alias stays separate | alias proof | adversarial | source exists only on merged-away node + redirect | `identity_derived_alias_requires_identity_replay` | redirect traversal used |
| Non-derivable key cannot invent display alias | alias proof | adversarial | key has no exact source alias string | residual/STOP | key promoted as display value |
| DM alias contract is exact | pinned DungeonMind model | contract | validate every package row with `AliasAssertionV4Record` / `KnowledgeAssertionMetadataV1` | all valid | any validation failure |
| Every blocker is fully covered | successor service | contract | exact set comparison | covered blocker IDs == predecessor 8 IDs; residuals == [] | any residual |
| Exactly the intended classifications change | successor service | lossless delta | predecessor vs successor classified index | exactly 8 EP blocker element transitions; no unrelated transition | compensating/unrelated change |
| EP closes | successor service | contract | canonical + migration report | `EVIDENCE_PROVENANCE` absent / 8→0 | residual row |
| Contribution history unchanged | successor service | regression | blocker delta | 5285→5285 | count/row drift |
| Identity history unchanged | successor service | regression | blocker delta | 14→14 | count/row drift |
| Attribute blocker stays clear | successor service | regression | blocker delta | ATTRIBUTE_ASSERTION remains absent | reintroduced |
| Relationships unchanged | successor service | regression | inventory proof | canonical 323/314/9/3; migration 323/318/5/3; same five residual IDs | any drift |
| #566 projection cannot affect alias proof | successor service | adversarial | compare canonical vs projection package proof | package rows/coverage identical | any alias delta |
| No graph/source mutation | successor service | contract | before/after digests | all exact | mutation |
| Case B remains forbidden while package blockers remain | selector | regression | `_next_slice_recommendation(actual blockers)` | recommendation derived from ledger; not Case B while five relationship package STOPs remain | hardcoded/invalid Case B |
| Fixture deterministic | build/verify CLI | replay | build then independent verify | exact new SHA; identical bytes | nondeterminism |
| Changed paths stay leased | git | scope | diff commands | §4 only | any unleased path |

### Required commands

Run every applicable command and report exact counts/results.

```bash
# predecessor / current CUTOVER regressions
uv run pytest -q \
  tests/test_cutover_identity_lifecycle_history_after_571.py \
  tests/test_cutover_whole_world_repin_after_dm30.py \
  tests/test_dungeonmind_whole_world_conformance_v5.py

# new owning proof
uv run pytest -q \
  tests/test_alias_assertion_package_conformance_v1.py \
  tests/test_cutover_alias_assertion_package_after_575.py

# alias behavior / provenance regressions
uv run pytest -q \
  tests/test_dungeonmind_whole_world_conformance_v3.py \
  tests/test_graph_kernel_contribution_integrity.py \
  tests/test_graph_kernel_contribution_source_authority.py

# relationship authority must stay untouched
uv run pytest -q \
  tests/test_eldyrwild_relationship_node_kind_source_repair.py \
  tests/test_cutover_whole_world_reanchor.py

# deterministic successor
uv run python scripts/build_cutover_alias_assertion_package_after_575.py status
uv run python scripts/build_cutover_alias_assertion_package_after_575.py build
uv run python scripts/build_cutover_alias_assertion_package_after_575.py verify

# lint / scope
uv run ruff check \
  apps/live_control_server/integrations/dungeonmind_kernel/alias_assertion_package_conformance_v1.py \
  apps/live_control_server/integrations/dungeonmind_kernel/whole_world_conformance_v4.py \
  apps/live_control_server/integrations/dungeonmind_kernel/whole_world_conformance_v5.py \
  apps/live_control_server/services/cutover_alias_assertion_package_after_575.py \
  scripts/build_cutover_alias_assertion_package_after_575.py \
  tests/test_alias_assertion_package_conformance_v1.py \
  tests/test_cutover_alias_assertion_package_after_575.py

git diff --check
git diff --stat <DISPATCH_BASE_SHA>...HEAD -- \
  apps/live_control_server/integrations/dungeonmind_kernel/alias_assertion_package_conformance_v1.py \
  apps/live_control_server/integrations/dungeonmind_kernel/whole_world_conformance_v4.py \
  apps/live_control_server/integrations/dungeonmind_kernel/whole_world_conformance_v5.py \
  apps/live_control_server/services/cutover_alias_assertion_package_after_575.py \
  scripts/build_cutover_alias_assertion_package_after_575.py \
  tests/test_alias_assertion_package_conformance_v1.py \
  tests/test_cutover_alias_assertion_package_after_575.py \
  tests/fixtures/dungeonmind_kernel/eldyrwild_cutover_alias_assertion_package_after_575_v1.json

git diff --name-only <DISPATCH_BASE_SHA>...HEAD
```

If the bounded discovery exception adds one or two existing test files, include them explicitly in Ruff/diff verification where applicable.

### Required real-world acceptance values

Before merge, the successor report must prove:

```text
predecessor EVIDENCE_PROVENANCE blocker element count:
8

exact predecessor blocker IDs:
<all eight, not representative examples>

package residual count:
0

covered blocker element count:
8

successor EVIDENCE_PROVENANCE:
0 / absent

ATTRIBUTE_ASSERTION:
0 / absent

CONTRIBUTION_HISTORY:
5285

IDENTITY_HISTORY:
14

canonical relationships:
323 semantic
314 represented
9 residual
3 uses_statblock

migration relationships:
323 semantic
318 represented
5 residual
3 uses_statblock

migration residual IDs:
edge:loc:central-office:located_in:node:meat_distribution_network_session9:site-of
edge:loc:packing-loading-area:part_of:node:meat_distribution_network_session9
edge:node:headmaster_tinkerbright:leads:loc:wizard_college
edge:node:hempholm_townsfolk:participates_in:node:hempholm_folk_revelry
edge:pc:caelynn:participates_in:node:hempholm_folk_revelry

cutover disposition:
CUTOVER_NOT_READY
```

### Exact classification delta

Seal every durable-element semantic transition.

Expected family:

```text
previous:
classification = DUNGEONMIND_DURABILITY_CONTRACT_GAP
blocker_class  = EVIDENCE_PROVENANCE

current:
classification = REPRESENTABLE_BY_EXPLICIT_ADAPTER
blocker_class  = None
```

The exact eight IDs come from measurement.

No other durable-element semantic key may change.

Add an adversarial compensating-change test similar to PR #571's T12 lesson: a same-count swap is still a failure.

### Minimal live / dogfood proof

```text
Not applicable — this is a non-publishing deterministic migration-package
diagnostic. The real-world Eldyrwild fixture is the owning integration proof.
No new product surface is authorized.
```

### Baseline failure protocol

If any required command already fails on the dispatch base:

1. run the same command on dispatch base and head;
2. preserve exact failure output;
3. distinguish baseline debt from head regression;
4. do not call the gate green;
5. identify an explicit operator waiver if the command is still a required merge gate.

Known historical DungeonMind PR #30 Ruff debt is outside this Buddy PR unless the pinned dependency causes a current required command to fail.

---

## §8 Required review handback

The implementation handback must include all of the following.

### Git identity

```text
dispatch base SHA:
head SHA:
branch:
PR URL:
```

### Pre-dispatch sync proof

```text
PR575 post-merge state sync SHA:
predecessor handoff status:
tracker current slice:
status current slice:
Backlog current item:
```

### Authority pins

```text
Buddy PR575 merge:
d32c244e8505b2d35d1aa536f6ef6cc097d735ce

PR575 fixture:
1a2cd8f9c47b223d4623fccbe1c988dd8d3eb1c8796078a32a32720f51ef000b

DungeonMind:
be76acc997c5fbcb8ceaa090969ec051afa6051d

world-object-v5:
f9fd5420e0ab3849224e0d58cf83dd432ca2e5da22ce661b25654406ec9c60d8

world-property-v3:
aa94df78c10a913e7ca6774198f080131f8f447c90cc917b9b840ed88bd856e4

profile-v3:
2199e8fb96e917c22718e6aec59cbbf55a37ee81575e1bcf16ce13fae0393496

canonical revision:
rev:5a7c13ae45c49a65b402920499be72ed

canonical payload:
2632870ef70638969503de788cfdec97acd490875deff3e2630ac91dc96fe974

#566 manifest:
96cc26fc6e99448e8fba5cd6982070c1e29bb058f2b1e8a4ac291f8a0a083247
```

### Exact eight-blocker inventory

Return all eight:

```text
element_id
element family (node.aliases / store.aliases)
target node id
current canonical label
current substantive alias values
derivable lookup keys
```

### Source-lineage proof per alias assertion row

Return:

```text
blocker element ID
target node ID
alias value
source form
Buddy source assertion ID
Buddy contribution ID
revision-bound contribution SHA
support state
exact evidence refs
exact source artifacts
DM assertion ID
DM metadata derivation
DM model validation result
```

### Residual proof

Must be:

```text
residual_count = 0
residuals = []
```

If not, **do not hand back as merge-ready**. Return the exact stop report instead.

### Classification and blocker delta

Return exact:

```text
all eight classified-element transitions
predecessor blocker count
successor blocker count
all unrelated blocker counts/stages/owners
```

At minimum:

```text
EVIDENCE_PROVENANCE 8 -> 0
CONTRIBUTION_HISTORY 5285 -> 5285
IDENTITY_HISTORY 14 -> 14
ATTRIBUTE_ASSERTION absent -> absent
```

### Relationship invariants

```text
canonical:
323 / 314 / 9 / 3

migration:
323 / 318 / 5 / 3

exact five migration residual IDs:
<list all five>
```

### Recommendation

```text
case:
repository:
basis:
blocking stage:
smallest next change:
cross-repository package blockers:
nonclaim:
```

The recommendation must be the actual selector output, not a hand-authored expected next case.

### Mutation proof

```text
head revision before/after
graph tree before/after
node aliases digest before/after
store.aliases digest before/after
assertion_support digest before/after
contribution replay manifest digest before/after
contribution source digest map before/after
contribution ledger source digests before/after
evidence digest before/after
source artifacts digest before/after
identity authority digest before/after
#566 manifest before/after
PR575 fixture before/after
```

### New fixture

```text
path:
SHA-256:
independent verify:
```

Do not invent the SHA before implementation.

### Nano commits

Recommended stories:

```text
1. CUTOVER: prove exact alias source lineage
2. CUTOVER: add proof-gated alias package policy
3. CUTOVER: remeasure post-575 alias package
4. TEST: seal exact alias package fixture
```

A separate pre-dispatch document/state-sync commit is not one of the implementation nano commits.

### Verification

Return every §7 command with:

```text
command
exit status
pass/fail count
provenance:
  author-local | independently rerun local | CI
baseline comparison if applicable
```

### Scope

```text
actual changed paths:
paths outside §4:
bounded discovery paths used:
operator waivers:
stop conditions encountered:
```

---

## §9 Acceptance rubric

The reviewer accepts only when every item is true.

- [ ] Post-PR575 atomic state-authority sync was completed before dispatch, and the implementation base is an exact descendant of `d32c244e...`.
- [ ] PR #575 predecessor fixture SHA `1a2cd8f9...` reproduces byte-for-byte.
- [ ] The predecessor/default analyzer behavior remains unchanged.
- [ ] The full classified inventory contains exactly eight `EVIDENCE_PROVENANCE` blocker element IDs.
- [ ] The new report contains all exact eight IDs; it does not substitute representative examples.
- [ ] Canonical-label aliases are not packaged.
- [ ] Derivable `store.aliases` keys are not packaged.
- [ ] Every substantive alias in every blocking node field is tied to one or more exact revision-bound active source assertions.
- [ ] Every explicit Buddy alias assertion preserves its exact source assertion identity unless a proven collision requires STOP.
- [ ] Every bundled-node alias uses the deterministic child assertion-ID rule.
- [ ] No array position, current time, or iteration order enters assertion identity.
- [ ] Every source contribution digest matches the revision-bound seal.
- [ ] Every support record is active/supported and its per-contribution evidence/source lineage matches the exact source assertion.
- [ ] Every package row has nonempty evidence and every evidence/source-artifact reference resolves.
- [ ] Every metadata field's derivation source is explicit; no hidden default/fallback exists.
- [ ] Session references never imply fictional time.
- [ ] Unknown temporal state is not rewritten as world-timeless.
- [ ] No alias package row is justified only by merged-away node/redirect traversal.
- [ ] Duplicate alias text from distinct active source assertions remains distinct assertion rows.
- [ ] Every package row validates against pinned DungeonMind `AliasAssertionV4Record` / `KnowledgeAssertionMetadataV1`.
- [ ] Package residual count is zero.
- [ ] Covered blocker IDs equal the exact predecessor eight-ID set.
- [ ] Exactly those eight classified elements change semantic classification/blocker.
- [ ] An adversarial compensating same-count transition fails.
- [ ] `EVIDENCE_PROVENANCE` clears 8→0 in canonical and migration views.
- [ ] `ATTRIBUTE_ASSERTION` remains absent.
- [ ] `CONTRIBUTION_HISTORY` remains 5285.
- [ ] `IDENTITY_HISTORY` remains 14.
- [ ] Canonical relationship inventory remains `323 / 314 / 9 / 3`.
- [ ] Migration relationship inventory remains `323 / 318 / 5 / 3`.
- [ ] The exact five dual-sense relationship STOP IDs are unchanged.
- [ ] Canonical and #566 migration alias-package proofs are identical.
- [ ] World Graph, node aliases, `store.aliases`, assertion support, contribution authority, evidence, source artifacts, identity authority, #566 manifest, and predecessor fixtures are byte/digest unchanged.
- [ ] No DungeonMind repository change exists.
- [ ] No adoption transaction, Postgres adoption, authority switch, or identity replay exists.
- [ ] The next recommendation is derived from the refreshed blocker ledger.
- [ ] Case B is not selected while any `adoption_package_construction` blocker remains.
- [ ] New successor fixture reproduces deterministically.
- [ ] No path outside §4 or the bounded test discovery exception changed.
- [ ] Every required §7 proof has an exact result/provenance or an explicit waiver.
- [ ] The named successor remains unimplemented and unclaimed.

---

## Stop conditions

Stop and report rather than expanding if implementation discovers:

- predecessor `EVIDENCE_PROVENANCE` is not exactly 8;
- the exact eight blocker IDs cannot be captured losslessly;
- any substantive current alias has no direct current-node source assertion;
- provenance exists only through a merged-away identity or redirect;
- a source contribution is missing from revision-bound active membership;
- mutable contribution bytes disagree with the revision-bound source digest;
- `DurableAssertionSupport` disagrees with the exact contribution assertion provenance;
- evidence or source-artifact references are missing;
- an alias value is recoverable only by casefolding/normalizing an opaque lookup key;
- source and current-node metadata disagree in a way that creates two competing authorities;
- visibility, epistemic kind, canon state, campaign scope, session refs, or temporal semantics cannot be mapped without invention;
- a needed fictional-time assertion lacks an already-governed exact DungeonMind time-anchor mapping;
- a DungeonMind alias record fails the pinned contract;
- any residual remains after all direct source-authority forms are exhausted;
- clearing alias blockers requires a DungeonMind change;
- any relationship or identity-history behavior must change;
- any code path would mutate Buddy graph/source truth;
- the requested implementation needs a path outside §4;
- current `main` advances with semantic/product code after the dispatch base;
- the selector would authorize Case B while package-construction blockers remain.

Use this exact stop report shape:

```text
Stop condition:
Exact blocker element(s):
Exact alias value/key:
Current target node:
Source candidate assertion IDs:
Source contribution IDs:
Revision-bound digest status:
Support/evidence status:
Why direct source authority is insufficient:
Would identity-history traversal be required:
Would a new DungeonMind contract be required:
Invariant clause affected:
Required proof now missing:
Proposed successor or steward decision:
Tracker/state-authority update required:
```

---

## Final boundary

This slice is correct only if the transition is:

```text
current substantive Buddy alias
    ↓
exact current EVIDENCE_PROVENANCE blocker
    ↓
revision-bound active source assertion(s)
    ↓
exact per-contribution evidence/source lineage
    ↓
explicit metadata derivation
    ↓
DungeonMind AliasAssertionV4Record validation
    ↓
proof-gated in-memory classification
    ↓
EVIDENCE_PROVENANCE 8 → 0
```

It is incorrect if the transition becomes:

```text
alias string exists
    ↓
copy node evidence / use lookup key / follow merge redirect / choose defaults
    ↓
call it provenance
```

The first path constructs an adoption package.

The second path invents authority.

After this PR, remeasure and let the blocker ledger choose the next CUTOVER slice. Do not pre-authorize Case B.
