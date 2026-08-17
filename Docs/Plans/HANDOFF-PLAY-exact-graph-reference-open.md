---
pr_body_template: |
  ## Review-repair pointer
  - Workstream: Playable Architecture Graduation / P3
  - Flow: PLAY
  - Artifact: Docs/Plans/HANDOFF-PLAY-exact-graph-reference-open.md
  - Original design PR: #615
  - Original design head: d5e51d0bea3ba53e9c6d3f278f96067026e4e65d
  - Accidental merge: a2723696b2073a49ee74d2bab903a747f20ad846
  - Formal post-merge review: Cycle 1 / review 4953312872
  - Disposition: REBRIEF REQUIRED — DO NOT DISPATCH CODE

  This file is a reviewed design record, not an implementation handoff.
---

# HANDOFF — exact World Graph reference opening in Play

**Created:** 2026-08-17  
**Reviewed / repaired:** 2026-08-17  
**Status:** **POST-MERGE REVIEWED — NON-DISPATCHABLE / REBRIEF REQUIRED.**  
**Canonical path:** `Docs/Plans/HANDOFF-PLAY-exact-graph-reference-open.md`  
**Workstream:** `Playable Architecture Graduation / P3`  
**Flow / owner:** `PLAY`  
**Original design PR:** #615 — `PLAY: design exact World Graph reference open`  
**Original design head:** `d5e51d0bea3ba53e9c6d3f278f96067026e4e65d`  
**Accidental merge:** `a2723696b2073a49ee74d2bab903a747f20ad846`  
**Formal post-merge review:** Cycle 1, review `4953312872`  
**Dispatch authority:** **none** — `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` correctly leaves the next P3 implementation handoff unselected.

> Repository law: [`AGENTS.md`](../../AGENTS.md). Graph authority: [`ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md). Playable authority: [`ARCHITECTURE-playable-material-and-runtime.md`](../Design/ARCHITECTURE-playable-material-and-runtime.md). Shared host authority: [`ARCHITECTURE-surface-interaction-layer.md`](../Design/ARCHITECTURE-surface-interaction-layer.md).

---

## 0. Review disposition

PR #615 was intended to be reviewed before merge and was merged accidentally. The post-merge review therefore treats its exact head as a design proposal already present on `main`, not as accepted CODE dispatch authority.

The useful architectural direction survives:

> A Play consumer must never treat transitional corpus fallback, labels, aliases, current-head retry, or an incomplete/mismatched graph scope as exact World Graph authority. When Play eventually opens a graph-backed object, it must consume one exact revision-pinned graph resolution through the existing shared Projection host and keep World/Source/Playable/Runtime/Mechanics ownership separate.

The implementation contract from the original #615 body does **not** survive review. No code agent may dispatch from the pre-review §4/§7 text in PR #615 or Git history.

### Cycle 1 findings

1. **Owning-boundary mismatch.** The mission claimed a native Play surface capability while current runtime has no native `/play` route or mounted Play entry surface. Component/helper evidence cannot prove a surface workflow that does not exist.
2. **False P3C exact history.** The original closeout named nonexistent SHA `32cee38b53d4d24337bffa20560aace01b54556a`.
3. **Invented predecessor vocabulary.** The original handoff named shared types that are not present in current `graphReference/types.ts`.
4. **Dispatch authority remains open.** The Playable roadmap still says P3 must be decomposed and the next implementation handoff is unselected. That is correct until a replacement design is accepted and synchronized.

Non-blocking cleanup from the review is also incorporated here: #615 changed both this file and `HANDOFF-PLAY-native-threat-mechanics.md`; the original statement that the design PR owned only this new file was inaccurate.

---

## 1. Retrospective atomic document sync — corrected prior completed slice

The predecessor synchronized by #615 was P3C / PR #608. The exact repository-backed closeout is:

```text
P3C — native exact Threat mechanics
PR: #608 — PLAY: project exact Threat mechanics
implementation/evidence head: 9b6918d66643094c06821f354f9afb80322f39ac
final reviewed / repair head: 6b0b177f08a09c2b1f8c8ff9a1eb71b450b57087
merge: 53aaf9a566cfd40dd09f1a4c9723276cefa2a98a
formal review cycles: 2
status: MERGED / HISTORICAL
```

`9b6918d66643094c06821f354f9afb80322f39ac` is the implementation/evidence commit recorded by the living Playable roadmap. `6b0b177f08a09c2b1f8c8ff9a1eb71b450b57087` is the final reviewed repair head. They are intentionally different identities.

P3C proved a surface-neutral exact Threat mechanics read/render seam and an early Play-owned `PlayGraphObjectSheet` / `PlayThreatMechanicsSection`. It did **not** prove native Play routing, graph-reference click/open, Runbook occurrence derivation, a mounted Play Projection-host workflow, or Add-to-Combat.

The predecessor handoff `Docs/Plans/HANDOFF-PLAY-native-threat-mechanics.md` must carry the same corrected exact facts. Historical review/design prose in that file remains evidence and is not current dispatch authority.

### Process rule going forward

Current `AGENTS.md` owns the generalized behavior:

- implementation handoffs identify the mutable authorities for their **already-completed predecessor**;
- those facts ride with the consuming implementation PR when truthfully knowable;
- an in-flight slice is never pre-marked complete and no future merge/review facts are invented;
- facts knowable only after a merge normally travel with the next dependent implementation PR, or through a guarded steward sync when delaying truth would materially mislead authority.

This reviewed design record does not invent a competing process rule.

---

## 2. Current repository truth

### Product topology

At the reviewed/repaired repository state:

```text
apps/live-control-ui/src/App.tsx
  routes: index | surface | tiptap-callout-spike | plan | ingest | build
  no native /play route

apps/live-control-ui/src/playSurface/
  reference/
    PlayGraphObjectSheet.tsx
    PlayGraphObjectSheet.test.tsx
    PlayThreatMechanicsSection.tsx
    PlayThreatMechanicsSection.test.tsx
```

Therefore `PlayGraphObjectSheet` is reusable Play-owned composition code, but it is not by itself proof that a GM can perform a native Play workflow.

### Shared host ownership

`ARCHITECTURE-surface-interaction-layer.md` remains authoritative:

- the app-scoped Surface Interaction Layer owns the single shared Projection host;
- surfaces publish/bind capabilities into that host;
- Play must not create a private second host;
- surface changes and lease changes must prevent stale async completion from mutating the wrong active projection.

### Campaign Supergraph lane

`Docs/Plans/PR-TRACKER-campaign-supergraph.md` still retains `PR009 Play projection migration` as a valid `READY` parallel product capability. This reviewed record does not consume or close that umbrella. The next Playable P3 implementation capability remains to be selected.

---

## 3. Exact current predecessor vocabulary

The original #615 handoff incorrectly described types that do not exist in the current shared contract. The actual authority is `apps/live-control-ui/src/graphReference/types.ts`.

### Exact graph scope

```ts
interface ExactGraphReferenceScope {
  worldId: string;
  campaignId: string;
  scopeMode: "campaign" | "world";
  revisionId: string;
}
```

### Resolution union

```text
GraphReferenceResolution
  kind = resolved_graph
    locator: string
    reference: RunbookReferenceAttrs | null
    graphNodeId: string
    graphObject: GraphObjectCardViewModel
    graphScope: ExactGraphReferenceScope
    projectionState: GraphReferenceProjectionState | null

  kind = resolved_corpus_fallback
    fallback: GraphReferenceCorpusFallback

  kind = ambiguous
  kind = unresolved
  kind = error
```

### Projection binding

```text
GraphReferenceProjectionBinding
  resolverState
  resolveRelationship(relationship, originatingScope?)
  openResolvedReference(resolution, projectionState?)
  openTool(toolId)
```

There is no current shared `GraphReferenceContext`, `ResolvedWorldGraphLocator`, `GraphReferenceStatus`, or `GraphResolutionSource` type in this contract. `locator` is an opaque string, not a typed `{ source, worldId, ... }` authority object.

For an eventual strict Play consumer, graph-vs-corpus authority is determined by the `GraphReferenceResolution.kind` discriminator. Exact World Graph identity/scope comes from:

```text
resolution.kind == resolved_graph
resolution.graphNodeId
resolution.graphScope.worldId
resolution.graphScope.campaignId
resolution.graphScope.scopeMode
resolution.graphScope.revisionId
```

No future implementation should manufacture parallel wire vocabulary merely to resemble the rejected #615 design prose.

---

## 4. Reusable design constraints from #615

These are design input for the P3 rebrief; they are **not** an implementation lease.

### Exact-only Play admission policy

If a future Play-owned capability consumes a requested durable graph node ID plus one active exact scope, safe admission is:

```text
resolution.kind == "resolved_graph"
AND resolution.graphNodeId == requestedNodeId
AND resolution.graphScope == active exact scope field-for-field
AND the request/lease that produced the result is still current
```

Every other result is non-openable as exact World Graph authority for that Play capability:

```text
resolved_corpus_fallback
ambiguous
unresolved
error
stale async completion
node ID mismatch
world mismatch
campaign mismatch
scopeMode mismatch
revision mismatch
```

Important: this is a **Play consumer policy**. It does not authorize removing `resolved_corpus_fallback` from the shared resolver because existing non-Play consumers may still use that transitional result honestly.

### Identity rules

- durable `graphNodeId` is identity;
- labels and aliases are presentation/evidence, never admission repair;
- no first-ranked or display-name selection;
- no current-head retry after an exact pinned mismatch;
- `revisionId` must be present because `ExactGraphReferenceScope` requires it;
- relationship drill must preserve originating exact scope when the shared binding supports it.

### Authority rules

A reference-open read must not itself:

- write World Graph or Source;
- write Playable Material or Run runtime;
- persist mechanics selection;
- create or mutate Combat;
- author mechanics/statblocks;
- create a second Projection host;
- copy a graph object body into Play persistence.

### Stale completion rule

Any future mounted capability must prove the dangerous sequence at the boundary that actually owns it:

```text
start exact resolve/open for X@G1
→ active surface/context/lease changes
→ old X@G1 completion arrives
→ old completion is discarded
→ current shared Projection host remains authoritative
```

`PlayGraphObjectSheet` already contains a separate relationship-navigation generation guard keyed by:

```text
graphNodeId + worldId + campaignId + scopeMode + revisionId
```

That P3C behavior is predecessor evidence; it does not by itself prove a future external Play reference-open admission workflow.

---

## 5. What the original #615 implementation contract may NOT be used for

The following are retired as dispatch instructions:

- creating `PlayExactGraphReference.tsx` merely because #615 named it;
- treating component + shared-host tests as proof of a native Play surface workflow;
- treating the old #615 §4 bounded discovery as an active write lease;
- treating its old §7 as merge evidence requirements;
- adding `/play` opportunistically to rescue the old invariant;
- updating the Playable roadmap to call #615 the selected implementation slice;
- inventing the rejected predecessor types from the old §2/§6 tables.

The original 500-line pre-review design remains in PR #615 / Git history as evidence of the rejected proposal. This repaired file is the current interpretation.

---

## 6. Required P3 rebrief before CODE dispatch

The steward must re-anchor current `main`, inspect active Play/Surface lanes, and decompose P3 again. Exactly one implementation-sized capability must be selected with one invariant and an owning-boundary proof that exists in current topology or is itself the product outcome of the selected slice.

The rebrief must answer:

1. What exact user/caller-visible outcome exists after the slice?
2. Where is the boundary that owns that outcome today or will own it as part of the same single capability?
3. What exact Playable / Run / World / Source / Mechanics authorities does it consume?
4. Which current shared Projection-host seam is reused?
5. What remains explicitly false afterward?
6. What exact §4 paths are leased?
7. What adversarial sequence can falsify the invariant, and which test exercises that owning boundary?
8. Does the capability actually need the exact-reference-only policy retained above?
9. Does implementation evidence justify any shared Buddy or DungeonMind hoist? Default: no.

Candidate P3 outcomes must be compared by independence/usefulness rather than old document order. P3C being merged and P4 being designed do not create a waterfall.

Possible remaining product capabilities include, without selecting one here:

```text
native Run / Scene / Beat table projection
native Play surface / Runbook mounting
exact graph-reference opening from a real mounted Play interaction
Runbook occurrence derivation
NPC/location/item Play Object Sheets at a mounted boundary
richer Source/Advanced detail
P4 Add to Combat (separate mutation capability)
```

---

## 7. Mutable authority state after this review repair

`Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` remains correct and should not be churned merely because #615 merged accidentally:

```text
P2: COMPLETE
current phase: P3 — native Play projections
next implementation-sized capability: UNSELECTED
next implementation handoff: UNSELECTED
```

`Docs/Plans/PR-TRACKER-campaign-supergraph.md` retains `PR009 Play projection migration` as a parallel `READY` umbrella; this repair does not change the Campaign Supergraph critical path.

Before a replacement P3 CODE dispatch, its accepted design must synchronize the Playable roadmap's mutable current-sequence fields so repository dispatch authority and the selected handoff agree.

---

## 8. Cleanup PR write set

The review-repair lane owns only:

```text
Docs/Plans/HANDOFF-PLAY-exact-graph-reference-open.md
Docs/Plans/HANDOFF-PLAY-native-threat-mechanics.md
```

Purpose:

1. convert this accidentally merged design into a reviewed, explicitly non-dispatchable record grounded in actual runtime types/topology;
2. repair P3C's false exact evidence SHA without rewriting its historical implementation/review body.

No runtime, architecture, Campaign Supergraph tracker, or Playable roadmap change is part of this cleanup.

---

## 9. Acceptance for this review repair

The cleanup is complete only when:

- [ ] this file cannot be mistaken for CODE dispatch authority;
- [ ] #615 exact head, accidental merge, formal review identity, and Cycle 1 disposition are recorded;
- [ ] P3C implementation/evidence head is exactly `9b6918d66643094c06821f354f9afb80322f39ac`;
- [ ] P3C final reviewed/repair head is exactly `6b0b177f08a09c2b1f8c8ff9a1eb71b450b57087`;
- [ ] P3C merge is exactly `53aaf9a566cfd40dd09f1a4c9723276cefa2a98a` and review cycles = 2;
- [ ] predecessor vocabulary matches current `graphReference/types.ts`;
- [ ] no native `/play` workflow is claimed on current topology;
- [ ] the exact-reference-only policy is retained as design input, not implementation proof;
- [ ] the Playable roadmap remains P3 / next implementation capability unselected;
- [ ] no runtime or stable architecture path changes.

After this cleanup is reviewed and merged, re-anchor P3 and select a replacement implementation slice. Do not dispatch CODE from this file.
