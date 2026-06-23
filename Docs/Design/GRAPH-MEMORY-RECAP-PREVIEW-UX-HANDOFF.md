# Graph Memory Recap Preview UX Handoff

**Status:** Design handoff  
**Created:** 2026-06-22  
**Project:** DungeonMindBuddy / DungeonBuddy  
**Workstream:** Graph Memory / Recap Ingestion / Agent Interaction  
**Audience:** Frontend, product, interaction design, graph-memory backend agents  
**Current checkpoint:** Post explicit real-artifact dogfood evaluation  
**Primary task:** Prepare the frontend and Agent Interaction layer for graph-memory preview UX before implementation.

---

## 1. Executive Summary

The graph-memory backend workstream is reaching a product transition point.

Until now, the ladder mostly proved that source artifacts can move through a safe diagnostic pipeline:

```txt
explicit recap artifact
→ source artifact materializer
→ source refs / provenance
→ projection-readiness checks
→ projection payload fixture
→ real-derived dogfood safety test
```

That proves wrapper safety. It does not yet prove GM-facing value.

The next product target is not another table of counts. The next target is a frontend preview experience where the GM can look at a recap-derived graph and say:

```txt
Yes, that is the session I wrote.
I can see what the system understood.
I can see what it is unsure about.
I can see where each claim came from.
I can approve, defer, or reject graph memory writes.
```

Design this as a **GM trust surface**, not a generic graph database viewer.

---

## 2. Relationship To `/plan` Agent Interaction

The current `/plan` Agent Interaction roadmap is focused on:

```txt
source-vocabulary adapter
inspectable live/Hermes question backend
plan-scoped Agent Interaction bar proof
future app-level AgentInteractionProvider
```

Graph memory preview is adjacent, not a replacement for that sequence.

Agent Interaction will eventually consume graph results as evidence-backed context and render graph/entity/evidence chips in responses. But the next graph-memory UX milestone is earlier:

```txt
Preview graph → GM trust evaluation
```

Do not jump directly to graph-backed Agent Interaction answers. First prove that a GM can understand and trust a recap-derived graph preview.

---

## 3. What Exists Today

The backend ladder has diagnostic infrastructure for:

```txt
explicit artifact inputs
source artifact identity
source anchors
source units
stable source_ref_id
provenance linkage
semantic states
projection-readiness checks
projection-safe payload fixtures
one real-derived explicit artifact dogfood bundle
```

The dogfood proved that a small explicit artifact set can pass through the chain without obvious leaks or boundary violations.

It has not yet produced a meaningful GM-facing graph from a full recap: named characters, places, session beats, relationships, unresolved threads, queryable graph memory, or approval-ready graph writes remain future-facing.

---

## 4. What Does Not Exist Yet

The frontend must not assume these exist:

```txt
real multi-pass LLM extraction
canonical graph candidate model
graph write approval backend
persistent graph memory store
graph query engine
query vocabulary executor
source-span highlight API
Agent Interaction chip renderer wired to graph results
graph-backed /plan
graph retrieval
shadow retrieval
corpus writeback
entity merge workflow
alias resolution workflow
```

The design may prepare for these things, but must label them as future contracts.

---

## 5. Product Loop We Are Designing Toward

Longer-term loop:

```txt
1. GM provides or imports a recap.
2. System extracts graph candidates over multiple passes.
3. System produces a preview graph.
4. GM inspects the preview.
5. GM approves, rejects, or defers proposed writes.
6. Approved graph memory becomes queryable.
7. Agent Interaction uses graph query results as evidence-backed context.
8. Frontend renders Markdown/answers with entity chips, evidence chips, source deeplinks, and hover cards.
```

First frontend milestone:

```txt
Preview graph → GM trust evaluation
```

---

## 6. Core UX Principle

The graph must be shown as a **proposed memory diff**, not as truth.

Default mental model:

```txt
This is what the system thinks the recap contains.
Nothing is committed until the GM approves it.
```

This matters because the graph will contain candidates, breadcrumbs, unresolved threads, and ignored or diagnostic material. Candidate extraction must not visually read as canon.

---

## 7. The Core Frontend Job

The frontend should help the GM answer:

```txt
Did the system understand my recap?
What did it extract?
What is it unsure about?
What evidence supports each proposed node or relationship?
What should be written to graph memory?
What should be ignored, deferred, or corrected?
```

The preview must make uncertainty legible.

The preview must make evidence easy to inspect.

The preview must keep internal plumbing out of the GM's way.

---

## 8. Graph Concepts The Frontend Must Understand

### 8.1 Nodes

A node is a proposed memory object.

Nodes may represent named things:

```txt
characters
NPCs
places
factions
items
organizations
locations
scenes
sessions
```

Nodes may also represent unnamed but important things:

```txt
the courier
the warning
the archive return
the unresolved motive
the prior notes
a suspicious sound
a ritual clue
an unknown patron
a temporary alliance
a debt
a promise
an open threat
a mystery object
```

Frontend implication:

```txt
Do not design the graph as named entities only.
Unnamed important nodes are essential.
```

### 8.2 Session Beats

A session beat is a structured event or moment from the recap.

Examples:

```txt
party returns to archive
warning is compared against prior notes
courier motive remains unresolved
negotiation pause is established
key remains uncertain
```

Frontend implication:

```txt
Session beats should be visible as first-class timeline cards or graph nodes.
Do not hide events inside edge labels only.
```

### 8.3 Edges / Relationships

An edge is a proposed relationship between graph objects.

Examples:

```txt
Lysandra spoke_to courier
warning refers_to prior notes
party returned_to archive
courier delivered warning
motive remains_unresolved
archive key has_state uncertain
```

GM-facing presentation should prefer plain language:

```txt
Courier → delivered → Warning
```

before internal labels:

```txt
relationship_type: delivered_artifact_to_party
```

### 8.4 Evidence

Every meaningful node, edge, or proposed fact should have evidence.

Evidence is not just a count. Evidence must be clickable and must lead to a source span or structured field whenever available.

### 8.5 Source Refs

`source_ref_id` is a machine-readable handle, not a display label.

Its job:

```txt
click evidence
→ open source recap
→ scroll to relevant location
→ highlight exact span
```

Frontend rule:

```txt
Hide raw source_ref_id by default.
Expose it only in advanced/debug mode.
Require every evidence-backed claim to have a resolvable source ref.
```

Bad UI:

```txt
source-ref: normalized_recap_markdown:770bb489a1ddb74b
```

Good UI:

```txt
Evidence: Normalized recap → “The party returned to a sealed archive…”
[Open source]
```

### 8.6 Provenance

Provenance explains where a node, edge, or fact came from and how it was produced.

GM-facing provenance labels might be:

```txt
From recap
From breadcrumb
From extraction pass
Diagnostic only
Needs review
Not promoted
```

Internal provenance records belong behind an advanced toggle.

### 8.7 Semantic States

Semantic states are not backend trivia. They drive trust.

Important state vocabulary:

```txt
canon_state
lifecycle_state
evidence_role
authority_state
visibility_state
```

---

## 9. State Vocabulary: Frontend Translation

### 9.1 canon_state

Purpose: answers “is this story truth?”

```txt
played_canon         → Played canon
planning_scaffold    → Prep / scaffold
candidate_extraction → Candidate
diagnostic_only      → Diagnostic only
unknown              → Unknown
```

Rule:

```txt
Never visually equate candidate extraction with canon.
```

### 9.2 lifecycle_state

Purpose: answers “where is this in the pipeline?”

```txt
candidate  → Needs review
validated  → Validated
promoted   → Approved
rejected   → Rejected
diagnostic → Diagnostic
stale      → Stale
```

Rule:

```txt
Candidate nodes should look pending, not committed.
```

### 9.3 evidence_role

Purpose: answers “what can this source be used for?”

```txt
source_evidence → Evidence
navigation_hint → Navigation only
diagnostic_only → Diagnostic
not_evidence    → Not evidence
```

Rule:

```txt
Do not let display summaries become evidence.
If a claim has no source-evidence role, do not present it as grounded fact.
```

### 9.4 authority_state

Purpose: answers “who or what authorized this?”

```txt
played_truth   → Played truth
system_derived → System-derived
llm_generated  → AI candidate
gm_prep        → GM prep
diagnostic     → Diagnostic
unknown        → Unknown
```

Rule:

```txt
AI candidate output needs clear review-required treatment.
```

### 9.5 visibility_state

Purpose: answers “who can safely see this?”

```txt
gm_private          → GM only
player_visible      → Player visible
internal_diagnostic → Internal
spoiler_sensitive   → Spoiler
unknown             → Unknown
```

Rule:

```txt
Default this entire workflow to GM-private until a later sharing model exists.
```

---

## 10. Required Preview Modes

### 10.1 Timeline / Beat View

Purpose: session comprehension.

Shows:

```txt
session beats in order
linked nodes per beat
relationships introduced by each beat
evidence per beat
unresolved threads surfaced at the end
```

This may be more useful than graph view for initial GM trust because recaps are temporal.

### 10.2 Graph View

Purpose: spatial understanding.

Shows:

```txt
nodes
edges
clusters
selected node detail
selected relationship detail
evidence drawer
```

Must support:

```txt
filter by state
filter by node type
hide diagnostics
highlight unresolved threads
show only proposed writes
show canon/candidate differences
```

### 10.3 Proposed Write Diff View

Purpose: approval.

Shows:

```txt
nodes to create
nodes to update
edges to create
facts to attach
items to ignore
items deferred for later
candidate merges or aliases, if any exist later
```

Default action:

```txt
Preview only. No writes unless GM approves.
```

### 10.4 Evidence Review View

Purpose: trust.

Shows:

```txt
source snippet
supporting claim
source artifact type
exact highlighted span
nearby context
provenance
state labels
```

This can be a side panel, drawer, modal, or split pane.

### 10.5 Query Demo View

Purpose: prove graph memory value later.

Potential questions:

```txt
What named characters are in this session?
Give me a concise outline of recent sessions.
What were the last few things that happened?
Who did Lysandra talk to?
```

For now, design for query-result cards, not raw query authoring.

---

## 11. First Preview Should Not Be Too Smart

V0 does not need identity merge, canonical writeback, or multi-session reasoning.

V0 should prove:

```txt
A recap can become a believable graph candidate.
Each candidate has evidence.
The GM can understand the proposed memory.
The GM can approve/defer/reject at a coarse level.
```

That is enough.

---

## 12. Frontend Object Model To Prepare For

The exact backend schema may change, but frontend design should expect this shape.

```ts
type CandidateGraphPreview = {
  previewId: string;
  campaignId?: string;
  sessionId?: string;
  sourceArtifactIds: string[];
  status: "preview" | "approved" | "partially_approved" | "rejected" | "deferred";
  nodes: CandidateNode[];
  edges: CandidateEdge[];
  beats: SessionBeat[];
  proposedWrites: ProposedWrite[];
  ignoredItems: IgnoredItem[];
  diagnostics: PreviewDiagnostics;
};
```

```ts
type CandidateNode = {
  nodeId: string;
  label: string;
  nodeType:
    | "character"
    | "location"
    | "item"
    | "faction"
    | "event"
    | "session_beat"
    | "clue"
    | "thread"
    | "mystery"
    | "group"
    | "unknown_important";
  description?: string;
  importance?: "low" | "medium" | "high";
  semanticState: SemanticState;
  evidenceRefs: EvidenceRef[];
  aliases?: string[];
  proposedAction: "create" | "update" | "link" | "ignore" | "defer";
  confidence?: "low" | "medium" | "high";
  warnings?: string[];
};
```

```ts
type CandidateEdge = {
  edgeId: string;
  fromNodeId: string;
  toNodeId: string;
  label: string;
  relationshipType: string;
  semanticState: SemanticState;
  evidenceRefs: EvidenceRef[];
  proposedAction: "create" | "update" | "ignore" | "defer";
  confidence?: "low" | "medium" | "high";
  warnings?: string[];
};
```

```ts
type SessionBeat = {
  beatId: string;
  order: number;
  title: string;
  summary: string;
  involvedNodeIds: string[];
  evidenceRefs: EvidenceRef[];
  unresolvedThreadIds?: string[];
  proposedAction: "create" | "ignore" | "defer";
};
```

```ts
type EvidenceRef = {
  sourceRefId: string;
  sourceArtifactId: string;
  sourceAnchorId?: string;
  label: string;
  evidenceRole: "source_evidence" | "navigation_hint" | "diagnostic_only" | "not_evidence";
  span?: {
    startLine?: number;
    endLine?: number;
    startChar?: number;
    endChar?: number;
  };
  previewSnippet?: string;
  canOpenSource: boolean;
  canHighlightSpan: boolean;
};
```

```ts
type SemanticState = {
  canonState: "played_canon" | "planning_scaffold" | "candidate_extraction" | "diagnostic_only" | "unknown";
  lifecycleState: "candidate" | "validated" | "promoted" | "rejected" | "stale" | "diagnostic";
  evidenceRole: "source_evidence" | "navigation_hint" | "diagnostic_only" | "not_evidence";
  authorityState: "played_truth" | "gm_prep" | "system_derived" | "llm_generated" | "diagnostic" | "unknown";
  visibilityState: "gm_private" | "player_visible" | "internal_diagnostic" | "spoiler_sensitive" | "unknown";
};
```

```ts
type ProposedWrite = {
  writeId: string;
  writeType: "create_node" | "update_node" | "create_edge" | "attach_fact" | "mark_ignored" | "defer";
  targetId: string;
  label: string;
  reason: string;
  evidenceRefs: EvidenceRef[];
  status: "pending" | "approved" | "rejected" | "deferred";
};
```

---

## 13. Source Evidence UX

Evidence is the trust layer.

Recommended behavior:

```txt
Click node
→ detail panel opens
→ shows summary, state chips, proposed action
→ evidence section lists source snippets
→ click evidence
→ source drawer opens
→ exact span is highlighted
```

The source drawer should show:

```txt
artifact kind
source label
snippet
line/section context
highlight
evidence role
provenance summary
advanced metadata toggle
```

Do not show raw opaque IDs unless advanced mode is enabled.

---

## 14. Chips And Agent Interaction Integration

Future Agent Interaction should render answer text with chips.

Example:

```txt
Lysandra warned the party after the archive incident.
```

Future chip behavior:

```txt
Lysandra → entity chip
archive incident → event/beat chip
warned → relationship/evidence affordance if useful
```

Chip hover/click should show:

```txt
entity card
recent session context
source evidence
relevant relationships
provenance
graph/source refs for deeplink
advanced metadata if enabled
```

Do not build the full chip system yet.

Prepare the design language:

```txt
entity chip
evidence chip
unresolved-thread chip
warning / candidate chip
GM-only / spoiler chip
```

---

## 15. Visual Language Recommendations

### Canon / Candidate

```txt
Canon      → solid treatment
Candidate  → dotted border, pending badge, or review color
Diagnostic → muted / secondary
Ignored    → dimmed or collapsed
Thread     → question-mark or thread badge
```

### Evidence Role

```txt
Source evidence → strong citation icon
Navigation hint → compass / breadcrumb icon
Diagnostic only → wrench / internal icon
Not evidence    → disabled citation icon
```

### Visibility

```txt
GM private        → lock icon
Player visible    → eye icon
Spoiler sensitive → warning / hidden icon
Internal          → tool icon
```

### Proposed Action

```txt
Create → plus
Update → pencil
Link   → chain
Ignore → crossed-out
Defer  → clock
```

---

## 16. Suggested First Screen

Title:

```txt
Recap Memory Preview
```

Header:

```txt
Session: <session title>
Status: Preview only
Source: <recap artifact>
Readiness: <ready / warning / blocked>
```

Main sections:

```txt
Timeline
Graph
Selected Item
Evidence
Proposed Writes
Ignored / Deferred
```

Primary CTA:

```txt
Approve selected
```

Secondary CTAs:

```txt
Reject selected
Defer selected
Open source
Show diagnostics
```

Warning banner:

```txt
This preview is generated from recap text. Nothing has been written to graph memory yet.
```

---

## 17. Backend Contracts To Ask For Later

Do not implement these endpoints yet unless explicitly authorized.

### Preview Graph Endpoint

```txt
POST /graph-memory/preview-recap
```

Input:

```txt
recap artifact ID or pasted recap
campaign/session context
extraction options
preview mode
```

Output:

```txt
CandidateGraphPreview
```

### Source Evidence Endpoint

```txt
GET /graph-memory/source/:sourceRefId
```

Output:

```txt
source artifact metadata
snippet
span
surrounding context
highlight coordinates
provenance
visibility/canon/evidence states
```

### Approval Endpoint

```txt
POST /graph-memory/previews/:previewId/approve
```

Input:

```txt
approved write IDs
rejected write IDs
deferred write IDs
GM notes
```

Output:

```txt
write result
updated graph memory IDs
warnings
```

### Query Endpoint

```txt
POST /graph-memory/query
```

Input:

```txt
constrained operation
params
scope
```

Output:

```txt
answer payload
nodes
edges
evidence refs
chip configs
```

---

## 18. Frontend Design Deliverables For The Next Design Slice

The frontend design agent should produce:

```txt
1. Screen map for graph memory recap preview.
2. Wireframe for graph + timeline split view.
3. Node detail panel design.
4. Edge detail panel design.
5. Evidence drawer design.
6. Proposed write diff panel.
7. Chip/deeplink concept for future Agent Interaction.
8. State-chip visual vocabulary.
9. Backend fields required for v0.
10. Intentionally hidden advanced fields.
11. Failure-state design for non-resolvable source refs.
12. Design note on what not to build yet.
```

---

## 19. Design Questions

```txt
1. Is graph canvas or timeline the primary comprehension view?
2. What is the smallest useful node card?
3. What edge labels are readable enough for GMs?
4. How should candidate vs canon be visually separated?
5. What does source evidence look like in one click?
6. How should unresolved threads be surfaced?
7. Where should ignored / not-promoted material live?
8. How much diagnostic metadata is helpful before it becomes noise?
9. What should be shown in normal mode versus advanced mode?
10. What would make Alan trust or distrust the preview?
11. What is the simplest future Agent Interaction chip design?
12. What backend fields are mandatory for a meaningful first UI?
```

---

## 20. Strong Warnings

Do not design from current count reports. Those reports are developer diagnostics.

Do not make the UI about:

```txt
number of source artifacts
number of payload units
schema names
readiness schema
materializer schema
opaque IDs
raw diagnostic tables
```

Design from the GM job:

```txt
Did the system understand my session recap, and can I safely approve this memory?
```

Do not present these as final truth before GM approval:

```txt
LLM-extracted entities
inferred relationships
unresolved threads
candidate aliases
candidate merges
generated summaries
display summaries
diagnostic proof records
```

---

## 21. Do Not Build Yet

Do not implement React components yet unless asked.

Do not choose a graph visualization library yet unless asked.

Do not wire API calls.

Do not change live-control UI.

Do not alter Agent Interaction.

Do not add routes.

Do not create query executor UI.

Do not create graph write approval mechanics.

This handoff is for design preparation.

---

## 22. Success Criteria

The design agent succeeds if it can answer:

```txt
What does the GM need to see to trust a recap-derived graph preview?
What graph concepts must be visible?
What graph concepts must remain hidden?
How does source evidence become inspectable?
How will this later connect to Agent Interaction chips?
What backend contracts are needed before implementation?
What must not be built yet?
```

The design agent fails if it produces:

```txt
a generic graph viewer
a diagnostics dashboard
a UI that treats candidate extraction as canon
```
