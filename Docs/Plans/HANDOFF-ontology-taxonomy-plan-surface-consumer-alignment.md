# HANDOFF - Ontology / Taxonomy alignment with the `/plan` consumer

**Created:** 2026-06-21 (UTC).  
**Status:** ACTIVE - design-alignment handoff for the Ontology / Taxonomy ladder.  
**Parent context:** Cursor plan-surface implementation and dogfood feedback.  
**Consumer anchor:** App-level Agent Interaction Bar/Pane, `/plan` surface, live-control UI, and current static live-play toolbox prototype.  
**Ontology anchor:** `Docs/Experiments/EXPERIMENT-Ontology-Taxonomy-Ladder.md`.

---

## §1 Mission

Evolve the Ontology / Taxonomy ladder with explicit knowledge of the `/plan` surface as a future graph-memory consumer, looking first for vocabulary, provenance, lifecycle, and adapter mismatches before production retrieval changes.

## §2 Why this handoff exists

The `/plan` workstream is no longer only a route scaffold. It is becoming one GM-facing surface that will consume derived knowledge: recap ingestion, statblock generation, reference-chip navigation, projected content surfaces, and eventually deeper graph-backed traversal.

Canon decision (2026-06-21): the durable consumer is the app-level **Agent Interaction Bar/Pane**, owned by `AgentInteractionProvider`, not a `/plan` sub-state. `/plan` publishes context and projection registrations into that provider. The provider owns user/session continuity across surfaces/projects: active conversation/thread pointers, pane state, active projection, recent tool runs, notifications, and proof-trail pointers.

The ontology ladder is still correctly isolated. It owns derived semantics, controlled vocabulary, graph model, validation, reports, and later shadow retrieval. It must not be pulled prematurely into UI implementation or production retrieval. But its design should now know what kind of consumer is coming so it does not mature in a vacuum.

The desired outcome is early alignment, not coupling. `/plan` should keep reading through adapters; ontology should keep producing diagnostic, source-grounded structures. The alignment work is to make sure those two shapes will meet cleanly when shadow retrieval becomes consumable.

## §3 Product shape of the consumer

`/plan` is an intentional planning workspace, not a random live session page. Its consumer role is now part of a larger app-level interaction model:

- A main Tiptap/Markdown planning canvas where the GM writes and reviews prep.
- A persistent bottom Agent Interaction Bar owned above surfaces, with an expandable Agent Interaction Pane.
- Tool projections for recap ingestion, statblock generation, chat/ask, reference inspection, and corpus-impact proof. These are workflows/projections, not pages.
- Reference chips inside the canvas, encoded as opaque handles such as `#dmb-ref:<type>:<id>`, that resolve into projected content surfaces.
- A shared projection registry: opening a tool, following a reference, and viewing proof use the same projection mechanism.
- Edit is a capability, not a separate data model: content is read-only by default, can be unlocked, and committed writes must go through the corpus writer / two-phase safety model where applicable.

Ownership boundary:

- `AgentInteractionProvider` owns user interaction continuity and stores pointers/summaries, not canonical corpus payloads.
- `/plan` publishes ambient context: campaign id, prep/live/ingest sessions, selected canvas block/reference, and available projections.
- Ontology/graph outputs should target adapters that can feed app-level projections, not route-specific drawer state.

Today, `/plan` resolves chips through live-derived corpus indexes:

- `npc` -> `/api/live/npcs/index`
- `location` -> `/api/live/locations/index`
- `statblock` -> `/api/live/statblocks/index`
- `roll-table` -> `/api/live/roll-tables/index`

The surface intentionally treats `refId` as an opaque locator. It validates the locator, asks an index/adapter to resolve it, and projects whatever source-backed unit comes back. It does not perform alias resolution, identity merging, relationship inference, or taxonomy ownership.

## §4 Current adapter boundary

The current React adapter already speaks the ladder-shaped vocabulary:

```text
source artifact -> source anchor -> source unit
```

Current files to read before changing ontology design:

1. `Docs/Experiments/EXPERIMENT-Ontology-Taxonomy-Ladder.md`
2. `Docs/Experiments/PLAN-SURFACE-LADDER-TRACKING.md`
3. `/home/drakosfire/.cursor/plans/plan-surface-toolbox_5034ad28.plan.md`
4. `apps/live-control-ui/src/planSurface/derivedViews/derivedViewsAdapter.ts`
5. `apps/live-control-ui/src/planSurface/reference/referenceResolver.ts`
6. `apps/live-control-ui/src/chrome/AppChrome.tsx`
7. `apps/live-control-ui/src/planSurface/projection/AdaptiveProjectionContainer.tsx`
8. `apps/live-control-ui/src/planSurface/projection/projectionRegistry.tsx`

Important current contract:

- `SourceAnchor` is the chip-level navigation handle: kind, label, `refId`, and local href.
- `SourceUnit` is the projected content unit: summary, fields, and optional source path.
- `DerivedViewsReader` has one job today: `resolveReference(ref)`.
- A later shadow-retrieval reader should be able to replace the implementation without requiring `/plan` to learn graph internals.

## §5 Alignment questions for the ontology ladder

Use these as design review prompts before adding new graph-memory rungs.

1. **Vocabulary ownership:** Which taxonomy registry terms map to today's UI-facing `refType` strings? Does the ladder preserve a stable adapter map, or does it expect the consumer to rename itself around graph vocabulary?

2. **Source unit shape:** Does the ladder's source unit carry enough information for a content projection: display label, source path or source locator, evidence role, lifecycle state, concise summary, and typed fields? If not, what is intentionally absent?

3. **Evidence vs summary:** How will the graph prevent a projected surface from treating a graph summary as source evidence? The UI can display summaries, but source-backed claims need source anchors.

4. **Lifecycle state:** Can the graph distinguish played truth, GM prep, rumor, generated candidate, dismissed candidate, promoted canon, and diagnostic-only extraction? `/plan` needs to display these differently and must not flatten them into "known fact."

5. **Identity and aliases:** How does the graph expose alias candidates without forcing the UI to merge identities? A chip locator may point to a corpus artifact while the graph knows related aliases; the adapter must preserve provenance and confidence.

6. **Depth control:** Reference chips are navigation handles into deeper context. What bounded expansion shape prevents high-degree hubs from flooding the drawer? What measurements tell us expansion is useful rather than noisy?

7. **Write interaction:** Recap ingestion and statblock promotion produce new corpus/session-memory artifacts. Does graph materialization consume these as source artifacts after the writer path completes, or does it imply a second write path? It must not mutate canonical corpus. `AgentInteractionProvider` can remember proof pointers and tool-run summaries, but writes still go through explicit project/corpus APIs.

8. **Generated statblocks:** Statblock generation has draft, accepted-to-combat, promoted-to-corpus, and indexed states. Which of these are graph candidates, which are corpus truth, and which must remain local/browser state?

9. **Error and degradation:** When graph shadow retrieval is missing, stale, or uncertain, what should the adapter return so `/plan` can degrade to current live-index behavior without pretending the graph answered?

10. **Security and privacy:** Does the graph expose filesystem paths, corpus excerpts, or player-private data in a way the UI could leak into logs/artifacts? The consumer should receive safe locators and display metadata, not unbounded traces by default.

## §6 Likely mismatch risks

### Risk A - taxonomy drift between UI strings and graph categories

The surface currently has operational strings (`npc`, `location`, `statblock`, `roll-table`) because the live indexes expose those routes. The ladder may prefer a richer taxonomy. If both sides independently name categories, they will drift.

Preferred mitigation: ontology owns the registry; `/plan` owns only adapter keys and display projections. Add an explicit adapter map from graph taxonomy terms to projection kinds.

### Risk B - session-memory sentence units are too narrow for the consumer

The current ontology next rung admits `session_memory_jsonl_sentence_units` only. That is a good boring gate, but `/plan` will need content surfaces for corpus hubs, dossiers, statblocks, roll tables, generated drafts, and recap/session memory.

Preferred mitigation: keep the next rung narrow, but document which future source families will be needed for the plan-surface consumer and what evidence shape each must provide.

### Risk C - graph summaries become tempting UI payloads

The drawer wants concise summaries. The ladder forbids graph summaries as source evidence. This is a healthy tension.

Preferred mitigation: return both `display_summary` and source-backed anchors, with schema-level clarity that the summary is navigational prose, not evidence.

### Risk D - lifecycle collapse

The user experience wants frictionless movement between planning, generated content, and canon. That can accidentally collapse prep, rumor, generated candidates, and played truth into one state.

Preferred mitigation: lifecycle / canon layer is first-class in ontology IR and every materialized unit. `/plan` can then visually style states instead of guessing.

### Risk E - identity merge pressure leaks into the consumer

Reference chips will create pressure to "just find the thing." But alias resolution and entity merge logic belong to the ladder, not the UI.

Preferred mitigation: adapter returns matched entity, candidate aliases, provenance, and confidence separately. `/plan` displays or offers navigation; it does not merge.

### Risk F - graph depth overwhelms a fast drawer

The live-play drawer feels good because it is fast and bounded. A graph traversal can easily become too much.

Preferred mitigation: the shadow retrieval API should support explicit limits, relation filters, source-family filters, and explanation metadata. Measure context flood before promotion.

## §7 Files in scope for an ontology alignment PR

This handoff is intentionally design-first. A follow-up ontology PR should stay in ontology/design/report surfaces unless explicitly promoted.

| Action | Path | Purpose |
|---|---|---|
| Modify | `Docs/Experiments/EXPERIMENT-Ontology-Taxonomy-Ladder.md` | Add a "Plan Surface consumer alignment" note or link to a companion review. |
| Create or modify | `Docs/Design/*ontology*` or `Docs/Design/*graph-memory*` | Capture adapter contract, lifecycle states, and source-unit expectations if a design doc already exists or is warranted. |
| Create or modify | `Docs/Reports/*ontology*` or `Docs/Reports/*graph-memory*` | Record risk/mismatch review results without changing runtime behavior. |
| Modify | `evals/graph_memory_layer/**` | Only if adding diagnostic fixtures or schema validation for the adapter/lifecycle shape. |
| Modify | `tests/test_graph_memory_*.py` | Only if graph-memory schema or validation behavior changes. |
| Modify | `src/graph_memory/**` | Only if the active ladder rung already permits this path. |

## §8 Files explicitly out of scope

Do not touch these from an ontology alignment PR unless a separate handoff says otherwise:

| Path | Why out of scope |
|---|---|
| `apps/live-control-ui/src/planSurface/**` | `/plan` is the consumer being studied; do not rewrite it from the ontology branch. |
| `apps/live-control-ui/src/modules/IngestionModule.tsx` | Ingestion UI is already mounted; ontology should consume artifacts after writes, not change the workflow. |
| `apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx` | Statblock workflow is a consumer/source producer; do not alter it for graph design. |
| `apps/live_control_server/routes/live.py` | Production live indexes remain the current read path until explicit promotion. |
| `apps/live_control_server/services/*corpus_index*.py` | Current index services are the fallback adapter source; do not replace them from the ladder. |
| `corpus/**` | Canonical corpus mutation is forbidden by the ontology ladder. |
| `src/prompts/**` | No prompt or LLM extraction change is part of this alignment step. |

## §9 Expected output from the ontology/taxonomy agent

Produce one of these, depending on scope:

1. A short design-review report that answers the §5 questions and lists mismatches by severity.
2. A targeted update to the ontology ladder anchor that names `/plan` as a known future consumer and records the adapter/lifecycle constraints.
3. A schema or fixture change only if the active rung already permits it and the change is diagnostic-only.

The report should include:

- A table or bullets mapping current `/plan` reference types to ontology/taxonomy concepts.
- A proposed graph-to-`SourceUnit` adapter shape.
- Lifecycle states required by `/plan`, with names that do not collapse prep, rumor, generated candidates, and played truth.
- At least three explicit mismatch risks and how the ladder will detect or defer them.
- A statement of what remains intentionally unaligned until shadow retrieval exists.

## §10 Verification commands

If the follow-up is docs/report only:

```bash
rg -n "Plan Surface|/plan|source artifact|source anchor|source unit|lifecycle|graph summaries|refId|statblock" Docs/Experiments Docs/Design Docs/Reports
```

If schema, fixture, validation, or graph-memory code changes:

```bash
uv run pytest tests/test_graph_memory_*.py -q
```

If a change claims compatibility with the current `/plan` consumer contract:

```bash
cd apps/live-control-ui && npm test -- PlanSurfaceShell.test.tsx referenceResolver.test.ts derivedViewsAdapter.test.ts
```

## §11 Acceptance rubric

- The ontology ladder remains isolated: no production retrieval change, no corpus mutation, no LLM extraction, no prompt edits.
- `/plan` is described as a consumer of source-grounded derived views, not as the owner of taxonomy, aliasing, or graph memory.
- The adapter vocabulary remains explicit: `source artifact -> source anchor -> source unit`.
- Lifecycle/provenance is first-class; generated candidates, prep, rumor, played truth, and promoted canon are not collapsed.
- Graph summaries are not treated as source evidence.
- Current live-index fallback remains valid until a measured shadow-retrieval path is promoted.
- Any runtime/schema change is diagnostic-only and verified by graph-memory tests.

## §12 Notes for future alignment

The north star is not "make the UI graph-aware." The north star is "let the UI ask for source-backed, lifecycle-aware units through a stable adapter." If the adapter is right, `/plan` can gain deeper reference navigation without learning graph internals, and ontology can mature without chasing every surface affordance.

The live-play drawer is the interaction prototype: fast, bounded, and content-sized. Graph memory should enhance what appears inside that drawer, not make the drawer slower, noisier, or more speculative.
