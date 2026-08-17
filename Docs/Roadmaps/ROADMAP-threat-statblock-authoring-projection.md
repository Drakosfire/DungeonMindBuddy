# Roadmap — Threat + Statblock Domain

**Status:** ACTIVE STRATEGIC ROADMAP — publication/query/projection foundation complete  
**Updated:** 2026-08-16  
**Repository verification anchor:** `e504310f71863604267637eea6209dcbea04f929`  
**Implementation/status tracker:** [`../Plans/PR-TRACKER-threat-statblock-authoring-projection.md`](../Plans/PR-TRACKER-threat-statblock-authoring-projection.md)  
**Lifecycle decision:** [`../Design/DECISION-grounded-authored-world-object-lifecycle.md`](../Design/DECISION-grounded-authored-world-object-lifecycle.md)

This roadmap preserves the Threat/Statblock product direction and authority boundaries. The tracker owns exact status. Newer Campaign Supergraph and Playable/Play roadmaps own whole-world CUTOVER, placement, and combat sequencing; this roadmap must not duplicate those queues.

## 1. Product goal

DungeonBuddy should carry one coherent Threat identity from authored mechanics through governed campaign publication and useful GM-facing consumption:

```text
ThreatDraft
→ generated candidate
→ local working copy
→ authoritative validation receipt
→ accepted immutable statblock revision
→ governed publication operation / identity decision / reviewed proposal
→ durable Threat + exact ThreatStatblockBinding
→ exact query + mechanics hydration
→ campaign-facing Threat projection
→ Playable placement / Play runtime through the owning Play architecture
```

The important invariant is not a single giant object. It is exact identity across boundaries:

```text
World Graph Threat node ID
statblock ID + immutable revision ID + definition digest
binding identity
source / publication evidence
later Playable placement identity
later runtime instance identity
```

## 2. Authority boundaries

- DungeonMind owns generated statblock contract semantics.
- Buddy owns draft orchestration, validation presentation, accepted-mechanics persistence, publication operations/proposals/receipts, and Threat/statblock presentation.
- The World Graph owns governed campaign identity and durable `uses_statblock` relationship truth.
- Saved mechanics are not automatically published.
- Publication is not placement.
- Placement is not runtime state.
- Runtime HP/conditions never mutate World Graph truth or immutable mechanics.
- Exact consumers pin exact revision identity; no `latest` fallback.

## 3. Completed foundation

The publication-first spine that this roadmap originally sequenced is now landed:

| Capability | Evidence |
|---|---|
| Draft → generation → semantic rendering/editing/validation | SBW01–05 through PR #404 |
| Immutable accepted mechanics | SBW07 through #409 |
| Revise contract/lineage foundation | SBW06 through #439 |
| Exact external statblock resource + binding | SBW08 / #457 |
| Durable publication operation | SBW09a / #462 |
| Explicit Threat identity decision | SBW09b / #467 |
| Durable no-write reviewed proposal | SBW09c1 / #478 |
| Immutable operation→revision recovery lookup | SBW09c2a / #476 |
| Proposal-bound commit/receipt/recovery/verification | SBW09c2b / #491 |
| Exact Threat query + mechanics hydration + Hermes read tool | SBW10a / #502 |
| Exact-revision Threat projection | SBW10b / #504 |
| Normal Workbench publication bridge dogfood | PR #508 |
| Verified resident World Graph read optimization | PR #509 |
| Campaign-useful Threat parchment/glance + shared Plan/Build graph lens | PR #512 |

The old statements “no durable Threat commit,” “no Hermes hydration,” and “no exact Threat projection” are therefore historical and must not be used for new dispatch.

## 4. Current Threat/Statblock lane — authoring and usability

Current domain-specific work is intentionally smaller than the old publication program. Exact statuses live in the tracker.

### Near-term bounded usability

- stable editable/copyable Hermes markdown artifact;
- GM-facing Revise-with-AI primary flow;
- truthful immediate Hermes long-turn/liveness UX;
- Build publication of the existing Workbench through the shared Tool Host (root backlog until sequenced elsewhere).

### Must decompose before dispatch

- grounded authored-object context vs durable “Develop as Threat” action;
- response evidence chips vs explicit query-anchor chips;
- authoring-library read/browse vs mutation/update;
- editor expansion one mechanic family at a time;
- Hermes telemetry capture vs aggregate reporting;
- exact accepted-locator revise semantics vs revise UX.

### Deferred

- immutable child mechanics revision and comparison;
- explicit binding adoption to a newer immutable revision;
- media/image/3D work;
- second-domain proof of any generalized authored-object architecture.

## 5. Sequencing delegated to current owners

### Whole-world DungeonMind adoption / authority CUTOVER

Owned by [`../Plans/PR-TRACKER-campaign-supergraph.md`](../Plans/PR-TRACKER-campaign-supergraph.md) and its current CUTOVER handoffs. Threat/Statblock per-object bridging is evidence for that work, not a second cutover authority.

### Playable placement and Play runtime

Owned by the current Playable/Play architecture and roadmap stack, including:

- [`ROADMAP-playable-hoist-dungeonmind-kernel.md`](ROADMAP-playable-hoist-dungeonmind-kernel.md)
- [`ROADMAP-play-world-object-combat-projection.md`](ROADMAP-play-world-object-combat-projection.md)

Historical `AOW03/AOW04`, `COMBAT01`, and `SBW15` labels remain useful design ancestry but are not dispatch authority from this roadmap. Reconcile any surviving capability against the current Play owner before creating work.

## 6. Product proofs

### Accepted-mechanics proof

The normal create → generate → edit → validate → accept → reload/reopen loop is established. Regressions are defects, not reasons to reopen the foundation sequence.

### Publication/query/projection proof

The product can publish an accepted Threat through the governed operation/identity/proposal/commit chain, recover durable publication outcome, query/hydrate exact mechanics, and render an exact campaign-facing Threat projection. PR #508 supplied a real Workbench publication path; #512 supplied the shared Plan/Build campaign-facing presentation seam.

### Remaining magic-moment interpretation

The original `MAGIC-D3` program is now a **partial product proof**, not a blocked infrastructure gate. Remaining authoring convenience, Hermes liveness, placement, and combat concerns are separately owned capabilities.

## 7. Roadmap hygiene

- This document owns strategic direction, not exact READY/DOING status.
- `PR-TRACKER-threat-statblock-authoring-projection.md` owns domain execution status.
- Campaign Supergraph and Playable/Play authorities own their own sequences; this roadmap only links them.
- Merged implementation narrative stays in PRs/handoffs rather than being replayed here.
- Any item older than 30 days must be re-verified against current `main` before dispatch.
