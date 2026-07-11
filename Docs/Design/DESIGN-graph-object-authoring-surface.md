# Design — Graph Object Authoring Surface

**Status:** Current architecture checkpoint; implementation trail retained below
**Date:** 2026-07-09
**Workstream:** Graph Memory / Memory Ingest / Graph Review / Graph Authoring  
**Companion roadmap:** `Docs/Plans/ROADMAP-graph-object-authoring-surface.md`  
**Supersedes product framing in:** `Docs/Design/DESIGN-graph-review-gold-authoring-workbench.md` where that document treats gold fixtures as the primary authoring destination.  
**Closeout:** `Docs/Reports/SPIKE-CLOSEOUT-graph-review-authored-memory-2026-07.md`
**Related docs:**

- `Docs/Plans/HANDOFF-prime-design-graph-review-workbench-authoring-next.md`
- `Docs/Plans/ROADMAP-graph-review-gold-authoring-workbench.md`
- `Docs/Plans/DOGFOOD-graph-review-authoring-loop-session-1.md`
- `Docs/Plans/AUDIT-ingest-surface-page-inventory.md`
- `Docs/Plans/FOLLOWUP-raw-dmb-node-links-and-duplicate-projected-objects.md`
- `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md`
- `Docs/Design/DESIGN-plan-surface-session-prep-current-goal-2026-07.md`
- `Docs/Design/ARCHITECTURE-campaign-supergraph.md`

---

## Current implementation checkpoint (historical / transitional truth)

The core authored-memory loop has landed through PR #305. Graph Review is the **correction cockpit**: a GM-facing surface for inspecting a live projection, authoring campaign graph assertions, and reviewing the resulting memory.

**TRANSITIONAL (current runtime — not the target durable path):**

- Authored object, link-existing, relationship, and merge-object assertions write to a campaign-scoped **authored overlay and event log** (not yet GraphContribution → Kernel → atomic graph-head).
- Normal staged work uses prepare → review → commit. The create-object wizard prepares and commits one object in a compact review+confirm flow — **object creation is NOT implicit confirmation**; the operator still explicitly confirms that single proposal.
- A committed identity merge materializes into the **selected preview union store** only when `previewUnionStorePath` is present and overlay plus event-log writes both succeed.
- Projection reload **prefers that selected live store** over a frozen manifest snapshot.
- A corrected merge supersedes an earlier survivor decision only when it explicitly merges away the prior survivor; the event log records old and new assertion IDs.

**TARGET write path** (per `Docs/Design/CONTRACT-agent-tool-authored-prep-contributions-v0.md` and Campaign Supergraph architecture):

```text
preview_write proposal
→ explicit proposal-bound / revision-bound GM confirm
→ GraphContribution
→ Kernel validation
→ atomic graph-head advancement
```

Graph Review/Ingest remains the primary correction cockpit. Plan is a **consumer surface** that may draft and launch preview_write but does not own durable commit semantics.

The selected-object card is game-first; evidence, provenance, review state, and raw IDs sit behind collapsed **Details**.

Materialization does not mutate source recap markdown, ingest artifacts, or gold fixtures. It does not import sibling-run nodes, evidence, or edges. Undo/retract, player-facing views, LLM assistance, and broader graph editing remain deferred.

### Plan consumption boundary

Graph Object Authoring (Graph Review/Ingest) owns campaign-memory **correction and governed commits**. `/plan` is a **consumer surface** that consumes reviewed graph/corpus memory for session preparation, including reusable game-facing selected-object cards and source-context projections. It may draft prep and launch preview_write but does not own Author Draft, authored-overlay/event-log commits, identity merging, or diagnostics in its default prep flow unless a future dogfood pass proves one specific correction need. See `Docs/Design/DESIGN-plan-surface-session-prep-current-goal-2026-07.md`.

## 1. Prime Design decision

The primary destination of manual authoring is **the authored campaign graph**, not a gold fixture and not the raw recap markdown.

Gold/evaluation artifacts are an advanced developer byproduct derived from authored graph corrections. They exist to tune, measure, and improve ingestion. They are not the normal user-facing reason the GM authors graph objects.

The current operator flow is:

```text
Ingestion
  -> review projected source material
  -> select a word, phrase, existing pill, or relationship context
  -> declare campaign graph objects and links
  -> stage normal authored graph assertions locally
  -> prepare a safe write preview and commit reviewed authored graph memory
  -> or create one object with the explicitly immediate create-object wizard
  -> append authoring event log
  -> materialize committed identity merges into the selected live preview union store when available
  -> refresh graph exploration/query views
  -> optionally derive/update graph-gold evaluation signal
```

This replaces the older mental model:

```text
Ingestion -> graph gold -> query/explore
```

with:

```text
Ingestion -> authored campaign graph -> query/explore/play support
                         \
                          -> gold/eval signal for developer tuning
```

## 2. Product thesis

Graph Object Authoring is the bridge between ingested source material and durable campaign memory.

After ingestion, a GM/developer can select source prose, declare that phrase as a graph object, connect it to recap/worldbuilding/party/GM-private graph objects, choose visibility, and commit the reviewed assertion into the campaign graph. The same action is also recorded as a learning signal so missed extraction behavior can be improved later.

The user-facing promise:

```text
I can read the ingested recap, touch the words that matter, and teach DungeonBuddy what those words mean in the campaign graph.
```

The developer-facing promise:

```text
Every human correction becomes durable graph memory and structured evidence of what ingestion missed, overfit, duplicated, or failed to connect.
```

## 3. What this is not

This is not a graph dashboard.  
This is not a generic node-link diagram editor.  
This is not a gold-fixture-only labeling tool.  
This is not a corpus markdown editor.  
This is not a general-purpose identity merge console.  
This is not an LLM write path.  
This is not a player-facing graph explorer yet.

The source prose remains the human interaction surface. The graph is authored from the prose and projected back into exploration/query tools.

## 4. Existing infrastructure to reuse

### 4.1 Memory Ingest / Graph Review surface

The current `/ingest` workbench already has the needed framing pieces:

- `Ingest Recap` brings source material into the system.
- `Graph Review` renders projected prose from graph-ingest runs.
- `Diagnostics` and advanced debug panels exist but should not dominate the default path.
- `Author Draft` already stages some local graph-authoring intent.
- Live graph-ingest runs can be reviewed even when no gold fixture exists.
- dmb-node pill rendering is now unified around embedded `[label](dmb-node:id)` links.

Relevant frontend paths:

```text
apps/live-control-ui/src/planSurface/config/ingestSurfaceConfig.ts
apps/live-control-ui/src/planSurface/graphReviewWorkbench/
apps/live-control-ui/src/planSurface/graphProjectionReader/
apps/live-control-ui/src/modules/IngestionModule.tsx
```

Relevant backend paths:

```text
src/graph_memory/projection/recap_projection.py
apps/live_control_server/services/graph_object_authoring_prepare.py
apps/live_control_server/services/graph_object_authoring_commit.py
apps/live_control_server/services/graph_authoring_event_log.py
apps/live_control_server/services/graph_authoring_overlay_projection.py
apps/live_control_server/services/union_supergraph_projection_adapter.py
src/graph_memory/union_supergraph/
```

The current **transitional** product write path is authored overlay plus event log. Gold-authoring services may remain for developer evaluation workflows, but they are not the normal Graph Review destination. The **target** path is GraphContribution → Kernel validation → atomic graph-head advancement.

### 4.2 Tiptap markdown infrastructure

The live-control UI already has robust Tiptap infrastructure and dependencies:

```text
apps/live-control-ui/package.json
  @tiptap/core
  @tiptap/pm
  @tiptap/react
  @tiptap/starter-kit
```

The existing `GraphProjectionReader` already renders projected markdown through read-only Tiptap:

```text
apps/live-control-ui/src/planSurface/graphProjectionReader/GraphProjectionReader.tsx
```

It imports:

```text
EditorContent
useEditor
StarterKit
GraphNodeReferenceNode
markdownToTiptapDoc
```

and currently converts markdown into a Tiptap document with:

```ts
markdownToTiptapDoc(markdown, { parseGraphNodeLinks: true })
```

The existing graph-reference extension is exactly the right model for already-projected graph objects:

```text
apps/live-control-ui/src/tiptap/extensions/GraphNodeReferenceNode.ts
apps/live-control-ui/src/tiptap/extensions/GraphNodeReferenceView.tsx
```

`GraphNodeReferenceNode` is:

```text
inline
atom
selectable
has nodeId + label attrs
rendered as button[data-graph-node-id]
rendered via ReactNodeViewRenderer(GraphNodeReferenceView)
```

The markdown importer already parses:

```md
[label](dmb-node:node_id)
```

into `graphNodeReference` nodes when `parseGraphNodeLinks` is true:

```text
apps/live-control-ui/src/tiptap/markdown/markdownToTiptap.ts
apps/live-control-ui/src/tiptap/markdown/markdownToTiptap.test.ts
```

The Tiptap callout/runbook spike proves additional reusable patterns:

```text
apps/live-control-ui/src/tiptap/TiptapCalloutBridgeSpike.tsx
apps/live-control-ui/src/tiptap/state/tiptapLocalState.ts
apps/live-control-ui/src/tiptap/markdown/calloutMarkdown.ts
apps/live-control-ui/src/tiptap/references/runbookReferences.ts
apps/live_control_server/services/tiptap_markdown_write.py
```

Useful concepts from that spike:

- local browser working state;
- semantic markdown import/export;
- custom inline reference nodes;
- custom block/callout nodes;
- active block boundary detection;
- editor lock/unlock state;
- prepare/diff/confirm/commit safety shape;
- stale confirm-token conflict rejection;
- file backup behavior.

Do not reuse the Tiptap markdown writer as the graph-authoring writer. Reuse it as a safety precedent.

## 5. Design stance on Tiptap

Tiptap should be the source-prose interaction substrate for graph authoring.

Tiptap owns:

- rendered source/projection document;
- text selection;
- block/paragraph context;
- existing graph-node reference atoms;
- future inline visual authoring marks if needed.

Graph Object Authoring owns:

- staged graph assertions;
- aliases;
- relationships;
- visibility/audience fields;
- resolver/link-existing decisions;
- prepare preview;
- commit;
- authoring event log;
- gold/eval signal.

Explicit rule:

```text
Tiptap produces GraphAuthoringSelection.
Graph Object Authoring consumes GraphAuthoringSelection.
```

This is the seam that keeps the authoring component independent and movable.

## 6. Product language

Prefer these names:

```text
Graph Object Authoring
Graph Authoring
Campaign Graph Authoring
Authored Campaign Graph
Authored Memory
Find existing object
Check for existing match
Relationship type
Stage locally
Prepare graph write preview
Commit authored graph changes
```

Avoid user-facing names that make gold the product target:

```text
Gold Authoring
Gold fixture editor
candidate_graph_gold editor
Resolver
Predicate
```

Gold may appear in advanced/developer copy:

```text
Advanced: include this authored correction in graph-gold evaluation data.
```

## 7. Conceptual graph layers

The durable campaign graph needs to support multiple graph scopes and audience views.

Minimum layers/scopes:

```text
recap_graph
  Objects and relationships extracted/authored from session recaps.

worldbuilding_graph
  Places, factions, lore, cosmology, NPCs, items, settlements, history.

campaign_memory_graph
  Cross-session graph used for query, exploration, timeline construction, prep, and play support.

gm_private_graph
  Secrets, future reveals, hidden motives, unrevealed truth, encounter plans, prep-only notes.

player_visible_graph
  What players may browse later without seeing GM-private information.

evaluation_gold
  Developer-facing measurement/tuning slices derived from human-authored corrections.
```

These are not necessarily separate physical stores in v0. They may be scopes/views on authored graph assertions.

## 8. Minimum assertion model

Every authored graph assertion should carry enough information to answer:

```text
What was selected?
What did the human declare?
Where did the assertion come from?
What graph object or relationship changed?
Who can see it?
Was it extracted, human-authored, imported, inferred, or derived?
Should it contribute to gold/eval?
```

### 8.1 Authored object assertion

```ts
interface AuthoredGraphObjectAssertion {
  assertion_id: string;
  assertion_kind: "object";
  operation: "create" | "update" | "alias" | "link_existing";

  campaign_id: string;
  session_id?: string | null;
  source_artifact_path?: string | null;
  source_artifact_sha256?: string | null;

  object_ref: {
    node_id: string;
    label: string;
    kind: string;
    role?: string | null;
    aliases?: string[];
    summary?: string | null;
  };

  source_anchor: GraphAuthoringSourceAnchor;
  provenance: GraphAuthoringProvenance;
  visibility: GraphVisibilityPolicy;
  graph_scope: GraphScope[];

  include_in_gold_eval: boolean;
  gold_eval_notes?: string | null;
}
```

### 8.2 Authored relationship assertion

```ts
interface AuthoredGraphRelationshipAssertion {
  assertion_id: string;
  assertion_kind: "relationship";
  operation: "create" | "update" | "link_existing";

  campaign_id: string;
  session_id?: string | null;
  source_artifact_path?: string | null;
  source_artifact_sha256?: string | null;

  source_node_ref: GraphNodeRef;
  target_node_ref: GraphNodeRef;
  relationship_type: string;
  relationship_label?: string | null;
  direction: "directed" | "undirected";
  summary?: string | null;

  source_anchor: GraphAuthoringSourceAnchor;
  provenance: GraphAuthoringProvenance;
  visibility: GraphVisibilityPolicy;
  graph_scope: GraphScope[];

  include_in_gold_eval: boolean;
  gold_eval_notes?: string | null;
}
```

### 8.3 Source anchor

Tiptap positions alone are not durable enough. Store redundant anchors.

```ts
interface GraphAuthoringSourceAnchor {
  anchor_kind: "text_span" | "graph_node_reference" | "block" | "relationship_context";
  selected_text: string;
  normalized_selected_text: string;
  surrounding_text_before?: string | null;
  surrounding_text_after?: string | null;
  paragraph_ordinal?: number | null;
  source_span_ref_id?: string | null;
  tiptap_from?: number | null;
  tiptap_to?: number | null;
  selected_text_sha256?: string | null;
  context_sha256?: string | null;
  existing_graph_node_id?: string | null;
}
```

### 8.4 Provenance

```ts
interface GraphAuthoringProvenance {
  origin: "human_authored" | "human_corrected_extraction" | "imported_worldbuilding" | "llm_proposed_human_accepted";
  authoring_surface: "memory_ingest_graph_authoring";
  created_at: string;
  updated_at?: string | null;
  source_run_id?: string | null;
  source_graph_id?: string | null;
  source_projection_id?: string | null;
  operator_note?: string | null;
}
```

### 8.5 Visibility

Visibility must enter the model now because future player access depends on it.

```ts
type GraphVisibility =
  | "gm_private"
  | "player_visible"
  | "table_known"
  | "character_specific"
  | "hidden_until_revealed";

interface GraphVisibilityPolicy {
  visibility: GraphVisibility;
  visible_to_player_ids?: string[];
  visible_to_character_ids?: string[];
  reveal_state?: "unrevealed" | "partial" | "revealed";
  visibility_note?: string | null;
}
```

v0 default:

```text
visibility = gm_private
reveal_state = unrevealed
```

The UI may expose a simple dropdown initially:

```text
GM private
Table known / player visible
Character-specific
Hidden until revealed
```

### 8.6 Graph scope

```ts
type GraphScope =
  | "recap_graph"
  | "worldbuilding_graph"
  | "campaign_memory_graph"
  | "gm_private_graph"
  | "player_visible_graph"
  | "evaluation_gold";
```

A single assertion may participate in more than one scope.

Example:

```json
{
  "graph_scope": ["recap_graph", "campaign_memory_graph", "evaluation_gold"],
  "visibility": { "visibility": "table_known", "reveal_state": "revealed" }
}
```

## 9. The “gang” example as canonical design proof

Source text in Session 2 uses the word:

```text
gang
```

The human knows that in this recap context, “gang” refers to the adventuring party and should connect to the group identity later known as Questionable Company and to the player characters.

The authoring flow should support:

```text
1. Select “gang” in the ingested recap projection.
2. Choose “Author graph object.”
3. Declare or link object:
   - label: Questionable Company
   - kind: party
   - aliases: gang
4. Link relationships:
   - Questionable Company has_member Bonogo
   - Questionable Company has_member Baergrom
   - Questionable Company has_member Ephanna
   - Questionable Company has_member Caelynn
   - Questionable Company has_member Stafl
   - Questionable Company has_member Karsemine
5. Choose visibility:
   - likely table_known or player_visible once party identity is table-known
6. Stage locally.
7. Prepare preview.
8. Commit authored campaign graph.
9. Append event log explaining ingestion missed a party-reference alias/link.
10. Optionally emit graph-gold/eval signal.
```

Important evaluation nuance:

If the name “Questionable Company” is learned later in the campaign, the event should record knowledge scope:

```ts
type KnowledgeScope =
  | "session_local"
  | "campaign_retrospective"
  | "cross_session_context_required";
```

For this example, the assertion may be:

```text
knowledge_scope = campaign_retrospective
```

This prevents future evals from unfairly punishing a session-local extraction run for not knowing later campaign knowledge.

## 10. UX architecture

### 10.1 Surface location

For now, Graph Object Authoring lives only on the Memory Ingest / Graph Review surface.

Do not put this in `/plan` generically yet.  
Do not create a global graph editor yet.  
Do not make it player-facing yet.

### 10.2 Component independence

The authoring tool should be independent and movable:

```text
It can be opened from selected text.
It can be opened from a projected graph pill.
It can live in a toolbox panel.
It can be launched from a contextual popup.
It can later move beside a Tiptap reader or into a dedicated split pane.
```

The trigger is contextual. The full workflow lives in the authoring component.

### 10.3 Recommended UI shape

v0 should use:

```text
Tiptap source/projection reader
  -> small contextual selection action
  -> Graph Object Authoring Surface in the toolbox or side panel
  -> local staging tray
  -> prepare/commit panel
```

Contextual popup actions:

```text
Author graph object
Link to existing object
Create relationship
```

Full authoring surface sections:

```text
Selected source
Declare object
Find existing object
Declare links / relationships
Visibility and scope
Staged changes
Prepare preview
Commit
Advanced gold/eval signal
```

### 10.4 Read-only source, writable graph

The Tiptap document should remain visually/read-semantically read-only in v0. The user selects from it, but the source markdown is not directly edited.

Do not insert source markdown links during local staging. If an authored object should appear as a pill after commit, the projection layer should render it from authored graph assertions.

If later markdown annotation is required, it must be a separate design decision.

## 11. Frontend architecture

### 11.1 New selection adapter

Create a Tiptap-backed selection adapter around `GraphProjectionReader`.

Likely files:

```text
apps/live-control-ui/src/planSurface/graphProjectionReader/GraphProjectionReader.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphAuthoringSelection.ts
apps/live-control-ui/src/planSurface/graphReviewWorkbench/useGraphAuthoringSelection.ts
```

Suggested contract:

```ts
export interface GraphAuthoringSelection {
  campaignId: string;
  sessionId: string;
  sourceArtifactPath?: string | null;
  sourceArtifactSha256?: string | null;

  selectionKind: "text_span" | "graph_node_reference" | "block" | "relationship";
  selectedText: string;
  surroundingTextBefore?: string | null;
  surroundingTextAfter?: string | null;
  paragraphOrdinal?: number | null;
  sourceSpanRefId?: string | null;

  tiptapFrom?: number | null;
  tiptapTo?: number | null;

  existingNodeId?: string | null;
  existingLabel?: string | null;

  graphId?: string | null;
  laneRole?: "gold" | "live" | "authored" | null;
}
```

Implementation guidance:

- Use Tiptap `onSelectionUpdate` or an explicit ProseMirror plugin to observe selection changes.
- Use `editor.state.selection.from` and `editor.state.selection.to` for transient positions.
- Use `editor.state.doc.textBetween(from, to, "\n")` to get selected text.
- Resolve the closest block/paragraph around `$from` to capture block context.
- Detect when selection is a `graphNodeReference` atom and emit `selectionKind = graph_node_reference`.
- Store redundant source anchors; do not trust Tiptap positions alone for durable provenance.
- Ignore blank/whitespace selections.
- Bound selection length in v0, for example max 200 characters for “Author object” action.

### 11.2 Extend GraphProjectionReader props

Add optional authoring props without making all readers writable:

```ts
interface GraphProjectionReaderProps {
  // existing props...
  authoringEnabled?: boolean;
  onGraphAuthoringSelection?: (selection: GraphAuthoringSelection | null) => void;
  onGraphAuthoringAction?: (selection: GraphAuthoringSelection, action: GraphAuthoringAction) => void;
}
```

Do not require every projection reader to support authoring. Authoring is enabled only on the Memory/Graph Review surface.

### 11.3 New authoring surface components

Likely files:

```text
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringSurface.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringSelectedSource.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringObjectForm.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringRelationshipForm.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringVisibilitySection.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringStagingTray.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringPrepareCommitPanel.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/useGraphObjectAuthoringDraft.ts
```

The component should consume `GraphAuthoringSelection` and produce staged proposals:

```ts
type GraphObjectAuthoringProposal =
  | AuthoredObjectProposal
  | AuthoredRelationshipProposal
  | AuthoredAliasProposal
  | AuthoredVisibilityProposal
  | AuthoredExistingLinkProposal;
```

### 11.4 Reuse existing resolver, but rename in UI

Current resolver concepts should become user-facing “Find existing object.”

The UI should say:

```text
DungeonBuddy can check whether this selected text or object already exists in the campaign graph. Suggestions are read-only until you stage one. No link or merge is written here.
```

Do not expose “Resolver” as the primary heading.

### 11.5 Local draft state

Reuse the spirit of `useGraphReviewAuthorDraftWorkflow`, but rename/reframe the state as graph authoring rather than gold authoring.

Likely new hook:

```text
useGraphObjectAuthoringDraft
```

State should include:

```ts
interface GraphObjectAuthoringDraftState {
  selectedSource: GraphAuthoringSelection | null;
  proposals: GraphObjectAuthoringProposal[];
  relationshipSource: GraphNodeRef | null;
  mode: "inspect" | "select_source" | "author_object" | "link_existing" | "author_relationship" | "review_staged";
  dirty: boolean;
}
```

## 12. Backend architecture

### 12.1 New service boundary

Do not overload `graph_gold_authoring_prepare.py` as the product writer. Create a graph-authoring service boundary.

Likely files:

```text
src/graph_memory/authoring/contracts.py
src/graph_memory/authoring/store.py
src/graph_memory/authoring/events.py
src/graph_memory/authoring/apply.py
apps/live_control_server/services/graph_object_authoring_prepare.py
apps/live_control_server/services/graph_object_authoring_commit.py
apps/live_control_server/routes/graph_preview.py
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/api/types.ts
```

The backend may internally reuse helper logic from current gold-authoring code, but the public contract should be graph-authoring oriented.

### 12.2 Prepare endpoint

Suggested route:

```text
POST /api/live/graph-authoring/prepare
```

Request:

```ts
interface GraphObjectAuthoringPrepareRequest {
  campaign_id: string;
  session_id?: string | null;
  source_artifact_path?: string | null;
  source_artifact_sha256?: string | null;
  base_authored_graph_fingerprint?: string | null;
  proposals: GraphObjectAuthoringProposal[];
  include_gold_eval_signal?: boolean;
}
```

Response:

```ts
interface GraphObjectAuthoringPrepareResponse {
  schema_version: "dmb_graph_object_authoring_prepare_v1";
  writer_ok: boolean;
  writer_phase: "prepare";
  campaign_id: string;
  session_id?: string | null;
  target_authored_graph_relpath: string;
  target_event_log_relpath: string;
  target_gold_eval_relpath?: string | null;
  authored_graph_fingerprint_before: string | null;
  authored_graph_fingerprint_after: string;
  writer_confirm_token: string | null;
  preview_summary: GraphAuthoringPreviewSummary;
  preview_diff: string | null;
  warnings: string[];
  diagnostics: string[];
}
```

### 12.3 Commit endpoint

Suggested route:

```text
POST /api/live/graph-authoring/commit
```

Request:

```ts
interface GraphObjectAuthoringCommitRequest {
  campaign_id: string;
  session_id?: string | null;
  source_artifact_path?: string | null;
  proposals: GraphObjectAuthoringProposal[];
  writer_confirm_token: string;
  include_gold_eval_signal?: boolean;
}
```

Response:

```ts
interface GraphObjectAuthoringCommitResponse {
  schema_version: "dmb_graph_object_authoring_commit_v1";
  writer_ok: boolean;
  writer_phase: "commit";
  campaign_id: string;
  session_id?: string | null;
  authored_graph_relpath: string;
  authored_graph_fingerprint: string;
  authored_graph_backup_relpath?: string | null;
  event_log_relpath: string;
  event_count: number;
  gold_eval_relpath?: string | null;
  diagnostics: string[];
}
```

### 12.4 v0 storage target

Recommended v0: file-backed authored graph overlay, not direct mutation of extracted run artifacts.

Suggested repo-relative layout:

```text
corpus/eldyrwild-markdown/<Campaign>/_graph_authoring/
  authored_graphs/
    session-2.authored-graph.json
  events/
    session-2.authoring-events.jsonl
  exports/
    session-2.graph-gold-eval.json
```

If the campaign path mapping is too risky for the first PR, use a temporary explicit store under a graph-memory artifacts path, but keep the schema and contract named as authored campaign graph.

Do not write into:

```text
raw ingest run directories
preview union store artifacts
source recap markdown
candidate_graph_gold as the primary product target
```

### 12.5 Event log

Every commit appends event records.

```json
{
  "schema": "dmb_graph_authoring_event_v1",
  "event_id": "...",
  "timestamp": "...",
  "campaign_id": "longmont-c1",
  "session_id": "session-2",
  "source_artifact_path": "corpus/.../Session 2 - ...md",
  "action": "create_object | add_alias | create_relationship | link_existing | set_visibility",
  "origin": "human_authored",
  "selected_text": "gang",
  "source_anchor": {},
  "before": {},
  "after": {},
  "include_in_gold_eval": true,
  "knowledge_scope": "campaign_retrospective",
  "operator_note": "In this recap context, gang refers to the party."
}
```

Do not defer the event log. It is core to learning from manual corrections.

## 13. Projection and query integration

After commit, authored graph assertions must become available to graph exploration/querying.

v0 options:

1. **Layer authored graph into projection immediately** without rerunning extraction.
2. **Trigger/recommend graph refresh** and then reload projection.
3. **Render an authored overlay lane** until the next graph build includes it.

Recommended v0:

```text
Commit writes authored graph overlay and event log.
The current projection reloads with authored overlay applied as an additional graph source.
A full re-ingest is not required to see the authored object.
```

This preserves the product promise:

```text
I committed the authored object; now the graph knows it.
```

Backend implication:

- projection services must be able to merge extracted run graph + authored graph overlay;
- authored assertions must have stable IDs;
- authored objects should render as pills using the same `dmb-node` / `graphNodeReference` mechanism;
- authored graph source should be visibly labeled but not metadata-heavy.

Possible lane labels:

```text
Ingested recap
Authored campaign graph
Reviewed graph memory
```

Avoid “live-only mode” as a durable product term.

## 14. Gold/eval export

Gold/eval export is advanced developer functionality.

The authored graph write may include:

```text
include_in_gold_eval = true
```

When true, the commit or a later export task emits a graph-gold/eval artifact derived from the authored assertions.

Purpose:

- measure extraction quality;
- tune prompts/rules/schema;
- identify missed relationships;
- compare future graph-ingest runs against human-authored truth.

Do not make gold/eval export the normal user-facing success state.

Preferred UI copy:

```text
Advanced: include these authored corrections in graph-evaluation data.
```

## 15. Visibility and future player access

Future players should be able to query/explore graph memory without seeing GM-private information.

Therefore every authored assertion needs visibility metadata from v0.

Minimum rules:

```text
1. New authored graph assertions default to GM private.
2. The user may mark table-known/player-visible assertions explicitly.
3. Query/exploration APIs must eventually accept an audience/viewer context.
4. Player-facing views must filter out gm_private and hidden_until_revealed assertions.
5. GM view sees all assertions with visibility labels.
```

Do not build player access in the first implementation slice, but do not ship authored graph storage without visibility fields.

## 16. Safety and write guardrails

Normal staged writes require:

```text
prepare (preview_write)
preview/diff
explicit proposal-bound / revision-bound commit (confirm_commit)
stale-token / stale-revision rejection
backup when replacing existing file
append-only event log (transitional) / GraphContribution lineage (target)
clear diagnostics that no source markdown or extracted run artifact was mutated
```

The create-object wizard uses a **compact review+confirm** for a single object proposal — it is **not** an exception to explicit confirmation. The operator still confirms that one bound proposal before any durable write. Object creation is NOT implicit confirmation.

Committed identity merges may additionally materialize only into the selected live preview union store (**transitional**), after overlay and event-log success. This path must not import sibling-run artifacts and must never run after event-log failure. **Target:** materialization follows Kernel merge and atomic graph-head advancement only.

The UI must always distinguish:

```text
staged locally
prepared preview
committed authored graph
exported gold/eval signal
```

Never imply:

```text
identity chosen automatically
gold promoted automatically
LLM confirmed
magic write
save all
```

## 17. Implementation slices in design terms

The first coding slice should not attempt the full write path.

Recommended first implementation goal:

```text
Tiptap-backed source selection -> GraphAuthoringSelection -> local graph object proposal -> visible staging tray.
```

Second implementation goal:

```text
Persist authored graph overlay through prepare/commit and append event log.
```

Third implementation goal:

```text
Reload projection with authored graph overlay applied.
```

Fourth implementation goal:

```text
Gold/eval export and dogfood evaluation loops.
```

## 18. Acceptance criteria

### 18.1 Selection substrate

- User can select raw text in a projected recap.
- Blank selection is ignored.
- Selection captures selected text and context.
- Selection can distinguish existing graph-node reference atom from raw text.
- Existing graph chips still open inspection behavior.
- Selection can launch Graph Object Authoring without turning the whole reader into a markdown editor.

### 18.2 Local authoring

- User can select “gang” and stage it as an object or alias.
- User can choose object kind/type.
- User can link to an existing party/worldbuilding/recap object if available.
- User can stage relationships from selected/source object to target objects.
- User can choose relationship type.
- User can set visibility.
- Staged assertions clearly say no graph write has happened yet.

### 18.3 Commit

- Prepare shows target authored graph path, event log path, preview summary, and diff.
- Commit rejects stale graph file state.
- Commit writes authored graph overlay.
- Commit appends event log records.
- Commit does not mutate source recap markdown.
- Commit does not mutate extracted run artifacts.
- Commit can optionally produce gold/eval export.

### 18.4 Projection/query

- After commit/reload, authored object appears in projection/exploration.
- Authored object is distinguishable from extracted-only object when needed.
- Query/exploration can consume authored graph overlay as campaign memory.

### 18.5 Visibility

- New assertions default to GM private.
- User can mark assertion table-known/player-visible.
- Stored assertion includes visibility fields.

## 19. Non-goals for v0

- No LLM assist.
- No player-facing portal.
- No full graph visualization.
- No automatic identity-survivor selection.
- No direct source markdown mutation.
- No worldbuilding graph UI beyond linking to existing objects if available.
- No gold/eval analytics dashboard.
- No full help mode, though labels/copy should be clear.

## 20. Final design sentence

```text
Graph Object Authoring is a Tiptap-backed, prose-first workflow for turning ingested campaign text into durable authored campaign graph memory, with safe staged commits, visibility metadata, and gold/evaluation signal captured as an advanced byproduct.
```
