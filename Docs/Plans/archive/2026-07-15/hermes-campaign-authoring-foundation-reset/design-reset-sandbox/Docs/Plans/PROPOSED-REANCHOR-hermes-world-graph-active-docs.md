# Proposed reanchor — active Campaign Supergraph and Hermes documents

**Status:** PROPOSED; do not apply until the design package is accepted.

## 1. `Docs/Design/ARCHITECTURE-campaign-supergraph.md`

### Replace or amend

Replace the current source-authority wording in the sections governing:

- graph ownership and authority;
- read architecture;
- source artifacts and evidence;
- Agent Interaction consumption;
- mandatory epistemic metadata.

### Proposed normative text

```text
The selected World Supergraph revision is authoritative for accepted graph claims:
governed identity decisions, accepted explicit assertions, and accepted relationship
records. Authority attaches to explicit claim records, not arbitrary projection summaries.

Source artifacts are authoritative for their own bounded content and provide provenance,
verification, quotation, deeper detail, and conflict detection. A source anchor records an
admitted claim-to-source association; a source citation is created only after a successful
integrity-checked source read.

Graph-native GM-authored accepted assertions are first-class canonical claims even when
no separate prose source exists. Their provenance must identify the GM/contribution/review
activity and revision.

Derived summaries are navigation context unless separately governed as accepted summary
assertions. Agent inferences are noncanonical turn-local conclusions supported by accepted
claim IDs.

Every factual agent turn consumes one GraphRetrievalSession pinned to one revision and
admissibility scope. UI projections and agent retrieval operate over that same session.
```

### Add

Add `GraphRetrievalSession`, claim ledger, graph reference, source citation, inference, and coverage-gap definitions to the read architecture.

## 2. `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`

### Replace

Replace the current PR010B Rung 5 → Rung 6 → Rung 7 critical path.

### Proposed sequence

```text
HOLD/SUPERSEDE  PR356 — bounded visible-prose replay
READY           HGI-0 — forensic observability + Tripod digest/head migration
LATER           HGI-1 — claim authority and ledger contracts
LATER           HGI-2 — shared retrieval session + deterministic candidate handoff
LATER           HGI-3 — bounded retrieval-plan executor
LATER           HGI-4 — source-read ledger + honest citations
LATER           HGI-5 — structured answer validator + partial-answer policy
LATER           HGI-6 — panel/trace convergence
LATER           HGI-7 — selected referents + bounded prose continuity
LATER           HGI-8 — cumulative dogfood + demolition
OPTIONAL        HGI-9 — durable Hermes sessions, only after acceptance
BLOCKED         PR011 — governed draft/write runtime
```

### Replace graph-only wording

Replace “current-turn source anchors are required for all factual claims” with:

```text
Current-turn accepted graph claims authorize graph-grounded facts. Successful current-turn
source reads authorize source-verified detail and quotations. No alternate Markdown discovery
plane is permitted on graph gaps.
```

## 3. `Docs/Plans/PR-TRACKER-campaign-supergraph.md`

### Update statuses

- PR356: `SUPERSEDE RECOMMENDED — design reset; do not merge pending operator decision`.
- Current Rung 6 durable session: `DEFERRED; no longer next critical path`.
- Current Rung 7: replaced by HGI-8 cumulative dogfood/demolition.
- PR011: remains blocked.

### Add acceptance criteria for the rebuild umbrella

```text
- panel and Hermes consume one retrieval-session ID and claim ledger;
- accepted graph claims can support graph-grounded answers without pretending a source was read;
- source citations require a successful integrity-checked read;
- candidates, used claims, inferences, sources, and gaps are distinct;
- selected node/edge/assertion IDs are first-class conversational referents;
- all factual answer sections map to accepted claims or opened source content;
- inference is disclosed and noncanonical;
- Tripod exact lookup, source-unreadable, source-readable, connection, prep implication,
  pronoun, and selected-node journeys pass with the real agent;
- obsolete independent retrieval/classifier/panel paths are removed;
- durable sessions remain optional and cannot authorize facts.
```

## 4. `Docs/Design/ANCHOR-agent-interaction-hermes.md`

### Replace target architecture and five-tool catalog

Proposed target:

```text
Hermes is a conversational planner and synthesizer over a server-owned GraphRetrievalSession.
The server binds scope/revision/admissibility, validates referents, performs deterministic
candidate resolution, and supplies an initial claim packet. Hermes requests bounded expansions
and source reads through validated tools. The panel and answer support view project the same
retrieval session.
```

Replace the five model-visible tools with:

```text
server-owned initial candidate/claim retrieval
expand_graph_retrieval
read_graph_source
```

Kernel search/object/neighborhood/evidence/source-read functions may remain internal implementation primitives.

### Replace grounding language

```text
graph_grounded — accepted explicit graph claims support factual statements
source_verified — successful source reads support exact detail/quotation
partial_coverage — useful claims exist, named dimensions are missing/unreadable/truncated
inferred_from_graph — disclosed noncanonical implication with premise claim IDs
conflicting_authority — graph and opened source disagree
abstained — no useful admissible factual support
execution_error — protocol/infrastructure failure
```

### Replace continuity sequencing

```text
Selected/pinned durable graph referents precede visible-prose replay. Bounded prose remains a
low-priority lexical aid. Durable Hermes sessions are deferred until the shared retrieval and
claim-support architecture passes cumulative dogfood.
```

## 5. `Docs/Design/UX-STORIES-agent-interaction-hermes.md`

Replace the document after operator acceptance with:

```text
Docs/Design/UX-STORIES-hermes-world-graph-interaction-v2.md
```

The v2 stories add:

- claim-level support;
- candidate versus used state;
- selected-object referents;
- graph facts versus source verification;
- constructive partial answers;
- paths, comparisons, timelines, coverage diagnostics;
- source/graph conflicts;
- future correction proposal seam.

## Repository action after acceptance

Make these documentation changes in one authority reanchor commit before dispatching implementation Slice 0. Archive the superseded Hermes anchor/story sections rather than leaving contradictory active language.
