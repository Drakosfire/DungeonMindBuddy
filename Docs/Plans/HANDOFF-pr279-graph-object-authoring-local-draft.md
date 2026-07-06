# HANDOFF pr279 — Graph Object Authoring A2 local draft surface

**Status:** ready for agent dispatch after PR #277 lands  
**Repo:** `Drakosfire/DungeonMindBuddy`  
**Expected implementation PR:** #279 if no parallel PR claims the number first  
**Target implementation branch:** `codex/graph-object-authoring-local-draft`  
**Dependency:** PR #277, `Graph Authoring A1: Tiptap selection adapter`  
**Workstream:** Graph Memory / Memory Ingest / Graph Object Authoring  
**Milestone:** A2 from `Docs/Plans/ROADMAP-graph-object-authoring-surface.md`  
**Mode:** frontend-only local authoring draft; no backend writes; no graph/corpus mutation

> If PR numbering shifts, keep the branch/title intent and rename/archive this handoff during post-merge doc sync. The implementation dependency is PR #277, not the literal PR number.

---

## §0 Copyable pickup prompt

```markdown
You are implementing Graph Object Authoring A2 for DungeonMindBuddy.

Read first, in this order:

1. `Docs/Plans/HANDOFF-pr279-graph-object-authoring-local-draft.md`
2. `Docs/Design/DESIGN-graph-object-authoring-surface.md`
3. `Docs/Plans/ROADMAP-graph-object-authoring-surface.md`
4. PR #277 / branch `codex/graph-authoring-selection-adapter`
5. `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphAuthoringSelection.ts`
6. `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewAuthoringReader.tsx`
7. `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLiveProjectionPanel.tsx`
8. `apps/live-control-ui/src/planSurface/config/ingestSurfaceConfig.ts`
9. `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewProjectedInteractionSurface.tsx`

Mission: implement A2 only — a local Graph Object Authoring draft surface that consumes `GraphAuthoringSelection`, lets the user declare object identity/type/aliases/visibility, and stages object proposals locally with clear no-write copy.

Do not add backend endpoints. Do not persist authored graph overlays. Do not mutate source markdown. Do not write candidate graph gold. Do not implement relationship authoring or link-existing writes.
```

---

## §1 Mission

Build the first real Graph Object Authoring draft surface.

After PR #277, the user can highlight source text in the ingested recap and capture a structured `GraphAuthoringSelection`. A2 should turn that selected source into a local, inspectable authored-object proposal.

The product promise for this slice:

```text
I can select source text, choose Author graph object, fill out a small object form, choose visibility, and stage a local graph object proposal. DungeonBuddy clearly shows that nothing has been written yet.
```

This PR is still local-only. It proves the authoring interaction and local proposal model before any prepare/commit/event-log storage exists.

---

## §2 Dependency and branch guidance

PR #277 is currently the prerequisite. It adds:

- `GraphAuthoringSelection`
- `GraphAuthoringContext`
- `GraphAuthoringAction`
- `buildGraphAuthoringSelectionFromEditor`
- `useGraphAuthoringSelection`
- `GraphReviewAuthoringReader`
- opt-in authoring props on `GraphProjectionReader`
- local selected-source preview wiring on `/ingest`

If PR #277 is merged before work starts, branch from `main`.

If PR #277 is still open, branch from `codex/graph-authoring-selection-adapter` and target the implementation PR onto that branch or wait for #277 to merge before opening. Do not reimplement the A1 selection seam.

---

## §3 Current state you are building on

A1 intentionally left a clunky debug bridge:

```text
toggle authoring mode → highlight text → Author graph object → preview panel
```

That is acceptable for A1, but A2 should not inherit it as the product surface.

A2 should replace the debug preview with a small authoring surface that feels like an actual tool:

1. selected source card;
2. object draft form;
3. visibility section;
4. local staging tray;
5. no-write status copy.

This should still be lightweight. The goal is not a polished final UX, but the interaction should be coherent enough that A3/A4 can build on it instead of working around a debug panel.

---

## §4 Product behavior

### 4.1 Entry

When the user has a valid `GraphAuthoringSelection` and clicks `Author graph object`, open or focus the Graph Object Authoring surface.

The selected source should remain visible in the authoring surface even if the browser selection later clears.

### 4.2 Selected source card

Show the captured selection as evidence/context:

- selected text;
- selection kind;
- campaign/session;
- lane role;
- graph id when available;
- source artifact path when available;
- surrounding text before/after when available;
- paragraph ordinal when available.

Copy must be user-facing, not developer dump copy.

Suggested copy:

```text
Selected source
This is the recap text this draft is grounded in. Nothing has been written yet.
```

### 4.3 Object draft form

The form should let the user declare a new authored graph object proposal.

Minimum fields:

- label;
- kind/type;
- role;
- aliases;
- summary;
- operator note, optional.

Defaults:

- `label` seeds from `selection.selectedText`;
- `aliases` may seed with selected text if the user changes label;
- `kind/type` defaults to empty or `unknown`, but should offer quick choices;
- `visibility` defaults to GM private;
- `include_in_gold_eval` defaults false or hidden for this PR.

Suggested quick kind options:

```text
party
npc
location
faction
object
thread
threat
event
concept
unknown
```

Do not overfit these options into backend semantics. They are frontend local proposal labels for now.

### 4.4 Visibility

Visibility must exist now, even in local-only form.

Minimum options:

```text
GM private
Table known / player visible
Character-specific
Hidden until revealed
```

Map them to stable internal values:

```ts
type GraphObjectAuthoringVisibility =
  | "gm_private"
  | "table_known"
  | "player_visible"
  | "character_specific"
  | "hidden_until_revealed";
```

Default:

```text
GM private / unrevealed
```

It is acceptable to omit player/character pickers in this PR. If `character_specific` is selected, show a small note that targeting specific characters will be implemented later.

### 4.5 Local staging

The user can click `Stage object draft` and add a local proposal to a staging tray.

The staged proposal should include:

- stable local draft id;
- source selection snapshot;
- object draft fields;
- visibility;
- graph scope defaults;
- provenance preview;
- status: `staged_local`.

The staging tray should show one or more local proposals and say clearly:

```text
Staged locally. No graph write has happened.
```

The user should be able to remove a staged proposal.

Editing staged proposals can be deferred if the implementation stays intentionally narrow; removing and restaging is enough for A2.

---

## §5 Suggested local types

Add local frontend proposal types near the graph review workbench. Keep these deliberately close to the Prime Design assertion model, but do not pretend they are backend contracts yet.

Suggested file:

```text
apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphObjectAuthoringDraft.ts
```

Suggested types:

```ts
export type GraphObjectAuthoringVisibility =
  | "gm_private"
  | "table_known"
  | "player_visible"
  | "character_specific"
  | "hidden_until_revealed";

export type GraphObjectAuthoringScope =
  | "recap_graph"
  | "campaign_memory_graph"
  | "gm_private_graph"
  | "player_visible_graph";

export interface GraphObjectAuthoringFormState {
  label: string;
  kind: string;
  role: string;
  aliasesText: string;
  summary: string;
  operatorNote: string;
  visibility: GraphObjectAuthoringVisibility;
}

export interface GraphObjectAuthoringProposal {
  localProposalId: string;
  proposalKind: "object";
  status: "staged_local";
  selection: GraphAuthoringSelection;
  objectRef: {
    label: string;
    kind: string;
    role?: string | null;
    aliases: string[];
    summary?: string | null;
  };
  visibility: {
    visibility: GraphObjectAuthoringVisibility;
    revealState: "unrevealed" | "partial" | "revealed";
    visibilityNote?: string | null;
  };
  graphScopes: GraphObjectAuthoringScope[];
  provenancePreview: {
    origin: "human_authored";
    authoringSurface: "memory_ingest_graph_authoring";
    sourceGraphId?: string | null;
    sourceArtifactPath?: string | null;
    operatorNote?: string | null;
  };
}
```

Suggested helper behavior:

- parse aliases from comma-separated or newline-separated text;
- trim aliases;
- deduplicate aliases case-insensitively;
- omit empty aliases;
- if label differs from selected text, include selected text as an alias unless already present;
- generate local ids with a deterministic-ish prefix like `local-object-${Date.now()}-${counter}` or a small local helper.

---

## §6 UI shape

Preferred component layout:

```text
GraphObjectAuthoringSurface
  GraphObjectAuthoringSelectedSource
  GraphObjectAuthoringObjectForm
  GraphObjectAuthoringVisibilitySection
  GraphObjectAuthoringStagingTray
```

Suggested files:

```text
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringSurface.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringSelectedSource.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringObjectForm.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringVisibilitySection.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringStagingTray.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/useGraphObjectAuthoringDraft.ts
apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphObjectAuthoringDraft.ts
```

A single file is acceptable if the implementation stays simple, but the component boundary above is preferred for A3/A4 composability.

### Placement

Use the existing `/ingest` Graph Review workbench surface. Do not create a new route.

Prefer placing the authoring surface adjacent to the projected recap, replacing the A1 selected-source debug preview.

Do not move Graph Object Authoring into `/plan`, a global graph editor, or a player-facing route.

### Interaction

The flow should be:

```text
highlight source text → Author graph object → authoring surface opens/focuses → form seeded from selection → Stage object draft → staging tray updates
```

If the authoring mode toggle remains, it should not be the center of the UX. The object authoring surface should make clear what the user can do next.

---

## §7 Allowlist

Only touch files needed for A2.

| Path | Action |
|------|--------|
| `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLiveProjectionPanel.tsx` | replace selected-source debug preview with local authoring surface wiring |
| `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewAuthoringReader.tsx` | pass confirmed/active selection into authoring surface if needed |
| `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringSurface.tsx` | create |
| `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringSelectedSource.tsx` | create |
| `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringObjectForm.tsx` | create |
| `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringVisibilitySection.tsx` | create |
| `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringStagingTray.tsx` | create |
| `apps/live-control-ui/src/planSurface/graphReviewWorkbench/useGraphObjectAuthoringDraft.ts` | create local draft/staging hook |
| `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphObjectAuthoringDraft.ts` | create local types/helpers |
| `apps/live-control-ui/src/planSurface/graphReviewWorkbench/*.test.tsx` | focused tests |
| `apps/live-control-ui/src/planSurface/planSurface.css` | minimal styling |

Only touch `apps/live-control-ui/src/planSurface/config/ingestSurfaceConfig.ts` if you truly need to expose the surface through the toolbox configuration. Prefer local workbench wiring if possible.

Do not touch backend files.

Do not touch corpus files.

Do not touch `graph_gold_authoring_prepare.py`, `graph_gold_authoring_commit.py`, authored graph store code, or event log code.

---

## §8 Required behavior

### 8.1 Open from selected source

Given a valid `GraphAuthoringSelection`, clicking `Author graph object` opens/focuses the authoring surface and seeds the form label from `selectedText`.

### 8.2 Preserve selected source snapshot

The authoring surface preserves the selected source snapshot even if the browser selection clears.

### 8.3 Form editing

The user can edit label, kind/type, role, aliases, summary, operator note, and visibility.

### 8.4 Stage locally

Clicking `Stage object draft` adds a proposal to local staging state and renders it in the staging tray.

### 8.5 Clear no-write semantics

The authoring surface and staging tray must both make it clear that no graph write has happened.

### 8.6 Remove staged proposal

The user can remove a staged local proposal.

### 8.7 A1 behavior survives

Existing graph chip inspection still works.

Gold-vs-live comparison mode still preserves decorated live lane behavior when authoring mode is off.

Live-only no-gold mode remains usable.

---

## §9 Non-goals and guardrails

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
- call an LLM;
- add identity merge behavior;
- implement relationship authoring;
- implement link-existing writes;
- build a generic graph editor;
- solve player-specific visibility targeting.

Relationship authoring and link-existing are A3. Prepare/commit is A5. Projection overlay reload is A6.

---

## §10 Verification

Run focused frontend checks from `apps/live-control-ui`.

```bash
npm test -- GraphObjectAuthoring GraphReviewLiveProjectionPanel graphObjectAuthoringDraft
npm run typecheck
npm run build
```

If filtering is unreliable, run:

```bash
npm test
npm run typecheck
npm run build
```

If unrelated pre-existing tests fail, report exact failures and explain why they are unrelated.

Expected test coverage:

- clicking `Author graph object` opens/focuses the authoring surface;
- selected text seeds the label field;
- changing the label can preserve selected text as an alias;
- aliases are parsed/trimmed/deduped;
- default visibility is GM private;
- user can change visibility;
- staging an object draft renders it in the staging tray;
- staging tray says no graph write has happened;
- removing a staged proposal works;
- gold-vs-live compare live lane remains decorated when authoring mode is off;
- graph chip inspection still works.

---

## §11 Manual dogfood checklist

Use C1S2 or another live-only/no-gold graph run if available. Also smoke a has-gold compare session if possible.

1. Open `/ingest`.
2. Load an ingested recap projection.
3. Highlight `gang` or another short source phrase.
4. Click `Author graph object`.
5. Confirm the Graph Object Authoring surface opens/focuses.
6. Confirm selected source card shows the phrase and context.
7. Confirm label seeds from selected text.
8. Change label to `Questionable Company`.
9. Confirm `gang` can be present as an alias.
10. Set kind/type to `party` or `faction`.
11. Add a short summary.
12. Confirm visibility defaults to `GM private`.
13. Change visibility to `Table known / player visible`.
14. Click `Stage object draft`.
15. Confirm a staging tray row/card appears with no-write copy.
16. Remove the staged proposal.
17. Confirm graph pill inspection still works.
18. In a has-gold session, leave authoring mode off and confirm compare decorations still appear.

---

## §12 Rubric

### Testing

Focused tests cover the object authoring form, seeded selection, visibility default/change, local staging tray, proposal removal, and no-regression review behavior.

### Security

No backend writes. No corpus writes. No source markdown mutation. No LLM calls. No eval fixture writes.

### Simplicity

A2 only. Local proposal state and UI form. No prepare/commit, no storage, no relationship builder.

### Composability

Types should be close enough to the Prime Design assertion model that A4/A5 can translate local proposals into authored graph assertions later.

### UX honesty

The user should never believe the graph changed. Use plain language: `staged locally`, `draft`, `no graph write has happened`.

---

## §13 Review risks to watch

1. **A2 accidentally starts A3.** Existing-object linking and relationship authoring are next, not now.
2. **A2 accidentally starts A5.** No prepare/commit endpoints or file writes.
3. **The staged proposal shape drifts away from the assertion model.** Keep selection, object ref, visibility, provenance preview, scopes, and local status together.
4. **The UX keeps the A1 debug preview as the main experience.** Replace it with a small form/staging surface.
5. **Gold-vs-live compare regresses again.** Keep the PR #277 safeguard: old decorated lane when authoring is off.
6. **Visibility is omitted.** Visibility metadata must enter now, even locally.
7. **No-write copy is missing.** This is a local staging slice; the UI must say so.

---

## §14 Follow-on PRs this enables

After A2 lands:

- A3 can add relationship authoring and link-existing local proposals.
- A4 can define authored graph overlay contracts and file-backed local store.
- A5 can add prepare/commit/event-log writes.
- A6 can reload projections with authored overlays applied.
- A9 can derive graph-gold/eval output from human-authored corrections.

Do not start those in this PR.

---

## §15 Reference index

Primary design/roadmap:

- `Docs/Design/DESIGN-graph-object-authoring-surface.md`
- `Docs/Plans/ROADMAP-graph-object-authoring-surface.md`

Dependency:

- PR #277, `Graph Authoring A1: Tiptap selection adapter`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphAuthoringSelection.ts`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/useGraphAuthoringSelection.ts`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewAuthoringReader.tsx`
- `apps/live-control-ui/src/planSurface/graphProjectionReader/GraphProjectionReader.tsx`

Likely A2 implementation anchors:

- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLiveProjectionPanel.tsx`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringSurface.tsx`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringSelectedSource.tsx`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringObjectForm.tsx`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringVisibilitySection.tsx`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringStagingTray.tsx`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/useGraphObjectAuthoringDraft.ts`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphObjectAuthoringDraft.ts`
- `apps/live-control-ui/src/planSurface/planSurface.css`

Backend/write paths to avoid:

- `apps/live_control_server/services/graph_gold_authoring_prepare.py`
- `apps/live_control_server/services/graph_gold_authoring_commit.py`
- authored graph overlay store files, if present
- event log writers, if present
- `src/agent/corpus_writer.py`
