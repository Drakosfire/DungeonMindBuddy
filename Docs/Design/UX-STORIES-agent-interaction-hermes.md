# UX Stories — Hermes Agent Interaction over Graph Retrieval

**Status:** Active acceptance reference
**Re-anchored:** 2026-07-14 after PR355 — Rung 5 owns same-thread pronoun resolution; Rung 6 owns session/reload lifecycle
**Parent:** [`ANCHOR-agent-interaction-hermes.md`](ANCHOR-agent-interaction-hermes.md)

## North star

As a GM, I can hold a continuous prep conversation with Hermes. Hermes discovers campaign facts through the current World Supergraph, opens evidence only through graph-admitted source anchors, and either cites what it found or clearly says the graph is missing what it needs.

There is no hidden manifest, corpus-index, or arbitrary Markdown fallback.

## Core stories

| ID | Story | Acceptance | Owning rung |
|---|---|---|---|
| H1 | Ask a natural-language prep question | Hermes chooses graph read tools and returns useful prose grounded in one revision | Rung 4B–4C (done) |
| H2 | Continue with pronouns and shorthand | “What is it connected to?” resolves the object established in the same thread via bounded prior visible prose and triggers fresh graph traversal; prior prose is not campaign truth | **Rung 5** |
| H3 | Trust the answer | Claims link to source anchors admitted by the **current** turn’s graph tools; evidence opens inside Agent Interaction | Rung 4C + Rung 5 authority invariant |
| H4 | See honest uncertainty | Empty/partial/denied graph retrieval produces explicit uncertainty or abstention, never unrelated Markdown fallback; prior prose must not fill a graph gap | Rung 4B–4C; Rung 5 regression |
| H5a | Reload completed-turn display | Reload restores sanitized Q/A, citation pointers, and safe trace for completed turns | Rung 4C (done) |
| H5b | Resume Hermes session identity | Reload restores a durable Hermes session pointer so internal session state can continue | **Rung 6** (not Rung 5) |
| H6 | Read current campaign state | New turns read current graph head unless the user explicitly asks for historical state | All factual turns |
| H7 | Inspect agent behavior during dogfood | Optional trace shows tool calls, graph revision, matched objects, traversed edges, anchors, and failures | Rung 4C |
| H8 | Keep memory boundaries understandable | UI distinguishes thread continuity (visible prose), Hermes session state (Rung 6), graph memory, and source evidence | Rung 5–6 separation |
| H9 | Work safely before write tools exist | PR010B is read-only; no draft or durable mutation is implied by conversation | PR010B |
| H10 | Add governed tools later | PR011 adds typed tools and preview/confirm without changing the graph-only factual retrieval rule | PR011 (blocked) |

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

### Turn 2 (Rung 5)

**Question:** “What is it connected to that should affect my prep?”

**Good enough:**

- Bounded prior visible user/assistant prose from the **same** active local thread is projected so Hermes can resolve “it” as Tripod Null-Calf.
- This is **stateless prose replay**, not a resumed Hermes session (Rung 6).
- Hermes calls bounded neighborhood traversal (or equivalent fresh graph tools) at the **new** request’s resolved revision.
- Connected objects are explained as prep implications, not merely listed as edge IDs.
- New factual claims cite only anchors admitted during Turn 2.
- Turn 1 anchors, revision, and citations do not automatically carry forward.
- The system does not rerun a broad Markdown search.

### Coverage-gap turn

**Question:** A factual question whose answer exists somewhere in repository Markdown but is not represented by the current graph or its anchors.

**Good enough:**

- Retrieval returns `partial` or `empty` with a coverage diagnostic.
- Hermes says the graph does not contain enough supported evidence.
- It may identify the missing object/source coverage needed for ingestion.
- It does not call manifest lookup, corpus search, lexical fallback, or arbitrary document read.
- Valid prior visible prose does not become a substitute answer.

## Thread and freshness rules

- Conversation history is per active local thread.
- **Rung 5:** outbound history is a bounded projection of visible Q/A pairs only (role + content); no citations, traces, revisions, anchors, or session pointers.
- Authority is shared through the current World Supergraph and source artifacts.
- Thread text may resolve intent but may not override a newer graph revision.
- Every factual turn records the revision it used.
- A head change marks older answers as potentially stale and biases the next factual turn toward fresh retrieval.
- Historical questions may request an explicit prior revision; silent stale reuse is forbidden.
- **Rung 6 (later):** durable Hermes session-pointer binding and process/restart lifecycle — distinct from Rung 4C display persistence and Rung 5 prose replay.


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

- Hermes is the steady-state conversational backend (selector/default change is Rung 7, not Rung 5).
- The graph is the sole factual discovery/admission plane.
- Source documents remain evidence authority but are reachable only through graph-admitted anchors.
- A graph miss is surfaced, not hidden.
- Same-thread pronoun/shorthand continuity is required (**Rung 5** via bounded visible-prose replay).
- Durable Hermes session-pointer resume is required later (**Rung 6**), distinct from Rung 5.
- Named parallel threads remain supported; Thread A prose must not enter Thread B requests.
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
