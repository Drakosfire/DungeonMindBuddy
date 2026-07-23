# HANDOFF — SBW09 Governed Threat + exact statblock binding publication

**Created:** 2026-07-22  
**Status:** PRE-DESIGNED — dispatch after `SBW07`, `SBW08`, and the current governed graph prepare/confirm path are merged and stable. Re-anchor the full proposal contract and base SHA.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw09-governed-threat-binding-publication.md`  
**Workstream:** `SBW09`  
**Repository:** `Drakosfire/DungeonMindBuddy`

> Dispatch one capability: prepare, review, confirm, and verify one Threat plus exact statblock binding through the existing governed graph write path. Do not build the Threat Sheet, Markdown embed, revision upgrade, combat, or media workflow.

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Durable contract? | Surface changed? | Decision |
|---|---:|---:|---:|---|
| Map a saved ThreatDraft + AcceptedMechanicsRef into graph proposals | No alone; required publication input | Yes | Yes | Include |
| Preview/review/confirm Threat + external resource + binding | Yes | Yes | Yes | Include |
| Recover mechanics-saved/graph-pending partial state | No; required truthful commit model | Yes | Yes | Include |
| Render composed Threat Sheet | Yes | No | Yes | Successor `SBW10` |
| Publish optional inferred relationships automatically | Yes | Yes | Yes | Exclude; explicit later proposal only |
| Hermes autonomous commit | Yes | Yes | Yes | Prohibited/out of scope |

**Selected capability:** the GM can publish a planned Threat and one exact immutable mechanics binding through normal graph review and later verify them at the committed graph revision.

**Why included rows share one invariant:** proposal preparation, human-bound confirmation, partial-state recovery, and verification are one governed publication transaction from the user's perspective; none is independently useful without the others.

## §1 Mission

A GM can review and confirm a planned Threat plus exact statblock binding into the World Graph so saved mechanics become campaign memory only through a stale-safe human-governed write.

**Invariant**

```text
Graph publication is a separate revision-bound commit after mechanics persistence; success requires verified Threat/resource/binding effects at the returned graph revision, while failed or stale publication leaves valid mechanics intact and recoverable.
```

**Mission falsification test**

```text
This is not one slice if it must also render the exact mechanics projection, edit accepted revisions, embed a document, add combatants, generate media, or let Hermes confirm a write.
```

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | Integration design §§7.2–8; authored-prep contribution contract; graph object authoring/Kernel authority; tracker `SBW09` |
| Repository rules | `AGENTS.md`; graph write confirmation rules; external-agent PR loop |
| Base revision | Actual merged SHA containing `SBW07`, `SBW08`, and current graph review/confirm contracts |
| Predecessor contract | `ThreatDraftV1`, `AcceptedMechanicsRefV1`, typed external resource/binding graph contract, graph prepare/commit tokens and immutable revision verification |
| Exact input consumed | Exact draft version/state, accepted mechanics ref, selected existing/new Threat identity decision, current graph parent/revision, review selections |
| Named successor | `SBW10` exact-revision Threat Sheet |
| What remains false | No mechanics projection, embed, revision upgrade, combat, or media selection exists |
| Explicit non-goals | autonomous agent commit, inferred relation batch, direct graph-file mutation, Server mechanics changes, broad Graph Review redesign |

Read in order:

1. Campaign Supergraph architecture and current authored-write contract
2. integration design §§7–8
3. tracker `SBW09`
4. merged `SBW07` accepted mechanics/partial state
5. merged `SBW08` node/binding assertion contract
6. current graph authoring prepare/commit services/routes/UI and existing-object resolution
7. immutable graph revision projection/read verification APIs

## §3 Observable-path inventory

| Path | Current | Required | Same invariant? | Owner |
|---|---|---|---:|---|
| Start publication from mechanics-saved draft | No joined workflow | Load exact draft/ref and current graph head | Yes | orchestration/UI |
| Resolve existing Threat | General graph authoring may support object linking | Explicit exact/unique resolution; user decides create vs bind existing | Yes | resolver/review UI |
| Prepare new Threat + resource + binding | Not productized | Build proposal-bound effects; write nothing | Yes | publication service/graph prepare |
| Review effects | General graph authoring UI | Show exact node/resource/binding fields and visibility/lifecycle | Yes | review UI |
| Confirm | Existing tokens | Confirm only the reviewed proposal against current parent/token | Yes | graph commit |
| Stale graph parent/token | Existing stale handling | Reject, retain mechanics, rebuild preview | Yes | commit/service/UI |
| Duplicate confirm/retry | Existing idempotency varies | Exact replay safe; no duplicate Threat/resource/binding | Yes | graph commit/service |
| Existing Threat selected | Risk duplicate node | Bind to exact existing node; resource reused by ID | Yes | proposal mapper |
| New Threat defaults | Not statblock-specific | planned, plan epistemic kind, GM visible, campaign scoped | Yes | mapper/review |
| Graph commit fails after mechanics saved | No joined partial state | `publication_failed`/pending record with recovery | Yes | draft/publication store |
| Commit response then verification unavailable | Could overclaim | Mark committed receipt pending verification; do not say verified | Yes | orchestration/UI |
| Verify/reload | No product proof | Read exact returned graph revision and prove node/edge | Yes | projection/read service |

## §4 Files in scope — allowlist

Re-anchor exact paths to merged graph review implementation.

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live_control_server/models/threat_publication.py` | Strict publication/pending/receipt view models |
| Create | `apps/live_control_server/services/threat_statblock_publication.py` | Draft/ref → graph proposal mapping, prepare/commit/reconcile/verify |
| Modify | `apps/live_control_server/services/threat_draft_store.py` | Atomic pending publication/workflow state record |
| Create/Modify | narrow statblock publication route module | Browser-safe prepare/confirm/retry/verify endpoints |
| Modify | `apps/live_control_server/main.py` | Mount router if new |
| Create | `tests/test_threat_statblock_publication.py` | mapping, stale, partial, idempotency, verification proof |
| Create | `tests/test_threat_statblock_publication_routes.py` | route contract proof |
| Modify | `apps/live-control-ui/src/api/types.ts` | prepare/confirm/pending/receipt view types |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | publication API calls |
| Modify | `apps/live-control-ui/src/api/liveApi.test.ts` | request/error mapping |
| Modify | `apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx` or existing Graph Review projection integration seam | launch/review/status UX without duplicating Graph Review |
| Modify | focused existing graph authoring/review components only if required to display typed binding effect | reuse normal review/confirm path |
| Modify | focused workbench/graph review tests | user path proof |

### Bounded discovery exception

```text
Directory: apps/live_control_server/services/, apps/live_control_server/routes/, apps/live-control-ui/src/graph*, apps/live-control-ui/src/surface/
Maximum additional paths: 8
Allowed path kinds: exact current graph prepare/commit adapter, existing-object resolver, typed review item renderer, immutable revision read/projection client, focused tests
Decision rule: include only to reuse the existing governed write/review path; no statblock-only graph writer or new review cockpit
Required report: list existing graph APIs reused and every path intentionally not forked
```

## §5 Explicitly out of scope

| Capability/path | Why excluded |
|---|---|
| Direct `UnionSupergraphStore` file writes | must use governed graph contribution/Kernel path |
| full Threat Sheet/statblock rendering | `SBW10` |
| Markdown/Tiptap | `SBW11–12` |
| append/compare/upgrade revision | `SBW13–14` |
| combat | `SBW15` |
| images/media | `SBW16–17` |
| Hermes confirm/commit tool | agent may draft/propose only under separate governed tool contract |
| inferred faction/scene relationships not explicitly reviewed | separate proposals; not required for binding publication |
| deleting Server mechanics after graph failure | prohibited |
| broad Graph Review redesign | reuse existing surface/contracts |

## §6 Implementation contract

### Publication input

```text
ThreatPublicationPrepareRequestV1:
  draft_id
  expected_draft_version/workflow token
  accepted_mechanics_ref (or loaded exact from draft)
  graph_parent_revision / current overlay token as required
  threat_identity_choice:
    create_new { proposed stable ID/label/kind/role/aliases/summary }
    | existing { exact node_id }
  binding_role
  visibility/lifecycle defaults and explicit overrides allowed by policy
  operator note
```

### Proposed graph effects

```text
1. Threat node assertion OR exact existing-node reference
2. External DungeonMind statblock resource node assertion if absent
3. Threat --uses_statblock--> resource binding assertion with exact revision/digest
4. Existing governed provenance, campaign scope, visibility, epistemic, lifecycle metadata
```

### Pending publication record

```text
PendingThreatPublicationV1:
  publication_id
  draft_id + draft_version
  accepted_mechanics_ref
  expected_parent_graph_revision/current overlay token
  proposal identity/version/digest
  proposed effect summary
  confirmation token metadata safe to persist under current graph rules
  status: prepared | stale | committed_unverified | committed | failed
  commit receipt/revision?
  last_error?
```

```text
Input:
  exact mechanics-saved draft + identity choice + current graph authority state

Output:
  prepared no-write review payload, then proposal-bound confirmation receipt,
  then exact revision verification and published draft state

Invariant:
  only reviewed exact effects commit; mechanics remain independent and valid on failure

Failure behavior:
  draft/ref mismatch or unsaved mechanics -> reject before graph prepare
  existing identity ambiguous/not found -> block for user resolution
  prepare diagnostics/errors -> no write
  zero/unreviewed effects -> no confirm
  stale graph parent/overlay/token/proposal digest -> reject; mark stale and rebuild
  commit partial/failure -> follow normal graph commit truth; never fabricate atomicity beyond owning Kernel
  commit success + verification unavailable -> committed_unverified, retain receipt/revision
  verification mismatch -> integrity failure requiring operator review; do not delete mechanics

Replay / idempotency:
  same prepared proposal/confirm token under valid state -> normal graph idempotent replay
  changed draft/ref/identity/effects -> new proposal digest and review
  duplicate confirm -> no duplicate semantic objects/edges
  retry after mechanics-saved publication failure -> rebuild against current graph state, reuse exact accepted mechanics ref

Trust boundary:
  Verifies: draft/ref/digest, graph parent/token, exact existing node identity, typed assertion contract, committed revision effects
  Records without proving: creative truth of Threat description beyond human review, Server resource existence beyond accepted ref
  Rejects: display-name-only identity, hidden inferred relationships, direct graph file paths, autonomous confirm
```

### Commit model

```text
Commit point: governed graph Kernel/authoring commit returns a committed revision/receipt according to current graph authority.
Before commit: prepared proposal writes nothing.
After commit: graph effects exist independently of UI verification availability.
Truthful post-commit failure: committed_unverified with exact receipt/revision; mechanics remain saved.
Recovery: read exact committed revision/projection; reconcile draft publication record.
```

### §6A State and fallback matrix

| Path | Loading | Success | Miss | Dependency unavailable | Integrity failure | Stale | Retry |
|---|---|---|---|---|---|---|---|
| Start/identity resolution | load draft/ref/current graph | exact create/existing choice | existing ID miss blocks | graph read unavailable blocks | ambiguity blocks | graph head changes → prepare fresh | safe |
| Prepare | no-write | review payload/token/digest | zero effects blocks | graph prepare unavailable | diagnostics fail closed | parent/token stale | rebuild |
| Confirm | committing | committed receipt | N/A | failure typed; current graph truth inspected | partial/integrity per graph contract | stale token/digest rejects | exact replay or rebuild |
| Verify | exact revision read | node/resource/binding proven | effect missing = integrity failure | committed_unverified | mismatch operator review | exact revision immutable | retry read |
| Draft state update | exact draft load | published + revision | draft missing = recoverable external commit | N/A | fail closed | stale draft → reconcile | idempotent receipt write |

No fallback to another graph revision, latest statblock revision, display name, corpus write, or direct store mutation.

### §6B Identity matrix

| Situation | Rule | Ambiguity | Fallback? | Persistence consequence |
|---|---|---|---|---|
| New Threat | stable proposed ID under current authoring policy | collision requires existing-object resolution | No first-win | committed node ID returned/verified |
| Existing Threat | exact graph node ID selected by user/resolver | ambiguous label blocks | Unique alias may only assist review, never final commit without exact ID | binding source |
| External resource | deterministic `external:dungeonmind:statblock:<id>` | mismatch rejects | No | reused endpoint |
| Binding | stable binding/assertion identity per `SBW08` | changed revision/digest distinct | No | exact edge |
| Mechanics | exact statblock/revision/digest | no latest | No | proposal input |
| Proposal | exact digest/token/current graph parent | changed effects require new review | No | pending record |
| Labels/aliases | display/resolution aids | collisions shown | No implicit identity | do not rebind persisted refs |

### §6C Persistence and replay matrix

| Operation | Representation | Round-trip | Duplicate/replay | Compatibility | Recovery |
|---|---|---|---|---|---|
| Prepare | `PendingThreatPublicationV1` + existing graph prepare result | proposal/effects/digest retained | same exact prepare may replace equivalent pending state | schema versioned | rebuild if stale |
| Commit | graph-authority immutable revision/overlay/event receipt | exact created IDs/revision | existing graph idempotency | no statblock-specific bypass | inspect current graph/receipt |
| Store published state | draft workflow + commit receipt/revision | exact mechanics/publication refs | same receipt idempotent | additive schema | reconcile from graph |
| Verify | exact graph revision projection/read | node/edge IDs and state equal | safe repeat | projection contract version | retry/unverified state |

### §6D Predecessor-to-consumer mapping

**Grounding source:** current graph authoring prepare/commit request/response/token vocabulary plus `SBW08` typed assertion contract.

The implementation PR must provide exact mapping, including:

| Source field/outcome | Graph proposal/consumer | Rule | Proof |
|---|---|---|---|
| draft name/description/kind/aliases | Threat object assertion | human-reviewed, planned/GM/campaign defaults | mapping fixture |
| accepted statblock/revision/digest | external resource + binding assertion | exact copy | fixture/test |
| existing Threat choice | exact object ref | no duplicate object | existing-node test |
| graph parent/current overlay token | prepare/commit request | exact current authority | stale test |
| prepare confirm/proposal digest | pending/confirm | proposal-bound | token mismatch test |
| commit created IDs/revision | published receipt/state | exact copy | reload test |
| diagnostics/partial outcomes | UI/pending state | preserve graph vocabulary | failure fixtures |

## §7 Verification ownership map

| Guarantee | Boundary | Command/scenario | Evidence |
|---|---|---|---|
| Prepare writes nothing | graph prepare integration | focused test | no graph/draft publish mutation except pending record as designed |
| Existing Threat avoids duplicate | mapper/graph integration | fixture test | exact node reused |
| New Threat defaults correct | mapper/review | snapshot/route test | planned/GM/campaign metadata visible |
| Confirm bound to reviewed proposal | graph commit | token/digest mutation tests | stale/mismatch rejected |
| Duplicate retry idempotent | graph/service | replay test | one node/resource/binding |
| Mechanics survive graph failure | service/store | failure injection | accepted ref unchanged/retry available |
| Exact committed revision verified | graph read/projection | end-to-end test | node/edge state proven |
| No direct graph writer/autonomous commit | diff/service | path/search + route tests | only existing governed APIs |

Required commands, re-anchored to actual graph tests:

```bash
uv run pytest tests/test_threat_statblock_publication.py tests/test_threat_statblock_publication_routes.py -q
uv run pytest <focused graph authoring prepare/commit/projection tests> -q
cd apps/live-control-ui && npm test -- --run <focused workbench/graph-review tests> src/api/liveApi.test.ts
cd apps/live-control-ui && npm run build
git diff --check
git diff --name-only <base>...HEAD
```

### Minimal live proof

Use an existing mechanics-saved draft and existing Graph Review/authoring surface. Prepare a new planned GM-visible Threat + binding, inspect exact effects, confirm, reload exact committed graph revision, and open graph details sufficient to verify the relationship metadata. Repeat with stale parent and existing Threat binding. Do not build the Threat Sheet.

## §8 Required handback

Include current graph API mapping, proposal fixture, base/head, paths, commands/results/provenance, live commit revision/created IDs, stale/existing/partial evidence, baseline failures/waivers, and confirmation that no Threat Sheet/embed/revision upgrade/combat/media/autonomous commit ships.

## §9 Acceptance rubric

- [ ] Only mechanics-saved exact refs can enter publication.
- [ ] Existing-object resolution is explicit and exact-ID final.
- [ ] Prepared effects show Threat/resource/binding and write nothing.
- [ ] New Threat defaults are planned, plan-kind, GM-visible, campaign-scoped.
- [ ] Confirmation is bound to reviewed effects and current graph authority.
- [ ] Stale/replay behavior is safe and proven.
- [ ] Graph failure leaves mechanics intact and recoverable.
- [ ] Exact committed revision proves the node and binding.
- [ ] No direct graph writer, autonomous confirm, projection view, embed, combat, or media ships.

## §10 Reviewer protocol

Start from the two commit points: Server mechanics already committed, graph commit now separate. Audit exact existing identity, proposal digest/token, stale handling, partial outcomes, metadata defaults, and verification. Search for direct store writes, display-name commit, latest revision, inferred relation batches, and rollback deletion.

## §11 Re-review protocol

Re-run new/existing Threat, zero-effect, stale token/parent, duplicate confirm, commit-success/draft-failure, verification unavailable/mismatch, and exact reload tests after every fix.

## Stop conditions

Stop if:

- current graph authoring prepare/commit cannot carry `SBW08` typed state;
- existing-object resolution cannot provide exact final node identity;
- graph commit semantics expose partial outcomes not representable truthfully by the pending record;
- committed revision cannot be read/projected for verification;
- publication requires changing mechanics or creating a statblock-specific graph writer;
- autonomous confirmation is the only available path;
- a path outside the bounded allowlist is required.

## Final dispatch check

- [ ] Re-anchor after `SBW07–08` and graph authoring changes.
- [ ] Capture exact prepare/commit/token/receipt vocabulary.
- [ ] Resolve actual Threat kind/role defaults against active graph ontology.
- [ ] Confirm `SBW10+` remain false.
