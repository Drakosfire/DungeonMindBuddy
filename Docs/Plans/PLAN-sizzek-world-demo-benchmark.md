# Sizzek World ingestion, demo, and benchmark plan

**Status: proposed.** This plan captures the work for review. It does not start implementation, provision a World, publish content, or change product sequencing.

## Goal

Let the owner author the **Sizzek** World with their normal Buddy sign-in. Provide a stable no-login link to a selected edition of that World for repeatable demos. Use the corpus to exercise Graph, chronology, contextual authoring and Play without publishing working material.

The existing [signed-in presenter issue](https://github.com/Drakosfire/DungeonMindBuddy/issues/3837) is not the guest path. The [cross-surface demo](https://github.com/Drakosfire/DungeonMindBuddy/issues/410) is broader than this first slice. Current managed World access requires authentication in the app source. The generic signed-out playground is not a named World release.

## 1. Seed the private World

1. **Inventory and normalize.** Catalog the owner-supplied Apprentice one-shot, Carnival Mechanics, Timeline, Izmati prep and played recap, and Winter scenario. Keep originals outside Git. Assign stable source keys, exact revisions or digests, source type, audience and edition where known. Preserve headings and table structure in citation-friendly text; identify duplicate exports and track assets independently. Exclude Glip Dak, uncleared art, legacy setting excerpts, and third-party statblocks from the guest release.
2. **Start with Apprentice.** Create the private Sizzek World through supported ownership paths. Make an editable player briefing and a separate GM prep document. Seed a small set of sourced people, locations, and relationships. Link the same objects into the opening-day Plan and Play scene. Verify one exact saved Build revision can be admitted, used to launch extraction, reviewed, and reopened from its citation before importing more. Re-run the seed to verify stable identities, no duplicates, and no overwritten edits.
3. **Add chronology and source depth.** Import the Izmati table recap through a path that preserves native Recap identity and exact World, campaign, session, source, and revision. Verify the committed Graph result, its citation, and the same recap in Plan; a generic Worldbuilding page or success receipt is not sufficient. Preserve fictional chronology, session/run order, and source revision order separately. Source before/after edges to their actual connective; use partial order and leave unknowns unresolved. Keep scenario plans and alternative outcomes distinct from recorded Play facts. Use the existing recorded-event chronology when appropriate; leave scenario-only schedules in Plan unless the view can label their authority correctly.

## 2. Release a no-login snapshot deliberately

- The signed-in owner controls an explicit release of allowlisted documents, graph objects, citations, assets and Play content pinned to exact revisions. The stable link points to a versioned, immutable snapshot, with deliberate promotion, rollback and unpublish. No live mirroring from the private World.
- Release-specific IDs and citation targets must resolve only inside the approved snapshot. Do not ship original manuscripts, GM-only data, private object or account identifiers, internal diagnostics, conversations, or back-links to private sources. A no-login link can be optionally unlisted, but it is not private from anyone who has the link.
- Give guests genuine read-only Graph, document and Plan views; keep Play choices session-local and resettable. Guest Ask is separate: until live inference against release-only evidence, no write tools, isolation and bounded spend are verified, show a clearly labeled saved Buddy answer and its approved citations.
- Rehearse twice in clean signed-out browser sessions. Verify stable deep links, citations and reset; verify that signed-out and unrelated authenticated sessions cannot read non-released objects or assets or write the owner World. Verify edits to the authoring World are not reflected until promotion, and that unpublishing blocks future access. Do not qualify hosted behavior from local source tests alone.

## 3. Present it in four minutes

Follow Sizzek from the Carnival’s graph into the one-shot. Open the player brief and one cited answer. Move to the linked opening scene, choose whether to investigate the Funhouse, and reset. Stop the guest scene at the threshold and omit the GM reveal. For the lean release, the cited cue is what Sizzek hired the party to do and what changed their assignment. Add the richer cross-source question about Sizzek’s intended carnival attractions versus recorded outcomes only when the needed excerpts are approved. Use a signed-in authoring aftershow optionally; the guest walkthrough must not depend on it.

## 4. Use authoring to make benchmarks

Freeze development and held-out cases by episode/source family before tuning. Pin source/Graph/document revisions, gold claims, forbidden inferences, acceptable citations and expected state changes. Keep the showcase prompt out of held-out scoring. Promote new dogfood examples to a new baseline only after freezing their expected behavior.

- **Extraction and Graph:** Score node/edge precision and recall, identity reuse, direction/scope, exact evidence, duplicate-free re-import and no draft-to-played promotion.
- **Chronology and retrieval:** Test recorded relative order, missing clock anchor, conflicting sources, distinct runs and multi-hop evidence. Require support for the order relation, not just its endpoints. Compare exact-passage retrieval against Graph plus bounded event-neighbor retrieval using the same writer; score evidence coverage, citation correctness and false claims separately.
- **Contextual authoring:** In the signed-in GM document, ask Buddy to add a clue after the passage where Sizzek reassigns the party. Start with no selection. Accept only the intended paragraph boundary, no spoilers and exact preservation of adjacent text and references after Save and reopen. With ambiguous targets, expect a clarification or let the user select; never silently insert at the top. Include wrong context, stale revisions, undo and no-mutation cases.
- **Play, isolation and speed:** Score branch fidelity and reset state, not prose. No trial outcome mutates canon. Treat disclosure, wrong-target writes and broken approved citations as hard failures. Record cold/warm p50 and p95, time to context-ready, first visible answer text and completion, and evidence/token usage alongside quality. Streaming progress alone is not reply text; [ordinary hosted streaming](https://github.com/Drakosfire/DungeonMindBuddy/issues/3838) remains independently scoped.

Reuse the [ordinary benchmark workflow](../Guides/ordinary-benchmark-workflow.md): context-only capture for current Plan retrieval; ordinary capture/report and pinned Build sequences for answer and turn quality; separate owning-browser Save/reopen action evidence and hosted guest qualification. The [no-selection Build draft](https://github.com/Drakosfire/DungeonMindBuddy/pull/3867) is a qualification candidate, not a shipped prerequisite. Automate routine scoring; reserve author judgment for canon, ambiguous expectations, and publication selection.

## Delivery order

1. Private Apprentice slice: ordinary signed-in authoring, repeat-safe seed and exact readback.
2. No-login Sizzek release: minimum player-safe scope and two signed-out rehearsals.
3. Frozen baseline and holdout: broader chronology, retrieval and authoring hill climb. Capture the baseline before tuning; the first private fixture can be frozen while guest delivery is being built.
