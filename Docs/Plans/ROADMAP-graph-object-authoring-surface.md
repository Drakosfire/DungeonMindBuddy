# Roadmap — Graph Object Authoring Surface

**Status:** Active Prime Design roadmap  
**Date:** 2026-07-05  
**Workstream:** Graph Memory / Memory Ingest / Graph Review / Graph Authoring  
**Design doc:** `Docs/Design/DESIGN-graph-object-authoring-surface.md`  
**Supersedes product direction in:** `Docs/Plans/ROADMAP-graph-review-gold-authoring-workbench.md` where that roadmap treats gold-fixture writes as the primary authoring destination.

---

## 1. Roadmap goal

Build a Tiptap-backed Graph Object Authoring workflow on the Memory/Graph Review surface.

The workflow lets a GM/developer:

1. ingest source material;
2. review projected graph objects over source prose;
3. select a word, phrase, existing graph pill, or relationship context;
4. declare graph objects, aliases, links, and relationships;
5. choose visibility/audience scope;
6. stage authored graph assertions locally;
7. prepare a safe write preview;
8. commit authored campaign graph memory;
9. append a robust authoring event log;
10. refresh graph exploration/query state;
11. optionally derive graph-gold/evaluation signal for ingestion tuning.

The product target is the authored campaign graph. Gold/eval is an advanced developer byproduct.

## 2. Current known state

Already available:

- `/ingest` exists as the Memory Ingest / Graph Review surface.
- The surface has a toolbox architecture.
- Ingest Recap exists as a first step.
- Live graph-ingest runs can be reviewed without gold.
- Projected prose can render graph pills through embedded `[label](dmb-node:id)` links.
- `GraphProjectionReader` renders projected markdown with read-only Tiptap.
- `GraphNodeReferenceNode` and `GraphNodeReferenceView` render existing graph nodes as selectable inline atoms.
- `markdownToTiptapDoc(markdown, { parseGraphNodeLinks: true })` imports graph-node links into Tiptap JSON.
- Existing Author Draft staging is partly implemented but conceptually points at graph-gold fixture authoring.
- Current prepare/commit services write candidate-graph-gold-shaped JSON and require gold as the write target.
- Tiptap runbook infrastructure proves local editor state, custom reference nodes, semantic markdown import/export, block boundary decoration, and two-phase markdown write preview/commit.

Important correction:

```text
Do not continue treating gold fixtures as the primary write target.
Use gold/eval as advanced tuning output derived from authored graph corrections.
```

## 3. Dependency map

```text
A0 Design + roadmap
  -> A1 Tiptap selection adapter
      -> A2 Local Graph Object Authoring Surface
          -> A3 Authored graph overlay contract + file store
              -> A4 Prepare/commit + event log
                  -> A5 Projection reload with authored overlay
                      -> A6 Existing-object/worldbuilding/recap linking
                          -> A7 Visibility-aware query/explore foundation
                              -> A8 Gold/eval export
                                  -> A9 Dogfood hardening
                                      -> A10 LLM assist and help-mode later
```

A1 and A2 should be done before any write path. A3/A4 should be narrow and boring. A5 is required before the user can feel that “the graph knows it.”

## 4. Implementation guardrails

- Ingestion is step one, not the entire surface.
- Source prose remains the visual focus.
- Tiptap is the selection/prose substrate, not the graph truth store.
- The authored campaign graph is the primary write target.
- Gold/eval artifacts are advanced developer output.
- Source markdown is not mutated in v0.
- Extracted live run artifacts are not mutated.
- Identity/linking choices are human decisions assisted by backend suggestions; the UI does not merge identity automatically.
- All writes use prepare/diff/confirm/commit.
- All commits append event log records.
- New assertions default to GM-private visibility.
- Player-facing views are out of scope but visibility fields are not optional.
- No LLM assist until manual authoring, write safety, projection refresh, and event logging are proven.

## 5. Milestones

## A0 — Design + roadmap docs

**Purpose:** Lock the corrected product target before implementation.

**Scope:**

- Add design doc for Graph Object Authoring Surface.
- Add this roadmap.
- Explicitly supersede the gold-fixture-as-primary-destination framing.
- Anchor in existing Tiptap and graph-review infrastructure.

**Acceptance:**

A coding agent can read the design + roadmap and understand:

- what to build;
- what not to build;
- where to put it;
- what existing infrastructure to reuse;
- how to slice implementation.

**Status:** Done by this docs PR.

---

## A1 — Tiptap-backed GraphAuthoringSelection adapter

**Purpose:** Make source selection first-class.

**Product behavior:**

The user can highlight a word/phrase in the projected recap and the system captures a structured selection object suitable for graph authoring.

**Scope:**

- Extend `GraphProjectionReader` with optional authoring selection props.
- Observe Tiptap selection changes when `authoringEnabled` is true.
- Capture selected text, Tiptap positions, surrounding context, and closest block/paragraph context.
- Detect selection of an existing `graphNodeReference` atom.
- Ignore blank/unsupported selections.
- Provide a minimal contextual action: “Author graph object.”
- Emit `GraphAuthoringSelection` to parent workbench.

**Likely files:**

```text
apps/live-control-ui/src/planSurface/graphProjectionReader/GraphProjectionReader.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphAuthoringSelection.ts
apps/live-control-ui/src/planSurface/graphReviewWorkbench/useGraphAuthoringSelection.ts
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLiveProjectionPanel.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLiveProjectionPanel.test.tsx
```

**Suggested contract:**

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

**Implementation notes:**

- Prefer Tiptap/ProseMirror selection state over raw DOM selection.
- Use redundant anchors; do not rely on Tiptap positions as durable provenance.
- Keep the editor visually read-only.
- Do not insert inline nodes or marks yet.
- Existing graph pill click behavior must continue working.

**Tests:**

- Selecting text emits `selectionKind = text_span` and selected text.
- Selecting whitespace emits null/no action.
- Selecting an existing graph pill emits or opens with `selectionKind = graph_node_reference` without breaking existing inspect behavior.
- Authoring disabled means no selection action appears.

**Acceptance:**

Manual: highlight “gang” in a projected recap and see an “Author graph object” affordance seeded with the selected text.

---

## A2 — Local Graph Object Authoring Surface

**Purpose:** Let selected prose become local staged graph intent without writes.

**Product behavior:**

The user selects text, opens the authoring surface, declares object identity/type/aliases/visibility, and stages a local authored graph proposal.

**Scope:**

- Add a Graph Object Authoring tool/panel on the Memory/Graph Review surface.
- Consume `GraphAuthoringSelection`.
- Show selected source phrase and context.
- Let user declare object label, kind/type, role, aliases, and summary.
- Let user set visibility with a simple dropdown.
- Let user stage object assertions locally.
- Show a staging tray.
- Keep all copy clear that nothing has been written.

**Likely files:**

```text
apps/live-control-ui/src/planSurface/config/ingestSurfaceConfig.ts
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringSurface.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringSelectedSource.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringObjectForm.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringVisibilitySection.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringStagingTray.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/useGraphObjectAuthoringDraft.ts
```

**Suggested proposal types:**

```ts
type GraphObjectAuthoringProposal =
  | AuthoredObjectProposal
  | AuthoredAliasProposal
  | AuthoredExistingLinkProposal
  | AuthoredRelationshipProposal
  | AuthoredVisibilityProposal;
```

**Minimum visibility options:**

```text
GM private
Table known / player visible
Character-specific
Hidden until revealed
```

**Tests:**

- Opening authoring from selected text seeds object label with selected text.
- User can edit label/kind/alias.
- User can stage an object proposal.
- Staging tray renders proposal and says no graph write has happened.
- Default visibility is GM private.

**Acceptance:**

Manual: select “gang,” open authoring, declare a party/group object or alias, set visibility, stage locally, and see a staged proposal with no write.

---

## A3 — Relationship authoring and link-existing workflow

**Purpose:** Support the real graph operation: objects become useful when linked.

**Product behavior:**

The user can choose one authored/existing object as a source, choose another object or selected phrase as a target, choose a relationship type, and stage a relationship. The user can also check whether the selected phrase/object already exists in campaign memory.

**Scope:**

- Rename user-facing resolver UI to “Find existing object.”
- Reuse existing resolver service where possible.
- Add relationship source/target state to the authoring draft hook.
- Rename user-facing `predicate` to `Relationship type`.
- Let user stage relationships locally.
- Let user stage alias/link-existing proposals.
- Keep identity semantics explicit: no merge, no link written until commit.

**Likely files:**

```text
apps/live-control-ui/src/planSurface/graphReviewWorkbench/ExistingObjectResolverPanel.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringRelationshipForm.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringSurface.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/useGraphObjectAuthoringDraft.ts
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/api/types.ts
```

**Tests:**

- User can set a relationship source.
- Selecting another object enables Stage relationship.
- Relationship type is visible; Predicate is not user-facing.
- Find existing object copy explains no link or merge is written.
- Stage link-existing proposal remains local.

**Acceptance:**

Manual: select “gang,” link or declare it as Questionable Company, then stage `has_member` relationships to PCs or known party nodes if available.

---

## A4 — Authored graph overlay contract and store

**Purpose:** Create the durable product write target.

**Product behavior:**

The system has a file-backed authored graph overlay that can receive committed human-authored graph assertions.

**Scope:**

- Define backend Pydantic contracts for authored graph assertions.
- Define file-backed store path convention.
- Define graph fingerprinting.
- Define backup behavior for replacing existing authored graph overlay.
- Define append-only event log writer.
- Do not wire UI commit yet unless this slice also includes A5.

**Likely files:**

```text
src/graph_memory/authoring/contracts.py
src/graph_memory/authoring/store.py
src/graph_memory/authoring/events.py
src/graph_memory/authoring/apply.py
apps/live_control_server/services/graph_object_authoring_prepare.py
apps/live_control_server/services/graph_object_authoring_commit.py
apps/live-control-ui/src/api/types.ts
```

**Recommended v0 storage layout:**

```text
corpus/eldyrwild-markdown/<Campaign>/_graph_authoring/
  authored_graphs/
    session-2.authored-graph.json
  events/
    session-2.authoring-events.jsonl
  exports/
    session-2.graph-gold-eval.json
```

**Required schemas:**

- `AuthoredGraphObjectAssertion`
- `AuthoredGraphRelationshipAssertion`
- `GraphAuthoringSourceAnchor`
- `GraphAuthoringProvenance`
- `GraphVisibilityPolicy`
- `GraphObjectAuthoringProposal`
- `GraphObjectAuthoringEvent`

**Tests:**

- Store creates new authored graph file when absent.
- Store loads existing authored graph file.
- Applying object proposal creates stable assertion.
- Applying relationship proposal creates stable assertion.
- Event writer appends JSONL records.
- Visibility is required and defaults to GM private.

**Acceptance:**

Unit tests prove a session with no prior gold or authored graph can create an authored graph overlay in memory and serialize it safely.

---

## A5 — Prepare/commit authored graph write

**Purpose:** Safely persist authored campaign graph changes.

**Product behavior:**

The user prepares a write, sees what authored graph memory will change, then explicitly commits. Commit writes authored graph overlay and event log. It does not mutate source markdown or extracted run artifacts.

**Scope:**

- Add prepare endpoint.
- Add commit endpoint.
- Compute confirm token from target path, proposed content, and current file-state token.
- Reject stale file conflicts.
- Backup existing authored graph file on commit.
- Append authoring events.
- Return clear diagnostics.
- Connect frontend prepare/commit panel.

**Suggested routes:**

```text
POST /api/live/graph-authoring/prepare
POST /api/live/graph-authoring/commit
```

**Likely files:**

```text
apps/live_control_server/routes/graph_preview.py
apps/live_control_server/services/graph_object_authoring_prepare.py
apps/live_control_server/services/graph_object_authoring_commit.py
src/graph_memory/authoring/store.py
src/graph_memory/authoring/events.py
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringPrepareCommitPanel.tsx
```

**Tests:**

- Prepare writes nothing.
- Prepare returns preview summary and confirm token.
- Commit with matching token writes authored graph and event log.
- Commit with stale token fails recoverably.
- Commit backs up existing authored graph file.
- Commit response says source markdown was not mutated.
- Commit response says extracted run artifact was not mutated.

**Acceptance:**

Manual: stage “gang” as a graph object/alias/relationship, prepare, review preview, commit, and see authored graph + event log paths in success response.

---

## A6 — Projection reload with authored overlay

**Purpose:** Make committed authored graph changes visible in the graph review/exploration experience.

**Product behavior:**

After commit and reload, the authored object appears in the graph projection/exploration. The user feels that the graph knows the authored fact.

**Scope:**

- Load authored graph overlay alongside extracted graph run.
- Merge authored assertions into projection payload.
- Render authored objects as pills using existing graph-node reference machinery.
- Label authored source clearly but unobtrusively.
- Allow authored object inspection and relationships.
- Preserve existing extracted object behavior.

**Likely files:**

```text
src/graph_memory/projection/recap_projection.py
apps/live_control_server/services/graph_gold_review.py
apps/live_control_server/routes/graph_preview.py
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLiveProjectionPanel.tsx
apps/live-control-ui/src/planSurface/graphProjectionReader/GraphProjectionReader.tsx
```

**Open implementation choice:**

v0 may either:

1. layer authored overlay into current projection without rerunning ingestion, or
2. show an authored overlay lane/panel until a full graph refresh is available.

Preferred:

```text
Layer authored overlay into current projection without requiring full re-ingest.
```

**Tests:**

- Projection service includes authored object after overlay load.
- Authored object renders as `graphNodeReference` / pill.
- Authored relationship appears in relationship context.
- Extracted-only objects continue rendering.

**Acceptance:**

Manual: after committing “gang” -> Questionable Company, reload and see the authored object/link in the graph review/exploration path.

---

## A7 — Worldbuilding / recap / GM-private linking

**Purpose:** Let authored graph objects connect to the wider campaign graph, not just the current recap.

**Product behavior:**

The user can link a selected phrase/object to objects from recap graph, worldbuilding graph, party/PC graph, and GM-private graph scopes.

**Scope:**

- Extend Find existing object search to multiple graph scopes.
- Return candidate source/scope labels.
- Add manual search fallback if candidate ranking is poor.
- Let user choose link-existing or create-new.
- Preserve no-merge semantics.
- Store relationship scope and visibility.

**Likely files:**

```text
src/graph_memory/identity/
src/graph_memory/authoring/
src/graph_memory/union_supergraph/
apps/live_control_server/services/
apps/live-control-ui/src/planSurface/graphReviewWorkbench/ExistingObjectResolverPanel.tsx
```

**Tests:**

- Same-session recap candidates are returned.
- Campaign/worldbuilding candidates are returned when available.
- Candidate includes graph scope/source label.
- Link-existing proposal records chosen candidate.
- UI does not imply identity merge.

**Acceptance:**

Manual: select a phrase and link it to an existing PC, party, location, faction, or worldbuilding object.

---

## A8 — Visibility-aware graph query/explore foundation

**Status:** foundation landed (2026-07-07). See `Docs/Plans/NOTE-a8-visibility-audience-filtering.md`.

**Purpose:** Prepare the authored graph for future GM/player views.

**Product behavior:**

Authored assertions carry visibility metadata. GM views can see all; future player views can filter safely.

**Scope:**

- Visibility on all authored graph assertions (already present from A3–A7).
- Default to GM private (already present).
- Simple UI control (already present in authoring surface).
- **Backend audience filter helper** (`graph_authoring_visibility.py`) — **new in A8**.
- Tests proving player/table/character audiences exclude GM-private assertions — **new in A8**.
- Optional audience parameter on projection enrichment (GM-default when omitted).
- Do not build player UI yet.

**Likely files:**

```text
apps/live_control_server/services/graph_authoring_visibility.py
apps/live_control_server/services/graph_authoring_overlay_projection.py
tests/test_graph_authoring_visibility.py
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringVisibilitySection.tsx
```

**Tests:**

- Missing visibility defaults to GM private at proposal creation.
- Stored assertions include visibility.
- Filtering helper excludes GM-private for player/table/character audiences.
- GM audience sees all assertions.
- Overlay filter does not mutate the source overlay.
- Projection with `audience=table` excludes GM-private authored nodes.

**Acceptance:**

Manual: stage two authored assertions, one GM private and one table known; stored JSON includes correct visibility. Future non-GM query surfaces can call the audience helpers without leaking GM-private authored memory.

**Not claimed:** A7 dogfood was not a clean pass. A8 solves one narrow trust boundary only.

---

## A9 — Gold/eval export from authored corrections

**Status:** A9a backend export foundation planned/landed. UI opt-in and candidate-graph-gold conversion deferred.

**Purpose:** Convert human-authored graph corrections into developer tuning/evaluation artifacts.

**Product behavior:**

Advanced users can include authored graph corrections in graph-gold/evaluation output. This is not the primary write success state.

**Scope:**

- Add `include_in_gold_eval` to proposals/assertions.
- Add optional export under `_graph_authoring/exports/` or existing eval path.
- Define `knowledge_scope` for retrospective/cross-session assertions.
- Export enough data to compare future extraction runs against human-authored graph truth.
- Do not block authored graph commit if gold/eval export fails unless explicitly configured.

**Likely files:**

```text
src/graph_memory/authoring/contracts.py
src/graph_memory/authoring/gold_export.py
apps/live_control_server/services/graph_object_authoring_commit.py
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringPrepareCommitPanel.tsx
```

**Knowledge scope:**

```text
session_local
campaign_retrospective
cross_session_context_required
```

**Tests:**

- Export includes authored object and relationship assertions.
- Export records source anchors.
- Export records knowledge scope.
- Export excludes assertions with `include_in_gold_eval = false`.

**Acceptance:**

Manual: author “gang” as retrospective party alias, commit, and see advanced gold/eval export record with `knowledge_scope = campaign_retrospective`.

---

## A10 — Dogfood hardening

**Purpose:** Validate the full graph-authoring loop on real campaign material.

**Dogfood target:**

C1S2 or another session with ingested graph material and obvious missed/underlinked objects.

**Checklist:**

```text
1. Ingest recap.
2. Load graph review surface.
3. Select raw text missed by extraction.
4. Author object.
5. Link to existing PC/party/worldbuilding object.
6. Stage relationship.
7. Set visibility.
8. Prepare write.
9. Commit authored graph.
10. Confirm event log.
11. Reload projection.
12. Query/explore authored object.
13. Confirm no source markdown mutation.
14. Confirm no extracted run artifact mutation.
15. Confirm gold/eval export if enabled.
```

**Acceptance:**

The dogfood report identifies interaction friction but proves the product loop end-to-end.

**Status (2026-07-07):** A10a dogfood report landed (`Docs/Reports/DOGFOOD-graph-object-authoring-a10-user-stories.md`). A10b addressed authored alias prose grounding after reload (`Docs/Plans/NOTE-a10b-authored-alias-prose-grounding.md`). A10c hardens selected-node detail hierarchy so summaries, aliases, and relationships appear before overlay/debug metadata (`Docs/Plans/NOTE-a10c-node-detail-hierarchy.md`). A10d clarifies authoring form choices by splitting table-known/player-visible visibility and adding relationship predicate coaching (`Docs/Plans/NOTE-a10d-authoring-form-clarity.md`). A10e streamlines the authoring surface by demoting selected-source and write metadata into collapsed details and bringing staged-memory prepare/commit controls closer to the GM workflow (`Docs/Plans/NOTE-a10e-authoring-layout-quiet-source.md`). A10i–A10k landed manual merge staging, post-overlay alias propagation, and the Existing Object identity workbench (PRs #293–#295). A10l polishes that workbench for the Lysandra dogfood path and hardens projection-time merge hydration when survivor/duplicate ids diverge from the live projection.

---

## A10m — Overlay merge → union supergraph reconciliation

**Status (2026-07-08):** **Design complete** — see `Docs/Plans/HANDOFF-a10m-union-supergraph-merge-reconciliation.md`. Implementation queued as PR A–E sequence below. A10l + PR #296 landed overlay polish and GM survivor-id preservation at staging time.

**Purpose:** Move human-reviewed identity merges from projection-only overlay collapse into durable union-supergraph identity, so session projections become lenses over reconciled global nodes instead of accumulating parallel ids (`party:captain_lysandra_ironveil` vs `character_lysandra` vs `node:lysandra`).

**Problem today:** A10i–A10l commit `merge_objects` assertions to the authored overlay; `graph_authoring_overlay_projection.py` collapses views at reload. That preserves review safety and avoids re-ingest, but does **not** rewrite the union read model — ID drift persists at the source and projection must fuzzy-match/hydrate at runtime.

**Resolved product decisions:**

| Decision | Rule |
|---|---|
| Survivor authority | GM-chosen survivor ref always wins |
| Commit boundary | Overlay commit unchanged; no union mutation in commit |
| Reconciliation | Separate explicit pass/job after commit (endpoint/CLI first) |
| Scope | `merge_objects` only — not `link_existing` |
| Undo | Retract hook designed; implementation deferred |

**Target behavior:**

```text
Stage/compare (overlay, reversible)
  → prepare/commit (durable assertion + event log, unchanged)
    → reconciliation pass materializes union identity redirects + edge/evidence rewiring
      → projection reads reconciled union + thin overlay for unmaterialized assertions
```

**Implementation PR sequence (from design handoff):**

1. **PR A** — Union identity redirect model + lookup tests
2. **PR B** — Reconciliation planner (read overlay, build plan, no writes)
3. **PR C** — Reconciliation apply (union store mutation + endpoint/CLI)
4. **PR D** — Projection adapter simplification (redirect-first, shrink fuzzy repair)
5. **PR E** — Session 23 Lysandra dogfood validation report

**Key design artifacts:**

- `UnionIdentityRedirect` — durable `from_node_id → to_node_id` (not recap text alias)
- `UnionSupergraphMergeRecord` — audit/retract replay snapshot
- Merged-away nodes: `memory_state: merged_away`, filtered from normal projection
- Edge rewire with provenance (`rewired_from_node_ids`, dedupe equivalent edges)

**Cross-track dependency:** Primary owner is graph-memory (`src/graph_memory/union_supergraph/`). Projection adapter changes in PR D touch `apps/live_control_server/services/`. Align with `Docs/Design/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md` projection contracts (PR D/E) but do not block A10m on full runtime adapter migration.

**Acceptance:**

Manual: commit Lysandra merge, run reconciliation pass, reload Session 23, click survivor — selected-object card shows full global projection (evidence, adjacency, summary) without projection-time fuzzy id repair. Re-ingest does not resurrect merged-away ids as separate normal nodes.

---

## A11 — Later: LLM assist and help mode

**Purpose:** Add acceleration only after manual authoring is stable.

**Scope later:**

- Per-selection LLM proposal assist.
- Whole-document graph reflow from human anchors.
- Help mode: hover/focus a tool and see concise, precise explanation.
- Candidate ranking improvements.
- Graph authoring lessons dashboard.

**Non-goal before A10:**

No LLM assist before manual authoring, write safety, projection reload, event logging, and visibility fields are stable.

## 6. Suggested first coding PR

**Branch:** `codex/graph-authoring-selection-adapter`  
**Title:** `feat(graph-authoring): capture Tiptap source selections for graph authoring`

**Scope:** A1 only.

**Files likely touched:**

```text
apps/live-control-ui/src/planSurface/graphProjectionReader/GraphProjectionReader.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphAuthoringSelection.ts
apps/live-control-ui/src/planSurface/graphReviewWorkbench/useGraphAuthoringSelection.ts
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLiveProjectionPanel.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLiveProjectionPanel.test.tsx
```

**Deliverable:**

- Text selection in Tiptap projection emits structured selection.
- Existing graph-node reference selection/click continues working.
- Contextual “Author graph object” action can be shown.
- No persistence.
- No backend.
- No graph mutation.

**Acceptance:**

A user can highlight `gang` and the UI can display a structured authoring selection containing selected text and context.

## 7. Suggested second coding PR

**Branch:** `codex/graph-object-authoring-local-draft`  
**Title:** `feat(graph-authoring): stage local graph object proposals from selected prose`

**Scope:** A2, part of A3 if small.

**Deliverable:**

- Graph Object Authoring tool/panel.
- Object form.
- Visibility section.
- Staging tray.
- No backend write.

**Acceptance:**

Select `gang`, declare object/alias/visibility, and stage proposal locally.

## 8. Suggested third coding PR

**Branch:** `codex/authored-graph-overlay-contract`  
**Title:** `feat(graph-authoring): add authored graph overlay contracts and store`

**Scope:** A4 only.

**Deliverable:**

- Pydantic contracts.
- Store load/save helpers.
- Event log writer.
- Unit tests.
- No UI commit yet unless tiny.

**Acceptance:**

Backend unit tests serialize/load authored graph overlay and append event logs.

## 9. Suggested fourth coding PR

**Branch:** `codex/graph-authoring-prepare-commit`  
**Title:** `feat(graph-authoring): prepare and commit authored campaign graph changes`

**Scope:** A5.

**Deliverable:**

- Prepare endpoint.
- Commit endpoint.
- Confirm token.
- Stale rejection.
- Backup.
- Event log append.
- Frontend prepare/commit panel.

**Acceptance:**

Manual staged proposal can be committed to authored graph overlay and event log.

## 10. Suggested fifth coding PR

**Branch:** `codex/graph-authoring-projection-overlay`  
**Title:** `feat(graph-authoring): render authored graph overlay in review projections`

**Scope:** A6.

**Deliverable:**

- Projection service loads authored graph overlay.
- Authored objects render as pills.
- Reload after commit shows authored objects.

**Acceptance:**

Committed object appears in graph review/exploration without mutating source markdown.

## 11. Verification matrix

| Capability | Verification |
|---|---|
| Tiptap text selection | Highlight a phrase in projected recap; structured selection appears. |
| Existing graph pill selection | Existing `graphNodeReference` remains clickable/selectable. |
| Local object staging | Selected text can become staged object/alias proposal. |
| Relationship staging | Source and target can be selected; relationship type can be staged. |
| Find existing object | Existing graph/worldbuilding candidates can be reviewed without automatic merge. |
| Visibility | Every staged assertion has visibility, default GM private. |
| Prepare write | Preview shows target authored graph and event log paths; writes nothing. |
| Commit write | Writes authored graph overlay and appends event log. |
| Stale safety | Commit with stale token fails recoverably. |
| Projection reload | Authored object appears after commit/reload. |
| Gold/eval byproduct | Advanced export can include authored corrections for tuning. |
| Source safety | Source markdown is not mutated by graph authoring. |
| Run safety | Extracted live run artifact is not mutated. |

## 12. Risks

### 12.1 Source selection anchoring drift

Tiptap positions may change if markdown import/export changes. Store redundant anchors: selected text, surrounding context, paragraph/source span ref, hashes, and optional positions.

### 12.2 Gold/eval confusion

If UI says “gold” too early, the product will regress into developer-only fixture editing. Keep gold/eval behind advanced/developer copy.

### 12.3 Authoring islands

If linking to existing graph/worldbuilding objects is weak, manual authoring creates duplicates. A3/A7 must remain high priority.

### 12.4 Visibility debt

If visibility is deferred, future player access becomes dangerous. Add visibility fields in v0 even if player UI is later.

### 12.5 Premature markdown mutation

Writing `[label](dmb-node:id)` back into source markdown may look attractive, but it confuses source artifact and authored graph memory. Do not do this in v0.

### 12.6 Premature LLM assist

LLM assist before manual authoring is stable will hide product and schema flaws. Defer.

## 13. Done definition

This roadmap is complete when:

1. A session can be ingested.
2. The projected recap can be reviewed in Tiptap.
3. A raw phrase can be selected as source.
4. The phrase can be authored as a campaign graph object or alias.
5. The object can be linked to existing recap/worldbuilding/party graph objects.
6. Relationships can be staged and committed.
7. Authored assertions include visibility and provenance.
8. Commit writes authored campaign graph overlay and event log.
9. Reload/query/explore sees the authored graph change.
10. Advanced gold/eval export records the correction for tuning.
11. Source markdown and extracted run artifacts remain unchanged by graph authoring.
