> Status: SUPERSEDED / HISTORICAL
> Use for: Conceptual ancestor context only, especially early tiered-memory and compiled-view framing.
> Do not use for: Campaign Supergraph architecture, roadmap sequencing, Kernel/write-path contracts, Project Source authority, or current implementation handoffs.
> Current authority: Docs/Design/ARCHITECTURE-campaign-supergraph.md; Docs/Roadmaps/ROADMAP-campaign-supergraph.md; Docs/Plans/PR-TRACKER-campaign-supergraph.md
> Last sync checked: 2026-07-10

# DungeonBuddy Specification and Architectural Design
**Version:** 0.2  
**Status:** Proposed (historical — see banner above; not current architecture authority)  
**Date:** 2026-04-09  
**Audience:** Engineering agents, human implementers, architecture reviewers

---

## 1. Executive summary

DungeonBuddy is a continuity-preserving campaign memory and planning system for tabletop roleplaying games. It is not merely a chat assistant, and it is not merely a retrieval wrapper over notes. Its purpose is to maintain a durable, queryable, evolving model of a campaign world so that a Game Master can prep sessions, inspect canon, recover context, generate new material, and update the world state without re-pasting recaps or re-deriving relationships every time. [I1][R1][R2]

The central architectural claim of this spec is that DungeonBuddy should be built as a **tiered memory system with a memory controller over it**, backed by a **temporal canon graph**, and surfaced through **compiled views** such as an Index, Profiles, and Source drill-down. This preserves what was strongest in the existing DungeonMindBuddy design—human-readable table-of-contents navigation, profile-based condensation, and source-grounded detail—while addressing the deeper issue that retrieval is not one problem but several: referent resolution, scope selection, evidence assembly, temporal truth maintenance, and controlled memory evolution. [I1][R1][R2][R3]

This design leans on recent work in agentic memory, graph-based agent memory, GraphRAG, time-aware knowledge graphs, and production memory systems. The literature increasingly frames agent memory as a **write–manage–read loop**, not as a convenience layer around prompts. It emphasizes tiered storage, controlled writes, contradiction handling, temporal reasoning, graph-structured retrieval, memory evolution, and holistic evaluation that includes latency and token costs alongside answer quality. [R1][R2][R3][R4][R5][R6][R7][R8][R9]

---

## 2. Problem statement

The current DungeonMindBuddy draft correctly identifies the core tension: the agent needs enough context to stay grounded, but loading everything into the prompt is expensive and noisy. Its proposed answer is a three-tier user-facing model:

1. **Index**: always-in-context table of contents  
2. **Profiles**: loaded on demand  
3. **Source files**: loaded on demand when more detail is needed [I1]

That design is directionally correct, but it also names its own limits:

- retrieval selection remains LLM-dependent,
- profile condensation is lossy and only a pointer to detail,
- incremental updates reintroduce entity extraction,
- the location hierarchy partly duplicates the filesystem,
- and the biggest risk is spending significant time curating profiles only to rediscover that “knowing which profiles to load” is still the same hard retrieval problem. [I1]

DungeonBuddy therefore needs an architecture that treats the Index/Profile/Source pattern as a **compiled interaction model**, not as the whole retrieval system.

---

## 3. Architectural thesis

DungeonBuddy should be implemented as five layers that work together:

1. **Working context** for the active turn  
2. **Session state** for the current prep/play workflow  
3. **Semantic and episodic memory** for searchable learned state  
4. **Structured canon graph** for durable world truth and relationships  
5. **Artifact store** for source files and generated outputs [R4][R5][R6]

The Index, Profile, and Source views remain, but they become projections over deeper stores:

- the **Index** becomes a compiled manifest optimized for navigation and prompt injection,
- the **Profile** becomes a compiled dossier optimized for entity-oriented reasoning,
- the **Source** remains the irreversible artifact of record. [I1]

This avoids a category error: the user-facing navigation model is not the same thing as the underlying memory substrate.

---

## 4. Goals

### 4.1 Primary goals

DungeonBuddy must:

- preserve campaign continuity across sessions,
- provide fast grounded recall for prep and play,
- support relational reasoning across entities, places, factions, items, and events,
- maintain temporal truth and historical state,
- evolve memories rather than endlessly append them,
- preserve provenance back to source artifacts,
- support explicit human review where the system is uncertain,
- and expose failures in a debuggable way rather than hiding them inside vector rankings. [I1][R1][R2][R3]

### 4.2 Secondary goals

DungeonBuddy should:

- minimize repeated human re-grounding work,
- make canon inspection easy for humans,
- support inline generation tools such as statblocks and cards,
- provide stable APIs for future DungeonMind tools,
- and allow partial automation without requiring fully autonomous ingestion from day one. [I1]

### 4.3 Non-goals

DungeonBuddy is not trying to:

- fully automate creative authorship,
- replace the GM’s final canon authority,
- produce a universal ontology for all TTRPG systems on day one,
- or solve long-term autonomous world simulation before memory and canon are stable.

---

## 5. Design principles

### 5.1 Explicit structure over rediscovery

Anything the system can deterministically store should be stored explicitly rather than re-inferred from search every time. Examples include aliases, session IDs, valid date ranges, contradiction status, open threads, and source pointers. [R1][R3][R7]

### 5.2 Tiered memory over oversized prompts

Working context must stay small and stable. Durable knowledge belongs in external stores and should be selectively assembled into context. Recent memory-engineering guidance explicitly treats working context as only one tier in a larger memory architecture. [R4][R5][R6]

### 5.3 Canon is not the same as conversation

Not every observed statement becomes canonical truth. Session chatter, speculative planning, and generated material should land in different layers with different promotion rules. [R1][R2][R10]

### 5.4 Graph structure for relationships and evolution

Relational and temporal questions should be answered from structured edges and fact histories, not from isolated chunks whenever possible. [R3][R7][R8][R11]

### 5.5 Memory must evolve

New memories should link to prior memories and trigger updates, extensions, derived observations, contradictions, or review states rather than being blindly appended forever. [R9][R10][R11]

### 5.6 Source-grounded evidence is mandatory

Summaries are useful, but source artifacts remain the record of authored detail. Profiles and graph facts must point back to source artifacts and source spans when possible. [I1][R1][R7]

### 5.7 Evaluation must include systems behavior

A memory system that looks accurate on a benchmark but is too slow, too expensive, or too noisy is not production-ready. Evaluation must include answer quality, latency, token usage, update quality, contradiction handling, and retrieval behavior. [R1][R2][R12][R13][R14]

---

## 6. System context

DungeonBuddy sits between a campaign corpus and the GM-facing planning workflow.

```text
Campaign Artifacts
(recaps, world docs, prep notes, NPC docs, items, maps, generated outputs)
        |
        v
Artifact Registry + Ingestion Pipeline
        |
        v
Memory Controller
        |
        +--> Semantic / Episodic Memory Store
        |
        +--> Structured Canon Graph
        |
        +--> Compilation Pipeline
                |
                +--> Index View
                +--> Profile View
                +--> Evidence Packs
        |
        v
Retrieval Planner / Query Router
        |
        v
GM-facing Agent + Tools
(statblock, cards, maps, continuity checks, session planning)
```

---

## 7. Memory tiers

## 7.1 Tier 0: Working context

Tier 0 is the only memory the model directly consumes during generation. It must remain deliberately small and stable. It contains:

- system policies,
- current user goal,
- current campaign/session scope,
- recent turns,
- a compact task plan,
- a selected index slice,
- and a bounded evidence pack. [R4]

Tier 0 must **not** become a transcript dump. It is the active working set, not the archive.

### Tier 0 constraints

- token budget should be explicit and enforced,
- retrieved evidence should be structured and labeled,
- the number of loaded entities should be bounded,
- source excerpts should be clipped to relevant spans,
- and low-confidence evidence should be marked as such.

## 7.2 Tier 1: Session state

Tier 1 stores operational state for the active workflow. This includes:

- current scene or prep topic,
- current location focus,
- retrieval candidates selected during the conversation,
- recent tool outputs,
- execution checkpoints,
- speculative generated entities not yet promoted,
- and per-turn controller state. [R4][R5][R7]

Tier 1 is durable across the current planning/play session but is **not automatically canon**.

## 7.3 Tier 2: Semantic and episodic memory

Tier 2 stores searchable memory objects derived from conversations, recaps, artifacts, and tool outputs. These objects are not raw logs. They are structured and time-aware. They may include:

- observations,
- user/GM preferences,
- learned heuristics,
- episodic summaries,
- extracted claims,
- tentative canon candidates,
- and “lessons learned” style reflections. [R1][R2][R5][R9][R10]

Tier 2 is appropriate for retain/recall/reflect behavior and for retrieval that benefits from semantic search plus metadata filtering.

## 7.4 Tier 3: Structured canon graph

Tier 3 is the durable structural substrate of DungeonBuddy. It stores:

- entities,
- events,
- sessions,
- facts,
- relationships,
- temporal validity,
- contradiction status,
- and provenance. [R3][R7][R8]

Tier 3 is not optimized for loose similarity. It is optimized for correctness, traceability, temporal evolution, and relational reasoning.

## 7.5 Tier 4: Artifact store

Tier 4 stores original and generated artifacts:

- source markdown files,
- PDFs,
- maps,
- generated statblocks,
- NPC sheets,
- exports,
- images,
- and other high-entropy content. [I1][R4]

Tier 4 is the authoritative evidence layer for raw content. It should be addressed by pointer, not injected wholesale.

---

## 8. Compiled views

The user-facing interaction model is preserved as compiled views over the deeper tiers.

## 8.1 Index view

The Index is a compact table of contents. It contains:

- entity name,
- entity class,
- one-sentence summary,
- parent,
- key children,
- profile path or ID,
- corpus anchor,
- and a minimal salience hint. [I1]

The Index is optimized for navigation and turn-time scope control, not for being the full memory system.

## 8.2 Profile view

Profiles are compiled dossiers for entities or composite locations. They include:

- integrated summary,
- identity and role,
- narrative layers,
- relationships,
- terminal beats,
- open threads,
- evidence sufficiency,
- store reliability,
- and citations or source pointers. [I1]

Profiles are pointers plus condensation. They are not a replacement for source artifacts.

## 8.3 Source view

Source view provides raw artifact access or selected excerpts with provenance. This is the layer used when exact mechanics, exact scene detail, or exact wording matters. [I1]

---

## 9. Memory controller

The memory controller is the governing subsystem that turns storage into memory.

### 9.1 Responsibilities

For every new input, the controller decides:

- **store class**: ignore, Tier 1 only, Tier 2 memory, Tier 3 canon candidate, Tier 4 artifact only,
- **operation**: ADD, UPDATE, DELETE, NOOP, REVIEW_REQUIRED,
- **relation update**: link, contradict, supersede, extend, derive, alias candidate,
- **promotion path**: tentative, trusted, canonical,
- **retrieval mode** for future queries,
- and **recompilation scope**: which profiles/index entries must be refreshed. [R1][R4][R10]

### 9.2 Promotion policy

A default promotion policy:

- raw session conversation enters Tier 1,
- extracted observations and summaries enter Tier 2,
- candidate canon updates enter Tier 3 as tentative facts,
- high-confidence or reviewed facts become canonical,
- and affected compiled views are regenerated.

### 9.3 Confidence and authority

Each stored fact or relation should carry:

- confidence,
- authority class,
- extraction method,
- source density,
- review state,
- and temporal validity. [R1][R10]

Suggested authority classes:

- `authored_source`
- `session_recap`
- `gm_confirmed`
- `agent_inferred`
- `generated_speculative`

---

## 10. Canon graph model

## 10.1 Node types

At minimum the canon graph requires the following node families:

### Entity
Represents actors, places, factions, items, organizations, events, concepts, or rule objects.

### Session
Represents a play session or prep session.

### Episode
Represents a finer-grained scene or beat within a session.

### Fact
Represents an atomic, typed claim with provenance and temporal validity.

### Artifact
Represents a source or generated file.

### Profile
Represents a compiled entity or location dossier.

### IndexEntry
Represents a compiled manifest entry.

## 10.2 Edge types

Minimum edge set:

- `contains`
- `located_in`
- `appears_in`
- `interacts_with`
- `allied_with`
- `opposes`
- `owns`
- `caused`
- `knows_about`
- `mentioned_in`
- `supported_by`
- `derived_from`
- `contradicted_by`
- `supersedes`
- `updates`
- `extends`
- `derives`
- `alias_of`
- `same_as_candidate`
- `open_thread_for`
- `resolved_by`

The `updates`, `extends`, and `derives` relation family should be first-class because it maps naturally onto changing world facts, canon drift, and memory evolution. Supermemory explicitly uses this pattern for knowledge chains. [R11]

## 10.3 Fact schema

A fact should include at least:

- `fact_id`
- `subject_id`
- `predicate`
- `object_id` or `value`
- `valid_from`
- `valid_to`
- `created_at`
- `confidence`
- `authority`
- `source_artifact_id`
- `source_span`
- `extraction_method`
- `review_state`
- `contradiction_group_id`
- `superseded_by`

## 10.4 Example

```json
{
  "fact_id": "fact_lysandra_state_2026_04_09_001",
  "subject_id": "ent_lysandra_ironveil",
  "predicate": "mental_state",
  "value": "fraying / near-breakdown",
  "valid_from": "C2S20",
  "valid_to": null,
  "confidence": 0.78,
  "authority": "session_recap",
  "source_artifact_id": "art_session20_recap_md",
  "source_span": "L120-L146",
  "extraction_method": "llm_extract_v1",
  "review_state": "needs_review"
}
```

---

## 11. Retrieval architecture

DungeonBuddy should not run one generic retrieval pass for every query. It should explicitly route queries into retrieval modes.

## 11.1 Direct lookup mode

Use for questions like:

- “Who is Bonogo?”
- “What does the Slinkstone do?”

Flow:

1. resolve referent,
2. retrieve profile or source,
3. inject minimal evidence into Tier 0,
4. answer with citations. [I1]

## 11.2 Hierarchical drill-down mode

Use for place and region prep:

- “I’m prepping Mirathorn’s sewers”
- “What’s under the council building?”

Flow:

1. resolve container entity,
2. traverse containment edges,
3. retrieve overview profile,
4. expand relevant children on demand,
5. pull source detail only when asked. [I1][R8]

## 11.3 Cross-cutting lore mode

Use for relational questions:

- “What connects the cult, the meat corruption, and Lysandra?”
- “Who around Mossford is entangled with the Branchbound?”

Flow:

1. resolve primary entities or motifs,
2. traverse relationships and sessions,
3. assemble minimal explanatory subgraph,
4. add evidence pack to Tier 0,
5. synthesize grounded answer.

## 11.4 Temporal diff mode

Use for:

- “What changed since Session 19?”
- “What is currently true about Threnn?”
- “Did the party already resolve the Witness Seed thread?”

Flow:

1. locate target facts/events,
2. follow `updates`, `supersedes`, and validity windows,
3. compare prior and current state,
4. return current truth plus history. [R1][R11][R12]

## 11.5 Evidence mode

Use when exact mechanics or wording matter:

- “Quote the cult vow”
- “What are the item mechanics exactly?”

Flow:

1. retrieve artifact spans,
2. prefer raw sources over summaries,
3. include provenance and abstain when unsupported. [I1]

---

## 12. Retrieval planner

A retrieval planner sits above the stores and decides **how** to answer a query.

### 12.1 Planner inputs

- current turn
- recent thread context
- current session state
- likely referents
- active campaign scope
- tool availability
- retrieval budget

### 12.2 Planner outputs

- retrieval mode
- candidate entity set
- artifact scope
- graph traversal depth
- number of profiles to load
- whether evidence mode is required
- whether a review warning is needed

### 12.3 Planner discipline

The planner must:

- prefer deterministic retrieval when structure exists,
- use semantic recall only where it adds value,
- keep retrieval visible in traces,
- and avoid collapsing unrelated retrieval modes into a single top-k chunk list. [I1][R1][R3]

---

## 13. Ingestion pipeline

## 13.1 Bootstrap ingestion

Bootstrap flow:

1. register all artifacts,
2. parse corpus metadata,
3. extract entity candidates,
4. resolve duplicates and aliases,
5. construct initial canon graph,
6. generate initial Tier 2 summaries,
7. compile profiles,
8. compile the Index. [I1]

## 13.2 Post-session ingestion

After each session:

1. ingest recap and notes as artifacts,
2. store raw session state in Tier 1,
3. extract episodic observations to Tier 2,
4. generate candidate fact updates for Tier 3,
5. detect contradictions and alias candidates,
6. mark low-confidence updates for review,
7. update graph,
8. recompile affected profiles/index entries.

This explicitly addresses the earlier design’s unresolved update problem. The system should not depend on grep alone, though name matching may remain a fallback tool. [I1]

## 13.3 Planning-time capture

When the GM creates something during planning:

1. store the generated draft in Tier 1,
2. if saved, write artifact to Tier 4,
3. create tentative memory objects in Tier 2,
4. create tentative canon objects in Tier 3,
5. flag for review if generated-only,
6. recompile relevant views.

## 13.4 Consolidation windows

Borrowing from GAM’s distinction between active buffering and stable retention, DungeonBuddy should not immediately canonize every new observation. It should use a consolidation window:

- **fast path** for reviewed or high-authority facts,
- **deferred path** for low-confidence extracted claims,
- **reflection path** for derived observations and pattern summaries. [R10]

---

## 14. Dynamic linking and memory evolution

DungeonBuddy should explicitly support memory evolution.

### 14.1 Link creation

When new memories arrive, candidate links should be proposed to existing:

- entities,
- facts,
- sessions,
- contradiction groups,
- and open narrative threads. [R9][R10][R11]

### 14.2 Update semantics

New information can have different relationships to old information:

- **updates**: replaces prior fact state,
- **extends**: adds detail without contradiction,
- **derives**: expresses a synthesized conclusion,
- **contradicts**: conflicts and requires arbitration,
- **aliases**: may refer to the same entity under another label. [R9][R11]

### 14.3 Reflection

Reflection should be used sparingly and explicitly. It can generate:

- summary observations,
- likely unresolved arcs,
- candidate consistency warnings,
- and human-review prompts.

Reflections are not automatically canon. They should be stored as derived memory objects with lower authority until confirmed. [R1][R9]

---

## 15. Off-the-shelf tool strategy

DungeonBuddy should aggressively reuse existing systems instead of building a memory stack from scratch.

## 15.1 Preferred production backbone: Zep / Graphiti

Zep is a strong default candidate for the structured memory layer because it already provides:

- a temporal knowledge graph,
- context assembly,
- graph ingestion,
- thread continuity,
- and deterministic context block retrieval on each turn. [R5][R7]

Relevant reasons:

- Zep documentation states that its temporal knowledge graph powers agent memory and Graph RAG. [R7]
- It supports both thread-based chat ingestion and graph-based business/system data ingestion. [R5]
- It supports deterministic per-turn context assembly as well as tool-based graph search. [R5]

For DungeonBuddy this maps neatly to:

- recap ingestion,
- world-doc ingestion,
- current-thread context assembly,
- and graph-aware retrieval.

## 15.2 Experimental extraction and GraphRAG layer: LlamaIndex PropertyGraph

LlamaIndex should be used for experimentation and extraction because its Property Graph tooling is well suited to:

- entity/relation extraction,
- graph-oriented indexing,
- and GraphRAG experiments over documents. [R6]

Use it when:

- testing corpus bootstrap extraction,
- comparing graph extraction prompts,
- evaluating alternate graph stores,
- or prototyping hybrid document + graph retrieval.

## 15.3 Lightweight memory accelerator: Mem0

Mem0 is valuable when a thinner memory layer is needed quickly. Its README positions it as a universal memory layer for AI agents and describes multi-level memory, search/add APIs, and lightweight integration patterns. [R13]

Use Mem0 when:

- prototyping controller actions quickly,
- adding memory tools to an existing agent loop,
- or comparing lightweight persistent-memory behavior against graph-heavy stacks.

## 15.4 Reflective memory lab backend: Hindsight

Hindsight is attractive for experimentation because it exposes a simple retain/recall/reflect model and performs multiple retrieval strategies in parallel, including semantic, keyword, graph, and temporal search, then fuses and reranks the results. [R14]

Use Hindsight when:

- comparing memory-evolution behavior,
- testing reflection-driven summaries,
- benchmarking recall quality,
- or exploring episodic vs world-knowledge separation.

## 15.5 Search layer for artifacts: Meilisearch

Meilisearch is a good fit for artifact indexing and fast lexical/filter retrieval. Its GraphRAG guide explicitly recommends fast text indexing first, then graph construction, then focused subgraph retrieval before generation. [R8]

Use it for:

- source artifact recall,
- exact-text and filter search,
- narrowing candidate artifacts before graph traversal.

---

## 16. Service architecture

A practical service decomposition:

### 16.1 Artifact registry service
Responsibilities:

- register artifacts,
- store metadata,
- track versions,
- expose source spans.

### 16.2 Ingestion service
Responsibilities:

- parse artifacts,
- run extraction pipelines,
- call controller for write classification.

### 16.3 Memory controller service
Responsibilities:

- write decisions,
- conflict detection,
- promotion rules,
- recompilation scope.

### 16.4 Canon graph service
Responsibilities:

- graph storage,
- deterministic graph queries,
- temporal fact management,
- contradiction groups.

### 16.5 Semantic memory service
Responsibilities:

- searchable memory objects,
- retain/recall operations,
- metadata filtering.

### 16.6 Compilation service
Responsibilities:

- generate index slices,
- generate profiles,
- generate evidence packs.

### 16.7 Retrieval planner service
Responsibilities:

- classify query mode,
- plan retrieval,
- set budgets,
- orchestrate multi-store retrieval.

### 16.8 Agent runtime
Responsibilities:

- converse with GM,
- call tools,
- consume compiled views,
- trace decisions.

### 16.9 Evaluation harness
Responsibilities:

- benchmark retrieval and memory quality,
- measure latency/tokens,
- replay workloads,
- produce regression reports.

---

## 17. Example end-to-end flows

## 17.1 Session prep in a location

Prompt: “I’m prepping a session in Mirathorn’s sewers.”

Flow:

1. planner classifies as hierarchical drill-down,
2. retrieves sewers entity and compiled overview,
3. injects small index slice into Tier 0,
4. loads related child entities and open threads,
5. if cult content becomes salient, switches to cross-cutting mode,
6. if exact temple detail is needed, opens source artifact span. [I1]

## 17.2 Ask about an item

Prompt: “What does the Slinkstone do?”

Flow:

1. planner classifies direct lookup,
2. resolves item entity,
3. sees no profile needed for short item artifact,
4. retrieves source file excerpt,
5. answers with evidence. [I1]

## 17.3 Update canon after a recap

Input: Session 20 recap.

Flow:

1. artifact stored,
2. episodic observations extracted,
3. candidate entities linked,
4. mental-state update proposed for Lysandra,
5. contradiction check performed,
6. low-confidence updates queued for review,
7. affected profiles and index entries regenerated.

## 17.4 Save a new generated NPC

Prompt: “Save Rootjaw as a new entity.”

Flow:

1. generated output becomes Tier 1 speculative object,
2. controller assigns `generated_speculative`,
3. artifact written,
4. entity node and tentative facts created,
5. profile compiled,
6. index updated,
7. future retrieval can now find Rootjaw. [I1]

---

## 18. Evaluation strategy

DungeonBuddy must be evaluated at three layers: memory architecture, DungeonBuddy-specific retrieval, and system performance.

## 18.1 External benchmarks

Recommended external benchmarks:

- **LongMemEval** for long-term interactive memory, knowledge updates, and temporal reasoning. [R12][R11]
- **MemBench** for effectiveness, efficiency, and capacity across factual and reflective memory. [R9]
- **LoCoMo / LOCOMO** for long-term conversational memory comparisons used in current memory-system reporting. [R2][R13]
- **CogGov-Bench** or equivalent governed-memory tests if contradiction handling and stale-knowledge resistance become product-critical. [R15]

## 18.2 DungeonBuddy-specific benchmarks

Create benchmark classes for:

1. direct entity lookup,  
2. alias / oblique reference resolution,  
3. location drill-down,  
4. cross-session continuity,  
5. contradiction resolution,  
6. temporal diffing,  
7. source-grounded evidence recall,  
8. planning-time save and future retrieval.

## 18.3 Metrics

Track at least:

- answer correctness,
- evidence sufficiency,
- false canonization rate,
- contradiction-detection rate,
- entity-resolution accuracy,
- retrieval depth,
- artifacts opened,
- graph traversals,
- median and tail latency,
- token usage,
- human-review rate.

## 18.4 Regression discipline

Every change to extraction, controller policies, graph schema, retrieval routing, or compilation must be benchmarked against frozen workloads.

---

## 19. Observability and debugging

DungeonBuddy should make retrieval visible.

### 19.1 Required trace events

For each turn, record:

- query classification,
- resolved referents,
- retrieval mode,
- stores touched,
- graph queries issued,
- candidate entities considered,
- compiled views loaded,
- evidence pack size,
- controller decisions,
- and any review warnings. [I1][R2]

### 19.2 Debug surfaces

Provide at least:

- an “answer support” panel showing entities, facts, and artifacts used,
- a controller audit log,
- a contradiction review queue,
- a stale-profile queue,
- and replayable benchmark traces.

---

## 20. Security and trust boundaries

Even though DungeonBuddy is not an enterprise HR system, it still needs trust boundaries.

- authored world docs should be distinguishable from generated speculative content,
- canon writes should be reversible,
- reviewable updates should not silently promote,
- and every generated claim used in an answer should be traceable to evidence or marked as derived. [R1][R2][R15]

---

## 21. Recommended build plan

## Phase 1: Thin slice over current design

Build:

- artifact registry,
- entity registry,
- compiled Index,
- compiled Profiles,
- direct lookup mode,
- source evidence mode.

Goal: preserve the current user experience, but back it with explicit IDs and provenance.

## Phase 2: Canon graph backbone

Build:

- temporal fact model,
- relationship edges,
- contradiction groups,
- `updates` / `extends` / `derives`,
- temporal diff mode.

Goal: make world truth queryable and evolvable.

## Phase 3: Memory controller

Build:

- write classification,
- promotion rules,
- review queues,
- recompilation logic,
- controller traces.

Goal: stop memory from becoming append-only noise.

## Phase 4: Multi-mode retrieval

Build:

- retrieval planner,
- hierarchical drill-down,
- cross-cutting lore mode,
- evidence pack assembly,
- explicit budgets.

Goal: stop treating all retrieval as generic search.

## Phase 5: Tool integration

Build:

- statblock generation hooks,
- card generation hooks,
- save-to-canon flow,
- continuity warnings.

## Phase 6: Benchmarks and hardening

Build:

- benchmark harness,
- replay traces,
- regression suite,
- comparison runs across backend options.

---

## 22. Open questions

The following decisions should remain open until implementation evidence exists:

1. Which backend becomes primary: Zep-first, Neo4j/LlamaIndex-first, or hybrid?
2. How much profile generation should be automated vs reviewed?
3. Which facts auto-promote and which always require review?
4. How aggressive should reflection be?
5. Should “planning canon” exist as a separate authority class before promotion to canon?
6. When does a generated entity become retrievable in normal answers?
7. How much of the filesystem hierarchy should be mirrored into graph edges vs computed on demand? [I1]

---

## 23. Final recommendation

The right move is not to throw away the current DungeonMindBuddy idea. The right move is to reinterpret it.

Keep the binder metaphor. Keep the Index. Keep Profiles. Keep source drill-down. But stop treating them as the whole architecture. The real system should be a tiered memory stack governed by a controller and anchored in a temporal canon graph, with compiled views optimized for human navigation and LLM prompt efficiency. That architecture matches both the problems already identified in the internal design and the broader direction of current agent-memory research. [I1][R1][R2][R3][R4][R5][R7][R9][R10][R11]

---

## 24. References

### Internal sources

- **[I1]** *DungeonMindBuddy: Corpus-Grounded Session Planning Agent* (uploaded working design draft, current conversation, April 2026). Key ideas used here: Index/Profile/Source drill-down, known retrieval risks, token-budget rationale, profile-vs-source distinctions, and phased corpus-building plan.

### External sources

- **[R1]** Du, Pengfei. *Memory for Autonomous LLM Agents: Mechanisms, Evaluation, and Emerging Frontiers.* arXiv:2603.07670, March 2026.  
  URL: https://arxiv.org/abs/2603.07670

- **[R2]** Jiang et al. *Anatomy of Agentic Memory: Taxonomy and Empirical Analysis of Evaluation and System Limitations.* arXiv:2602.19320, February 2026.  
  URL: https://arxiv.org/abs/2602.19320

- **[R3]** Yang et al. *Graph-based Agent Memory: Taxonomy, Techniques, and Applications.* arXiv:2602.05665, February 2026.  
  URL: https://arxiv.org/abs/2602.05665

- **[R4]** Mjgmario. *Memory Engineering for AI Agents (2026).* January 2026. Used here specifically for tiered-memory and memory-controller framing.  
  URL: https://medium.com/@mjgmario/memory-engineering-for-ai-agents-how-to-build-real-long-term-memory-and-avoid-production-1d4e5266595c

- **[R5]** Zep Documentation. *Architecture Patterns* and *Quick Start Guide.* Accessed April 2026. Used for thread + graph ingestion patterns, deterministic context blocks, and context assembly.  
  URLs:  
  https://help.getzep.com/architecture-patterns  
  https://help.getzep.com/quick-start-guide

- **[R6]** LlamaIndex Documentation. *Using a Property Graph Index.* Accessed April 2026. Used for graph extraction and GraphRAG experimentation strategy.  
  URL: https://developers.llamaindex.ai/python/framework/module_guides/indexing/lpg_index_guide/

- **[R7]** Zep Documentation. *Graph Overview.* Accessed April 2026. Used for temporal knowledge graph and Graph RAG positioning.  
  URL: https://help.getzep.com/graph-overview

- **[R8]** Meilisearch Blog. *What is GraphRAG: Complete guide [2026].* Published September 15, 2025. Used for the practical “text index first, graph second, focused subgraph retrieval before generation” implementation pattern.  
  URL: https://www.meilisearch.com/blog/graph-rag

- **[R9]** Xu et al. *A-Mem: Agentic Memory for LLM Agents.* arXiv:2502.12110 / NeurIPS 2025 poster. Used for dynamic indexing, dynamic linking, and memory evolution concepts.  
  URL: https://arxiv.org/abs/2502.12110

- **[R10]** Wu et al. *GAM: Hierarchical Graph Memory for LLM-based Agents.* ICLR 2026 Workshop MemAgents. Used for active-buffer vs archived-topic memory separation and graph-guided multi-factor retrieval.  
  URL: https://openreview.net/forum?id=mmsVZGaYyp

- **[R11]** Supermemory Research. *State-of-the-Art Agent Memory.* Accessed April 2026. Used for relational versioning (`updates`, `extends`, `derives`) and temporal grounding patterns.  
  URL: https://supermemory.ai/research/

- **[R12]** Wu et al. *LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory.* arXiv:2410.10813, 2024.  
  URL: https://arxiv.org/abs/2410.10813

- **[R13]** Mem0 README and research references. Accessed April 2026. Used for lightweight persistent memory integration patterns and LOCOMO-oriented claims.  
  URL: https://github.com/mem0ai/mem0

- **[R14]** Hindsight README. Accessed April 2026. Used for retain/recall/reflect API design and parallel semantic/keyword/graph/temporal retrieval with fusion and reranking.  
  URL: https://github.com/vectorize-io/hindsight

- **[R15]** Estey-Ang, Andrew. *Pith: A Governed Cognitive Architecture for Persistent AI Memory.* Technical Disclosure Commons, March 30, 2026. Used for governed-memory framing, stale-knowledge resistance, and context-integrity emphasis.  
  URL: https://www.tdcommons.org/dpubs_series/9660/

---

## 25. Short implementation recommendation

If a concrete implementation decision is needed immediately:

- use **Zep** as the first production-grade memory/canon backbone,
- use **LlamaIndex Property Graph** for extraction experiments and GraphRAG lab work,
- use **Meilisearch** for artifact-level lexical and metadata retrieval,
- keep **Mem0** as the lightest memory API fallback,
- and keep **Hindsight** as the reflective-memory benchmark and comparison backend.

That combination maximizes reuse while preserving the ability to evolve toward a stronger bespoke canon model later. [R5][R6][R7][R8][R13][R14]
