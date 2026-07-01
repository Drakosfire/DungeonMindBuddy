# HANDOFF — Prime Design: Graph Memory extraction taxonomy, passes, and consolidation

**Created:** 2026-06-30
**Repo:** `Drakosfire/DungeonMindBuddy`
**Target base branch:** `main` (already merged — see §1)
**Suggested next branch:** `codex/prime-design-graph-memory-extraction-taxonomy` (research/design) or a narrow `graph-memory/*` implementation branch once a direction is picked
**Mode:** Prime Design — architecture/taxonomy decision + narrow follow-up handoffs. Some of this can be implemented directly; the highest-leverage parts are design decisions that should be made deliberately, not pattern-matched by a mechanical subagent.
**From:** the dogfooding agent (manual review + UI iteration on the vocabulary ablation experiment)
**To:** the next Prime Design agent picking up Graph Memory

---

## 0. Copyable pickup prompt

```markdown
You are the next-phase Prime Design agent for DungeonMindBuddy's Graph Memory workstream.

Read first (in this order):

1. This file: `Docs/Plans/HANDOFF-prime-design-graph-memory-extraction-taxonomy.md`
2. `Docs/Reports/GRAPH-MEMORY-VOCABULARY-ABLATION-DOGFOOD-MANUAL-REVIEW.md` — the full manual-review writeup this handoff summarizes (sections 6-13 are the load-bearing ones)
3. `Docs/Design/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md` and `Docs/Design/GRAPH-MEMORY-PROJECT-LAYOUT.md` — the durable architecture boundary this workstream must respect
4. `Docs/Experiments/GRAPH-MEMORY-WORKSTREAM-ANCHOR.md` — a parallel/prior re-anchor. **Note the branch mismatch**: it names `experiment/ontology-taxonomy-ladder` and Session 22/23 category-pipeline work; the vocabulary-ablation work in this handoff landed on `main` via `dogfood/vocabulary-ablation-c2s23-mireward`. Reconcile these two anchors — do not silently pick one and ignore the other.
5. `Backlog.md` — search for `## [DOING] Graph memory vocabulary ablation` — the living tracker with the latest dated observations (2026-06-30 dogfood pass).

Mission: decide the next structural shape of graph-memory extraction — node taxonomy expansion vs. dedicated extraction passes vs. a consolidation/type-arbitration layer — and produce a narrow implementation handoff for the first slice. Do not just keep adding vocabulary text to the existing prompts; the manual-review report and the backlog both conclude that several failures are architectural, not prompt-local.

This is not a green light to touch corpus canon, delete fixtures, or change the union-supergraph model contract without reading `GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md` first.
```

---

## 1. Executive summary — what this project is and where it stands

DungeonMindBuddy is a GM-support tool for a long-running D&D campaign (Eldyrwild/Longmont). One active workstream, **Graph Memory**, is building a pipeline that ingests session recaps and worldbuilding documents, extracts a knowledge graph (nodes = people/places/factions/objects/threads, edges = relationships), reconciles that into a durable **union supergraph** (campaign + worldbuilding, one graph), and projects scoped views of it — most visibly as clickable entity "pills" inside rendered session recaps in the Command Board (`/plan` surface).

The immediate sub-workstream that produced this handoff is **contextual vocabulary ablation**: testing whether injecting a compiled "known names/types/aliases" vocabulary packet into the LLM extraction prompts improves graph quality versus a no-vocabulary baseline. That question is now reasonably well answered (§3). Answering it required building real tooling (a manual-review UI, §5) and produced a second, more important layer of findings about the **extraction taxonomy itself** (§4) that is now the live open question for Prime Design.

**Bottom line for the next agent:** vocabulary is a real but secondary lever. The bigger lever is deciding how many extraction passes exist and what node/edge types they own. That decision has not been made. This handoff exists to hand you the evidence needed to make it.

---

## 2. How we got here (chronology, for orientation only)

1. Contextual vocabulary layer designed and built (`Docs/Design/DESIGN-contextual-vocabulary-layer.md`, `src/graph_memory/vocabulary/`) — compiles source-derived names/types/aliases/containment/do-not-merge hints into a packet, renders it into node- and edge-pass prompts.
2. Four-variant ablation harness built (`baseline`, `node_packet`, `edge_packet`, `edge_and_node_packet`) and run across two hand-authored gold beds:
   - **C1S1** — Campaign 1 Session 1 recap ("Stonebridge and Glowkindle Rats"), gold at `evals/graph_memory_layer/examples/session_1_candidate_graph_gold/`.
   - **Mirathorn** — a worldbuilding document (`corpus/.../Cities and Towns/Mirathorn/The City of Mirathorn.docx` → `evals/graph_memory_layer/examples/mirathorn_city_world_doc/`), gold at `evals/graph_memory_layer/examples/mirathorn_city_candidate_graph_gold/`.
3. First ablation run appeared to show vocabulary "recovering party continuity" — **this was a bug, not a finding**: the C1S1 run had no `_party_registry.json`, so party anchors were empty for every variant. Corrected rerun (after adding `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_party_registry.json`) falsified that claim. See `Docs/Reports/GRAPH-MEMORY-VOCABULARY-ABLATION-DOGFOOD-MANUAL-REVIEW.md` §3.5. **Lesson embedded in process now**: any session-recap ablation bed must have a party registry before results are trusted.
4. Aggregate recall-metric reports (`Docs/Reports/GRAPH-MEMORY-VOCABULARY-ABLATION-DOGFOOD-EXPANDED-BEDS*.md`) were judged **insufficient** by the operator — they compress real graph behavior into counts and hid the actual signal. This triggered building a manual, qualitative review process and a UI for it (§5).
5. Manual review of baseline vs. `edge_and_node_packet` candidate graphs, pass-by-pass, produced the bulk of the durable findings in this handoff (§3, §4).
6. A first slice of the review UI ("Vocabulary Review" tool in the Plan surface) shipped and was iteratively refined based on direct operator feedback (side-by-side layout, inline pill detail, edge↔node click navigation). This UI is now a reusable diagnostic asset for the next round of experiments (§5).
7. Everything above landed on `main` (fast-forward merge from `dogfood/vocabulary-ablation-c2s23-mireward`, tip commit `8b59997`) as of 2026-06-30.

---

## 3. What the vocabulary-ablation question answered

Full detail: `Docs/Reports/GRAPH-MEMORY-VOCABULARY-ABLATION-DOGFOOD-MANUAL-REVIEW.md` (§3, §3.5, §13 are the verdict sections).

**Verdict: contextual vocabulary is directionally useful, not ready to promote as a runtime default.**

It helps when the task is:
- recognizing source-relevant names the baseline omitted (present-set recall, e.g. 7/7 vs 6/7 on C1S1);
- stabilizing obvious spatial/location containment (Mirathorn `located_in`/`contains` hierarchy improved sharply);
- nudging the edge pass toward more concrete relationship predicates.

It hurts or is neutral when the task is:
- preserving institutional structure — Mirathorn's council/leadership got *worse* with vocabulary, flattening `Elara Swiftwind leads Mirathorn City Council` into `Elara Swiftwind leads Mirathorn` and putting council members directly under the city node instead of the council;
- keeping species/resource/product nodes at sane granularity (vocabulary made Mirathorn's fauna/product object-explosion *worse*, not better);
- avoiding same-label cross-class duplication (`Stone Bridge` as place+faction+object; `The River's Edge Pub` as place+organization+object) — present in both baseline and vocabulary-assisted, unaffected by vocabulary either way;
- recovering party continuity — this is a **deterministic party-registry problem** (`_party_registry.json` + `merge_party_anchor_nodes`/`merge_party_collective` in `src/graph_memory/party_context.py`, `src/graph_memory/session_graph_context.py`), not something vocabulary should be expected to fix. Once the registry exists, baseline already gets party anchors right;
- edge recall generally — stuck around ~29% on C1S1 regardless of vocabulary condition.

**Practical implication:** do not spend more effort tuning the vocabulary packet as the primary lever. It is a secondary optimization. The primary lever is §4.

---

## 4. What the deeper problem is: extraction taxonomy and passes

This is the part of the manual review (§6–§10) and the 2026-06-30 UI-based pass-level dogfood (see Backlog entry) that matters most for what to build next.

### 4.1 Current extraction pass shape

Node passes (`src/graph_memory/extraction/category_candidate_graph_extractor.py`, prompts referenced in `Docs/Reports/.../MANUAL-REVIEW.md` §6.1):

| Pass | Scope | Known pressure |
|---|---|---|
| `actor_pass` | named non-party NPCs, characters, creatures. **Explicitly excludes player characters** (those come from party anchors) | Monsters/adversaries are lumped in as the same `character` node type as NPCs — no distinct type |
| `location_pass` | regions, towns, cities, roads, sublocations | Same-label collisions with object/collective passes for the same real-world noun (a tavern is both a place and, per collective_pass, an "organization") |
| `collective_pass` | factions, councils, guards, mercenary groups, organizations, **and parties** | Overbroad — institutions (city council) compete with place nodes and individual leader nodes; establishments get duplicated as organizations |
| `object_pass` | notable items, devices, artifacts | Explodes into commodity/product lists on worldbuilding docs (Mirathorn: `Luminox Sheep wool`, `Float Goat milk`, `Bioluminescent Dye`, etc. as separate object nodes) |
| `thread_pass` | mysteries, clues, warnings, events, unresolved phenomena | **Validated as good** in the 2026-06-30 dogfood (the "shattered mage's tower" mystery landed correctly here) — but also becomes a dumping ground for event summaries that should be their own type |

Plus a `beat_pass` (source-local scene/event scaffold, "not the focus of this review" but architecturally important — see §4.3) and an `edge_pass` (single pass handling containment, authority/command, threat, knowledge/report, and composition/participation relationship families simultaneously — assessed as overloaded).

### 4.2 Concrete gaps surfaced by gold comparison + the 2026-06-30 UI dogfood

From manually walking the C1S1 gold graph against extracted output using the new Manual Review UI (see Backlog entry "2026-06-30 pass-level dogfood"):

- **Player-character actions/details are barely captured.** PCs are deliberately excluded from `actor_pass` (by design — they come from party anchors), but nothing currently captures rich PC *action* detail from the recap prose. This is a real product gap: PCs should carry the densest detail of any actor in the graph, and today they carry almost none beyond the deterministic `member_of` edge.
- **Monsters/adversaries have no distinct node type.** Gold treats them as conceptually separate from NPCs/PCs; the pipeline currently emits them as `character` nodes, same as everyone else.
- **Gold contains node shapes the taxonomy has no home for:**
  - a **job/quest/task** node (the rat-clearing job) — not a thread, not a location, not an object;
  - a **combat/encounter** node, kept **separate** from the job/quest it's tied to in gold (i.e. "accepted the rat job" and "fought the rats" are two different nodes with an edge between them, not one blob);
  - an ambiguous **infrastructure/architecture** node (the giant statue foot; the stone bridge treated as a thing-in-itself, not just an edge target for a `located_in` relationship);
  - the mage's-tower mystery, which **does** map cleanly onto the existing `thread_pass` — this one is not a gap.
- **All missing gold edges were agreed-with on manual review** (no disagreement that they should exist) — which is a useful signal: the gaps look patterned, not random, and likely cluster around unhandled node types (an edge extractor can't emit an edge to a node type the pipeline never produces). The idea of "beats" (discrete scene/event units, from the existing but underused `beat_pass`) as the organizing concept tying these missing edges together is raised but **not yet investigated**.

### 4.3 The open decision Prime Design needs to make

The manual-review report (§10) already sketches a target shape; the operator has explicitly flagged the type-expansion-vs-passes tradeoff as **undecided**:

> "Am I expanding nodes too much? It feels like if we had nodes to put some of these missing things in, or maybe we can find specific passes to capture these." — operator, 2026-06-30 dogfood notes

Two non-exclusive directions, both partially motivated by evidence:

**A. Node-type taxonomy expansion** — add first-class node types: `adversary`/`monster`, `job`/`quest`, `encounter`/`combat`, `infrastructure`/`landmark`. Keeps pass count stable, raises the type vocabulary each pass must reason about.

**B. Dedicated extraction passes** — the manual review's own recommendation (§9, §10) is a combat/encounter/job pass, a governance/institution pass (motivated independently by Mirathorn), and an ecology/resource pass (also Mirathorn), on top of a **party/roster attachment pass** (already partially solved deterministically, not by an LLM pass — see §3) and a **type-arbitration/consolidation stage** that runs after all extraction passes to resolve cross-class duplicates.

The 2026-06-30 dogfood notes lean toward **passes over unbounded type sprawl**, and specifically flag a **combat pass** as "the strongest single candidate raised" — but this is explicitly **not a final decision**, just the direction of lean going into this handoff. Prime Design should treat this as the first thing to resolve, informed by:

- `Docs/Reports/GRAPH-MEMORY-VOCABULARY-ABLATION-DOGFOOD-MANUAL-REVIEW.md` §9 (full architectural-gap analysis: party/roster, entity type arbitration, institution/governance, ecology/resource, event/encounter/job — each with a proposed pass shape);
- §10 of the same report ("Proposed Next Design Shape") — a 6-stage pipeline sketch (vocabulary compile+review gate → core node passes → specialized extraction passes → relationship-family passes → type arbitration/identity reconciliation → projection review UI) that has **not been implemented**, only proposed;
- the consolidation-layer gap specifically. **Correction to the manual review's framing:** a type-arbitration seam already exists — `src/graph_memory/identity_resolution.py::reconcile_cross_class_label_collisions` (plus `should_merge_cross_class_label_collision`, `_CROSS_CLASS_TYPE_PRIORITY`) — but it is deliberately narrow: it only auto-merges an exact-label collision when the two classes are `place`+`collective`; every other cross-class collision (place+object, place+object+collective, actor+object, etc.) is intentionally **blocked** (kept as separate nodes, surfaced in a `blocked` diagnostics list) rather than resolved, because the code comment is explicit that false-merges of distinct identities are worse than fail-to-merge. This is *why* `Stone Bridge`-as-place/faction/object and `The River's Edge Pub`-as-place/organization/object persist identically with or without vocabulary — they hit the `blocked` path, not a missing feature. The real next step is **extending this seam's merge-policy table** (more approved class-pair combinations, informed by node descriptions/evidence/corpus refs, not just type-class priority) rather than building type arbitration from zero. Verify current `blocked` diagnostics output on the C1S1/Mirathorn beds before designing further — it should already enumerate most of the duplication pairs cited in the manual review.

### 4.4 A further idea not yet designed: dynamic cross-session vocabulary enrichment

Raised by the operator, not yet explored: when ingesting session N+1, the pipeline will need to load some subset of nodes (and possibly edges) from session N / the growing union supergraph as context. Rather than one static vocabulary list for every pass, bias each pass's injected vocabulary toward nodes *likely to carry edges relevant to that pass's topic* — e.g. a future combat/encounter pass would get combat-relevant nodes (adversaries, prior encounter outcomes) preferentially, not the full undifferentiated node list. This composes with whichever taxonomy/pass decision is made in §4.3 and should probably be designed together with it rather than bolted on after.

---

## 5. Tooling built during this workstream (reusable for whatever comes next)

### 5.1 Manual Review UI — "Vocabulary Review" Plan-surface tool

**Purpose:** side-by-side, pass-level comparison of baseline vs. vocabulary-assisted (or any two variants) candidate graphs, with the exact prompt text shown alongside extracted output. Built because aggregate metrics hid real signal; this is the tool that produced §4's findings.

**Frontend:** `apps/live-control-ui/src/planSurface/manualReview/`
- `ManualReviewModule.tsx` — the component. Renders a full-width vocabulary-prompt panel above a 2-column baseline/assisted grid; node pills show description, labeled confidence/importance, anchor-quote evidence inline; node pills list connected edges as clickable chips, edge pills' endpoints are clickable — clicking jumps to the connected node/edge's pass and highlights it.
- `manualReviewPasses.ts` — pass IDs, labels, variant name constants.
- `ManualReviewModule.test.tsx` — covers load/switch/error states and the edge↔node navigation round trip.

**Backend:** `apps/live_control_server/services/graph_manual_review.py` (Pydantic response models + artifact loader), wired into `apps/live_control_server/routes/graph_preview.py` at:
- `GET /api/live/graph-preview/manual-review/beds`
- `GET /api/live/graph-preview/manual-review/beds/{bed_id}`

Reads the checked-in artifact directly — **no new LLM calls, read-only, no writes**:
`evals/graph_memory_layer/artifacts/vocabulary_ablation_dogfood/manual_review/baseline_vs_edge_and_node_manual_review.json`

**Deliberately not built yet** (flagged as v2 if the pass-level view proves useful): accept/reject/retype persistence controls (needs a write-safety design decision — this UI must not casually mutate corpus or graph state), and a third+ variant column for `node_packet`-only/`edge_packet`-only comparison.

**To view it:** run the live-control stack (`uv run uvicorn apps.live_control_server.main:app --reload` + `cd apps/live-control-ui && npm run dev`, see `apps/live-control-ui/README.md`), open `/plan`, open the Plan toolbox, select "Vocabulary Review".

### 5.2 Sibling review tool — Graph Gold Review

`apps/live-control-ui/src/planSurface/graphGoldReview/` + `apps/live_control_server/services/graph_gold_review.py` — a related but distinct tool comparing extracted graphs against hand-authored gold with scorecards, miss tables, and evidence diffs. Endpoints under the same router: `/gold-review/sessions`, `/gold-review/compare`, `/gold-review/evidence`, `/gold-review/vocabulary-ablation`. Useful for quantitative gold-recall checks; the Manual Review tool (§5.1) is for qualitative pass-level inspection. They are complementary, not redundant.

### 5.3 Ablation experiment runner

`evals/graph_memory_layer/run_vocabulary_ablation_expanded_beds_dogfood.py` — the harness that runs all four variants (`baseline`/`node_packet`/`edge_packet`/`edge_and_node_packet`) across a configurable set of beds and emits both the metric report and the manual-review artifact consumed by §5.1. This is the script to extend if the next experiment is "add a specialized pass and rerun."

### 5.4 C1S1 projection materialization + campaign picker

Separate from vocabulary ablation but built in the same window: `evals/graph_memory_layer/run_session_1_projection_dogfood.py` materializes the C1S1 (+ Mirathorn-merged) candidate graph into the same artifact shape the Command Board's recap projection consumes (`preview_union_store.json`, `projection_payload.json`, `graph_ingest_run_manifest.json`), and `apps/live-control-ui/src/planSurface/ReviewCampaignPicker.tsx` + `sessionCampaignContext.ts` let the operator explicitly pick which campaign a review surface is looking at (fixes a real bug: `session-1` collided across `longmont-c1` and `longmont-c2`). This makes C1S1 viewable in the same recap-pill UI as live campaign sessions — useful for eyeballing how a new taxonomy/pass change affects the *rendered* graph, not just the JSON.

---

## 6. Prompt hygiene issues — cheap, mechanical, safe to delegate

These are called out in the manual review (§7) as real but narrow — the kind of fix that is safe to hand to a mechanical/composer-tier subagent with a tight brief, **not** something that needs Prime Design judgment:

1. **Do-not-merge hints are currently unsafe.** The C1S1 dogfood packet includes probe hints like "Stone Bridge (town) vs. literal stone bridge (landmark)" that are not reliably source-derived and actively *encourage* the duplicate-entity problem they're meant to prevent. Remove from the dogfood packet; when a real compiler exists, render do-not-merge as human-readable labels+types+reasons, never opaque internal IDs.
2. **Absent-set contamination probes leak into the model-facing vocabulary.** They exist to measure hallucination risk but are currently shown in the same "Known names" list as real vocabulary — confusing for both the model and human reviewers. Must be separated: source-relevant vocabulary / background vocabulary / eval-only contamination probes (never shown to the model) / do-not-merge hints.
3. **Alias handling is too implicit.** Aliases render as untyped standalone "known names" instead of nested under their parent entity (`Stone Bridge [place] — aliases: stone bridge`).

Relevant code: `src/graph_memory/vocabulary/packet_render.py`, `src/graph_memory/vocabulary/seed_compile.py`, `src/graph_memory/vocabulary/model.py`. See `.cursor/rules/subagent-delegation.mdc` for how to brief this out safely (explicit file allowlist, verification command = rerun the ablation harness + inspect the rendered packet in the Manual Review UI, out-of-scope = don't touch the node/edge extraction prompts themselves).

---

## 7. Non-negotiables and guardrails to carry forward

From `Docs/Design/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md` and `Docs/Experiments/GRAPH-MEMORY-WORKSTREAM-ANCHOR.md` (still governing, independent of this handoff's taxonomy question):

- The **union supergraph** (`src/graph_memory/union_supergraph/`) is the durable graph-memory read model — not an eval fixture, not owned by `evals/`. Any new node type or pass output must eventually flow through this contract.
- `evals/graph_memory_layer` is proof/dogfood machinery. It does not own architecture. Durable contracts belong in `src/graph_memory/`.
- No corpus mutation, canon promotion, or approved-memory writes as part of this workstream. Two-phase preview/confirm write discipline (`src/agent/corpus_writer.py` pattern) is non-negotiable for anything that eventually touches `corpus/eldyrwild-markdown/`.
- Party membership is a **deterministic** context problem (`_party_registry.json` + `src/graph_memory/party_context.py`), not an LLM extraction problem. Do not let a future pass re-litigate this by trying to have an LLM pass "discover" the party roster.
- Any new session-recap ablation/dogfood bed **must** have a `_party_registry.json` for its campaign before results are trusted (this was the root cause of an entire invalidated first report — see §2.3).
- Respect `Docs/Anchors/CORPUS-ANCHOR.md` for where canonical recap/worldbuilding markdown actually lives; regenerate via `PYTHONPATH=. python scripts/build_corpus_index.py` if corpus structure changes.

---

## 8. Reconciling the two workstream anchors (do this early)

`Docs/Experiments/GRAPH-MEMORY-WORKSTREAM-ANCHOR.md` (dated 2026-06-27/28, branch `experiment/ontology-taxonomy-ladder`) describes a **different concrete proof target**: Session 23 Caelynn resolving into global-node graph navigation via the `category_graph_model_study.py` 7-pass pipeline (5 category node passes + beat + edge, proven ~0.80–0.88 node recall on Session 22). That work and this vocabulary-ablation work share the same underlying node-pass taxonomy (`actor`/`location`/`collective`/`object`/`thread` + `beat` + `edge`) but ran as parallel efforts on different branches, with different bed sets (Session 22/23 live-campaign vs. C1S1/Mirathorn hand-authored gold) and different proof criteria (global-node navigation vs. vocabulary-assisted extraction quality).

**Before making the taxonomy/pass decision in §4.3, check:**
- whether `experiment/ontology-taxonomy-ladder` has moved since 2026-06-28 and whether `category_graph_model_study.py`'s pass set has already changed;
- whether the "next PR sequence" pointer in that anchor (package cleanup → typed union-supergraph models → evidence/source-domain contracts → projection contracts → `/plan` adapter seam) has advanced, since new extraction passes should probably slot into whatever the current contract shape is, not the 2026-06-27 snapshot described there;
- whether it makes sense to update `GRAPH-MEMORY-WORKSTREAM-ANCHOR.md` itself once you've reconciled it with this handoff, so there is one current anchor instead of two.

---

## 9. Suggested first tasks for the next agent

1. Read §8 first and reconcile the two anchors — do not start designing a new pass in ignorance of `category_graph_model_study.py`'s current state.
2. Read `Docs/Reports/GRAPH-MEMORY-VOCABULARY-ABLATION-DOGFOOD-MANUAL-REVIEW.md` §9 and §10 in full — they already contain a proposed 6-stage pipeline shape and per-gap pass sketches; your job is to critique/refine/decide, not originate from scratch.
3. Decide the §4.3 question (taxonomy expansion vs. dedicated passes vs. both) for at least the highest-signal gap: combat/encounter (flagged as the strongest single candidate). Write the decision down with falsification criteria — what would prove a combat pass is/isn't worth it.
4. Scope extending the existing `reconcile_cross_class_label_collisions` merge-policy table (§4.3 correction) as a candidate first slice **regardless** of the taxonomy decision — it fixes an existing, vocabulary-independent bug (cross-class duplication currently routed to `blocked` rather than resolved) and is likely to be needed under either taxonomy path. Start by dumping the `blocked` diagnostics for the C1S1/Mirathorn beds to confirm they match the duplication pairs cited in the manual review before designing new policy rules.
5. Delegate the prompt-hygiene cleanup (§6) as a narrow, separately-briefed mechanical fix — do not let it block or blend with the taxonomy decision.
6. If a new pass is prototyped, rerun `evals/graph_memory_layer/run_vocabulary_ablation_expanded_beds_dogfood.py` (extended with the new pass) and inspect results in the Manual Review UI (§5.1) before trusting recall numbers alone — that is the whole lesson of this workstream.
7. Write a narrow implementation handoff for the first accepted slice, following this repo's `HANDOFF-pr<N>-<slug>.md` convention if it will go through the external-agent-pr-loop (see `AGENTS.md`), or a plain `HANDOFF-<slug>.md` if you'll implement it yourself/in-session.

---

## 10. Reference index (all paths repo-relative)

**Reports (read in this order for full context):**
- `Docs/Reports/GRAPH-MEMORY-VOCABULARY-ABLATION-DOGFOOD-MANUAL-REVIEW.md` — the primary qualitative writeup, supersedes the invalid first-run findings in its own §3.5
- `Docs/Reports/GRAPH-MEMORY-VOCABULARY-ABLATION-PROMPT-REVIEW.md` — prompt-hygiene detail feeding into §6 here
- `Docs/Reports/GRAPH-MEMORY-VOCABULARY-ABLATION-DOGFOOD-EXPANDED-BEDS.md` / `-MIRATHORN.md` — the aggregate-metric reports judged insufficient on their own
- `Docs/Reports/GRAPH-MEMORY-VOCABULARY-ABLATION-DOGFOOD-C2S23-MIREWARD.md` — earlier, narrower ablation pass (live campaign bed, not gold-backed)
- `Docs/Reports/GRAPH-MEMORY-SESSION-1-VOCABULARY-ABLATION-PROJECTION-DOGFOOD-RUN.md` — the C1S1 projection-materialization dogfood (§5.4 tooling)

**Design/architecture:**
- `Docs/Design/DESIGN-contextual-vocabulary-layer.md` — original vocabulary-layer design
- `Docs/Design/GRAPH-MEMORY-CONTEXTUAL-VOCABULARY-ROADMAP.md`
- `Docs/Design/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md` — governing architecture, do not violate
- `Docs/Design/GRAPH-MEMORY-PROJECT-LAYOUT.md` — path/ownership boundaries
- `Docs/Design/GRAPH-MEMORY-MULTI-PASS-EXTRACTION-CONTRACT.md` — prior broader 9-pass design sketch, referenced but not the graduated path
- `Docs/Experiments/GRAPH-MEMORY-WORKSTREAM-ANCHOR.md` — the other anchor to reconcile (§8)

**Backlog (living, dated entries):**
- `Backlog.md` → search `## [DOING] Graph memory vocabulary ablation` — most current single source of "what's still open"

**Gold fixtures:**
- `evals/graph_memory_layer/examples/session_1_candidate_graph_gold/`
- `evals/graph_memory_layer/examples/mirathorn_city_candidate_graph_gold/`
- `evals/graph_memory_layer/examples/session_1_recap_ingest/`, `mirathorn_city_world_doc/`

**Party registry (deterministic, not vocabulary):**
- `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_party_registry.json`
- `src/graph_memory/party_context.py`, `src/graph_memory/session_graph_context.py`

**Extraction code:**
- `src/graph_memory/extraction/category_candidate_graph_extractor.py` (node/edge pass prompts + orchestration)
- `src/graph_memory/vocabulary/` (packet compile/render/artifact)
- `src/graph_memory/identity_resolution.py` — existing (narrow) cross-class reconciliation: `reconcile_cross_class_label_collisions`, `should_merge_cross_class_label_collision`, `_CROSS_CLASS_TYPE_PRIORITY`. Only `place`+`collective` exact-label collisions auto-merge today; everything else routes to `blocked` diagnostics. This is the seam to extend, not replace.
- `evals/graph_memory_layer/category_graph_model_study.py`, `run_category_graph_model_study.py` (the parallel 7-pass pipeline referenced in §8)

**Review UIs:**
- `apps/live-control-ui/src/planSurface/manualReview/` + `apps/live_control_server/services/graph_manual_review.py` (§5.1)
- `apps/live-control-ui/src/planSurface/graphGoldReview/` + `apps/live_control_server/services/graph_gold_review.py` (§5.2)
- Router: `apps/live_control_server/routes/graph_preview.py` (prefix `/api/live/graph-preview`)

**Corpus anchor:**
- `Docs/Anchors/CORPUS-ANCHOR.md` / `corpus/CORPUS-INDEX.json` — regenerate via `PYTHONPATH=. python scripts/build_corpus_index.py`

**Current `main` tip at handoff time:** `8b59997` (merged from `dogfood/vocabulary-ablation-c2s23-mireward`, itself descended from `1495309`, `6915f60`, `1225917`, `a7a4790`).
