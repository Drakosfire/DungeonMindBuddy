# Hermes × World Graph interaction — as-built audit

**Snapshot:** `main 4e9b489…`, PR356 head `2f10dd5…`  
**Purpose:** describe the actual question → panel → Hermes → graph → source → answer → trace → persistence path before redesign.

## As-built system in one sentence

DungeonBuddy currently runs a deterministic graph projection for the panel, converts only its scope into a second independent Hermes graph-agent turn, classifies the final answer from summarized tool events using source-anchor presence, and persists the panel summary, answer, citations, and trace as separate artifacts.

## Component map

```mermaid
flowchart TD
    U[GM question] --> UI[PlanAgentInteractionBar]
    UI --> API[/api/live/query]
    API --> PF[Agent World Graph preflight]
    PF --> PROJ[PR007A revision-pinned projection]
    PROJ --> ENV[Panel envelope: candidates nodes edges attributes]
    ENV --> PANEL[WorldGraphQueryContextPanel]

    ENV --> X[Hermes request translator]
    X -->|keeps scope/revision only| HOST[Hermes process host]
    HOST --> H[AIAgent + five graph tools]
    H --> K[Kernel retrieval on same pinned revision]
    K --> H
    H --> EVT[Tool start/completion callbacks]
    EVT --> SUM[Bounded tool-event summarizer]
    SUM --> CLS[Grounding classifier]
    CLS --> ANSWER[Model prose or canned substitution]
    CLS --> CITES[Anchor-ID citation projection]
    ANSWER --> TURN[Completed local turn]
    ENV --> TURN
    SUM --> TRACE[Generic trace + graph tool events]
    TRACE --> TURN
    TURN --> LS[Local thread persistence]
```

## Boundary inventory

### B1 — browser request

For Hermes, the browser sends:

```json
{
  "campaign_id": "longmont-c2",
  "session": 22,
  "mode": "live",
  "query_backend": "hermes",
  "text": "What do we know about Tripod Null-Calf at the North Gate?",
  "agent_thread_id": "...",
  "world_graph_context": {
    "world_id": "eldyrwild",
    "campaign_id": "longmont-c2",
    "focus": {"kind": "session", "session_id": "session-23"},
    "admissibility": "gm",
    "revision_pin": null
  },
  "conversation_history": null
}
```

PR356 optionally adds bounded visible prose. It does not add selected node IDs or prior resolved referents.

### B2 — deterministic preflight envelope

The server resolves one revision and returns:

```json
{
  "status": "ready",
  "revision_id": "revision:...",
  "matched_node_ids": ["threat:tripod-null-calf"],
  "nodes": [{"node_id": "threat:tripod-null-calf", "label": "Tripod Null-Calf", "summary": "..."}],
  "relationships": [{"edge_id": "edge:...", "predicate": "appeared_in", "target_node_id": "event:..."}],
  "attributes": [{"assertion_id": "assertion:f902...", "predicate": "battlefield_role", "text_value": "Siege scout..."}],
  "trust_boundary": {
    "graph_role": "structured_campaign_memory_and_navigation",
    "citation_authority": "corpus_source_evidence",
    "graph_citations_permitted": false
  }
}
```

This envelope drives the visible World Graph panel.

### B3 — Hermes host request

The request translator keeps:

```text
question
world_id
campaign_id
focus
admissibility
revision_pin
root
optional role/content history
```

It drops:

```text
matched_node_ids
node views
relationship views
attribute/assertion views
match reasons
panel diagnostics beyond scope status
```

This is the first confirmed architecture divergence: the product has already resolved Tripod, but Hermes receives no Tripod seed.

### B4 — model-visible tools

Current catalog:

```text
search_campaign_graph
get_campaign_object
get_object_neighborhood
get_object_evidence
read_source_anchor
```

Scope and revision are server-injected. The model supplies query text, node/edge/assertion IDs, traversal bounds, and anchor IDs.

### B5 — raw kernel result

The retrieval result is richer than the product classifier:

```text
snapshot
matched node IDs + match reasons
nodes with summaries/evidence refs/source artifacts
relationships with epistemic/canon/visibility metadata
attributes with assertion IDs and support state
source anchors with readability + locator kind
coverage gaps + unreadable anchors + truncation
diagnostics + trust boundary
```

A source read additionally returns bounded content, digest, line range, and truncation state.

### B6 — summarized tool event

The host strips the raw result to:

```text
tool name
start/completion/error
duration
injected scope/revision
bounded request IDs
retrieval schema
outcome
matched node IDs
relationship IDs
source anchor IDs
diagnostic codes
```

Lost before product classification:

```text
attribute/assertion IDs
claim values
support state
anchor readability
locator kind
source-read digest/content range
coverage detail
which claims answer synthesis used
```

### B7 — result classifier

A tool event is evidence-bearing only when:

```text
state == completion
scope == dispatched scope
outcome in {enough, partial, truncated}
source_anchor_ids is non-empty
```

Consequences:

- accepted graph claims without anchors cannot ground an answer;
- unreadable anchors can ground an answer;
- an unopened anchor can ground an answer;
- source-read success adds no distinct product state;
- graph claims used by the answer are not recorded;
- model prose is either accepted wholesale or replaced wholesale.

### B8 — citation projection

Every admitted anchor ID becomes an opaque `world_graph_anchor` citation carrying world/campaign/focus/admissibility/revision. The citation does not say:

- what claim it supports;
- whether it was readable;
- whether it was opened;
- what excerpt was returned;
- whether the answer directly quoted or merely referenced it.

### B9 — panel

The panel shows:

- status/revision/focus;
- matched durable IDs;
- connected objects;
- graph attributes;
- warnings/diagnostics.

It does not distinguish candidate context from answer-used support.

### B10 — trace

The generic trace displays mode, provider/model, toolset, elapsed time, steps, tokens, and graph tool activity. For Hermes graph turns:

- `steps` is always empty under the current product builder;
- `toolset` is not populated;
- graph events show IDs but not claim/readability/source-read semantics;
- the trace cannot explain `hermes_insufficient_evidence` precisely.

### B11 — persistence

The completed local turn persists:

- visible question/answer;
- grounding summary;
- opaque citations;
- compact panel summary;
- generic trace/tool events.

Detailed panel claims are intentionally not persisted. No durable Hermes session exists. PR356 replays visible prose from completed local turns.

## Authority map as built

| Object | What code currently permits | What the user is likely to believe |
|---|---|---|
| Panel candidate | Navigation context only | The system found and knows this object |
| Accepted graph assertion | Returned to Hermes, but insufficient without anchor ID | Canonical campaign fact |
| Source anchor | Presence is enough for “grounded” | A source was verified/read |
| Source read | Same acceptance category as any anchor completion | Stronger evidence than an unopened anchor |
| Prior prose | Intent/referent only | Conversation memory |
| Final answer | Accepted/replaced as one block | Supported claim-by-claim |

## Contradictions

1. **Graph authority contradiction:** canonical architecture treats the graph as durable materialized memory; Hermes policy treats it as a discovery plane that cannot authorize prose by itself.
2. **Citation contradiction:** the product calls opaque anchor IDs citations even when no source was opened.
3. **Panel contradiction:** the UI presents candidate graph facts without exposing that Hermes did not receive them.
4. **Grounding contradiction:** `grounded` means “one accepted event had an anchor ID,” not “answer claims have support.”
5. **Trace contradiction:** the product advertises inspectability but omits the exact state used for acceptance.
6. **Continuity contradiction:** the product already owns durable node IDs but relies on prose reconstruction for referents.

## As-built invariants worth preserving

- one immutable revision per factual turn;
- server-owned world/campaign/focus/admissibility;
- graph-only discovery plane;
- no arbitrary model-selected filesystem reads;
- digest-verified bounded source reads;
- visibility/canon/admissibility enforcement in Kernel/projection;
- no automatic durable writes;
- conversation prose never becomes factual authority.

## Conclusion

The core defect is not that Hermes needs more prompt context. It is that candidate resolution, graph claim retrieval, source verification, answer acceptance, and user inspection are represented by disconnected payloads. The replacement must introduce one shared retrieval/claim state that every layer consumes.
