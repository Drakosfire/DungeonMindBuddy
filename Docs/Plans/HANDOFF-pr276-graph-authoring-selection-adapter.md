# HANDOFF pr276 — Graph Authoring A1 selection adapter

**Status:** ready for agent dispatch  
**Repo:** `Drakosfire/DungeonMindBuddy`  
**Target implementation branch:** `codex/graph-authoring-selection-adapter`  
**Planned PR:** #276  
**Workstream:** Graph Memory / Memory Ingest / Graph Object Authoring  
**Milestone:** A1 from `Docs/Plans/ROADMAP-graph-object-authoring-surface.md`  
**Mode:** small frontend-first coding PR; no backend writes; no graph/corpus mutation

---

## §0 Copyable pickup prompt

```markdown
You are implementing the first Graph Object Authoring coding slice for DungeonMindBuddy.

Read first, in this order:

1. `Docs/Plans/HANDOFF-pr276-graph-authoring-selection-adapter.md`
2. `Docs/Design/DESIGN-graph-object-authoring-surface.md`
3. `Docs/Plans/ROADMAP-graph-object-authoring-surface.md`
4. `Docs/Plans/HANDOFF-prime-design-graph-review-workbench-authoring-next.md`
5. `apps/live-control-ui/src/planSurface/graphProjectionReader/GraphProjectionReader.tsx`
6. `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLiveProjectionPanel.tsx`
7. `apps/live-control-ui/src/tiptap/extensions/GraphNodeReferenceNode.ts`
8. `apps/live-control-ui/src/tiptap/extensions/GraphNodeReferenceView.tsx`
9. `apps/live-control-ui/src/tiptap/markdown/markdownToTiptap.ts`

Mission: implement A1 only — a Tiptap-backed `GraphAuthoringSelection` adapter that lets the Memory Ingest / Graph Review surface capture structured source selections from projected recap prose.

The user should be able to highlight a word such as `gang` in the projected recap and see a small contextual `Author graph object` affordance seeded with a structured selection.

Do not persist anything. Do not add backend endpoints. Do not mutate source markdown. Do not write graph files. Do not continue building the gold-fixture authoring path.
```

---

## §1 Mission

Build the first usable selection seam for Graph Object Authoring.

A user reviewing an ingested recap on `/ingest` should be able to select source prose inside the projected recap and produce a structured `GraphAuthoringSelection` object that can be handed to the next PR's local Graph Object Authoring surface.

This PR is intentionally narrow. It proves the selection substrate and contextual action, not the authoring form, not persistence, and not the authored graph store.

The product promise for this slice:

```text
I can highlight source text in the ingested recap and DungeonBuddy knows what text, block context, graph lane, session, and graph projection I selected.
```

---

## §2 Current state you are building on

`/ingest` is now a focused Memory Ingest / Graph Review surface. It has a toolbox with `Ingest Recap`, `Diagnostics`, and `Author Draft`, and it can review a live graph-ingest run even when no gold fixture exists.

The current visual review lane in `GraphReviewLiveProjectionPanel.tsx` still renders through `GraphReviewProjectionLane`, which parses literal `[label](dmb-node:id)` links and turns them into clickable pills. That renderer also has a raw DOM text-selection callback today (`window.getSelection()`), but it does not produce durable source anchors, Tiptap positions, block context, or graph-node-reference selections.

A separate Tiptap projection reader already exists at `GraphProjectionReader.tsx`. It imports `EditorContent`, `useEditor`, `StarterKit`, `GraphNodeReferenceNode`, and `markdownToTiptapDoc(markdown, { parseGraphNodeLinks: true })`. That is the correct substrate for this slice because Graph Object Authoring should consume Tiptap/ProseMirror selection state rather than raw DOM selections.

The Prime Design correction is settled: the durable authoring target is authored campaign graph memory, not a gold fixture and not direct source markdown mutation. A1 should not deepen the old gold-fixture-shaped authoring workflow.

---

## §3 Design decisions for this PR

### 3.1 Tiptap is the source-selection substrate

Create a typed selection contract and capture it from Tiptap/ProseMirror state. Do not extend the existing `window.getSelection()` path as the durable authoring mechanism.

Suggested file:

```text
apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphAuthoringSelection.ts
```

Suggested contract:

```ts
export type GraphAuthoringSelectionKind =
  | "text_span"
  | "graph_node_reference"
  | "block"
  | "relationship";

export type GraphAuthoringLaneRole = "gold" | "live" | "authored";

export interface GraphAuthoringSelection {
  campaignId: string;
  sessionId: string;
  sourceArtifactPath?: string | null;
  sourceArtifactSha256?: string | null;

  selectionKind: GraphAuthoringSelectionKind;
  selectedText: string;
  normalizedSelectedText: string;
  surroundingTextBefore?: string | null;
  surroundingTextAfter?: string | null;
  paragraphOrdinal?: number | null;
  sourceSpanRefId?: string | null;

  tiptapFrom?: number | null;
  tiptapTo?: number | null;

  existingNodeId?: string | null;
  existingLabel?: string | null;

  graphId?: string | null;
  laneRole?: GraphAuthoringLaneRole | null;
}
```

This shape is deliberately frontend-friendly and should remain compatible with the richer assertion/source-anchor model in the design doc.

### 3.2 Add optional authoring props to `GraphProjectionReader`

Extend `GraphProjectionReaderProps` without making every reader authoring-aware:

```ts
export type GraphAuthoringAction = "author_object";

interface GraphProjectionReaderProps {
  // existing props...
  authoringEnabled?: boolean;
  authoringContext?: {
    campaignId: string;
    sessionId: string;
    graphId?: string | null;
    laneRole?: "gold" | "live" | "authored" | null;
    sourceArtifactPath?: string | null;
    sourceArtifactSha256?: string | null;
  };
  onGraphAuthoringSelection?: (selection: GraphAuthoringSelection | null) => void;
  onGraphAuthoringAction?: (
    selection: GraphAuthoringSelection,
    action: GraphAuthoringAction,
  ) => void;
}
```

Keep all props optional. Existing projection readers should behave exactly as they do today when `authoringEnabled` is false or absent.

### 3.3 Capture selection from ProseMirror state

Use `editor.state.selection`, not `window.getSelection()`, for the selection object.

At minimum:

- ignore blank or whitespace-only selections;
- bound raw text selection length, e.g. 200 chars for the contextual action;
- store `tiptapFrom` / `tiptapTo` as transient anchors;
- store `selectedText` and `normalizedSelectedText`;
- store short `surroundingTextBefore` and `surroundingTextAfter`, bounded to something like 80 chars each;
- compute a best-effort `paragraphOrdinal` by walking document blocks;
- detect graph-node-reference atoms where practical;
- emit `null` when selection is cleared or unsupported.

Do not pretend Tiptap positions are durable enough for backend writes. They are transient UI anchors. The durable write path comes later and must include redundant text/context/source anchors.

### 3.4 Add a tiny contextual action, not the whole authoring surface

When `authoringEnabled` is true and a valid selection exists, show a small contextual affordance near the reader or selection area:

```text
Author graph object
```

Clicking it should call `onGraphAuthoringAction(selection, "author_object")`.

For A1, the visible result can be a lightweight selected-source preview or status panel in the Graph Review workbench that prints the structured selection fields. That preview is a test/debug bridge for A2, not the final authoring UI.

Acceptable copy:

```text
Selected source ready for graph authoring. No graph write has happened.
```

### 3.5 Wire into `/ingest` without rewriting the whole lane system

Preferred narrow wiring:

1. Extend `GraphProjectionReader` with authoring selection support.
2. Use it inside the Graph Review workbench for the live ingested recap path when graph authoring is enabled.
3. Preserve existing graph pill inspection behavior.
4. Preserve current gold/live review behavior unless you can prove a no-regression swap.

Implementation latitude:

- If replacing `GraphReviewProjectionLane` broadly is too risky, do not do it.
- It is acceptable to introduce a small `GraphReviewAuthoringReader` wrapper that uses `GraphProjectionReader` only for the authoring-enabled live/ingested recap lane.
- It is acceptable for the first dogfood target to be the single-lane ingested recap case, because C1S2 is the motivating live-run/no-gold workflow.
- Do not leave the selection adapter unmounted and unexercised; A1 must be visible enough on `/ingest` to manually highlight text and trigger the action.

### 3.6 Existing graph chips must still inspect normally

Existing `[label](dmb-node:id)` pills imported as `GraphNodeReferenceNode` must remain selectable/clickable for inspection. Do not let text-selection authoring swallow chip clicks or remove the graph explorer/projected-object flow.

If a graph-node-reference atom is selected and the adapter can detect it, emit:

```ts
selectionKind: "graph_node_reference"
existingNodeId: <node id>
existingLabel: <label>
selectedText: <label>
```

If atom-selection detection proves too brittle for A1, keep chip-click inspection intact and document the limitation in the PR body. Text-span selection is the required acceptance path.

---

## §4 Allowlist

Only touch files needed for A1.

| Path | Action |
|------|--------|
| `apps/live-control-ui/src/planSurface/graphProjectionReader/GraphProjectionReader.tsx` | extend optional authoring-selection props and Tiptap selection capture |
| `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphAuthoringSelection.ts` | create typed selection/action contract |
| `apps/live-control-ui/src/planSurface/graphReviewWorkbench/useGraphAuthoringSelection.ts` | optional helper hook if useful |
| `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLiveProjectionPanel.tsx` | wire selection/action into `/ingest` review path |
| `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLiveProjectionPanel.test.tsx` | focused integration coverage |
| `apps/live-control-ui/src/planSurface/graphProjectionReader/GraphProjectionReader.test.tsx` | create or update focused reader tests |
| `apps/live-control-ui/src/planSurface/planSurface.css` | minimal contextual action/status styling only |
| `apps/live-control-ui/src/api/types.ts` | only if a local frontend type import forces it; prefer local type file |

Do not touch backend files in this PR.

Do not touch corpus files.

Do not touch `graph_gold_authoring_prepare.py` / `graph_gold_authoring_commit.py`.

Do not modify eval fixtures or gold fixture JSON.

---

## §5 Required behavior

### 5.1 Text selection

When authoring is enabled and a user highlights a non-blank source phrase in the Tiptap projection:

- a `GraphAuthoringSelection` is emitted;
- `selectionKind` is `text_span`;
- `selectedText` matches the selected prose;
- `normalizedSelectedText` is whitespace-normalized;
- `campaignId` and `sessionId` are populated from workbench context;
- `graphId` and `laneRole` are populated when available;
- Tiptap positions are included as transient UI anchors;
- context before/after and paragraph ordinal are best-effort and bounded.

### 5.2 Blank selection

Whitespace-only, collapsed, or unsupported selection clears/does not emit an authoring selection.

### 5.3 Contextual action

A visible `Author graph object` action appears only for a valid authoring selection and only when authoring is enabled.

Clicking it calls the provided callback with the current selection.

### 5.4 Local-only preview

The workbench may show a local selected-source preview so the user can see what was captured.

It must clearly say no graph write has happened.

### 5.5 Existing graph-node behavior

Existing graph chips must remain inspectable. A text-selection feature that breaks pill inspection is a failed PR even if text selection works.

---

## §6 Non-goals and guardrails

This PR must not:

- add backend endpoints;
- add prepare/commit;
- write authored graph overlays;
- write event logs;
- write gold/eval exports;
- mutate source recap markdown;
- insert `[label](dmb-node:id)` links into corpus files;
- mutate extracted live run artifacts;
- mutate candidate graph gold fixtures;
- add LLM assistance;
- add identity merge behavior;
- build a generic graph editor;
- rename the whole Author Draft workflow.

Keep wording future-proof: prefer `Graph Object Authoring`, `Author graph object`, `selected source`, and `staged locally`. Avoid expanding user-facing `Gold Authoring` language.

---

## §7 Verification

Run focused frontend checks from `apps/live-control-ui`.

```bash
npm test -- GraphProjectionReader GraphReviewLiveProjectionPanel
npm run typecheck
npm run build
```

If test filtering by file name is unreliable in this repo, run:

```bash
npm test
npm run typecheck
npm run build
```

The PR body must report the exact commands run and any failures.

Expected test coverage:

- `GraphProjectionReader` with `authoringEnabled={false}` emits no selection/action UI.
- `GraphProjectionReader` with `authoringEnabled={true}` emits `text_span` selection from Tiptap state.
- Whitespace/collapsed selection emits null or no action.
- `Author graph object` calls `onGraphAuthoringAction` with the current selection.
- Existing `dmb-node` graph reference still renders and remains inspectable/clickable.
- `/ingest` live review path can display selected-source capture without requiring gold.

---

## §8 Manual dogfood checklist

Use any preview-ready graph run, ideally C1S2 because it is the motivating live-run/no-gold case.

1. Open `/ingest`.
2. Load a session with an ingested recap projection.
3. Confirm graph pills still render.
4. Click an existing graph pill and confirm inspection still opens.
5. Highlight the word `gang` or another short source phrase in the projected recap.
6. Confirm `Author graph object` appears.
7. Click `Author graph object`.
8. Confirm the UI shows a selected-source preview or equivalent debug bridge with:
   - selected text;
   - campaign/session;
   - lane role;
   - graph id when available;
   - no-write copy.
9. Clear the selection and confirm the action disappears or disables.
10. Confirm no files changed outside the frontend implementation diff.

---

## §9 Rubric

### Testing

Focused unit/integration tests cover the selection adapter, disabled state, action callback, and no-regression graph chip behavior. Build/typecheck pass.

### Security

No backend writes. No corpus writes. No source markdown mutation. No LLM calls. No external data leaves the browser beyond existing graph review API calls.

### Simplicity

A1 only. Do not build the local object form, relationship staging, authored graph store, prepare/commit, event log, or gold export.

### Composability

The selection contract is a reusable typed seam. `GraphProjectionReader` remains usable by non-authoring consumers with all new behavior opt-in.

---

## §10 Review risks to watch

1. **Raw DOM selection sneaks back in as the core seam.** A1 is specifically about Tiptap/ProseMirror selection state.
2. **Reader replacement breaks graph chip inspection.** This is a reject; existing graph object inspection must survive.
3. **The PR accidentally deepens gold-fixture authoring.** Do not modify gold prepare/commit services.
4. **The UI implies a save happened.** The action is local capture only. Copy must say no graph write has happened.
5. **The selection object overclaims durability.** Tiptap positions are transient. Store redundant text/context, and leave durable backend anchoring for later.
6. **The slice tries to do A2.** Object forms, aliases, visibility dropdowns, and staging trays belong to the next PR unless a tiny debug preview needs a label.

---

## §11 Follow-on PRs this enables

After A1 lands:

- A2 can consume `GraphAuthoringSelection` to stage local object/alias/visibility proposals.
- A3 can add relationship/link-existing local proposals.
- A4 can define authored graph overlay contracts and file store.
- A5 can add prepare/commit/event-log writes.
- A6 can reload projection with authored overlay applied.

Do not start any of those in PR #276.

---

## §12 Reference index

Primary design/roadmap:

- `Docs/Design/DESIGN-graph-object-authoring-surface.md`
- `Docs/Plans/ROADMAP-graph-object-authoring-surface.md`

Prior handoff/state:

- `Docs/Plans/HANDOFF-prime-design-graph-review-workbench-authoring-next.md`
- `Docs/Plans/AUDIT-ingest-surface-page-inventory.md`
- `Docs/Plans/DOGFOOD-graph-review-authoring-loop-session-1.md`

Frontend implementation anchors:

- `apps/live-control-ui/src/planSurface/graphProjectionReader/GraphProjectionReader.tsx`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLiveProjectionPanel.tsx`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewProjectionLane.tsx`
- `apps/live-control-ui/src/tiptap/extensions/GraphNodeReferenceNode.ts`
- `apps/live-control-ui/src/tiptap/extensions/GraphNodeReferenceView.tsx`
- `apps/live-control-ui/src/tiptap/markdown/markdownToTiptap.ts`

Backend/write paths to avoid in this PR:

- `apps/live_control_server/services/graph_gold_authoring_prepare.py`
- `apps/live_control_server/services/graph_gold_authoring_commit.py`
- `src/agent/corpus_writer.py`

