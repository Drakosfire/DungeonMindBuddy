---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: Playable Architecture Graduation / P3B
  - Flow: PLAY
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-PLAY-native-graph-object-sheet.md
  - Branch / PR: agent/play-native-graph-object-sheet / `PLAY: open native graph object sheets`

  ## Verification pointer
  - Design anchor: merged PR #603 / current main at `bc442717addb264073a68f7528929ec1aac51b2a`
  - P3A design anchor: `Docs/Plans/HANDOFF-PLAY-native-runbook-table-deck.md` at design commit `b47c66c6a780308ceb2d8720de2f3086aad33cfc`
  - Required predecessor before dispatch: Start Run dogfood bridge → Runbook briefing/instructions → live dogfood → re-anchor; P3A merged is not sufficient to dispatch P3B
  - Base/head: <PIN_AFTER_P3A_STATE_SYNC> / <implementation head>
  - Changed paths: must remain inside HANDOFF §4
  - Verification: HANDOFF §7 + roadmap review disposition

  The checked-in handoff, cumulative diff, nano-commit story, independently
  rerun evidence, and roadmap review disposition are the review contract.
  This body is transport metadata.
---

# HANDOFF — open native Play graph-object sheets from exact Runbook references

**Created:** 2026-08-16  
**Status:** DESIGNED — **NON-DISPATCHABLE.** P3A is merged, but current sequence is the Start Run dogfood bridge, then Runbook briefing/instructions, then live dogfood / re-anchor, before this P3B capability may be pinned.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-native-graph-object-sheet.md`  
**Conversation/workstream:** `Playable Architecture Graduation / P3B`  
**Flow / owner:** `PLAY`  
**Direction:** DESIGN → CODE → REVIEW  
**Design anchor:** merged PR #603 / `bc442717addb264073a68f7528929ec1aac51b2a`  
**P3A design anchor:** `b47c66c6a780308ceb2d8720de2f3086aad33cfc` on `documents/play-p3a-native-runbook-deck`  
**Required predecessor:** P3A — native Runbook table deck over exact P1/P2 authorities  
**Implementation base:** `PIN_AFTER_P3A_STATE_SYNC`  
**Suggested branch:** `agent/play-native-graph-object-sheet`  
**PR title:** `PLAY: open native graph object sheets`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

---

## Dispatch gate — P3A must be product truth first

At this design anchor, repository truth is:

```text
main: bc442717addb264073a68f7528929ec1aac51b2a
P2A: merged
P2B1: merged
P2B2: merged
P2C: designed, current next implementation slice
P3A: designed on documents/play-p3a-native-runbook-deck, not dispatchable yet
P3B: this design, successor only
```

P3A is now merged (PR #618). That does **not** make this file current dispatch authority. Product sequence after P3A is:

```text
Start Run from committed Runbook
        ↓
Play Runbook briefing / instructions
        ↓
real session dogfood
        ↓
re-anchor, then pin this P3B handoff
```

This handoff remains **NON-DISPATCHABLE** until that dogfood sequence has landed and a later re-anchor names P3B next.

Before P3B CODE dispatch, all of the following must be true:

1. P2C is implemented, merged, reviewed, and state-synchronized;
2. P3A's handoff is on `main`, pinned to its exact post-P2C base, implemented, merged, and reviewed;
3. the exact P3A implementation/evidence head, final reviewed head, merge SHA, and formal review-cycle count are known;
4. a guarded post-P3A state-authority sync marks P3A merged/historical;
5. Start Run → Runbook briefing/instructions → live dogfood have completed, and `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` then names P3B as the current next slice and this file as the next handoff;
6. this handoff is present on `main`;
7. every `PIN_AFTER_P3A_STATE_SYNC` is replaced on the implementation branch with that exact synchronized `main` SHA;
8. the implementation agent re-reads the merged P3A projection/admission/component seams, because those paths do not exist on this design anchor and their final names/shapes are predecessor authority.

Stop and re-brief instead of carrying this design forward by assumption if P3A materially changes:

- how the exact Runbook TipTap document is exposed to Play children;
- how the admitted Run/snapshot/manifest authority set is represented in UI state;
- how either admitted graph-native form (`graphNodeReference` from `dmb-node:` or `runbookReference` `graph-node` from `#dmb-ref:graph-node:`) renders inside the native deck;
- whether P3A canonicalizes one of those two representations away (pin that predecessor fact; do not assume dual-form if one is gone);
- how P3A Scene/Beat/Choice/Option `bodyDoc` slices are owned (Beat ends at the next root playable marker; Choice is a sibling body; Option nests under Choice);
- the Play surface publication/lease seam;
- the app-scoped Projection host integration;
- the exact workspace campaign/world scope available to Play.

---

## §1 Mission and merge-ready invariant

**Mission:** While running one exact admitted native Runbook in `/play`, a GM can click an exact `graph-node` reference and open a table-useful object sheet in the shared Projection host, inspect World identity/relationships and Source evidence plus truthful current-Runbook reference context, drill to related World objects without losing Play position, and close the sheet back to the same table moment — without campaign-specific bridge data or a new object truth store.

**Merge-ready invariant:**

> **Every native Play object sheet is a reconstructable projection over explicit existing authorities: (a) the exact P3A-admitted Run/Runbook snapshot supplies the Playable reference occurrences and current Run context; (b) one exact World Graph projection supplies object identity, accepted facts, relationships, evidence, campaign tenancy, and its exact world/campaign/scope/revision identity; (c) Source detail is opened only through existing evidence/source handles. Both admitted graph-native TipTap representations — `graphNodeReference { nodeId }` from `dmb-node:<id>` and `runbookReference { kind: ref, refType: graph-node, refId }` from `#dmb-ref:graph-node:<id>` — normalize to the same durable node ID and both participate in click/open and occurrence derivation. A graph-native reference resolves only by that durable node ID in the Run's admitted campaign/world scope — never by label, alias, first match, ambient/default campaign lens, corpus fallback, or #578 dictionaries. Occurrence membership comes from disjoint P3A body slices, not a walk that can carry Beat context into a later Choice/Option. Relationship drilling preserves the originating World Graph revision or fails closed. Opening/closing/drilling never mutates Run, Runbook, World, Source, Mechanics, or Combat. When richer object-attached Playable interpretation does not exist, the sheet truthfully degrades to World + Source + exact Runbook-occurrence context rather than inventing `At the table`, `Attitude`, `Offers`, `Rules now`, or copied source prose as a new durable contract.**

### Why this is the next P3 slice

P3A makes the Runbook itself native. It deliberately excludes graph-reference opening and generic object sheets so one PR is responsible only for exact Runbook projection + P2 Runtime controls.

P3B then turns one of those already-authored durable handles into a table interaction:

```text
exact bound Runbook
  → exact graph-node reference
  → exact Run campaign/world graph projection
  → shared Projection host
  → table-first object sheet
  → related object drill / source detail
  → close
  → exact same Play table position
```

This is the smallest independent successor that begins replacing #578's `ofConksPlayObjectBridge` without recreating it as a generic-looking second datastore.

### What #578 proved, and what P3B must not copy

PR #578 proved that a GM benefits from clicking NPC/location/item references and receiving a calm table-facing sheet with useful relationships and source detail.

Its implementation also made the architectural failure mode concrete:

```text
ofConksPlayObjectBridge
  nodeId -> {
    kind,
    atTable,
    attitude,
    offersHooks,
    rulesNow,
    connectedNow,
    sourceBlocks,
    provenance
  }
```

That object-body dictionary is campaign/adventure-specific projection scaffolding, not product authority.

P3B must not replace it with:

```text
genericPlayObjectBridge
playObjectBodies.json
npcSheetMetadata
object-attached projection cache
```

or any equivalent second truth store.

### The Playable contribution in P3B

The durable Playable authority available by P3B is the exact P3A-admitted Runbook. It already contains exact graph references within exact stable Scene/Beat/Choice/Option structure.

P3B may therefore derive, in memory only:

```text
PlayableGraphReferenceOccurrence {
  graphNodeId
  sourceNodeType            # graphNodeReference | runbookReference; diagnostic, not identity
  referenceLabel            # presentation only
  sceneId
  sceneTitle
  beatId?
  beatTitle?
  choiceId?
  choiceTitle?
  optionId?
  optionTitle?
  documentOrder
}
```

Exact field names may vary, but the derivation rules may not:

- node identity comes only from the normalized durable graph node ID of either admitted graph-native TipTap form (below);
- membership comes from disjoint P3A `bodyDoc` slices, not a second Markdown membership parser;
- titles are presentation only;
- all occurrences are retained in document order;
- if one World object is referenced multiple times, do **not** silently choose the first occurrence as canonical;
- the active Run's current Scene/Beat may be highlighted as context, but does not delete other occurrences;
- a relationship-drilled World object may have zero Runbook occurrences and still render truthfully as a World/Source object sheet.

This derived occurrence index is reconstructable projection data. It is never persisted.

### No invented object-attached Playable schema

The architecture permits object-attached Playable interpretation, and the product design describes useful labels such as `At the table`, `Attitude`, and `Offers & hooks`.

Current durable P1 contracts do **not** define a generic object-attached Playable block schema. Therefore P3B must not infer those fields from nearby prose, section names, graph neighbors, or #578 content.

Required degradation:

```text
rich object-attached Playable interpretation exists in a future admitted contract
  → future sheet may render it

no such durable interpretation exists now
  → identity + World summary + exact Runbook occurrence context
    + relevant World relationships + Source/evidence detail
```

This is explicitly supported by `DESIGN-play-surface-projection.md` §14: an object with no Playable interpretation remains a useful World/source-backed object sheet.

### Capability decomposition

| Candidate outcome | Independently useful? | Durable/public contract? | Decision |
|---|---:|---:|---|
| Make exact Runbook graph-native refs clickable in native Play | No; entry to same sheet capability | Existing `dmb-node:` and `#dmb-ref:graph-node:` identity | **Include** |
| Load World Graph for the admitted Run campaign/world | No; resolver prerequisite | Existing projection API | **Include** |
| Resolve `graph-node` by exact durable node ID | No; identity safety | Existing shared `graphReference` contract | **Include** |
| Derive all exact Runbook occurrences for a graph node | No; Playable context clause | Reconstructable local projection | **Include** |
| Render table-first generic object sheet in shared Projection host | Yes | Reconstructable UI projection | **Include** |
| Show World relationships and Source/evidence detail | No; same object-sheet capability | Existing projection/evidence contracts | **Include** |
| Drill related World objects while preserving origin graph revision | No; navigation safety clause | Existing graph revision authority | **Include** |
| Extract Plan's exact-scope relationship navigation into shared `graphReference` | No; safety helper used by two surfaces | Buddy-shared implementation seam | **Include — narrow hoist** |
| Add `play` presentation mode / neutral after-summary slot to shared GraphObjectCard | No; composition support | Shared presentation helper only | **Include if still needed at pinned base** |
| Corpus fallback for exact `graph-node` refs | Yes / alternate resolution policy | Existing legacy reference behavior | **Exclude / prohibited for graph-native refs** |
| Legacy `npc`/`location` label-based Runbook refs | Yes | Different resolution/fallback semantics | **Exclude — later compatibility slice if still needed** |
| Durable object-attached Playable fields | Yes | New Playable authoring/storage contract | **Exclude** |
| Threat-specific exact mechanics sheet | Yes | Mechanics projection | **Exclude — P3C** |
| Add to Combat | Yes | Combat mutation | **Exclude — P4** |
| Map/media/annotation projection | Yes | Asset/annotation authority | **Exclude** |
| Agent proposal/adoption | Yes | Shared mutation workflow | **Exclude — P5** |
| Generic `WorkObjectElementRef` / `WorkObjectRevisionRef` | Yes | Buddy-shared work-object contract | **Exclude — still not justified here** |
| DungeonMind/DungeonMindDnD contract | Yes | Cross-repository authority | **Prohibited** |

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes.** Click, open, relationship drill, source read, close, graph degradation, and Playable-context rendering are all read-only projections over exact existing authorities. |
| Most likely adversarial sequence | Run A opens object X at graph revision G1 → World Graph advances to G2 while sheet is open → GM clicks X→Y relationship → unsafe client resolves Y from ambient G2. Required: relationship drill uses G1 or fails closed; it never mixes X@G1 with Y@G2 invisibly. |
| Will §7 detect that failure? | Yes. A test opens X from G1, swaps the ambient/current projection to G2, clicks a relationship, and proves the resolver requests/uses pinned G1 before opening Y. |
| Easiest owning boundary to under-test | Dual graph-native chip forms and P3A slice membership. An implementation can wire only `runbookReference` and still look green, or walk “current Beat then current Choice” and mislabel Choice/Option refs with the previous Beat. Campaign/world admission remains the other easy miss: Play must derive graph scope from the admitted Run/Runbook rather than ambient UI selection. |
| Fact that forces stop/split | Need for new persistent object-attached Playable storage, new server projection schema, historical Runbook storage, graph writes, Threat mechanics special casing, Combat mutation, or a second app Projection host. |

---

## §2 Context, authority, and lane

### Parent authority — read in this order

1. `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`
   - §2 Core invariant;
   - §4.4 Object-attached Playable Material;
   - §7 Runtime State;
   - §8 Projection architecture;
   - §8.1 Play Object Sheet;
   - §11 Persistence and revision rules;
   - §12 Surface Interaction boundary;
   - §13 migration from #578.
2. `Docs/Design/DESIGN-play-surface-projection.md`
   - §0 product thesis;
   - §5 Play Object Sheets;
   - §6 Relevant-now connections;
   - §7 References are handles, not copied truth;
   - §10 Maps/media boundary;
   - §11 Source detail and Advanced;
   - §14 degradation behavior;
   - §15 acceptance stories.
3. `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`
   - Projection Pane host ownership;
   - graph lens/admissibility surface ownership;
   - chip reopen contract;
   - one-host rule;
   - stale surface lease behavior.
4. `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`
   - promotion test;
   - current sequence at dispatch time;
   - P3 Buddy-shared hoist candidates;
   - P4/P5 boundaries.
5. merged P3A handoff and implementation at the pinned base:
   - `Docs/Plans/HANDOFF-PLAY-native-runbook-table-deck.md`;
   - actual `playSurface/**` paths created by P3A;
   - exact P3A projection/admission tests.
6. shared graph/reference seams:
   - `apps/live-control-ui/src/graphReference/types.ts`;
   - `apps/live-control-ui/src/graphReference/resolveGraphReference.ts`;
   - `apps/live-control-ui/src/graphReference/ResolvedGraphObjectProjection.tsx`;
   - `apps/live-control-ui/src/graphReference/GraphNodeChipRuntime.tsx`;
   - `apps/live-control-ui/src/tiptap/extensions/GraphNodeReferenceNode.ts`;
   - `apps/live-control-ui/src/tiptap/extensions/GraphNodeReferenceView.tsx`;
   - `apps/live-control-ui/src/tiptap/extensions/RunbookReferenceNode.ts`;
   - `apps/live-control-ui/src/tiptap/extensions/RunbookReferenceView.tsx`;
   - `apps/live-control-ui/src/tiptap/references/runbookReferences.ts`.
7. graph-object projection seams:
   - `apps/live-control-ui/src/graphObjectCard/GraphObjectCard.tsx`;
   - `apps/live-control-ui/src/graphObjectCard/GraphObjectProjectionCard.tsx`;
   - `apps/live-control-ui/src/graphObjectCard/types.ts`.
8. exact graph projection/load seams:
   - `apps/live-control-ui/src/api/liveApi.ts` `postWorldGraphProjection`;
   - `apps/live-control-ui/src/api/types.ts` `WorldGraphProjection*`;
   - `apps/live-control-ui/src/worldGraph/worldGraphSurfaceContext.ts`;
   - `apps/live-control-ui/src/worldGraph/verifyWorldGraphProjectionResponse.ts`;
   - `apps/live-control-ui/src/graphLens/useWorldGraphLensProjection.ts`.
9. Plan as characterized existing consumer:
   - `apps/live-control-ui/src/planSurface/reference/usePlanGraphReferenceResolver.ts`;
   - `apps/live-control-ui/src/planSurface/reference/resolvePlanRelationshipTarget.ts`;
   - `apps/live-control-ui/src/planSurface/reference/PlanReferenceObjectCard.tsx`.
10. shared source navigation:
   - `apps/live-control-ui/src/sourceNavigation/sourceNavigation.ts`.
11. PR #578 **as mining evidence only**:
   - `PlayObjectSheetProjection.tsx`;
   - `ofConksPlayObjectBridge.ts`;
   - `PlayReferenceCapability.tsx`;
   - `buildPlayLocalGraphReference.ts`;
   - `buildPlaySurfaceInteractionPublication.ts`.

Do not import or copy #578 `ofConks*` contracts into product code.

### Current design-anchor observations

Current `main` already proves:

```text
two admitted graph-native Markdown/TipTap forms:
  [label](dmb-node:<id>) → graphNodeReference { nodeId, label }
  [label](#dmb-ref:graph-node:<id>) → runbookReference { kind: ref, refType: graph-node, refId, label }
both NodeViews publish the exact node ID through GraphNodeChipRuntime.onSelectNode
P3A does not canonicalize one form away
neutral resolveGraphReference exact graph-native semantics
GraphReferenceResolution carrying exact graphScope revision
neutral GraphObjectCard / ResolvedGraphObjectProjection
source evidence handles + shared source navigation
one shared ProjectionHost owned above surfaces
Plan exact-scope relationship navigation with pinned revision recovery
WorldGraphProjection revisionPin reads
```

Current `main` also contains transition debt relevant to P3B:

```text
App global graph lens has a default campaign
World ID helper currently has explicit known campaign mapping
LegacyProjectionHostAdapter is still temporary and recognizes native Build specially
Plan owns some exact-scope relationship navigation code that Play will also need
GraphObjectCard presentation modes currently reflect its existing consumers
```

P3B must consume/hoist the safe invariant, not copy the transition debt blindly.

### Lane table

| Field | Required content |
|---|---|
| Parent authority | Playable architecture + Play projection design + Surface Interaction architecture |
| Base revision | `PIN_AFTER_P3A_STATE_SYNC` |
| Design anchor | `bc442717addb264073a68f7528929ec1aac51b2a` — merge of PR #603 |
| Predecessor contract | merged P3A native Runbook table deck over exact P1/P2 authority set |
| Exact input consumed | P3A admitted Run + workspace Runbook snapshot/TipTap projection including both graph-native chip forms; normalized exact graph node ID; Run campaign/world scope; WorldGraphProjection; graph evidence/source handles |
| Output | reconstructable Play object sheet in existing shared Projection host; no new durable object record |
| Named successor | P3C — Threat sheet over exact accepted mechanics, still no Combat mutation |
| What remains false | no object-attached durable fields, no Threat mechanics specialization, no Add to Combat, no map/media, no proposal/editing, no non-graph-native compatibility fallback |
| Branch / isolated checkout | `agent/play-native-graph-object-sheet` in isolated worktree/equivalent |
| Parallel lanes / collision hotspots | merged P3A `playSurface/**`; `graphReference/**`; `graphObjectCard/**`; temporary Projection-host adapter; living roadmap; Plan resolver extraction |
| Runtime/state ownership | read-only projection; no Runtime writes; Run is context only; tests use static projection fixtures / mocked API |
| State-authority sync after merge | add P3B roadmap evidence row; if evidence holds, mark P3B merged and set P3C next; explicitly record whether narrow graphReference hoist occurred |

### Hoist posture — one narrow promotion is expected

P3B is the first slice in this sequence where a genuinely independent second surface needs one already-proven Plan invariant:

> A relationship opened from object X must resolve against X's exact originating World Graph scope/revision, not whatever graph projection happens to be current later.

That rule is already implemented in Plan-local resolver code. Play will need the same rule.

Therefore P3B should, if the pinned base still has this topology, extract only that behavior into the existing neutral `graphReference` layer and make **both Plan and Play** consume the neutral helper.

This is an evidence-driven Buddy-shared hoist and is consistent with the roadmap's P3 candidates.

It does **not** justify:

```text
WorkObjectRevisionRef
WorkObjectElementRef
generic Runtime state
generic transaction framework
DungeonMind kernel contract
```

Those remain false.

---

## §3 Observable paths and adversarial sequences

### A. Exact Play graph scope

P3B must not resolve a Runbook graph reference from the app's ambient/default graph lens.

At the pinned P3A base, derive the Play graph request from the admitted Run/Runbook authority set:

```text
campaignId = exact admitted Run campaign_id
worldId = exact admitted Runbook workspace record world_id when present
          else existing governed campaign→world mapping if available
scopeMode = campaign
focus = none
admissibility = gm
revisionPin = null for initial head read
```

Admission rules:

1. Run `campaign_id` and Runbook workspace `campaign_id` must already agree by P3A admission. If P3A does not prove this at the pinned base, stop/re-brief.
2. If workspace `world_id` is present and a governed campaign→world mapping also exists, they must agree or graph projection is blocked.
3. If workspace `world_id` is absent, existing governed campaign→world mapping may supply world identity.
4. If neither can establish world identity, the Runbook remains usable but graph references are unavailable with truthful copy. Do not guess Eldyrwild or use the app default.
5. Initial Play object open uses the current admitted World Graph head for that exact campaign/world and captures the returned exact `graphScope` revision in `GraphReferenceResolution`.

P3B does not bind the Run to a World Graph revision. World is a separate authority that may evolve. The exact revision rule applies to one opened object-sheet navigation chain so related objects are not silently mixed across revisions.

### B. Exact graph-node resolution

Current Markdown admits **two** durable graph-native representations. P3A does **not** canonicalize one away. Both remain in scope unless a later merged P3A pins an explicit collapse.

```text
[label](dmb-node:<id>)
  → TipTap graphNodeReference { nodeId, label }
  → GraphNodeReferenceView onSelectNode(nodeId)

[label](#dmb-ref:graph-node:<id>)
  → TipTap runbookReference { kind: "ref", refType: "graph-node", refId, label }
  → RunbookReferenceView onSelectNode(refId)
```

P3B defines one normalization seam over both TipTap node shapes. Exact helper name may vary; the contract may not:

```text
admitPlayGraphNodeRef(node) -> { graphNodeId } | reject

graphNodeReference:
  graphNodeId = node.attrs.nodeId if isValidGraphNodeId(nodeId)

runbookReference:
  graphNodeId = node.attrs.refId
    only when kind == "ref" and refType == "graph-node"
    and isValidGraphNodeId(refId)

all other TipTap nodes, corpus/action runbook refs, empty IDs, and label-only chips
  → reject; never enter click/open or occurrence derivation
```

After admission, resolution uses the existing shared contract with a `RunbookReferenceAttrs` view of the **normalized ID**, not of whichever chip happened to be clicked:

```text
resolveGraphReference({
  ref: {
    kind: "ref",
    refType: "graph-node",
    refId: graphNodeId,
    label: presentation-only
  },
  projection: exact Play WorldGraphProjection,
  projectionState
})
```

Required semantics:

- exact durable node ID only, identical for both source forms;
- click/open and “In this Runbook” derivation both consume `admitPlayGraphNodeRef`;
- `PlayGraphReferenceCapability` / `GraphNodeChipRuntime` must keep both NodeViews live; wiring only `runbookReference` is a miss;
- no normalized label lookup;
- no alias rebind;
- no corpus fallback when World Graph is unavailable;
- absent node → unresolved sheet state;
- missing exact graph scope on otherwise-resolved projection → integrity/error state;
- conflicting exact locator/ref ID → error;
- no opening the first matching node.

If merged P3A later collapses one representation, pin that predecessor fact in the implementation handback and drop only the collapsed form. Do not treat remaining dual Markdown on disk as out of scope without that pin.

### C. Runbook occurrence projection

From P3A's exact admitted model, derive all graph-node occurrences by walking **disjoint `bodyDoc` slices**, not a linear “current Beat / current Choice” state machine over the unsliced document.

P3A body ownership is already normative:

```text
Scene bodyDoc:  nodes after Scene heading until first following root playable marker
Beat bodyDoc:   nodes after Beat heading until next root playable marker
Choice bodyDoc: nodes after Choice heading until first Option or next root Beat/Choice/Scene
Option bodyDoc: nodes after Option heading until next root playable marker
```

Choice is a sibling of Beat, not a child of the previous Beat. Option nests under Choice only.

Occurrence context is exactly the owning slice plus that slice's legitimate P3A parent IDs:

```text
scene.bodyDoc  → { sceneId }
beat.bodyDoc   → { sceneId, beatId }          # choiceId/optionId absent
choice.bodyDoc → { sceneId, choiceId }        # beatId/optionId absent
option.bodyDoc → { sceneId, choiceId, optionId }  # beatId absent
```

Inside each `bodyDoc`, every node that `admitPlayGraphNodeRef` accepts is one occurrence of that `graphNodeId`, retaining `sourceNodeType` for evidence. Document order is slice order then in-slice order.

Do **not** implement a walk of the form “Beat becomes current Beat; Choice becomes current Choice” unless it produces these same identities, including **clearing Beat when Choice starts**. A Choice/Option occurrence must never retain the previous Beat.

For a sheet opened on node X:

- list every exact occurrence of X from both graph-native forms;
- show stable Scene/Beat/Choice/Option context with presentation titles from the owning slice;
- indicate current Runtime Scene/Beat when an occurrence's membership matches;
- never call one occurrence `the` canonical occurrence merely because it appears first;
- relationship-drilled Y may have no occurrence; render `Not explicitly referenced in this Runbook` rather than hiding Y or fabricating context.

### D. Table-first sheet hierarchy

For ordinary non-Threat World objects in P3B:

```text
1. World identity / compact role + concise accepted summary
2. In this Runbook
   - exact occurrence list
   - current Scene/Beat highlight where applicable
3. Relevant World relationships
4. Source/evidence summary
5. Advanced/supporting graph/evidence detail
```

Do not present raw claim/revision/node IDs in the default table scan path.

`GraphObjectCard` remains the neutral underlying representation. If the pinned base still needs composition support, the allowed shared extension is neutral:

```text
GraphObjectCardMode += "play"
afterSummarySlot?: ReactNode
```

or an equivalently small neutral slot/mode.

Do not add Play vocabulary into `graphObjectCard` types.

### E. Relevant relationships

Default visible relationships continue to use the existing shared selection/ordering policy from GraphObjectCard.

P3B must not invent `connectedNow` as stored data.

Runbook occurrence context may make some relationships more useful later, but this slice does not create a ranking engine that rewrites World adjacency.

### F. Relationship drill — exact originating graph revision

For X opened from exact graph scope:

```text
G = {
  worldId,
  campaignId,
  scopeMode,
  revisionId
}
```

Click relationship X→Y:

1. require exact relationship target ID; label alone is not identity;
2. if current loaded projection still exactly matches G, resolve Y there;
3. otherwise request the same world/campaign/scope with `revisionPin = G.revisionId` and `focus = none`;
4. verify returned projection scope exactly equals G;
5. resolve Y by exact target ID;
6. open Y in the same shared Projection host;
7. if G cannot be retrieved or Y is absent there, show a truthful unresolved/error state; **do not** retry against current graph head.

This rule must live in neutral `graphReference` once both Plan and Play consume it.

### G. Source detail

World projection evidence/source handles remain authoritative.

P3B may show:

- human-readable evidence/source label;
- admitted excerpt/source phrase already present in the projection model;
- source domain;
- explicit `Read source` action when the existing evidence row says it can be opened.

`Read source` may intentionally navigate to the existing Build/source reader as a secondary deep-detail action. Opening the object sheet itself must not navigate away from Play.

Source failure behavior:

- row-local source navigation failure does not destroy the object sheet;
- no copied full source block is cached into Play;
- no source text is written into the Runbook or Run;
- no #578 `sourceBlocks` equivalent is added.

### H. Shared Projection host / lease

Play publishes graph-reference capability upward to the existing app-scoped Projection host.

Required:

```text
one ProjectionHost only
Play owns lens/resolver/content policy
Interaction Layer owns host chrome/open/close lease
surface switch clears or revalidates stale Play projection
async graph/source completion cannot reopen content under a different surface lease
```

At the design anchor, `LegacyProjectionHostAdapter` is temporary and recognizes native Build specially. If it remains the current owning host adapter at the pinned P3A base, P3B may minimally add native Play publication handling there. It must not create a second route-local ProjectionHost.

If a newer neutral host has replaced that adapter by dispatch time, use the new owner and re-brief §4 rather than reviving legacy code.

### I. Threat boundary

P3B must not accidentally consume `ResolvedGraphObjectProjection`'s existing Threat specialization as proof that native Play Threats are done.

For P3B acceptance, ordinary NPC/location/item/faction-like graph objects are the target.

Threat handling options at the pinned base:

```text
preferred: explicitly render generic World/source object sheet with "Threat mechanics projection comes next"
OR
if shared renderer routes to existing exact Threat sheet with no new Play coupling:
  treat that as inherited shared behavior only, not P3B evidence and not P4 completion
```

No P3B code may add or modify Add-to-Combat behavior.

### Observable path table

| Path | Current / predecessor behavior | Required P3B behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| Runbook `dmb-node:` chip | P3A renders `graphNodeReference` | click opens exact node via `onSelectNode(nodeId)` | Yes | Play ref capability + graphReference |
| Runbook `#dmb-ref:graph-node:` chip | P3A renders `runbookReference` graph-node | click opens the same exact node via `onSelectNode(refId)` | Yes | Play ref capability + graphReference |
| Ambient graph lens disagrees with Run | global app context may carry another/default campaign | Play derives graph projection from exact admitted Run/Runbook scope | Yes | Play graph projection loader |
| Exact node present | n/a in native Play | table-first sheet + exact graphScope | Yes | resolver + sheet |
| Exact node absent | n/a | unresolved state; no label/alias/corpus fallback | Yes | graphReference |
| World Graph unavailable | P3A deck still useful | deck stays useful; graph ref open reports unavailable | Yes | Play resolver |
| Object has multiple Runbook refs | no object sheet | list all occurrences; highlight current, no first-as-canonical | Yes | occurrence index |
| Related object click | no native Play drill | same host, exact origin graph revision | Yes | shared relationship resolver |
| Ambient graph head advances while X open | n/a | X→Y drill remains pinned to X's origin revision | Yes | shared relationship resolver |
| Source evidence available | no native Play object sheet | show source/evidence; explicit Read source | Yes | GraphObjectCard/source nav |
| Source navigation fails | n/a | row error only; sheet remains | Yes | source nav wrapper |
| Close object sheet | n/a | exact Play surface/table deck remains underneath | Yes | Projection host |
| Surface changes during async drill | n/a | stale completion cannot open under new lease | Yes | Interaction Layer publication/lease |

### Adversarial sequences

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| Run C2 open → ambient global lens C1 → click C2 graph-node | request/resolve C2 scope only; never C1/default | graph-scope test |
| workspace world_id says W1 + governed campaign map says W2 | graph refs blocked; no preferred scope | admission test |
| X exact ref label renamed but ID stable | opens same X; label remains presentation | identity test |
| ref ID missing, label matches one graph object | unresolved; no label rebind | graph-native negative test |
| X appears in Scene A Beat 1 and Scene C Beat 4 | sheet lists both occurrences; current one highlighted if applicable | occurrence-index test |
| same node X once as `dmb-node:` and once as `#dmb-ref:graph-node:` | both chips open X; occurrence index retains both; exact ID only; no label/alias fallback | dual-representation test |
| Scene → Beat(X) → Choice(X) → Option(X) → Beat(X) | four occurrences; Choice/Option have no beatId; Beats have no choiceId; no stale sibling context | slice-membership test |
| X@G1 open → ambient projection refreshes G2 → click X→Y | pinned G1 fetch/use; no G2 Y | exact-scope drill test |
| pinned G1 no longer retrievable | unresolved/error; no current-head fallback | exact-scope drill failure test |
| relationship has label but no exact targetId | no guessed target | relationship identity test |
| source read fails | row-local error; X sheet remains open | source degradation test |
| Play surface lease unmounts while pinned fetch pending | completion discarded; projection does not reopen | lease race test |
| relationship drill lands on Y not present in Runbook | Y sheet renders World/source + truthful no-occurrence state | degradation test |
| #578 Of Conks bridge exists elsewhere | P3B imports none of it | static diff/import audit |

---

## §4 Files in scope — write lease

The exact P3A-created paths must be re-read at dispatch. Expected implementation lease if P3A lands with the designed topology:

| Action | Path | Purpose |
|---|---|---|
| Create / Modify | `Docs/Plans/HANDOFF-PLAY-native-graph-object-sheet.md` | pin base/status + evidence handback |
| Modify | `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` | P3B evidence ledger/disposition; record narrow Plan+Play graphReference hoist if proven |
| Modify | `apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx` | bind admitted Runbook context to Play graph-reference capability/publication |
| Modify | `apps/live-control-ui/src/playSurface/runbook/RunbookTableDeck.tsx` | provide exact Runbook projection/current Runtime context to ref occurrence/open seam; no new authority |
| Create | `apps/live-control-ui/src/playSurface/reference/playGraphReferenceOccurrences.ts` | pure all-occurrence derivation over P3A `bodyDoc` slices; both graph-native TipTap forms |
| Create | `apps/live-control-ui/src/playSurface/reference/playGraphReferenceOccurrences.test.ts` | dual-representation, P3A slice-membership, duplicate occurrence, current-context proof |
| Create | `apps/live-control-ui/src/playSurface/reference/usePlayGraphReferenceResolver.ts` | Run-bound campaign/world graph load + exact graph-node resolver |
| Create | `apps/live-control-ui/src/playSurface/reference/usePlayGraphReferenceResolver.test.tsx` | scope/admission/unavailable/ref identity proof |
| Create | `apps/live-control-ui/src/playSurface/reference/PlayGraphReferenceCapability.tsx` | GraphNodeChipRuntime + Interaction Layer publication/bindings for native Play |
| Create | `apps/live-control-ui/src/playSurface/reference/PlayGraphReferenceCapability.test.tsx` | click/open for both graph-native forms; lease/no-mutation proof |
| Create | `apps/live-control-ui/src/playSurface/reference/PlayGraphObjectSheet.tsx` | table-first World + Runbook context + Source/evidence sheet |
| Create | `apps/live-control-ui/src/playSurface/reference/PlayGraphObjectSheet.test.tsx` | hierarchy/degradation/source/relationship behavior |
| Create | `apps/live-control-ui/src/playSurface/reference/index.ts` | local exports |
| Modify | `apps/live-control-ui/src/graphObjectCard/types.ts` | add neutral `play` presentation mode only if still required |
| Modify | `apps/live-control-ui/src/graphObjectCard/GraphObjectCard.tsx` | add neutral composition slot/mode only if required; no Play semantics |
| Modify | `apps/live-control-ui/src/graphObjectCard/GraphObjectCard.test.tsx` | shared consumer regression for neutral extension |
| Create | `apps/live-control-ui/src/graphReference/resolveGraphRelationship.ts` | neutral exact-origin-scope relationship drill used by Plan+Play |
| Create | `apps/live-control-ui/src/graphReference/resolveGraphRelationship.test.ts` | pinned revision / no current-head fallback proof |
| Modify | `apps/live-control-ui/src/graphReference/index.ts` | export the narrow shared resolver |
| Modify | `apps/live-control-ui/src/planSurface/reference/usePlanGraphReferenceResolver.ts` | delegate existing exact-scope relationship behavior to shared helper; no behavior change |
| Modify | `apps/live-control-ui/src/planSurface/reference/usePlanGraphReferenceResolver.test.tsx` | prove Plan retains exact existing semantics after extraction |
| Modify if still owning host | `apps/live-control-ui/src/planSurface/projection/LegacyProjectionHostAdapter.tsx` | admit native Play publication into the one shared ProjectionHost; transitional path only |
| Modify if still owning host | `apps/live-control-ui/src/planSurface/projection/LegacyProjectionHostAdapter.test.tsx` | one-host / Play lease / Plan+Build regression |

### Bounded discovery exception

```text
Directory:
  apps/live-control-ui/src/

Maximum additional paths:
  4

Allowed path kinds:
  exact P3A successor paths whose names differ from this design,
  current owning SurfaceInteraction projection catalog/registration test,
  existing sourceNavigation test,
  existing GraphNodeChipRuntime test.

Decision rule:
  allowed only when the same §1 invariant is already owned by that current path
  and the change is required to connect/prove native Play without adding a second
  public workflow or authority.
```

If P3A's final topology requires changing more than two expected Play paths above, update this handoff/write lease before CODE changes rather than treating bounded discovery as a substitute for re-briefing.

### Deliberate non-lease / read only

```text
apps/live_control_server/**
apps/live-control-ui/src/tiptap/playable/**
apps/live-control-ui/src/tiptap/markdown/**
apps/live-control-ui/src/tiptap/extensions/GraphNodeReferenceNode.ts
apps/live-control-ui/src/tiptap/extensions/GraphNodeReferenceView.tsx
apps/live-control-ui/src/statblocks/**
apps/live-control-ui/src/combat*/**
apps/live-control-ui/src/sourceNavigation/sourceNavigation.ts
Docs/Design/ARCHITECTURE-playable-material-and-runtime.md
Docs/Design/ARCHITECTURE-surface-interaction-layer.md
Docs/Design/DESIGN-play-surface-projection.md
```

A required backend production change, P1 grammar change, source storage change, or mechanics/Combat change is a stop report.

---

## §5 Explicitly out of scope / collision boundary

| Path / authority | Why P3B must not touch or claim it |
|---|---|
| P2/P3A Run/manifest/progress backend | object opening is read-only; Runtime is context only |
| P1 element/reference grammar | P3B consumes exact existing graph-node refs; grammar changes are separate |
| durable object-attached Playable schema | architecture allows it, but no generic contract exists yet; projection layer must not invent one |
| World Graph writes / Graph Review | sheet reads accepted projection only |
| Source persistence/import | use existing evidence handles; no copied source truth |
| `ofConksPlayObjectBridge` / `ofConks*` | dogfood mining evidence only |
| Threat mechanics specialization | P3C |
| Add to Combat | P4; Combat owns mutable combat state |
| map/media overlays | separate Asset/Annotation path |
| Run rebase UI | separate lifecycle operator workflow if/when scheduled |
| editable Play object sheet | P5/proposal/adoption or later narrow editing |
| agent/Hermes mutation | P5 |
| generic WorkObject refs | no independent need discovered by this slice |
| DungeonMind / DungeonMindDnD | no kernel/profile change in P3B |

---

## §6 Implementation contract

```text
Input:
  P3A exact admitted Play context:
    Run
    exact bound Runbook snapshot / parsed projection
    current P2 Runtime fields for context highlighting only
  exact graph-node from either admitted TipTap form, after admitPlayGraphNodeRef
  existing WorldGraphProjection API
  existing graphReference exact-node resolver
  existing GraphObjectCard projection model
  existing evidence/source-navigation handles

Output:
  READY:
    shared-host Play graph object sheet
    World identity/summary
    exact all-occurrence Runbook context
    relevant World relationships
    Source/evidence detail
    exact-revision relationship drill

  or DEGRADED/BLOCKED reference state:
    graph unavailable
    world scope unknown/conflicting
    exact node unresolved
    exact graph scope integrity error
    pinned relationship revision unavailable
    source navigation row error

Invariant:
  same §1 invariant

Failure behavior:
  graph load unavailable -> Runbook stays usable; graph refs report unavailable
  world scope conflict -> block graph refs; no default/ambient fallback
  exact node miss -> unresolved; no label/alias/corpus fallback
  graph response scope malformed -> integrity/error; no object card from unscoped bytes
  pinned drill failure -> keep current sheet + report target failure; no current-head retry
  source navigation failure -> row-local error; current sheet remains
  stale surface lease -> drop async completion

Replay / idempotency:
  same Runbook + graph projection + ref -> deterministic same resolution/context
  repeated open of same ref -> same sheet identity for same graphScope; no writes
  changed World head before a fresh independent open -> new open may capture new exact graphScope
  active relationship chain -> remains on originating graphScope until a new independent open/reset
```

### A. Play graph projection state

Use an explicit state owned by Play reference capability; exact names may vary:

```text
idle
loading
ready
unavailable
blocked-scope
error
```

The native Runbook deck is not gated by this state after P3A admission. Graph projection is an optional read dependency for graph references, not a Runbook authority prerequisite.

### B. Graph scope admission matrix

| Runbook workspace world_id | governed campaign→world | Required result |
|---|---|---|
| W | W | use W |
| W | absent | use explicit workspace W |
| absent | W | use governed mapping W |
| W1 | W2 | block graph capability; integrity/scope conflict |
| absent | absent | graph unavailable; Runbook remains usable |

No app default campaign/world may fill the final row.

### C. Reference identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| `graphNodeReference` from `dmb-node:<id>` | admit `nodeId` as durable graphNodeId | same ID as typed graph-node form | **No** preferring typed form |
| `runbookReference` `graph-node` from `#dmb-ref:graph-node:<id>` | admit `refId` as durable graphNodeId | same ID as `dmb-node:` form | **No** preferring `dmb-node:` form |
| same node authored once in each form | both click/open; both retained as occurrences | do not collapse to one chip | **No** |
| `graph-node` exact ID exists | resolve exact ID | n/a | No fallback needed |
| ID absent, label matches unique object | unresolved | do not use label | **No** |
| ID absent, alias matches | unresolved | do not use alias | **No** |
| exact ID resolves but label differs | exact ID wins; show authoritative World label + optional authored ref label as context | no identity conflict | No |
| exact locator conflicts with refId | error | fail closed | No |
| graph unavailable | unresolved/unavailable | no corpus fallback for graph-native | **No** |
| legacy `npc/location/...` typed ref | outside P3B | leave predecessor rendering behavior unchanged | n/a |

### D. World revision matrix

| Operation | Revision rule | Fallback |
|---|---|---|
| independent Runbook ref open | current head for exact Run campaign/world; capture returned graphScope | none to ambient scope |
| relationship drill from X@G | exact G | no current-head fallback |
| source read from X@G evidence | exact handles already carried by X model | no label/path guessing |
| close/reopen same Runbook ref after World advances | fresh independent open may use new head and capture G2 | truthful new sheet scope |

### E. Occurrence projection matrix

| Condition | Required presentation |
|---|---|
| one occurrence | show exact owning P3A slice path (Scene and Beat and/or Choice/Option as applicable) |
| multiple occurrences | show all in document order; no canonical-first claim |
| occurrence in Choice/Option after a Beat | Choice/Option context only; `beatId` absent |
| same ID once per graph-native TipTap form | retain both; record distinct `sourceNodeType` |
| occurrence in current Scene/Beat | highlight current context |
| occurrence only in non-current context | show without current highlight |
| relationship target has zero occurrence | `Not explicitly referenced in this Runbook` |
| malformed P3A occurrence context | stop/integrity failure in occurrence derivation; do not invent membership |

### F. Projection composition

The Play sheet may add presentation-only model/slots such as:

```text
In this Runbook
  Scene: <title>
  Beat: <title>          # only when owning slice is a Beat
  Choice / Option: ...   # only when owning slice is Choice or Option
  Current
```

but must not mutate `GraphObjectCardViewModel` into a Playable data store.

Do not add fields such as:

```text
attitude
offers
atTable
rulesNow
sourceBlocks
connectedNow
```

to the neutral graph object model solely for P3B.

### G. Narrow shared relationship resolver

**Grounding source:** current Plan exact-scope drill behavior in `usePlanGraphReferenceResolver.ts`.

Required neutral contract:

```text
Input:
  relationship row with exact targetId
  originating ExactGraphReferenceScope
  current WorldGraphProjection? + state
  loadPinnedProjection(request) dependency

Output:
  GraphReferenceResolution for exact target

Rules:
  exact targetId required
  if current projection scope == origin scope -> resolve there
  else load origin scope at revisionPin
  verify loaded projection scope exactly
  no label fallback
  no current-head fallback after pinned failure
```

Plan must use the neutral implementation after extraction and retain its existing tests/behavior. Play uses the same neutral helper.

If the pinned base already hoisted this contract elsewhere, consume that owner instead; do not create a duplicate helper.

### H. Host / surface publication contract

```text
Play publishes:
  surfaceId = play
  graph-reference projection registration/bindings
  exact resolver state/binding for active Run

Interaction Layer owns:
  ProjectionHost DOM/chrome
  open/close/expand lifecycle
  lease cleanup

Play does not:
  mount a second ProjectionHost
  write projection host state to Run
  retain stale active graph object across a different surface lease
```

If the temporary `LegacyProjectionHostAdapter` remains the host policy owner at dispatch, extend its **native publication** policy to accept Play by capability shape/surface publication, not by copying Plan config or inventing a Play-owned host.

### I. Persistence / replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay | Compatibility/migration | Rollback |
|---|---|---|---|---|---|
| Runbook occurrence index | none | same exact P3A model -> same occurrences | deterministic recompute | none | n/a |
| World object sheet | none | same graph projection/ref -> same model | deterministic reopen | none | n/a |
| active Projection host state | Interaction Layer transient | lease-scoped | reopen permitted | existing host semantics | close |
| relationship drill | none | exact origin graphScope carried through chain | retry exact pinned read allowed | existing graph revision API | stay on prior sheet on failure |
| Source read | none in Play | exact source handles forwarded | ordinary read retry | existing source nav | return/back navigation |

No P3B persistence file is allowed.

---

## §7 Evidence required to merge

Every material clause must be proved at its owning boundary.

### Required proof table

| Guarantee / invariant clause | Owning boundary | Evidence class | Required proof |
|---|---|---|---|
| exact Run campaign/world scope, not ambient default | Play resolver | adversarial unit/component | Run C2 + ambient C1/default still requests C2/W exact |
| world_id/map conflict fails closed | Play resolver | contract | W1 vs W2 blocks; no request with guessed scope |
| graph-node exact ID only | shared resolver | contract | label/alias match cannot rescue missing ID |
| both admitted graph-native forms click and occur | Play capability + occurrence index | adversarial | same node once as `graphNodeReference` and once as `runbookReference` graph-node; both open that ID; index retains both; no label/alias fallback |
| P3A slice membership has no stale Beat | occurrence index | adversarial | Scene → Beat(X) → Choice(X) → Option(X) → Beat(X) yields four occurrences; Choice/Option `beatId` absent; Beat rows have no choice/option |
| graph unavailable does not break Runbook deck | Play component | degradation | deck remains; ref unavailable copy |
| all Runbook occurrences retained | occurrence index | pure unit | same node in multiple Scene/Beat contexts returns all ordered entries |
| current occurrence highlight truthful | sheet/component | component | current Scene/Beat marks only matching occurrence |
| zero-occurrence related object still useful | sheet | component | World/source sheet + explicit no-occurrence state |
| object open uses shared host | Interaction Layer | integration | click opens one shared ProjectionHost; no route-local host |
| close restores exact table position | Play + host | integration | Scene/Beat selection unchanged after open/close |
| relationship drill stays on origin revision | shared graphReference | adversarial | G1 open, ambient G2, target resolves from pinned G1 |
| pinned revision unavailable never falls to head | shared graphReference | adversarial | G1 fetch fail -> unresolved/error; no G2 lookup |
| Plan behavior preserved after hoist | Plan resolver | regression | existing Plan exact-scope tests remain green against shared helper |
| source navigation error is row-local | Play sheet/source wrapper | degradation | failed Read source leaves current sheet open |
| surface lease race safe | Interaction Layer | concurrency | unmount/switch before async drill completion prevents stale reopen |
| no mutation | Play/shared host | contract | object open/drill/source inspect makes no Run progress, workspace, graph, mechanics, Combat calls |
| no campaign bridge | diff/import audit | static | no `ofConksPlayObjectBridge`, `ofConksNodeMedia`, `ofConksMapOverlays`, or equivalent hard-coded mapping imported/created |
| narrow hoist only | cumulative diff | review | shared change limited to graph relation navigation / neutral card composition; no WorkObject/DungeonMind contracts |

### Focused test commands

Exact filenames may be adjusted only to match the final pinned P3A topology recorded in §4 before implementation begins.

```bash
cd apps/live-control-ui
pnpm exec vitest run \
  src/playSurface/reference/playGraphReferenceOccurrences.test.ts \
  src/playSurface/reference/usePlayGraphReferenceResolver.test.tsx \
  src/playSurface/reference/PlayGraphReferenceCapability.test.tsx \
  src/playSurface/reference/PlayGraphObjectSheet.test.tsx \
  src/graphReference/resolveGraphRelationship.test.ts \
  src/planSurface/reference/usePlanGraphReferenceResolver.test.tsx \
  src/graphObjectCard/GraphObjectCard.test.tsx
```

### Required predecessor regressions

Run the merged P3A tests that own:

```text
exact Runbook admission
native Runbook projection
Runbook table deck / P2 Runtime overlay
/play route
```

The exact command must name the real merged P3A test files in the evidence packet.

Also run existing shared reference regressions covering exact graph-native identity and GraphNode chip runtime. At the design anchor likely candidates include:

```bash
cd apps/live-control-ui
pnpm exec vitest run \
  src/graphReference/ \
  src/graphObjectCard/
```

If that directory command is too broad/slow at the pinned base, replace it with the exact owning tests and record why.

### Type/build gate

```bash
cd apps/live-control-ui
pnpm run typecheck
pnpm run build
```

### Steward / diff gate

```bash
uv run python scripts/steward_preflight.py \
  --handoff Docs/Plans/HANDOFF-PLAY-native-graph-object-sheet.md \
  --pr <N>

git diff --check
git diff --name-only <PIN_AFTER_P3A_STATE_SYNC>...HEAD
```

### Static no-bridge audit

At minimum:

```bash
rg -n "ofConksPlayObjectBridge|ofConksNodeMedia|ofConksMapOverlays|OF_CONKS" \
  apps/live-control-ui/src/playSurface \
  apps/live-control-ui/src/graphReference \
  apps/live-control-ui/src/graphObjectCard
```

Expected: no new P3B production dependency on campaign-specific bridge data. Existing unrelated historical/dogfood files outside the changed production path are not a failure by themselves.

### Minimal live / dogfood proof

Required because P3B is a table-interaction projection and its value includes continuity of attention.

Use one **non-Of-Conks hard-coded** admitted Runbook fixture or real workspace Run available at the pinned base.

Scenario:

```text
1. Open /play?run=<exact Run UUID>.
2. Navigate to a Scene/Beat containing an exact graph-node reference.
3. Click the reference.
4. Confirm one shared projection drawer opens without leaving /play.
5. Confirm identity/summary + In this Runbook + relationships + source/evidence are truthful.
6. Open one related object and confirm Play position remains underneath.
7. Close projection and confirm same Scene/Beat/table position remains.
8. Reload or use a second fixture where an object has no richer Playable interpretation;
   confirm the sheet remains useful without fabricated At-the-table/Attitude fields.
```

Capture exact Run UUID, Runbook document/revision/SHA, graph world/campaign/revision, clicked node ID, related target ID, and observed URL/surface state in the evidence packet.

Do not use copyrighted source prose as pasted PR evidence. Record handles/labels and behavior, not long source text.

### Baseline failure handling

If a required existing Plan/graphObjectCard/graphReference test fails on the pinned base before P3B changes, run the exact same command on base and head and record:

```text
BASELINE_FAILURE
command
base result
head result
whether P3B adds a new failure
```

No silent waiver.

### Roadmap review required

P3B must explicitly answer:

```text
P3B_HOIST_OBSERVATION
- Did Plan + Play both require exact-origin graph relationship navigation? yes/no
- Was that invariant hoisted into neutral graphReference? yes/no/already shared
- Did Play need a new generic graph/source projection contract beyond existing Buddy seams? yes/no
- Did any generic WorkObjectRevisionRef become necessary? yes/no
- Did any generic WorkObjectElementRef become necessary? yes/no
- Did object-attached Playable interpretation require a new durable schema? yes/no
- Did DungeonMind relevance appear? none / exact future question
- Does P3C exact Threat mechanics remain next? yes/no
```

Expected disposition if the implementation matches this design:

```text
ROADMAP_REVIEW — UPDATED
Plan + Play now independently prove exact-origin World Graph relationship navigation
as a shared Buddy graphReference invariant; record that narrow hoist. Keep Play Object
Sheet semantics/product ordering Play-owned. Keep WorkObject refs, Runtime, and
DungeonMind hoists false. P3C remains next.
```

If the pinned base already contains that shared helper before P3B, the expected disposition may instead be `NO DESIGN CHANGE` with evidence that P3B reused the already-hoisted seam.

---

## §8 Required review handback

Record:

1. `Review Cycle <N>` and exact PR/head SHA;
2. exact pinned post-P3A base SHA;
3. P3A predecessor merge/review/evidence anchors and total review cycles;
4. §1 mission/invariant disposition;
5. exact Play Run/Runbook authority used in tests/dogfood;
6. exact World Graph scope/revision used for object open and relationship drill proof;
7. §7 required vs produced evidence with provenance;
8. nano-commit/fix story;
9. actual changed paths vs §4 / bounded discovery;
10. baseline failures/waivers;
11. prior review findings and closure on re-review;
12. dual-representation proof: both `dmb-node:` and `#dmb-ref:graph-node:` click/open and occur;
13. P3A slice-membership proof: Choice/Option occurrences do not retain a previous Beat;
14. narrow hoist disposition: Plan+Play exact-scope resolver shared or not, and why;
15. explicit confirmation no `ofConks*` bridge entered product path;
16. explicit confirmation no Run/Runbook/World/Source/Mechanics/Combat write occurs from object open/drill;
17. named successor P3C still false;
18. roadmap disposition and implementation/evidence head.

One formal reviewer judgment against one distinct head SHA counts as one review cycle. Re-inspecting the same unchanged head does not create another cycle.

---

## §9 Acceptance rubric

PASS only if all are true:

- [ ] Exactly one independently useful capability: native Play graph-object sheet from exact Runbook graph-node refs.
- [ ] P3A remains the predecessor and no P3A authority is duplicated.
- [ ] Play graph scope comes from admitted Run/Runbook context, never ambient/default campaign state.
- [ ] Exact graph-native refs resolve by durable node ID only.
- [ ] Both admitted graph-native TipTap forms (`dmb-node:` `graphNodeReference` and `#dmb-ref:graph-node:` `runbookReference`) participate in click/open and occurrence derivation through one normalization seam.
- [ ] Occurrence membership is taken from disjoint P3A body slices; Choice/Option occurrences never retain a previous Beat.
- [ ] All exact Runbook occurrences are derived/reconstructable; no persisted projection cache/body map exists.
- [ ] Missing richer object-attached Playable interpretation degrades truthfully rather than being inferred.
- [ ] Object sheet uses World identity/summary/relationships and Source/evidence handles without copying truth into Play.
- [ ] Object open uses the one shared Projection host and preserves table position.
- [ ] Relationship drill preserves exact originating World Graph revision or fails closed.
- [ ] Plan retains the same exact-scope relationship semantics after any neutral extraction.
- [ ] Source navigation failure is local and does not destroy the sheet.
- [ ] No opening/drilling action mutates Run, Runbook, World, Source, Mechanics, or Combat.
- [ ] No campaign-specific `ofConks*` mapping/bridge enters the product path.
- [ ] Threat mechanics / Add-to-Combat remain unclaimed.
- [ ] No generic WorkObject refs, Runtime primitive, transaction framework, or DungeonMind contract is introduced.
- [ ] Actual paths stay within §4/bounded discovery.
- [ ] Focused tests + P3A predecessor regressions + typecheck/build + diff/preflight evidence are exact and independently rerun.
- [ ] Minimal live/dogfood proof demonstrates open → inspect/drill → close → same table moment.
- [ ] Roadmap review records the narrow shared graphReference evidence without over-hoisting.

REQUEST CHANGES for repairable implementation/evidence gaps.

STOP/rebrief for architecture/scope mismatch.

---

## Stop conditions

Stop and report instead of expanding if any of these appears:

- P3A is not merged/state-synchronized or this handoff cannot be pinned to exact post-P3A `main`;
- P3A does not expose one exact admitted Runbook model/TipTap context suitable for deterministic reference occurrence derivation;
- P3A body slices no longer make Choice/Option disjoint from the previous Beat, and this handoff's membership rule cannot be restated without a second parser;
- merged P3A drops one admitted graph-native representation without pinning an explicit canonicalization fact;
- native Play graph references require a new server-side Play projection API rather than existing graph/source APIs;
- world identity cannot be derived without inventing a campaign/world guess or changing persistent Run schema;
- object sheet requires persistent `atTable`/`attitude`/`offers`/`connectedNow` data to be useful;
- relationship navigation cannot preserve exact origin World Graph revision without a new graph authority contract;
- a second ProjectionHost would be required;
- current Interaction Layer owner changed and §4 no longer names the real host integration seam;
- a P1 Markdown/reference grammar change is required;
- a backend production path is required;
- World/Source write behavior becomes necessary;
- Threat exact mechanics or Combat mutation becomes necessary to satisfy the mission;
- map/media asset authority becomes necessary;
- generic WorkObject refs or DungeonMind changes become necessary;
- another active lane owns any required write path and cannot be serialized cleanly.

Report:

```text
Stop condition:
Invariant clause affected:
Why current P3B mission cannot absorb it:
Required evidence now missing:
Affected paths/ownership layers:
Proposed successor or re-brief:
State-authority update needed:
```

---

## §10 Successor boundary

If P3B lands without contradictory evidence, the next planned slice is:

```text
P3C — exact Threat mechanics projection in native Play
```

P3C should prove:

```text
exact World threat identity
→ exact admitted DungeonMindDnD mechanics/statblock binding
→ Play Threat sheet
```

while keeping this false until P4:

```text
Add to Combat
Combat entity mutation
HP / initiative / conditions ownership changes
```

P3B must not pre-build P3C merely because the shared graph renderer already knows that Threat objects exist.
