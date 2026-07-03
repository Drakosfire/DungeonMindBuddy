# Roadmap — Graph Review + Gold Authoring Workbench

**Status:** Active roadmap  
**Date:** 2026-07-02  
**Workstream:** Graph Memory / Graph Review / Gold Authoring  
**Design doc:** `Docs/Design/DESIGN-graph-review-gold-authoring-workbench.md`  
**Archived predecessor:** `Docs/Plans/archive/2026-07-02/handoffs/HANDOFF-prime-design-graph-exploring-tool-consolidation.md`

## 1. Roadmap goal

Build a prose-first graph review and gold-authoring workbench that feels magical and useful to a GM while preserving strict source, write-safety, and graph-memory boundaries.

The workbench must support:

1. side-by-side projected recap review;
2. game-useful node and relationship interactions;
3. writable gold authoring over prose;
4. existing-object linking;
5. LLM proposal staging;
6. safe two-phase gold fixture writes;
7. minimal authoring event logging;
8. retirement of old table-first surfaces once the new surface is proven.

## 2. Current known state

The first Graph Review Workbench delivered useful machinery:

- lane shell;
- run/session pickers;
- live projection panel;
- delta index / match-pair mapping;
- source-span overlays;
- evidence split inspectors;
- GET-only read behavior.

Dogfood verdict: the machinery is real, but the experience is not yet useful enough because it is still metadata-first. The next roadmap must pivot toward projected prose and authoring.

## 3. Dependency map

```text
R0 visual walkthrough
  → R1 mode/state information architecture
  → R2 gold projection endpoint
  → R3 two-lane projected review
      → R4 game-facing node and relationship cards
      → R5 existing-object resolver contract
          → R6 authoring primitives
              → R7 two-phase fixture write
                  → R8 per-seed LLM assist
                  → R9 whole-document reflow
                  → R10 authoring event log
                      → R11 remove/hide old surfaces
```

R4 and R5 may proceed in parallel after R3 if the projection payload supports game-object affordances and linked-object refs.

## 4. Milestones

## R0 — Low-fidelity visual walkthrough

**Purpose:** Avoid repeating the prior mistake of shipping metadata panels without validating the human object of attention.

**Scope:**

- sketch two-lane prose-with-pills review;
- sketch collapsed right rail;
- sketch node hover with game-facing content;
- sketch relationship card;
- sketch author mode text selection;
- sketch staging tray;
- sketch lane header state.

**Acceptance:**

The visual walkthrough proves that the default surface is readable prose, not metadata tables, and that authoring state is legible.

**Non-goals:**

- no backend;
- no component polish;
- no new data model beyond visible state decisions.

## R1 — Mode and state information architecture

**Purpose:** Make review/edit/staging state explicit before adding write behavior.

**Scope:**

- define lane states: `gold_fixture`, `live_run`, `gold_draft`, `seeded_gold_draft`, `blank_authoring_draft`, `reference_variant`;
- define lane mutability: `read_only` vs. `editable`;
- define interaction modes: `inspect`, `select_span`, `draw_edge`, `review_proposals`, `evidence_debug`;
- define unsaved-change and staging counts;
- make right rail collapsed by default.

**Likely files:**

```text
apps/live-control-ui/src/planSurface/graphReviewWorkbench/
apps/live-control-ui/src/planSurface/graphProjectionReader/
apps/live-control-ui/src/api/types.ts
```

**Acceptance:**

A user can always tell which lane is editable, what source each lane represents, and whether changes are staged or accepted.

## R2 — Gold projection endpoint

**Purpose:** Give gold the same prose-with-pills projection treatment as live runs.

**Scope:**

- add backend endpoint for gold fixture projection;
- render the gold fixture’s own normalized recap copy;
- bulk-resolve gold evidence refs;
- construct node and relationship views;
- anchor mentions via text-snippet matching inside the gold document;
- avoid assuming shared line numbers across gold/live lanes.

**Likely files:**

```text
apps/live_control_server/routes/graph_preview.py
apps/live_control_server/services/graph_gold_review.py
src/graph_memory/source_span.py
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/api/types.ts
```

**Acceptance:**

A gold fixture can render as projected markdown with pills in a lane without using live-run markdown as its coordinate system.

## R3 — Two-lane projected review

**Purpose:** Replace metadata-first comparison with visual prose comparison.

**Scope:**

- place gold projection and live projection in the existing two-lane shell;
- consume existing delta index / match pairs for cross-lane highlighting;
- show matched, missing, and extra objects inline;
- keep scorecard as a thin summary strip;
- keep evidence/debug behind drill-in.

**Likely files:**

```text
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewTwoLaneShell.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLiveProjectionPanel.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewReferenceLanePanel.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewDeltaUtils.ts
apps/live-control-ui/src/planSurface/graphProjectionReader/
```

**Acceptance:**

Open a real session with gold in one lane and a live run in the other. Hover a matched node in either lane and see its counterpart highlight. Missing/extra objects are visible without leaving the prose view.

## R4 — Game-facing node and relationship cards

**Purpose:** Make graph objects useful to the GM by surfacing game artifacts and relationships first.

**Scope:**

- replace metadata-first hover content with game-facing node cards;
- surface available statblocks, encounter notes, NPC dossiers, location dossiers, item cards, quests/threads, and related threats;
- add relationship chips and relationship cards;
- move evidence, score, extractor, and raw IDs into Evidence / Debug.

**Backend need:**

A game-object enrichment adapter that maps node/link refs to available campaign surfaces.

**Acceptance:**

Hovering a threat such as Tripod Null-Calf offers useful table-facing actions, such as opening a statblock or encounter note if they exist, before showing evidence/debug details.

## R5 — Existing-object resolver contract

**Purpose:** Prevent gold authoring from producing isolated session-local duplicates when an existing campaign object already exists.

**Scope:**

- define resolver request shape: selected text, declared type, label, source context, campaign/session, current draft graph;
- define resolver response shape: candidate existing objects, confidence/explanation, create-new option, manual search fallback;
- expose resolver to author mode and LLM proposal staging;
- keep identity semantics in backend graph/corpus layer, not UI.

**Likely files:**

```text
src/graph_memory/identity/
src/graph_memory/projection/
apps/live_control_server/services/
apps/live_control_server/routes/graph_preview.py
apps/live-control-ui/src/api/types.ts
```

**Acceptance:**

Selecting a phrase that corresponds to an existing object gives the user link-existing options as well as create-new.

## R6 — Authoring primitives

**Purpose:** Make gold authoring possible without hand-writing JSON.

**Scope:**

- start blank or start from run;
- select span → declare node;
- click node/span → draw edge;
- edit label/type/predicate;
- link node to existing object using R5;
- maintain client-side draft graph state;
- keep staged proposals separate from accepted graph objects.

**Acceptance:**

The user can create a node and an edge from rendered prose and see them as committed draft pills before saving.

## R7 — Two-phase gold fixture write

**Purpose:** Safely persist authored gold data.

**Scope:**

- implement `prepare_graph_gold_authoring_write`;
- implement `commit_graph_gold_authoring_write`;
- compute diff and confirm token from target path, new content, and current file-state token;
- reject stale-file conflicts;
- batch saves rather than writing each edit individually;
- emit candidate-graph-gold-shaped output.

**Precedent:**

Mirror the Party Registry write path rather than inventing a new write safety pattern.

**Acceptance:**

Save shows a human-readable diff and writes only after confirmation. Stale target files produce a recoverable conflict, not a silent overwrite.

## R8 — Per-seed LLM assist

**Purpose:** Let the GM seed one judgment and ask the model to propose nearby graph additions.

**Scope:**

- add structured-output action `graph_gold_authoring_seed_expand`;
- input current seed, local context window, existing accepted graph, and linked existing objects;
- output proposed nodes, edges, attributes, and existing-object links;
- land output in staging tray only;
- handle refusal/incomplete/error visibly.

**Acceptance:**

After declaring one node, the user can trigger LLM assist, accept one proposal, reject one proposal, and see only accepted items enter the draft graph.

## R9 — Whole-document reflow

**Purpose:** Let the model propose a fuller graph around accepted human anchors.

**Scope:**

- add structured-output action `graph_gold_authoring_document_reflow`;
- use accepted human-authored nodes/edges as fixed anchors;
- propose additional nodes, edges, attributes, and existing links;
- never overwrite accepted labels directly;
- route all output to staging tray.

**Acceptance:**

The model proposes a fuller document-level graph constrained by accepted human labels, without mutating accepted graph objects.

## R10 — Minimal authoring event log

**Purpose:** Preserve human-vs-LLM decision data now; defer analysis UI.

**Scope:**

- append JSONL event records for manual creation, LLM proposals, accept/reject/edit decisions, and final accepted values;
- store locally / git-ignored according to corpus and LLM-payload discipline;
- do not build authoring-lessons analytics yet.

**Acceptance:**

Accepted and rejected proposal decisions are preserved in an append-only log, including rejected proposal payloads.

## R11 — Remove or hide old surfaces

**Purpose:** Make the new workbench the only normal destination once it proves itself.

**Scope:**

- remove or hide old Graph Preview, Graph Gold Review table view, and Vocabulary Review entries;
- move useful diagnostic panels behind explicit drill-ins inside the new workbench;
- no backward-compatibility ceremony is required for a single-user internal product.

**Acceptance:**

The normal toolbox exposes one Graph Review + Gold Authoring Workbench, not several competing graph review destinations.

## 5. Implementation guardrails

- The source prose remains the visual focus.
- The right rail is collapsed by default.
- Game utility appears before graph metadata.
- Evidence/debug details are explicit drill-ins.
- Review lanes stay read-only unless explicitly toggled into author mode.
- LLM proposals never enter the document before accept/edit-accept.
- Existing-object linking is backend-assisted; the UI does not invent identity merge.
- Gold writes use two-phase prepare/commit.
- Authoring event logs stay local / git-ignored.
- Structured extraction is mandatory for LLM assist.
- Old surfaces may be removed once replacement parity exists.

## 6. Suggested first implementation slice

The first useful implementation slice should be:

```text
R0 + R1 + R2 + a narrow R3 review path
```

That slice should deliver:

- visual confirmation of the intended magical UX;
- explicit lane/mode state;
- gold projection endpoint;
- two-lane gold-vs-live projected prose review;
- cross-lane hover highlighting;
- metrics demoted to secondary summary.

It should not attempt authoring yet.

## 7. Suggested second implementation slice

The second slice should be:

```text
R4 + R5
```

That slice should deliver:

- game-facing node cards;
- relationship cards;
- available artifact surfaces such as statblocks and encounter notes;
- existing-object resolver contract.

This is the key bridge from “projection viewer” to “useful GM workbench.”

## 8. Suggested third implementation slice

The third slice should be:

```text
R6 + R7 + R10
```

That slice should deliver:

- manual span-to-node authoring;
- manual edge drawing;
- batched two-phase save;
- minimal authoring event logging.

This proves authoring without LLM uncertainty.

## 9. Suggested fourth implementation slice

The fourth slice should be:

```text
R8 + R9
```

That slice should add LLM assist only after the projection, resolver, draft state, write path, and event logging are stable.

## 10. Verification matrix

| Capability | Verification |
|---|---|
| Gold projection | Gold fixture renders as prose-with-pills from its own markdown copy. |
| Two-lane review | Gold and live lanes render side by side and cross-highlight matched pills. |
| Metadata demotion | Evidence and scores require explicit drill-in. |
| Game utility | Threat node can surface statblock/encounter affordances if available. |
| Existing linking | Authoring can link a span/node to an existing corpus/graph object. |
| Manual authoring | Span-to-node and node-to-node edge authoring work without JSON editing. |
| Safe write | Save uses prepare/diff/confirm/commit and rejects stale target files. |
| Proposal staging | LLM proposals are accepted/rejected/edited before entering the document. |
| Event log | Accept and reject decisions are preserved separately from the gold fixture. |
| Surface simplification | Old graph review tools are removed or hidden after replacement parity. |

## 11. Risks

### 11.1 Gold projection anchoring drift

Gold and live recap copies may differ. Do not share line coordinates between lanes. Anchor each lane internally with text/snippet matching.

### 11.2 Metadata creep

The existing tool already drifted into metadata-first panels. Every new card should pass the question: “Does this help the GM use the game object before it helps the developer debug extraction?”

### 11.3 Session-local gold islands

Manual authoring can accidentally create duplicate local nodes. R5 existing-object linking is required before serious authoring dogfood.

### 11.4 Premature LLM assist

LLM assist is seductive but should not land before manual authoring and safe writes are stable.

### 11.5 Event-log overreach

Keep event logging now; defer mining/analytics UI.

## 12. Done definition for the roadmap

The roadmap is complete when the GM can:

1. compare gold and live graph readings as projected prose;
2. inspect game-useful node and relationship cards;
3. author gold nodes and edges directly from text;
4. link authored nodes to existing campaign objects;
5. use LLM assist through a staging tray;
6. save safely to candidate-graph-gold-shaped fixtures;
7. rely on one graph review/authoring destination instead of multiple table-first tools.
