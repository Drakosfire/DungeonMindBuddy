# Goal Anchor — Hermes as a Campaign Sensemaking Partner

**Status:** PROPOSED GOAL; operator review required  
**Created:** 2026-07-15  
**Scope:** Hermes free-form interaction, recap change investigation, campaign sensemaking, graph/source evidence, and prep implications

This is a product goal anchor for the Hermes Campaign Authoring Foundation Reset.
The explicit Phase 1 re-anchor must reconcile it with the active architecture,
stories, evaluation, and the Campaign Supergraph roadmap before implementation
sequencing changes.

Start with the active Hermes document index:
[`INDEX-hermes-campaign-authoring-foundation.md`](INDEX-hermes-campaign-authoring-foundation.md).

## North-star experience

As a GM, I can ask DungeonBuddy a broad question in ordinary language and receive a
thoughtful, campaign-aware read of what matters. Hermes uses the available graph,
recap, source, and conversation context to investigate the question, chooses what is
interesting, and explains how the campaign moved. The answer feels like a knowledgeable
co-GM, not a retrieval report or an empty evidence verdict.

Canonical example:

> What changed after the latest ingested recap?

The useful answer may include:

- changes in the situation, relationships, threats, resources, or locations;
- consequences that follow from those changes;
- unresolved threads that became more important;
- details present in the recap but not yet promoted into durable campaign memory;
- prep questions or opportunities suggested by the new state.

Facts must remain grounded. Consequences and prep ideas may be inferred, but the
answer must make that distinction naturally and clearly.

## Product principles

1. **Free-form text is a real agent task.** A populated button may suggest a question
   or carry optional context, but its text is still passed to Hermes for interpretation.
   We do not replace free-form judgment with a hidden menu of typed intents.
2. **Breadth should trigger investigation.** An empty first retrieval is not a final
   answer. Hermes should use bounded tools and available context before deciding that
   nothing useful can be said.
3. **The answer leads with meaning.** The primary response should select and narrate
   the important movement in the campaign. Claim IDs, revision state, source status,
   and diagnostics are supporting evidence, preferably behind lightweight inspection
   UI.
4. **No invention is required for liveliness.** “Fun” means useful selection,
   connective interpretation, and prep relevance—not relaxed factual standards.
5. **No-change differs from unknown.** A completed comparison that finds no accepted
   changes is different from a missing scope, failed retrieval, empty graph, or
   unavailable source.
6. **The system can expose memory lag.** If the recap contains meaningful material
   that is not yet durable graph memory, Hermes should be able to say so and treat it
   as a lead rather than silently losing it or promoting it.

## Desired answer behavior

For a broad change question, Hermes should independently decide which dimensions are
useful. It should not enumerate every graph mutation. A good answer usually has:

1. a concise narrative of how the situation moved;
2. a few selected changes that matter;
3. the consequences or pressures those changes create;
4. open threads or uncertain details worth watching;
5. an optional prep-oriented next question.

The support surface should let the GM inspect the factual basis without making the
main answer read like a ledger. Every factual beat still needs a claim, source read,
or other governed support. Every inference needs identifiable premises. Unsupported
prose must not become accepted merely because it sounds plausible.

## Scope of the architecture review

The review must answer:

- Which current systems already support this experience?
- Which systems force lookup-first, citation-first, or abstention-first behavior?
- Is the current `GraphRetrievalSession` the right center, or only a useful boundary
  that should be simplified?
- Do the graph and ingest layers expose real latest-recap, before/after, timeline,
  thread, and consequence primitives?
- Which old paths, tests, schemas, panels, and UX assumptions are now context/code
  bloat?
- What can be deleted, quarantined, or rebuilt without preserving compatibility?

The review is explicitly allowed to recommend a replacement architecture. It is not
constrained to incremental repair.

## Hard boundaries

Keep:

- server-owned world, campaign, revision, admissibility, and security boundaries;
- graph and source integrity checks;
- governed distinction between facts, source detail, inference, and suggestion;
- bounded model-visible retrieval;
- no autonomous canon writes.

Do not preserve merely for compatibility:

- duplicate retrieval or grounding paths;
- mechanical evidence-first answer framing;
- operation names whose implementations are only aliases for generic search;
- synthetic tests that prove plumbing but not useful agent behavior;
- durable conversation state that is mistaken for factual memory.

## Success criterion

The goal is not “the agent emits a valid grounding envelope.” The goal is that a GM
can ask the canonical free-form question and receive an engaging, useful account of
what changed, with honest uncertainty and inspectable support, across real recap and
campaign data.

The first proving slice should be one end-to-end `change_since_latest_recap` journey:
the latest recap is identified, the relevant before/after or recap-to-head delta is
retrieved, Hermes selects meaningful changes, and the final prose distinguishes
campaign facts, implications, unresolved material, and prep relevance.

