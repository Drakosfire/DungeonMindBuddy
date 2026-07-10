# Graph Memory Workstream Anchor



Architecture roadmap: `Docs/Design/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md` is the current post-PR196 roadmap. It records that Graph Memory is now organized around a reusable campaign/worldbuilding union supergraph in `src/graph_memory`; evals remain proof machinery, projections are lenses, and runtime apps consume graph-memory contracts rather than owning graph semantics.

Layout boundary: `Docs/Design/GRAPH-MEMORY-PROJECT-LAYOUT.md` records that reusable graph-memory contracts live in `src/graph_memory`, deterministic contract fixtures live in `tests/fixtures/graph_memory`, and `evals/graph_memory_layer` remains evaluation/dogfood territory.

**Corpus anchor:** `Docs/Anchors/CORPUS-ANCHOR.md` — repo-relative hierarchy of Campaign 1/2 session recaps and Elderwyld worldbuilding markdown under `corpus/eldyrwild-markdown/`. Regenerate index: `PYTHONPATH=. python scripts/build_corpus_index.py` → `corpus/CORPUS-INDEX.json`.

Date: 2026-06-27
Status: active current anchor — post-union-supergraph model contract v0 checkpoint
Workstream: Graph Memory / Union Supergraph / Recap Projection
Branch: `experiment/ontology-taxonomy-ladder`
Current committed head at re-anchor: `eb06491` — `graph-memory: add union supergraph model contract v0 (#199)`

## Purpose

This file is the short operational anchor for future agents. It summarizes where the Graph Memory workstream currently stands, what the latest dogfood changed, and what must exist before the project can execute the next meaningful vertical slice.

The longer historical ladder remains in:

`Docs/Experiments/EXPERIMENT-Ontology-Taxonomy-Ladder.md`

The current union-supergraph design target is in:

`Docs/Design/GRAPH-MEMORY-UNION-SUPERGRAPH-PROJECTION.md`

The narrow checklist for the model-contract implementation spike is archived at:

`Docs/Plans/archive/2026-06-28/handoffs/HANDOFF-pr194-union-supergraph-projection-spike-checklist.md`

This file should be updated whenever the workstream meaningfully re-anchors.

## Current State (2026-06-28 cleanup re-anchor)

**Product direction:** graph-first recap projection over a union supergraph. Recap pills resolve to global nodes; session focus is an overlay, not a separate graph.

**What one-click ingest runs today:**

```text
raw recap → stage/apply/normalize → breadcrumb + session memory (legacy) → preview_candidate_graph_extractor (single gpt-5-mini call, ~12-node cap) → preview union store → projection payload
```

**What one-click ingest should run next:**

```text
raw recap → stage/apply/normalize → source spans → category-decomposed extraction (7 LLM passes) → preview union → projection
```

Category extraction = `evals/graph_memory_layer/category_graph_model_study.py` (`run_category_pipeline`): **actor, location, collective, object, thread** node passes, then **beat** and **edge** passes, deterministic assembly. Proven in `anchor_quote_n3` (n=3, `gpt-5.4-mini`, Session 22 gold node recall ~0.80–0.88). **Not** the compact single-pass `preview_candidate_graph_extractor`.

Graph path must **not** require breadcrumb/frontmatter/session-memory steps. See `Docs/Plans/HANDOFF-graph-first-recap-ingest.md`.

**Authority map:** `Docs/Design/GRAPH-MEMORY-PROJECT-LAYOUT.md` (runtime vs eval vs legacy vs generated).

**Legacy (do not confuse with graph substrate):**

- Breadcrumb ingest, frontmatter seed, session memory JSONL under `corpus/.../_breadcrumbed` and `_session_memory`
- Session 24 manual projection dogfood (projection gold fixture; `llm_extraction: false`)
- Multi-pass extraction contract + eval-only harness (broader 9-pass design reference; category study is the graduated slice)

**Known extraction gap:** runtime still uses `preview_candidate_graph_extractor` (single call, ~12-node cap). Session 23 gold has 42 nodes including Orik Tane and 7 locations. Wire `run_category_pipeline` from `category_graph_model_study.py` (proven in `anchor_quote_n3`) into `graph_preview_runner.py` — do **not** patch the compact extractor caps as the long-term fix.

**Repo cleanup (2026-06-28):** superseded fixture/prototype docs archived under `Docs/Design/archive/2026-06-28/graph-memory/` and `Docs/Reports/archive/2026-06-28/graph-memory/`. Evals README updated with fixture status labels.

## Current Re-Anchor

The workstream has crossed from **recap ingestion / selector plumbing** into **global graph projection design**.

The old question was:

```text
Can a selected recap artifact render graph-aware pills in /plan?
```

That has been answered well enough for now. Session 22 demonstrates linked recap behavior: hover an entity pill, see a node description, click the pill, and pin the node in the side panel.

The new question is:

```text
Can any recap projection resolve its pills into a shared union supergraph, so clicking Caelynn from Session 23 opens all of Caelynn across the campaign/worldbuilding graph while clearly highlighting what is anchored to Session 23?
```

Everything next should serve that question.

## Current State

The latest shipped bridge layer is:

```text
recap artifacts
→ file-backed recap artifact registry
→ campaign/session selector
→ optional graph-run selector
→ /api/live/graph-preview artifacts/runs/latest/recap resolution
→ /plan recap projection with hover/pin pills
```

The registry is locator-only. It records source recap paths, ingest run bundle paths, span/provenance paths, and optional graph run refs. It should not be treated as authoritative graph memory.

The PR #199 model-contract slice is now merged. `src/graph_memory/union_supergraph/model.py` and `src/graph_memory/union_supergraph/load.py` define the typed DTO/load seam for the file-backed union-supergraph fixture, while the validator and report continue to own graph-level policy checks.

The current projection can render linked pills if the response contains:

```text
payload.markdown with dmb-node links
payload.nodes with matching node records
```

The UI already supports:

```text
hover pill → node hover card
click pill → pinned node panel
session selector → recap/graph context switch
recap-only fallback → no graph extraction runs
```

What is missing is not more selector UI. What is missing is the producer-side graph substrate.

## Critical Correction

Do not design the next slice as a hand-authored Session 23 projection snapshot.

The user explicitly wants to move away from hand-authored proof artifacts. The current system has already proven that ingestion/projection can produce pills in the recap render. The next work should move toward the graph that those pills resolve into.

The target graph is not a session graph.

The target graph is a union view over at least:

```text
Campaign supergraph
+ Worldbuilding supergraph
= unified campaign/world graph substrate
```

Recaps, statblocks, worldbuilding docs, NPC dossiers, location notes, faction notes, item notes, session memory, and future artifact types must all be reachable through the same graph substrate.

A recap projection is a scoped lens over that graph, not the graph itself.

## Primary User Story

The primary proof-of-success story is:

```text
As GM reviewing Session 23,
when I hover a Caelynn pill,
I see the Session 23-relevant projection of the global Caelynn node.

When I click Caelynn,
I enter graph navigation on global pc_caelynn,
where I can see all known Caelynn facts, edges, and evidence across the campaign/worldbuilding graph,
with clear markers for which facts/edges are anchored to Session 23
and which come from other sessions or other corpus artifacts.

From Caelynn, I can keep following edges to adjacent nodes without being restricted to Session 23.
```

This means the Caelynn pill in Session 23 should resolve to global `pc_caelynn`, not to a Session 23-local Caelynn node.

## Current Data Reality

Known local registry reality after the bridge layer:

```text
longmont-c2/session-21:
  recap-only
  no graph refs

longmont-c2/session-22:
  recap + graph-run refs from category_graph_model_study
```

Session 23 does not yet have the required graph-backed projection state.

There may also be local/test registry residue such as `session-test`. Treat `out/registries/recap_artifacts.json` as generated local state, not source-of-truth.

## What The Current Work Proved

The current work proved:

- recap artifacts can be registered by campaign/session
- /plan can select recap sessions
- graph preview APIs can resolve by artifact/session/run locator
- recap-only fallback works when no graph run exists
- graph-aware markdown links can render as pills
- pills can show hover-card descriptions
- pills can pin nodes in the side panel
- Session 22 can demonstrate linked recap behavior from existing graph/eval artifacts

## What The Current Work Did Not Prove

The current work did not prove:

- that Session 23 can resolve Caelynn into a graph-backed global node
- that clicked nodes open an all-of-node graph view
- that graph navigation can follow edges beyond the current session
- that campaign and worldbuilding facts can coexist in one navigable graph
- that recaps, statblocks, and worldbuilding docs can all contribute evidence to the same node
- that Session 23-specific facts can be highlighted without hiding non-Session-23 graph context
- that category_graph_model_study run dirs are an acceptable long-term graph source

## New Product Loop

The intended product loop is now:

```text
1. Source artifacts enter the system.
   - recaps
   - statblocks
   - worldbuilding docs
   - NPC/location/faction/item notes
   - future artifact types

2. Ingestion/extraction produces source-grounded graph assertions.

3. Reconciliation resolves assertions into stable global nodes and edges.

4. A campaign/world union supergraph becomes the graph read substrate.

5. Session recap projection renders a scoped lens into that supergraph.

6. Pills in a recap resolve to global nodes.

7. Clicking a pill opens graph navigation on the global node.

8. The UI distinguishes session-anchored facts/edges from broader campaign/worldbuilding facts/edges.
```

The next work should move toward that loop. Do not optimize selector or run-picker behavior unless it directly supports global-node graph navigation.

## Recommended Next Design/Backend PR

Recommended next PR sequence is now owned by:

`Docs/Design/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md`

The immediate next implementation should be package cleanup, not graph model expansion:

```text
graph-memory: normalize src package import layout
```

After that, proceed through union-supergraph typed models, evidence/source-domain contracts, projection contracts, and finally the `/plan` adapter seam. Keep this anchor focused on operational context; use the roadmap for architectural sequencing.

## Immediate Implementation Shape

Prefer a file-backed graph substrate for v0, but design it as a graph store/read model, not as a session-local snapshot.

The v0 store may be JSON files, but it should already model:

```text
global nodes
stable node IDs
aliases
edges
edge predicates
evidence refs
source artifacts
source domains
session focus overlays
adjacency for navigation
```

The read model should support:

```text
open_global_node(node_id, focus_session_id?)
list_adjacent_nodes(node_id, scope=all, focus_session_id?)
project_recap_mentions(session_id) -> dmb-node links into global nodes
```

## Required Conceptual Boundaries

### Union supergraph

The navigated graph is the union of campaign and worldbuilding graph knowledge.

```text
Campaign graph:
  sessions, events, player actions, evolving relationships, unresolved threads, encounters

Worldbuilding graph:
  locations, factions, NPC dossiers, statblocks, items, cosmology, setting lore, threats
```

These should not become isolated identity silos. Caelynn, Mireward, Lysandra, Shepherd threats, factions, and locations will naturally straddle both domains.

### Source-domain metadata

Use source metadata to distinguish where a fact/edge came from, not separate stores that duplicate identity.

Example source domains:

```text
recap
statblock
worldbuilding
npc_note
location_note
faction_note
item_note
session_memory
manual_seed
future_artifact
```

### Session focus overlay

A session projection is a focus overlay over the global graph.

Session 23 should highlight Session 23-supported facts and edges, but it should not hide the rest of Caelynn.

## Non-Negotiable Blocks

Until explicitly gated in later PRs, do not implement:

- corpus mutation
- canon promotion
- approved memory writes
- Agent Interaction integration
- production retrieval changes
- automatic fact promotion
- opaque identity merging without evidence
- category_graph_model_study run dirs as the long-term graph source of truth
- session-local graph snapshots as the primary design target
- hand-authored Session 23 graph proof as the next success path

## Allowed Next Work

Allowed next work:

- extend the union-supergraph model contract into reusable evidence/source-domain modules
- decide whether typed node/edge state DTOs should replace loose `dict[str, Any]` state fields
- define source-domain and focus-session metadata
- define global node view payload
- define adjacency payload for graph navigation
- update recap graph API contracts to return global-node/adjacency data
- connect Session 23 recap pills to global nodes once producer artifacts exist
- use generated/extractor/materialized artifacts as inputs
- keep v0 file-backed and inspectable
- keep tests deterministic

## Success Bar

The next time this workstream claims progress, the success bar should be human-recognizable:

```text
Alan can select Session 23.
Alan can hover Caelynn and see a useful node description.
Alan can click Caelynn and open global pc_caelynn.
Alan can see which Caelynn facts/edges are Session 23-anchored.
Alan can also see all-of-Caelynn from other sessions/worldbuilding artifacts.
Alan can follow edges from Caelynn to adjacent nodes without being trapped in the Session 23 recap.
```

If the work only produces a session-local graph or another table that says `ready`, it is not enough.

## Current Anchor In One Sentence

We are building a shared campaign/worldbuilding union supergraph where recap projections are scoped lenses into global nodes; the next proof is Session 23 Caelynn resolving to all-of-Caelynn graph navigation with Session 23 evidence highlighted, without hand-authoring a local Session 23 graph or promoting anything to canon.
