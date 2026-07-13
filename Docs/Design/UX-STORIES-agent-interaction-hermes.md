# UX Stories — Hermes Agent Interaction over Graph Retrieval

**Status:** Active acceptance reference
**Re-anchored:** 2026-07-13
**Parent:** [`ANCHOR-agent-interaction-hermes.md`](ANCHOR-agent-interaction-hermes.md)

## North star

As a GM, I can hold a continuous prep conversation with Hermes. Hermes discovers campaign facts through the current World Supergraph, opens evidence only through graph-admitted source anchors, and either cites what it found or clearly says the graph is missing what it needs.

There is no hidden manifest, corpus-index, or arbitrary Markdown fallback.

## Core stories

| ID | Story | Acceptance |
|---|---|---|
| H1 | Ask a natural-language prep question | Hermes chooses graph read tools and returns useful prose grounded in one revision |
| H2 | Continue with pronouns and shorthand | “What is it connected to?” resolves the object established in the same thread and triggers fresh graph traversal |
| H3 | Trust the answer | Claims link to source anchors admitted by graph assertions; evidence opens inside Agent Interaction |
| H4 | See honest uncertainty | Empty/partial/denied graph retrieval produces explicit uncertainty or abstention, never unrelated Markdown fallback |
| H5 | Resume named threads | Reload restores full Q/A, citation pointers, trace pointers, and Hermes session identity |
| H6 | Read current campaign state | New turns read current graph head unless the user explicitly asks for historical state |
| H7 | Inspect agent behavior during dogfood | Optional trace shows tool calls, graph revision, matched objects, traversed edges, anchors, and failures |
| H8 | Keep memory boundaries understandable | UI distinguishes thread continuity, Hermes session state, graph memory, and source evidence |
| H9 | Work safely before write tools exist | PR010B is read-only; no draft or durable mutation is implied by conversation |
| H10 | Add governed tools later | PR011 adds typed tools and preview/confirm without changing the graph-only factual retrieval rule |

## Primary dogfood journey

### Turn 1

**Question:** “What do we know about Tripod Null-Calf at the North Gate?”

**Good enough:**

- Hermes calls graph search/lookup.
- `threat:tripod-null-calf` is selected from the current campaign/focus projection.
- Relevant attributes and North Gate relationships are retrieved.
- Source anchors are admitted for factual claims.
- The answer emphasizes useful game/prep information rather than graph metadata.
- Trace can show revision and tool activity.

### Turn 2

**Question:** “What is it connected to that should affect my prep?”

**Good enough:**

- The same Hermes thread/session resolves “it” as Tripod Null-Calf.
- Hermes calls bounded neighborhood traversal.
- Connected objects are explained as prep implications, not merely listed as edge IDs.
- New factual claims cite graph-admitted anchors.
- The system does not rerun a broad Markdown search.

### Coverage-gap turn

**Question:** A factual question whose answer exists somewhere in repository Markdown but is not represented by the current graph or its anchors.

**Good enough:**

- Retrieval returns `partial` or `empty` with a coverage diagnostic.
- Hermes says the graph does not contain enough supported evidence.
- It may identify the missing object/source coverage needed for ingestion.
- It does not call manifest lookup, corpus search, lexical fallback, or arbitrary document read.

## Thread and freshness rules

- Conversation history is per thread.
- Authority is shared through the current World Supergraph and source artifacts.
- Thread text may resolve intent but may not override a newer graph revision.
- Every factual turn records the revision it used.
- A head change marks older answers as potentially stale and biases the next factual turn toward fresh retrieval.
- Historical questions may request an explicit prior revision; silent stale reuse is forbidden.

## Evidence UX

- Answer first.
- Connected objects should be visible as useful, clickable game concepts.
- Evidence and revision diagnostics remain collapsed by default after dogfood confidence improves.
- Clicking a citation opens the current bounded source excerpt/document view inside Agent Interaction.
- The UI does not expose arbitrary filesystem paths as an agent input.

## Trace UX

Trace is user-toggleable and contains:

- Hermes session/thread identifier.
- Revision/head/focus/admissibility.
- Retrieval/tool steps and durations.
- Matched graph object IDs and traversed relationships.
- Source-anchor locators.
- Retrieval outcome, truncation, denial, and coverage-gap state.
- Final answer or abstention state.

Trace does not persist raw prompts, unbounded source bodies, secrets, or internal graph storage paths.

## Locked product decisions

- Hermes is the steady-state conversational backend.
- The graph is the sole factual discovery/admission plane.
- Source documents remain evidence authority but are reachable only through graph-admitted anchors.
- A graph miss is surfaced, not hidden.
- Same-thread continuity is required.
- Named parallel threads remain supported.
- Long-term Hermes memory is off for campaign facts.
- Durable writes are never autonomous and remain PR011 work.
- The existing Agent Interaction bar/pane is extended, not redesigned from scratch.

## Non-goals for PR010B

- Play/live-table UX.
- Full operator tool parity.
- Statblock/NPC/table generation tools.
- Draft artifact persistence.
- Preview-write or confirm-commit.
- App-wide provider hoist.
- Broad GraphRAG optimization or embeddings.
- A fallback route to unmodeled Markdown.
