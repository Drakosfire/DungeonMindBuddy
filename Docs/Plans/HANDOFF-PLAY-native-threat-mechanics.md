---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: Playable Architecture Graduation / P3C
  - Flow: PLAY
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-PLAY-native-threat-mechanics.md
  - Branch / PR: documents/play-p3c-native-threat-mechanics / `PLAY: design native Threat mechanics`
  - Base/head: `bad7496677cb2f739935ebc454c153934994d160` / <implementation head>

  ## Verification pointer
  - Design anchor: merged PR #606 / current main at `bad7496677cb2f739935ebc454c153934994d160`
  - P3B design head: `61aa6325b38e0902b360b63e8f06d7573c5e3966`
  - P3A design anchor: `b47c66c6a780308ceb2d8720de2f3086aad33cfc` on `documents/play-p3a-native-runbook-deck`
  - Required predecessor before dispatch: living-roadmap P2C remains current; this PR executes P3C CODE on design-anchor main by steward instruction
  - Base/head: `bad7496677cb2f739935ebc454c153934994d160` / <implementation head>
  - Changed paths: must remain inside HANDOFF §4
  - Verification: HANDOFF §7 + roadmap review disposition

  The checked-in handoff, cumulative diff, nano-commit story, independently
  rerun evidence, and roadmap review disposition are the review contract.
  This body is transport metadata.
---

# HANDOFF — project exact Threat mechanics inside native Play object sheets

**Created:** 2026-08-16
**Status:** CODE IN PR #608 — steward authorized executing against design-anchor `main` without waiting for a P3B implementation merge. Living-roadmap **dispatch authority remains P2C**.
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-native-threat-mechanics.md`
**Conversation/workstream:** `Playable Architecture Graduation / P3C`
**Flow / owner:** `PLAY`
**Direction:** DESIGN → CODE → REVIEW
**Design anchor:** merged PR #606 / `bad7496677cb2f739935ebc454c153934994d160`
**P3B design head:** `61aa6325b38e0902b360b63e8f06d7573c5e3966`
**P3A design anchor:** `b47c66c6a780308ceb2d8720de2f3086aad33cfc` on `documents/play-p3a-native-runbook-deck`
**Required predecessor:** P3B product sheet is still design-only; this PR creates the designed Play wrapper over existing resolved-graph World/Source fields plus shared mechanics.
**Implementation base:** `bad7496677cb2f739935ebc454c153934994d160`
**Suggested branch:** `documents/play-p3c-native-threat-mechanics`
**PR title:** `PLAY: design native Threat mechanics`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

---

## Dispatch gate — P3B must be product truth first

At this design anchor, repository truth is:

```text
main: bad7496677cb2f739935ebc454c153934994d160
PR #606: merged P3B DESIGN handoff only
P2A: merged
P2B1: merged
P2B2: merged
P2C: designed; living roadmap still names it current implementation authority
P3A: designed at b47c66c6..., but its handoff is not yet on main and it is not implemented
P3B: design handoff is on main; implementation does not exist yet
P3C: this design; successor only
```

This handoff is deliberately staged multiple dependencies ahead. It is not permission to skip state-authority transitions.

Before P3C CODE dispatch, all of the following must be true:

1. P2C is implemented, reviewed, merged, and post-merge synchronized;
2. the P3A handoff has landed on `main`, been pinned to the exact post-P2C synchronized base, implemented, reviewed, merged, and post-merge synchronized with P3B named next;
3. P3B has been pinned to the exact post-P3A synchronized base, implemented, reviewed, merged, and post-merge synchronized with P3C named next;
4. the exact P3B implementation/evidence head, final reviewed head, merge SHA, and formal review-cycle count are known;
5. `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` names P3C as current next slice and this file as the next handoff;
6. every `PIN_AFTER_P3B_STATE_SYNC` is replaced on the implementation branch with that exact synchronized `main` SHA;
7. the implementation agent re-reads the actual merged P3B Play object-sheet topology and the then-current shared Threat/statblock projection seams before editing;
8. steward preflight finds no conflicting active lease over P3B Play reference paths or shared statblock projection paths.

### Retirement gate

P3C exists to prove a capability, not to force code churn.

If merged P3B already satisfies the full §1 invariant by safely composing the existing exact Threat mechanics path into native Play — including Play-owned Runbook occurrence context, exact binding/revision integrity, surface-neutral policy, honest multi-binding behavior, and no Combat mutation — **do not manufacture a P3C implementation PR**.

Instead stop and re-brief the state sync with evidence that P3C is already satisfied or can be retired as a verification-only slice.

Stop and re-brief if P3B materially changes:

- the native Play object-sheet component or projection composition seam;
- how exact graph scope is carried into an opened object sheet;
- how relationship drilling preserves originating graph revision;
- how Runbook occurrence context is rendered;
- the shared Projection host publication/lease seam;
- Threat handling already inherited by the P3B sheet;
- source/evidence presentation ownership.

---

## §1 Mission and merge-ready invariant

**Mission:** When a GM opens an authored Threat from one exact admitted native Runbook, the existing Play object sheet shows the Threat's exact immutable mechanics from its accepted World→mechanics binding while preserving Play's Runbook context, World identity, relationships, and Source evidence — without copying mechanics into Playable/Runtime state and without creating or mutating Combat.

**Merge-ready invariant:**

> **Native Play displays Threat mechanics only from one exact resolved Threat identity at one exact World Graph scope and the exact mechanics attachment(s) returned for that pinned Threat by the existing Threat query/hydration contract. Every rendered statblock is an immutable `StatblockRevisionResourceV1` whose `(statblock_id, revision_id, definition_digest)` coheres with the hydrated binding and whose validation receipt/digest passes the existing renderer gate. Play never chooses first/latest/display-name mechanics, never collapses multiple exact bindings into an implicit winner, never reconstructs mechanics from World prose, and never persists mechanics into Runbook or Run state. Mechanics loading/error state is an optional read dependency: the P3B object sheet remains truthful and usable when mechanics are absent/unavailable. No P3C action creates Combat, chooses a combat team/quantity, or owns HP/initiative/conditions; that mutation boundary remains P4.**

### Why this is P3C

The living roadmap's P3 target is a Play Object Sheet composed from:

```text
World + Source + Playable + Mechanics + small Runtime status
                     ↓
              Play Object Sheet
```

P3A owns the native Runbook/runtime deck.

P3B owns exact graph-reference opening plus the read-only World + Source + Runbook-context object sheet.

P3C adds only the remaining P3 authority for authored Threats:

```text
P3B exact Threat object sheet
  + existing exact Threat mechanics hydration
  + immutable StatblockRevision rendering
  = native Play Threat sheet
```

P4 remains a different independently useful capability:

```text
native Play Threat sheet
  → explicit mechanics attachment choice if needed
  → explicit Add to Combat
  → Combat-owned mutable state
```

### Existing evidence this slice must reuse

Merged PR #504 already established the exact Threat projection contract:

- exact `scopeMode` and graph revision are carried through Threat hydration;
- relationship navigation preserves originating exact graph scope and reloads the pinned graph revision when needed;
- the frontend refuses incomplete statblock revision resources before rendering;
- Threat classification and exact-node selection are fail-closed;
- Combat, editing, binding adoption, and placement remained out of scope.

Merged PR #512 then established the table-facing shared Threat presentation:

- Threat chips can expand into full campaign-facing `StatblockRenderer` output;
- Plan and Build can consume the same Threat projection;
- multi-binding Threats do not silently show a first-winner compact statblock;
- mechanics identity is `(statblock_id, revision_id, digest)`;
- campaign belongs to Threat/graph scope and presentation, not ownership of an immutable mechanics revision.

Current design-anchor code already has:

```text
ResolvedGraphObjectProjection
  → shouldRenderThreatCampaignSheet(resolution)
  → ThreatSheetProjection

ThreatSheetProjection
  → exact graph-scope selection tuple
  → postThreatQueryHydration(includeMechanics=true, revisionPin=<exact graph revision>)
  → selectExactThreatHit
  → buildThreatSheetViewModel
  → StatblockRenderer for every available exact binding
```

The remaining problem is composition ownership, not a missing mechanics API.

Current `ThreatSheetProjection` still contains Plan-specific policy and presentation details such as:

```text
PlanSessionDescriptor
buildPlanGraphObjectActions(...)
plan-reference-object-card CSS/test identifiers
Plan-oriented /ingest action policy
```

P3C must not bring those Plan policies into native Play merely because the hydration/rendering code is useful.

### Capability decomposition

| Candidate outcome | Independently useful? | Durable/public contract? | Decision |
|---|---:|---:|---|
| Detect authored Threat object from exact P3B resolution | No; entry gate | Existing shared Threat classification | **Include / reuse** |
| Hydrate exact Threat mechanics at exact originating graph scope | No; mechanics prerequisite | Existing `dmb_threat_query_hydration_*` API | **Include / reuse** |
| Verify exact Threat response + binding/revision integrity | No; safety clause | Existing mechanics identity/contracts | **Include / strengthen at UI boundary if needed** |
| Render exact immutable statblock revision(s) in Play | Yes | Existing statblock renderer contract | **Include** |
| Preserve P3B Runbook occurrence/World/Source context around mechanics | No; same Play object-sheet capability | Reconstructable Play projection | **Include** |
| Extract a surface-neutral exact Threat mechanics hook/panel from current Threat sheet | No; composition support used by current Threat sheet + Play | Buddy-shared statblock projection seam | **Include — narrow refactor** |
| Preserve current Plan/Build Threat sheet behavior after extraction | No; regression requirement | Existing product behavior | **Include** |
| Select one binding as active/default for future Combat | Yes | New product state/choice semantics | **Exclude — P4** |
| Persist selected mechanics binding on Run | Yes | New Runtime contract | **Exclude — P4 design question, not P3C** |
| Add to Combat | Yes | Combat mutation | **Exclude — P4** |
| Create Combat encounter/entity | Yes | Combat runtime | **Prohibited** |
| Edit/adopt mechanics binding | Yes | World/Profile mutation | **Exclude** |
| Create/modify statblock | Yes | Mechanics authoring | **Exclude** |
| New Threat hydration backend/API | Yes | Shared transport contract | **Exclude; stop if required** |
| New DungeonMind/DungeonMindDnD contract | Yes | Cross-repository authority | **Exclude; existing profile contract should suffice** |
| Generic WorkObject refs / generic Runtime | Yes | Buddy-shared work-object/runtime | **Exclude** |

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed path? | **Yes.** Threat detection, exact hydration, renderer admission, Play composition, degradation, and stale async handling are all reads over existing exact authorities. |
| Most likely adversarial sequence | Open Threat X@G1 → mechanics request begins → GM drills to Threat Y or closes/switches surface → X response arrives late → unsafe implementation paints X mechanics into Y/current Play projection. Required: exact selection key + lease/generation guard drops stale X completion. |
| Other high-risk sequence | Threat has two exact mechanics bindings → UI presents one as if canonical because array order is convenient. Required: show both/explicit status; never choose first. |
| Easiest authority boundary to lose | `(statblock_id, revision_id, definition_digest)` coherence. A complete-looking revision must not render under a different binding locator. |
| Fact that forces stop/split | Need for a new backend mechanics contract, persistent Play mechanics selection, mechanics authoring/binding mutation, or any Combat mutation. |

---

## §2 Context, authority, and lane

### Parent authority — read in this order

1. `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`
   - §2 core invariant;
   - §3 authority table;
   - §7 Runtime ownership;
   - §8 projection architecture;
   - §8.2 Threat projection;
   - §11 persistence/revision rules;
   - §13 migration from #578.
2. `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`
   - ownership model;
   - promotion test;
   - P3 Native Play projections;
   - P4 Threat → exact mechanics → Combat boundary;
   - current sequence at actual dispatch time.
3. merged P3A implementation/handoff at dispatch.
4. merged P3B implementation/handoff at dispatch, especially:
   - `PlayGraphObjectSheet` or its actual successor;
   - exact graph-scope admission;
   - Runbook occurrence model;
   - source/evidence behavior;
   - exact-origin relationship resolver;
   - Projection-host lease/publication behavior.
5. current exact Threat projection:
   - `apps/live-control-ui/src/statblocks/projection/ThreatSheetProjection.tsx`;
   - `apps/live-control-ui/src/statblocks/projection/ThreatSheetProjection.test.tsx`;
   - `apps/live-control-ui/src/statblocks/projection/threatSheetViewModel.ts`;
   - owning view-model tests.
6. shared graph projection:
   - `apps/live-control-ui/src/graphReference/ResolvedGraphObjectProjection.tsx`;
   - `apps/live-control-ui/src/graphReference/types.ts`;
   - `apps/live-control-ui/src/graphReference/resolveGraphReference.ts`.
7. statblock renderer/contract:
   - `apps/live-control-ui/src/statblocks/render/StatblockRenderer.tsx`;
   - `apps/live-control-ui/src/contracts/dungeonbuddy-statblocks-v1/client.ts`;
   - exact revision fixture/tests.
8. existing Threat hydration transport:
   - `apps/live-control-ui/src/api/liveApi.ts` `postThreatQueryHydration`;
   - `apps/live-control-ui/src/api/types.ts` `ThreatQueryHydration*`, `ThreatBindingHydrationV1`, `ThreatMechanicsDisposition`.
9. Plan action policy only as transition debt to keep out of the new shared mechanics primitive:
   - `apps/live-control-ui/src/planSurface/reference/buildPlanGraphObjectActions.ts`.
10. PR #504 and PR #512 history/evidence for exact mechanics and shared Threat presentation.
11. PR #578 only as historical Play Threat interaction evidence; no `ofConksThreatPlayBridge` production reuse.

### Current design-anchor observations

At `bad7496677cb2f739935ebc454c153934994d160`:

```text
ResolvedGraphObjectProjection is already surface-oriented shared composition.
Authored Threats route to ThreatSheetProjection.
ThreatSheetProjection performs exact mechanics hydration and renders all available bindings.
Threat hydration is pinned to the selected graph revision.
Threat selection is exact node ID + exact graph scope.
Incomplete revision resources are withheld from StatblockRenderer.
Multiple exact bindings are represented, not silently reduced to one full-sheet winner.
Relationship drill already preserves origin graph revision through graphReference binding.
```

But:

```text
ThreatSheetProjection still imports PlanSessionDescriptor.
ThreatSheetProjection still builds Plan actions internally.
ThreatSheetProjection still carries Plan-named wrapper classes/test IDs.
P3B needs Play-owned Runbook occurrence + Source composition around mechanics.
```

The design intent is therefore to extract only the exact mechanics read/render core necessary for Play, while leaving Play section vocabulary in Play and leaving Plan action policy in Plan/current wrapper code.

### Lane table

| Field | Required content |
|---|---|
| Parent authority | Playable architecture + living Playable roadmap + existing exact Threat/statblock contracts |
| Base revision | `PIN_AFTER_P3B_STATE_SYNC` |
| Design anchor | `bad7496677cb2f739935ebc454c153934994d160` — merge of PR #606 |
| Predecessor contract | merged P3B native graph-object sheet over exact Runbook/World/Source authority |
| Exact input consumed | P3B exact resolved Threat + exact graphScope + Play occurrence context; existing Threat hydration response; immutable statblock revision resources |
| Output | reconstructable Play Threat mechanics section inside the P3B object sheet; no new durable mechanics/runtime record |
| Named successor | P4 — explicit Add to Combat from exact mechanics attachment(s) |
| What remains false | no Combat mutation, no mechanics selection persistence, no statblock/binding authoring, no new backend contract |
| Branch / isolated checkout | `agent/play-native-threat-mechanics` in isolated worktree/equivalent |
| Parallel lanes / collision hotspots | merged P3B Play object-sheet paths; `statblocks/projection/**`; `graphReference/ResolvedGraphObjectProjection*`; living roadmap |
| Runtime/state ownership | read-only mechanics projection; no Run progress write; no Combat runtime write; async component state only |
| State-authority sync after merge | add P3C roadmap evidence row; mark P3C merged; if evidence holds set P4 next; explicitly record no new mechanics/kernel contract |

### Hoist posture

This slice should not invent a new abstraction layer below statblocks.

The useful repeated invariant is already product-neutral:

> Given an exact resolved authored Threat at exact graph scope, hydrate and render only its exact immutable mechanics attachment(s), failing closed on identity/scope/integrity mismatch.

That invariant already serves Plan/Build presentation through the current shared Threat sheet. P3C may extract a cleaner neutral hook/panel from that implementation so Play can compose it without importing Plan policy.

Expected destination:

```text
PLAY DOMAIN
  Runbook occurrence context
  Play object-sheet ordering
  table labels / Play degradation copy

BUDDY SHARED STATBLOCK PROJECTION
  exact Threat mechanics hydration
  binding/revision admission
  immutable statblock rendering

DUNGEONMIND-DND
  existing exact mechanics attachment semantics
  no new P3C contract
```

No generic work-object or Runtime hoist is justified.

---

## §3 Observable paths and adversarial sequences

### A. Authored Threat gate

P3C is for authored Threat objects, not every creature-like World node.

At the pinned base, preserve the existing campaign Threat gate semantics unless predecessor evidence deliberately changed them:

```text
shouldRenderThreatCampaignSheet(resolution)
```

Current intent:

- exact resolved graph object required;
- exact graph scope required;
- explicit Threat identity (`kind/role == threat` or governed `threat:` node identity) enters the Threat sheet;
- a generic NPC/creature/monster that is not authored as a Threat remains a normal P3B object sheet even if broader helpers can classify it as creature-like.

Do not broaden P3C merely to maximize statblock rendering.

### B. Exact selection tuple

Mechanics read identity begins from the exact P3B resolution:

```text
ThreatSelectionTuple {
  worldId
  campaignId
  scopeMode
  revisionId       # exact originating World Graph revision
  threatNodeId     # exact durable World Graph node ID
}
```

Build the existing request:

```json
{
  "schema": "dmb_threat_query_hydration_request_v1",
  "worldId": "<exact>",
  "campaignId": "<exact>",
  "scopeMode": "campaign|world",
  "revisionPin": "<exact graph revision>",
  "queryText": "<exact threat node ID>",
  "focusNodeIds": ["<exact threat node ID>"],
  "maxHits": 64,
  "includeMechanics": true
}
```

Do not replace `queryText`/`focusNodeIds` with label text.

### C. Response admission

Before any exact mechanics render:

1. response world/campaign/scope/revision must equal the requested tuple;
2. exactly one returned hit may have `hit.threat.nodeId == selectedThreatNodeId`;
3. zero exact matches is `not_found`/truthful no mechanics;
4. multiple exact matches is integrity failure;
5. no response from a different graph revision may be accepted as “close enough”;
6. request failure/unavailable must not destroy the surrounding P3B object sheet.

No current-head retry after a pinned mismatch.

### D. Exact mechanics binding identity

Each hydrated mechanics attachment is explicit.

Required conceptual identity:

```text
Threat binding
  relationshipEdgeId
  bindingId?
  bindingRole?
  statblockId
  revisionId
  definitionDigest

Immutable revision
  statblock_id
  revision_id
  definition_digest
  validation_receipt.definition_digest
```

An available binding may render only when all available identity fields cohere:

```text
binding.statblockId == revision.statblock_id
binding.revisionId == revision.revision_id
binding.definitionDigest == revision.definition_digest
revision.validation_receipt.definition_digest == revision.definition_digest
revision passes existing complete StatblockRevisionResource gate
```

If an existing shared helper already proves all of this at the pinned base, reuse it.

If current transport intentionally permits a nullable locator field for a status other than `available`, preserve that degradation; do not manufacture identity.

If an `available` response cannot be proven coherent, mark that binding `integrity_failure` and withhold its `StatblockRenderer`.

Do not fetch latest revision by `statblockId` to repair a mismatch.

### E. Multi-binding behavior

Multiple exact attachments are not an error by themselves.

Examples may include:

```text
primary
phase
variant
alternate role
```

P3C display behavior:

- zero bindings: show truthful no-binding/no-mechanics state;
- one available binding: show its full exact statblock;
- multiple bindings: show every binding with explicit role/phase/variant/status; render every available exact revision;
- partial/unavailable bindings remain visible as statuses;
- never choose array[0], highest revision, “primary” by convention, or matching display name as a hidden active mechanics choice.

P4 may later ask the operator to choose the exact attachment to instantiate into Combat. P3C does not create that state.

### F. Surface-neutral mechanics extraction

Preferred topology, if the pinned base still resembles this design anchor:

```text
useExactThreatMechanics(resolution)
  owns exact hydration async lifecycle
  returns exact admitted mechanics state

ThreatMechanicsPanel
  pure/read-only mechanics rendering
  no Plan/Play action policy

ThreatSheetProjection (existing Plan/Build behavior)
  uses shared hook/panel
  keeps its current relationships / evidence / Plan action compatibility

PlayGraphObjectSheet (P3B)
  keeps Play-owned World + Runbook occurrence + relationships + Source composition
  inserts shared ThreatMechanicsPanel for authored Threats
```

Exact helper/component names may vary. The ownership split may not.

The shared mechanics primitive must not import:

```text
PlanSessionDescriptor
buildPlanGraphObjectActions
Play Run/Scene/Beat vocabulary
Combat APIs
```

It may import shared graph-reference types, Threat hydration transport, statblock contract/view-model helpers, and `StatblockRenderer`.

### G. Play composition order

P3B remains authority for the object-sheet table hierarchy.

For an authored Threat, the final native Play sheet should read approximately:

```text
1. World identity / concise accepted summary
2. In this Runbook
   - exact P3B occurrences / current-context highlight
3. Mechanics
   - loading / exact statblock(s) / honest binding statuses
4. Relevant World relationships
5. Source/evidence
6. Advanced/supporting exact IDs, validation/provenance as appropriate
```

Exact presentation may change if P3B lands a different tested hierarchy, but mechanics may not replace or hide the Play-owned Runbook context.

A Threat with unavailable mechanics is still a useful P3B World/Runbook/Source object sheet.

### H. Async selection safety

Mechanics hydration is keyed by the full exact Threat selection tuple.

Required stale-completion behavior:

```text
open X@G1
→ request X mechanics
→ open Y@G1 or close/switch surface
→ X response returns
→ discard X completion
→ never paint X mechanics under Y/current lease
```

Likewise:

```text
open X@G1
→ World head advances to G2
→ active X sheet remains scoped to G1
→ mechanics hydration remains G1
```

A fresh independent object open may capture G2 under P3B's normal graph rules.

### I. Failure/degradation matrix

| Condition | Required P3C result |
|---|---|
| exact single binding available | render exact immutable statblock |
| multiple exact bindings | render all explicit statuses/revisions; no hidden winner |
| no mechanics binding | World/Runbook/Source sheet remains; “No exact mechanics binding” |
| mechanics service unavailable / 503 | surrounding sheet remains; honest unavailable status |
| exact Threat not found | surrounding sheet remains; honest not-found status |
| response graph revision mismatch | integrity failure; no renderer |
| duplicate exact Threat hits | integrity failure; no renderer |
| available binding identity disagrees with returned revision | binding integrity failure; no renderer for that binding |
| revision resource incomplete | integrity failure; no renderer |
| source/evidence failure | existing P3B row-local behavior; mechanics unaffected |
| stale async completion | discarded |
| ordinary non-Threat object | existing P3B generic sheet; no Threat hydration |

### J. No mutation / P4 boundary

P3C object open and mechanics hydration may perform only existing read operations.

P3C must not:

```text
PUT Run progress
write Runbook/workspace document
write World Graph
adopt/edit mechanics binding
create/edit statblock revision
create Combat encounter/entity
write HP/initiative/conditions
persist active mechanics selection
infer quantity/team
```

No button labeled `Add to Combat`, `Start Combat`, or equivalent belongs in this slice.

### Observable path table

| Path | Predecessor/current behavior | Required P3C behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| Open ordinary P3B graph object | World+Runbook+Source sheet | unchanged generic sheet | Yes | P3B Play object sheet |
| Open authored Threat | P3B generic/inherited behavior only; not P3B mechanics evidence | same Play sheet + exact Mechanics section | Yes | Play composition + shared mechanics |
| Exact mechanics request | shared Threat sheet already hydrates exact tuple | reuse exact request from P3B graphScope | Yes | shared mechanics hook |
| Exact response scope | current shared selection checks exact response scope | preserve/fail closed | Yes | shared mechanics admission |
| Single binding | current full sheet renders exact revision | native Play renders exact revision | Yes | shared mechanics panel |
| Multiple bindings | current full sheet can render all | Play shows all, no first-winner selection | Yes | shared mechanics panel |
| Incomplete revision | current gate withholds renderer | same in Play | Yes | view-model/admission |
| Mechanics unavailable | current Threat sheet error state | mechanics section degrades; P3B sheet survives | Yes | Play composition |
| Threat changes during request | current component has cancellation/selection generation | stale completion cannot alter newer Play object | Yes | shared hook + surface lease |
| Relationship drill | P3B exact-origin graph revision | unchanged; mechanics for drilled Threat uses drilled exact graphScope | Yes | P3B/shared graphReference |
| Combat action | absent from P3C | remains absent | Yes | P4 boundary |

### Adversarial sequences

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| X@G1 open → hydration response says G2 | integrity failure; no statblock render | exact-scope test |
| X@G1 request → open Y → X resolves late | X completion discarded; Y sheet unchanged | stale-selection test |
| X has bindings A+B | both represented; no first/highest/default winner | multi-binding test |
| binding says statblock A/rev1/digest1 → revision payload says A/rev2/digest2 | integrity failure; renderer withheld | binding/revision coherence test |
| available binding returns incomplete revision shape | integrity failure; renderer withheld | complete-resource gate regression |
| Threat has no binding | Play still shows World + Runbook context + Source | degradation test |
| mechanics service down | same surrounding sheet; unavailable status only | degradation test |
| ordinary NPC with statblock-like relationship but not authored Threat | no P3C Threat hydration from convenience classification | Threat gate test |
| X@G1 → relationship drill Y@G1 → Y is Threat | Y mechanics hydrates with G1, never ambient G2 | relationship/mechanics scope integration test |
| Play unmounts while mechanics pending | completion discarded; shared Projection host not reopened | lease/unmount test |
| user inspects Threat | no Run/World/mechanics/Combat write calls | no-mutation test |

---

## §4 Files in scope — write lease

Pinned against design-anchor `bad7496677cb2f739935ebc454c153934994d160`. `apps/live-control-ui/src/playSurface/` did not exist on that base, so the designed Play paths were created rather than substituted. `ResolvedGraphObjectProjection.tsx` was not modified: Plan/Build still route authored Threats to `ThreatSheetProjection`. No `ResolvedGraphObjectProjection.test.tsx` exists; Build Threat routing is covered by `BuildReferenceObjectProjection.test.tsx`.

| Action | Path | Purpose |
|---|---|---|
| Create / Modify | `Docs/Plans/HANDOFF-PLAY-native-threat-mechanics.md` | pin base/status + evidence handback |
| Modify | `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` | P3C evidence row/disposition and successor state during implementation/state-sync as required |
| Modify | `apps/live-control-ui/src/playSurface/reference/PlayGraphObjectSheet.tsx` | compose exact mechanics into authored Threat sheet without losing P3B context |
| Modify | `apps/live-control-ui/src/playSurface/reference/PlayGraphObjectSheet.test.tsx` | Play hierarchy/degradation/non-Threat/no-mutation proof |
| Create if useful | `apps/live-control-ui/src/playSurface/reference/PlayThreatMechanicsSection.tsx` | Play-owned wrapper/label around shared mechanics primitive; no authority |
| Create if useful | `apps/live-control-ui/src/playSurface/reference/PlayThreatMechanicsSection.test.tsx` | Play composition and degradation proof |
| Create | `apps/live-control-ui/src/statblocks/projection/useExactThreatMechanics.ts` | extract exact hydration lifecycle from current Threat sheet into surface-neutral read seam |
| Create | `apps/live-control-ui/src/statblocks/projection/useExactThreatMechanics.test.tsx` | exact tuple/scope/stale selection/error/binding identity proof |
| Create | `apps/live-control-ui/src/statblocks/projection/ThreatMechanicsPanel.tsx` | render admitted exact binding statuses/revisions without Plan/Play policy |
| Create | `apps/live-control-ui/src/statblocks/projection/ThreatMechanicsPanel.test.tsx` | single/multi/partial/integrity renderer proof |
| Modify | `apps/live-control-ui/src/statblocks/projection/ThreatSheetProjection.tsx` | consume shared hook/panel while preserving current Plan/Build full Threat behavior |
| Modify | `apps/live-control-ui/src/statblocks/projection/ThreatSheetProjection.test.tsx` | regression proof for current consumers |
| Modify if identity check belongs here | `apps/live-control-ui/src/statblocks/projection/threatSheetViewModel.ts` | exact binding↔revision coherence admission only; no new mechanics model |
| Modify if above changes | existing owning `threatSheetViewModel` test | prove identity and complete-resource gate |
| Modify only if wrapper signature changes | `apps/live-control-ui/src/graphReference/ResolvedGraphObjectProjection.tsx` | preserve current shared Threat routing |
| Modify only if above changes | owning `ResolvedGraphObjectProjection` test | Plan/Build/shared routing regression |

### Bounded discovery exception

```text
Directory:
  apps/live-control-ui/src/

Maximum additional paths:
  4

Allowed path kinds:
  exact merged P3B path names replacing the expected Play paths above,
  existing Threat projection index/export file,
  existing statblock projection CSS if the neutral panel needs current styles,
  current owning shared Projection-host test needed to prove no stale reopen.

Decision rule:
  allowed only when the same §1 read-only exact-mechanics invariant is already owned
  by that path and no new workflow/authority is introduced.
```

If the final merged P3B topology requires more than two unanticipated Play production paths, update this handoff/write lease before CODE changes rather than stretching bounded discovery.

### Deliberate non-lease / read only

```text
apps/live_control_server/**
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/contracts/dungeonbuddy-statblocks-v1/**
apps/live-control-ui/src/statblocks/render/**        # unless a regression proves current renderer cannot consume valid exact revision; then STOP
apps/live-control-ui/src/combat*/**
apps/live-control-ui/src/tiptap/**
apps/live-control-ui/src/graphReference/resolveGraphReference.ts
apps/live-control-ui/src/graphReference/resolveGraphRelationship.ts
Docs/Design/ARCHITECTURE-playable-material-and-runtime.md
Docs/Design/ARCHITECTURE-surface-interaction-layer.md
Docs/Design/DESIGN-play-surface-projection.md
```

A required backend, wire-contract, generated statblock-contract, Combat, or Playable grammar production change is a stop report.

---

## §5 Explicitly out of scope / collision boundary

| Path / authority | Why P3C must not touch or claim it |
|---|---|
| P2 Run/manifest/progress/rebase | mechanics projection is read-only; Runtime provides table context only |
| P3A Runbook projection | consume existing exact admitted projection; do not change Playable grammar/body ownership |
| P3B graph scope/reference semantics | consume exact P3B resolution; do not invent another graph resolver |
| World Graph writes | Threat mechanics binding is read-only here |
| Statblock authoring/revision creation | exact immutable revision is input only |
| Mechanics binding adoption/edit | separate World/profile mutation workflow |
| Source persistence | P3B owns source/evidence read behavior |
| `ofConksThreatPlayBridge` | historical dogfood evidence only |
| active mechanics attachment selection | no durable selection needed merely to inspect; P4 owns any Combat-facing choice |
| Add to Combat | P4 |
| Combat HP/initiative/conditions | Combat runtime |
| encounter composition authoring | separate Playable capability; not necessary to inspect exact Threat mechanics |
| generic WorkObject refs/runtime/transactions | no evidence from this slice |
| DungeonMind kernel | no P3C kernel relevance |
| new DungeonMindDnD contract | existing exact mechanics binding is presumed sufficient; stop if false |

---

## §6 Implementation contract

```text
Input:
  exact P3B resolution:
    kind = resolved_graph
    graphNodeId = exact Threat node
    graphScope = exact {worldId,campaignId,scopeMode,revisionId}
    graphObject = World projection
  P3B Play occurrence context
  existing Threat query/hydration API
  existing immutable StatblockRevisionResourceV1 contract

Output:
  READY:
    P3B Play object sheet
    + exact Mechanics section
      + every exact binding/status
      + immutable rendered revision(s)

  DEGRADED:
    P3B Play object sheet remains
    + mechanics status: no binding / unavailable / not found / partial

  INTEGRITY BLOCKED FOR MECHANICS ONLY:
    P3B Play object sheet remains
    + mechanics integrity failure
    + no invalid StatblockRenderer call

Invariant:
  same §1 invariant
```

### A. Shared exact-mechanics state

Exact names may vary, but the neutral extracted seam should represent at least:

```text
ExactThreatMechanicsState {
  selectionTuple
  loadStatus
  mechanicsDisposition
  bindings[]
    relationshipEdgeId
    bindingId?
    role?
    phaseKey?
    variantLabel?
    statblockId?
    revisionId?
    definitionDigest?
    hydrationStatus
    revision?          # only when exact + complete + coherent
    message?
  message?
}
```

Do not add:

```text
activeBindingId
selectedForCombat
quantity
team
initiative
currentHp
```

Those would cross into P4/Combat semantics.

### B. Hydration lifecycle

One exact selection tuple owns one request generation.

Conceptual behavior:

```text
selection changes
→ clear prior admitted mechanics
→ increment generation / cancel prior request
→ request exact pinned tuple
→ admit only if selection key + mount/lease still current
→ normalize exact result
```

Response-loss retry is ordinary read retry; no persisted idempotency contract is needed.

### C. Binding/revision admission

Preserve existing complete revision validation and add explicit binding-locator coherence at the owning shared mechanics boundary if not already present by dispatch.

Available binding admission concept:

```text
binding.hydrationStatus == available
AND binding statblock/revision/digest are non-empty
AND returned revision is structurally complete
AND returned revision identifiers exactly equal binding identifiers
AND validation receipt digest equals revision digest
  → renderable exact revision

otherwise
  → integrity_failure / revision withheld
```

Do not silently downgrade an identity mismatch to “unavailable” if the server claimed `available`; that is an integrity failure.

### D. Mechanics rendering

Use existing `StatblockRenderer` and its current exact revision mode.

P3C does not create a second statblock presentation model.

The neutral mechanics panel may expose table-first ordering, but it must retain every exact binding status.

Recommended Play presentation:

```text
Mechanics
  [one exact statblock]

or

Mechanics
  Primary · available
    <StatblockRenderer>
  Phase 2 · available
    <StatblockRenderer>
  Variant · unavailable
    <status copy>
```

Advanced validation/provenance can remain collapsible.

### E. Plan/Build compatibility

The extraction is successful only if existing non-Play consumers retain behavior.

Current `ThreatSheetProjection` may remain the Plan/Build compatibility composition wrapper. It may continue to own:

```text
Plan-specific actions
current wrapper CSS
relationship list
current evidence/Advanced composition
```

but exact mechanics hydration/rendering should flow through the new neutral seam.

Do not move Plan actions into the neutral mechanics primitive just to avoid touching the wrapper.

### F. Play-specific composition

P3C adds no new object identity and no new Projection host registration.

P3B already opened the object and owns the sheet lease.

The Play wrapper supplies only presentation context around shared mechanics:

```text
Threat resolution
Runbook occurrences
current Run context
```

The shared mechanics primitive receives only the exact Threat resolution/scope it needs.

### G. Persistence / replay matrix

| Operation | Durable representation | Replay behavior | Ownership |
|---|---|---|---|
| exact mechanics hydration | none in Play | deterministic read for exact graph revision/Threat binding state | shared projection |
| rendered statblock | none | reconstruct from exact immutable revision | mechanics projection |
| Play mechanics section | none | reconstruct from P3B object + exact hydration | Play projection |
| active binding for Combat | **none in P3C** | n/a | P4 decision |
| mutable HP/etc | **none in P3C** | n/a | Combat |

No P3C persistence file is allowed.

---

## §7 Evidence required to merge

Every material clause must be proved at its owning boundary.

### Required proof table

| Guarantee / invariant clause | Owning boundary | Evidence class | Required proof |
|---|---|---|---|
| authored Threat gate only | shared Threat gate + Play composition | adversarial | ordinary non-Threat NPC/creature stays generic and makes no mechanics request |
| exact graph scope in hydration | shared mechanics hook | request contract | exact world/campaign/scope/revision from P3B resolution appears in request |
| exact Threat ID selection | shared mechanics hook/view model | contract | label mismatch/rename does not change node identity; duplicate exact hits fail |
| response revision mismatch fails closed | shared mechanics admission | adversarial | G1 request + G2 response → integrity failure; no renderer |
| binding↔revision triple coherence | shared mechanics admission | adversarial | locator/revision mismatch → integrity failure; invalid revision withheld |
| complete revision gate preserved | shared mechanics admission | regression | incomplete revision never reaches StatblockRenderer |
| single binding renders exact statblock | shared mechanics panel | component | correct exact revision rendered |
| multi-binding has no hidden winner | shared mechanics panel | adversarial | A+B both represented; no implicit active/default binding |
| partial/unavailable binding stays explicit | shared mechanics panel | component | status remains visible while available siblings render |
| no binding degrades truthfully | Play composition | degradation | World/Runbook/Source remains; mechanics says no binding |
| mechanics service failure is local | Play composition | degradation | surrounding P3B sheet remains on 503/transport error |
| Runbook context remains visible | Play object sheet | component | exact occurrence/current context survives loading/ready/error mechanics states |
| stale X completion cannot paint Y | shared hook + Play component | concurrency | X request → switch Y → resolve X; Y remains authoritative |
| relationship-drilled Threat keeps origin graph revision | P3B + mechanics integration | adversarial | X@G1 drill Y@G1 while ambient G2; Y mechanics request pins G1 |
| Plan/Build behavior preserved | existing ThreatSheetProjection | regression | current shared Threat tests remain green after extraction |
| neutral primitive has no Plan/Play policy | static/diff | review | no PlanSessionDescriptor/buildPlanGraphObjectActions/Scene/Beat imports in shared mechanics hook/panel |
| no mutation / no Combat | Play component/network mocks | contract | open/load/inspect makes no Run, workspace, World, statblock-write, or Combat mutation call |
| no dogfood bridge | static audit | review | no `ofConksThreatPlayBridge` or equivalent mapping enters product path |

### Focused frontend tests

Exact filenames must be updated to the actual pinned P3B topology before CODE begins.

Expected command shape:

```bash
cd apps/live-control-ui
pnpm exec vitest run \
  src/playSurface/reference/PlayGraphObjectSheet.test.tsx \
  src/playSurface/reference/PlayThreatMechanicsSection.test.tsx \
  src/statblocks/projection/useExactThreatMechanics.test.tsx \
  src/statblocks/projection/ThreatMechanicsPanel.test.tsx \
  src/statblocks/projection/ThreatSheetProjection.test.tsx \
  src/statblocks/projection/threatSheetViewModel.test.ts \
  src/buildSurface/reference/BuildReferenceObjectProjection.test.tsx
```

`src/graphReference/ResolvedGraphObjectProjection.test.tsx` does not exist on this base and was not created: the wrapper signature did not change. Build Threat routing remains covered by `BuildReferenceObjectProjection.test.tsx`.

Native `/play?run=` dogfood is not available on this base (`playSurface` had no product route). Owning Play proof is the new Play object-sheet / mechanics-section tests.

### Required predecessor regressions

Run the merged P3B tests that own:

```text
exact graph scope from admitted Run
both graph-native reference forms
Runbook occurrence context
exact-origin relationship drill
source/evidence degradation
one shared Projection host / lease safety
no mutation on object open
```

Run the existing Threat/statblock tests owning:

```text
exact Threat query/hydration
multi-binding behavior
complete revision gate
StatblockRenderer exact revision rendering
Plan/Build Threat projection
```

### Type/build gate

```bash
cd apps/live-control-ui
pnpm run typecheck
pnpm run build
```

If repository scripts require the existing explicit equivalents, record the exact commands actually run.

### Steward / diff gate

```bash
uv run python scripts/steward_preflight.py \
  --handoff Docs/Plans/HANDOFF-PLAY-native-threat-mechanics.md \
  --pr <N>

git diff --check
git diff --name-only <PIN_AFTER_P3B_STATE_SYNC>...HEAD
```

### Static boundary audit

At minimum:

```bash
rg -n "ofConksThreatPlayBridge|Add to Combat|create.*combat|PlanSessionDescriptor|buildPlanGraphObjectActions" \
  apps/live-control-ui/src/playSurface \
  apps/live-control-ui/src/statblocks/projection
```

Interpretation:

- no `ofConksThreatPlayBridge` production dependency;
- no P3C Combat mutation/action;
- Plan-specific types/actions may remain in the existing Plan/Build compatibility wrapper, but **not** in the newly extracted neutral mechanics hook/panel;
- Play may not import Plan policy merely to render mechanics.

### Minimal live / dogfood proof

Required because this slice is a table-facing mechanics projection.

Use one real or fixture-backed native Play Runbook at the pinned base containing an exact graph-native reference to an authored Threat with at least one exact mechanics binding.

Scenario:

```text
1. Open /play?run=<exact Run UUID>.
2. Navigate to the exact Scene/Beat/Choice/Option containing the Threat reference.
3. Open the Threat object sheet through P3B.
4. Confirm World identity + In this Runbook render before/while mechanics loads.
5. Confirm exact Mechanics renders from the pinned Threat/graph scope.
6. Confirm Source/relationships remain available in the same sheet.
7. Close and reopen without leaving the Play table position.
8. Repeat with mechanics service unavailable or no-binding fixture; confirm the object sheet remains useful.
9. If a multi-binding fixture exists, confirm every binding is explicit and no binding is silently selected for Combat.
```

Capture in the evidence packet:

```text
Run UUID
Runbook document/revision/SHA
Threat node ID
World/campaign/scope/graph revision
hydration result label
for every rendered binding:
  binding ID/role
  statblock ID
  revision ID
  definition digest
no Combat handle created
```

Do not paste copyrighted source prose into PR evidence.

### Baseline failure handling

If required existing Threat/renderer/P3B tests fail on the pinned base before P3C changes, run the same command on base and head and record:

```text
BASELINE_FAILURE
command
base result
head result
whether P3C adds a new failure
```

No silent waiver.

### Roadmap review required

P3C must explicitly answer:

```text
P3C_HOIST_OBSERVATION
- Did Play reuse the existing exact Threat query/hydration API without a new backend contract? yes/no
- Did exact mechanics identity remain (statblock_id, revision_id, definition_digest)? yes/no
- Did Play require any new DungeonMindDnD attachment semantic? yes/no
- Was a surface-neutral mechanics read/render seam extracted from the current Threat sheet? yes/no/already neutral
- Did any mechanics data become Playable or Run persistence? yes/no
- Did any active/default binding choice become necessary merely to inspect mechanics? yes/no
- Did any Combat mutation enter P3C? yes/no
- Does P4 Add to Combat remain independently useful and next? yes/no
- Did generic WorkObject/Runtime/DungeonMind relevance appear? none / exact future question
```

Expected disposition if implementation matches this design:

```text
ROADMAP_REVIEW — NO DESIGN CHANGE
P3C reused the already-established exact World→DungeonMindDnD/statblock mechanics
projection and only extracted/consumed a surface-neutral read/render seam for native Play.
Mechanics remain immutable/external, Play remains projection-only, and P4 remains the
first explicit Combat mutation boundary. No generic Runtime/work-object/kernel hoist.
```

If implementation evidence changes the P3/P4 ownership boundary, update the roadmap and canonical architecture consistently before PASS rather than hiding the change in the ledger.

---

## §8 Required review handback

Record:

1. `Review Cycle <N>` and exact PR/head SHA;
2. exact pinned post-P3B state-sync base SHA;
3. P3B predecessor implementation/evidence head, final reviewed head, merge SHA, and total review cycles;
4. §1 mission/invariant disposition;
5. exact Threat selection tuple used in proof;
6. exact hydration result and binding/revision identity triples used in proof;
7. §7 required vs produced evidence with provenance;
8. nano-commit/fix story;
9. actual changed paths vs §4/bounded discovery;
10. baseline failures/waivers;
11. prior review findings and closure on re-review;
12. exact disposition of shared mechanics extraction: hook/panel names and remaining Plan policy owner;
13. explicit confirmation all exact multi-bindings remain visible and no active/default binding is persisted;
14. explicit confirmation no Run/Runbook/World/mechanics authoring/Combat mutation occurs;
15. explicit confirmation no `ofConksThreatPlayBridge` enters the product path;
16. roadmap disposition and implementation/evidence head;
17. named successor P4 remains false/unimplemented.

One formal reviewer judgment against one distinct head SHA counts as one review cycle. Re-inspecting the same unchanged head does not create another cycle.

---

## §9 Acceptance rubric

PASS only if all are true:

- [ ] Exactly one independently useful capability: exact immutable Threat mechanics inside native Play object sheets.
- [ ] P3B remains the owner of graph object identity/scope, Runbook occurrence context, Source, relationships, and Projection-host interaction.
- [ ] Authored Threat gate is explicit; ordinary non-Threat objects do not trigger convenience mechanics hydration.
- [ ] Hydration uses the exact P3B world/campaign/scope/revision + Threat node ID.
- [ ] Response scope and exact Threat hit selection fail closed.
- [ ] Every rendered binding is exact and its statblock/revision/digest coheres with the returned immutable revision.
- [ ] Existing complete StatblockRevision resource validation remains enforced.
- [ ] No first/latest/display-name/default mechanics selection exists.
- [ ] Multi-binding Threats show all exact bindings/statuses.
- [ ] Missing/unavailable mechanics degrades locally while P3B World/Runbook/Source context remains useful.
- [ ] Stale async completion cannot paint mechanics into a newer object/surface lease.
- [ ] Existing Plan/Build Threat behavior remains green after shared extraction.
- [ ] Newly extracted shared mechanics code contains no Plan/Play product policy.
- [ ] No mechanics are copied into Runbook, Run progress, or another persistence file.
- [ ] No statblock/binding authoring occurs.
- [ ] No Add to Combat, Combat entity creation, HP, initiative, conditions, quantity, or team mutation occurs.
- [ ] No new backend/API/schema/DungeonMind/DungeonMindDnD contract is required.
- [ ] No `ofConksThreatPlayBridge` or equivalent campaign mapping enters product code.
- [ ] Actual paths stay within §4/bounded discovery.
- [ ] Focused tests + predecessor regressions + typecheck/build + diff/preflight are independently rerun and exact.
- [ ] Minimal live/dogfood proof demonstrates Play context + exact mechanics + local degradation without losing table position.
- [ ] Roadmap review keeps P4 as the first Combat mutation boundary unless evidence explicitly changes architecture.

REQUEST CHANGES for repairable implementation/evidence gaps.

STOP/rebrief for architecture/scope mismatch.

---

## Stop conditions

Stop and report instead of expanding if any of these appears:

- P3B is not implemented/merged/state-synchronized or P3C cannot be pinned to exact post-P3B `main`;
- merged P3B already satisfies the complete P3C invariant, making this slice redundant;
- P3B does not expose an exact resolved Threat + exact graphScope suitable for current Threat hydration;
- native Play mechanics requires a new backend Threat query/hydration endpoint or wire schema;
- exact mechanics attachment identity cannot be proven with current `(statblock_id, revision_id, definition_digest)` semantics;
- a valid exact revision cannot be rendered without modifying the generated statblock contract or `StatblockRenderer` ownership boundary;
- inspecting mechanics requires persistent active-binding choice, quantity, team, encounter, or Combat state;
- a requested UX action mutates Combat or is independently useful from mechanics inspection;
- mechanics binding adoption/editing becomes necessary;
- World Graph write behavior becomes necessary;
- P3C would require importing Plan action/session policy into new neutral mechanics code;
- a second ProjectionHost is required;
- P3B graph relationship/scope semantics would need to be duplicated in statblocks;
- generic WorkObject refs, generic Runtime, or DungeonMind kernel changes become necessary;
- another active lane owns required shared statblock/P3B paths and cannot be serialized cleanly.

Report:

```text
Stop condition:
Invariant clause affected:
Why current P3C mission cannot absorb it:
Required evidence now missing:
Affected paths/ownership layers:
Proposed successor/re-brief:
State-authority update needed:
```

---

## §10 Successor boundary

If P3C lands without contradictory evidence, the next independently useful slice is the roadmap's P4 capability:

```text
P4 — explicit Add to Combat from exact Threat mechanics
```

P4 should begin from the exact authority already visible in the native Threat sheet:

```text
exact Threat World identity
+ exact mechanics binding(s)
+ exact immutable StatblockRevision identity
        ↓ explicit operator action
choose exact attachment when ambiguous
choose quantity/team/encounter inputs explicitly
        ↓
Combat mutation
        ↓
Combat owns mutable HP / initiative / conditions
```

P4 must never use first/latest/display-name mechanics selection.

P3C must not pre-build P4 merely because it now has exact mechanics in hand.
