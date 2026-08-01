# Current State — World Graph Continuity Spine

**Status:** Current-state guide; not a replacement for architecture or sequencing authority  
**Updated:** 2026-07-28 after PR380C / GitHub #443 merged  
**Architecture:** [`ARCHITECTURE-campaign-supergraph.md`](ARCHITECTURE-campaign-supergraph.md)  
**Roadmap:** [`../Roadmaps/ROADMAP-campaign-supergraph.md`](../Roadmaps/ROADMAP-campaign-supergraph.md)  
**Tracker:** [`../Plans/PR-TRACKER-campaign-supergraph.md`](../Plans/PR-TRACKER-campaign-supergraph.md)  
**Integration roadmap:** [`../Roadmaps/ROADMAP-cross-surface-statblock-demo.md`](../Roadmaps/ROADMAP-cross-surface-statblock-demo.md)
**UI shell (cross-boundary):** [`ARCHITECTURE-surface-interaction-layer.md`](ARCHITECTURE-surface-interaction-layer.md)

## Why this exists

DungeonBuddy's graph work now spans storage, extraction, Graph Review, Recap, Build, Plan, Hermes, and eventually Play. This document is the concise operational map: what owns truth, how reads and writes move, what PR380A/B/C established, and what remains false.

## Objective in one sentence

Turn raw campaign prose and authored records into governed, correctable World Graph memory that every surface and Hermes can use through exact identity and revision-aware projections, without giving any surface or agent silent write authority.

## Authority stack

1. `ARCHITECTURE-campaign-supergraph.md` — invariants and ownership.
2. `ROADMAP-campaign-supergraph.md` — phases and critical path.
3. `PR-TRACKER-campaign-supergraph.md` — active implementation order.
4. Owning design contracts and current handoffs — one bounded capability.
5. Tests, dogfood, and reports — evidence that the contract is true.
6. Historical handoffs and old roadmaps — context only.

## Durable model

```text
one world
→ one World Supergraph and graph head
→ campaign-scoped assertions/evidence/chronology/visibility
→ immutable revisions
→ many bounded projections
→ many surfaces
```

The graph owns durable object identity, relationships, attributes, evidence links, authority metadata, and replayable correction history. Sessions are projection focus, not graph ownership. Campaigns scope assertions; they do not create a second copy of Mirathorn by default.

## Write path

```text
Source Artifact / authored record
→ exact ExtractionRun and candidate assertions
→ Graph Review prepare against current parent revision
→ game-facing review and exact assertion selection
→ sealed proposal
→ explicit GM confirm
→ Kernel contribution / identity resolution / validation
→ immutable committed revision
→ atomic graph-head advancement
→ terminal confirm receipt
→ exact committed projection reload
```

### Write authority rules

- Ingest proposes; it does not publish.
- Graph Review is the human reference confirmation surface.
- The sealed proposal, selected assertion IDs, parent revision, world/campaign/session scope, and receipt identity form the authority boundary.
- Stale proposals fail closed.
- A terminal receipt means publication is known. A subsequent read failure may retry the exact committed projection, never re-confirm.
- Agents may later prepare or propose through typed capabilities, but they must reuse this protocol and cannot bypass GM confirmation.
- Worldbuilding draft elevation is a separate authority decision; draft lore must not be relabeled as played canon to make promotion convenient.

## Read path

```text
World Graph revision (head or explicit pin)
→ projection request
   worldId
   campaignId
   focus
   admissibility
   scope mode
   exact node IDs / query
   bounds
→ projection / retrieval result
→ surface or Hermes
→ graph-admitted source anchors for evidence
```

### Read authority rules

- Graph objects are addressed by durable IDs.
- A request reads one coherent revision.
- Visibility and campaign scope fail closed.
- Relationships resolve by exact endpoint IDs within the same admitted projection.
- Hermes discovers facts through graph retrieval and opens only admitted source anchors.
- A graph miss produces a coverage diagnostic or abstention, not arbitrary Markdown search.
- Cache and conversation history may improve continuity or latency; neither is authority.

## Candidate versus committed authority

Before confirmation, Graph Review presents an unpublished candidate review lens. After a terminal receipt for the exact review binding, candidate authority ends.

```text
candidate
  preview/review material for an exact run
  may be accepted, rejected, unresolved, or inspect-only

committed
  exact World Graph revision named by the terminal receipt
  affected objects opened by exact durable IDs
  survives graph reload/retrieval
```

The product must not blend these into a hybrid view or use candidate labels to stand in for missing durable objects.

## What PR380A/B/C established

### PR380A / GitHub #412 — recap projection contract

Canonical recap prose, mentions, node views, relationships, evidence, and focus metadata are produced from an exact World Graph snapshot plus the selected canonical recap. Recap no longer needs a session preview graph as runtime authority.

### PR380B / GitHub #437 — shared object consumption

Recap and Build consume the same exact-ID World Graph object contract. Recap prose chips, relationship traversal, and Build's pointer-only context resolve durable objects without importing candidate or latest-ingest authority.

### PR380C / GitHub #443 — post-confirm authority transition

Graph Review now owns committed-transition state for a typed review binding. On a terminal receipt it:

- freezes the binding and validates prepared/receipt identity;
- requests the receipt's exact world, campaign, focus, and committed revision;
- replaces candidate presentation with committed loading/ready/error state;
- opens affected objects by exact ID;
- preserves the receipt on projection failure;
- retries only the exact committed read;
- rejects stale completion or a receipt resolving after the active binding changed;
- blocks load actions while confirmation is in flight.

This closes the post-confirm authority lie. It does not yet replace the pre-confirm preview-union candidate lane or persist receipts across browser reload.

## Current surface state

| Surface | Current graph role | Remaining gap |
|---|---|---|
| Ingest | Creates exact extraction candidates and routes to Graph Review | Primary workflow still carries preview-union-era candidate/materialization concepts |
| Graph Review | Prepares/selects/confirms; post-confirm reads exact committed revision | Direct exact-run candidate presentation and preview-union retirement |
| Recap | Reads canonical prose through World Graph recap projection | Shared coordinator/cache/invalidation polish |
| Build | Reads an incoming exact graph object as pointer-only context; authors source documents | Cross-surface pinned agent context and governed worldbuilding elevation |
| Plan | Reads graph objects/references; Hermes is graph-first | Cross-route agent continuity and exact bound mechanics consumption |
| Hermes | Graph retrieval, admitted anchors, same-thread continuity in Plan | Governed writes through human protocol; app-level cross-surface identity |
| Statblock Workbench | Generates, renders, edits, and validates structured mechanics | Complete immutable acceptance proof and typed Threat binding |
| Play | Existing independent product | World Graph projection/admissibility migration and exact mechanics resolution |

## Product-state vocabulary

Keep these visibly and semantically distinct:

- source prose or authored document;
- extraction candidate;
- inspect-only candidate;
- prepared/sealed proposal;
- terminal confirm receipt;
- committed World Graph object/revision;
- statblock candidate;
- validated definition;
- immutable saved mechanics;
- proposed Threat/statblock binding;
- committed binding;
- Plan graph reference;
- Play runtime instance.

## Current next gates

1. Direct exact-ExtractionRun candidate-review projection.
2. Preview-union review materialization retirement.
3. Shared projection coordinator, coalescing, cache, revision invalidation, and telemetry.
4. Ingest primary-path simplification.
5. Fresh end-to-end durable-memory dogfood.
6. Cross-surface Agent Interaction thread and pinned-context continuity.
7. Hermes governed write capability over the same human reference protocol.
8. Typed Threat → exact statblock binding and governed publication.
9. Plan and Play consumption of the same Threat and exact mechanics revision.

## Fast diagnostic questions

When adding or reviewing a feature, ask:

- What exact durable identity owns this object?
- Which graph revision is being read?
- Is this candidate, committed memory, saved mechanics, or runtime state?
- Who is authorized to write it?
- What explicit confirmation or receipt proves the transition?
- Can a stale async response attach to a different run, campaign, session, or thread?
- Does failure preserve the last known durable authority?
- Is any path silently falling back to preview, latest-ingest, Markdown, labels, or current head?
- Can the graph be reconstructed with approved corrections intact?
- Which obsolete path is deleted when this becomes production-ready?

If those questions do not have exact answers, the capability is not yet on the continuity spine.
