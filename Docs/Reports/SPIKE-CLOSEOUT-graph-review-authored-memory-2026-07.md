# Spike Closeout — Graph Review Authored Memory

**Date:** 2026-07-09  
**Status:** PAUSED AT STABLE CHECKPOINT  
**Branch/PR context:** After PR #305, “Graph Review pause-point: durable merges, authoring, and selected-object UX”  
**Primary product surface:** Graph Review / authored graph memory

## Executive summary

The Graph Review authored-memory spike is closed at a useful checkpoint. A GM can inspect a live ingest projection, author explicit campaign graph assertions from recap context, commit those assertions through the authored overlay and event-log path, and reload the projection to inspect the result.

Identity merges have one additional durable behavior: when the operator has selected a live run with a preview union store, a successfully committed merge materializes its identity choices into that selected store. This is intentionally narrower than general graph editing or cross-run enrichment.

This is a pause, not a declaration of product completeness. The core loop is proven; undo, broader source authoring, player views, richer management tools, and explicit enrichment remain future product work.

## What is now true

- Graph Review can load and inspect a live ingest projection.
- The operator can select recap context and author object, link-existing, relationship, and `merge_objects` assertions.
- Normal staged proposals retain prepare → review → commit semantics.
- The create-object wizard is an intentional exception: it immediately writes one object assertion to authored memory, refreshes the projection, then guides the operator through Existing object and Relationships.
- Authored assertions are stored in a campaign-scoped overlay and commits append an event log.
- A committed identity merge with `previewUnionStorePath` materializes active redirects, merge records, survivor hydration, merged-away state, and applicable edge rewiring into that selected preview union store.
- Projection reload prefers the selected live preview union store over a frozen manifest projection snapshot.
- A corrected merge can supersede an older survivor choice only when the newer merge explicitly merges the old survivor away. The event log records both assertion IDs.
- Selected-object cards lead with game-facing identity, summaries, related objects, relationship source context, and inline relationship detail. Evidence, review state, merge provenance, identifiers, and technical metadata are under collapsed **Details**.

## Current operator workflow

1. Select a live ingest run in Graph Review.
2. Inspect projected recap prose and graph objects.
3. Select recap text or choose a graph object in Author Draft.
4. Create a new object, find/link an existing object, stage a relationship, or stage an identity merge.
5. For normal staged work, prepare and commit the authored-memory change.
6. For a new object, use **Create object**; it immediately saves authored memory, reloads projection, and continues to Existing object.
7. For an identity merge with a live preview union store selected, commit once and refresh Graph Review. The survivor should reflect the durable identity choice.
8. Open **Details** only when provenance, evidence, raw identifiers, or review state is needed.

## Current architecture

### Source projection

A live ingest run produces graph-memory artifacts, including a preview union supergraph store. Graph Review projects session objects, relationships, evidence, and source spans from that active run. When both are available, projection reads the selected preview union store instead of a frozen manifest snapshot.

### Authored overlay

Manual GM decisions live in a campaign-scoped authored graph overlay. Assertion kinds are object creation, link-existing, relationship, and merge-objects. The overlay is the durable authored-memory layer; it is not a gold fixture and it does not rewrite recap markdown.

### Event log

Every successful authored-memory commit appends events to the authored graph event log. It is the audit trail for authored changes.

The overlay and event log are not yet a fully transactional unit. In particular, an event-log append failure can leave an overlay write in place; it must never trigger union-store materialization. Merge supersession is audited by an `authored_graph_assertion_superseded` event carrying both the superseded and superseding assertion IDs.

### Commit path

Staged proposals use prepare, confirm-token validation, and commit. The create-object wizard prepares and commits a single object proposal back-to-back by design. Its UI explicitly says that **Create object** writes authored memory immediately.

### Durable identity materialization

Committed `merge_objects` assertions materialize only when a selected live run supplies `previewUnionStorePath`, and only after overlay write and event-log append succeed. Materialization:

- adds active redirects and merge records;
- hydrates or updates the chosen survivor;
- marks merged-away nodes;
- rewires applicable edges from merged-away identities;
- skips already-materialized assertions; and
- writes only the selected preview union store, with backups.

It does not mutate source recap markdown, ingest artifacts, or gold fixtures. It does not import sibling-run nodes, evidence, or edges. Session-peer enrichment was deliberately removed from PR #305; any future backfill must be explicit, deterministic, provenance-preserving, and constrained by exact identity references.

### Projection reload

After commit, Graph Review reloads from the active live store and layers authored overlay state. Durable redirects resolve authored references that still point at merged-away identities.

### Selected-object card

The selected-object card presents the object name with a type badge, campaign summary when present, related objects, and expandable relationship details. Relationship details can show source paragraph context and highlighted material. Details is collapsed by default and holds metadata, evidence, review state, merge provenance, and raw identifiers.

### Create-object wizard

Creating one object is an immediate authored-memory action, not an uncommitted staged draft. After success, the wizard reloads Graph Review, selects the new node, searches Existing object for relevant links, and offers an explicit next step into Relationships.

### Relationship authoring

The operator can stage relationships between selected or existing objects. Relationship rows prioritize the related object and source context over edge IDs. Further GM-facing predicate and relationship-management polish remains deferred.

### Merge correction / supersession

Conflicting identity merges are rejected unless the proposed merge explicitly merges the prior survivor away. The old overlay assertion becomes superseded and an append-only event identifies the old and replacement assertions.

## What was deliberately excluded

- General graph-database editing.
- Source recap markdown mutation.
- Automatic sibling-run enrichment or backfill.
- LLM authoring assistance.
- Player-facing/public projection UI.
- Undo or revert for authored assertions and materialized merge passes.
- Gold/eval-first authoring.

## Known limitations

- Overlay and event-log writes are not fully transactional.
- Preview union-store materialization changes a selected run artifact; backups exist, but a GM-facing undo workflow does not.
- Quick-create must remain visibly labeled as an immediate write.
- Relationship authoring and selected-object summaries are useful but not yet full campaign-management or statblock surfaces.
- Worldbuilding and non-recap source authoring remain narrow.

## Safety invariants

- Authored campaign memory is the primary write target; gold/eval export is opt-in and secondary.
- Source recap markdown and extracted ingest artifacts are not authoring write targets.
- Union-store materialization runs only after overlay write and event-log append succeed.
- Materialization is limited to committed identity merges and the selected preview union store.
- Merge supersession must retain an event-log audit record.
- Visibility defaults to GM-private; no player-facing surface is implied by the stored visibility field.

## Dogfood evidence

- `Docs/Reports/DOGFOOD-graph-object-authoring-a10-user-stories.md` records the initial C1S2 authoring loop and the issues that drove subsequent hardening.
- `evals/lysandra_vertical_slice/A10O-DURABLE-MERGE-MATERIALIZATION-BRIDGE.md` records Mireward Reach and Lysandra durable-merge validation.
- PR #305 consolidates the materialization safety fix, selected-object UX, create-object wizard, merge supersession audit, and the removal of heuristic session-peer enrichment.

## Canonical docs after this closeout

- `Docs/Design/DESIGN-graph-object-authoring-surface.md` — product and architecture stance.
- `Docs/Plans/ROADMAP-graph-object-authoring-surface.md` — current checkpoint and deferred work.
- This report — concise pause-point state, safety invariants, and restart surface.
- `Backlog.md` — active follow-ups and risk reminders.

## Historical / archived docs

The A10 implementation notes, early dogfood reports, and A10m handoff remain useful as evidence of decisions made during the spike. They are marked historical and indexed at `Docs/Archive/graph-review-a10/README.md`; they are not the current architecture authority.

## Resume-later backlog

See `Backlog.md` under **Resume after Graph Review authored-memory pause**. The next phase should be planned as product hardening, not continuation of an unbounded feasibility spike.

## Suggested next slices

1. Full browser dogfood across multiple real sessions.
2. Relationship authoring and authored-memory management UX.
3. Explicit undo/retract for overlay assertions and materialized merge passes.
4. Worldbuilding and non-recap source authoring.
5. Player-safe projection and visibility review.
6. An explicit sibling-store enrichment/backfill design with deterministic provenance and exact identity constraints.
7. Richer game-facing object summaries, statblocks, and campaign panels.

> This spike is closed because the core product loop is now proven: a GM can inspect projected recap memory, author explicit campaign graph assertions, commit them through the authored overlay/event-log path, materialize durable identity choices into the selected working union store, and see the result in Graph Review. The next phase should be planned as product hardening, not as continuation of the original feasibility spike.
