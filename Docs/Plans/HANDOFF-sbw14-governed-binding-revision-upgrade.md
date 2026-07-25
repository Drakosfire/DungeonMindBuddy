# HANDOFF — SBW14 Governed Threat-binding revision upgrade

**Created:** 2026-07-22  
**Status:** PRE-DESIGNED — dispatch after `SBW13` and current graph replacement/supersession semantics are stable; re-anchor base and exact graph contract.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw14-governed-binding-revision-upgrade.md`  
**Workstream:** `SBW14`  
**Repository:** `Drakosfire/DungeonMindBuddy`

> Dispatch one capability: replace one selected Threat’s pinned statblock binding with one exact new revision through governed graph review. Do not update Plan embeds, placements, other Threats, or active combatants.

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Durable contract? | Surface changed? | Decision |
|---|---:|---:|---:|---|
| Upgrade one exact Threat binding to a child revision | Yes | Yes | Yes | Include |
| Show parent/child comparison before review | No; predecessor reuse | No | Yes | Include as read-only context |
| Upgrade all bindings using the logical statblock | Yes | Yes | Yes | Exclude |
| Upgrade Plan embeds/placements | Yes | Yes | Yes | Separate later capability |
| Upgrade active combatants | Yes | Yes | Yes | Prohibited |
| Set automatic latest/campaign preferred | Yes | Yes | Yes | Exclude |

**Selected capability:** the GM can intentionally select one Threat binding and replace its pinned revision with one exact child revision after reviewing the graph effect.

## §1 Mission

A GM can upgrade one published Threat’s exact statblock binding to a chosen immutable revision so the Threat adopts new mechanics without rebasing any other use.

**Invariant**

```text
One governed confirmation changes one exact binding from one exact revision/digest to one exact revision/digest; every other binding, embed, placement, and combatant remains byte-semantically unchanged.
```

**Mission falsification test**

```text
This is not one slice if implementation must also migrate documents, placements, other Threats, campaign-wide preferred state, or combat runtime.
```

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | Integration design §11; Campaign Supergraph governed write rules; `SBW08–09` binding/publication; `SBW13` append/compare |
| Repository rules | `AGENTS.md`; graph preview/confirm; immutable revision ownership; external-agent PR loop |
| Base revision | Actual merged SHA containing `SBW09–10` and `SBW13` |
| Predecessor contract | Exact current binding in graph revision; exact child revision/digest; parent/child compare; graph assertion replacement/supersession semantics |
| Exact input consumed | Threat node ID, binding ID, expected current revision/digest, selected new revision/digest, expected graph parent/token |
| Named successor | Optional future Plan embed/placement upgrade capability |
| What remains false | No other use moves; no automatic preferred/latest state |
| Explicit non-goals | bulk migration, embed/placement update, combat update, branch merge, media, direct graph write |

Read in order:

1. Campaign Supergraph architecture and current contribution replacement/supersession contracts
2. integration design §11
3. merged `SBW08–10` binding/publication/Threat Sheet contracts
4. merged `SBW13` child revision/compare
5. current graph authoring prepare/confirm/verification implementation and tests

## §3 Observable-path inventory

| Path | Current | Required | Same invariant? | Owner |
|---|---|---|---:|---|
| Start upgrade from Threat Sheet/compare | No adoption workflow | Load exact current binding and selected child | Yes | UI/service |
| Verify child lineage/compatibility | Child exists but may not belong to statblock | Require same logical statblock; exact IDs/digests | Yes | service |
| Prepare graph effect | General graph authoring | Preview old binding supersession + new exact binding | Yes | graph prepare/service |
| Review | No statblock-specific delta | Show current/new IDs/digests and compare summary | Yes | review UI |
| Confirm | Existing graph commit | Proposal-bound exact replacement | Yes | graph commit |
| Stale current binding/graph parent | Undefined product UX | Reject/reload/reprepare | Yes | service/UI |
| Duplicate confirm | Existing semantics | Idempotent; one active selected binding | Yes | graph/verification |
| Verify | No upgrade proof | Exact committed revision has new active binding and old superseded/inactive according to Kernel semantics | Yes | graph read |
| Other Threat binding | Could share same statblock | Unchanged | Yes | non-mutation proof |
| Plan embed/placement/combat | Pinned current/other revision | Unchanged | Yes | non-mutation proof |

## §4 Files in scope — allowlist

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live_control_server/models/statblock_binding_upgrade.py` | strict prepare/confirm/receipt view models |
| Create | `apps/live_control_server/services/statblock_binding_upgrade.py` | exact current/new validation and graph proposal mapping |
| Create/Modify | narrow binding-upgrade routes | prepare/confirm/verify APIs |
| Modify | `apps/live_control_server/services/threat_draft_store.py` only if workflow audit pointer is stored | optional non-authoritative history pointer |
| Create | `tests/test_statblock_binding_upgrade.py` | stale/idempotency/non-mutation proof |
| Create | route tests | API proof |
| Modify | `apps/live-control-ui/src/api/types.ts`, `liveApi.ts`, `liveApi.test.ts` | upgrade API |
| Modify | `apps/live-control-ui/src/statblocks/threat/ThreatSheet.tsx` | launch upgrade and show status |
| Modify | `apps/live-control-ui/src/statblocks/revisions/StatblockRevisionCompare.tsx` | “adopt for this Threat” action only |
| Modify | focused Threat Sheet/compare/Graph Review tests | user path proof |
| Modify | exact existing Graph Review typed effect renderer if needed | show binding replacement through normal review |

### Bounded discovery exception

```text
Directory: apps/live_control_server/services/, apps/live-control-ui/src/graph*, apps/live-control-ui/src/statblocks/
Maximum additional paths: 7
Allowed path kinds: exact graph replacement mapper, current-binding reader, review effect adapter, focused tests
Decision rule: include only to update one exact binding through existing governed graph paths
Required report: provide before/after graph fixture and non-mutation inventory for every sibling use
```

## §5 Explicitly out of scope

| Capability | Why excluded |
|---|---|
| bulk/campaign-wide adoption | separate capability and risk |
| `campaign_preferred` automatic resolution | no automatic latest |
| Plan embed or placement rewrite | independent durable document/plan operations |
| active combatant revision upgrade | unsafe runtime mutation; prohibited |
| other Threat bindings sharing statblock | must remain pinned |
| creating new mechanics revision | `SBW13` |
| direct graph store mutation | governed write only |
| media selection/regeneration | separate workstream |

## §6 Implementation contract

```text
BindingUpgradePrepareRequestV1:
  threat_node_id
  binding_id
  expected_current_statblock_id
  expected_current_revision_id
  expected_current_definition_digest
  selected_new_revision_id
  selected_new_definition_digest
  expected_graph_parent/current token
  operator note
```

Validation:

- Read current binding from exact graph revision/current authority.
- Require binding belongs to exact Threat.
- Require logical `statblock_id` unchanged.
- Exact-read selected new revision and require digest equality.
- If lineage/parent metadata is available, show it; do not require direct-child status unless product policy explicitly chooses that constraint. Re-anchor before dispatch.
- Build one supersession/replacement effect under active graph semantics. Do not create a second active primary binding accidentally.

```text
Input:
  exact current binding + exact selected revision + current graph authority

Output:
  no-write preview, proposal-bound confirmation, exact committed revision verification

Invariant:
  only one binding changes; all sibling uses remain unchanged

Failure behavior:
  current binding missing/mismatch -> stale conflict
  selected revision missing/digest mismatch/different logical statblock -> block
  prepare diagnostics/zero effect -> no confirm
  graph parent/token stale -> reject/reprepare
  commit success + UI/draft state failure -> graph remains authority; reconcile exact committed revision
  verification mismatch/multiple active primaries -> integrity failure/operator review

Replay / idempotency:
  same exact replacement confirm -> one resulting active binding state
  already-upgraded current state -> idempotent success or explicit no-op preview under graph policy
  changed selected revision -> new preview/review
  retry after stale -> reload current binding and reprepare

Trust boundary:
  Verifies: exact Threat/binding/current/new IDs/digests, same logical statblock, graph tokens/effects
  Records without proving: whether the new mechanics are creatively preferable
  Rejects: latest/name lookup, bulk selection, hidden consumer migration
```

### Commit model

```text
Commit point: governed graph commit records replacement/supersession and new active binding.
Before commit: all uses remain current.
After commit: this Threat binding resolves new revision; every other use remains pinned.
Truthful post-commit failure: graph may be upgraded even if UI receipt update fails; verify exact graph revision.
Recovery: read current binding and committed revision, then reconcile UI/audit pointer.
```

### §6A State and fallback matrix

| Path | Loading | Success | Miss | Dependency unavailable | Integrity failure | Stale | Retry |
|---|---|---|---|---|---|---|---|
| Load current/new | exact reads | validated pair | 404 blocks | graph/Server unavailable blocks | digest/statblock mismatch | current changed | safe reload |
| Prepare | no-write | one replacement effect | no-op/already upgraded explicit | unavailable | multiple/invalid effects fail | token/parent stale | reprepare |
| Confirm | committing | receipt | N/A | typed failure | partial/mismatch per graph contract | stale rejects | idempotent/reconcile |
| Verify | exact revision read | one expected active binding | missing fails | committed_unverified | multiple active/wrong digest fails | exact immutable | retry |
| Sibling audit | fixture/store reads | all unchanged | N/A | N/A | any mutation fails PR | N/A | N/A |

### §6B Identity matrix

| Situation | Rule | Ambiguity | Fallback? | Consequence |
|---|---|---|---|---|
| Threat | exact graph node ID | none | No | scope of change |
| Binding | exact binding ID/current state | mismatch stale | No role-first fallback | replacement target |
| Logical statblock | exact same statblock ID | different ID rejected | No | mechanics family stable |
| Current/new revisions | exact IDs/digests | none | No latest | before/after |
| Proposal | exact digest/token/graph parent | changed effect new review | No | governed commit |
| Other uses | exact persisted refs | N/A | No migration | unchanged |

### §6C Persistence and replay matrix

| Operation | Representation | Round-trip | Replay | Compatibility | Reversion |
|---|---|---|---|---|---|
| Prepare | existing graph proposal/pending view | before/after exact refs | same state no-op/equivalent | uses graph contract | discard preview |
| Commit | immutable graph revision/assertion support/supersession | current binding exact | idempotent normal graph semantics | `SBW08` schema | later governed replacement back to old revision |
| Verify | exact projection | expected binding fields | safe repeat | projection version | N/A |
| Sibling uses | unchanged stores/docs/combat | exact refs remain | no operation | existing schemas | N/A |

### §6D Predecessor-to-consumer mapping

**Grounding source:** `SBW08` binding schema, current graph replacement/supersession contract, `SBW13` revision ref/compare.

| Source | Upgrade effect/behavior | Rule | Proof |
|---|---|---|---|
| current binding ID/statblock/revision/digest | expected old assertion/effect | exact copy | stale test |
| new revision ID/digest/statblock | replacement binding fields | exact same logical ID | mapping test |
| comparison summary | review context only | no mechanics copy into graph | UI test |
| graph token/proposal digest | confirm request | exact bound | mismatch test |
| committed revision/effects | verification | one expected active state | integration test |
| other binding/embed/combat refs | non-mutation | byte/exact equality | fixture tests |

## §7 Verification ownership map

| Guarantee | Boundary | Command/scenario | Evidence |
|---|---|---|---|
| Exact current/new pair required | service | mismatch/different statblock tests | blocked |
| Prepare one replacement only | graph mapper | fixture snapshot | exact effects |
| Stale/replay safe | graph service | token/current-state tests | reject/idempotent |
| Verify one active selected binding | graph projection | integration test | exact new revision/digest |
| Other uses unchanged | graph/document/combat fixtures | non-mutation tests | exact equality |
| No latest/bulk | diff/service | search + tests | absent |

Required commands:

```bash
uv run pytest tests/test_statblock_binding_upgrade.py <focused graph route/projection tests> -q
cd apps/live-control-ui && npm test -- --run <ThreatSheet/RevisionCompare/GraphReview tests> src/api/liveApi.test.ts
cd apps/live-control-ui && npm run build
git diff --check
git diff --name-only <base>...HEAD
```

### Minimal live proof

Append a child revision, open the current Threat binding, preview/confirm adoption for that Threat only, then reload exact graph state. Show another Threat and an existing Plan embed still use the prior revision. Simulate stale binding and duplicate confirm.

## §8 Required handback

Include exact graph replacement mapping, base/head, paths, commands/results/provenance, live before/after binding IDs/digests/revision, sibling non-mutation evidence, baseline failures/waivers, and confirmation that no bulk/embed/placement/combat/latest behavior ships.

## §9 Acceptance rubric

- [ ] One exact Threat binding is the complete mutation scope.
- [ ] Current and new revisions/digests/statblock identity are verified.
- [ ] Preview shows one governed replacement and writes nothing.
- [ ] Stale/replay/partial outcomes follow graph authority.
- [ ] Exact verification proves the new active binding.
- [ ] Other Threats, embeds, placements, and combatants remain unchanged.
- [ ] No latest, preferred, bulk migration, or direct graph write exists.

## §10 Reviewer protocol

Begin with the sibling non-mutation ledger. Audit replacement semantics, multiple-active risk, stale state, same logical statblock, and exact verification. Search for loops over uses, latest/preferred, document/combat writes, and direct store mutation.

## §11 Re-review protocol

Rerun exact-pair, different-statblock, no-op, stale, duplicate confirm, post-commit reconcile, multiple-active integrity, and all sibling non-mutation tests after every fix.

## Stop conditions

Stop if:

- graph replacement/supersession semantics cannot represent one active binding cleanly;
- current binding identity is not stable enough for exact targeting;
- adopting a revision necessarily rewrites all uses;
- graph verification cannot distinguish active/superseded bindings;
- a Plan/combat migration becomes required for this Threat to render correctly;
- a path outside the bounded allowlist is required.

## Final dispatch check

- [ ] Re-anchor active graph replacement semantics.
- [ ] Decide whether only direct child revisions are eligible; document explicitly.
- [ ] Prepare sibling non-mutation fixture inventory.
- [ ] Confirm all bulk/document/combat successors remain false.
