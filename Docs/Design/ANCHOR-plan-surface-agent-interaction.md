# Anchor — Plan Surface Agent Interaction

**Status:** Active anchor  
**Updated:** 2026-06-22  
**Scope:** `/plan` surface, toolbar/projection flow, Agent Interaction Bar/Pane, source-vocabulary adapter, Hermes-backed ask flow, and future app-level Agent Interaction provider.

---

## 1. One-Sentence Anchor

The `/plan` Agent Interaction work is about turning DungeonBuddy's planning surface into a calm, inspectable GM workspace where a toolbar, canvas, projections, source-backed answers, and agent traces cooperate without turning the surface into a hidden knowledge store, raw retrieval dump, or unreviewed mutation layer.

Short form:

```txt
/plan is the workshop surface.
Agent Interaction is the inspectable assistant layer.
SourceBundle is the evidence vocabulary.
Hermes is a possible runtime, not canon.
The corpus and live packet remain the evidence authorities.
```

---

## 2. Why This Work Exists

The project has been converging on a broader product pattern:

```txt
calm toolbar
busy but understandable canvas
projection layer for focused tools/details
agent interaction layer for questions, traces, and guided next steps
reviewed write boundaries for durable changes
```

The `/plan` surface is the first place all of these pressures collide.

Before this work, `/plan` had useful surface-local mechanics: a configured surface, a canvas, a transitional right-side Tools drawer, and projection affordances. The missing piece was a durable place for the GM to ask questions, inspect grounding, and let an agent help without losing trust in the evidence path.

This workstream gives that missing piece a shape.

---

## 3. Current Branch Truth

The exploratory branch currently under review is:

```txt
cursor/cloud-agent-1782137144843-h0ddf
```

It is a valuable working branch, but it is intentionally broader than a clean PR should be. It currently mixes:

```txt
/plan Agent Interaction UI
source-bundle adapter
live API typing
backend /api/live/source-bundle route
backend /api/live/query Hermes routing
Hermes plugin updates
trace telemetry
context sufficiency UI
manifest context query refinements
ingested corpus library / manifest updates
docs and self-continuity handoff
pytest live workspace artifacts
```

Design conclusion:

```txt
Do not land this branch as one PR.
Use it as the working branch to slice reviewable PRs.
```

The branch proves useful product behavior, but the landing strategy must preserve separation between evidence vocabulary, agent runtime, UI surface, and generated artifacts.

---

## 4. Canonical Documents To Read

Read in this order when picking the workstream back up:

1. `Docs/Design/ANCHOR-plan-surface-agent-interaction.md` — this anchor.
2. `Docs/Design/ROADMAP-plan-surface-agent-interaction.md` — landing roadmap and PR sequence.
3. `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md` — surface/toolbox architecture.
4. `Docs/Design/CONTRACT-surface-vocabulary-boundary-v0.md` — SourceArtifact / SourceAnchor / SourceUnit boundary.
5. `Docs/Experiments/PLAN-SURFACE-LADDER-TRACKING.md` — rung tracking.
6. `Docs/Plans/HANDOFF-self-continuity-plan-toolbar-ingestion-design.md` — prior toolbar / ingestion plan.
7. `Docs/Plans/HANDOFF-ontology-taxonomy-plan-surface-consumer-alignment.md` — alignment with graph-memory vocabulary.
8. `Docs/Plans/HANDOFF-self-continuity-hermes-agent-interaction-bar.md` — Hermes spike continuity, if present on the branch.
9. `.hermes.md` — Hermes memory/canon rules.

Related backlog idea:

```txt
Backlog.md — [IDEA] Plan surface dogfood — calm toolbar, busy canvas, branching slide graph
```

---

## 5. Core Product Model

### 5.1 Surface

A **Surface** is the top-level work abstraction. A surface composes:

```txt
Nav region
Tool region
Edit region
Canvas region
Projection region
Agent Interaction affordance
```

`/plan` is the first intentional configured surface. It is not the only future surface.

### 5.2 Toolbar

The toolbar is the GM's quick launch strip for surface-specific tools. It should feel calm and predictable. It opens projections or tool panels; it should not become a second application shell.

Toolbar responsibilities:

```txt
show available tools
open a projection
preserve canvas context
avoid hiding source boundaries
```

Toolbar non-responsibilities:

```txt
owning agent memory
owning corpus writes
owning canonical state
owning projection implementation details
```

### 5.3 Canvas

The canvas is the main planning workspace. It can be visually rich and busy, but it must stay legible.

The canvas should publish ambient context outward, such as:

```txt
campaign id
session id
selected beat or target
available projections
current surface mode
```

It should not become the source of campaign continuity.

### 5.4 Projection Layer

Projection is the focused detail/tool layer. Existing reference-chip projection and toolbar projection should converge on one projection path.

Design rule:

```txt
One projection registry. One adaptive projection container.
No second projection stack for Agent Interaction.
```

### 5.5 Agent Interaction

Agent Interaction is the GM-facing assistant layer. It lets the GM ask questions, inspect evidence, see traces, and eventually carry a multi-turn conversation.

The current branch keeps Agent Interaction plan-scoped, mounted inside `PlanSurfaceShell`. That is acceptable as a proof slice.

Target architecture is broader:

```txt
AgentInteractionProvider above routes/surfaces
bottom Agent Interaction Bar
expandable Agent Interaction Pane
surfaces publish context into the provider
provider persists only bounded UI state and proof pointers
```

### 5.6 Source Bundle

`IngestionSourceBundle` is the read-only source vocabulary consumed by the Agent Interaction surface.

It maps ingestion artifacts into:

```txt
SourceArtifact -> SourceAnchor -> SourceUnit
```

It should expose locators, roles, authority, lifecycle, evidence role, and coverage diagnostics without embedding corpus bodies.

### 5.7 Hermes

Hermes is an agent runtime option, not the campaign-memory authority.

The useful branch proof is:

```txt
live backend = native manifest retrieval / context packet review
hermes backend = preflight retrieval + Hermes synthesis + trace telemetry
```

Hermes may eventually provide multi-turn conversation and tool loops. It must not become campaign canon or bypass DungeonBuddy's evidence/corpus boundaries.

---

## 6. Canon Decisions

1. **Surface remains the top-level work abstraction.** `SurfaceConfig` composes Nav, Tool, Edit, Canvas, Projection, and Agent Interaction affordances.
2. **`/plan` is the workshop, not the whole product.** The plan surface is where preparation, retrieval, arrangement, and tool-assisted thinking converge.
3. **Agent Interaction is app/user scoped in the target architecture.** The branch may prove it inside `/plan`, but the durable shape is app-level provider + bottom bar/pane.
4. **The bottom bar is the durable interaction affordance.** The right-side Tools drawer is transitional surface-local implementation state.
5. **Projection stays singular.** Agent Interaction should not create a second projection path.
6. **Surfaces publish context; they do not own continuity.** Surface context helps the agent know where the GM is working, but continuity belongs to DungeonBuddy's corpus/live/session stores.
7. **The provider stores pointers and bounded summaries only.** It must not store corpus bodies, normalized recap bodies, statblock content, graph internals, or raw retrieval payloads.
8. **`IngestionSourceBundle` is the adapter vocabulary for recap-ingestion proof.** Agent Interaction consumes SourceArtifact / SourceAnchor / SourceUnit, not raw `_normalized/`, `_breadcrumbed/`, `.records_meta.jsonl`, or corpus-impact internals.
9. **Hermes must receive preflight evidence, not blind trust.** If Hermes synthesizes, the UI still needs retrieval/admission diagnostics.
10. **Hermes memory is not campaign canon.** Conversation memory may exist as thread continuity, but campaign facts must be retrieved from DungeonBuddy evidence.
11. **The current branch is a quarry, not a single PR.** Slice it before merge.

---

## 7. Data Boundary Model

### Allowed in Agent Interaction local persistence

```txt
pane open/closed state
active backend selection
bounded turn summaries
question text
answer summaries
trace ids
admitted/rejected counts
selected surface/campaign/session pointers
```

### Not allowed in Agent Interaction local persistence

```txt
corpus document bodies
retrieved text excerpts
context_packet bodies
normalized recap text
breadcrumbed recap text
session_memory_jsonl bodies
statblock markdown/content
live operational state snapshots
ontology graph internals
Hermes raw session logs
```

### Allowed in API responses for inspection

```txt
context packet excerpts
trace metadata
prompt preview in local/dev mode
source bundle locators
coverage diagnostics
artifact references
warnings
```

### Dangerous unless explicitly bounded

```txt
full prompt preview
absolute local filesystem paths
Hermes session/log paths
large retrieved excerpt payloads
raw corpus routes exposed as product labels
```

---

## 8. Current Working Concepts

### Source vocabulary adapter

The source bundle adapter is a clean foundation slice. It should be landed before UI consumers depend on raw ingestion internals.

Good signs:

```txt
read-only adapter
corpus bodies not embedded
source units derived from ingested corpus library
locators are repo/corpus-relative rather than body payloads
```

### Context sufficiency ladder

The context sufficiency ladder gives the GM an inspectable answer to:

```txt
Do we have enough evidence to answer this?
What evidence is strong campaign text?
What evidence is weak, broad, route-only, or metadata?
What should be opened next?
```

This belongs in Agent Interaction because it supports trust in the answer, not because it is an editor feature.

### Hermes backend

Hermes integration is useful only if it remains inspectable.

The branch's strongest Hermes pattern is:

```txt
run DungeonBuddy context lookup first
embed admitted evidence in the Hermes prompt
return answer + context packet + agent trace
show prompt/trace/token estimates for audit
```

Known limitation:

```txt
current Hermes path is one-shot, not session-continuous
```

### Agent Interaction turn history

Turn history should be bounded and should not store retrieved evidence bodies.

Preferred wording:

```txt
bounded turn summaries, no retrieved evidence bodies
```

Avoid saying “metadata-only” if answer summaries are persisted.

---

## 9. Invariants

Do not violate these while slicing the branch:

```txt
Do not make Agent Interaction a mutable knowledge store.
Do not let Agent Interaction consume raw ingestion internals as its product model.
Do not duplicate projection paths.
Do not duplicate statblock generation logic.
Do not remove terminal fallback paths for ingestion.
Do not create surface-owned corpus category enums.
Do not build alias resolution, identity merge, relationship inference, or graph traversal here.
Do not store corpus content in provider/localStorage persistence.
Do not bypass corpus writer safety or two-phase commit.
Do not treat Hermes memory as canon.
Do not land generated pytest live workspace artifacts.
Do not land the current broad branch as one PR.
```

---

## 10. Branch Hygiene Rules

Before opening any PR from this branch:

1. Remove changes under:

```txt
evals/c2_live_prep/live/_pytest/**
```

2. Confirm whether generated manifest/library updates are required for the slice.
3. Keep docs updates with the slice they support, or split them into a docs-only PR.
4. Avoid bundling source-bundle adapter, Hermes runtime, and UI proof into one review.
5. State whether the slice is:

```txt
source-vocabulary adapter
backend agent runtime
/plan UI consumer
docs/roadmap
```

---

## 11. Verification Gates

Minimum verification before claiming a slice is ready:

```bash
cd apps/live-control-ui && npm run build
cd apps/live-control-ui && npm test -- --run src/planSurface
uv run pytest tests/test_live_control_server.py tests/test_hermes_dungeonbuddy_plugin.py tests/test_source_bundle.py tests/test_manifest_context_query.py -q
```

Slice-specific gates:

### Source bundle adapter

```bash
uv run pytest tests/test_source_bundle.py tests/test_ingested_corpus_library.py -q
```

### Hermes backend

```bash
uv run pytest tests/test_live_control_server.py tests/test_hermes_dungeonbuddy_plugin.py -q
```

### `/plan` UI proof

```bash
cd apps/live-control-ui && npm test -- --run src/planSurface/PlanSurfaceShell.test.tsx src/planSurface/components/contextSufficiencyLadder.test.ts
```

### Manifest/context query changes

```bash
uv run pytest tests/test_manifest_context_query.py tests/test_planning_corpus_manifest.py -q
```

---

## 12. Recommended Landing Shape

The roadmap document owns the detailed sequence, but the recommended high-level landing shape is:

```txt
PR A — source bundle adapter
PR B — Hermes live-query backend + trace
PR C — plan-scoped Agent Interaction bar proof
PR D — docs / self-continuity cleanup
PR E — app-level provider hoist
```

The first merge should be the source bundle adapter unless the operator explicitly prioritizes UI dogfood first.

---

## 13. Re-Anchor Procedure

When resuming this work:

1. Read this file.
2. Read `Docs/Design/ROADMAP-plan-surface-agent-interaction.md`.
3. Compare the working branch against `main`.
4. Remove pytest workspace artifacts before PR slicing.
5. Pick exactly one slice from the roadmap.
6. Write or update the slice handoff/allowlist before implementation.
7. Do not expand the slice midstream because adjacent code is nearby.

The question to ask before each change:

```txt
Does this make /plan more inspectable and trustworthy without turning Agent Interaction into the database, the corpus, or hidden canon?
```
