# Anchor — Hermes Agent Interaction over World Graph Retrieval

**Status:** Active reference; sequencing authority remains the Campaign Supergraph roadmap and tracker
**Created:** 2026-06-23
**Re-anchored:** 2026-07-14 after PR355 (Rung 4C) merge — post single-turn Hermes product path and Plan evidence presentation
**Scope:** Hermes conversational runtime, graph-only factual retrieval, thread continuity, source-anchor evidence, inspectability, and the bridge to governed tools

Start here for Hermes/Agent Interaction design. Then read:

1. [`ROADMAP-campaign-supergraph.md`](../Roadmaps/ROADMAP-campaign-supergraph.md)
2. [`PR-TRACKER-campaign-supergraph.md`](../Plans/PR-TRACKER-campaign-supergraph.md)
3. [`UX-STORIES-agent-interaction-hermes.md`](UX-STORIES-agent-interaction-hermes.md)
4. [`.hermes.md`](../../.hermes.md)
5. [`CONTRACT-agent-tool-authored-prep-contributions-v0.md`](CONTRACT-agent-tool-authored-prep-contributions-v0.md)

## Executive decision

Hermes is the intended conversational agent and tool-orchestration runtime for DungeonBuddy. The World Supergraph is its sole factual discovery and evidence-admission plane.

The product is abandoning the earlier hybrid ladder in which Hermes or Live could search manifests, corpus indexes, or arbitrary Markdown when graph context was missing. Source Markdown remains authoritative evidence, but Hermes reaches it only through source anchors returned by graph retrieval.

```text
User question
  -> Plan Agent Interaction turn (optional bounded prior visible prose)
    -> Hermes graph-agent host turn (revision-pinned)
      -> graph retrieval over one pinned World Supergraph revision
        -> objects / relationships / attributes / source anchors
          -> optional bounded source-anchor read
            -> Hermes answer with grounding, citations, or explicit abstention
```

A graph gap is a product signal. It must not be hidden by searching unmodeled files.

## Current state after PR355 (Rung 4C)

The repository now has:

- A published Eldyrwild C2 World Supergraph.
- Revision-pinned projection/search APIs and PR010A graph retrieval with source-anchor admission.
- Plan object cards and reference navigation using World Graph projection.
- PR010B Rungs 1–4B: graph-only dispatcher, model-visible catalog, embedded Hermes graph-agent turn, process-isolated host, and single-turn `query_backend="hermes"` product cutover with fail-closed grounding.
- PR355 / Rung 4C: Plan presentation of grounding labels, opaque revision-pinned graph citations, bounded graph-tool trace, and reload-safe local completed-turn persistence (answer / citations / sanitized trace display).
- Named local threads, answer-first UI, source reader for graph anchors, and trace panels.

What is **not** yet true:

- Same-thread pronouns and shorthand are not yet resolved by projecting prior visible prose into the Hermes turn (Rung 5 / planned #356).
- There is no durable Hermes session pointer bound to a Plan thread, and reload does not resume Hermes internal state (Rung 6).
- Cumulative product acceptance, obsolete Hermes retrieval demolition, and backend-selector/default removal are not done (Rung 7).
- PR011 governed write/draft tools remain blocked until PR010B is cumulatively accepted.

### Continuity layers (do not conflate)

| Layer | Owner | Meaning |
|---|---|---|
| Completed-turn local persistence | Rung 4C / PR355 | Reload can re-display sanitized Q/A, grounding, citations, and safe trace. Not a Hermes session. |
| Bounded visible-prose replay | Rung 5 (next) | Prior user/assistant text from the active local thread may resolve conversational identity (“it”). Never campaign truth; never citation/revision authority. |
| Durable Hermes session pointer | Rung 6 (later) | Thread-to-Hermes session identity and reload/process-restart lifecycle. |
| Cumulative acceptance + demolition | Rung 7 (later) | Real-runtime cumulative proof and deletion of replaced Hermes product paths. |

Fresh factual answers re-read current graph state unless the user explicitly asks a historical question. Conversation history helps resolve intent and pronouns; it does not override graph state.

## Authority and memory model

| Layer | Role | Canonical? |
|---|---|---|
| Source artifacts | Prose and evidentiary authority | Yes, for source text/evidence |
| World Supergraph head | Durable materialized knowledge and governed identity/assertions | Yes, for materialized memory state |
| Graph retrieval result | Revision-pinned read/admission envelope | No; derived from a canonical revision |
| Source anchor read | Bounded evidence opened from an admitted anchor | Evidence, not new canon |
| Agent Interaction thread (visible turns) | User intent, prior Q/A display, local continuity | No |
| Bounded prose replay (Rung 5) | Pronoun/shorthand resolution only | Never for campaign facts |
| Hermes session pointer (Rung 6) | Durable session identity across reload/process | No; continuity only |
| Hermes long-term memory | Preferences only if later enabled | Never for campaign facts |

## Graph-only retrieval rule

Hermes product tools may:

- Search the projected graph.
- Resolve exact durable object IDs.
- Traverse bounded neighborhoods.
- Inspect attributes and focus relevance.
- Obtain graph-admitted source anchors.
- Read bounded excerpts through those anchors.

Hermes product tools may not:

- Search a manifest as an alternate discovery plane.
- Search the repository or corpus Markdown directly.
- Use a lexical/vector fallback outside graph admission.
- Read arbitrary file paths supplied by the model.
- Answer campaign facts from ambient memory or old thread text alone.
- Convert a graph miss into a confident answer.

## Target read-only tool vocabulary

### `search_campaign_graph`

Find graph objects and relevant paths from natural language within `worldId`, `campaignId`, focus, admissibility, and a revision pin.

### `get_campaign_object`

Resolve one durable graph ID and return its card-ready attributes, aliases, relationships, focus relevance, and revision metadata.

### `get_object_neighborhood`

Traverse a bounded, admissible neighborhood from one or more object IDs. Return endpoint-relative direction and path/relevance reasons.

### `get_object_evidence`

Return active assertion support and opaque source anchors for a graph object, relationship, or attribute.

### `read_source_anchor`

Open a bounded excerpt from an opaque anchor previously returned by graph retrieval. Arbitrary paths are invalid.

## Hermes runtime boundary

The product path must run a real Hermes agent/session loop. It may use embedded Python or a supported session service boundary, but it must not shell out one subprocess per turn.

Required runtime properties (current and laddered):

- Process-isolated Hermes graph-agent host for product turns (Rung 4A–4B).
- Tool calls and intermediate outcomes observable to `live-control`.
- Cancellation/error propagation.
- Bounded context and explicit revision metadata.
- No automatic fallback to Live synthesis.
- Hermes memory off for campaign facts.
- **Rung 5:** optional caller-owned bounded prior visible prose for pronoun/shorthand resolution only — not a durable session.
- **Rung 6 (later):** one durable Hermes session pointer per Agent Interaction thread, including reload/process-restart lifecycle.

The old CLI one-shot path may remain temporarily as a clearly labeled developer smoke harness only. It is not a production compatibility mode.

## Dogfood ladder

### Gate 1 — Retrieval contract without an LLM

PR010A proves that graph search, exact lookup, neighborhood traversal, evidence admission, and anchor reading work from one revision and fail closed.

### Gate 2 — Single-turn Hermes answer

Rungs 4B–4C: Hermes receives a question, chooses graph tools, returns grounding + opaque citations + bounded tool trace; Plan persists completed-turn display locally.

### Gate 3 — Same-thread object continuity (Rung 5)

Turn 1 establishes Tripod Null-Calf. Turn 2 asks “What is it connected to that should affect my prep?” Hermes resolves “it” from bounded prior visible prose and performs fresh graph traversal. Prior prose is not factual authority; citations and revision come only from the new turn.

### Gate 4 — Coverage-gap honesty

Ask a question whose answer exists in a Markdown source but is absent from the graph. Hermes must abstain and report the missing graph coverage. Any hidden Markdown fallback is a failure. Valid prior history must not fill the gap.

### Gate 5 — Reload/session continuity (Rung 6)

Reload restores the named thread’s completed-turn display (already Rung 4C) **and** a durable Hermes session pointer so internal session state can continue. Factual re-asks still read current graph state. Rung 5 prose replay after reload is not evidence of Rung 6 session resume.


## Required inspectability

Normal UX remains answer-first. Dogfood trace must be available on demand and include:

- Hermes session/thread ID.
- Graph revision/head status, world, campaign, focus, and admissibility.
- Tool names, inputs summarized safely, start/completion/error state, and duration.
- Matched object IDs and traversed relationship IDs.
- Retrieval outcome and truncation/denial/coverage diagnostics.
- Source-anchor IDs and citation locators.
- Whether the answer abstained.

Raw prompts, unbounded source bodies, graph internals, and secrets are not persisted in the client.

## Product acceptance journey

1. The GM opens a named Plan thread.
2. They ask: “What do we know about Tripod Null-Calf at the North Gate?”
3. Hermes finds `threat:tripod-null-calf`, retrieves North Gate relationships and anchored evidence, and answers in useful game language.
4. The GM asks: “What is it connected to that should affect my prep?”
5. Hermes resolves the pronoun, traverses the graph, and explains concrete consequences: nearby threats, NPCs, locations, encounter roles, or unresolved dependencies.
6. Clicking evidence opens the current bounded source through the Agent Interaction pane.
7. A graph gap produces: “DungeonBuddy’s graph does not currently contain enough evidence,” plus the missing objects/anchors needed—not a fallback answer from another Markdown file.

## Deletion map

PR010B owns removal from the Hermes product path of:

- `dungeon_search` and lexical fallback.
- `dungeon_manifest_index`.
- Manifest-backed `dungeon_context_lookup`.
- Arbitrary-path `dungeon_get_document`.
- CLI `hermes --oneshot` backend.
- Live synthesis fallback for Hermes questions.
- The steady-state Live/Hermes user toggle after Hermes dogfood is accepted.

Legacy code may remain only for a named non-product consumer, with an explicit deletion owner.

## Relationship to PR011

PR010A/PR010B are read-only and intentionally narrow. PR011 follows accepted dogfood and adds:

- App-level/cross-surface Agent Interaction context.
- Full typed tool registry.
- Draft-only work.
- Preview-write and proposal-bound confirmation.
- Graph Review/Kernel correction escalation.
- Freshness fan-out across threads.

PR010B must not smuggle write tools or a second memory system into the read-only spike.

## Document consolidation

- **Roadmap + tracker:** sole sequencing authority.
- **This anchor:** active Hermes architecture/product reference.
- **UX stories:** active acceptance catalog.
- **`.hermes.md`:** runtime policy.
- **`HANDOFF-self-continuity-hermes-agent-interaction-bar.md`:** historical evidence only; pre-World-Supergraph CLI spike.
- **Backlog Hermes entry:** captured signal only; this anchor and tracker supersede its sequencing language.
