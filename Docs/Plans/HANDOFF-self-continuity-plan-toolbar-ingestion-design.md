# HANDOFF — Plan Toolbar / Ingestion Design Reset

**Status:** Active self-continuity handoff  
**Written:** 2026-06-21  
**Audience:** Fresh in-IDE agent working directly with the user on design before implementation  
**Primary goal:** Redesign the app-level agent interaction experience that `/plan` uses, with the recap ingestion workflow as the initial focus, so the user can complete the ingestion pipeline in the UI and prove the result through interaction.

## 0. Hard Stop Context

The previous agent work reached a hard stop. The user explicitly said the current `/plan` ingestion experience is "ugly and bad" and so distracting they cannot focus or tell whether the pipeline is working.

The next agent must not treat the current `/plan` route as the design exemplar. It is current implementation state only.

The exemplar is:

`http://localhost:5173/evals/c2_live_prep/mireward-prep/live-play.html`

That static live-play route is not perfect, but it is materially better than `/plan` for this purpose. It has the "glorious Tools drawer" feel the user wants copied or lifted: fast, styled, obvious handle, tool tabs, content-specific expansion, and a calmer command-board feel. The placement decision has changed: the durable shell should be a persistent bottom **Agent Interaction Bar** and expandable **Agent Interaction Pane**, not a `/plan`-owned right drawer.

## 1. Mission

Work with the user to design the app-level Agent Interaction Bar/Pane, using the live-play Tools drawer as the feel/source of truth but not as a literal placement constraint. The first workflow to design inside that component is recap ingestion.

Do not jump straight into implementation. The first deliverable should be a clear design proposal or wireframe-level component model that the user can react to.

The design must make it possible to dogfood this end-to-end goal:

1. Start on `/plan`.
2. Use the bottom Agent Interaction Bar.
3. Open the Agent Interaction Pane into the ingestion projection.
4. Run the full recap ingestion pipeline through the UI.
5. Understand each review gate without guessing.
6. Prove ingestion succeeded by interacting with the resulting knowledge or artifacts from the UI.

## 2. Non-Negotiable Product Direction

- `/plan` is **not** the exemplar.
- The static live-play page **is** the exemplar: `evals/c2_live_prep/mireward-prep/live-play.html`.
- The design should copy or lift the live-play Tools drawer feel as much as is practical, but the persistent control lives along the bottom as the Agent Interaction Bar.
- `AgentInteractionProvider` is app/user scoped, not `/plan` scoped. It belongs above surfaces, alongside or inside `AppChrome`.
- Surfaces publish context and available projections into the agent layer; they do not own conversation state, pane state, proof trail state, or cross-project continuity.
- The Agent Interaction Bar is intended to live across surfaces and projects. `/plan` is the first consumer, not the owner.
- Recap-ingestion proof/memory data must cross into Agent Interaction through `Docs/Design/CONTRACT-surface-vocabulary-boundary-v0.md`: `IngestionSourceBundle` (`SourceArtifact` -> `SourceAnchor` -> `SourceUnit`), not raw ingestion internals.
- Ingestion must feel like one guided workflow with human review gates, not a random row of peer buttons.
- The UI must reduce distraction. If the user cannot focus or tell whether something worked, the design has failed.
- The terminal path must remain available, but it should be secondary/collapsible. The UI is the primary dogfood path.
- Statblock generation remains a second drawer tool and should expand just as far as ingestion when needed.
- The toolbar/drawer should be reusable later, but do not let abstraction dominate the immediate ingestion UX.

## 3. Current User Feedback To Preserve

The user liked:

- The live-play Tools drawer.
- The speed of the static prototype.
- The styling and feel of the live-play toolbox.
- The idea that statblock generation lives in the same drawer and expands into an appropriate surface.

The user disliked:

- Current `/plan` ingestion layout.
- Visual clutter and distraction.
- The workflow not clearly showing whether it is working.
- The feeling that buttons are just available without a clear sequence or review model.
- The current `/plan` attempt still not matching the live-play route closely enough.

Quote-level intent to preserve:

> "This looks right" applied to the drawer direction, but not the ingestion workflow.

> "It's ugly and bad and so distracting I cant focus or really tell if it's working still."

> "It still doesn't really match the live play one."

> "That expands different amounts. That is the prototype. Rebuild it or lift it whole."

> "Agent Interaction bar lives across Surfaces as well. That should be inherent. It's state is the users state across all projects. Not a sub state of a particular surface."

## 4. Files In Scope For Design Investigation

Read these first.

Static live-play exemplar:

- `evals/c2_live_prep/mireward-prep/live-play.html`
- `evals/c2_live_prep/mireward-prep/assets/prep.js`
- `evals/c2_live_prep/mireward-prep/assets/prep.css`

Key static drawer areas:

- `prep.js`: `statblockDogfoodPanelHtml`
- `prep.js`: `ingestionToolboxPanelHtml`
- `prep.js`: `ensureToolboxDrawer`
- `prep.js`: `setToolboxOpen`
- `prep.js`: `setToolboxTool`
- `prep.js`: `wireToolboxControls`
- `prep.css`: `.prep-toolbox-toggle`
- `prep.css`: `.prep-toolbox-drawer`
- `prep.css`: `.prep-toolbox.tool-ingestion .prep-toolbox-drawer`
- `prep.css`: `.prep-toolbox-nav`
- `prep.css`: `.recap-ingestion-grid`
- `prep.css`: `.recap-ingestion-flow-card`
- `prep.css`: `.recap-ingestion-preview`

Current `/plan` implementation state:

- `apps/live-control-ui/src/chrome/AppChrome.tsx`
- `apps/live-control-ui/src/planSurface/PlanSurfaceShell.tsx`
- `apps/live-control-ui/src/planSurface/projection/AdaptiveProjectionContainer.tsx`
- `apps/live-control-ui/src/planSurface/projection/projectionContext.tsx`
- `apps/live-control-ui/src/planSurface/projection/projectionRegistry.tsx`
- `apps/live-control-ui/src/planSurface/config/planSurfaceConfig.ts`
- `apps/live-control-ui/src/planSurface/planSurface.css`
- `apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx`

Current React ingestion workflow:

- `apps/live-control-ui/src/modules/IngestionModule.tsx`
- `apps/live-control-ui/src/modules/IngestionStatusPanel.tsx`
- `apps/live-control-ui/src/modules/IngestionModule.test.tsx`
- `apps/live-control-ui/src/api/types.ts`
- `Docs/Design/CONTRACT-surface-vocabulary-boundary-v0.md`

Backend ingestion API:

- `apps/live_control_server/routes/recap_ingest.py`
- `src/live_play/recap_ingest_pipeline.py`
- `tests/test_live_recap_ingest_api.py`

Related dogfood learning:

- `Backlog.md` entry: `Plan surface dogfood — calm toolbar, busy canvas, branching slide graph`

## 5. Files Explicitly Out Of Scope Unless User Approves

- Do not edit the original Cursor plan file: `/home/drakosfire/.cursor/plans/plan-surface-toolbox_5034ad28.plan.md`.
- Do not restructure unrelated `/plan` reference-chip or derived-view architecture.
- Do not change corpus content as part of toolbar design.
- Do not change statblock generation behavior unless the design specifically requires a wrapper/layout change.
- Do not rewrite the backend ingestion pipeline to compensate for UI confusion until the UI design has been reviewed.
- Do not remove the terminal fallback.

## 6. Current Implementation State

The previous agent moved `/plan` toward a live-play-like drawer:

- `AdaptiveProjectionContainer.tsx` now renders a fixed right-side drawer with a vertical `Tools` button, backdrop, header, nav tabs, and projection body.
- `planSurface.css` now includes `.plan-toolbox-*` and `.plan-projection-*` rules copied in spirit from `.prep-toolbox-*`.
- `/plan` no longer renders the old in-page `PlanToolBar` card in `PlanSurfaceShell.tsx`.
- Tool tabs open existing React modules:
  - `Ingest Recap` -> `IngestionModule`
  - `Statblock` -> `StatblockWorkbenchModule`
- Focused UI tests passed:
  - `npm test -- PlanSurfaceShell.test.tsx`
- Frontend build passed:
  - `npm run build`
  - Only the existing Vite large-chunk warning appeared.

This is implementation state, not design approval. The user still considers the ingestion experience bad, and has now clarified that the right-side Tools drawer is the wrong ownership boundary. The durable interaction surface is an app-level bottom Agent Interaction Bar/Pane.

## 7. Design Problem To Solve

The current UI is mixing two questions:

1. "Can the backend operation be triggered?"
2. "Does the user understand where they are in the ingestion pipeline and what evidence proves it worked?"

The design must separate those.

The ingestion projection should answer, at a glance:

- What session/slug/title is being ingested?
- What is the current pipeline step?
- What is the next recommended action?
- What is waiting for human review?
- What artifact or state proves each step completed?
- What should the user click if something is blocked?
- What did the UI ingest, and how can the user interact with the result?

Avoid a flat list of operation buttons as the primary mental model. The operations are real, but the user should experience them as a guided pipeline.

## 8. Canonical Agent Interaction Direction

Use the live-play drawer shell as a feel/design source, then implement the ownership boundary as an app-level agent interaction layer.

The canonical composition is:

```text
AppChrome
  AgentInteractionProvider
    Route / Surface
      PlanSurfaceShell
      LiveControlSurface
      TiptapSurface

  AgentInteractionBar
  AgentInteractionPane
```

### AgentInteractionProvider

This provider owns the user's agent interaction state across surfaces/projects:

- current conversation/thread pointers,
- open/minimized/expanded pane state,
- active projection (`chat`, `ingestion`, `statblock`, `reference`, `corpus-impact`, etc.),
- recent tool runs and proof-trail pointers,
- notifications like "C2S23 ready - view proof",
- ambient project/campaign/session context received from surfaces.

It should store pointers, summaries, and UI state. It must not become a second corpus store and must not bypass explicit backend write flows.

For recap ingestion, those pointers/summaries are supplied by the source-vocabulary adapter. Agent Interaction consumes `IngestionSourceBundle`; `_normalized/`, `_breadcrumbed/`, `.records_meta.jsonl`, and `corpus_impact` stay production artifacts behind the adapter.

### Surface Boundary

Surfaces contribute context and projection registrations:

- `/plan`: campaign id, prep/live/ingest sessions, selected canvas block/reference, planning projections.
- `/surface`: live session, active event/job/combat state, live projections.
- editor/developer surfaces: selected document/reference and edit capability state.

The surface can request `openProjection("ingestion")` or publish `selectedReference`, but it does not own the agent pane lifecycle.

### Bottom Shell

- Persistent bottom Agent Interaction Bar.
- Compact status/ask affordance visible across surfaces.
- Expandable bottom pane with peek/half/full sizes.
- Projection tabs or chips for `Ask`, `Ingestion`, `Statblock`, `Inspect`, and `Proof` as available.
- Body scrolls independently inside the pane.
- The pane renders app-level projections using the shared projection registry.

### Ingestion Projection

The panel likely wants three zones:

- **Left: Source and controls**
  - session, slug, title
  - raw recap text
  - primary next-action button
  - secondary/manual operation controls collapsed under "Advanced / Terminal path"

- **Center/top: Pipeline state**
  - Source -> Preview -> Normalize -> Seed -> Breadcrumb -> Memory -> Prove
  - each step has status: waiting, active, needs review, done, blocked
  - active step has one obvious next action

- **Right: Evidence / Preview**
  - rendered markdown preview for early steps
  - frontmatter seed review when seed exists
  - breadcrumb/session-memory artifact proof when later steps complete
  - final "Prove ingestion" affordance

### Final Proof Step

Add an explicit final step named something like `Prove` or `Use It`.

This is important. The user’s goal is not just to see "ready"; it is to prove ingestion by interacting with the resulting knowledge.

Candidate proof affordances:

- show `IngestionSourceBundle` artifacts/anchors/units for the normalized recap, breadcrumbed recap, frontmatter seed, session-memory recordset, and corpus-impact proof,
- show materialized session-memory record count and artifact locators,
- show generated/breadcrumbed files with open/preview links through opaque locators,
- surface entity/reference anchors discovered from the recap,
- let the user click an entity/reference and open the same projection surface used by reference chips,
- expose an "Ask/inspect what changed" UI if such a safe endpoint exists,
- at minimum, provide an inspectable artifact list with statuses and links.

In the bottom bar, this should become a durable notification/proof affordance: e.g. `C2S23 ready - 7 memory records - View proof`. Expanding it opens an ingestion proof projection backed by `IngestionSourceBundle` and preserves that proof pointer even if the user navigates away from `/plan`.

If the current backend does not expose enough proof metadata, the smallest backend/API addition is the read-only ingestion source-vocabulary adapter defined in `Docs/Design/CONTRACT-surface-vocabulary-boundary-v0.md`.

## 9. Known Backend / Pipeline Operations

The UI currently wraps operations like:

- `stage_preview`
- `apply_normalize`
- `build_frontmatter_seed`
- `run_breadcrumb_ingest`
- `materialize_session_memory`
- `inspect_status`

Relevant implementation paths:

- `apps/live_control_server/routes/recap_ingest.py`
- `src/live_play/recap_ingest_pipeline.py`
- `src/live_play/*` or equivalent new adapter module for `build_ingestion_source_bundle(...)`
- `apps/live-control-ui/src/modules/IngestionModule.tsx`
- `apps/live-control-ui/src/api/types.ts`
- `Docs/Design/CONTRACT-surface-vocabulary-boundary-v0.md`

Important recent backend behavior:

- `stage_preview` was changed so existing staged raw notes can become a recoverable review/conflict state rather than a hard error.
- The UI has some states like `staged_raw_notes_conflict`, `frontmatter_seed_built`, `frontmatter_seed_reused`, etc.
- Do not assume every backend status is currently presented well in the UI.

## 10. Design Acceptance Criteria

The next design is good enough to implement only if the user can look at it and answer:

- "I know what the next click is."
- "I know whether I am reviewing text, approving a generated artifact, or running a machine step."
- "I know whether the pipeline is blocked or just waiting."
- "I can tell what artifact changed."
- "I can prove the recap has become usable campaign knowledge without opening a terminal."
- "This feels like the live-play Tools drawer lineage, not a separate dashboard."
- "The ask/proof/tool surface follows me across surfaces instead of being trapped inside `/plan`."
- "The surface gives context to the agent pane; it does not own my agent interaction state."

## 11. Verification Plan Once Implemented

Frontend:

- `cd apps/live-control-ui && npm test -- PlanSurfaceShell.test.tsx`
- `cd apps/live-control-ui && npm test -- IngestionModule.test.tsx`
- `cd apps/live-control-ui && npm run build`

Backend, if API behavior changes:

- `uv run pytest tests/test_live_recap_ingest_api.py`

Dogfood:

- Start servers already used by the user:
  - Vite at `http://localhost:5173`
  - FastAPI at `http://localhost:8000`
- Open `/plan`.
- Use the bottom Agent Interaction Bar.
- Complete the ingestion pipeline through the UI.
- Use the final proof surface to interact with what was ingested.
- Compare drawer feel against `http://localhost:5173/evals/c2_live_prep/mireward-prep/live-play.html`.

## 12. Recommended First Move For Fresh Agent

Do not start by editing code.

Start by telling the user:

1. You understand that live-play is the exemplar and `/plan` is not.
2. You will inspect the live-play drawer and current `/plan` drawer.
3. You will propose a focused ingestion-drawer design before changing files.
4. You will keep the design centered on the dogfood proof: ingest in UI, then prove it by interaction.

Then read the files in §4 and come back with a concise design proposal.

