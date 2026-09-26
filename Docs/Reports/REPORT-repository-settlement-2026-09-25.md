# Repository Settlement Report — 2026-09-25

**Status:** SETTLEMENT DESIGN / authority repair
**Repository:** `Drakosfire/DungeonMindBuddy`
**Re-anchor:** `main@9473244f57e7845928fc47225fd08863ea85804b`
**Perspective:** cross-repository / OverMind settlement
**Scope:** documentation authority, ownership boundaries, completed scaffolds, immediate-source set

## Re-anchor

Observed current open PR topology at design time:

```text
#753        CON-READY / WorldKeeper consumer-proof design
#755-#761   existing stacked UI presentation-design chain
```

The UI stack has partially drained. PR #761 still explicitly leases
`Docs/Roadmaps/ROADMAP-campaign-supergraph.md` to replace the active UI sidequest
checkpoint. This settlement therefore does **not** take a competing write lease
on that path.

## Finding 1 — CUTOVER closed but the mutable authority sync did not

The repository contains terminal implementation evidence that predates the
current tracker/status claims:

```text
Buddy #665  mounted graph-engine excision merged
Buddy #667  physical legacy graph-engine deletion merged
Buddy #668  CUTOVER closure authority report merged
```

#668's closure report explicitly listed the Campaign tracker, Campaign roadmap,
continuity status guide, and their source mirrors as the authority sync set.
The current tracker/status still describe D.3B as live.

This is post-success settlement debt, not unfinished implementation.

## Finding 2 — World architecture survived while runtime ownership moved

The durable model remains useful:

- one World identity domain;
- campaign-scoped truth;
- immutable revisions;
- provenance/evidence;
- explicit write authority;
- projections rather than duplicate stores;
- agents are not privileged writers.

The implementation ownership is now:

```text
DungeonBuddy  interaction / reversible intent / projection / AgentRuntime
WorldKeeper   semantic World-change coordination
DungeonMind   durable identity / provenance / revision / publication / reads
```

The Campaign architecture is retained and re-anchored to that ownership. The
old Buddy Graph Kernel placement is historical.

## Finding 3 — two construction scaffolds outlived successful implementation

### Surface Interaction hoist

`PLAN-surface-interaction-hoist-build-first.md` still says SI-01 is NEXT even
though DOGFOOD-POLISH closed the Plan/Build interaction/document baseline on
2026-08-11.

Disposition: archive body + forwarding stub.

### Hermes campaign-authoring foundation

The July Hermes reset still presents Hermes as the product framing. Current
architecture owns the Agent boundary in Buddy's `AgentRuntime`; Hermes is the
current adapter.

Disposition: archive body + forwarding stub to current Agent/source-to-World
authorities.

## Finding 4 — immediate-source export was internally stale

The canonical source index had advanced beyond its checked-in export mirror, and
the clean bundle still promoted frozen/superseded construction documents.

Disposition:

- rebuild the manifest around current domain authorities;
- remove frozen Campaign tracker/status and stale Campaign roadmap from the
  clean export;
- remove SI hoist/Hermes foundation from the clean export;
- add source-to-World and AgentRuntime/context decisions;
- keep the user-managed Project Sources snapshot date unchanged until the
  operator actually refreshes it.

## Changes in this settlement

1. Re-anchor Campaign architecture ownership.
2. Freeze Campaign tracker and continuity status as historical records.
3. Retire Surface Interaction hoist plan.
4. Retire Hermes campaign-authoring foundation index.
5. Reconcile AgentRuntime decision with accepted WorldKeeper authority.
6. Replace the graph document audit with a current settlement ledger.
7. Refresh README and the design-agent manifest/export.
8. Land a BLOCKED successor for physical Campaign-roadmap retirement.

## Deliberate remaining falsehood

`ROADMAP-campaign-supergraph.md` still physically carries a stale canonical
header because #761 currently owns that path inside the remaining UI stack.

That is not permission to use it.

The blocked handoff
`Docs/Plans/HANDOFF-SETTLEMENT-retire-campaign-supergraph-roadmap.md`
activates only after #761 merges/closes and a fresh re-anchor confirms no active
write lease remains.

## Settlement invariant

After this change, a fresh contributor following README → source manifest →
domain authority cannot mistake a completed Buddy migration scaffold for
current implementation sequence or durable World ownership.

## Verification

Review must prove:

- no file changed that is in the observed #753 or #755–#761 write sets;
- canonical/export copies are byte-identical for every changed mapped source;
- frozen/superseded files are absent from the clean export mapping;
- tracker/status contain explicit no-dispatch banners;
- SI/Hermes historical bodies remain recoverable from archive paths;
- architecture names DungeonMind/WorldKeeper/Buddy ownership truthfully;
- `git diff --check` / Markdown/link hygiene passes in the implementation checkout.

This report changes no runtime behavior, source data, database state, or product
contract.
