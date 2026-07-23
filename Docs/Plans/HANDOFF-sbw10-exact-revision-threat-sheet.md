# HANDOFF — SBW10 Exact-revision Threat Sheet and full statblock view

**Created:** 2026-07-22  
**Status:** PRE-DESIGNED — dispatch after `SBW09` merges; re-anchor graph projection, Server read, and shared renderer paths.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw10-exact-revision-threat-sheet.md`  
**Workstream:** `SBW10`  
**Repository:** `Drakosfire/DungeonMindBuddy`

> Dispatch one read-projection capability: opening a graph Threat resolves and renders the exact selected statblock revision through the existing backend boundary and shared renderer. Do not edit, append, embed, upgrade, mutate combat, or generate media.

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Durable contract? | Surface changed? | Decision |
|---|---:|---:|---:|---|
| Resolve graph Threat binding to exact Server revision | No alone; required projection input | No | No | Include |
| Compose Threat identity + exact mechanics in one Threat Sheet | Yes | No | Yes | Include |
| Provide summary/full renderer host policies | No; same projection family | No | Yes | Include |
| Edit accepted mechanics | Yes | Yes | Yes | Successor `SBW13` |
| Embed in Plan document | Yes | Yes | Yes | Successor `SBW12` |
| Add to combat | Yes | Yes | Yes | Successor `SBW15` |
| Generate/select media | Yes | Yes | Yes | Successors `SBW16–17` |

**Selected capability:** a user can open a published Threat and inspect its exact pinned mechanics as one composed projection.

## §1 Mission

A GM can open a World Graph Threat and view its exact selected statblock revision so campaign identity and immutable mechanics are usable together without collapsing their ownership.

**Invariant**

```text
Every displayed mechanic is traceable to the exact (statblock_id, revision_id, definition_digest) named by the selected binding; no latest, label, corpus path, or cached unrelated candidate may substitute.
```

**Mission falsification test**

```text
This is not one slice if implementation must also edit/save mechanics, create a document node, update a binding, add a combatant, or generate/select media.
```

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | Integration design §§3, 8–9; tracker `SBW10`; Plan projection registry/graph-aware resolver authority |
| Repository rules | `AGENTS.md`; one registry/one adaptive container; server-owned credentials |
| Base revision | Actual merged SHA containing `SBW04`, `SBW08–09`, and exact-read client |
| Predecessor contract | Published Threat/resource/binding graph views; exact Server revision read; shared semantic renderer |
| Exact input consumed | Exact graph node ID and selected typed binding from one graph revision |
| Named successor | `SBW12` pinned embed, `SBW13` revision append, `SBW15` combat |
| What remains false | View is read-only; no use or binding changes occur |
| Explicit non-goals | Editor, append/save, preferred/latest resolver, document serialization, combat, image generation, generic content redesign |

Read in order:

1. integration design §§8–9
2. tracker `SBW10`
3. merged `SBW08` projection types
4. merged `SBW09` publication/verification contract
5. merged `SBW04` renderer
6. current Plan graph-reference resolver/projection registry/container
7. merged `SBW01` exact revision backend client and route conventions
8. predecessor `StatblockViewModule` for demolition inventory only

## §3 Observable-path inventory

| Path | Current | Required | Same invariant? | Owner |
|---|---|---|---:|---|
| Open Threat from graph card/chip | Shows graph identity/details only | Resolve selected binding and open Threat Sheet | Yes | graph resolver/projection |
| Load exact revision | No graph→Server composition | Buddy backend reads exact IDs | Yes | resolver service/route |
| Full view | Legacy corpus/generated artifact view | Shared semantic renderer + Threat lore/context | Yes | Threat Sheet component |
| Summary view | Generic graph card | Compact mechanics digest from same exact revision | Yes | view model/renderer |
| Same statblock bound to two Threats | Not composed | Distinct Threat identity/lore, same exact mechanics | Yes | composition |
| Multiple bindings | Not resolved | Explicit selected/default primary policy; ambiguity shown, never first-win | Yes | resolver/UI |
| Server unavailable | Mechanics view may fail entirely | Preserve Threat identity and exact locator; mechanics unavailable state | Yes | resolver/UI |
| Revision missing/digest mismatch | Undefined | Honest integrity state; no latest fallback | Yes | service/UI |
| Graph revision reload | Potentially current-head only | Same graph revision/binding resolves same exact mechanics | Yes | graph/projection |
| Legacy artifact/corpus view | Active predecessor | Removed for named normal consumer when replacement is complete | Yes | demolition |

## §4 Files in scope — allowlist

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live_control_server/models/threat_sheet.py` | Strict composed read response and failure states |
| Create | `apps/live_control_server/services/threat_sheet_projection.py` | Graph binding → exact Server read composition |
| Create/Modify | narrow Threat Sheet read route | Browser-safe exact projection API |
| Modify | merged DungeonMind client only if exact read method/view requires extension | Typed read |
| Create | `tests/test_threat_sheet_projection.py` | exact/multiple/unavailable/mismatch proof |
| Create | `tests/test_threat_sheet_routes.py` | route contract proof |
| Create | `apps/live-control-ui/src/statblocks/threat/ThreatSheet.tsx` | Composed summary/full projection |
| Create | `apps/live-control-ui/src/statblocks/threat/ThreatSheet.test.tsx` | UI state/identity proof |
| Create | `apps/live-control-ui/src/statblocks/threat/threatSheetViewModel.ts` | Derived composition only |
| Modify | `apps/live-control-ui/src/api/types.ts` | Threat Sheet response types |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | exact projection read function |
| Modify | `apps/live-control-ui/src/api/liveApi.test.ts` | mapping/error proof |
| Modify | current graph reference resolver/projection registry files | open Threat Sheet from graph node/card |
| Modify | focused graph projection/component tests | navigation proof |
| Delete/Modify | exact legacy `StatblockViewModule`/artifact route consumer replaced by this path | demolition when no named consumer remains |

### Bounded discovery exception

```text
Directory: apps/live_control_server/services/, apps/live-control-ui/src/graph*, apps/live-control-ui/src/surface/, apps/live-control-ui/src/statblocks/
Maximum additional paths: 7
Allowed path kinds: exact graph projection reader, projection registry entry, selected-object card action, legacy direct consumer deletion, focused tests
Decision rule: include only to open the one Threat Sheet through the existing shared projection system
Required report: name every retained legacy artifact/corpus view consumer and deletion owner
```

## §5 Explicitly out of scope

| Capability | Why excluded |
|---|---|
| edit/fork accepted revision | `SBW13` |
| update selected binding or placement | `SBW14` |
| Plan Markdown/Tiptap node | `SBW12` |
| committed Plan document hydration | `SBW11` |
| combat insertion | `SBW15` |
| image generation/selection | `SBW16–17` |
| campaign-preferred automatic latest | prohibited for pinned binding; later explicit policy only |
| generic content projection redesign | reuse current registry/container |
| direct browser DungeonMind call | credentials remain backend-only |

## §6 Implementation contract

```text
Input:
  campaign/world graph revision context
  exact threat_node_id
  optional exact binding_id when multiple bindings exist

Output:
  ThreatSheetProjectionV1:
    threat identity/lore/view metadata
    exact binding metadata
    exact external resource locator
    exact StatblockRevisionResourceV1 or typed unavailable/integrity state
    optional selected media refs already present (display only; no selection workflow)

Invariant:
  mechanics match the binding's exact revision/digest

Failure behavior:
  threat missing/denied -> ordinary unresolved/authorization state
  no binding -> Threat identity view with no mechanics state
  multiple bindings without deterministic primary/explicit selection -> selection-required state
  external resource/binding mismatch -> integrity failure
  Server unavailable -> retain Threat/binding locator, mechanics unavailable
  exact revision 404 -> missing exact revision; no latest fallback
  digest mismatch -> integrity failure; do not render mechanics as trusted
  malformed Server response -> fail closed

Replay / idempotency:
  same graph revision + node + binding -> deterministic exact projection
  current graph head changes -> caller must explicitly resolve new graph projection; existing exact projection remains attributable
  retry unavailable exact read -> safe

Trust boundary:
  Verifies: graph binding/resource agreement, exact Server IDs/digest, visibility/admissibility from graph projection
  Records/displays without proving: lore truth beyond graph authority, mechanical balance
  Rejects: display-name lookup, arbitrary URL, latest selection, corpus path fallback
```

### Binding selection decisions

- If exactly one active `role=primary` binding exists, select it.
- If caller provides exact `binding_id`, require it belong to the Threat in the requested graph revision.
- If zero primary and exactly one active binding exists, the product may show it only if the design explicitly approves that deterministic fallback; otherwise return selection-required. Re-anchor this decision before dispatch.
- Multiple equally eligible bindings never use first list order.
- Phase/variant bindings are visible but not silently selected as primary.

### §6A State and fallback matrix

| Path | Loading | Success | Ordinary miss | Dependency unavailable | Integrity failure | Stale | Retry |
|---|---|---|---|---|---|---|---|
| Graph Threat read | graph projection load | identity + bindings | threat/no binding state | graph unavailable blocks | malformed typed state fails | requested revision exact | safe |
| Binding selection | evaluate exact IDs/roles | exact binding | selection required | N/A | mismatch fails | binding superseded in newer graph does not rebind exact view | explicit new selection |
| Server revision read | skeleton mechanics | exact revision/digest | 404 exact missing | mechanics unavailable; Threat retained | digest/schema mismatch fail | no latest | safe |
| UI render | identity first | summary/full shared renderer | no mechanics state | unavailable panel | integrity panel | graph revision disclosed | reopen/retry |

No fallback to candidate cache, legacy artifact, corpus Markdown, another revision, or display name.

### §6B Identity matrix

| Situation | Rule | Ambiguity | Fallback? | Consequence |
|---|---|---|---|---|
| Threat | exact graph node ID in exact graph revision | none | No | lore/context owner |
| Binding | exact binding ID or deterministic approved primary rule | multiple eligible = selection required | No first-win | selected mechanics relation |
| Resource | exact external resource node/provider/statblock ID | mismatch fails | No | Server logical ID |
| Revision | exact selected revision ID | none | No latest | immutable mechanics |
| Digest | exact binding vs Server equality | mismatch integrity failure | No | trusted render gate |
| Label/name | display only | duplicates allowed | No | never resolution |
| Graph update | newer graph may select another revision | old exact view remains stable | No automatic rebind | caller chooses new projection |

### §6C Persistence and replay matrix

Not applicable to new durable data — Threat Sheet is a derived read projection. Existing graph and Server records remain authorities. UI may cache only locators/transient view state under current projection rules, never mechanics as a new authority.

### §6D Predecessor-to-consumer mapping

**Grounding source:** `SBW08` graph node/relationship views and Server `StatblockRevisionResourceV1`.

Required mapping:

| Source | Threat Sheet field/behavior | Rule | Proof |
|---|---|---|---|
| graph Threat ID/label/kind/aliases/summary/visibility | identity/lore header | exact projection | graph fixture test |
| binding ID/statblock/revision/digest/role/policy | mechanics locator/badge | exact typed copy | composition test |
| external resource provider/resource ID | Server lookup identity | must agree | mismatch tests |
| Server revision definition | shared renderer input | exact digest match | fixture test |
| Server unavailable/error | typed mechanics state | safe bounded diagnostic | route/UI tests |
| optional media ref | display slot only | exact durable ref; no selection | fixture if available |

## §7 Verification ownership map

| Guarantee | Boundary | Command/scenario | Evidence |
|---|---|---|---|
| Exact binding→revision resolution | service | focused tests | exact client call IDs |
| Digest mismatch blocks trusted render | service/route/UI | mismatch fixture | integrity state |
| Two Threats share mechanics but retain lore | service/UI | fixture test | distinct identity, same revision |
| Multiple binding ambiguity not first-win | resolver | tests | selection-required |
| Server unavailable preserves Threat | route/UI | failure tests | identity/locator visible |
| Shared renderer used | component/diff | UI test | renderer receives revision definition |
| Graph navigation opens one shared projection | resolver/registry | component integration | Threat Sheet opens |
| Legacy exact consumer demolished | diff/tests | search/consumer inventory | no orphan path |

Required commands:

```bash
uv run pytest tests/test_threat_sheet_projection.py tests/test_threat_sheet_routes.py -q
cd apps/live-control-ui && npm test -- --run src/statblocks/threat/ThreatSheet.test.tsx <focused graph resolver/projection tests> src/api/liveApi.test.ts
cd apps/live-control-ui && npm run build
git diff --check
git diff --name-only <base>...HEAD
```

### Minimal live proof

Open a published Threat from Plan/graph projection, switch summary/full, reload, then simulate Server unavailable and exact revision missing. Prove the Threat remains visible and no latest/corpus fallback occurs. Also open a second Threat sharing the statblock.

## §8 Required handback

Include binding-selection policy, base/head, actual paths, commands/results/provenance, live exact IDs/digest and failure screenshots, demolition ledger, baseline failures/waivers, and confirmation that no edit/embed/upgrade/combat/media workflow ships.

## §9 Acceptance rubric

- [ ] Exact graph node/binding/resource/revision identity is used.
- [ ] Digest equality gates trusted mechanics rendering.
- [ ] Multiple binding ambiguity never first-wins.
- [ ] Same mechanics can compose with distinct Threat identities.
- [ ] Server failure preserves identity and locator honestly.
- [ ] Shared renderer powers summary/full view.
- [ ] No latest, label, corpus, candidate-cache, or direct browser Server fallback exists.
- [ ] No edit, embed, upgrade, combat, or media workflow ships.

## §10 Reviewer protocol

Trace identity from graph revision to exact Server call and renderer. Test multiple bindings and mismatches. Search for `latest`, label/name matching, corpus/artifact path reads, candidate cache fallback, direct Server URLs, and copied renderer implementations.

## §11 Re-review protocol

Rerun exact, multiple-binding, shared-mechanics, unavailable, 404, digest-mismatch, graph-revision, and navigation tests after every fix.

## Stop conditions

Stop if:

- graph projection cannot expose typed binding/resource state;
- exact Server read requires browser credentials;
- binding selection policy is unresolved;
- renderer cannot accept exact revision definition;
- legacy consumer deletion reveals a named active use requiring separate migration;
- a path outside the bounded allowlist is required.

## Final dispatch check

- [ ] Re-anchor after `SBW09`.
- [ ] Resolve binding selection policy explicitly.
- [ ] Inventory legacy view consumers.
- [ ] Confirm all write/embed/runtime/media successors remain false.
